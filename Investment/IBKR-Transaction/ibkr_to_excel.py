"""
Build Excel from IBKR Activity / TRANSACTIONS / Activity Statement CSV(s).

Supports:
  - Single Transaction History export (*.TRANSACTIONS*.csv)
  - Split BUY_SELL + sibling CSVs
  - Activity Statement multi-section CSVs under Latest/ (U*_YYYY_YYYY.csv, U*_YYYYMMDD_YYYYMMDD.csv)
    — --discover merges ALL of these (not just one file)

Usage:
  python ibkr_to_excel.py
  python ibkr_to_excel.py --input "C:\\...\\U3831357.TRANSACTIONS....csv"
  python ibkr_to_excel.py --discover --dir "C:\\Investment\\IBKR-Transaction"
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TRANSACTIONS_CSV = SCRIPT_DIR / "Latest" / "U3831357.TRANSACTIONS.20200218.20260320.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "IBKR_Summary.xlsx"

# Excel 1900 date system (epoch used by IBKR serials in some deposit exports)
_EXCEL_EPOCH = datetime(1899, 12, 30)

_DIV_USD_PER_SHARE = re.compile(r"USD\s+([\d.]+)\s+per\s+Share", re.IGNORECASE)
_SYMBOL_IN_DESC = re.compile(
    r"^([A-Z][A-Z0-9.\-]{0,11})\s*\([A-Z0-9]+\)",
    re.IGNORECASE,
)


def excel_serial_to_datetime(value: Any) -> datetime | pd.Timestamp | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s or s == "-":
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    if n < 20000 or n > 60000:  # plausible serial range only
        return None
    return _EXCEL_EPOCH + timedelta(days=n)


def parse_flexible_date(val: Any) -> pd.Timestamp | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    dt = excel_serial_to_datetime(s)
    if dt is not None:
        return pd.Timestamp(dt)
    # IBKR: YYYY-MM-DD in trade/dividend files; d/m/y in some other reports
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        try:
            return pd.to_datetime(s, errors="raise")
        except (ValueError, TypeError):
            pass
    for dayfirst in (True, False):
        try:
            return pd.to_datetime(s, dayfirst=dayfirst, errors="raise")
        except (ValueError, TypeError):
            continue
    return pd.NaT


def _norm_header(name: str) -> str:
    return name.strip().replace("  ", " ")


def load_ibkr_transaction_csv(path: Path) -> pd.DataFrame:
    """Load rows after Transaction History,Header; supports Data rows and deposit-style rows."""
    header: list[str] | None = None
    records: list[dict[str, str]] = []

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0] == "Transaction History" and row[1] == "Header":
                header = [_norm_header(h) for h in row[2:]]
                continue
            if header is None:
                continue

            if len(row) >= 2 and row[0] == "Transaction History" and row[1] == "Data":
                vals = row[2 : 2 + len(header)]
                if len(vals) < len(header):
                    vals = vals + [""] * (len(header) - len(vals))
                records.append(dict(zip(header, vals)))
                continue

            # Deposit/withdrawal export: leading empty cells, same column count as header
            if (
                len(row) >= len(header) + 2
                and (not row[0] or row[0].strip() == "")
                and (not row[1] or row[1].strip() == "")
            ):
                vals = row[2 : 2 + len(header)]
                if len(vals) < len(header):
                    vals = vals + [""] * (len(header) - len(vals))
                records.append(dict(zip(header, vals)))

    if not header:
        raise ValueError(f"No Transaction History header found in {path}")
    return pd.DataFrame.from_records(records)


def coerce_trade_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Date" in out.columns:
        out["Date"] = out["Date"].map(parse_flexible_date)
    for col in ("Quantity", "Price", "Gross Amount", "Commission", "Net Amount"):
        if col not in out.columns:
            continue
        out[col] = (
            out[col]
            .replace("-", "")
            .replace("", pd.NA)
            .apply(lambda x: pd.to_numeric(x, errors="coerce") if pd.notna(x) else pd.NA)
        )
    return out


def safe_sheet_name(name: str, max_len: int = 31) -> str:
    bad = r'[]:*?/\\'
    s = "".join("_" if c in bad else c for c in name)
    s = s.strip() or "Sheet"
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


def _classify_ibkr_csv(path: Path, out: dict[str, Path]) -> None:
    u = path.stem.upper()
    if ".DIVIDEND." in u:
        out["DIVIDEND"] = path
    elif ".DEPOSIT_WITHDRAWAL." in u:
        out["DEPOSIT_WITHDRAWAL"] = path
    elif ".OTHERCHARGES." in u:
        out["OTHERCHARGES"] = path
    elif ".CREDIT_DEBIT" in u:
        out["CREDIT_DEBIT"] = path


def _file_end_date(p: Path) -> int:
    """Parse end date from filename for newest-first sorting."""
    name = p.name
    m = re.search(r"\.(\d{8})\.csv$", name, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"_(\d{8})_(\d{8})\.csv$", name, re.I)
    if m:
        return int(m.group(2))
    m = re.search(r"_(\d{4})_(\d{4})\.csv$", name, re.I)
    if m:
        return int(m.group(2)) * 10000 + 1231  # year file → Dec 31 of that year
    m = re.search(r"_(\d{8})\.csv$", name, re.I)
    if m:
        return int(m.group(1))
    return 0


def is_activity_statement_csv(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8-sig", errors="replace") as f:
            head = f.read(120)
        return head.lstrip().startswith("Statement,")
    except OSError:
        return False


def load_statement_section(path: Path, section: str) -> pd.DataFrame:
    """Load Data rows for a named Activity Statement section."""
    header: list[str] | None = None
    records: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            if row[0] == section and row[1] == "Header":
                header = [_norm_header(h) for h in row[2:]]
                continue
            if header is None:
                continue
            if row[0] == section and row[1] == "Data":
                vals = row[2 : 2 + len(header)]
                if len(vals) < len(header):
                    vals = vals + [""] * (len(header) - len(vals))
                records.append(dict(zip(header, vals)))
    return pd.DataFrame.from_records(records) if records else pd.DataFrame()


def _symbol_from_description(description: str) -> str:
    if not description:
        return ""
    m = _SYMBOL_IN_DESC.match(str(description).strip())
    if m:
        return m.group(1).upper()
    tok = str(description).strip().split()[0] if str(description).strip() else ""
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9.\-]{0,11}", tok):
        return tok.upper()
    return ""


def activity_statement_trades_to_frame(path: Path) -> pd.DataFrame:
    """Activity Statement Trades section → Transaction-History-like Buy/Sell frame."""
    raw = load_statement_section(path, "Trades")
    if raw.empty:
        return pd.DataFrame()
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
        lambda q: "Buy"
        if pd.notna(q) and float(q) > 0
        else ("Sell" if pd.notna(q) and float(q) < 0 else "")
    )
    out["Symbol"] = raw.get("Symbol", "").astype(str).str.strip()
    out["Quantity"] = qty  # keep signed for sells
    out["Price"] = price
    out["Gross Amount"] = proceeds
    out["Commission"] = comm.fillna(0.0)
    out["Net Amount"] = proceeds
    out["Price Currency"] = raw.get("Currency", "")
    out = out.loc[out["Transaction Type"].isin(["Buy", "Sell"])].copy()
    out["_SourceFile"] = path.name
    return coerce_trade_frame(out)


def activity_statement_dividends_to_frame(path: Path) -> pd.DataFrame:
    raw = load_statement_section(path, "Dividends")
    if raw.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for _, r in raw.iterrows():
        desc = str(r.get("Description", "") or "")
        cur = str(r.get("Currency", "") or "")
        if not desc or cur.upper().startswith("TOTAL"):
            continue
        amt = pd.to_numeric(str(r.get("Amount", "")).replace(",", ""), errors="coerce")
        rows.append(
            {
                "Date": parse_flexible_date(r.get("Date")),
                "Account": "",
                "Description": desc,
                "Transaction Type": "Dividend",
                "Symbol": _symbol_from_description(desc),
                "Quantity": None,
                "Price": None,
                "Gross Amount": float(amt) if pd.notna(amt) else None,
                "Commission": 0.0,
                "Net Amount": float(amt) if pd.notna(amt) else None,
                "Price Currency": cur,
                "_SourceFile": path.name,
            }
        )
    return coerce_trade_frame(pd.DataFrame(rows)) if rows else pd.DataFrame()


def activity_statement_deposits_to_frame(path: Path) -> pd.DataFrame:
    raw = load_statement_section(path, "Deposits & Withdrawals")
    if raw.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for _, r in raw.iterrows():
        desc = str(r.get("Description", "") or "")
        amt = pd.to_numeric(str(r.get("Amount", "")).replace(",", ""), errors="coerce")
        if pd.isna(amt):
            continue
        rows.append(
            {
                "Date": parse_flexible_date(r.get("Settle Date") or r.get("Date")),
                "Account": "",
                "Description": desc,
                "Transaction Type": "Deposit" if float(amt) > 0 else "Withdrawal",
                "Symbol": "",
                "Quantity": None,
                "Price": None,
                "Gross Amount": float(amt),
                "Commission": 0.0,
                "Net Amount": float(amt),
                "Price Currency": str(r.get("Currency", "") or ""),
                "_SourceFile": path.name,
            }
        )
    return coerce_trade_frame(pd.DataFrame(rows)) if rows else pd.DataFrame()


def activity_statement_interest_to_frame(path: Path) -> pd.DataFrame:
    raw = load_statement_section(path, "Interest")
    if raw.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for _, r in raw.iterrows():
        desc = str(r.get("Description", "") or "")
        amt = pd.to_numeric(str(r.get("Amount", "")).replace(",", ""), errors="coerce")
        if not desc or pd.isna(amt):
            continue
        tt = "Credit Interest" if float(amt) > 0 else "Debit Interest"
        rows.append(
            {
                "Date": parse_flexible_date(r.get("Date")),
                "Account": "",
                "Description": desc,
                "Transaction Type": tt,
                "Symbol": "",
                "Quantity": None,
                "Price": None,
                "Gross Amount": float(amt),
                "Commission": 0.0,
                "Net Amount": float(amt),
                "Price Currency": str(r.get("Currency", "") or ""),
                "_SourceFile": path.name,
            }
        )
    return coerce_trade_frame(pd.DataFrame(rows)) if rows else pd.DataFrame()


def activity_statement_corporate_to_frame(path: Path) -> pd.DataFrame:
    raw = load_statement_section(path, "Corporate Actions")
    if raw.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for _, r in raw.iterrows():
        desc = str(r.get("Description", "") or "")
        if not desc:
            continue
        qty = pd.to_numeric(str(r.get("Quantity", "")).replace(",", ""), errors="coerce")
        proceeds = pd.to_numeric(str(r.get("Proceeds", "")).replace(",", ""), errors="coerce")
        rows.append(
            {
                "Date": parse_flexible_date(
                    r.get("Report Date") or r.get("Date/Time") or r.get("Date")
                ),
                "Account": "",
                "Description": desc,
                "Transaction Type": "Corporate Action",
                "Symbol": str(r.get("Symbol", "") or "").strip() or _symbol_from_description(desc),
                "Quantity": float(qty) if pd.notna(qty) else None,
                "Price": None,
                "Gross Amount": float(proceeds) if pd.notna(proceeds) else None,
                "Commission": 0.0,
                "Net Amount": float(proceeds) if pd.notna(proceeds) else None,
                "Price Currency": str(r.get("Currency", "") or ""),
                "_SourceFile": path.name,
            }
        )
    return coerce_trade_frame(pd.DataFrame(rows)) if rows else pd.DataFrame()


def _dedupe_trade_like(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    out = df.copy()
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce")

    def _key(row: pd.Series) -> tuple:
        dt = row.get("Date")
        day = pd.Timestamp(dt).normalize() if pd.notna(dt) else pd.NaT
        qty = pd.to_numeric(row.get("Quantity"), errors="coerce")
        price = pd.to_numeric(row.get("Price"), errors="coerce")
        net = pd.to_numeric(row.get("Net Amount"), errors="coerce")
        return (
            str(day.date()) if pd.notna(day) else "",
            str(row.get("Symbol", "")).strip().upper(),
            str(row.get("Transaction Type", "")).strip(),
            round(float(qty), 6) if pd.notna(qty) else 0.0,
            round(float(price), 4) if pd.notna(price) else 0.0,
            round(float(net), 4) if pd.notna(net) else 0.0,
            str(row.get("Description", ""))[:60],
        )

    out["_k"] = out.apply(_key, axis=1)
    # Prefer rows from newer source files when overlapping
    if "_SourceFile" in out.columns:
        out["_rank"] = out["_SourceFile"].map(lambda n: _file_end_date(Path(str(n))))
        out = out.sort_values("_rank", ascending=False, kind="mergesort")
    out = out.drop_duplicates(subset=["_k"], keep="first")
    drop_cols = [c for c in ("_k", "_rank") if c in out.columns]
    return out.drop(columns=drop_cols).reset_index(drop=True)


def discover_activity_statement_csvs(directory: Path) -> list[Path]:
    """All Activity Statement CSVs under directory (newest end-date first)."""
    directory = directory.resolve()
    candidates: list[Path] = []
    for pattern in ("U*_*.csv", "*Activity*.csv"):
        candidates.extend(directory.rglob(pattern))
    filtered: list[Path] = []
    for p in candidates:
        if not p.name.lower().endswith(".csv"):
            continue
        upper = p.name.upper()
        if any(
            x in upper
            for x in (
                ".TRANSACTIONS.",
                ".BUY_SELL.",
                ".DIVIDEND.",
                ".DEPOSIT_",
                ".OTHERCHARGES.",
                ".CREDIT_DEBIT",
            )
        ):
            continue
        if is_activity_statement_csv(p):
            filtered.append(p)
    return sorted(
        set(filtered),
        key=lambda p: (_file_end_date(p), p.stat().st_mtime),
        reverse=True,
    )


def load_merged_activity_statements(paths: list[Path]) -> dict[str, pd.DataFrame]:
    """Merge yearly/YTD Activity Statement CSVs into trade-like frames."""
    trades_f: list[pd.DataFrame] = []
    div_f: list[pd.DataFrame] = []
    dep_f: list[pd.DataFrame] = []
    int_f: list[pd.DataFrame] = []
    corp_f: list[pd.DataFrame] = []
    for path in paths:
        try:
            t = activity_statement_trades_to_frame(path)
            if not t.empty:
                trades_f.append(t)
            d = activity_statement_dividends_to_frame(path)
            if not d.empty:
                div_f.append(d)
            dep = activity_statement_deposits_to_frame(path)
            if not dep.empty:
                dep_f.append(dep)
            i = activity_statement_interest_to_frame(path)
            if not i.empty:
                int_f.append(i)
            c = activity_statement_corporate_to_frame(path)
            if not c.empty:
                corp_f.append(c)
        except (ValueError, OSError) as exc:
            print(f"Warning: skip {path.name}: {exc}")

    def _cat(frames: list[pd.DataFrame]) -> pd.DataFrame:
        if not frames:
            return pd.DataFrame()
        return _dedupe_trade_like(pd.concat(frames, ignore_index=True))

    return {
        "trades": _cat(trades_f),
        "dividends": _cat(div_f),
        "deposits": _cat(dep_f),
        "interest": _cat(int_f),
        "corporate": _cat(corp_f),
    }


def collect_split_files(latest: Path) -> dict[str, Path]:
    """Attach DIVIDEND / DEPOSIT / OTHER / CREDIT_DEBIT siblings next to a BUY_SELL export."""
    out: dict[str, Path] = {"BUY_SELL": latest.resolve()}
    parent = latest.parent

    m = re.match(
        r"^(?P<acct>[^.]+)\.BUY_SELL\.(?P<start>\d{8})\.(?P<end>\d{8})\.csv$",
        latest.name,
        re.I,
    )
    if m:
        acct, start, end = m.group("acct"), m.group("start"), m.group("end")
        paths = list(parent.glob(f"{acct}.*.{start}.{end}.csv"))
    else:
        acct = latest.name.split(".")[0]
        paths = list(parent.glob(f"{acct}.*.csv"))

    for p in paths:
        _classify_ibkr_csv(p, out)
    return out


def find_report_files(directory: Path) -> dict[str, Any]:
    """
    Prefer merging all Activity Statement CSVs under Latest/ (or anywhere under dir).
    Else newest full TRANSACTIONS export; else BUY_SELL + siblings.
    """
    directory = directory.resolve()
    statements = discover_activity_statement_csvs(directory)
    # Prefer statements that live under Latest\ when present
    latest_dir = directory / "Latest"
    latest_stmts = [p for p in statements if latest_dir in p.parents or p.parent == latest_dir]
    if latest_stmts:
        return {"ACTIVITY_STATEMENTS": latest_stmts}
    if statements:
        return {"ACTIVITY_STATEMENTS": statements}

    transactions = list(directory.rglob("*.TRANSACTIONS*.csv"))
    buy_sells = list(directory.rglob("*.BUY_SELL*.csv"))

    def sort_key(p: Path) -> tuple[int, float]:
        return (_file_end_date(p), p.stat().st_mtime)

    best_t = max(transactions, key=sort_key) if transactions else None
    best_b = max(buy_sells, key=sort_key) if buy_sells else None

    if not best_t and not best_b:
        raise FileNotFoundError(
            f"No Activity Statement (U*_*.csv), *.TRANSACTIONS*.csv, or *.BUY_SELL*.csv under {directory}"
        )

    if best_t and best_b:
        end_t, end_b = sort_key(best_t)[0], sort_key(best_b)[0]
        if end_t >= end_b:
            return {"TRANSACTIONS": best_t}
    elif best_t:
        return {"TRANSACTIONS": best_t}

    latest = best_b
    assert latest is not None
    return collect_split_files(latest)


def _parse_statement_period(path: Path) -> str | None:
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if len(row) >= 4 and row[0] == "Statement" and row[1] == "Data" and row[2] == "Period":
                    return row[3].strip().strip('"')
    except OSError:
        return None
    return None


def _signed_trade_quantity(row: pd.Series) -> float:
    q = pd.to_numeric(row.get("Quantity"), errors="coerce")
    if pd.isna(q):
        return 0.0
    tt = str(row.get("Transaction Type", "")).strip().lower()
    if tt == "sell":
        return -abs(float(q))
    if tt == "buy":
        return abs(float(q))
    return float(q)


def computed_positions_from_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Net share balance from Buy/Sell only (see Corporate_Actions sheet for gaps)."""
    empty = pd.DataFrame(columns=["Symbol", "Net_Qty_From_Buy_Sell", "Buy_Lots", "Sell_Lots"])
    if trades.empty or "Symbol" not in trades.columns:
        return empty

    tt = trades["Transaction Type"].astype(str).str.strip()
    sub = trades.loc[tt.isin(["Buy", "Sell"])].copy()
    sub["_sk"] = sub["Symbol"].astype(str).str.strip()
    sub = sub[(sub["_sk"].notna()) & (sub["_sk"] != "") & (sub["_sk"] != "-")]
    if sub.empty:
        return empty

    sub["_signed"] = sub.apply(_signed_trade_quantity, axis=1)
    tt2 = sub["Transaction Type"].astype(str).str.strip()
    net = sub.groupby("_sk", dropna=False)["_signed"].sum().rename("Net_Qty_From_Buy_Sell")
    buy_lots = sub[tt2 == "Buy"].groupby("_sk").size().rename("Buy_Lots")
    sell_lots = sub[tt2 == "Sell"].groupby("_sk").size().rename("Sell_Lots")
    out = (
        net.to_frame()
        .join(buy_lots, how="left")
        .join(sell_lots, how="left")
        .reset_index()
        .rename(columns={"_sk": "Symbol"})
    )
    out["Buy_Lots"] = out["Buy_Lots"].fillna(0).astype(int)
    out["Sell_Lots"] = out["Sell_Lots"].fillna(0).astype(int)
    return out.sort_values("Symbol").reset_index(drop=True)


