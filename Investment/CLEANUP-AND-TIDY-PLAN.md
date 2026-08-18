# C:\Investment — Cleanup & Tidy Plan

Saved reference so later cleanup can proceed **one action at a time** without redoing the folder review.

**Last updated:** 2026-08-18 (cleanup implemented)  
**Source reviews:** feature inventory + duplication audit of `C:\Investment`  
**Related docs:** [`INVESTMENT-PROGRAMS-REFERENCE.md`](INVESTMENT-PROGRAMS-REFERENCE.md), [`IBKR-REPORTS-GUIDE.md`](IBKR-REPORTS-GUIDE.md), [`README.md`](README.md)

**How to use:** pick the next unchecked item under [Action checklist](#action-checklist), implement only that item, mark it done, stop. Do not restart planning unless requirements change.

---

## Feature inventory (developed capabilities)

| Area | What it does | Key paths |
|------|----------------|-----------|
| Root price monitor | Yahoo Finance % threshold alerts via CallMeBot or Twilio | `stock_whatsapp_monitor.py`, `config.ini` |
| AlertApp | Green API WhatsApp threshold alerts; `STATUS` command on active script | `AlertApp\backgroundAlert1.py` (active via `start_stock_alert.bat`), `backgroundAlert.py`, `personalInvestAlert.py` |
| AlertApp-IBKR | WhatsApp command listener (`STATUS` / `SUPPORT` / `SOLD`); prototype-style | `AlertApp-IBKR\backgroundAlert.py` |
| AutomatedTrading | EMA / ATR / volume / chart S-R heuristics; Yahoo or IBKR data; optional WhatsApp | `AutomatedTrading\` |
| IBKR Client Portal Gateway | Local HTTPS REST bridge (port 5000) | `IBKR-Client-GateWay\` |
| IBKR Flex Buy/Sell | Flex download, Activity merge, Completely_Sold / Still_Holding Excel | `IBKR-Flex-BuySell\` → `reports\IBKR_BuySell_Since_2020.xlsx` |
| Trade history | Durable store + Symbol_PnL workbook | `IBKR-Flex-BuySell\trade_history\` → `reports\IBKR_TradeHistory.xlsx` |
| IBKR Account Statement P1 | Deposits, trades, dividends, withholding tax, interest | `IBKR-Download\` → `reports\IBKR_AccountStatement_P1.xlsx` |
| IBKR Transaction Excel | Activity CSV → multi-sheet summary workbook | `IBKR-Transaction\ibkr_to_excel.py` |
| IBKR Symbol PnL | Profit/Loss workbook from Buys/Sells sheets | `IBKR-SymbolPnL\` → `reports\IBKR_Symbol_PnL_From_BuySell.xlsx` |
| CompletelySoldAlert | LangGraph market-day digest when sold names drop vs last sold | `CompletelySoldAlert\` |
| SeasonalStocks | Common calendar month of annual high/low via IBKR history | `SeasonalStocks\` |
| Sector top-5 | Top holdings per sector ETF | `ListTop5SectorwiseStocks\` |
| Data only | Personal PDFs / FSM Excel — no scripts | `Documents\`, `FSM\` |
| Report orchestration | One-shot regenerate into canonical `reports\` | `regenerate-ibkr-reports.bat` |

**Stack notes:** ~61 first-party Python files; not a Git repository today. Python 3.10+/3.11+, pandas/openpyxl, yfinance, requests/httpx, PyYAML, LangGraph, WhatsApp providers, IBKR Flex + Client Portal, Java gateway.

---

## Redundancy & tidy findings

### Confirmed

1. **Plaintext secrets duplicated** — Green API id/token/phone in `AlertApp\*.py` and `AutomatedTrading\config*.ini`; CallMeBot (and related) in root `config.ini`; IBKR Flex token in `IBKR-Flex-BuySell\config.ini`.
2. **Exact config duplicate** — `AutomatedTrading\config.ini` ≡ `config_backup.ini`.
3. **Overlapping alert apps** — root monitor + three AlertApp variants all do Yahoo threshold → WhatsApp with different providers/config styles.
4. **Overlapping Symbol P&L** — `IBKR-Flex-BuySell\trade_history\symbol_pnl.py` and `IBKR-SymbolPnL\symbol_pnl_from_buysell.py`.
5. **Repeated indicator helpers** — ATR and `_targets_ok` copied across Adaptive/Chart scripts in `AutomatedTrading\`.
6. **Fragmented dependencies** — root `requirements.txt` is only `yfinance`/`requests`; AlertApp needs undeclared `whatsapp_api_client_python`; AutomatedTrading needs `pandas` with no local manifest.
7. **Unsafe stop script** — `stop_stock_alert.bat` runs `taskkill /F /IM python.exe /T` (kills all Python).
8. **Generated clutter** — two `.venv` folders (~326 MB), `__pycache__`, `stdout1.log`, root `seasonal_consistency_report.csv`, non-canonical Excel copies under project `reports\` / `data\` folders.
9. **Intentional dual CSV copies** — Activity statements mirrored in `IBKR-Transaction\Latest\` and `IBKR-Download\AccountStatement\` per `IBKR-REPORTS-GUIDE.md` — do **not** delete until input contract is redesigned.

### Suspected / clarify before delete

- `ema_single_ticker_test.py` (debug)
- Exploratory `AutomatedTrading\Readme.md` vs short `Readme.txt`
- Prototype `AlertApp-IBKR` if command interface is unused
- Vendored `IBKR-Client-GateWay` — do not “dedupe” as ordinary source

### Keep as runtime state (ignore if Git is added later)

- `AutomatedTrading\chart_support_notify_state*.json`
- `IBKR-Flex-BuySell\data\state.json`, `downloads\flex_unavailable_windows.json`
- `CompletelySoldAlert\data\last_export.json`, `alert_cooldown.json`

---

## Target end state

- Canonical Excel only under `C:\Investment\reports\`
- Secrets only in ignored local config / env; examples committed without live values
- One supported daily alert path; legacy monitors under `archive\` or `examples\`
- One canonical Symbol P&L story (workbook + entrypoint)
- Per-project or one documented shared dependency install
- Shared AutomatedTrading helpers for ATR / payload checks
- Safe process stop for alerts; clear launcher/docs for supported commands

---

## Action checklist

Mark status as you go: `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` skipped (with note).

### 1. Secrets & config hygiene
- [ ] Rotate Green API credentials and phone (assumed compromised once present in source)
- [ ] Rotate CallMeBot / Twilio keys in root `config.ini` if ever shared
- [ ] Rotate IBKR Flex token in `IBKR-Flex-BuySell\config.ini` if ever shared
- [ ] Remove hardcoded secrets from `AlertApp\backgroundAlert.py` and `backgroundAlert1.py`
- [ ] Strip secrets from `AutomatedTrading\config.ini` and `config_longterm.ini`; use env or ignored local overlay
- [ ] Ensure `.gitignore` covers `config.ini`, `settings.yaml`, tokens, `.venv/`, state JSON, logs

### 2. Alert path consolidation
- [ ] Decide single supported alert path (recommend: either root `stock_whatsapp_monitor.py` **or** Green API `backgroundAlert1.py`, plus optional `AlertApp-IBKR` if commands are needed)
- [ ] Archive unused AlertApp scripts (`backgroundAlert.py`, `personalInvestAlert.py`, etc.)
- [ ] Align `start_stock_alert.bat` / docs with the chosen path
- [ ] Replace `stop_stock_alert.bat` with PID- or script-specific stop (no global `python.exe` kill)

### 3. Config & P&L consolidation
- [ ] Delete `AutomatedTrading\config_backup.ini` after confirming still identical to `config.ini`
- [ ] Keep `config_longterm.ini` as a named profile only (no secrets)
- [ ] Choose canonical Symbol P&L: trade_history export **or** `IBKR-SymbolPnL`; make the other a thin wrapper or archive
- [ ] Document the chosen report path in `IBKR-REPORTS-GUIDE.md`

### 4. Dependencies & shared code
- [ ] Add `AlertApp\requirements.txt` (or document shared env) including `whatsapp_api_client_python`, `yfinance`
- [ ] Add `AutomatedTrading\requirements.txt` including `pandas`, `yfinance`, optional WhatsApp / `ib-insync`
- [ ] Extract shared ATR + `_targets_ok` (and related helpers) into one AutomatedTrading module; update importers

### 5. Artifacts & layout
- [ ] Remove/regenerate: root `__pycache__`, `stdout1.log`, stale root seasonal CSV if regenerable
- [ ] Apply retention to non-canonical Excel under `IBKR-Flex-BuySell\reports`, `IBKR-Download\reports`, `CompletelySoldAlert\data` (keep `_archive` policy explicit)
- [ ] Optionally remove local `.venv` folders when using a single shared venv (recreate via docs)
- [ ] Do **not** bulk-delete dual Activity CSV trees until readers share one input root
- [ ] Optionally introduce `archive\` / `examples\` for debug scripts and prototype AlertApp-IBKR

### 6. Verification (after each batch)
- [ ] Dry-run / offline: CompletelySoldAlert, Flex `--from-downloads`, `regenerate-ibkr-reports.bat --offline`
- [ ] Confirm outputs land only under `reports\` for canonical workbooks
- [ ] Confirm launchers import cleanly from declared requirements
- [ ] Confirm stop script does not kill unrelated Python processes
- [ ] Grep workspace for leftover live tokens in source/examples

---

## Suggested order for “one by one” sessions

1. Secrets rotation + remove hardcoded credentials (highest risk)  
2. Safe stop script + pick one alert path  
3. Delete `config_backup.ini` + dependency manifests  
4. Symbol P&L canonicalization  
5. Shared ATR helpers  
6. Artifact cleanup  
7. Optional archive of prototypes / debug scripts  

---

## Explicit non-goals (unless planned separately)

- Live order execution / trading automation redesign  
- Deleting `Documents\` or `FSM\` personal data  
- Rewriting the vendored Client Portal Gateway  
- Deduplicating Activity CSVs before unifying input readers  

---

*Personal tooling reference — not financial advice. Verify credentials are never committed if this folder becomes a Git repo.*
