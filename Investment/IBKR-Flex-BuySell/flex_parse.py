"""Parse Flex CSV/XML into a normalized Buy/Sell trades DataFrame."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

# Reuse IBKR Activity CSV loader from sibling project
_TRANSACTION_DIR = Path(__file__).resolve().parent.parent / "IBKR-Transaction"
if str(_TRANSACTION_DIR) not in sys.path:
    sys.path.insert(0, str(_TRANSACTION_DIR))

from ibkr_to_excel import coerce_trade_frame, load_ibkr_transaction_csv, parse_flexible_date  # noqa: E402

STANDARD_COLS = [
    "Date",
    "Account",
    "Description",
    "Transaction Type",
    "Symbol",
    "Quantity",
    "Price",
    "Gross Amount",
    "Commission",
    "Net Amount",
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    if "Gross Amount " in out.columns and "Gross Amount" not in out.columns:
        out = out.rename(columns={"Gross Amount ": "Gross Amount"})
    return out


def parse_flex_trades_csv(path: Path) -> pd.DataFrame:
    """IBKR Flex Trades query: AssetClass, Symbol, TradeDate, Quantity, TradePrice, …"""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = _normalize_columns(df)
    if "AssetClass" in df.columns:
        df = df.loc[df["AssetClass"].astype(str).str.upper().eq("STK")].copy()
    col_map = {c.lower().replace("/", "_").replace(" ", "_"): c for c in df.columns}
    side_col = col_map.get("buy_sell") or col_map.get("buy/sell")
    if not side_col:
        raise ValueError(f"Not a Flex Trades CSV (missing Buy/Sell column): {path}")

    def _txn(side: str) -> str:
        s = str(side).strip().upper()
        if s in ("BUY", "B", "BOT"):
            return "Buy"
        if s in ("SELL", "S", "SLD"):
            return "Sell"
        return ""

    out = pd.DataFrame()
    date_col = col_map.get("tradedate") or col_map.get("trade_date") or "TradeDate"
    sym_col = col_map.get("symbol") or "Symbol"
    qty_col = col_map.get("quantity") or "Quantity"
    price_col = col_map.get("tradeprice") or col_map.get("trade_price") or "TradePrice"
    comm_col = col_map.get("ibcommission") or col_map.get("ib_commission")

    out["Date"] = df[date_col].map(
        lambda v: parse_flexible_date(
            f"{str(v)[:4]}-{str(v)[4:6]}-{str(v)[6:8]}" if re.match(r"^\d{8}$", str(v).strip()) else v
        )
    )
    out["Symbol"] = df[sym_col]
    out["Transaction Type"] = df[side_col].map(_txn)
    out["Quantity"] = pd.to_numeric(df[qty_col], errors="coerce").abs()
    out["Price"] = pd.to_numeric(df[price_col], errors="coerce")
    out["Commission"] = pd.to_numeric(df[comm_col], errors="coerce") if comm_col else 0.0
    out["Gross Amount"] = out["Quantity"] * out["Price"]
    out["Net Amount"] = out["Gross Amount"] + out["Commission"]
    out["Description"] = out["Symbol"]
    out["Account"] = ""

    out = out.loc[out["Transaction Type"].isin(["Buy", "Sell"])].copy()
    return coerce_trade_frame(_normalize_columns(out))


def merge_trade_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Combine Flex + Activity CSV trades; dedupe on date/symbol/side/qty/price.

    Net/Gross amounts are intentionally excluded from the key so the same fill
    from Flex (trade currency) and Activity Statement (base currency) collapses
    to one row. Prefers the row whose |Gross| best matches Qty × Price.
    """
    non_empty = [f for f in frames if f is not None and not f.empty]
    if not non_empty:
        return pd.DataFrame()
    merged = pd.concat(non_empty, ignore_index=True)
    merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")

    def _dedupe_key(row: pd.Series) -> tuple:
        dt = row.get("Date")
        day = pd.Timestamp(dt).normalize() if pd.notna(dt) else pd.NaT
        qty = pd.to_numeric(row.get("Quantity"), errors="coerce")
        price = pd.to_numeric(row.get("Price"), errors="coerce")
        return (
            str(day.date()) if pd.notna(day) else "",
            str(row.get("Symbol", "")).strip().upper(),
            str(row.get("Transaction Type", "")).strip(),
            round(abs(float(qty)), 6) if pd.notna(qty) else 0.0,
            round(float(price), 4) if pd.notna(price) else 0.0,
        )

    def _prefer_score(row: pd.Series) -> float:
        """Higher = better keep candidate (trade-currency gross ≈ qty×price)."""
        qty = pd.to_numeric(row.get("Quantity"), errors="coerce")
        price = pd.to_numeric(row.get("Price"), errors="coerce")
        gross = pd.to_numeric(row.get("Gross Amount"), errors="coerce")
        if pd.isna(qty) or pd.isna(price) or abs(float(qty)) < 1e-12:
            return -1e9
        expected = abs(float(qty)) * abs(float(price))
        if expected < 1e-12:
            return -1e9
        g = abs(float(gross)) if pd.notna(gross) else 0.0
        # Perfect match → 0 distance; FX base-currency rows score worse
        distance = abs(g - expected) / expected
        # Slight preference for rows with an account id / richer description
        bonus = 0.0
        acct = str(row.get("Account", "") or "").strip()
        if acct and acct.upper() not in ("NAN", "NONE"):
            bonus += 0.001
        return -distance + bonus

    merged["_dedupe"] = merged.apply(_dedupe_key, axis=1)
    merged["_prefer"] = merged.apply(_prefer_score, axis=1)
    merged = merged.sort_values("_prefer", ascending=False, kind="mergesort")
    merged = merged.drop_duplicates(subset=["_dedupe"], keep="first")
    merged = merged.drop(columns=["_dedupe", "_prefer"])
    return merged.sort_values(["Date", "Symbol"], na_position="last").reset_index(drop=True)


