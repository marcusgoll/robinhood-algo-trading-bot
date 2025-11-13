# Robinhood Algo Trading Bot - Codebase Architecture

## Overview
A comprehensive Python-based algorithmic trading bot for Robinhood platform with multi-agent LLM support, comprehensive state management, risk controls, and monitoring capabilities.

## Project Structure

```
/home/user/robinhood-algo-trading-bot/
├── src/trading_bot/              # Main bot implementation
├── api/                          # FastAPI REST/WebSocket API
├── tests/                        # Test suite
├── scripts/                      # Utility scripts
├── config/                       # Configuration files
└── docs/                         # Documentation
```

---

## 1. MAIN ENTRY POINTS AND BOT INITIALIZATION

### Primary Entry Point: `src/trading_bot/__main__.py`
- Allows running as `python -m trading_bot`
- Delegates to `main.py`

### Main Entry Point: `src/trading_bot/main.py` (94 lines)
**Key Functions:**
- `parse_arguments()`: Parses CLI arguments
- `main()`: Orchestrates bot startup and trading loop

**Supported Modes:**
1. **trade** (default): Normal trading mode with startup validation
2. **dashboard**: CLI dashboard for monitoring
3. **generate-watchlist**: Dynamic watchlist generation
4. **orchestrator**: LLM-enhanced trading with multi-agent system

**Command-line Arguments:**
- `--dry-run`: Validate startup without trading
- `--json`: Machine-readable JSON output
- `--orchestrator-mode {live,paper,backtest}`: Select orchestrator mode
- `--preview`: Preview watchlist
- `--save`: Save watchlist
- `--sectors`: Filter by sectors (comma-separated)

**Exit Codes:**
- 0: Success
- 1: Configuration error
- 2: Validation error
- 3: Initialization failure
- 130: User interrupt (Ctrl+C)

### Bot Class: `src/trading_bot/bot.py`
**Status:** Core class with deprecated CircuitBreaker
**Features:**
- Trade execution and management
- Session health monitoring
- Risk management integration
- Order management via OrderManager
- Structured logging (TradeRecord)

**Deprecated:** CircuitBreaker class (moved to SafetyChecks module)

---

## 2. TRADING BOT CLASSES AND CORE FUNCTIONALITY

### Core Bot Components

#### Configuration: `src/trading_bot/config.py`
**Dual Configuration System:**
- `.env`: Credentials (username, password, MFA secret, device token)
- `config.json`: Trading parameters (position sizes, hours, strategy)

**Key Classes:**
- `Config`: Main configuration dataclass
  - Robinhood credentials
  - Trading mode (paper/live)
  - Risk management config
  - Order management config
  - Phase configuration
  - Crypto configuration
  - Portfolio targets

- `OrderManagementConfig`: Order execution parameters
  - offset_mode (bps or absolute)
  - buy_offset, sell_offset
  - max_slippage_pct
  - poll_interval_seconds
  - strategy_overrides (per-strategy customization)

#### Order Management: `src/trading_bot/order_management/`
**Key Components:**
- `OrderManager`: Manages order lifecycle
- `OrderRequest`: Order request model
- `OrderEnvelope`: Order with execution tracking
- `OrderValidator`: Validates orders before submission
- `OrderExecutor`: Executes orders via gateways

**Features:**
- Limit order support (phase one)
- Order offset calculations (BPS or absolute)
- Slippage management
- Order polling and status tracking
- Structured JSONL logging

#### Risk Management: `src/trading_bot/risk_management/`
**Key Components:**
- `RiskManager`: Comprehensive risk controls
- `RiskManagementConfig`: Risk parameters
- `ATRCalculator`: Volatility-based position sizing
- `StopAdjuster`: Dynamic stop loss management
- `TargetMonitor`: Profit target tracking
- `PullbackAnalyzer`: Support/resistance analysis
- `TradeRules`: Risk rule enforcement

**Features:**
- Daily loss limits (circuit breaker)
- Consecutive loss tracking
- Buying power validation
- Position sizing (Kelly Criterion support)
- ATR-based stops and targets
- Trading hours enforcement

#### Account Data: `src/trading_bot/account/account_data.py`
**Key Classes:**
- `Position`: Position with P&L calculation
  - symbol, quantity, average_buy_price, current_price
  - Properties: cost_basis, current_value, profit_loss, profit_loss_pct

