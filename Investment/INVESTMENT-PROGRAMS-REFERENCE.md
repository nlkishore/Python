# C:\Investment — Programs Reference

Future reference for all investment automation under this folder: what each feature does, how to run it, and what to configure first.

**Last reviewed:** May 2026

---

## Folder map

| Folder | Purpose |
|--------|---------|
| `reports\` | **Canonical IBKR Excel outputs** (Buy/Sell, TradeHistory, AccountStatement P1) — see `IBKR-REPORTS-GUIDE.md` |
| `AlertApp\` | Green API WhatsApp price alerts (hardcoded watchlist) |
| `AlertApp-IBKR\` | IBKR + support-level alert prototype (not fully configured) |
| `AutomatedTrading\` | EMA / ATR / chart heuristics; Yahoo or IBKR data; optional WhatsApp |
| `IBKR-Client-GateWay\` | IBKR Client Portal REST gateway (port 5000) |
| `IBKR-Transaction\` | IBKR CSV drop folder (`Latest\`) for Activity / TRANSACTIONS |
| `IBKR-Download\` | Account Statement CSVs + P1 report generator |
| `IBKR-Flex-BuySell\` | Flex download, Buy/Sell + trade_history tools |
| `ListTop5SectorwiseStocks\` | Top 5 ETF holdings by sector |
| `SeasonalStocks\` | Seasonal peak/trough month analysis (IBKR history) |
| `Documents\` | Personal PDFs (no scripts) |
| `FSM\` | FSM broker Excel records (data only) |
| `CompletelySoldAlert\` | LangGraph alert when sold stocks drop below config % vs last sold; WhatsApp digest |
| Root (`C:\Investment\`) | CallMeBot/Twilio WhatsApp monitor + `regenerate-ibkr-reports.bat` |

---

## Shared prerequisites

### Python environment (recommended)

```cmd
cd C:\Investment
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

Install additional packages per folder as noted below.

### IBKR Client Portal Gateway (for IBKR scripts)

Required by: `SeasonalStocks`, `AutomatedTrading\*IBKR*`, `ClientPortalMarketSnapshot.py`, etc.

| Step | Action |
|------|--------|
| 1 | Run `IBKR-Client-GateWay\Start-IBKR-Gateway.bat` |
| 2 | Login at **https://localhost:5000** |
| 3 | Verify session: `POST /v1/api/iserver/auth/status` → `authenticated: true` |

Full guide: **`IBKR-Client-GateWay\README.md`**

### WhatsApp notification methods (used in different scripts)

