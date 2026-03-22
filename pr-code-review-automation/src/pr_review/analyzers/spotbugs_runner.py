"""Run SpotBugs CLI (+ optional FindSecBugs plugin)."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from pr_review.analyzers.models import AnalyzerRun
from pr_review.build.maven_runner import write_classpath_file
from pr_review.config.schema import Settings


def _spotbugs_executable(home: str) -> Path:
    p = Path(home)
    if p.is_file():
        return p
    if platform.system() == "Windows":
        for name in ("spotbugs.bat", "spotbugs.cmd"):
            cand = p / "bin" / name
            if cand.is_file():
                return cand
    ex = p / "bin" / "spotbugs"
    if ex.is_file():
        return ex
    raise FileNotFoundError(f"SpotBugs executable not found under: {home}")


def run_spotbugs(settings: Settings, repo: Path, reports_dir: Path) -> AnalyzerRun:
    if not settings.spotbugs.enabled:
        return AnalyzerRun("spotbugs", True, 0, "skipped (disabled)", "")

    home = settings.spotbugs.home.strip()
    if not home:
        return AnalyzerRun("spotbugs", False, -1, "", "spotbugs.home not set")

    try:
        exe = _spotbugs_executable(home)
    except FileNotFoundError as e:
        return AnalyzerRun("spotbugs", False, -1, "", str(e))

    cp_file = repo / "target" / "spotbugs-auxclasspath.txt"
    mcp = write_classpath_file(settings, repo, cp_file)
    if not mcp.ok:
        return AnalyzerRun(
            "spotbugs",
            False,
            mcp.exit_code,
            mcp.stdout,
            mcp.stderr or "Could not build aux classpath",
        )

    out_xml = reports_dir / "spotbugs-report.xml"
    reports_dir.mkdir(parents=True, exist_ok=True)

    classes_dir = repo / "target" / "classes"
    if not classes_dir.is_dir():
        return AnalyzerRun("spotbugs", False, -1, "", "target/classes missing — compile first")

    cmd: list[str] = [
        str(exe),
        "-textui",
        "-xml:withMessages",
        "-output",
        str(out_xml),
        "-auxclasspathFromFile",
        str(cp_file),
    ]
    src_java = repo / "src" / "main" / "java"
    if src_java.is_dir():
        cmd.extend(["-sourcepath", str(src_java)])
    plugin = settings.spotbugs.findsecbugs_plugin_jar.strip()
    if plugin and Path(plugin).is_file():
        cmd.extend(["-pluginList", plugin])
    cmd.append(str(classes_dir))

    env = os.environ.copy()
    if settings.paths.java_home:
        env["JAVA_HOME"] = settings.paths.java_home

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
    except subprocess.TimeoutExpired as e:
        return AnalyzerRun("spotbugs", False, -1, e.stdout or "", "SpotBugs timeout")

    # SpotBugs returns non-zero if bugs found
    ok = out_xml.is_file()
    return AnalyzerRun("spotbugs", ok, cp.returncode, cp.stdout or "", cp.stderr or "")
