# Feature: Emotional control mechanisms

## Overview
This feature implements emotional control safeguards to protect traders from making poor decisions during losing streaks or after significant losses. The system automatically reduces position sizes and enforces recovery periods to prevent emotional revenge trading and preserve capital during periods of drawdown.

## Research Findings

### Finding 1: Existing circuit breaker infrastructure
**Source**: src/trading_bot/safety_checks.py, src/trading_bot/error_handling/circuit_breaker.py
**Details**: Project already has circuit breaker implementation for consecutive losses and daily loss limits
**Decision**: Extend existing circuit breaker pattern rather than creating new mechanism

### Finding 2: Risk management foundation
**Source**: src/trading_bot/risk_management/manager.py
**Details**: RiskManager class with position sizing calculator and pullback analyzer
**Decision**: Integrate emotional control as risk manager extension

### Finding 3: Daily profit goal management shipped (v1.5.0)
**Source**: roadmap.md lines 649-676
**Details**: DailyProfitTracker with profit protection, giveback threshold, state persistence
**Decision**: Use similar pattern for loss tracking and position size reduction

### Finding 4: Roadmap backlog entry exists
**Source**: roadmap.md lines 715-728
**Details**: "emotional-controls" feature listed with ICE score 1.60 (Impact: 4, Effort: 2, Confidence: 0.8)
**Requirements captured**:
- Detect significant loss (threshold TBD)
- Auto-reduce position size to 25% of normal
- Require manual reset after recovery period
- Log all size adjustments
- Force simulator mode after daily loss limit hit
**Decision**: Use roadmap requirements as baseline, add details via specification

### Finding 5: Constitution §Safety_First and §Risk_Management
**Source**: .spec-flow/memory/constitution.md lines 11-27
**Principles**:
- Fail safe, not fail open (errors halt trading)
- Circuit breakers required (hard limits on losses)
- Position sizing mandatory (never exceed 5% portfolio per position)
**Decision**: Emotional controls must align with these principles

## System Components Analysis
N/A - Backend-only feature (no UI components needed)

## Feature Classification
- UI screens: false
- Improvement: true (enhances existing risk management)
- Measurable: true (track loss events, position size reductions, recovery periods)
- Deployment impact: false (pure Python logic, no infrastructure changes)

## Key Decisions

1. **Position Size Reduction**: Reduce to 25% of normal size after significant loss event (defined as single trade loss ≥3% of account OR consecutive loss streak ≥3 trades)

2. **Recovery Period**: Require 3 consecutive profitable trades OR manual admin reset to restore normal position sizing

3. **Manual Reset Authority**: Only admin/user can manually override recovery period (prevents automated premature scaling)

4. **State Persistence**: Use JSONL logging pattern (similar to DailyProfitTracker) for audit trail and state recovery

5. **Integration Point**: Extend RiskManager class with new EmotionalControl module that wraps position sizing calculations

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-22

## Last Updated
2025-10-22T09:45:00-04:00
- Phase 1 (Plan): 2025-10-22

## Phase 1 Summary (Planning)

**Research Depth**: 267 lines (research.md)
**Key Decisions**: 6 architectural decisions documented
**Components to Reuse**: 8 (DailyProfitTracker pattern, RiskManager, CircuitBreaker, AccountData, PerformanceTracker, logging patterns, persistence patterns, Decimal precision)
**New Components**: 5 (EmotionalControl tracker, models, config, CLI, log files)
**Migration Needed**: No (file-based storage, auto-created on first run)

**Architecture Highlights**:
- Follow DailyProfitTracker v1.5.0 pattern for state persistence and JSONL logging
- EmotionalControl multiplier (0.25 or 1.00) integrates with RiskManager.calculate_position_plan()
- Fail-safe default: State corruption → ACTIVE (conservative 25% sizing)
- Atomic file writes (temp + rename) prevent state corruption on crash
- CLI-only interface (no web UI for v1.0)

**Artifacts**:
- research.md: Research decisions, component reuse analysis, architecture notes
- data-model.md: Entity definitions (State, Event, Config), schemas, persistence strategy
- plan.md: Consolidated architecture, stack decisions, integration points, testing strategy
- quickstart.md: Integration scenarios, manual testing workflows, CLI examples
- contracts/cli-interface.md: CLI command specifications, Python API, error handling
- error-log.md: Initialized for implementation tracking

## Phase 2 Summary (Task Breakdown)