def dividend_implied_shares_latest(dividends: pd.DataFrame) -> pd.DataFrame:
    """
    For each symbol, use the most recent *Ordinary Dividend* row and parse
    'USD x.xx per Share' from Description; Implied_Shares ≈ Gross Amount / rate.
    Aligns better with Portfolio when Buy/Sell lines in the file are incomplete.
    """
    cols = ["Symbol", "As_Of_Date", "Gross_Amount", "USD_Per_Share", "Implied_Shares", "Description"]
    if dividends.empty or "Symbol" not in dividends.columns:
        return pd.DataFrame(columns=cols)
    d = dividends.copy()
    d = d[d["Transaction Type"].astype(str).str.strip().str.lower() == "dividend"]
    if "Description" not in d.columns:
        return pd.DataFrame(columns=cols)
    d = d[d["Description"].astype(str).str.contains("Ordinary Dividend", case=False, na=False)]
    d = d[~d["Description"].astype(str).str.contains("Payment in Lieu", case=False, na=False)]
    rows: list[dict[str, Any]] = []
    sk = d["Symbol"].astype(str).str.strip()
    for sym in sk.unique():
        if not sym or sym == "-":
            continue
        grp = d.loc[sk == sym].sort_values("Date", ascending=False)
        if grp.empty:
            continue
        row = grp.iloc[0]
        dtext = str(row["Description"])
        m = _DIV_USD_PER_SHARE.search(dtext)
        if not m:
            continue
        rate = float(m.group(1))
        if rate <= 0:
            continue
        gross = pd.to_numeric(row.get("Gross Amount"), errors="coerce")
        if pd.isna(gross) or gross <= 0:
            continue
        implied = float(gross) / rate
        rows.append(
            {
                "Symbol": sym,
                "As_Of_Date": row["Date"],
                "Gross_Amount": float(gross),
                "USD_Per_Share": rate,
                "Implied_Shares": implied,
                "Description": dtext[:220],
            }
        )
    return pd.DataFrame(rows).sort_values("Symbol").reset_index(drop=True)


