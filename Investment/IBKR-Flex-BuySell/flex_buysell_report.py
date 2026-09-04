"""
Download IBKR Flex Query trades (or use a local Activity CSV), then build one Excel workbook
with all Buy/Sell stock trades since 2020 on separate sheets: All, Buys, Sells, summaries.

Setup:
  1. IBKR Client Portal → Performance & Reports → Flex Queries
     Create an Activity Flex Query including stock Buy/Sell (CSV output recommended).
  2. Flex Web Service → generate token; note query_id in config.ini
  3. pip install -r requirements.txt
  4. copy config.ini.example → config.ini

Usage:
  python flex_buysell_report.py --download
  python flex_buysell_report.py --input "..\\IBKR-Transaction\\U3831357.BUY_SELL....csv"
  python flex_buysell_report.py --discover
"""

from __future__ import annotations

import argparse
import configparser
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from flex_client import FlexServiceError, download_flex_report
from flex_cache_fill import fill_missing_windows_from_activity
from flex_skip_cache import (
    clear_window_skip,
    get_skipped_window,
    is_window_skipped,
    print_skip_summary,
    record_window_failure,
    seed_skip_window,
    skip_cache_path,
)
from flex_ytd import compare_ytd_trades, print_compare_result, sync_ytd, ytd_window_for_year
from flex_parse import (
    add_year_column,
    build_completely_sold_summary,
    build_still_holding_summary,
    filter_since_year,
    merge_trade_frames,
    ordered_columns,
    parse_activity_trades,
    parse_flex_file,
    summary_by_year,
)
from market_prices import enrich_completely_sold_with_market_prices

SCRIPT_DIR = Path(__file__).resolve().parent
INVESTMENT_ROOT = SCRIPT_DIR.parent
if str(INVESTMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(INVESTMENT_ROOT))

from shared.config_loader import flex_credentials, read_merged_ini  # noqa: E402

DEFAULT_CONFIG = SCRIPT_DIR / "config.ini"
IBKR_TRANSACTION_DIR = SCRIPT_DIR.parent / "IBKR-Transaction"


def _clean(value: str) -> str:
    out = value.strip()
    if len(out) >= 2 and out[0] == out[-1] and out[0] in "\"'":
        out = out[1:-1].strip()
    return out


def load_config(path: Path, *, required_for_download: bool = False) -> dict:
    base_dir = path.parent
    if not (path.is_file() or (base_dir / "secrets.local.ini").is_file()):
        if required_for_download:
            raise FileNotFoundError(
                f"Missing {path}. Copy config.ini.example to config.ini and "
                "secrets.local.ini.example to secrets.local.ini."
            )
    parser = read_merged_ini(base_dir)
    flex = parser["flex"] if parser.has_section("flex") else {}
    out_sec = parser["output"] if parser.has_section("output") else {}

    token, query_id = flex_credentials(parser)

    start_year = int(flex.get("start_year", "2020"))
    from_date = _clean(flex.get("from_date", "20200101") or "20200101")
    to_date = _clean(flex.get("to_date", "") or "")
    if not to_date:
        to_date = date.today().strftime("%Y%m%d")

    report = _clean(out_sec.get("report_path", "reports/IBKR_BuySell_Since_2020.xlsx"))
    report_path = Path(report)
    if not report_path.is_absolute():
        report_path = SCRIPT_DIR / report_path

    dl = _clean(out_sec.get("download_dir", "downloads"))
    download_dir = Path(dl)
    if not download_dir.is_absolute():
        download_dir = SCRIPT_DIR / download_dir

    return {
        "token": _clean(token),
        "query_id": _clean(query_id),
        "start_year": start_year,
        "from_date": from_date,
        "to_date": to_date,
        "base_url": _clean(
            flex.get(
                "base_url",
                "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService",
            )
        ),
        "poll_seconds": float(flex.get("poll_seconds", "10")),
        "max_poll_attempts": int(flex.get("max_poll_attempts", "36")),
        "user_agent": _clean(flex.get("user_agent", "Python/3.11 ibkr-flex-buysell")),
        "report_path": report_path,
        "download_dir": download_dir,
        "pause_between_windows": float(flex.get("pause_between_windows", "30")),
        "retries_per_window": int(flex.get("retries_per_window", "4")),
        "ytd_baseline": _clean(flex.get("ytd_baseline", "")),
    }


