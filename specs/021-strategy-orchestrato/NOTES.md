# Feature: strategy-orchestrator

## Overview
Strategy orchestration system to manage, coordinate, and execute multiple trading strategies within the backtesting engine framework.

## Research Findings

### Finding 1: Existing Strategy Protocol
Source: src/trading_bot/backtest/strategy_protocol.py
- IStrategy protocol defines should_enter() and should_exit() interfaces
- Strategies are stateless: all state passed via parameters
- Strategies receive chronological data (no look-ahead bias)
- Currently designed for single-strategy execution

Decision: Orchestrator should support multiple IStrategy implementations simultaneously

### Finding 2: Sample Strategy Patterns
Source: examples/sample_strategies.py
- BuyAndHoldStrategy: Simple baseline (single trade, hold forever)
- MomentumStrategy: MA crossover (short/long window configurable)
- Strategies use clean, focused logic without side effects

Decision: Orchestrator should remain strategy-agnostic (works with any IStrategy)

### Finding 3: Backtesting Engine Architecture
Source: src/trading_bot/backtest/engine.py
- BacktestEngine executes single strategy chronologically
- Tracks portfolio state, positions, equity curve
- Generates comprehensive performance metrics
- Currently single-strategy focused

Implication: Orchestrator needs to coordinate multiple strategy instances while maintaining single execution timeline

### Finding 4: Similar Orchestration Pattern
Source: api/app/services/status_orchestrator.py
- StatusOrchestrator coordinates multiple status check services
- Aggregates results from parallel operations
- Provides unified interface for multi-component systems

Decision: Apply similar coordination pattern for strategy management

## System Components Analysis
**Reusable Components**:
- IStrategy protocol (existing interface)
- BacktestEngine (execution engine)
- HistoricalDataBar, Position, Trade models (data structures)
- PerformanceCalculator (metrics generation)

**New Components Needed**:
- StrategyOrchestrator (main coordinator)
- Strategy allocation/weighting system
- Multi-strategy portfolio aggregator
- Strategy conflict resolution logic

**Rationale**: System-first approach leverages existing backtesting infrastructure while adding coordination layer

## Feature Classification
- UI screens: false (backend system, no UI)
- Improvement: false (new capability, not improving existing)
- Measurable: true (strategy performance metrics, portfolio returns)
- Deployment impact: false (library code, no infrastructure changes)

## Research Mode
Standard (backend feature with measurable outcomes)

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-20
- Phase 1 (Plan): 2025-10-20
  - Artifacts: research.md, data-model.md, quickstart.md, plan.md, contracts/api.yaml, error-log.md
  - Research decisions: 5 key architectural choices
  - Migration required: No

## Phase 1 Summary
- Research depth: 120 lines
- Key decisions: 5 (composition pattern, protocol preservation, result aggregation, allocation tracking, structured logging)
- Components to reuse: 9 (BacktestEngine, IStrategy, PerformanceCalculator, ReportGenerator, models, test patterns)
- New components: 6 (StrategyOrchestrator, 3 dataclasses, 2 test modules)
- Migration needed: No

## Last Updated
2025-10-20T15:45:00-05:00

## Phase 2: Tasks (2025-10-20)

**Summary**:
- Total tasks: 27
- User story tasks: 17 (US1: 7, US2: 5, US3: 5)
- Parallel opportunities: 15 tasks marked [P]
- Setup tasks: 2
- Task file: specs/021-strategy-orchestrato/tasks.md

**Checkpoint**:
- ✅ Tasks generated: 27
- ✅ User story organization: Complete (US1-US3 mapped to tasks)
- ✅ Dependency graph: Created (7-phase sequential execution)
- ✅ MVP strategy: Defined (all P1 stories - US1, US2, US3)
- 📋 Ready for: /analyze

**Task Breakdown**:
- Phase 1 (Setup): 2 tasks
- Phase 2 (Core Data Models): 5 tasks
- Phase 3 (US1 - Multi-strategy execution): 7 tasks
- Phase 4 (US2 - Independent tracking): 5 tasks
- Phase 5 (US3 - Capital limits): 5 tasks
- Phase 6 (Integration & Logging): 6 tasks
- Phase 7 (Documentation): 3 tasks

**Key Task Decisions**:
1. TDD approach: Write tests before implementation (T010-T012, T020-T023, T030-T032)
2. Dataclasses first: Core models block all implementation (T005-T009)
3. Integration tests validate end-to-end user stories (T040-T042)
4. Performance benchmarks enforce NFRs (T044-T045)
5. Structured logging enables measurement queries (T043)

## Phase 3: Analysis (2025-10-20)

**Summary**:
- Cross-artifact consistency: ✅ Validated
- Total issues found: 5 (0 critical, 0 high, 2 medium, 3 low)
- Requirements coverage: 95% (21/22 requirements mapped to tasks)
- User story coverage: 100% (3/3 MVP stories complete)
- Analysis report: specs/021-strategy-orchestrato/analysis-report.md

**Checkpoint**:
- ✅ Spec → Plan alignment: Validated
- ✅ Plan → Tasks alignment: Validated
- ✅ Coverage gaps identified: 2 minor gaps (FR-011, FR-014)
- ✅ Quality gates passed: All core requirements met
- ✅ Constitution alignment: No violations
- 📋 Ready for: /implement

**Key Findings**:

1. **Coverage Analysis**:
   - 21/22 functional requirements mapped to tasks (95%)
   - FR-011 (conflict detection): Partial coverage - logging only (resolution deferred to P2/US4)
   - FR-014 (IStrategy compatibility): Missing explicit test (recommended to add T019)
   - All 3 MVP user stories (US1-US3) fully covered with 23 tasks

2. **Cross-Artifact Consistency**:
   - Architecture (plan.md) matches requirements (spec.md)
   - All 7 implementation phases have corresponding tasks
   - TDD approach enforced: All implementation tasks have preceding test tasks
   - Reuse strategy followed: 9 components reused, 6 new components

3. **Quality Validation**:
   - Test coverage target: ≥90% (NFR-004, constitution requirement)
   - Performance targets specified: <2x overhead (T044), O(n) memory (T045)
   - Fail-fast validation planned (T010, T016)
   - Structured logging planned (T043)

4. **Minor Issues Identified**:
   - MEDIUM: FR-011 conflict detection underspecified (mitigation: logging only for MVP)
   - MEDIUM: FR-014 IStrategy compatibility lacks explicit test (mitigation: recommend adding T019)
   - LOW: Terminology inconsistencies (strategy_id vs strategy ID) - non-blocking
   - LOW: NFR-002 validation method could reference plan.md memory profiling

5. **Parallelization Opportunities**:
   - 23 tasks marked [P] (64% of total)
   - Estimated speedup: 12 hours → 8 hours with parallel execution (33% reduction)
   - Critical path: T001 → Models → US1 → US2 → US3 → Integration → Docs

**Next Actions**:
- Execute `/implement` to begin TDD implementation
- Expected duration: 8-10 hours with parallel execution
- Quality gates: mypy --strict, ruff linting, pytest --cov ≥90%

## Phase 4: Implementation (2025-10-20)

**Task Completion**:

✅ T001: Created error tracking log
  - Evidence: File created at specs/021-strategy-orchestrato/error-log.md
  - Committed: ea99dbf (design:plan: complete architecture with reuse analysis)

