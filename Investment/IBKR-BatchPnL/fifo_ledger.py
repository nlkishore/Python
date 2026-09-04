"""FIFO lot matching: per-symbol averages plus buy/sell batch P&L rows."""

from __future__ import annotations

import logging
import re
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Deque

import pandas as pd

_FLEX_DIR = Path(__file__).resolve().parents[1] / "IBKR-Flex-BuySell"
if str(_FLEX_DIR) not in sys.path:
    sys.path.insert(0, str(_FLEX_DIR))

logger = logging.getLogger(__name__)

_EPS = 1e-9

# IBKR often names the surviving/child ticker in "(TICKER, COMPANY, ISIN)".
_PAREN_TICKER = re.compile(r"\(([A-Z][A-Z0-9.]{0,11})\s*,")
_SPINOFF_CHILD = re.compile(
    r"Spinoff\s+(\d+)\s+for\s+(\d+)\s+\(([A-Z][A-Z0-9.]{0,11})\s*,",
    re.IGNORECASE,
)
_CUSIP_CHANGE_TO = re.compile(
    r"CUSIP/ISIN Change.*\(([A-Z][A-Z0-9.]{0,11})\s*,",
    re.IGNORECASE | re.DOTALL,
)
_SPLIT_RATIO = re.compile(r"Split\s+(\d+)\s+for\s+(\d+)", re.IGNORECASE)
_WITH_TICKER = re.compile(r"\bWITH\s+([A-Z]{1,6})(?:\s+WI)?\b", re.IGNORECASE)
_CUSIP_AND_RATIO = re.compile(
    r"\b((?:US)?[A-Z0-9]{9,12})\s+(\d+)\s+for\s+(\d+)\b",
    re.IGNORECASE,
)

# CUSIPs that do not appear as the (TICKER, ...) result (cash+stock deals).
_KNOWN_CUSIP_TO_SYMBOL = {
    "874054109": "TTWO",
    "US8740541094": "TTWO",
    "8740541094": "TTWO",
}


def _normalize_symbol(sym: object) -> str:
    s = str(sym or "").strip().upper()
    if s.endswith(".OLD"):
        s = s[: -len(".OLD")]
    return s


def _paren_tickers(desc: str) -> list[str]:
    return [_normalize_symbol(m.group(1)) for m in _PAREN_TICKER.finditer(desc or "")]


def parse_split_ratio(desc: str) -> float | None:
    """'Split 20 for 1' → 20.0; 'Split 1 for 20' (reverse) → 0.05."""
    m = _SPLIT_RATIO.search(desc or "")
    if not m:
        return None
    a, b = float(m.group(1)), float(m.group(2))
    if b <= _EPS:
        return None
    return a / b


def incoming_symbol_from_corp(desc: str, row_symbol: str, action: str, qty: float) -> str | None:
    """
    Ticker that should receive shares from a corporate action.

    Spinoff / CUSIP change / 'WITH NEWTICKER' often list a different symbol
    than the row's Symbol column (e.g. PFE spinoff → VTRS, LAAC → LAR).
    """
    row = _normalize_symbol(row_symbol)
    d = desc or ""
    act = (action or "").upper()

    m_spin = _SPINOFF_CHILD.search(d)
    if m_spin or act == "SPINOFF":
        child = _normalize_symbol(m_spin.group(3)) if m_spin else None
        if not child:
            parens = [p for p in _paren_tickers(d) if p and p != row]
            child = parens[-1] if parens else None
        if child and child != row:
            return child

    if "CUSIP/ISIN CHANGE" in d.upper() and qty > _EPS:
        m_ch = _CUSIP_CHANGE_TO.search(d)
        if m_ch:
            dest = _normalize_symbol(m_ch.group(1))
            if dest and dest != row and not dest.endswith(".OLD"):
                return dest
        parens = [p for p in _paren_tickers(d) if p and p != row and not str(p).endswith("OLD")]
        if parens:
            return parens[-1]

    m_with = _WITH_TICKER.search(d)
    if m_with and qty > _EPS:
        dest = _normalize_symbol(m_with.group(1))
        if dest and dest != row:
            return dest

    return None


