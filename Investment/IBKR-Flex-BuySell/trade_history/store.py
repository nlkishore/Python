"""CSV store for trades and corporate actions with dedupe merge."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from flex_parse import merge_trade_frames


TRADES_FILE = "trades.csv"
CORPORATE_FILE = "corporate_actions.csv"


def trades_path(store_dir: Path) -> Path:
    return store_dir / TRADES_FILE


def corporate_path(store_dir: Path) -> Path:
    return store_dir / CORPORATE_FILE


def load_trades(store_dir: Path) -> pd.DataFrame:
    path = trades_path(store_dir)
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def save_trades(store_dir: Path, trades: pd.DataFrame) -> Path:
    store_dir.mkdir(parents=True, exist_ok=True)
    path = trades_path(store_dir)
    out = trades.copy()
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def merge_trades(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    return merge_trade_frames([existing, incoming])


def load_corporate(store_dir: Path) -> pd.DataFrame:
    path = corporate_path(store_dir)
    if not path.is_file():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def save_corporate(store_dir: Path, corp: pd.DataFrame) -> Path:
    store_dir.mkdir(parents=True, exist_ok=True)
    path = corporate_path(store_dir)
    out = corp.copy()
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def merge_corporate(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    frames = [f for f in (existing, incoming) if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    if "Date" in merged.columns:
        merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")

    def _key(row: pd.Series) -> tuple:
        dt = row.get("Date")
        day = pd.Timestamp(dt).normalize() if pd.notna(dt) else pd.NaT
        # Omit Amount so USD vs base-currency copies of the same dividend collapse.
        # Keep description prefix + action type + symbol + date.
        return (
            str(day.date()) if pd.notna(day) else "",
            str(row.get("Symbol", "")).strip().upper(),
            str(row.get("ActionType", "")).strip().upper(),
            str(row.get("Description", ""))[:80],
        )

    def _prefer(row: pd.Series) -> float:
        # Prefer non-zero amount rows; prefer activity_statement / newer source lightly
        amt = pd.to_numeric(row.get("Amount"), errors="coerce")
        score = abs(float(amt)) if pd.notna(amt) else 0.0
        src = str(row.get("Source", "") or "")
        if src == "activity_statement":
            score += 0.0001
        return score

    merged["_dedupe"] = merged.apply(_key, axis=1)
    merged["_prefer"] = merged.apply(_prefer, axis=1)
    merged = merged.sort_values("_prefer", ascending=False, kind="mergesort")
    merged = merged.drop_duplicates(subset=["_dedupe"], keep="first")
    merged = merged.drop(columns=["_dedupe", "_prefer"])
    return merged.sort_values(["Date", "Symbol"], na_position="last").reset_index(drop=True)


def max_date_iso(trades: pd.DataFrame, corp: pd.DataFrame) -> str | None:
    dates: list[pd.Timestamp] = []
    for df in (trades, corp):
        if df is not None and not df.empty and "Date" in df.columns:
            series = pd.to_datetime(df["Date"], errors="coerce").dropna()
            if not series.empty:
                dates.append(series.max())
    if not dates:
        return None
    return max(dates).date().isoformat()