| Method | Used in | Config location |
|--------|---------|-----------------|
| **CallMeBot** | Root `stock_whatsapp_monitor.py` | `config.ini` → `[whatsapp]` |
| **Twilio** | Root monitor (optional) | `config.ini` → `[whatsapp]` |
| **Green API** | `AlertApp\`, `AutomatedTrading\` chart scripts | Hardcoded or `AutomatedTrading\config.ini` → `[trading]` |

**Never commit files with live API keys** (`config.ini` is gitignored at root).

---

## 1. Root — Stock WhatsApp monitor

### Feature

Watches Yahoo Finance symbols. Sends WhatsApp when price moves above/below configured % thresholds vs a reference price (previous close or open).

### Programs

| File | Purpose |
|------|---------|
| `stock_whatsapp_monitor.py` | Main monitor (continuous or one-shot) |
| `start_stock_alert.bat` | Starts `AlertApp\backgroundAlert1.py` instead |
| `silent_start.vbs` | Hidden start of `start_stock_alert.bat` |
| `stop_stock_alert.bat` | Stops Python alert processes |

### Configuration

| File | Section | Keys |
|------|---------|------|
| `config.ini` | `[stock]` | `symbols`, `check_interval_seconds`, `up_percent`, `down_percent`, `reference`, `alert_cooldown_seconds` |
| `config.ini` | `[whatsapp]` | `method` (callmebot \| twilio), `phone`, `apikey` (+ Twilio fields if used) |

Copy template: `config.ini.example` or `config.ini.example-fixed-ref` (per-symbol fixed reference prices).

### Dependencies

```cmd
pip install -r requirements.txt
```
(`yfinance`, `requests`)

### How to run

```cmd
cd C:\Investment
.venv\Scripts\activate.bat
python stock_whatsapp_monitor.py
python stock_whatsapp_monitor.py --once
python stock_whatsapp_monitor.py --config my-config.ini
```

### Docs

- `README.md`

---

## 2. AlertApp — Green API background alerts

### Feature

Background loop: compares Yahoo prices to hardcoded reference levels; sends Green API WhatsApp on breach. `backgroundAlert1.py` also replies to incoming `STATUS` command.

### Programs

| File | Purpose |
|------|---------|
| `backgroundAlert1.py` | **Active** — used by `start_stock_alert.bat` |
| `backgroundAlert.py` | Simpler 10-minute monitor loop |
| `personalInvestAlert.py` | Browser-based via `pywhatkit` (opens WhatsApp Web) |

### Configuration

**No `config.ini`** — edit constants inside each script:

- `ID_INSTANCE`, `API_TOKEN_INSTANCE`, `TARGET_PHONE` (Green API)
- `WATCHLIST` dict: `{symbol: [ref_price, up_%, down_%]}`

### Dependencies

```cmd
pip install whatsapp-api-client-python yfinance
```

Green API account: https://green-api.com/ (link WhatsApp device in console).

### How to run

```cmd
cd C:\Investment
start_stock_alert.bat
```

Or directly:

```cmd
python AlertApp\backgroundAlert1.py
```

### Docs

- `AlertApp\readme.txt` (Green API setup, optional Windows service via NSSM)

---

## 3. AlertApp-IBKR — Prototype

### Feature

Experimental: support-level calculation from 6-month Yahoo history + Green API command listener.

### Program

- `AlertApp-IBKR\backgroundAlert.py`

### Configuration

Placeholder credentials (`YOUR_ID_INSTANCE`, etc.) — **must be filled in before use**.

### Status

Prototype only; prefer `AutomatedTrading` IBKR scripts for production-style workflows.

---

## 4. AutomatedTrading — Analysis & signals

### Feature

**Analysis only** (not live order execution):

- 52-week EMA reference targets
- ATR adaptive bands
- Volume-filtered buy/sell/hold
- Chart pivot support/resistance + candle heuristics
- IBKR live snapshot and intraday chart analysis
- Optional WhatsApp alerts (Green API)

### Programs

| Script | Data source | Output |
|--------|-------------|--------|
| `averagePriceFetcher.py` | Yahoo | `trading_targets.csv` |
| `AdaptiveAItrader.py` | Yahoo | `adaptive_ai_targets.csv` |
| `AdaptiveTraderWithVolume.py` | Yahoo | `adaptive_trader_volume.csv` |
| `ChartSupportAndSignals.py` | Yahoo | `chart_support_signals.csv` + optional WhatsApp |
| `ChartSupportAndSignals_IBKR.py` | IBKR Client Portal | `chart_support_signals_ibkr.csv` |
| `ClientPortalMarketSnapshot.py` | IBKR CP | Console / optional WhatsApp |
| `ChartSupportResistanceWhatsApp_IBKR.py` | IBKR CP candles | S/R digest + optional WhatsApp |
| `ema_single_ticker_test.py` | Yahoo | Debug EMA for one symbol |

### Configuration

| File | Purpose |
|------|---------|
| `config.ini` | **Primary** — symbols, CSV paths, chart/WhatsApp settings |
| `config_longterm.ini` | Daily bars, longer history (10/10 pivots, 1y) |
| `config_backup.ini` | Backup copy |

**`[trading]`** — symbols, output CSV paths, chart pivot settings, market-hours watch loop, Green API WhatsApp fields.

**`[ibkr]`** — `ibkr_data_source` (`client_portal` \| `tws_socket`), `cp_gateway_host`, `cp_gateway_port` (5000), bar size, duration, TWS socket host/port if used.

### Prerequisites

| Mode | Needs |
|------|--------|
| Yahoo scripts | `pandas`, `yfinance` |
| IBKR Client Portal | Gateway running + browser login |
| IBKR TWS socket | `pip install ib-insync`, TWS/IB Gateway on 7496/7497 |
| WhatsApp | Green API credentials in `config.ini` |

### How to run

```cmd
cd C:\Investment\AutomatedTrading

REM Yahoo-only (no gateway)
python averagePriceFetcher.py
python ChartSupportAndSignals.py

REM IBKR (start gateway + login first)
python ChartSupportAndSignals_IBKR.py
python ClientPortalMarketSnapshot.py --send-whatsapp
python ChartSupportResistanceWhatsApp_IBKR.py --quiet --send-whatsapp

