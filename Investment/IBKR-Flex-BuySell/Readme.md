# IBKR Flex Buy/Sell Report

**Canonical Excel outputs:** `C:\Investment\reports\`  
**Download + regenerate guide:** [`..\IBKR-REPORTS-GUIDE.md`](../IBKR-REPORTS-GUIDE.md)  
**One-shot refresh:** `C:\Investment\regenerate-ibkr-reports.bat`

Python tool under `C:\Investment\IBKR-Flex-BuySell` that downloads **IBKR Flex Query** trade history (or reads local Activity CSV exports), merges sources, and builds Excel workbooks with stock **Buy/Sell** trades since 2020 — including a **Completely_Sold** analysis sheet for fully closed positions.

---

## Features developed

| Feature | Description |
|---------|-------------|
| **Flex Web Service download** | Calls IBKR `SendRequest` + `GetStatement` (v3) with token and query ID from `config.ini` |
| **Yearly chunked downloads** | IBKR limits each request to **366 days**; script auto-splits 2020 → today into windows |
| **Cached downloads** | Saves each window as `downloads/flex_{queryId}_{from}_{to}.csv`; re-runs skip cached files |
| **Retry / skip on failure** | Retries failed windows with backoff; continues and merges successful windows |
| **Activity CSV merge** | Combines Flex cache + `IBKR-Transaction\Latest\*.TRANSACTIONS*.csv` to fill gaps (e.g. missing 2023 / 2026 Flex windows) |
| **Dual CSV formats** | Parses IBKR **Flex Trades CSV** (`Buy/Sell`, `TradeDate`) and **Activity CSV** (`Transaction History`) |
| **Incremental dedupe** | Merges duplicate trades across sources by date, symbol, side, quantity, price |
| **Buy/Sell Excel sheets** | `All_Buy_Sell`, separate `Buys` and `Sells` tabs |
| **Still_Holding sheet** | Net qty ≠ 0; flags symbols missing sell rows (e.g. QBTS, IONQ until export refreshed) |
| **Summary_By_Year** | Trade counts and amounts grouped by year and Buy/Sell |
| **Report_Info** | Metadata: source files, row counts, date range |

---

## Excel output

**Default file:** `C:\Investment\reports\IBKR_BuySell_Since_2020.xlsx`  
(Override with `--output` or `report_path` in `config.ini`.)

| Sheet | Content |
|-------|---------|
| `Report_Info` | Source description, start-year filter, trade counts, date range |
| `All_Buy_Sell` | Every buy and sell row since filter year (default 2020) |
| `Buys` | Buy transactions only |
| `Sells` | Sell transactions only |
| `Completely_Sold` | Fully closed positions (see columns below) |
| `Still_Holding` | Net qty ≠ 0 — open or **missing sell rows** in export |
| `Summary_By_Year` | Counts and net amounts by calendar year and side |

### Completely_Sold columns

| Column | Meaning |
|--------|---------|
| `Symbol` | Ticker |
| `Buy_Qty_Total` / `Sell_Qty_Total` | Total shares bought vs sold (must match for closed position) |
| `Buy_Trades` / `Sell_Trades` | Number of buy/sell line items |
| `Total_Buy_Cost` | Total cash paid including commissions |
| `Total_Sell_Proceeds` | Total cash received from sells |
| `Profit` | Sell proceeds − buy cost |
| `Profit_Pct` | Profit as % of buy cost |
| `Last_Sold_Date` | Date of final sell |
| `Last_Sold_Price` | Execution price of the final sell |
| `Current_Market_Price` | Latest close from Yahoo Finance (`yfinance`) |
| `Price_As_Of` | Date of the market price quote |
| `Change_Since_Last_Sold_Pct` | `(Current − Last_Sold) / Last_Sold × 100` |
| `First_Buy_Date` | Date of first purchase |

A symbol appears here only when **net shares = 0** and there is at least one buy and one sell in the merged data.

---

## Support / Resistance report (completely sold stocks)

Uses the same **swing pivot heuristics** as `C:\Investment\AutomatedTrading\ChartSupportAndSignals.py` (Yahoo Finance daily OHLC). For each symbol on the **Completely_Sold** sheet, the tool fetches nearest support below and resistance above the current price, plus ATR, candle pattern, and heuristic signal.

**Default output:** `C:\Investment\reports\Completely_Sold_Support_Resistance.xlsx`

| Sheet | Content |
|-------|---------|
| `Report_Info` | Generation time, source buy/sell report, symbol count |
| `Support_Resistance` | Trade P&amp;L columns + S/R levels for every completely sold symbol |
| `With_Levels` | Rows where Yahoo Finance returned valid levels |
| `Errors` | Delisted or unavailable symbols (e.g. SIVB) |

### Merged columns (Support_Resistance sheet)

Trade context from **Completely_Sold**: `Profit`, `Last_Sold_Price`, `Change_Since_Last_Sold_Pct`, etc.

| Column | Meaning |
|--------|---------|
| `Current_Price` | Latest daily close (Yahoo Finance) |
| `Nearest_Support` | Nearest pivot low below current price |
| `Distance_To_Support_Pct` | `(Price / Support − 1) × 100` |
| `Nearest_Resistance` | Nearest pivot high above current price |
| `Distance_To_Resistance_Pct` | `(1 − Price / Resistance) × 100` |
| `ATR14` | 14-period average true range |
| `Candle_Pattern` / `Signal` / `Signal_Reason` | Heuristic chart labels (illustrative only) |

Pivot settings (`chart_pivot_left`, `chart_pivot_right`, `chart_atr_proximity_mult`) are read from `AutomatedTrading\config.ini` unless you pass `--chart-config`.

### Generate the S/R report

**After the buy/sell report exists** (or directly from Flex cache):

```powershell
cd C:\Investment\IBKR-Flex-BuySell
python completely_sold_support_report.py
```

From Flex cache (no Excel required):

```powershell
python completely_sold_support_report.py --from-downloads
```

From a specific buy/sell workbook:

```powershell
python completely_sold_support_report.py --input reports\IBKR_BuySell_Since_2020.xlsx
```

Custom output:

```powershell
python completely_sold_support_report.py --output reports\Closed_Stocks_SR.xlsx
```

**Typical two-step workflow:**

```cmd
cd C:\Investment\IBKR-Flex-BuySell
python flex_buysell_report.py --sync-ytd
python completely_sold_support_report.py
```

*Not trading advice. For live IBKR intraday S/R, see `AutomatedTrading\ChartSupportAndSignals_IBKR.py` (requires Client Portal Gateway).*

---

## Trade history baseline + incremental (`trade_history`)

Downloads **buys/sells** (Flex + Activity) and **dividends / corporate actions** (Activity DIVIDEND / TRANSACTIONS), stores a durable baseline, then refreshes incrementally. Builds analysis Excel with **Symbol_PnL** and **By_Symbol_Trades**.

```cmd
cd C:\Investment\IBKR-Flex-BuySell
.venv\Scripts\activate.bat

