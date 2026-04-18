from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .models import OrderBook
from .orderbook import apply_bybit_orderbook_update, convert_binance_depth


@dataclass
class MarketState:
    bybit_books: Dict[str, OrderBook] = field(default_factory=dict)
    binance_books: Dict[str, OrderBook] = field(default_factory=dict)
    limit_price: Dict[str, float] = field(default_factory=dict)

    def update_bybit(self, topic: str, message: dict) -> None:
        book = self.bybit_books.get(topic) or OrderBook()
        self.bybit_books[topic] = apply_bybit_orderbook_update(book, message)

    def update_binance(self, stream_name: str, payload: dict) -> None:
        self.binance_books[stream_name] = convert_binance_depth(payload)

    def update_limit_price(self, message: dict) -> None:
        payload = message.get("data") or {}
        asks = payload.get("a") or []
        bids = payload.get("b") or []
        if asks:
            self.limit_price["ask"] = float(asks[0][0])
        if bids:
            self.limit_price["bid"] = float(bids[0][0])

    def get_book(self, key: str) -> Optional[OrderBook]:
        if key in self.bybit_books:
            return self.bybit_books[key]
        return self.binance_books.get(key)
