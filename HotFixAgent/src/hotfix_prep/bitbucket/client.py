"""Bitbucket Server / Data Center REST client. Tokens are never logged."""

from __future__ import annotations

from typing import Any, Protocol
from urllib.parse import quote

import httpx

from hotfix_prep.exceptions import BitbucketError
from hotfix_prep.models import MergedPrEvent, PrChange


class BitbucketPort(Protocol):
    def iter_pr_changes(self, project: str, slug: str, pr_id: int) -> list[PrChange]: ...

    def get_file(
        self, project: str, slug: str, branch: str, path: str
    ) -> str | None: ...

    def add_pr_comment(self, project: str, slug: str, pr_id: int, text: str) -> None: ...

    def get_pull_request(self, project: str, slug: str, pr_id: int) -> MergedPrEvent: ...

    def clone_url(self, project: str, slug: str) -> str: ...


class BitbucketServerClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        token: str,
        *,
        api_prefix: str = "/rest/api/1.0",
        verify_ssl: bool = True,
        timeout: float = 60.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._api = f"{self._base}{api_prefix}"
        self._username = username
        self._token = token
        self._client = httpx.Client(
            auth=httpx.BasicAuth(username, token),
            verify=verify_ssl,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BitbucketServerClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _url(self, *parts: str) -> str:
        encoded = "/".join(quote(p, safe="") for p in parts)
        return f"{self._api}/{encoded}"

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise BitbucketError(f"Bitbucket GET failed: {exc}") from exc

    def iter_pr_changes(self, project: str, slug: str, pr_id: int) -> list[PrChange]:
        changes: list[PrChange] = []
        start = 0
        limit = 100
        while True:
            url = self._url(
                "projects", project, "repos", slug, "pull-requests", str(pr_id), "changes"
            )
            data = self._get(url, params={"limit": limit, "start": start})
            for item in data.get("values") or []:
                path = (item.get("path") or {}).get("toString") or ""
                if path:
                    changes.append(
                        PrChange(path=str(path), change_type=str(item.get("type") or "MODIFY"))
                    )
            if data.get("isLastPage", True):
                break
            start = int(data.get("nextPageStart") or 0)
        return changes

    def get_pull_request(self, project: str, slug: str, pr_id: int) -> MergedPrEvent:
        url = self._url("projects", project, "repos", slug, "pull-requests", str(pr_id))
        data = self._get(url)
        from_ref = data.get("fromRef") or {}
        to_ref = data.get("toRef") or {}
        props = data.get("properties") or {}
        merge = props.get("mergeCommit") or {}
        merge_sha = str(merge.get("id") or to_ref.get("latestCommit") or "")
        if not merge_sha:
            raise BitbucketError(f"PR {pr_id} has no merge commit SHA")
        author = ""
        author_block = data.get("author") or {}
        user = author_block.get("user") if isinstance(author_block, dict) else {}
        if isinstance(user, dict):
            author = str(user.get("name") or "")
        return MergedPrEvent(
            pr_id=int(data.get("id", pr_id)),
            title=str(data.get("title") or ""),
            from_branch=str(from_ref.get("displayId") or ""),
            to_branch=str(to_ref.get("displayId") or ""),
            merge_commit=merge_sha,
            project=project,
            slug=slug,
            author=author,
            raw=data,
        )

    def get_file(self, project: str, slug: str, branch: str, path: str) -> str | None:
        url = self._url("projects", project, "repos", slug, "raw", *path.split("/"))
        try:
            response = self._client.get(url, params={"at": f"refs/heads/{branch}"})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            raise BitbucketError(f"Failed to read {path} from {branch}: {exc}") from exc

    def add_pr_comment(self, project: str, slug: str, pr_id: int, text: str) -> None:
        url = self._url(
            "projects", project, "repos", slug, "pull-requests", str(pr_id), "comments"
        )
        try:
            response = self._client.post(url, json={"text": text})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BitbucketError(f"Failed to comment on PR {pr_id}: {exc}") from exc

    def clone_url(self, project: str, slug: str) -> str:
        return f"{self._base}/scm/{project}/{slug}.git"
