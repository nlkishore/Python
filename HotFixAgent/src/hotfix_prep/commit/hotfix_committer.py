"""Commit filesList.txt and buildScripts.sh together on the HotFix branch."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlsplit, urlunsplit

from hotfix_prep.exceptions import CommitError

logger = logging.getLogger(__name__)


class HotfixCommitter(Protocol):
    def commit_pair(
        self,
        *,
        clone_url: str,
        hotfix_branch: str,
        files_list_name: str,
        files_list_content: str,
        build_scripts_name: str,
        build_scripts_content: str,
        message: str,
    ) -> str: ...


@dataclass
class GitHotfixCommitter:
    username: str
    token: str
    timeout_seconds: int = 120

    def commit_pair(
        self,
        *,
        clone_url: str,
        hotfix_branch: str,
        files_list_name: str,
        files_list_content: str,
        build_scripts_name: str,
        build_scripts_content: str,
        message: str,
    ) -> str:
        authed = self._authed_url(clone_url)
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env.pop("GIT_ASKPASS", None)

        with tempfile.TemporaryDirectory(prefix="hotfix-prep-") as tmp:
            work = Path(tmp) / "repo"
            self._run(
                ["git", "clone", "--depth", "1", "--branch", hotfix_branch, authed, str(work)],
                env=env,
                cwd=tmp,
            )
            (work / files_list_name).write_text(files_list_content, encoding="utf-8", newline="\n")
            (work / build_scripts_name).write_text(
                build_scripts_content, encoding="utf-8", newline="\n"
            )
            self._run(["git", "add", "--", files_list_name, build_scripts_name], env=env, cwd=work)
            staged = self._run(
                ["git", "diff", "--cached", "--name-only"], env=env, cwd=work
            ).stdout.splitlines()
            expected = {files_list_name, build_scripts_name}
            if not expected.issubset(set(staged)):
                raise CommitError(
                    f"Paired commit requires both files staged; got {staged}"
                )
            self._run(
                ["git", "commit", "-m", message],
                env=env,
                cwd=work,
            )
            sha = self._run(["git", "rev-parse", "HEAD"], env=env, cwd=work).stdout.strip()
            self._run(["git", "push", "origin", f"HEAD:{hotfix_branch}"], env=env, cwd=work)
            logger.info(
                "Committed HotFix metadata",
                extra={"hotfix_branch": hotfix_branch, "merge_sha": sha},
            )
            return sha

    def _authed_url(self, clone_url: str) -> str:
        parts = urlsplit(clone_url)
        if not parts.scheme.startswith("http"):
            return clone_url
        user = quote(self.username, safe="")
        token = quote(self.token, safe="")
        netloc = f"{user}:{token}@{parts.hostname}"
        if parts.port:
            netloc += f":{parts.port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

    def _run(
        self,
        args: list[str],
        *,
        env: dict[str, str],
        cwd: str | Path,
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                args,
                cwd=str(cwd),
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            return result
        except subprocess.CalledProcessError as exc:
            stderr = _redact(exc.stderr or "", self.token, self.username)
            raise CommitError(f"git {' '.join(args[:4])} failed: {stderr}") from exc
        except FileNotFoundError as exc:
            raise CommitError("git is not installed on this host") from exc
        except subprocess.TimeoutExpired as exc:
            raise CommitError("git command timed out") from exc


def _redact(text: str, token: str, username: str) -> str:
    redacted = text
    if token:
        redacted = redacted.replace(token, "***")
        redacted = redacted.replace(quote(token, safe=""), "***")
    if username:
        redacted = redacted.replace(username, "***")
    return redacted
