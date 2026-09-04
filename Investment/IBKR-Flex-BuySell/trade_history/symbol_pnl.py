"""Average-cost Symbol_PnL with splits / cash mergers applied chronologically."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from flex_parse import _signed_quantity, _trade_cash_amount
from market_prices import fetch_current_market_prices

_CASH_PER_SHARE = re.compile(
    r"for\s+USD\s+([0-9]+(?:\.[0-9]+)?)\s+per\s+Share",
    re.IGNORECASE,
)
_CASH_AND_STOCK = re.compile(
    r"USD\s+([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)


@dataclass
class _Position:
    qty: float = 0.0
    cost: float = 0.0  # total remaining cost basis
    buy_qty: float = 0.0
    sell_qty: float = 0.0
    buy_cost: float = 0.0
    sell_proceeds: float = 0.0
    realized: float = 0.0
    buy_trades: int = 0
    sell_trades: int = 0
    first_buy: pd.Timestamp | None = None
    last_sell: pd.Timestamp | None = None
    corp_notes: list[str] = field(default_factory=list)

    def avg_cost(self) -> float:
        return (self.cost / self.qty) if self.qty > 1e-9 else 0.0

    def apply_buy(self, qty: float, cash_paid: float, dt: pd.Timestamp) -> None:
        q = abs(qty)
        paid = abs(cash_paid)
        self.qty += q
        self.cost += paid
        self.buy_qty += q
        self.buy_cost += paid
        self.buy_trades += 1
        if self.first_buy is None or (pd.notna(dt) and dt < self.first_buy):
            self.first_buy = dt

    def apply_sell(self, qty: float, proceeds: float, dt: pd.Timestamp) -> None:
        q = abs(qty)
        proc = abs(proceeds)
        if self.qty <= 1e-9:
            # Sell with no basis (data gap / stock from merger not tracked)
            self.sell_qty += q
            self.sell_proceeds += proc
            self.sell_trades += 1
            self.qty -= q
            if self.last_sell is None or (pd.notna(dt) and dt > self.last_sell):
                self.last_sell = dt
            return
        sold = min(q, self.qty)
        avg = self.avg_cost()
        cost_sold = avg * sold
        proc_sold = proc * (sold / q) if q > 1e-9 else proc
        self.realized += proc_sold - cost_sold
        self.cost = max(self.cost - cost_sold, 0.0)
        self.qty -= q  # may go slightly negative if oversell
        if self.qty < 0 and abs(self.qty) < 1e-8:
            self.qty = 0.0
        if self.qty <= 1e-9:
            self.cost = 0.0
        self.sell_qty += q
        self.sell_proceeds += proc
        self.sell_trades += 1
        if self.last_sell is None or (pd.notna(dt) and dt > self.last_sell):
            self.last_sell = dt

    def apply_split_qty(self, delta_qty: float, note: str) -> None:
        """IBKR reports share delta for splits (e.g. +114 on 20:1). Cost unchanged.

        Reverse splits often arrive as two rows (retire old shares, credit new).
        The first delta can overshoot held qty by a fraction of a share; that must
        NOT wipe cost — otherwise the new shares look free and sells look like profit.
        Zero basis only when the position is truly flat.
        """
        self.qty += float(delta_qty)
        if abs(self.qty) < 1e-8:
            self.qty = 0.0
            self.cost = 0.0
        self.corp_notes.append(note)

    def apply_cash_merger_exit(self, shares: float, cash: float, dt: pd.Timestamp, note: str) -> None:
        """Cash buyout / cash portion of merger: close shares for cash proceeds."""
        q = abs(shares) if pd.notna(shares) and abs(float(shares)) > 1e-9 else abs(self.qty)
        if q <= 1e-9 and self.qty > 1e-9:
            q = self.qty
        if q <= 1e-9:
            return
        self.apply_sell(q, abs(cash), dt)
        self.corp_notes.append(note)


def build_by_symbol_trades(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty or "Symbol" not in trades.columns:
        return pd.DataFrame(
            columns=["Symbol", "Side", "TradeCount", "Quantity", "GrossAmount", "NetAmount"]
        )
    df = trades.copy()
    df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
    df["Side"] = df["Transaction Type"].astype(str).str.strip()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").abs()
    df["Gross Amount"] = pd.to_numeric(df.get("Gross Amount"), errors="coerce")
    df["Net Amount"] = pd.to_numeric(df.get("Net Amount"), errors="coerce")
    g = (
        df.groupby(["Symbol", "Side"], dropna=False)
        .agg(
            TradeCount=("Symbol", "count"),
            Quantity=("Quantity", "sum"),
            GrossAmount=("Gross Amount", "sum"),
            NetAmount=("Net Amount", "sum"),
        )
        .reset_index()
    )
    return g.sort_values(["Symbol", "Side"]).reset_index(drop=True)


def _normalize_symbol(sym: object) -> str:
    s = str(sym or "").strip().upper()
    # TEAM.OLD / LRCX.OLD / AZN.OLD → base ticker for ledger continuity
    if s.endswith(".OLD"):
        s = s[: -len(".OLD")]
    return s


def _cash_from_merger_description(desc: str, shares: float) -> float | None:
    m = _CASH_PER_SHARE.search(desc or "")
    if m and shares:
        return float(m.group(1)) * abs(shares)
    return None


def _dividends_by_symbol(corporate: pd.DataFrame | None) -> dict[str, float]:
    if corporate is None or corporate.empty:
        return {}
    c = corporate.copy()
    c["Symbol"] = c["Symbol"].map(_normalize_symbol)
    action = c.get("ActionType", pd.Series(dtype=str)).astype(str).str.upper()
    is_div = action.eq("DIVIDEND")
    if "Transaction Type" in c.columns:
        raw_tt = c["Transaction Type"].astype(str).str.strip().str.upper()
        is_div = is_div | raw_tt.eq("DIVIDEND")
    divs = c.loc[is_div].copy()
    if divs.empty:
        return {}
    amt = pd.to_numeric(divs.get("Amount"), errors="coerce")
    if amt.isna().all() and "Net Amount" in divs.columns:
        amt = pd.to_numeric(divs["Net Amount"], errors="coerce")
    divs = divs.assign(_amt=amt.fillna(0.0).abs())
    return divs.groupby("Symbol")["_amt"].sum().to_dict()


def _run_symbol_ledger(
    trades: pd.DataFrame,
    corporate: pd.DataFrame | None,
) -> dict[str, _Position]:
    """Chronological average-cost ledger per symbol (trades + SPLIT + MERGER)."""
    events: list[tuple[pd.Timestamp, int, str, dict]] = []

    if not trades.empty:
        df = trades.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["_sym"] = df["Symbol"].map(_normalize_symbol)
        df = df.loc[df["_sym"].ne("") & df["_sym"].ne("-")].copy()
        df["_cash"] = df.apply(_trade_cash_amount, axis=1)
        df["_signed_qty"] = df.apply(_signed_quantity, axis=1)
        for _, r in df.iterrows():
            dt = r["Date"] if pd.notna(r["Date"]) else pd.Timestamp.min
            tt = str(r.get("Transaction Type", "")).strip()
            qty = float(r["_signed_qty"])
            cash = float(r["_cash"])
            if tt == "Buy":
                events.append(
                    (pd.Timestamp(dt), 0, str(r["_sym"]), {"kind": "buy", "qty": abs(qty), "cost": abs(cash)})
                )
            elif tt == "Sell":
                events.append(
                    (pd.Timestamp(dt), 3, str(r["_sym"]), {"kind": "sell", "qty": abs(qty), "proc": abs(cash)})
                )

    if corporate is not None and not corporate.empty:
        c = corporate.copy()
        c["Date"] = pd.to_datetime(c["Date"], errors="coerce")
        c["Symbol"] = c["Symbol"].map(_normalize_symbol)
        for _, r in c.iterrows():
            act = str(r.get("ActionType", "") or "").strip().upper()
            sym = str(r.get("Symbol", "") or "")
            if not sym or sym == "-":
                continue
            dt = r["Date"] if pd.notna(r["Date"]) else pd.Timestamp.min
            qty = pd.to_numeric(r.get("Quantity"), errors="coerce")
            amt = pd.to_numeric(r.get("Amount"), errors="coerce")
            desc = str(r.get("Description", "") or "")
            if act == "SPLIT" and pd.notna(qty) and abs(float(qty)) > 1e-12:
                events.append(
                    (
                        pd.Timestamp(dt),
                        1,
                        sym,
                        {"kind": "split", "qty": float(qty), "note": f"SPLIT {desc[:50]}"},
                    )
                )
            elif act in ("MERGER", "CORPORATE_ACTION", "SPINOFF") and pd.notna(qty):
                q = float(qty)
                cash = float(amt) if pd.notna(amt) else 0.0
                parsed = _cash_from_merger_description(desc, q)
                if parsed is not None:
                    cash = parsed
                events.append(
                    (
                        pd.Timestamp(dt),
                        2,
                        sym,
                        {
                            "kind": "merger",
                            "qty": q,
                            "cash": abs(cash),
                            "desc": desc,
                            "note": f"{act} {desc[:50]}",
                        },
                    )
                )

    events.sort(key=lambda e: (e[0], e[1], e[2]))
    positions: dict[str, _Position] = {}

    for dt, _prio, sym, payload in events:
        pos = positions.setdefault(sym, _Position())
        kind = payload["kind"]
        if kind == "buy":
            pos.apply_buy(payload["qty"], payload["cost"], dt)
        elif kind == "sell":
            pos.apply_sell(payload["qty"], payload["proc"], dt)
        elif kind == "split":
            pos.apply_split_qty(payload["qty"], payload["note"])
        elif kind == "merger":
            q = payload["qty"]
            cash = payload["cash"]
            desc = payload["desc"]
            if q < -1e-12:
                if cash > 1e-9 or _CASH_PER_SHARE.search(desc):
                    if cash <= 1e-9:
                        cash = _cash_from_merger_description(desc, q) or 0.0
                    pos.apply_cash_merger_exit(abs(q), cash, dt, payload["note"])
                else:
                    sold = abs(q)
                    if pos.qty > 1e-9:
                        take = min(sold, pos.qty)
                        pos.cost = max(pos.cost - pos.avg_cost() * take, 0.0)
                        pos.qty -= sold
                        if pos.qty <= 1e-9:
                            pos.qty = 0.0
                            pos.cost = 0.0
                    else:
                        pos.qty -= sold
                    pos.corp_notes.append(payload["note"])
            elif q > 1e-12:
                pos.qty += q
                if cash > 1e-9:
                    pos.cost += cash
                pos.corp_notes.append(payload["note"])

    return positions


def build_symbol_pnl(
    trades: pd.DataFrame,
    corporate: pd.DataFrame | None = None,
    *,
    fetch_marks: bool = True,
) -> pd.DataFrame:
    """
    Per-symbol average-cost P&L with corporate SPLIT / MERGER applied in date order.

    - Splits adjust Open_Qty (cost basis unchanged).
    - Cash mergers (e.g. ATVI @ $95, COUP @ $81) realize exit P&L and clear Open_Qty.
    """
    empty_cols = [
        "Symbol",
        "Buy_Qty",
        "Sell_Qty",
        "Buy_Cost",
        "Sell_Proceeds",
        "Open_Qty",
        "Realized_PnL",
        "Dividends",
        "Mark_Price",
        "Unrealized_PnL",
        "Total_PnL",
        "First_Buy_Date",
        "Last_Sell_Date",
        "Buy_Trades",
        "Sell_Trades",
        "Corp_Notes",
    ]
    if trades.empty or "Symbol" not in trades.columns:
        return pd.DataFrame(columns=empty_cols)

    positions = _run_symbol_ledger(trades, corporate)
    div_by_sym = _dividends_by_symbol(corporate)

    rows: list[dict] = []
    for sym, pos in sorted(positions.items()):
        dividends = float(div_by_sym.get(sym, 0.0))
        rows.append(
            {
                "Symbol": sym,
                "Buy_Qty": round(pos.buy_qty, 4),
                "Sell_Qty": round(pos.sell_qty, 4),
                "Buy_Cost": round(pos.buy_cost, 2),
                "Sell_Proceeds": round(pos.sell_proceeds, 2),
                "Open_Qty": round(pos.qty, 4),
                "Realized_PnL": round(pos.realized, 2),
                "Dividends": round(dividends, 2),
                "Mark_Price": None,
                "Unrealized_PnL": None,
                "Total_PnL": None,
                "First_Buy_Date": pos.first_buy.date()
                if pos.first_buy is not None and pd.notna(pos.first_buy)
                else None,
                "Last_Sell_Date": pos.last_sell.date()
                if pos.last_sell is not None and pd.notna(pos.last_sell)
                else None,
                "Buy_Trades": pos.buy_trades,
                "Sell_Trades": pos.sell_trades,
                "Corp_Notes": "; ".join(pos.corp_notes[:3]) if pos.corp_notes else "",
                "_remaining_cost": pos.cost,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=empty_cols)

    open_syms = out.loc[out["Open_Qty"].abs() > 1e-6, "Symbol"].tolist()
    marks: dict[str, tuple[float | None, object]] = {}
    if fetch_marks and open_syms:
        try:
            marks = fetch_current_market_prices(open_syms)
        except ImportError:
            marks = {}

    unrealized_vals: list[float | None] = []
    mark_vals: list[float | None] = []
    totals: list[float] = []
    for _, row in out.iterrows():
        mark = None
        unreal = None
        oq = float(row["Open_Qty"])
        if abs(oq) > 1e-6:
            price, _ = marks.get(row["Symbol"], (None, None))
            mark = price
            if price is not None and oq > 0:
                market_value = oq * float(price)
                unreal = market_value - float(row["_remaining_cost"])
        mark_vals.append(round(mark, 4) if mark is not None else None)
        unrealized_vals.append(round(unreal, 2) if unreal is not None else None)
        total = float(row["Realized_PnL"]) + float(row["Dividends"])
        if unreal is not None:
            total += unreal
        totals.append(round(total, 2))

    out["Mark_Price"] = mark_vals
    out["Unrealized_PnL"] = unrealized_vals
    out["Total_PnL"] = totals
    out = out.drop(columns=["_remaining_cost"])
    return out.sort_values("Symbol").reset_index(drop=True)


def _last_sell_price_by_symbol(trades: pd.DataFrame | None) -> dict[str, float]:
    """Map each symbol to its latest non-null sell price from the raw trade log."""
    if trades is None or trades.empty or "Symbol" not in trades.columns:
        return {}

    sells = trades.loc[trades["Transaction Type"].astype(str).str.strip().str.upper().eq("SELL")].copy()
    if sells.empty:
        return {}

    sells["Date"] = pd.to_datetime(sells["Date"], errors="coerce")
    sells["Price"] = pd.to_numeric(sells.get("Price"), errors="coerce")
    out: dict[str, float] = {}

    for sym, sub in sells.sort_values(["Date", "Symbol"], na_position="last").groupby("Symbol", sort=False):
        last_price = sub.loc[sub["Price"].notna(), "Price"]
        if not last_price.empty:
            out[str(sym).strip().upper()] = round(float(last_price.iloc[-1]), 4)
    return out


def _average_sell_price_by_symbol(trades: pd.DataFrame | None) -> dict[str, float]:
    """Map each symbol to the weighted-average sell price across all closed lots."""
    if trades is None or trades.empty or "Symbol" not in trades.columns:
        return {}

    sells = trades.loc[trades["Transaction Type"].astype(str).str.strip().str.upper().eq("SELL")].copy()
    if sells.empty:
        return {}

    sells["Quantity"] = pd.to_numeric(sells.get("Quantity"), errors="coerce").abs()
    sells["Price"] = pd.to_numeric(sells.get("Price"), errors="coerce")
    sells["Net Amount"] = pd.to_numeric(sells.get("Net Amount"), errors="coerce")
    out: dict[str, float] = {}

    for sym, sub in sells.groupby("Symbol", sort=False):
        qty = sub["Quantity"].fillna(0.0).sum()
        if qty <= 1e-9:
            continue
        net = sub["Net Amount"].fillna(0.0).abs().sum()
        if pd.notna(net) and net > 0 and sub["Price"].notna().any():
            out[str(sym).strip().upper()] = round(float(net / qty), 4)
        else:
            price_total = (sub["Price"].fillna(0.0) * sub["Quantity"].fillna(0.0)).sum()
            if qty > 0:
                out[str(sym).strip().upper()] = round(float(price_total / qty), 4)
    return out


def completely_sold_from_symbol_pnl(symbol_pnl: pd.DataFrame, trades: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build Completely_Sold rows from corporate-aware Symbol_PnL (Open_Qty ≈ 0)."""
    if symbol_pnl is None or symbol_pnl.empty:
        return pd.DataFrame()
    closed = symbol_pnl.loc[symbol_pnl["Open_Qty"].abs() <= 1e-6].copy()
    # Need some activity (buys or merger exit proceeds)
    closed = closed.loc[
        (closed["Buy_Qty"] > 0) | (closed["Sell_Proceeds"].abs() > 0) | (closed["Realized_PnL"].abs() > 0)
    ].copy()
    if closed.empty:
        return pd.DataFrame()
    sell_prices = _average_sell_price_by_symbol(trades)
    out = pd.DataFrame(
        {
            "Symbol": closed["Symbol"],
            "Buy_Qty_Total": closed["Buy_Qty"],
            "Sell_Qty_Total": closed["Sell_Qty"],
            "Buy_Trades": closed["Buy_Trades"],
            "Sell_Trades": closed["Sell_Trades"],
            "Total_Buy_Cost": closed["Buy_Cost"],
            "Total_Sell_Proceeds": closed["Sell_Proceeds"],
            "Profit": closed["Realized_PnL"],
            "Profit_Pct": closed.apply(
                lambda r: round(float(r["Realized_PnL"]) / float(r["Buy_Cost"]) * 100.0, 2)
                if float(r["Buy_Cost"]) > 1e-9
                else None,
                axis=1,
            ),
            "Last_Sold_Date": closed["Last_Sell_Date"],
            "Last_Sold_Price": closed["Symbol"].map(lambda s: sell_prices.get(str(s).strip().upper())),
            "First_Buy_Date": closed["First_Buy_Date"],
        }
    )
    return out.sort_values(["Last_Sold_Date", "Symbol"], ascending=[False, True]).reset_index(drop=True)


