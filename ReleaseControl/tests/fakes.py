from __future__ import annotations

from pathlib import Path
from typing import Any

from release_control.exceptions import HttpError


class FakeHttp:
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def _match(self, path: str) -> Any:
        if path in self.responses:
            return self.responses[path]
        for key, value in self.responses.items():
            if key in path:
                return value
        raise HttpError(f"no fake for {path}", status_code=404)

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append(("json", path, params))
        value = self._match(path)
        if isinstance(value, HttpError):
            raise value
        return value

    def get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        self.calls.append(("text", path, params))
        value = self._match(path)
        if isinstance(value, HttpError):
            raise value
        return value if isinstance(value, str) else str(value)

    def get_bytes(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        return self.get_text(path, params).encode("utf-8")

    def stream_to(
        self, path: str, dest: Path, params: dict[str, Any] | None = None
    ) -> str:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.get_bytes(path, params))
        return "abc123"

    def close(self) -> None:
        return None
