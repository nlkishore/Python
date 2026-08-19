# C:\Investment — Cleanup & Tidy Plan

Saved reference so later cleanup can proceed **one action at a time** without redoing the folder review.

**Last updated:** 2026-08-19  
**Status:** Phase 1 (secrets, alerts, config, shared code, artifacts) — COMPLETE. Phase 2 (future enhancements) — see backlog below.  
**Source reviews:** feature inventory + duplication audit of `C:\Investment`  
**Related docs:** [`INVESTMENT-PROGRAMS-REFERENCE.md`](INVESTMENT-PROGRAMS-REFERENCE.md), [`IBKR-REPORTS-GUIDE.md`](IBKR-REPORTS-GUIDE.md), [`README.md`](README.md)

**How to use (Phase 2):** pick the next unchecked item from the backlog below, implement only that item, mark it done, stop. Do not restart planning unless requirements change.

---

## Feature inventory (developed capabilities)

| Area | What it does | Key paths |
|------|----------------|-----------|
| Root price monitor | Yahoo Finance % threshold alerts via CallMeBot or Twilio | `stock_whatsapp_monitor.py`, `config.ini` |
| AlertApp | **Consolidated** Green API monitor: price threshold alerts + `STATUS` / `WATCHLIST` / `SUPPORT SYMBOL` / `SOLD` commands + single-instance lock + heartbeat + watchdog | `AlertApp\backgroundAlert1.py` (active via `start_stock_alert.bat`) |
| AlertApp-IBKR | **ARCHIVED** (2026-08-19) — scripts moved to `AlertApp-IBKR\archive\`; see `AlertApp-IBKR\README.md` | `AlertApp-IBKR\README.md` |
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

**Stack notes:** ~61 first-party Python files. Tracked in Git (`C:\Python\Investment` on branch `GoogleAntiGraviryProjets`, remote `nlkishore/Python`). Python 3.10+/3.11+, pandas/openpyxl, yfinance, requests/httpx, PyYAML, LangGraph, WhatsApp providers, IBKR Flex + Client Portal, Java gateway.

**Shared modules (added 2026-08-18):**

| Path | Purpose |
|------|---------|
| `shared\config_loader.py` | Merged INI + env overrides; UTF-8 BOM safe; `green_api_credentials()`, `flex_credentials()` |
| `shared\alert_watchlist.py` | Load `[watchlist]` from AlertApp `config.ini` / `secrets.local.ini` |
| `AutomatedTrading\indicators.py` | Shared `atr14()`, `targets_ok()`, `append_atr_ema_columns()` |

**Secrets pattern (enforced):** live credentials in gitignored `secrets.local.ini` files; example templates committed; env vars override INI.

---

## Redundancy & tidy findings (audit 2026-08-18)

### Resolved in Phase 1
1. **Plaintext secrets** — removed from all source files; moved to `secrets.local.ini`.
2. **Exact config duplicate** — `AutomatedTrading\config_backup.ini` deleted.
3. **Overlapping alert apps** — `backgroundAlert.py` and `personalInvestAlert.py` archived; `backgroundAlert1.py` is the single supported path.
4. **Overlapping Symbol P&L** — `IBKR-SymbolPnL\symbol_pnl_from_buysell.py` is canonical; `trade_history\symbol_pnl.py` kept as internal store reference.
5. **Repeated indicator helpers** — ATR and `_targets_ok` extracted to `AutomatedTrading\indicators.py`.
6. **Fragmented dependencies** — per-project `requirements.txt` files added.
7. **Unsafe stop script** — replaced with process-specific stop.
8. **Generated clutter** — `__pycache__`, `stdout1.log`, stale CSVs removed or gitignored.

### Still deferred
- Intentional dual Activity CSV copies (`IBKR-Transaction\Latest\` and `IBKR-Download\AccountStatement\`) — do **not** delete until input readers share one root.
- `AlertApp-IBKR` prototype — not yet production-hardened.
- `ema_single_ticker_test.py` moved to `examples\`; not deleted.

### Runtime state (gitignored, keep local)
- `AutomatedTrading\chart_support_notify_state*.json`
- `IBKR-Flex-BuySell\data\state.json`, `downloads\flex_unavailable_windows.json`
- `CompletelySoldAlert\data\last_export.json`, `alert_cooldown.json`

---

## Target end state (achieved for Phase 1)

- [x] Canonical Excel only under `C:\Investment\reports\`
- [x] Secrets only in ignored local config / env; examples committed without live values
- [x] One supported daily alert path; legacy monitors under `archive\`
- [x] One canonical Symbol P&L story (workbook + entrypoint)
- [x] Per-project dependency manifests
- [x] Shared AutomatedTrading helpers for ATR / payload checks
- [x] Safe process stop for alerts; clear launcher/docs for supported commands

---

## Phase 1 checklist — COMPLETED (2026-08-18)

`[x]` = done · `[-]` = skipped with note

### 1. Secrets & config hygiene
- [x] Rotate Green API credentials and phone
- [-] Rotate CallMeBot / Twilio keys — not shared externally, no rotation needed
- [x] Rotate IBKR Flex token; moved to `secrets.local.ini`
- [x] Remove hardcoded secrets from `AlertApp\backgroundAlert.py` and `backgroundAlert1.py`
- [x] Strip secrets from `AutomatedTrading\config.ini` and `config_longterm.ini`
- [x] `.gitignore` expanded — covers config, secrets, venvs, state JSON, logs, generated data

### 2. Alert path consolidation
- [x] Supported path: `AlertApp\backgroundAlert1.py` via `start_stock_alert.bat`
- [x] Archived `backgroundAlert.py` and `personalInvestAlert.py` under `AlertApp\archive\`
- [x] `start_stock_alert.bat` updated and documented
- [x] `stop_stock_alert.bat` kills only `backgroundAlert1.py` by name

### 3. Config & P&L consolidation
- [x] `AutomatedTrading\config_backup.ini` deleted
- [x] `config_longterm.ini` retained as named strategy profile; credentials removed
- [x] Canonical Symbol P&L: `IBKR-SymbolPnL\symbol_pnl_from_buysell.py` → `reports\IBKR_Symbol_PnL_From_BuySell.xlsx`
- [x] `IBKR-REPORTS-GUIDE.md` updated

### 4. Dependencies & shared code
- [x] `AlertApp\requirements.txt`, `AutomatedTrading\requirements.txt` added
- [x] `shared\config_loader.py` and `shared\alert_watchlist.py` created
- [x] `AutomatedTrading\indicators.py` created
- [x] `AdaptiveAItrader.py`, `AdaptiveTraderWithVolume.py`, `ChartSupportAndSignals.py` updated

### 5. Artifacts & layout
- [x] Root `__pycache__` and `stdout1.log` removed
- [x] Stale Excel copies moved to `_archive`
- [x] `examples\ema_single_ticker_test.py` moved from `AutomatedTrading`
- [x] `AlertApp\archive\README.md` added

### 6. Verification
- [x] Flex + Symbol P&L reports write to canonical `reports\` folder
- [x] AlertApp imports cleanly; watchlist loads from config
- [x] Stop script confirmed targeted — does not kill unrelated Python processes
- [x] No live secrets in source or example files

---

## Known operational notes (2026-08-19)

| # | Issue | Detail | Fix / Action |
|---|-------|--------|-------------|
| 1 | `to_date` in `IBKR-Flex-BuySell\config.ini` | Must match your latest Activity CSV export date | Update `to_date = YYYYMMDD` each time you export a new Activity Statement |
| 2 | Flex API "Statement not available" for 2026 YTD | IBKR Flex does not serve current-year recent windows | Normal — tool falls back to Activity CSV automatically |
| 3 | Flex skip-cache file | `downloads\flex_unavailable_windows.json` records failed windows | Run `python flex_buysell_report.py --clear-skip-cache` then `--sync-ytd` to force retry |
| 4 | `--sync-ytd --force-download` does NOT call Flex | `--force-download` reimports Activity CSV only | Remove `--force-download`; or delete the cached Flex CSV then re-run without it |
| 5 | Delisted symbols (SKLZ, COUP, ATVI, ZNGA, SIVB) | Yahoo returns no price | Expected — P&L intact; current-price column blank for those rows |
| 6 | `FutureWarning` from pandas concat | `corporate_parse.py:316` — cosmetic | Fix in future session; does not affect output |
| 7 | Flex token still in `config.ini` | User re-entered token directly | Move `token =` to `secrets.local.ini`; delete from `config.ini` |

---

## Phase 2 — Future enhancement backlog

Pick one item per session. Mark `[~]` when started, `[x]` when done.

### A. IBKR data currency
- [ ] **Auto-update `to_date`** — parse newest filename in `IBKR-Transaction\Latest\` and set `to_date` automatically before each run
- [ ] **Unify Activity CSV input root** — single drop folder serving both `IBKR-Download` and `IBKR-Flex-BuySell`, removing manual dual-copy step
- [ ] **Flex token fully in `secrets.local.ini`** — remove `token` from `config.ini`; all credential paths via `shared\config_loader.flex_credentials()`

### B. Alerts
- [ ] **Green API token expiry warning** — log expiry date on startup; warn N days before expiry
- [x] **AlertApp-IBKR consolidation** — merged `SUPPORT`, `SOLD`, single-instance lock, heartbeat, watchdog into `AlertApp\backgroundAlert1.py`; `AlertApp-IBKR` archived (2026-08-19)
- [ ] **CompletelySoldAlert Windows Task Scheduler entry** — configure with correct venv path + working directory (see `CompletelySoldAlert\readme.txt`)

### C. Reporting
- [ ] **Auto-run Symbol P&L after BuySell regenerate** — add `IBKR-SymbolPnL` as step 4 in `regenerate-ibkr-reports.bat`
- [ ] **Fix pandas FutureWarning** — update `corporate_parse.py:316` concat call
- [ ] **Delisted symbol registry** — small list of known-delisted tickers; suppress Yahoo errors and flag rows explicitly in Completely_Sold sheet
- [ ] **Seasonal report output path** — `seasonal_consistency_report.csv` writes to cwd; redirect to `reports\`

### D. Code quality
- [ ] **`ChartSupportAndSignals_IBKR.py`** — inline credential reads; migrate to `shared\config_loader.green_api_credentials()`
- [ ] **`ClientPortalMarketSnapshot.py`** — same migration
- [ ] **`ChartSupportResistanceWhatsApp_IBKR.py`** — same migration
- [ ] **`CompletelySoldAlert\config.py`** — remove leftover unused `configparser` import (already uses `shared\config_loader`)

### E. Infrastructure
- [ ] **`C:\Investment` as its own git repo** — currently tracked via `C:\Python\Investment`; consider making `C:\Investment` the canonical git root to avoid path confusion
- [ ] **Consolidate `.venv` folders** — `IBKR-Flex-BuySell\.venv` + `CompletelySoldAlert\.venv` (~325 MB total); merge to one root venv once dependency conflicts resolved
- [ ] **Document single-venv setup** — one clear `## Setup` section in `README.md` covering full install for all modules

---

## Explicit non-goals (unless planned separately)

- Live order execution / trading automation redesign
- Deleting `Documents\` or `FSM\` personal data
- Rewriting the vendored Client Portal Gateway
- Deduplicating Activity CSVs before unifying input readers

---

*Personal tooling reference — not financial advice. Verify credentials are never committed before any public push.*
