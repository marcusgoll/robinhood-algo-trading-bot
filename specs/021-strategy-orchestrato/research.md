# Research & Discovery: strategy-orchestrato

## Research Decisions

### Decision: Extend BacktestEngine architecture with composition pattern

- **Decision**: Build StrategyOrchestrator as a wrapper around BacktestEngine, not a subclass
- **Rationale**: Composition over inheritance allows orchestrator to manage multiple engine instances or reuse engine's bar-iteration logic without tight coupling. Maintains single-responsibility principle.
- **Alternatives**:
  - Subclass BacktestEngine (rejected - violates LSP, orchestrator "is-not-a" single strategy engine)
  - Modify BacktestEngine directly (rejected - breaks existing single-strategy API, violates OCP)
- **Source**: src/trading_bot/backtest/engine.py (existing BacktestEngine.run() pattern)

### Decision: Reuse IStrategy protocol without modification

- **Decision**: Keep existing IStrategy protocol (should_enter/should_exit methods) unchanged
- **Rationale**: FR-014 requires strategies work without modification. Orchestrator handles multi-strategy coordination at higher level, strategies remain unaware of each other.
- **Alternatives**:
  - Add strategy_id to IStrategy (rejected - breaks existing strategies)
  - Create new IMultiStrategy protocol (rejected - duplicates logic, complicates migration)
- **Source**: src/trading_bot/backtest/strategy_protocol.py (IStrategy definition)

### Decision: Extend PerformanceMetrics for per-strategy tracking

- **Decision**: Create OrchestratorResult dataclass containing dict[str, BacktestResult] for per-strategy results
- **Rationale**: Reuses existing BacktestResult/PerformanceMetrics structure (FR-009), adds aggregation layer for portfolio-level metrics. Maintains backward compatibility with single-strategy reports.
- **Alternatives**:
  - Modify BacktestResult to support multi-strategy (rejected - breaks existing code)
  - Flatten metrics into single structure (rejected - loses per-strategy attribution required by US2)
- **Source**: src/trading_bot/backtest/models.py (BacktestResult, PerformanceMetrics)

### Decision: Track capital allocation using dedicated StrategyAllocation dataclass

- **Decision**: Create StrategyAllocation with fields: strategy_id, allocated_capital, used_capital, available_capital
- **Rationale**: Explicit tracking enables FR-007 (capital limits), FR-008 (capital release), NFR-006 (auditability). Separates allocation logic from strategy execution.
- **Alternatives**:
  - Track in dict[str, Decimal] (rejected - loses semantic meaning, harder to debug)
  - Add allocation to BacktestState (rejected - pollutes single-strategy model)
- **Source**: Spec requirement FR-003, FR-007, FR-008

### Decision: Use Python's built-in logging for strategy events

- **Decision**: Log all orchestrator events using structured logging (JSON format) via Python logging module
- **Rationale**: Aligns with constitution §Audit_Everything, matches existing backtest logging patterns, enables measurement plan queries (grep/jq).
- **Alternatives**:
  - Custom event bus (rejected - over-engineering for MVP, adds complexity)
  - Store events in database (rejected - local-only requirement, unnecessary I/O)
- **Source**: Constitution §Safety_First (audit everything), measurement plan (logs/backtest/*.jsonl)

---

## Components to Reuse (9 found)

- src/trading_bot/backtest/engine.py: BacktestEngine.run() - chronological bar iteration, position tracking, trade execution
- src/trading_bot/backtest/strategy_protocol.py: IStrategy protocol - strategy interface contract
- src/trading_bot/backtest/models.py: BacktestConfig, BacktestResult, Trade, Position - core data models
- src/trading_bot/backtest/models.py: PerformanceMetrics - return, Sharpe, drawdown calculations
- src/trading_bot/backtest/performance_calculator.py: PerformanceCalculator - metrics computation logic
- src/trading_bot/backtest/report_generator.py: ReportGenerator - markdown/JSON report formatting
- src/trading_bot/backtest/historical_data_manager.py: HistoricalDataManager - data loading and caching
- src/trading_bot/backtest/utils.py: Utility functions for date handling, validation
- tests/backtest/test_engine.py: Test patterns - pytest fixtures, mock data generation, assertion patterns

---

## New Components Needed (6 required)

- src/trading_bot/backtest/orchestrator.py: StrategyOrchestrator class - main coordination logic
- src/trading_bot/backtest/models.py: StrategyAllocation dataclass - capital allocation tracking
- src/trading_bot/backtest/models.py: OrchestratorConfig dataclass - orchestrator configuration
- src/trading_bot/backtest/models.py: OrchestratorResult dataclass - multi-strategy results container
- tests/backtest/test_orchestrator.py: Unit tests for orchestrator logic (FR-001 through FR-015)
- tests/backtest/test_orchestrator_integration.py: Integration tests for full workflow (US1-US3)

---

## Unknowns & Questions

None - all technical questions resolved during specification phase (0 clarifications needed)
