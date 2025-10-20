# Implementation Plan: Backtesting Engine

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Event-driven execution model, Alpaca + Yahoo Finance data, Protocol-based strategy interface
- Components to reuse: 7 (market data service, validators, performance models, retry decorator, auth, logging)
- New components needed: 5 (engine, historical data manager, strategy protocol, performance calculator, report generator)
- Key decisions: Chronological event simulation, next-bar-open fill model, file-based reports, disk caching

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (existing project standard)
- Data Sources: Alpaca API (primary) + yfinance (fallback)
- Data Processing: pandas for OHLCV manipulation, Decimal for precision
- Caching: Parquet files in .backtest_cache/ directory
- Testing: pytest with 90% coverage requirement (constitution)
- Type Checking: mypy with strict mode (constitution)
- Reports: Markdown (human-readable) + JSON (machine-readable)

**Patterns**:
- **Event-Driven Simulation**: Process bars chronologically to prevent look-ahead bias, matches live trading execution model
- **Protocol-Based Strategy Interface**: IStrategy Protocol with should_enter/should_exit methods for type-safe strategy contracts
- **Repository Pattern**: HistoricalDataManager abstracts data fetching from Alpaca/Yahoo Finance
- **Strategy Pattern**: Pluggable trading strategies implementing common interface
- **Dataclass-Heavy Design**: Use @dataclass for all entities (BacktestConfig, Trade, PerformanceMetrics, etc.)
- **Decimal for Money**: Use Decimal type for all monetary calculations to avoid float precision errors

**Dependencies** (new packages required):
- yfinance@0.2.36: Yahoo Finance data source (fallback)
- pyarrow@15.0.0: Fast parquet file I/O for caching
- Optional: matplotlib@3.8.0 for visualization (P3 feature, deferred)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── backtest/
│   ├── __init__.py                    # Public API exports
│   ├── engine.py                       # BacktestEngine class (main execution loop)
│   ├── models.py                       # Dataclasses: BacktestConfig, BacktestResult, Trade, etc.
│   ├── strategy_protocol.py           # IStrategy Protocol definition
│   ├── historical_data_manager.py     # Fetch, cache, validate historical data
│   ├── performance_calculator.py      # Calculate metrics from trades
│   ├── report_generator.py            # Generate markdown/JSON reports
│   ├── exceptions.py                   # BacktestException, DataQualityError, etc.
│   └── utils.py                        # Helper functions (date math, validation)
└── tests/
    └── backtest/
        ├── __init__.py
        ├── test_engine.py              # BacktestEngine tests
        ├── test_models.py              # Model validation tests
        ├── test_historical_data_manager.py
        ├── test_performance_calculator.py
        ├── test_report_generator.py
        ├── fixtures.py                 # Shared test fixtures
        └── sample_strategies.py        # Test strategy implementations

examples/
├── simple_backtest.py                  # Basic usage example
├── strategy_comparison.py              # Compare multiple strategies
└── custom_strategy_example.py          # How to implement IStrategy

