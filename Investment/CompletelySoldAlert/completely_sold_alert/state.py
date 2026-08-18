"""LangGraph state."""

from __future__ import annotations

from typing import Any, TypedDict


class AlertState(TypedDict, total=False):
    dry_run: bool
    force_market_day: bool
    fixture_path: str | None

    is_market_day: bool
    market_calendar: str
    skip_reason: str | None

    last_export_at: str | None
    data_age_hours: float
    is_stale: bool

    refresh_attempted: bool
    refresh_success: bool
    refresh_error: str | None
    report_path: str

    completely_sold_rows: list[dict[str, Any]]
    row_count: int

    alert_candidates: list[dict[str, Any]]
    skipped_rows: list[dict[str, Any]]
    cooldown_suppressed: list[str]

    digest_text: str | None
    digest_sent: bool
    errors: list[str]
    log_messages: list[str]
