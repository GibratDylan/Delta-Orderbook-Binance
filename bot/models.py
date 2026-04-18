from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Dict, Iterable, List, Tuple


Price = float
Quantity = float
Level = Tuple[Price, Quantity]


@dataclass
class OrderBook:
    bids: Dict[Price, Quantity] = field(default_factory=dict)
    asks: Dict[Price, Quantity] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def replace(self, bids: Iterable[Level], asks: Iterable[Level]) -> None:
        self.bids = {float(price): float(qty) for price, qty in bids if float(qty) > 0.0}
        self.asks = {float(price): float(qty) for price, qty in asks if float(qty) > 0.0}
        self.updated_at = time.time()

    def apply(self, side: str, levels: Iterable[Level]) -> None:
        target = self.bids if side == "bids" else self.asks
        for price, qty in levels:
            p = float(price)
            q = float(qty)
            if q > 0.0:
                target[p] = q
            else:
                target.pop(p, None)
        self.updated_at = time.time()

    def best_bid(self) -> float | None:
        return max(self.bids.keys()) if self.bids else None

    def best_ask(self) -> float | None:
        return min(self.asks.keys()) if self.asks else None

    def spread_pct(self) -> float | None:
        ask = self.best_ask()
        bid = self.best_bid()
        if ask is None or bid is None or ask <= 0:
            return None
        return abs(ask - bid) / ask * 100.0

    def is_consistent(self) -> bool:
        bid = self.best_bid()
        ask = self.best_ask()
        if bid is None or ask is None:
            return False
        return bid <= ask


@dataclass(frozen=True)
class Decision:
    should_open: bool
    reason: str
    delta: float | None
    spread_pct: float | None


def top_levels_qty(book: OrderBook, depth: int) -> Tuple[float, float]:
    bid_prices = sorted(book.bids.keys(), reverse=True)[:depth]
    ask_prices = sorted(book.asks.keys())[:depth]
    bid_qty = sum(book.bids[p] for p in bid_prices)
    ask_qty = sum(book.asks[p] for p in ask_prices)
    return bid_qty, ask_qty


def all_fresh(orderbooks: List[OrderBook], max_age_seconds: float) -> bool:
    now = time.time()
    for book in orderbooks:
        if now - book.updated_at > max_age_seconds:
            return False
    return True
