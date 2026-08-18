"""Parse corporate actions and dividends from Activity / Flex exports."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pandas as pd

_TRANSACTION_DIR = Path(__file__).resolve().parent.parent.parent / "IBKR-Transaction"
if str(_TRANSACTION_DIR) not in sys.path:
    sys.path.insert(0, str(_TRANSACTION_DIR))

from ibkr_to_excel import (  # noqa: E402
    coerce_trade_frame,
    collect_split_files,
    load_ibkr_transaction_csv,
)

_SYMBOL_IN_DESC = re.compile(
    r"^([A-Z][A-Z0-9.\-]{0,11})\s*\([A-Z0-9]+\)",
    re.IGNORECASE,
)

CORPORATE_COLS = [
    "Date",
    "Symbol",
    "ActionType",
    "Quantity",
    "Amount",
    "Description",
    "Account",
    "Source",
    "SourceFile",
]


def _normalize_action_type(raw: str, description: str = "") -> str:
    t = (raw or "").strip().upper()
    d = (description or "").upper()
    if t in ("DIVIDEND", "DIV"):
        return "DIVIDEND"
    if t in ("CORPORATE ACTION", "CORP ACTION", "CORPORATE_ACTION"):
        if "SPLIT" in d:
            return "SPLIT"
        if "MERGER" in d or "ACQUISITION" in d:
            return "MERGER"
        if "SPIN" in d:
            return "SPINOFF"
        if "RIGHT" in d:
            return "RIGHTS"
        if "DIVIDEND" in d:
            return "DIVIDEND"
        return "CORPORATE_ACTION"
    if "DIVIDEND" in d and t in ("", "OTHER", "PAYMENT IN LIEU"):
        return "DIVIDEND"
    if t:
        return t.replace(" ", "_")
    return "OTHER"


def _rows_from_activity_frame(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    if df.empty or "Transaction Type" not in df.columns:
        return pd.DataFrame(columns=CORPORATE_COLS)
    tt = df["Transaction Type"].astype(str).str.strip()
    mask = tt.str.lower().isin(
        {
            "dividend",
            "corporate action",
            "payment in lieu of dividend",
        }
    )
    # Also catch description-based dividends if typed oddly
    if "Description" in df.columns:
        mask = mask | df["Description"].astype(str).str.contains(
            "Ordinary Dividend|Cash Dividend|Stock Split|Corporate Action",
            case=False,
            na=False,
        )
    sub = df.loc[mask].copy()
    if sub.empty:
        return pd.DataFrame(columns=CORPORATE_COLS)

    rows: list[dict] = []
    for _, r in sub.iterrows():
        desc = str(r.get("Description", "") or "")
        raw_tt = str(r.get("Transaction Type", "") or "")
        amt = pd.to_numeric(r.get("Net Amount"), errors="coerce")
        if pd.isna(amt):
            amt = pd.to_numeric(r.get("Gross Amount"), errors="coerce")
        qty = pd.to_numeric(r.get("Quantity"), errors="coerce")
        rows.append(
            {
                "Date": r.get("Date"),
                "Symbol": str(r.get("Symbol", "") or "").strip().upper(),
                "ActionType": _normalize_action_type(raw_tt, desc),
                "Quantity": float(qty) if pd.notna(qty) else None,
                "Amount": float(amt) if pd.notna(amt) else None,
                "Description": desc,
                "Account": str(r.get("Account", "") or ""),
                "Source": "activity",
                "SourceFile": source_file,
            }
        )
    out = pd.DataFrame(rows)
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out = out.loc[out["Symbol"].ne("") & out["Symbol"].ne("-")].copy()
    return out.reset_index(drop=True)


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


def _load_statement_section(path: Path, section: str) -> pd.DataFrame:
    header: list[str] | None = None
    records: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            if row[0] == section and row[1] == "Header":
                header = [h.strip() for h in row[2:]]
                continue
            if header is None:
                continue
            if row[0] == section and row[1] == "Data":
                vals = row[2 : 2 + len(header)]
                if len(vals) < len(header):
                    vals = vals + [""] * (len(header) - len(vals))
                records.append(dict(zip(header, vals)))
    return pd.DataFrame.from_records(records) if records else pd.DataFrame()


def load_corporate_from_activity_statement(path: Path) -> pd.DataFrame:
    """Dividends / Withholding Tax / Corporate Actions from Activity Statement CSV."""
    rows: list[dict] = []
    source = path.name

    div = _load_statement_section(path, "Dividends")
    if not div.empty:
        for _, r in div.iterrows():
            desc = str(r.get("Description", "") or "")
            if not desc or str(r.get("Currency", "")).upper().startswith("TOTAL"):
                continue
            amt = pd.to_numeric(
                str(r.get("Amount", "")).replace(",", ""), errors="coerce"
            )
            rows.append(
                {
                    "Date": r.get("Date"),
                    "Symbol": _symbol_from_description(desc),
                    "ActionType": "DIVIDEND",
                    "Quantity": None,
                    "Amount": float(amt) if pd.notna(amt) else None,
                    "Description": desc,
                    "Account": "",
                    "Source": "activity_statement",
                    "SourceFile": source,
                }
            )

    wt = _load_statement_section(path, "Withholding Tax")
    if not wt.empty:
        for _, r in wt.iterrows():
            desc = str(r.get("Description", "") or "")
            if not desc or str(r.get("Currency", "")).upper().startswith("TOTAL"):
                continue
            amt = pd.to_numeric(
                str(r.get("Amount", "")).replace(",", ""), errors="coerce"
            )
            rows.append(
                {
                    "Date": r.get("Date"),
                    "Symbol": _symbol_from_description(desc),
                    "ActionType": "FOREIGN_TAX_WITHHOLDING",
                    "Quantity": None,
                    "Amount": float(amt) if pd.notna(amt) else None,
                    "Description": desc,
                    "Account": "",
                    "Source": "activity_statement",
                    "SourceFile": source,
                }
            )

    corp = _load_statement_section(path, "Corporate Actions")
    if not corp.empty:
        for _, r in corp.iterrows():
            desc = str(r.get("Description", "") or "")
            if not desc:
                continue
            date_val = r.get("Report Date") or r.get("Date/Time") or r.get("Date")
            amt = pd.to_numeric(
                str(r.get("Proceeds", "") or r.get("Value", "")).replace(",", ""),
                errors="coerce",
            )
            qty = pd.to_numeric(
                str(r.get("Quantity", "")).replace(",", ""), errors="coerce"
            )
            sym = str(r.get("Symbol", "") or "").strip().upper()
            if not sym:
                sym = _symbol_from_description(desc)
            rows.append(
                {
                    "Date": date_val,
                    "Symbol": sym,
                    "ActionType": _normalize_action_type("CORPORATE ACTION", desc),
                    "Quantity": float(qty) if pd.notna(qty) else None,
                    "Amount": float(amt) if pd.notna(amt) else None,
                    "Description": desc,
                    "Account": "",
                    "Source": "activity_statement",
                    "SourceFile": source,
                }
            )

    if not rows:
        return pd.DataFrame(columns=CORPORATE_COLS)
    out = pd.DataFrame(rows)
    out["Date"] = pd.to_datetime(
        out["Date"].astype(str).str.split(",").str[0].str.strip(), errors="coerce"
    )
    out = out.loc[out["Symbol"].ne("") & out["Symbol"].ne("-")].copy()
    return out.reset_index(drop=True)


def load_corporate_from_activity_file(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if "Transaction History,Header" in text:
        raw = load_ibkr_transaction_csv(path)
        df = coerce_trade_frame(raw)
        return _rows_from_activity_frame(df, path.name)
    if text.lstrip().startswith("Statement,") and (
        "Dividends,Header" in text
        or "Withholding Tax,Header" in text
        or "Corporate Actions,Header" in text
    ):
        return load_corporate_from_activity_statement(path)
    # Fallback: try Transaction History loader, else statement sections
    try:
        raw = load_ibkr_transaction_csv(path)
        df = coerce_trade_frame(raw)
        return _rows_from_activity_frame(df, path.name)
    except ValueError:
        return load_corporate_from_activity_statement(path)


def load_corporate_from_transactions_dir(transactions_dir: Path) -> pd.DataFrame:
    """Load dividends / corporate actions from BUY_SELL, TRANSACTIONS, DIVIDEND siblings."""
    if not transactions_dir.is_dir():
        return pd.DataFrame(columns=CORPORATE_COLS)

    frames: list[pd.DataFrame] = []
    patterns = (
        "*.TRANSACTIONS*.csv",
        "*.BUY_SELL*.csv",
        "*.DIVIDEND*.csv",
        "*DIVIDEND*.csv",
        "U*_*.csv",  # Activity Statement e.g. U3831357_20260101_20260805.csv
    )
    seen: set[Path] = set()
    for pattern in patterns:
        for path in transactions_dir.rglob(pattern):
            resolved = path.resolve()
            if resolved in seen:
                continue
            upper = path.name.upper()
            if any(
                x in upper
                for x in (
                    ".DEPOSIT_",
                    ".OTHERCHARGES.",
                    ".CREDIT_DEBIT",
                )
            ):
                continue
            seen.add(resolved)
            try:
                frames.append(load_corporate_from_activity_file(path))
            except (ValueError, OSError) as exc:
                print(f"Warning: skip corporate parse {path.name}: {exc}")

    # Also attach sibling split files for newest BUY_SELL
    buy_sells = list(transactions_dir.rglob("*.BUY_SELL*.csv"))
    if buy_sells:
        latest = max(buy_sells, key=lambda p: p.stat().st_mtime)
        try:
            splits = collect_split_files(latest)
            for key, path in splits.items():
                if key == "BUY_SELL":
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                try:
                    frames.append(load_corporate_from_activity_file(path))
                except (ValueError, OSError):
                    pass
        except Exception:
            pass

    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame(columns=CORPORATE_COLS)
    merged = pd.concat(frames, ignore_index=True)
    # light dedupe (Amount omitted so FX copies collapse)
    merged["_k"] = (
        merged["Date"].astype(str)
        + "|"
        + merged["Symbol"].astype(str)
        + "|"
        + merged["ActionType"].astype(str)
        + "|"
        + merged["Description"].astype(str).str[:80]
    )
    merged = merged.drop_duplicates(subset=["_k"], keep="last").drop(columns=["_k"])
    return merged.sort_values(["Date", "Symbol"], na_position="last").reset_index(drop=True)


def parse_flex_corporate_csv(path: Path) -> pd.DataFrame:
    """
    Best-effort Flex CSV with Corporate Actions / Cash Transactions sections.
    Falls back to scanning for Dividend / Corporate Action columns.
    """
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    # Multi-section Activity / Activity Statement
    if "Transaction History,Header" in text or text.lstrip().startswith("Statement,"):
        return load_corporate_from_activity_file(path)

    # Single-table Flex with Type / Code columns
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=CORPORATE_COLS)
    df.columns = [str(c).strip() for c in df.columns]
    type_col = None
    for cand in ("Type", "Transaction Type", "Code", "ActionType", "CorpActionType"):
        if cand in df.columns:
            type_col = cand
            break
    if type_col is None:
        return pd.DataFrame(columns=CORPORATE_COLS)

    tt = df[type_col].astype(str)
    mask = tt.str.contains("Dividend|Corporate|Split|Merger", case=False, na=False)
    sub = df.loc[mask].copy()
    if sub.empty:
        return pd.DataFrame(columns=CORPORATE_COLS)

    # Map loosely to standard activity shape
    rename = {}
    for a, b in (
        ("TradeDate", "Date"),
        ("Date/Time", "Date"),
        ("ReportDate", "Date"),
        ("ExDate", "Date"),
        ("Quantity", "Quantity"),
        ("Amount", "Net Amount"),
        ("Proceeds", "Net Amount"),
        ("Cash", "Net Amount"),
        ("Description", "Description"),
        ("Symbol", "Symbol"),
    ):
        if a in sub.columns and b not in sub.columns:
            rename[a] = b
    sub = sub.rename(columns=rename)
    if type_col != "Transaction Type":
        sub["Transaction Type"] = sub[type_col]
    if "Account" not in sub.columns:
        sub["Account"] = ""
    coerced = coerce_trade_frame(sub)
    return _rows_from_activity_frame(coerced, path.name)


def load_corporate_from_flex_downloads(download_dir: Path, query_id: str) -> pd.DataFrame:
    if not download_dir.is_dir():
        return pd.DataFrame(columns=CORPORATE_COLS)
    frames: list[pd.DataFrame] = []
    for path in sorted(download_dir.glob(f"flex_{query_id}_*_*.csv")):
        if path.stat().st_size < 50:
            continue
        try:
            part = parse_flex_corporate_csv(path)
            if not part.empty:
                frames.append(part)
        except Exception:
            continue
    # Also any dedicated corporate dumps
    for path in download_dir.glob("*corporate*.csv"):
        try:
            frames.append(parse_flex_corporate_csv(path))
        except Exception:
            pass
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=CORPORATE_COLS)
    return pd.concat(frames, ignore_index=True)
