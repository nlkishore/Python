"""End-to-end PR review pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console

from pr_review.analyzers.dependency_check_runner import run_dependency_check
from pr_review.analyzers.pmd_runner import run_pmd
from pr_review.analyzers.semgrep_runner import run_semgrep
from pr_review.analyzers.sonar_runner import run_sonar_scanner
from pr_review.analyzers.spotbugs_runner import run_spotbugs
from pr_review.build.maven_runner import run_maven_compile
from pr_review.config.schema import Settings
from pr_review.diff_parser import parse_unified_diff, ranges_to_json_serializable
from pr_review.git_ops import (
    fetch_pr_and_target,
    git_diff_range,
    merge_base,
    _inject_auth_into_git_url,
)
from pr_review.reports.writer import write_html_summary, write_json
from pr_review.scm.bitbucket_server import BitbucketServerClient


def run_pipeline(settings: Settings, console: Console | None = None) -> dict[str, Any]:
    c = console or Console()
    bb = settings.bitbucket
    reports_dir = settings.reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "bitbucket": {
            "server_url": bb.server_url,
            "project_key": bb.project_key,
            "repository_slug": bb.repository_slug,
            "pull_request_id": bb.pull_request_id,
        },
        "steps": {},
    }

    client = BitbucketServerClient(settings)
    try:
        c.print("[bold]Fetching PR metadata from Bitbucket Server…[/bold]")
        meta = client.get_pull_request()
        summary["pull_request"] = {
            "title": meta.title,
            "from_branch": meta.from_branch,
            "to_branch": meta.to_branch,
            "from_commit": meta.from_commit,
            "to_commit": meta.to_commit,
        }
        change_paths = client.iter_change_paths()
        summary["pull_request"]["changed_paths_api"] = change_paths
    finally:
        client.close()

    auth_url = _inject_auth_into_git_url(
        settings.clone_url(),
        bb.username,
        bb.token,
    )
    c.print("[bold]Preparing Git workspace…[/bold]")
    repo = fetch_pr_and_target(settings, meta, auth_url)
    summary["workspace"] = str(repo)

    c.print("[bold]Computing merge-base diff…[/bold]")
    try:
        base = merge_base(settings, repo, meta.to_commit, meta.from_commit)
        diff_text = git_diff_range(settings, repo, base, meta.from_commit)
    except RuntimeError as e:
        summary["steps"]["diff"] = {"ok": False, "error": str(e)}
        diff_text = ""
        c.print(f"[yellow]Diff warning:[/yellow] {e}")
    else:
        summary["steps"]["diff"] = {"ok": True, "merge_base": base}
        paths_map = parse_unified_diff(diff_text)
        files_json = ranges_to_json_serializable(paths_map)
        changed_lines_path = reports_dir / "changed-lines.json"
        write_json(
            changed_lines_path,
            {
                "pull_request_id": bb.pull_request_id,
                "from_commit": meta.from_commit,
                "to_commit": meta.to_commit,
                "merge_base": base,
                "files": files_json,
            },
        )
        summary["steps"]["changed_lines_report"] = str(changed_lines_path)

    compile_result = None
    if settings.pipeline.maven_compile:
        c.print("[bold]Maven compile…[/bold]")
        compile_result = run_maven_compile(settings, repo)
        compile_path = reports_dir / "compile-report.json"
        write_json(
            compile_path,
            {
                "ok": compile_result.ok,
                "exit_code": compile_result.exit_code,
                "issues": compile_result.issues,
            },
        )
        summary["steps"]["maven_compile"] = {
            "ok": compile_result.ok,
            "report": str(compile_path),
        }
        if not compile_result.ok:
            c.print(f"[red]Compile failed[/red] (exit {compile_result.exit_code})")

    analyzers_out: list[dict[str, Any]] = []
    if compile_result is None or compile_result.ok:
        c.print("[bold]Running optional analyzers…[/bold]")
        for runner in (
            run_spotbugs,
            run_semgrep,
            run_pmd,
            run_dependency_check,
            run_sonar_scanner,
        ):
            ar = runner(settings, repo, reports_dir)
            analyzers_out.append(
                {
                    "name": ar.name,
                    "ok": ar.ok,
                    "exit_code": ar.exit_code,
                }
            )
            tag = "green" if ar.ok else "red"
            c.print(f"  [{tag}]{ar.name}[/{tag}] exit={ar.exit_code}")
            if ar.stderr and not ar.ok:
                c.print(f"    [dim]{ar.stderr[:500]}[/dim]")
        summary["steps"]["analyzers"] = analyzers_out
    else:
        summary["steps"]["analyzers"] = {
            "skipped": True,
            "reason": "compile failed",
        }
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()

    write_json(reports_dir / "run-summary.json", summary)
    write_html_summary(reports_dir / "summary.html", settings, summary)

    if settings.ide.print_open_hints:
        _print_ide_hints(c, settings, repo)

    c.print(f"\n[bold green]Reports:[/bold green] {reports_dir}")
    return summary


def _print_ide_hints(c: Console, settings: Settings, repo: Path) -> None:
    c.print("\n[bold]IDE hints (SonarLint is in-IDE; open project for manual review)[/bold]")
    ij = settings.ide.intellij_path.strip()
    if ij and Path(ij).is_file():
        c.print(f"  IntelliJ: [cyan]{ij}[/cyan] [dim]{repo}[/dim]")
    ec = settings.ide.eclipse_path.strip()
    if ec and Path(ec).is_file():
        c.print(f"  Eclipse:    [cyan]{ec}[/cyan] -import [dim]{repo}[/dim]")