REM Long-term config variant
python ChartSupportAndSignals_IBKR.py --config config_longterm.ini
```

Use `--help` on each script for flags.

### Docs

| File | Content |
|------|---------|
| `AutomatedTrading-Scripts-Reference.md` | Full script comparison and config keys |
| `IBKR_Snapshot_and_Chart_WhatsApp.md` | Snapshot/chart WhatsApp CLI |
| `Readme.md` | Strategy notes (EMA, ATR, RSI) |

---

## 5. IBKR-Client-GateWay — API gateway

### Feature

Local HTTPS REST API bridge to Interactive Brokers (Client Portal Web API on port **5000**).

### Programs

| File | Purpose |
|------|---------|
| `Start-IBKR-Gateway.bat` | **Recommended** start (CMD) |
| `Start-IBKR-Gateway.ps1` | PowerShell start |
| `clientportal.gw\bin\run.bat` | Internal IBKR launcher |

### Configuration

| File | Key settings |
|------|----------------|
| `clientportal.gw\root\conf.yaml` | `listenPort: 5000`, `listenSsl: true`, `proxyRemoteHost` |

### Prerequisites

- Java 8+ / 11 / 17 (`java -version`)
- IBKR account + browser login + 2FA

### How to run

```cmd
C:\Investment\IBKR-Client-GateWay\Start-IBKR-Gateway.bat
```

Then open **https://localhost:5000** and log in.

### Docs

- `IBKR-Client-GateWay\README.md`
- `clientportal.gw\doc\GettingStarted.md`

---

## 6. SeasonalStocks — Peak / trough months

### Feature

For each symbol in a CSV list, fetches ~5 years of monthly IBKR history and reports the most common calendar month for annual price **high** and **low**.

### Programs

| File | Purpose |
|------|---------|
| `seasonaStockLowAndHigh.py` | Main analysis |
| `seasonal_stocks_list.csv` | Input symbols (Ag, Energy, Retail, Travel, etc.) |

### Output

- `C:\Investment\seasonal_consistency_report.csv` (written to current working directory)

### Configuration

- No local config file
- API URL hardcoded: `https://localhost:5000/v1/api`

### Prerequisites

1. IBKR Client Portal Gateway running + logged in
2. `pip install pandas requests`

### How to run

```cmd
C:\Investment\IBKR-Client-GateWay\Start-IBKR-Gateway.bat
REM Login at https://localhost:5000

cd C:\Investment
python SeasonalStocks\seasonaStockLowAndHigh.py
```

### Docs

- `SeasonalStocks\Readme.txt`

---

## 7. ListTop5SectorwiseStocks — Sector ETF holdings

### Feature

Lists **top 5 holdings** per sector ETF from `config.ini`. Optional live prices and dividend report.

### Programs

| File | Purpose |
|------|---------|
| `top5StocksByIndustry.py` | CLI |

### Configuration

`config.ini` → section **`[ETFs]`**:

```ini
[ETFs]
Technology = XLK
Consumer_Staples = XLP
Health_Care = XLV
Financials = XLF
Energy = XLE
```

### Dependencies

```cmd
pip install pandas yfinance
```

No IBKR or API keys required.

### How to run

```cmd
cd C:\Investment\ListTop5SectorwiseStocks
python top5StocksByIndustry.py
python top5StocksByIndustry.py --no-prices
python top5StocksByIndustry.py --motion-report --dividend-csv dividends.csv
```

### Docs

- `ListTop5SectorwiseStocks\readme.md`

---

## 8. IBKR-Transaction — CSV to Excel

### Feature

Converts one **IBKR Activity / TRANSACTIONS CSV** export into a multi-sheet Excel workbook: buy/sell detail, computed positions, dividend-implied shares, reconciliation.

### Programs

| File | Purpose |
|------|---------|
| `ibkr_to_excel.py` | Main converter |

### Input / output

| Item | Default path |
|------|----------------|
| Input CSV | `Latest\U3831357.TRANSACTIONS.*.csv` |
| Output | `IBKR_Summary.xlsx` (same folder) |

### Dependencies

```cmd
pip install -r requirements-ibkr-excel.txt
```
(`pandas`, `openpyxl`)

No live gateway — download CSV manually from IBKR Activity Statement.

### How to run

```cmd
cd C:\Investment\IBKR-Transaction
python ibkr_to_excel.py
python ibkr_to_excel.py --input "C:\path\to\TRANSACTIONS.csv"
python ibkr_to_excel.py --discover --dir C:\Investment\IBKR-Transaction
```

---

## 9. CompletelySoldAlert — Sold position price-drop digest

### Feature

LangGraph workflow: on **NYSE market days**, load **Completely_Sold** from IBKR Flex Excel (refresh if &gt; 24h), alert when `Change_Since_Last_Sold_Pct` is at or below **`alert.price_drop_threshold_pct`** in `config/settings.yaml`, send **one WhatsApp digest** (Green API).

### Programs

