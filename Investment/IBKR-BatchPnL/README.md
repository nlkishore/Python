# IBKR Batch P&L (FIFO)

Per-symbol **average buy / sell** plus a **FIFO batch** sheet that pairs each buy lot with the sell that closed it.

**Default run** refreshes Buy/Sell from IBKR Flex **through today**, then writes  
**`C:\Investment\reports\IBKR_Batch_PnL.xlsx`**.

This is different from `IBKR-SymbolPnL` (average-cost ledger). Here realized P&L is **lot-matched**: the oldest remaining buy is closed first.

Sells with **no matching buy lot** are booked as realized **LOSS** (Buy_Qty/Price = 0, Batch_PnL = −proceeds, −100%) so the report has no unmatched leftover rows.

**Corporate actions:** spinoffs, CUSIP/ticker changes, and cash+stock mergers credit the *surviving* ticker (so LAR / VTRS / TTWO lots match later sells). Splits use the ratio in the IBKR description (`20 for 1`) once per symbol/day. Remaining unmatched sells (no buy *and* no corp receipt) stay LOSS.

## Run

```cmd
cd C:\Investment\IBKR-BatchPnL
python batch_pnl_report.py --no-market-prices
```

Or: `run-batch-pnl.bat --no-market-prices`

That pulls Flex YTD through **today** (if IBKR has the statement; otherwise the latest available prior day), rebuilds `IBKR_BuySell_Since_2020.xlsx`, then runs FIFO.

| Switch | Effect |
|--------|--------|
| *(default)* | Refresh Buy/Sell from IBKR through today, then Batch P&L |
| `--skip-refresh` | Use the existing BuySell Excel (no IBKR call) |
| `--offline` | Rebuild BuySell from local Flex cache + Activity CSV only |
| `--to-date YYYYMMDD` | End date for the Flex YTD window (default: today) |
| `--no-market-prices` | Skip Yahoo marks for open lots |

Optional Yahoo marks for open lots (unrealized P&L):

```cmd
python batch_pnl_report.py
```

## Output sheets

| Sheet | Content |
|-------|---------|
| `Symbol_Summary` | Symbol, Buy_Qty, Avg_Buy_Price, Sell_Qty, Avg_Sell_Price, Open_Qty, Realized_PnL, Unrealized_PnL, Total_PnL |
| `Batch_PnL` | One row per FIFO slice: Buy_Qty / Buy_Price / Buy_Date, Sell_Qty / Sell_Price / Sell_Date, Batch_PnL, Batch_PnL_Pct, Status |
| `Summary` | Counts and totals |
| `Report_Info` | Input path, method, timestamps |

**Batch_PnL Status**

| Status | Meaning |
|--------|---------|
| `MATCHED` | Buy lot (or slice) closed by a later sell |
| `OPEN` | Remaining long lot (Sell_Price = mark if fetched) |
| `LOSS` | Sell with no buy lot — booked as realized loss (−100%) |

Splits and cash mergers from `IBKR-Transaction` are applied in date order (same sources as Symbol P&L).
