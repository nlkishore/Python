"""SonarScanner — server-side analysis; complements IDE SonarLint rules when bound to same Quality Profile."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from pr_review.analyzers.models import AnalyzerRun
from pr_review.config.schema import Settings


def write_sonar_project_properties(
    settings: Settings,
    repo: Path,
    reports_dir: Path,
) -> Path:
    props = reports_dir / "sonar-project.properties"
    reports_dir.mkdir(parents=True, exist_ok=True)
    bb = settings.bitbucket
    key = settings.sonarqube.project_key.strip() or f"{bb.project_key}:{bb.repository_slug}".lower()
    lines = [
        f"sonar.projectKey={key}",
        f"sonar.projectName={bb.repository_slug}",
        "sonar.sources=src/main/java",
        "sonar.java.binaries=target/classes",
        f"sonar.host.url={settings.sonarqube.host_url.rstrip('/')}",
    ]
    props.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return props


def run_sonar_scanner(settings: Settings, repo: Path, reports_dir: Path) -> AnalyzerRun:
    if not settings.sonarqube.enabled:
        return AnalyzerRun("sonar-scanner", True, 0, "skipped (disabled)", "")

    host = settings.sonarqube.host_url.strip()
    token = settings.sonarqube.token.strip()
    if not host or not token:
        return AnalyzerRun("sonar-scanner", False, -1, "", "sonarqube.host_url and token required")

    write_sonar_project_properties(settings, repo, reports_dir)
    exe = settings.sonarqube.scanner_path

    env = os.environ.copy()
    env["SONAR_TOKEN"] = token
    env["SONAR_HOST_URL"] = host

    cmd = [exe, f"-Dproject.settings={reports_dir / 'sonar-project.properties'}"]
    try:
        cp = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
            timeout=max(settings.pipeline.analyzer_timeout_sec, 3600),
            check=False,
        )
    except FileNotFoundError:
        return AnalyzerRun("sonar-scanner", False, -1, "", f"executable not found: {exe}")
    except subprocess.TimeoutExpired as e:
        return AnalyzerRun("sonar-scanner", False, -1, e.stdout or "", "SonarScanner timeout")

    return AnalyzerRun("sonar-scanner", cp.returncode == 0, cp.returncode, cp.stdout or "", cp.stderr or "")
