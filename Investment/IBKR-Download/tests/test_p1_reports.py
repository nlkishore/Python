from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ibkr_download_reports.export import build_all_reports, write_workbook
from ibkr_download_reports.parser import extract_symbol_from_description, load_section_rows
from ibkr_download_reports.reports import report_withholding_tax


def test_extract_symbol():
    assert extract_symbol_from_description(
        "AAPL(US0378331005) Cash Dividend USD 0.205 per Share - US Tax"
    ) == "AAPL"


def test_withholding_from_2025_file():
    path = ROOT / "AccountStatement" / "U3831357_2025_2025.csv"
    if not path.is_file():
        return
    raw = load_section_rows(path, "Withholding Tax")
    assert not raw.empty
    wt = report_withholding_tax(raw)
    assert "Tax_Paid" in wt.columns
    assert wt["Tax_Paid"].sum() > 0


def test_build_p1_workbook(tmp_path: Path):
    as_dir = ROOT / "AccountStatement"
    if not as_dir.is_dir() or not list(as_dir.glob("*.csv")):
        return
    sheets = build_all_reports(as_dir)
    assert "Withholding_Tax" in sheets
    assert len(sheets["Withholding_Tax"]) > 0
    assert "Funding_Summary" in sheets
    assert "Commission_By_Symbol" in sheets
    assert "Interest_Summary" in sheets
    out = tmp_path / "p1.xlsx"
    write_workbook(sheets, out)
    assert out.is_file()
