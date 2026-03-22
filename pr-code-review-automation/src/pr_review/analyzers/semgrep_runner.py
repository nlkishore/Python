"""Semgrep (OWASP-oriented rules via config packs)."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pr_review.analyzers.models import AnalyzerRun
from pr_review.config.schema import Settings


def run_semgrep(settings: Settings, repo: Path, reports_dir: Path) -> AnalyzerRun:
    if not settings.semgrep.enabled:
        return AnalyzerRun("semgrep", True, 0, "skipped (disabled)", "")

    exe = settings.semgrep.executable
    out = reports_dir / "semgrep.sarif"
    reports_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe,
        *settings.semgrep.extra_args,
        "--sarif",
        "--output",
        str(out),
        str(repo),
    ]
    env = os.environ.copy()
    try:
        cp = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
            timeout=settings.pipeline.analyzer_timeout_sec,
            check=False,
        )
    except FileNotFoundError:
        return AnalyzerRun("semgrep", False, -1, "", f"executable not found: {exe}")
    except subprocess.TimeoutExpired as e:
        return AnalyzerRun("semgrep", False, -1, e.stdout or "", "Semgrep timeout")

    return AnalyzerRun("semgrep", cp.returncode in (0, 1), cp.returncode, cp.stdout or "", cp.stderr or "")
