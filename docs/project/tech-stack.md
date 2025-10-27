# Technology Stack

**Last Updated**: 2025-10-26
**Related Docs**: See `system-architecture.md` for how components fit together, `deployment-strategy.md` for infrastructure

## Stack Overview

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Language | Python | 3.11 | Core trading logic, async execution, data processing |
| Framework | FastAPI | 0.104.1 | REST API for LLM-friendly bot operations |
| Broker API | robin-stocks | 3.0.5 | Robinhood API wrapper (authentication, orders, positions) |
| Market Data | Alpaca Markets API | N/A | Primary market data (quotes, historical data) |
| Market Data (alt) | yfinance | 0.2.36 | Backup/backtest data source (Yahoo Finance) |
| Order Flow Data | Polygon.io | 1.12.5 | Level 2 order book, Time & Sales data |
| Backtesting | backtrader | 1.9.78.123 | Strategy backtesting engine |
| Data Analysis | pandas, numpy | 2.3.3, 1.26.3 | Time series analysis, indicator calculations |
| Cache | Redis | 7.x (Alpine) | LLM response caching, session storage |
| API Server | Uvicorn | 0.24.0 | ASGI server with WebSocket support |
| Container | Docker | Latest | Reproducible deployments, 24/7 operation |
| Orchestration | Docker Compose | 3.8 | Multi-service deployment (bot + API + Redis) |
| LLM Integration | OpenAI API | 1.54.3 | Trade analysis, natural language bot queries |

---

## Core Language & Runtime

### Language

**Choice**: Python
**Version**: 3.11
**Rationale**:
- **Trading ecosystem**: Rich libraries for data analysis (pandas, numpy), technical indicators, backtesting (backtrader)
- **Async support**: asyncio/await for concurrent market scanning, API calls
- **Rapid development**: Readable syntax, dynamic typing (with type hints for safety)
- **Math/data processing**: First-class support for numerical computations
- **Robinhood API**: robin-stocks library well-maintained, Python-native

**Alternatives Rejected**:
- **JavaScript/Node.js**: Weaker ecosystem for numerical computing, less mature trading libraries
- **Go**: Faster execution but steeper learning curve, fewer trading-specific libraries
- **Rust**: Excellent performance but overkill for MVP, slower development velocity
- **C++/C#**: Too low-level for rapid iteration, not needed for this scale (<100 trades/day)

---

## Broker & Market Data Stack

### Brokerage API

**Choice**: robin-stocks (Robinhood API wrapper)
**Version**: 3.0.5
**Rationale**:
- **Direct integration**: Executes orders on Robinhood (target brokerage)
- **Full API coverage**: Authentication (MFA), quotes, order placement, position tracking
- **Community-maintained**: Active development, good documentation
- **Free**: No brokerage fees beyond Robinhood's (none for stocks)

**Limitations**:
- **Single broker**: Tied to Robinhood (migration to TD Ameritrade/IBKR requires rewrite)
- **No Level 2 data**: Robinhood API lacks order book (requires Polygon.io)
- **Rate limits**: 60 requests/minute (managed via retry logic + exponential backoff)

**Alternatives Rejected**:
- **alpaca-trade-api**: Better for paper trading but requires separate live broker
- **ib_insync (Interactive Brokers)**: Professional-grade but complex setup, higher account minimums
- **TD Ameritrade API**: Good but TDA acquired by Schwab (API future uncertain)

### Market Data (Primary)

**Choice**: Alpaca Markets API
**Version**: Free tier (real-time quotes, historical data)
**Rationale**:
- **Real-time quotes**: Free access to IEX real-time quotes (vs 15-min delayed Yahoo Finance)
- **Premarket data**: Critical for momentum scanning (4am-9:30am ET window)
- **Historical data**: Backfilling for indicator calculations (SMA, ATR)
- **No brokerage account required**: Data-only account (free)

**Alternatives Rejected**:
- **Yahoo Finance (yfinance)**: 15-min delayed quotes (unacceptable for day trading), used as backup only
- **Polygon.io** (data-only): $99/mo for real-time data (too expensive vs Alpaca free tier)
- **Robinhood API quotes**: Rate-limited, unreliable for scanning (used for final validation only)

### Market Data (Order Flow)