REM First run — full history from account_open_date (uses Flex API unless --offline)
python -m trade_history baseline
python -m trade_history baseline --offline

REM Later — merge new windows from watermark (7-day overlap by default)
python -m trade_history refresh
python -m trade_history refresh --offline

python -m trade_history status
python -m trade_history export --no-market-prices
```

| Output | Path |
|--------|------|
| State / watermark | `data/state.json` |
| Trade + corporate store | `data/store/trades.csv`, `corporate_actions.csv` |
| Analysis workbook | `reports/IBKR_TradeHistory.xlsx` |

Sheets: `Trades_All`, `Buys`, `Sells`, `Corporate_Actions`, `By_Symbol_Trades`, **`Symbol_PnL`**, `Completely_Sold`, `Still_Holding`, `Report_Info`.

Config: `[history]` in `config.ini` (see `config.ini.example`).

---

## Project layout

```
IBKR-Flex-BuySell/
  trade_history/           # baseline | refresh | status | export
  flex_buysell_report.py   # Main CLI
  completely_sold_support_report.py  # S/R levels for Completely_Sold symbols
  flex_client.py           # IBKR Flex Web Service (download)
  flex_parse.py            # CSV/XML parsing, merge, Completely_Sold logic
  flex_ytd.py              # Year-to-date sync + compare
  flex_skip_cache.py       # Skip cache for unavailable Flex windows
  config.ini               # Your token, query ID, paths (not in git)
  config.ini.example       # Template
  requirements.txt
  run-report.bat           # Windows shortcut
  downloads/               # Cached Flex window CSVs
  data/store/              # Baseline trade + corporate CSVs
  reports/                 # Generated Excel workbooks
