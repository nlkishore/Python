"""
Swing pivot support/resistance from daily OHLC candles plus simple heuristic BUY/SELL labels.

Signals are illustrative only and not trading advice.
"""

from __future__ import annotations

import argparse
import configparser
import json
import math
import sys
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

INVESTMENT_ROOT = Path(__file__).resolve().parent.parent
if str(INVESTMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(INVESTMENT_ROOT))

from shared.config_loader import green_api_credentials, read_merged_ini  # noqa: E402

from averagePriceFetcher import (
    EMA_SPAN,
    load_price_history_for_ema,
    load_symbols_from_config,
    meta_summary_for_exports,
    write_csv_dicts,
)
from indicators import atr14, targets_ok as _targets_ok

CHART_SIGNALS_CSV_FIELDNAMES: tuple[str, ...] = (
    "Symbol",
    "Period Used",
    "Bars Loaded",
    "Meet Recommended bar count",
    "Recommended Mn Bars",
    "Current Price",
    "ATR14",
    "Nearest Support",
    "Distance To Support %",
    "Nearest Resistance",
    "Distance To Resistance %",
    "Pivot Lows Detected",
    "Pivot Highs Detected",
    "Candle Pattern",
    "Signal",
    "Signal Reason",
)

_DEFAULT_PIVOT_LEFT = 3
_DEFAULT_PIVOT_RIGHT = 3
_DEFAULT_ATR_PROX_MULT = 1.15
_DEFAULT_WHATSAPP_ENABLED = False
_DEFAULT_NOTIFY_SIGNALS = "BUY_HEURISTIC,SELL_HEURISTIC"
_DEFAULT_NOTIFY_COOLDOWN_MINUTES = 120
_DEFAULT_NOTIFY_STATE_FILE = "chart_support_notify_state.json"
_DEFAULT_NOTIFY_PRICE_BUCKET_PCT = 0.5
_DEFAULT_CHART_WATCH_ENABLED = False
_DEFAULT_CHART_WATCH_INTERVAL_SEC = 300
_DEFAULT_CHART_WATCH_TZ = "America/New_York"
_DEFAULT_CHART_WATCH_START = "09:30"
_DEFAULT_CHART_WATCH_END = "16:00"