**Date**: 2025-10-22
**Total Tasks**: 33
**Parallel Opportunities**: 25 tasks marked [P]
**Test Tasks**: 10 (unit + integration + performance + smoke tests)

**Task Breakdown by Phase**:
- Phase 1 (Setup): 3 tasks - Project structure, log directory, configuration
- Phase 2 (Data Models): 3 tasks - State, Event, Config models
- Phase 3 (Core Tracker Logic): 9 tasks - EmotionalControl class implementation
- Phase 4 (RiskManager Integration): 2 tasks - Position sizing multiplier integration
- Phase 5 (CLI Commands): 3 tasks - Status, reset, events commands
- Phase 6 (Testing): 10 tasks - Unit, integration, performance tests
- Phase 7 (Deployment): 3 tasks - Smoke tests, documentation, deployment checklist

**Reuse Opportunities Identified**: 8
- DailyProfitTracker (state persistence, JSONL logging, update_state orchestration)
- RiskManager (position sizing integration)
- CircuitBreaker (streak tracking pattern)
- PerformanceTracker (win/loss detection)
- AccountData (balance retrieval)
- Atomic write patterns (temp + rename)
- JSONL logging (daily rotation, Decimal serialization)
- pytest framework

**Key Task Decisions**:
1. TDD approach required per Constitution (test coverage ≥90%)
2. Performance benchmarks for NFR validation (<10ms update_state)
3. Fail-safe testing (state corruption → ACTIVE default)
4. Integration tests verify RiskManager multiplier application
5. Smoke tests for deployment validation (<90s execution)

**Checkpoint**:
- ✅ Tasks generated: 33 tasks
- ✅ Dependency graph created (7 sequential phases)
- ✅ Parallel execution identified (25 tasks can run in parallel)
- ✅ Test strategy defined (unit + integration + performance + smoke)
- 📋 Ready for: /analyze

**Next Phase**: /analyze (cross-artifact consistency, anti-duplication, architecture validation)

## Phase 3 Summary (Analysis)

**Date**: 2025-10-22
**Status**: ✅ READY FOR IMPLEMENTATION
**Critical Issues**: 0
**High Priority Issues**: 0
**Medium Priority Issues**: 0
**Low Priority Issues**: 0

**Validation Results**:
- ✅ Constitution Alignment: All principles addressed (§Safety_First, §Code_Quality, §Risk_Management, §Testing_Requirements)
- ✅ Cross-Artifact Consistency: 100% (terminology, thresholds, requirements)
- ✅ Requirements Traceability: 100% (14/14 functional requirements mapped to tasks)
- ✅ Acceptance Criteria Coverage: 100% (23/23 criteria mapped to tests)
- ✅ Test Coverage Strategy: Comprehensive (10 test tasks, ≥90% target)
- ✅ Dependency Analysis: No new external dependencies required
- ✅ Implementation Readiness: Clear task breakdown with 14 parallel opportunities

**Key Validation Findings**:
1. Threshold Consistency: 3% loss, 3 consecutive trades, 25% position size - consistent across all artifacts
2. Pattern Reuse: DailyProfitTracker reference validated (20+ consistent references)
3. No Ambiguity: Zero vague terms or unresolved placeholders detected
4. Data Model Integrity: All 3 entities (State, Event, Config) well-defined
5. Test Quality: Comprehensive guardrails (speed, coverage, clarity requirements)

**Quality Metrics**:
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Requirements defined | ≥10 | 20 | ✅ PASS |
| Acceptance criteria | ≥15 | 23 | ✅ PASS |
| Task breakdown clarity | Clear | 33 tasks, 7 phases | ✅ PASS |
| Test coverage target | ≥90% | ≥90% | ✅ PASS |
| Constitution alignment | 100% | 100% | ✅ PASS |
| Requirement traceability | 100% | 100% | ✅ PASS |

**Artifacts**:
- analysis-report.md: Comprehensive cross-artifact validation (385 lines)

**Recommendation**: 🟢 GREEN LIGHT FOR IMPLEMENTATION

**Checkpoint**:
- ✅ Constitution principles validated
- ✅ Cross-artifact consistency verified
- ✅ Requirements fully traced to tasks
- ✅ Test strategy comprehensive
- ✅ No blocking issues identified
- 📋 Ready for: /implement

**Next Phase**: /implement (TDD execution, 33 tasks, estimated 13 hours with parallelization)