def corporate_action_qty_by_symbol(corp: pd.DataFrame) -> pd.DataFrame:
    """
    Sum Quantity on Corporate Action rows per symbol (splits sometimes populate Quantity;
    cash mergers often leave '-' so sum stays 0 and All_Quantities_Numeric is False).
    """
    cols = ["Symbol", "Corporate_Action_Qty_Sum", "Corporate_Action_Rows", "All_Corp_Qty_Numeric"]
    if corp.empty or "Symbol" not in corp.columns:
        return pd.DataFrame(columns=cols)
    c = corp.copy()
    sk = c["Symbol"].astype(str).str.strip()
    c = c.loc[sk.notna() & (sk != "") & (sk != "-")]
    if c.empty:
        return pd.DataFrame(columns=cols)
    q = pd.to_numeric(c["Quantity"], errors="coerce") if "Quantity" in c.columns else pd.Series(
        pd.NA, index=c.index, dtype="float"
    )
    g = c.assign(_q=q, _sk=sk.loc[c.index]).groupby("_sk", dropna=False)

    def _all_numeric(s: pd.Series) -> bool:
        return bool(s.notna().all()) if len(s) else True

    out = g.agg(
        Corporate_Action_Qty_Sum=("_q", "sum"),
        Corporate_Action_Rows=("Symbol", "count"),
        All_Corp_Qty_Numeric=("_q", _all_numeric),
    ).reset_index()
    out = out.rename(columns={"_sk": "Symbol"})
    return out


