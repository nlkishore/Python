# Completely Sold Price Alert

LangGraph-orchestrated monitor for **fully closed positions** from IBKR Flex Buy/Sell. Sends **one WhatsApp digest** when current price drops below a **configurable %** vs last sold price.

**Full future reference:** [readme.txt](readme.txt) — setup, execution, troubleshooting, and related programs under `C:\Investment`.

**Design:** `C:\MyGeneratedProjects\GitRepoPlan\repo-consolidated\docs\review\COMPLETELY_SOLD_PRICE_ALERT_DESIGN.md`

## Setup

```cmd
cd C:\Investment\CompletelySoldAlert
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy config\settings.example.yaml config\settings.yaml
```

Edit `config\settings.yaml`:

- `alert.price_drop_threshold_pct` (e.g. `-5.0`)
- `data.report_path` → `C:/Investment/reports/IBKR_BuySell_Since_2020.xlsx`
- WhatsApp: `GREEN_API_ID_INSTANCE`, `GREEN_API_TOKEN`, `WHATSAPP_TARGET_PHONE` env vars or yaml

IBKR report refresh: see `C:\Investment\IBKR-REPORTS-GUIDE.md`.

## Commands

```cmd
REM Offline test (fixture, no market-day gate issues on weekends use --force-market-day)
python -m completely_sold_alert run --fixture fixtures\completely_sold_sample.json --dry-run --force-market-day --print-digest

REM Production (NYSE market days only)
python -m completely_sold_alert run

REM Dry-run against real Excel
python -m completely_sold_alert run --dry-run --force-market-day --print-digest

REM Status
python -m completely_sold_alert status

REM Refresh IBKR report only
python -m completely_sold_alert refresh-only
```

Or: `run-alert.bat run --dry-run ...`

## Workflow

1. `check_market_day` — skip weekends/NYSE holidays
2. `check_freshness` — if report &gt; 24h, run `flex_buysell_report.py --from-downloads`
3. Load `Completely_Sold` sheet
4. Evaluate `Change_Since_Last_Sold_Pct <= price_drop_threshold_pct`
5. Format single digest → Green API WhatsApp

## Task Scheduler

Daily post-market (~16:30 ET). Graph skips non-trading days automatically.

```cmd
C:\Investment\CompletelySoldAlert\run-alert.bat run
```

## Project isolation

Uses its own `.venv` with `langgraph` and `langchain-core`. Does not modify `C:\Investment\requirements.txt`.