**Choice**: Polygon.io SDK
**Version**: 1.12.5
**Pricing**: Starter plan ($99/mo) - Level 2 data, Time & Sales
**Rationale**:
- **Level 2 order book**: Detect large seller walls, institutional selling pressure
- **Time & Sales**: Real-time tick data for volume spike detection
- **Critical for exits**: Identifies "red burst" sell-offs (4x volume spike = exit signal)
- **Edge generator**: Reduces false breakouts, improves win rate (expected +5-10%)

**Alternatives Rejected**:
- **Alpaca** (Level 2): Not available on free tier
- **TD Ameritrade**: Requires brokerage account, API complexity higher
- **Skip order flow entirely**: Tested in backtest - win rate drops 8% without institutional exit detection

---

## Data Processing & Analysis Stack

### Data Manipulation

**Choice**: pandas + numpy
**Versions**: pandas 2.3.3, numpy 1.26.3
**Rationale**:
- **Time series**: pandas DataFrames perfect for OHLCV data (Open, High, Low, Close, Volume)
- **Indicator calculation**: SMA, EMA, ATR easily computed with rolling windows
- **Backtesting**: Vectorized operations for fast backtest execution
- **Industry standard**: Every trading algo uses pandas

**Alternatives Rejected**:
- **Raw Python lists**: Too slow for time-series operations
- **Polars**: Faster than pandas but less mature, fewer trading examples
- **TA-Lib**: C library, harder to install/deploy than pure Python solutions

### Technical Indicators

**Choice**: Custom implementations (in `src/trading_bot/indicators/`)
**Rationale**:
- **Transparency**: Know exactly how SMA, ATR, RSI calculated (no black-box libraries)
- **Customization**: Tailored to momentum strategies (e.g., custom ATR multipliers)
- **Lightweight**: No external C dependencies (TA-Lib requires compilation)

**Libraries Used**:
- `pandas` rolling windows for SMA, EMA
- Custom ATR calculation (Average True Range for stop-loss placement)
- Custom bull flag detector (pole + flag pattern recognition)

**Alternatives Rejected**:
- **TA-Lib**: Hard to install on Windows, overkill for simple indicators
- **pandas-ta**: Good but adds dependency, our needs simple enough for custom code

### Backtesting

**Choice**: backtrader
**Version**: 1.9.78.123
**Rationale**:
- **Event-driven**: Simulates real-time trading (bar-by-bar execution)
- **Realistic slippage/commission modeling**: Accounts for market impact
- **Strategy validation**: Test momentum strategies before live trading
- **Extensible**: Easy to add custom indicators, analyzers

**Alternatives Rejected**:
- **Backtrader.py forks (faster versions)**: Not as battle-tested
- **Zipline**: Alpaca-focused, more complex setup
- **Vectorbt**: Vectorized (faster) but less realistic (assumes perfect fills)

---

## API & Integration Stack

### REST API Framework

