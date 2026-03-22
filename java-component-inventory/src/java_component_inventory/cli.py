"""CLI entry point."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from java_component_inventory.config_loader import load_ini
from java_component_inventory.excel_report import write_report
from java_component_inventory.scanner import group_by_fqn, iter_java_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan selected Java component folders (INI config) and write Excel inventory.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.ini",
        help="Path to INI file (default: ./config.ini)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Override output .xlsx path (default: report_dir/java-inventory_TIMESTAMP.xlsx)",
    )
    args = parser.parse_args(argv)

    try:
        cfg = load_ini(args.config)
    except Exception as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 2

    try:
        records = iter_java_files(cfg)
    except Exception as e:
        print(f"Scan error: {e}", file=sys.stderr)
        return 3

    collisions = group_by_fqn(records) if cfg.detect_collisions else {}

    if args.output.strip():
        out = Path(args.output).expanduser().resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = cfg.report_dir / f"java-inventory_{ts}.xlsx"

    write_report(records, collisions, out)
    print(f"Wrote {out}")
    print(f"  Java files: {len(records)}")
    if cfg.detect_collisions:
        print(f"  Duplicate FQNs: {len(collisions)}")
    return 0


def run() -> None:
    """Setuptools console_script entrypoint."""
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