specs/001-backtesting-engine/
├── spec.md                             # Feature specification
├── plan.md                             # This file
├── research.md                         # Research decisions
├── data-model.md                       # Entity definitions
├── quickstart.md                       # Integration scenarios
├── contracts/
│   └── api.yaml                        # OpenAPI schema (Python API)
├── NOTES.md                            # Phase checkpoints
└── backtest-report.md                  # Generated report (sample output)
```

**Module Organization**:
- **backtest/engine.py**: Core BacktestEngine class with run() method, chronological iteration loop
- **backtest/models.py**: All dataclasses (BacktestConfig, BacktestResult, Trade, PerformanceMetrics, HistoricalDataBar, Position, BacktestState)
- **backtest/strategy_protocol.py**: IStrategy Protocol with should_enter/should_exit methods
- **backtest/historical_data_manager.py**: HistoricalDataManager class with fetch(), cache(), validate() methods
- **backtest/performance_calculator.py**: PerformanceCalculator class with calculate_metrics() method
- **backtest/report_generator.py**: ReportGenerator class with generate_markdown() and generate_json() methods
- **backtest/exceptions.py**: Custom exceptions (BacktestException, DataQualityError, InsufficientDataError, StrategyError)
- **backtest/utils.py**: Utility functions (trading_days_between, is_market_day, validate_date_range)

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: BacktestConfig, HistoricalDataBar, Trade, PerformanceMetrics, BacktestResult (5 main entities)
- Relationships: BacktestResult contains Trades, PerformanceMetrics, and uses HistoricalDataBars
- Migrations required: No (file-based storage, no database)
- Key validations: Date ranges, positive prices/capital, valid market hours, chronological ordering

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Backtest of 252 trading days (1 year) MUST complete within 30 seconds for single stock
- NFR-002: Historical data fetch and cache MUST complete within 60 seconds for 10 stocks
- NFR-003: Backtest results MUST match manual calculations within 0.01% for simple buy-and-hold strategy
- NFR-010: Backtests with same inputs MUST produce identical results (deterministic execution)

**Implementation Strategies**:
- Use pandas vectorized operations where possible (while avoiding look-ahead bias)
- Cache historical data aggressively (parquet format for fast I/O)
- Avoid Python loops for metric calculations (use pandas/numpy)
- Profile with cProfile if performance targets not met
- Consider Numba JIT compilation for hot loops (if needed)

---

## [SECURITY]

**Authentication Strategy**:
- Alpaca API credentials from environment variables (ALPACA_API_KEY, ALPACA_SECRET_KEY)
- Yahoo Finance is unauthenticated (public data)
- No user-facing authentication (internal developer tool)

**Authorization Model**:
- Not applicable (local tool, no multi-user access)

**Input Validation**:
- Validate all BacktestConfig parameters (date ranges, positive capital, valid symbols)
- Validate historical data (price bounds, volume non-negative, timestamps in UTC)
- Sanitize file paths for cache directory (prevent directory traversal)
- Validate strategy class implements IStrategy protocol (runtime check)

**Data Protection**:
- API keys ONLY in environment variables (constitution §Security)
- Never log API keys or credentials
- Backtest reports contain no PII (only symbol/price data)
- Cache files in .backtest_cache/ added to .gitignore

**Rate Limiting**:
- Respect Alpaca API rate limits (200 requests/minute)
- Use exponential backoff with @with_retry decorator (existing pattern)
- Yahoo Finance fallback if Alpaca quota exhausted
- Cache data to minimize API calls (FR-017)

---

## [EXISTING INFRASTRUCTURE - REUSE] (7 components)

**Services/Modules**:
- src/trading_bot/market_data/market_data_service.py: Real-time data fetching, extend for historical data with date range parameters
- src/trading_bot/market_data/validators.py: Data validation logic (validate_quote can be adapted for historical bars)
- src/trading_bot/performance/models.py: PerformanceSummary dataclass as template for PerformanceMetrics
- src/trading_bot/error_handling/retry.py: @with_retry decorator for API calls with exponential backoff
- src/trading_bot/auth/robinhood_auth.py: Authentication handling (may not be needed for Alpaca, but pattern reusable)
- src/trading_bot/logger.py: TradingLogger for consistent structured logging

**Data Models**:
- src/trading_bot/market_data/data_models.py: Quote dataclass can be template for HistoricalDataBar

**Utilities**:
- src/trading_bot/utils/security.py: Environment variable loading patterns
- src/trading_bot/error_handling/exceptions.py: Base exception classes to inherit from

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

**Backend**:
- src/trading_bot/backtest/engine.py: BacktestEngine class with chronological execution loop
  - run() method: Main backtest execution
  - _process_bar() method: Handle single OHLCV bar
  - _check_exits() method: Evaluate exit conditions for open positions
  - _check_entries() method: Evaluate entry signals
  - _fill_order() method: Simulate order fill at next bar open
  - _update_equity() method: Calculate portfolio value

- src/trading_bot/backtest/historical_data_manager.py: HistoricalDataManager class
  - fetch_data() method: Download from Alpaca or Yahoo Finance
  - cache_data() method: Save to parquet file
  - load_cached_data() method: Load from parquet if valid
  - validate_data() method: Check for gaps, invalid prices
  - _get_cache_path() method: Generate cache file path

- src/trading_bot/backtest/strategy_protocol.py: IStrategy Protocol definition
  - should_enter() method signature
  - should_exit() method signature
  - Optional: position_size() method for dynamic sizing

- src/trading_bot/backtest/performance_calculator.py: PerformanceCalculator class
  - calculate_metrics() method: Generate PerformanceMetrics from trades
  - _calculate_returns() method: Total, annualized, CAGR
  - _calculate_drawdown() method: Max drawdown and duration
  - _calculate_sharpe() method: Risk-adjusted return
  - _calculate_trade_stats() method: Win rate, profit factor, avg win/loss

- src/trading_bot/backtest/report_generator.py: ReportGenerator class
  - generate_markdown() method: Create markdown report from BacktestResult
  - generate_json() method: Export JSON for programmatic access
  - _format_trade_table() method: Format trades as markdown table
  - _format_equity_curve() method: Format equity curve data

**Tests**:
- tests/backtest/test_engine.py: Test BacktestEngine execution
  - test_buy_and_hold_strategy: Validate simple strategy
  - test_insufficient_capital: Verify capital checks
  - test_chronological_execution: Ensure no look-ahead bias
  - test_reproducibility: Same inputs -> same outputs

- tests/backtest/test_historical_data_manager.py: Test data fetching and caching
  - test_fetch_alpaca_data: Fetch from Alpaca API
  - test_fetch_yahoo_fallback: Fallback to Yahoo Finance
  - test_cache_persistence: Verify parquet caching
  - test_data_validation: Check gap detection

- tests/backtest/test_performance_calculator.py: Test metric calculations
  - test_win_rate_calculation: Verify win rate formula
  - test_sharpe_ratio_calculation: Validate Sharpe ratio
  - test_drawdown_calculation: Check max drawdown logic
  - test_metrics_accuracy: Compare to manual calculations (NFR-003)

- tests/backtest/test_report_generator.py: Test report generation
  - test_markdown_format: Verify markdown structure
  - test_json_export: Check JSON schema
  - test_trade_table_formatting: Validate table rendering

**Documentation**:
- examples/simple_backtest.py: Basic backtest example
- examples/strategy_comparison.py: Compare multiple strategies
- examples/custom_strategy_example.py: Implement IStrategy

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local development tool (no deployment infrastructure changes)
- Env vars: New optional variables for data sources
- Breaking changes: No (new module only, backward compatible)
- Migration: No (no database changes)

**Build Commands**:
- No changes to build process
- Add optional dependency group: `pip install -e ".[backtest]"`
- CI can run backtest tests: `pytest tests/backtest/`

**Environment Variables** (update secrets.schema.json):
- New optional: BACKTEST_DATA_SOURCE (default: "alpaca")
  - Staging: "alpaca"
  - Production: "alpaca" (not applicable, local tool)
- New optional: BACKTEST_CACHE_DIR (default: ".backtest_cache/")
  - Staging: ".backtest_cache/"
  - Production: ".backtest_cache/"
- New optional: YAHOO_FINANCE_ENABLED (default: "true")
  - Set to "false" to disable fallback
- Existing: ALPACA_API_KEY, ALPACA_SECRET_KEY (already in use)

**Schema Update Required**: No - all variables optional with defaults

**Database Migrations**:
- Not required (file-based storage only)

**Smoke Tests**:
- Not applicable (internal tool, no API endpoints)
- Validation via pytest: `pytest tests/backtest/ -v`

**Platform Coupling**:
- None - pure Python module, no platform-specific dependencies
- Works on Windows, macOS, Linux
- No Docker, Railway, or Vercel changes

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- No breaking changes to existing modules
- All tests pass with ≥90% coverage (constitution requirement)
- Type checking passes with no errors (mypy --strict)
- API keys loaded from environment variables only
- Deterministic execution: same inputs -> same outputs (NFR-010)

**Validation Tests**:
```python
# tests/backtest/test_acceptance.py

