"""
Per-symbol IBKR snapshot: buys, sells, corporate actions, last traded price,
realized P&L and unrealized P&L.

Default input:  C:\\Investment\\reports\\IBKR_BuySell_Since_2020.xlsx
Default output: C:\\Investment\\reports\\IBKR_Symbol_Detail.xlsx
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

INVESTMENT_ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = INVESTMENT_ROOT / "IBKR-BatchPnL"
FLEX_DIR = INVESTMENT_ROOT / "IBKR-Flex-BuySell"
for _p in (BATCH_DIR, FLEX_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from batch_pnl_report import _fetch_marks, _load_corporate, load_buys_sells  # noqa: E402
from fifo_ledger import _normalize_symbol, run_fifo_ledger  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_INPUT = INVESTMENT_ROOT / "reports" / "IBKR_BuySell_Since_2020.xlsx"
DEFAULT_OUTPUT = INVESTMENT_ROOT / "reports" / "IBKR_Symbol_Detail.xlsx"
TX_DIR = INVESTMENT_ROOT / "IBKR-Transaction"

SHARE_ACTIONS = frozenset({"SPLIT", "MERGER", "SPINOFF", "CORPORATE_ACTION"})

_BY_SYMBOL_COLS = [
    "Symbol",
    "Result",
    "Buy_Qty",
    "Avg_Buy_Price",
    "Buy_Cost",
    "Buy_Trades",
    "First_Buy_Date",
    "Sell_Qty",
    "Avg_Sell_Price",
    "Sell_Proceeds",
    "Sell_Trades",
    "Last_Sell_Date",
    "Open_Qty",
    "Last_Trade_Price",
    "Price_As_Of",
    "Realized_PnL",
    "Unrealized_PnL",
    "Total_PnL",
    "Corp_Action_Count",
    "Corp_Actions",
]


def parse_symbol_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [_normalize_symbol(p) for p in raw.replace(";", ",").split(",") if p.strip()]


def _filter_symbols(df: pd.DataFrame, symbols: list[str], column: str = "Symbol") -> pd.DataFrame:
    if not symbols or df.empty or column not in df.columns:
        return df
    want = {_normalize_symbol(s) for s in symbols}
    mapped = df[column].map(_normalize_symbol)
    return df.loc[mapped.isin(want)].copy()


def corporate_touching_symbol(corp: pd.DataFrame, symbols: list[str] | None = None) -> pd.DataFrame:
    """Share-moving corporate actions; optional filter to symbols (row ticker or description)."""
    if corp is None or corp.empty:
        return pd.DataFrame(
            columns=["Date", "Symbol", "ActionType", "Quantity", "Amount", "Description"]
        )
    out = corp.copy()
    out["Symbol"] = out["Symbol"].map(_normalize_symbol)
    out["ActionType"] = out["ActionType"].astype(str).str.strip().str.upper()
    out = out.loc[out["ActionType"].isin(SHARE_ACTIONS)].copy()
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    if symbols:
        want = {_normalize_symbol(s) for s in symbols}
        desc = out["Description"].astype(str) if "Description" in out.columns else ""
        keep = out["Symbol"].isin(want)
        for sym in want:
            keep = keep | desc.str.contains(rf"\({re.escape(sym)}\s*,", case=False, na=False)
            keep = keep | desc.str.contains(rf"\b{re.escape(sym)}\b", case=False, na=False)
        out = out.loc[keep].copy()
    cols = [c for c in ["Date", "Symbol", "ActionType", "Quantity", "Amount", "Description"] if c in out.columns]
    return out.sort_values(["Symbol", "Date"], na_position="last")[cols].reset_index(drop=True)


def corp_notes_by_symbol(corp_share: pd.DataFrame) -> dict[str, tuple[int, str]]:
    """Map symbol -> (count, short note list)."""
    notes: dict[str, list[str]] = {}
    if corp_share.empty:
        return {}
    for _, row in corp_share.iterrows():
        sym = _normalize_symbol(row.get("Symbol"))
        if not sym:
            continue
        dt = row.get("Date")
        dt_s = pd.Timestamp(dt).date().isoformat() if pd.notna(dt) else ""
        act = str(row.get("ActionType") or "")
        desc = str(row.get("Description") or "")[:60]
        notes.setdefault(sym, []).append(f"{dt_s} {act} {desc}".strip())
        extra = re.findall(r"\(([A-Z][A-Z0-9.]{0,11})\s*,", str(row.get("Description") or ""))
        for other in extra:
            o = _normalize_symbol(other)
            if o and o != sym:
                notes.setdefault(o, []).append(f"{dt_s} {act} via {sym} {desc}".strip())
    return {k: (len(v), "; ".join(v[:5])) for k, v in notes.items()}


def trade_detail(trades: pd.DataFrame, side: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["Date", "Symbol", "Quantity", "Price", "Net Amount"])
    side_l = side.strip().lower()
    tt = trades["Transaction Type"].astype(str).str.strip().str.lower()
    sub = trades.loc[tt.eq(side_l)].copy()
    cols = [c for c in ["Date", "Symbol", "Quantity", "Price", "Net Amount", "Gross Amount", "Commission"] if c in sub.columns]
    return sub[cols].sort_values(["Symbol", "Date"], na_position="last").reset_index(drop=True)


def build_timeline(buys: pd.DataFrame, sells: pd.DataFrame, corp: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for side, frame in (("Buy", buys), ("Sell", sells)):
        if frame.empty:
            continue
        for _, r in frame.iterrows():
            rows.append(
                {
                    "Date": r.get("Date"),
                    "Symbol": _normalize_symbol(r.get("Symbol")),
                    "Event": side,
                    "Quantity": pd.to_numeric(r.get("Quantity"), errors="coerce"),
                    "Price": pd.to_numeric(r.get("Price"), errors="coerce"),
                    "Amount": pd.to_numeric(r.get("Net Amount"), errors="coerce"),
                    "Description": "",
                }
            )
    if not corp.empty:
        for _, r in corp.iterrows():
            rows.append(
                {
                    "Date": r.get("Date"),
                    "Symbol": _normalize_symbol(r.get("Symbol")),
                    "Event": str(r.get("ActionType") or "CORP"),
                    "Quantity": pd.to_numeric(r.get("Quantity"), errors="coerce"),
                    "Price": None,
                    "Amount": pd.to_numeric(r.get("Amount"), errors="coerce"),
                    "Description": str(r.get("Description") or "")[:120],
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=["Date", "Symbol", "Event", "Quantity", "Price", "Amount", "Description"]
        )
    out = pd.DataFrame(rows)
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    return out.sort_values(["Symbol", "Date", "Event"], na_position="last").reset_index(drop=True)


def apply_last_prices(
    summary: pd.DataFrame,
    marks: dict[str, tuple[float | None, object]],
) -> pd.DataFrame:
    out = summary.copy()
    prices: list[float | None] = []
    as_ofs: list[object] = []
    for _, row in out.iterrows():
        price, as_of = marks.get(str(row["Symbol"]), (None, None))
        prices.append(round(float(price), 4) if price is not None else None)
        as_ofs.append(as_of)
    out["Last_Trade_Price"] = prices
    out["Price_As_Of"] = as_ofs
    if "Mark_Price" not in out.columns:
        out["Mark_Price"] = out["Last_Trade_Price"]
    else:
        out["Mark_Price"] = out["Mark_Price"].where(out["Mark_Price"].notna(), out["Last_Trade_Price"])
    return out


def attach_corp_columns(summary: pd.DataFrame, corp_share: pd.DataFrame) -> pd.DataFrame:
    notes = corp_notes_by_symbol(corp_share)
    out = summary.copy()
    out["Corp_Action_Count"] = out["Symbol"].map(lambda s: notes.get(str(s), (0, ""))[0])
    out["Corp_Actions"] = out["Symbol"].map(lambda s: notes.get(str(s), (0, ""))[1])
    return out


def assemble_by_symbol(summary: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in _BY_SYMBOL_COLS if c in summary.columns]
    extra = [c for c in summary.columns if c not in cols]
    return summary[cols + extra]


def print_symbol_card(row: pd.Series, timeline: pd.DataFrame) -> None:
    sym = row["Symbol"]
    print(f"=== {sym}  ({row.get('Result', '')}) ===")
    print(
        f"  Buy:      {row.get('Buy_Qty')} sh  avg {row.get('Avg_Buy_Price')}  "
        f"cost {row.get('Buy_Cost')}  trades={row.get('Buy_Trades')}  first={row.get('First_Buy_Date')}"
    )
    print(
        f"  Sell:     {row.get('Sell_Qty')} sh  avg {row.get('Avg_Sell_Price')}  "
        f"proceeds {row.get('Sell_Proceeds')}  trades={row.get('Sell_Trades')}  last={row.get('Last_Sell_Date')}"
    )
    print(f"  Open:     {row.get('Open_Qty')} sh")
    print(f"  Last px:  {row.get('Last_Trade_Price')}  as of {row.get('Price_As_Of')}")
    print(f"  Realized: {row.get('Realized_PnL')}")
    print(f"  Unrealzd: {row.get('Unrealized_PnL')}")
    print(f"  Total:    {row.get('Total_PnL')}")
    corp = row.get("Corp_Actions") or "(none)"
    print(f"  Corp:     {corp}")
    sub = timeline.loc[timeline["Symbol"].map(_normalize_symbol) == _normalize_symbol(sym)]
    if not sub.empty:
        print("  Timeline:")
        for _, ev in sub.iterrows():
            dt = ev["Date"]
            dt_s = pd.Timestamp(dt).date().isoformat() if pd.notna(dt) else ""
            print(
                f"    {dt_s}  {ev['Event']:16}  qty={ev['Quantity']}  "
                f"px={ev['Price']}  amt={ev['Amount']}"
            )


def build_report(
    input_path: Path,
    *,
    transactions_dir: Path,
    fetch_marks: bool,
    symbols: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trades = load_buys_sells(input_path)
    if symbols:
        trades = _filter_symbols(trades, symbols)
        if trades.empty:
            raise ValueError(f"No buys/sells for symbol(s): {', '.join(symbols)}")
    corp, corp_note = _load_corporate(transactions_dir)
    logger.info("Corporate actions: %s", corp_note)
    corp_df = corp if not corp.empty else None
    corp_share = corporate_touching_symbol(corp, symbols or None)

    summary, _batches = run_fifo_ledger(trades, corp_df, marks={})
    marks: dict[str, tuple[float | None, object]] = {}
    if fetch_marks:
        want = symbols if symbols else (
            summary["Symbol"].tolist() if not summary.empty else []
        )
        marks = _fetch_marks(want)
        if marks:
            summary, _batches = run_fifo_ledger(trades, corp_df, marks=marks)
    summary = apply_last_prices(summary, marks)
    summary = attach_corp_columns(summary, corp_share)
    if symbols:
        summary = _filter_symbols(summary, symbols)
    by_symbol = assemble_by_symbol(summary)

    buys = trade_detail(trades, "Buy")
    sells = trade_detail(trades, "Sell")
    timeline = build_timeline(buys, sells, corp_share)
    return by_symbol, buys, sells, corp_share, timeline


def write_workbook(
    output_path: Path,
    *,
    by_symbol: pd.DataFrame,
    buys: pd.DataFrame,
    sells: pd.DataFrame,
    corp: pd.DataFrame,
    timeline: pd.DataFrame,
    meta: pd.DataFrame,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        by_symbol.to_excel(writer, sheet_name="By_Symbol", index=False)
        buys.to_excel(writer, sheet_name="Buys", index=False)
        sells.to_excel(writer, sheet_name="Sells", index=False)
        corp.to_excel(writer, sheet_name="Corporate_Actions", index=False)
        timeline.to_excel(writer, sheet_name="Timeline", index=False)
        meta.to_excel(writer, sheet_name="Report_Info", index=False)
    return output_path


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(
        description=(
            "Per-symbol buys, sells, corporate actions, last traded price, "
            "realized and unrealized P&L."
        )
    )
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--transactions-dir", type=Path, default=TX_DIR)
    ap.add_argument("--symbol", "--symbols", dest="symbols", default=None, help="AAPL or AAPL,NVDA")
    ap.add_argument(
        "--no-market-prices",
        action="store_true",
        help="Skip Yahoo last traded prices (unrealized stays blank)",
    )
    args = ap.parse_args(argv)
    symbols = parse_symbol_list(args.symbols)

    if not args.input.is_file():
        print(f"ERROR: Buy/Sell workbook not found: {args.input}", file=sys.stderr)
        return 2

    try:
        by_symbol, buys, sells, corp, timeline = build_report(
            args.input,
            transactions_dir=args.transactions_dir,
            fetch_marks=not args.no_market_prices,
            symbols=symbols,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        logger.exception("symbol detail failed")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    meta = pd.DataFrame(
        [
            {"Field": "Generated at", "Value": datetime.now().isoformat(timespec="seconds")},
            {"Field": "Input", "Value": str(args.input)},
            {"Field": "Symbols filter", "Value": ",".join(symbols) if symbols else "(all)"},
            {"Field": "Method", "Value": "FIFO lots + IBKR corporate actions + Yahoo last price"},
            {"Field": "Output", "Value": str(args.output)},
        ]
    )
    path = write_workbook(
        args.output,
        by_symbol=by_symbol,
        buys=buys,
        sells=sells,
        corp=corp,
        timeline=timeline,
        meta=meta,
    )
    print(f"Wrote {path}")
    print(f"  Symbols={len(by_symbol)}  buys={len(buys)}  sells={len(sells)}  corp={len(corp)}")
    if symbols:
        for _, row in by_symbol.iterrows():
            print_symbol_card(row, timeline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
