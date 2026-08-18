"""
Intraday / near-real-time support heuristics using Interactive Brokers.

Default: Client Portal Web API (HTTPS to local Client Portal Gateway).
Optional: classic TWS / IB Gateway socket API via ib_insync (config: ibkr_data_source).

Not financial advice.

Client Portal: log in in a browser; POST /tickle yields session → send Cookie api=<session>
on all /v1/api calls; then POST /iserver/auth/ssodh/init for brokerage (market data).
See IBKR CP Web API docs (tickle, authentication). Stdlib HTTP only.
Socket mode: pip install ib-insync
"""

from __future__ import annotations

import configparser
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from averagePriceFetcher import write_csv_dicts

from ChartSupportAndSignals import (  # noqa: E402
    CHART_SIGNALS_CSV_FIELDNAMES,
    _configure_stdio_utf8,
    _targets_ok,
    chart_signal_to_csv_row,
    compute_chart_signal_from_ohlcv,
    load_whatsapp_notify_params,
    _send_whatsapp_messages_for_signals,
)

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 7497
_DEFAULT_CLIENT_ID = 12
_DEFAULT_BAR_SIZE = "5 mins"
_DEFAULT_DURATION = "5 D"
_DEFAULT_CP_PORT = 5000
_DEFAULT_DATA_SOURCE = "client_portal"


def _ssl_insecure_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace").strip()
        if len(raw) > 800:
            return raw[:800] + "..."
        return raw
    except Exception:
        return ""


def _cp_base_url(host: str, port: int) -> str:
    return f"https://{host}:{port}/v1/api"


def _cp_request_headers(api_session: str | None) -> dict[str, str]:
    """Gateway expects POST /tickle first; pass returned session as Cookie api=<id> on later calls."""
    h: dict[str, str] = {"User-Agent": "Console"}
    if api_session:
        h["Cookie"] = f"api={api_session}"
    return h


def _http_get_json(
    url: str, timeout: float, api_session: str | None = None
) -> Any:
    req = urllib.request.Request(
        url,
        method="GET",
        headers=_cp_request_headers(api_session),
    )
    ctx = _ssl_insecure_context()
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    if not body:
        return None
    return json.loads(body)


def _http_post_json(
    url: str, body: dict[str, Any], timeout: float, api_session: str | None = None
) -> Any:
    payload = json.dumps(body).encode("utf-8")
    h = _cp_request_headers(api_session)
    h["Content-Type"] = "application/json"
    h["Accept"] = "application/json"
    req = urllib.request.Request(url, data=payload, method="POST", headers=h)
    ctx = _ssl_insecure_context()
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    if not raw:
        return None
    return json.loads(raw)


def _cp_get(
    base_url: str,
    path: str,
    params: dict[str, Any],
    timeout: float,
    api_session: str | None = None,
) -> Any:
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{base_url.rstrip('/')}{path}"
    if q:
        url = f"{url}?{q}"
    return _http_get_json(url, timeout=timeout, api_session=api_session)


def _to_cp_period(legacy: str) -> str:
    t = legacy.strip().replace(" ", "")
    if not t:
        return "5d"
    return t.lower()


def _to_cp_bar(legacy: str) -> str:
    t = legacy.strip().lower().replace(" ", "")
    t = t.replace("mins", "min")
    t = t.replace("minute", "min")
    if t == "1day":
        return "1d"
    return t


def _map_what_to_show_to_cp_source(what: str) -> str:
    w = (what or "TRADES").strip().upper()
    if w in ("TRADES", "TRADE"):
        return "Trades"
    if w in ("MIDPOINT", "MID"):
        return "Midpoint"
    if w in ("BID_ASK", "BIDASK"):
        return "Bid_Ask"
    return "Trades"


def _cp_history_json_to_ohlcv(payload: dict[str, Any]) -> pd.DataFrame | None:
    if not isinstance(payload, dict) or payload.get("error"):
        return None
    bars = payload.get("data")
    if not bars:
        return None
    rows: list[dict[str, Any]] = []
    for b in bars:
        if not isinstance(b, dict):
            continue
        ts = b.get("t")
        if ts is None:
            continue
        t_int = int(ts)
        if t_int > 10**15:
            dt = pd.to_datetime(t_int / 1_000_000_000.0, unit="s", utc=True)
        elif t_int > 10**12:
            dt = pd.to_datetime(t_int, unit="ms", utc=True)
        elif t_int > 10**9:
            dt = pd.to_datetime(t_int, unit="s", utc=True)
        else:
            continue
        rows.append(
            {
                "date": dt,
                "Open": float(b.get("o", 0) or 0),
                "High": float(b.get("h", 0) or 0),
                "Low": float(b.get("l", 0) or 0),
                "Close": float(b.get("c", 0) or 0),
                "Volume": float(b.get("v", 0) or 0),
            }
        )
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df = df.set_index("date").sort_index()
    return df


