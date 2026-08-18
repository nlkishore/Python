"""Persist baseline watermark and store metadata."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class HistoryState:
    account_open_date: str
    baseline_completed_at: str | None = None
    watermark_date: str | None = None
    trade_query_id: str = ""
    corporate_query_id: str = ""
    row_counts: dict[str, int] = field(default_factory=dict)
    last_mode: str = ""
    last_source_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryState:
        return cls(
            account_open_date=str(data.get("account_open_date") or ""),
            baseline_completed_at=data.get("baseline_completed_at"),
            watermark_date=data.get("watermark_date"),
            trade_query_id=str(data.get("trade_query_id") or ""),
            corporate_query_id=str(data.get("corporate_query_id") or ""),
            row_counts=dict(data.get("row_counts") or {}),
            last_mode=str(data.get("last_mode") or ""),
            last_source_label=str(data.get("last_source_label") or ""),
        )


def load_state(path: Path) -> HistoryState | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return HistoryState.from_dict(data)


def save_state(path: Path, state: HistoryState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def today_iso() -> str:
    return date.today().isoformat()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def from_yyyymmdd(s: str) -> date:
    return datetime.strptime(s, "%Y%m%d").date()
