"""Unit tests for row selection."""

from completely_sold_alert.config import AppSettings, AlertSettings
from completely_sold_alert.services.evaluate import evaluate_rows, should_alert


def test_threshold_mode_at_threshold():
    settings = AppSettings(
        alert=AlertSettings(notify_all_positions=False, price_drop_threshold_pct=-5.0)
    )
    row = {
        "Symbol": "AAPL",
        "Last_Sold_Price": 200.0,
        "Current_Market_Price": 190.0,
        "Change_Since_Last_Sold_Pct": -5.0,
    }
    assert should_alert(row, settings) is True


def test_threshold_mode_above_threshold():
    settings = AppSettings(
        alert=AlertSettings(notify_all_positions=False, price_drop_threshold_pct=-5.0)
    )
    row = {
        "Symbol": "MSFT",
        "Last_Sold_Price": 400.0,
        "Current_Market_Price": 395.0,
        "Change_Since_Last_Sold_Pct": -1.25,
    }
    assert should_alert(row, settings) is False


def test_all_positions_includes_any_with_prices():
    settings = AppSettings(alert=AlertSettings(notify_all_positions=True))
    rows = [
        {
            "Symbol": "MSFT",
            "Last_Sold_Price": 420.0,
            "Current_Market_Price": 410.0,
            "Change_Since_Last_Sold_Pct": -2.38,
        },
        {
            "Symbol": "AAPL",
            "Last_Sold_Price": 200.0,
            "Current_Market_Price": 188.0,
            "Change_Since_Last_Sold_Pct": -6.0,
        },
    ]
    candidates, skipped = evaluate_rows(rows, settings)
    assert len(candidates) == 2
    assert len(skipped) == 0


def test_evaluate_fixture_sample_all_positions():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    rows = json.loads((root / "fixtures" / "completely_sold_sample.json").read_text())
    settings = AppSettings(alert=AlertSettings(notify_all_positions=True))
    candidates, _ = evaluate_rows(rows, settings)
    assert len(candidates) == 3
