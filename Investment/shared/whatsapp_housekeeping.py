"""Select WhatsApp history rows older than a cutoff (no Green API calls)."""

from __future__ import annotations

from typing import Iterable, Mapping


def message_timestamp(item: Mapping[str, object]) -> float:
    raw = item.get("timestamp")
    try:
        ts = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    # Milliseconds if clearly larger than year-2286 in seconds.
    if ts >= 1e12:
        ts = ts / 1000.0
    return ts


def old_message_ids(
    items: Iterable[Mapping[str, object]],
    *,
    cutoff_ts: float,
) -> list[str]:
    """Return idMessage values with timestamp strictly older than cutoff_ts (unix seconds)."""
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        msg_id = str(item.get("idMessage") or item.get("id") or "").strip()
        if not msg_id or msg_id in seen:
            continue
        ts = message_timestamp(item)
        if ts <= 0 or ts >= cutoff_ts:
            continue
        seen.add(msg_id)
        out.append(msg_id)
    return out