def _parse_conid_from_secdef_search(data: Any, symbol: str) -> str | None:
    sym_u = symbol.upper()
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            if str(item.get("symbol", "")).upper() == sym_u:
                cid = item.get("conid")
                if cid is not None:
                    return str(cid)
        if data and isinstance(data[0], dict) and data[0].get("conid") is not None:
            return str(data[0]["conid"])
    if isinstance(data, dict):
        if data.get("conid") is not None:
            return str(data["conid"])
    return None


def cp_resolve_conid(
    base_url: str,
    symbol: str,
    sec_type: str,
    timeout: float,
    api_session: str | None = None,
) -> str | None:
    raw = _cp_get(
        base_url,
        "/iserver/secdef/search",
        {"symbol": symbol, "secType": sec_type},
        timeout,
        api_session=api_session,
    )
    return _parse_conid_from_secdef_search(raw, symbol)


def cp_fetch_history_df(
    base_url: str,
    conid: str,
    exchange: str,
    period_cp: str,
    bar_cp: str,
    outside_rth: bool,
    source: str,
    timeout: float,
    api_session: str | None = None,
) -> tuple[pd.DataFrame | None, str | None]:
    # Omit exchange when blank so CP uses the contract primary (IB docs: SMART optional).
    params: dict[str, Any] = {
        "conid": conid,
        "period": period_cp,
        "bar": bar_cp,
        "outsideRth": "true" if outside_rth else "false",
        "source": source,
    }
    ex = (exchange or "").strip()
    if ex:
        params["exchange"] = ex
    try:
        raw = _cp_get(
            base_url,
            "/iserver/marketdata/history",
            params,
            timeout,
            api_session=api_session,
        )
    except urllib.error.HTTPError as exc:
        detail = _http_error_detail(exc)
        tail = f" {detail}" if detail else ""
        return None, f"HTTP {exc.code} on /marketdata/history{tail}"
    except urllib.error.URLError as exc:
        return None, f"network error on /marketdata/history: {exc.reason!r}"
    if isinstance(raw, dict) and raw.get("error"):
        return None, str(raw.get("error"))
    df = _cp_history_json_to_ohlcv(raw if isinstance(raw, dict) else {})
    if df is None or df.empty:
        err = None
        if isinstance(raw, dict):
            err = raw.get("text") or raw.get("message")
        return None, err or "empty_history"
    return df, None


def cp_tickle_post(
    base_url: str, timeout: float, api_session: str | None = None
) -> tuple[bool, str | None]:
    """
    IB docs: POST /tickle (not GET). Response 'session' must be sent as Cookie api=<session>
    on subsequent /v1/api requests so HMDS/iserver requests are bridged.
    """
    api = base_url.rstrip("/")
    url = f"{api}/tickle"
    try:
        raw = _http_post_json(url, {}, timeout, api_session=api_session)
        if isinstance(raw, dict) and raw.get("session"):
            return True, str(raw["session"])
    except Exception:
        return False, None
    return False, None


