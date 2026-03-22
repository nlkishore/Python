"""Bitbucket Server / Data Center REST API client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from pr_review.config.schema import Settings


@dataclass
class PullRequestMeta:
    pr_id: int
    title: str
    from_branch: str
    to_branch: str
    from_commit: str
    to_commit: str
    raw: dict[str, Any]


class BitbucketServerClient:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        bb = settings.bitbucket
        base = bb.server_url.rstrip("/")
        self._base = f"{base}{bb.api_path_prefix}"
        self._verify = bb.verify_ssl
        auth = httpx.BasicAuth(bb.username, bb.token)
        self._client = httpx.Client(auth=auth, verify=self._verify, timeout=120.0)

    def close(self) -> None:
        self._client.close()

    def _url(self, *parts: str) -> str:
        path = "/".join(parts)
        return f"{self._base}/{path}"

    def get_pull_request(self) -> PullRequestMeta:
        bb = self._s.bitbucket
        url = self._url(
            "projects",
            quote(bb.project_key, safe=""),
            "repos",
            quote(bb.repository_slug, safe=""),
            "pull-requests",
            str(bb.pull_request_id),
        )
        r = self._client.get(url)
        r.raise_for_status()
        data = r.json()
        from_ref = data.get("fromRef") or {}
        to_ref = data.get("toRef") or {}
        return PullRequestMeta(
            pr_id=data.get("id", bb.pull_request_id),
            title=data.get("title", ""),
            from_branch=str(from_ref.get("displayId") or ""),
            to_branch=str(to_ref.get("displayId") or ""),
            from_commit=str(from_ref.get("latestCommit") or ""),
            to_commit=str(to_ref.get("latestCommit") or ""),
            raw=data,
        )

    def iter_change_paths(self) -> list[str]:
        """List file paths touched in PR (paginated)."""
        bb = self._s.bitbucket
        paths: list[str] = []
        start = 0
        limit = 100
        while True:
            url = self._url(
                "projects",
                quote(bb.project_key, safe=""),
                "repos",
                quote(bb.repository_slug, safe=""),
                "pull-requests",
                str(bb.pull_request_id),
                "changes",
            )
            r = self._client.get(url, params={"limit": limit, "start": start})
            r.raise_for_status()
            data = r.json()
            for ch in data.get("values") or []:
                p = (ch.get("path") or {}).get("toString")
                if p:
                    paths.append(str(p))
            if data.get("isLastPage", True):
                break
            start = int(data.get("nextPageStart") or 0)
        return paths
