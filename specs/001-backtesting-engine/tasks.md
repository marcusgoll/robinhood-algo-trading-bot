# Tasks: Backtesting Engine

## [CODEBASE REUSE ANALYSIS]
Scanned: D:/Coding/Stocks/src/trading_bot/

[EXISTING - REUSE]
- âœ… MarketDataService (src/trading_bot/market_data/market_data_service.py) - Extend for historical data
- âœ… validators.py (src/trading_bot/market_data/validators.py) - Data validation patterns
- âœ… PerformanceTracker (src/trading_bot/performance/tracker.py) - Performance tracking patterns
- âœ… @with_retry decorator (src/trading_bot/error_handling/retry.py) - Exponential backoff for API calls
- âœ… TradingLogger (src/trading_bot/logger.py) - Structured logging
- âœ… Quote dataclass (src/trading_bot/market_data/data_models.py) - Template for HistoricalDataBar
- âœ… Environment variable patterns (src/trading_bot/utils/security.py) - API key loading

[NEW - CREATE]
- ðŸ†• BacktestEngine (no existing backtest execution pattern)
- ðŸ†• HistoricalDataManager (no historical data fetching pattern)
- ðŸ†• IStrategy Protocol (no strategy interface pattern)
- ðŸ†• PerformanceCalculator (extend existing performance tracking)
- ðŸ†• ReportGenerator (no markdown/JSON report pattern)

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 2: Foundational (data models, directory structure - blocks all stories)
2. Phase 3: US1 [P1] - Historical data loading (independent, required for all)
3. Phase 4: US2 [P1] - Strategy execution engine (depends on US1)
4. Phase 5: US3 [P1] - Performance metrics (depends on US2)
5. Phase 6: US4 [P1] - Report generation (depends on US3)
6. Phase 7: US5 [P2] - Trading costs (depends on US2, US3)
7. Phase 8: Polish & Cross-Cutting Concerns

## [PARALLEL EXECUTION OPPORTUNITIES]
- US1: T010, T011, T012 (models, historical data manager, caching - different files)
- US2: T020, T021 (strategy protocol, example strategies - independent)
- US3: T030, T031, T032 (different metric calculation methods)
- US4: T040, T041 (markdown and JSON report generators - independent)
- Phase 7: T070, T071, T072, T073 (different test files)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phases 3-6 (US1-US4 only)
**Incremental delivery**: US1 â†’ US2 â†’ US3 â†’ US4 â†’ staging validation â†’ US5-US7
**Testing approach**: TDD required - 90% coverage per constitution

---

## Phase 1: Setup

- [X] T001 Create project structure per plan.md
  - Directories: src/trading_bot/backtest/, tests/backtest/, examples/
  - Files: __init__.py in each directory
     Created backtest project structure (backtest/, tests/backtest/, examples/)
     Evidence: Directories created successfully
     Committed: 35617ae
  - Pattern: src/trading_bot/performance/ structure
  - From: plan.md [STRUCTURE]

- [X] T002 [P] Add new dependencies to requirements.txt
  - Libraries: yfinance@0.2.36, pyarrow@15.0.0
  - Optional: matplotlib@3.8.0 (P3 feature, commented out)
  - Pattern: existing requirements.txt
  - From: plan.md [ARCHITECTURE DECISIONS]

- [X] T003 [P] Add .backtest_cache/ to .gitignore
  - Entry: .backtest_cache/ (cache directory for historical data)
  - Pattern: existing .gitignore entries
  - From: plan.md [SECURITY]

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Core data models and infrastructure that blocks all user stories

- [X] T005 Create backtest data models in src/trading_bot/backtest/models.py
  - Dataclasses: BacktestConfig, HistoricalDataBar, Trade, PerformanceMetrics, BacktestResult, Position, BacktestState
  - Fields: Per data-model.md entity definitions
  - Validations: Positive prices/capital, valid date ranges, UTC timestamps
     Created 7 data models with comprehensive validation and type hints
     Evidence: All models use Decimal for money, UTC-only timestamps, full __post_init__ validation
     Committed: 5301396
  - REUSE: Quote dataclass pattern (src/trading_bot/market_data/data_models.py)
  - Pattern: src/trading_bot/performance/models.py
  - From: data-model.md all entities

