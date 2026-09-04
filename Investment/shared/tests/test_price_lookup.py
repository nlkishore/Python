"""Unit tests for WhatsApp PRICE lookup (avg sold + reply text)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.price_lookup import (  # noqa: E402
    SellStats,
    aggregate_sell_rows,
    clear_sell_averages_cache,
    format_price_reply,
    load_sell_averages,
    parse_price_command,
)


def test_parse_price_command():
    assert parse_price_command("PRICE NVDA") == "NVDA"
    assert parse_price_command("Q AAPL") == "AAPL"
    assert parse_price_command("PRICE") == ""
    assert parse_price_command("Q") == ""
    assert parse_price_command("PRICE  msft extra") == "MSFT"
    assert parse_price_command("STATUS") is None
    assert parse_price_command("QUESTION") is None


def test_aggregate_weighted_avg_and_last_sold():
    rows = [
        {
            "symbol": "NVDA",
            "quantity": 10,
            "net": 1000,
            "date": "2023-01-15",
        },
        {
            "symbol": "NVDA",
            "quantity": 30,
            "net": 4500,
            "date": "2024-06-01",
        },
        {
            "symbol": "AAPL",
            "quantity": 5,
            "price": 150,
            "date": date(2022, 3, 1),
        },
    ]
    out = aggregate_sell_rows(rows)
    assert out["NVDA"].sell_qty == 40
    assert out["NVDA"].avg_sell == pytest.approx(137.5, abs=0.001)
    assert out["NVDA"].last_sold == date(2024, 6, 1)
    assert out["AAPL"].avg_sell == pytest.approx(150.0, abs=0.001)


def test_aggregate_skips_buys():
    rows = [
        {"symbol": "X", "quantity": 2, "net": 20, "side": "BUY"},
        {"symbol": "X", "quantity": 3, "net": 30, "side": "SELL"},
    ]
    out = aggregate_sell_rows(rows)
    assert set(out) == {"X"}
    assert out["X"].sell_qty == 3
    assert out["X"].avg_sell == pytest.approx(10.0, abs=0.001)


def test_format_price_reply_full():
    stats = SellStats(
        avg_sell=100.0,
        sell_qty=12.5,
        proceeds=1250.0,
        last_sold=date(2024, 10, 18),
    )
    text = format_price_reply("nvda", stats, 110.0, "Yahoo last 2026-09-02 15:32")
    assert "*NVDA*" in text
    assert "Avg Sold:" in text
    assert "$100.00" in text
    assert "12.5 sh" in text
    assert "$110.00" in text
    assert "+10.0%" in text
    assert "2024-10-18" in text


def test_format_price_reply_missing_parts():
    none_sells = format_price_reply("FOO", None, 12.0, "Yahoo last")
    assert "no sells" in none_sells.lower()
    assert "$12.00" in none_sells

    none_mkt = format_price_reply(
        "SKLZ",
        SellStats(avg_sell=8.0, sell_qty=1.0, proceeds=8.0, last_sold=None),
        None,
        None,
    )
    assert "no Yahoo quote" in none_mkt
    assert "vs Avg Sold" not in none_mkt


def test_load_sell_averages_from_xlsx(tmp_path: Path):
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "buysell.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sells"
    ws.append(["Date", "Symbol", "Quantity", "Price", "Net Amount"])
    ws.append(["2024-01-02", "TEST", 4, 10.0, 40.0])
    ws.append(["2024-03-01", "TEST", 6, 20.0, 120.0])
    wb.save(path)
    wb.close()

    clear_sell_averages_cache()
    data = load_sell_averages(path, force=True)
    assert "TEST" in data
    assert data["TEST"].sell_qty == 10
    assert data["TEST"].avg_sell == pytest.approx(16.0, abs=0.001)
    assert data["TEST"].last_sold == date(2024, 3, 1)
    clear_sell_averages_cache()
