"""Year-to-date (YTD) trade sync from IBKR Activity export + compare with manual baseline."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from flex_cache_fill import export_activity_window_to_flex_cache
from flex_client import FlexServiceError, download_flex_report
from flex_parse import merge_trade_frames, parse_flex_file
from flex_skip_cache import (
    clear_window_skip,
    get_skipped_window,
    is_window_skipped,
    record_window_failure,
    skip_cache_path,
)


def ytd_window_for_year(year: int, to_yyyymmdd: str) -> tuple[str, str]:
    """Calendar YTD window: Jan 1 through config to_date (matches IBKR portal Year-to-Date)."""
    end = datetime.strptime(to_yyyymmdd, "%Y%m%d").date()
    ytd_start = date(year, 1, 1)
    if end < ytd_start:
        raise ValueError(f"to_date {to_yyyymmdd} is before YTD start for {year}")
    return ytd_start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def ytd_cache_path(download_dir: Path, query_id: str, year: int, to_yyyymmdd: str) -> Path:
    fd, td = ytd_window_for_year(year, to_yyyymmdd)
    return download_dir / f"flex_{query_id}_{fd}_{td}.csv"


def trade_row_key(row: pd.Series) -> tuple:
    """Comparable key for merge dedupe (keeps split fills with different net amounts)."""
    dt = pd.Timestamp(row.get("Date"))
    day = dt.normalize() if pd.notna(dt) else pd.NaT
    qty = pd.to_numeric(row.get("Quantity"), errors="coerce")
    price = pd.to_numeric(row.get("Price"), errors="coerce")
    net = pd.to_numeric(row.get("Net Amount"), errors="coerce")
    return (
        str(day.date()) if pd.notna(day) else "",
        str(row.get("Symbol", "")).strip().upper(),
        str(row.get("Transaction Type", "")).strip(),
        round(abs(float(qty)), 6) if pd.notna(qty) else 0.0,
        round(float(price), 4) if pd.notna(price) else 0.0,
        round(float(net), 4) if pd.notna(net) else 0.0,
    )


def compare_trade_key(row: pd.Series) -> tuple:
    """Looser key for YTD manual vs auto diff (ignores commission/net rounding)."""
    dt = pd.Timestamp(row.get("Date"))
    day = dt.normalize() if pd.notna(dt) else pd.NaT
    qty = pd.to_numeric(row.get("Quantity"), errors="coerce")
    price = pd.to_numeric(row.get("Price"), errors="coerce")
    return (
        str(day.date()) if pd.notna(day) else "",
        str(row.get("Symbol", "")).strip().upper(),
        str(row.get("Transaction Type", "")).strip(),
        round(abs(float(qty)), 6) if pd.notna(qty) else 0.0,
        round(float(price), 4) if pd.notna(price) else 0.0,
    )


def trades_to_key_set(trades: pd.DataFrame, *, for_compare: bool = False) -> set[tuple]:
    if trades.empty:
        return set()
    t = trades.copy()
    t["Date"] = pd.to_datetime(t["Date"], errors="coerce")
    fn = compare_trade_key if for_compare else trade_row_key
    return {fn(r) for _, r in t.iterrows()}


@dataclass
class YtdCompareResult:
    year: int
    manual_count: int
    auto_count: int
    matched: int
    only_manual: int
    only_auto: int
    only_manual_rows: pd.DataFrame
    only_auto_rows: pd.DataFrame


def compare_ytd_trades(
    manual: pd.DataFrame,
    auto: pd.DataFrame,
    *,
    year: int,
) -> YtdCompareResult:
    """Compare two normalized trade frames for one calendar year."""
    manual = manual.copy()
    auto = auto.copy()
    manual["Date"] = pd.to_datetime(manual["Date"], errors="coerce")
    auto["Date"] = pd.to_datetime(auto["Date"], errors="coerce")
    manual = manual.loc[manual["Date"].dt.year == year].copy()
    auto = auto.loc[auto["Date"].dt.year == year].copy()

    manual_keys = trades_to_key_set(manual, for_compare=True)
    auto_keys = trades_to_key_set(auto, for_compare=True)
    matched = manual_keys & auto_keys
    only_m = manual_keys - auto_keys
    only_a = auto_keys - manual_keys

    def _rows(df: pd.DataFrame, keys: set[tuple]) -> pd.DataFrame:
        if not keys:
            return pd.DataFrame()
        keyed = df.copy()
        keyed["_key"] = keyed.apply(compare_trade_key, axis=1)
        return keyed.loc[keyed["_key"].isin(keys)].drop(columns=["_key"])

    return YtdCompareResult(
        year=year,
        manual_count=len(manual),
        auto_count=len(auto),
        matched=len(matched),
        only_manual=len(only_m),
        only_auto=len(only_a),
        only_manual_rows=_rows(manual, only_m),
        only_auto_rows=_rows(auto, only_a),
    )


def print_compare_result(result: YtdCompareResult) -> None:
    print(f"\nYTD {result.year} compare:", flush=True)
    print(f"  Manual trades: {result.manual_count}", flush=True)
    print(f"  Auto trades:   {result.auto_count}", flush=True)
    print(f"  Matched:       {result.matched}", flush=True)
    print(f"  Only manual:   {result.only_manual}", flush=True)
    print(f"  Only auto:     {result.only_auto}", flush=True)
    if result.only_manual and not result.only_manual_rows.empty:
        print("  Missing from auto (in manual only):", flush=True)
        for _, r in result.only_manual_rows.iterrows():
            print(
                f"    {r['Date'].date()} {r['Symbol']} {r['Transaction Type']} "
                f"qty={r['Quantity']} @ {r['Price']}",
                flush=True,
            )
    if result.only_auto and not result.only_auto_rows.empty:
        print("  Extra in auto (not in manual):", flush=True)
        for _, r in result.only_auto_rows.iterrows():
            print(
                f"    {r['Date'].date()} {r['Symbol']} {r['Transaction Type']} "
                f"qty={r['Quantity']} @ {r['Price']}",
                flush=True,
            )
    if result.matched == result.manual_count == result.auto_count and result.manual_count > 0:
        print("  ✓ YTD datasets match.", flush=True)


def remove_obsolete_cross_year_ytd(
    download_dir: Path,
    query_id: str,
    year: int,
    *,
    keep: set[Path] | None = None,
) -> list[Path]:
    """Remove old Dec→May cross-year cache when clean Jan-1 YTD file exists."""
    ytd_files = list(download_dir.glob(f"flex_{query_id}_{year}0101_*.csv"))
    if not ytd_files:
        return []
    protected = {p.resolve() for p in (keep or set())}
    protected.add(download_dir.resolve() / f"manual_baseline_{year}_ytd.csv")
    removed: list[Path] = []
    for path in download_dir.glob(f"flex_{query_id}_*_*.csv"):
        name = path.stem
        parts = name.split("_")
        if len(parts) < 4:
            continue
        try:
            w_from = int(parts[-2])
            w_to = int(parts[-1])
        except ValueError:
            continue
        # Cross-year window ending in target year but starting before Jan 1
        if w_from < year * 10000 + 101 and w_to >= year * 10000 + 101 and path not in ytd_files:
            if path.resolve() in protected:
                continue
            path.unlink(missing_ok=True)
            removed.append(path)
    return removed


def download_ytd_flex(
    cfg: dict,
    *,
    year: int | None = None,
    force: bool = False,
    skip_path: Path | None = None,
) -> Path | None:
    """Try Flex API for calendar YTD window (Jan 1 → to_date). Returns path or None."""
    to_date = cfg["to_date"]
    y = year or datetime.strptime(to_date, "%Y%m%d").date().year
    fd, td = ytd_window_for_year(y, to_date)
    cache_path = cfg["download_dir"] / f"flex_{cfg['query_id']}_{fd}_{td}.csv"
    qid = cfg["query_id"]
    sc = skip_path or skip_cache_path(cfg["download_dir"])

    if cache_path.is_file() and cache_path.stat().st_size > 50 and not force:
        print(f"  YTD Flex cache exists: {cache_path.name}", flush=True)
        return cache_path

    if not force and is_window_skipped(sc, qid, fd, td):
        sk = get_skipped_window(sc, qid, fd, td)
        reason = sk.get("reason", "unavailable") if sk else "unavailable"
        print(f"  Skipping YTD Flex API (recorded unavailable): {reason[:80]}", flush=True)
        return None

    print(f"  Flex YTD download {fd} – {td} …", flush=True)
    try:
        result = download_flex_report(
            token=cfg["token"],
            query_id=cfg["query_id"],
            output_dir=cfg["download_dir"],
            from_date=fd,
            to_date=td,
            base_url=cfg["base_url"],
            poll_seconds=cfg["poll_seconds"],
            max_poll_attempts=cfg["max_poll_attempts"],
            user_agent=cfg["user_agent"],
        )
        clear_window_skip(sc, qid, fd, td)
        return result.raw_path
    except FlexServiceError as exc:
        record_window_failure(sc, qid, fd, td, str(exc))
        print(f"  Flex YTD failed (recorded in skip cache): {exc}", flush=True)
        return None


def sync_ytd_from_activity(
    cfg: dict,
    activity_path: Path,
    *,
    year: int | None = None,
    force: bool = True,
) -> Path:
    """
    Import IBKR Activity TRANSACTIONS (portal Year-to-Date export) into Flex cache.
    Drop into IBKR-Transaction\\Latest\\ — newest file is used automatically.
    """
    to_date = cfg["to_date"]
    y = year or datetime.strptime(to_date, "%Y%m%d").date().year
    fd, td = ytd_window_for_year(y, to_date)
    cache_path = cfg["download_dir"] / f"flex_{cfg['query_id']}_{fd}_{td}.csv"
    if cache_path.is_file() and cache_path.stat().st_size > 50 and not force:
        print(f"  YTD activity cache exists: {cache_path.name}", flush=True)
        return cache_path

    n = export_activity_window_to_flex_cache(
        activity_path,
        from_yyyymmdd=fd,
        to_yyyymmdd=td,
        output_path=cache_path,
    )
    print(
        f"  YTD activity import: {cache_path.name} ({n} trades from {activity_path.name})",
        flush=True,
    )
    removed = remove_obsolete_cross_year_ytd(cfg["download_dir"], cfg["query_id"], y)
    for p in removed:
        print(f"  Removed obsolete cross-year cache: {p.name}", flush=True)
    return cache_path


def sync_ytd(
    cfg: dict,
    activity_path: Path | None,
    *,
    year: int | None = None,
    try_flex: bool = True,
    force_activity: bool = True,
    force_flex: bool = False,
) -> Path | None:
    """Try Flex YTD API, then Activity YTD import. Returns YTD cache path."""
    to_date = cfg["to_date"]
    y = year or datetime.strptime(to_date, "%Y%m%d").date().year
    fd, td = ytd_window_for_year(y, to_date)
    print(f"Sync YTD {y} ({fd} – {td}) …", flush=True)

    path: Path | None = None
    if try_flex and cfg.get("token") and cfg.get("query_id"):
        path = download_ytd_flex(cfg, year=y, force=force_flex)

    if path is None or (path.is_file() and path.stat().st_size <= 50):
        if not activity_path or not activity_path.is_file():
            print("  No Activity TRANSACTIONS CSV for YTD fallback.", flush=True)
            return path
        path = sync_ytd_from_activity(cfg, activity_path, year=y, force=force_activity)

    remove_obsolete_cross_year_ytd(cfg["download_dir"], cfg["query_id"], y)
    return path


def load_ytd_trades(cache_path: Path, year: int) -> pd.DataFrame:
    trades = parse_flex_file(cache_path)
    trades["Date"] = pd.to_datetime(trades["Date"], errors="coerce")
    return trades.loc[trades["Date"].dt.year == year].copy()
