#!/usr/bin/env python3
"""
Monitor one or more stock symbols against up/down percentage thresholds and notify WhatsApp.
Configuration: INI file (see config.ini.example). Use [stock] symbols = A, B, C or legacy symbol = X.
Secrets stay out of code.
"""

from __future__ import annotations

import argparse
import configparser
import logging
import sys
import time
from pathlib import Path

import requests
import yfinance as yf

LOG = logging.getLogger("stock_monitor")


def parse_fixed_reference_map(
    st: configparser.SectionProxy, symbols: list[str]
) -> dict[str, float]:
    """
    When use_configured_reference_prices = true, parse reference_prices as a
    comma-separated list aligned 1:1 with symbols (same order).
    """
    raw_flag = (st.get("use_configured_reference_prices") or "").strip().lower()
    use_fixed = raw_flag in ("1", "true", "yes", "on")
    if not use_fixed:
        return {}
    raw = st.get("reference_prices", "").strip()
    if not raw:
        raise ValueError(
            "use_configured_reference_prices=true requires reference_prices = price1, price2, ... "
            "(same count and order as symbols)"
        )
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) != len(symbols):
        raise ValueError(
            f"reference_prices has {len(parts)} value(s) but symbols has {len(symbols)}; counts must match."
        )
    return {sym: float(val) for sym, val in zip(symbols, parts)}


def parse_symbols(st: configparser.SectionProxy) -> list[str]:
    """
    Read comma-separated stock.symbols, or fall back to stock.symbol for one ticker.
    """
    raw = st.get("symbols", "").strip()
    if raw:
        parts = [p.strip().upper() for p in raw.split(",") if p.strip()]
        if parts:
            return parts
    single = st.get("symbol", "").strip().upper()
    if single:
        return [single]
    raise ValueError('Configure [stock] symbols = TICKER1, TICKER2 or symbol = TICKER')


def load_config(path: Path) -> configparser.ConfigParser:
    if not path.is_file():
        raise FileNotFoundError(
            f"Config not found: {path}. Copy config.ini.example to config.ini and edit."
        )
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    return cp


def get_current_price(symbol: str) -> float:
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="10d", auto_adjust=True)
    if hist.empty:
        raise ValueError(f"No price history for symbol '{symbol}'")
    return float(hist["Close"].iloc[-1])


def get_reference_and_current(
    symbol: str,
    reference_mode: str,
    configured_reference: float | None = None,
) -> tuple[float, float, str]:
    """
    Returns (reference_price, current_price, reference_label) for percent change:
    percent_change = (current - reference) / reference * 100
    """
    if configured_reference is not None:
        if configured_reference <= 0:
            raise ValueError(f"Configured reference price must be positive for {symbol}")
        current = get_current_price(symbol)
        return configured_reference, current, "configured"

    mode = (reference_mode or "previous_close").strip().lower()
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="10d", auto_adjust=True)
    if hist.empty:
        raise ValueError(f"No price history for symbol '{symbol}'")

    current = float(hist["Close"].iloc[-1])

    if mode == "open":
        reference = float(hist["Open"].iloc[-1])
    elif mode == "previous_close":
        if len(hist) < 2:
            raise ValueError("Need at least two trading days for reference=previous_close")
        reference = float(hist["Close"].iloc[-2])
    else:
        raise ValueError(f"Unknown reference mode: {reference_mode!r} (use open or previous_close)")

    return reference, current, mode


def percent_change(reference: float, current: float) -> float:
    if reference == 0:
        raise ValueError("Reference price is zero")
    return (current - reference) / reference * 100.0


def send_whatsapp_callmebot(phone: str, apikey: str, message: str) -> None:
    phone = phone.strip().replace("+", "").replace(" ", "")
    url = "https://api.callmebot.com/whatsapp.php"
    resp = requests.get(
        url,
        params={"phone": phone, "text": message, "apikey": apikey},
        timeout=60,
    )
    resp.raise_for_status()
    body = (resp.text or "").strip()
    if body and "success" not in body.lower() and "queued" not in body.lower():
        LOG.warning("CallMeBot response: %s", body[:500])


def send_whatsapp_twilio(
    account_sid: str,
    auth_token: str,
    from_whatsapp: str,
    to_whatsapp: str,
    message: str,
) -> None:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    resp = requests.post(
        url,
        data={"From": from_whatsapp, "To": to_whatsapp, "Body": message},
        auth=(account_sid, auth_token),
        timeout=60,
    )
    resp.raise_for_status()