def parse_stock_merger_conversion(desc: str, closed_qty: float) -> tuple[str, float] | None:
    """Cash+stock merger: CUSIP + '406 for 10000' → (TTWO, new_qty)."""
    d = desc or ""
    m = _CUSIP_AND_RATIO.search(d)
    if not m:
        return None
    cusip = m.group(1).upper()
    new_sym = _KNOWN_CUSIP_TO_SYMBOL.get(cusip) or _KNOWN_CUSIP_TO_SYMBOL.get(
        cusip[2:] if cusip.startswith("US") else f"US{cusip}"
    )
    if not new_sym:
        return None
    denom = float(m.group(3))
    if denom <= _EPS:
        return None
    new_qty = abs(closed_qty) * (float(m.group(2)) / denom)
    if new_qty <= _EPS:
        return None
    return _normalize_symbol(new_sym), new_qty


def _as_date(dt: object) -> date | None:
    ts = pd.to_datetime(dt, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).date()


def _round_qty(value: float) -> float:
    return round(float(value), 4)


def _round_money(value: float) -> float:
    return round(float(value), 2)


def _round_price(value: float) -> float:
    return round(float(value), 4)


def _pct(pnl: float, cost: float) -> float | None:
    if abs(cost) <= _EPS:
        return None
    return round(float(pnl) / float(cost) * 100.0, 2)


@dataclass
class _Lot:
    qty: float
    cost: float
    price: float
    trade_date: pd.Timestamp

    def take(self, matched_qty: float) -> tuple[float, float]:
        """Remove matched_qty; return (cost_taken, price)."""
        if self.qty <= _EPS:
            return 0.0, self.price
        take = min(matched_qty, self.qty)
        cost_taken = self.cost * (take / self.qty)
        self.cost = max(self.cost - cost_taken, 0.0)
        self.qty -= take
        if self.qty <= _EPS:
            self.qty = 0.0
            self.cost = 0.0
        return cost_taken, self.price


@dataclass
class _SymbolBook:
    longs: Deque[_Lot] = field(default_factory=deque)
    shorts: Deque[_Lot] = field(default_factory=deque)
    buy_qty: float = 0.0
    buy_cost: float = 0.0
    sell_qty: float = 0.0
    sell_proceeds: float = 0.0
    realized: float = 0.0
    buy_trades: int = 0
    sell_trades: int = 0
    first_buy: pd.Timestamp | None = None
    last_sell: pd.Timestamp | None = None
    corp_notes: list[str] = field(default_factory=list)

    def note_buy_date(self, dt: pd.Timestamp) -> None:
        if self.first_buy is None or (pd.notna(dt) and dt < self.first_buy):
            self.first_buy = dt

    def note_sell_date(self, dt: pd.Timestamp) -> None:
        if self.last_sell is None or (pd.notna(dt) and dt > self.last_sell):
            self.last_sell = dt

    def apply_split(self, delta_qty: float, note: str, *, ratio: float | None = None) -> None:
        """Scale remaining lots by split ratio (preferred) or IBKR share delta."""
        if ratio is not None and ratio > _EPS:
            for lot in list(self.longs) + list(self.shorts):
                lot.qty *= ratio
                if lot.qty > _EPS:
                    lot.price = lot.cost / lot.qty
            self.corp_notes.append(note)
            return
        long_qty = sum(lot.qty for lot in self.longs)
        short_qty = sum(lot.qty for lot in self.shorts)
        if long_qty > _EPS and abs(delta_qty) > _EPS:
            new_ratio = (long_qty + float(delta_qty)) / long_qty
            if new_ratio > _EPS:
                for lot in self.longs:
                    lot.qty *= new_ratio
                    lot.price = (lot.cost / lot.qty) if lot.qty > _EPS else lot.price
        elif short_qty > _EPS and abs(delta_qty) > _EPS:
            new_ratio = (short_qty + abs(float(delta_qty))) / short_qty
            if new_ratio > _EPS:
                for lot in self.shorts:
                    lot.qty *= new_ratio
                    lot.price = (lot.cost / lot.qty) if lot.qty > _EPS else lot.price
        self.corp_notes.append(note)

    def open_qty(self) -> float:
        long_qty = sum(lot.qty for lot in self.longs)
        short_qty = sum(lot.qty for lot in self.shorts)
        return long_qty - short_qty

    def remaining_cost(self) -> float:
        return sum(lot.cost for lot in self.longs)

    def take_longs(self, qty: float) -> tuple[float, float]:
        """Remove qty from oldest long lots. Returns (qty_taken, cost_taken)."""
        remaining = abs(qty)
        qty_taken = 0.0
        cost_taken = 0.0
        while remaining > _EPS and self.longs:
            lot = self.longs[0]
            take = min(lot.qty, remaining)
            cost, _price = lot.take(take)
            qty_taken += take
            cost_taken += cost
            remaining -= take
            if lot.qty <= _EPS:
                self.longs.popleft()
        return qty_taken, cost_taken