def cp_ensure_brokerage_session(
    base_url: str,
    timeout: float,
    *,
    compete: bool,
    max_wait: float,
    api_session: str | None,
) -> tuple[bool, str]:
    """
    IBKR: browser login creates a portal session; market data needs a brokerage session.
    POST /iserver/auth/ssodh/init opens that session (see CP API docs).
    Requires Cookie api=<session> from POST /tickle (passed as api_session).
    """
    if not api_session:
        return (
            False,
            "No gateway session id — POST /tickle did not return a session token.",
        )
    api = base_url.rstrip("/")
    status_url = f"{api}/iserver/auth/status"
    init_url = f"{api}/iserver/auth/ssodh/init"

    try:
        st = _http_post_json(status_url, {}, timeout, api_session=api_session)
    except urllib.error.HTTPError as exc:
        detail = _http_error_detail(exc)
        if exc.code == 401:
            login_root = base_url.replace("/v1/api", "").rstrip("/")
            return (
                False,
                "Client Portal Gateway returned 401 on auth/status. "
                f"Open {login_root} in a browser, sign in with IB credentials, "
                "keep the gateway running, then rerun.",
            )
        return False, f"auth/status failed HTTP {exc.code}: {detail}"
    except Exception as exc:
        return False, f"auth/status failed: {exc}"

    if not isinstance(st, dict):
        return False, "auth/status returned unexpected payload"

    if st.get("authenticated"):
        return True, "brokerage session already authenticated"

    try:
        init_resp = _http_post_json(
            init_url,
            {"publish": True, "compete": compete},
            timeout,
            api_session=api_session,
        )
    except urllib.error.HTTPError as exc:
        detail = _http_error_detail(exc)
        return False, f"ssodh/init failed HTTP {exc.code}: {detail}"
    except Exception as exc:
        return False, f"ssodh/init failed: {exc}"

    if isinstance(init_resp, dict) and init_resp.get("authenticated"):
        return True, "brokerage session ready (ssodh/init)"

    deadline = time.monotonic() + max(5.0, max_wait)
    while time.monotonic() < deadline:
        try:
            st = _http_post_json(status_url, {}, timeout, api_session=api_session)
        except urllib.error.HTTPError as exc:
            detail = _http_error_detail(exc)
            return False, f"auth/status after init failed HTTP {exc.code}: {detail}"
        except Exception as exc:
            return False, f"auth/status after init failed: {exc}"
        if isinstance(st, dict) and st.get("authenticated"):
            return True, "brokerage session ready (after ssodh/init)"
        time.sleep(1.0)

    msg = ""
    try:
        st = _http_post_json(status_url, {}, timeout, api_session=api_session)
        if isinstance(st, dict):
            msg = (st.get("message") or "").strip()
    except Exception:
        pass
    tail = f" Message: {msg}" if msg else ""
    return (
        False,
        "Timed out waiting for authenticated=true after ssodh/init."
        f"{tail} Check IB login and market-data permissions.",
    )