def position_reconciliation(
    positions: pd.DataFrame,
    implied: pd.DataFrame,
    corp_qty: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Outer-join trade-net, optional corporate-action qty sum, and dividend-implied shares."""
    col_order = [
        "Symbol",
        "Net_Qty_Buy_Sell_In_This_File",
        "Corporate_Action_Qty_Sum",
        "Corporate_Action_Rows",
        "All_Corp_Qty_Numeric",
        "Est_Net_Trades_Plus_CorpQty",
        "Buy_Lots",
        "Sell_Lots",
        "Latest_Div_Date",
        "Implied_Shares_From_Latest_Div",
        "USD_Per_Share",
        "Gross_Amount",
        "Gap_Implied_minus_TradeNet",
        "Gap_Implied_minus_EstNet",
        "Note",
    ]
    p = (
        positions.rename(columns={"Net_Qty_From_Buy_Sell": "Net_Qty_Buy_Sell_In_This_File"}).copy()
        if not positions.empty
        else pd.DataFrame(columns=["Symbol", "Net_Qty_Buy_Sell_In_This_File", "Buy_Lots", "Sell_Lots"])
    )
    im = (
        implied[["Symbol", "As_Of_Date", "Implied_Shares", "USD_Per_Share", "Gross_Amount"]]
        .rename(
            columns={
                "As_Of_Date": "Latest_Div_Date",
                "Implied_Shares": "Implied_Shares_From_Latest_Div",
            }
        )
        .copy()
        if not implied.empty
        else pd.DataFrame(
            columns=["Symbol", "Latest_Div_Date", "Implied_Shares_From_Latest_Div", "USD_Per_Share", "Gross_Amount"]
        )
    )
    if p.empty and im.empty:
        return pd.DataFrame(columns=col_order)

    if p.empty:
        merged = im.copy()
        merged["Net_Qty_Buy_Sell_In_This_File"] = 0.0
        merged["Buy_Lots"] = 0
        merged["Sell_Lots"] = 0
    elif im.empty:
        merged = p.copy()
        merged["Latest_Div_Date"] = pd.NaT
        merged["Implied_Shares_From_Latest_Div"] = pd.NA
        merged["USD_Per_Share"] = pd.NA
        merged["Gross_Amount"] = pd.NA
    else:
        merged = p.merge(im, on="Symbol", how="outer")

    merged["Net_Qty_Buy_Sell_In_This_File"] = pd.to_numeric(
        merged["Net_Qty_Buy_Sell_In_This_File"], errors="coerce"
    ).fillna(0)
    merged["Implied_Shares_From_Latest_Div"] = pd.to_numeric(
        merged["Implied_Shares_From_Latest_Div"], errors="coerce"
    )

    if corp_qty is not None and not corp_qty.empty:
        merged = merged.merge(corp_qty, on="Symbol", how="outer")
    if "Corporate_Action_Qty_Sum" not in merged.columns:
        merged["Corporate_Action_Qty_Sum"] = 0.0
        merged["Corporate_Action_Rows"] = 0
        merged["All_Corp_Qty_Numeric"] = True
    merged["Corporate_Action_Qty_Sum"] = pd.to_numeric(
        merged["Corporate_Action_Qty_Sum"], errors="coerce"
    ).fillna(0)
    merged["Corporate_Action_Rows"] = pd.to_numeric(
        merged["Corporate_Action_Rows"], errors="coerce"
    ).fillna(0).astype(int)
    merged["All_Corp_Qty_Numeric"] = merged["All_Corp_Qty_Numeric"].astype("boolean").fillna(True).astype(bool)

    # Outer merge with corp_qty can add symbols with no trade/div rows; fill missing trade fields
    merged["Net_Qty_Buy_Sell_In_This_File"] = pd.to_numeric(
        merged["Net_Qty_Buy_Sell_In_This_File"], errors="coerce"
    ).fillna(0)
    for _c in ("Buy_Lots", "Sell_Lots"):
        if _c not in merged.columns:
            merged[_c] = 0
        merged[_c] = pd.to_numeric(merged[_c], errors="coerce").fillna(0).astype(int)
    merged["Gap_Implied_minus_TradeNet"] = merged["Implied_Shares_From_Latest_Div"] - merged[
        "Net_Qty_Buy_Sell_In_This_File"
    ]

    merged["Est_Net_Trades_Plus_CorpQty"] = (
        merged["Net_Qty_Buy_Sell_In_This_File"] + merged["Corporate_Action_Qty_Sum"]
    )
    merged["Gap_Implied_minus_EstNet"] = (
        merged["Implied_Shares_From_Latest_Div"] - merged["Est_Net_Trades_Plus_CorpQty"]
    )

    def _note(r: pd.Series) -> str:
        imp = r.get("Implied_Shares_From_Latest_Div")
        net = float(r.get("Net_Qty_Buy_Sell_In_This_File") or 0)
        rows = int(r.get("Corporate_Action_Rows") or 0)
        all_corp = bool(r.get("All_Corp_Qty_Numeric"))
        caq = float(r.get("Corporate_Action_Qty_Sum") or 0)
        parts: list[str] = []
        if rows > 0 and not all_corp:
            parts.append(
                "Corporate Action rows exist but Quantity is '-' in CSV — "
                "cash mergers / many splits are not auto-adjusted; use IBKR Positions or manual."
            )
        elif rows > 0 and all_corp and caq != 0:
            parts.append("Corporate_Action_Qty_Sum included in Est_Net_Trades_Plus_CorpQty.")
        if pd.isna(imp):
            parts.append("No parsable ordinary dividend in file; use trade / corp estimate only.")
        elif net == 0 and rows == 0:
            parts.append("No Buy/Sell net in file; Implied_Shares reflects latest ordinary dividend payment.")
        elif not pd.isna(imp) and abs(float(imp) - net) > 0.05:
            parts.append(
                "Buy/Sell net alone does not match dividend (older lots / transfers / pre-report / corp actions)."
            )
        elif not pd.isna(imp):
            est = r.get("Est_Net_Trades_Plus_CorpQty")
            if not pd.isna(est) and abs(float(imp) - float(est)) <= 0.05:
                parts.append("Implied dividend ~ matches Est_Net_Trades_Plus_CorpQty.")
            elif not pd.isna(est) and abs(float(imp) - float(est)) > 0.05:
                parts.append("Implied dividend still differs from Est_Net — opening lots or unmodeled events.")
            else:
                parts.append("Trade net matches dividend-implied (approx).")
        return " ".join(parts) if parts else "OK."

    merged["Note"] = merged.apply(_note, axis=1)
    for c in ("Buy_Lots", "Sell_Lots"):
        if c not in merged.columns:
            merged[c] = 0
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0).astype(int)

    for c in col_order:
        if c not in merged.columns:
            merged[c] = pd.NA
    return merged[col_order].sort_values("Symbol").reset_index(drop=True)


_OTHER_TYPES_FROM_FULL = (
    "Foreign Tax Withholding",
    "Other Fee",
    "Payment in Lieu",
    "Adjustment",
    "Forex Trade Component",
    "Cancel",
)


def write_excel(
    files: dict[str, Any],
    output: Path,
    max_symbol_sheets: int = 60,
) -> None:
    corporate_actions = pd.DataFrame()
    other = pd.DataFrame()
    statement_period = None
    source_label = ""

    if "ACTIVITY_STATEMENTS" in files:
        paths: list[Path] = list(files["ACTIVITY_STATEMENTS"])
        merged = load_merged_activity_statements(paths)
        trades = merged["trades"]
        dividends = merged["dividends"]
        deposits = merged["deposits"]
        interest = merged["interest"]
        corporate_actions = merged["corporate"]
        data_source = paths[0] if paths else SCRIPT_DIR
        statement_period = _parse_statement_period(paths[0]) if paths else None
        names = ", ".join(p.name for p in paths[:8])
        if len(paths) > 8:
            names += f" … (+{len(paths) - 8})"
        source_label = f"Activity Statements ({len(paths)} files): {names}"
        print(f"Using {source_label}")
    else:
        data_source = files.get("TRANSACTIONS") or files["BUY_SELL"]
        statement_period = _parse_statement_period(data_source)
        source_label = str(data_source)

        if "TRANSACTIONS" in files:
            primary = coerce_trade_frame(load_ibkr_transaction_csv(files["TRANSACTIONS"]))
            p_tt = primary["Transaction Type"].astype(str).str.strip()
            trades = primary.loc[p_tt.isin(["Buy", "Sell"])].copy()
            dividends = primary.loc[p_tt.str.lower() == "dividend"].copy()
            deposits = primary.loc[p_tt.isin(["Deposit", "Withdrawal"])].copy()
            interest = primary.loc[p_tt.isin(["Credit Interest", "Debit Interest"])].copy()
            corporate_actions = primary.loc[p_tt == "Corporate Action"].copy()
            other = primary.loc[p_tt.isin(list(_OTHER_TYPES_FROM_FULL))].copy()
        else:
            trades = coerce_trade_frame(load_ibkr_transaction_csv(files["BUY_SELL"]))
            tt0 = trades["Transaction Type"].astype(str).str.strip()
            trades = trades.loc[tt0.isin(["Buy", "Sell"])].copy()

            dividends = pd.DataFrame()
            if "DIVIDEND" in files:
                dividends = coerce_trade_frame(load_ibkr_transaction_csv(files["DIVIDEND"]))
                div_mask = dividends["Transaction Type"].astype(str).str.strip().str.lower() == "dividend"
                dividends = dividends[div_mask]

            deposits = pd.DataFrame()
            if "DEPOSIT_WITHDRAWAL" in files:
                deposits = coerce_trade_frame(load_ibkr_transaction_csv(files["DEPOSIT_WITHDRAWAL"]))

            other = pd.DataFrame()
            if "OTHERCHARGES" in files:
                other = coerce_trade_frame(load_ibkr_transaction_csv(files["OTHERCHARGES"]))

            interest = pd.DataFrame()
            if "CREDIT_DEBIT" in files:
                interest = coerce_trade_frame(load_ibkr_transaction_csv(files["CREDIT_DEBIT"]))

    if trades.empty:
        raise ValueError(f"No Buy/Sell trades found from sources: {source_label}")

    tt = trades["Transaction Type"].astype(str).str.strip()
    buys = trades[tt == "Buy"].copy()
    sells = trades[tt == "Sell"].copy()

    cols_order = [
        c
        for c in (
            "Date",
            "Transaction Type",
            "Symbol",
            "Description",
            "Quantity",
            "Price",
            "Price Currency",
            "Gross Amount",
            "Commission",
            "Net Amount",
            "Account",
        )
        if c in trades.columns
    ]
    buys_out = buys[cols_order] if cols_order else buys
    sells_out = sells[cols_order] if cols_order else sells

    trade_comm = pd.to_numeric(trades["Commission"], errors="coerce").fillna(0)
    sym_key = trades["Symbol"].astype(str).str.strip()

    def _agg_side(mask: pd.Series) -> pd.DataFrame:
        sub = trades.loc[mask].copy()
        if sub.empty:
            return pd.DataFrame(columns=["Symbol", "Trades", "Qty_Sum", "Commission_Sum", "Net_Sum"])
        sk = sub["Symbol"].astype(str).str.strip()
        q = pd.to_numeric(sub["Quantity"], errors="coerce").fillna(0)
        c = pd.to_numeric(sub["Commission"], errors="coerce").fillna(0)
        n = pd.to_numeric(sub["Net Amount"], errors="coerce").fillna(0)
        g = sub.assign(_q=q, _c=c, _n=n, _sk=sk).groupby("_sk", dropna=False)
        out = g.agg(Trades=("Symbol", "count"), Qty_Sum=("_q", "sum"), Commission_Sum=("_c", "sum"), Net_Sum=("_n", "sum"))
        return out.reset_index().rename(columns={"_sk": "Symbol"}).sort_values("Symbol")

    buy_summary_by_sym = _agg_side(tt == "Buy")
    sell_summary_by_sym = _agg_side(tt == "Sell")
    if not sell_summary_by_sym.empty and "Qty_Sum" in sell_summary_by_sym.columns:
        sell_summary_by_sym = sell_summary_by_sym.copy()
        # IBKR stores sells as negative quantity; this is total shares sold per symbol
        sell_summary_by_sym["Qty_Abs_Sum"] = sell_summary_by_sym["Qty_Sum"].abs()

    comm_by_symbol = (
        trades.assign(_c=trade_comm, _sk=sym_key)
        .groupby("_sk", dropna=False)["_c"]
        .sum()
        .reset_index()
        .rename(columns={"_sk": "Symbol", "_c": "Commission_Sum"})
    )

    positions_df = computed_positions_from_trades(trades)
    div_implied_df = dividend_implied_shares_latest(dividends)
    corp_qty_df = corporate_action_qty_by_symbol(corporate_actions)
    position_recon_df = position_reconciliation(
        positions_df,
        div_implied_df,
        corp_qty_df if not corp_qty_df.empty else None,
    )

    # Totals
    total_deposits = 0.0
    total_withdrawals_abs = 0.0
    if not deposits.empty and "Transaction Type" in deposits.columns and "Net Amount" in deposits.columns:
        d = deposits.copy()
        t = d["Transaction Type"].astype(str).str.strip().str.lower()
        net = pd.to_numeric(d["Net Amount"], errors="coerce").fillna(0)
        total_deposits = float(net[t == "deposit"].sum())
        # Withdrawals are negative in IBKR exports; show positive total withdrawn
        w = float(net[t == "withdrawal"].sum())
        total_withdrawals_abs = abs(w) if w != 0 else 0.0

    div_total = 0.0
    if not dividends.empty and "Net Amount" in dividends.columns:
        div_total = float(pd.to_numeric(dividends["Net Amount"], errors="coerce").fillna(0).sum())

    trade_comm_total = float(trade_comm.sum())
    trade_comm_paid = float(-trade_comm.sum())  # positive = cost when commissions are negative

    other_fees_total = 0.0
    wh_total = 0.0
    if not other.empty and "Net Amount" in other.columns:
        net_o = pd.to_numeric(other["Net Amount"], errors="coerce").fillna(0)
        other_fees_total = float(net_o.sum())
        if "Transaction Type" in other.columns:
            ot = other["Transaction Type"].astype(str).str.strip().str.lower()
            wh_total = float(net_o[ot == "foreign tax withholding"].sum())

    credit_int = debit_int = 0.0
    if not interest.empty and "Transaction Type" in interest.columns and "Net Amount" in interest.columns:
        ni = pd.to_numeric(interest["Net Amount"], errors="coerce").fillna(0)
        it = interest["Transaction Type"].astype(str).str.strip().str.lower()
        credit_int = float(ni[it == "credit interest"].sum())
        debit_int = float(ni[it == "debit interest"].sum())

    if "ACTIVITY_STATEMENTS" in files:
        paths = list(files["ACTIVITY_STATEMENTS"])
        mode_label = f"Merged Activity Statements ({len(paths)} CSV files under Latest/dir)"
        primary_name = "; ".join(p.name for p in paths[:5]) + (" …" if len(paths) > 5 else "")
        primary_folder = str(paths[0].parent.resolve()) if paths else str(SCRIPT_DIR)
    elif "TRANSACTIONS" in files:
        mode_label = "Full TRANSACTIONS CSV"
        primary_name = Path(data_source).name
        primary_folder = str(Path(data_source).parent.resolve())
    else:
        mode_label = "Split exports (BUY_SELL + siblings)"
        primary_name = Path(data_source).name
        primary_folder = str(Path(data_source).parent.resolve())

    summary_rows = [
        ("Data mode", mode_label),
        ("Primary CSV", primary_name),
        ("Source folder", primary_folder),
        ("Statement period (from CSV preamble)", statement_period or "(not found / multi-file)"),
        (
            "Portfolio vs this file",
            "IBKR Portfolio quantity often matches 'Implied_Shares_From_Latest_Div' on sheet "
            "Position_Reconciliation, not Net_Qty_Buy_Sell_In_This_File — Activity CSVs often omit "
            "older purchases that still appear on dividend lines.",
        ),
        (
            "Example AAPL in this CSV",
            "Buy/Sell net in file = 7 shares (3 buys, 1 sell); latest ordinary dividend implies ~44 "
            "shares on the pay date. If your Portfolio shows 35, that is between those two views — "
            "confirm date and account on IBKR; this workbook cannot invent missing Buy rows.",
        ),
        (
            "Negative net quantity",
            "If a symbol shows negative Net_Qty but IBKR Portfolio is flat, you likely sold more than "
            "this file shows as purchased (opening lot outside the report window or ACATS).",
        ),
        ("Corporate Action rows in this file", int(len(corporate_actions)) if not corporate_actions.empty else 0),
        (
            "Reconciliation columns",
            "Position_Reconciliation: Est_Net_Trades_Plus_CorpQty = Buy/Sell net + sum(Corporate Action Quantity). "
            "If Quantity is '-' (common for cash mergers), that sum is 0 — cannot match Portfolio without "
            "IBKR Positions export or manual split/merger math.",
        ),
        ("Total Deposits (Net Amount, Deposit rows)", total_deposits),
        ("Total Withdrawals (absolute, Withdrawal rows)", total_withdrawals_abs),
        ("Net Funding (Deposits - Withdrawals)", total_deposits - total_withdrawals_abs),
        ("Dividends received (sum Net Amount)", div_total),
        ("Trade commissions (sum as in CSV)", trade_comm_total),
        ("Trade commissions (as positive cost, -sum)", trade_comm_paid),
        ("Other charges / adjustments (sum Net Amount)", other_fees_total),
        ("  of which Foreign Tax Withholding (if typed)", wh_total),
        ("Credit interest (sum)", credit_int),
        ("Debit interest (sum)", debit_int),
        ("Net interest (credit + debit)", credit_int + debit_int),
    ]
    summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])

    div_by_sym = pd.DataFrame()
    if not dividends.empty and "Symbol" in dividends.columns:
        div_by_sym = (
            dividends.assign(
                _n=pd.to_numeric(dividends["Net Amount"], errors="coerce").fillna(0)
            )
            .groupby(dividends["Symbol"].astype(str).str.strip(), dropna=False)["_n"]
            .sum()
            .reset_index()
            .rename(columns={"Symbol": "Symbol", "_n": "Dividend_Net_Total"})
            .sort_values("Dividend_Net_Total", ascending=False)
        )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        positions_df.to_excel(writer, sheet_name="Computed_Positions", index=False)
        if not div_implied_df.empty:
            div_implied_df.to_excel(writer, sheet_name="Dividend_Implied_Shares", index=False)
        position_recon_df.to_excel(writer, sheet_name="Position_Reconciliation", index=False)
        if not corporate_actions.empty:
            corporate_actions.to_excel(writer, sheet_name="Corporate_Actions", index=False)
        buys_out.to_excel(writer, sheet_name="All_Buys", index=False)
        sells_out.to_excel(writer, sheet_name="All_Sells", index=False)
        buy_summary_by_sym.to_excel(writer, sheet_name="Buy_Summary_By_Symbol", index=False)
        sell_summary_by_sym.to_excel(writer, sheet_name="Sell_Summary_By_Symbol", index=False)
        comm_by_symbol.to_excel(writer, sheet_name="Commission_By_Symbol", index=False)

        if not dividends.empty:
            dividends.to_excel(writer, sheet_name="Dividends_Detail", index=False)
        if not div_by_sym.empty:
            div_by_sym.to_excel(writer, sheet_name="Dividends_By_Symbol", index=False)

        if not deposits.empty:
            deposits.to_excel(writer, sheet_name="Deposits_Withdrawals", index=False)

        if not other.empty:
            other.to_excel(writer, sheet_name="Other_Charges", index=False)

        if not interest.empty:
            interest.to_excel(writer, sheet_name="Credit_Debit_Interest", index=False)

        sym_from_trades = {
            str(s).strip()
            for s in trades["Symbol"].dropna().unique()
            if str(s).strip() and str(s).strip() != "-"
        }
        sym_from_implied = set(div_implied_df["Symbol"].astype(str).str.strip()) if not div_implied_df.empty else set()
        symbols = sorted(sym_from_trades | sym_from_implied)
        n = 0
        for sym in symbols:
            if n >= max_symbol_sheets:
                break
            sub = trades[trades["Symbol"].astype(str).str.strip() == sym]
            sub = sub[cols_order] if cols_order else sub
            sheet = safe_sheet_name(f"S_{sym}")
            sub.to_excel(writer, sheet_name=sheet, index=False)
            n += 1

    print(f"Wrote {output} ({n} symbol sheets, max {max_symbol_sheets})")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="IBKR Activity Statement / TRANSACTIONS CSV(s) -> Excel workbook"
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_TRANSACTIONS_CSV,
        help="Single TRANSACTIONS / Activity Statement CSV (default path may be stale)",
    )
    ap.add_argument(
        "--dir",
        type=Path,
        default=SCRIPT_DIR,
        help="With --discover: folder to search (includes Latest\\ Activity Statements)",
    )
    ap.add_argument("--output", type=Path, default=None, help="Output .xlsx path")
    ap.add_argument("--buy-sell", type=Path, default=None, help="Legacy: split exports next to this BUY_SELL file")
    ap.add_argument("--max-symbol-sheets", type=int, default=60)
    ap.add_argument(
        "--transactions",
        type=Path,
        default=None,
        help="Same as --input (backward compatible)",
    )
    ap.add_argument(
        "--discover",
        action="store_true",
        help=(
            "Auto-pick sources under --dir: merge all Activity Statement CSVs in Latest\\ "
            "(U*_*.csv), else newest TRANSACTIONS, else BUY_SELL+siblings"
        ),
    )
    args = ap.parse_args()

    if args.discover:
        files = find_report_files(args.dir.resolve())
    elif args.transactions is not None:
        path = args.transactions.resolve()
        files = (
            {"ACTIVITY_STATEMENTS": [path]}
            if is_activity_statement_csv(path)
            else {"TRANSACTIONS": path}
        )
    elif args.buy_sell:
        files = collect_split_files(args.buy_sell.resolve())
    else:
        csv_path = args.input.resolve()
        if not csv_path.is_file():
            # Fall back to discover Latest Activity Statements when default TRANSACTIONS missing
            latest = SCRIPT_DIR / "Latest"
            if latest.is_dir() and discover_activity_statement_csvs(latest):
                print(f"Default input missing ({csv_path}); discovering under {latest}")
                files = find_report_files(SCRIPT_DIR)
            else:
                raise SystemExit(f"Input CSV not found: {csv_path}")
        elif is_activity_statement_csv(csv_path):
            files = {"ACTIVITY_STATEMENTS": [csv_path]}
        else:
            files = {"TRANSACTIONS": csv_path}

    out = args.output or DEFAULT_OUTPUT
    write_excel(files, out, max_symbol_sheets=args.max_symbol_sheets)


if __name__ == "__main__":
    main()
