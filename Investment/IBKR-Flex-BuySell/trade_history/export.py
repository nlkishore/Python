"""Excel export for trade history analysis workbook."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from flex_parse import (
    add_year_column,
    build_completely_sold_summary,
    build_still_holding_summary,
    ordered_columns,
)
from market_prices import enrich_completely_sold_with_market_prices
from trade_history.symbol_pnl import (
    build_by_symbol_trades,
    build_symbol_pnl,
    completely_sold_from_symbol_pnl,
    still_holding_from_symbol_pnl,
)


def write_trade_history_workbook(
    trades: pd.DataFrame,
    corporate: pd.DataFrame,
    output: Path,
    *,
    mode: str,
    source_label: str,
    account_open_date: str,
    watermark_date: str | None,
    fetch_market_prices: bool = True,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    trades_out = add_year_column(trades.copy()) if not trades.empty else trades
    cols = ordered_columns(trades_out) if not trades_out.empty else []
    if cols:
        trades_out = trades_out[cols]

    tt = (
        trades_out["Transaction Type"].astype(str).str.strip()
        if not trades_out.empty and "Transaction Type" in trades_out.columns
        else pd.Series(dtype=str)
    )
    buys = trades_out.loc[tt == "Buy"].copy() if not trades_out.empty else pd.DataFrame()
    sells = trades_out.loc[tt == "Sell"].copy() if not trades_out.empty else pd.DataFrame()
    by_symbol = build_by_symbol_trades(trades)
    symbol_pnl = build_symbol_pnl(trades, corporate, fetch_marks=fetch_market_prices)
    # Prefer corporate-aware open qty (mergers/splits) over trade-only Completely_Sold
    closed = completely_sold_from_symbol_pnl(symbol_pnl)
    still_holding = still_holding_from_symbol_pnl(symbol_pnl)
    if closed.empty:
        closed = build_completely_sold_summary(trades)
    if still_holding.empty:
        still_holding = build_still_holding_summary(trades)
    if fetch_market_prices and not closed.empty:
        try:
            closed = enrich_completely_sold_with_market_prices(closed)
        except ImportError as exc:
            print(f"Warning: {exc}")

    corp_out = corporate.copy() if corporate is not None else pd.DataFrame()
    if corp_out.empty:
        corp_out = pd.DataFrame(
            [
                {
                    "Note": (
                        "No corporate actions/dividends found. "
                        "Ensure IBKR Activity DIVIDEND CSV or Flex Query includes dividends/corporate actions."
                    )
                }
            ]
        )

    meta = pd.DataFrame(
        [
            {"Field": "Mode", "Value": mode},
            {"Field": "Source", "Value": source_label},
            {"Field": "Account open date", "Value": account_open_date},
            {"Field": "Watermark", "Value": watermark_date or "n/a"},
            {"Field": "Generated at", "Value": datetime.now().isoformat(timespec="seconds")},
            {"Field": "Total trades", "Value": str(len(trades))},
            {"Field": "Buy rows", "Value": str(len(buys))},
            {"Field": "Sell rows", "Value": str(len(sells))},
            {
                "Field": "Corporate/dividend rows",
                "Value": str(
                    len(corporate) if corporate is not None and not corporate.empty else 0
                ),
            },
            {"Field": "Symbol_PnL rows", "Value": str(len(symbol_pnl))},
            {"Field": "Completely sold symbols", "Value": str(len(closed))},
            {
                "Field": "Date range",
                "Value": (
                    f"{trades['Date'].min()} – {trades['Date'].max()}"
                    if not trades.empty and "Date" in trades.columns
                    else "n/a"
                ),
            },
        ]
    )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        meta.to_excel(writer, sheet_name="Report_Info", index=False)
        trades_out.to_excel(writer, sheet_name="Trades_All", index=False)
        buys.to_excel(writer, sheet_name="Buys", index=False)
        sells.to_excel(writer, sheet_name="Sells", index=False)
        corp_out.to_excel(writer, sheet_name="Corporate_Actions", index=False)
        by_symbol.to_excel(writer, sheet_name="By_Symbol_Trades", index=False)
        symbol_pnl.to_excel(writer, sheet_name="Symbol_PnL", index=False)
        closed.to_excel(writer, sheet_name="Completely_Sold", index=False)
        if not still_holding.empty:
            still_holding.to_excel(writer, sheet_name="Still_Holding", index=False)

    print(f"Wrote {output}")
    print(
        f"  Trades={len(trades)} | Symbol_PnL={len(symbol_pnl)} | "
        f"Corporate={0 if corporate is None or corporate.empty else len(corporate)} | "
        f"Completely_Sold={len(closed)}"
    )