```

**Dependency:** `..\IBKR-Transaction\ibkr_to_excel.py` (Activity CSV loader).

---

## One-time IBKR setup

1. **Client Portal** → **Performance & Reports** → **Flex Queries**
2. Create a **Trades** (or Activity) Flex Query with stock **Buy** and **Sell**.
3. Prefer **CSV** output format.
4. Note the **Query ID**.
5. **Flex Web Service** → generate a **token** (expires periodically; renew in portal).
6. Copy `config.ini.example` → `config.ini` and set:
   - `[flex] token`
   - `[flex] query_id`

**Optional but recommended:** Export full **Transaction History** from IBKR portal and save under:

`C:\Investment\IBKR-Transaction\Latest\U3831357.TRANSACTIONS.*.csv`

This file is merged automatically to improve completeness when Flex windows fail.

---

## Install

```powershell
cd C:\Investment\IBKR-Flex-BuySell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Requirements:** Python 3.11+, `httpx`, `pandas`, `openpyxl`, `pyyaml`, `yfinance` (live prices on `Completely_Sold`).

---

## How to regenerate the report

### Fill missing raw windows (2023, 2026) when Flex API fails

IBKR often returns *Statement is not available* for some yearly windows. The tool can build **Flex-format raw CSVs** from your Activity export:

```powershell
python flex_buysell_report.py --fill-missing-from-activity
```

This writes missing files under `downloads/`, e.g.:

- `flex_{queryId}_20221231_20231230.csv` (2023)
- `flex_{queryId}_20251230_20260530.csv` (2026 YTD)

Then merges all raw files + Activity CSV and writes the Excel report.

