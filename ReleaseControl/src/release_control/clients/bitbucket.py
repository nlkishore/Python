"""Bitbucket Server / Data Center REST. No git clone, no local repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote

from release_control.exceptions import BitbucketError, HttpError
from release_control.http import HttpPort, RestClient
from release_control.models import PrChange


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
        http: HttpPort | None = None,
    ) -> None:
        self._owns_http = http is None
        self._http = http or RestClient(
            f"{base_url.rstrip('/')}{api_prefix}",
            username=username,
            token=token,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> BitbucketServerClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _repo(self, project: str, slug: str, *parts: str) -> str:
        chunks = ["projects", project, "repos", slug, *parts]
        return "/".join(quote(p, safe="") for p in chunks)

    def get_pull_request(self, project: str, slug: str, pr_id: int) -> dict[str, Any]:
        path = self._repo(project, slug, "pull-requests", str(pr_id))
        try:
            return self._http.get_json(path)
        except HttpError as exc:
            raise BitbucketError(f"PR {pr_id} fetch failed: {exc.message}") from exc

    def iter_pr_changes(self, project: str, slug: str, pr_id: int) -> list[PrChange]:
        changes: list[PrChange] = []
        for item in self._paginate(
            self._repo(project, slug, "pull-requests", str(pr_id), "changes")
        ):
            path = (item.get("path") or {}).get("toString") or ""
            if path:
                changes.append(
                    PrChange(path=str(path), change_type=str(item.get("type") or "MODIFY"))
                )
        return changes

    def compare_changes(
        self, project: str, slug: str, *, from_ref: str, to_ref: str
    ) -> list[PrChange]:
        changes: list[PrChange] = []
        for item in self._paginate(
            self._repo(project, slug, "compare", "changes"),
            extra={"from": from_ref, "to": to_ref},
        ):
            path = (item.get("path") or {}).get("toString") or ""
            if path:
                changes.append(
                    PrChange(path=str(path), change_type=str(item.get("type") or "MODIFY"))
                )
        return changes

    def get_raw_file(
        self, project: str, slug: str, branch: str, path: str
    ) -> str | None:
        raw_path = self._repo(project, slug, "raw", *path.split("/"))
        try:
            return self._http.get_text(raw_path, params={"at": f"refs/heads/{branch}"})
        except HttpError as exc:
            if exc.status_code == 404:
                return None
            raise BitbucketError(f"Failed to read {path} from {branch}: {exc.message}") from exc

    def browse(
        self, project: str, slug: str, branch: str, path: str = ""
    ) -> list[dict[str, Any]]:
        parts = ("browse", *path.split("/")) if path else ("browse",)
        browse_path = self._repo(project, slug, *parts)
        children: list[dict[str, Any]] = []
        for item in self._paginate(browse_path, extra={"at": f"refs/heads/{branch}"}):
            children.append(item)
        return children

    def list_commits_for_path(
        self, project: str, slug: str, branch: str, path: str
    ) -> list[dict[str, Any]]:
        commits: list[dict[str, Any]] = []
        for item in self._paginate(
            self._repo(project, slug, "commits"),
            extra={"until": f"refs/heads/{branch}", "path": path},
        ):
            commits.append(item)
        return commits

    def download_raw(
        self,
        project: str,
        slug: str,
        branch: str,
        path: str,
        dest: Path,
    ) -> str:
        raw_path = self._repo(project, slug, "raw", *path.split("/"))
        try:
            return self._http.stream_to(
                raw_path, dest, params={"at": f"refs/heads/{branch}"}
            )
        except HttpError as exc:
            raise BitbucketError(
                f"Failed to download {path} from {branch}: {exc.message}"
            ) from exc

    def _paginate(
        self, path: str, extra: dict[str, Any] | None = None
    ) -> Iterator[dict[str, Any]]:
        start = 0
        limit = 100
        while True:
            params: dict[str, Any] = {"limit": limit, "start": start}
            if extra:
                params.update(extra)
            try:
                data = self._http.get_json(path, params=params)
            except HttpError as exc:
                raise BitbucketError(exc.message) from exc
            values = data.get("values") if isinstance(data, dict) else None
            if values is None and isinstance(data, dict) and "children" in data:
                values = (data.get("children") or {}).get("values") or []
                is_last = (data.get("children") or {}).get("isLastPage", True)
                next_start = (data.get("children") or {}).get("nextPageStart") or 0
            else:
                values = values or []
                is_last = data.get("isLastPage", True) if isinstance(data, dict) else True
                next_start = data.get("nextPageStart") or 0 if isinstance(data, dict) else 0
            for item in values:
                if isinstance(item, dict):
                    yield item
            if is_last:
                break
            start = int(next_start)