def _unit_price(cash: float, qty: float, fallback: float | None = None) -> float:
    q = abs(qty)
    if q > _EPS:
        return abs(cash) / q
    if fallback is not None and pd.notna(fallback):
        return float(fallback)
    return 0.0


def _match_against_queue(
    queue: Deque[_Lot],
    *,
    remaining: float,
    closing_cash: float,
    closing_qty: float,
    closing_date: pd.Timestamp,
    closing_is_sell: bool,
    symbol: str,
    rows: list[dict],
) -> tuple[float, float]:
    """
    Match remaining qty against FIFO lots.

    Long cover of a sell: lots are buys; closing is sell proceeds.
    Short cover of a buy: lots are shorts (sold first); closing is buy cost.
    Returns (qty_still_unmatched, realized_delta).
    """
    realized = 0.0
    close_price = _unit_price(closing_cash, closing_qty)
    while remaining > _EPS and queue:
        lot = queue[0]
        matched = min(lot.qty, remaining)
        lot_cost, lot_price = lot.take(matched)
        close_slice = abs(closing_cash) * (matched / closing_qty) if closing_qty > _EPS else 0.0
        if closing_is_sell:
            buy_qty, buy_price, buy_date = matched, lot_price, lot.trade_date
            sell_qty, sell_price, sell_date = matched, close_price, closing_date
            buy_cost, sell_proceeds = lot_cost, close_slice
            pnl = sell_proceeds - buy_cost
        else:
            buy_qty, buy_price, buy_date = matched, close_price, closing_date
            sell_qty, sell_price, sell_date = matched, lot_price, lot.trade_date
            buy_cost, sell_proceeds = close_slice, lot_cost
            pnl = sell_proceeds - buy_cost
        rows.append(
            _batch_row(
                symbol=symbol,
                buy_qty=buy_qty,
                buy_price=buy_price,
                buy_date=buy_date,
                sell_qty=sell_qty,
                sell_price=sell_price,
                sell_date=sell_date,
                matched_qty=matched,
                buy_cost=buy_cost,
                sell_proceeds=sell_proceeds,
                pnl=pnl,
                status="MATCHED",
            )
        )
        realized += pnl
        remaining -= matched
        if lot.qty <= _EPS:
            queue.popleft()
    return remaining, realized


