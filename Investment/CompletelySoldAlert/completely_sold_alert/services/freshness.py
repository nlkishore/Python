"""Export freshness tracking."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def last_export_path(data_dir: Path) -> Path:
    return data_dir / "last_export.json"


def read_last_export(data_dir: Path) -> dict | None:
    path = last_export_path(data_dir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_last_export(
    data_dir: Path,
    report_path: Path,
    completely_sold_count: int,
    *,
    success: bool = True,
    source: str = "flex_buysell_report",
) -> None:
    payload = {
        "report_path": str(report_path),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "completely_sold_count": completely_sold_count,
        "source": source,
        "success": success,
    }
    path = last_export_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def data_age_hours(exported_at: str | None) -> float:
    if not exported_at:
        return float("inf")
    try:
        dt = datetime.fromisoformat(exported_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except ValueError:
        return float("inf")


def is_stale(data_dir: Path, max_age_hours: float, report_path: Path) -> tuple[bool, float, str | None]:
    meta = read_last_export(data_dir)
    exported_at = meta.get("exported_at") if meta else None
    age = data_age_hours(exported_at)

    if not report_path.is_file():
        return True, age, exported_at

    if meta is None:
        mtime = datetime.fromtimestamp(report_path.stat().st_mtime, tz=timezone.utc)
        exported_at = mtime.isoformat()
        age = data_age_hours(exported_at)

    return age > max_age_hours, age, exported_at
