"""Structured JSON logging. Never log tokens or webhook secrets."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


_SECRET_KEYS = frozenset(
    {"token", "password", "secret", "authorization", "webhook_secret", "bitbucket_token"}
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in (
            "pr_id",
            "market",
            "merge_sha",
            "event_id",
            "hotfix_branch",
            "status",
            "entry_count",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def extra(**kwargs: Any) -> dict[str, Any]:
    safe = {}
    for key, value in kwargs.items():
        if key.lower() in _SECRET_KEYS:
            continue
        safe[key] = value
    return {"extra": safe}
