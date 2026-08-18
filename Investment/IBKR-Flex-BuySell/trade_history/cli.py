"""CLI for trade_history baseline / refresh / status / export."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trade_history.orchestrator import (
    DEFAULT_CONFIG,
    HistoryError,
    load_history_config,
    run_baseline,
    run_export,
    run_refresh,
    run_status,
)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    common.add_argument(
        "--offline",
        action="store_true",
        help="Do not call Flex API; use cached Flex CSVs + Activity/Dividend CSVs only.",
    )
    common.add_argument(
        "--no-market-prices",
        action="store_true",
        help="Skip Yahoo mark prices for open positions / Completely_Sold.",
    )

    ap = argparse.ArgumentParser(
        prog="trade_history",
        description=(
            "Baseline + incremental IBKR buy/sell/corporate history with Symbol_PnL analysis."
        ),
        parents=[common],
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_base = sub.add_parser(
        "baseline",
        parents=[common],
        help="Full history since account open (first run).",
    )
    p_base.add_argument(
        "--force-rebaseline",
        action="store_true",
        help="Replace existing baseline store and state.",
    )

    sub.add_parser(
        "refresh",
        parents=[common],
        help="Incremental update from watermark (with overlap).",
    )
    sub.add_parser("status", parents=[common], help="Show baseline watermark and store counts.")
    sub.add_parser(
        "export",
        parents=[common],
        help="Rebuild Excel from store without downloading.",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_history_config(args.config)
    fetch_marks = not args.no_market_prices

    try:
        if args.command == "baseline":
            out = run_baseline(
                cfg,
                force_rebaseline=bool(getattr(args, "force_rebaseline", False)),
                offline=args.offline,
                fetch_market_prices=fetch_marks,
            )
            print(f"Baseline complete -> {out}")
            return 0
        if args.command == "refresh":
            out = run_refresh(
                cfg, offline=args.offline, fetch_market_prices=fetch_marks
            )
            print(f"Refresh complete -> {out}")
            return 0
        if args.command == "export":
            out = run_export(cfg, fetch_market_prices=fetch_marks)
            print(f"Export complete -> {out}")
            return 0
        if args.command == "status":
            return run_status(cfg)
    except HistoryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