def _parse_yyyymmdd(s: str) -> date:
    return datetime.strptime(s, "%Y%m%d").date()


def iter_flex_date_windows(
    from_yyyymmdd: str,
    to_yyyymmdd: str,
    *,
    max_days: int = 365,
) -> list[tuple[str, str]]:
    """
    IBKR Flex SendRequest allows at most 366 days per request.
    History is chunked by max_days; the final calendar year uses a clean YTD window
    (Jan 1 → to_date), matching IBKR portal Year-to-Date exports.
    """
    start = _parse_yyyymmdd(from_yyyymmdd)
    end = _parse_yyyymmdd(to_yyyymmdd)
    to_year = end.year
    history_end = end
    if to_year > start.year:
        history_end = min(end, date(to_year - 1, 12, 31))

    windows: list[tuple[str, str]] = []
    cur = start
    while cur <= history_end:
        window_end = min(cur + timedelta(days=max_days - 1), history_end)
        windows.append((cur.strftime("%Y%m%d"), window_end.strftime("%Y%m%d")))
        cur = window_end + timedelta(days=1)

    ytd_start = date(to_year, 1, 1)
    if ytd_start <= end and (not windows or windows[-1][1] < ytd_start.strftime("%Y%m%d")):
        windows.append((ytd_start.strftime("%Y%m%d"), end.strftime("%Y%m%d")))
    return windows


def iter_flex_history_windows(
    from_yyyymmdd: str,
    to_yyyymmdd: str,
    *,
    max_days: int = 365,
) -> list[tuple[str, str]]:
    """History-only windows (excludes current calendar year YTD — handled by sync_ytd)."""
    all_windows = iter_flex_date_windows(from_yyyymmdd, to_yyyymmdd, max_days=max_days)
    to_year = _parse_yyyymmdd(to_yyyymmdd).year
    ytd_prefix = f"{to_year}0101"
    return [(fd, td) for fd, td in all_windows if fd < ytd_prefix]


def clean_raw_data_and_reports(
    cfg: dict,
    *,
    keep_skip_cache: bool = True,
    keep_manual_baseline: bool = True,
) -> None:
    """Remove cached Flex CSVs and Excel reports; preserve skip cache and manual baselines."""
    removed_csv = 0
    for path in cfg["download_dir"].glob("flex_*.csv"):
        try:
            path.unlink(missing_ok=True)
            removed_csv += 1
        except OSError as exc:
            print(f"Warning: could not delete {path.name}: {exc}", file=sys.stderr)
    removed_xlsx = 0
    report_dir = cfg["report_path"].parent
    if report_dir.is_dir():
        for path in report_dir.glob("*.xlsx"):
            try:
                path.unlink(missing_ok=True)
                removed_xlsx += 1
            except OSError as exc:
                print(f"Warning: could not delete {path.name}: {exc}", file=sys.stderr)
    print(f"Cleaned {removed_csv} flex cache CSV(s) and {removed_xlsx} report(s).", flush=True)
    if keep_skip_cache:
        sc = skip_cache_path(cfg["download_dir"])
        if sc.is_file():
            print(f"Kept skip cache: {sc.name}", flush=True)
    if keep_manual_baseline:
        for path in cfg["download_dir"].glob("manual_baseline_*_ytd.csv"):
            print(f"Kept manual baseline: {path.name}", flush=True)


