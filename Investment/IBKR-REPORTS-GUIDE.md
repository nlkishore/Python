# IBKR reports — where they live & how to refresh

**All Excel outputs live in one place:** `C:\Investment\reports\`

| File | What it is | Source data |
|------|------------|-------------|
| `IBKR_BuySell_Since_2020.xlsx` | Buys/sells + Completely_Sold / Still_Holding | Flex cache + Activity CSV |
| `IBKR_Symbol_PnL_From_BuySell.xlsx` | **Canonical dedicated** per-symbol PROFIT / LOSS (run `IBKR-SymbolPnL\symbol_pnl_from_buysell.py`) | Buys+Sells from BuySell workbook |
| `IBKR_TradeHistory.xlsx` | Full trade history; includes Symbol_PnL sheet from durable store | Flex + Activity + store |
| `IBKR_AccountStatement_P1.xlsx` | Deposits, trades, dividends, **withholding tax**, interest | Account Statement CSVs |
| `IBKR_Batch_PnL.xlsx` | Avg buy/sell + FIFO batch P&L (lot-matched) | Buys+Sells; run `IBKR-BatchPnL\batch_pnl_report.py` |
| `IBKR_Symbol_Detail.xlsx` | Per-symbol buys/sells/corp, last price, realized/unrealized P&L | `IBKR-SymbolDetail\symbol_detail_report.py` |
| `Completely_Sold_Support_Resistance.xlsx` | Optional S/R levels for closed symbols | Buy/Sell Completely_Sold sheet |

Do **not** keep copies under `IBKR-Flex-BuySell\reports\`, `IBKR-Download\reports\`, or `CompletelySoldAlert\data\` (those folders only hold `_archive` or pointers).

---

## Quick regenerate (after you drop new CSVs)

```cmd
C:\Investment\regenerate-ibkr-reports.bat
```

Or offline (no Flex API):

```cmd
C:\Investment\regenerate-ibkr-reports.bat --offline
```

---

## Step 1 — Download from IBKR Client Portal

### A) Activity Statement (recommended for YTD / latest trades)

1. Log in → **Performance & Reports** → **Activity** (or **Statements**).
2. Choose **Activity Statement**, period **Year to Date** (or custom through today).
3. Format: **CSV**.
4. Save as:
   ```
   C:\Investment\IBKR-Transaction\Latest\U3831357_YYYYMMDD_YYYYMMDD.csv
   ```
   Example: `U3831357_20260101_20260805.csv`
5. **Also copy** the same file into:
   ```
   C:\Investment\IBKR-Download\AccountStatement\
   ```
6. If you already have an older YTD for the same year (e.g. `…_20260728.csv`), move it to `AccountStatement\_archive\` so it does not confuse you (the generator also dedupes overlaps).

### B) Optional: Transaction History (long history)

1. **Reports** → **Transaction History** (or Activity → Transaction History).
2. Export full range (account open → today) as CSV.
3. Save under `IBKR-Transaction\Latest\` as:
   ```
   U3831357.TRANSACTIONS.<from>.<to>.csv
   ```

### C) Optional: Flex Query API (auto download)

Configured in `IBKR-Flex-BuySell\config.ini` (`token`, `query_id`).

```cmd
cd C:\Investment\IBKR-Flex-BuySell
python flex_buysell_report.py --download --fill-missing-from-activity
```

Flex windows cache under `IBKR-Flex-BuySell\downloads\`. Activity CSV fills gaps Flex cannot return.

---

## Step 2 — Regenerate reports

### One-shot (preferred)

```cmd
C:\Investment\regenerate-ibkr-reports.bat
```

### Manual (same order)

```cmd
REM 1) Account Statement P1 (withholding, dividends, …)
cd C:\Investment\IBKR-Download
python -m ibkr_download_reports

REM 2) Buy/Sell Excel (Completely_Sold)
cd C:\Investment\IBKR-Flex-BuySell
python flex_buysell_report.py --from-downloads --fill-missing-from-activity --discover

REM 3) Trade history + Symbol_PnL (rebuild store if you saw duplicates)
python -m trade_history baseline --force-rebaseline --offline --no-market-prices
REM later incremental:
python -m trade_history refresh --offline --no-market-prices

REM 4) Optional support/resistance
python completely_sold_support_report.py
```

Outputs always land in `C:\Investment\reports\`.

---

## Folder roles (inputs vs outputs)

| Path | Role |
|------|------|
| `IBKR-Transaction\Latest\` | **Input:** newest Activity Statement / TRANSACTIONS CSV |
| `IBKR-Download\AccountStatement\` | **Input:** yearly + YTD Account Statement CSVs |
| `IBKR-Flex-BuySell\downloads\` | **Cache:** Flex API window CSVs |
| `IBKR-Flex-BuySell\data\store\` | **Store:** durable trades/corporate for trade_history |
| `C:\Investment\reports\` | **Output:** all Excel workbooks (canonical) |

---

## Which report should I open?

| Need | Open |
|------|------|
| Completely sold P&L / still holding | `IBKR_BuySell_Since_2020.xlsx` |
| Per-symbol buys/sells/corp + last price + P&L | `IBKR_Symbol_Detail.xlsx` |
| Symbol P&L, dividends, tax rows over time | `IBKR_TradeHistory.xlsx` |
| Withholding tax total / by symbol | `IBKR_AccountStatement_P1.xlsx` → sheets `Withholding_*` |
| WhatsApp Completely Sold alert | Uses `reports\IBKR_BuySell_Since_2020.xlsx` automatically |

---

## Deduplication notes

- Same trade from Flex (USD) and Activity (base currency) → **one row** (match on date / symbol / side / qty / price).
- Overlapping Account Statement YTD files → **one row** (keeps newest file).
- After fixing duplicates once, use `baseline --force-rebaseline` if the store still looks wrong; then use `refresh` monthly.

## `ibkr_to_excel.py --discover` (Transaction summary Excel)

```cmd
cd C:\Investment\IBKR-Transaction
python ibkr_to_excel.py --discover --dir "C:\Investment\IBKR-Transaction" --output "C:\Investment\reports\IBKR_Summary.xlsx"
```

**What it does now:** merges **all** Activity Statement CSVs under `Latest\`  
(`U3831357_2020_2020.csv` … `U3831357_20260101_20260807.csv`), not only `*.TRANSACTIONS*` / `*.BUY_SELL*`.

Older behaviour ignored `Latest\U*_*.csv` and fell back to Dec-2025 `BUY_SELL` only.

Uses **Buys** + **Sells** sheets in `reports\IBKR_BuySell_Since_2020.xlsx`:

```cmd
cd C:\Investment\IBKR-SymbolPnL
python symbol_pnl_from_buysell.py --no-market-prices
```

Output: `C:\Investment\reports\IBKR_Symbol_PnL_From_BuySell.xlsx`  
Sheets: **Losses**, **Profits**, **Symbol_PnL** (`Result_Simple` = PROFIT / LOSS / OPEN).

See `IBKR-SymbolPnL\README.md`.
