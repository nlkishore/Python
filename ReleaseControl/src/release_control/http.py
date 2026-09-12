"""Single HTTP client for Bitbucket, Jenkins, and Artifactory. Tokens are never logged."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx

from release_control.exceptions import HttpError


class HttpPort(Protocol):
    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any: ...

    def get_text(self, path: str, params: dict[str, Any] | None = None) -> str: ...

    def get_bytes(self, path: str, params: dict[str, Any] | None = None) -> bytes: ...

    def stream_to(
        self, path: str, dest: Path, params: dict[str, Any] | None = None
    ) -> str: ...

    def close(self) -> None: ...


class RestClient:
    def __init__(
        self,
        base_url: str,
        *,
        username: str = "",
        token: str = "",
        header_auth: dict[str, str] | None = None,
        verify_ssl: bool = True,
        timeout: float = 60.0,
    ) -> None:
        self._base = base_url.rstrip("/") + "/"
        self._token = token
        if not token:
            auth = None
        else:
            # HTTP Basic password slot carries the PAT/API token, never a login password.
            auth = httpx.BasicAuth(username or "token", token)
        headers = {"Accept": "application/json"}
        if header_auth:
            headers.update(header_auth)
        self._client = httpx.Client(
            auth=auth,
            verify=verify_ssl,
            timeout=timeout,
            headers=headers,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> RestClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(self._base, path.lstrip("/"))

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = self._url(path)
        try:
            response = self._client.request(method, url, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise HttpError(
                f"{method} {self._redact(url)} failed: HTTP {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise HttpError(f"{method} {self._redact(url)} failed: {exc}") from exc

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params).json()

    def get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        return self._request("GET", path, params=params).text

    def get_bytes(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        return self._request("GET", path, params=params).content

    def stream_to(
        self, path: str, dest: Path, params: dict[str, Any] | None = None
    ) -> str:
        url = self._url(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        try:
            with self._client.stream("GET", url, params=params) as response:
                response.raise_for_status()
                with dest.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
                        digest.update(chunk)
        except httpx.HTTPStatusError as exc:
            raise HttpError(
                f"GET {self._redact(url)} failed: HTTP {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise HttpError(f"GET {self._redact(url)} failed: {exc}") from exc
        return digest.hexdigest()

    def _redact(self, url: str) -> str:
        if not self._token:
            return url
        return url.replace(self._token, "***")
