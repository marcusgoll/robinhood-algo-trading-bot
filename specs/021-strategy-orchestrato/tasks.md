# Tasks: Strategy Orchestrator

## [CODEBASE REUSE ANALYSIS]
Scanned: src/trading_bot/backtest/**/*.py, tests/backtest/**/*.py

[EXISTING - REUSE]
- ✅ BacktestEngine (src/trading_bot/backtest/engine.py)
- ✅ IStrategy protocol (src/trading_bot/backtest/strategy_protocol.py)
- ✅ PerformanceCalculator (src/trading_bot/backtest/performance_calculator.py)
- ✅ ReportGenerator (src/trading_bot/backtest/report_generator.py)
- ✅ BaseModel patterns (src/trading_bot/backtest/models.py)
- ✅ HistoricalDataManager (src/trading_bot/backtest/historical_data_manager.py)
- ✅ Test fixtures (tests/backtest/conftest.py)
- ✅ Mock data generation (tests/backtest/test_engine.py)
- ✅ Validation helpers (src/trading_bot/backtest/utils.py)

[NEW - CREATE]
- 🆕 StrategyOrchestrator (no existing multi-strategy coordination pattern)
- 🆕 StrategyAllocation dataclass (new capital tracking concept)
- 🆕 OrchestratorConfig dataclass (new configuration model)
- 🆕 OrchestratorResult dataclass (extends BacktestResult pattern)
- 🆕 test_orchestrator.py (unit tests for new orchestrator)
- 🆕 test_orchestrator_integration.py (integration tests for US1-US3)

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 1: Setup (no blockers)
2. Phase 2: Core Data Models (blocks all implementation)
3. Phase 3: US1 [P1] - Multi-strategy execution (foundation for US2, US3)
4. Phase 4: US2 [P2] - Independent tracking (depends on US1 execution)
5. Phase 5: US3 [P1] - Capital limits (depends on US1 execution)
6. Phase 6: Integration & Testing (depends on US1, US2, US3)
7. Phase 7: Documentation (depends on working implementation)

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 2: T005, T006, T007 (independent dataclasses)
- Phase 3: T010, T011 (tests can run parallel with implementation setup)
- Phase 4: T020, T021 (metric calculation tests independent)
- Phase 5: T025, T026 (capital limit tests independent)
- Phase 6: T030, T031, T032, T033 (integration tests for different user stories)
- Phase 7: T040, T041, T042 (documentation tasks independent)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phase 3 (US1), Phase 4 (US2), Phase 5 (US3) - all P1 stories
**Incremental delivery**: Models → Orchestrator skeleton → Execution → Tracking → Limits → Integration
**Testing approach**: TDD required - write tests before implementation, 90% coverage target

---

## Phase 1: Setup

- [ ] T001 Create error tracking log for orchestrator implementation
  - File: specs/021-strategy-orchestrato/error-log.md
  - Template: Standard error-log template (timestamp, error, resolution)
  - Pattern: specs/001-backtesting-engine/error-log.md

- [ ] T002 [P] Create test configuration fixtures for orchestrator
  - File: tests/backtest/conftest.py (extend existing)
  - Fixtures: sample_strategies (list of 3 test strategies), sample_weights (valid allocations)
  - REUSE: Existing conftest.py fixture patterns
  - Pattern: tests/backtest/conftest.py @pytest.fixture decorators

---

## Phase 2: Core Data Models (blocking prerequisites)

**Goal**: Define all dataclasses required for orchestrator implementation

- [ ] T005 [P] Create StrategyAllocation dataclass in src/trading_bot/backtest/models.py
  - Fields: strategy_id (str), allocated_capital (Decimal), used_capital (Decimal), available_capital (Decimal)
  - Methods: allocate(amount), release(amount), can_allocate(amount) -> bool
  - Validation: allocated_capital > 0, used_capital >= 0, available_capital = allocated - used
  - REUSE: BaseModel validation patterns from models.py
  - Pattern: src/trading_bot/backtest/models.py BacktestConfig dataclass
  - From: plan.md [DATA MODEL] StrategyAllocation entity

- [x] T006 [P] Create OrchestratorConfig dataclass in src/trading_bot/backtest/models.py
  - Fields: logging_level (str, default="INFO"), validate_weights (bool, default=True)
  - Validation: logging_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
  - REUSE: BaseModel patterns from models.py
  - Pattern: src/trading_bot/backtest/models.py BacktestConfig dataclass
  - From: plan.md [DATA MODEL] OrchestratorConfig entity

