"""Orchestrate baseline / refresh of IBKR trade + corporate history."""

from __future__ import annotations

import configparser
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from flex_buysell_report import (
    IBKR_TRANSACTION_DIR,
    discover_latest_csv,
    download_flex_trades_chunked,
    load_config,
    load_trades_combined,
)
from flex_ytd import sync_ytd
from trade_history.corporate_parse import (
    load_corporate_from_flex_downloads,
    load_corporate_from_transactions_dir,
)
from trade_history.export import write_trade_history_workbook
from trade_history import store as store_mod
from trade_history.state import (
    HistoryState,
    load_state,
    parse_iso_date,
    save_state,
    today_iso,
    utc_now_iso,
    yyyymmdd,
)

SCRIPT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SCRIPT_DIR / "config.ini"


def _clean(value: str) -> str:
    out = value.strip()
    if len(out) >= 2 and out[0] == out[-1] and out[0] in "\"'":
        out = out[1:-1].strip()
    return out


def load_history_config(config_path: Path) -> dict:
    base = load_config(config_path, required_for_download=False)
    parser = configparser.ConfigParser()
    if config_path.is_file():
        parser.read(config_path, encoding="utf-8")
    hist = parser["history"] if parser.has_section("history") else {}

    account_open = _clean(hist.get("account_open_date", "") or "")
    if not account_open:
        fd = base["from_date"]
        account_open = f"{fd[:4]}-{fd[4:6]}-{fd[6:8]}"

    store_dir = _clean(hist.get("store_dir", "data/store") or "data/store")
    store_path = Path(store_dir)
    if not store_path.is_absolute():
        store_path = SCRIPT_DIR / store_path

    state_path = _clean(hist.get("state_path", "data/state.json") or "data/state.json")
    state_file = Path(state_path)
    if not state_file.is_absolute():
        state_file = SCRIPT_DIR / state_file

    report = _clean(
        hist.get("report_path", "reports/IBKR_TradeHistory.xlsx")
        or "reports/IBKR_TradeHistory.xlsx"
    )
    report_path = Path(report)
    if not report_path.is_absolute():
        report_path = SCRIPT_DIR / report_path

    tx_dir = _clean(hist.get("transactions_dir", "") or "")
    transactions_dir = Path(tx_dir) if tx_dir else IBKR_TRANSACTION_DIR
    if not transactions_dir.is_absolute():
        transactions_dir = SCRIPT_DIR / transactions_dir

    corporate_qid = _clean(hist.get("corporate_query_id", "") or "") or base["query_id"]

    return {
        **base,
        "account_open_date": account_open,
        "refresh_overlap_days": int(hist.get("refresh_overlap_days", "7") or "7"),
        "store_dir": store_path,
        "state_path": state_file,
        "history_report_path": report_path,
        "transactions_dir": transactions_dir,
        "corporate_query_id": corporate_qid,
        "fetch_market_prices": str(hist.get("fetch_market_prices", "true")).lower()
        in ("1", "true", "yes"),
    }


def _apply_account_open_filter(trades: pd.DataFrame, account_open_date: str) -> pd.DataFrame:
    if trades.empty:
        return trades
    cutoff = pd.Timestamp(account_open_date)
    out = trades.copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    return out.loc[out["Date"] >= cutoff].copy()


def _load_corporate(cfg: dict) -> pd.DataFrame:
    from trade_history.store import merge_corporate

    activity = load_corporate_from_transactions_dir(cfg["transactions_dir"])
    flex_corp = load_corporate_from_flex_downloads(cfg["download_dir"], cfg["corporate_query_id"])
    return merge_corporate(activity, flex_corp)


def _maybe_sync_ytd(cfg: dict, *, force_flex: bool = False) -> None:
    activity = discover_latest_csv(cfg["transactions_dir"])
    try:
        sync_ytd(
            cfg,
            activity,
            try_flex=bool(cfg.get("token") and cfg.get("query_id")),
            force_activity=True,
            force_flex=force_flex,
        )
    except Exception as exc:
        print(f"Warning: YTD sync skipped: {exc}")


