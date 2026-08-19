#!/usr/bin/env python3
"""
Green API WhatsApp stock monitor + command listener (consolidated alert app).

Runs two loops in one process:
  - Price monitor   — polls Yahoo Finance every CHECK_INTERVAL seconds; sends a
                      WhatsApp alert when a stock moves beyond a configured %.
  - Command listener— polls Green API for incoming/outgoing WhatsApp messages.

Supported commands (send to linked WhatsApp or from the Green API web console):
  STATUS              — confirm listener is online; lists tracked symbols
  SUPPORT AAPL        — 3 recent pivot support levels (6-month Yahoo history)
  SOLD  or  SEND      — run CompletelySoldAlert digest on demand
  WATCHLIST           — show current watchlist symbols and reference prices

Extras:
  - Single-instance Windows named mutex (prevents two listeners racing on the
    same Green API instance and causing 502 RMQ_ERROR / dropped messages).
  - External heartbeat (dead-man's switch): listener pings a URL every N seconds
    so an external service (e.g. healthchecks.io) can alert your phone if the
    whole machine goes down. Configure via LISTENER_HEARTBEAT_URL env var,
    heartbeat_url.txt in this folder, or config.ini [monitoring] heartbeat_url.

Credentials (pick any — later sources override earlier):
  1. Environment variables: GREEN_API_ID_INSTANCE, GREEN_API_TOKEN,
     WHATSAPP_TARGET_PHONE
  2. AlertApp/secrets.local.ini  [whatsapp]  (gitignored)
  3. AlertApp/config.ini         [whatsapp]
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import yfinance as yf
from whatsapp_api_client_python import API

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
INVESTMENT_ROOT = SCRIPT_DIR.parent
if str(INVESTMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(INVESTMENT_ROOT))

from shared.alert_watchlist import load_watchlist  # noqa: E402
from shared.config_loader import green_api_credentials, read_merged_ini  # noqa: E402

SOLD_ALERT_BAT = INVESTMENT_ROOT / "CompletelySoldAlert" / "run-alert.bat"
_HEARTBEAT_URL_FILE = SCRIPT_DIR / "heartbeat_url.txt"

# ---------------------------------------------------------------------------
# Single-instance lock (Windows named mutex)
# Green API allows only ONE active receiveNotification consumer per instance.
# Two listeners cause "consumer closed" (502 RMQ_ERROR) and dropped messages.
# ---------------------------------------------------------------------------
_SINGLE_INSTANCE_MUTEX_NAME = "Global\\AlertApp_GreenAPI_Listener"
_ERROR_ALREADY_EXISTS = 183
_single_instance_handle = None  # kept alive for process lifetime


def _acquire_single_instance_lock() -> bool:
    """Return True if this is the only listener; False if one already runs."""
    global _single_instance_handle
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, _SINGLE_INSTANCE_MUTEX_NAME)
        last_error = kernel32.GetLastError()
    except Exception as exc:  # noqa: BLE001
        print(f"[!] Single-instance check skipped ({exc}).", flush=True)
        return True
    if not handle:
        return True
    if last_error == _ERROR_ALREADY_EXISTS:
        return False
    _single_instance_handle = handle
    return True


# ---------------------------------------------------------------------------
# stdio
# ---------------------------------------------------------------------------
def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError, AttributeError):
                pass


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def _load_settings() -> tuple[str, str, str, int, int]:
    parser = read_merged_ini(SCRIPT_DIR)
    id_inst, token, phone = green_api_credentials(parser, section="whatsapp")
    # Fall back to [trading] section (AutomatedTrading style)
    if (not id_inst or not token or not phone) and parser.has_section("trading"):
        id_inst, token, phone = green_api_credentials(parser, section="trading")
    if not id_inst or not token or not phone:
        raise RuntimeError(
            "WhatsApp credentials missing.\n"
            "Copy AlertApp/config.ini.example → config.ini, then\n"
            "copy AlertApp/secrets.local.ini.example → secrets.local.ini\n"
            "and fill in your Green API credentials.\n"
            "Or set GREEN_API_ID_INSTANCE / GREEN_API_TOKEN / WHATSAPP_TARGET_PHONE env vars."
        )
    check_interval = 600
    poll_seconds = 2
    if parser.has_section("whatsapp"):
        check_interval = parser.getint("whatsapp", "check_interval_seconds", fallback=600)
        poll_seconds = parser.getint("whatsapp", "command_poll_seconds", fallback=2)
    return id_inst, token, phone, check_interval, poll_seconds


def _load_heartbeat_url() -> str:
    """Heartbeat ping URL from env, heartbeat_url.txt, or config.ini [monitoring]."""
    url = os.environ.get("LISTENER_HEARTBEAT_URL", "").strip()
    if url:
        return url
    if _HEARTBEAT_URL_FILE.is_file():
        url = _HEARTBEAT_URL_FILE.read_text(encoding="utf-8").strip()
        if url:
            return url
    parser = read_merged_ini(SCRIPT_DIR)
    if parser.has_section("monitoring"):
        url = parser.get("monitoring", "heartbeat_url", fallback="").strip()
    return url


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------
HEARTBEAT_INTERVAL_SECONDS = 300


def send_heartbeat(url: str) -> None:
    """Best-effort GET to the heartbeat URL; never disrupts the listener."""
    if not url:
        return
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"[!] Heartbeat ping failed: {exc}", flush=True)


# ---------------------------------------------------------------------------
# Initialise (module-level so watchdog can import without running)
# ---------------------------------------------------------------------------
_configure_stdio_utf8()
ID_INSTANCE, API_TOKEN_INSTANCE, TARGET_PHONE, CHECK_INTERVAL, POLL_SECONDS = _load_settings()
WATCHLIST = load_watchlist(SCRIPT_DIR)
greenAPI = API.GreenAPI(ID_INSTANCE, API_TOKEN_INSTANCE)


# ---------------------------------------------------------------------------
# WhatsApp send
# ---------------------------------------------------------------------------
def send_whatsapp(text: str) -> None:
    chat_id = f"{TARGET_PHONE}@c.us"
    response = greenAPI.sending.sendMessage(chat_id, text)
    if response.code != 200:
        print(f"Send failed: {getattr(response, 'error', response.code)}", flush=True)


# ---------------------------------------------------------------------------
# Price monitor
# ---------------------------------------------------------------------------
def monitor_stocks() -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] Periodic stock check...", flush=True)

    for symbol, config in WATCHLIST.items():
        ref_price, up_pct, down_pct = config
        try:
            data = yf.Ticker(symbol).history(period="1d")
        except Exception as exc:
            print(f"  [{symbol}] fetch error: {exc}", flush=True)
            continue
        if data.empty:
            continue

        current_price = float(data["Close"].iloc[-1])
        change = ((current_price - ref_price) / ref_price) * 100
        print(f"  {symbol}: ${current_price:.2f} ({change:+.2f}%)", flush=True)

        if change >= up_pct:
            send_whatsapp(
                f"🚀 *UP ALERT*: {symbol}\n"
                f"Price: ${current_price:.2f}  Change: {change:+.2f}%"
            )
        elif change <= -down_pct:
            send_whatsapp(
                f"📉 *DOWN ALERT*: {symbol}\n"
                f"Price: ${current_price:.2f}  Change: {change:+.2f}%"
            )


# ---------------------------------------------------------------------------
# SUPPORT command helper
# ---------------------------------------------------------------------------
def get_support_levels(symbol: str) -> list[float]:
    """Pivot lows from last 6 months (Yahoo Finance)."""
    try:
        df = yf.Ticker(symbol).history(period="6mo")
        if df.empty:
            return []
        levels: list[float] = []
        for i in range(2, len(df) - 2):
            low = df["Low"].iloc[i]
            if (
                low < df["Low"].iloc[i - 1]
                and low < df["Low"].iloc[i - 2]
                and low < df["Low"].iloc[i + 1]
                and low < df["Low"].iloc[i + 2]
            ):
                levels.append(round(float(low), 2))
        cleaned: list[float] = []
        for s in sorted(levels):
            if not cleaned or abs(s - cleaned[-1]) > s * 0.015:
                cleaned.append(s)
        return cleaned[-3:]
    except Exception as exc:
        print(f"Support calc error: {exc}", flush=True)
        return []


# ---------------------------------------------------------------------------
# SOLD / SEND command helper
# ---------------------------------------------------------------------------
def run_sold_alert() -> tuple[bool, str]:
    """Launch CompletelySoldAlert run-alert.bat; it sends its own WhatsApp digest."""
    if not SOLD_ALERT_BAT.is_file():
        return False, f"run-alert.bat not found at {SOLD_ALERT_BAT}"
    try:
        result = subprocess.run(
            [str(SOLD_ALERT_BAT), "run", "--force-market-day"],
            cwd=str(SOLD_ALERT_BAT.parent),
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return False, "timed out after 300 s"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    tail = (result.stdout or result.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit code {result.returncode}"
    return result.returncode == 0, detail


# ---------------------------------------------------------------------------
# Command dispatcher
# ---------------------------------------------------------------------------
_INCOMING_TYPES = {"incomingMessageReceived"}
_OUTGOING_TYPES = {"outgoingMessageReceived", "outgoingAPIMessageReceived"}
_MESSAGE_TYPES = _INCOMING_TYPES | _OUTGOING_TYPES


def _extract_text(body: dict) -> str:
    data = body.get("messageData", {}) or {}
    text = data.get("textMessageData", {}).get("textMessage")
    if not text:
        text = data.get("extendedTextMessageData", {}).get("text")
    return (text or "").upper().strip()


def handle_command(msg_text: str, *, is_outgoing: bool) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if msg_text == "STATUS":
        symbols = ", ".join(WATCHLIST.keys()) or "none"
        send_whatsapp(
            f"✅ *AlertApp Online*\nLast poll: {now}\n"
            f"Tracking: {symbols}\n"
            "Commands: STATUS | WATCHLIST | SUPPORT SYMBOL | SOLD | SEND"
        )
        print(f"[{now}] Replied to STATUS", flush=True)

    elif msg_text == "WATCHLIST":
        lines = [f"  {sym}: ref=${cfg[0]:.2f}  ↑{cfg[1]}%  ↓{cfg[2]}%" for sym, cfg in WATCHLIST.items()]
        send_whatsapp("📋 *Current watchlist:*\n" + "\n".join(lines))
        print(f"[{now}] Replied to WATCHLIST", flush=True)

    elif msg_text in ("SOLD", "SEND"):
        print(f"[{now}] {msg_text} command; running run-alert.bat", flush=True)
        send_whatsapp("⏳ Running Completely Sold price summary...")
        ok, detail = run_sold_alert()
        if not ok:
            send_whatsapp(f"❌ Completely Sold run failed: {detail}")
        print(f"[{now}] {msg_text} ok={ok} {detail}", flush=True)

    elif msg_text.startswith("SUPPORT "):
        parts = msg_text.split()
        if len(parts) < 2:
            send_whatsapp("Usage: SUPPORT SYMBOL  (e.g. SUPPORT AAPL)")
        else:
            symbol = parts[1]
            send_whatsapp(f"🔍 Analysing {symbol} support levels...")
            levels = get_support_levels(symbol)
            if levels:
                send_whatsapp(
                    f"*Support levels for {symbol}:*\n"
                    + "\n".join(f"📍 ${lvl}" for lvl in levels)
                )
            else:
                send_whatsapp(f"❌ Could not find support levels for {symbol}.")
            print(f"[{now}] SUPPORT {symbol} → {levels}", flush=True)

    # Never reply "unknown command" to outgoing messages: the listener's own
    # replies are outgoing and would cause an endless reply loop.
    elif msg_text and not is_outgoing:
        send_whatsapp(
            "❓ Unknown command.\n"
            "Try: *STATUS* | *WATCHLIST* | *SUPPORT AAPL* | *SOLD*"
        )
        print(f"[{now}] Unknown command: {msg_text!r}", flush=True)


def check_commands() -> None:
    try:
        resp = greenAPI.receiving.receiveNotification()
        if resp.code != 200 or not resp.data:
            return
        notification = resp.data
        receipt_id = notification.get("receiptId")
        body = notification.get("body") or {}
        type_webhook = body.get("typeWebhook")
        if type_webhook in _MESSAGE_TYPES:
            msg_text = _extract_text(body)
            if msg_text:
                handle_command(msg_text, is_outgoing=type_webhook in _OUTGOING_TYPES)
        if receipt_id is not None:
            greenAPI.receiving.deleteNotification(receipt_id)
    except Exception as exc:
        print(f"Command poll error: {exc}", flush=True)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not _acquire_single_instance_lock():
        print(
            "[X] Another AlertApp listener is already running.\n"
            "    Exiting to avoid Green API race condition (one consumer per instance).",
            flush=True,
        )
        sys.exit(1)

    print("[*] AlertApp started (price monitor + command listener).", flush=True)
    print(f"    Instance: {ID_INSTANCE}  Target: {TARGET_PHONE}", flush=True)
    print(f"    Watchlist: {', '.join(WATCHLIST.keys())}", flush=True)
    print(f"    Price check interval: {CHECK_INTERVAL}s  Poll: {POLL_SECONDS}s", flush=True)
    print("    Commands: STATUS | WATCHLIST | SUPPORT SYMBOL | SOLD | SEND", flush=True)

    heartbeat_url = _load_heartbeat_url()
    if heartbeat_url:
        print(f"    Heartbeat: enabled (every {HEARTBEAT_INTERVAL_SECONDS}s)", flush=True)
        send_heartbeat(heartbeat_url)
    else:
        print(
            "    Heartbeat: disabled "
            "(set LISTENER_HEARTBEAT_URL, heartbeat_url.txt, or config.ini [monitoring])",
            flush=True,
        )
    last_heartbeat = time.monotonic()
    last_stock_check = 0.0

    while True:
        check_commands()

        now_mono = time.monotonic()
        if now_mono - last_stock_check >= CHECK_INTERVAL:
            monitor_stocks()
            last_stock_check = now_mono

        if heartbeat_url and (now_mono - last_heartbeat) >= HEARTBEAT_INTERVAL_SECONDS:
            send_heartbeat(heartbeat_url)
            last_heartbeat = now_mono

        time.sleep(POLL_SECONDS)
