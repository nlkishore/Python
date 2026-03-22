"""OWASP Dependency-Check CLI (optional)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from pr_review.analyzers.models import AnalyzerRun
from pr_review.config.schema import Settings


def run_dependency_check(settings: Settings, repo: Path, reports_dir: Path) -> AnalyzerRun:
    if not settings.dependency_check.enabled:
        return AnalyzerRun("dependency-check", True, 0, "skipped (disabled)", "")

    exe = settings.dependency_check.executable.strip()
    if not exe:
        return AnalyzerRun("dependency-check", False, -1, "", "dependency_check.executable not set")

    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / "dependency-check-report"
    cmd = [
        exe,
        "--project",
        settings.bitbucket.repository_slug,
        "--scan",
        str(repo),
        "--format",
        "JSON",
        "--out",
        str(out),
    ]
    env = os.environ.copy()
    try:
        cp = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
            timeout=max(settings.pipeline.analyzer_timeout_sec, 7200),
            check=False,
        )
    except FileNotFoundError:
        return AnalyzerRun("dependency-check", False, -1, "", f"executable not found: {exe}")
    except subprocess.TimeoutExpired as e:
        return AnalyzerRun("dependency-check", False, -1, e.stdout or "", "Dependency-Check timeout")

    return AnalyzerRun("dependency-check", cp.returncode == 0, cp.returncode, cp.stdout or "", cp.stderr or "")
