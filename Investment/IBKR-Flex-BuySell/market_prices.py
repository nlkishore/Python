"""Fetch latest market prices via Yahoo Finance (yfinance)."""

from __future__ import annotations

from datetime import date

import pandas as pd


def _last_close(ticker_history: pd.DataFrame) -> tuple[float | None, date | None]:
    if ticker_history.empty or "Close" not in ticker_history.columns:
        return None, None
    closes = ticker_history["Close"].dropna()
    if closes.empty:
        return None, None
    last_ts = closes.index[-1]
    price = float(closes.iloc[-1])
    as_of = last_ts.date() if hasattr(last_ts, "date") else None
    return round(price, 4), as_of


def fetch_current_market_prices(symbols: list[str]) -> dict[str, tuple[float | None, date | None]]:
    """
    Return {SYMBOL: (price, as_of_date)} for each symbol.
    Missing/delisted symbols map to (None, None).
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("Install yfinance: pip install yfinance") from exc

    unique = sorted({str(s).strip().upper() for s in symbols if str(s).strip()})
    out: dict[str, tuple[float | None, date | None]] = {s: (None, None) for s in unique}
    if not unique:
        return out

    try:
        if len(unique) == 1:
            sym = unique[0]
            hist = yf.Ticker(sym).history(period="5d", auto_adjust=True)
            out[sym] = _last_close(hist)
            return out

        raw = yf.download(
            unique,
            period="5d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        for sym in unique:
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if sym in raw.columns.get_level_values(0):
                        hist = raw[sym].dropna(how="all")
                    elif sym in raw.columns.get_level_values(1):
                        hist = raw.xs(sym, level=1, axis=1).dropna(how="all")
                    else:
                        hist = pd.DataFrame()
                else:
                    hist = raw
                price, as_of = _last_close(hist if isinstance(hist, pd.DataFrame) else pd.DataFrame())
                if price is None:
                    hist = yf.Ticker(sym).history(period="5d", auto_adjust=True)
                    price, as_of = _last_close(hist)
                out[sym] = (price, as_of)
            except Exception:
                try:
                    hist = yf.Ticker(sym).history(period="5d", auto_adjust=True)
                    out[sym] = _last_close(hist)
                except Exception:
                    out[sym] = (None, None)
    except Exception:
        for sym in unique:
            try:
                hist = yf.Ticker(sym).history(period="5d", auto_adjust=True)
                out[sym] = _last_close(hist)
            except Exception:
                out[sym] = (None, None)

    return out


def enrich_completely_sold_with_market_prices(closed: pd.DataFrame) -> pd.DataFrame:
    """Add Current_Market_Price and Price_As_Of columns."""
    if closed.empty or "Symbol" not in closed.columns:
        return closed

    out = closed.copy()
    prices = fetch_current_market_prices(out["Symbol"].astype(str).tolist())

    out["Current_Market_Price"] = out["Symbol"].map(lambda s: prices.get(str(s).upper(), (None, None))[0])
    out["Price_As_Of"] = out["Symbol"].map(lambda s: prices.get(str(s).upper(), (None, None))[1])

    if "Last_Sold_Price" in out.columns:
        def _chg(row: pd.Series) -> float | None:
            cur = row.get("Current_Market_Price")
            last = row.get("Last_Sold_Price")
            if cur is None or last is None or not last:
                return None
            return round((float(cur) / float(last) - 1.0) * 100.0, 2)

        out["Change_Since_Last_Sold_Pct"] = out.apply(_chg, axis=1)

    col_order = [
        "Symbol",
        "Buy_Qty_Total",
        "Sell_Qty_Total",
        "Buy_Trades",
        "Sell_Trades",
        "Total_Buy_Cost",
        "Total_Sell_Proceeds",
        "Profit",
        "Profit_Pct",
        "Last_Sold_Date",
        "Last_Sold_Price",
        "Current_Market_Price",
        "Price_As_Of",
        "Change_Since_Last_Sold_Pct",
        "First_Buy_Date",
    ]
    present = [c for c in col_order if c in out.columns]
    rest = [c for c in out.columns if c not in present]
    return out[present + rest]
