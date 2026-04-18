from __future__ import annotations

from typing import Dict, Iterable, Tuple

from .models import OrderBook, top_levels_qty


def apply_bybit_orderbook_update(orderbook: OrderBook, message: Dict) -> OrderBook:
    msg_type = message.get("type")
    payload = message.get("data") or {}

    bids = payload.get("b") or []
    asks = payload.get("a") or []

    if msg_type == "snapshot":
        orderbook.replace(bids, asks)
        return orderbook

    if msg_type == "delta":
        orderbook.apply("bids", bids)
        orderbook.apply("asks", asks)
        return orderbook

    return orderbook


def convert_binance_depth(payload: Dict) -> OrderBook:
    book = OrderBook()
    bids = payload.get("b") or payload.get("bids") or []
    asks = payload.get("a") or payload.get("asks") or []
    book.replace(bids, asks)
    return book


def compute_delta(orderbooks: Iterable[OrderBook], depth: int) -> float | None:
    total_bid = 0.0
    total_ask = 0.0
    for book in orderbooks:
        bid_qty, ask_qty = top_levels_qty(book, depth)
        total_bid += bid_qty
        total_ask += ask_qty
    total = total_bid + total_ask
    if total <= 0:
        return None
    return (total_bid - total_ask) / total


def safe_best_prices(orderbook: OrderBook) -> Tuple[float | None, float | None]:
    return orderbook.best_bid(), orderbook.best_ask()


def has_minimum_depth(orderbook: OrderBook, depth: int) -> bool:
    return len(orderbook.bids) >= depth and len(orderbook.asks) >= depth