- `AccountBalance`: Account balance breakdown
  - cash, equity, buying_power, last_updated

- `AccountDataService`: Fetches and caches account data
  - TTL-based caching to minimize API calls
  - Position and balance queries

#### Health Monitoring: `src/trading_bot/health/session_health.py`
**Key Classes:**
- `SessionHealthStatus`: Session metrics
  - is_healthy, session_start_time, session_uptime_seconds
  - health_check_count, reauth_count, consecutive_failures

- `HealthCheckResult`: Single health check result

- `SessionHealthMonitor`: Proactive health checking
  - Periodic checks every 5 minutes
  - Automatic reauthentication
  - Circuit breaker integration

#### Phase Management: `src/trading_bot/phase/`
**Phases:**
1. EXPERIENCE: Initial learning phase
2. PROOF_OF_CONCEPT: Validate strategy in paper trading
3. REAL_MONEY_TRIAL: Limited real money testing
4. SCALING: Full production deployment

**Components:**
- `PhaseManager`: Orchestrates phase transitions
- `Phase`: Enum of trading phases
- `PhaseTransition`: Records phase changes
- `SessionMetrics`: Tracks metrics for phase validation
- `TradeLimiter`: Enforces trading constraints per phase
- Phase-specific validators (ExperienceToPoCValidator, etc.)

#### Emotional Control: `src/trading_bot/emotional_control/`
**Features:**
- Tracks consecutive wins/losses
- Activates position size reduction on loss triggers
- Tracks activation reason and recovery path
- CLI for status monitoring and manual reset
- State persistence to file

---

## 3. AGENT CLASSES AND PURPOSES

### Base Agent: `src/trading_bot/llm/agents/base_agent.py`
**Abstract class** all agents inherit from

**Features:**
- LLM call tracking and database storage
- Cost calculation (Claude API pricing)
- Memory integration (AgentMemory)
- Standard execute() interface

**Pricing (Haiku-4.5):**
- Input: $0.40 per million tokens
- Output: $2.00 per million tokens

**Methods:**
- `execute(context)`: Main execution method (abstract)
- `_call_llm()`: Internal LLM call wrapper with tracking

### Specialized Agents

#### 1. **NewsAnalystAgent** (Sentiment Analysis)
**Purpose:** Analyze financial news for trading signals
**Uses:** FMP API for news fetching
**Analyzes:**
- Headline sentiment (bullish/neutral/bearish)
- Article credibility (source quality)
- Trading impact (BUY_SIGNAL, SELL_SIGNAL, NEUTRAL, NOISE)
- Urgency (IMMEDIATE, NEAR_TERM, LONG_TERM)
- Sentiment consistency across sources
**Output:** Sentiment score (-100 to +100), confidence score

#### 2. **ResearchAgent** (Fundamental Analysis)
**Purpose:** Fundamental analysis using Financial Modeling Prep API
**Fetches:**
- Company profile (market cap, P/E, beta)
- Key metrics (ROE, ROA, debt/equity)
- Analyst recommendations
- Insider trades
- Earnings surprises
**Output:** BUY/HOLD/SELL/SKIP with confidence, strengths, concerns

#### 3. **RiskManagerAgent** (Position Sizing)
**Purpose:** Risk assessment and position sizing
**Analyzes:**
- Portfolio exposure and concentration
- Historical win rate and P&L
- Kelly Criterion for optimal sizing
- Correlation with existing positions
- Volatility and beta
**Output:** APPROVE/REDUCE/REJECT decision, recommended position %, stop loss, take profit

#### 4. **StrategyBuilderAgent** (Self-Improvement)
**Purpose:** Proposes strategy parameter adjustments based on performance
**Analyzes:**
- Historical trade outcomes (win rate, Sharpe ratio)
- Parameter correlation with successful trades
- Market regime changes
- Overfitting risk
**Output:** Parameter adjustment proposals with expected impact and confidence

#### 5. **RegimeDetectorAgent** (Market Classification)
**Purpose:** Classify market regime for adaptive strategy selection
**Classifies as:**
- BULL: Strong uptrend, price above MAs
- BEAR: Strong downtrend, price below MAs
- SIDEWAYS: Range-bound, choppy
- HIGH_VOL: Volatility > 2x normal
- LOW_VOL: Low volatility, compressed
**Output:** Regime classification, trend strength (0-100), volatility state

