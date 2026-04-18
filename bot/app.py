from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import List

from .analytics import SignalEngine
from .config import AppConfig, as_safe_dict, build_config
from .execution import BinanceExecutor, DryRunExecutor
from .ingestion import MarketState
from .logger import setup_logging
from .streams import ReconnectingWebSocket


class OrderbookTradingApp:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = setup_logging(config.log_level)
        self.state = MarketState()
        self.signal_engine = SignalEngine(config.strategy)

        self.stop_event = asyncio.Event()
        self.tasks: List[asyncio.Task] = []
        self.close_tasks: List[asyncio.Task] = []

        self.public_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)
        self.binance_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)
        self.linear_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)

        self.current_positions = 0

        if self.config.execution.dry_run:
            self.executor = DryRunExecutor(
                symbol=self.config.execution.symbol,
                qty=self.config.strategy.order_qty,
                logger=self.logger,
            )
        else:
            self.executor = BinanceExecutor(
                api_key=self.config.execution.binance_api_key,
                api_secret=self.config.execution.binance_api_secret,
                symbol=self.config.execution.symbol,
                qty=self.config.strategy.order_qty,
                logger=self.logger,
            )

    async def _enqueue(self, queue: asyncio.Queue, message: dict) -> None:
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            _ = queue.get_nowait()
            queue.put_nowait(message)

    async def _public_handler(self, message: dict) -> None:
        if message.get("data"):
            await self._enqueue(self.public_queue, message)

    async def _linear_handler(self, message: dict) -> None:
        if message.get("data"):
            await self._enqueue(self.linear_queue, message)

    async def _binance_handler(self, message: dict) -> None:
        if message.get("data") and message.get("stream"):
            await self._enqueue(self.binance_queue, message)

    def _spawn(self, name: str, coro) -> None:
        task = asyncio.create_task(self._task_guard(name, coro), name=name)
        self.tasks.append(task)

    async def _task_guard(self, name: str, coro) -> None:
        try:
            await coro
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger.exception("task crashed name=%s", name)
            self.stop_event.set()

    async def _consume_bybit_public(self) -> None:
        while not self.stop_event.is_set():
            message = await self.public_queue.get()
            topic = message.get("topic")
            if not topic:
                continue
            self.state.update_bybit(topic, message)

    async def _consume_bybit_linear(self) -> None:
        while not self.stop_event.is_set():
            message = await self.linear_queue.get()
            self.state.update_limit_price(message)

    async def _consume_binance(self) -> None:
        while not self.stop_event.is_set():
            message = await self.binance_queue.get()
            stream = message.get("stream")
            payload = message.get("data")
            if stream and payload:
                self.state.update_binance(stream, payload)

    async def _delayed_close(self, seconds: int) -> None:
        await asyncio.sleep(seconds)
        await self.executor.close_long()
        self.current_positions = max(0, self.current_positions - 1)
        self.logger.info("position closed open_positions=%s", self.current_positions)

    async def _decision_loop(self) -> None:
        strategy = self.config.strategy
        required_books = list(self.config.streams.bybit_topics or []) + [
            "btcusdt@depth20@100ms",
            "btcfdusd@depth20@100ms",
        ]

        while not self.stop_event.is_set():
            books = []
            for name in required_books:
                book = self.state.get_book(name)
                if book is not None:
                    books.append(book)

            decision = self.signal_engine.evaluate(books)
            self.logger.info(
                "decision open=%s reason=%s delta=%s spread_pct=%s pos=%s",
                decision.should_open,
                decision.reason,
                decision.delta,
                decision.spread_pct,
                self.current_positions,
            )

            if (
                decision.should_open
                and self.current_positions < strategy.max_long_positions
            ):
                await self.executor.open_long()
                self.current_positions += 1
                self.logger.info("position opened open_positions=%s", self.current_positions)
                close_task = asyncio.create_task(self._delayed_close(strategy.hold_seconds))
                self.close_tasks.append(close_task)

            await asyncio.sleep(strategy.decision_interval_seconds)

    def _build_streams(self) -> List[ReconnectingWebSocket]:
        streams = self.config.streams
        return [
            ReconnectingWebSocket(
                name="bybit_public",
                url=streams.bybit_public_url,
                subscribe_payload={"op": "subscribe", "args": streams.bybit_topics or []},
                on_message=self._public_handler,
                logger=self.logger,
                recv_timeout_seconds=streams.recv_timeout_seconds,
                base_backoff_seconds=streams.reconnect_base_seconds,
                max_backoff_seconds=streams.reconnect_max_seconds,
                jitter_seconds=streams.reconnect_jitter_seconds,
            ),
            ReconnectingWebSocket(
                name="bybit_linear",
                url=streams.bybit_linear_url,
                subscribe_payload={"op": "subscribe", "args": streams.bybit_linear_topics or []},
                on_message=self._linear_handler,
                logger=self.logger,
                recv_timeout_seconds=streams.recv_timeout_seconds,
                base_backoff_seconds=streams.reconnect_base_seconds,
                max_backoff_seconds=streams.reconnect_max_seconds,
                jitter_seconds=streams.reconnect_jitter_seconds,
            ),
            ReconnectingWebSocket(
                name="binance",
                url=streams.binance_stream_url,
                subscribe_payload={"method": "SUBSCRIBE", "params": [], "id": 1},
                on_message=self._binance_handler,
                logger=self.logger,
                recv_timeout_seconds=streams.recv_timeout_seconds,
                base_backoff_seconds=streams.reconnect_base_seconds,
                max_backoff_seconds=streams.reconnect_max_seconds,
                jitter_seconds=streams.reconnect_jitter_seconds,
            ),
        ]

    async def run(self) -> None:
        self.logger.info("starting app config=%s", as_safe_dict(self.config))
        if not self.config.execution.dry_run:
            if not self.config.execution.binance_api_key or not self.config.execution.binance_api_secret:
                raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET are required when DRY_RUN=false")

        streams = self._build_streams()

        self._spawn("consume_bybit_public", self._consume_bybit_public())
        self._spawn("consume_bybit_linear", self._consume_bybit_linear())
        self._spawn("consume_binance", self._consume_binance())
        self._spawn("decision_loop", self._decision_loop())

        for stream in streams:
            self._spawn(f"stream_{stream.name}", stream.run(self.stop_event))

        try:
            await asyncio.gather(*self.tasks)
        finally:
            self.stop_event.set()
            for task in self.tasks:
                task.cancel()
            for task in self.close_tasks:
                task.cancel()
            for task in self.tasks + self.close_tasks:
                with suppress(asyncio.CancelledError):
                    await task
            self.logger.info("shutdown complete")


def run() -> None:
    config = build_config()
    app = OrderbookTradingApp(config)
    asyncio.run(app.run())