- [ ] T007 [P] Create OrchestratorResult dataclass in src/trading_bot/backtest/models.py
  - Fields: aggregate_metrics (PerformanceMetrics), strategy_results (dict[str, BacktestResult]), comparison_table (dict[str, dict])
  - Methods: to_dict(), get_strategy_result(strategy_id) -> BacktestResult
  - REUSE: BacktestResult pattern from models.py
  - Pattern: src/trading_bot/backtest/models.py BacktestResult dataclass
  - From: plan.md [DATA MODEL] OrchestratorResult entity

- [ ] T008 [P] Write unit tests for StrategyAllocation in tests/backtest/test_models.py
  - Tests: allocate() increases used_capital, release() decreases used_capital, can_allocate() respects limits
  - Given-When-Then structure
  - Pattern: tests/backtest/test_models.py existing model tests
  - Coverage: 100% (new code)

- [ ] T009 [P] Write unit tests for OrchestratorConfig and OrchestratorResult in tests/backtest/test_models.py
  - Tests: OrchestratorConfig validates logging_level, OrchestratorResult aggregates correctly
  - Given-When-Then structure
  - Pattern: tests/backtest/test_models.py existing model tests
  - Coverage: 100% (new code)

---

## Phase 3: User Story 1 [P1] - Multi-strategy execution with fixed allocation

**Story Goal**: Trader can run multiple strategies in single backtest with fixed capital allocation

**Independent Test Criteria**:
- [ ] Orchestrator accepts list of (strategy, weight) tuples at initialization
- [ ] Weights sum to ≤100%, validation error if >100%
- [ ] Each strategy receives allocated portion of capital
- [ ] Backtest executes chronologically with all strategies evaluating each bar
- [ ] Final equity = sum of strategy equity curves

### Tests (TDD - write first)

- [ ] T010 [P] [US1] Write test: Orchestrator initialization validates weight sum ≤1.0
  - File: tests/backtest/test_orchestrator.py (new file)
  - Test: test_init_valid_weights_passes, test_init_invalid_weights_raises_value_error
  - Given: List of (strategy, weight) tuples
  - When: StrategyOrchestrator.__init__() called
  - Then: Accepts if sum ≤1.0, raises ValueError if sum >1.0
  - Pattern: tests/backtest/test_engine.py initialization tests
  - From: spec.md FR-002

- [ ] T011 [P] [US1] Write test: Orchestrator allocates capital proportionally
  - File: tests/backtest/test_orchestrator.py
  - Test: test_capital_allocation_proportional
  - Given: 3 strategies with weights [0.5, 0.3, 0.2], initial_capital=100000
  - When: Orchestrator initialized
  - Then: Strategy allocations = [50000, 30000, 20000]
  - Pattern: tests/backtest/test_engine.py state verification tests
  - From: spec.md FR-003

- [ ] T012 [P] [US1] Write test: Orchestrator executes all strategies chronologically
  - File: tests/backtest/test_orchestrator.py
  - Test: test_chronological_execution_all_strategies
  - Given: 2 strategies, historical data with 10 bars
  - When: orchestrator.run() called
  - Then: Each strategy's on_bar() called 10 times in date order
  - Pattern: tests/backtest/test_engine.py execution order tests
  - From: spec.md FR-004, FR-015

### Implementation

- [ ] T015 [US1] Create StrategyOrchestrator class skeleton in src/trading_bot/backtest/orchestrator.py
  - Methods: __init__(strategies, config), run(historical_data, initial_capital)
  - Attributes: _strategies (dict[str, IStrategy]), _allocations (dict[str, StrategyAllocation])
  - REUSE: BacktestEngine structure pattern (engine.py)
  - Pattern: src/trading_bot/backtest/engine.py BacktestEngine class
  - From: plan.md [STRUCTURE] orchestrator.py module

- [ ] T016 [US1] Implement __init__ with weight validation in orchestrator.py
  - Validation: Sum of weights ≤1.0 (FR-002)
  - Create StrategyAllocation for each strategy (FR-003)
  - Setup structured logging (JSON formatter)
  - REUSE: Validation helpers from utils.py
  - Pattern: src/trading_bot/backtest/engine.py __init__ validation
  - From: plan.md Phase 2 - Orchestrator Skeleton

- [ ] T017 [US1] Implement run() method with chronological bar iteration
  - Logic: For each bar in historical_data, call _execute_bar(bar)
  - Track per-strategy state (positions, trades, equity)
  - Aggregate results into OrchestratorResult
  - REUSE: BacktestEngine.run() chronological iteration pattern
  - Pattern: src/trading_bot/backtest/engine.py run() method
  - From: plan.md Phase 3 - Execution Loop