- [X] T006 [P] Create backtest exceptions in src/trading_bot/backtest/exceptions.py
  - Classes: BacktestException, DataQualityError, InsufficientDataError, StrategyError
  - Inheritance: Inherit from base exception classes
  - REUSE: Exception patterns (src/trading_bot/error_handling/exceptions.py)
  - Pattern: src/trading_bot/market_data/exceptions.py
  - From: plan.md [STRUCTURE]

- [X] T007 [P] Create backtest utilities in src/trading_bot/backtest/utils.py
  - Functions: trading_days_between(), is_market_day(), validate_date_range()
  - Validations: UTC timestamps, market hours, chronological ordering
  - Pattern: src/trading_bot/utils/ modules
  - From: plan.md [STRUCTURE]

---

## Phase 3: User Story 1 [P1] - Load historical data for backtesting

**Story Goal**: Fetch, cache, and validate historical OHLCV data from multiple sources

**Independent Test Criteria**:
- [ ] User requests AAPL daily data for 2023 â†’ fetches 252 bars from Alpaca
- [ ] Alpaca API fails â†’ automatically falls back to Yahoo Finance
- [ ] Data has gaps or invalid prices â†’ validation detects and reports warnings
- [ ] Repeat backtest with same symbols â†’ loads from cache (no redundant API calls)

### Tests

- [X] T010 [P] [US1] Write test: HistoricalDataManager fetches from Alpaca
  - File: tests/backtest/test_historical_data_manager.py
  - Test: test_fetch_alpaca_data() - Verify Alpaca API integration
  - Mock: Alpaca API responses
  - Pattern: tests/market_data/ test patterns
  - Coverage: â‰¥90% (new code must be 100%)

- [X] T011 [P] [US1] Write test: Yahoo Finance fallback when Alpaca fails
  - Notes: Test for Yahoo Finance fallback written (RED phase - failing as expected)
  - Evidence: pytest: FAILED (AttributeError - historical_data_manager module does not exist)
  - Committed: 2ceafe9
  - File: tests/backtest/test_historical_data_manager.py
  - Test: test_fetch_yahoo_fallback() - Verify fallback mechanism
  - Simulate: Alpaca API failure, Yahoo Finance success
  - Pattern: tests/error_handling/ retry patterns

- [X] T012 [P] [US1] Write test: Data validation detects gaps and invalid prices
  - File: tests/backtest/test_historical_data_manager.py
  - Test: test_data_validation() - Check gap detection logic
  - Cases: Missing dates, negative prices, zero volume
  - Pattern: tests/market_data/test_validators.py

- [X] T013 [P] [US1] Write test: Parquet caching persists and loads data
  - File: tests/backtest/test_historical_data_manager.py
  - Test: test_cache_persistence() - Verify parquet I/O
  - Verify: Cache hit on second request, no redundant API call
  - Pattern: tests/performance/test_cache.py

### Implementation

- [X] T015 [US1] Implement HistoricalDataManager in src/trading_bot/backtest/historical_data_manager.py
  - Methods: fetch_data(), cache_data(), load_cached_data(), validate_data(), _get_cache_path()
  - Data sources: Alpaca API (primary), yfinance (fallback)
  - Caching: Parquet files in .backtest_cache/{symbol}_{start}_{end}.parquet
  - Validation: Check gaps, negative prices, zero volume, chronological order
  - REUSE: MarketDataService patterns (src/trading_bot/market_data/market_data_service.py)
  - REUSE: @with_retry decorator (src/trading_bot/error_handling/retry.py)
  - REUSE: validators.py patterns (src/trading_bot/market_data/validators.py)
  - REUSE: TradingLogger (src/trading_bot/logger.py)
  - Pattern: src/trading_bot/market_data/market_data_service.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [X] T016 [US1] Add Alpaca historical data API integration
  - Method: _fetch_alpaca_data() in HistoricalDataManager
  - API: Alpaca Bars API with date range parameters
  - Adjustments: Split-adjusted, dividend-adjusted prices
  - Error handling: API failures, rate limits (200/min)
  - REUSE: API key patterns (src/trading_bot/utils/security.py)
  - Pattern: src/trading_bot/market_data/market_data_service.py