#### 6. **TrendAnalystAgent** (Technical Trends - Crypto)
**Purpose:** Analyze price trends and breakout patterns
**Analyzes:**
- Moving average alignments (SMA 20/50/200)
- Trend strength and momentum
- Support/resistance levels
- Golden cross/Death cross patterns
- Price position relative to MAs
**Output:** BUY/HOLD/SELL/SKIP, trend direction, trend strength, signals

#### 7. **MomentumAnalystAgent** (Oscillators - Crypto)
**Purpose:** Analyze momentum indicators and oscillators
**Analyzes:**
- RSI levels (oversold/neutral/overbought)
- MACD signals and crossovers
- Volume patterns (accumulation/distribution)
- Momentum divergences
- Volume confirmation
**Output:** BUY/HOLD/SELL/SKIP, RSI interpretation, momentum state, signals

#### 8. **VolatilityAnalystAgent** (Risk Assessment - Crypto)
**Purpose:** Assess volatility and risk
**Analyzes:**
- ATR (magnitude and trend)
- Bollinger Bands positions
- Volatility squeeze patterns
- Risk/reward based on volatility
- Market regime context
**Output:** BUY/HOLD/SELL/SKIP, volatility state, risk assessment, signals

#### 9. **LearningAgent** (Self-Learning)
**Purpose:** Learn from historical trades to improve over time
**Features:**
- Pattern recognition in winning/losing trades
- Adaptive strategy adjustment
- Performance tracking and feedback loops

### Agent Orchestrator: `src/trading_bot/llm/agents/orchestrator.py`
**Purpose:** Coordinates multiple agents
**Features:**
- Agent registration and lifecycle management
- Task routing to appropriate agents
- Multi-agent consensus voting
- Performance metrics tracking (daily, per-agent)
- Shared memory for inter-agent learning

**Key Methods:**
- `register_agent(agent)`: Register agent
- `get_agent(agent_name)`: Retrieve agent
- `route_task(agent_name, context)`: Execute task and track metrics
- `consensus_vote(task_type, context)`: Get consensus from multiple agents

---

## 4. CONFIGURATION FILES AND ENVIRONMENT VARIABLES

### .env File (Credentials)
```
ROBINHOOD_USERNAME=your_username
ROBINHOOD_PASSWORD=your_password
ROBINHOOD_MFA_SECRET=your_mfa_secret (optional)
ROBINHOOD_DEVICE_TOKEN=your_device_token (optional)
ANTHROPIC_API_KEY=your_anthropic_key (for LLM agents)
FMP_API_KEY=your_fmp_key (for fundamental data)
```

### config.json (Trading Parameters)
**Sections:**
- `trading_mode`: paper or live
- `phase_mode`: experience, proof, trial, scaling
- `order_management`: offset, slippage, polling
- `risk_management`: daily loss %, consecutive losses, position limits
- `portfolio_targets`: profit goals, risk limits
- `crypto`: enabled, mode, budget (if using crypto)
- `strategies`: per-strategy configurations

### Environment-based Config
- Loaded via `Config.from_env_and_json()`
- Environment variables override config.json
- Supports multiple deployment modes

---

## 5. STATE MANAGEMENT AND MONITORING

### Workflow State Machine: `src/trading_bot/orchestrator/workflow.py`

**States:**
1. IDLE: Ready for next operation
2. PRE_MARKET_SCREENING: Pre-market analysis (6:30am EST)
3. TRADE_ANALYSIS: Analyzing opportunities
4. POSITION_OPTIMIZATION: Optimizing portfolio
5. MARKET_EXECUTION: Executing trades at market open (9:30am EST)
6. INTRADAY_MONITORING: Monitoring positions (10am, 11am, 2pm EST)
7. END_OF_DAY_REVIEW: End-of-day analysis (4pm EST)
8. WEEKLY_REVIEW: Weekly performance review (Friday 4pm EST)
9. BACKTESTING: Historical validation
10. ERROR: Error state

**Transitions:**
- START_PRE_MARKET → PRE_MARKET_SCREENING
- SCREENING_COMPLETE → TRADE_ANALYSIS
- ANALYSIS_COMPLETE → POSITION_OPTIMIZATION
- OPTIMIZATION_COMPLETE → MARKET_EXECUTION
- MARKET_OPEN → INTRADAY_MONITORING (from MARKET_EXECUTION)
- EXECUTION_COMPLETE → INTRADAY_MONITORING
- START_MONITORING → INTRADAY_MONITORING (from IDLE)
- MARKET_CLOSE → END_OF_DAY_REVIEW
- REVIEW_COMPLETE → IDLE

