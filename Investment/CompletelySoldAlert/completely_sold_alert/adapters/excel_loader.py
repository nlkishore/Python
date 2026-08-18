"""Load Completely_Sold sheet from Excel or JSON fixture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_completely_sold(report_path: Path) -> list[dict[str, Any]]:
    path = report_path.resolve()
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [_normalize_row(r) for r in raw]
        raise ValueError("JSON fixture must be a list of row objects")

    df = pd.read_excel(path, sheet_name="Completely_Sold", engine="openpyxl")
    rows: list[dict[str, Any]] = []
    for _, series in df.iterrows():
        row = {k: _clean_value(v) for k, v in series.items()}
        rows.append(_normalize_row(row))
    return rows


def _clean_value(v: Any) -> Any:
    if pd.isna(v):
        return None
    if hasattr(v, "isoformat"):
        return str(v)[:10]
    return v


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    if "Symbol" in row and row["Symbol"]:
        row["Symbol"] = str(row["Symbol"]).strip().upper()
    return row