def load_trading_symbols(cfg_path: Path) -> list[str]:
    parser = configparser.ConfigParser()
    parser.read(cfg_path, encoding="utf-8")
    if not parser.has_section("trading"):
        raise ValueError(f"Missing [trading] in {cfg_path}")
    raw = parser.get("trading", "symbols", fallback="").strip()
    if not raw:
        raise ValueError("No symbols configured under [trading].")
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def load_ibkr_settings(cfg_path: Path) -> dict[str, Any]:
    parser = configparser.ConfigParser()
    parser.read(cfg_path, encoding="utf-8")
    if not parser.has_section("ibkr"):
        raise ValueError(
            f"Missing [ibkr] section in {cfg_path}. See comments in config.ini for keys."
        )
    sec = "ibkr"
    data_source = (
        parser.get(sec, "ibkr_data_source", fallback=_DEFAULT_DATA_SOURCE)
        .strip()
        .lower()
    )
    if data_source not in ("client_portal", "tws_socket"):
        data_source = "client_portal"

    host = parser.get(sec, "host", fallback=_DEFAULT_HOST).strip() or _DEFAULT_HOST
    port = parser.getint(sec, "port", fallback=_DEFAULT_PORT)
    client_id = parser.getint(sec, "client_id", fallback=_DEFAULT_CLIENT_ID)
    readonly = parser.getboolean(sec, "readonly", fallback=True)
    exchange = parser.get(sec, "exchange", fallback="SMART").strip() or "SMART"
    currency = parser.get(sec, "currency", fallback="USD").strip() or "USD"
    bar_size = parser.get(sec, "bar_size", fallback=_DEFAULT_BAR_SIZE).strip() or _DEFAULT_BAR_SIZE
    duration = parser.get(sec, "duration", fallback=_DEFAULT_DURATION).strip() or _DEFAULT_DURATION
    what_to_show = parser.get(sec, "what_to_show", fallback="TRADES").strip() or "TRADES"
    use_rth = parser.getboolean(sec, "use_rth", fallback=True)
    pause = parser.getfloat(sec, "request_pause_seconds", fallback=11.0)
    pivot_left = parser.getint(sec, "pivot_left", fallback=5)
    pivot_right = parser.getint(sec, "pivot_right", fallback=5)
    atr_mult = parser.getfloat(sec, "atr_proximity_mult", fallback=1.15)
    min_rec = parser.getint(sec, "min_bars_recommended", fallback=200)
    sec_type = parser.get(sec, "sec_type", fallback="STK").strip() or "STK"
    cp_host = parser.get(sec, "cp_gateway_host", fallback="127.0.0.1").strip() or "127.0.0.1"
    cp_port = parser.getint(sec, "cp_gateway_port", fallback=_DEFAULT_CP_PORT)
    cp_timeout = parser.getfloat(sec, "cp_request_timeout_seconds", fallback=60.0)
    cp_period = parser.get(sec, "cp_period", fallback="").strip()
    cp_bar = parser.get(sec, "cp_bar", fallback="").strip()
    cp_include_exchange = parser.getboolean(
        sec, "cp_include_exchange_in_history", fallback=True
    )
    cp_ssodh_compete = parser.getboolean(sec, "cp_ssodh_compete", fallback=True)
    cp_brokerage_wait = parser.getfloat(sec, "cp_brokerage_auth_wait_seconds", fallback=45.0)
    out_csv = parser.get(sec, "output_csv", fallback="chart_support_signals_ibkr.csv").strip()
    out_path = Path(out_csv)
    if not out_path.is_absolute():
        out_path = cfg_path.parent / out_path
    ws_state_raw = parser.get(
        sec, "whatsapp_notify_state_file", fallback="chart_support_notify_state_ibkr.json"
    ).strip() or "chart_support_notify_state_ibkr.json"
    ws_state = Path(ws_state_raw)
    if not ws_state.is_absolute():
        ws_state = cfg_path.parent / ws_state

    period_out = _to_cp_period(cp_period) if cp_period else _to_cp_period(duration)
    bar_out = _to_cp_bar(cp_bar) if cp_bar else _to_cp_bar(bar_size)

    return {
        "data_source": data_source,
        "host": host,
        "port": port,
        "client_id": client_id,
        "readonly": readonly,
        "exchange": exchange,
        "currency": currency,
        "bar_size": bar_size,
        "duration": duration,
        "cp_period": period_out,
        "cp_bar": bar_out,
        "what_to_show": what_to_show,
        "use_rth": use_rth,
        "request_pause_seconds": max(0.0, float(pause)),
        "pivot_left": max(1, pivot_left),
        "pivot_right": max(1, pivot_right),
        "atr_proximity_mult": max(0.5, float(atr_mult)),
        "min_bars_recommended": max(50, min_rec),
        "output_csv": out_path,
        "whatsapp_notify_state_file": ws_state,
        "cp_gateway_host": cp_host,
        "cp_gateway_port": cp_port,
        "cp_request_timeout_seconds": max(5.0, float(cp_timeout)),
        "sec_type": sec_type,
        "cp_include_exchange_in_history": cp_include_exchange,
        "cp_ssodh_compete": cp_ssodh_compete,
        "cp_brokerage_auth_wait_seconds": max(5.0, float(cp_brokerage_wait)),
    }


def _normalize_ibkr_df(df_raw: pd.DataFrame) -> pd.DataFrame | None:
    if df_raw is None or df_raw.empty:
        return None
    df = df_raw.copy()
    colmap = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    lower = {c.lower(): c for c in df.columns}
    rename: dict[str, str] = {}
    for lc, canon in colmap.items():
        if lc in lower:
            rename[lower[lc]] = canon
    df = df.rename(columns=rename)

    req = {"Open", "High", "Low", "Close"}
    if not req.issubset(df.columns):
        return None

    if "Volume" not in df.columns:
        df["Volume"] = 0.0

    if not isinstance(df.index, pd.DatetimeIndex):
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], utc=False)
            df = df.set_index("date")
        else:
            return None

    df = df.sort_index()
    return df


def _ibkr_contract(symbol: str, exchange: str, currency: str):
    from ib_insync import Stock

    return Stock(symbol, exchange, currency)


def fetch_ibkr_intraday_socket(
    symbol: str, ib: Any, ibkr_cfg: dict[str, Any]
) -> pd.DataFrame | None:
    from ib_insync import util

    contract = _ibkr_contract(symbol, ibkr_cfg["exchange"], ibkr_cfg["currency"])
    qualified = ib.qualifyContracts(contract)
    if not qualified:
        return None
    contract = qualified[0]

    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr=ibkr_cfg["duration"],
        barSizeSetting=ibkr_cfg["bar_size"],
        whatToShow=ibkr_cfg["what_to_show"],
        useRTH=ibkr_cfg["use_rth"],
        formatDate=1,
        keepUpToDate=False,
    )
    return _normalize_ibkr_df(util.df(bars))