**Context Tracking:**
- watchlist: Screening results
- analyzed_symbols: Analysis results
- optimized_trades: Position recommendations
- executed_trades: Completed trades
- daily_pnl: P&L tracking
- trade_count: Trade statistics
- errors: Error tracking

### Trading Orchestrator: `src/trading_bot/orchestrator/trading_orchestrator.py`

**Responsibilities:**
- Coordinates LLM-enhanced trading workflows
- Manages scheduled tasks
- Integrates with multi-agent system
- Tracks portfolio state

**Scheduled Workflows:**
- 6:30am EST: Pre-market screening
- 9:30am EST: Market open execution
- 10:00am, 11:00am, 2:00pm EST: Intraday monitoring
- 4:00pm EST: End-of-day review
- Friday 4:05pm EST: Weekly review

**Key Features:**
- Paper/live/backtest modes
- Multi-agent consensus for trading decisions
- Portfolio tracking (value, cash available)
- Telegram notification integration
- Workflow state management

### Structured Logging: `src/trading_bot/logging/structured_logger.py`

**TradeRecord Model:**
- symbol, side, quantity, entry_price, exit_price
- pnl, pnl_pct, duration
- strategy_name, agent_decisions
- timestamp

**Features:**
- Thread-safe JSONL-based logging
- Daily file rotation (logs/trades/YYYY-MM-DD.jsonl)
- Atomic writes with file locking
- <5ms write latency
- Immutable append-only log

### Health Check Logger: `src/trading_bot/health/health_logger.py`
- Tracks session health events
- Reauth attempts
- Session uptime metrics
- Health check failures

---

## 6. EXISTING CLI AND COMMAND STRUCTURE

### Main CLI Commands

#### 1. **Dashboard Mode**
```bash
python -m trading_bot dashboard
```
- Rich-based CLI dashboard
- Real-time account status
- Position monitoring
- Performance metrics
- Targets vs actuals

#### 2. **Generate Watchlist**
```bash
python -m trading_bot generate-watchlist --preview
python -m trading_bot generate-watchlist --save
python -m trading_bot generate-watchlist --sectors technology,biopharmaceutical
```
- Dynamic watchlist generation via screener
- Sector-based filtering
- Preview or save to config.json

#### 3. **Orchestrator Mode**
```bash
python -m trading_bot orchestrator --orchestrator-mode {live|paper|backtest}
```
- LLM-enhanced trading
- Multi-agent decision making
- Scheduled workflows
- 24/7 crypto support (if enabled)

#### 4. **Trade Mode (Default)**
```bash
python -m trading_bot [--dry-run] [--json]
```
- Normal trading with startup validation
- Async trading loop with heartbeat
- Momentum scanning

### Natural Language Commands (Planned): `src/trading_bot/cli/nl_commands.py`
**Intents:**
- STATUS: Bot status queries
- PERFORMANCE: Performance metrics
- POSITIONS: Open positions
- HEALTH: System health
- ERRORS: Error reporting
- CONFIG: Configuration queries

### Phase CLI: `src/trading_bot/phase/cli.py`
```bash
# Export phase history
python -m trading_bot phase export --start 2025-01-01 --end 2025-01-31 --format csv
python -m trading_bot phase export --start 2025-01-01 --end 2025-01-31 --format json

# Display phase status
python -m trading_bot phase status
```

### Emotional Control CLI: `src/trading_bot/emotional_control/cli.py`
```bash
python -m trading_bot emotional-control status
python -m trading_bot emotional-control reset
python -m trading_bot emotional-control events
```

---

## 7. REST API AND MONITORING

### FastAPI Application: `api/app/main.py`

**Base Endpoints:**
- Health checks
- WebSocket for real-time streaming
- CORS middleware

**API Routes:**

#### State Routes (`/api/state/*`)
- Get bot state snapshot
- Query specific state sections
- Historical state queries

#### Metrics Routes (`/api/metrics/*`)
- Real-time performance metrics
- Win rate, P&L, drawdown
- Per-symbol performance
- Time-windowed aggregations

#### Config Routes (`/api/config/*`)
- Get current configuration
- Validate configuration
- Update configuration (with rollback)

