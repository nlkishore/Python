"""
Nearest support & resistance from IBKR Client Portal candle history, with optional WhatsApp.

Uses the same pivot / ATR heuristics as ChartSupportAndSignals.py (compute_chart_signal_from_ohlcv)
and the same CP session + history path as ClientPortalMarketSnapshot.chart_signals_from_cp_history.

This script does **not** send live quote snapshots — only chart-derived levels for symbols in config.

Requires Client Portal Gateway running and logged in. Green API credentials come from
config.ini [trading] whatsapp_* (same as ChartSupportAndSignals).

WhatsApp is not sent automatically. You must pass --send-whatsapp on the command line
so the script calls Green API; otherwise you only get JSON/stdout with whatsapp_friendly_text.

Not financial advice.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from ChartSupportAndSignals import (
    load_whatsapp_notify_params,
    resolve_symbol_list,
    send_whatsapp_plain_text,
)
from ChartSupportAndSignals_IBKR import (
    _cp_base_url,
    cp_ensure_brokerage_session,
    cp_resolve_conid,
    cp_tickle_post,
    load_ibkr_settings,
    load_trading_symbols,
)

from ClientPortalMarketSnapshot import chart_signals_from_cp_history


def build_whatsapp_chart_levels_digest(chart_signals: list[dict[str, Any]]) -> str:
    """Plain-text lines for WhatsApp: symbol, price, support, resistance, optional signal."""
    lines: list[str] = []
    lines.append("IBKR chart — nearest support / resistance (pivot heuristic)")
    lines.append("Not financial advice.")
    for row in chart_signals:
        sym = str(row.get("Ticker", "?"))
        if row.get("error"):
            lines.append(f"{sym}: {row.get('error')}")
            continue
        price = row.get("Current Price", "")
        sup = row.get("Nearest Support", "")
        ds = row.get("Distance To Support %", "")
        res = row.get("Nearest Resistance", "")
        dr = row.get("Distance To Resistance %", "")
        sig = row.get("Signal", "")
        reason = row.get("Signal Reason", "")
        period = row.get("Period used (yfinance)", "")
        parts = [sym, f"Price {price}"]
        if sup != "":
            parts.append(f"Support {sup}" + (f" ({ds})" if ds else ""))
        if res != "":
            parts.append(f"Resist {res}" + (f" ({dr})" if dr else ""))
        if sig:
            parts.append(f"Signal {sig}")
        if reason:
            parts.append(str(reason)[:120])
        line = " · ".join(str(p) for p in parts if p not in ("", None))
        lines.append(line)
        if period and sym != "?":
            lines.append(f"  ({period})")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Fetch IBKR CP intraday history, compute nearest support/resistance, "
            "print JSON; optionally send formatted text via WhatsApp (Green API)."
        )
    )
    ap.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config.ini (default: config.ini next to this script).",
    )
    ap.add_argument(
        "--send-whatsapp",
        action="store_true",
        help=(
            "Required to actually send: posts whatsapp_friendly_text via Green API using "
            "[trading] whatsapp_enabled, whatsapp_id_instance, whatsapp_api_token_instance, "
            "whatsapp_target_phone. Without this flag, nothing is sent (JSON/text only)."
        ),
    )
    ap.add_argument(
        "--json-out",
        action="store_true",
        help="Print only JSON (no session status lines on stdout).",
    )
    ap.add_argument(
        "--text-only",
        action="store_true",
        help="Print only the WhatsApp-style text block (no JSON).",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="No per-symbol progress on stderr (history + pacing can take many minutes).",
    )
    ap.add_argument(
        "--symbol",
        default=None,
        metavar="TICKER",
        help="Single symbol override (e.g. AAPL). Overrides config.ini [trading] symbols.",
    )
    ap.add_argument(
        "--symbols",
        default=None,
        metavar="A,B,C",
        help="Comma-separated symbol list override. Do not combine with --symbol.",
    )
    args = ap.parse_args()

    cfg_path = args.config or (_SCRIPT_DIR / "config.ini")
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        sys.exit(1)

    try:
        ibkr = load_ibkr_settings(cfg_path)
        try:
            config_symbols = load_trading_symbols(cfg_path)
        except ValueError:
            config_symbols = []
        symbols = resolve_symbol_list(
            symbol=args.symbol,
            symbols=args.symbols,
            config_symbols=config_symbols,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    if ibkr["data_source"] != "client_portal":
        print(
            "This script supports Client Portal only (ibkr_data_source = client_portal).",
            file=sys.stderr,
        )
        sys.exit(2)

    timeout = ibkr["cp_request_timeout_seconds"]
    base = _cp_base_url(ibkr["cp_gateway_host"], ibkr["cp_gateway_port"])

    _, api_sess = cp_tickle_post(base, min(timeout, 15.0), None)
    if not api_sess:
        print(
            "POST /tickle did not return a session. Start Client Portal Gateway and log in.",
            file=sys.stderr,
        )
        sys.exit(1)

    auth_ok, auth_msg = cp_ensure_brokerage_session(
        base,
        min(timeout, 60.0),
        compete=ibkr["cp_ssodh_compete"],
        max_wait=ibkr["cp_brokerage_auth_wait_seconds"],
        api_session=api_sess,
    )
    if not auth_ok:
        print(auth_msg, file=sys.stderr)
        sys.exit(1)
    if not args.json_out:
        print(f"Session: {auth_msg}", file=sys.stderr)

    _, sess2 = cp_tickle_post(base, min(timeout, 15.0), api_sess)
    if sess2:
        api_sess = sess2

    sym_to_cid: dict[str, str] = {}
    for sym in symbols:
        cid = cp_resolve_conid(
            base, sym, ibkr["sec_type"], timeout, api_session=api_sess
        )
        if cid:
            sym_to_cid[sym] = cid

    missing = [s for s in symbols if s not in sym_to_cid]
    if missing:
        print(
            f"Could not resolve conid for: {', '.join(missing)}",
            file=sys.stderr,
        )

    if not sym_to_cid:
        print("No contract ids resolved.", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        n_sym = len(symbols)
        pause_s = ibkr["request_pause_seconds"]
        print(
            f"Chart levels: {n_sym} symbol(s). "
            f"IB pacing ~{pause_s:g}s between requests; fetching history (stderr progress)…",
            file=sys.stderr,
            flush=True,
        )

    chart_signals = chart_signals_from_cp_history(
        base,
        api_sess,
        ibkr,
        symbols,
        sym_to_cid,
        timeout,
        progress=not args.quiet,
    )
    digest = build_whatsapp_chart_levels_digest(chart_signals)

    out_obj: dict[str, Any] = {
        "symbols_requested": symbols,
        "chart_signals": chart_signals,
        "whatsapp_friendly_text": digest,
    }

    if not args.send_whatsapp:
        notify_hint = load_whatsapp_notify_params(cfg_path)
        if notify_hint.get("enabled"):
            print(
                "WhatsApp: not sent (add --send-whatsapp to post this digest via Green API).",
                file=sys.stderr,
                flush=True,
            )
        out_obj["whatsapp_delivery"] = {
            "attempted": False,
            "success": False,
            "detail": "Pass --send-whatsapp to send; config whatsapp_enabled alone does not send.",
        }

    delivery: dict[str, Any] | None = None
    if args.send_whatsapp:
        notify_cfg = load_whatsapp_notify_params(cfg_path)
        ok, detail = send_whatsapp_plain_text(notify_cfg, digest)
        delivery = {"attempted": True, "success": ok, "detail": None if ok else detail}
        out_obj["whatsapp_delivery"] = delivery  # overwrites the skipped placeholder above
        if not args.json_out:
            if ok:
                print("WhatsApp: chart levels sent.", file=sys.stderr)
            else:
                print(f"WhatsApp: not sent — {detail}", file=sys.stderr)

    if args.text_only:
        print(digest)
        return

    print(json.dumps(out_obj, indent=2))


if __name__ == "__main__":
    main()