def _download_trades_if_needed(cfg: dict, *, force: bool, do_download: bool) -> tuple[pd.DataFrame, str]:
    labels: list[str] = []
    if do_download:
        if not cfg.get("token") or not cfg.get("query_id"):
            raise FileNotFoundError(
                "Flex token/query_id required for download. "
                "Use --offline to build from cache/Activity CSV only."
            )
        open_d = parse_iso_date(cfg["account_open_date"])
        cfg = {**cfg, "from_date": yyyymmdd(open_d), "to_date": yyyymmdd(date.today())}
        hist, hist_label = download_flex_trades_chunked(cfg, force=force)
        labels.append(hist_label)
        _maybe_sync_ytd(cfg, force_flex=force)

    trades, label = load_trades_combined(
        cfg["download_dir"], cfg["query_id"], cfg["transactions_dir"]
    )
    labels.append(label)
    trades = _apply_account_open_filter(trades, cfg["account_open_date"])
    return trades, " | ".join(labels)


class HistoryError(Exception):
    """User-facing orchestration error."""


def run_baseline(
    cfg: dict,
    *,
    force_rebaseline: bool = False,
    offline: bool = False,
    fetch_market_prices: bool | None = None,
) -> Path:
    state_path: Path = cfg["state_path"]
    store_dir: Path = cfg["store_dir"]
    existing = load_state(state_path)
    if existing and not force_rebaseline:
        raise HistoryError(
            f"Baseline already exists at {state_path}. "
            "Use refresh, or baseline --force-rebaseline."
        )

    if force_rebaseline and store_dir.exists():
        for name in (store_mod.TRADES_FILE, store_mod.CORPORATE_FILE):
            p = store_dir / name
            p.unlink(missing_ok=True)

    trades, source = _download_trades_if_needed(
        cfg, force=force_rebaseline, do_download=not offline
    )
    if trades.empty:
        raise HistoryError("No trades found for baseline. Check Flex cache / Activity CSV.")

    corporate = _load_corporate(cfg)
    if not corporate.empty and "Date" in corporate.columns:
        cutoff = pd.Timestamp(cfg["account_open_date"])
        corporate = corporate.loc[
            pd.to_datetime(corporate["Date"], errors="coerce") >= cutoff
        ].copy()

    store_mod.save_trades(store_dir, trades)
    store_mod.save_corporate(store_dir, corporate)
    watermark = store_mod.max_date_iso(trades, corporate) or today_iso()

    state = HistoryState(
        account_open_date=cfg["account_open_date"],
        baseline_completed_at=utc_now_iso(),
        watermark_date=watermark,
        trade_query_id=cfg["query_id"],
        corporate_query_id=cfg["corporate_query_id"],
        row_counts={
            "trades": len(trades),
            "corporate_actions": 0 if corporate.empty else len(corporate),
        },
        last_mode="baseline",
        last_source_label=source,
    )
    save_state(state_path, state)

    marks = cfg["fetch_market_prices"] if fetch_market_prices is None else fetch_market_prices
    write_trade_history_workbook(
        trades,
        corporate,
        cfg["history_report_path"],
        mode="baseline",
        source_label=source,
        account_open_date=cfg["account_open_date"],
        watermark_date=watermark,
        fetch_market_prices=marks,
    )
    return cfg["history_report_path"]


