"""CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from completely_sold_alert.config import load_settings
from completely_sold_alert.graph import build_graph
from completely_sold_alert.logging_util import setup_logging
from completely_sold_alert.services.freshness import read_last_export


def _cmd_run(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    settings = load_settings(args.config)
    graph = build_graph(settings)

    initial = {
        "dry_run": args.dry_run,
        "force_market_day": args.force_market_day,
        "fixture_path": str(args.fixture.resolve()) if args.fixture else None,
        "errors": [],
        "log_messages": [],
    }

    result = graph.invoke(initial)

    if args.print_digest and result.get("digest_text"):
        print("\n--- Digest preview ---\n")
        print(result["digest_text"])

    errors = result.get("errors") or []
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    if result.get("skip_reason"):
        print(f"Skipped: {result['skip_reason']}")
        return 0

    if result.get("digest_sent") or result.get("digest_text"):
        n = len(result.get("alert_candidates") or [])
        print(f"Done. Alert candidates: {n}. Sent: {result.get('digest_sent', False)}")
        return 0

    print("Done. No alerts triggered.")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    meta = read_last_export(settings.data_dir)
    print(json.dumps(meta, indent=2) if meta else "No last_export.json")
    cooldown = settings.data_dir / "alert_cooldown.json"
    if cooldown.is_file():
        print(f"\nCooldown file: {cooldown}")
        print(cooldown.read_text(encoding="utf-8")[:2000])
    return 0


def _cmd_refresh_only(args: argparse.Namespace) -> int:
    from completely_sold_alert.adapters.flex_report import run_flex_refresh

    settings = load_settings(args.config)
    ok, msg = run_flex_refresh(settings)
    print(msg)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Completely Sold price-drop alert (LangGraph)"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to settings.yaml",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute alert workflow")
    run_p.add_argument("--dry-run", action="store_true", help="No WhatsApp send")
    run_p.add_argument(
        "--force-market-day",
        action="store_true",
        help="Run even on non-market days (testing)",
    )
    run_p.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="JSON fixture instead of Excel report",
    )
    run_p.add_argument(
        "--print-digest",
        action="store_true",
        help="Print digest text to stdout",
    )
    run_p.set_defaults(func=_cmd_run)

    status_p = sub.add_parser("status", help="Show last export and cooldown")
    status_p.set_defaults(func=_cmd_status)

    ref_p = sub.add_parser("refresh-only", help="Run flex_buysell_report only")
    ref_p.set_defaults(func=_cmd_refresh_only)

    known_commands = {"run", "status", "refresh-only"}
    argv_list = list(argv) if argv is not None else sys.argv[1:]
    # Default to "run" when no subcommand is present. Only skip known global flags
    # (--verbose, --config) so run-specific flags like --dry-run stay after "run".
    if not any(tok in known_commands for tok in argv_list):
        insert_at = 0
        while insert_at < len(argv_list):
            tok = argv_list[insert_at]
            if tok in ("-v", "--verbose"):
                insert_at += 1
            elif tok == "--config" and insert_at + 1 < len(argv_list):
                insert_at += 2
            else:
                break
        argv_list = argv_list[:insert_at] + ["run"] + argv_list[insert_at:]

    args = parser.parse_args(argv_list)
    setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