- [ ] T018 [US1] Implement _execute_bar() to process bar across all strategies
  - Logic: For each strategy, call strategy.on_bar(bar, state)
  - Collect signals from each strategy
  - Tag trades with strategy_id (FR-006)
  - Enforce chronological order (FR-015 - no look-ahead)
  - REUSE: BacktestEngine bar processing logic
  - Pattern: src/trading_bot/backtest/engine.py bar iteration
  - From: plan.md Phase 3 - Execution Loop

---

## Phase 4: User Story 2 [P2] - Independent performance tracking

**Story Goal**: Each strategy's performance tracked independently for comparison

**Independent Test Criteria**:
- [ ] Each strategy has separate equity curve tracking
- [ ] Each trade tagged with originating strategy_id
- [ ] Performance metrics calculated per-strategy (Sharpe, max drawdown, total return)
- [ ] Comparison table generated (strategy_id, total_return, sharpe_ratio, win_rate)

### Tests (TDD - write first)

- [ ] T020 [P] [US2] Write test: Each strategy has independent equity curve
  - File: tests/backtest/test_orchestrator.py
  - Test: test_per_strategy_equity_curves_independent
  - Given: 2 strategies with different performance
  - When: orchestrator.run() completes
  - Then: result.strategy_results[strategy_id].equity_curve distinct for each
  - Pattern: tests/backtest/test_engine.py equity tracking tests
  - From: spec.md FR-005

- [ ] T021 [P] [US2] Write test: Trades tagged with strategy_id
  - File: tests/backtest/test_orchestrator.py
  - Test: test_trades_tagged_with_strategy_id
  - Given: 2 strategies generating trades
  - When: orchestrator.run() completes
  - Then: Each trade.metadata["strategy_id"] matches originating strategy
  - Pattern: tests/backtest/test_engine.py trade tracking tests
  - From: spec.md FR-006

- [ ] T022 [P] [US2] Write test: Performance metrics calculated per-strategy
  - File: tests/backtest/test_orchestrator.py
  - Test: test_per_strategy_performance_metrics
  - Given: 2 strategies with known performance characteristics
  - When: orchestrator.run() completes
  - Then: Each strategy_result contains PerformanceMetrics (Sharpe, drawdown, return)
  - Pattern: tests/backtest/test_performance_calculator.py metric tests
  - From: spec.md FR-009

- [ ] T023 [P] [US2] Write test: Comparison table generated correctly
  - File: tests/backtest/test_orchestrator.py
  - Test: test_comparison_table_format
  - Given: 3 strategies with different performance
  - When: orchestrator.run() completes
  - Then: result.comparison_table contains rows for each strategy with metrics
  - Pattern: tests/backtest/test_report_generator.py table format tests
  - From: spec.md FR-013

### Implementation

- [ ] T025 [US2] Implement per-strategy equity curve tracking in orchestrator.py
  - Logic: Maintain dict[strategy_id, List[Decimal]] for equity curves
  - Update equity after each bar based on strategy positions
  - Store in OrchestratorResult.strategy_results
  - REUSE: PerformanceCalculator equity tracking patterns
  - Pattern: src/trading_bot/backtest/performance_calculator.py equity curve logic
  - From: plan.md Phase 4 - Performance Tracking

- [ ] T026 [US2] Implement per-strategy metrics calculation in orchestrator.py
  - Logic: For each strategy, call PerformanceCalculator.calculate_metrics()
  - Store in OrchestratorResult.strategy_results[strategy_id].metrics
  - Calculate aggregate portfolio metrics
  - REUSE: PerformanceCalculator.calculate_metrics()
  - Pattern: src/trading_bot/backtest/performance_calculator.py
  - From: plan.md Phase 4 - Performance Tracking

- [ ] T027 [US2] Implement _aggregate_results() to create OrchestratorResult
  - Logic: Combine per-strategy BacktestResults into OrchestratorResult
  - Calculate aggregate equity curve (sum of strategy curves)
  - Generate comparison_table (dict with strategy_id → metrics mapping)
  - REUSE: ReportGenerator table formatting patterns
  - Pattern: src/trading_bot/backtest/report_generator.py
  - From: plan.md Phase 4 - Performance Tracking

---

## Phase 5: User Story 3 [P1] - Capital allocation limits

**Story Goal**: Orchestrator prevents strategies from exceeding capital allocation

**Independent Test Criteria**:
- [ ] Orchestrator tracks capital used per strategy in real-time
- [ ] Entry signals rejected if strategy at max allocation
- [ ] Logged warning when strategy blocked by capital limit
- [ ] Capital released when positions close

