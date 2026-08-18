"""Parse IBKR multi-section Account Statement / Realized Summary CSVs."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

SYMBOL_IN_DESC = re.compile(
    r"^([A-Z][A-Z0-9.\-]{0,11})\s*\([A-Z0-9]+\)",
    re.IGNORECASE,
)


def extract_symbol_from_description(description: str) -> str | None:
    if not description:
        return None
    m = SYMBOL_IN_DESC.match(str(description).strip())
    if m:
        return m.group(1).upper()
    # Fallback: first token before space if looks like ticker
    tok = str(description).strip().split()[0] if str(description).strip() else ""
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9.\-]{0,11}", tok):
        return tok.upper()
    return None


def load_section_rows(path: Path, section: str) -> pd.DataFrame:
    """Load Data rows for a named section into a DataFrame."""
    header: list[str] | None = None
    records: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            if row[0] == section and row[1] == "Header":
                header = [h.strip() for h in row[2:]]
                continue
            if header is None:
                continue
            if row[0] == section and row[1] == "Data":
                vals = row[2 : 2 + len(header)]
                if len(vals) < len(header):
                    vals = vals + [""] * (len(header) - len(vals))
                records.append(dict(zip(header, vals)))
    if not records:
        return pd.DataFrame()
    return pd.DataFrame.from_records(records)


def list_sections(path: Path) -> list[str]:
    seen: list[str] = []
    found: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1] == "Header":
                sec = row[0].strip()
                if sec and sec not in found:
                    found.add(sec)
                    seen.append(sec)
    return seen


def discover_statement_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.csv"), key=lambda p: p.name)


def load_section_from_files(files: list[Path], section: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in files:
        df = load_section_rows(path, section)
        if df.empty:
            continue
        df = df.copy()
        df["_SourceFile"] = path.name
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).replace("", pd.NA).replace("-", pd.NA),
        errors="coerce",
    )


def parse_date_series(series: pd.Series) -> pd.Series:
    # IBKR often uses YYYY-MM-DD or "YYYY-MM-DD, HH:MM:SS"
    cleaned = series.astype(str).str.split(",").str[0].str.strip()
    return pd.to_datetime(cleaned, errors="coerce")
