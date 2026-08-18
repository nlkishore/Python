# IBKR-Download — Account Statement & Realized Summary reports

**Canonical Excel output:** `C:\Investment\reports\IBKR_AccountStatement_P1.xlsx`  
**How to download + regenerate:** [`..\IBKR-REPORTS-GUIDE.md`](../IBKR-REPORTS-GUIDE.md)

## Data

| Folder | Content |
|--------|---------|
| `AccountStatement\` | Yearly / period IBKR Account Statement CSVs |
| `AccountStatement\_archive\` | Superseded YTD files (keep out of active set) |
| `RealizedSummary\` | Rolling-window Realized Summary CSVs |

Catalog of all possible reports:  
`repo-consolidated/docs/IBKR_DOWNLOAD_REPORT_CATALOG.md`

## P1 generator (implemented)

Builds an Excel workbook from **all** `AccountStatement\*.csv` files (dedupes overlapping YTD):

| Sheet | Report |
|-------|--------|
| Deposits_Withdrawals / Funding_Summary | R01 deposits & withdrawals |
| Trades_All / By_Symbol_Trades | R10 symbol buy/sell |
| Commission_By_Symbol | R11 commission by symbol |
| Corporate_Actions | R20 |
| Dividends | R21 |
| **Withholding_Tax** / Withholding_By_Symbol | **R22** |
| Dividends_Net_Of_Tax | Dividends − withholding by symbol |
| Interest / Interest_Summary | R30 interest paid to IBKR (+ earned) |

### Run

```cmd
cd C:\Investment\IBKR-Download
python -m ibkr_download_reports
```

Or from Investment root: `regenerate-ibkr-reports.bat`

Default output: `C:\Investment\reports\IBKR_AccountStatement_P1.xlsx`

### Dependencies

```cmd
pip install pandas openpyxl
```
