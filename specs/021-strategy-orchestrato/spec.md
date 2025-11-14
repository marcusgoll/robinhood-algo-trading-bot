# Feature Specification: Strategy Orchestrator

**Branch**: `feature/021-strategy-orchestrato`
**Created**: 2025-10-20
**Status**: Draft

## User Scenarios

### Primary User Story
As a trader developing multiple trading strategies, I want to run and compare multiple strategies simultaneously within a single backtest, so that I can evaluate portfolio-level performance and identify the best strategy combinations without running separate backtests for each strategy.

### Acceptance Scenarios

1. **Given** I have 3 different trading strategies (BuyAndHold, Momentum, RSI), **When** I run a backtest with all strategies using a portfolio allocation of 33% each, **Then** the orchestrator executes all strategies in parallel, tracks individual and aggregate performance, and generates a comparison report showing each strategy's contribution to total portfolio returns.

2. **Given** I am running 2 strategies with different entry signals, **When** both strategies generate buy signals on the same bar but only 40% capital remains, **Then** the orchestrator allocates capital according to strategy weights, respects position limits, and logs allocation decisions for auditability.

3. **Given** I have configured 4 strategies with capital limits, **When** one strategy hits its maximum allocation (e.g., 30% of portfolio), **Then** the orchestrator prevents that strategy from opening new positions until existing positions close, while other strategies continue operating within their limits.

### Edge Cases

- What happens when multiple strategies want to trade the same symbol simultaneously?
  - Orchestrator aggregates signals using configurable logic (first-come, weighted-average, priority-based)

- How does system handle strategy conflicts (one wants to buy, another wants to sell same symbol)?
  - Orchestrator applies conflict resolution policy (net signal, cancel both, priority wins)

- What happens when total strategy allocations exceed 100%?
  - Orchestrator normalizes weights proportionally or rejects configuration at init

- How does system track P&L attribution across strategies?
  - Each trade tagged with strategy_id, individual equity curves maintained per strategy

## User Stories (Prioritized)

> **Priority 1 (MVP)** focuses on basic multi-strategy execution with simple allocation.
> **Priority 2** adds advanced features like conflict resolution and rebalancing.
> **Priority 3** covers optimization and advanced analytics.

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As a trader, I want to run multiple strategies in a single backtest with fixed capital allocation percentages so that I can evaluate combined portfolio performance
  - **Acceptance**:
    - Orchestrator accepts list of (strategy, weight) tuples at initialization
    - Weights sum to ≤100% (validation error if >100%)
    - Each strategy receives allocated portion of capital
    - Backtest executes chronologically with all strategies evaluating each bar
  - **Independent test**: Run 2 strategies (50/50 split) on same historical data, verify both execute trades and final equity = strategy1_equity + strategy2_equity
  - **Effort**: L (8-12 hours)

- **US2** [P1]: As a trader, I want each strategy's performance tracked independently so that I can identify which strategies contribute positively to portfolio returns
  - **Acceptance**:
    - Each strategy has separate equity curve tracking
    - Each trade tagged with originating strategy_id
    - Performance metrics calculated per-strategy (Sharpe, max drawdown, total return)
    - Orchestrator generates comparison table (strategy_id, total_return, sharpe_ratio, win_rate)
  - **Independent test**: Run 2 strategies with different performance, verify individual metrics match single-strategy backtests
  - **Effort**: M (6-8 hours)

- **US3** [P1]: As a trader, I want the orchestrator to prevent strategies from exceeding their capital allocation so that portfolio risk stays within defined limits
  - **Acceptance**:
    - Orchestrator tracks capital used per strategy in real-time
    - Entry signals rejected if strategy at max allocation
    - Logged warning when strategy blocked by capital limit
    - Capital released when positions close
  - **Independent test**: Configure strategy with 30% allocation, verify cannot use >30% even if generating strong signals
  - **Effort**: M (6-8 hours)

**Priority 2 (Enhancement)**

