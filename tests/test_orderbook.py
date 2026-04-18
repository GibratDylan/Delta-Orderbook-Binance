import time
import unittest

from bot.analytics import SignalEngine
from bot.config import StrategyConfig
from bot.models import OrderBook
from bot.orderbook import apply_bybit_orderbook_update, compute_delta, convert_binance_depth


class TestOrderbookUpdates(unittest.TestCase):
    def test_snapshot_then_delta_delete_level_is_safe(self):
        book = OrderBook()

        snapshot = {
            "type": "snapshot",
            "data": {
                "b": [["100", "1.5"], ["99", "2.0"]],
                "a": [["101", "1.2"], ["102", "3.1"]],
            },
        }
        delta = {
            "type": "delta",
            "data": {
                "b": [["100", "0"], ["98", "1.0"]],
                "a": [["102", "0"], ["103", "0.8"]],
            },
        }

        apply_bybit_orderbook_update(book, snapshot)
        apply_bybit_orderbook_update(book, delta)

        self.assertNotIn(100.0, book.bids)
        self.assertIn(98.0, book.bids)
        self.assertNotIn(102.0, book.asks)
        self.assertIn(103.0, book.asks)

    def test_convert_binance_depth(self):
        payload = {
            "b": [["100", "1"], ["99", "2"]],
            "a": [["101", "3"], ["102", "4"]],
        }
        book = convert_binance_depth(payload)
        self.assertEqual(book.bids[100.0], 1.0)
        self.assertEqual(book.asks[101.0], 3.0)


class TestSignals(unittest.TestCase):
    def test_compute_delta(self):
        b1 = OrderBook(bids={100.0: 3.0}, asks={101.0: 1.0}, updated_at=time.time())
        b2 = OrderBook(bids={100.0: 2.0}, asks={101.0: 4.0}, updated_at=time.time())
        delta = compute_delta([b1, b2], depth=20)
        self.assertAlmostEqual(delta, 0.0)

    def test_decision_guards_stale_data(self):
        strategy = StrategyConfig(max_data_age_seconds=0.5, orderbook_depth=1)
        engine = SignalEngine(strategy)

        stale_book = OrderBook(
            bids={100.0: 2.0},
            asks={101.0: 1.0},
            updated_at=time.time() - 10,
        )

        decision = engine.evaluate([stale_book])
        self.assertFalse(decision.should_open)
        self.assertEqual(decision.reason, "stale_data")

    def test_decision_trigger(self):
        strategy = StrategyConfig(
            delta_threshold=0.2,
            max_spread_pct=2.0,
            orderbook_depth=1,
            max_data_age_seconds=10,
        )
        engine = SignalEngine(strategy)

        bullish = OrderBook(
            bids={100.0: 9.0},
            asks={101.0: 1.0},
            updated_at=time.time(),
        )
        decision = engine.evaluate([bullish])
        self.assertTrue(decision.should_open)
        self.assertEqual(decision.reason, "delta_triggered")


if __name__ == "__main__":
    unittest.main()
