"""
Support / resistance levels for completely sold stocks from the IBKR Buy/Sell report.

Reuses swing pivot heuristics from AutomatedTrading/ChartSupportAndSignals.py
(Yahoo Finance daily OHLC via averagePriceFetcher).

Usage:
  python completely_sold_support_report.py
  python completely_sold_support_report.py --input reports/IBKR_BuySell_Since_2020.xlsx
  python completely_sold_support_report.py --from-downloads
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
AUTOMATED_TRADING_DIR = SCRIPT_DIR.parent / "AutomatedTrading"
DEFAULT_BUYSELL_REPORT = Path(r"C:\Investment\reports\IBKR_BuySell_Since_2020.xlsx")
DEFAULT_OUTPUT = Path(r"C:\Investment\reports\Completely_Sold_Support_Resistance.xlsx")
DEFAULT_CHART_CONFIG = AUTOMATED_TRADING_DIR / "config.ini"

if str(AUTOMATED_TRADING_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATED_TRADING_DIR))

from ChartSupportAndSignals import (  # noqa: E402
    get_support_chart_signal,
    load_chart_scan_params,
)

from flex_buysell_report import (  # noqa: E402
    DEFAULT_CONFIG,
    filter_since_year,
    load_config,
    load_trades_for_report,
)
from flex_parse import build_completely_sold_summary  # noqa: E402


def load_completely_sold_from_excel(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Buy/Sell report not found: {path}")
    df = pd.read_excel(path, sheet_name="Completely_Sold", engine="openpyxl")
    if df.empty or "Symbol" not in df.columns:
        raise ValueError(f"No Completely_Sold sheet or empty: {path}")
    return df


def load_completely_sold_from_trades(cfg: dict) -> pd.DataFrame:
    trades, _ = load_trades_for_report(cfg["download_dir"], cfg["query_id"])
    trades = filter_since_year(trades, cfg["start_year"])
    return build_completely_sold_summary(trades)


def fetch_support_resistance_rows(
    symbols: list[str],
    *,
    pivot_left: int,
    pivot_right: int,
    atr_proximity_mult: float,
) -> list[dict]:
    rows: list[dict] = []
    for i, sym in enumerate(symbols, start=1):
        sym = str(sym).strip().upper()
        if not sym:
            continue
        print(f"  [{i}/{len(symbols)}] {sym} …", flush=True)
        payload = get_support_chart_signal(
            sym,
            pivot_left=pivot_left,
            pivot_right=pivot_right,
            atr_proximity_mult=atr_proximity_mult,
        )
        err = payload.get("error")
        rows.append(
            {
                "Symbol": sym,
                "Current_Price": payload.get("Current Price", ""),
                "Nearest_Support": payload.get("Nearest Support", ""),
                "Distance_To_Support_Pct": payload.get("Distance To Support %", ""),
                "Nearest_Resistance": payload.get("Nearest Resistance", ""),
                "Distance_To_Resistance_Pct": payload.get("Distance To Resistance %", ""),
                "ATR14": payload.get("ATR14", ""),
                "Candle_Pattern": payload.get("Candle Pattern", ""),
                "Signal": payload.get("Signal", ""),
                "Signal_Reason": payload.get("Signal Reason", ""),
                "Bars_Loaded": payload.get("Bars loaded", ""),
                "Period_Used": payload.get("Period used (yfinance)", ""),
                "Pivot_Lows": payload.get("Pivot Lows Detected", ""),
                "Pivot_Highs": payload.get("Pivot Highs Detected", ""),
                "Error": err or "",
            }
        )
    return rows


def build_merged_report(closed: pd.DataFrame, sr_rows: list[dict]) -> pd.DataFrame:
    sr = pd.DataFrame(sr_rows)
    trade_cols = [
        c
        for c in (
            "Symbol",
            "Total_Buy_Cost",
            "Total_Sell_Proceeds",
            "Profit",
            "Profit_Pct",
            "Last_Sold_Date",
            "Last_Sold_Price",
            "Current_Market_Price",
            "Change_Since_Last_Sold_Pct",
            "First_Buy_Date",
            "Buy_Qty_Total",
            "Sell_Qty_Total",
        )
        if c in closed.columns
    ]
    base = closed[trade_cols].copy()
    base["Symbol"] = base["Symbol"].astype(str).str.strip().str.upper()
    sr["Symbol"] = sr["Symbol"].astype(str).str.strip().str.upper()
    merged = base.merge(sr, on="Symbol", how="left")
    return merged


def write_support_report(
    merged: pd.DataFrame,
    *,
    output: Path,
    source_label: str,
    symbol_count: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    meta = pd.DataFrame(
        [
            {"Field": "Generated", "Value": datetime.now().isoformat(timespec="seconds")},
            {"Field": "Source", "Value": source_label},
            {"Field": "Completely sold symbols", "Value": str(symbol_count)},
            {"Field": "Support/Resistance engine", "Value": "ChartSupportAndSignals.py (Yahoo Finance daily pivots)"},
            {
                "Field": "Note",
                "Value": "Illustrative pivot levels only — not trading advice. Delisted symbols may show errors.",
            },
        ]
    )
    errors = merged.loc[merged["Error"].astype(str).str.len() > 0] if "Error" in merged.columns else pd.DataFrame()
    ok = merged.loc[merged["Error"].astype(str).str.len() == 0] if "Error" in merged.columns else merged

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        meta.to_excel(writer, sheet_name="Report_Info", index=False)
        merged.to_excel(writer, sheet_name="Support_Resistance", index=False)
        if not ok.empty:
            ok.to_excel(writer, sheet_name="With_Levels", index=False)
        if not errors.empty:
            errors.to_excel(writer, sheet_name="Errors", index=False)

    print(f"Wrote {output}")
    print(f"  Symbols: {symbol_count} | With levels: {len(ok)} | Errors: {len(errors)}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Support/resistance report for completely sold stocks (IBKR Buy/Sell report)"
    )
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="IBKR Flex config.ini")
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help=f"Buy/Sell Excel with Completely_Sold sheet (default: {DEFAULT_BUYSELL_REPORT.name})",
    )
    ap.add_argument(
        "--from-downloads",
        action="store_true",
        help="Derive completely sold list from Flex cache instead of Excel",
    )
    ap.add_argument(
        "--chart-config",
        type=Path,
        default=DEFAULT_CHART_CONFIG,
        help="AutomatedTrading config.ini for pivot settings",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output Excel path")
    args = ap.parse_args()

    cfg = load_config(args.config)
    pivot_left, pivot_right, atr_prox = load_chart_scan_params(args.chart_config)

    if args.from_downloads:
        closed = load_completely_sold_from_trades(cfg)
        source_label = "Flex cache → build_completely_sold_summary"
    else:
        report_path = args.input or DEFAULT_BUYSELL_REPORT
        if not report_path.is_absolute():
            report_path = SCRIPT_DIR / report_path
        closed = load_completely_sold_from_excel(report_path)
        source_label = str(report_path)

    symbols = sorted(closed["Symbol"].astype(str).str.strip().str.upper().unique())
    if not symbols:
        print("No completely sold symbols found.", file=sys.stderr)
        return 1

    print(f"Fetching support/resistance for {len(symbols)} completely sold symbols …", flush=True)
    sr_rows = fetch_support_resistance_rows(
        symbols,
        pivot_left=pivot_left,
        pivot_right=pivot_right,
        atr_proximity_mult=atr_prox,
    )
    merged = build_merged_report(closed, sr_rows)

    output = args.output.resolve() if args.output.is_absolute() else SCRIPT_DIR / args.output
    write_support_report(merged, output=output, source_label=source_label, symbol_count=len(symbols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
