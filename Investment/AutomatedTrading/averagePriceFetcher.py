import configparser
import csv
import sys
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import yfinance as yf

INVESTMENT_ROOT = Path(__file__).resolve().parent.parent
if str(INVESTMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(INVESTMENT_ROOT))

from shared.config_loader import read_merged_ini  # noqa: E402

from indicators import targets_ok

EMA_SPAN = 52

_BASE_DIR = Path(__file__).resolve().parent
_DEFAULT_CONFIG = _BASE_DIR / "config.ini"

# CSV columns (spelling matches requested headers)
CSV_FIELDNAMES: tuple[str, ...] = (
    "Symbol",
    "Period Used",
    "Bars Loaded",
    "Meet Recommended bar count",
    "Recommended Mn Bars",
    "Current Price",
    "Referance price (52 EMA)",
    "Buy Traget (-5%)",
    "Sell Traget (+7%)",
    "Distance to Buy",
)

# Shorter-first: use the smallest window that still has enough bars for a stable EMA.
_YF_PERIODS: tuple[str, ...] = ("100d", "6mo", "1y", "2y", "max")


def recommended_min_bars(ema_span: int = EMA_SPAN) -> int:
    """Rough warm-up rule: ~3x span bars so the tail EMA is not dominated by initialization."""
    return max(ema_span * 3, ema_span)