def parse_activity_statement_trades(path: Path) -> pd.DataFrame:
    """
    IBKR Activity Statement multi-section CSV (Statement,Header / Trades,Data)
    → normalized Buy/Sell trade frame.
    """
    import csv

    header: list[str] | None = None
    records: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            if row[0] == "Trades" and row[1] == "Header":
                header = [h.strip() for h in row[2:]]
                continue
            if header is None:
                continue
            if row[0] == "Trades" and row[1] == "Data":
                vals = row[2 : 2 + len(header)]
                if len(vals) < len(header):
                    vals = vals + [""] * (len(header) - len(vals))
                records.append(dict(zip(header, vals)))

    if not records:
        return pd.DataFrame()

    raw = pd.DataFrame.from_records(records)
    if "DataDiscriminator" in raw.columns:
        disc = raw["DataDiscriminator"].astype(str).str.strip()
        raw = raw.loc[disc.isin(["Order", "Trade", ""]) | disc.isna()].copy()
        raw = raw.loc[~disc.loc[raw.index].isin(["ClosedLot", "SubTotal", "Total"])]

    qty = pd.to_numeric(
        raw.get("Quantity", pd.Series(dtype=str))
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("", pd.NA)
        .replace("-", pd.NA),
        errors="coerce",
    )
    price = pd.to_numeric(
        raw.get("T. Price", pd.Series(dtype=str))
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("", pd.NA),
        errors="coerce",
    )
    proceeds = pd.to_numeric(
        raw.get("Proceeds", pd.Series(dtype=str))
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("", pd.NA),
        errors="coerce",
    )
    comm = pd.to_numeric(
        raw.get("Comm/Fee", pd.Series(dtype=str))
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("", pd.NA),
        errors="coerce",
    )
    dates = (
        raw.get("Date/Time", pd.Series(dtype=str))
        .astype(str)
        .str.split(",")
        .str[0]
        .str.strip()
    )

    out = pd.DataFrame()
    out["Date"] = dates.map(parse_flexible_date)
    out["Account"] = ""
    out["Description"] = raw.get("Symbol", "")
    out["Transaction Type"] = qty.map(
        lambda q: "Buy" if pd.notna(q) and float(q) > 0 else ("Sell" if pd.notna(q) and float(q) < 0 else "")
    )
    out["Symbol"] = raw.get("Symbol", "").astype(str).str.strip()
    out["Quantity"] = qty.abs()
    out["Price"] = price
    out["Gross Amount"] = proceeds.abs() if proceeds is not None else out["Quantity"] * out["Price"]
    out["Commission"] = comm.fillna(0.0)
    out["Net Amount"] = proceeds.fillna(out["Quantity"] * out["Price"])
    out = out.loc[out["Transaction Type"].isin(["Buy", "Sell"])].copy()
    return coerce_trade_frame(_normalize_columns(out))