- [x] T017 [US1] Add Yahoo Finance fallback integration (✓ da4eaeb)
  - Method: _fetch_yahoo_data() in HistoricalDataManager
  - Library: yfinance.download()
  - Fallback logic: Try Alpaca first, Yahoo Finance on failure
  - Data mapping: Convert Yahoo format to HistoricalDataBar
  - From: plan.md [EXISTING INFRASTRUCTURE - REUSE]
  - **Status**: DONE
  - **Evidence**: pytest: TestYahooFinanceFallback - 2/2 passing, all 50 backtest tests passing
  - **Notes**: Implemented Yahoo Finance fallback with yfinance.download(). Auto-adjust=True for split/dividend corrections. Converted DataFrame to HistoricalDataBar list with proper UTC timezone handling. Fixed test suite to use manual exception handling for InsufficientDataError verification.

### Integration

- [X] T018 [US1] Write integration test: End-to-end data loading
  - Notes: Integration test suite created with 5 comprehensive tests for real API data loading
  - Evidence: pytest: 5 integration tests created (auto-skip when ALPACA_API_KEY not set)
  - Committed: 335d8a4
  - File: tests/backtest/test_integration_data.py
  - Tests:
    * test_load_one_year_data() - Load AAPL 2023 (~252 bars), validate OHLCV, check gaps
    * test_load_multiple_stocks_performance() - Load 5 stocks (<30s target per NFR-002)
    * test_data_quality_validation_integration() - Validate real API data quality
    * test_api_fallback_to_yahoo_finance() - Test Alpaca → Yahoo fallback with invalid credentials
    * test_insufficient_data_error() - Error handling for invalid symbols
  - Documentation: tests/backtest/README.md (setup, run commands, performance benchmarks)
  - Markers: @pytest.mark.integration, @pytest.mark.slow, auto-skip if ALPACA_API_KEY not set
  - Performance: <30s for 5 stocks (extrapolates to <60s for 10 stocks per NFR-002)
  - Pattern: tests/integration/test_market_data_integration.py
  - **Status**: DONE

---

## Phase 4: User Story 2 [P1] - Execute strategy against historical data

**Story Goal**: Chronological execution of strategy logic with position tracking

**Independent Test Criteria**:
- [ ] Run buy-and-hold strategy on AAPL 2023 â†’ enters once, holds to end
- [ ] Strategy tries to buy with insufficient capital â†’ trade rejected
- [ ] Iterate through 252 bars in order â†’ no look-ahead bias (can't see future data)

### Tests

- [X] T020 [P] [US2] Write test: IStrategy protocol runtime checking
  - File: tests/backtest/test_strategy_protocol.py
  - Test: test_protocol_compliance() - Verify should_enter/should_exit methods exist
  - Cases: Valid strategy, missing methods, incorrect signatures
  - Pattern: Python Protocol runtime checking patterns

- [X] T021 [P] [US2] Write test: BacktestEngine chronological execution
  - File: tests/backtest/test_engine.py
  - Test: test_chronological_execution() - Verify no look-ahead bias
  - Strategy: Track what data is visible at each bar
  - Assert: Can only see past data, not future
  - Pattern: tests/order_management/ execution patterns

- [X] T022 [P] [US2] Write test: Buy-and-hold strategy executes correctly
  - File: tests/backtest/test_engine.py
  - Test: test_buy_and_hold_strategy() - End-to-end simple strategy
  - Expected: One buy at start, one sell at end
  - Verify: P&L matches (end_price - start_price) / start_price
  - From: spec.md Success Criteria #2

- [X] T023 [P] [US2] Write test: Insufficient capital prevents trades
  - File: tests/backtest/test_engine.py
  - Test: test_insufficient_capital() - Verify cash validation
  - Scenario: Initial capital too low for position
  - Expected: Trade rejected, warning logged
  - Pattern: tests/risk_management/ capital validation tests

- [X] T024 [P] [US2] Write test: Reproducibility (deterministic execution)
  - File: tests/backtest/test_engine.py
  - Test: test_reproducibility() - Same inputs â†’ same outputs
  - Run: Same BacktestConfig twice
  - Assert: Identical metrics, trades, equity curve
  - From: spec.md NFR-010

### Implementation

- [X] T025 [US2] Define IStrategy protocol in src/trading_bot/backtest/strategy_protocol.py
  - Methods: should_enter(bars: List[HistoricalDataBar]) -> bool, should_exit(position: Position, bars: List[HistoricalDataBar]) -> bool
  - Optional: position_size(capital: float, price: float) -> int
  - Docstrings: Clear documentation of parameters and return values
  - Type hints: Full type annotations with generics if needed
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [X] T026 [P] [US2] Create example strategies in examples/
  - Files: examples/simple_backtest.py, examples/sample_strategies.py
  - Strategies: BuyAndHoldStrategy (always buy once), MomentumStrategy (MA crossover)
  - Purpose: Test cases and documentation examples
  - Pattern: IStrategy protocol implementation
  - From: plan.md [IMPLEMENTATION ROADMAP] Phase 2

- [X] T027 [US2] Implement BacktestEngine core in src/trading_bot/backtest/engine.py
  - Class: BacktestEngine with run(config: BacktestConfig) -> BacktestResult
  - Chronological loop: Iterate bars in time order
  - State tracking: Cash, positions, equity curve
  - REUSE: TradingLogger (src/trading_bot/logger.py)
  - Pattern: Event-driven execution (plan.md pattern)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]
  - **Status**: DONE
  - **Evidence**: Created BacktestEngine with chronological execution, position tracking, and equity curve generation
  - **Tests**: test_buy_and_hold_strategy passing

