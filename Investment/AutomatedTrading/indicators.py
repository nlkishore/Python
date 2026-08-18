"""Shared technical-indicator helpers for AutomatedTrading scripts."""

from __future__ import annotations

from typing import Any

import pandas as pd


def targets_ok(payload: dict[str, Any]) -> bool:
    """True when a strategy payload has a usable current price (no error)."""
    return "error" not in payload and "Current Price" in payload


def atr14(df: pd.DataFrame) -> pd.Series:
    """14-period average true range from OHLC columns."""
    high_low = df["High"] - df["Low"]
    high_cp = (df["High"] - df["Close"].shift()).abs()
    low_cp = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    return tr.rolling(window=14).mean()


def append_atr_ema_columns(df: pd.DataFrame, ema_span: int = 52) -> pd.DataFrame:
    """Return a copy with EMA and ATR columns added."""
    out = df.copy()
    out["EMA_52"] = out["Close"].ewm(span=ema_span, adjust=False).mean()
    out["ATR"] = atr14(out)
    return out