- **US4** [P2]: As a trader, I want to configure how the orchestrator resolves conflicts when multiple strategies generate signals for the same symbol so that I have control over signal aggregation logic
  - **Acceptance**:
    - Orchestrator supports conflict resolution modes: NET_SIGNAL (sum), FIRST_WINS (priority), CANCEL_BOTH (conservative)
    - Mode configurable at orchestrator initialization
    - Conflict events logged with original signals and resolution outcome
    - Unit tests for each resolution mode
  - **Depends on**: US1
  - **Effort**: L (8-12 hours)

- **US5** [P2]: As a trader, I want strategies to rebalance to target allocation when deviations exceed threshold so that portfolio maintains desired strategy mix over time
  - **Acceptance**:
    - Orchestrator tracks current vs. target allocation per strategy
    - When deviation >10% (configurable), triggers rebalance event
    - Rebalancing sells overweight positions, buys underweight (respects strategy signals)
    - Rebalance events logged with before/after allocations
  - **Depends on**: US1, US3
  - **Effort**: XL (12-16 hours)

**Priority 3 (Nice-to-have)**

- **US6** [P3]: As a trader, I want to run strategy parameter optimization across a grid of configurations so that I can identify optimal parameter combinations for each strategy
  - **Acceptance**:
    - Orchestrator accepts parameter grid (strategy, param_name, values[])
    - Runs backtests for all combinations (cartesian product)
    - Generates heatmap of performance metrics vs. parameters
    - Returns best-performing parameter set per strategy
  - **Depends on**: US1, US2
  - **Effort**: XL (16+ hours, consider breaking down)

