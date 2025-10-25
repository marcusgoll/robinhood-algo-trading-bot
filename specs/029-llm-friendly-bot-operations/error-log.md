# Error Log: LLM-Friendly Bot Operations and Monitoring

## Planning Phase (Phase 0-2)

None yet.

---

## Implementation Phase (Phase 3-4)

[Populated during /tasks and /implement]

---

## Testing Phase (Phase 5)

[Populated during /debug and /preview]

---

## Deployment Phase (Phase 6-7)

[Populated during staging validation and production deployment]

---

## Error Template

**Error ID**: ERR-[NNN]
**Phase**: [Planning/Implementation/Testing/Deployment]
**Date**: YYYY-MM-DD HH:MM
**Component**: [api/frontend/database/deployment]
**Severity**: [Critical/High/Medium/Low]

**Description**:
[What happened]

**Root Cause**:
[Why it happened]

**Resolution**:
[How it was fixed]

**Prevention**:
[How to prevent in future]

**Related**:
- Spec: [link to requirement]
- Code: [file:line]
- Commit: [sha]

---

## Example Error Entry

**Error ID**: ERR-001
**Phase**: Implementation
**Date**: 2025-10-24 15:30
**Component**: api/app/services/state_aggregator.py
**Severity**: Medium

**Description**:
State aggregator failed to retrieve performance metrics, causing GET /api/v1/state to return 500 error

**Root Cause**:
PerformanceTracker.get_summary() raised AttributeError when no trades exist for the day (empty trade log)

**Resolution**:
Added null check in state_aggregator.py:45 to handle empty performance data gracefully. Returns default PerformanceMetrics(win_rate=0, trades_today=0, ...) when no data available.

**Prevention**:
Add unit tests for edge case: bot just started, no trades yet. Validate all external data sources return valid data or None (never raise exceptions).

**Related**:
- Spec: FR-001 (state API must return valid response)
- Code: api/app/services/state_aggregator.py:45
- Commit: abc1234

### Entry 1: 2025-10-24 - Contract Violations from Code Review

**Failure**: Three critical API contract violations preventing schema validation
**Symptom**: Code review reported CRITICAL issues in SemanticError, BotState, and HealthStatus schemas failing to match OpenAPI contract spec
**Learning**: Contract-first development requires validating implementation against spec before optimization. Missing fields: severity enum in SemanticError, data_age_seconds and warnings in BotState, last_heartbeat in HealthStatus. Enum value mismatch: "unhealthy" vs contract-required "offline"
**Ghost Context Cleanup**: None - pure additions to match contract

**From /optimize → /debug auto-fix flow**

**Files changed**:
- src/trading_bot/logging/semantic_error.py: Added ErrorSeverity enum and severity field
- api/app/schemas/state.py: Added data_age_seconds, warnings to BotStateResponse; added last_heartbeat to HealthStatus; fixed enum "unhealthy" → "offline"; fixed "positions_count" → "position_count"

**Fix time**: 20 minutes (schema corrections)
