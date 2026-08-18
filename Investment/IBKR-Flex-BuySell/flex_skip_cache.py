"""Persist Flex windows that IBKR will not return (skip API retries on future runs)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SKIP_FILENAME = "flex_unavailable_windows.json"
MIN_FAIL_COUNT_FOR_SKIP = 1


def skip_cache_path(download_dir: Path) -> Path:
    return download_dir / DEFAULT_SKIP_FILENAME


def _window_key(from_yyyymmdd: str, to_yyyymmdd: str) -> str:
    return f"{from_yyyymmdd}_{to_yyyymmdd}"


def load_skip_cache(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "queries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "queries": {}}
    if "queries" not in data:
        data["queries"] = {}
    return data


def save_skip_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_skipped_window(
    path: Path,
    query_id: str,
    from_yyyymmdd: str,
    to_yyyymmdd: str,
) -> dict[str, Any] | None:
    data = load_skip_cache(path)
    q = data.get("queries", {}).get(str(query_id), {})
    entry = q.get(_window_key(from_yyyymmdd, to_yyyymmdd))
    if entry and entry.get("skip_flex_api"):
        return entry
    return None


def is_window_skipped(
    path: Path,
    query_id: str,
    from_yyyymmdd: str,
    to_yyyymmdd: str,
) -> bool:
    return get_skipped_window(path, query_id, from_yyyymmdd, to_yyyymmdd) is not None


def record_window_failure(
    path: Path,
    query_id: str,
    from_yyyymmdd: str,
    to_yyyymmdd: str,
    reason: str,
) -> None:
    data = load_skip_cache(path)
    qid = str(query_id)
    queries = data.setdefault("queries", {})
    q = queries.setdefault(qid, {})
    key = _window_key(from_yyyymmdd, to_yyyymmdd)
    prev = q.get(key, {})
    fail_count = int(prev.get("fail_count", 0)) + 1
    q[key] = {
        "from_date": from_yyyymmdd,
        "to_date": to_yyyymmdd,
        "reason": str(reason)[:500],
        "last_failed": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fail_count": fail_count,
        "skip_flex_api": fail_count >= MIN_FAIL_COUNT_FOR_SKIP,
    }
    save_skip_cache(path, data)


def clear_window_skip(
    path: Path,
    query_id: str,
    from_yyyymmdd: str,
    to_yyyymmdd: str,
) -> None:
    data = load_skip_cache(path)
    qid = str(query_id)
    q = data.get("queries", {}).get(qid, {})
    key = _window_key(from_yyyymmdd, to_yyyymmdd)
    if key in q:
        del q[key]
        save_skip_cache(path, data)


def seed_skip_window(
    path: Path,
    query_id: str,
    from_yyyymmdd: str,
    to_yyyymmdd: str,
    reason: str,
    *,
    fail_count: int = 4,
) -> None:
    """Manually mark a window unavailable (e.g. known IBKR gap for 2023)."""
    data = load_skip_cache(path)
    qid = str(query_id)
    queries = data.setdefault("queries", {})
    q = queries.setdefault(qid, {})
    key = _window_key(from_yyyymmdd, to_yyyymmdd)
    q[key] = {
        "from_date": from_yyyymmdd,
        "to_date": to_yyyymmdd,
        "reason": reason,
        "last_failed": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fail_count": fail_count,
        "skip_flex_api": True,
        "seeded": True,
    }
    save_skip_cache(path, data)


def list_skipped_windows(path: Path, query_id: str) -> list[dict[str, Any]]:
    data = load_skip_cache(path)
    q = data.get("queries", {}).get(str(query_id), {})
    rows = [v for v in q.values() if v.get("skip_flex_api")]
    return sorted(rows, key=lambda r: r.get("from_date", ""))


def print_skip_summary(path: Path, query_id: str) -> None:
    rows = list_skipped_windows(path, query_id)
    if not rows:
        print("No Flex windows marked unavailable in skip cache.", flush=True)
        return
    print(f"Flex skip cache ({path.name}):", flush=True)
    for r in rows:
        seeded = " [seeded]" if r.get("seeded") else ""
        print(
            f"  {r['from_date']}-{r['to_date']}: {r.get('reason', '')[:80]}{seeded}",
            flush=True,
        )
