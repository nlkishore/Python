"""Excel export for P1 IBKR-Download reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ibkr_download_reports.parser import discover_statement_files, load_section_from_files
from ibkr_download_reports import reports as R


def build_all_reports(account_statement_dir: Path) -> dict[str, pd.DataFrame]:
    files = discover_statement_files(account_statement_dir)
    if not files:
        raise FileNotFoundError(f"No CSV files in {account_statement_dir}")

    dep_raw = load_section_from_files(files, "Deposits & Withdrawals")
    trades_raw = load_section_from_files(files, "Trades")
    corp_raw = load_section_from_files(files, "Corporate Actions")
    div_raw = load_section_from_files(files, "Dividends")
    wt_raw = load_section_from_files(files, "Withholding Tax")
    int_raw = load_section_from_files(files, "Interest")

    dep_ledger, dep_summary = R.report_deposits_withdrawals(dep_raw)
    trades, by_symbol, commission = R.report_trades_and_by_symbol(trades_raw)
    corporate = R.report_corporate_actions(corp_raw)
    dividends = R.report_dividends(div_raw)
    withholding = R.report_withholding_tax(wt_raw)
    interest, interest_summary = R.report_interest(int_raw)
    wt_by_sym = R.withholding_by_symbol(withholding)
    div_net = R.dividends_net_of_tax(dividends, withholding)

    meta = pd.DataFrame(
        [
            {"Field": "Generated at", "Value": datetime.now().isoformat(timespec="seconds")},
            {"Field": "Source folder", "Value": str(account_statement_dir)},
            {"Field": "Files", "Value": ", ".join(p.name for p in files)},
            {"Field": "File count", "Value": str(len(files))},
            {"Field": "Deposit/Withdrawal rows", "Value": str(len(dep_ledger))},
            {"Field": "Trade rows", "Value": str(len(trades))},
            {"Field": "Corporate Action rows", "Value": str(len(corporate))},
            {"Field": "Dividend rows", "Value": str(len(dividends))},
            {"Field": "Withholding Tax rows", "Value": str(len(withholding))},
            {"Field": "Interest rows", "Value": str(len(interest))},
            {
                "Field": "Reports",
                "Value": "R01 deposits, R10/R11 trades+commission, R20 corporate, R21 dividends, R22 withholding tax, R30 interest",
            },
        ]
    )

    return {
        "Report_Info": meta,
        "Deposits_Withdrawals": dep_ledger,
        "Funding_Summary": dep_summary,
        "Trades_All": trades,
        "By_Symbol_Trades": by_symbol,
        "Commission_By_Symbol": commission,
        "Corporate_Actions": corporate,
        "Dividends": dividends,
        "Withholding_Tax": withholding,
        "Withholding_By_Symbol": wt_by_sym,
        "Dividends_Net_Of_Tax": div_net,
        "Interest": interest,
        "Interest_Summary": interest_summary,
    }


def write_workbook(sheets: dict[str, pd.DataFrame], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            out = df if df is not None else pd.DataFrame()
            sheet = name[:31]
            if out.empty:
                pd.DataFrame([{"Note": "No rows for this section in source files"}]).to_excel(
                    writer, sheet_name=sheet, index=False
                )
            else:
                out.to_excel(writer, sheet_name=sheet, index=False)
    return output
