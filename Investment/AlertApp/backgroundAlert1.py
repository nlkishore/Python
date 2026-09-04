#!/usr/bin/env python3
"""
Green API WhatsApp stock monitor + command listener (consolidated alert app).

Runs two monitoring loops in one process:

1. MANUAL WATCHLIST (config.ini [watchlist])
   Polls Yahoo Finance every CHECK_INTERVAL seconds. Alerts on UP or DOWN breach
   vs a manually configured reference price and threshold %.

2. REBUY WATCHLIST (auto-loaded from Completely_Sold sheet in BuySell Excel)
   Monitors all completely-sold symbols using the weighted-average sell price as
   the reference. Fires a "rebuy candidate" alert when the current price is ≤
   (avg_sell_price × (1 - rebuy_drop_pct / 100)), i.e. when the stock has
   fallen enough below what you sold it for to be worth re-entering.
   Default rebuy_drop_pct = 5.0 (configurable via [rebuy] drop_pct in config.ini).

Supported WhatsApp commands:
  STATUS              — confirm listener is online; lists symbol counts
  WATCHLIST           — show manual watchlist symbols + reference prices
  REBUY               — show current rebuy candidate list with avg sell prices
  PRICE NVDA  or  Q NVDA — avg sold price (all sells) + current Yahoo market
  SUPPORT AAPL        — 3 recent pivot support levels (6-month Yahoo history)
  SOLD  or  SEND      — run CompletelySoldAlert digest on demand
  RELOAD              — reload watchlists + sell averages from Excel
  HELP  or  ?         — list commands

Housekeeping: once a day (and ~2 min after start) deletes WhatsApp messages
in the alert chat that are older than 24 hours (configurable).

Non-command chat is ignored (no "unknown command" reply).

Extras:
  - Single-instance Windows named mutex (prevents two listeners racing on the
    same Green API instance causing 502 RMQ_ERROR / dropped messages).
  - External heartbeat (dead-man's switch): listener pings a URL every N seconds
    so an external service (e.g. healthchecks.io) can alert your phone if the
    whole machine goes down. Configure via LISTENER_HEARTBEAT_URL env var,
    heartbeat_url.txt in this folder, or config.ini [monitoring] heartbeat_url.

Credentials (pick any — env vars override INI):
  1. GREEN_API_ID_INSTANCE, GREEN_API_TOKEN, WHATSAPP_TARGET_PHONE env vars
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
from typing import Optional

import yfinance as yf
from whatsapp_api_client_python import API

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
INVESTMENT_ROOT = SCRIPT_DIR.parent
if str(INVESTMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(INVESTMENT_ROOT))

from shared.alert_watchlist import load_watchlist          # noqa: E402
from shared.config_loader import green_api_credentials, read_merged_ini  # noqa: E402
from shared.price_lookup import (  # noqa: E402
    clear_sell_averages_cache,
    lookup_price_reply,
    parse_price_command,
)
from shared.sold_watchlist import load_sold_watchlist      # noqa: E402
from shared.whatsapp_housekeeping import old_message_ids  # noqa: E402

SOLD_ALERT_BAT = INVESTMENT_ROOT / "CompletelySoldAlert" / "run-alert.bat"
_HEARTBEAT_URL_FILE = SCRIPT_DIR / "heartbeat_url.txt"

# ---------------------------------------------------------------------------
# Single-instance lock (Windows named mutex)
# Green API allows only ONE active receiveNotification consumer per instance.
# ---------------------------------------------------------------------------
_SINGLE_INSTANCE_MUTEX_NAME = "Global\\AlertApp_GreenAPI_Listener"
_ERROR_ALREADY_EXISTS = 183
_single_instance_handle = None  # kept alive for process lifetime


def _acquire_single_instance_lock() -> bool:
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
    if (not id_inst or not token or not phone) and parser.has_section("trading"):
        id_inst, token, phone = green_api_credentials(parser, section="trading")
    if not id_inst or not token or not phone:
        raise RuntimeError(
            "WhatsApp credentials missing.\n"
            "Copy AlertApp/config.ini.example → config.ini, then\n"
            "copy AlertApp/secrets.local.ini.example → secrets.local.ini\n"
            "and fill in your Green API credentials.\n"
            "Or set GREEN_API_ID_INSTANCE / GREEN_API_TOKEN / WHATSAPP_TARGET_PHONE."
        )
    check_interval = 600
    poll_seconds = 2
    if parser.has_section("whatsapp"):
        check_interval = parser.getint("whatsapp", "check_interval_seconds", fallback=600)
        poll_seconds = parser.getint("whatsapp", "command_poll_seconds", fallback=2)
    return id_inst, token, phone, check_interval, poll_seconds


def _load_rebuy_settings() -> tuple[float, Optional[Path], list[str]]:
    """
    Returns (drop_pct, workbook_path, exclude_symbols).
    drop_pct        — alert when price ≤ avg_sell * (1 - drop_pct/100). Default 5.0.
    workbook_path   — path to BuySell Excel. None = use shared default.
    exclude_symbols — list of symbols to skip (delisted, etc.).
    """
    parser = read_merged_ini(SCRIPT_DIR)
    if not parser.has_section("rebuy"):
        return 5.0, None, []

    drop_pct = parser.getfloat("rebuy", "drop_pct", fallback=5.0)
    wb_str = parser.get("rebuy", "workbook_path", fallback="").strip()
    workbook_path = Path(wb_str) if wb_str else None

    exclude_raw = parser.get("rebuy", "exclude_symbols", fallback="").strip()
    exclude = [s.strip().upper() for s in exclude_raw.split(",") if s.strip()]

    return drop_pct, workbook_path, exclude


def _load_housekeeping_settings() -> tuple[bool, int, int, int]:
    """
    Returns (enabled, max_age_hours, history_count, max_delete_per_run).
    Deletes WhatsApp messages in the target chat older than max_age_hours.
    """
    parser = read_merged_ini(SCRIPT_DIR)
    if not parser.has_section("housekeeping"):
        return True, 24, 100, 50
    enabled = parser.getboolean("housekeeping", "enabled", fallback=True)
    max_age_hours = parser.getint("housekeeping", "max_age_hours", fallback=24)
    history_count = parser.getint("housekeeping", "history_count", fallback=100)
    max_delete = parser.getint("housekeeping", "max_delete_per_run", fallback=50)
    return enabled, max(1, max_age_hours), max(10, history_count), max(1, max_delete)


def _load_heartbeat_url() -> str:
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
    if not url:
        return
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"[!] Heartbeat ping failed: {exc}", flush=True)


# ---------------------------------------------------------------------------
# Initialise
# ---------------------------------------------------------------------------
_configure_stdio_utf8()
ID_INSTANCE, API_TOKEN_INSTANCE, TARGET_PHONE, CHECK_INTERVAL, POLL_SECONDS = _load_settings()
REBUY_DROP_PCT, _REBUY_WORKBOOK, _REBUY_EXCLUDE = _load_rebuy_settings()
HK_ENABLED, HK_MAX_AGE_HOURS, HK_HISTORY_COUNT, HK_MAX_DELETE = _load_housekeeping_settings()

# Manual watchlist: {SYMBOL: [ref_price, up_pct, down_pct]}
WATCHLIST: dict[str, list[float]] = load_watchlist(SCRIPT_DIR)

# Rebuy watchlist: {SYMBOL: {"avg_buy": float, "avg_sell": float}}
REBUY_WATCHLIST: dict[str, dict[str, float]] = load_sold_watchlist(
    workbook_path=_REBUY_WORKBOOK,
    exclude_symbols=_REBUY_EXCLUDE,
)

# Alert cooldown for rebuy: avoid spamming the same symbol every cycle.
# {SYMBOL: epoch_seconds of last alert sent}
_REBUY_ALERT_SENT: dict[str, float] = {}
_REBUY_COOLDOWN_SECONDS = 3600  # re-alert at most once per hour per symbol

greenAPI = API.GreenAPI(ID_INSTANCE, API_TOKEN_INSTANCE, host_timeout=20)

# When handling a WhatsApp command, reply in that chat; alerts still go to TARGET_PHONE.
_command_reply_chat: str | None = None


# ---------------------------------------------------------------------------
# WhatsApp send
# ---------------------------------------------------------------------------
def send_whatsapp(text: str, chat_id: str | None = None) -> None:
    dest = chat_id or _command_reply_chat or f"{TARGET_PHONE}@c.us"
    if "@" not in dest:
        dest = f"{dest}@c.us"
    response = greenAPI.sending.sendMessage(dest, text)
    if response.code != 200:
        print(f"Send failed to {dest}: {getattr(response, 'error', response.code)}", flush=True)


# ---------------------------------------------------------------------------
# Manual watchlist monitor
# ---------------------------------------------------------------------------
def monitor_stocks() -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] Manual watchlist check ({len(WATCHLIST)} symbols)...", flush=True)

    for symbol, cfg in WATCHLIST.items():
        ref_price, up_pct, down_pct = cfg
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
                f"Price: ${current_price:.2f}  Change: {change:+.2f}%\n"
                f"(Ref: ${ref_price:.2f}, threshold ↑{up_pct}%)"
            )
        elif change <= -down_pct:
            send_whatsapp(
                f"📉 *DOWN ALERT*: {symbol}\n"
                f"Price: ${current_price:.2f}  Change: {change:+.2f}%\n"
                f"(Ref: ${ref_price:.2f}, threshold ↓{down_pct}%)"
            )


# ---------------------------------------------------------------------------
# Rebuy watchlist monitor
# ---------------------------------------------------------------------------
def monitor_rebuy() -> None:
    """
    Alert when a completely-sold symbol's current price has dropped ≥ REBUY_DROP_PCT
    below the average sell price — a potential re-buy signal.
    Message always includes Current / Avg Buy / Avg Sold.
    """
    if not REBUY_WATCHLIST:
        return

    now_str = datetime.now().strftime("%H:%M:%S")
    now_epoch = time.time()
    print(
        f"[{now_str}] Rebuy watchlist check ({len(REBUY_WATCHLIST)} symbols, "
        f"threshold ↓{REBUY_DROP_PCT}% below avg sell)...",
        flush=True,
    )

    for symbol, levels in REBUY_WATCHLIST.items():
        avg_buy = float(levels["avg_buy"])
        avg_sell = float(levels["avg_sell"])
        try:
            data = yf.Ticker(symbol).history(period="1d")
        except Exception as exc:
            print(f"  [{symbol}] fetch error: {exc}", flush=True)
            continue
        if data.empty:
            continue

        current_price = float(data["Close"].iloc[-1])
        # Positive drop_pct = current is cheaper than avg sell
        drop_pct = ((avg_sell - current_price) / avg_sell) * 100
        vs_buy_pct = ((avg_buy - current_price) / avg_buy) * 100 if avg_buy else 0.0
        print(
            f"  {symbol}: now=${current_price:.2f}  "
            f"avg_buy=${avg_buy:.2f}  avg_sold=${avg_sell:.2f}  "
            f"vs_sell={drop_pct:+.2f}%  vs_buy={vs_buy_pct:+.2f}%",
            flush=True,
        )

        if drop_pct >= REBUY_DROP_PCT:
            last_sent = _REBUY_ALERT_SENT.get(symbol, 0.0)
            if now_epoch - last_sent < _REBUY_COOLDOWN_SECONDS:
                continue

            send_whatsapp(
                f"♻️ *REBUY CANDIDATE*: {symbol}\n"
                f"Current:   ${current_price:.2f}\n"
                f"Avg Buy:   ${avg_buy:.2f}\n"
                f"Avg Sold:  ${avg_sell:.2f}\n"
                f"vs Avg Sold: {drop_pct:+.1f}% "
                f"(alert when ≤ −{REBUY_DROP_PCT}%)\n"
                f"vs Avg Buy:  {vs_buy_pct:+.1f}%\n"
                f"Consider re-entering this position."
            )
            _REBUY_ALERT_SENT[symbol] = now_epoch
            print(
                f"  [{symbol}] Rebuy alert sent "
                f"(drop {drop_pct:.1f}% >= {REBUY_DROP_PCT}%)",
                flush=True,
            )


# ---------------------------------------------------------------------------
# Reload both watchlists from disk (RELOAD command)
# ---------------------------------------------------------------------------
def reload_watchlists() -> str:
    global WATCHLIST, REBUY_WATCHLIST, REBUY_DROP_PCT, _REBUY_WORKBOOK, _REBUY_EXCLUDE
    try:
        WATCHLIST = load_watchlist(SCRIPT_DIR)
        REBUY_DROP_PCT, _REBUY_WORKBOOK, _REBUY_EXCLUDE = _load_rebuy_settings()
        REBUY_WATCHLIST = load_sold_watchlist(
            workbook_path=_REBUY_WORKBOOK,
            exclude_symbols=_REBUY_EXCLUDE,
        )
        clear_sell_averages_cache()
        return (
            f"✅ Reloaded.\n"
            f"Manual watchlist: {len(WATCHLIST)} symbols\n"
            f"Rebuy watchlist:  {len(REBUY_WATCHLIST)} symbols "
            f"(threshold ↓{REBUY_DROP_PCT}%)\n"
            f"Avg-sold cache cleared (next PRICE / Q reloads Sells sheet)."
        )
    except Exception as exc:  # noqa: BLE001
        return f"❌ Reload failed: {exc}"


# ---------------------------------------------------------------------------
# SUPPORT command helper
# ---------------------------------------------------------------------------
def get_support_levels(symbol: str) -> list[float]:
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

# Phone-typed commands show up in lastOutgoingMessages, not receiveNotification.
_seen_journal_ids: dict[str, None] = {}
_journal_seeded = False
_MAX_SEEN_IDS = 2000


def _extract_text(body: dict) -> str:
    data = body.get("messageData", {}) or {}
    text = data.get("textMessageData", {}).get("textMessage")
    if not text:
        text = data.get("extendedTextMessageData", {}).get("text")
    return (text or "").upper().strip()


def _extract_chat_id(body: dict) -> str | None:
    sender = body.get("senderData") or {}
    chat_id = sender.get("chatId") or sender.get("sender")
    if chat_id:
        return str(chat_id)
    return None


def _mark_seen(msg_id: str) -> bool:
    """Return True if this id is new (now recorded)."""
    if not msg_id or msg_id in _seen_journal_ids:
        return False
    _seen_journal_ids[msg_id] = None
    while len(_seen_journal_ids) > _MAX_SEEN_IDS:
        _seen_journal_ids.pop(next(iter(_seen_journal_ids)))
    return True


def _journal_text(item: dict) -> str:
    data = item.get("messageData") or {}
    text = item.get("textMessage") or item.get("text") or ""
    if not text and isinstance(data, dict):
        text = (data.get("textMessageData") or {}).get("textMessage") or ""
        if not text:
            text = (data.get("extendedTextMessageData") or {}).get("text") or ""
    return str(text or "").upper().strip()


def _journal_chat_id(item: dict) -> str | None:
    chat = item.get("chatId")
    if chat:
        return str(chat)
    sender = item.get("senderData") or {}
    chat = sender.get("chatId") or sender.get("sender")
    return str(chat) if chat else None


def _journal_items(resp) -> list[dict]:
    data = getattr(resp, "data", None)
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def _drain_notification_queue() -> None:
    """Drop one queued webhook so the Green API queue does not back up."""
    try:
        resp = greenAPI.request(
            "GET",
            "{{host}}/waInstance{{idInstance}}/"
            "receiveNotification/{{apiTokenInstance}}?receiveTimeout=1",
        )
        if resp.code != 200 or not isinstance(resp.data, dict):
            return
        receipt_id = resp.data.get("receiptId")
        if receipt_id is not None:
            greenAPI.receiving.deleteNotification(receipt_id)
    except Exception:
        return


_HELP_TEXT = (
    "Commands:\n"
    "*STATUS* | *WATCHLIST* | *REBUY* | *PRICE NVDA* | *Q NVDA* | "
    "*SUPPORT AAPL* | *SOLD* | *RELOAD* | *HELP*\n"
    "Other chat messages are ignored (no reply)."
)

# Exact one-word commands. Casual chat must NOT trigger a reply.
_EXACT_COMMANDS = frozenset(
    {"STATUS", "WATCHLIST", "REBUY", "RELOAD", "SOLD", "SEND", "HELP", "?"}
)


def _looks_like_command(msg_text: str) -> bool:
    """True only for known verbs — avoids treating normal chat as commands."""
    if not msg_text:
        return False
    if msg_text in _EXACT_COMMANDS:
        return True
    # SUPPORT AAPL / SUPPORT alone
    if msg_text == "SUPPORT" or msg_text.startswith("SUPPORT "):
        return True
    if parse_price_command(msg_text) is not None:
        return True
    if _bare_known_symbol(msg_text):
        return True
    return False


def _bare_known_symbol(msg_text: str) -> str | None:
    """Treat a single known ticker (NVDA) as PRICE NVDA — not random chat words."""
    token = (msg_text or "").strip().upper()
    if not token or " " in token:
        return None
    if token in _EXACT_COMMANDS or token in ("PRICE", "Q", "SUPPORT", "SEND"):
        return None
    if not (1 <= len(token) <= 8) or not all(c.isalnum() or c == "." for c in token):
        return None
    if token in WATCHLIST or token in REBUY_WATCHLIST:
        return token
    try:
        from shared.price_lookup import load_sell_averages

        if token in load_sell_averages(_REBUY_WORKBOOK):
            return token
    except Exception:  # noqa: BLE001
        pass
    return None


def handle_command(msg_text: str, *, is_outgoing: bool, reply_chat: str | None = None) -> None:
    global _command_reply_chat
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _command_reply_chat = reply_chat
    try:
        _handle_command_body(msg_text, is_outgoing=is_outgoing, now=now)
    finally:
        _command_reply_chat = None


def _handle_command_body(msg_text: str, *, is_outgoing: bool, now: str) -> None:
    # Ignore normal conversation (incoming or outgoing). Still delete the
    # notification in check_commands() so the queue does not back up.
    if not _looks_like_command(msg_text):
        preview = msg_text if len(msg_text) <= 60 else msg_text[:57] + "..."
        print(f"[{now}] Ignored non-command chat: {preview!r}", flush=True)
        return

    if msg_text in ("HELP", "?"):
        send_whatsapp(_HELP_TEXT)
        print(f"[{now}] Replied to HELP", flush=True)

    elif msg_text == "STATUS":
        send_whatsapp(
            f"✅ *AlertApp Online*\nLast poll: {now}\n"
            f"Manual watchlist: {len(WATCHLIST)} symbols\n"
            f"Rebuy watchlist:  {len(REBUY_WATCHLIST)} symbols "
            f"(↓{REBUY_DROP_PCT}% trigger)\n"
            + _HELP_TEXT
        )
        print(f"[{now}] Replied to STATUS", flush=True)

    elif msg_text == "WATCHLIST":
        if WATCHLIST:
            lines = [
                f"  {sym}: ref=${cfg[0]:.2f}  ↑{cfg[1]}%  ↓{cfg[2]}%"
                for sym, cfg in WATCHLIST.items()
            ]
            send_whatsapp("📋 *Manual watchlist:*\n" + "\n".join(lines))
        else:
            send_whatsapp("📋 Manual watchlist is empty.")
        print(f"[{now}] Replied to WATCHLIST", flush=True)

    elif msg_text == "REBUY":
        if REBUY_WATCHLIST:
            lines = [
                f"  {sym}: buy=${lv['avg_buy']:.2f}  sold=${lv['avg_sell']:.2f}  "
                f"alert ≤${lv['avg_sell'] * (1 - REBUY_DROP_PCT / 100):.2f}"
                for sym, lv in REBUY_WATCHLIST.items()
            ]
            send_whatsapp(
                f"♻️ *Rebuy candidates ({len(REBUY_WATCHLIST)} symbols)*\n"
                f"Alert when Current ≤ Avg Sold − {REBUY_DROP_PCT}%\n"
                f"(Current / Avg Buy / Avg Sold shown on each alert)\n"
                + "\n".join(lines)
            )
        else:
            send_whatsapp(
                "♻️ Rebuy watchlist is empty.\n"
                "Make sure IBKR_BuySell_Since_2020.xlsx is up to date and has a "
                "Completely_Sold sheet."
            )
        print(f"[{now}] Replied to REBUY", flush=True)

    elif msg_text == "RELOAD":
        msg = reload_watchlists()
        send_whatsapp(msg)
        print(f"[{now}] RELOAD: {msg.splitlines()[0]}", flush=True)

    elif msg_text in ("SOLD", "SEND"):
        print(f"[{now}] {msg_text} command; running run-alert.bat", flush=True)
        send_whatsapp("⏳ Running Completely Sold price summary...")
        ok, detail = run_sold_alert()
        if not ok:
            send_whatsapp(f"❌ Completely Sold run failed: {detail}")
        print(f"[{now}] {msg_text} ok={ok} {detail}", flush=True)

    elif parse_price_command(msg_text) is not None or _bare_known_symbol(msg_text):
        symbol = parse_price_command(msg_text)
        if symbol is None:
            symbol = _bare_known_symbol(msg_text) or ""
        if not symbol:
            send_whatsapp("Usage: PRICE SYMBOL  or  Q SYMBOL  (e.g. PRICE NVDA)")
        else:
            send_whatsapp(f"⏳ {symbol}: avg sold + market…")
            try:
                reply = lookup_price_reply(symbol, workbook_path=_REBUY_WORKBOOK)
            except Exception as exc:  # noqa: BLE001
                reply = f"❌ Lookup failed for {symbol}: {exc}"
            send_whatsapp(reply)
            print(f"[{now}] PRICE {symbol}\n{reply}", flush=True)

    elif msg_text == "SUPPORT" or msg_text.startswith("SUPPORT "):
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

    # Known verb but incomplete / unexpected form — only reply if incoming
    # (never to outgoing, or the bot's own messages loop).
    elif not is_outgoing:
        send_whatsapp("❓ " + _HELP_TEXT)
        print(f"[{now}] Unrecognized command form: {msg_text!r}", flush=True)


def check_commands() -> None:
    """
    Read commands from WhatsApp journals.

    Messages you type on the Green API-linked phone are *outgoing* and often
    never appear in receiveNotification. lastOutgoingMessages always has them.
    Incoming messages from another phone are covered by lastIncomingMessages.
    """
    global _journal_seeded
    _drain_notification_queue()
    try:
        incoming = greenAPI.journals.lastIncomingMessages(minutes=15)
        outgoing = greenAPI.journals.lastOutgoingMessages(minutes=15)
    except Exception as exc:
        print(f"Command poll error: {exc}", flush=True)
        return

    rows: list[tuple[str, str, str | None, bool, float]] = []
    for item in _journal_items(incoming):
        rows.append(
            (
                str(item.get("idMessage") or ""),
                _journal_text(item),
                _journal_chat_id(item),
                False,
                float(item.get("timestamp") or 0),
            )
        )
    for item in _journal_items(outgoing):
        if item.get("sendByApi") in (True, "true", "True", 1):
            continue
        rows.append(
            (
                str(item.get("idMessage") or ""),
                _journal_text(item),
                _journal_chat_id(item),
                True,
                float(item.get("timestamp") or 0),
            )
        )

    now_ts = time.time()
    first_poll = not _journal_seeded
    _journal_seeded = True
    if first_poll:
        print(
            f"[*] Journal poll ready ({len(rows)} recent WhatsApp messages). "
            "Commands typed in the last 15 minutes will be answered.",
            flush=True,
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for msg_id, msg_text, chat_id, is_outgoing, ts in rows:
        if not msg_id:
            continue
        if first_poll and ts and ts < now_ts - 900:
            _seen_journal_ids[msg_id] = None
            continue
        if not _mark_seen(msg_id):
            continue
        if not msg_text or not _looks_like_command(msg_text):
            continue
        print(
            f"[{now}] journal {'out' if is_outgoing else 'in'} "
            f"chat={chat_id} text={msg_text[:80]!r}",
            flush=True,
        )
        handle_command(msg_text, is_outgoing=is_outgoing, reply_chat=chat_id)


def _alert_chat_id() -> str:
    return f"{TARGET_PHONE}@c.us"


def run_message_housekeeping() -> None:
    """Delete WhatsApp messages in the alert chat older than HK_MAX_AGE_HOURS."""
    if not HK_ENABLED:
        return
    chat_id = _alert_chat_id()
    cutoff = time.time() - (HK_MAX_AGE_HOURS * 3600)
    try:
        resp = greenAPI.journals.getChatHistory(chat_id, HK_HISTORY_COUNT)
    except Exception as exc:  # noqa: BLE001
        print(f"[housekeeping] getChatHistory failed: {exc}", flush=True)
        return
    items = resp.data if isinstance(getattr(resp, "data", None), list) else []
    if resp.code != 200:
        print(
            f"[housekeeping] getChatHistory http={resp.code} "
            f"err={getattr(resp, 'error', '')}",
            flush=True,
        )
        return
    to_delete = old_message_ids(items, cutoff_ts=cutoff)[:HK_MAX_DELETE]
    if not to_delete:
        print(
            f"[housekeeping] no messages older than {HK_MAX_AGE_HOURS}h in {chat_id}",
            flush=True,
        )
        return

    deleted = 0
    for msg_id in to_delete:
        try:
            del_resp = greenAPI.serviceMethods.deleteMessage(chat_id, msg_id)
            if del_resp.code == 200:
                deleted += 1
            else:
                print(
                    f"[housekeeping] delete {msg_id} http={del_resp.code}",
                    flush=True,
                )
        except Exception as exc:  # noqa: BLE001
            print(f"[housekeeping] delete {msg_id} failed: {exc}", flush=True)
        time.sleep(0.15)
    print(
        f"[housekeeping] deleted {deleted}/{len(to_delete)} messages "
        f"older than {HK_MAX_AGE_HOURS}h in {chat_id}",
        flush=True,
    )


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

    print("[*] AlertApp started (price monitor + rebuy monitor + command listener).", flush=True)
    print(f"    Instance: {ID_INSTANCE}  Target: {TARGET_PHONE}", flush=True)
    print(f"    Manual watchlist:  {list(WATCHLIST.keys())}", flush=True)
    print(
        f"    Rebuy watchlist:   {list(REBUY_WATCHLIST.keys())} "
        f"(alert ↓{REBUY_DROP_PCT}% below avg sell; shows Current/Avg Buy/Avg Sold)",
        flush=True,
    )
    print(f"    Price check: every {CHECK_INTERVAL}s  Command poll: every {POLL_SECONDS}s", flush=True)
    print(
        "    Commands: STATUS | WATCHLIST | REBUY | PRICE SYMBOL | Q SYMBOL | "
        "SUPPORT SYMBOL | SOLD | RELOAD",
        flush=True,
    )

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
    # Poll commands immediately; do not block the first loop on Yahoo.
    last_stock_check = time.monotonic()
    started_at = time.monotonic()
    last_housekeeping = 0.0
    print(
        f"    Housekeeping: "
        + (
            f"delete alert-chat messages older than {HK_MAX_AGE_HOURS}h "
            f"(first run ~2 min after start, then daily)"
            if HK_ENABLED
            else "disabled"
        ),
        flush=True,
    )

    while True:
        check_commands()

        now_mono = time.monotonic()
        if now_mono - last_stock_check >= CHECK_INTERVAL:
            monitor_stocks()
            monitor_rebuy()
            last_stock_check = now_mono

        due_first = last_housekeeping == 0.0 and (now_mono - started_at) >= 120
        due_daily = last_housekeeping > 0.0 and (now_mono - last_housekeeping) >= 86400
        if HK_ENABLED and (due_first or due_daily):
            run_message_housekeeping()
            last_housekeeping = now_mono

        if heartbeat_url and (now_mono - last_heartbeat) >= HEARTBEAT_INTERVAL_SECONDS:
            send_heartbeat(heartbeat_url)
            last_heartbeat = now_mono

        time.sleep(POLL_SECONDS)