#### Order Routes (`/api/orders/*`)
- Submit orders
- Cancel orders
- Query order status
- Order history

#### Workflow Routes (`/api/workflows/*`)
- Execute workflows
- Query workflow status
- List workflow definitions

#### Command Routes (`/api/commands/*`)
- Pause/resume trading
- Bot control commands
- State manipulation

#### Backtest Routes (`/api/backtests/*`)
- Run backtests
- Query backtest results
- Compare strategy performance

**WebSocket:**
- Real-time state updates (every 5 seconds)
- Broadcast to all connected clients
- State change notifications

---

## 8. SUPPORTED ASSET CLASSES

### Stock Trading
- Robinhood API via robin_stocks
- Paper and live modes
- Pre-market, market hours, after-hours
- Multi-timeframe technical analysis

### Crypto Trading
**Status:** Supported in orchestrator mode
**Features:**
- 24/7 monitoring and trading
- Separate CryptoOrchestrator (background thread)
- Crypto-specific agents:
  - TrendAnalystAgent
  - MomentumAnalystAgent
  - VolatilityAnalystAgent
- Crypto configuration (enabled, mode, budget)

---

## 9. KEY DEPENDENCIES

**Core Dependencies:**
- `robin-stocks>=3.4.0`: Robinhood API
- `pandas==2.3.3`: Data manipulation
- `numpy==1.26.3`: Numerical computing
- `python-dotenv==1.0.0`: Environment config
- `PyYAML==6.0.3`: Configuration files
- `rich==13.7.0`: Terminal formatting

**API Dependencies:**
- `fastapi`: REST API framework
- `pydantic`: Data validation
- `sqlalchemy`: ORM
- `alembic`: Database migrations

**LLM Dependencies:**
- `anthropic`: Claude API client
- `openai`: OpenAI integration

**Testing:**
- `pytest`, `pytest-cov`, `pytest-asyncio`
- `freezegun`: Time mocking
- `mypy`: Type checking
- `ruff`: Linting
- `bandit`: Security scanning

---

## 10. KEY FEATURES SUMMARY

### ✅ Implemented
1. **Multi-Agent System** - 8+ specialized agents with consensus voting
2. **State Machine** - Workflow-based trading (pre-market, intraday, EOD)
3. **Risk Management** - Daily loss limits, position sizing, stops, targets
4. **Phase Progression** - Experience → PoC → Trial → Scaling
5. **Emotional Control** - Position size reduction on loss streaks
6. **Structured Logging** - JSONL-based immutable trade records
7. **Health Monitoring** - Periodic session checks and reauthentication
8. **Dashboard** - Rich-based CLI with real-time metrics
9. **REST API** - FastAPI with WebSocket streaming
10. **Orchestrator** - Scheduled workflows with LLM decision making
11. **Crypto Support** - 24/7 crypto trading in background
12. **Configuration** - Dual system (.env + config.json)
13. **Backtesting** - Historical validation and walk-forward analysis

### 🎯 CLI Exposure Opportunities
The bot has extensive functionality that should be exposed through an enhanced CLI:

**Management Commands:**
- Agent status and metrics
- Workflow execution and monitoring
- Configuration validation and updates
- Phase progression and validation
- Risk metrics and portfolio analysis

**Monitoring Commands:**
- Real-time position tracking
- Performance summary (daily, weekly, monthly)
- Agent decision logging and analysis
- Health check reports
- Error reporting and diagnostics

**Control Commands:**
- Start/stop trading
- Execute specific workflows
- Pause/resume by phase or symbol
- Manual emotional control reset
- Backtest execution and analysis

**Data Commands:**
- Export trade history
- Generate performance reports
- Analyze agent performance
- Examine decision logs

---

## File Structure Summary

