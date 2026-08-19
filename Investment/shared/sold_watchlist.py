"""
Load the Completely_Sold symbol list from the canonical BuySell Excel workbook.

Returns a dict of {SYMBOL: avg_sell_price} for all completely-sold positions,
so AlertApp can monitor them for a re-buy opportunity when the price dips below
a configured % of the average sell price.

The workbook path defaults to C:\\Investment\\reports\\IBKR_BuySell_Since_2020.xlsx
but can be overridden by passing ``workbook_path`` explicitly or by setting
``[rebuy] workbook_path`` in AlertApp/config.ini.

Column layout expected on the Completely_Sold sheet (openpyxl read_only=True):
  Col 0  Symbol
  Col 2  Sell_Qty_Total
  Col 6  Total_Sell_Proceeds
  Col 10 Last_Sold_Price

The average sell price is computed as Total_Sell_Proceeds / Sell_Qty_Total,
which equals the weighted average across all sell trades for that symbol.
If the workbook is missing or unreadable this returns an empty dict (graceful
degradation — the main watchlist still works).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

_DEFAULT_WORKBOOK = (
    Path(__file__).resolve().parents[1] / "reports" / "IBKR_BuySell_Since_2020.xlsx"
)
_SHEET_NAME = "Completely_Sold"

# Column indices (0-based) in the Completely_Sold sheet
_COL_SYMBOL = 0
_COL_SELL_QTY = 2
_COL_SELL_PROCEEDS = 6
_COL_LAST_SOLD_PRICE = 10


def load_sold_watchlist(
    workbook_path: Optional[Path] = None,
    *,
    exclude_symbols: Optional[list[str]] = None,
) -> dict[str, float]:
    """
    Return {SYMBOL: avg_sell_price} for all rows in Completely_Sold.

    Args:
        workbook_path: Path to IBKR_BuySell_Since_2020.xlsx.
                       Defaults to C:\\Investment\\reports\\IBKR_BuySell_Since_2020.xlsx.
        exclude_symbols: Upper-case list of symbols to skip (e.g. delisted tickers).

    Returns:
        Dict mapping symbol string to its average sell price (float).
        Empty dict if the workbook cannot be read.
    """
    path = workbook_path or _DEFAULT_WORKBOOK
    skip = {s.upper() for s in (exclude_symbols or [])}

    if not Path(path).is_file():
        print(
            f"[sold_watchlist] Workbook not found: {path}. "
            "Rebuy watchlist will be empty.",
            flush=True,
        )
        return {}

    try:
        import openpyxl  # imported lazily — not required if feature is disabled
    except ImportError:
        print(
            "[sold_watchlist] openpyxl not installed; rebuy watchlist disabled. "
            "Run: pip install openpyxl",
            flush=True,
        )
        return {}

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        print(f"[sold_watchlist] Cannot open workbook {path}: {exc}", flush=True)
        return {}

    if _SHEET_NAME not in wb.sheetnames:
        print(
            f"[sold_watchlist] Sheet '{_SHEET_NAME}' not found in {path}. "
            f"Available: {wb.sheetnames}",
            flush=True,
        )
        wb.close()
        return {}

    ws = wb[_SHEET_NAME]
    result: dict[str, float] = {}
    first_row = True

    for row in ws.iter_rows(values_only=True):
        if first_row:
            first_row = False
            continue  # skip header

        symbol = row[_COL_SYMBOL]
        sell_qty = row[_COL_SELL_QTY]
        proceeds = row[_COL_SELL_PROCEEDS]

        if not symbol:
            continue
        symbol = str(symbol).strip().upper()
        if symbol in skip:
            continue

        # Compute average sell price
        if sell_qty and proceeds and float(sell_qty) > 0:
            avg_sell = float(proceeds) / float(sell_qty)
        elif row[_COL_LAST_SOLD_PRICE] is not None:
            # Fallback: use last sold price if qty/proceeds are missing
            avg_sell = float(row[_COL_LAST_SOLD_PRICE])
        else:
            continue

        if avg_sell > 0:
            result[symbol] = round(avg_sell, 4)

    wb.close()
    print(
        f"[sold_watchlist] Loaded {len(result)} completely-sold symbols "
        f"from {path.name}.",
        flush=True,
    )
    return result
