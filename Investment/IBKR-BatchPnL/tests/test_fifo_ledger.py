"""Unit tests for FIFO batch matching."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FLEX = ROOT.parent / "IBKR-Flex-BuySell"
for p in (ROOT, FLEX):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fifo_ledger import run_fifo_ledger


def _trade(date: str, symbol: str, side: str, qty: float, price: float) -> dict:
    cash = qty * price
    net = -cash if side == "Buy" else cash
    return {
        "Date": date,
        "Symbol": symbol,
        "Transaction Type": side,
        "Quantity": qty,
        "Price": price,
        "Commission": 0.0,
        "Net Amount": net,
        "Gross Amount": net,
        "Account": "",
        "Description": symbol,
    }


def test_closed_position_averages_and_one_batch():
    trades = pd.DataFrame(
        [
            _trade("2024-01-01", "AAA", "Buy", 10, 10.0),
            _trade("2024-06-01", "AAA", "Sell", 10, 12.0),
        ]
    )
    summary, batches = run_fifo_ledger(trades, marks={})
    row = summary.iloc[0]
    assert row["Symbol"] == "AAA"
    assert row["Buy_Qty"] == 10
    assert row["Avg_Buy_Price"] == 10.0
    assert row["Sell_Qty"] == 10
    assert row["Avg_Sell_Price"] == 12.0
    assert row["Open_Qty"] == 0
    assert row["Realized_PnL"] == 20.0
    assert row["Result"] == "PROFIT"
    matched = batches.loc[batches["Status"] == "MATCHED"]
    assert len(matched) == 1
    m = matched.iloc[0]
    assert m["Buy_Qty"] == 10
    assert m["Buy_Price"] == 10.0
    assert str(m["Buy_Date"]) == "2024-01-01"
    assert m["Sell_Qty"] == 10
    assert m["Sell_Price"] == 12.0
    assert str(m["Sell_Date"]) == "2024-06-01"
    assert m["Batch_PnL"] == 20.0
    assert m["Batch_PnL_Pct"] == 20.0


def test_fifo_two_buys_partial_sell():
    """First buy lot is closed first; leftover second lot stays OPEN."""
    trades = pd.DataFrame(
        [
            _trade("2024-01-01", "BBB", "Buy", 5, 10.0),
            _trade("2024-02-01", "BBB", "Buy", 5, 20.0),
            _trade("2024-03-01", "BBB", "Sell", 6, 15.0),
        ]
    )
    summary, batches = run_fifo_ledger(trades, marks={})
    row = summary.iloc[0]
    assert row["Buy_Qty"] == 10
    assert row["Avg_Buy_Price"] == 15.0
    assert row["Sell_Qty"] == 6
    assert row["Avg_Sell_Price"] == 15.0
    assert row["Open_Qty"] == 4
    # FIFO: sell 5 of $10 lot (+25) + 1 of $20 lot (-5) = +20
    assert row["Realized_PnL"] == 20.0
    matched = batches.loc[batches["Status"] == "MATCHED"].reset_index(drop=True)
    assert len(matched) == 2
    assert matched.iloc[0]["Buy_Price"] == 10.0
    assert matched.iloc[0]["Matched_Qty"] == 5
    assert matched.iloc[0]["Batch_PnL"] == 25.0
    assert matched.iloc[1]["Buy_Price"] == 20.0
    assert matched.iloc[1]["Matched_Qty"] == 1
    assert matched.iloc[1]["Batch_PnL"] == -5.0
    open_lots = batches.loc[batches["Status"] == "OPEN"]
    assert len(open_lots) == 1
    assert open_lots.iloc[0]["Buy_Qty"] == 4
    assert open_lots.iloc[0]["Buy_Price"] == 20.0
    assert pd.isna(open_lots.iloc[0]["Sell_Date"])


def test_open_lot_unrealized_uses_mark():
    trades = pd.DataFrame([_trade("2024-01-01", "CCC", "Buy", 10, 10.0)])
    summary, batches = run_fifo_ledger(trades, marks={"CCC": (12.0, None)})
    row = summary.iloc[0]
    assert row["Result"] == "OPEN"
    assert row["Realized_PnL"] == 0.0
    assert row["Unrealized_PnL"] == 20.0
    assert row["Mark_Price"] == 12.0
    open_lot = batches.loc[batches["Status"] == "OPEN"].iloc[0]
    assert open_lot["Batch_PnL"] == 20.0
    assert open_lot["Sell_Price"] == 12.0


def test_split_scales_remaining_lot_then_sell():
    trades = pd.DataFrame(
        [
            _trade("2022-01-01", "AMZN", "Buy", 6, 100.0),
            _trade("2023-01-01", "AMZN", "Sell", 20, 10.0),
        ]
    )
    corp = pd.DataFrame(
        [
            {
                "Date": "2022-06-06",
                "Symbol": "AMZN",
                "ActionType": "SPLIT",
                "Quantity": 114,
                "Amount": 0.0,
                "Description": "AMZN Split 20 for 1",
                "Account": "",
                "Source": "test",
                "SourceFile": "t.csv",
            }
        ]
    )
    summary, batches = run_fifo_ledger(trades, corp, marks={})
    row = summary.iloc[0]
    assert row["Open_Qty"] == 100
    assert abs(float(row["Realized_PnL"]) - 100.0) < 0.02
    matched = batches.loc[batches["Status"] == "MATCHED"].iloc[0]
    assert matched["Matched_Qty"] == 20
    assert abs(float(matched["Buy_Price"]) - 5.0) < 0.01


def test_cash_merger_matches_as_sell_batch():
    trades = pd.DataFrame([_trade("2021-03-09", "ATVI", "Buy", 20, 80.0)])
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
    summary, batches = run_fifo_ledger(trades, corp, marks={})
    row = summary.iloc[0]
    assert row["Open_Qty"] == 0
    assert row["Realized_PnL"] == 300.0
    matched = batches.loc[batches["Status"] == "MATCHED"].iloc[0]
    assert matched["Sell_Price"] == 95.0
    assert matched["Batch_PnL"] == 300.0


def test_unmatched_sell_booked_as_loss():
    trades = pd.DataFrame([_trade("2024-06-01", "DDD", "Sell", 3, 11.0)])
    summary, batches = run_fifo_ledger(trades, marks={})
    row = summary.iloc[0]
    assert row["Sell_Qty"] == 3
    assert row["Open_Qty"] == 0
    assert row["Result"] == "LOSS"
    assert row["Realized_PnL"] == -33.0
    loss_rows = batches.loc[batches["Status"] == "LOSS"]
    assert len(loss_rows) == 1
    assert loss_rows.iloc[0]["Sell_Qty"] == 3
    assert loss_rows.iloc[0]["Buy_Qty"] == 0
    assert loss_rows.iloc[0]["Batch_PnL"] == -33.0
    assert loss_rows.iloc[0]["Batch_PnL_Pct"] == -100.0
    assert (batches["Status"] == "UNMATCHED_SELL").sum() == 0


def test_excess_sell_slice_is_loss_rest_matched():
    trades = pd.DataFrame(
        [
            _trade("2024-01-01", "EEE", "Buy", 10, 10.0),
            _trade("2024-06-01", "EEE", "Sell", 12, 15.0),
        ]
    )
    summary, batches = run_fifo_ledger(trades, marks={})
    row = summary.iloc[0]
    assert row["Open_Qty"] == 0
    # Matched 10: +50; leftover 2 shares proceeds 30 booked as -30 → realized +20
    assert row["Realized_PnL"] == 20.0
    assert (batches["Status"] == "MATCHED").sum() == 1
    assert (batches["Status"] == "LOSS").sum() == 1
    loss = batches.loc[batches["Status"] == "LOSS"].iloc[0]
    assert loss["Sell_Qty"] == 2
    assert loss["Batch_PnL"] == -30.0


def test_spinoff_credits_child_ticker_not_parent():
    trades = pd.DataFrame(
        [
            _trade("2020-11-01", "PFE", "Buy", 20, 40.0),
            _trade("2021-07-14", "VTRS", "Buy", 10, 14.0),
            _trade("2025-11-06", "VTRS", "Sell", 12.4816, 10.0),
        ]
    )
    corp = pd.DataFrame(
        [
            {
                "Date": "2020-11-17",
                "Symbol": "PFE",
                "ActionType": "SPINOFF",
                "Quantity": 2.4816,
                "Amount": 0.0,
                "Description": (
                    "PFE(US7170811035) Spinoff  124079 for 1000000 "
                    "(VTRS, VIATRIS INC-W/I, US92556V1061)"
                ),
            }
        ]
    )
    summary, batches = run_fifo_ledger(trades, corp, marks={})
    vtrs = summary.loc[summary["Symbol"] == "VTRS"].iloc[0]
    assert abs(float(vtrs["Open_Qty"])) < 1e-6
    loss = batches.loc[(batches["Symbol"] == "VTRS") & (batches["Status"] == "LOSS")]
    assert loss.empty
    matched = batches.loc[(batches["Symbol"] == "VTRS") & (batches["Status"] == "MATCHED")]
    assert abs(float(matched["Matched_Qty"].sum()) - 12.4816) < 0.001


def test_cusip_change_credits_new_ticker():
    trades = pd.DataFrame([_trade("2025-11-06", "LAR", "Sell", 40, 3.8)])
    corp = pd.DataFrame(
        [
            {
                "Date": "2023-10-04",
                "Symbol": "LAC",
                "ActionType": "MERGER",
                "Quantity": 40.0,
                "Amount": 0.0,
                "Description": (
                    "LAC(CA53680Q2071) Merged(Acquisition) WITH LAAC WI 1 for 1, "
                    "CA53681J1030 1 for 1 (LAC, LITHIUM AMERICAS ARGENTINA COR, CA53681J1030)"
                ),
            },
            {
                "Date": "2025-01-27",
                "Symbol": "LAAC",
                "ActionType": "CORPORATE_ACTION",
                "Quantity": -40.0,
                "Amount": 0.0,
                "Description": (
                    "LAAC(CA53681K1003) CUSIP/ISIN Change to (CH1403212751) "
                    "(LAAC.OLD, LITHIUM AMERICAS ARGENTINA C, CA53681K1003)"
                ),
            },
            {
                "Date": "2025-01-27",
                "Symbol": "LAAC",
                "ActionType": "CORPORATE_ACTION",
                "Quantity": 40.0,
                "Amount": 0.0,
                "Description": (
                    "LAAC(CA53681K1003) CUSIP/ISIN Change to (CH1403212751) "
                    "(LAR, LITHIUM ARGENTINA AG, CH1403212751)"
                ),
            },
        ]
    )
    summary, batches = run_fifo_ledger(trades, corp, marks={})
    lar = summary.loc[summary["Symbol"] == "LAR"].iloc[0]
    assert lar["Open_Qty"] == 0
    assert (batches.loc[batches["Symbol"] == "LAR", "Status"] == "LOSS").sum() == 0
    matched = batches.loc[(batches["Symbol"] == "LAR") & (batches["Status"] == "MATCHED")]
    assert abs(float(matched["Matched_Qty"].sum()) - 40.0) < 0.01


def test_cash_and_stock_merger_credits_acquirer():
    trades = pd.DataFrame(
        [
            _trade("2021-06-18", "ZNGA", "Buy", 100, 10.0),
            _trade("2026-02-24", "TTWO", "Sell", 4.06, 202.89),
        ]
    )
    corp = pd.DataFrame(
        [
            {
                "Date": "2022-05-24",
                "Symbol": "ZNGA",
                "ActionType": "MERGER",
                "Quantity": -100.0,
                "Amount": 350.0,
                "Description": (
                    "ZNGA(US98986T1088) Cash and Stock Merger (Acquisition) "
                    "US8740541094 406 for 10000 and USD 3.50 "
                    "(ZNGA, ZYNGA INC - CL A, US98986T1088)"
                ),
            }
        ]
    )
    summary, batches = run_fifo_ledger(trades, corp, marks={})
    ttwo = summary.loc[summary["Symbol"] == "TTWO"].iloc[0]
    assert abs(float(ttwo["Open_Qty"])) < 0.02
    assert (batches.loc[batches["Symbol"] == "TTWO", "Status"] == "LOSS").sum() == 0
    znga = summary.loc[summary["Symbol"] == "ZNGA"].iloc[0]
    assert abs(float(znga["Open_Qty"])) < 1e-6