def load_price_history_for_ema(
    ticker_symbol: str, ema_span: int = EMA_SPAN
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Pick a Yahoo Finance `period` that yields enough rows for EMA_SPAN reference price.

    Returns (dataframe, meta). On failure dataframe is empty and meta contains "error".
    """
    ticker = yf.Ticker(ticker_symbol)
    need_min = ema_span
    need_recommended = recommended_min_bars(ema_span)
    meta: dict[str, Any] = {
        "recommended_min_bars": need_recommended,
        "minimum_bars_for_ema": need_min,
    }

    chosen: tuple[str, pd.DataFrame] | None = None
    for period in _YF_PERIODS:
        df = ticker.history(period=period)
        if df.empty:
            continue
        if len(df) >= need_recommended:
            meta["period_used"] = period
            meta["bars_loaded"] = len(df)
            meta["meets_recommended_bars"] = True
            return df, meta
        if chosen is None or len(df) > len(chosen[1]):
            chosen = (period, df)

    if chosen is None:
        meta["error"] = "Invalid ticker or no price history returned."
        return pd.DataFrame(), meta

    period, df = chosen
    meta["period_used"] = period
    meta["bars_loaded"] = len(df)
    meta["meets_recommended_bars"] = len(df) >= need_recommended

    if len(df) < need_min:
        meta["error"] = (
            f"Only {len(df)} bars available; need at least {need_min} for "
            f"a {ema_span}-period EMA reference."
        )
        return pd.DataFrame(), meta

    return df, meta


def get_trading_targets(ticker_symbol: str, ema_span: int = EMA_SPAN) -> dict[str, Any]:
    df, meta = load_price_history_for_ema(ticker_symbol, ema_span=ema_span)
    if df.empty:
        base: dict[str, Any] = {"Ticker": ticker_symbol}
        base.update(meta)
        return base

    df["Reference_Price"] = df["Close"].ewm(span=ema_span, adjust=False).mean()
    current_reference = df["Reference_Price"].iloc[-1]
    current_price = df["Close"].iloc[-1]
    buy_target = current_reference * 0.95
    sell_target = current_reference * 1.07

    result: dict[str, Any] = {
        "Ticker": ticker_symbol,
        "Period used (yfinance)": meta["period_used"],
        "Bars loaded": meta["bars_loaded"],
        "Meets recommended bar count": meta["meets_recommended_bars"],
        "Recommended min bars": meta["recommended_min_bars"],
        "Current Price": round(float(current_price), 2),
        f"Reference Price ({ema_span} EMA)": round(float(current_reference), 2),
        "BUY Target (-5%)": round(float(buy_target), 2),
        "SELL Target (+7%)": round(float(sell_target), 2),
        "Distance to Buy": f"{round(((current_price / buy_target) - 1) * 100, 2)}%",
    }
    if "error" in meta:
        result["warning"] = meta["error"]
    return result


_targets_ok = targets_ok


def load_symbols_from_config(
    path: Path | None = None,
    *,
    output_csv_key: str = "output_csv",
    output_csv_fallback: str = "trading_targets.csv",
) -> tuple[list[str], Path]:
    cfg_path = path or _DEFAULT_CONFIG
    base_dir = cfg_path.parent if cfg_path.is_file() else cfg_path
    if not (base_dir / "config.ini").is_file() and not cfg_path.is_file():
        raise FileNotFoundError(f"Config not found: {cfg_path}")

    parser = read_merged_ini(base_dir)
    if not parser.has_section("trading"):
        raise ValueError(f"Missing [trading] section in {base_dir / 'config.ini'}")

    raw = parser.get("trading", "symbols", fallback="").strip()
    if not raw:
        raise ValueError(f"'symbols' is empty in {base_dir / 'config.ini'}")

    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    if not symbols:
        raise ValueError(f"No valid symbols after parsing in {base_dir / 'config.ini'}")

    out_csv = parser.get(
        "trading", output_csv_key, fallback=output_csv_fallback
    ).strip() or output_csv_fallback
    out_path = Path(out_csv)
    if not out_path.is_absolute():
        out_path = base_dir / out_path

    return symbols, out_path


def meta_summary_for_exports(meta: dict[str, Any]) -> dict[str, Any]:
    """Common period/bars columns for CSV exports (keys match get_trading_targets)."""
    return {
        "Period used (yfinance)": meta.get("period_used", ""),
        "Bars loaded": meta.get("bars_loaded", ""),
        "Meets recommended bar count": meta.get("meets_recommended_bars"),
        "Recommended min bars": meta.get("recommended_min_bars", ""),
    }


def trading_targets_to_csv_row(
    symbol: str, payload: dict[str, Any], ema_span: int = EMA_SPAN
) -> dict[str, Any]:
    """Map API-style payload to CSV column names (requested spellings)."""
    ref_key = f"Reference Price ({ema_span} EMA)"
    err = payload.get("error")
    if err or "Current Price" not in payload:
        return {
            "Symbol": symbol,
            "Period Used": err or payload.get("warning", "") or "Unknown error",
            "Bars Loaded": "",
            "Meet Recommended bar count": "",
            "Recommended Mn Bars": payload.get("recommended_min_bars", ""),
            "Current Price": "",
            "Referance price (52 EMA)": "",
            "Buy Traget (-5%)": "",
            "Sell Traget (+7%)": "",
            "Distance to Buy": "",
        }

    meets = payload.get("Meets recommended bar count")
    return {
        "Symbol": symbol,
        "Period Used": payload.get("Period used (yfinance)", ""),
        "Bars Loaded": payload.get("Bars loaded", ""),
        "Meet Recommended bar count": "Yes" if meets else "No",
        "Recommended Mn Bars": payload.get("Recommended min bars", ""),
        "Current Price": payload.get("Current Price", ""),
        "Referance price (52 EMA)": payload.get(ref_key, ""),
        "Buy Traget (-5%)": payload.get("BUY Target (-5%)", ""),
        "Sell Traget (+7%)": payload.get("SELL Target (+7%)", ""),
        "Distance to Buy": payload.get("Distance to Buy", ""),
    }


def write_csv_dicts(
    rows: list[dict[str, Any]],
    output_path: Path,
    fieldnames: Sequence[str],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def write_targets_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    write_csv_dicts(rows, output_path, CSV_FIELDNAMES)


if __name__ == "__main__":
    try:
        symbols, out_path = load_symbols_from_config()
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    rows: list[dict[str, Any]] = []
    errors = 0
    for sym in symbols:
        payload = get_trading_targets(sym)
        rows.append(trading_targets_to_csv_row(sym, payload))
        if not targets_ok(payload):
            errors += 1
            msg = payload.get("error") or payload.get("warning") or payload
            print(f"{sym}: {msg}", file=sys.stderr)

    write_targets_csv(rows, out_path)
    print(f"Wrote {len(rows)} row(s) to {out_path}")
    if errors:
        sys.exit(1)
