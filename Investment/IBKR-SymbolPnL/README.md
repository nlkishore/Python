# IBKR Symbol P&L (from Buy / Sell sheets)

**Canonical dedicated P&L workbook** for per-symbol profit/loss from the Buy/Sell report.

Reads **`C:\Investment\reports\IBKR_BuySell_Since_2020.xlsx`** sheets **Buys** and **Sells**, then builds  
**`C:\Investment\reports\IBKR_Symbol_PnL_From_BuySell.xlsx`**.

Implementation reuses `IBKR-Flex-BuySell\trade_history\symbol_pnl.py` (shared logic).  
For Symbol_PnL embedded in the full trade-history export, see `IBKR_TradeHistory.xlsx` from `python -m trade_history export`.

## Run

```cmd
cd C:\Investment\IBKR-SymbolPnL
python symbol_pnl_from_buysell.py --no-market-prices
```

Or: `run-symbol-pnl.bat`

Optional live marks for open positions (needs `yfinance`):

```cmd
python symbol_pnl_from_buysell.py
```

## Output

`C:\Investment\reports\IBKR_Symbol_PnL_From_BuySell.xlsx`

| Sheet | Content |
|-------|---------|
| `Summary` | Counts + sum of profits / losses |
| `Symbol_PnL` | Every symbol with **Result_Simple** = PROFIT / LOSS / BREAKEVEN / OPEN |
| `Losses` | Closed positions with realized loss |
| `Profits` | Closed positions with realized profit |
| `Still_Open` | Symbols with Open_Qty ≠ 0 |
| `Completely_Sold` | Closed positions detail |
| `Report_Info` | Input path, method, timestamps |

## Method

- Average-cost P&L from Buy + Sell rows
- Applies **SPLIT** / **MERGER** from `IBKR-Transaction` when available (so ATVI / COUP / AMZN etc. are correct)

## After refreshing BuySell

1. Regenerate BuySell: `C:\Investment\regenerate-ibkr-reports.bat --offline`
2. Run this tool: `C:\Investment\IBKR-SymbolPnL\run-symbol-pnl.bat`