def test_buy_and_hold_accuracy():
    """NFR-003: Results match manual calculations within 0.01%."""
    # Run buy-and-hold backtest for AAPL 2023
    # Calculate expected return manually: (last_price - first_price) / first_price
    # Assert actual return within 0.01% of expected

def test_performance_benchmark():
    """NFR-001: 1 year backtest completes in <30 seconds."""
    start_time = time.time()
    # Run backtest for 252 trading days
    execution_time = time.time() - start_time
    assert execution_time < 30.0

def test_reproducibility():
    """NFR-010: Same inputs produce identical results."""
    result1 = engine.run(config)
    result2 = engine.run(config)
    assert result1.metrics == result2.metrics
    assert result1.trades == result2.trades

def test_constitution_compliance():
    """§Code_Quality: Type hints, test coverage, single-purpose functions."""
    # Run mypy: mypy src/trading_bot/backtest/
    # Run coverage: pytest --cov=src/trading_bot/backtest --cov-fail-under=90
    # Verify functions <30 lines (code quality check)
```

**Rollback Plan**:
- Standard 3-command rollback (git revert, push)
- No database migrations to reverse
- Delete .backtest_cache/ directory if needed
- Remove optional dependency: `pip uninstall yfinance pyarrow`

**Artifact Strategy**:
- Not applicable (local development tool, no build artifacts)
- Module installed via `pip install -e .` in dev environment

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Scenario 1: Install dependencies and configure environment
- Scenario 2: Run simple backtest with example strategy
- Scenario 3: Implement custom strategy using IStrategy protocol
- Scenario 4: Run validation tests (pytest, mypy, ruff, bandit)
- Scenario 5: Compare multiple strategies side-by-side
- Scenario 6: Manual testing checklist (data loading, metrics, reports)

---

## [IMPLEMENTATION ROADMAP]

**Phase 1: Core Data Infrastructure (US1)**
1. Create backtest/models.py with dataclasses (BacktestConfig, HistoricalDataBar, Trade, etc.)
2. Implement backtest/historical_data_manager.py
   - Alpaca data fetching
   - Yahoo Finance fallback
   - Parquet caching
   - Data validation (gaps, invalid prices)
3. Write tests: test_historical_data_manager.py
4. Validate: Can fetch and cache 1 year of AAPL data in <60 seconds

**Phase 2: Strategy Interface (US2 - Part 1)**
1. Define backtest/strategy_protocol.py with IStrategy Protocol
2. Create example strategies in examples/
   - BuyAndHoldStrategy (simple test case)
   - MomentumStrategy (moving average crossover)
3. Write tests: test_strategy_protocol.py (runtime protocol checking)

**Phase 3: Backtest Engine (US2 - Part 2)**
1. Implement backtest/engine.py with BacktestEngine class
   - Chronological iteration loop
   - Entry signal checking (should_enter)
   - Exit signal checking (should_exit)
   - Order fill simulation (next bar open)
   - Cash and position tracking
   - Equity curve generation
2. Write tests: test_engine.py
   - test_buy_and_hold_strategy (end-to-end)
   - test_insufficient_capital (cash validation)
   - test_chronological_execution (no look-ahead)
   - test_reproducibility (deterministic)
3. Validate: Buy-and-hold strategy returns match manual calculation (NFR-003)

**Phase 4: Performance Metrics (US3)**
1. Implement backtest/performance_calculator.py
   - Total return, annualized return, CAGR
   - Win rate, profit factor, avg win/loss
   - Maximum drawdown and duration
   - Sharpe ratio
2. Write tests: test_performance_calculator.py
   - test_win_rate_calculation
   - test_sharpe_ratio_calculation
   - test_drawdown_calculation
   - test_metrics_accuracy (compare to known results)
3. Validate: All metrics calculate correctly for sample trade history

**Phase 5: Report Generation (US4)**
1. Implement backtest/report_generator.py
   - Markdown report using backtest-report-template.md
   - JSON export for programmatic access
   - Trade table formatting
   - Equity curve data
2. Write tests: test_report_generator.py
   - test_markdown_format
   - test_json_export
   - test_complete_report (all sections present)
3. Validate: Generated report matches template structure

**Phase 6: Integration and Acceptance**
1. Write integration tests: test_integration.py
   - End-to-end backtest flow (config -> run -> report)
   - Multi-symbol backtesting
   - Data quality handling (gaps, errors)
2. Write acceptance tests: test_acceptance.py
   - NFR-001: Performance benchmark (<30s for 1 year)
   - NFR-003: Accuracy within 0.01%
   - NFR-010: Reproducibility
3. Create examples:
   - examples/simple_backtest.py
   - examples/strategy_comparison.py
   - examples/custom_strategy_example.py
4. Update documentation:
   - Update README.md with backtest module
   - Add quickstart.md examples
   - Document IStrategy protocol in docstrings

**Phase 7: Quality Gates (Constitution Compliance)**
1. Run test coverage: `pytest --cov=src/trading_bot/backtest --cov-fail-under=90`
   - Must achieve ≥90% coverage (§Pre_Deploy)
2. Run type checking: `mypy src/trading_bot/backtest/`
   - Must pass with no errors (§Code_Quality)
3. Run linting: `ruff check src/trading_bot/backtest/`
   - Must pass with no violations
4. Run security check: `bandit -r src/trading_bot/backtest/`
   - No high-severity issues
5. Manual validation:
   - Run quickstart.md scenarios
   - Verify accuracy (NFR-003)
   - Benchmark performance (NFR-001)

---

## [RISKS AND MITIGATIONS]

**Risk: Alpaca API rate limits**
- Mitigation: Aggressive caching (FR-017), Yahoo Finance fallback (FR-004)
- Impact: Low (cache minimizes API calls)

**Risk: Look-ahead bias in backtest**
- Mitigation: Event-driven execution, strict chronological iteration, comprehensive tests
- Impact: Critical (invalidates backtest results)

**Risk: Float precision errors in P&L calculations**
- Mitigation: Use Decimal type for all monetary calculations
- Impact: Medium (affects accuracy NFR-003)

**Risk: Performance not meeting 30-second target (NFR-001)**
- Mitigation: Pandas vectorization, profiling with cProfile, consider Numba if needed
- Impact: Low (30s is conservative for daily bars)

**Risk: Strategy implementations not following IStrategy protocol**
- Mitigation: Runtime protocol checking, clear documentation, example strategies
- Impact: Medium (user error in custom strategies)

**Risk: Historical data quality issues (gaps, invalid prices)**
- Mitigation: Comprehensive validation (FR-002), warning system (FR-016), graceful skipping (FR-018)
- Impact: Medium (affects backtest validity)

---

## [SUCCESS CRITERIA]

Feature is successful when:
1. ✅ Can load 1 year of daily OHLCV data in <60 seconds with caching (NFR-002)
2. ✅ Buy-and-hold backtest matches manual calculation within 0.01% (NFR-003)
3. ✅ Backtest of 252 trading days completes in <30 seconds (NFR-001)
4. ✅ All metrics (return, Sharpe, drawdown) calculate correctly
5. ✅ Same config produces identical results (deterministic - NFR-010)
6. ✅ Generated reports match backtest-report-template.md format
7. ✅ Test coverage ≥90% (constitution §Pre_Deploy)
8. ✅ Type checking passes with no errors (constitution §Code_Quality)
9. ✅ Data gaps detected and reported in warnings (FR-016)
10. ✅ At least 2 custom strategies validated using backtest engine

---

## [NEXT STEPS]

After plan approval:
1. Run `/tasks` to generate TDD task breakdown
2. Implement Phase 1 (Historical Data Infrastructure)
3. Implement Phase 2 (Strategy Interface)
4. Implement Phase 3 (Backtest Engine Core)
5. Implement Phase 4 (Performance Metrics)
6. Implement Phase 5 (Report Generation)
7. Complete Phase 6 (Integration Tests)
8. Validate Phase 7 (Quality Gates)
9. Create pull request for review
10. Merge to main and validate with real strategies
