from __future__ import annotations

import asyncio


class DryRunExecutor:
    def __init__(self, symbol: str, qty: float, logger):
        self.symbol = symbol
        self.qty = qty
        self.logger = logger

    async def open_long(self) -> None:
        self.logger.info("dry_run open_long symbol=%s qty=%s", self.symbol, self.qty)

    async def close_long(self) -> None:
        self.logger.info("dry_run close_long symbol=%s qty=%s", self.symbol, self.qty)


class BinanceExecutor:
    def __init__(self, *, api_key: str, api_secret: str, symbol: str, qty: float, logger):
        self.symbol = symbol
        self.qty = qty
        self.logger = logger
        self.api_key = api_key
        self.api_secret = api_secret
        self._client = None

    def _get_client(self):
        if self._client is None:
            from binance.client import Client

            self._client = Client(self.api_key, self.api_secret)
        return self._client

    async def open_long(self) -> None:
        self.logger.info("live open_long symbol=%s qty=%s", self.symbol, self.qty)
        client = self._get_client()
        await asyncio.to_thread(
            client.order_market_buy,
            symbol=self.symbol,
            quantity=self.qty,
        )

    async def close_long(self) -> None:
        self.logger.info("live close_long symbol=%s qty=%s", self.symbol, self.qty)
        client = self._get_client()
        await asyncio.to_thread(
            client.order_market_sell,
            symbol=self.symbol,
            quantity=self.qty,
        )
