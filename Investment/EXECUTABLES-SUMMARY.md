# C:\Investment — Executables Summary

**Last updated:** 2026-08-20  
**Purpose:** One place to scan every runnable script/bat — two lines each: what it does, and the switches/commands to run the intended operation.

Related deeper docs: [`INVESTMENT-PROGRAMS-REFERENCE.md`](INVESTMENT-PROGRAMS-REFERENCE.md), [`IBKR-REPORTS-GUIDE.md`](IBKR-REPORTS-GUIDE.md), [`CLEANUP-AND-TIDY-PLAN.md`](CLEANUP-AND-TIDY-PLAN.md).

---

## Root (`C:\Investment\`)

### `stock_whatsapp_monitor.py`
Yahoo Finance % threshold monitor using CallMeBot or Twilio (root `config.ini`); continuous loop or one-shot check.  
**Run:** `python stock_whatsapp_monitor.py` · `python stock_whatsapp_monitor.py --once` · `--config PATH`

### `start_stock_alert.bat`
Starts the **supported** Green API alert app (`AlertApp\backgroundAlert1.py`) in the foreground.  
**Run:** `start_stock_alert.bat` (no switches)

### `stop_stock_alert.bat`
Stops only processes running `backgroundAlert1.py` (`python.exe` / `pythonw.exe`); does not kill other Python jobs.  
**Run:** `stop_stock_alert.bat` (no switches)

### `regenerate-ibkr-reports.bat`
One-shot rebuild of AccountStatement P1 + Buy/Sell + TradeHistory into `reports\`.  
**Run:** `regenerate-ibkr-reports.bat` · `regenerate-ibkr-reports.bat --offline` (no Flex API; Activity/cache only)

---

## AlertApp\

### `backgroundAlert1.py`
Consolidated Green API listener: manual watchlist alerts + Completely_Sold **rebuy** monitor (↓% vs avg sell) + WhatsApp commands (`STATUS`, `WATCHLIST`, `REBUY`, `SUPPORT`, `SOLD`, `RELOAD`).  
**Run:** `python backgroundAlert1.py` (config-driven; no CLI switches) · or `run-green-api-listener.bat`

### `watchdog.py`
Checks the single-instance mutex; if the listener is down, starts it detached and notifies WhatsApp.  
**Run:** `python watchdog.py` (no switches; used by Task Scheduler)

### `run-green-api-listener.bat`
Foreground shortcut to `backgroundAlert1.py`.  
**Run:** `run-green-api-listener.bat`

### `install-scheduled-tasks.bat`
Creates Task Scheduler jobs `AlertApp-Startup` (logon) and `AlertApp-Watchdog` (every 5 min).  
**Run:** `install-scheduled-tasks.bat` (once)

### `uninstall-scheduled-tasks.bat`
Removes those scheduled tasks (does not stop a running listener by itself).  
**Run:** `uninstall-scheduled-tasks.bat`

---

## AutomatedTrading\

### `averagePriceFetcher.py`
Core Yahoo history + 52-EMA library; CLI writes fixed Buy (−5%) / Sell (+7%) targets CSV for configured symbols.  
**Run:** `python averagePriceFetcher.py` (reads `config.ini`; no switches)

### `AdaptiveAItrader.py`
Same 52-EMA baseline with **ATR-adaptive** buy/sell bands (±2×ATR) → `adaptive_ai_targets.csv`.  
**Run:** `python AdaptiveAItrader.py`

### `AdaptiveTraderWithVolume.py`
ATR bands plus 20-day volume filter; outputs `BUY` / `SELL` / `HOLD` / `WAIT` decisions.  
**Run:** `python AdaptiveTraderWithVolume.py` (`volume_filter_enabled` in `config.ini`)

### `ChartSupportAndSignals.py`
Yahoo chart pivots + candle heuristics (`BUY_HEURISTIC` / `SELL_HEURISTIC`); optional Green API WhatsApp + session watch loop.  
**Run:** `python ChartSupportAndSignals.py` · `--once` · `--symbol AAPL` · `--symbols AAPL,MSFT`

### `ChartSupportAndSignals_IBKR.py`
Same chart heuristics using **IBKR Client Portal** (or TWS socket) bars; WhatsApp via `[trading]` when enabled.  
**Run:** `python ChartSupportAndSignals_IBKR.py` (CP Gateway must be logged in; config `[ibkr]`; no CLI switches)

### `ClientPortalMarketSnapshot.py`
Live IBKR CP quote snapshot (bid/ask/last/volume); optional chart S/R and WhatsApp digest.  
**Run:** `python ClientPortalMarketSnapshot.py` · `--send-whatsapp` · `--chart-support` · `--json-out` · `--whatsapp-only` · `--no-snapshot` · `--fields 31,84,86`

### `ChartSupportResistanceWhatsApp_IBKR.py`
IBKR CP candle-based nearest support/resistance digest (no live quotes); WhatsApp only if requested.  
**Run:** `python ChartSupportResistanceWhatsApp_IBKR.py` · `--send-whatsapp` · `--config PATH` · `--symbol AAPL` · `--symbols A,B` · `--text-only` · `--json-out` · `--quiet`

---

## CompletelySoldAlert\

### `run-alert.bat` → `python -m completely_sold_alert`
LangGraph workflow: refresh Completely_Sold prices, evaluate drop vs last sold, send WhatsApp digest on market days.  
**Run:** `run-alert.bat run` · `run --dry-run` · `run --force-market-day` · `run --fixture PATH` · `run --print-digest` · `status` · `refresh-only` · `-v` · `--config settings.yaml`

---

## IBKR-Flex-BuySell\

### `flex_buysell_report.py` (via `run-report.bat`)
Builds `IBKR_BuySell_Since_2020.xlsx` (Buys/Sells/Completely_Sold/Still_Holding) from Flex API and/or Activity CSVs.  
**Run:** `run-report.bat --download` · `--from-downloads --fill-missing-from-activity --discover` · `--sync-ytd` · `--force-download` · `--clear-skip-cache` · `--list-skipped` · `--clean-all` · `--no-market-prices` · `--output PATH` · `--compare-baseline PATH`

### `completely_sold_support_report.py`
Support/resistance Excel for symbols on the Completely_Sold sheet (Yahoo pivots; optional chart config).  
**Run:** `python completely_sold_support_report.py` · `--input BuySell.xlsx` · `--from-downloads` · `--chart-config PATH` · `--output PATH`

### `run-trade-history.bat` → `python -m trade_history`
Durable trade store + Symbol_PnL workbook (`IBKR_TradeHistory.xlsx`); baseline once, then incremental refresh.  
**Run:** `run-trade-history.bat baseline` · `baseline --force-rebaseline` · `refresh` · `status` · `export` · add `--offline` and/or `--no-market-prices` to any subcommand

---

## IBKR-Download\

### `run-p1-reports.bat` → `python -m ibkr_download_reports`
Parses Account Statement CSVs into P1 Excel (deposits, trades, dividends, **withholding tax**, interest).  
**Run:** `run-p1-reports.bat` · `--out PATH` · `--account-statement-dir PATH`

---

## IBKR-SymbolPnL\

### `run-symbol-pnl.bat` → `symbol_pnl_from_buysell.py`
**Canonical** per-symbol Profit/Loss workbook from BuySell Buys+Sells sheets → `reports\IBKR_Symbol_PnL_From_BuySell.xlsx`.  
**Run:** `run-symbol-pnl.bat` · `--input PATH` · `--output PATH` · `--transactions-dir PATH` · `--no-market-prices`

---

## IBKR-BatchPnL\

### `run-batch-pnl.bat` → `batch_pnl_report.py`
Refreshes Buy/Sell from IBKR Flex through **today**, then writes per-symbol avg buy/sell + FIFO batch P&L. Unmatched sells are booked as LOSS.  
**Run:** `run-batch-pnl.bat` · `--no-market-prices` · `--skip-refresh` · `--offline` · `--to-date YYYYMMDD` · `--input PATH` · `--output PATH`

---

## IBKR-SymbolDetail\

### `run-symbol-detail.bat` → `symbol_detail_report.py`
Per-symbol buys, sells, corporate actions, Yahoo last traded price, realized and unrealized P&L.  
**Run:** `run-symbol-detail.bat` · `--symbol NVDA` · `--symbols AAPL,AMZN` · `--no-market-prices`

---

## IBKR-Transaction\

### `ibkr_to_excel.py`
Converts IBKR Activity / TRANSACTIONS CSV(s) into a multi-sheet Excel summary workbook.  
**Run:** `python ibkr_to_excel.py --discover` · `--dir Latest` · `--input FILE.csv` · `--output PATH` · `--max-symbol-sheets N`

---

## IBKR-Client-GateWay\

### `Start-IBKR-Gateway.bat`
Starts the local IBKR Client Portal Gateway (HTTPS, typically port 5000); then open browser and log in.  
**Run:** `Start-IBKR-Gateway.bat` (no switches; required before any `*_IBKR.py` / SeasonalStocks)

---

## ListTop5SectorwiseStocks\

### `top5StocksByIndustry.py`
Prints top 5 holdings per sector ETF from `config.ini [ETFs]`; optional dividend payer report.  
**Run:** `python top5StocksByIndustry.py` · `--config PATH` · `--no-prices` · `--dividend-report` · `--dividend-csv PATH`

---

## SeasonalStocks\

### `seasonaStockLowAndHigh.py`
Uses IBKR CP monthly history to find common calendar months of annual highs/lows across a symbol list.  
**Run:** `python seasonaStockLowAndHigh.py` (no switches; requires CP Gateway logged in at `https://localhost:5000`)

