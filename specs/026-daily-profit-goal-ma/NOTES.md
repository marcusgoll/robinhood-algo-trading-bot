# Feature: Daily profit goal management

## Overview

Daily profit goal management feature for automated profit protection. System tracks daily P&L (realized + unrealized), detects when trader has given back 50% of peak profit, and triggers protection mode to block new entries and preserve gains. Integrates with existing performance-tracking and safety-checks modules.

**Core Value**: Prevents overtrading and profit giveback by automatically protecting gains when trader experiences significant drawdown from daily peak.

**MVP Scope**: US1-US3 (configure target, track P&L, trigger protection at 50% drawdown)
**Enhancement Scope**: US4-US6 (configurable thresholds, dashboard display, historical analytics)

## Research Findings

### Finding 1: Feature exists in roadmap as "profit-goal-manager"
- **Source**: .spec-flow/memory/roadmap.md (lines 701-713)
- **ICE Score**: 1.60 (Impact: 4, Effort: 2, Confidence: 0.8)
- **Area**: strategy
- **Status**: Backlog
- **Dependencies**: performance-tracking ✅ (shipped v1.0.0), safety-checks ✅ (shipped v1.0.0)
- **Requirements from roadmap**:
  - Set daily profit target
  - Track progress to goal
  - Detect when half of profit given back
  - Trigger exit rule when threshold hit
  - Reset daily at market open (§Risk_Management)

### Finding 2: Constitution compliance required
- **Source**: .spec-flow/memory/constitution.md
- **Relevant principles**:
  - §Risk_Management: Stop losses required, position sizing mandatory, validate all inputs
  - §Safety_First: Fail safe not fail open, audit everything, circuit breakers
  - §Testing_Requirements: 90%+ test coverage, unit tests, integration tests
  - §Code_Quality: Type hints required, one function one purpose, no duplicate logic
  - §Audit_Everything: Trade decisions must be logged with reasoning

### Finding 3: Related shipped features for integration
- **Source**: roadmap.md Shipped section
- **performance-tracking** (v1.0.0 - Oct 15, 2025):
  - PerformanceTracker class with daily/weekly/monthly aggregation
  - AlertEvaluator for threshold monitoring
  - Win/loss ratio calculator
  - 92% test coverage
  - Location: src/trading_bot/performance/
- **safety-checks** (Oct 8, 2025):
  - SafetyChecks module with pre-trade validation
  - Daily loss circuit breaker (3% threshold)
  - Circuit breaker management (trigger/reset)
  - Location: src/trading_bot/safety_checks.py
- **trade-logging** (Oct 9, 2025):
  - TradeRecord dataclass with 27 fields
  - StructuredTradeLogger with daily JSONL rotation
  - TradeQueryHelper for analytics
  - Location: src/trading_bot/logging/

### Finding 4: No existing profit goal logic found
- **Source**: Grep search for "profit.*goal" patterns in src/ directory
- **Result**: No existing profit goal classes or methods
- **Decision**: This is a new feature, not an enhancement

## System Components Analysis
[Populated during system component check]

## Feature Classification
- UI screens: false
- Improvement: false
- Measurable: false
- Deployment impact: false
- Research mode: minimal

## Checkpoints
- Phase 0 (Spec): 2025-10-21

## Last Updated
2025-10-21T23:15:00

## Phase 2: Tasks (2025-10-21 23:30)

**Summary**:
- Total tasks: 36
- User story tasks: 17 (US1: 4, US2: 6, US3: 7)
- Parallel opportunities: 15 tasks marked [P]
- Setup tasks: 2 (Phase 1)
- Foundational tasks: 4 (Phase 2 - blocking prerequisites)
- Polish tasks: 13 (Phase 6 - cross-cutting concerns)
- Task file: specs/026-daily-profit-goal-ma/tasks.md

**Task Breakdown by Phase**:
- Phase 1 (Setup): T001-T002 (2 tasks - directory structure)
- Phase 2 (Foundational): T005-T008 (4 tasks - core models and config)
- Phase 3 (US1 - Configure target): T011-T014 (4 tasks - config and validation)
- Phase 4 (US2 - Track P&L): T015-T020 (6 tasks - tracking and persistence)
- Phase 5 (US3 - Detect giveback): T021-T027 (7 tasks - protection and integration)
- Phase 6 (Polish): T030-T052 (13 tasks - reset, error handling, docs)

**Dependency Graph Highlights**:
1. Phase 2 blocks all user stories (core models required)
2. US1 independent (config only)
3. US2 depends on US1 (needs config to track against target)
4. US3 depends on US2 (needs tracking to detect drawdown)
5. Phase 6 depends on US1-US3 complete

**Parallel Execution Strategy**:
- 15 tasks can run in parallel (42% of total)
- Phase 2: T005, T006, T007 (3 model files simultaneously)
- Phase 3: T011, T012 (2 test files)
- Phase 4: T015, T016, T017 (3 test aspects)
- Phase 5: T021, T022, T023 (3 test files)
- Phase 6: T030, T035, T036, T040, T041 (5 independent polish tasks)

**Testing Strategy**:
- TDD required (tests written before implementation per task order)
- Target: ≥90% coverage (spec.md NFR-005)
- 17 test tasks (47% of total - high test investment)
- Integration tests: T045-T047 (E2E workflow validation)

**REUSE Opportunities**:
- 6 existing components identified for reuse
- PerformanceTracker: P&L aggregation (avoid duplicate logic)
- SafetyChecks: Trade blocking integration point
- StructuredTradeLogger: JSONL daily rotation pattern
- TradeRecord: Dataclass + validation pattern
- Config: Dual loading pattern (env vars + config.json)
- PerformanceSummary: Decimal precision for monetary values

**Key Decisions**:
1. TDD workflow: Write tests before implementation for all user stories
2. Dependency injection: DailyProfitTracker receives PerformanceTracker (testability)
3. File-based state: JSON for persistence, JSONL for audit trail (following existing patterns)
4. Circuit breaker extension: Profit protection as additional validation rule in SafetyChecks
5. Fail-safe design: Protection blocks entries but allows exits (§Safety_First)
6. Single source of truth: PerformanceTracker calculates P&L, profit goal only reads

**Checkpoint**:
- ✅ Tasks generated: 36
- ✅ User story organization: Complete (US1-US3 mapped to tasks)
- ✅ Dependency graph: Created (sequential phases with parallel opportunities)
- ✅ MVP strategy: Defined (US1-US3 only, US4-US6 deferred)
- ✅ Test strategy: TDD with ≥90% coverage requirement
- ✅ REUSE analysis: 6 components identified with integration points
- 📋 Ready for: /analyze

## Phase 4: Implementation (2025-10-21 23:34)

**Batch 1 (Setup) - Complete**:
- ✅ T001: Created profit_goal module structure (src/trading_bot/profit_goal/, tests/unit/profit_goal/)
- ✅ T002: Created logs directory structure (logs/profit-protection/)

**Batch 2 (Foundational Models) - Complete**:
- ✅ T005: Created ProfitGoalConfig dataclass with validation (target $0-$10k, threshold 0.10-0.90)
- ✅ T006: Created DailyProfitState dataclass with 8 fields (P&L tracking, peak profit, protection status)
- ✅ T007: Created ProfitProtectionEvent dataclass with factory method (audit trail logging)

