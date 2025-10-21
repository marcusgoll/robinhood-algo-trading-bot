# Implementation Plan: Strategy Orchestrator

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11+, dataclasses, composition pattern over inheritance
- Components to reuse: 9 (BacktestEngine, IStrategy, PerformanceCalculator, ReportGenerator, models, test patterns)
- New components needed: 6 (StrategyOrchestrator, 3 new dataclasses, 2 test modules)

**Key Architectural Choices**:
1. **Composition over inheritance**: Orchestrator wraps BacktestEngine logic, doesn't subclass
2. **Protocol preservation**: IStrategy unchanged, strategies unaware of orchestration
3. **Result aggregation**: OrchestratorResult extends BacktestResult pattern with per-strategy breakdown
4. **Structured logging**: JSON logs for auditability and measurement queries

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (existing project standard)
- Testing: pytest, pytest-mock, pytest-cov (existing patterns)
- Type checking: mypy with strict mode (constitution requirement)
- Linting: ruff (existing project standard)
- Data structures: dataclasses (frozen where immutable), Decimal for money
- Logging: Python logging module with JSON formatter

**Patterns**:
- **Strategy Pattern**: IStrategy protocol for pluggable strategies (existing)
- **Composition Pattern**: StrategyOrchestrator composes BacktestEngine, doesn't subclass (maintains SRP)
- **Repository Pattern**: HistoricalDataManager for data access (existing, reused)
- **Value Objects**: StrategyAllocation, OrchestratorConfig as immutable dataclasses
- **Result Aggregation**: OrchestratorResult contains dict[str, BacktestResult] for per-strategy attribution

**Design Principles**:
- **Single Responsibility**: Orchestrator handles coordination only, delegates execution to BacktestEngine
- **Open/Closed**: Existing code unchanged, new functionality added via composition
- **Liskov Substitution**: Orchestrator doesn't subclass BacktestEngine (avoids LSP violations)
- **Interface Segregation**: IStrategy protocol minimal and focused
- **Dependency Inversion**: Orchestrator depends on IStrategy abstraction, not concrete implementations

**Dependencies** (new packages required):
- None - all MVP functionality uses existing dependencies (pytest, mypy, ruff already installed)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/backtest/
├── orchestrator.py          [NEW] StrategyOrchestrator class
├── models.py                [EXTEND] Add StrategyAllocation, OrchestratorConfig, OrchestratorResult
├── engine.py                [REUSE] BacktestEngine unchanged
├── strategy_protocol.py     [REUSE] IStrategy unchanged
├── performance_calculator.py [REUSE] PerformanceCalculator unchanged
├── report_generator.py      [REUSE] ReportGenerator unchanged (or extend for comparison table)
└── __init__.py              [EXTEND] Export new orchestrator classes

tests/backtest/
├── test_orchestrator.py          [NEW] Unit tests for orchestrator (FR-001 to FR-015)
├── test_orchestrator_integration.py [NEW] Integration tests (US1, US2, US3)
├── test_engine.py                [REUSE] Existing engine tests unchanged
└── test_models.py                [EXTEND] Add tests for new dataclasses

