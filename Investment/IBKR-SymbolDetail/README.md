# IBKR Symbol Detail

One row per symbol: **buys**, **sells**, **corporate actions**, **last traded price**, **realized P&L**, **unrealized P&L**.

Uses FIFO lots from `IBKR-BatchPnL` (same corporate-action matching: spinoffs, CUSIP changes, cash+stock mergers, splits). Last price is Yahoo Finance last close.

**Input:** `C:\Investment\reports\IBKR_BuySell_Since_2020.xlsx` plus `IBKR-Transaction` corporate actions.  
**Output:** `C:\Investment\reports\IBKR_Symbol_Detail.xlsx`

## Run

```cmd
cd C:\Investment\IBKR-SymbolDetail
python symbol_detail_report.py
```

Or: `run-symbol-detail.bat`

One symbol (prints a card and still writes Excel filtered to that ticker):

```cmd
python symbol_detail_report.py --symbol NVDA
python symbol_detail_report.py --symbols AAPL,AMZN --no-market-prices
```

| Switch | Effect |
|--------|--------|
| `--symbol` / `--symbols` | Limit to one or more tickers |
| `--no-market-prices` | Skip Yahoo last price (unrealized blank) |
| `--input` / `--output` | Override Excel paths |

Refresh Buy/Sell from IBKR first if you need newer trades:

```cmd
cd C:\Investment\IBKR-BatchPnL
python batch_pnl_report.py --no-market-prices
cd C:\Investment\IBKR-SymbolDetail
python symbol_detail_report.py
```

## Sheets

| Sheet | Content |
|-------|---------|
| `By_Symbol` | Buy/sell qty & averages, open qty, last trade price, realized / unrealized / total P&L, corp-action notes |
| `Buys` | Every buy row |
| `Sells` | Every sell row |
| `Corporate_Actions` | Splits, mergers, spinoffs, CUSIP changes |
| `Timeline` | Buys + sells + corp actions in date order per symbol |
| `Report_Info` | Generated-at, paths |
