"""
FIFO batch P&L from IBKR_BuySell_Since_2020.xlsx Buys + Sells.

Sheet 1 — Symbol_Summary: avg buy/sell price and qty, realized / unrealized P&L.
Sheet 2 — Batch_PnL: each FIFO-matched buy lot vs sell (relative batch profit).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

INVESTMENT_ROOT = Path(__file__).resolve().parents[1]
FLEX_DIR = INVESTMENT_ROOT / "IBKR-Flex-BuySell"
if str(FLEX_DIR) not in sys.path:
    sys.path.insert(0, str(FLEX_DIR))

from fifo_ledger import run_fifo_ledger  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_INPUT = INVESTMENT_ROOT / "reports" / "IBKR_BuySell_Since_2020.xlsx"
DEFAULT_OUTPUT = INVESTMENT_ROOT / "reports" / "IBKR_Batch_PnL.xlsx"
TX_DIR = INVESTMENT_ROOT / "IBKR-Transaction"


def _today_yyyymmdd() -> str:
    return date.today().strftime("%Y%m%d")


def _end_dates_newest_first(to_date: str, lookback_days: int = 5) -> list[str]:
    end = datetime.strptime(to_date, "%Y%m%d").date()
    return [(end - timedelta(days=i)).strftime("%Y%m%d") for i in range(lookback_days + 1)]


def refresh_buysell_through_today(
    output_path: Path,
    *,
    to_date: str,
    offline: bool,
) -> None:
    """Pull IBKR Flex YTD through to_date (or latest available day), then rebuild Buy/Sell Excel."""
    from flex_buysell_report import (
        IBKR_TRANSACTION_DIR,
        filter_since_year,
        load_config,
        load_trades_combined,
        write_report,
    )
    from flex_ytd import download_ytd_flex

    cfg_path = FLEX_DIR / "config.ini"
    cfg = load_config(cfg_path, required_for_download=not offline)
    effective = to_date

    if not offline:
        got = None
        for td in _end_dates_newest_first(to_date):
            cfg["to_date"] = td
            logger.info("Trying IBKR Flex YTD through %s", td)
            got = download_ytd_flex(cfg, force=True)
            if got is not None and got.is_file() and got.stat().st_size > 50:
                effective = td
                logger.info("Flex YTD ready through %s (%s)", td, got.name)
                break
            time.sleep(5)
        else:
            logger.warning(
                "Flex YTD not available through %s; rebuilding from cache + Activity CSV",
                to_date,
            )
            effective = to_date

    cfg["to_date"] = effective
    trades, label = load_trades_combined(
        cfg["download_dir"],
        cfg["query_id"],
        IBKR_TRANSACTION_DIR,
    )
    trades = filter_since_year(trades, cfg["start_year"])
    if trades.empty:
        raise RuntimeError("No Buy/Sell trades after refresh")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(
        trades,
        output_path,
        source_label=f"{label}; through {effective}",
        start_year=cfg["start_year"],
        fetch_market_prices=False,
    )
    logger.info("Buy/Sell refreshed through %s → %s", effective, output_path)


def load_buys_sells(path: Path) -> pd.DataFrame:
    """Combine Buys + Sells sheets into one trade frame."""
    if not path.is_file():
        raise FileNotFoundError(f"Buy/Sell workbook not found: {path}")
    xl = pd.ExcelFile(path)
    sheets = {n.lower(): n for n in xl.sheet_names}
    buy_name = sheets.get("buys")
    sell_name = sheets.get("sells")
    if not buy_name or not sell_name:
        raise ValueError(
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


def _load_corporate(transactions_dir: Path) -> tuple[pd.DataFrame, str]:
    if not transactions_dir.is_dir():
        return pd.DataFrame(), f"skipped (not a directory: {transactions_dir})"
    try:
        from trade_history.corporate_parse import load_corporate_from_transactions_dir

        corp = load_corporate_from_transactions_dir(transactions_dir)
        return corp, f"{len(corp)} rows from {transactions_dir}"
    except Exception as exc:
        logger.warning("corporate actions skipped: %s", exc)
        return pd.DataFrame(), f"skipped ({exc})"


def _fetch_marks(symbols: list[str]) -> dict[str, tuple[float | None, object]]:
    if not symbols:
        return {}
    try:
        from market_prices import fetch_current_market_prices

        return fetch_current_market_prices(symbols)
    except ImportError:
        logger.warning("yfinance not installed — skipping market prices")
        return {}
    except Exception as exc:
        logger.warning("market prices failed: %s", exc)
        return {}


def build_workbook(
    input_path: Path,
    output_path: Path,
    *,
    transactions_dir: Path,
    fetch_marks: bool,
) -> Path:
    trades = load_buys_sells(input_path)
    corp, corp_note = _load_corporate(transactions_dir)

    corp_df = corp if not corp.empty else None
    summary, batches = run_fifo_ledger(trades, corp_df, marks={})
    if fetch_marks and not summary.empty:
        open_syms = summary.loc[summary["Open_Qty"].abs() > 1e-6, "Symbol"].tolist()
        marks = _fetch_marks(open_syms)
        if marks:
            summary, batches = run_fifo_ledger(trades, corp_df, marks=marks)

    matched = batches.loc[batches["Status"] == "MATCHED"] if not batches.empty else batches
    open_lots = batches.loc[batches["Status"] == "OPEN"] if not batches.empty else batches
    loss_lots = batches.loc[batches["Status"] == "LOSS"] if not batches.empty else batches

    summary_stats = pd.DataFrame(
        [
            {"Metric": "Symbols", "Value": len(summary)},
            {
                "Metric": "PROFIT (closed)",
                "Value": int((summary["Result"] == "PROFIT").sum()) if not summary.empty else 0,
            },
            {
                "Metric": "LOSS (closed)",
                "Value": int((summary["Result"] == "LOSS").sum()) if not summary.empty else 0,
            },
            {
                "Metric": "OPEN / still holding",
                "Value": int((summary["Result"] == "OPEN").sum()) if not summary.empty else 0,
            },
            {
                "Metric": "FIFO matched batches",
                "Value": len(matched),
            },
            {
                "Metric": "Open lots (unrealized)",
                "Value": len(open_lots),
            },
            {
                "Metric": "Unmatched sells booked as LOSS",
                "Value": len(loss_lots),
            },
            {
                "Metric": "Sum Realized_PnL",
                "Value": round(float(summary["Realized_PnL"].sum()), 2) if not summary.empty else 0.0,
            },
            {
                "Metric": "Sum Unrealized_PnL",
                "Value": round(
                    float(pd.to_numeric(summary["Unrealized_PnL"], errors="coerce").fillna(0).sum()),
                    2,
                )
                if not summary.empty
                else 0.0,
            },
        ]
    )

    meta = pd.DataFrame(
        [
            {"Field": "Generated at", "Value": datetime.now().isoformat(timespec="seconds")},
            {"Field": "Input workbook", "Value": str(input_path)},
            {"Field": "Sheets used", "Value": "Buys + Sells"},
            {
                "Field": "Buy rows",
                "Value": str(int((trades["Transaction Type"] == "Buy").sum())),
            },
            {
                "Field": "Sell rows",
                "Value": str(int((trades["Transaction Type"] == "Sell").sum())),
            },
            {"Field": "Corporate actions", "Value": corp_note},
            {
                "Field": "Method",
                "Value": (
                    "FIFO lot matching; unmatched sells booked as realized LOSS; "
                    "splits/mergers applied"
                ),
            },
            {
                "Field": "Symbol_Summary",
                "Value": "Avg buy/sell price & qty, realized vs unrealized P&L",
            },
            {
                "Field": "Batch_PnL",
                "Value": "One row per FIFO slice: buy qty/price/date vs sell qty/price/date + batch P&L",
            },
            {"Field": "Output", "Value": str(output_path)},
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Symbol_Summary", index=False)
        batches.to_excel(writer, sheet_name="Batch_PnL", index=False)
        summary_stats.to_excel(writer, sheet_name="Summary", index=False)
        meta.to_excel(writer, sheet_name="Report_Info", index=False)

    return output_path


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(
        description=(
            "Per-symbol average buy/sell plus FIFO batch P&L from IBKR BuySell Excel."
        )
    )
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="IBKR_BuySell_Since_2020.xlsx")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output Excel path")
    ap.add_argument(
        "--transactions-dir",
        type=Path,
        default=TX_DIR,
        help="IBKR-Transaction folder for splits/mergers",
    )
    ap.add_argument(
        "--no-market-prices",
        action="store_true",
        help="Skip Yahoo marks for open lots (unrealized stays blank)",
    )
    ap.add_argument(
        "--skip-refresh",
        action="store_true",
        help="Do not refresh Buy/Sell from IBKR first (use existing Excel)",
    )
    ap.add_argument(
        "--offline",
        action="store_true",
        help="Refresh Buy/Sell from local Flex cache + Activity CSV only (no Flex API)",
    )
    ap.add_argument(
        "--to-date",
        default=None,
        help="Buy/Sell refresh end date YYYYMMDD (default: today)",
    )
    args = ap.parse_args(argv)

    to_date = str(args.to_date).replace("-", "").strip() if args.to_date else _today_yyyymmdd()

    try:
        if not args.skip_refresh:
            refresh_buysell_through_today(
                args.input,
                to_date=to_date,
                offline=args.offline,
            )
        path = build_workbook(
            args.input,
            args.output,
            transactions_dir=args.transactions_dir,
            fetch_marks=not args.no_market_prices,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        logger.exception("batch P&L failed")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    summary = pd.read_excel(path, sheet_name="Symbol_Summary")
    batches = pd.read_excel(path, sheet_name="Batch_PnL")
    matched = int((batches["Status"] == "MATCHED").sum()) if not batches.empty else 0
    loss_n = int((batches["Status"] == "LOSS").sum()) if not batches.empty else 0
    print(f"Wrote {path}")
    print(
        f"  Symbols={len(summary)} | "
        f"PROFIT={(summary['Result']=='PROFIT').sum()} | "
        f"LOSS={(summary['Result']=='LOSS').sum()} | "
        f"OPEN={(summary['Result']=='OPEN').sum()} | "
        f"FIFO batches={matched} | "
        f"Unmatched sells as LOSS={loss_n}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