- [X] T028 [US2] Implement entry signal checking in BacktestEngine
  - Method: _check_entries(current_bar: HistoricalDataBar, historical_bars: List[HistoricalDataBar])
  - Logic: Call strategy.should_enter() with visible historical data only
  - Capital check: Verify sufficient cash for position
  - Fill simulation: First bar at open, subsequent bars at close
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] engine methods
  - **Status**: DONE
  - **Evidence**: Implemented in BacktestEngine._check_entries() with capital validation and realistic fill simulation
  - **Tests**: test_buy_and_hold_strategy passing

- [X] T029 [US2] Implement exit signal checking in BacktestEngine
  - Method: _check_exits(current_bar: HistoricalDataBar, historical_bars: List[HistoricalDataBar])
  - Logic: Call strategy.should_exit() for all open positions
  - Fill simulation: Next bar open price
  - Tracking: Record exit reason (strategy_signal, stop_loss, take_profit, end_of_data)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] engine methods
  - **Status**: DONE
  - **Evidence**: Implemented _check_exits() and _close_position() with strategy_signal and end_of_data exit reasons
  - **Tests**: test_buy_and_hold_strategy passing (exits with end_of_data reason)
  - **Notes**: Includes end-of-backtest cleanup via _close_all_positions() method

- [X] T030 [US2] Implement position and cash tracking in BacktestEngine
  - Methods: _fill_order(), _update_equity()
  - State: Current cash, open positions, equity curve (time series)
  - Validation: Prevent trading when cash < position cost
  - Logging: Log all fills, rejections, position updates
  - REUSE: TradingLogger (src/trading_bot/logger.py)
  - Pattern: src/trading_bot/order_management/ position tracking
  - **Status**: DONE
  - **Evidence**: Implemented _update_equity(), _update_position_prices(), capital validation in _check_entries()
  - **Tests**: test_buy_and_hold_strategy passing (equity curve tracking verified)

### Integration

- [x] T031 [US2] Write integration test: Complete backtest flow
  - File: tests/backtest/test_integration_engine.py
  - Test: test_complete_backtest_flow() - Config â†’ run â†’ result
  - Strategy: Simple momentum strategy
  - Data: Real historical data (1 year AAPL)
  - Verify: All trades recorded, equity curve generated
  - Pattern: End-to-end integration test
  - **Status**: DONE
  - **Commit**: 98da98d
  - **Notes**: Two test scenarios: (1) Full backtest with 2 trades generating 42.57% return, (2) No-trade scenario with insufficient data. All validations passing.
  - **Evidence**: pytest: test_complete_backtest_flow and test_complete_backtest_flow_no_trades passing (2 tests)

