from __future__ import annotations

from pathlib import Path

import pytest

from hotfix_prep.config import load_app_config
from hotfix_prep.models import MergedPrEvent, PrChange
from hotfix_prep.wiring import package_root


class FakeBitbucket:
    def __init__(self) -> None:
        self.changes: list[PrChange] = []
        self.files: dict[str, str] = {}
        self.comments: list[str] = []
        self.clone_calls: list[tuple[str, str]] = []

    def iter_pr_changes(self, project: str, slug: str, pr_id: int) -> list[PrChange]:
        return list(self.changes)

    def get_file(self, project: str, slug: str, branch: str, path: str) -> str | None:
        return self.files.get(path)

    def add_pr_comment(self, project: str, slug: str, pr_id: int, text: str) -> None:
        self.comments.append(text)

    def get_pull_request(self, project: str, slug: str, pr_id: int) -> MergedPrEvent:
        raise NotImplementedError

    def clone_url(self, project: str, slug: str) -> str:
        self.clone_calls.append((project, slug))
        return f"https://bitbucket.example.com/scm/{project}/{slug}.git"


class FakeCommitter:
    def __init__(self, sha: str = "abc123def456") -> None:
        self.sha = sha
        self.calls: list[dict] = []

    def commit_pair(self, **kwargs: str) -> str:
        self.calls.append(kwargs)
        return self.sha


@pytest.fixture
def repo_root() -> Path:
    return package_root()


@pytest.fixture
def app_config(repo_root: Path):
    return load_app_config(base_dir=repo_root)


@pytest.fixture
def merged_event() -> MergedPrEvent:
    return MergedPrEvent(
        pr_id=1842,
        title="CR-1234: fix login",
        from_branch="feature/CR-1234-fix-login",
        to_branch="release/sg",
        merge_commit="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        project="BANK",
        slug="core-app",
        author="dev1",
    )
