import configparser
import sys
from pathlib import Path
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

ADAPTIVE_VOLUME_CSV_FIELDNAMES: tuple[str, ...] = (
    "Symbol",
    "Period Used",
    "Bars Loaded",
    "Meet Recommended bar count",
    "Recommended Mn Bars",
    "Decision",
    "Reason",
    "Current Price",
    "Ref Price (EMA)",
    "Volume Status",
    "Volume Ratio",
)


def _read_volume_filter_enabled(cfg_path: Path) -> bool:
    from shared.config_loader import read_merged_ini

    parser = read_merged_ini(cfg_path.parent)
    if parser.has_section("trading"):
        return parser.getboolean("trading", "volume_filter_enabled", fallback=True)
    return True


def get_ai_trade_decision(
    ticker_symbol: str,
    volume_filter_enabled: bool = True,
    ema_span: int = EMA_SPAN,
) -> dict[str, Any]:
    df, meta = load_price_history_for_ema(ticker_symbol, ema_span=ema_span)
    summary = meta_summary_for_exports(meta)
    if df.empty or meta.get("error"):
        return {
            "Ticker": ticker_symbol,
            "error": meta.get("error", "No price history."),
            **summary,
        }

    df = append_atr_ema_columns(df, ema_span=ema_span)
    df["Vol_Avg"] = df["Volume"].rolling(window=20).mean()

    latest = df.iloc[-1]
    ref_price = float(latest["EMA_52"])
    current_price = float(latest["Close"])
    current_vol = float(latest["Volume"])
    avg_vol = latest["Vol_Avg"]
    atr_val = latest["ATR"]

    if (
        pd.isna(latest["ATR"])
        or pd.isna(latest["EMA_52"])
        or pd.isna(latest["Vol_Avg"])
    ):
        return {
            "Ticker": ticker_symbol,
            "error": "Insufficient bars for EMA, ATR, or volume average.",
            **summary,
        }

    atr_f = float(atr_val)
    buy_target = ref_price - (2 * atr_f)
    sell_target = ref_price + (2 * atr_f)

    avg_vol_f = float(avg_vol)
    volume_confirmed = avg_vol_f > 0 and current_vol > (avg_vol_f * 1.5)
    ratio_str = (
        f"{round((current_vol / avg_vol_f), 2)}x"
        if avg_vol_f > 0
        else "N/A"
    )

    decision = "HOLD"
    reason = "Price within normal range."

    if current_price <= buy_target:
        if not volume_filter_enabled or volume_confirmed:
            decision = "BUY"
            reason = (
                "Price hit buy zone with volume confirmation."
                if volume_confirmed
                else "Price hit buy zone (volume filter off or not required)."
            )
        else:
            decision = "WAIT"
            reason = "Price in buy zone, but LOW VOLUME (higher fade risk)."
    elif current_price >= sell_target:
        if not volume_filter_enabled or volume_confirmed:
            decision = "SELL"
            reason = "Price hit sell zone with volume confirmation."
        else:
            decision = "WAIT"
            reason = "Price in sell zone, but LOW VOLUME (trend may continue)."

    return {
        "Ticker": ticker_symbol,
        **summary,
        "Decision": decision,
        "Reason": reason,
        "Current Price": round(current_price, 2),
        "Ref Price (EMA)": round(ref_price, 2),
        "Volume Status": "HIGH" if volume_confirmed else "NORMAL/LOW",
        "Volume Ratio": ratio_str,
    }


def volume_decision_to_csv_row(symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    err = payload.get("error")
    if err or "Current Price" not in payload:
        return {
            "Symbol": symbol,
            "Period Used": err or "Unknown error",
            "Bars Loaded": payload.get("Bars loaded", ""),
            "Meet Recommended bar count": "",
            "Recommended Mn Bars": payload.get("Recommended min bars", ""),
            "Decision": "",
            "Reason": "",
            "Current Price": "",
            "Ref Price (EMA)": "",
            "Volume Status": "",
            "Volume Ratio": "",
        }

    meets = payload.get("Meets recommended bar count")
    return {
        "Symbol": symbol,
        "Period Used": payload.get("Period used (yfinance)", ""),
        "Bars Loaded": payload.get("Bars loaded", ""),
        "Meet Recommended bar count": "Yes" if meets else "No",
        "Recommended Mn Bars": payload.get("Recommended min bars", ""),
        "Decision": payload.get("Decision", ""),
        "Reason": payload.get("Reason", ""),
        "Current Price": payload.get("Current Price", ""),
        "Ref Price (EMA)": payload.get("Ref Price (EMA)", ""),
        "Volume Status": payload.get("Volume Status", ""),
        "Volume Ratio": payload.get("Volume Ratio", ""),
    }


if __name__ == "__main__":
    cfg_path = Path(__file__).resolve().parent / "config.ini"
    try:
        symbols, out_path = load_symbols_from_config(
            output_csv_key="output_csv_adaptive_volume",
            output_csv_fallback="adaptive_trader_volume.csv",
        )
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    volume_filter = _read_volume_filter_enabled(cfg_path)

    rows: list[dict[str, Any]] = []
    errors = 0
    for sym in symbols:
        payload = get_ai_trade_decision(sym, volume_filter_enabled=volume_filter)
        rows.append(volume_decision_to_csv_row(sym, payload))
        if not _targets_ok(payload):
            errors += 1
            print(f"{sym}: {payload.get('error', payload)}", file=sys.stderr)

    write_csv_dicts(rows, out_path, ADAPTIVE_VOLUME_CSV_FIELDNAMES)
    print(f"Wrote {len(rows)} row(s) to {out_path} (volume_filter={volume_filter})")
    if errors:
        sys.exit(1)
