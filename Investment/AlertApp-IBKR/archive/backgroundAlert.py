"""
Green API WhatsApp command listener (AlertApp-IBKR).

Commands (send to your linked WhatsApp / Green API instance):
  STATUS           — confirm listener is online
  SUPPORT AAPL     — return pivot support levels (6mo Yahoo history)
  SOLD             — run CompletelySoldAlert digest (all completely sold prices)
  SEND             — same as SOLD

Credentials: config.ini in this folder, or AutomatedTrading\\config.ini, or env vars.
"""

from __future__ import annotations

import configparser
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

SCRIPT_DIR = Path(__file__).resolve().parent
AUTOMATED_TRADING_INI = SCRIPT_DIR.parent / "AutomatedTrading" / "config.ini"
SOLD_ALERT_BAT = SCRIPT_DIR.parent / "CompletelySoldAlert" / "run-alert.bat"
POLL_SECONDS = 2

# External heartbeat (dead-man's switch). The listener periodically pings a URL
# (e.g. a healthchecks.io check). If the machine dies / loses power / loses
# internet, the pings stop and the EXTERNAL service alerts your phone — the only
# reliable way to detect a fully-down machine, since a down machine cannot warn
# you itself. Configure via LISTENER_HEARTBEAT_URL env var, heartbeat_url.txt in
# this folder, or [monitoring] heartbeat_url in config.ini. Disabled if unset.
HEARTBEAT_INTERVAL_SECONDS = 300
_HEARTBEAT_URL_FILE = SCRIPT_DIR / "heartbeat_url.txt"

# Green API allows only ONE active receiveNotification consumer per instance.
# Two listeners polling the same instance cause "consumer closed" (502 RMQ_ERROR)
# and dropped/delayed commands. Enforce a single instance with a named mutex
# (auto-released by the OS if the process dies, so no stale-lock problem).
_SINGLE_INSTANCE_MUTEX_NAME = "Global\\AlertApp_IBKR_GreenAPI_Listener"
_ERROR_ALREADY_EXISTS = 183
_single_instance_handle = None  # keep the handle alive for the process lifetime


def _acquire_single_instance_lock() -> bool:
    """Return True if this is the only listener; False if one already runs.

    Uses a Windows named mutex. On non-Windows (or if the call fails), it
    degrades gracefully and allows startup.
    """
    global _single_instance_handle
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, _SINGLE_INSTANCE_MUTEX_NAME)
        last_error = kernel32.GetLastError()
    except Exception as exc:  # noqa: BLE001 - never block startup on lock errors
        print(f"[!] Single-instance check skipped ({exc}).", flush=True)
        return True

    if not handle:
        print("[!] Single-instance check skipped (no mutex handle).", flush=True)
        return True
    if last_error == _ERROR_ALREADY_EXISTS:
        return False

    _single_instance_handle = handle
    return True


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError, AttributeError):
                pass


def _load_whatsapp_config() -> tuple[str, str, str]:
    id_inst = os.environ.get("GREEN_API_ID_INSTANCE", "").strip()
    token = os.environ.get("GREEN_API_TOKEN", "").strip()
    phone = os.environ.get("WHATSAPP_TARGET_PHONE", "").strip()

    for ini_path in (SCRIPT_DIR / "config.ini", AUTOMATED_TRADING_INI):
        if not ini_path.is_file():
            continue
        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8")
        section = parser["trading"] if parser.has_section("trading") else parser["whatsapp"] if parser.has_section("whatsapp") else {}
        id_inst = id_inst or section.get("whatsapp_id_instance", section.get("id_instance", "")).strip()
        token = token or section.get("whatsapp_api_token_instance", section.get("api_token", "")).strip()
        phone = phone or section.get("whatsapp_target_phone", section.get("target_phone", "")).strip()
        if id_inst and token and phone:
            break

    if not id_inst or not token or not phone:
        raise RuntimeError(
            "WhatsApp credentials missing. Set GREEN_API_* env vars or configure "
            f"{AUTOMATED_TRADING_INI} [trading] whatsapp_* keys."
        )
    return id_inst, token, phone


def _load_heartbeat_url() -> str:
    """Heartbeat ping URL from env, heartbeat_url.txt, or [monitoring] in ini."""
    url = os.environ.get("LISTENER_HEARTBEAT_URL", "").strip()
    if url:
        return url
    if _HEARTBEAT_URL_FILE.is_file():
        url = _HEARTBEAT_URL_FILE.read_text(encoding="utf-8").strip()
        if url:
            return url
    for ini_path in (SCRIPT_DIR / "config.ini", AUTOMATED_TRADING_INI):
        if not ini_path.is_file():
            continue
        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8")
        if parser.has_section("monitoring"):
            url = parser["monitoring"].get("heartbeat_url", "").strip()
            if url:
                return url
    return ""


def send_heartbeat(url: str) -> None:
    """Best-effort GET to the heartbeat URL; never disrupts the listener."""
    if not url:
        return
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            resp.read()
    except Exception as exc:  # noqa: BLE001 - heartbeat must not crash listener
        print(f"[!] Heartbeat ping failed: {exc}", flush=True)


_configure_stdio_utf8()
ID_INSTANCE, API_TOKEN_INSTANCE, TARGET_PHONE = _load_whatsapp_config()
greenAPI = API.GreenAPI(ID_INSTANCE, API_TOKEN_INSTANCE)