def seed_known_unavailable_windows(cfg: dict) -> None:
    """Pre-seed windows known to fail on IBKR Flex API (avoids retry on clean download)."""
    sc = skip_cache_path(cfg["download_dir"])
    qid = cfg["query_id"]
    seed_skip_window(
        sc,
        qid,
        "20221231",
        "20231230",
        "Statement is not available (IBKR Flex gap for 2023 — use Activity CSV fill)",
        fail_count=4,
    )
    to_year = _parse_yyyymmdd(cfg["to_date"]).year
    fd, td = ytd_window_for_year(to_year, cfg["to_date"])
    seed_skip_window(
        sc,
        qid,
        fd,
        td,
        "Statement is not available (use YTD Activity export from IBKR portal)",
        fail_count=4,
    )
    print("Seeded known-unavailable Flex windows in skip cache.", flush=True)


def download_flex_trades_chunked(
    cfg: dict,
    *,
    force: bool = False,
) -> tuple[pd.DataFrame, str]:
    """Download Flex history windows (not current-year YTD). Respects skip cache."""
    windows = iter_flex_history_windows(cfg["from_date"], cfg["to_date"])
    skip_path = skip_cache_path(cfg["download_dir"])
    frames: list[pd.DataFrame] = []
    saved: list[str] = []
    pause_between = float(cfg.get("pause_between_windows", 30))
    retries_per_window = int(cfg.get("retries_per_window", 4))
    qid = cfg["query_id"]

    print_skip_summary(skip_path, qid)

    for i, (fd, td) in enumerate(windows, start=1):
        cache_path = cfg["download_dir"] / f"flex_{qid}_{fd}_{td}.csv"
        print(f"Flex window {i}/{len(windows)}: {fd} – {td} …", flush=True)

        if cache_path.is_file() and cache_path.stat().st_size > 50 and not force:
            print(f"  Using cached {cache_path.name}", flush=True)
            result_path = cache_path
        elif not force and is_window_skipped(skip_path, qid, fd, td):
            sk = get_skipped_window(skip_path, qid, fd, td)
            reason = sk.get("reason", "unavailable") if sk else "unavailable"
            print(f"  Skipping Flex API (recorded unavailable): {reason[:80]}", flush=True)
            continue
        else:
            last_err: Exception | None = None
            result_path = cache_path
            for attempt in range(1, retries_per_window + 1):
                try:
                    result = download_flex_report(
                        token=cfg["token"],
                        query_id=qid,
                        output_dir=cfg["download_dir"],
                        from_date=fd,
                        to_date=td,
                        base_url=cfg["base_url"],
                        poll_seconds=cfg["poll_seconds"],
                        max_poll_attempts=cfg["max_poll_attempts"],
                        user_agent=cfg["user_agent"],
                    )
                    result_path = result.raw_path
                    clear_window_skip(skip_path, qid, fd, td)
                    break
                except FlexServiceError as exc:
                    last_err = exc
                    wait = pause_between * attempt
                    print(f"  Attempt {attempt} failed: {exc}. Waiting {wait:.0f}s …", flush=True)
                    time.sleep(wait)
            else:
                record_window_failure(skip_path, qid, fd, td, str(last_err))
                print(
                    f"  Skipping window {fd}-{td} after {retries_per_window} attempts: {last_err}",
                    flush=True,
                )
                print(f"  Recorded in {skip_path.name} — will not retry Flex API unless --force-download",
                      flush=True)
                continue

        saved.append(result_path.name)
        chunk = parse_flex_file(result_path)
        if not chunk.empty:
            frames.append(chunk)
        if i < len(windows):
            time.sleep(pause_between)

    if not frames:
        print("No trades from Flex history windows (skipped/failed); continuing with activity fill.",
              flush=True)
        return pd.DataFrame(), "Flex download (no history frames)"

    merged = merge_trade_frames(frames)
    label = f"Flex download ({len(windows)} history windows): {', '.join(saved[:3])}" + (
        " …" if len(saved) > 3 else ""
    )
    return merged, label


