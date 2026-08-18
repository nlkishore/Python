"""Build P1 report DataFrames from Account Statement sections."""

from __future__ import annotations

import re

import pandas as pd

from ibkr_download_reports.parser import (
    extract_symbol_from_description,
    parse_date_series,
    to_number,
)


def _source_file_rank(name: object) -> int:
    """Higher = newer / preferred statement file for overlapping periods."""
    s = str(name or "")
    m = re.search(r"_(\d{8})_(\d{8})\.csv$", s, re.I)
    if m:
        return int(m.group(2))
    m = re.search(r"\.(\d{8})\.csv$", s, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"_(\d{4})_(\d{4})\.csv$", s, re.I)
    if m:
        return int(m.group(2)) * 10000 + 1231
    if "YTD" in s.upper():
        return 1
    return 0


def dedupe_statement_rows(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    """Drop overlapping rows from multiple AccountStatement CSVs; keep newest file."""
    if df.empty:
        return df
    present = [c for c in key_cols if c in df.columns]
    if not present:
        return df
    out = df.copy()
    if "_SourceFile" in out.columns:
        out["_src_rank"] = out["_SourceFile"].map(_source_file_rank)
        out = out.sort_values("_src_rank", ascending=False, kind="mergesort")
    out = out.drop_duplicates(subset=present, keep="first")
    if "_src_rank" in out.columns:
        out = out.drop(columns=["_src_rank"])
    return out.reset_index(drop=True)


def report_deposits_withdrawals(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """R01: ledger + summary totals."""
    if raw.empty:
        empty = pd.DataFrame(columns=["Currency", "Settle Date", "Description", "Amount", "_SourceFile"])
        return empty, pd.DataFrame(columns=["Metric", "Currency", "Count", "Total_Amount"])

    df = raw.copy()
    df["Amount"] = to_number(df.get("Amount", pd.Series(dtype=float)))
    df["Settle Date"] = parse_date_series(df.get("Settle Date", pd.Series(dtype=str)))
    df = dedupe_statement_rows(
        df,
        ["Settle Date", "Description", "Amount", "Currency"],
    )

    summary_rows: list[dict] = []
    for currency, sub in df.groupby(df.get("Currency", pd.Series(["UNKNOWN"] * len(df))), dropna=False):
        cur = currency if pd.notna(currency) else "UNKNOWN"
        dep = sub.loc[sub["Amount"] > 0, "Amount"]
        wit = sub.loc[sub["Amount"] < 0, "Amount"]
        summary_rows.append(
            {
                "Metric": "Deposits",
                "Currency": cur,
                "Count": int(dep.count()),
                "Total_Amount": round(float(dep.sum()), 2) if not dep.empty else 0.0,
            }
        )
        summary_rows.append(
            {
                "Metric": "Withdrawals",
                "Currency": cur,
                "Count": int(wit.count()),
                "Total_Amount": round(float(wit.sum()), 2) if not wit.empty else 0.0,
            }
        )
        summary_rows.append(
            {
                "Metric": "Net_Funding",
                "Currency": cur,
                "Count": int(sub["Amount"].count()),
                "Total_Amount": round(float(sub["Amount"].sum()), 2),
            }
        )
    return df, pd.DataFrame(summary_rows)


def _normalize_trades(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    if "DataDiscriminator" in df.columns:
        disc = df["DataDiscriminator"].astype(str).str.strip()
        # Prefer Order rows; also keep Trade if present; skip SubTotal-like / ClosedLot
        df = df.loc[disc.isin(["Order", "Trade", ""]) | disc.isna()].copy()
        if "DataDiscriminator" in df.columns:
            df = df.loc[~disc.loc[df.index].isin(["ClosedLot", "SubTotal", "Total"])]
    df["Quantity"] = to_number(df.get("Quantity", pd.Series(dtype=float)))
    df["T. Price"] = to_number(df.get("T. Price", pd.Series(dtype=float)))
    df["Proceeds"] = to_number(df.get("Proceeds", pd.Series(dtype=float)))
    df["Comm/Fee"] = to_number(df.get("Comm/Fee", pd.Series(dtype=float)))
    df["Date"] = parse_date_series(df.get("Date/Time", pd.Series(dtype=str)))
    df["Symbol"] = df.get("Symbol", pd.Series(dtype=str)).astype(str).str.strip().str.upper()
    df["Side"] = df["Quantity"].map(
        lambda q: "Buy" if pd.notna(q) and q > 0 else ("Sell" if pd.notna(q) and q < 0 else "")
    )
    df["Qty_Abs"] = df["Quantity"].abs()
    df["Commission_Paid"] = df["Comm/Fee"].abs()
    df = df.loc[df["Symbol"].ne("") & df["Symbol"].ne("NAN")].copy()
    # Overlapping YTD/year statement files → one row per fill
    return dedupe_statement_rows(
        df,
        ["Date", "Symbol", "Side", "Qty_Abs", "T. Price"],
    )


def report_trades_and_by_symbol(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """R10/R11: trade blotter, by-symbol buy/sell, commission by symbol."""
    trades = _normalize_trades(raw)
    if trades.empty:
        empty = pd.DataFrame()
        return empty, empty, empty

    by_rows: list[dict] = []
    comm_rows: list[dict] = []
    for sym, sub in trades.groupby("Symbol", sort=True):
        buys = sub.loc[sub["Side"] == "Buy"]
        sells = sub.loc[sub["Side"] == "Sell"]
        by_rows.append(
            {
                "Symbol": sym,
                "Buy_Trades": len(buys),
                "Sell_Trades": len(sells),
                "Buy_Qty": round(float(buys["Qty_Abs"].sum()), 4) if not buys.empty else 0.0,
                "Sell_Qty": round(float(sells["Qty_Abs"].sum()), 4) if not sells.empty else 0.0,
                "Buy_Proceeds": round(float(buys["Proceeds"].sum()), 2) if not buys.empty else 0.0,
                "Sell_Proceeds": round(float(sells["Proceeds"].sum()), 2) if not sells.empty else 0.0,
                "Commission_Paid": round(float(sub["Commission_Paid"].sum()), 2),
            }
        )
        comm_rows.append(
            {
                "Symbol": sym,
                "Trade_Count": len(sub),
                "Commission_Paid": round(float(sub["Commission_Paid"].sum()), 2),
                "Currency": sub["Currency"].iloc[0] if "Currency" in sub.columns else "",
            }
        )

    by_symbol = pd.DataFrame(by_rows)
    commission = pd.DataFrame(comm_rows).sort_values("Commission_Paid", ascending=False)
    cols = [
        c
        for c in [
            "Date",
            "Symbol",
            "Side",
            "Quantity",
            "Qty_Abs",
            "T. Price",
            "Proceeds",
            "Comm/Fee",
            "Commission_Paid",
            "Currency",
            "Asset Category",
            "DataDiscriminator",
            "_SourceFile",
        ]
        if c in trades.columns
    ]
    return trades[cols], by_symbol, commission.reset_index(drop=True)


def report_corporate_actions(raw: pd.DataFrame) -> pd.DataFrame:
    """R20."""
    if raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    df["Date"] = parse_date_series(df.get("Date/Time", df.get("Report Date", pd.Series(dtype=str))))
    df["Quantity"] = to_number(df.get("Quantity", pd.Series(dtype=float)))
    df["Proceeds"] = to_number(df.get("Proceeds", pd.Series(dtype=float)))
    df["Value"] = to_number(df.get("Value", pd.Series(dtype=float)))
    df["Realized P/L"] = to_number(df.get("Realized P/L", pd.Series(dtype=float)))
    desc = df.get("Description", pd.Series(dtype=str)).astype(str)
    df["Symbol"] = desc.map(extract_symbol_from_description)
    return dedupe_statement_rows(
        df,
        ["Date", "Symbol", "Description", "Quantity"],
    )


def report_dividends(raw: pd.DataFrame) -> pd.DataFrame:
    """R21."""
    if raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    df["Date"] = parse_date_series(df.get("Date", pd.Series(dtype=str)))
    df["Amount"] = to_number(df.get("Amount", pd.Series(dtype=float)))
    df["Symbol"] = df.get("Description", pd.Series(dtype=str)).map(extract_symbol_from_description)
    return dedupe_statement_rows(df, ["Date", "Symbol", "Description", "Amount"])


def report_withholding_tax(raw: pd.DataFrame) -> pd.DataFrame:
    """R22 — withholding tax (US Tax on dividends, etc.)."""
    if raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    df["Date"] = parse_date_series(df.get("Date", pd.Series(dtype=str)))
    df["Amount"] = to_number(df.get("Amount", pd.Series(dtype=float)))
    df["Symbol"] = df.get("Description", pd.Series(dtype=str)).map(extract_symbol_from_description)
    df["Tax_Paid"] = df["Amount"].abs()
    return dedupe_statement_rows(df, ["Date", "Symbol", "Description", "Amount"])


def report_interest(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """R30/R31: interest detail + paid vs earned summary."""
    if raw.empty:
        empty = pd.DataFrame()
        return empty, empty
    df = raw.copy()
    df["Date"] = parse_date_series(df.get("Date", pd.Series(dtype=str)))
    df["Amount"] = to_number(df.get("Amount", pd.Series(dtype=float)))
    desc = df.get("Description", pd.Series(dtype=str)).astype(str).str.lower()
    # Debit / paid to IBKR: negative amount or debit wording
    paid_mask = (df["Amount"] < 0) | desc.str.contains(
        "debit interest|interest paid|on borrowings|borrow", regex=True, na=False
    )
    earned_mask = (df["Amount"] > 0) & ~paid_mask
    df["Interest_Kind"] = "Other"
    df.loc[paid_mask, "Interest_Kind"] = "Paid_To_IBKR"
    df.loc[earned_mask, "Interest_Kind"] = "Earned_Credit"
    df = dedupe_statement_rows(df, ["Date", "Description", "Amount", "Currency"])

    summary_rows: list[dict] = []
    for currency, sub in df.groupby(df.get("Currency", pd.Series(["UNKNOWN"] * len(df))), dropna=False):
        cur = currency if pd.notna(currency) else "UNKNOWN"
        paid = sub.loc[sub["Interest_Kind"] == "Paid_To_IBKR", "Amount"]
        earned = sub.loc[sub["Interest_Kind"] == "Earned_Credit", "Amount"]
        summary_rows.append(
            {
                "Currency": cur,
                "Interest_Paid_To_IBKR": round(float(paid.sum()), 2) if not paid.empty else 0.0,
                "Interest_Earned": round(float(earned.sum()), 2) if not earned.empty else 0.0,
                "Net_Interest": round(float(sub["Amount"].sum()), 2),
                "Paid_Rows": int(paid.count()),
                "Earned_Rows": int(earned.count()),
            }
        )
    return df, pd.DataFrame(summary_rows)


def withholding_by_symbol(wt: pd.DataFrame) -> pd.DataFrame:
    if wt.empty or "Symbol" not in wt.columns:
        return pd.DataFrame(columns=["Symbol", "Tax_Paid", "Rows"])
    g = (
        wt.dropna(subset=["Symbol"])
        .groupby("Symbol", dropna=False)
        .agg(Tax_Paid=("Tax_Paid", "sum"), Rows=("Tax_Paid", "count"))
        .reset_index()
    )
    g["Tax_Paid"] = g["Tax_Paid"].round(2)
    return g.sort_values("Tax_Paid", ascending=False).reset_index(drop=True)


def dividends_net_of_tax(div: pd.DataFrame, wt: pd.DataFrame) -> pd.DataFrame:
    """Per-symbol dividends vs withholding tax."""
    cols = ["Symbol", "Dividends", "Withholding_Tax", "Net_Dividend"]
    if (div.empty or "Symbol" not in div.columns) and (wt.empty or "Symbol" not in wt.columns):
        return pd.DataFrame(columns=cols)

    pieces: list[pd.Series] = []
    if not div.empty and "Symbol" in div.columns:
        pieces.append(
            div.dropna(subset=["Symbol"]).groupby("Symbol")["Amount"].sum().rename("Dividends")
        )
    if not wt.empty and "Symbol" in wt.columns:
        pieces.append(
            wt.dropna(subset=["Symbol"]).groupby("Symbol")["Tax_Paid"].sum().rename("Withholding_Tax")
        )
    out = pd.concat(pieces, axis=1).fillna(0.0).reset_index()
    if "Symbol" not in out.columns and "index" in out.columns:
        out = out.rename(columns={"index": "Symbol"})
    if "Dividends" not in out.columns:
        out["Dividends"] = 0.0
    if "Withholding_Tax" not in out.columns:
        out["Withholding_Tax"] = 0.0
    out["Net_Dividend"] = (out["Dividends"] - out["Withholding_Tax"]).round(2)
    out["Dividends"] = out["Dividends"].round(2)
    out["Withholding_Tax"] = out["Withholding_Tax"].round(2)
    return out.sort_values("Dividends", ascending=False).reset_index(drop=True)[cols]
