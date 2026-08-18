"""
Build per-symbol P&L (Profit / Loss) from IBKR_BuySell_Since_2020.xlsx Buys + Sells sheets.

Default input:  C:\\Investment\\reports\\IBKR_BuySell_Since_2020.xlsx
Default output: C:\\Investment\\reports\\IBKR_Symbol_PnL_From_BuySell.xlsx
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

FLEX_DIR = Path(r"C:\Investment\IBKR-Flex-BuySell")
if str(FLEX_DIR) not in sys.path:
    sys.path.insert(0, str(FLEX_DIR))

from trade_history.corporate_parse import load_corporate_from_transactions_dir  # noqa: E402
from trade_history.symbol_pnl import (  # noqa: E402
    build_symbol_pnl,
    completely_sold_from_symbol_pnl,
    still_holding_from_symbol_pnl,
)

DEFAULT_INPUT = Path(r"C:\Investment\reports\IBKR_BuySell_Since_2020.xlsx")
DEFAULT_OUTPUT = Path(r"C:\Investment\reports\IBKR_Symbol_PnL_From_BuySell.xlsx")
TX_DIR = Path(r"C:\Investment\IBKR-Transaction")


def load_buys_sells(path: Path) -> pd.DataFrame:
    """Combine Buys + Sells sheets into one trade frame."""
    xl = pd.ExcelFile(path)
    sheets = {n.lower(): n for n in xl.sheet_names}
    buy_name = sheets.get("buys")
    sell_name = sheets.get("sells")
    if not buy_name or not sell_name:
        raise FileNotFoundError(
            f"{path} must contain 'Buys' and 'Sells' sheets. Found: {xl.sheet_names}"
        )
    buys = pd.read_excel(path, sheet_name=buy_name)
    sells = pd.read_excel(path, sheet_name=sell_name)
    buys = buys.copy()
    sells = sells.copy()
    buys["Transaction Type"] = "Buy"
    sells["Transaction Type"] = "Sell"
    trades = pd.concat([buys, sells], ignore_index=True)
    if "Date" in trades.columns:
        trades["Date"] = pd.to_datetime(trades["Date"], errors="coerce")
    if "Symbol" in trades.columns:
        trades["Symbol"] = trades["Symbol"].astype(str).str.strip().str.upper()
    return trades.sort_values(["Date", "Symbol"], na_position="last").reset_index(drop=True)


def classify_result(row: pd.Series) -> str:
    open_qty = float(row.get("Open_Qty") or 0)
    realized = float(row.get("Realized_PnL") or 0)
    total = row.get("Total_PnL")
    if total is None or (isinstance(total, float) and pd.isna(total)):
        total = realized
    total = float(total)

    if abs(open_qty) > 1e-6:
        if total > 1e-2:
            return "OPEN — unrealized/total profit"
        if total < -1e-2:
            return "OPEN — unrealized/total loss"
        return "OPEN — flat"
    if realized > 1e-2:
        return "PROFIT"
    if realized < -1e-2:
        return "LOSS"
    return "BREAKEVEN"


def enrich_clarity(pnl: pd.DataFrame) -> pd.DataFrame:
    out = pnl.copy()
    out["Result"] = out.apply(classify_result, axis=1)
    out["Result_Simple"] = out["Result"].map(
        lambda r: (
            "PROFIT"
            if str(r).startswith("PROFIT")
            else (
                "LOSS"
                if str(r).startswith("LOSS")
                else ("OPEN" if str(r).startswith("OPEN") else "BREAKEVEN")
            )
        )
    )
    order = {"LOSS": 0, "OPEN": 1, "BREAKEVEN": 2, "PROFIT": 3}
    out["_ord"] = out["Result_Simple"].map(order).fillna(9)
    front = [
        "Symbol",
        "Result_Simple",
        "Result",
        "Realized_PnL",
        "Total_PnL",
        "Open_Qty",
        "Buy_Qty",
        "Sell_Qty",
        "Buy_Cost",
        "Sell_Proceeds",
        "Dividends",
        "Unrealized_PnL",
        "Mark_Price",
        "First_Buy_Date",
        "Last_Sell_Date",
        "Buy_Trades",
        "Sell_Trades",
        "Corp_Notes",
    ]
    cols = [c for c in front if c in out.columns] + [
        c for c in out.columns if c not in front and c != "_ord"
    ]
    out = out.sort_values(["_ord", "Realized_PnL"], ascending=[True, True]).drop(columns=["_ord"])
    return out[cols].reset_index(drop=True)


def build_workbook(
    input_path: Path,
    output_path: Path,
    *,
    transactions_dir: Path,
    fetch_marks: bool,
) -> Path:
    trades = load_buys_sells(input_path)
    corp = pd.DataFrame()
    corp_note = "none"
    if transactions_dir.is_dir():
        try:
            corp = load_corporate_from_transactions_dir(transactions_dir)
            corp_note = f"{len(corp)} rows from {transactions_dir}"
        except Exception as exc:
            corp_note = f"skipped ({exc})"

    pnl = build_symbol_pnl(trades, corp if not corp.empty else None, fetch_marks=fetch_marks)
    pnl = enrich_clarity(pnl)
    closed = completely_sold_from_symbol_pnl(pnl)
    if not closed.empty:
        closed = closed.copy()
        closed["Result_Simple"] = closed["Profit"].map(
            lambda p: "PROFIT" if float(p) > 1e-2 else ("LOSS" if float(p) < -1e-2 else "BREAKEVEN")
        )
        closed["Result"] = closed["Result_Simple"]
    holding = still_holding_from_symbol_pnl(pnl)

    profits = pnl.loc[pnl["Result_Simple"] == "PROFIT"].copy()
    losses = pnl.loc[pnl["Result_Simple"] == "LOSS"].copy()
    open_rows = pnl.loc[pnl["Result_Simple"] == "OPEN"].copy()

    summary = pd.DataFrame(
        [
            {"Metric": "Symbols total", "Value": len(pnl)},
            {"Metric": "PROFIT (closed)", "Value": len(profits)},
            {"Metric": "LOSS (closed)", "Value": len(losses)},
            {"Metric": "OPEN / still holding", "Value": len(open_rows)},
            {
                "Metric": "Sum Realized_PnL (all symbols)",
                "Value": round(float(pnl["Realized_PnL"].sum()), 2),
            },
            {
                "Metric": "Sum Realized_PnL — PROFIT only",
                "Value": round(float(profits["Realized_PnL"].sum()), 2) if not profits.empty else 0.0,
            },
            {
                "Metric": "Sum Realized_PnL — LOSS only",
                "Value": round(float(losses["Realized_PnL"].sum()), 2) if not losses.empty else 0.0,
            },
            {
                "Metric": "Sum Total_PnL (incl. open marks if fetched)",
                "Value": round(float(pd.to_numeric(pnl["Total_PnL"], errors="coerce").fillna(0).sum()), 2),
            },
        ]
    )

    meta = pd.DataFrame(
        [
            {"Field": "Generated at", "Value": datetime.now().isoformat(timespec="seconds")},
            {"Field": "Input workbook", "Value": str(input_path)},
            {"Field": "Sheets used", "Value": "Buys + Sells"},
            {"Field": "Buy rows", "Value": str(int((trades["Transaction Type"] == "Buy").sum()))},
            {"Field": "Sell rows", "Value": str(int((trades["Transaction Type"] == "Sell").sum()))},
            {"Field": "Corporate actions", "Value": corp_note},
            {"Field": "Method", "Value": "Average-cost ledger + SPLIT/MERGER (chronological)"},
            {
                "Field": "Result labels",
                "Value": "PROFIT / LOSS / BREAKEVEN (closed) or OPEN (still holding)",
            },
            {"Field": "Output", "Value": str(output_path)},
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        meta.to_excel(writer, sheet_name="Report_Info", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        pnl.to_excel(writer, sheet_name="Symbol_PnL", index=False)
        losses.to_excel(writer, sheet_name="Losses", index=False)
        profits.to_excel(writer, sheet_name="Profits", index=False)
        open_rows.to_excel(writer, sheet_name="Still_Open", index=False)
        if not closed.empty:
            closed.to_excel(writer, sheet_name="Completely_Sold", index=False)
        if not holding.empty:
            holding.to_excel(writer, sheet_name="Still_Holding", index=False)

    return output_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Symbol-wise P&L (Profit/Loss) from IBKR BuySell Excel Buys+Sells sheets."
    )
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="IBKR_BuySell_Since_2020.xlsx")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output Excel path")
    ap.add_argument(
        "--transactions-dir",
        type=Path,
        default=TX_DIR,
        help="IBKR-Transaction folder for corporate actions (splits/mergers)",
    )
    ap.add_argument(
        "--no-market-prices",
        action="store_true",
        help="Skip Yahoo marks for open positions",
    )
    args = ap.parse_args(argv)

    if not args.input.is_file():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 2

    try:
        path = build_workbook(
            args.input,
            args.output,
            transactions_dir=args.transactions_dir,
            fetch_marks=not args.no_market_prices,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    pnl = pd.read_excel(path, sheet_name="Symbol_PnL")
    print(f"Wrote {path}")
    print(
        f"  Symbols={len(pnl)} | "
        f"PROFIT={(pnl['Result_Simple']=='PROFIT').sum()} | "
        f"LOSS={(pnl['Result_Simple']=='LOSS').sum()} | "
        f"OPEN={(pnl['Result_Simple']=='OPEN').sum()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
