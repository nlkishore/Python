import sys
from typing import Any

import pandas as pd

from averagePriceFetcher import (
    EMA_SPAN,
    load_price_history_for_ema,
    load_symbols_from_config,
    meta_summary_for_exports,
    write_csv_dicts,
)
from indicators import append_atr_ema_columns, targets_ok as _targets_ok

ADAPTIVE_AI_CSV_FIELDNAMES: tuple[str, ...] = (
    "Symbol",
    "Period Used",
    "Bars Loaded",
    "Meet Recommended bar count",
    "Recommended Mn Bars",
    "Current Price",
    "Reference (52 EMA)",
    "Daily Volatility (ATR)",
    "Adaptive Buy Target",
    "Adaptive Sell Target",
    "Implied Buy %",
)


def get_adaptive_targets(ticker_symbol: str, ema_span: int = EMA_SPAN) -> dict[str, Any]:
    df, meta = load_price_history_for_ema(ticker_symbol, ema_span=ema_span)
    summary = meta_summary_for_exports(meta)
    if df.empty or meta.get("error"):
        return {
            "Ticker": ticker_symbol,
            "error": meta.get("error", "No price history."),
            **summary,
        }

    df = append_atr_ema_columns(df, ema_span=ema_span)

    latest = df.iloc[-1]
    ref_price = float(latest["EMA_52"])
    atr_val = float(latest["ATR"])
    current_price = float(latest["Close"])

    if pd.isna(latest["ATR"]) or pd.isna(latest["EMA_52"]):
        return {
            "Ticker": ticker_symbol,
            "error": "Insufficient bars for stable ATR or EMA.",
            **summary,
        }

    buy_target = ref_price - (2 * atr_val)
    sell_target = ref_price + (2 * atr_val)
    implied_buy_pct = f"-{round((1 - buy_target / ref_price) * 100, 2)}%"

    return {
        "Ticker": ticker_symbol,
        **summary,
        "Current Price": round(current_price, 2),
        "Reference (52 EMA)": round(ref_price, 2),
        "Daily Volatility (ATR)": round(atr_val, 2),
        "Adaptive Buy Target": round(buy_target, 2),
        "Adaptive Sell Target": round(sell_target, 2),
        "Implied Buy %": implied_buy_pct,
    }


def adaptive_targets_to_csv_row(symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    err = payload.get("error")
    if err or "Current Price" not in payload:
        return {
            "Symbol": symbol,
            "Period Used": err or "Unknown error",
            "Bars Loaded": payload.get("Bars loaded", ""),
            "Meet Recommended bar count": "",
            "Recommended Mn Bars": payload.get("Recommended min bars", ""),
            "Current Price": "",
            "Reference (52 EMA)": "",
            "Daily Volatility (ATR)": "",
            "Adaptive Buy Target": "",
            "Adaptive Sell Target": "",
            "Implied Buy %": "",
        }

    meets = payload.get("Meets recommended bar count")
    return {
        "Symbol": symbol,
        "Period Used": payload.get("Period used (yfinance)", ""),
        "Bars Loaded": payload.get("Bars loaded", ""),
        "Meet Recommended bar count": "Yes" if meets else "No",
        "Recommended Mn Bars": payload.get("Recommended min bars", ""),
        "Current Price": payload.get("Current Price", ""),
        "Reference (52 EMA)": payload.get("Reference (52 EMA)", ""),
        "Daily Volatility (ATR)": payload.get("Daily Volatility (ATR)", ""),
        "Adaptive Buy Target": payload.get("Adaptive Buy Target", ""),
        "Adaptive Sell Target": payload.get("Adaptive Sell Target", ""),
        "Implied Buy %": payload.get("Implied Buy %", ""),
    }


if __name__ == "__main__":
    try:
        symbols, out_path = load_symbols_from_config(
            output_csv_key="output_csv_adaptive_ai",
            output_csv_fallback="adaptive_ai_targets.csv",
        )
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    rows: list[dict[str, Any]] = []
    errors = 0
    for sym in symbols:
        payload = get_adaptive_targets(sym)
        rows.append(adaptive_targets_to_csv_row(sym, payload))
        if not _targets_ok(payload):
            errors += 1
            print(f"{sym}: {payload.get('error', payload)}", file=sys.stderr)

    write_csv_dicts(rows, out_path, ADAPTIVE_AI_CSV_FIELDNAMES)
    print(f"Wrote {len(rows)} row(s) to {out_path}")
    if errors:
        sys.exit(1)