def load_trades_from_downloads(download_dir: Path, query_id: str) -> pd.DataFrame:
    """Merge cached Flex window CSVs (no API call). Skips obsolete cross-year YTD caches."""
    pattern = f"flex_{query_id}_*_*.csv"
    files = sorted(download_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No cached Flex files matching {pattern} in {download_dir}")

    # Prefer clean Jan-1 YTD files over legacy Dec→year-end cross-year windows
    ytd_years = set()
    for p in files:
        parts = p.stem.split("_")
        if len(parts) >= 4 and parts[-2].endswith("0101"):
            try:
                ytd_years.add(int(parts[-2][:4]))
            except ValueError:
                pass
    skip: set[Path] = set()
    for p in files:
        parts = p.stem.split("_")
        if len(parts) < 4:
            continue
        try:
            w_from, w_to = int(parts[-2]), int(parts[-1])
        except ValueError:
            continue
        for y in ytd_years:
            if w_from < y * 10000 + 101 <= w_to and not parts[-2].endswith("0101"):
                skip.add(p)

    use = [p for p in files if p not in skip and p.stat().st_size > 50]
    frames = [parse_flex_file(p) for p in use]
    if not frames:
        raise ValueError("Cached Flex files are empty.")
    return merge_trade_frames(frames)


def load_trades_for_report(
    download_dir: Path,
    query_id: str,
) -> tuple[pd.DataFrame, str]:
    """Build report from Flex cache only (YTD synced into cache beforehand)."""
    trades = load_trades_from_downloads(download_dir, query_id)
    pattern = f"flex_{query_id}_*_*.csv"
    n = len(list(download_dir.glob(pattern)))
    return trades, f"Flex cache ({n} files, YTD-aware)"


def load_trades_combined(
    download_dir: Path,
    query_id: str,
    transactions_dir: Path,
) -> tuple[pd.DataFrame, str]:
    """
    Merge Flex cached windows + IBKR Activity TRANSACTIONS CSV.
    Fills gaps when Flex windows fail (e.g. 2023, 2026).
    """
    frames: list[pd.DataFrame] = []
    parts: list[str] = []

    pattern = f"flex_{query_id}_*_*.csv"
    flex_files = sorted(download_dir.glob(pattern))
    if flex_files:
        flex_frames = [parse_flex_file(p) for p in flex_files if p.stat().st_size > 50]
        if flex_frames:
            frames.extend(flex_frames)
            parts.append(f"Flex ({len(flex_files)} files)")

    activity_path = discover_latest_csv(transactions_dir)
    activity = load_all_activity_trades(transactions_dir)
    if not activity.empty:
        frames.append(activity)
        names = [p.name for p in discover_all_activity_csvs(transactions_dir)[:3]]
        parts.append(f"Activity CSV ({', '.join(names)}{'…' if len(names) > 3 else ''})")
    elif activity_path:
        one = parse_activity_trades(activity_path)
        if not one.empty:
            frames.append(one)
            parts.append(f"Activity CSV ({activity_path.name})")

    if not frames:
        raise FileNotFoundError(
            f"No trade data: no Flex files in {download_dir} and no TRANSACTIONS CSV under {transactions_dir}"
        )

    merged = merge_trade_frames(frames)
    label = " + ".join(parts) if parts else "merged"
    return merged, label


def discover_latest_csv(directory: Path) -> Path | None:
    candidates = discover_all_activity_csvs(directory)
    return candidates[0] if candidates else None


def _activity_end_date_from_name(name: str) -> int:
    """Parse end date from TRANSACTIONS.*.YYYYMMDD.csv or U*_YYYYMMDD_YYYYMMDD.csv."""
    import re

    m = re.search(r"\.(\d{8})\.csv$", name, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"_(\d{8})_(\d{8})\.csv$", name, re.I)
    if m:
        return int(m.group(2))
    m = re.search(r"_(\d{8})\.csv$", name, re.I)
    if m:
        return int(m.group(1))
    return 0


def discover_all_activity_csvs(directory: Path) -> list[Path]:
    """All Activity / BUY_SELL / Activity-Statement exports (newest end-date first)."""
    candidates: list[Path] = []
    for pattern in (
        "*.BUY_SELL*.csv",
        "*.TRANSACTIONS*.csv",
        "supplemental*.csv",
        "U*_*.csv",  # e.g. U3831357_20260101_20260805.csv Activity Statement
    ):
        candidates.extend(directory.rglob(pattern))

    # Keep only plausible trade/activity files (skip xlsx companions already excluded)
    filtered: list[Path] = []
    for p in candidates:
        if not p.name.lower().endswith(".csv"):
            continue
        # Skip known non-trade siblings if matched by U*_*.csv
        upper = p.name.upper()
        if any(
            x in upper
            for x in (
                ".DIVIDEND.",
                ".DEPOSIT_",
                ".OTHERCHARGES.",
                ".CREDIT_DEBIT",
            )
        ):
            continue
        filtered.append(p)

    return sorted(
        set(filtered),
        key=lambda p: (_activity_end_date_from_name(p.name), p.stat().st_mtime),
        reverse=True,
    )


def load_all_activity_trades(transactions_dir: Path) -> pd.DataFrame:
    """Merge every Activity / BUY_SELL / supplemental CSV found."""
    paths = discover_all_activity_csvs(transactions_dir)
    frames: list[pd.DataFrame] = []
    for path in paths:
        try:
            df = parse_activity_trades(path)
            if not df.empty:
                frames.append(df)
        except (ValueError, OSError) as exc:
            print(f"Warning: skip {path.name}: {exc}", file=sys.stderr)
    return merge_trade_frames(frames) if frames else pd.DataFrame()


def write_report(
    trades: pd.DataFrame,
    output: Path,
    *,
    source_label: str,
    start_year: int,
    fetch_market_prices: bool = True,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    trades = add_year_column(trades)
    cols = ordered_columns(trades)
    trades = trades[cols] if cols else trades

    tt = trades["Transaction Type"].astype(str).str.strip()
    buys = trades[tt == "Buy"].copy()
    sells = trades[tt == "Sell"].copy()
    summary = summary_by_year(trades)
    # Corporate-aware Completely_Sold (cash mergers / splits) when Activity data exists
    try:
        from trade_history.corporate_parse import load_corporate_from_transactions_dir
        from trade_history.symbol_pnl import (
            build_symbol_pnl,
            completely_sold_from_symbol_pnl,
            still_holding_from_symbol_pnl,
        )

        corp = load_corporate_from_transactions_dir(IBKR_TRANSACTION_DIR)
        symbol_pnl = build_symbol_pnl(trades, corp, fetch_marks=False)
        closed = completely_sold_from_symbol_pnl(symbol_pnl, trades)
        still_holding = still_holding_from_symbol_pnl(symbol_pnl)
        if closed.empty:
            closed = build_completely_sold_summary(trades)
        if still_holding.empty:
            still_holding = build_still_holding_summary(trades)
    except Exception as exc:
        print(f"Warning: corporate-aware P&L skipped ({exc}); using trade-only.", file=sys.stderr)
        closed = build_completely_sold_summary(trades)
        still_holding = build_still_holding_summary(trades)
    activity_paths = discover_all_activity_csvs(IBKR_TRANSACTION_DIR)
    activity_end = ""
    activity_file = ""
    if activity_paths:
        import re

        newest = activity_paths[0]
        activity_file = newest.name
        end_int = _activity_end_date_from_name(newest.name)
        if end_int:
            d = f"{end_int:08d}"
            activity_end = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    if fetch_market_prices and not closed.empty:
        try:
            closed = enrich_completely_sold_with_market_prices(closed)
        except ImportError as exc:
            print(f"Warning: {exc}. Completely_Sold without live prices.", file=sys.stderr)

    meta = pd.DataFrame(
        [
            {"Field": "Source", "Value": source_label},
            {"Field": "Start year filter", "Value": str(start_year)},
            {"Field": "Total trades", "Value": str(len(trades))},
            {"Field": "Buy rows", "Value": str(len(buys))},
            {"Field": "Sell rows", "Value": str(len(sells))},
            {"Field": "Completely sold symbols", "Value": str(len(closed))},
            {"Field": "Still holding (net qty ≠ 0)", "Value": str(len(still_holding))},
            {
                "Field": "Activity export end (from filename)",
                "Value": activity_end or "unknown",
            },
            {
                "Field": "Activity export file (newest)",
                "Value": activity_file or "none found under IBKR-Transaction",
            },
            {
                "Field": "Data note",
                "Value": (
                    "Activity export end is parsed from the newest TRANSACTIONS/BUY_SELL "
                    "filename (...YYYYMMDD.csv), not hardcoded. Export a newer file from "
                    "IBKR portal to extend coverage; sells after that date may be missing."
                ),
            },
            {
                "Field": "Date range",
                "Value": (
                    f"{trades['Date'].min()} – {trades['Date'].max()}"
                    if not trades.empty and "Date" in trades.columns
                    else "n/a"
                ),
            },
        ]
    )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        meta.to_excel(writer, sheet_name="Report_Info", index=False)
        trades.to_excel(writer, sheet_name="All_Buy_Sell", index=False)
        buys.to_excel(writer, sheet_name="Buys", index=False)
        sells.to_excel(writer, sheet_name="Sells", index=False)
        closed.to_excel(writer, sheet_name="Completely_Sold", index=False)
        if not still_holding.empty:
            still_holding.to_excel(writer, sheet_name="Still_Holding", index=False)
        if not summary.empty:
            summary.to_excel(writer, sheet_name="Summary_By_Year", index=False)

    print(f"Wrote {output}")
    print(
        f"  All_Buy_Sell: {len(trades)} rows | Buys: {len(buys)} | Sells: {len(sells)} | "
        f"Completely sold: {len(closed)} symbols"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="IBKR Flex Buy/Sell → Excel report since 2020")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument(
        "--download",
        action="store_true",
        help="Download via Flex Web Service (requires token + query_id in config.ini)",
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Use existing IBKR Activity / BUY_SELL CSV instead of downloading",
    )
    ap.add_argument(
        "--discover",
        action="store_true",
        help=f"Use newest BUY_SELL/TRANSACTIONS CSV under {IBKR_TRANSACTION_DIR}",
    )
    ap.add_argument(
        "--from-downloads",
        action="store_true",
        help="Rebuild from cached Flex CSVs + Activity TRANSACTIONS CSV (no API call)",
    )
    ap.add_argument(
        "--fill-missing-from-activity",
        action="store_true",
        help="After Flex download (or alone), write missing window CSVs from Activity TRANSACTIONS export",
    )
    ap.add_argument(
        "--sync-ytd",
        action="store_true",
        help="Sync current-year YTD into Flex cache from API (if available) or Latest Activity export",
    )
    ap.add_argument(
        "--compare-baseline",
        type=Path,
        default=None,
        help="Compare auto YTD trades with a manual baseline Flex/Activity CSV (2026 rows only)",
    )
    ap.add_argument(
        "--clean-all",
        action="store_true",
        help="Delete all flex_*.csv caches and reports/*.xlsx (keeps skip cache + manual baselines)",
    )
    ap.add_argument(
        "--force-download",
        action="store_true",
        help="Ignore skip cache and re-attempt Flex API for all windows",
    )
    ap.add_argument(
        "--list-skipped",
        action="store_true",
        help="Print Flex windows recorded as unavailable in skip cache",
    )
    ap.add_argument(
        "--clear-skip-cache",
        action="store_true",
        help="Remove flex_unavailable_windows.json (Flex API will retry all windows)",
    )
    ap.add_argument(
        "--no-market-prices",
        action="store_true",
        help="Skip Yahoo Finance lookup for Current_Market_Price on Completely_Sold",
    )
    ap.add_argument("--output", type=Path, default=None, help="Override output .xlsx path")
    ap.add_argument("--start-year", type=int, default=None, help="Override start year (default 2020)")
    ap.add_argument(
        "--to-date",
        default=None,
        help="Override Flex/YTD end date as YYYYMMDD or YYYY-MM-DD (default: config.ini to_date, else today)",
    )
    args = ap.parse_args()

    cfg = load_config(args.config, required_for_download=args.download)
    if args.to_date:
        cfg["to_date"] = str(args.to_date).replace("-", "").strip()
    start_year = args.start_year if args.start_year is not None else cfg["start_year"]
    output = args.output.resolve() if args.output else cfg["report_path"].resolve()
    fetch_prices = not args.no_market_prices

    if args.clear_skip_cache:
        sc = skip_cache_path(cfg["download_dir"])
        sc.unlink(missing_ok=True)
        print(f"Removed skip cache: {sc}", flush=True)
        if not args.download and not args.from_downloads and not args.list_skipped:
            return 0

    if args.list_skipped:
        print_skip_summary(skip_cache_path(cfg["download_dir"]), cfg["query_id"])
        if not args.download and not args.from_downloads and not args.clean_all:
            return 0

    if args.clean_all:
        clean_raw_data_and_reports(cfg)
        seed_known_unavailable_windows(cfg)
        if not args.download and not args.from_downloads and not args.sync_ytd:
            return 0

    source_path: Path | None = None
    source_label = ""

    def _fill_activity_gaps() -> None:
        activity_path = discover_latest_csv(IBKR_TRANSACTION_DIR)
        if not activity_path:
            print("No Activity TRANSACTIONS CSV for gap fill.", file=sys.stderr)
            return
        windows = iter_flex_date_windows(cfg["from_date"], cfg["to_date"])
        print("Filling missing Flex windows from Activity CSV …", flush=True)
        fill_missing_windows_from_activity(
            activity_path=activity_path,
            download_dir=cfg["download_dir"],
            query_id=cfg["query_id"],
            windows=windows,
            overwrite_from_yyyymmdd=f"{_parse_yyyymmdd(cfg['to_date']).year}0101",
        )

    def _sync_ytd_step(*, try_flex: bool = True, force_flex: bool = False) -> None:
        activity_path = discover_latest_csv(IBKR_TRANSACTION_DIR)
        y = _parse_yyyymmdd(cfg["to_date"]).year
        sync_ytd(
            cfg,
            activity_path,
            year=y,
            try_flex=try_flex and bool(cfg["token"]),
            force_flex=force_flex,
        )

    def _compare_ytd_baseline(baseline: Path | None) -> None:
        path = baseline
        if path is None and cfg.get("ytd_baseline"):
            path = Path(cfg["ytd_baseline"])
            if not path.is_absolute():
                path = SCRIPT_DIR / path
        if path is None:
            default = SCRIPT_DIR / "downloads" / f"manual_baseline_{_parse_yyyymmdd(cfg['to_date']).year}_ytd.csv"
            if default.is_file():
                path = default
        if path is None or not path.is_file():
            return
        y = _parse_yyyymmdd(cfg["to_date"]).year
        fd, td = ytd_window_for_year(y, cfg["to_date"])
        ytd_cache = cfg["download_dir"] / f"flex_{cfg['query_id']}_{fd}_{td}.csv"
        if not ytd_cache.is_file():
            print(f"No YTD cache to compare: {ytd_cache.name}", file=sys.stderr)
            return
        manual = parse_flex_file(path) if "flex_" in path.name else parse_activity_trades(path)
        auto = parse_flex_file(ytd_cache)
        print(f"Compare baseline: {path.name} vs {ytd_cache.name}", flush=True)
        print_compare_result(compare_ytd_trades(manual, auto, year=y))

    if args.sync_ytd and not args.download and not args.from_downloads and not args.fill_missing_from_activity:
        _sync_ytd_step(try_flex=True, force_flex=args.force_download)
        if args.compare_baseline or cfg.get("ytd_baseline"):
            _compare_ytd_baseline(args.compare_baseline)
        try:
            trades_merged, source_label = load_trades_for_report(cfg["download_dir"], cfg["query_id"])
        except (FileNotFoundError, ValueError) as exc:
            print(exc, file=sys.stderr)
            return 1
        trades_merged = filter_since_year(trades_merged, start_year)
        if trades_merged.empty:
            print("No trades after YTD sync.", file=sys.stderr)
            return 1
        write_report(
            trades_merged,
            output,
            source_label=f"{source_label} (YTD sync)",
            start_year=start_year,
            fetch_market_prices=fetch_prices,
        )
        return 0

    if args.fill_missing_from_activity and not args.download:
        _fill_activity_gaps()
        _sync_ytd_step(try_flex=False, force_flex=False)
        if args.compare_baseline or cfg.get("ytd_baseline"):
            _compare_ytd_baseline(args.compare_baseline)
        trades_merged, source_label = load_trades_for_report(
            cfg["download_dir"], cfg["query_id"]
        )
        trades_merged = filter_since_year(trades_merged, start_year)
        if trades_merged.empty:
            print("No trades after gap fill.", file=sys.stderr)
            return 1
        write_report(
            trades_merged,
            output,
            source_label=f"{source_label} (activity gap fill)",
            start_year=start_year,
            fetch_market_prices=fetch_prices,
        )
        return 0

    if args.download:
        if not cfg["token"] or not cfg["query_id"]:
            print(
                "Set [flex] token and query_id in config.ini for --download.",
                file=sys.stderr,
            )
            return 1
        try:
            download_flex_trades_chunked(cfg, force=args.force_download)
            _fill_activity_gaps()
            _sync_ytd_step(try_flex=True, force_flex=args.force_download)
            if args.compare_baseline or cfg.get("ytd_baseline"):
                _compare_ytd_baseline(args.compare_baseline)
            trades_merged, merge_label = load_trades_for_report(
                cfg["download_dir"], cfg["query_id"]
            )
            source_label = f"Flex+YTD; {merge_label}"
            trades_merged = filter_since_year(trades_merged, start_year)
            if trades_merged.empty:
                print(f"No Buy/Sell trades on or after {start_year}-01-01.", file=sys.stderr)
                return 1
            write_report(
                trades_merged,
                output,
                source_label=source_label,
                start_year=start_year,
                fetch_market_prices=fetch_prices,
            )
            return 0
        except FlexServiceError as exc:
            print(f"Flex download failed: {exc}", file=sys.stderr)
            return 1

    elif args.from_downloads:
        _fill_activity_gaps()
        _sync_ytd_step(try_flex=False, force_flex=False)
        if args.compare_baseline or cfg.get("ytd_baseline"):
            _compare_ytd_baseline(args.compare_baseline)
        try:
            trades_merged, source_label = load_trades_for_report(
                cfg["download_dir"], cfg["query_id"]
            )
        except (FileNotFoundError, ValueError) as exc:
            print(exc, file=sys.stderr)
            return 1
        trades_merged = filter_since_year(trades_merged, start_year)
        if trades_merged.empty:
            print(f"No trades on or after {start_year}-01-01 in cached downloads.", file=sys.stderr)
            return 1
        write_report(
            trades_merged,
            output,
            source_label=source_label,
            start_year=start_year,
            fetch_market_prices=fetch_prices,
        )
        return 0

    elif args.input:
        source_path = args.input.resolve()
        if not source_path.is_file():
            print(f"Input not found: {source_path}", file=sys.stderr)
            return 1
        source_label = str(source_path)

    else:
        found = discover_latest_csv(IBKR_TRANSACTION_DIR)
        if found:
            source_path = found
            source_label = str(found)
            print(f"Using discovered CSV: {found}")
        elif args.discover:
            print(f"No BUY_SELL/TRANSACTIONS CSV under {IBKR_TRANSACTION_DIR}", file=sys.stderr)
            return 1

    if source_path is None:
        print(
            "Provide --download (with config.ini), --input PATH, or place CSV under IBKR-Transaction.",
            file=sys.stderr,
        )
        return 1

    trades = parse_flex_file(source_path)
    trades = filter_since_year(trades, start_year)
    if trades.empty:
        print(f"No Buy/Sell trades on or after {start_year}-01-01 in {source_path}", file=sys.stderr)
        return 1

    write_report(
        trades,
        output,
        source_label=source_label,
        start_year=start_year,
        fetch_market_prices=fetch_prices,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
