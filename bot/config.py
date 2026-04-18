from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Dict, List


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    return float(value)


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _parse_list(value: str | None, default: List[str]) -> List[str]:
    if value is None:
        return default
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or default


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class StrategyConfig:
    delta_threshold: float = 0.9
    max_spread_pct: float = 0.08
    max_long_positions: int = 1
    order_qty: float = 0.004
    reduced_order_qty: float = 0.003
    hold_seconds: int = 120
    decision_interval_seconds: float = 0.25
    max_data_age_seconds: float = 2.0
    orderbook_depth: int = 20
    primary_topic: str = "orderbook.50.BTCUSDC"


@dataclass(frozen=True)
class StreamConfig:
    bybit_public_url: str = "wss://stream.bybit.com/v5/public/spot"
    bybit_linear_url: str = "wss://stream.bybit.com/v5/public/linear"
    bybit_topics: List[str] | None = None
    bybit_linear_topics: List[str] | None = None
    binance_stream_url: str = "wss://stream.binance.com:9443/stream?streams=btcusdt@depth20@100ms/btcfdusd@depth20@100ms"
    reconnect_base_seconds: float = 0.5
    reconnect_max_seconds: float = 20.0
    reconnect_jitter_seconds: float = 0.5
    recv_timeout_seconds: float = 60.0


@dataclass(frozen=True)
class ExecutionConfig:
    dry_run: bool = True
    exchange: str = "binance"
    symbol: str = "BTCFDUSD"
    binance_api_key: str = ""
    binance_api_secret: str = ""


@dataclass(frozen=True)
class AppConfig:
    log_level: str
    strategy: StrategyConfig
    streams: StreamConfig
    execution: ExecutionConfig


def build_config() -> AppConfig:
    load_env_file()

    bybit_topics = _parse_list(
        os.getenv("BYBIT_TOPICS"),
        ["orderbook.50.BTCUSDC", "orderbook.50.BTCUSDT"],
    )
    bybit_linear_topics = _parse_list(
        os.getenv("BYBIT_LINEAR_TOPICS"),
        ["orderbook.1.BTCUSDT"],
    )

    strategy = StrategyConfig(
        delta_threshold=_parse_float(os.getenv("DELTA_THRESHOLD"), 0.9),
        max_spread_pct=_parse_float(os.getenv("MAX_SPREAD_PCT"), 0.08),
        max_long_positions=_parse_int(os.getenv("MAX_LONG_POSITIONS"), 1),
        order_qty=_parse_float(os.getenv("ORDER_QTY"), 0.004),
        reduced_order_qty=_parse_float(os.getenv("REDUCED_ORDER_QTY"), 0.003),
        hold_seconds=_parse_int(os.getenv("HOLD_SECONDS"), 120),
        decision_interval_seconds=_parse_float(os.getenv("DECISION_INTERVAL_SECONDS"), 0.25),
        max_data_age_seconds=_parse_float(os.getenv("MAX_DATA_AGE_SECONDS"), 2.0),
        orderbook_depth=_parse_int(os.getenv("ORDERBOOK_DEPTH"), 20),
        primary_topic=os.getenv("PRIMARY_TOPIC", "orderbook.50.BTCUSDC"),
    )

    streams = StreamConfig(
        bybit_public_url=os.getenv("BYBIT_PUBLIC_WS_URL", "wss://stream.bybit.com/v5/public/spot"),
        bybit_linear_url=os.getenv("BYBIT_LINEAR_WS_URL", "wss://stream.bybit.com/v5/public/linear"),
        bybit_topics=bybit_topics,
        bybit_linear_topics=bybit_linear_topics,
        binance_stream_url=os.getenv(
            "BINANCE_WS_URL",
            "wss://stream.binance.com:9443/stream?streams=btcusdt@depth20@100ms/btcfdusd@depth20@100ms",
        ),
        reconnect_base_seconds=_parse_float(os.getenv("RECONNECT_BASE_SECONDS"), 0.5),
        reconnect_max_seconds=_parse_float(os.getenv("RECONNECT_MAX_SECONDS"), 20.0),
        reconnect_jitter_seconds=_parse_float(os.getenv("RECONNECT_JITTER_SECONDS"), 0.5),
        recv_timeout_seconds=_parse_float(os.getenv("RECV_TIMEOUT_SECONDS"), 60.0),
    )

    execution = ExecutionConfig(
        dry_run=_parse_bool(os.getenv("DRY_RUN"), True),
        exchange=os.getenv("EXECUTION_EXCHANGE", "binance"),
        symbol=os.getenv("TRADING_SYMBOL", "BTCFDUSD"),
        binance_api_key=os.getenv("BINANCE_API_KEY", ""),
        binance_api_secret=os.getenv("BINANCE_API_SECRET", ""),
    )

    return AppConfig(
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        strategy=strategy,
        streams=streams,
        execution=execution,
    )


def as_safe_dict(config: AppConfig) -> Dict[str, str]:
    return {
        "log_level": config.log_level,
        "dry_run": str(config.execution.dry_run),
        "exchange": config.execution.exchange,
        "symbol": config.execution.symbol,
        "bybit_topics": ",".join(config.streams.bybit_topics or []),
        "binance_stream_url": config.streams.binance_stream_url,
    }