```
src/trading_bot/
├── __main__.py                          # Module entry point
├── main.py                              # Main CLI entry point
├── bot.py                               # Core bot class
├── config.py                            # Configuration management
├── startup.py                           # Startup orchestration
├── safety_checks.py                     # Safety validations
├── validator.py                         # Configuration validator

├── account/                             # Account management
│   └── account_data.py                  # Account/position tracking

├── auth/                                # Authentication
│   └── robinhood_auth.py                # Robinhood auth

├── cli/                                 # CLI commands
│   ├── generate_watchlist.py            # Watchlist generation
│   └── nl_commands.py                   # Natural language intents

├── orchestrator/                        # Trading orchestration
│   ├── trading_orchestrator.py          # Main orchestrator
│   ├── crypto_orchestrator.py           # Crypto trading
│   ├── workflow.py                      # State machine
│   ├── scheduler.py                     # Task scheduling
│   └── backtest_harness.py              # Backtesting

├── llm/                                 # LLM and agents
│   ├── claude_manager.py                # LLM manager
│   ├── memory_service.py                # Agent memory
│   ├── agents/
│   │   ├── base_agent.py                # Base agent class
│   │   ├── orchestrator.py              # Agent orchestrator
│   │   ├── news_analyst_agent.py        # Sentiment analysis
│   │   ├── research_agent.py            # Fundamental analysis
│   │   ├── risk_manager_agent.py        # Risk assessment
│   │   ├── strategy_builder_agent.py    # Parameter optimization
│   │   ├── regime_detector_agent.py     # Market regime
│   │   ├── trend_analyst_agent.py       # Technical trends
│   │   ├── momentum_analyst_agent.py    # Momentum analysis
│   │   ├── volatility_analyst_agent.py  # Volatility analysis
│   │   └── learning_agent.py            # Self-learning

├── order_management/                    # Order execution
│   ├── manager.py                       # Order manager
│   ├── calculator.py                    # Price calculations
│   ├── gateways.py                      # Exchange gateways
│   └── models.py                        # Order models

├── risk_management/                     # Risk controls
│   ├── manager.py                       # Risk manager
│   ├── calculator.py                    # Risk calculations
│   ├── atr_calculator.py                # ATR-based sizing
│   ├── stop_adjuster.py                 # Dynamic stops
│   └── target_monitor.py                # Profit targets

├── phase/                               # Phase management
│   ├── manager.py                       # Phase orchestrator
│   ├── models.py                        # Phase models
│   ├── validators.py                    # Transition validators
│   ├── history_logger.py                # Phase history
│   ├── trade_limiter.py                 # Trading constraints
│   └── cli.py                           # Phase CLI

├── health/                              # Health monitoring
│   ├── session_health.py                # Session health checks
│   └── health_logger.py                 # Health logging

├── logging/                             # Structured logging
│   ├── structured_logger.py             # JSONL trade logger
│   ├── trade_record.py                  # Trade record model
│   └── semantic_error.py                # Error tracking

├── dashboard/                           # CLI dashboard
│   ├── dashboard.py                     # Main dashboard
│   ├── data_provider.py                 # Data aggregation
│   ├── display_renderer.py              # Terminal rendering
│   ├── models.py                        # Dashboard models
│   └── __main__.py                      # Dashboard entry point

├── emotional_control/                   # Emotional control
│   ├── tracker.py                       # State tracking
│   ├── config.py                        # Configuration
│   └── cli.py                           # CLI commands

├── market_data/                         # Market data services
│   ├── market_data_service.py           # Data aggregation
│   ├── fmp_client.py                    # FMP API client
│   └── crypto_service.py                # Crypto data

└── indicators/                          # Technical indicators
    ├── calculators.py                   # Indicator calculations
    └── service.py                       # Indicator service
```

---

## Command Examples

```bash
# Start trading bot in default mode
python -m trading_bot

# Dry run (validate without trading)
python -m trading_bot --dry-run

# JSON output for integrations
python -m trading_bot --json

# Launch dashboard
python -m trading_bot dashboard

# Generate watchlist
python -m trading_bot generate-watchlist --preview
python -m trading_bot generate-watchlist --save --sectors technology

# Run LLM orchestrator in paper mode
python -m trading_bot orchestrator --orchestrator-mode paper

# Run LLM orchestrator in live mode
python -m trading_bot orchestrator --orchestrator-mode live

# Export phase history
python -m trading_bot phase export --start 2025-01-01 --end 2025-01-31 --format csv

# Check emotional control state
python -m trading_bot emotional-control status
```

---

## Key Design Principles (Constitution v1.0.0)

- **§Safety_First**: Circuit breakers, paper trading defaults, startup validation
- **§Risk_Management**: Position limits, daily loss caps, consecutive loss tracking
- **§Code_Quality**: Type hints required, 90% test coverage minimum
- **§Audit_Everything**: JSONL logging of all trades, immutable records
- **§Data_Integrity**: Atomic file operations, thread-safe logging
- **§Security**: Credentials from environment, never logged

