from __future__ import annotations

from typing import List

from .config import StrategyConfig
from .models import Decision, all_fresh
from .orderbook import compute_delta, has_minimum_depth


class SignalEngine:
    def __init__(self, strategy: StrategyConfig):
        self.strategy = strategy

    def evaluate(self, books: List) -> Decision:
        if not books:
            return Decision(False, "missing_orderbooks", None, None)

        if any(not has_minimum_depth(book, self.strategy.orderbook_depth) for book in books):
            return Decision(False, "insufficient_depth", None, None)

        if any(not book.is_consistent() for book in books):
            return Decision(False, "inconsistent_orderbook", None, None)

        if not all_fresh(books, self.strategy.max_data_age_seconds):
            return Decision(False, "stale_data", None, None)

        delta = compute_delta(books, depth=self.strategy.orderbook_depth)
        spread = books[0].spread_pct()

        if delta is None or spread is None:
            return Decision(False, "invalid_signal_input", delta, spread)

        if spread > self.strategy.max_spread_pct:
            return Decision(False, "spread_too_wide", delta, spread)

        if delta > self.strategy.delta_threshold:
            return Decision(True, "delta_triggered", delta, spread)

        return Decision(False, "delta_below_threshold", delta, spread)
