"""Row selection for WhatsApp digest."""

from __future__ import annotations

from typing import Any

from completely_sold_alert.config import AppSettings


def _has_usable_prices(row: dict[str, Any]) -> bool:
    symbol = row.get("Symbol")
    if not symbol:
        return False
    current = row.get("Current_Market_Price")
    last_sold = row.get("Last_Sold_Price")
    try:
        if current is not None and float(current) > 0:
            return True
        if last_sold is not None and float(last_sold) > 0:
            return True
    except (TypeError, ValueError):
        return False
    return False


def should_alert(row: dict[str, Any], settings: AppSettings) -> bool:
    """Threshold mode only: notify when change <= price_drop_threshold_pct."""
    if settings.alert.notify_all_positions:
        return _has_usable_prices(row)

    threshold = settings.alert.price_drop_threshold_pct
    change = row.get("Change_Since_Last_Sold_Pct")
    last_sold = row.get("Last_Sold_Price")
    current = row.get("Current_Market_Price")
    if change is None or last_sold is None or current is None:
        return False
    try:
        if float(last_sold) <= 0 or float(current) <= 0:
            return False
        return float(change) <= float(threshold)
    except (TypeError, ValueError):
        return False


def evaluate_rows(
    rows: list[dict[str, Any]], settings: AppSettings
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in rows:
        if should_alert(row, settings):
            candidates.append(row)
        else:
            skipped.append(row)

    if settings.alert.notify_all_positions:
        candidates.sort(key=lambda r: str(r.get("Symbol") or ""))
    else:
        candidates.sort(
            key=lambda r: float(r.get("Change_Since_Last_Sold_Pct") or 0),
        )
    return candidates, skipped