def get_support_levels(symbol: str) -> list[float]:
    """Pivot lows from last 6 months (Yahoo Finance)."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo")
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
            if not cleaned or abs(s - cleaned[-1]) > (s * 0.015):
                cleaned.append(s)
        return cleaned[-3:]
    except Exception as exc:
        print(f"Support Calc Error: {exc}")
        return []


def run_sold_alert() -> tuple[bool, str]:
    """Launch CompletelySoldAlert run-alert.bat; it sends its own WhatsApp digest."""
    if not SOLD_ALERT_BAT.is_file():
        return False, f"run-alert.bat not found at {SOLD_ALERT_BAT}"
    try:
        # --force-market-day: SOLD/SEND is an explicit on-demand request, so
        # produce the price summary even on weekends / NYSE holidays.
        result = subprocess.run(
            [str(SOLD_ALERT_BAT), "run", "--force-market-day"],
            cwd=str(SOLD_ALERT_BAT.parent),
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return False, "timed out after 300s"
    except Exception as exc:  # noqa: BLE001 - report any launch failure
        return False, str(exc)

    tail = (result.stdout or result.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit code {result.returncode}"
    return result.returncode == 0, detail


def send_whatsapp(text: str) -> None:
    chat_id = f"{TARGET_PHONE}@c.us"
    response = greenAPI.sending.sendMessage(chat_id, text)
    if response.code != 200:
        print(f"Send failed: {getattr(response, 'error', response.code)}")


# Message webhook types we react to. "outgoing*" lets you trigger commands by
# messaging from the linked phone itself or the Green API web console.
_INCOMING_TYPES = {"incomingMessageReceived"}
_OUTGOING_TYPES = {"outgoingMessageReceived", "outgoingAPIMessageReceived"}
_MESSAGE_TYPES = _INCOMING_TYPES | _OUTGOING_TYPES


def _extract_text(body: dict) -> str:
    """Pull the message text from either text or extendedText message payloads."""
    data = body.get("messageData", {}) or {}
    text = data.get("textMessageData", {}).get("textMessage")
    if not text:
        text = data.get("extendedTextMessageData", {}).get("text")
    return (text or "").upper().strip()


def handle_command(msg_text: str, *, is_outgoing: bool) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if msg_text == "STATUS":
        send_whatsapp(
            f"✅ *AlertApp-IBKR Online*\nLast poll: {now}\n"
            "Commands: STATUS, SUPPORT SYMBOL, SOLD, SEND"
        )
        print(f"[{now}] Replied to STATUS")

    elif msg_text in ("SOLD", "SEND"):
        print(f"[{now}] {msg_text} command received; running run-alert.bat")
        send_whatsapp("⏳ Running Completely Sold price summary...")
        ok, detail = run_sold_alert()
        if not ok:
            send_whatsapp(f"❌ Completely Sold run failed: {detail}")
        print(f"[{now}] {msg_text} run ok={ok} detail={detail}")

    elif msg_text.startswith("SUPPORT "):
        parts = msg_text.split()
        if len(parts) < 2:
            send_whatsapp("Usage: SUPPORT SYMBOL  (e.g. SUPPORT AAPL)")
        else:
            symbol = parts[1]
            send_whatsapp(f"🔍 Analyzing {symbol} support levels...")
            levels = get_support_levels(symbol)
            if levels:
                levels_str = "\n".join(f"📍 ${lvl}" for lvl in levels)
                send_whatsapp(f"*Support Levels for {symbol}:*\n{levels_str}")
            else:
                send_whatsapp(f"❌ Could not find levels for {symbol}.")
            print(f"Support query: {symbol} -> {levels}")

    # Never reply "unknown command" to outgoing messages: the listener's own
    # replies are outgoing and would otherwise trigger an endless loop.
    elif msg_text and not is_outgoing:
        send_whatsapp(
            "❓ Unknown command.\n"
            "Try: *STATUS* | *SEND* or *SOLD* | *SUPPORT AAPL*"
        )
        print(f"Unknown command: {msg_text!r}")


def check_commands() -> None:
    try:
        receive_response = greenAPI.receiving.receiveNotification()
        if receive_response.code != 200 or not receive_response.data:
            return

        notification = receive_response.data
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
        print(f"Command Error: {exc}")


if __name__ == "__main__":
    if not _acquire_single_instance_lock():
        print(
            "[X] Another AlertApp-IBKR listener is already running. Exiting to "
            "avoid a Green API race condition (only one consumer per instance).",
            flush=True,
        )
        sys.exit(1)

    print("[*] AlertApp-IBKR Green API listener started.", flush=True)
    print(f"    Instance: {ID_INSTANCE}  Target: {TARGET_PHONE}", flush=True)
    print("    WhatsApp commands: STATUS | SUPPORT SYMBOL | SOLD | SEND", flush=True)
    print("    Single-instance lock acquired.", flush=True)

    heartbeat_url = _load_heartbeat_url()
    if heartbeat_url:
        print(f"    Heartbeat: enabled (every {HEARTBEAT_INTERVAL_SECONDS}s)", flush=True)
        send_heartbeat(heartbeat_url)
    else:
        print(
            "    Heartbeat: disabled (set LISTENER_HEARTBEAT_URL or heartbeat_url.txt)",
            flush=True,
        )
    last_heartbeat = time.monotonic()

    while True:
        check_commands()
        if heartbeat_url and (time.monotonic() - last_heartbeat) >= HEARTBEAT_INTERVAL_SECONDS:
            send_heartbeat(heartbeat_url)
            last_heartbeat = time.monotonic()
        time.sleep(POLL_SECONDS)