---

## Phase 5: User Story 3 [P1] - Calculate performance metrics from results

**Story Goal**: Compute standard performance statistics from trade history

**Independent Test Criteria**:
- [ ] Sample trade history (10 trades, 6 wins, 4 losses) â†’ win rate = 60%
- [ ] Equity curve with peak-to-trough decline â†’ max drawdown calculated correctly
- [ ] Return series with volatility â†’ Sharpe ratio matches manual calculation

### Tests

- [X] T035 [P] [US3] Write test: Win rate calculation accuracy
  - File: tests/backtest/test_performance_calculator.py
  - Test: test_win_rate_calculation() - Verify formula
  - Given: 10 trades (6 wins, 4 losses)
  - Expected: 60% win rate
  - Pattern: tests/performance/ metric tests

- [X] T036 [P] [US3] Write test: Sharpe ratio calculation
  - File: tests/backtest/test_performance_calculator.py
  - Test: test_sharpe_ratio_calculation() - Verify risk-adjusted return
  - Given: Sample returns, risk-free rate = 2%
  - Expected: Sharpe ratio matches manual calculation
  - From: spec.md FR-013
  - Notes: Test written with comprehensive equity curve (13 monthly data points, ~19% total return)
  - Evidence: pytest: ModuleNotFoundError - PerformanceCalculator.calculate_sharpe_ratio() does not exist
  - Status: TDD RED phase complete - test fails as expected until implementation

- [X] T037 [P] [US3] Write test: Maximum drawdown calculation
  - File: tests/backtest/test_performance_calculator.py
  - Test: test_drawdown_calculation() - Check peak-to-trough logic
  - Given: Equity curve with known drawdown
  - Expected: Max drawdown = 15%, duration = 42 days (Feb 1 to Mar 15)
  - Pattern: Standard drawdown calculation
  - Notes: Test written (TDD RED phase - failing as expected)
  - Evidence: pytest: ModuleNotFoundError - performance_calculator module does not exist

- [ ] T038 [P] [US3] Write test: Metrics accuracy vs manual calculations
  - File: tests/backtest/test_performance_calculator.py
  - Test: test_metrics_accuracy() - Verify all metrics
  - Given: Known trade history with pre-calculated metrics
  - Expected: All metrics within 0.01% of expected (NFR-003)
  - From: spec.md NFR-003

### Implementation

- [ ] T040 [US3] Implement PerformanceCalculator in src/trading_bot/backtest/performance_calculator.py
  - Class: PerformanceCalculator with calculate_metrics(trades, equity_curve, config) -> PerformanceMetrics
  - Methods: _calculate_returns(), _calculate_drawdown(), _calculate_sharpe(), _calculate_trade_stats()
  - REUSE: PerformanceTracker patterns (src/trading_bot/performance/tracker.py)
  - Pattern: src/trading_bot/performance/models.py for PerformanceMetrics structure
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T041 [P] [US3] Implement return calculations
  - Method: _calculate_returns() in PerformanceCalculator
  - Metrics: Total return, annualized return, CAGR
  - Formula: CAGR = (end_value / start_value) ^ (1 / years) - 1
  - From: spec.md FR-010

- [ ] T042 [P] [US3] Implement drawdown calculations
  - Method: _calculate_drawdown() in PerformanceCalculator
  - Metrics: Maximum drawdown (peak-to-trough), max drawdown duration (days)
  - Algorithm: Running max equity, calculate all drawdowns, find maximum
  - From: spec.md FR-012

- [ ] T043 [P] [US3] Implement Sharpe ratio calculation
  - Method: _calculate_sharpe() in PerformanceCalculator
  - Formula: (annualized_return - risk_free_rate) / annualized_volatility
  - Risk-free rate: From BacktestConfig (default 0.02)
  - From: spec.md FR-013

- [ ] T044 [P] [US3] Implement trade statistics calculations
  - Method: _calculate_trade_stats() in PerformanceCalculator
  - Metrics: Win rate, profit factor, average win, average loss
  - Profit factor: Gross profit / gross loss
  - From: spec.md FR-011

### Integration