def parse_activity_trades(path: Path) -> pd.DataFrame:
    """IBKR Activity TRANSACTIONS export or Activity Statement → Buy/Sell rows only."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if "Transaction History,Header" in text:
        raw = load_ibkr_transaction_csv(path)
        trades = coerce_trade_frame(raw)
        tt = trades["Transaction Type"].astype(str).str.strip()
        trades = trades.loc[tt.isin(["Buy", "Sell"])].copy()
        return _normalize_columns(trades)
    # Activity Statement (Account Statement style) with Trades section
    if text.lstrip().startswith("Statement,") and "Trades,Header" in text:
        return parse_activity_statement_trades(path)
    if text.startswith("Statement,Header"):
        # Statement without Trades section — try Transaction History path (may fail)
        try:
            raw = load_ibkr_transaction_csv(path)
            trades = coerce_trade_frame(raw)
            tt = trades["Transaction Type"].astype(str).str.strip()
            return _normalize_columns(trades.loc[tt.isin(["Buy", "Sell"])].copy())
        except ValueError:
            return parse_activity_statement_trades(path)
    return parse_flex_trades_csv(path)


def parse_flex_csv_file(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if "Transaction History,Header" in text:
        return parse_activity_trades(path)
    if text.lstrip().startswith("Statement,") and "Trades,Header" in text:
        return parse_activity_statement_trades(path)
    if "Buy/Sell" in text.split("\n", 1)[0] or '"Buy/Sell"' in text:
        return parse_flex_trades_csv(path)
    return parse_activity_trades(path)


def _attr(elem: ET.Element, *keys: str) -> str:
    for k in keys:
        v = elem.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def parse_flex_xml_text(text: str) -> pd.DataFrame:
    root = ET.fromstring(text)
    rows: list[dict[str, str]] = []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag not in ("Trade", "Order", "Execution"):
            continue
        buy_sell = _attr(elem, "buySell", "side", "transactionType").upper()
        if buy_sell in ("B", "BOT", "BUY"):
            txn = "Buy"
        elif buy_sell in ("S", "SLD", "SELL"):
            txn = "Sell"
        else:
            txn_raw = _attr(elem, "buySell", "transactionType")
            if txn_raw.lower() == "buy":
                txn = "Buy"
            elif txn_raw.lower() == "sell":
                txn = "Sell"
            else:
                continue

        date_raw = _attr(elem, "tradeDate", "dateTime", "orderTime", "reportDate")
        symbol = _attr(elem, "symbol", "underlyingSymbol")
        if not symbol or symbol == "-":
            continue

        qty = _attr(elem, "quantity", "tradeQuantity", "qty")
        price = _attr(elem, "tradePrice", "price", "avgPrice")
        desc = _attr(elem, "description", "symbol") or symbol
        acct = _attr(elem, "accountId", "acctId", "account")
        comm = _attr(elem, "ibCommission", "commission")
        net = _attr(elem, "netCash", "amount", "proceeds")
        gross = _attr(elem, "tradeMoney", "gross", "cost")

        rows.append(
            {
                "Date": date_raw,
                "Account": acct,
                "Description": desc,
                "Transaction Type": txn,
                "Symbol": symbol,
                "Quantity": qty,
                "Price": price,
                "Gross Amount": gross,
                "Commission": comm,
                "Net Amount": net,
            }
        )

    if not rows:
        raise ValueError(
            "No Trade/Execution elements in Flex XML. "
            "Configure Flex Query output as Activity CSV or Trades section."
        )

    df = pd.DataFrame(rows)
    return coerce_trade_frame(_normalize_columns(df))


def parse_flex_file(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if text.lstrip().startswith("<"):
        return parse_flex_xml_text(text)
    if "Buy/Sell" in text.split("\n", 1)[0] or '"Buy/Sell"' in text:
        return parse_flex_trades_csv(path)
    if "Transaction History,Header" in text or text.startswith("Statement,Header"):
        return parse_flex_csv_file(path)
    return parse_flex_csv_file(path)


def filter_since_year(df: pd.DataFrame, start_year: int) -> pd.DataFrame:
    out = df.copy()
    if "Date" not in out.columns:
        return out
    out["Date"] = out["Date"].map(parse_flexible_date)
    cutoff = pd.Timestamp(f"{start_year}-01-01")
    return out.loc[out["Date"] >= cutoff].copy()


def add_year_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Date" in out.columns:
        out["Year"] = pd.to_datetime(out["Date"], errors="coerce").dt.year
    return out


def summary_by_year(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Year" not in df.columns:
        return pd.DataFrame()
    tt = df["Transaction Type"].astype(str).str.strip()
    g = df.groupby(["Year", "Transaction Type"], dropna=False).agg(
        Trades=("Symbol", "count"),
        Total_Quantity=("Quantity", lambda s: pd.to_numeric(s, errors="coerce").abs().sum()),
        Total_Net_Amount=("Net Amount", lambda s: pd.to_numeric(s, errors="coerce").sum()),
    )
    return g.reset_index().sort_values(["Year", "Transaction Type"])


def ordered_columns(df: pd.DataFrame) -> list[str]:
    preferred = ["Year", "Date"] + [c for c in STANDARD_COLS if c in df.columns]
    seen: set[str] = set()
    ordered: list[str] = []
    for c in preferred + [c for c in df.columns if c not in preferred]:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def _trade_cash_amount(row: pd.Series) -> float:
    """Negative = cash paid (buy), positive = cash received (sell)."""
    txn = str(row.get("Transaction Type", "")).strip()
    net = pd.to_numeric(row.get("Net Amount"), errors="coerce")
    qty = pd.to_numeric(row.get("Quantity"), errors="coerce")
    price = pd.to_numeric(row.get("Price"), errors="coerce")
    comm = pd.to_numeric(row.get("Commission"), errors="coerce")

    if pd.notna(net) and net != 0:
        if txn == "Buy":
            return -abs(float(net)) if float(net) > 0 else float(net)
        return abs(float(net)) if float(net) < 0 else float(net)

    gross = float(qty * price) if pd.notna(qty) and pd.notna(price) else 0.0
    commission = abs(float(comm)) if pd.notna(comm) else 0.0
    return -(gross + commission) if txn == "Buy" else (gross - commission)


def _signed_quantity(row: pd.Series) -> float:
    txn = str(row.get("Transaction Type", "")).strip()
    qty = pd.to_numeric(row.get("Quantity"), errors="coerce")
    if pd.isna(qty):
        return 0.0
    return float(qty) if txn == "Buy" else -float(abs(qty))


def build_completely_sold_summary(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Stocks fully closed (net quantity ~ 0): total buy cost, sell proceeds, profit, last sell date.
    """
    if trades.empty or "Symbol" not in trades.columns:
        return pd.DataFrame()

    df = trades.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["_sym"] = df["Symbol"].astype(str).str.strip().str.upper()
    df = df.loc[df["_sym"].ne("") & df["_sym"].ne("-")].copy()
    df["_cash"] = df.apply(_trade_cash_amount, axis=1)
    df["_signed_qty"] = df.apply(_signed_quantity, axis=1)
    tt = df["Transaction Type"].astype(str).str.strip()

    rows: list[dict] = []
    for sym, sub in df.groupby("_sym", sort=True):
        net_qty = sub["_signed_qty"].sum()
        if abs(net_qty) > 1e-6:
            continue

        buys = sub.loc[tt.loc[sub.index] == "Buy"]
        sells = sub.loc[tt.loc[sub.index] == "Sell"]
        if buys.empty or sells.empty:
            continue

        buy_qty = buys["_signed_qty"].sum()
        sell_qty = abs(sells["_signed_qty"].sum())
        total_buy_cost = abs(buys.loc[buys["_cash"] < 0, "_cash"].sum())
        if total_buy_cost == 0:
            total_buy_cost = abs(buys["_cash"].sum())
        total_sell_proceeds = sells.loc[sells["_cash"] > 0, "_cash"].sum()
        if total_sell_proceeds == 0:
            total_sell_proceeds = abs(sells["_cash"].sum())

        profit = total_sell_proceeds - total_buy_cost
        profit_pct = (profit / total_buy_cost * 100.0) if total_buy_cost else None
        last_sold = sells["Date"].max()
        sell_qty = abs(sells["Quantity"].sum())
        if pd.notna(sell_qty) and sell_qty > 0:
            weighted_sell_price = abs(sells["Net Amount"].sum()) / sell_qty
        else:
            weighted_sell_price = None
        rows.append(
            {
                "Symbol": sym,
                "Buy_Qty_Total": round(buy_qty, 4),
                "Sell_Qty_Total": round(sell_qty, 4),
                "Buy_Trades": len(buys),
                "Sell_Trades": len(sells),
                "Total_Buy_Cost": round(total_buy_cost, 2),
                "Total_Sell_Proceeds": round(total_sell_proceeds, 2),
                "Profit": round(profit, 2),
                "Profit_Pct": round(profit_pct, 2) if profit_pct is not None else None,
                "Last_Sold_Date": last_sold.date() if pd.notna(last_sold) else None,
                "Last_Sold_Price": round(float(weighted_sell_price), 4) if weighted_sell_price is not None else None,
                "First_Buy_Date": buys["Date"].min().date() if pd.notna(buys["Date"].min()) else None,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Symbol",
                "Buy_Qty_Total",
                "Sell_Qty_Total",
                "Buy_Trades",
                "Sell_Trades",
                "Total_Buy_Cost",
                "Total_Sell_Proceeds",
                "Profit",
                "Profit_Pct",
                "Last_Sold_Date",
                "Last_Sold_Price",
                "First_Buy_Date",
            ]
        )

    out = pd.DataFrame(rows)
    return out.sort_values(["Last_Sold_Date", "Symbol"], ascending=[False, True]).reset_index(drop=True)


