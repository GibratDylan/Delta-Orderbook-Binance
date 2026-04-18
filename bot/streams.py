from __future__ import annotations

import asyncio
import json
import random
from typing import Awaitable, Callable, Optional

from websockets import connect
from websockets.exceptions import ConnectionClosed


MessageHandler = Callable[[dict], Awaitable[None]]


class ReconnectingWebSocket:
    def __init__(
        self,
        *,
        name: str,
        url: str,
        subscribe_payload: dict,
        on_message: MessageHandler,
        logger,
        recv_timeout_seconds: float,
        base_backoff_seconds: float,
        max_backoff_seconds: float,
        jitter_seconds: float,
    ) -> None:
        self.name = name
        self.url = url
        self.subscribe_payload = subscribe_payload
        self.on_message = on_message
        self.logger = logger
        self.recv_timeout_seconds = recv_timeout_seconds
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.jitter_seconds = jitter_seconds

    async def run(self, stop_event: asyncio.Event) -> None:
        attempt = 0
        while not stop_event.is_set():
            wait_seconds = min(
                self.max_backoff_seconds,
                self.base_backoff_seconds * (2**attempt),
            ) + random.uniform(0.0, self.jitter_seconds)
            try:
                self.logger.info("connecting stream=%s url=%s", self.name, self.url)
                async with connect(self.url, compression=None) as ws:
                    attempt = 0
                    await ws.send(json.dumps(self.subscribe_payload))
                    self.logger.info("subscribed stream=%s payload=%s", self.name, self.subscribe_payload)

                    while not stop_event.is_set():
                        raw = await asyncio.wait_for(ws.recv(), timeout=self.recv_timeout_seconds)
                        message = json.loads(raw)
                        await self.on_message(message)
            except asyncio.TimeoutError:
                self.logger.warning("stream timeout stream=%s reconnecting", self.name)
                attempt += 1
            except ConnectionClosed as exc:
                self.logger.warning(
                    "stream closed stream=%s code=%s reason=%s reconnecting",
                    self.name,
                    exc.code,
                    exc.reason,
                )
                attempt += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("stream failure stream=%s reconnecting", self.name)
                attempt += 1

            if stop_event.is_set():
                break
            await asyncio.sleep(wait_seconds)
