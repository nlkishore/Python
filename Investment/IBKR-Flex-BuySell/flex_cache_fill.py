"""Build Flex-format raw cache CSVs from IBKR Activity export when Flex API windows fail."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from flex_parse import parse_activity_trades


def _to_tradedate(d) -> str:
    ts = pd.Timestamp(d)
    if pd.isna(ts):
        return ""
    return ts.strftime("%Y%m%d")


def trades_to_flex_trades_csv(trades: pd.DataFrame) -> pd.DataFrame:
    """Convert normalized Buy/Sell frame to IBKR Flex Trades CSV columns."""
    rows: list[dict] = []
    for _, r in trades.iterrows():
        side = str(r.get("Transaction Type", "")).strip()
        if side == "Buy":
            bs = "BUY"
        elif side == "Sell":
            bs = "SELL"
        else:
            continue

        qty = pd.to_numeric(r.get("Quantity"), errors="coerce")
        if pd.isna(qty):
            continue
        qty_f = float(qty)
        if bs == "SELL" and qty_f > 0:
            qty_f = -qty_f
        elif bs == "BUY":
            qty_f = abs(qty_f)

        price = pd.to_numeric(r.get("Price"), errors="coerce")
        comm = pd.to_numeric(r.get("Commission"), errors="coerce")

        rows.append(
            {
                "AssetClass": "STK",
                "Symbol": str(r.get("Symbol", "")).strip().upper(),
                "TradeDate": _to_tradedate(r.get("Date")),
                "Quantity": qty_f,
                "TradePrice": float(price) if pd.notna(price) else "",
                "IBCommission": float(comm) if pd.notna(comm) else "",
                "Buy/Sell": bs,
            }
        )
    return pd.DataFrame(rows)


def export_activity_window_to_flex_cache(
    activity_path: Path,
    *,
    from_yyyymmdd: str,
    to_yyyymmdd: str,
    output_path: Path,
) -> int:
    """Filter Activity CSV to date window; write Flex Trades CSV. Returns row count."""
    start = pd.Timestamp(datetime.strptime(from_yyyymmdd, "%Y%m%d").date())
    end = pd.Timestamp(datetime.strptime(to_yyyymmdd, "%Y%m%d").date())

    trades = parse_activity_trades(activity_path)
    trades["Date"] = pd.to_datetime(trades["Date"], errors="coerce")
    sub = trades.loc[(trades["Date"] >= start) & (trades["Date"] <= end)].copy()
    flex_df = trades_to_flex_trades_csv(sub)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    flex_df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    return len(flex_df)


def fill_missing_windows_from_activity(
    *,
    activity_path: Path,
    download_dir: Path,
    query_id: str,
    windows: list[tuple[str, str]],
    overwrite: bool = False,
    overwrite_from_yyyymmdd: str | None = None,
) -> list[Path]:
    """Create flex_{queryId}_{from}_{to}.csv for missing (or empty) windows."""
    written: list[Path] = []
    cutoff = overwrite_from_yyyymmdd or ""
    for fd, td in windows:
        cache_path = download_dir / f"flex_{query_id}_{fd}_{td}.csv"
        force = overwrite or (cutoff and fd >= cutoff)
        if cache_path.is_file() and cache_path.stat().st_size > 50 and not force:
            continue
        n = export_activity_window_to_flex_cache(
            activity_path,
            from_yyyymmdd=fd,
            to_yyyymmdd=td,
            output_path=cache_path,
        )
        if n > 0:
            print(f"  Activity fill: {cache_path.name} ({n} trades)", flush=True)
            written.append(cache_path)
        elif cache_path.is_file():
            cache_path.unlink(missing_ok=True)
    return written
