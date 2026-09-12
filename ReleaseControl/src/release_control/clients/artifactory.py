"""Artifactory list / latest numeric build / download."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from release_control.exceptions import ArtifactoryError, HttpError
from release_control.http import HttpPort, RestClient


_NUMERIC = re.compile(r"^(\d+)$")
_PATTERN_NUM = re.compile(r"(\d+)$")


class ArtifactoryClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        token: str,
        *,
        verify_ssl: bool = True,
        timeout: float = 60.0,
        http: HttpPort | None = None,
    ) -> None:
        self._owns_http = http is None
        self._base = base_url.rstrip("/")
        header = {"X-JFrog-Art-Api": token} if token else None
        # Token in header (or Basic username+token). Never a login password.
        self._http = http or RestClient(
            base_url,
            username=username,
            token=token,
            header_auth=header,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def storage_children(self, folder_path: str) -> list[dict[str, Any]]:
        api = f"api/storage/{folder_path.lstrip('/')}"
        try:
            data = self._http.get_json(api)
        except HttpError as exc:
            raise ArtifactoryError(f"Artifactory list failed: {exc.message}") from exc
        children = data.get("children") if isinstance(data, dict) else None
        return [c for c in (children or []) if isinstance(c, dict)]

    def latest_numeric_build(
        self, folder_path: str, *, pattern: str | None = None
    ) -> tuple[int, str]:
        children = self.storage_children(folder_path)
        numbers: list[tuple[int, str]] = []
        for child in children:
            uri = str(child.get("uri") or "").strip("/")
            if pattern:
                token = pattern.replace("{number}", r"(\d+)")
                match = re.fullmatch(token, uri)
                if match:
                    numbers.append((int(match.group(1)), uri))
                continue
            match = _NUMERIC.fullmatch(uri) or _PATTERN_NUM.search(uri)
            if match:
                numbers.append((int(match.group(1)), uri))
        if not numbers:
            raise ArtifactoryError(f"No numeric builds under {folder_path}")
        numbers.sort(key=lambda item: item[0])
        latest, name = numbers[-1]
        url = f"{self._base}/{folder_path.strip('/')}/{name}"
        return latest, url

    def download(self, uri: str, dest: Path) -> str:
        try:
            return self._http.stream_to(uri, dest)
        except HttpError as exc:
            raise ArtifactoryError(f"Download failed: {exc.message}") from exc