- **US7** [P3]: As a trader, I want to see correlation analysis between strategy returns so that I can build diversified strategy portfolios
  - **Acceptance**:
    - Orchestrator calculates pairwise correlation matrix of strategy daily returns
    - Generates correlation heatmap visualization
    - Identifies low-correlation pairs (<0.3) for diversification
    - Warns if strategies highly correlated (>0.8)
  - **Depends on**: US2
  - **Effort**: L (8-12 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (P1 stories) to enable basic multi-strategy backtesting. Validate with sample strategies, then add conflict resolution (US4) and rebalancing (US5) based on user needs.

## Visual References

Not applicable (backend system, no UI)

## Success Metrics (HEART Framework)

> **Purpose**: Measure orchestrator effectiveness and adoption by traders developing strategies.

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Traders trust orchestrator calculations | Error-free strategy execution | Error rate in logs | <1% backtest failures | Zero data corruption |
| **Engagement** | Traders use orchestrator for multi-strategy testing | Backtest runs with >1 strategy | % backtests using orchestrator | 40% of backtests multi-strategy | <5min P95 runtime |
| **Adoption** | New strategy developers discover orchestrator | First orchestrator usage | Unique users running orchestrator | 5+ users in first month | Complete documentation |
| **Retention** | Traders continue using orchestrator | Repeated usage over time | 7-day return rate | 60% run again in 7 days | <2 support requests/user |
| **Task Success** | Strategy comparison completed successfully | Backtest completes with report | Success rate of orchestrator runs | 95% complete successfully | <30s P95 report generation |

**Performance Targets**:
- Backtest execution: <2x slowdown vs single-strategy (overhead <100%)
- Memory usage: Linear growth with strategy count (O(n) not O(n²))
- Report generation: <30s for 5 strategies, 2 years data

## Context Strategy & Signal Design

- **System prompt altitude**: Low-level implementation (direct code generation for strategy coordination)
- **Tool surface**: File read/write (models, protocols), test execution, minimal web search
- **Examples in scope**: BuyAndHold + Momentum combo (2 strategies), conflict resolution example, capital limit scenario
- **Context budget**: ~15,000 tokens (implementation phase)
- **Retrieval strategy**: JIT - load strategy_protocol.py, engine.py, models.py when needed
- **Memory artifacts**: NOTES.md for design decisions, update after each implementation milestone
- **Compaction cadence**: Summarize research findings after spec phase
- **Sub-agents**: None (focused implementation, single agent sufficient)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST accept a list of (IStrategy, Decimal weight) tuples at initialization
- **FR-002**: System MUST validate that strategy weights sum to ≤1.0 (≤100%), raising ValueError if exceeded
- **FR-003**: System MUST allocate initial capital to each strategy according to its weight (strategy_capital = total_capital × weight)
- **FR-004**: System MUST execute all strategies chronologically on every historical bar in the dataset
- **FR-005**: System MUST track separate equity curves for each strategy throughout the backtest
- **FR-006**: System MUST tag each trade with the originating strategy identifier
- **FR-007**: System MUST prevent a strategy from opening new positions when it has reached its capital allocation limit
- **FR-008**: System MUST release capital back to a strategy when it closes positions
- **FR-009**: System MUST calculate performance metrics (total return, Sharpe ratio, max drawdown, win rate) independently for each strategy
- **FR-010**: System MUST generate an aggregated portfolio equity curve combining all strategy equity curves
- **FR-011**: System MUST detect conflicts when multiple strategies generate signals for the same symbol on the same bar
- **FR-012**: System MUST log all strategy signal decisions (entry, exit, blocked by capital limit) with timestamps and strategy identifiers
- **FR-013**: System MUST produce a comparison report showing per-strategy performance metrics in tabular format
- **FR-014**: System MUST support strategies implementing the IStrategy protocol without modification to strategy code
- **FR-015**: System MUST maintain chronological order guarantee (no look-ahead bias) when executing multiple strategies

### Non-Functional

- **NFR-001**: Performance: Backtest execution time MUST be <2× single-strategy baseline (overhead <100% for 5 strategies)
- **NFR-002**: Performance: Memory usage MUST grow linearly with strategy count (O(n) complexity, not O(n²))
- **NFR-003**: Reliability: System MUST validate all configuration parameters at initialization (fail-fast principle)
- **NFR-004**: Maintainability: Code MUST achieve ≥90% test coverage (per existing backtest module standard)
- **NFR-005**: Usability: Orchestrator API MUST match BacktestEngine conventions (same run() method signature pattern)
- **NFR-006**: Auditability: All capital allocation decisions MUST be logged with sufficient detail for debugging
- **NFR-007**: Extensibility: Conflict resolution logic MUST be pluggable (support future resolution strategies)

### Key Entities

- **StrategyOrchestrator**: Main coordination class managing multiple strategy instances
  - Attributes: strategies (list), weights (list), capital_allocations (dict), state_per_strategy (dict)
  - Relationships: Composes BacktestEngine, aggregates results from multiple strategies

- **StrategyAllocation**: Capital allocation tracker per strategy
  - Attributes: strategy_id (str), allocated_capital (Decimal), used_capital (Decimal), available_capital (Decimal)
  - Relationships: One per strategy instance

- **OrchestratorConfig**: Configuration for orchestrator behavior
  - Attributes: conflict_resolution_mode (enum), rebalance_threshold (Decimal), logging_level (enum)
  - Relationships: Passed to StrategyOrchestrator at initialization

- **OrchestratorResult**: Extended backtest result with per-strategy breakdowns
  - Attributes: aggregate_metrics (PerformanceMetrics), strategy_results (dict[str, BacktestResult]), comparison_table (DataFrame)
  - Relationships: Extends BacktestResult model

## Deployment Considerations

> **SKIP**: Backend library code, no infrastructure changes required.

No platform dependencies, environment variables, breaking changes, or migrations needed. Standard 3-command rollback via git revert applies.

## Measurement Plan

> **Purpose**: Track orchestrator adoption and reliability through structured logs and test metrics.

### Data Collection

**Structured Logs** (`logs/backtest/*.jsonl`):
- `orchestrator.backtest_started` - { strategy_count, total_capital, weights, symbols, date_range }
- `orchestrator.strategy_signal` - { strategy_id, signal_type, symbol, bar_date, capital_available }
- `orchestrator.capital_limit_hit` - { strategy_id, used_capital, allocation_limit, rejected_signal }
- `orchestrator.conflict_detected` - { symbol, strategies, resolution_mode, outcome }
- `orchestrator.backtest_completed` - { duration_seconds, trade_count, final_equity, error_count }
- `orchestrator.backtest_failed` - { error_type, error_message, strategy_id, bar_date }

**Key Events to Track**:
1. `orchestrator.backtest_started` - Engagement (usage frequency)
2. `orchestrator.backtest_completed` - Task Success (completion rate)
3. `orchestrator.strategy_signal` - Core functionality (signal processing)
4. `orchestrator.backtest_failed` - Happiness (inverse - error tracking)
5. `orchestrator.capital_limit_hit` - Safety verification (limit enforcement)

### Measurement Queries

**Logs** (`logs/backtest/*.jsonl`):
```bash
# Orchestrator adoption rate
total_backtests=$(grep '"event":"backtest' logs/backtest/*.jsonl | wc -l)
orchestrator_backtests=$(grep '"event":"orchestrator.backtest' logs/backtest/*.jsonl | wc -l)
adoption_rate=$(echo "scale=2; $orchestrator_backtests * 100 / $total_backtests" | bc)

# Error rate (target: <1%)
errors=$(grep '"event":"orchestrator.backtest_failed"' logs/backtest/*.jsonl | wc -l)
success=$(grep '"event":"orchestrator.backtest_completed"' logs/backtest/*.jsonl | wc -l)
error_rate=$(echo "scale=2; $errors * 100 / ($errors + $success)" | bc)

# Average strategy count per backtest
grep '"event":"orchestrator.backtest_started"' logs/backtest/*.jsonl | \
  jq -r '.strategy_count' | \
  awk '{sum+=$1; count++} END {print sum/count}'

# P95 execution time
grep '"event":"orchestrator.backtest_completed"' logs/backtest/*.jsonl | \
  jq -r '.duration_seconds' | \
  sort -n | \
  awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'
```

**Test Coverage** (`pytest --cov`):
```bash
# Code coverage (target: ≥90%)
pytest --cov=trading_bot.backtest.orchestrator --cov-report=term

# Performance benchmark (target: <2x slowdown)
pytest tests/backtest/test_orchestrator_performance.py -v
```

**Performance Comparison** (before/after):
```python
# Single-strategy baseline
single_runtime = run_backtest(MomentumStrategy(), data)

# Multi-strategy with orchestrator
multi_runtime = run_orchestrator([Strategy1(), Strategy2(), Strategy3()], data)

slowdown_factor = multi_runtime / single_runtime
assert slowdown_factor < 2.0  # Must be less than 2x
```

### Success Criteria Validation

**Week 1 (Post-MVP)**:
- ✅ Error rate <1% (measure via logs)
- ✅ Test coverage ≥90% (measure via pytest --cov)
- ✅ Performance overhead <100% (measure via benchmarks)

**Week 2-4 (Adoption)**:
- ✅ 5+ unique users running orchestrator (count from logs)
- ✅ 40% of backtests multi-strategy (adoption_rate calculation)
- ✅ 60% 7-day return rate (repeat users in logs)

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [x] Requirements testable, no [NEEDS CLARIFICATION] markers
- [x] No implementation details (tech stack, APIs, code)
- [x] All functional requirements have specific acceptance criteria

### Conditional: Success Metrics (Skip if no user tracking)
- [x] HEART metrics defined with measurement sources (structured logs, test metrics)
- [x] Measurement queries documented (bash log analysis, pytest commands)

### Conditional: UI Features (Skip if backend-only)
- [x] SKIPPED - Backend system, no UI components

### Conditional: Deployment Impact (Skip if no infrastructure changes)
- [x] SKIPPED - Library code, no deployment changes