- [ ] T045 [US3] Write integration test: Metrics from real backtest
  - File: tests/backtest/test_integration_metrics.py
  - Test: test_metrics_from_real_backtest() - End-to-end metric calculation
  - Run: Complete backtest with known strategy
  - Verify: All metrics calculated, values reasonable
  - Pattern: Integration test with real data

---

## Phase 6: User Story 4 [P1] - Generate backtest report

**Story Goal**: Create human-readable markdown and machine-readable JSON reports

**Independent Test Criteria**:
- [ ] BacktestResult provided â†’ generates markdown with all required sections
- [ ] Report includes performance metrics, trade table, equity curve data
- [ ] JSON export contains same data in structured format

### Tests

- [ ] T050 [P] [US4] Write test: Markdown report format validation
  - File: tests/backtest/test_report_generator.py
  - Test: test_markdown_format() - Verify markdown structure
  - Check: All required sections present (metrics, trades, warnings)
  - Pattern: Markdown template matching

- [ ] T051 [P] [US4] Write test: JSON export schema validation
  - File: tests/backtest/test_report_generator.py
  - Test: test_json_export() - Check JSON structure
  - Verify: All fields present, correct types, valid JSON
  - Pattern: JSON schema validation

- [ ] T052 [P] [US4] Write test: Trade table formatting
  - File: tests/backtest/test_report_generator.py
  - Test: test_trade_table_formatting() - Verify table rendering
  - Check: Columns aligned, dates formatted, P&L with signs
  - Pattern: Table formatting tests

- [ ] T053 [P] [US4] Write test: Complete report generation
  - File: tests/backtest/test_report_generator.py
  - Test: test_complete_report() - End-to-end report creation
  - Given: Sample BacktestResult
  - Verify: Report file created, all sections populated
  - Pattern: File generation tests

### Implementation

- [ ] T055 [US4] Implement ReportGenerator in src/trading_bot/backtest/report_generator.py
  - Class: ReportGenerator with generate_markdown(), generate_json()
  - Methods: _format_trade_table(), _format_equity_curve(), _format_metrics()
  - Output: Save to specs/001-backtesting-engine/backtest-reports/
  - REUSE: TradingLogger patterns for file I/O (src/trading_bot/logger.py)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T056 [P] [US4] Implement markdown report generation
  - Method: generate_markdown(result: BacktestResult, output_path: str)
  - Template: Use backtest-report-template.md structure
  - Sections: Configuration, Performance Metrics, Trades, Equity Curve, Data Warnings
  - From: spec.md FR-015

- [ ] T057 [P] [US4] Implement JSON report export
  - Method: generate_json(result: BacktestResult, output_path: str)
  - Format: Structured JSON with same data as markdown
  - Purpose: Programmatic access for comparisons, dashboards
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T058 [P] [US4] Implement trade table formatting
  - Method: _format_trade_table(trades: List[Trade]) -> str
  - Columns: Symbol, Entry Date, Entry Price, Exit Date, Exit Price, Shares, P&L, P&L %, Duration, Exit Reason
  - Format: Markdown table with aligned columns
  - Pattern: Table formatting utilities

### Integration

- [ ] T059 [US4] Write integration test: Full report workflow
  - File: tests/backtest/test_integration_reports.py
  - Test: test_full_report_workflow() - Backtest â†’ report generation
  - Run: Complete backtest, generate both markdown and JSON
  - Verify: Files created, content matches expected format
  - Pattern: End-to-end file generation test

---

## Phase 7: Integration and Acceptance

**Goal**: Validate complete feature meets all NFRs and quality gates

- [ ] T070 [P] Write acceptance test: Performance benchmark (NFR-001)
  - File: tests/backtest/test_acceptance.py
  - Test: test_performance_benchmark() - 1 year backtest in <30 seconds
  - Run: Backtest 252 trading days for single stock
  - Assert: execution_time < 30.0 seconds
  - From: spec.md NFR-001

- [ ] T071 [P] Write acceptance test: Accuracy validation (NFR-003)
  - File: tests/backtest/test_acceptance.py
  - Test: test_buy_and_hold_accuracy() - Results match manual calculation
  - Strategy: Buy-and-hold AAPL 2023
  - Expected: Total return within 0.01% of manual calculation
  - From: spec.md NFR-003

