"""Unit tests for trade_history Symbol_PnL, corporate parse, baseline/refresh offline."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trade_history.corporate_parse import load_corporate_from_activity_file
from trade_history.orchestrator import HistoryError, load_history_config, run_baseline, run_refresh
from trade_history.state import load_state
from trade_history.store import load_corporate, load_trades, merge_trades
from trade_history.symbol_pnl import (
    build_by_symbol_trades,
    build_symbol_pnl,
    completely_sold_from_symbol_pnl,
)


def test_symbol_pnl_closed_and_dividends():
    trades = pd.DataFrame(
        [
            {
                "Date": "2024-01-01",
                "Symbol": "AAA",
                "Transaction Type": "Buy",
                "Quantity": 10,
                "Price": 10.0,
                "Commission": 0.0,
                "Net Amount": 100.0,
                "Gross Amount": 100.0,
                "Account": "",
                "Description": "AAA",
            },
            {
                "Date": "2024-06-01",
                "Symbol": "AAA",
                "Transaction Type": "Sell",
                "Quantity": 10,
                "Price": 12.0,
                "Commission": 0.0,
                "Net Amount": 120.0,
                "Gross Amount": 120.0,
                "Account": "",
                "Description": "AAA",
            },
        ]
    )
    corp = pd.DataFrame(
        [
            {
                "Date": "2024-03-01",
                "Symbol": "AAA",
                "ActionType": "DIVIDEND",
                "Quantity": None,
                "Amount": 5.0,
                "Description": "Ordinary Dividend",
                "Account": "",
                "Source": "test",
                "SourceFile": "t.csv",
            }
        ]
    )
    pnl = build_symbol_pnl(trades, corp, fetch_marks=False)
    assert len(pnl) == 1
    row = pnl.iloc[0]
    assert row["Symbol"] == "AAA"
    assert row["Open_Qty"] == 0
    assert row["Realized_PnL"] == 20.0
    assert row["Dividends"] == 5.0
    assert row["Total_PnL"] == 25.0

    by_sym = build_by_symbol_trades(trades)
    assert set(by_sym["Side"]) == {"Buy", "Sell"}


def test_symbol_pnl_cash_merger_realizes_loss_or_gain():
    """Acquired ticker (e.g. ATVI) must clear Open_Qty and realize cash buyout P&L."""
    trades = pd.DataFrame(
        [
            {
                "Date": "2021-03-09",
                "Symbol": "ATVI",
                "Transaction Type": "Buy",
                "Quantity": 20,
                "Price": 80.0,
                "Commission": 0.0,
                "Net Amount": -1600.0,
                "Gross Amount": -1600.0,
                "Account": "",
                "Description": "ATVI",
            }
        ]
    )
    corp = pd.DataFrame(
        [
            {
                "Date": "2023-10-13",
                "Symbol": "ATVI",
                "ActionType": "MERGER",
                "Quantity": -20,
                "Amount": 1900.0,
                "Description": "ATVI Merged(Acquisition) for USD 95.00 per Share (ATVI, ACTIVISION)",
                "Account": "",
                "Source": "test",
                "SourceFile": "t.csv",
            }
        ]
    )
    pnl = build_symbol_pnl(trades, corp, fetch_marks=False)
    row = pnl.iloc[0]
    assert row["Open_Qty"] == 0
    assert row["Sell_Proceeds"] == 1900.0
    assert row["Realized_PnL"] == 300.0  # 1900 - 1600


def test_symbol_pnl_split_fixes_open_qty():
    """Forward split share delta must adjust Open_Qty (AMZN-style)."""
    trades = pd.DataFrame(
        [
            {
                "Date": "2022-01-01",
                "Symbol": "AMZN",
                "Transaction Type": "Buy",
                "Quantity": 6,
                "Price": 100.0,
                "Commission": 0.0,
                "Net Amount": -600.0,
                "Gross Amount": -600.0,
                "Account": "",
                "Description": "AMZN",
            },
            {
                "Date": "2023-01-01",
                "Symbol": "AMZN",
                "Transaction Type": "Sell",
                "Quantity": 20,
                "Price": 10.0,
                "Commission": 0.0,
                "Net Amount": 200.0,
                "Gross Amount": 200.0,
                "Account": "",
                "Description": "AMZN",
            },
        ]
    )
    corp = pd.DataFrame(
        [
            {
                "Date": "2022-06-06",
                "Symbol": "AMZN",
                "ActionType": "SPLIT",
                "Quantity": 114,  # 6 → 120 via 20:1
                "Amount": 0.0,
                "Description": "AMZN Split 20 for 1",
                "Account": "",
                "Source": "test",
                "SourceFile": "t.csv",
            }
        ]
    )
    pnl = build_symbol_pnl(trades, corp, fetch_marks=False)
    row = pnl.iloc[0]
    assert row["Open_Qty"] == 100  # 6+114-20
    assert abs(float(row["Realized_PnL"]) - (200 - 100)) < 0.02  # sold 20 of 120 @ avg $5


def test_symbol_pnl_reverse_split_does_not_wipe_cost():
    """SKLZ-style 1-for-20: IBKR posts -275 then +13.75. Cost must survive the overshoot."""
    trades = pd.DataFrame(
        [
            {
                "Date": "2021-01-01",
                "Symbol": "SKLZ",
                "Transaction Type": "Buy",
                "Quantity": 275,
                "Price": 8.0,
                "Commission": 0.0,
                "Net Amount": -2200.0,
                "Gross Amount": -2200.0,
                "Account": "",
                "Description": "SKLZ",
            },
            {
                "Date": "2023-06-23",
                "Symbol": "SKLZ",
                "Transaction Type": "Sell",
                "Quantity": 0.75,
                "Price": 9.42,
                "Commission": 0.0,
                "Net Amount": 7.065,
                "Gross Amount": 7.065,
                "Account": "",
                "Description": "SKLZ",
            },
            {
                "Date": "2024-10-18",
                "Symbol": "SKLZ",
                "Transaction Type": "Sell",
                "Quantity": 26,
                "Price": 5.48,
                "Commission": 0.0,
                "Net Amount": 142.48,
                "Gross Amount": 142.48,
                "Account": "",
                "Description": "SKLZ",
            },
            {
                "Date": "2025-08-12",
                "Symbol": "SKLZ",
                "Transaction Type": "Buy",
                "Quantity": 13,
                "Price": 8.0,
                "Commission": 0.0,
                "Net Amount": -104.0,
                "Gross Amount": -104.0,
                "Account": "",
                "Description": "SKLZ",
            },
        ]
    )
    corp = pd.DataFrame(
        [
            {
                "Date": "2023-06-26",
                "Symbol": "SKLZ",
                "ActionType": "SPLIT",
                "Quantity": -275,
                "Amount": 0.0,
                "Description": "SKLZ(US83067L1098) Split 1 for 20",
                "Account": "",
                "Source": "test",
                "SourceFile": "t.csv",
            },
            {
                "Date": "2023-06-26",
                "Symbol": "SKLZ",
                "ActionType": "SPLIT",
                "Quantity": 13.75,
                "Amount": 0.0,
                "Description": "SKLZ(US83067L2088) Split 1 for 20",
                "Account": "",
                "Source": "test",
                "SourceFile": "t.csv",
            },
        ]
    )
    pnl = build_symbol_pnl(trades, corp, fetch_marks=False)
    row = pnl.iloc[0]
    # Remaining after 0.75 sell: 274.25 → ~13.71 post-split; sell 26 oversells.
    # Realized must be a large loss (proceeds << original cost), not a small profit.
    assert float(row["Realized_PnL"]) < -1000
    closed = completely_sold_from_symbol_pnl(pnl, trades)
    if not closed.empty:
        assert float(closed.iloc[0]["Profit"]) < 0


def test_merge_trades_dedupes():
    a = pd.DataFrame(
        [
            {
                "Date": "2024-01-01",
                "Symbol": "BBB",
                "Transaction Type": "Buy",
                "Quantity": 1,
                "Price": 5.0,
                "Net Amount": 5.0,
                "Gross Amount": 5.0,
                "Commission": 0,
                "Account": "",
                "Description": "BBB",
            }
        ]
    )
    b = a.copy()
    merged = merge_trades(a, b)
    assert len(merged) == 1


def test_merge_trades_dedupes_fx_copies():
    """Same fill in trade currency vs base currency must collapse to one row."""
    usd = pd.DataFrame(
        [
            {
                "Date": "2021-12-21",
                "Symbol": "NIO",
                "Transaction Type": "Buy",
                "Quantity": 5,
                "Price": 30.115,
                "Net Amount": 149.575,
                "Gross Amount": 150.575,
                "Commission": -1.0,
                "Account": "",
                "Description": "NIO",
            }
        ]
    )
    sgd = pd.DataFrame(
        [
            {
                "Date": "2021-12-21",
                "Symbol": "NIO",
                "Transaction Type": "Buy",
                "Quantity": 5,
                "Price": 30.115,
                "Net Amount": -206.778615,
                "Gross Amount": -205.414415,
                "Commission": -1.3642,
                "Account": "U***1357",
                "Description": "NIO INC - ADR",
            }
        ]
    )
    merged = merge_trades(usd, sgd)
    assert len(merged) == 1
    # Prefer trade-currency gross ≈ qty×price
    assert abs(float(merged.iloc[0]["Gross Amount"]) - 150.575) < 0.01


def test_corporate_from_dividend_csv():
    path = Path(r"C:\Investment\IBKR-Transaction\U3831357.DIVIDEND.20200218.20251225.csv")
    if not path.is_file():
        pytest.skip("dividend CSV not present")
    corp = load_corporate_from_activity_file(path)
    assert not corp.empty
    assert (corp["ActionType"] == "DIVIDEND").all()
    assert corp["Symbol"].notna().all()


def test_baseline_refresh_offline(tmp_path: Path):
    # Use real Flex cache + Activity via config pointing store/state into tmp
    cfg_path = ROOT / "config.ini"
    if not cfg_path.is_file():
        pytest.skip("config.ini missing")

    cfg = load_history_config(cfg_path)
    cfg["store_dir"] = tmp_path / "store"
    cfg["state_path"] = tmp_path / "state.json"
    cfg["history_report_path"] = tmp_path / "out.xlsx"
    cfg["fetch_market_prices"] = False

    out = run_baseline(cfg, offline=True, fetch_market_prices=False)
    assert out.is_file()
    state = load_state(cfg["state_path"])
    assert state is not None
    assert state.watermark_date
    trades = load_trades(cfg["store_dir"])
    corp = load_corporate(cfg["store_dir"])
    assert len(trades) > 0
    # Dividends expected from sibling DIVIDEND export
    assert len(corp) > 0

    with pytest.raises(HistoryError):
        run_baseline(cfg, offline=True, fetch_market_prices=False)

    n_before = len(trades)
    run_refresh(cfg, offline=True, fetch_market_prices=False)
    trades2 = load_trades(cfg["store_dir"])
    assert len(trades2) >= n_before


def test_symbol_pnl_closed_keeps_last_sold_price():
    trades = pd.DataFrame(
        [
            {
                "Date": "2024-01-01",
                "Symbol": "BBB",
                "Transaction Type": "Buy",
                "Quantity": 10,
                "Price": 10.0,
                "Commission": 0.0,
                "Net Amount": -100.0,
                "Gross Amount": -100.0,
                "Account": "",
                "Description": "BBB",
            },
            {
                "Date": "2024-06-01",
                "Symbol": "BBB",
                "Transaction Type": "Sell",
                "Quantity": 10,
                "Price": 15.0,
                "Commission": 0.0,
                "Net Amount": 150.0,
                "Gross Amount": 150.0,
                "Account": "",
                "Description": "BBB",
            },
        ]
    )
    pnl = build_symbol_pnl(trades, fetch_marks=False)
    closed = completely_sold_from_symbol_pnl(pnl, trades)
    assert len(closed) == 1
    assert closed.iloc[0]["Last_Sold_Price"] == 15.0


def test_symbol_pnl_closed_uses_weighted_average_sell_price():
    trades = pd.DataFrame(
        [
            {
                "Date": "2024-01-01",
                "Symbol": "CCC",
                "Transaction Type": "Buy",
                "Quantity": 10,
                "Price": 10.0,
                "Commission": 0.0,
                "Net Amount": -100.0,
                "Gross Amount": -100.0,
                "Account": "",
                "Description": "CCC",
            },
            {
                "Date": "2024-03-01",
                "Symbol": "CCC",
                "Transaction Type": "Sell",
                "Quantity": 4,
                "Price": 12.0,
                "Commission": 0.0,
                "Net Amount": 48.0,
                "Gross Amount": 48.0,
                "Account": "",
                "Description": "CCC",
            },
            {
                "Date": "2024-05-01",
                "Symbol": "CCC",
                "Transaction Type": "Sell",
                "Quantity": 6,
                "Price": 18.0,
                "Commission": 0.0,
                "Net Amount": 108.0,
                "Gross Amount": 108.0,
                "Account": "",
                "Description": "CCC",
            },
        ]
    )
    pnl = build_symbol_pnl(trades, fetch_marks=False)
    closed = completely_sold_from_symbol_pnl(pnl, trades)
    assert len(closed) == 1
    assert closed.iloc[0]["Last_Sold_Price"] == 15.6
