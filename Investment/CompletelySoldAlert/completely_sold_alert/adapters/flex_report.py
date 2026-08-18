"""Subprocess adapter for IBKR-Flex-BuySell report refresh."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from completely_sold_alert.config import AppSettings


def run_flex_refresh(settings: AppSettings) -> tuple[bool, str]:
    flex_dir = Path(settings.data.flex_project_dir).resolve()
    script = flex_dir / "flex_buysell_report.py"
    if not script.is_file():
        return False, f"flex_buysell_report.py not found: {script}"

    python = settings.data.flex_python
    cmd = [python, str(script)]
    if settings.data.refresh_mode == "download":
        cmd.append("--download")
    else:
        cmd.append("--from-downloads")

    out_path = Path(settings.data.report_path).resolve()
    cmd.extend(["--output", str(out_path)])

    try:
        result = subprocess.run(
            cmd,
            cwd=str(flex_dir),
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "flex_buysell_report timed out after 3600s"
    except OSError as exc:
        return False, str(exc)

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()[:500]
        return False, f"exit {result.returncode}: {err}"

    if not out_path.is_file():
        return False, f"report not created: {out_path}"

    return True, "ok"