### Tests (TDD - write first)

- [ ] T030 [P] [US3] Write test: Strategy blocked when at max allocation
  - File: tests/backtest/test_orchestrator.py
  - Test: test_capital_limit_blocks_new_positions
  - Given: Strategy with 30% allocation, generates signal requiring 35%
  - When: orchestrator._execute_bar() processes signal
  - Then: Signal rejected, no trade executed, log contains capital_limit_hit event
  - Pattern: tests/backtest/test_engine.py position limit tests
  - From: spec.md FR-007

- [ ] T031 [P] [US3] Write test: Capital released when positions close
  - File: tests/backtest/test_orchestrator.py
  - Test: test_capital_released_on_position_close
  - Given: Strategy at max allocation closes position
  - When: Position closed
  - Then: StrategyAllocation.available_capital increases by position value
  - Pattern: tests/backtest/test_engine.py position close tests
  - From: spec.md FR-008

- [ ] T032 [P] [US3] Write test: Real-time capital tracking accuracy
  - File: tests/backtest/test_orchestrator.py
  - Test: test_capital_tracking_real_time
  - Given: Strategy opens 3 positions sequentially
  - When: Each position opened
  - Then: StrategyAllocation.used_capital matches sum of open position values
  - Pattern: tests/backtest/test_engine.py state tracking tests
  - From: spec.md FR-007

### Implementation

- [ ] T035 [US3] Implement _allocate_capital() method in orchestrator.py
  - Logic: Check StrategyAllocation.can_allocate(amount)
  - If blocked, log capital_limit_hit event, return False
  - If allowed, update StrategyAllocation.used_capital, return True
  - REUSE: Validation helpers from utils.py
  - Pattern: src/trading_bot/backtest/engine.py position validation
  - From: plan.md Phase 3 - Execution Loop

- [ ] T036 [US3] Implement _release_capital() method in orchestrator.py
  - Logic: When position closes, call StrategyAllocation.release(position_value)
  - Update available_capital
  - Log capital release event
  - REUSE: Position tracking from BacktestEngine
  - Pattern: src/trading_bot/backtest/engine.py position close logic
  - From: plan.md Phase 3 - Execution Loop

- [ ] T037 [US3] Integrate capital limits into _execute_bar() signal processing
  - Logic: Before executing strategy signal, check _allocate_capital()
  - Only execute trade if capital available
  - Log blocked signals with strategy_id and allocation state
  - REUSE: BacktestEngine signal validation patterns
  - Pattern: src/trading_bot/backtest/engine.py signal processing
  - From: plan.md Phase 3 - Execution Loop

---

## Phase 6: Integration & Cross-Cutting

**Goal**: Full end-to-end testing and logging infrastructure

- [ ] T040 [P] Write integration test for US1: Multi-strategy fixed allocation
  - File: tests/backtest/test_orchestrator_integration.py (new file)
  - Test: test_us1_multi_strategy_fixed_allocation_e2e
  - Given: 2 strategies (BuyAndHold, Momentum) with 50/50 allocation, 2 years historical data
  - When: Orchestrator runs full backtest
  - Then: Both execute trades, final equity = strategy1_equity + strategy2_equity (within rounding)
  - Real data: Use actual HistoricalDataManager
  - Pattern: tests/backtest/test_integration_engine.py full workflow tests
  - From: spec.md US1 acceptance criteria

- [ ] T041 [P] Write integration test for US2: Independent tracking
  - File: tests/backtest/test_orchestrator_integration.py
  - Test: test_us2_independent_tracking_comparison_e2e
  - Given: 2 strategies with known different performance
  - When: Orchestrator runs backtest
  - Then: Individual metrics match single-strategy baseline backtests, comparison table accurate
  - Real data: Use actual HistoricalDataManager
  - Pattern: tests/backtest/test_integration_metrics.py metric validation tests
  - From: spec.md US2 acceptance criteria

- [ ] T042 [P] Write integration test for US3: Capital limits
  - File: tests/backtest/test_orchestrator_integration.py
  - Test: test_us3_capital_limits_enforcement_e2e
  - Given: Strategy with 30% allocation, generates signals requiring >30%
  - When: Orchestrator processes signals
  - Then: Strategy cannot exceed 30%, blocked signals logged, capital released on close
  - Real data: Use actual HistoricalDataManager
  - Pattern: tests/backtest/test_integration_engine.py limit enforcement tests
  - From: spec.md US3 acceptance criteria

