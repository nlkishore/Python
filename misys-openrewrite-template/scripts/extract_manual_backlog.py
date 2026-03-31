#!/usr/bin/env python3
"""
Aggregate OpenRewrite datatable CSV outputs into one manual migration backlog CSV.

Default scan root: current directory (multi-module project root)
Default output: ./manual-migration-backlog.csv

Examples:
  python scripts/extract_manual_backlog.py
  python scripts/extract_manual_backlog.py --root . --out reports/backlog.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def find_datatable_csvs(root: Path) -> List[Path]:
    # Common locations used by rewrite-maven-plugin exports
    patterns = [
        "**/target/rewrite/**/datatable*.csv",
        "**/target/rewrite/**/data-table*.csv",
        "**/target/rewrite/**/tables/*.csv",
        "**/target/rewrite/**/*.csv",
    ]
    found: List[Path] = []
    for pattern in patterns:
        for p in root.glob(pattern):
            if p.is_file() and p.name.lower().endswith(".csv"):
                found.append(p)
    # stable + unique
    uniq = sorted(set(found))
    return uniq


def infer_module_name(project_root: Path, csv_path: Path) -> str:
    """
    Infer module as the path segment before `target`.
    """
    rel = csv_path.relative_to(project_root)
    parts = rel.parts
    if "target" in parts:
        idx = parts.index("target")
        if idx > 0:
            return parts[idx - 1]
    return "."


def normalize_row(
    project_root: Path, csv_path: Path, row: Dict[str, str], source_table: str
) -> Dict[str, str]:
    out = dict(row)
    out["source_table"] = source_table
    out["source_csv"] = str(csv_path.relative_to(project_root)).replace("\\", "/")
    out["module"] = infer_module_name(project_root, csv_path)
    return out


def read_all_rows(project_root: Path, csv_files: List[Path]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for p in csv_files:
        table_name = p.stem
        try:
            with p.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(normalize_row(project_root, p, r, table_name))
        except Exception:
            # keep script resilient; skip malformed files
            continue
    return rows


def write_union_csv(out_file: Path, rows: List[Dict[str, str]]) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    # union of all keys so mixed datatables can coexist in one backlog file
    fieldnames: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    # put core columns first if present
    preferred = ["module", "source_table", "source_csv", "sourcePath", "sourceFile", "fullyQualifiedTypeName"]
    ordered = [c for c in preferred if c in fieldnames] + [c for c in fieldnames if c not in preferred]
    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ordered, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract OpenRewrite datatable outputs into one manual backlog CSV."
    )
    parser.add_argument("--root", default=".", help="Project root to scan")
    parser.add_argument(
        "--out",
        default="manual-migration-backlog.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()

    csvs = find_datatable_csvs(root)
    if not csvs:
        print("No rewrite datatable CSV files found under:", root)
        return 1

    rows = read_all_rows(root, csvs)
    if not rows:
        print("Found CSV files, but no rows could be read.")
        return 2

    write_union_csv(out, rows)
    print(f"Wrote backlog CSV: {out}")
    print(f"Source tables: {len(csvs)} file(s)")
    print(f"Backlog rows : {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