def _batch_row(
    *,
    symbol: str,
    buy_qty: float | None,
    buy_price: float | None,
    buy_date: object,
    sell_qty: float | None,
    sell_price: float | None,
    sell_date: object,
    matched_qty: float | None,
    buy_cost: float | None,
    sell_proceeds: float | None,
    pnl: float | None,
    status: str,
    mark_price: float | None = None,
) -> dict:
    cost = float(buy_cost) if buy_cost is not None else 0.0
    return {
        "Symbol": symbol,
        "Buy_Qty": _round_qty(buy_qty) if buy_qty is not None else None,
        "Buy_Price": _round_price(buy_price) if buy_price is not None else None,
        "Buy_Date": _as_date(buy_date),
        "Sell_Qty": _round_qty(sell_qty) if sell_qty is not None else None,
        "Sell_Price": _round_price(sell_price) if sell_price is not None else None,
        "Sell_Date": _as_date(sell_date),
        "Matched_Qty": _round_qty(matched_qty) if matched_qty is not None else None,
        "Buy_Cost": _round_money(buy_cost) if buy_cost is not None else None,
        "Sell_Proceeds": _round_money(sell_proceeds) if sell_proceeds is not None else None,
        "Batch_PnL": _round_money(pnl) if pnl is not None else None,
        "Batch_PnL_Pct": _pct(float(pnl), cost) if pnl is not None else None,
        "Status": status,
        "Mark_Price": _round_price(mark_price) if mark_price is not None else None,
    }


def _import_trade_helpers():
    """Lazy import so unit tests can inject helpers without Flex on path."""
    from flex_parse import _signed_quantity, _trade_cash_amount
    from trade_history.symbol_pnl import _cash_from_merger_description

    return _trade_cash_amount, _signed_quantity, _cash_from_merger_description