specs/021-strategy-orchestrato/
├── spec.md                  [EXISTING] Feature specification
├── research.md              [CREATED] Research decisions and component analysis
├── data-model.md            [CREATED] Entity definitions and relationships
├── quickstart.md            [CREATED] Integration scenarios and usage examples
├── plan.md                  [THIS FILE] Implementation architecture
└── error-log.md             [TO CREATE] Error tracking during implementation
```

**Module Organization**:

**orchestrator.py**:
- `StrategyOrchestrator` class - main coordination logic
  - `__init__(strategies, config)` - validate weights, setup allocations
  - `run(historical_data, initial_capital)` - execute multi-strategy backtest
  - `_execute_bar(bar)` - process single bar across all strategies
  - `_allocate_capital(strategy_id, amount)` - track capital usage
  - `_release_capital(strategy_id, amount)` - return capital on position close
  - `_aggregate_results()` - combine strategy results into OrchestratorResult
  - `_log_event(event_name, **kwargs)` - structured logging

**models.py extensions**:
- `StrategyAllocation` dataclass - capital tracking per strategy
- `OrchestratorConfig` dataclass - orchestrator configuration
- `OrchestratorResult` dataclass - multi-strategy results container

**report_generator.py extensions** (optional for MVP):
- `generate_comparison_markdown()` - format comparison table (can be added in P2)

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 4 (StrategyOrchestrator, StrategyAllocation, OrchestratorConfig, OrchestratorResult)
- Relationships: Orchestrator → Allocations (1:N), Orchestrator → Results (1:N)
- Migrations required: No (in-memory Python dataclasses, no database)

**Key Entities**:
1. **StrategyOrchestrator**: Coordinates multiple strategies, tracks allocations
2. **StrategyAllocation**: Tracks allocated/used/available capital per strategy
3. **OrchestratorConfig**: Configuration for orchestrator behavior (minimal for MVP)
4. **OrchestratorResult**: Aggregates per-strategy BacktestResults + portfolio metrics

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs** (or defaults from design/systems/budgets.md):
- NFR-001: Backtest execution <2× single-strategy baseline (overhead <100% for 5 strategies)
- NFR-002: Memory usage O(n) with strategy count, not O(n²)
- NFR-003: Fail-fast validation at initialization (invalid weights raise ValueError immediately)

**Benchmarks to Implement**:
```python
# Test: test_orchestrator_performance.py
def test_performance_overhead_under_2x():
    # Baseline: single strategy
    single_runtime = time_backtest(MomentumStrategy(), data)

    # Multi-strategy: 5 strategies
    multi_runtime = time_backtest_orchestrator([Strategy1(), ..., Strategy5()], data)

    assert multi_runtime / single_runtime < 2.0  # <2x slowdown
```

**Memory Profiling**:
```bash
# Use memory_profiler to validate O(n) growth
@profile
def test_memory_growth():
    # 1 strategy
    mem_1 = measure_memory(orchestrator_with_n_strategies(1))
    # 5 strategies
    mem_5 = measure_memory(orchestrator_with_n_strategies(5))
    # 10 strategies
    mem_10 = measure_memory(orchestrator_with_n_strategies(10))

    # Validate linear growth (not quadratic)
    assert (mem_10 - mem_1) / 9 ≈ (mem_5 - mem_1) / 4  # Linear slope
