"""Tests for per-symbol detail assembly (no Yahoo / IBKR calls)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT.parent / "IBKR-BatchPnL"
FLEX = ROOT.parent / "IBKR-Flex-BuySell"
for p in (ROOT, BATCH, FLEX):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from symbol_detail_report import (
    apply_last_prices,
    attach_corp_columns,
    build_timeline,
    corporate_touching_symbol,
    parse_symbol_list,
    trade_detail,
)


def test_parse_symbol_list():
    assert parse_symbol_list("aapl, nvda; TSLA") == ["AAPL", "NVDA", "TSLA"]
    assert parse_symbol_list(None) == []


def test_corporate_touching_includes_spinoff_child():
    corp = pd.DataFrame(
        [
            {
                "Date": "2020-11-17",
                "Symbol": "PFE",
                "ActionType": "SPINOFF",
                "Quantity": 2.48,
                "Amount": 0.0,
                "Description": "PFE Spinoff (VTRS, VIATRIS INC-W/I, US92556V1061)",
            },
            {
                "Date": "2021-06-16",
                "Symbol": "VTRS",
                "ActionType": "DIVIDEND",
                "Quantity": None,
                "Amount": 1.65,
                "Description": "Ordinary Dividend",
            },
        ]
    )
    out = corporate_touching_symbol(corp, ["VTRS"])
    assert len(out) == 1
    assert out.iloc[0]["ActionType"] == "SPINOFF"


def test_timeline_orders_buy_corp_sell():
    buys = pd.DataFrame(
        [{"Date": "2022-01-01", "Symbol": "AMZN", "Quantity": 6, "Price": 100.0, "Net Amount": -600}]
    )
    sells = pd.DataFrame(
        [{"Date": "2023-01-01", "Symbol": "AMZN", "Quantity": 20, "Price": 10.0, "Net Amount": 200}]
    )
    corp = pd.DataFrame(
        [
            {
                "Date": "2022-06-06",
                "Symbol": "AMZN",
                "ActionType": "SPLIT",
                "Quantity": 114,
                "Amount": 0.0,
                "Description": "Split 20 for 1",
            }
        ]
    )
    tl = build_timeline(buys, sells, corp)
    assert list(tl["Event"]) == ["Buy", "SPLIT", "Sell"]


def test_last_price_and_corp_columns():
    summary = pd.DataFrame(
        [
            {
                "Symbol": "AAA",
                "Result": "OPEN",
                "Buy_Qty": 10,
                "Open_Qty": 10,
                "Realized_PnL": 0.0,
                "Unrealized_PnL": None,
            }
        ]
    )
    marks = {"AAA": (12.5, None)}
    out = apply_last_prices(summary, marks)
    assert out.iloc[0]["Last_Trade_Price"] == 12.5
    corp = pd.DataFrame(
        [
            {
                "Date": "2022-06-06",
                "Symbol": "AAA",
                "ActionType": "SPLIT",
                "Quantity": 10,
                "Amount": 0,
                "Description": "Split 2 for 1",
            }
        ]
    )
    out = attach_corp_columns(out, corp)
    assert out.iloc[0]["Corp_Action_Count"] == 1
    assert "SPLIT" in str(out.iloc[0]["Corp_Actions"])


def test_trade_detail_buy_only():
    trades = pd.DataFrame(
        [
            {
                "Date": "2024-01-01",
                "Symbol": "BBB",
                "Transaction Type": "Buy",
                "Quantity": 2,
                "Price": 5,
                "Net Amount": -10,
            },
            {
                "Date": "2024-02-01",
                "Symbol": "BBB",
                "Transaction Type": "Sell",
                "Quantity": 2,
                "Price": 6,
                "Net Amount": 12,
            },
        ]
    )
    buys = trade_detail(trades, "Buy")
    assert len(buys) == 1
    assert float(buys.iloc[0]["Quantity"]) == 2