def build_still_holding_summary(trades: pd.DataFrame) -> pd.DataFrame:
    """Symbols with net quantity != 0 (open or missing sell data in export)."""
    if trades.empty or "Symbol" not in trades.columns:
        return pd.DataFrame()

    df = trades.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["_sym"] = df["Symbol"].astype(str).str.strip().str.upper()
    df["_signed_qty"] = df.apply(_signed_quantity, axis=1)
    tt = df["Transaction Type"].astype(str).str.strip()

    rows: list[dict] = []
    for sym, sub in df.groupby("_sym", sort=True):
        net_qty = sub["_signed_qty"].sum()
        if abs(net_qty) <= 1e-6:
            continue
        buys = sub.loc[tt.loc[sub.index] == "Buy"]
        sells = sub.loc[tt.loc[sub.index] == "Sell"]
        rows.append(
            {
                "Symbol": sym,
                "Net_Qty": round(net_qty, 4),
                "Buy_Trades": len(buys),
                "Sell_Trades": len(sells),
                "Last_Trade_Date": sub["Date"].max().date() if pd.notna(sub["Date"].max()) else None,
                "Note": (
                    "Has buys but no sells in data — export newer Activity CSV if fully sold"
                    if len(sells) == 0 and len(buys) > 0
                    else "Open position or incomplete trade history"
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("Symbol").reset_index(drop=True)

