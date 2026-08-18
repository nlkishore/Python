from __future__ import annotations

import argparse
import configparser
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf


def _normalize_yield_display(y: Any) -> float | None:
    """Yahoo dividend yields are usually decimals (e.g. 0.025 = 2.5%); sometimes percent."""
    if y is None:
        return None
    try:
        fy = float(y)
    except (TypeError, ValueError):
        return None
    if fy != fy or fy <= 0:
        return None
    return fy * 100 if fy <= 1 else fy


def _ensure_symbol_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    yfinance ETF top_holdings often stores tickers in the index (index name 'Symbol').
    Produce a frame with a string column 'Symbol' for pricing.
    """
    w = df.copy()
    idx_name = (w.index.name or "").strip().lower()
    if idx_name in ("symbol", "symbols", "ticker"):
        w = w.reset_index()
        first = w.columns[0]
        if first != "Symbol":
            w = w.rename(columns={first: "Symbol"})
        return w
    if "Symbol" in w.columns:
        return w
    if "symbol" in w.columns:
        return w.rename(columns={"symbol": "Symbol"})
    return w


def _last_price_and_currency(ticker: str) -> tuple[float | None, str | None]:
    """Most recent trade price from fast_info; fallback to last daily close."""
    t = str(ticker).strip().upper()
    if not t:
        return None, None
    tk = yf.Ticker(t)
    try:
        fi = tk.fast_info
        px = fi.get("lastPrice")
        if px is None:
            px = getattr(fi, "last_price", None)
        cur = fi.get("currency")
        if px is not None:
            return float(px), (str(cur) if cur else "USD")
    except Exception:
        pass
    try:
        hist = tk.history(period="5d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1]), "USD"
    except Exception:
        pass
    return None, None


def dividend_equity_snapshot(
    symbol: str,
    *,
    company_name: str = "",
    last_price: float | None = None,
    currency: str = "",
) -> dict[str, Any]:
    """
    Dividend-focused fields via yfinance (delayed / may be incomplete).
    Marks Pays dividend=True if trailing yield, disclosed rate, or dividend history suggests dividends.
    """
    sym = str(symbol).strip().upper()
    if not sym:
        return {"Pays dividend": False}

    t = yf.Ticker(sym)
    row: dict[str, Any] = {
        "Symbol": sym,
        "Name": (company_name or "").strip(),
        "Last price": None,
        "Currency": (currency or "").strip(),
        "Dividend yield %": None,
        "Annual div/sh": None,
        "5Y avg yield %": None,
        "Ex-dividend date": None,
        "Pays dividend": False,
    }

    if last_price is not None:
        row["Last price"] = float(last_price)
    if not row["Currency"]:
        pass

    if row["Last price"] is None or not row["Currency"]:
        px, cur = _last_price_and_currency(sym)
        if row["Last price"] is None and px is not None:
            row["Last price"] = px
        if not row["Currency"]:
            row["Currency"] = cur or ""

    info: dict[str, Any] = {}
    try:
        raw_info = getattr(t, "info", None)
        if isinstance(raw_info, dict):
            info = raw_info
    except Exception:
        info = {}

    nm = info.get("shortName") or info.get("longName")
    if nm and not row["Name"]:
        row["Name"] = str(nm)

    dy = _normalize_yield_display(info.get("dividendYield"))
    if dy is not None:
        row["Dividend yield %"] = round(dy, 2)
        row["Pays dividend"] = True

    adr = info.get("trailingAnnualDividendRate")
    if adr is None:
        adr = info.get("dividendRate")
    if adr is not None:
        try:
            row["Annual div/sh"] = round(float(adr), 4)
            row["Pays dividend"] = True
        except (TypeError, ValueError):
            pass

    five_y = _normalize_yield_display(info.get("fiveYearAvgDividendYield"))
    if five_y is not None:
        row["5Y avg yield %"] = round(five_y, 2)

    exd = info.get("exDividendDate")
    if exd is not None:
        try:
            row["Ex-dividend date"] = str(
                pd.to_datetime(exd, unit="s", utc=True).date()
            )
        except Exception:
            try:
                row["Ex-dividend date"] = str(pd.Timestamp(exd).date())
            except Exception:
                row["Ex-dividend date"] = str(exd)

    try:
        divs = t.dividends
    except Exception:
        divs = None
    if divs is not None and len(divs) > 0:
        row["Pays dividend"] = True
        if row["Annual div/sh"] is None:
            try:
                cutoff = pd.Timestamp(divs.index.max()) - pd.Timedelta(days=400)
                window = divs[divs.index >= cutoff]
                row["Annual div/sh"] = round(
                    float(window.sum()) if len(window) else float(divs.iloc[-1]),
                    4,
                )
            except Exception:
                pass

    return row


def _holdings_display_columns(df: pd.DataFrame) -> list[str]:
    """Pick symbol/name and weight columns; yfinance column names vary by version."""
    cols = list(df.columns)
    sym = next(
        (c for c in cols if c in ("Symbol", "symbol") or "symbol" in c.lower()),
        cols[0] if cols else None,
    )
    out: list[str] = []
    if sym:
        out.append(sym)
    pct = next(
        (
            c
            for c in cols
            if c in ("Holding Percent", "holdingPercent")
            or "percent" in c.lower()
            or "weight" in c.lower()
        ),
        None,
    )
    if pct and pct not in out:
        out.append(pct)
    return [c for c in out if c in cols] or cols


def _attach_last_prices(work: pd.DataFrame) -> pd.DataFrame:
    """Add Last price and Currency columns using yfinance per ticker."""
    if work.empty or "Symbol" not in work.columns:
        work = _ensure_symbol_column(work)
    if "Symbol" not in work.columns:
        work["Last price"] = ""
        work["Currency"] = ""
        return work

    prices: list[float | None] = []
    currencies: list[str] = []
    for sym in work["Symbol"].astype(str):
        px, cur = _last_price_and_currency(sym)
        prices.append(px)
        currencies.append(cur or "")

    out = work.copy()
    out["Last price"] = prices
    out["Currency"] = currencies
    return out


def _collect_dividend_rows_from_work(
    sector_key: str,
    etf_ticker: str,
    work: pd.DataFrame,
    *,
    include_prices: bool,
) -> list[dict[str, Any]]:
    """Return dividend snapshot dicts only for holdings flagged as dividend payers."""
    rows_out: list[dict[str, Any]] = []
    if work.empty or "Symbol" not in work.columns:
        return rows_out

    sector_label = sector_key.replace("_", " ")

    for _, r in work.iterrows():
        sym = str(r.get("Symbol", "")).strip().upper()
        if not sym:
            continue
        nm = str(r.get("Name") or "").strip()
        lp: float | None = None
        cur = ""
        if include_prices and "Last price" in work.columns:
            raw_lp = r.get("Last price")
            if pd.notna(raw_lp) and raw_lp is not None and raw_lp != "":
                try:
                    lp = float(raw_lp)
                except (TypeError, ValueError):
                    lp = None
            cur = str(r.get("Currency") or "").strip()

        snap = dividend_equity_snapshot(
            sym, company_name=nm, last_price=lp, currency=cur
        )
        if not snap.get("Pays dividend"):
            continue
        snap.pop("Pays dividend", None)
        rows_out.append(
            {
                "Sector": sector_label,
                "ETF": etf_ticker.upper(),
                **snap,
            }
        )
    return rows_out


def _print_and_save_dividend_report(
    div_rows: list[dict[str, Any]],
    *,
    csv_path: Path | None,
) -> None:
    ordered_cols = [
        "Sector",
        "ETF",
        "Symbol",
        "Name",
        "Last price",
        "Currency",
        "Dividend yield %",
        "Annual div/sh",
        "5Y avg yield %",
        "Ex-dividend date",
    ]
    bar = "=" * 68
    print(f"\n{bar}")
    print("DIVIDEND REPORT — top-5 holdings that pay dividends (Yahoo Finance; delayed / incomplete)")
    print(bar)
    print("Not financial advice.\n")

    if not div_rows:
        print("No dividend payers detected among screened holdings.\n")
        if csv_path:
            pd.DataFrame(columns=ordered_cols).to_csv(csv_path, index=False)
            print(f"Wrote CSV (headers only): {csv_path.resolve()}")
        return

    df = pd.DataFrame(div_rows)
    for c in ordered_cols:
        if c not in df.columns:
            df[c] = None
    df = df[[c for c in ordered_cols if c in df.columns]]

    def _fmt_px(x: Any) -> str:
        if x is None or (isinstance(x, float) and x != x):
            return ""
        try:
            return f"{float(x):,.2f}"
        except (TypeError, ValueError):
            return str(x)

    printable = df.copy()
    if "Last price" in printable.columns:
        printable["Last price"] = printable["Last price"].apply(_fmt_px)
    print(printable.to_string(index=False))
    print()

    if csv_path:
        df.to_csv(csv_path, index=False)
        print(f"Wrote CSV: {csv_path.resolve()}")


def get_top_holdings_from_ini(
    filename: str | Path = "config.ini",
    *,
    include_prices: bool = True,
    dividend_report: bool = False,
    dividend_csv: Path | None = None,
):
    # 1. Initialize the config parser
    config = configparser.ConfigParser()
    path = Path(filename)
    if not path.is_file():
        print(f"Error: Config file not found: {path.resolve()}")
        return

    config.read(path, encoding="utf-8")
    
    if 'ETFs' not in config:
        print("Error: No [ETFs] section found in the INI file.")
        return

    dividend_rows_all: list[dict[str, Any]] = []

    # 2. Iterate through each sector defined in the INI
    for sector, ticker_symbol in config.items('ETFs'):
        print(f"\n--- Sector: {sector.replace('_', ' ')} (ETF: {ticker_symbol}) ---")
        
        try:
            # 3. Use yfinance to fetch ETF data
            etf = yf.Ticker(ticker_symbol)
            
            # 4. Access the top_holdings data
            # Note: This requires a recent version of yfinance (pip install -U yfinance)
            holdings_data = etf.funds_data.top_holdings
            
            if holdings_data is not None and not holdings_data.empty:
                # Select only the Top 5
                top_5 = holdings_data.head(5)
                work = _ensure_symbol_column(top_5)
                if include_prices:
                    work = _attach_last_prices(work)

                # Columns: Symbol, Name, weight, last price, currency
                disp = _holdings_display_columns(work)
                if "Symbol" in work.columns and "Symbol" not in disp:
                    disp = ["Symbol"] + [c for c in disp if c != "Symbol"]
                extra = [c for c in ("Last price", "Currency") if c in work.columns]
                show_cols: list[str] = []
                for c in ("Symbol", "Name"):
                    if c in work.columns and c not in show_cols:
                        show_cols.append(c)
                for c in disp + extra:
                    if c in work.columns and c not in show_cols:
                        show_cols.append(c)
                # Format percentages if Holding Percent present
                printable = work[show_cols].copy()
                pct_col = next(
                    (c for c in printable.columns if "percent" in c.lower()), None
                )
                if pct_col:
                    printable[pct_col] = printable[pct_col].apply(
                        lambda x: f"{float(x) * 100:.2f}%"
                        if pd.notna(x) and isinstance(x, (int, float))
                        else x
                    )
                lp_col = "Last price"
                if lp_col in printable.columns:
                    printable[lp_col] = printable[lp_col].apply(
                        lambda x: f"{x:,.2f}" if pd.notna(x) and x != "" and x is not None else ""
                    )
                print(printable.to_string(index=False))

                if dividend_report:
                    dividend_rows_all.extend(
                        _collect_dividend_rows_from_work(
                            sector,
                            ticker_symbol,
                            work,
                            include_prices=include_prices,
                        )
                    )
            else:
                print(f"No holdings data available for {ticker_symbol}.")
                
        except Exception as e:
            print(f"Could not retrieve data for {ticker_symbol}: {e}")

    if dividend_report:
        csv_out = dividend_csv.resolve() if dividend_csv else None
        _print_and_save_dividend_report(dividend_rows_all, csv_path=csv_out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Print top 5 holdings per sector ETF from config.ini [ETFs]."
    )
    ap.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path(__file__).resolve().parent / "config.ini",
        help="Path to config.ini (default: config.ini next to this script).",
    )
    ap.add_argument(
        "--no-prices",
        action="store_true",
        help="Skip per-stock quotes (faster; holdings weights only).",
    )
    ap.add_argument(
        "--dividend-report",
        action="store_true",
        help=(
            "After sector tables, list top-5 names that Yahoo marks as dividend payers "
            "(symbol, price, yield, annual div estimate, optional 5y avg / ex-div)."
        ),
    )
    ap.add_argument(
        "--dividend-csv",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "With --dividend-report: write dividend table to CSV (UTF-8). "
            "If no rows, writes an empty file with headers."
        ),
    )
    args = ap.parse_args()

    if args.dividend_csv and not args.dividend_report:
        args.dividend_report = True

    get_top_holdings_from_ini(
        args.config,
        include_prices=not args.no_prices,
        dividend_report=args.dividend_report,
        dividend_csv=args.dividend_csv,
    )