---

## examples\

### `ema_single_ticker_test.py`
Debug helper: prints 52-EMA / targets for one ticker via `averagePriceFetcher` helpers.  
**Run:** `python examples\ema_single_ticker_test.py` · `python examples\ema_single_ticker_test.py TSLA`

---

## Quick “intended operation” cheat sheet

| Goal | Command |
|------|---------|
| Start WhatsApp alerts (price + rebuy + commands) | `C:\Investment\start_stock_alert.bat` |
| Stop alerts | `C:\Investment\stop_stock_alert.bat` |
| Refresh all IBKR Excels offline | `regenerate-ibkr-reports.bat --offline` |
| Download Flex + rebuild Buy/Sell | `cd IBKR-Flex-BuySell` → `run-report.bat --download` |
| Sync YTD into Buy/Sell cache | `python flex_buysell_report.py --sync-ytd` |
| Symbol P&L workbook | `cd IBKR-SymbolPnL` → `run-symbol-pnl.bat` |
| FIFO batch P&L (avg buy/sell + lot matches) | `cd IBKR-BatchPnL` → `run-batch-pnl.bat --no-market-prices` |
| Completely sold digest (dry) | `cd CompletelySoldAlert` → `run-alert.bat run --dry-run --force-market-day` |
| Live IBKR quotes → WhatsApp | `cd AutomatedTrading` → `python ClientPortalMarketSnapshot.py --send-whatsapp` |
| Chart S/R → WhatsApp | `python ChartSupportResistanceWhatsApp_IBKR.py --send-whatsapp` |

---

*Not financial advice. Keep credentials in `secrets.local.ini` / env vars — never commit live tokens.*
