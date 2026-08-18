"""Per-symbol alert cooldown store."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _load(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def filter_cooldown(
    candidates: list[dict],
    cooldown_path: Path,
    cooldown_hours: float,
) -> tuple[list[dict], list[str]]:
    store = _load(cooldown_path)
    now = datetime.now(timezone.utc)
    allowed: list[dict] = []
    suppressed: list[str] = []

    for row in candidates:
        sym = str(row.get("Symbol") or "").upper()
        if not sym:
            continue
        last = store.get(sym)
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age_h = (now - last_dt).total_seconds() / 3600
                if age_h < cooldown_hours:
                    suppressed.append(sym)
                    continue
            except ValueError:
                pass
        allowed.append(row)

    return allowed, suppressed


def record_alerts(cooldown_path: Path, symbols: list[str]) -> None:
    store = _load(cooldown_path)
    now = datetime.now(timezone.utc).isoformat()
    for sym in symbols:
        store[sym.upper()] = now
    _save(cooldown_path, store)