**Note:** Activity CSV must be current. Prefer a fresh **Activity Statement** (`U*_YYYYMMDD_YYYYMMDD.csv`) or **TRANSACTIONS** export under `IBKR-Transaction\Latest\`. Report_Info end date is parsed from the newest filename (e.g. `U3831357_20260101_20260805.csv` → **2026-08-05**).

---

### Recommended: rebuild from cache + Activity CSV (no API call)

Use this after a prior `--download`, or whenever you drop a fresh TRANSACTIONS export into `IBKR-Transaction\Latest\`.

```powershell
cd C:\Investment\IBKR-Flex-BuySell
.\.venv\Scripts\Activate.ps1
python flex_buysell_report.py --from-downloads
```

**CMD:**

```cmd
cd C:\Investment\IBKR-Flex-BuySell
run-report.bat --from-downloads
```

**Custom output path:**

```powershell
python flex_buysell_report.py --from-downloads --output reports\IBKR_BuySell_Since_2020_updated.xlsx
```

---

### Full refresh: clean download (recommended after config changes)

Removes all raw Flex CSVs and Excel reports, seeds known-unavailable windows (2023, current-year YTD Flex API), downloads history, fills gaps from Activity CSV, syncs **Year-to-Date** for the latest year, and writes Excel.

```powershell
python flex_buysell_report.py --clean-all --download
```

**Skip cache:** `downloads/flex_unavailable_windows.json` records Flex windows that return *Statement is not available* so future runs **do not retry** the API (2023 is pre-seeded). Activity CSV fill + YTD import still run for those periods.

```powershell
python flex_buysell_report.py --list-skipped
python flex_buysell_report.py --clear-skip-cache
python flex_buysell_report.py --force-download
```

| Flag | Action |
|------|--------|
| `--clean-all` | Delete `flex_*.csv` + `reports/*.xlsx` (keeps skip cache + manual baselines) |
| `--list-skipped` | Show windows in skip cache |
| `--clear-skip-cache` | Remove skip cache (Flex API retries all windows again) |
| `--force-download` | Ignore skip cache for this run |

---

### Full refresh: download from IBKR Flex + merge Activity CSV

Pulls missing Flex windows (skips cached), merges with Activity CSV, writes Excel.

```powershell
python flex_buysell_report.py --download
```

**CMD:**

```cmd
run-report.bat --download
```

Expect **several minutes** (IBKR pacing between windows). Some windows may fail with *Statement is not available* — re-run later or rely on Activity CSV merge.

---

### From a single Activity / BUY_SELL CSV only

```powershell
python flex_buysell_report.py --input "..\IBKR-Transaction\Latest\U3831357.TRANSACTIONS.20200218.20260320.csv"
```

Or auto-pick newest file under `IBKR-Transaction`:

```powershell
python flex_buysell_report.py --discover
```

---

## CLI reference

| Command | Action |
|---------|--------|
| `--fill-missing-from-activity` | Write missing `downloads/flex_*.csv` from Activity export + generate Excel |
| `--from-downloads` | Merge all raw cache + Activity CSV → Excel (auto-fills missing windows first) |
| `--download` | Fetch Flex data (yearly chunks) + merge Activity CSV → Excel |
| `--input PATH` | Build Excel from one CSV file |
| `--discover` | Use newest `*.TRANSACTIONS*` or `*.BUY_SELL*` under `IBKR-Transaction` |
| `--no-market-prices` | Skip Yahoo Finance lookup on `Completely_Sold` (offline run) |
| `--output PATH` | Override output `.xlsx` |
| `--start-year 2020` | Override filter year (default from `config.ini`) |
| `--config PATH` | Alternate config file |
| `--sync-ytd` | Sync current-year YTD into Flex cache from API or Latest Activity export |
| `--compare-baseline PATH` | Compare auto YTD vs manual baseline CSV |

**Support / resistance (completely sold):**

| Command | Action |
|---------|--------|
| `python completely_sold_support_report.py` | S/R levels for symbols on `Completely_Sold` sheet |
| `--from-downloads` | Derive completely sold list from Flex cache |
| `--input PATH` | Use a specific buy/sell `.xlsx` |
| `--chart-config PATH` | Pivot settings (default: `AutomatedTrading\config.ini`) |
| `--output PATH` | Override S/R report path |

**Status / counts only:**

```powershell
python flex_buysell_report.py --from-downloads
# Prints: rows, buys, sells, completely sold symbol count
```

---

## Configuration (`config.ini`)

| Section | Key | Purpose |
|---------|-----|---------|
| `[flex]` | `token` | Flex Web Service token (required for `--download`) |
| `[flex]` | `query_id` | Flex Query ID for trades |
| `[flex]` | `from_date` | Start date for Flex requests (`yyyymmdd`, default `20200101`) |
| `[flex]` | `to_date` | End date (optional; default = today) |
| `[flex]` | `start_year` | Filter trades in Excel (default `2020`) |
| `[flex]` | `poll_seconds` | Wait between GetStatement polls |
| `[flex]` | `max_poll_attempts` | Max polls per window |
| `[output]` | `report_path` | Default Excel output path |
| `[output]` | `download_dir` | Cached Flex CSV folder (`downloads`) |

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **Missing from Completely_Sold** (e.g. QBTS, IONQ sold in 2026) | Your Activity export ends **2026-03-20** and has **buys only** for those symbols — **no sell rows**. Export a new TRANSACTIONS CSV through **today** from IBKR portal → save under `IBKR-Transaction\Latest\` → re-run `--fill-missing-from-activity`. Check `Still_Holding` sheet. |
| **Flex window failed** (*Statement is not available*) | Wait 30+ minutes; re-run `--download` (cached windows are skipped) |
| **Token expired** | Regenerate token in Client Portal → update `config.ini` |
| **Permission denied writing Excel** | Close the `.xlsx` in Excel; use `--output` to a new filename |
| **Date range invalid (366 days)** | Normal — script chunks automatically; ensure you use current version of `flex_buysell_report.py` |
| **Empty Completely_Sold** | Trades may still be open (net qty ≠ 0) or data incomplete |

---

## Typical workflow (future reference)

1. **Monthly or after trades:** Export TRANSACTIONS CSV from IBKR → save to `IBKR-Transaction\Latest\`.
2. **Regenerate report:**
   ```cmd
   cd C:\Investment\IBKR-Flex-BuySell
   run-report.bat --from-downloads
   ```
3. **Open:** `reports\IBKR_BuySell_Since_2020.xlsx` → review `Completely_Sold`, `Buys`, `Sells`.
4. **Support / resistance for closed positions:**
   ```cmd
   python completely_sold_support_report.py
   ```
   → `reports\Completely_Sold_Support_Resistance.xlsx`
5. **Optional quarterly Flex refresh:**
   ```cmd
   run-report.bat --download
   ```

---

## Related tools

| Path | Purpose |
|------|---------|
| `C:\Investment\AutomatedTrading\ChartSupportAndSignals.py` | Daily pivot S/R + heuristic signals (Yahoo Finance) — used by `completely_sold_support_report.py` |
| `C:\Investment\AutomatedTrading\ChartSupportAndSignals_IBKR.py` | Intraday S/R via IBKR Client Portal Gateway |
| `C:\Investment\IBKR-Transaction\ibkr_to_excel.py` | Full transaction workbook (dividends, deposits, positions) |
| `C:\Investment\IBKR-Client-GateWay` | Live REST API gateway (not used by Flex; Flex uses portal token) |
| `C:\Investment\INVESTMENT-PROGRAMS-REFERENCE.md` | Overview of all Investment folder programs |

---

*Not financial advice. Verify totals against IBKR official statements.*