def main() -> None:
    _configure_stdio_utf8()
    cfg_path = _SCRIPT_DIR / "config.ini"

    try:
        ibkr_cfg = load_ibkr_settings(cfg_path)
        symbols = load_trading_symbols(cfg_path)
        notify_cfg = load_whatsapp_notify_params(cfg_path)
        notify_cfg["state_file"] = ibkr_cfg["whatsapp_notify_state_file"]
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    rows_out: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    errors = 0
    pause = ibkr_cfg["request_pause_seconds"]
    min_rec = ibkr_cfg["min_bars_recommended"]
    mode = ibkr_cfg["data_source"]

    if mode == "client_portal":
        base = _cp_base_url(ibkr_cfg["cp_gateway_host"], ibkr_cfg["cp_gateway_port"])
        timeout = ibkr_cfg["cp_request_timeout_seconds"]
        outside_cp = not ibkr_cfg["use_rth"]
        src = _map_what_to_show_to_cp_source(ibkr_cfg["what_to_show"])
        period_tag = (
            f"CP {ibkr_cfg['cp_bar']}/{ibkr_cfg['cp_period']} "
            f"RTH={ibkr_cfg['use_rth']}"
        )

        _, api_sess = cp_tickle_post(base, min(timeout, 15.0), None)
        if not api_sess:
            print(
                "POST /tickle did not return a session id. Is Client Portal Gateway running? "
                "Open https://"
                f"{ibkr_cfg['cp_gateway_host']}:{ibkr_cfg['cp_gateway_port']} "
                "in a browser, sign in, keep the gateway running, then rerun.",
                file=sys.stderr,
            )
            sys.exit(1)

        auth_ok, auth_msg = cp_ensure_brokerage_session(
            base,
            min(timeout, 60.0),
            compete=ibkr_cfg["cp_ssodh_compete"],
            max_wait=ibkr_cfg["cp_brokerage_auth_wait_seconds"],
            api_session=api_sess,
        )
        print(f"Client Portal session: {auth_msg}")
        if not auth_ok:
            print(auth_msg, file=sys.stderr)
            sys.exit(1)

        _, sess_after = cp_tickle_post(base, min(timeout, 15.0), api_sess)
        if sess_after:
            api_sess = sess_after

        conid_cache: dict[str, str] = {}
        for i, sym in enumerate(symbols):
            if pause > 0 and i > 0:
                time.sleep(pause)
            df = None
            err_msg: str | None = None
            try:
                if sym not in conid_cache:
                    cid = cp_resolve_conid(
                        base,
                        sym,
                        ibkr_cfg["sec_type"],
                        timeout,
                        api_session=api_sess,
                    )
                    if not cid:
                        raise RuntimeError("secdef/search returned no conid")
                    conid_cache[sym] = cid
                else:
                    cid = conid_cache[sym]
                hist_ex = (
                    ibkr_cfg["exchange"]
                    if ibkr_cfg["cp_include_exchange_in_history"]
                    else ""
                )
                df, err_msg = cp_fetch_history_df(
                    base,
                    cid,
                    hist_ex,
                    ibkr_cfg["cp_period"],
                    ibkr_cfg["cp_bar"],
                    outside_cp,
                    src,
                    timeout,
                    api_session=api_sess,
                )
                if df is None:
                    raise RuntimeError(err_msg or "empty_history")
            except urllib.error.HTTPError as exc:
                detail = _http_error_detail(exc)
                err_msg = f"HTTP {exc.code}"
                if detail:
                    err_msg = f"{err_msg}: {detail}"
                payloads.append({"Ticker": sym, "error": err_msg})
                rows_out.append(chart_signal_to_csv_row(sym, payloads[-1]))
                errors += 1
                print(f"{sym}: {err_msg}", file=sys.stderr)
                if exc.code == 401:
                    print(
                        "  CP hint: no brokerage session — open https://"
                        f"{ibkr_cfg['cp_gateway_host']}:{ibkr_cfg['cp_gateway_port']}"
                        " in a browser, log in to Client Portal Gateway, rerun.",
                        file=sys.stderr,
                    )
                elif exc.code == 400:
                    if "no bridge" in err_msg.lower():
                        print(
                            "  CP hint: 'no bridge' usually means requests lacked the gateway "
                            "session cookie (script now sends Cookie: api=<session> from POST /tickle). "
                            "If this persists, restart the gateway, log in again, retry.",
                            file=sys.stderr,
                        )
                    else:
                        print(
                            "  CP hint: bad request — often invalid period+bar (IB step-size rules), "
                            "wrong conid, or market-data entitlement. "
                            "Try e.g. cp_period = 1d with cp_bar = 5min, or cp_bar = 10min for multi-day.",
                            file=sys.stderr,
                        )
                continue
            except Exception as exc:
                payloads.append({"Ticker": sym, "error": str(exc)})
                rows_out.append(chart_signal_to_csv_row(sym, payloads[-1]))
                errors += 1
                print(f"{sym}: {exc}", file=sys.stderr)
                continue

            if df is None or df.empty:
                summary = {
                    "Period used (yfinance)": period_tag,
                    "Bars loaded": 0 if df is None else len(df),
                    "Meets recommended bar count": False,
                    "Recommended min bars": min_rec,
                }
                payloads.append(
                    {
                        "Ticker": sym,
                        "error": err_msg or "No bars returned from Client Portal.",
                        **summary,
                    }
                )
                rows_out.append(chart_signal_to_csv_row(sym, payloads[-1]))
                errors += 1
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
                pivot_left=ibkr_cfg["pivot_left"],
                pivot_right=ibkr_cfg["pivot_right"],
                atr_proximity_mult=ibkr_cfg["atr_proximity_mult"],
            )
            payloads.append(payload)
            rows_out.append(chart_signal_to_csv_row(sym, payload))
            if not _targets_ok(payload):
                errors += 1
                print(f"{sym}: {payload.get('error', payload)}", file=sys.stderr)

    else:
        try:
            from ib_insync import IB
        except ImportError:
            print(
                "Socket mode requires: pip install ib-insync",
                file=sys.stderr,
            )
            sys.exit(1)

        ib = IB()
        period_tag = (
            f"Socket {ibkr_cfg['bar_size']}/{ibkr_cfg['duration']} "
            f"RTH={ibkr_cfg['use_rth']}"
        )
        try:
            ib.connect(
                ibkr_cfg["host"],
                ibkr_cfg["port"],
                clientId=ibkr_cfg["client_id"],
                readonly=ibkr_cfg["readonly"],
            )
            for i, sym in enumerate(symbols):
                if pause > 0 and i > 0:
                    time.sleep(pause)
                df = None
                try:
                    df = fetch_ibkr_intraday_socket(sym, ib, ibkr_cfg)
                except Exception as exc:
                    payloads.append({"Ticker": sym, "error": str(exc)})
                    rows_out.append(chart_signal_to_csv_row(sym, payloads[-1]))
                    errors += 1
                    print(f"{sym}: {exc}", file=sys.stderr)
                    continue

                if df is None or df.empty:
                    summary = {
                        "Period used (yfinance)": period_tag,
                        "Bars loaded": 0 if df is None else len(df),
                        "Meets recommended bar count": False,
                        "Recommended min bars": min_rec,
                    }
                    payloads.append(
                        {
                            "Ticker": sym,
                            "error": "No bars returned from IBKR socket.",
                            **summary,
                        }
                    )
                    rows_out.append(chart_signal_to_csv_row(sym, payloads[-1]))
                    errors += 1
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
                    pivot_left=ibkr_cfg["pivot_left"],
                    pivot_right=ibkr_cfg["pivot_right"],
                    atr_proximity_mult=ibkr_cfg["atr_proximity_mult"],
                )
                payloads.append(payload)
                rows_out.append(chart_signal_to_csv_row(sym, payload))
                if not _targets_ok(payload):
                    errors += 1
                    print(f"{sym}: {payload.get('error', payload)}", file=sys.stderr)
        except Exception as exc:
            print(
                "Could not connect to TWS/IB Gateway socket. "
                "Check host/port/client_id and API enabled.",
                file=sys.stderr,
            )
            print(f"Underlying error: {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            if ib.isConnected():
                ib.disconnect()

    write_csv_dicts(rows_out, ibkr_cfg["output_csv"], CHART_SIGNALS_CSV_FIELDNAMES)
    print(
        f"Wrote {len(rows_out)} row(s) to {ibkr_cfg['output_csv']} "
        f"(mode={mode}; pivots={ibkr_cfg['pivot_left']}/{ibkr_cfg['pivot_right']})"
    )
    sent = _send_whatsapp_messages_for_signals(payloads, notify_cfg)
    if notify_cfg.get("enabled"):
        print(f"WhatsApp notifications sent: {sent}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