```

---

## [SECURITY]

**Authentication Strategy**:
- N/A: Local library, no network access, no authentication required

**Authorization Model**:
- N/A: Single-user local execution, no multi-tenancy

**Input Validation**:
- **Strategy weights**: Sum ≤ 1.0, each weight > 0 (FR-002)
- **Initial capital**: Positive Decimal (>0)
- **Historical data**: Non-empty dict/list, valid HistoricalDataBar objects
- **Config**: Valid OrchestratorConfig (logging_level in allowed values)

**Data Protection**:
- **PII handling**: No PII collected (only market data and strategy names)
- **Encryption**: Not required (local-only, no network transmission)
- **Logging**: Scrub sensitive data (no API keys in logs, only strategy IDs and performance metrics)

**Constitution Alignment**:
- §Safety_First: Fail-fast validation prevents silent failures
- §Code_Quality: Type hints required, 90% test coverage enforced
- §Risk_Management: Capital limits enforced (FR-007), all decisions logged (FR-012)
- §Data_Integrity: Validate all inputs, handle missing data gracefully

---

## [EXISTING INFRASTRUCTURE - REUSE] (9 components)

**Services/Modules**:
- `src/trading_bot/backtest/engine.py`: BacktestEngine.run() - chronological bar iteration, position management, trade execution
- `src/trading_bot/backtest/historical_data_manager.py`: HistoricalDataManager - data loading, caching, validation
- `src/trading_bot/backtest/performance_calculator.py`: PerformanceCalculator - metrics computation (Sharpe, drawdown, returns)

**Data Models**:
- `src/trading_bot/backtest/models.py`: BacktestConfig, BacktestResult, Trade, Position, PerformanceMetrics, BacktestState
- `src/trading_bot/backtest/strategy_protocol.py`: IStrategy protocol - strategy interface contract

**Utilities**:
- `src/trading_bot/backtest/utils.py`: Date validation, Decimal formatting, validation helpers
- `src/trading_bot/backtest/report_generator.py`: ReportGenerator - markdown/JSON report formatting

**Testing Infrastructure**:
- `tests/backtest/test_engine.py`: Test patterns - pytest fixtures, mock data generation (sample_bars fixture)
- `tests/backtest/conftest.py`: Shared fixtures - sample strategies, historical data builders

**Reuse Strategy**:
1. **BacktestEngine**: Orchestrator delegates bar iteration to engine (composition)
2. **IStrategy**: Strategies unchanged, orchestrator coordinates multiple instances
3. **PerformanceCalculator**: Reuse for per-strategy metrics calculation
4. **Test fixtures**: Reuse sample_bars, sample_strategies for orchestrator tests

---

## [NEW INFRASTRUCTURE - CREATE] (6 components)

**Backend**:
- `src/trading_bot/backtest/orchestrator.py`: StrategyOrchestrator class (300-400 LOC)
  - Multi-strategy coordination
  - Capital allocation tracking
  - Signal aggregation (conflict detection for P2)
  - Event logging (structured JSON)

- `src/trading_bot/backtest/models.py` extensions:
  - `StrategyAllocation` dataclass (~30 LOC)
  - `OrchestratorConfig` dataclass (~20 LOC)
  - `OrchestratorResult` dataclass (~50 LOC)

**Testing**:
- `tests/backtest/test_orchestrator.py`: Unit tests (500-600 LOC)
  - Test FR-001 to FR-015 (one test per requirement)
  - Test edge cases (empty strategies, invalid weights, capital exhaustion)
  - Test logging (verify JSON event structure)

- `tests/backtest/test_orchestrator_integration.py`: Integration tests (300-400 LOC)
  - Test US1 (fixed allocation, combined performance)
  - Test US2 (independent tracking, comparison table)
  - Test US3 (capital limits, blocked trades)
  - Full workflow tests (multiple symbols, strategies, time periods)

**Documentation**:
- Update `src/trading_bot/backtest/__init__.py` to export StrategyOrchestrator
- Update `README.md` with orchestrator usage example (quickstart reference)

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local-only library, no deployment infrastructure
- Env vars: None required
- Breaking changes: No (existing BacktestEngine API unchanged)
- Migration: No (new feature, backward compatible)

**Build Commands**:
- No changes - existing `pytest` command covers new tests
- Type checking: `mypy src/trading_bot/backtest/orchestrator.py` (add to CI if not already)
- Coverage: `pytest --cov=trading_bot.backtest.orchestrator --cov-fail-under=90`

**Environment Variables**:
- None required for MVP

**Database Migrations**:
- No migrations - in-memory dataclasses only

**Smoke Tests**:
- N/A: Local library, no deployment endpoints
- Validation: Integration tests in test_orchestrator_integration.py serve as smoke tests

**Platform Coupling**:
- None - pure Python library, platform-agnostic

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- No breaking changes to existing BacktestEngine API
- All existing tests pass (no regressions)
- New tests achieve ≥90% coverage (constitution requirement)
- Type checking passes with no errors (`mypy --strict`)

**Local Validation Checklist**:
```gherkin
Given I have the orchestrator implemented
When I run `pytest tests/backtest/test_orchestrator.py -v`
Then all FR-001 to FR-015 tests pass
  And test coverage ≥90%
  And no mypy type errors
  And no ruff linting errors