- [ ] T072 [P] Write acceptance test: Reproducibility (NFR-010)
  - File: tests/backtest/test_acceptance.py
  - Test: test_reproducibility() - Same inputs â†’ same outputs
  - Run: Same BacktestConfig twice
  - Assert: result1.metrics == result2.metrics, result1.trades == result2.trades
  - From: spec.md NFR-010

- [ ] T073 [P] Write acceptance test: Data fetch performance (NFR-002)
  - File: tests/backtest/test_acceptance.py
  - Test: test_data_fetch_performance() - 10 stocks in <60 seconds
  - Fetch: Historical data for 10 stocks, 1 year each
  - Assert: Total time < 60 seconds
  - From: spec.md NFR-002

- [ ] T074 Create usage examples in examples/
  - Files: examples/simple_backtest.py, examples/strategy_comparison.py, examples/custom_strategy_example.py
  - Purpose: Documentation and developer onboarding
  - Content: Complete end-to-end examples with comments
  - Pattern: Existing examples/ directory
  - From: plan.md [IMPLEMENTATION ROADMAP] Phase 6

- [ ] T075 Update project README with backtest module
  - File: README.md
  - Section: Add "Backtesting Engine" section
  - Content: Quick start, example usage, link to docs
  - Pattern: Existing module documentation sections

---

## Phase 8: Polish & Cross-Cutting Concerns

### Error Handling & Resilience

- [ ] T080 Add comprehensive error handling to BacktestEngine
  - Errors: DataQualityError, StrategyError, InsufficientDataError
  - Logging: Log all errors with context (symbol, date, error type)
  - REUSE: ErrorTracker patterns (src/trading_bot/error_handling/)
  - From: spec.md NFR-006

- [ ] T081 [P] Add retry logic for API calls in HistoricalDataManager
  - Decorator: @with_retry(max_attempts=3, backoff_factor=2)
  - Apply to: _fetch_alpaca_data(), _fetch_yahoo_data()
  - REUSE: @with_retry decorator (src/trading_bot/error_handling/retry.py)
  - From: plan.md [SECURITY]

- [ ] T082 [P] Add data quality validation and warnings
  - Validation: Check gaps, negative prices, zero volume, missing adjustments
  - Warnings: Collect in BacktestResult.data_warnings list
  - Logging: Log all data quality issues
  - From: spec.md FR-002, FR-016, FR-018

### Quality Gates (Constitution Compliance)

- [ ] T085 Run test coverage validation
  - Command: pytest --cov=src/trading_bot/backtest --cov-fail-under=90
  - Requirement: â‰¥90% coverage (constitution Â§Pre_Deploy)
  - Fix: Add tests for uncovered code paths
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] T086 [P] Run type checking with mypy
  - Command: mypy src/trading_bot/backtest/ --strict
  - Requirement: No type errors (constitution Â§Code_Quality)
  - Fix: Add type hints to all functions and methods
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] T087 [P] Run linting with ruff
  - Command: ruff check src/trading_bot/backtest/
  - Requirement: No violations
  - Fix: Address all linting issues
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] T088 [P] Run security check with bandit
  - Command: bandit -r src/trading_bot/backtest/
  - Requirement: No high-severity issues
  - Check: API keys in env vars, no hardcoded secrets
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

### Documentation

- [ ] T090 Document IStrategy protocol implementation
  - File: src/trading_bot/backtest/strategy_protocol.py
  - Docstrings: Comprehensive docstrings with examples
  - Type hints: Full type annotations
  - Pattern: Existing protocol documentation

- [ ] T091 [P] Create backtest module __init__.py with public API
  - File: src/trading_bot/backtest/__init__.py
  - Exports: BacktestEngine, BacktestConfig, BacktestResult, IStrategy, HistoricalDataManager
  - Docstring: Module-level documentation
  - From: plan.md [STRUCTURE]

- [ ] T092 [P] Update quickstart.md with validation results
  - File: specs/001-backtesting-engine/quickstart.md
  - Sections: Test results, performance benchmarks, example outputs
  - Pattern: Existing quickstart.md structure
