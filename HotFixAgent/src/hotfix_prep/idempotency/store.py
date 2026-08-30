"""File-backed idempotency store keyed by repo + PR + merge SHA."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FileIdempotencyStore:
    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "processed.json"

    @staticmethod
    def key(project: str, slug: str, pr_id: int, merge_sha: str) -> str:
        return f"{project}/{slug}:{pr_id}:{merge_sha}"

    def get(self, key: str) -> dict[str, Any] | None:
        data = self._load()
        record = data.get("keys", {}).get(key)
        return record if isinstance(record, dict) else None

    def already_succeeded(self, key: str) -> bool:
        record = self.get(key)
        return bool(record and record.get("status") == "success")

    def record_success(self, key: str, *, hotfix_commit: str, market_id: str) -> None:
        self._upsert(
            key,
            {
                "status": "success",
                "hotfix_commit": hotfix_commit,
                "market_id": market_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def record_failure(self, key: str, *, error_code: str, message: str) -> None:
        self._upsert(
            key,
            {
                "status": "failed",
                "error_code": error_code,
                "message": message,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _load(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {"keys": {}}
        with self._path.open(encoding="utf-8") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError:
                return {"keys": {}}
        if not isinstance(data, dict) or "keys" not in data:
            return {"keys": {}}
        return data

    def _upsert(self, key: str, record: dict[str, Any]) -> None:
        data = self._load()
        data.setdefault("keys", {})[key] = record
        fd, tmp_name = tempfile.mkstemp(dir=str(self._dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.replace(tmp_name, self._path)
        except Exception:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise
