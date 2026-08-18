"""
Live market data snapshots via IBKR Client Portal Web API.

Implements the flow described for GET /iserver/marketdata/snapshot:
  https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#md-snapshot

Per IBKR documentation:
  - GET /iserver/accounts must be called before /iserver/marketdata/snapshot.
  - For stocks, resolve contract ids via /iserver/secdef/search (symbols from config).
  - GET /iserver/marketdata/snapshot?conids=...&fields=...

Requires Client Portal Gateway running, browser login, and the same session pattern as
ChartSupportAndSignals_IBKR (POST /tickle, Cookie api=<session>, brokerage session).

Optional `--chart-support`: loads intraday bars via GET /iserver/marketdata/history and runs
the same pivot / ATR / support-resistance heuristics as ChartSupportAndSignals_IBKR.

Snapshot JSON includes `snapshot_labeled` (human-readable keys such as Volume instead of 87)
and `whatsapp_friendly_text` for SMS/WhatsApp; prefer that string over raw snapshot dicts.

Use `--send-whatsapp` to deliver the **quote digest** via Green API (`[trading]` whatsapp_* in config.ini).
Nearest support/resistance from candles is in JSON only when you add `--chart-support` (field `chart_signals`);
it is not included in that WhatsApp message. For a dedicated S/R WhatsApp report, use
`ChartSupportResistanceWhatsApp_IBKR.py`.

Not financial advice.
"""

from __future__ import annotations

import argparse
import configparser
import json
import sys
import time
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from ChartSupportAndSignals import (
    compute_chart_signal_from_ohlcv,
    load_whatsapp_notify_params,
    send_whatsapp_plain_text,
)

from ChartSupportAndSignals_IBKR import (
    _cp_base_url,
    _http_error_detail,
    _http_get_json,
    _map_what_to_show_to_cp_source,
    cp_ensure_brokerage_session,
    cp_fetch_history_df,
    cp_resolve_conid,
    cp_tickle_post,
    load_ibkr_settings,
    load_trading_symbols,
)

_DEFAULT_FIELDS = "31,84,86,85,87,88,6509"

# IBKR Web API: Market Data Fields (numeric ids in snapshot JSON). See cpapi-v1 #md-snapshot.
_FIELD_ID_LEGEND: dict[str, str] = {
    "31": "Last price — last trade",
    "84": "Bid — top-of-book bid",
    "85": "Ask size — size at the ask",
    "86": "Ask — top-of-book ask",
    "87": "Volume — day volume with K / M formatting",
    "88": "Bid size — size at the bid",
    "6119": "Request / server id (echo)",
    "6508": "Service routing (internal)",
    "6509": "Market data availability — 3 characters (latency, delivery, book)",
    "7059": "RT / display flags (varies by product)",
    "conid": "Contract id",
    "conidEx": "Conid (optional exchange suffix)",
    "_symbol": "Ticker (added by this script)",
    "_updated": "Update time (epoch ms)",
    "server_id": "Server id for this row",
    "87_raw": "Volume — raw numeric when IB sends field 87_raw",
}

# Output key -> meaning (same facts as IBKR ids above).
_QUOTE_FIELD_DEFINITIONS: dict[str, str] = {
    "last_price": "IBKR 31 — Last price — last trade",
    "bid": "IBKR 84 — Bid — top-of-book bid",
    "ask": "IBKR 86 — Ask — top-of-book ask",
    "ask_size": "IBKR 85 — Ask size — size at the ask",
    "bid_size": "IBKR 88 — Bid size — size at the bid",
    "volume": "IBKR 87 — Volume — day volume (K/M suffix)",
    "volume_raw": "IBKR 87_raw — Volume — raw units when present",
    "market_data_availability": "IBKR 6509 — raw 1–3 letter code",
    "market_data_availability_decoded": "IBKR 6509 — interpreted latency / delivery / book",
}

# Raw IB snapshot rows use numeric string keys ("87"); labeled JSON uses readable names.
_IBKR_SNAPSHOT_NUMERIC_TO_LABEL: dict[str, str] = {
    "31": "LastPrice",
    "84": "Bid",
    "86": "Ask",
    "85": "AskSize",
    "87": "Volume",
    "88": "BidSize",
    "87_raw": "VolumeRaw",
    "6509": "MarketDataAvailability",
    "6508": "IbServiceRouting",
    "6119": "IbRequestEcho",
    "7059": "IbRtDisplay",
    "conid": "Conid",
    "conidEx": "ConidEx",
    "_updated": "UpdatedMs",
    "server_id": "ServerId",
    "_symbol": "Symbol",
}


def label_ib_numeric_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Turn one IB `/marketdata/snapshot` object into JSON with meaningful keys
    (e.g. "87" -> "Volume") for APIs and notifications.
    """
    out: dict[str, Any] = {}
    for k, v in row.items():
        label = _IBKR_SNAPSHOT_NUMERIC_TO_LABEL.get(k)
        if label:
            out[label] = v
        else:
            out[f"ib_{k}"] = v
    return out


def build_whatsapp_snapshot_digest(quotes: list[dict[str, Any]]) -> str:
    """
    Short plain text for WhatsApp / SMS — not raw JSON.
    Prefer sending this over dumping snapshot keys like \"87\".
    """
    lines: list[str] = []
    lines.append("IBKR snapshot (Client Portal)")
    for q in quotes:
        sym = q.get("symbol") or "?"
        lp = q.get("last_price")
        bid = q.get("bid")
        ask = q.get("ask")
        vol = q.get("volume")
        md = q.get("market_data_availability")
        parts = [sym]
        if lp is not None:
            parts.append(f"Last {lp}")
        if bid is not None or ask is not None:
            parts.append(f"Bid {bid or '—'} / Ask {ask or '—'}")
        if vol is not None:
            parts.append(f"Vol {vol}")
        if md:
            parts.append(f"MD {md}")
        lines.append(" · ".join(parts))
    return "\n".join(lines)


def _meaning_for_md_availability_char(ch: str) -> str:
    """
    IBKR 6509 uses 1–3 characters; meanings are NOT strictly fixed by slot.
    Letters combine per IB Web API "Market Data Availability" (e.g. Ri, ZB, Zi, N).
    """
    m = {
        # First-character style (latency / permission class)
        "R": "Real-time",
        "D": "Delayed (~15–20 min)",
        "Z": "Frozen (last recorded value at prior close)",
        "Y": "Frozen delayed",
        "N": "Not subscribed (no live/delayed entitlement)",
        "i": "Incomplete",
        "v": "VDR exempt (vendor display rule)",
        # Often 2nd / 3rd position (delivery / book style)
        "P": "Snapshot request path available",
        "p": "Consolidated (aggregated venues)",
        "B": "Top-of-book (bid/ask) available",
    }
    return m.get(
        ch,
        f"Reserved/extension ({ch!r}) — see IBKR cpapi Market Data Fields §6509",
    )


def decode_market_data_availability(code: str | None) -> dict[str, Any]:
    """
    IBKR field 6509: typically 1–3 letters; decode **each** letter (IB does not
    always send full RiB triple — Zi and ZB are valid shorter codes).
    """
    empty = {
        "code": None,
        "summary": "No 6509 value from IB.",
        "characters": [],
        "latency_letter": None,
        "latency": None,
        "delivery_letter": None,
        "delivery": None,
        "book_letter": None,
        "book": None,
    }
    if not code or not isinstance(code, str):
        empty["summary"] = (
            "No 6509 value from IB (subscribe market data or wait for snapshot)."
        )
        return empty

    s = code.strip()
    chars_out: list[dict[str, Any]] = []
    parts: list[str] = []
    for idx, ch in enumerate(s):
        meaning = _meaning_for_md_availability_char(ch)
        chars_out.append({"position": idx + 1, "character": ch, "meaning": meaning})
        parts.append(f"{ch}: {meaning}")

    # Legacy compatibility: if exactly 3 chars, map to slots 1/2/3 as doc describes
    lat = delivery = book = None
    dl = dlv = bl = None
    if len(s) >= 1:
        dl = s[0]
        lat = _meaning_for_md_availability_char(s[0])
    if len(s) >= 2:
        dlv = s[1]
        delivery = _meaning_for_md_availability_char(s[1])
    if len(s) >= 3:
        bl = s[2]
        book = _meaning_for_md_availability_char(s[2])

    return {
        "code": s,
        "summary": "; ".join(parts),
        "characters": chars_out,
        "doc_note": (
            "IB may return 1–3 letters (e.g. N, Zi, ZB). Interpret each letter; "
            "full triple often RiB-style when stream + book are active."
        ),
        "latency_letter": dl,
        "latency": lat,
        "delivery_letter": dlv,
        "delivery": delivery,
        "book_letter": bl,
        "book": book,
    }


def humanize_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Map IBKR numeric snapshot keys to stable JSON keys.
    **Always** emit every translated field (null if IB omitted it) so output stays consistent.
    """
    md_code = row.get("6509")
    md_s = str(md_code).strip() if md_code is not None and md_code != "" else None
    decoded = decode_market_data_availability(md_s)

    return {
        "symbol": row.get("_symbol"),
        "conid": row.get("conid"),
        "last_price": row.get("31"),
        "bid": row.get("84"),
        "ask": row.get("86"),
        "ask_size": row.get("85"),
        "bid_size": row.get("88"),
        "volume": row.get("87"),
        "volume_raw": row.get("87_raw"),
        "market_data_availability": md_s,
        "market_data_availability_decoded": decoded,
        "updated_ms": row.get("_updated"),
    }


def _print_quotes_table(quotes: list[dict[str, Any]]) -> None:
    """Fixed-width table for quick terminal reading."""
    if not quotes:
        return
    cols = [
        ("symbol", 8),
        ("last", 10),
        ("bid", 10),
        ("ask", 10),
        ("volume", 8),
        ("md6509", 6),
    ]
    header = "  ".join(f"{c[0]:<{c[1]}}" for c in cols)
    print(
        "\n--- Quotes (defaults request IB ids 31,84,86,85,87,88,6509; null = not returned yet) ---"
    )
    print(header)
    print("-" * len(header))
    for q in quotes:
        sym = str(q.get("symbol") or "")[:8]
        last = str(q.get("last_price") if q.get("last_price") is not None else "")[
            :10
        ] or "—"
        bid = str(q.get("bid") if q.get("bid") is not None else "")[:10] or "—"
        ask = str(q.get("ask") if q.get("ask") is not None else "")[:10] or "—"
        vol = str(q.get("volume") if q.get("volume") is not None else "")[:8] or "—"
        md = str(q.get("market_data_availability") or "")[:6] or "—"
        line = [
            f"{sym:<8}",
            f"{last:<10}",
            f"{bid:<10}",
            f"{ask:<10}",
            f"{vol:<8}",
            f"{md:<6}",
        ]
        print("  ".join(line))
    print()


def _load_snapshot_fields(cfg_path: Path) -> str:
    parser = configparser.ConfigParser()
    parser.read(cfg_path, encoding="utf-8")
    if parser.has_option("ibkr", "md_snapshot_fields"):
        raw = parser.get("ibkr", "md_snapshot_fields", fallback=_DEFAULT_FIELDS).strip()
        return raw or _DEFAULT_FIELDS
    return _DEFAULT_FIELDS


def cp_get_iserver_accounts(
    base_url: str, timeout: float, api_session: str
) -> Any:
    """Pre-flight per IBKR: /iserver/accounts before marketdata/snapshot."""
    url = f"{base_url.rstrip('/')}/iserver/accounts"
    return _http_get_json(url, timeout, api_session=api_session)


def cp_marketdata_snapshot(
    base_url: str,
    conids: list[str],
    fields_csv: str,
    timeout: float,
    api_session: str,
) -> Any:
    """GET /iserver/marketdata/snapshot — max 100 conids, max 50 field ids."""
    if not conids:
        raise ValueError("No conids for snapshot.")
    chunk = conids[:100]
    ids = ",".join(chunk)
    fields = fields_csv.replace(" ", "").strip()
    q = urllib.parse.urlencode({"conids": ids, "fields": fields})
    url = f"{base_url.rstrip('/')}/iserver/marketdata/snapshot?{q}"
    return _http_get_json(url, timeout, api_session=api_session)


def _symbol_to_conids(
    base_url: str,
    symbols: list[str],
    sec_type: str,
    timeout: float,
    api_session: str,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for sym in symbols:
        cid = cp_resolve_conid(base_url, sym, sec_type, timeout, api_session=api_session)
        if cid:
            out[sym] = cid
    return out


def chart_signals_from_cp_history(
    base_url: str,
    api_session: str,
    ibkr: dict[str, Any],
    symbols: list[str],
    sym_to_cid: dict[str, str],
    timeout: float,
    *,
    progress: bool = False,
) -> list[dict[str, Any]]:
    """GET /iserver/marketdata/history → OHLCV → compute_chart_signal_from_ohlcv (support/resistance)."""
    outside_cp = not ibkr["use_rth"]
    src = _map_what_to_show_to_cp_source(ibkr["what_to_show"])
    hist_ex = ibkr["exchange"] if ibkr["cp_include_exchange_in_history"] else ""
    min_rec = ibkr["min_bars_recommended"]
    pause = ibkr["request_pause_seconds"]
    period_tag = (
        f"CP {ibkr['cp_bar']}/{ibkr['cp_period']} RTH={ibkr['use_rth']}"
    )
    total = len(symbols)

    out: list[dict[str, Any]] = []
    for i, sym in enumerate(symbols):
        if pause > 0 and i > 0:
            if progress:
                print(
                    f"Chart history: pacing {pause:g}s before {sym} ({i + 1}/{total})…",
                    file=sys.stderr,
                    flush=True,
                )
            time.sleep(pause)
        cid = sym_to_cid.get(sym)
        if not cid:
            out.append({"Ticker": sym, "error": "No conid from secdef/search"})
            if progress:
                print(
                    f"Chart history: {sym} ({i + 1}/{total}) skipped — no conid.",
                    file=sys.stderr,
                    flush=True,
                )
            continue
        if progress:
            print(
                f"Chart history: {sym} ({i + 1}/{total}) fetching bars…",
                file=sys.stderr,
                flush=True,
            )
        df, err_msg = cp_fetch_history_df(
            base_url,
            cid,
            hist_ex,
            ibkr["cp_period"],
            ibkr["cp_bar"],
            outside_cp,
            src,
            timeout,
            api_session=api_session,
        )
        if df is None or getattr(df, "empty", True):
            err = err_msg or "No bars returned from CP history."
            out.append({"Ticker": sym, "error": err})
            if progress:
                print(
                    f"Chart history: {sym} ({i + 1}/{total}) failed — {err}",
                    file=sys.stderr,
                    flush=True,
                )
            continue
        meets = len(df) >= min_rec
        summary = {
            "Period used (yfinance)": period_tag,
            "Bars loaded": len(df),
            "Meets recommended bar count": meets,
            "Recommended min bars": min_rec,
        }
        payload = compute_chart_signal_from_ohlcv(
            sym,
            df,
            summary,
            pivot_left=ibkr["pivot_left"],
            pivot_right=ibkr["pivot_right"],
            atr_proximity_mult=ibkr["atr_proximity_mult"],
        )
        out.append(payload)
        if progress and "error" not in payload:
            bars = payload.get("Bars loaded", "?")
            print(
                f"Chart history: {sym} done ({bars} bars).",
                file=sys.stderr,
                flush=True,
            )
        elif progress:
            print(
                f"Chart history: {sym} error — {payload.get('error', payload)}",
                file=sys.stderr,
                flush=True,
            )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="IBKR Client Portal live market data snapshot (GET /iserver/marketdata/snapshot)."
    )
    ap.add_argument(
        "--fields",
        default=None,
        help=f"Comma-separated tick field ids (default: from config [ibkr] md_snapshot_fields or {_DEFAULT_FIELDS}). See IBKR Market Data Fields.",
    )
    ap.add_argument(
        "--json-out",
        action="store_true",
        help="Print pretty JSON only (no status lines).",
    )
    ap.add_argument(
        "--whatsapp-only",
        action="store_true",
        help=(
            "After snapshot, print only whatsapp_friendly_text (plain lines) and exit; "
            "no JSON. Ignored if --no-snapshot without quotes."
        ),
    )
    ap.add_argument(
        "--send-whatsapp",
        action="store_true",
        help=(
            "After snapshot, send whatsapp_friendly_text via Green API. Uses [trading] "
            "whatsapp_enabled, whatsapp_id_instance, whatsapp_api_token_instance, "
            "whatsapp_target_phone in config.ini (same as ChartSupportAndSignals)."
        ),
    )
    ap.add_argument(
        "--chart-support",
        action="store_true",
        help=(
            "After snapshot (or alone with --no-snapshot), fetch CP historical bars and "
            "compute nearest support/resistance, pivots, and heuristic signal "
            "(same logic as ChartSupportAndSignals_IBKR)."
        ),
    )
    ap.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Skip GET /iserver/accounts and market snapshot; only session + optional chart-support.",
    )
    ap.add_argument(
        "--drop-raw-snapshot",
        action="store_true",
        help="Omit raw IBKR snapshot JSON (numeric keys); output uses `quotes` + field_id_legend only.",
    )
    ap.add_argument(
        "--no-table",
        action="store_true",
        help="Do not print the ASCII quotes table (JSON still includes `quotes`).",
    )
    args = ap.parse_args()
    if args.no_snapshot and not args.chart_support:
        print(
            "--no-snapshot only makes sense with --chart-support",
            file=sys.stderr,
        )
        sys.exit(2)

    cfg_path = _SCRIPT_DIR / "config.ini"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        sys.exit(1)

    try:
        ibkr = load_ibkr_settings(cfg_path)
        symbols = load_trading_symbols(cfg_path)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    fields_csv = args.fields or _load_snapshot_fields(cfg_path)
    timeout = ibkr["cp_request_timeout_seconds"]
    base = _cp_base_url(ibkr["cp_gateway_host"], ibkr["cp_gateway_port"])

    # --- Session (required for all modes) ---
    _, api_sess = cp_tickle_post(base, min(timeout, 15.0), None)
    if not api_sess:
        print(
            "POST /tickle did not return a session. Start Client Portal Gateway, "
            "log in in the browser, then retry.",
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
        print(f"Session: {auth_msg}")

    _, sess2 = cp_tickle_post(base, min(timeout, 15.0), api_sess)
    if sess2:
        api_sess = sess2

    sym_to_cid = _symbol_to_conids(
        base,
        symbols,
        ibkr["sec_type"],
        timeout,
        api_sess,
    )
    missing = [s for s in symbols if s not in sym_to_cid]
    if missing:
        print(f"Could not resolve conid for: {', '.join(missing)}", file=sys.stderr)

    if not sym_to_cid:
        print("No contract ids resolved.", file=sys.stderr)
        sys.exit(1)

    out_obj: dict[str, Any] = {"symbols_requested": symbols}

    if not args.no_snapshot:
        try:
            accounts = cp_get_iserver_accounts(base, min(timeout, 30.0), api_sess)
        except urllib.error.HTTPError as exc:
            print(
                f"GET /iserver/accounts failed HTTP {exc.code}: {_http_error_detail(exc)}",
                file=sys.stderr,
            )
            sys.exit(1)

        if not args.json_out:
            acct_preview = json.dumps(accounts, indent=2)
            if acct_preview.strip() in ("{}", "[]", "null"):
                print(
                    "Accounts pre-flight: {} (empty — IB sometimes returns this before trading "
                    "session or on paper; snapshot may still work.)",
                    file=sys.stderr,
                )
            else:
                print(f"Accounts pre-flight: {acct_preview[:800]}...")

        conids_ordered = [sym_to_cid[s] for s in symbols if s in sym_to_cid]
        chunk_size = 100
        all_rows: list[Any] = []
        for i in range(0, len(conids_ordered), chunk_size):
            chunk = conids_ordered[i : i + chunk_size]
            try:
                snap = cp_marketdata_snapshot(
                    base, chunk, fields_csv, timeout, api_sess
                )
            except urllib.error.HTTPError as exc:
                print(
                    f"snapshot HTTP {exc.code}: {_http_error_detail(exc)}",
                    file=sys.stderr,
                )
                sys.exit(1)
            if isinstance(snap, list):
                all_rows.extend(snap)
            elif snap is not None:
                all_rows.append(snap)

        cid_to_sym = {v: k for k, v in sym_to_cid.items()}
        enriched = []
        for row in all_rows:
            if isinstance(row, dict):
                r = dict(row)
                cid = row.get("conid")
                if cid is not None and str(cid) in cid_to_sym:
                    r["_symbol"] = cid_to_sym[str(cid)]
                enriched.append(r)
            else:
                enriched.append(row)

        out_obj["fields_requested"] = fields_csv
        quotes = []
        for row in enriched:
            if isinstance(row, dict):
                quotes.append(humanize_snapshot_row(row))
            else:
                quotes.append({"_unparsed_row": row})
        out_obj["field_id_legend"] = _FIELD_ID_LEGEND
        out_obj["quote_field_definitions"] = _QUOTE_FIELD_DEFINITIONS
        out_obj["quotes"] = quotes
        out_obj["snapshot_key_aliases"] = dict(_IBKR_SNAPSHOT_NUMERIC_TO_LABEL)
        out_obj["snapshot_labeled"] = [
            label_ib_numeric_snapshot_row(dict(row))
            for row in enriched
            if isinstance(row, dict)
        ]
        out_obj["whatsapp_friendly_text"] = build_whatsapp_snapshot_digest(quotes)
        if not args.drop_raw_snapshot:
            out_obj["snapshot"] = enriched
        out_obj["note_snapshot_fields"] = (
            "Raw IBKR keys are tick field ids (see field_id_legend). Typical request "
            "31=last, 84=bid, 86=ask, 87=volume, 85=ask size, 88=bid size; 6509=data availability."
        )

        if not args.json_out and not args.no_table and quotes:
            _print_quotes_table(quotes)

    if args.chart_support:
        out_obj["chart_signals"] = chart_signals_from_cp_history(
            base,
            api_sess,
            ibkr,
            symbols,
            sym_to_cid,
            timeout,
        )
        out_obj["chart_note"] = (
            "Bars and pivots use [ibkr] cp_period/cp_bar (or duration/bar_size), "
            "pivot_left/right, atr_proximity_mult — same as ChartSupportAndSignals_IBKR."
        )

    if args.send_whatsapp:
        notify_cfg = load_whatsapp_notify_params(cfg_path)
        digest_send = (out_obj.get("whatsapp_friendly_text") or "").strip()
        ok, err_detail = send_whatsapp_plain_text(notify_cfg, digest_send)
        out_obj["whatsapp_delivery"] = {
            "attempted": True,
            "success": ok,
            "detail": None if ok else err_detail,
        }
        if not args.json_out:
            if ok:
                print("WhatsApp: snapshot digest sent.", file=sys.stderr)
            else:
                print(f"WhatsApp: not sent — {err_detail}", file=sys.stderr)

    if args.whatsapp_only:
        digest = out_obj.get("whatsapp_friendly_text")
        if digest:
            print(digest)
        elif not args.json_out:
            print(
                "No whatsapp_friendly_text (use snapshot without --no-snapshot).",
                file=sys.stderr,
            )
        return

    print(json.dumps(out_obj, indent=2))


if __name__ == "__main__":
    main()