def still_holding_from_symbol_pnl(symbol_pnl: pd.DataFrame) -> pd.DataFrame:
    if symbol_pnl is None or symbol_pnl.empty:
        return pd.DataFrame()
    open_rows = symbol_pnl.loc[symbol_pnl["Open_Qty"].abs() > 1e-6].copy()
    if open_rows.empty:
        return pd.DataFrame()
    rows = []
    for _, r in open_rows.iterrows():
        note = "Open position"
        if float(r["Open_Qty"]) < 0:
            note = "Negative open qty — check missing buys or incomplete corporate actions"
        elif float(r["Sell_Trades"]) == 0 and not str(r.get("Corp_Notes", "")):
            note = "Has buys but no sells — still holding (or missing merger exit in corporate data)"
        elif str(r.get("Corp_Notes", "")):
            note = f"Open after corporate actions: {str(r['Corp_Notes'])[:80]}"
        rows.append(
            {
                "Symbol": r["Symbol"],
                "Net_Qty": r["Open_Qty"],
                "Buy_Trades": r["Buy_Trades"],
                "Sell_Trades": r["Sell_Trades"],
                "Realized_PnL": r["Realized_PnL"],
                "Unrealized_PnL": r.get("Unrealized_PnL"),
                "Note": note,
            }
        )
    return pd.DataFrame(rows).sort_values("Symbol").reset_index(drop=True)