- [ ] T043 [P] Implement structured logging with JSON formatter in orchestrator.py
  - Events: orchestrator.backtest_started, orchestrator.strategy_signal, orchestrator.capital_limit_hit, orchestrator.backtest_completed
  - Format: JSON with timestamp, event, strategy_id, details
  - Log file: logs/backtest/orchestrator.jsonl
  - REUSE: Python logging module
  - Pattern: Standard JSON logging pattern
  - From: plan.md Phase 5 - Logging & Auditability, spec.md FR-012

- [ ] T044 Write performance benchmark test: Overhead <2x single-strategy
  - File: tests/backtest/test_orchestrator_integration.py
  - Test: test_performance_overhead_under_2x
  - Given: Single strategy backtest as baseline
  - When: Same backtest run with 5 strategies via orchestrator
  - Then: orchestrator_runtime / single_runtime < 2.0
  - Pattern: Performance timing pattern with time.perf_counter()
  - From: spec.md NFR-001, plan.md [PERFORMANCE TARGETS]

- [ ] T045 Write memory profiling test: O(n) growth with strategy count
  - File: tests/backtest/test_orchestrator_integration.py
  - Test: test_memory_growth_linear
  - Given: Orchestrator with 1, 5, 10 strategies
  - When: Memory usage measured for each
  - Then: Growth is linear (not quadratic)
  - Pattern: Memory profiling with tracemalloc
  - From: spec.md NFR-002, plan.md [PERFORMANCE TARGETS]

---

## Phase 7: Documentation & Export

**Goal**: Public API and usage documentation

- [ ] T050 [P] Update src/trading_bot/backtest/__init__.py to export orchestrator classes
  - Exports: StrategyOrchestrator, StrategyAllocation, OrchestratorConfig, OrchestratorResult
  - Follow existing export pattern
  - Pattern: src/trading_bot/backtest/__init__.py current exports
  - From: plan.md Phase 7 - Documentation & Examples

- [ ] T051 [P] Create quickstart usage example in specs/021-strategy-orchestrato/quickstart.md
  - Example 1: Basic 2-strategy portfolio (BuyAndHold + Momentum)
  - Example 2: Capital limit demonstration
  - Example 3: Reading comparison table
  - Code: Copy-paste runnable Python code
  - Pattern: specs/001-backtesting-engine/quickstart.md
  - From: plan.md [INTEGRATION SCENARIOS]

- [ ] T052 Update README.md with orchestrator section
  - Section: "Multi-Strategy Backtesting with StrategyOrchestrator"
  - Content: Brief overview, link to quickstart.md, key features
  - Placement: After "Backtesting Engine" section
  - Pattern: README.md existing backtest section
  - From: plan.md Phase 7 - Documentation & Examples

---

## [TEST GUARDRAILS]

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each
- Full test suite: <6 min total

**Coverage Requirements:**
- New code: 100% coverage (orchestrator.py, new dataclasses)
- Unit tests: ≥90% line coverage (constitution requirement)
- Integration tests: ≥90% critical path coverage

**Measurement:**
```bash
# Coverage report
pytest --cov=trading_bot.backtest.orchestrator --cov-report=term-missing --cov-fail-under=90

# Performance benchmark
pytest tests/backtest/test_orchestrator_integration.py::test_performance_overhead_under_2x -v
```

**Quality Gates:**
- All tests must pass before merge
- mypy --strict passes with no errors
- ruff linting passes with no warnings
- No regressions (all existing tests still pass)

**Clarity Requirements:**
- One behavior per test
- Descriptive names: `test_capital_limit_blocks_new_positions_when_at_max_allocation()`
- Given-When-Then structure in test body
- Arrange-Act-Assert pattern

**Anti-Patterns:**
- ❌ NO integration tests that take >30s (use smaller datasets)
- ❌ NO mocking BacktestEngine in integration tests (test real coordination)
- ✅ USE real HistoricalDataManager with small datasets (10-20 bars)
- ✅ USE Given-When-Then for clarity

---

## Task Summary

**Total Tasks**: 27
- Phase 1 (Setup): 2 tasks
- Phase 2 (Core Data Models): 5 tasks
- Phase 3 (US1 - Multi-strategy execution): 7 tasks
- Phase 4 (US2 - Independent tracking): 5 tasks
- Phase 5 (US3 - Capital limits): 5 tasks
- Phase 6 (Integration & Logging): 6 tasks
- Phase 7 (Documentation): 3 tasks

**Parallel Opportunities**: 15 tasks marked [P]
**User Story Tasks**: 17 tasks ([US1]: 7, [US2]: 5, [US3]: 5)
**MVP Critical Path**: T001→T005-T009→T010-T018→T020-T027→T030-T037→T040-T045→T050-T052
