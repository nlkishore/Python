"""
One-symbol check: prints which yfinance period was chosen, bar counts, last EMA, and tail preview.

Run from repo root:
  python examples\\ema_single_ticker_test.py MSFT
"""
from __future__ import annotations

import sys
from pathlib import Path

AT_DIR = Path(__file__).resolve().parents[1] / "AutomatedTrading"
if str(AT_DIR) not in sys.path:
    sys.path.insert(0, str(AT_DIR))

from averagePriceFetcher import EMA_SPAN, get_trading_targets, load_price_history_for_ema


def main() -> None:
    symbol = sys.argv[1].strip().upper() if len(sys.argv) > 1 else "AAPL"
    df, meta = load_price_history_for_ema(symbol, ema_span=EMA_SPAN)
    print(f"Symbol: {symbol}")
    print(f"Recommended min bars: {meta.get('recommended_min_bars')}")
    print(f"Minimum bars for EMA: {meta.get('minimum_bars_for_ema')}")
    if df.empty:
        print("No data:", meta.get("error", meta))
        raise SystemExit(1)

    print(f"yfinance period used: {meta.get('period_used')}")
    print(f"Bars loaded: {meta.get('bars_loaded')}")
    print(f"Meets recommended bar count: {meta.get('meets_recommended_bars')}")

    df = df.copy()
    df["EMA52"] = df["Close"].ewm(span=EMA_SPAN, adjust=False).mean()
    last_close = df["Close"].iloc[-1]
    last_ema = df["EMA52"].iloc[-1]
    print(f"Last close: {last_close:.4f}")
    print(f"Last {EMA_SPAN}-EMA: {last_ema:.4f}")

    preview = df[["Close", "EMA52"]].tail(5).round(4)
    print("\nTail (Close vs EMA):")
    print(preview.to_string())

    summary = get_trading_targets(symbol)
    print("\nStrategy snapshot from get_trading_targets:")
    if "Current Price" in summary:
        for k in (
            "Period used (yfinance)",
            "Bars loaded",
            "Meets recommended bar count",
            "Recommended min bars",
            "Current Price",
            f"Reference Price ({EMA_SPAN} EMA)",
        ):
            if k in summary:
                print(f"  {k}: {summary[k]}")
    else:
        print(" ", summary.get("error") or summary)


if __name__ == "__main__":
    main()