| File | Purpose |
|------|---------|
| `completely_sold_alert\` | Python package (LangGraph nodes) |
| `run-alert.bat` | Activates `.venv` and runs CLI |
| `config\settings.yaml` | Threshold, paths, WhatsApp (gitignored) |

### Configuration

Copy `config\settings.example.yaml` → `config\settings.yaml`. Key: `alert.price_drop_threshold_pct` (default `-5.0`).

Env overrides: `GREEN_API_ID_INSTANCE`, `GREEN_API_TOKEN`, `WHATSAPP_TARGET_PHONE`.

### Prerequisites

1. `IBKR-Flex-BuySell` report at `data.report_path`
2. Project venv: `pip install -r requirements.txt` inside `CompletelySoldAlert\`
3. Green API credentials (same pattern as `AlertApp\`)

### How to run

```cmd
cd C:\Investment\CompletelySoldAlert
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy config\settings.example.yaml config\settings.yaml

REM Test with fixture
python -m completely_sold_alert run --fixture fixtures\completely_sold_sample.json --dry-run --force-market-day --print-digest

REM Production (market days only)
python -m completely_sold_alert run
```

### Docs

- `CompletelySoldAlert\readme.txt` — **full future reference** (setup, execute, troubleshoot)
- `CompletelySoldAlert\README.md` — quick start
- `MyGeneratedProjects\GitRepoPlan\repo-consolidated\docs\review\COMPLETELY_SOLD_PRICE_ALERT_DESIGN.md`

---

## 10. FSM & Documents (data only)

| Folder | Contents | Scripts |
|--------|----------|---------|
| `FSM\` | FSM transaction Excel workbooks (`.xlsx`, `.xlsm`) | None |
| `Documents\` | Personal PDFs | None |

---

## Quick reference — what needs what

| Feature | Gateway | Yahoo | Green API / CallMeBot | Config file |
|---------|---------|-------|----------------------|-------------|
| Root WhatsApp monitor | No | Yes | Yes | `config.ini` |
| AlertApp | No | Yes | Green API (in script) | Hardcoded |
| AutomatedTrading (Yahoo) | No | Yes | Optional | `AutomatedTrading\config.ini` |
| AutomatedTrading (IBKR) | **Yes** | — | Optional | `AutomatedTrading\config.ini` |
| SeasonalStocks | **Yes** | — | No | — |
| ListTop5SectorwiseStocks | No | Yes | No | `ListTop5SectorwiseStocks\config.ini` |
| IBKR-Transaction | No | No | No | CSV path via CLI |

---

## Recommended daily workflows

### A. Price alerts only (no IBKR)

```cmd
cd C:\Investment
.venv\Scripts\activate.bat
python stock_whatsapp_monitor.py
```

Or: `start_stock_alert.bat` (Green API via AlertApp).

### B. IBKR analysis session

```cmd
C:\Investment\IBKR-Client-GateWay\Start-IBKR-Gateway.bat
REM Browser: https://localhost:5000 — login

cd C:\Investment\AutomatedTrading
python ChartSupportAndSignals_IBKR.py
python ClientPortalMarketSnapshot.py
```

### C. Seasonal study

```cmd
C:\Investment\IBKR-Client-GateWay\Start-IBKR-Gateway.bat
REM Login

cd C:\Investment
python SeasonalStocks\seasonaStockLowAndHigh.py
REM Output: seasonal_consistency_report.csv
```

### D. Portfolio / tax prep (offline)

```cmd
REM Export TRANSACTIONS CSV from IBKR web
cd C:\Investment\IBKR-Transaction
python ibkr_to_excel.py --input Latest\your_export.csv
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| `WinError 10061` on port 5000 | Gateway not running | `Start-IBKR-Gateway.bat` |
| `authenticated: false` | Not logged in | https://localhost:5000 |
| No WhatsApp messages | Wrong API key / phone | Check `config.ini` or script constants |
| Empty seasonal report | Gateway down or bad symbols | Check gateway + `seasonal_stocks_list.csv` |
| `ClassNotFoundException` (Java) | Wrong gateway start dir | Use `Start-IBKR-Gateway.bat` only |

Gateway logs: `IBKR-Client-GateWay\clientportal.gw\logs\gw.<date>.log`

---

## Related documentation index

| Path | Topic |
|------|--------|
| `CLEANUP-AND-TIDY-PLAN.md` | Feature inventory + redundancy cleanup checklist (sequential backlog) |
| `README.md` | Root WhatsApp monitor |
| `IBKR-Client-GateWay\README.md` | Gateway start & verify |
| `SeasonalStocks\Readme.txt` | Seasonal analysis runbook |
| `AutomatedTrading\AutomatedTrading-Scripts-Reference.md` | All trading scripts |
| `AutomatedTrading\IBKR_Snapshot_and_Chart_WhatsApp.md` | IBKR snapshot WhatsApp |
| `ListTop5SectorwiseStocks\readme.md` | ETF top-5 CLI |
| `AlertApp\readme.txt` | Green API alert setup |

---

*This document describes local tooling for personal use. Not financial advice. Verify credentials are not committed to version control.*
