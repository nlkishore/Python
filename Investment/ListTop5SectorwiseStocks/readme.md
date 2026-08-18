# ListTop5SectorwiseStocks

Lists the **top five holdings** for each sector ETF defined in `config.ini`, using **yfinance** fund holdings data. Optionally fetches a **last price** and **currency** per holding (extra API calls per stock).

With **`--dividend-report`**, after those tables the script prints an extra **dividend report**: only holdings that Yahoo Finance treats as dividend payers (among the same top‑5 names), with **symbol**, **price**, yield, trailing annual dividend per share, optional 5‑year average yield and ex‑dividend date. You can also write this table to **`--dividend-csv`**.

Not financial advice; holdings and quotes come from public Yahoo Finance data and may be delayed or incomplete.

## Contents

| File | Purpose |
|------|---------|
| `top5StocksByIndustry.py` | CLI script: read `[ETFs]`, print top 5 holdings per ETF |
| `config.ini` | Maps sector labels → ETF ticker symbols |

## Requirements

- Python 3.10+ recommended (uses `str \| Path` typing with `from __future__ import annotations`)
- Packages: `pandas`, `yfinance`

```bash
pip install pandas yfinance
```

## Configuration (`config.ini`)

Use a section **`[ETFs]`**. Each key is a sector label (spaces may use underscores); each value is the **ETF ticker** used to resolve holdings (e.g. sector proxies like XLK, XLF).

Example:

```ini
[ETFs]
Technology = XLK
Consumer_Staples = XLP
Health_Care = XLV
Financials = XLF
Energy = XLE
```

## Command-line flags

| Flag | Short | Description |
|------|-------|----------------|
| `--config PATH` | `-c` | Path to the INI file. **Default:** `config.ini` in the **same folder as the script** (not the current working directory). |
| `--no-prices` | — | Do **not** fetch per-stock quotes. Output shows holdings and weights only (faster; fewer network calls). |
| `--dividend-report` | — | Append a dividend-only table for top‑5 holdings that pay dividends (`info` / dividend history via yfinance). One extra ticker fetch per holding when building the dividend row. |
| `--dividend-csv PATH` | — | Write the dividend table to CSV (UTF‑8). **Implies** `--dividend-report`. If nobody qualifies, writes headers only. |

With **no** `--no-prices` (default): for each top holding, the script requests last price via `yfinance` (`fast_info`, with fallback to recent daily close). The dividend pass reuses known price when available; otherwise it fetches quote data again.

## Execution commands

Adjust paths if your repo root differs.

### From the project folder (recommended)

```powershell
cd C:\Investment\ListTop5SectorwiseStocks

python top5StocksByIndustry.py
```

Uses the default `config.ini` next to the script.

### Explicit config path

```powershell
python top5StocksByIndustry.py --config C:\Investment\ListTop5SectorwiseStocks\config.ini
```

```powershell
python top5StocksByIndustry.py -c .\config.ini
```

### Holdings only (no last prices)

```powershell
python top5StocksByIndustry.py --no-prices
```

### From parent directory (`C:\Investment`)

```powershell
cd C:\Investment

python ListTop5SectorwiseStocks\top5StocksByIndustry.py --config ListTop5SectorwiseStocks\config.ini
```

### Combine flags

```powershell
python top5StocksByIndustry.py --config .\config.ini --no-prices
```

### Dividend report (console + optional CSV)

```powershell
python top5StocksByIndustry.py --dividend-report
```

```powershell
python top5StocksByIndustry.py --dividend-report --dividend-csv .\dividend_report.csv
```

```powershell
# Holdings without prices first, dividend section still obtains prices per dividend row where needed
python top5StocksByIndustry.py --no-prices --dividend-report
```

## Sample output

For each sector/ETF block you get a table with columns such as:

- **Symbol**, **Name**, **Holding Percent** (formatted as %)
- **Last price**, **Currency** — omitted when using `--no-prices`

After **`--dividend-report`**:

- Filtered rows: **Sector**, **ETF**, **Symbol**, **Name**, **Last price**, **Currency**, **Dividend yield %**, **Annual div/sh**, **5Y avg yield %**, **Ex-dividend date** (some fields empty depending on Yahoo data).

## Troubleshooting

- **`No [ETFs] section found`** — The INI path being read does not contain `[ETFs]`. Use `--config` to point at this folder’s `config.ini`, or run from this directory so the default path resolves correctly.
- **`Config file not found`** — Fix `--config` to an absolute or correct relative path.
- **Missing columns / holdings errors** — Upgrade yfinance: `pip install -U yfinance`. Some ETFs may not expose holdings in all environments.
- **Slow runs** — Default mode quotes each of the top 5 names per ETF; use `--no-prices` for a quicker pass.
- **`--dividend-report` slower still** — One additional `Ticker` scrape per holding to resolve dividend fields; mega-cap growers with no payout may correctly show zero rows.
