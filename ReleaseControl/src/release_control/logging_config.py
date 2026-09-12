"""Structured JSON logging. Never log tokens."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


_SECRET_KEYS = frozenset(
    {
        "token",
        "password",
        "secret",
        "authorization",
        "bitbucket_token",
        "jenkins_token",
        "artifactory_token",
        "api_key",
    }
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("run_id", "pr_id", "job", "status", "market"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info and record.exc_info[0]:
            payload["exc_type"] = record.exc_info[0].__name__
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
    safe = {k: v for k, v in kwargs.items() if k.lower() not in _SECRET_KEYS}
    return {"extra": safe}