def send_alert(cp: configparser.ConfigParser, message: str) -> None:
    section = cp["whatsapp"]
    method = section.get("method", "callmebot").strip().lower()
    if method == "callmebot":
        phone = section.get("phone", "").strip()
        apikey = section.get("apikey", "").strip()
        if not phone or not apikey or apikey.startswith("YOUR_"):
            raise ValueError("whatsapp.phone and whatsapp.apikey must be set for callmebot")
        send_whatsapp_callmebot(phone, apikey, message)
        LOG.info("WhatsApp notification sent (callmebot).")
    elif method == "twilio":
        sid = section.get("account_sid", "").strip()
        token = section.get("auth_token", "").strip()
        from_w = section.get("from_whatsapp", "").strip()
        to_w = section.get("to_whatsapp", "").strip()
        if not all([sid, token, from_w, to_w]):
            raise ValueError("Twilio requires account_sid, auth_token, from_whatsapp, to_whatsapp")
        send_whatsapp_twilio(sid, token, from_w, to_w, message)
        LOG.info("WhatsApp notification sent (twilio).")
    else:
        raise ValueError(f"Unknown whatsapp.method: {method!r}")


def run_loop(cp: configparser.ConfigParser) -> None:
    st = cp["stock"]
    symbols = parse_symbols(st)
    fixed_map = parse_fixed_reference_map(st, symbols)

    up_thr = float(st.get("up_percent", "2.0"))
    down_thr = float(st.get("down_percent", "2.0"))
    if up_thr <= 0 or down_thr <= 0:
        raise ValueError("stock.up_percent and stock.down_percent must be positive")

    interval = int(st.get("check_interval_seconds", "300"))
    reference_mode = st.get("reference", "previous_close")
    cooldown = int(st.get("alert_cooldown_seconds", "3600"))

    last_alert_ts: dict[str, float] = {}

    ref_desc = (
        "configured reference_prices (per symbol)"
        if fixed_map
        else reference_mode
    )
    LOG.info(
        "Monitoring %s | alert if change >= +%.2f%% or <= -%.2f%% vs %s | cycle every %ss | per-symbol cooldown %ss",
        ", ".join(symbols),
        up_thr,
        down_thr,
        ref_desc,
        interval,
        cooldown,
    )

    while True:
        for symbol in symbols:
            try:
                cfg_ref = fixed_map.get(symbol)
                ref, cur, ref_label = get_reference_and_current(
                    symbol, reference_mode, cfg_ref
                )
                pct = percent_change(ref, cur)
                LOG.info(
                    "%s reference=%.4f (%s) current=%.4f change=%+.2f%%",
                    symbol,
                    ref,
                    ref_label,
                    cur,
                    pct,
                )

                triggered = pct >= up_thr or pct <= -down_thr
                now = time.time()
                last_ts = last_alert_ts.get(symbol, 0.0)
                if triggered and (now - last_ts) >= cooldown:
                    direction = "UP" if pct > 0 else "DOWN"
                    msg = (
                        f"Stock alert ({symbol})\n"
                        f"Change: {pct:+.2f}% ({direction})\n"
                        f"Reference ({ref_label}): {ref:.4f}\n"
                        f"Current: {cur:.4f}\n"
                        f"Thresholds: +{up_thr:.2f}% / -{down_thr:.2f}%"
                    )
                    send_alert(cp, msg)
                    last_alert_ts[symbol] = now
                elif triggered:
                    LOG.info("%s: threshold hit but cooldown active; skipping send.", symbol)

            except Exception as e:
                LOG.exception("Check failed for %s: %s", symbol, e)

        time.sleep(max(interval, 30))


def main() -> int:
    parser = argparse.ArgumentParser(description="Stock % monitor -> WhatsApp (INI config).")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "config.ini",
        help="Path to config.ini",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch once, log result, exit (no loop, no WhatsApp unless threshold hit).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        cp = load_config(args.config)
    except FileNotFoundError as e:
        LOG.error("%s", e)
        return 1

    if args.once:
        st = cp["stock"]
        symbols = parse_symbols(st)
        fixed_map = parse_fixed_reference_map(st, symbols)
        reference_mode = st.get("reference", "previous_close")
        up_thr = float(st.get("up_percent", "2.0"))
        down_thr = float(st.get("down_percent", "2.0"))
        for symbol in symbols:
            try:
                ref, cur, ref_label = get_reference_and_current(
                    symbol, reference_mode, fixed_map.get(symbol)
                )
                pct = percent_change(ref, cur)
                print(
                    f"{symbol} ref={ref:.4f} ({ref_label}) current={cur:.4f} change={pct:+.2f}%"
                )
                if pct >= up_thr or pct <= -down_thr:
                    send_alert(
                        cp,
                        f"Stock alert ({symbol})\nChange: {pct:+.2f}%\n"
                        f"Ref ({ref_label}): {ref:.4f} Current: {cur:.4f}",
                    )
            except Exception as e:
                LOG.error("%s: %s", symbol, e)
        return 0

    try:
        run_loop(cp)
    except KeyboardInterrupt:
        LOG.info("Stopped by user.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