def _build_events(
    trades: pd.DataFrame,
    corporate: pd.DataFrame | None,
    *,
    trade_cash_amount,
    signed_quantity,
    cash_from_merger_description,
) -> list[tuple[pd.Timestamp, int, str, dict]]:
    events: list[tuple[pd.Timestamp, int, str, dict]] = []

    if not trades.empty:
        df = trades.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["_sym"] = df["Symbol"].map(_normalize_symbol)
        df = df.loc[df["_sym"].ne("") & df["_sym"].ne("-")].copy()
        df["_cash"] = df.apply(trade_cash_amount, axis=1)
        df["_signed_qty"] = df.apply(signed_quantity, axis=1)
        for _, r in df.iterrows():
            dt = r["Date"] if pd.notna(r["Date"]) else pd.Timestamp.min
            tt = str(r.get("Transaction Type", "")).strip()
            qty = abs(float(r["_signed_qty"]))
            cash = abs(float(r["_cash"]))
            price = pd.to_numeric(r.get("Price"), errors="coerce")
            fallback = float(price) if pd.notna(price) else None
            if tt == "Buy":
                events.append(
                    (
                        pd.Timestamp(dt),
                        0,
                        str(r["_sym"]),
                        {"kind": "buy", "qty": qty, "cash": cash, "price": fallback},
                    )
                )
            elif tt == "Sell":
                events.append(
                    (
                        pd.Timestamp(dt),
                        3,
                        str(r["_sym"]),
                        {"kind": "sell", "qty": qty, "cash": cash, "price": fallback},
                    )
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
            if act == "SPLIT":
                ratio = parse_split_ratio(desc)
                delta = float(qty) if pd.notna(qty) else 0.0
                if (ratio is not None and ratio > _EPS) or abs(delta) > 1e-12:
                    events.append(
                        (
                            pd.Timestamp(dt),
                            1,
                            sym,
                            {
                                "kind": "split",
                                "qty": delta,
                                "ratio": ratio,
                                "note": f"SPLIT {desc[:50]}",
                            },
                        )
                    )
            elif act in ("MERGER", "CORPORATE_ACTION", "SPINOFF") and pd.notna(qty):
                q = float(qty)
                cash = float(amt) if pd.notna(amt) else 0.0
                parsed = cash_from_merger_description(desc, q)
                if parsed is not None:
                    cash = parsed
                dest = incoming_symbol_from_corp(desc, sym, act, q)
                conversion = None
                if q < -1e-12:
                    conversion = parse_stock_merger_conversion(desc, abs(q))
                if dest and q > _EPS:
                    events.append(
                        (
                            pd.Timestamp(dt),
                            2,
                            dest,
                            {
                                "kind": "incoming",
                                "qty": q,
                                "cost": abs(cash) if cash > _EPS else 0.0,
                                "note": f"{act} {sym}→{dest} {desc[:40]}",
                            },
                        )
                    )
                else:
                    payload = {
                        "kind": "merger",
                        "qty": q,
                        "cash": abs(cash),
                        "desc": desc,
                        "note": f"{act} {desc[:50]}",
                        "cash_from_desc": cash_from_merger_description,
                    }
                    if conversion:
                        payload["new_symbol"] = conversion[0]
                        payload["new_qty"] = conversion[1]
                    events.append((pd.Timestamp(dt), 2, sym, payload))

    # One split per symbol/day/ratio so +delta and -old CUSIP rows are not applied twice.
    split_seen: set[tuple] = set()
    deduped: list[tuple[pd.Timestamp, int, str, dict]] = []
    for ev in events:
        dt, prio, ev_sym, payload = ev
        if payload.get("kind") == "split":
            ratio = payload.get("ratio")
            key = (
                ev_sym,
                pd.Timestamp(dt).normalize(),
                round(float(ratio), 8) if ratio else round(float(payload.get("qty") or 0), 4),
            )
            if key in split_seen:
                continue
            split_seen.add(key)
        deduped.append(ev)
    deduped.sort(key=lambda e: (e[0], e[1], e[2]))
    return deduped


def run_fifo_ledger(
    trades: pd.DataFrame,
    corporate: pd.DataFrame | None = None,
    *,
    marks: dict[str, tuple[float | None, object]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return (symbol_summary, batch_rows).

    Batch rows are FIFO matches (Status=MATCHED), leftover long lots (OPEN),
    and sells with no buy lot booked as realized LOSS.
    """
    trade_cash_amount, signed_quantity, cash_from_merger = _import_trade_helpers()
    events = _build_events(
        trades,
        corporate,
        trade_cash_amount=trade_cash_amount,
        signed_quantity=signed_quantity,
        cash_from_merger_description=cash_from_merger,
    )
    books: dict[str, _SymbolBook] = {}
    batch_rows: list[dict] = []

    for dt, _prio, sym, payload in events:
        book = books.setdefault(sym, _SymbolBook())
        kind = payload["kind"]

        if kind == "buy":
            qty = float(payload["qty"])
            cash = float(payload["cash"])
            if qty <= _EPS:
                continue
            book.buy_qty += qty
            book.buy_cost += cash
            book.buy_trades += 1
            book.note_buy_date(dt)
            remaining, realized = _match_against_queue(
                book.shorts,
                remaining=qty,
                closing_cash=cash,
                closing_qty=qty,
                closing_date=dt,
                closing_is_sell=False,
                symbol=sym,
                rows=batch_rows,
            )
            book.realized += realized
            if remaining > _EPS:
                price = _unit_price(cash, qty, payload.get("price"))
                leftover_cost = cash * (remaining / qty)
                book.longs.append(_Lot(qty=remaining, cost=leftover_cost, price=price, trade_date=dt))

        elif kind == "sell":
            qty = float(payload["qty"])
            cash = float(payload["cash"])
            if qty <= _EPS:
                continue
            book.sell_qty += qty
            book.sell_proceeds += cash
            book.sell_trades += 1
            book.note_sell_date(dt)
            remaining, realized = _match_against_queue(
                book.longs,
                remaining=qty,
                closing_cash=cash,
                closing_qty=qty,
                closing_date=dt,
                closing_is_sell=True,
                symbol=sym,
                rows=batch_rows,
            )
            book.realized += realized
            if remaining > _EPS:
                price = _unit_price(cash, qty, payload.get("price"))
                leftover_proceeds = cash * (remaining / qty)
                book.shorts.append(
                    _Lot(qty=remaining, cost=leftover_proceeds, price=price, trade_date=dt)
                )

        elif kind == "split":
            book.apply_split(
                float(payload.get("qty") or 0),
                payload["note"],
                ratio=payload.get("ratio"),
            )

        elif kind == "incoming":
            qty = float(payload["qty"])
            cost = float(payload.get("cost") or 0.0)
            if qty <= _EPS:
                continue
            price = _unit_price(cost, qty)
            book.longs.append(_Lot(qty=qty, cost=cost, price=price, trade_date=dt))
            book.note_buy_date(dt)
            book.corp_notes.append(str(payload.get("note") or "incoming shares"))

        elif kind == "merger":
            q = float(payload["qty"])
            cash = float(payload["cash"])
            desc = str(payload.get("desc") or "")
            note = str(payload.get("note") or "")
            fn = payload.get("cash_from_desc") or cash_from_merger
            if q < -1e-12:
                sold = abs(q)
                if cash <= _EPS:
                    parsed = fn(desc, q) if fn else None
                    cash = float(parsed) if parsed else 0.0
                new_sym = payload.get("new_symbol")
                new_qty = float(payload.get("new_qty") or 0.0)
                if new_sym and new_qty > _EPS:
                    qty_taken, cost_taken = book.take_longs(sold)
                    stock_cost = max(cost_taken - cash, 0.0)
                    cash_cost = cost_taken - stock_cost
                    if cash > _EPS:
                        book.sell_qty += qty_taken
                        book.sell_proceeds += cash
                        book.sell_trades += 1
                        book.note_sell_date(dt)
                        book.realized += cash - cash_cost
                    leftover_close = sold - qty_taken
                    dest = books.setdefault(str(new_sym), _SymbolBook())
                    dest_price = _unit_price(stock_cost, new_qty)
                    dest.longs.append(
                        _Lot(qty=new_qty, cost=stock_cost, price=dest_price, trade_date=dt)
                    )
                    dest.note_buy_date(dt)
                    dest.corp_notes.append(f"from {sym} merger → {new_qty:.4f} sh")
                    if leftover_close > _EPS:
                        book.shorts.append(
                            _Lot(
                                qty=leftover_close,
                                cost=cash * (leftover_close / sold) if sold > _EPS else 0.0,
                                price=_unit_price(cash, sold),
                                trade_date=dt,
                            )
                        )
                    book.corp_notes.append(note)
                elif cash > _EPS:
                    book.sell_qty += sold
                    book.sell_proceeds += cash
                    book.sell_trades += 1
                    book.note_sell_date(dt)
                    remaining, realized = _match_against_queue(
                        book.longs,
                        remaining=sold,
                        closing_cash=cash,
                        closing_qty=sold,
                        closing_date=dt,
                        closing_is_sell=True,
                        symbol=sym,
                        rows=batch_rows,
                    )
                    book.realized += realized
                    if remaining > _EPS:
                        leftover_proceeds = cash * (remaining / sold) if sold > _EPS else cash
                        price = _unit_price(cash, sold)
                        book.shorts.append(
                            _Lot(
                                qty=remaining,
                                cost=leftover_proceeds,
                                price=price,
                                trade_date=dt,
                            )
                        )
                else:
                    # Stock-for-stock: drop qty, keep cost on remaining lots proportionally.
                    remaining = sold
                    while remaining > _EPS and book.longs:
                        lot = book.longs[0]
                        take = min(lot.qty, remaining)
                        lot.take(take)
                        remaining -= take
                        if lot.qty <= _EPS:
                            book.longs.popleft()
                book.corp_notes.append(note)
            elif q > 1e-12:
                price = _unit_price(cash, q)
                book.longs.append(_Lot(qty=q, cost=cash, price=price, trade_date=dt))
                book.corp_notes.append(note)

    marks = marks or {}
    open_rows: list[dict] = []
    summary_rows: list[dict] = []

    for sym, book in sorted(books.items()):
        unmatched_loss = 0.0
        for lot in book.shorts:
            if lot.qty <= _EPS:
                continue
            loss = -abs(float(lot.cost))
            unmatched_loss += loss
            loss_row = _batch_row(
                symbol=sym,
                buy_qty=0.0,
                buy_price=0.0,
                buy_date=None,
                sell_qty=lot.qty,
                sell_price=lot.price,
                sell_date=lot.trade_date,
                matched_qty=lot.qty,
                buy_cost=0.0,
                sell_proceeds=lot.cost,
                pnl=loss,
                status="LOSS",
            )
            loss_row["Batch_PnL_Pct"] = -100.0
            open_rows.append(loss_row)
        if abs(unmatched_loss) > _EPS:
            book.realized += unmatched_loss
            book.corp_notes.append("Unmatched sells booked as LOSS (no buy lot)")

        open_qty = sum(lot.qty for lot in book.longs)
        remaining_cost = book.remaining_cost()
        mark = None
        unrealized = None
        if abs(open_qty) > 1e-6 and open_qty > 0:
            price, _as_of = marks.get(sym, (None, None))
            mark = price
            if price is not None:
                unrealized = open_qty * float(price) - remaining_cost

        for lot in book.longs:
            if lot.qty <= _EPS:
                continue
            lot_unreal = None
            if mark is not None:
                lot_unreal = lot.qty * float(mark) - lot.cost
            open_rows.append(
                _batch_row(
                    symbol=sym,
                    buy_qty=lot.qty,
                    buy_price=lot.price,
                    buy_date=lot.trade_date,
                    sell_qty=None,
                    sell_price=mark,
                    sell_date=None,
                    matched_qty=None,
                    buy_cost=lot.cost,
                    sell_proceeds=lot.qty * float(mark) if mark is not None else None,
                    pnl=lot_unreal,
                    status="OPEN",
                    mark_price=mark,
                )
            )

        avg_buy = (book.buy_cost / book.buy_qty) if book.buy_qty > _EPS else None
        avg_sell = (book.sell_proceeds / book.sell_qty) if book.sell_qty > _EPS else None
        total = book.realized
        if unrealized is not None:
            total += unrealized

        if abs(open_qty) > 1e-6:
            result = "OPEN"
        elif book.realized > 1e-2:
            result = "PROFIT"
        elif book.realized < -1e-2:
            result = "LOSS"
        else:
            result = "BREAKEVEN"

        summary_rows.append(
            {
                "Symbol": sym,
                "Result": result,
                "Buy_Qty": _round_qty(book.buy_qty),
                "Avg_Buy_Price": _round_price(avg_buy) if avg_buy is not None else None,
                "Sell_Qty": _round_qty(book.sell_qty),
                "Avg_Sell_Price": _round_price(avg_sell) if avg_sell is not None else None,
                "Open_Qty": _round_qty(open_qty),
                "Buy_Cost": _round_money(book.buy_cost),
                "Sell_Proceeds": _round_money(book.sell_proceeds),
                "Realized_PnL": _round_money(book.realized),
                "Unrealized_PnL": _round_money(unrealized) if unrealized is not None else None,
                "Total_PnL": _round_money(total),
                "Mark_Price": _round_price(mark) if mark is not None else None,
                "First_Buy_Date": _as_date(book.first_buy),
                "Last_Sell_Date": _as_date(book.last_sell),
                "Buy_Trades": book.buy_trades,
                "Sell_Trades": book.sell_trades,
                "Corp_Notes": "; ".join(book.corp_notes[:3]) if book.corp_notes else "",
            }
        )

    summary = pd.DataFrame(summary_rows)
    batches = pd.DataFrame(batch_rows + open_rows)
    if not batches.empty:
        status_order = {"LOSS": 0, "OPEN": 1, "MATCHED": 2}
        batches["_ord"] = batches["Status"].map(status_order).fillna(9)
        batches = batches.sort_values(
            ["Symbol", "_ord", "Buy_Date", "Sell_Date"],
            ascending=[True, True, True, True],
            na_position="last",
        ).drop(columns=["_ord"])
        batches = batches.reset_index(drop=True)
    if not summary.empty:
        result_order = {"LOSS": 0, "OPEN": 1, "BREAKEVEN": 2, "PROFIT": 3}
        summary["_ord"] = summary["Result"].map(result_order).fillna(9)
        summary = summary.sort_values(
            ["_ord", "Realized_PnL"],
            ascending=[True, True],
        ).drop(columns=["_ord"]).reset_index(drop=True)
    return summary, batches
