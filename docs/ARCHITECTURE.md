# System Architecture

This document describes the high-level architecture of the Robinhood Trading Bot system.

---

## Table of Contents

- [Overview](#overview)
- [System Components](#system-components)
- [Architecture Diagram](#architecture-diagram)
- [Data Flow](#data-flow)
- [Component Details](#component-details)
- [Integration Points](#integration-points)
- [Technology Stack](#technology-stack)
- [Design Patterns](#design-patterns)
- [File Structure](#file-structure)
- [Deployment Architecture](#deployment-architecture)

---

## Overview

The Robinhood Trading Bot is a Python-based algorithmic trading system built with **safety-first** principles. The architecture separates concerns into distinct layers and follows the Constitution v1.0.0 guidelines for risk management, testing, and security.

### Key Architectural Principles

1. **Safety First**: Multiple circuit breakers and fail-safes
2. **Separation of Concerns**: Clear boundaries between components
3. **Testability**: 90%+ test coverage requirement
4. **Observability**: Comprehensive logging and monitoring
5. **API-First Design**: Modern API for external integration (v1.8.0+)

---

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Trading Bot System                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Core Bot   │    │  API Service │    │   CLI Tools  │ │
│  │              │    │  (FastAPI)   │    │              │ │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘ │
│         │                   │                              │
│  ┌──────▼────────────────────▼───────────────────────────┐ │
│  │         Strategy & Risk Management Layer              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │ │
│  │  │Strategies│  │   Risk   │  │ Circuit Breakers  │  │ │
│  │  └──────────┘  └──────────┘  └───────────────────┘  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Data & Order Management Layer             │  │
│  │  ┌───────────┐  ┌──────────┐  ┌──────────────────┐ │  │
│  │  │  Market   │  │  Order   │  │   Performance    │ │  │
│  │  │   Data    │  │  Mgmt    │  │    Tracking      │ │  │
│  │  └───────────┘  └──────────┘  └──────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Infrastructure Layer                     │  │
│  │  ┌───────────┐  ┌──────────┐  ┌──────────────────┐ │  │
│  │  │   Auth    │  │ Logging  │  │  Config Mgmt     │ │  │
│  │  └───────────┘  └──────────┘  └──────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
    ┌─────────────┐              ┌──────────────┐
    │  Robinhood  │              │  Polygon.io  │
    │     API     │              │      API     │
    └─────────────┘              └──────────────┘
```

---

## Architecture Diagram

### High-Level Architecture

```
┌─────────────────┐
│   User/LLM      │
│                 │
└────────┬────────┘
         │
         │ HTTP/WebSocket
         ▼
┌────────────────────────────────────────┐
│         API Layer (v1.8.0+)            │
│  ┌──────────────────────────────────┐  │
│  │  FastAPI Application             │  │
│  │  - REST Endpoints                │  │
│  │  - WebSocket Streaming           │  │
│  │  - Authentication                │  │
│  │  - Rate Limiting                 │  │
│  └──────────────────────────────────┘  │
└────────┬───────────────────────────────┘
         │
         │ Internal API
         ▼
┌────────────────────────────────────────┐
│        Core Trading Bot                │
│  ┌──────────────────────────────────┐  │
│  │  Main Bot Loop                   │  │
│  │  - Strategy Execution            │  │
│  │  - Order Management              │  │
│  │  - Risk Enforcement              │  │
│  │  - State Management              │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  Safety Systems                  │  │
│  │  - Circuit Breakers              │  │
│  │  - Emotional Control             │  │
│  │  - Profit Protection             │  │
│  │  - Session Health                │  │
│  └──────────────────────────────────┘  │
└────────┬───────────────────────────────┘
         │
         │ API Calls
         ▼
┌────────────────────────────────────────┐
│      External Services                 │
│  ┌────────────┐    ┌───────────────┐   │
│  │ Robinhood  │    │  Polygon.io   │   │
│  │    API     │    │      API      │   │
│  └────────────┘    └───────────────┘   │
└────────────────────────────────────────┘
```

### Data Flow

```
1. Market Data Collection:
   Polygon.io → Market Data Service → Order Flow Detector
   Robinhood → Market Data Service → Price Data Cache

2. Strategy Execution:
   Market Data → Strategy Engine → Entry/Exit Signals
   Signals → Risk Manager → Position Sizing
   Sized Orders → Order Manager → Robinhood API

3. Performance Tracking:
   Executed Orders → Performance Tracker → Metrics
   Metrics → Profit Goal Tracker → Protection State
   Metrics → Emotional Control → Position Multiplier

4. Monitoring (v1.8.0+):
   Bot State → State Aggregator → API Endpoints
   API Endpoints → Users/LLMs → Actions
   Actions → Workflow Engine → Bot Commands
```

---

## Component Details

### 1. Core Trading Bot (`src/trading_bot/bot.py`)

**Responsibility**: Main orchestration loop for trading operations

**Key Functions**:
- Market hours detection
- Strategy signal generation
- Order execution coordination
- Safety check enforcement
- State persistence

**Interactions**:
- Uses strategies to generate signals
- Consults risk manager for position sizing
- Delegates order execution to order manager
- Triggers circuit breakers on violations

---

### 2. API Service (`api/app/`)

**Responsibility**: RESTful API and WebSocket interface (v1.8.0+)

**Components**:
- **FastAPI Application** (`main.py`): ASGI application
- **Routes** (`routes/`): Endpoint handlers
- **Schemas** (`schemas/`): Pydantic models
- **Services** (`services/`): Business logic
- **Middleware** (`middleware/`): Auth, rate limiting, error handling

**Endpoints**:
- State API: `/api/v1/state`, `/api/v1/summary`, `/api/v1/health`
- Config API: `/api/v1/config/*`
- Workflow API: `/api/v1/workflows/*`
- Observability: `/api/v1/metrics`, WebSocket `/api/v1/stream`

---

### 3. Strategy Layer (`src/trading_bot/strategies/`)

**Responsibility**: Generate entry/exit signals based on market data

**Strategies**:
- Bull Flag Breakout
- Momentum Detection
- VWAP Mean Reversion
- Support/Resistance Zone Trading

**Interface**:
```python
class Strategy(ABC):
    @abstractmethod
    def should_enter(self, symbol: str, data: MarketData) -> bool:
        """Determine if entry conditions met."""
        pass

    @abstractmethod
    def should_exit(self, symbol: str, position: Position) -> bool:
        """Determine if exit conditions met."""
        pass
```

---

### 4. Risk Management (`src/trading_bot/risk_management/`)

**Responsibility**: Position sizing, stop loss calculation, risk limits

**Components**:
- **RiskManager**: Core position sizing logic
- **ATRCalculator**: Volatility-based stops
- **EmotionalControl**: Position size reduction after losses
- **ProfitGoalTracker**: Profit protection mechanism

**Safety Features**:
- Max 5% account per position
- Mandatory stop losses
- ATR-based dynamic stops
- Emotional control (25% sizing after losses)
- Daily profit protection

---

### 5. Order Management (`src/trading_bot/order_management/`)

**Responsibility**: Order execution, tracking, and synchronization

**Components**:
- **OrderManager**: Order lifecycle management
- **LiveGateway**: Robinhood API integration
- **PaperGateway**: Simulated order execution

**Features**:
- Limit orders only (safety)
- Offset calculation (BPS/absolute)
- Slippage guardrails
- Order status polling
- Audit logging (JSONL)

---

### 6. Market Data Service (`src/trading_bot/market_data/`)

**Responsibility**: Fetch and cache market data

**Data Sources**:
- Robinhood API: Quotes, historical data
- Polygon.io: Level 2 order book, time & sales

**Caching**:
- 60-second TTL for state data
- Real-time quotes for order execution
- Historical data for backtesting

---

### 7. Performance Tracking (`src/trading_bot/performance/`)

**Responsibility**: Track P&L, win rates, streaks

**Metrics**:
- Daily P&L (realized + unrealized)
- Win rate
- Average risk:reward ratio
- Consecutive win/loss streaks
- Max drawdown

**Consumers**:
- Profit Goal Tracker
- Emotional Control
- Performance reports
- API state endpoints

---

### 8. Authentication (`src/trading_bot/auth/`)

**Responsibility**: Robinhood authentication and session management

**Features**:
- MFA support (pyotp)
- Device token caching
- Session health monitoring
- Automatic re-authentication

**Security**:
- Credentials in .env (never committed)
- Session tokens encrypted
- Health checks every 5 minutes

---

### 9. Logging System (`src/trading_bot/logger.py`)

**Responsibility**: Structured logging with audit trails

**Log Files**:
- `trading_bot.log`: General application logs
- `trades.log`: Trade execution audit (§Audit_Everything)
- `errors.log`: Error and exception tracking
- `*.jsonl`: Structured event logs

**Features**:
- UTC timestamps (§Data_Integrity)
- 10MB rotation, 5 backup files
- Console + file output
- Trade-specific logger

---

### 10. Configuration Management (`src/trading_bot/config.py`)

**Responsibility**: Load and validate configuration

**Sources**:
- `.env`: Credentials (gitignored)
- `config.json`: Trading parameters (gitignored)
- Environment variables: Overrides

**Validation**:
- Pre-deploy checks (§Pre_Deploy)
- Phase-mode conflict detection
- Required field validation
- Range checks on parameters

---

## Integration Points

### Robinhood API

**Library**: `robin_stocks`

**Operations**:
- Login/authentication
- Account data (balance, buying power)
- Order placement (limit orders)
- Position retrieval
- Historical data

**Rate Limiting**:
- Exponential backoff on errors
- Session health monitoring
- Graceful degradation

---

### Polygon.io API (v1.7.0+)

**Library**: `polygon-api-client`

**Operations**:
- Level 2 order book snapshots
- Time & Sales data
- Large order detection
- Volume spike detection

**Use Cases**:
- Institutional selling pressure detection
- Exit signal generation
- Order flow analysis

---

### FastAPI Service (v1.8.0+)

**Integration**: Internal Python API

**Consumers**:
- Web dashboards
- LLM assistants
- Monitoring tools
- Automation scripts

**Data Flow**:
```
Bot State → StateAggregator → Pydantic Models → JSON → HTTP/WebSocket
```

---

## Technology Stack

### Core Application

- **Language**: Python 3.11+
- **Trading Library**: `robin_stocks`
- **Decimal Math**: `decimal.Decimal` (§Data_Integrity)
- **Async**: Not currently used (synchronous)

### API Service (v1.8.0+)

- **Framework**: FastAPI 0.104+
- **ASGI Server**: Uvicorn 0.24+
- **Validation**: Pydantic 2.5+
- **WebSocket**: `websockets` 12.0+
- **Workflows**: PyYAML for YAML parsing

### Data & State

- **Market Data**: HTTP requests to Robinhood/Polygon APIs
- **State Storage**: JSONL files for events, JSON for state
- **Caching**: In-memory with TTL
- **No Database**: File-based storage only

### Development Tools

- **Testing**: pytest, pytest-cov
- **Type Checking**: mypy
- **Linting**: ruff
- **Formatting**: black
- **Security**: bandit

---

## Design Patterns

### 1. Strategy Pattern

Used for trading strategies:

```python
class BullFlagStrategy(Strategy):
    def should_enter(self, symbol, data):
        # Bull flag logic
        pass

class MomentumStrategy(Strategy):
    def should_enter(self, symbol, data):
        # Momentum logic
        pass

# Bot uses strategies polymorphically
bot.add_strategy(BullFlagStrategy())
bot.add_strategy(MomentumStrategy())
```

### 2. Dependency Injection

Used for testability:

```python
class TradingBot:
    def __init__(
        self,
        config: Config,
        auth: RobinhoodAuth,
        market_data: MarketDataService,
        order_manager: OrderManager,
        risk_manager: RiskManager,
    ):
        # Dependencies injected, not created internally
        self.config = config
        self.auth = auth
        # ... etc
```

### 3. Factory Pattern

Used for configuration:

```python
class EmotionalControlConfig:
    @classmethod
    def from_env(cls) -> "EmotionalControlConfig":
        """Create config from environment variables."""
        return cls(
            enabled=os.getenv("EMOTIONAL_CONTROL_ENABLED", "true") == "true"
        )

    @classmethod
    def default(cls) -> "EmotionalControlConfig":
        """Create config with safe defaults."""
        return cls(enabled=True)
```

### 4. Circuit Breaker Pattern

Used for safety:

```python
class CircuitBreaker:
    def __init__(self):
        self.tripped = False

    def check_daily_loss(self, loss_pct):
        if loss_pct > MAX_DAILY_LOSS:
            self.trip("Daily loss limit exceeded")

    def trip(self, reason):
        self.tripped = True
        logger.critical(f"Circuit breaker tripped: {reason}")
        # Block new trades
```

### 5. Observer Pattern

Used for event logging:

```python
class PerformanceTracker:
    def update_on_trade(self, trade):
        """Called when trade executes."""
        self._update_metrics(trade)
        self._emit_event(trade)

# Observers
profit_goal_tracker.observe(performance_tracker)
emotional_control.observe(performance_tracker)
```

---

## File Structure

```
src/trading_bot/
├── __init__.py                # Package init
├── bot.py                     # Main bot loop
├── config.py                  # Configuration management
├── logger.py                  # Logging system
│
├── auth/                      # Authentication
│   ├── robinhood_auth.py     # Login, session management
│   └── session_health.py     # Health monitoring
│
├── strategies/                # Trading strategies
│   ├── base.py               # Strategy interface
│   ├── bull_flag.py          # Bull flag breakout
│   ├── momentum.py           # Momentum detection
│   └── support_resistance.py # S/R zone trading
│
├── risk_management/           # Risk and position sizing
│   ├── risk_manager.py       # Core position sizing
│   ├── atr_calculator.py     # ATR-based stops
│   ├── circuit_breakers.py   # Safety circuit breakers
│   └── pullback_calculator.py # Pullback-based stops
│
├── order_management/          # Order execution
│   ├── order_manager.py      # Order lifecycle
│   ├── live_gateway.py       # Robinhood integration
│   └── paper_gateway.py      # Simulated execution
│
├── market_data/               # Market data fetching
│   ├── market_data_service.py # Data aggregation
│   ├── robinhood_client.py   # Robinhood data
│   └── polygon_client.py     # Polygon.io data
│
├── performance/               # Performance tracking
│   ├── performance_tracker.py # P&L, win rate
│   ├── profit_goal.py        # Profit protection
│   └── emotional_control/    # Emotional safeguards
│
├── support_resistance/        # S/R zone detection
│   ├── zone_detector.py      # Zone identification
│   ├── proximity_checker.py  # Proximity alerts
│   └── breakout_detector.py  # Breakout detection
│
├── order_flow/                # Order flow analysis (v1.7.0)
│   ├── detector.py           # Large seller detection
│   ├── tape_monitor.py       # Volume spike detection
│   └── models.py             # Data models
│
├── backtest/                  # Backtesting engine
│   ├── engine.py             # Backtest orchestration
│   ├── historical_data.py    # Data management
│   └── metrics.py            # Performance metrics
│
└── cli/                       # CLI tools
    ├── nl_commands.py        # Natural language CLI (v1.8.0)
    └── workflow_cli.py       # Workflow execution

api/
└── app/
    ├── main.py               # FastAPI application
    ├── routes/               # API endpoints
    │   ├── state.py         # State endpoints
    │   ├── config.py        # Config management
    │   ├── workflows.py     # Workflow execution
    │   └── metrics.py       # Observability
    ├── schemas/              # Pydantic models
    │   ├── state.py         # State responses
    │   ├── config.py        # Config schemas
    │   └── errors.py        # Error schemas
    ├── services/             # Business logic
    │   ├── state_aggregator.py # State composition
    │   └── workflow_executor.py # Workflow engine
    ├── middleware/           # Middleware
    │   ├── auth.py          # API key authentication
    │   ├── rate_limit.py    # Rate limiting
    │   └── error_handler.py # Semantic error handling
    └── core/                 # Core functionality
        ├── websocket.py     # WebSocket streaming
        └── auth.py          # Authentication logic
```

---

## Deployment Architecture

### Local Deployment (Current)

```
┌─────────────────────────────────────┐
│      Local Machine                  │
│                                     │
│  ┌────────────────────────────────┐ │
│  │  Trading Bot Process           │ │
│  │  (python -m src.trading_bot)   │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌────────────────────────────────┐ │
│  │  API Service Process           │ │
│  │  (uvicorn api.app.main:app)    │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌────────────────────────────────┐ │
│  │  File System                   │ │
│  │  - logs/                       │ │
│  │  - data/                       │ │
│  │  - config.json                 │ │
│  │  - .env                        │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Production Deployment (Recommended)

```
┌──────────────────────────────────────────┐
│          Cloud VM / VPS                  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  Systemd Services                  │  │
│  │  - trading-bot.service             │  │
│  │  - trading-bot-api.service         │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  Reverse Proxy (nginx/Caddy)       │  │
│  │  - HTTPS termination               │  │
│  │  - Rate limiting                   │  │
│  │  - Load balancing                  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  Monitoring (Prometheus/Grafana)   │  │
│  │  - Metrics collection              │  │
│  │  - Alerting                        │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  Persistent Storage                │  │
│  │  - Logs (rotated, backed up)       │  │
│  │  - State files                     │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

---

## Scalability Considerations

### Current Limitations

- **Single Instance**: No horizontal scaling
- **File-Based State**: No distributed state
- **WebSocket**: Single server connections only
- **No Database**: Limited query capabilities

### Future Enhancements

1. **Database Integration**:
   - PostgreSQL for trade history
   - Redis for caching
   - TimescaleDB for time-series metrics

2. **Message Queue**:
   - RabbitMQ/Redis for order processing
   - Asynchronous order execution
   - Event-driven architecture

3. **Horizontal Scaling**:
   - Multiple API instances behind load balancer
   - Distributed WebSocket (Redis pub/sub)
   - Shared state management

---

## Security Architecture

### Credential Management

```
.env file → Environment Variables → Config Object
         (gitignored)          (masked in logs)
```

### API Security (v1.8.0+)

- **Authentication**: API key in X-API-Key header
- **Rate Limiting**: 100 req/min per key
- **CORS**: Configurable allowed origins
- **Input Validation**: Pydantic schemas
- **Constant-Time Comparison**: Prevents timing attacks

### Network Security

- **Local Binding**: 0.0.0.0:8000 by default
- **Reverse Proxy**: nginx/Caddy for TLS
- **Firewall**: Restrict access to API port

---

## Further Reading

- [API Documentation](API.md)
- [Operations Guide](OPERATIONS.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Constitution](.spec-flow/memory/constitution.md)
- [Contributing](../CONTRIBUTING.md)

---

**Last Updated**: 2025-10-26
**Version**: v1.8.0
