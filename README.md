# Orderbook Trading Bot

An orderbook trading bot focused on real-time execution, with an async architecture, DRY_RUN-first workflow, and clear separation between ingestion, analytics, and execution.

This project has one clear objective: capture microstructure orderbook imbalances while keeping a robust production-ready foundation.

## Disclaimer

This repository is shared for learning purposes only.

It is not finished and must not be used in production, with real funds, or as a real trading decision system.

Some parts can be incomplete, experimental, or wrong, and results are not guaranteed.

## Description

Orderbook Trading Bot uses live orderbook flow (bids/asks) to detect buy/sell pressure imbalances, estimate slippage risk, and trigger trading decisions through explicit rules.

The engine is built around:

- **WebSocket Streaming**: continuous market depth updates
- **Incremental Ingestion**: local orderbook reconstruction with consistency checks
- **Delta Signal**: bid vs ask pressure comparison over a configurable depth
- **Quality Filters**: max spread, minimum depth, and anti-noise safeguards
- **Execution Modes**: full DRY_RUN simulation, then live Binance execution
- **Async Supervision**: resilient tasks with exponential backoff and jitter

The system is designed to evolve easily: modules are decoupled, testable, and replaceable without breaking the full pipeline.

## Preview

![Bot Preview](assets/Screenshot%20From%202026-04-19%2015-15-32.png)

## Project Structure

```text
Orderbook/
├── bot_orderbook_main.py               # Entry point
├── Dockerfile                          # Container image definition
├── docker-compose.yml                  # Local container orchestration
├── .dockerignore                       # Excludes files from build context
├── README.md                           # Project documentation
├── bot/
│   ├── __init__.py
│   ├── app.py                          # Async bootstrap and lifecycle
│   ├── config.py                       # Config and env loading
│   ├── streams.py                      # WebSocket + reconnect logic
│   ├── ingestion.py                    # Market state (orderbook/prices)
│   ├── orderbook.py                    # Orderbook update routines
│   ├── analytics.py                    # Delta, signal, and filters
│   ├── execution.py                    # DRY_RUN / live execution
│   ├── logger.py                       # Standardized logging
│   └── models.py                       # Data structures
└── tests/
    ├── __init__.py
   └── test_orderbook.py               # Core unit tests
```

## Instructions

### Prerequisites

- Python 3.10+
- Stable network access to Binance endpoints
- Binance API key/secret (live mode only)

### Installation

1. Move to the project folder:
   ```bash
   cd Orderbook
   ```

2. Install minimal dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

4. Start in safe simulation mode:
   ```bash
   DRY_RUN=true python bot_orderbook_main.py
   ```

### Docker

1. Create your runtime env file:
   ```bash
   cp .env.example .env
   ```

2. Build the image:
   ```bash
    make build
   ```

3. Run the bot in container:
   ```bash
    make up
   ```

4. Follow logs:
   ```bash
   docker compose logs -f bot
   ```

5. Stop the container:
   ```bash
    make down
    ```

### Makefile commands

The project includes a Makefile to manage Docker quickly.

- Build image:
   ```bash
   make build
   ```
- Start container in background:
   ```bash
   make up
   ```
- Stop and remove running containers:
   ```bash
   make down
   ```
- Stop containers and remove local images/volumes/orphans:
   ```bash
   make clean
   ```
- Run default full workflow (build + up):
   ```bash
   make all
   ```
- Recreate everything (clean + all):
   ```bash
   make re
   ```

### Usage

- **Simulation mode (recommended first)**
  ```bash
  DRY_RUN=true python bot_orderbook_main.py
  ```

- **Live mode (with valid API key/secret)**
  ```bash
  DRY_RUN=false python bot_orderbook_main.py
  ```

Critical variables:

- `DRY_RUN=true|false`
- `BINANCE_API_KEY` and `BINANCE_API_SECRET` (required if `DRY_RUN=false`)
- `DELTA_THRESHOLD`
- `MAX_SPREAD_PCT`
- `ORDERBOOK_DEPTH`

### How I used AI on this project

I used AI as a learning and coding assistant while building this bot, especially to move faster on architecture, debugging, and test coverage.

Concretely, I used it to:

- Break down modules step by step (`streams.py`, `ingestion.py`, `analytics.py`) when I needed a clearer mental model.
- Draft small refactors, then keep only the parts that improved readability or reliability.
- Generate test ideas and edge cases for orderbook logic.
- Investigate tracebacks and isolate likely root causes faster.
- Brainstorm performance checks and what metrics to compare before/after.

### Cleaning

There are no build artifacts specific to this module.

To quickly validate the local state:

```bash
python -m unittest discover -s tests -v
```

## Resources

### Exchanges and Microstructure

- Binance Spot API Docs: https://developers.binance.com/docs/binance-spot-api-docs/README
- Binance WebSocket Streams: https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams
- Order Book Basics (Investopedia): https://www.investopedia.com/terms/o/order-book.asp

### Trading Infrastructure and Latency

- AWS Global Infrastructure: https://aws.amazon.com/about-aws/global-infrastructure/
- Linux Network Tuning Guide (Red Hat): https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/
- Python asyncio docs: https://docs.python.org/3/library/asyncio.html

### Testing and Reliability

- Python unittest: https://docs.python.org/3/library/unittest.html
- Exponential Backoff patterns: https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/

## Difficulty and Solution

### Challenges Encountered

#### 1. **Latency race even with AWS near Binance**
**Difficulty**: Even when infrastructure was deployed in the same country as Binance servers and on AWS, the bot was still frequently outrun by faster traders.

**Why this happens**:
- Network distance is only one part of total latency
- Other traders use ultra-optimized stacks (C/C++, kernel bypass, co-located infra, FPGA)
- Serialization/deserialization overhead, Python scheduling, GC, and exchange order queueing add critical milliseconds
- The matching engine processes competitive order flow: being geographically close does not guarantee priority

**Implemented solution**:
- Reduced memory copies and per-tick CPU work
- Simplified the async pipeline to reduce internal latency
- Added quality filters (spread/depth) to avoid degraded fills
- Shifted strategy toward stronger statistical edge instead of pure speed racing

#### 2. **Local orderbook stability under high throughput**
**Difficulty**: During volatility spikes, keeping a coherent and usable local book in real time is difficult.

**Solution**: Incremental updates, consistency safeguards, and shared routines in `orderbook.py` to standardize update handling.

#### 3. **Avoiding micro-noise false signals**
**Difficulty**: Instantaneous deltas can flip quickly and produce low-quality entries.

**Solution**: Threshold confirmation, max spread check, and minimum depth validation before taking decisions.

#### 4. **Smooth transition from simulation to live trading**
**Difficulty**: Many strategies look good in theory but degrade in real execution.

**Solution**: DRY_RUN by default with explicit simulated open/close logs, then live activation only after behavioral validation.

### Key Takeaways

- Network latency alone is not enough; end-to-end execution path determines competitiveness.
- An orderbook signal must be filtered by execution quality (spread, depth, liquidity).
- DRY_RUN is essential to secure production rollout.

## Features

### Trading principle with orderbook deltas

The core of the strategy is a **depth delta** computed on the first levels of the book:

$$
\Delta = \sum_{i=1}^{N} \text{BidSize}_i - \sum_{i=1}^{N} \text{AskSize}_i
$$

You can also normalize it to obtain a score between -1 and 1:

$$
\Delta_{norm} = \frac{\sum Bid - \sum Ask}{\sum Bid + \sum Ask}
$$

General interpretation:

- `Delta > 0`: dominant buy pressure
- `Delta < 0`: dominant sell pressure
- Higher absolute value: stronger imbalance

Operational flow:

1. Continuously read orderbook updates.
2. Aggregate bid/ask quantities over depth `N`.
3. Compute `Delta` or `Delta_norm`.
4. Validate market context (`spread <= MAX_SPREAD_PCT`, sufficient depth).
5. Trigger entry/exit only if the signal exceeds `DELTA_THRESHOLD`.

### Bot capabilities

- `DRY_RUN` mode for full simulation with no live orders
- Live Binance execution enabled through environment variables
- WebSocket reconnection with exponential backoff and jitter
- Separable analytics layer (signal, filters, decision)
- Actionable logs for audit and debugging
- Core unit tests for orderbook logic