def _configure_stdio_utf8() -> None:
    """Avoid UnicodeEncodeError on some Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError, AttributeError):
                pass


def _clean_cfg_value(value: str) -> str:
    """Trim whitespace and matching single/double quotes around config values."""
    out = value.strip()
    if len(out) >= 2 and ((out[0] == '"' and out[-1] == '"') or (out[0] == "'" and out[-1] == "'")):
        out = out[1:-1].strip()
    return out


def _atr14(df: pd.DataFrame) -> pd.Series:
    return atr14(df)


def pivot_low_prices(df: pd.DataFrame, left: int, right: int) -> list[float]:
    """Fractal-style pivot lows: bar low equals window minimum."""
    lows = df["Low"]
    n = len(lows)
    out: list[float] = []
    for i in range(left, n - right):
        window = lows.iloc[i - left : i + right + 1]
        v = float(lows.iloc[i])
        if math.isfinite(v) and abs(v - float(window.min())) < 1e-9:
            out.append(v)
    return out


def pivot_high_prices(df: pd.DataFrame, left: int, right: int) -> list[float]:
    highs = df["High"]
    n = len(highs)
    out: list[float] = []
    for i in range(left, n - right):
        window = highs.iloc[i - left : i + right + 1]
        v = float(highs.iloc[i])
        if math.isfinite(v) and abs(v - float(window.max())) < 1e-9:
            out.append(v)
    return out


def nearest_support_below(close: float, pivot_lows: list[float]) -> float | None:
    below = [p for p in pivot_lows if p < close - 1e-9]
    if not below:
        return None
    return max(below)


def nearest_resistance_above(close: float, pivot_highs: list[float]) -> float | None:
    above = [p for p in pivot_highs if p > close + 1e-9]
    if not above:
        return None
    return min(above)


def _body_bounds(o: float, c: float) -> tuple[float, float]:
    lo = min(o, c)
    hi = max(o, c)
    return lo, hi


def classify_latest_pattern(df: pd.DataFrame) -> str:
    """Single-bar (+ prior bar where needed) heuristic labels."""
    if len(df) < 3:
        return "INSUFFICIENT_BARS"

    i = df.index[-1]
    hi = float(df["High"].iloc[-1])
    lo = float(df["Low"].iloc[-1])
    o = float(df["Open"].iloc[-1])
    c = float(df["Close"].iloc[-1])
    rng = hi - lo
    if rng <= 0:
        return "NO_RANGE"

    body = abs(c - o)
    body_lo, body_hi = _body_bounds(o, c)
    upper_wick = hi - body_hi
    lower_wick = body_lo - lo

    # Hammer / Hanging man shape (bullish reversal context heuristic uses zone logic later)
    if body <= max(upper_wick, lower_wick) * 1.05:
        if lower_wick >= 2 * max(body, 1e-6) and upper_wick <= 1.25 * max(body, 1e-6):
            return "HAMMER_LIKE"

    # Shooting star like
    if body <= max(upper_wick, lower_wick) * 1.05:
        if upper_wick >= 2 * max(body, 1e-6) and lower_wick <= 1.25 * max(body, 1e-6):
            return "STAR_LIKE_TOP"

    o1 = float(df["Open"].iloc[-2])
    c1 = float(df["Close"].iloc[-2])

    # Bullish engulfing
    bear_prev = o1 >= c1
    bull_curr = c > o
    if bear_prev and bull_curr and o <= min(c1, o1) and c >= max(c1, o1):
        return "BULLISH_ENGULFING"

    # Bearish engulfing
    bull_prev = o1 <= c1
    bear_curr = c < o
    if bull_prev and bear_curr and o >= max(c1, o1) and c <= min(c1, o1):
        return "BEARISH_ENGULFING"

    return "NONE"


def _near_level(price: float, level: float, atr_v: float, mult: float) -> bool:
    if atr_v <= 0 or not math.isfinite(atr_v):
        return False
    return abs(price - level) <= mult * atr_v


def heuristic_signal_from_chart(
    close: float,
    atr_tail: float,
    support_below: float | None,
    resistance_above: float | None,
    pattern: str,
    atr_proximity_mult: float,
) -> tuple[str, str]:
    """
    Conservative rules: BUY/SELL needs both context (within ATR of key level)
    plus a plausible reversal pattern.
    """
    near_support = support_below is not None and _near_level(
        close, support_below, atr_tail, atr_proximity_mult
    )
    near_resistance = resistance_above is not None and _near_level(
        close, resistance_above, atr_tail, atr_proximity_mult
    )

    bullish_patterns = {"HAMMER_LIKE", "BULLISH_ENGULFING"}
    bearish_patterns = {"STAR_LIKE_TOP", "BEARISH_ENGULFING"}

    if pattern in bullish_patterns and near_support:
        pct = ""
        if support_below is not None and support_below > 0:
            pct = f"{round((close / support_below - 1) * 100, 2)}%"
        return (
            "BUY_HEURISTIC",
            f"Bullish pattern ({pattern}) while price sits near pivot support (~{pct} vs level).",
        )

    if pattern in bearish_patterns and near_resistance:
        pct = ""
        if resistance_above is not None and resistance_above > 0:
            pct = f"{round((1 - close / resistance_above) * 100, 2)}%"
        return (
            "SELL_HEURISTIC",
            f"Bearish pattern ({pattern}) while price sits near pivot resistance (~{pct} vs level).",
        )

    if near_support or near_resistance or pattern != "NONE":
        return (
            "HOLD",
            "Zones/patterns inconclusive: need matching reversal pattern "
            "and ATR-distance to support/resistance.",
        )
    return (
        "HOLD",
        "No qualifying pivot proximity or reversal pattern.",
    )


def load_chart_scan_params(cfg_path: Path) -> tuple[int, int, float]:
    parser = configparser.ConfigParser()
    parser.read(cfg_path, encoding="utf-8")
    if not parser.has_section("trading"):
        return _DEFAULT_PIVOT_LEFT, _DEFAULT_PIVOT_RIGHT, _DEFAULT_ATR_PROX_MULT
    left = parser.getint("trading", "chart_pivot_left", fallback=_DEFAULT_PIVOT_LEFT)
    right = parser.getint("trading", "chart_pivot_right", fallback=_DEFAULT_PIVOT_RIGHT)
    prox = parser.getfloat(
        "trading", "chart_atr_proximity_mult", fallback=_DEFAULT_ATR_PROX_MULT
    )
    left = max(1, left)
    right = max(1, right)
    prox = max(0.5, float(prox))
    return left, right, prox


def resolve_symbol_list(
    *,
    symbol: str | None = None,
    symbols: str | None = None,
    config_symbols: list[str] | None = None,
) -> list[str]:
    """Resolve tickers: CLI --symbol / --symbols override config [trading] symbols."""
    if symbol is not None and symbols is not None:
        raise ValueError("Pass either --symbol or --symbols, not both.")

    if symbols is not None:
        raw_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    elif symbol is not None:
        one = symbol.strip().upper()
        raw_list = [one] if one else []
    elif config_symbols:
        raw_list = [s.strip().upper() for s in config_symbols if s and s.strip()]
    else:
        raw_list = []

    if not raw_list:
        raise ValueError(
            "No symbols: pass --symbol SYMBOL or --symbols A,B,C, "
            "or set [trading] symbols in config.ini."
        )

    seen: set[str] = set()
    out: list[str] = []
    for s in raw_list:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _chart_output_path(cfg_path: Path) -> Path:
    parser = configparser.ConfigParser()
    parser.read(cfg_path, encoding="utf-8")
    out_csv = (
        parser.get(
            "trading", "output_csv_chart_support", fallback="chart_support_signals.csv"
        ).strip()
        or "chart_support_signals.csv"
    )
    out_path = Path(out_csv)
    if not out_path.is_absolute():
        out_path = cfg_path.parent / out_path
    return out_path


def _parse_hhmm(raw: str) -> tuple[int, int]:
    s = raw.strip()
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format {raw!r}; use HH:MM (e.g., 09:30).")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Invalid time values in {raw!r}.")
    return h, m


def load_chart_watch_params(cfg_path: Path) -> dict[str, Any]:
    parser = configparser.ConfigParser()
    parser.read(cfg_path, encoding="utf-8")
    defaults: dict[str, Any] = {
        "enabled": _DEFAULT_CHART_WATCH_ENABLED,
        "interval_seconds": _DEFAULT_CHART_WATCH_INTERVAL_SEC,
        "timezone": _DEFAULT_CHART_WATCH_TZ,
        "session_start_hm": (_parse_hhmm(_DEFAULT_CHART_WATCH_START)),
        "session_end_hm": (_parse_hhmm(_DEFAULT_CHART_WATCH_END)),
        "skip_weekends": True,
        "log_when_closed": False,
    }
    if not parser.has_section("trading"):
        return defaults

    enabled = parser.getboolean(
        "trading", "chart_watch_enabled", fallback=_DEFAULT_CHART_WATCH_ENABLED
    )
    interval = parser.getint(
        "trading",
        "chart_watch_interval_seconds",
        fallback=_DEFAULT_CHART_WATCH_INTERVAL_SEC,
    )
    tz_name = parser.get(
        "trading", "chart_watch_timezone", fallback=_DEFAULT_CHART_WATCH_TZ
    ).strip() or _DEFAULT_CHART_WATCH_TZ
    start_raw = parser.get(
        "trading", "chart_watch_session_start", fallback=_DEFAULT_CHART_WATCH_START
    )
    end_raw = parser.get(
        "trading", "chart_watch_session_end", fallback=_DEFAULT_CHART_WATCH_END
    )
    skip_weekends = parser.getboolean(
        "trading", "chart_watch_skip_weekends", fallback=True
    )
    log_closed = parser.getboolean(
        "trading", "chart_watch_log_when_closed", fallback=False
    )

    try:
        sh, sm = _parse_hhmm(start_raw)
        eh, em = _parse_hhmm(end_raw)
    except ValueError:
        raise ValueError(
            "Invalid chart_watch_session_start or chart_watch_session_end "
            "in config.ini"
        ) from None

    return {
        "enabled": enabled,
        "interval_seconds": max(60, int(interval)),
        "timezone": tz_name,
        "session_start_hm": (sh, sm),
        "session_end_hm": (eh, em),
        "skip_weekends": skip_weekends,
        "log_when_closed": log_closed,
    }


def _us_regular_session_open(watch_cfg: dict[str, Any]) -> tuple[bool, str]:
    tz_name = str(watch_cfg.get("timezone") or _DEFAULT_CHART_WATCH_TZ)
    try:
        tz = ZoneInfo(tz_name)
    except Exception as exc:
        raise RuntimeError(
            f"Timezone {tz_name!r} is invalid. Install IANA tz data on Windows:\n"
            "  pip install tzdata\n"
            f"Underlying error: {exc}"
        ) from exc

    now = datetime.now(tz)
    if watch_cfg.get("skip_weekends", True) and now.weekday() >= 5:
        return False, "weekend"

    sh, sm = watch_cfg["session_start_hm"]
    eh, em = watch_cfg["session_end_hm"]
    start_t = dt_time(sh, sm)
    end_t = dt_time(eh, em)
    cur = now.time()
    if start_t == end_t:
        return False, "invalid_session_window"
    in_session = start_t <= cur < end_t
    return in_session, "open" if in_session else "outside_session_hours"


def run_chart_scan_job(
    cfg_path: Path,
    pivot_left: int,
    pivot_right: int,
    atr_prox: float,
    notify_cfg: dict[str, Any],
    symbols_override: list[str] | None = None,
) -> tuple[int, int, int]:
    if symbols_override is not None:
        symbols = symbols_override
        out_path = _chart_output_path(cfg_path)
    else:
        symbols, out_path = load_symbols_from_config(
            path=cfg_path,
            output_csv_key="output_csv_chart_support",
            output_csv_fallback="chart_support_signals.csv",
        )
    rows: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    errors = 0
    for sym in symbols:
        payload = get_support_chart_signal(
            sym,
            pivot_left=pivot_left,
            pivot_right=pivot_right,
            atr_proximity_mult=atr_prox,
        )
        payloads.append(payload)
        rows.append(chart_signal_to_csv_row(sym, payload))
        if not _targets_ok(payload):
            errors += 1
            print(f"{sym}: {payload.get('error', payload)}", file=sys.stderr)

    write_csv_dicts(rows, out_path, CHART_SIGNALS_CSV_FIELDNAMES)
    sent = _send_whatsapp_messages_for_signals(payloads, notify_cfg)
    print(
        f"Wrote {len(rows)} row(s) to {out_path} "
        f"(pivot L/R={pivot_left}/{pivot_right}, atr_prox={atr_prox})"
    )
    if notify_cfg.get("enabled"):
        print(f"WhatsApp notifications sent: {sent}")

    return errors, len(rows), sent


def load_whatsapp_notify_params(cfg_path: Path) -> dict[str, Any]:
    parser = read_merged_ini(cfg_path.parent)
    if not parser.has_section("trading"):
        return {
            "enabled": _DEFAULT_WHATSAPP_ENABLED,
            "id_instance": "",
            "api_token_instance": "",
            "target_phone": "",
            "notify_signals": {"BUY_HEURISTIC", "SELL_HEURISTIC"},
        }

    enabled = parser.getboolean(
        "trading", "whatsapp_enabled", fallback=_DEFAULT_WHATSAPP_ENABLED
    )
    id_instance, api_token_instance, target_phone = green_api_credentials(
        parser, section="trading"
    )
    notify_raw = parser.get(
        "trading", "whatsapp_notify_signals", fallback=_DEFAULT_NOTIFY_SIGNALS
    )
    cooldown_minutes = parser.getint(
        "trading",
        "whatsapp_notify_cooldown_minutes",
        fallback=_DEFAULT_NOTIFY_COOLDOWN_MINUTES,
    )
    price_bucket_pct = parser.getfloat(
        "trading",
        "whatsapp_notify_price_bucket_pct",
        fallback=_DEFAULT_NOTIFY_PRICE_BUCKET_PCT,
    )
    state_file_raw = parser.get(
        "trading",
        "whatsapp_notify_state_file",
        fallback=_DEFAULT_NOTIFY_STATE_FILE,
    ).strip() or _DEFAULT_NOTIFY_STATE_FILE
    state_file = Path(state_file_raw)
    if not state_file.is_absolute():
        state_file = cfg_path.parent / state_file
    notify_signals = {
        token.strip().upper()
        for token in notify_raw.split(",")
        if token.strip()
    }
    if not notify_signals:
        notify_signals = {"BUY_HEURISTIC", "SELL_HEURISTIC"}

    return {
        "enabled": enabled,
        "id_instance": id_instance,
        "api_token_instance": api_token_instance,
        "target_phone": target_phone,
        "notify_signals": notify_signals,
        "cooldown_seconds": max(0, cooldown_minutes) * 60,
        "state_file": state_file,
        "price_bucket_pct": max(0.05, float(price_bucket_pct)),
    }


def _price_bucket_label(price: float, bucket_pct: float) -> str:
    """Map prices into coarse bands so near-identical prices don't re-alert."""
    if not math.isfinite(price) or price <= 0:
        return "na"
    step = max(price * (bucket_pct / 100.0), 0.01)
    idx = int(price // step)
    bucket_lo = idx * step
    bucket_hi = (idx + 1) * step
    return f"{bucket_lo:.2f}-{bucket_hi:.2f}"


def _build_whatsapp_message(payload: dict[str, Any]) -> str:
    return (
        "Chart Signal Alert\n"
        f"Symbol: {payload.get('Ticker', '')}\n"
        f"Signal: {payload.get('Signal', '')}\n"
        f"Pattern: {payload.get('Candle Pattern', '')}\n"
        f"Price: {payload.get('Current Price', '')}\n"
        f"Support: {payload.get('Nearest Support', '')}\n"
        f"Resistance: {payload.get('Nearest Resistance', '')}\n"
        f"Reason: {payload.get('Signal Reason', '')}"
    )


def _response_status_details(response: Any) -> tuple[int | None, Any]:
    """Best-effort status/data extraction across Green API SDK response shapes."""
    if response is None:
        return None, None
    code = getattr(response, "code", None)
    data = getattr(response, "data", None)
    if code is not None:
        return code, data
    if isinstance(response, dict):
        return response.get("code"), response.get("data")
    return None, response


def send_whatsapp_plain_text(
    notify_cfg: dict[str, Any], message: str
) -> tuple[bool, str | None]:
    """
    Send a single plain-text WhatsApp message via Green API (whatsapp_api_client_python).
    Uses the same [trading] whatsapp_* settings as chart signal alerts.
    Returns (success, error_detail or None). No-op if disabled, empty message, or missing config.
    """
    if not notify_cfg.get("enabled"):
        return False, "whatsapp_enabled is false in config.ini"
    text = (message or "").strip()
    if not text:
        return False, "empty message"
    id_instance = notify_cfg.get("id_instance", "")
    api_token_instance = notify_cfg.get("api_token_instance", "")
    target_phone = notify_cfg.get("target_phone", "")
    if not id_instance or not api_token_instance or not target_phone:
        return False, "missing whatsapp_id_instance, token, or target_phone in config.ini"
    try:
        from whatsapp_api_client_python import API
    except ImportError:
        return False, "whatsapp_api_client_python is not installed"
    green_api = API.GreenAPI(id_instance, api_token_instance)
    chat_id = f"{target_phone}@c.us"
    try:
        response = green_api.sending.sendMessage(chat_id, text)
        status_code, status_data = _response_status_details(response)
        if status_code in (200, 201):
            return True, None
        return False, f"API status={status_code}, data={status_data!r}"
    except Exception as exc:  # pragma: no cover - network/API
        return False, str(exc)


def _send_whatsapp_messages_for_signals(
    results: list[dict[str, Any]], notify_cfg: dict[str, Any]
) -> int:
    if not notify_cfg.get("enabled"):
        return 0

    id_instance = notify_cfg.get("id_instance", "")
    api_token_instance = notify_cfg.get("api_token_instance", "")
    target_phone = notify_cfg.get("target_phone", "")
    notify_signals = notify_cfg.get("notify_signals", set())
    cooldown_seconds = int(notify_cfg.get("cooldown_seconds", 0))
    state_file = notify_cfg.get("state_file")
    price_bucket_pct = float(
        notify_cfg.get("price_bucket_pct", _DEFAULT_NOTIFY_PRICE_BUCKET_PCT)
    )

    if not id_instance or not api_token_instance or not target_phone:
        print(
            "WhatsApp enabled but credentials/phone are missing in config.ini; "
            "skipping notifications.",
            file=sys.stderr,
        )
        return 0

    try:
        from whatsapp_api_client_python import API
    except ImportError:
        print(
            "whatsapp_api_client_python is not installed; skipping notifications.",
            file=sys.stderr,
        )
        return 0

    green_api = API.GreenAPI(id_instance, api_token_instance)
    chat_id = f"{target_phone}@c.us"
    sent = 0
    now_ts = time.time()

    state: dict[str, float] = {}
    if isinstance(state_file, Path) and state_file.is_file():
        try:
            loaded = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = {
                    str(k): float(v)
                    for k, v in loaded.items()
                    if isinstance(v, (int, float))
                }
        except (OSError, ValueError, TypeError):
            state = {}

    for payload in results:
        if "error" in payload:
            continue
        signal = str(payload.get("Signal", "")).upper()
        if signal not in notify_signals:
            continue
        symbol = str(payload.get("Ticker", "")).upper()
        price = float(payload.get("Current Price", 0.0) or 0.0)
        bucket = _price_bucket_label(price, price_bucket_pct)
        state_key = f"{symbol}|{signal}|{bucket}"
        last_sent = float(state.get(state_key, 0.0))
        if cooldown_seconds > 0 and (now_ts - last_sent) < cooldown_seconds:
            continue
        message = _build_whatsapp_message(payload)
        try:
            response = green_api.sending.sendMessage(chat_id, message)
            status_code, status_data = _response_status_details(response)
            if status_code in (200, 201):
                sent += 1
                state[state_key] = now_ts
            else:
                ticker = payload.get("Ticker", "UNKNOWN")
                print(
                    f"WhatsApp send failed for {ticker}: status={status_code}, data={status_data}",
                    file=sys.stderr,
                )
        except Exception as exc:  # pragma: no cover - network/API surface
            ticker = payload.get("Ticker", "UNKNOWN")
            print(f"WhatsApp send failed for {ticker}: {exc}", file=sys.stderr)

    if isinstance(state_file, Path):
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(
                json.dumps(state, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"Could not persist WhatsApp notify state: {exc}", file=sys.stderr)

    return sent


def compute_chart_signal_from_ohlcv(
    ticker_symbol: str,
    df_in: pd.DataFrame,
    summary: dict[str, Any],
    pivot_left: int = _DEFAULT_PIVOT_LEFT,
    pivot_right: int = _DEFAULT_PIVOT_RIGHT,
    atr_proximity_mult: float = _DEFAULT_ATR_PROX_MULT,
) -> dict[str, Any]:
    """
    Run pivot / ATR / candle heuristics on a DataFrame with columns
    Open, High, Low, Close, Volume (and optional datetime index).
    `summary` should match keys used by CSV export (Period used, Bars loaded, …).
    """
    need = pivot_left + pivot_right + 20
    if len(df_in) < need:
        out_sum = dict(summary)
        out_sum["Bars loaded"] = len(df_in)
        return {
            "Ticker": ticker_symbol,
            "error": f"Need at least {need} bars for pivots/ATR; got {len(df_in)}.",
            **out_sum,
        }

    df = df_in.copy()
    for col in ("Open", "High", "Low", "Close"):
        if col not in df.columns:
            return {
                "Ticker": ticker_symbol,
                "error": f"Missing column {col}; expected Open, High, Low, Close.",
                **summary,
            }

    atr = _atr14(df)
    atr_tail = float(atr.iloc[-1])
    close = float(df["Close"].iloc[-1])

    if pd.isna(atr_tail) or not math.isfinite(atr_tail):
        return {
            "Ticker": ticker_symbol,
            "error": "ATR14 not available on last bar.",
            **summary,
        }

    piv_lo = pivot_low_prices(df, pivot_left, pivot_right)
    piv_hi = pivot_high_prices(df, pivot_left, pivot_right)
    sup = nearest_support_below(close, piv_lo)
    res = nearest_resistance_above(close, piv_hi)

    dist_sup_pct = ""
    if sup is not None and sup > 0:
        dist_sup_pct = f"{round((close / sup - 1) * 100, 2)}%"

    dist_res_pct = ""
    if res is not None and res > 0:
        dist_res_pct = f"{round((1 - close / res) * 100, 2)}%"

    pattern = classify_latest_pattern(df)
    signal, reason = heuristic_signal_from_chart(
        close, atr_tail, sup, res, pattern, atr_proximity_mult
    )

    out_sum = dict(summary)
    out_sum["Bars loaded"] = len(df_in)

    return {
        "Ticker": ticker_symbol,
        **out_sum,
        "Current Price": round(close, 2),
        "ATR14": round(atr_tail, 4),
        "Nearest Support": round(sup, 2) if sup is not None else "",
        "Distance To Support %": dist_sup_pct,
        "Nearest Resistance": round(res, 2) if res is not None else "",
        "Distance To Resistance %": dist_res_pct,
        "Pivot Lows Detected": len(piv_lo),
        "Pivot Highs Detected": len(piv_hi),
        "Candle Pattern": pattern,
        "Signal": signal,
        "Signal Reason": reason,
    }


def get_support_chart_signal(
    ticker_symbol: str,
    pivot_left: int = _DEFAULT_PIVOT_LEFT,
    pivot_right: int = _DEFAULT_PIVOT_RIGHT,
    atr_proximity_mult: float = _DEFAULT_ATR_PROX_MULT,
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

    return compute_chart_signal_from_ohlcv(
        ticker_symbol,
        df,
        summary,
        pivot_left=pivot_left,
        pivot_right=pivot_right,
        atr_proximity_mult=atr_proximity_mult,
    )


def chart_signal_to_csv_row(symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    err = payload.get("error")
    if err or "Current Price" not in payload:
        return {
            "Symbol": symbol,
            "Period Used": err or "Unknown error",
            "Bars Loaded": payload.get("Bars loaded", ""),
            "Meet Recommended bar count": "",
            "Recommended Mn Bars": payload.get("Recommended min bars", ""),
            "Current Price": "",
            "ATR14": "",
            "Nearest Support": "",
            "Distance To Support %": "",
            "Nearest Resistance": "",
            "Distance To Resistance %": "",
            "Pivot Lows Detected": "",
            "Pivot Highs Detected": "",
            "Candle Pattern": "",
            "Signal": "",
            "Signal Reason": "",
        }

    meets = payload.get("Meets recommended bar count")
    return {
        "Symbol": symbol,
        "Period Used": payload.get("Period used (yfinance)", ""),
        "Bars Loaded": payload.get("Bars loaded", ""),
        "Meet Recommended bar count": "Yes" if meets else "No",
        "Recommended Mn Bars": payload.get("Recommended min bars", ""),
        "Current Price": payload.get("Current Price", ""),
        "ATR14": payload.get("ATR14", ""),
        "Nearest Support": payload.get("Nearest Support", ""),
        "Distance To Support %": payload.get("Distance To Support %", ""),
        "Nearest Resistance": payload.get("Nearest Resistance", ""),
        "Distance To Resistance %": payload.get("Distance To Resistance %", ""),
        "Pivot Lows Detected": payload.get("Pivot Lows Detected", ""),
        "Pivot Highs Detected": payload.get("Pivot Highs Detected", ""),
        "Candle Pattern": payload.get("Candle Pattern", ""),
        "Signal": payload.get("Signal", ""),
        "Signal Reason": payload.get("Signal Reason", ""),
    }


if __name__ == "__main__":
    _configure_stdio_utf8()
    argp = argparse.ArgumentParser(
        description="Chart pivot support/heuristic signals; optional watch during session."
    )
    argp.add_argument(
        "--once",
        action="store_true",
        help="Single run even if chart_watch_enabled=true in config.ini",
    )
    argp.add_argument(
        "--symbol",
        default=None,
        metavar="TICKER",
        help="Single symbol override (e.g. AAPL). Overrides config.ini [trading] symbols.",
    )
    argp.add_argument(
        "--symbols",
        default=None,
        metavar="A,B,C",
        help="Comma-separated symbol list override. Do not combine with --symbol.",
    )
    args = argp.parse_args()

    cfg_path = Path(__file__).resolve().parent / "config.ini"
    pivot_left, pivot_right, atr_prox = load_chart_scan_params(cfg_path)
    notify_cfg = load_whatsapp_notify_params(cfg_path)

    try:
        watch_cfg = load_chart_watch_params(cfg_path)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    symbols_override: list[str] | None = None
    if args.symbol or args.symbols:
        try:
            try:
                config_symbols, _ = load_symbols_from_config(
                    path=cfg_path,
                    output_csv_key="output_csv_chart_support",
                    output_csv_fallback="chart_support_signals.csv",
                )
            except ValueError:
                config_symbols = []
            symbols_override = resolve_symbol_list(
                symbol=args.symbol,
                symbols=args.symbols,
                config_symbols=config_symbols,
            )
        except ValueError as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)

    use_watch_loop = watch_cfg.get("enabled", False) and not args.once

    if use_watch_loop:
        try:
            _ = ZoneInfo(str(watch_cfg.get("timezone") or _DEFAULT_CHART_WATCH_TZ))
        except Exception as exc:
            print(
                f"Configure chart_watch_timezone (IANA zone, e.g. America/New_York). "
                f"On Windows: pip install tzdata. Error: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

        print(
            "Watch mode: runs only inside session window (timezone "
            f"{watch_cfg.get('timezone')}). "
            "Data is daily Yahoo bars; intraday fills may lag—use brokers for live execution."
        )
        print(f"Poll every {watch_cfg['interval_seconds']} s. Ctrl+C to stop.")

        try:
            while True:
                try:
                    open_now, reason = _us_regular_session_open(watch_cfg)
                except RuntimeError as exc:
                    print(exc, file=sys.stderr)
                    sys.exit(1)

                if open_now:
                    try:
                        errors, _, _ = run_chart_scan_job(
                            cfg_path,
                            pivot_left,
                            pivot_right,
                            atr_prox,
                            notify_cfg,
                            symbols_override=symbols_override,
                        )
                    except (OSError, ValueError) as exc:
                        print(exc, file=sys.stderr)
                        errors = 1
                    if errors:
                        sys.exit(1)
                elif watch_cfg.get("log_when_closed"):
                    tz = ZoneInfo(str(watch_cfg.get("timezone") or _DEFAULT_CHART_WATCH_TZ))
                    stamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
                    print(f"[{stamp}] Market closed/skipped ({reason}).")

                time.sleep(int(watch_cfg["interval_seconds"]))
        except KeyboardInterrupt:
            print("\nWatch stopped.")
            sys.exit(0)
    else:
        try:
            errors, _, _ = run_chart_scan_job(
                cfg_path,
                pivot_left,
                pivot_right,
                atr_prox,
                notify_cfg,
                symbols_override=symbols_override,
            )
        except (OSError, ValueError) as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)
        if errors:
            sys.exit(1)
