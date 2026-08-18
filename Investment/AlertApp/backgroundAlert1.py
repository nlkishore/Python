#!/usr/bin/env python3
"""Green API stock threshold monitor with STATUS command listener (supported alert path)."""

from __future__ import annotations

import configparser
import sys
import time
from datetime import datetime
from pathlib import Path

import yfinance as yf
from whatsapp_api_client_python import API

INVESTMENT_ROOT = Path(__file__).resolve().parents[1]
if str(INVESTMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(INVESTMENT_ROOT))

from shared.alert_watchlist import load_watchlist  # noqa: E402
from shared.config_loader import green_api_credentials, read_merged_ini  # noqa: E402

APP_DIR = Path(__file__).resolve().parent


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError, AttributeError):
                pass


def _load_settings() -> tuple[str, str, str, int, int]:
    parser = read_merged_ini(APP_DIR)
    id_inst, token, phone = green_api_credentials(parser, section="whatsapp")
    if not parser.has_section("whatsapp") and parser.has_section("trading"):
        id_inst, token, phone = green_api_credentials(parser, section="trading")
    if not id_inst or not token or not phone:
        raise RuntimeError(
            "WhatsApp credentials missing. Copy AlertApp/config.ini.example to config.ini "
            "and secrets.local.ini, or set GREEN_API_* env vars."
        )
    check_interval = 600
    poll_seconds = 2
    if parser.has_section("whatsapp"):
        check_interval = parser.getint("whatsapp", "check_interval_seconds", fallback=600)
        poll_seconds = parser.getint("whatsapp", "command_poll_seconds", fallback=2)
    return id_inst, token, phone, check_interval, poll_seconds


_configure_stdio_utf8()

ID_INSTANCE, API_TOKEN_INSTANCE, TARGET_PHONE, CHECK_INTERVAL, POLL_SECONDS = _load_settings()
WATCHLIST = load_watchlist(APP_DIR)
greenAPI = API.GreenAPI(ID_INSTANCE, API_TOKEN_INSTANCE)


def send_whatsapp(text: str) -> None:
    chat_id = f"{TARGET_PHONE}@c.us"
    greenAPI.sending.sendMessage(chat_id, text)


def check_commands() -> None:
    try:
        receive_response = greenAPI.receiving.receiveNotification()
        if receive_response.code != 200 or not receive_response.data:
            return

        notification = receive_response.data
        receipt_id = notification.get("receiptId")
        body = notification.get("body") or {}

        if body.get("typeWebhook") == "incomingMessageReceived":
            msg_text = (
                body.get("messageData", {})
                .get("textMessageData", {})
                .get("textMessage", "")
                .upper()
            )
            if "STATUS" in msg_text:
                now = datetime.now().strftime("%H:%M:%S")
                status_msg = (
                    f"Monitor is Online\nLast Check: {now}\n"
                    f"Tracking: {', '.join(WATCHLIST.keys())}"
                )
                send_whatsapp(status_msg)
                print(f"[{now}] Replied to STATUS command.")

        if receipt_id is not None:
            greenAPI.receiving.deleteNotification(receipt_id)
    except Exception as exc:
        print(f"Command Error: {exc}")


def monitor_stocks() -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] Periodic stock check...")

    for symbol, config in WATCHLIST.items():
        ref_price, up_pct, down_pct = config
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if data.empty:
            continue

        current_price = float(data["Close"].iloc[-1])
        change = ((current_price - ref_price) / ref_price) * 100

        if change >= up_pct or change <= -down_pct:
            direction = "UP" if change > 0 else "DOWN"
            msg = (
                f"{direction} ALERT: {symbol}\n"
                f"Price: ${current_price:.2f}\nChange: {change:.2f}%"
            )
            send_whatsapp(msg)


if __name__ == "__main__":
    print("[*] Stock Monitor & Command Listener started...")
    last_stock_check = 0.0

    while True:
        check_commands()
        current_time = time.time()
        if current_time - last_stock_check > CHECK_INTERVAL:
            monitor_stocks()
            last_stock_check = current_time
        time.sleep(POLL_SECONDS)
