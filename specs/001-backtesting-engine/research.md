# Research & Discovery: backtesting-engine

## Research Decisions

### Decision: Event-driven execution model
- **Decision**: Use chronological event-driven simulation (not vectorized backtesting)
- **Rationale**:
  - Prevents look-ahead bias by processing bars sequentially
  - Matches live trading execution model for realistic simulation
  - Easier to debug and validate trade logic
  - Aligns with constitution §Data_Integrity (validate timestamps)
- **Alternatives**:
  - Vectorized backtesting (pandas operations) - faster but harder to prevent look-ahead bias
  - Backtrader library - adds dependency, overkill for MVP daily backtesting
- **Source**: Industry best practices for algorithmic trading backtesting

### Decision: Alpaca as primary data source with Yahoo Finance fallback
- **Decision**: Use Alpaca API for historical data with yfinance as fallback
- **Rationale**:
  - Already using Alpaca for live trading (credentials exist)
  - High-quality data with split/dividend adjustments
  - Yahoo Finance free tier provides backup (spec requirement FR-004)
  - Existing market_data module can be extended
- **Alternatives**:
  - Robin Stocks only - limited historical data access, inconsistent API
  - Yahoo Finance only - free but lower data quality, rate limiting
  - Polygon.io - requires additional paid subscription
- **Source**: Spec requirement FR-001, existing project uses Alpaca

### Decision: Simple order fill model (next bar open)
- **Decision**: Fill orders at next bar's open price with configurable slippage
- **Rationale**:
  - Conservative assumption (worst case for backtest)
  - Simple and deterministic (reproducible results)
  - Adequate for daily bar backtesting (no intraday)
  - Meets spec requirement FR-007
- **Alternatives**:
  - Mid-price fill (current close + next open) / 2 - overly optimistic
  - Volume-weighted fill - requires intraday data (out of scope for MVP)
  - Market impact model - complex, deferred to P2
- **Source**: Spec NFR-010 (deterministic execution)

### Decision: Protocol-based strategy interface
- **Decision**: Define IStrategy Protocol with should_enter() and should_exit() methods
- **Rationale**:
  - Type-safe interface without inheritance complexity
  - Allows multiple strategy implementations
  - Meets constitution §Code_Quality (type hints required)
  - Simple contract: inspect current bar, return True/False
- **Alternatives**:
  - Abstract base class - more rigid inheritance
  - Dict-based configuration - not type-safe
  - Callback functions - harder to test and validate
- **Source**: Python typing.Protocol, constitution §Code_Quality

### Decision: File-based report storage (no database)
- **Decision**: Generate markdown reports and JSON results files in specs/ directory
- **Rationale**:
  - MVP simplicity (no database schema or migrations)
  - Human-readable markdown for analysis
  - Machine-readable JSON for programmatic access
  - Version-controllable results (git tracking)
  - Meets spec requirement FR-015 (backtest-report-template.md)
- **Alternatives**:
  - SQLite database - adds persistence complexity for MVP
  - In-memory only - results lost after run
  - CSV only - harder to read than markdown
- **Source**: Spec deployment considerations (no database changes)

### Decision: Disk-based caching for historical data
- **Decision**: Cache downloaded historical data as parquet files in .backtest_cache/
- **Rationale**:
  - Avoids redundant API calls (spec FR-017)
  - Fast pandas read/write with parquet format
  - Configurable cache directory (env var)
  - Simple invalidation strategy (check date ranges)
- **Alternatives**:
  - No caching - slow, wastes API quota
  - Redis cache - overkill for local tool
  - In-memory only - lost between runs
- **Source**: Spec NFR-002 (performance), FR-017 (caching requirement)

---

## Components to Reuse (7 found)

- src/trading_bot/market_data/market_data_service.py: Real-time data fetching, can extend for historical
- src/trading_bot/market_data/validators.py: Data validation logic (timestamps, price ranges)
- src/trading_bot/market_data/data_models.py: Quote dataclass, can reuse for historical bars
- src/trading_bot/performance/models.py: PerformanceSummary dataclass as starting point
- src/trading_bot/error_handling/retry.py: @with_retry decorator for API calls
- src/trading_bot/auth/robinhood_auth.py: Authentication handling (if using Robin Stocks)
- src/trading_bot/logger.py: TradingLogger for consistent logging

---

## New Components Needed (5 required)

- src/trading_bot/backtest/engine.py: Core backtest execution loop (chronological iteration)
- src/trading_bot/backtest/historical_data_manager.py: Fetch, cache, validate historical OHLCV data
- src/trading_bot/backtest/strategy_protocol.py: IStrategy Protocol definition
- src/trading_bot/backtest/performance_calculator.py: Calculate metrics from trade history
- src/trading_bot/backtest/report_generator.py: Generate markdown reports from BacktestResult

---

## Unknowns & Questions

None - all technical questions resolved during specification and research phases.