**Choice**: FastAPI
**Version**: 0.104.1
**Rationale**:
- **LLM-friendly operations**: Exposes bot state, trade history, commands via REST API
- **Auto-generated docs**: OpenAPI/Swagger UI (http://localhost:8000/docs)
- **Async support**: Non-blocking API calls (important for real-time data fetching)
- **Pydantic validation**: Type-safe request/response models
- **Fast development**: Python's readability + auto-validation

**Use Cases**:
- `/api/v1/status` - Get bot status (positions, performance, alerts)
- `/api/v1/commands/start` - Start/stop trading
- `/api/v1/trades` - Query trade history
- `/api/v1/analysis` - LLM-powered trade analysis

**Alternatives Rejected**:
- **Flask**: No async support, no auto-validation
- **Django**: Too heavy (includes ORM, admin panel we don't need)
- **Sanic**: Similar to FastAPI but smaller community

### API Server

**Choice**: Uvicorn (ASGI server)
**Version**: 0.24.0 (with [standard] extras)
**Rationale**:
- **ASGI**: Required for FastAPI async routes
- **WebSocket support**: Potential future feature (real-time updates to dashboard)
- **Production-ready**: Handles 1000s of requests/sec
- **Lightweight**: Minimal resource overhead

**Alternatives Rejected**:
- **Gunicorn**: WSGI only (no async), would need Uvicorn workers anyway
- **Hypercorn**: Good but Uvicorn more popular, better docs

### Data Validation

**Choice**: Pydantic
**Version**: 2.5.0
**Rationale**:
- **Built into FastAPI**: Automatic request/response validation
- **Type safety**: Runtime validation + static type hints
- **JSON schema generation**: Auto-generates API docs
- **Config management**: Used for config.json validation

**Alternatives Rejected**:
- **Marshmallow**: Older, less integrated with FastAPI
- **Cerberus**: No type hints, less Pythonic

---

## Infrastructure & Deployment Stack

### Containerization

**Choice**: Docker
**Version**: Latest (python:3.11-slim base image)
**Rationale**:
- **Reproducibility**: Same environment dev → staging → prod
- **24/7 operation**: Container restart policies (unless-stopped)
- **Isolation**: Dependencies isolated from host system
- **Easy deployment**: Single `docker-compose up -d` command

**Dockerfile Strategy**:
- **Multi-stage builds**: Not needed (single Python app)
- **Layer caching**: requirements.txt copied first (cache pip install)
- **Health checks**: Python process liveness check

**Alternatives Rejected**:
- **Virtual env only**: Not reproducible across systems (different OS, Python versions)
- **Kubernetes**: Overkill for single-server deployment
- **Systemd service**: Harder to reproduce, OS-specific

### Orchestration

**Choice**: Docker Compose
**Version**: 3.8
**Rationale**:
- **Multi-service**: Manages bot + API + Redis with single command
- **Networking**: Automatic service discovery (bot → redis, API → bot logs)
- **Volume management**: Persist logs, config, Robinhood session
- **Simple**: No Kubernetes overhead for single-server deployment

**Services**:
1. **trading-bot**: Main trading loop (24/7)
2. **api**: FastAPI service (monitoring, LLM queries)
3. **redis**: Cache for LLM responses (reduce OpenAI API costs)

**Alternatives Rejected**:
- **Separate containers manually**: Harder to manage, no service discovery
- **Single container (all services)**: Less modular, harder to debug
- **Kubernetes**: Too complex for single-server, solo-developer use case

### Deployment Platform

**Choice**: Self-hosted VPS (Hetzner)
**Pricing**: ~€4-10/mo (CX11-CX21 instance)
**Rationale**:
- **Cost**: 24/7 operation on cloud serverless too expensive (Railway $20-50/mo)
- **Control**: Full root access, custom networking for API rate limiting
- **Performance**: Dedicated resources (vs shared cloud functions)
- **Data residency**: Keep trade data on own server (not third-party cloud)

**Alternatives Rejected**:
- **Railway**: Good DX but $20-30/mo (3-5x more expensive than VPS)
- **AWS EC2**: More expensive, overkill features (load balancers, auto-scaling not needed)
- **Render**: Similar to Railway, costs add up for 24/7 containers
- **Vercel/Netlify**: Not suitable for long-running processes (serverless functions timeout)
- **Local machine (laptop)**: Unreliable (power outages, internet downtime, not 24/7)

---

## Caching & State Management

### Cache Layer

**Choice**: Redis
**Version**: 7 (Alpine Docker image)
**Rationale**:
- **LLM response caching**: Cache OpenAI API responses (reduce costs by 60-80%)
- **Session storage**: Potential future use (API rate limiting, user sessions)
- **Fast**: In-memory, <1ms read latency
- **Simple**: Key-value store (no complex queries needed)

**Usage**:
- **LLM cache**: `llm_cache:{prompt_hash}` → cached response (TTL: 1 hour)
- **Rate limiting**: Future feature (track API calls per user/IP)

**Alternatives Rejected**:
- **No cache**: OpenAI API costs $0.50-2.00 per 1K requests (cache reduces to $0.10-0.40)
- **In-memory dict**: Doesn't persist across bot restarts, not shared between bot/API containers
- **Memcached**: Less features than Redis (no persistence, no pub/sub)

---

## LLM Integration

### LLM Provider

**Choice**: OpenAI API (GPT-4o-mini)
**Version**: openai==1.54.3
**Pricing**: $0.15 per 1M input tokens, $0.60 per 1M output tokens
**Rationale**:
- **Trade analysis**: Analyze why trade won/lost, suggest improvements
- **Natural language queries**: "What's my performance this week?" via API
- **Debugging**: Explain why signal rejected (complex multi-factor rules)
- **Cost-effective**: gpt-4o-mini 10x cheaper than gpt-4o, sufficient for structured data analysis

**Use Cases**:
1. **Trade post-mortem**: Analyze trade logs, identify mistakes
2. **Bot status**: Natural language bot queries via API
3. **Signal explanation**: Why premarket scanner rejected a stock
4. **Performance summary**: Weekly performance reports

**Alternatives Rejected**:
- **gpt-4o**: 10x more expensive, not needed for structured data (trade logs are JSON)
- **Claude (Anthropic)**: Good but no native caching, worse structured output
- **Local LLM (Llama 3.x)**: Free but requires GPU, inference slower, quality lower
- **No LLM**: Trade analysis manual (time-consuming), debugging harder

### Token Management

**Choice**: tiktoken (token counting) + tenacity (retry logic)
**Rationale**:
- **Budget control**: tiktoken counts tokens before API call (prevent overages)
- **Monthly budget**: $100/mo cap (alerts at 80% usage)
- **Retry logic**: tenacity handles rate limits, transient errors
- **Cache-first**: Redis cache prevents redundant API calls (saves 60-80% cost)

---

## Testing Stack

### Unit & Integration Testing

**Choice**: pytest + pytest-asyncio + pytest-mock + pytest-cov
**Versions**: pytest 8.4.2, pytest-cov 4.1.0
**Rationale**:
- **Industry standard**: Python testing de facto standard
- **Async support**: pytest-asyncio for testing async API routes, market data fetching
- **Mocking**: pytest-mock for Robinhood API calls (no real orders in tests)
- **Coverage**: pytest-cov tracks test coverage (target >80%)

**Test Structure**:
```
tests/
├── unit/               # Pure logic tests (indicators, calculators)
├── integration/        # API integration tests (Robinhood, Alpaca)
└── backtest/          # Strategy validation tests
```

**Alternatives Rejected**:
- **unittest**: Less Pythonic, more boilerplate than pytest
- **nose**: Deprecated, pytest won
- **Robot Framework**: Overkill for unit/integration tests

---

## Code Quality & Security Tools

### Linting & Formatting

**Linting**: Ruff (modern Python linter, 10x faster than Pylint)
**Version**: 0.14.1
**Formatting**: (Using Ruff's formatter - future migration)
**Type Checking**: mypy
**Version**: 1.18.2

**Rationale**:
- **Ruff**: Replaces Pylint + Flake8 + isort, 10-100x faster (Rust-based)
- **mypy**: Static type checking (catches bugs before runtime)
- **Pre-commit hooks**: Enforce style before commit (future)

**Alternatives Rejected**:
- **Pylint**: Slow, verbose output (Ruff replaces it)
- **Black**: Good formatter but Ruff has equivalent built-in
- **Pyright**: Faster than mypy but less mature

### Security Scanning

**Choice**: bandit (security linter)
**Version**: 1.7.6
**Rationale**:
- **Credential leaks**: Detect hardcoded API keys, passwords
- **Insecure code**: Flag SQL injection, unsafe pickle usage
- **CI integration**: Run on every commit

**Alternatives Rejected**:
- **Snyk**: Commercial, overkill for solo project
- **Manual review**: Error-prone, doesn't scale

### Dependency Security

**Choice**: `safety` (not in requirements.txt - run manually)
**Alternative**: GitHub Dependabot alerts (enabled)
**Rationale**:
- **CVE detection**: Scan requirements.txt for known vulnerabilities
- **Auto-alerts**: Dependabot creates PR to bump vulnerable packages
- **Recent fix**: Bumped pyarrow to 17.0.0 (fixed PYSEC-2024-161)

---

## Configuration & Secrets Management

### Environment Variables

**Choice**: python-dotenv
**Version**: 1.0.0
**Rationale**:
- **12-factor app**: Config via environment, not code
- **Secrets safety**: `.env` file in `.gitignore`, never committed
- **Easy Docker integration**: `env_file: .env` in docker-compose.yml

**Managed Secrets**:
- `ROBINHOOD_USERNAME`, `ROBINHOOD_PASSWORD`, `ROBINHOOD_MFA_SECRET`
- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`
- `POLYGON_API_KEY`
- `OPENAI_API_KEY`
- `BOT_API_AUTH_TOKEN`

**Alternatives Rejected**:
- **Hardcoded secrets**: Security risk (Git history leak)
- **AWS Secrets Manager**: Overkill, adds cost + complexity
- **HashiCorp Vault**: Too complex for solo project

### MFA/2FA Handling

**Choice**: pyotp (TOTP generation)
**Version**: 2.9.0
**Rationale**:
- **Automated login**: Generate Robinhood MFA codes programmatically
- **No manual intervention**: Bot can re-authenticate 24/7 without human input
- **Standard TOTP**: Compatible with Google Authenticator secret format

**Alternatives Rejected**:
- **Manual MFA codes**: Not feasible for 24/7 automated trading
- **SMS-based 2FA**: Robinhood doesn't support API access to SMS codes

---

## Monitoring & Logging

### Logging Framework

**Choice**: Python built-in `logging` module + custom loggers
**Rationale**:
- **Structured logging**: JSON logs for easy parsing (trade logs)
- **Multiple outputs**: Console (development) + file (production)
- **Log rotation**: Python's RotatingFileHandler (10MB max per file)

**Log Categories**:
- `logs/trading_bot.log` - General bot operations
- `logs/trades.jsonl` - Trade records (JSON Lines format)
- `logs/health/` - Circuit breaker events, performance alerts
- `logs/llm_cache/` - LLM API usage, cache hits/misses

**Alternatives Rejected**:
- **Loguru**: Nice API but built-in `logging` sufficient
- **Structlog**: Good for complex systems, overkill here
- **ELK Stack (Elasticsearch, Logstash, Kibana)**: Too complex for solo project

### CLI Dashboard

**Choice**: rich (terminal UI)
**Version**: 13.7.0
**Rationale**:
- **Real-time monitoring**: Live updates of positions, performance, alerts
- **Beautiful output**: Tables, progress bars, colors
- **Keyboard controls**: pynput for interactive commands (start/stop, view logs)

**Alternatives Rejected**:
- **Textual (rich-based TUI framework)**: More complex, rich sufficient for simple dashboard
- **Curses**: Low-level, harder to use than rich
- **Web dashboard**: Adds complexity (FastAPI already provides REST API for external tools)

---

## Constraints & Trade-offs

### Performance

**Target**: Signal detection <30s, order execution <5s
**Trade-off**: Python slower than Go/Rust but development speed >10x faster

**Why acceptable**: Day trading doesn't require microsecond latency (HFT does, we don't)

### Cost

**Budget**: <$150/mo for production operation
- Hetzner VPS: €10/mo ($11)
- Polygon.io: $99/mo
- OpenAI API (gpt-4o-mini): $20-40/mo (with caching)
- **Total**: ~$130-150/mo

**Trade-off**: Using managed services (Polygon.io) vs building own Level 2 feed parser (saves development time)

### Scalability

**Current Capacity**: Single trading account, <100 trades/day
**Next Tier**: Multi-account support requires Robinhood API limits increase (not currently needed)

---

## Dependency Management

### Python Dependencies

**Lock File**: `requirements.txt` with pinned versions
**Update Strategy**:
- **Security updates**: Immediately (e.g., pyarrow PYSEC-2024-161)
- **Feature updates**: Quarterly review
- **Major version bumps**: Only if needed (breaking changes)

**Security**: GitHub Dependabot alerts + manual `safety check`

**Example Pin**:
```
robin-stocks==3.0.5  # Pinned to prevent API breaking changes
pandas==2.3.3        # Pinned for backtest reproducibility
```

---

## Technology Upgrade Path

**When to Upgrade**:
- **Security vulnerabilities**: Immediately (e.g., pyarrow 17.0.0)
- **API breaking changes**: When robin-stocks or broker API changes
- **End-of-life libraries**: Before EOL date (e.g., Python 3.11 EOL ~2027)

**How to Upgrade**:
1. Test in feature branch
2. Run full test suite (`pytest`)
3. Backtest validation (ensure results unchanged)
4. Deploy to staging (paper trading mode)
5. Monitor for 48 hours
6. Deploy to production

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2025-10-26 | Python 3.11 over Go/Rust | Trading ecosystem (pandas, backtrader), rapid development | Slower execution (acceptable for day trading latency requirements) |
| 2025-10-20 | Added Polygon.io for Level 2 data | Detect institutional exits, improve win rate | +$99/mo cost, expected +5-10% win rate |
| 2025-10-15 | FastAPI for LLM-friendly API | Enable OpenAI integration for trade analysis | +0 cost (Uvicorn lightweight), better observability |
| 2025-09-01 | Backtrader over Zipline | Simpler setup, event-driven (more realistic) | Adequate for strategy validation |
| 2025-08-15 | robin-stocks over alpaca-trade-api | Direct Robinhood execution (target broker) | Locked to single broker (acceptable for MVP) |