def run_refresh(
    cfg: dict,
    *,
    offline: bool = False,
    fetch_market_prices: bool | None = None,
) -> Path:
    state_path: Path = cfg["state_path"]
    store_dir: Path = cfg["store_dir"]
    state = load_state(state_path)
    if state is None:
        raise HistoryError("No baseline found. Run: python -m trade_history baseline")

    existing_trades = store_mod.load_trades(store_dir)
    existing_corp = store_mod.load_corporate(store_dir)

    overlap = int(cfg["refresh_overlap_days"])
    wm = parse_iso_date(state.watermark_date or state.account_open_date)
    from_d = wm - timedelta(days=overlap)
    open_d = parse_iso_date(cfg["account_open_date"])
    if from_d < open_d:
        from_d = open_d

    refresh_cfg = {
        **cfg,
        "from_date": yyyymmdd(from_d),
        "to_date": yyyymmdd(date.today()),
    }

    if not offline:
        if not cfg.get("token") or not cfg.get("query_id"):
            raise FileNotFoundError(
                "Flex token/query_id required for refresh download. Use --offline."
            )
        try:
            download_flex_trades_chunked(refresh_cfg, force=False)
        except Exception as exc:
            print(f"Warning: Flex history download issue: {exc}")
        _maybe_sync_ytd(refresh_cfg, force_flex=False)

    incoming, source = load_trades_combined(
        cfg["download_dir"], cfg["query_id"], cfg["transactions_dir"]
    )
    incoming = _apply_account_open_filter(incoming, cfg["account_open_date"])
    if not incoming.empty:
        incoming = incoming.loc[
            pd.to_datetime(incoming["Date"], errors="coerce") >= pd.Timestamp(from_d)
        ].copy()

    merged_trades = store_mod.merge_trades(existing_trades, incoming)
    new_corp = _load_corporate(cfg)
    merged_corp = store_mod.merge_corporate(existing_corp, new_corp)

    store_mod.save_trades(store_dir, merged_trades)
    store_mod.save_corporate(store_dir, merged_corp)
    watermark = store_mod.max_date_iso(merged_trades, merged_corp) or today_iso()

    state.watermark_date = watermark
    state.row_counts = {
        "trades": len(merged_trades),
        "corporate_actions": 0 if merged_corp.empty else len(merged_corp),
    }
    state.last_mode = "refresh"
    state.last_source_label = source
    save_state(state_path, state)

    marks = cfg["fetch_market_prices"] if fetch_market_prices is None else fetch_market_prices
    write_trade_history_workbook(
        merged_trades,
        merged_corp,
        cfg["history_report_path"],
        mode="refresh",
        source_label=source,
        account_open_date=cfg["account_open_date"],
        watermark_date=watermark,
        fetch_market_prices=marks,
    )
    return cfg["history_report_path"]


def run_export(cfg: dict, *, fetch_market_prices: bool | None = None) -> Path:
    state = load_state(cfg["state_path"])
    if state is None:
        raise HistoryError("No baseline found. Run baseline first.")
    trades = store_mod.load_trades(cfg["store_dir"])
    corp = store_mod.load_corporate(cfg["store_dir"])
    marks = cfg["fetch_market_prices"] if fetch_market_prices is None else fetch_market_prices
    write_trade_history_workbook(
        trades,
        corp,
        cfg["history_report_path"],
        mode="export",
        source_label=state.last_source_label or "store",
        account_open_date=state.account_open_date or cfg["account_open_date"],
        watermark_date=state.watermark_date,
        fetch_market_prices=marks,
    )
    return cfg["history_report_path"]


def run_status(cfg: dict) -> int:
    state = load_state(cfg["state_path"])
    if state is None:
        print(f"No baseline. state missing: {cfg['state_path']}")
        print("Run: python -m trade_history baseline --offline   # or with Flex download")
        return 2
    trades = store_mod.load_trades(cfg["store_dir"])
    corp = store_mod.load_corporate(cfg["store_dir"])
    print(f"state: {cfg['state_path']}")
    print(f"  account_open_date: {state.account_open_date}")
    print(f"  baseline_completed_at: {state.baseline_completed_at}")
    print(f"  watermark_date: {state.watermark_date}")
    print(f"  last_mode: {state.last_mode}")
    print(f"  trades_in_store: {len(trades)}")
    print(f"  corporate_in_store: {len(corp)}")
    print(f"  report: {cfg['history_report_path']}")
    return 0
