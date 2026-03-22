"""PMD CLI — error-prone / security categories (NPE-style patterns, etc.)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from pr_review.analyzers.models import AnalyzerRun
from pr_review.config.schema import Settings


def run_pmd(settings: Settings, repo: Path, reports_dir: Path) -> AnalyzerRun:
    if not settings.pmd.enabled:
        return AnalyzerRun("pmd", True, 0, "skipped (disabled)", "")

    exe = settings.pmd.executable
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / "pmd-report.xml"
    src = repo / "src" / "main" / "java"
    if not src.is_dir():
        return AnalyzerRun("pmd", True, 0, "skipped (no src/main/java)", "")

    rules = ",".join(settings.pmd.rulesets)
    # PMD 7: pmd check -d src/main/java -R ruleset -f xml -r report.xml
    cmd = [
        exe,
        "check",
        "-d",
        str(src),
        "-R",
        rules,
        "-f",
        "xml",
        "-r",
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
            timeout=settings.pipeline.analyzer_timeout_sec,
            check=False,
        )
    except FileNotFoundError:
        return AnalyzerRun("pmd", False, -1, "", f"executable not found: {exe}")
    except subprocess.TimeoutExpired as e:
        return AnalyzerRun("pmd", False, -1, e.stdout or "", "PMD timeout")

    return AnalyzerRun("pmd", True, cp.returncode, cp.stdout or "", cp.stderr or "")
