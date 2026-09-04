# Canonical IBKR Excel reports

All generated workbooks for IBKR analysis live **here**.

See **[IBKR-REPORTS-GUIDE.md](../IBKR-REPORTS-GUIDE.md)** for download + regenerate steps.

| File | Tool |
|------|------|
| `IBKR_BuySell_Since_2020.xlsx` | `IBKR-Flex-BuySell` |
| `IBKR_TradeHistory.xlsx` | `IBKR-Flex-BuySell` / `trade_history` |
| `IBKR_AccountStatement_P1.xlsx` | `IBKR-Download` |
| `IBKR_Batch_PnL.xlsx` | `IBKR-BatchPnL` (FIFO avg buy/sell + batch matches) |
| `IBKR_Symbol_Detail.xlsx` | `IBKR-SymbolDetail` (per-symbol buys/sells/corp/last price/P&L) |
| `Completely_Sold_Support_Resistance.xlsx` | `completely_sold_support_report.py` |

Regenerate:

```cmd
C:\Investment\regenerate-ibkr-reports.bat
```
