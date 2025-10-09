# Feature: trade-logging

## Overview
Enhanced trade logging system that extends the existing logging framework with structured, queryable trade execution data. Enables Claude Code-measurable analytics for strategy performance analysis, compliance auditing, and decision audit trails.

## Research Findings

### Finding 1: Existing Logging System
Source: `src/trading_bot/logger.py`
- Current implementation: Basic text-based logging to `logs/trades.log`
- Format: `BUY 100 shares of AAPL @ $150.50 [PAPER]`
- Limitation: Not queryable, no structured data, difficult to analyze
- Decision: Build on existing framework, add structured JSON logging

### Finding 2: Constitution Requirements
Source: `.spec-flow/memory/constitution.md`
- §Audit_Everything: Every trade decision must be logged with reasoning
- §Data_Integrity: All timestamps in UTC, validate market data
- §Safety_First: Comprehensive audit trail for compliance
- Decision: Must maintain backwards compatibility with existing audit requirements

### Finding 3: Claude Code Measurement
Source: `spec-template.md` HEART metrics section
- Requirement: All metrics must be Claude Code-measurable (SQL, logs, Lighthouse)
- Implication: Need structured logs (JSON format) for grep/jq queries
- Decision: Dual logging - human-readable text + machine-readable JSON

### Finding 4: Similar Patterns
Source: Project structure analysis
- No existing structured logging for trades
- No database for trade history
- Gaps: Performance analytics, strategy comparison, backtest validation
- Decision: File-based structured logging (no database dependency for v1)

## System Components Analysis
**Reusable (from existing codebase)**:
- `TradingLogger` class (base framework)
- `UTCFormatter` (timestamp handling)
- `log_trade()` function (hook point for enhancement)

**New Components Needed**:
- `TradeRecord` dataclass (typed trade data structure)
- `StructuredTradeLogger` (JSON logging)
- `TradeQueryHelper` (analytics queries)

**Rationale**: System-first approach ensures consistency with existing logging framework and maintains backwards compatibility.

## Feature Classification
- UI screens: false (no UI components)
- Improvement: true (enhances existing logging)
- Measurable: true (strategy performance metrics)
- Deployment impact: false (code-only, no platform changes)

## Checkpoints
- Phase 0 (Spec): 2025-10-09
- Phase 1 (Plan): 2025-10-09
- Phase 2 (Tasks): 2025-10-09

## Phase 1 Summary (Plan)
- Research depth: 59 lines (NOTES.md research findings)
- Key decisions: 4 (build on existing, dual logging, file-based, incremental)
- Components to reuse: 3 (TradingLogger, UTCFormatter, log_trade hook)
- New components: 3 (TradeRecord, StructuredTradeLogger, TradeQueryHelper)
- Migration needed: No (backwards compatible enhancement)

## Phase 2 Summary (Tasks)
- Total tasks: 41 (setup, tests, implementation, integration, polish)
- TDD breakdown: 17 RED (failing tests), 17 GREEN (minimal implementation), 0 explicit REFACTOR
- Parallel tasks: 7 (can run independently)
- Test tasks: 23 (comprehensive test coverage)
- Setup/infrastructure: 3 tasks
- Integration: 5 tasks
- Error handling: 4 tasks
- Documentation: 3 tasks
- Task file: specs/trade-logging/tasks.md
- Ready for: /analyze (codebase pattern analysis)

## Artifacts Created
- specs/trade-logging/plan.md (consolidated architecture + design)
- specs/trade-logging/contracts/api.yaml (Python API contracts)
- specs/trade-logging/error-log.md (error tracking initialized)
- specs/trade-logging/tasks.md (41 concrete TDD tasks)

## Phase 3 Summary (Analysis)
- Analysis duration: 5 minutes
- Artifacts analyzed: spec.md (284 lines), plan.md (330 lines), tasks.md (380 lines)
- Requirement coverage: 50% explicit (5/10 FR requirements directly referenced in tasks)
- Critical issues: 3 (log rotation missing, coverage validation missing, field validation incomplete)
- High issues: 5 (serialization failure, pre-write validation, performance target mismatch, missing query helpers)
- Medium issues: 2 (terminology inconsistency, missing helper method)
- TDD ordering: Valid (all RED→GREEN sequences correct)
- Constitution alignment: Strong (3/4 pillars addressed, testing partially addressed)
- Status: Warning - 3 critical issues must be fixed before implementation
- Blockers: NFR-008 (log rotation), NFR-006 (coverage validation), FR-002 (all fields validation)
- Next step: Fix critical issues, then re-run /analyze or proceed with caution to /implement
- Analysis report: specs/trade-logging/analysis-report.md

## Implementation Progress
- ✅ T001 [P]: Create logging package structure
- ✅ T002 [P]: Create logs/trades directory with 700 permissions (Windows ACL: owner-only full control)
- ✅ T003 [P]: Add test fixtures for trade data
- ✅ T004 [RED]: Write test: TradeRecord validates required fields (FAILING - ModuleNotFoundError)
- ✅ T005 [RED]: Write test: TradeRecord validates symbol format (FAILING - ModuleNotFoundError)
- ✅ T006 [RED]: Write test: TradeRecord validates numeric constraints (FAILING - ModuleNotFoundError)
- ✅ T007 [RED]: Write test: TradeRecord serializes to JSON (FAILING - ModuleNotFoundError)
- ✅ T008 [RED]: Write test: TradeRecord serializes to JSONL (FAILING - ModuleNotFoundError)

## Last Updated
2025-10-09T06:15:00Z
