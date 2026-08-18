"""CLI: generate P1 reports from AccountStatement CSVs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ibkr_download_reports.export import build_all_reports, write_workbook

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AS = ROOT / "AccountStatement"
DEFAULT_OUT = Path(r"C:\Investment\reports\IBKR_AccountStatement_P1.xlsx")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="IBKR-Download P1 reports from AccountStatement (incl. Withholding Tax)."
    )
    ap.add_argument(
        "--account-statement-dir",
        type=Path,
        default=DEFAULT_AS,
        help="Folder of AccountStatement CSV files",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output Excel path",
    )
    args = ap.parse_args(argv)

    try:
        sheets = build_all_reports(args.account_statement_dir)
        path = write_workbook(sheets, args.out)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    print(f"Wrote {path}")
    for name, df in sheets.items():
        n = 0 if df is None else len(df)
        print(f"  {name}: {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
