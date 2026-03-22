"""Git clone, fetch Bitbucket PR refs, diff."""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

from pr_review.config.schema import Settings
from pr_review.scm.bitbucket_server import PullRequestMeta


def _inject_auth_into_git_url(clone_url: str, username: str, password: str) -> str:
    """Embed credentials for non-interactive fetch (password = token)."""
    p = urlparse(clone_url)
    if p.scheme not in ("http", "https"):
        return clone_url
    user_enc = quote(username, safe="")
    pass_enc = quote(password, safe="")
    netloc = f"{user_enc}:{pass_enc}@{p.hostname}"
    if p.port:
        netloc += f":{p.port}"
    return urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))


def run_git(
    settings: Settings,
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [settings.paths.git, *args]
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )


def ensure_clone(settings: Settings, authenticated_url: str) -> Path:
    ws = settings.workspace_dir()
    ws.parent.mkdir(parents=True, exist_ok=True)
    if (ws / ".git").is_dir():
        return ws
    ws.parent.mkdir(parents=True, exist_ok=True)
    cp = run_git(
        settings,
        ["clone", "--origin", "origin", authenticated_url, str(ws)],
        cwd=ws.parent,
        timeout=600,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"git clone failed: {cp.stderr or cp.stdout}")
    return ws


def fetch_pr_and_target(
    settings: Settings,
    meta: PullRequestMeta,
    authenticated_url: str,
) -> Path:
    repo = ensure_clone(settings, authenticated_url)
    # Point origin to authenticated URL for fetch
    run_git(settings, ["remote", "set-url", "origin", authenticated_url], cwd=repo)
    pr_id = settings.bitbucket.pull_request_id
    # Bitbucket Server refs
    fetch_from = f"refs/pull-requests/{pr_id}/from:refs/remotes/origin/pr-from"
    cp = run_git(settings, ["fetch", "origin", fetch_from], cwd=repo, timeout=600)
    if cp.returncode != 0:
        raise RuntimeError(f"git fetch PR ref failed: {cp.stderr or cp.stdout}")
    # Target branch tip (merge base calculation)
    if meta.to_branch:
        refspec = f"+refs/heads/{meta.to_branch}:refs/remotes/origin/pr-target"
        cp2 = run_git(settings, ["fetch", "origin", refspec], cwd=repo, timeout=600)
        if cp2.returncode != 0:
            # Fallback: shallow fetch all heads (may be slow on huge repos)
            run_git(
                settings,
                ["fetch", "origin", "+refs/heads/*:refs/remotes/origin/*"],
                cwd=repo,
                timeout=900,
            )
    if settings.repository.pr_ref_strategy == "merge":
        fetch_merge = f"refs/pull-requests/{pr_id}/merge:refs/remotes/origin/pr-merge"
        run_git(settings, ["fetch", "origin", fetch_merge], cwd=repo, timeout=600)
    # Checkout PR source tree at from_commit
    cp3 = run_git(settings, ["checkout", "--force", meta.from_commit], cwd=repo, timeout=120)
    if cp3.returncode != 0:
        raise RuntimeError(f"git checkout failed: {cp3.stderr or cp3.stdout}")
    return repo


def git_diff_range(settings: Settings, repo: Path, base: str, head: str) -> str:
    cp = run_git(settings, ["diff", f"{base}...{head}"], cwd=repo, timeout=300)
    if cp.returncode != 0:
        raise RuntimeError(f"git diff failed: {cp.stderr or cp.stdout}")
    return cp.stdout


def merge_base(settings: Settings, repo: Path, a: str, b: str) -> str:
    cp = run_git(settings, ["merge-base", a, b], cwd=repo, timeout=60)
    if cp.returncode != 0:
        raise RuntimeError(f"git merge-base failed: {cp.stderr or cp.stdout}")
    return cp.stdout.strip()