Given I run integration tests
When I execute `pytest tests/backtest/test_orchestrator_integration.py -v`
Then US1 (fixed allocation) test passes
  And US2 (independent tracking) test passes
  And US3 (capital limits) test passes
  And performance overhead <2x baseline
```

**Rollback Plan**:
- Rollback method: `git revert <commit>` (library code, no infrastructure)
- Risk: Low (new feature, existing code unchanged)
- Special considerations: None - backward compatible addition

**Artifact Strategy**:
- No build artifacts (source code only)
- Distribution: Git repository (local development)
- Versioning: Git commits (no semantic versioning for internal library yet)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- **Scenario 1**: Initial setup & basic usage (2 strategies, 50/50 allocation)
- **Scenario 2**: Validation & testing (pytest commands, coverage checks)
- **Scenario 3**: Manual testing - capital limits (verify FR-007 blocking behavior)
- **Scenario 4**: Performance comparison report (FR-013 comparison table)
- **Scenario 5**: Debugging - event logs (structured log queries)
- **Scenario 6**: Migration from single-strategy (backward compatibility)

**Common Workflows**:
- Add new strategy to portfolio
- Optimize strategy weights
- Debug capital limit issues
- Generate comparison reports

---

## [IMPLEMENTATION PHASES]

### Phase 1: Core Data Models (1-2 hours)
- Create StrategyAllocation dataclass
- Create OrchestratorConfig dataclass
- Create OrchestratorResult dataclass
- Add validation logic to each model
- Write unit tests for model validation

**Acceptance**:
- All new dataclasses pass validation tests
- mypy type checking passes
- Test coverage ≥90% for models

### Phase 2: Orchestrator Skeleton (2-3 hours)
- Create StrategyOrchestrator class
- Implement `__init__` with weight validation (FR-002)
- Implement capital allocation setup (FR-003)
- Add structured logging setup
- Write tests for initialization and validation

**Acceptance**:
- FR-001 test passes (accepts strategy list)
- FR-002 test passes (validates weights ≤1.0)
- FR-003 test passes (allocates capital correctly)

### Phase 3: Execution Loop (3-4 hours)
- Implement `run()` method
- Implement `_execute_bar()` for chronological iteration (FR-004)
- Add signal collection per strategy (FR-006 - trade tagging)
- Implement capital tracking (FR-007 - limit enforcement)
- Implement capital release (FR-008 - on position close)
- Write execution loop tests

**Acceptance**:
- FR-004 test passes (chronological execution)
- FR-006 test passes (trade tagging)
- FR-007 test passes (capital limit blocking)
- FR-008 test passes (capital release)
- FR-015 test passes (no look-ahead bias)

### Phase 4: Performance Tracking (2-3 hours)
- Implement per-strategy equity curve tracking (FR-005)
- Implement aggregate equity curve (FR-010)
- Implement metrics calculation per strategy (FR-009)
- Generate comparison table (FR-013)
- Add conflict detection logging (FR-011)
- Write performance tracking tests

**Acceptance**:
- FR-005 test passes (separate equity curves)
- FR-009 test passes (per-strategy metrics)
- FR-010 test passes (aggregate equity curve)
- FR-013 test passes (comparison table format)

### Phase 5: Logging & Auditability (1-2 hours)
- Implement structured JSON logging (FR-012)
- Add event types: backtest_started, strategy_signal, capital_limit_hit, conflict_detected, backtest_completed
- Write logging tests (verify JSON structure)

**Acceptance**:
- FR-012 test passes (all decisions logged)
- NFR-006 test passes (sufficient detail for debugging)
- Logs queryable via grep/jq (measurement plan validation)

### Phase 6: Integration Tests (2-3 hours)
- Write US1 integration test (fixed allocation, combined performance)
- Write US2 integration test (independent tracking, comparison)
- Write US3 integration test (capital limits, blocked trades)
- Write performance benchmark test (NFR-001 - <2x overhead)
- Write memory profile test (NFR-002 - O(n) growth)

**Acceptance**:
- All US1-US3 tests pass
- Performance overhead <2x single-strategy
- Memory growth linear (not quadratic)

### Phase 7: Documentation & Examples (1 hour)
- Update `__init__.py` exports
- Create usage examples in quickstart.md
- Update README.md with orchestrator section
- Document logging events for measurement plan

**Acceptance**:
- Quickstart examples run without errors
- README accurately describes orchestrator API
- Measurement queries documented and tested

---

## [RISK ASSESSMENT]

**Technical Risks**:

1. **Risk**: Performance overhead exceeds 2x target (NFR-001 violation)
   - **Likelihood**: Low - composition approach should be efficient
   - **Mitigation**: Profile early (Phase 6), optimize hot paths if needed
   - **Contingency**: Reduce logging verbosity, cache calculations, parallelize strategies (P3)

2. **Risk**: Capital allocation tracking introduces bugs (position sizing errors)
   - **Likelihood**: Medium - complex state management
   - **Mitigation**: Extensive unit tests (Phase 3), fuzz testing with random allocations
   - **Contingency**: Add assertion checks, detailed logging for debugging

3. **Risk**: Equity curve aggregation incorrect (FR-010)
   - **Likelihood**: Low - straightforward summation
   - **Mitigation**: Integration tests with known expected values
   - **Contingency**: Add validation against sum of individual equity curves

**Project Risks**:

1. **Risk**: Scope creep (temptation to implement P2 features in MVP)
   - **Likelihood**: Medium - conflict resolution, rebalancing are interesting
   - **Mitigation**: Strict adherence to P1 scope (US1-US3 only)
   - **Contingency**: Document P2 ideas in NOTES.md, defer to future PRs

2. **Risk**: Test coverage falls below 90% (constitution violation)
   - **Likelihood**: Low - TDD approach enforces coverage
   - **Mitigation**: Run `pytest --cov` after each phase
   - **Contingency**: Add missing test cases before final commit

---

## [SUCCESS CRITERIA]

**Definition of Done** (all must be true):
- ✅ All FR-001 to FR-015 tests pass
- ✅ All US1-US3 integration tests pass
- ✅ Test coverage ≥90% for orchestrator.py
- ✅ mypy --strict passes with no errors
- ✅ ruff linting passes with no warnings
- ✅ Performance benchmark <2x overhead (NFR-001)
- ✅ Memory growth O(n) validated (NFR-002)
- ✅ Structured logs queryable (measurement plan validated)
- ✅ Quickstart examples run successfully
- ✅ No regressions (all existing tests still pass)

**User Acceptance** (validate with sample strategies):
- Run 3 strategies with different allocations → comparison table shows expected breakdown
- Hit capital limit on one strategy → log shows capital_limit_hit events
- Compare orchestrator result vs. sum of individual backtests → equity curves match within rounding

---

## [NEXT STEPS AFTER /plan]

**Immediate**:
1. `/tasks` - Generate concrete TDD task breakdown from this plan
   - Expected: 20-30 tasks with acceptance criteria
   - Each task maps to test case(s)
   - Tasks ordered by phase (models → orchestrator → integration)

**Subsequent Workflow**:
2. `/analyze` - Cross-artifact consistency check before implementation
3. `/implement` - Execute tasks with TDD (write tests first)
4. `/optimize` - Code review, performance validation, accessibility (N/A for backend)
5. `/debug` - Fix any errors discovered during implementation
6. `/preview` - Manual validation with sample strategies
7. `/phase-1-ship` - Commit to feature branch (no deployment for library)

**Manual Gates**:
- After `/implement`: Review test coverage report, ensure ≥90%
- After `/optimize`: Review performance benchmarks, ensure <2x overhead
- Before `/phase-1-ship`: Run full test suite, validate no regressions
