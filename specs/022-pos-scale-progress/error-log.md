# Error Log: Position Scaling & Phase Progression

## Planning Phase (Phase 0-2)
None yet - planning completed without errors.

## Implementation Phase (Phase 3-4)
[Populated during /tasks and /implement]

## Testing Phase (Phase 5)
[Populated during /debug and /preview]

## Deployment Phase (Phase 6-7)
[Populated during staging validation and production deployment]

---

## Error Template

**Error ID**: ERR-[NNN]
**Phase**: [Planning/Implementation/Testing/Deployment]
**Date**: YYYY-MM-DD HH:MM
**Component**: [phase/manager | phase/validators | phase/trade_limiter | config]
**Severity**: [Critical/High/Medium/Low]

**Description**:
[What happened - detailed error message]

**Root Cause**:
[Why it happened - investigation findings]

**Resolution**:
[How it was fixed - code changes, configuration updates]

**Prevention**:
[How to prevent in future - tests added, validation improved]

**Related**:
- Spec: [link to requirement - e.g., FR-002, NFR-001]
- Code: [file:line - e.g., phase/manager.py:125]
- Commit: [sha - e.g., a1b2c3d]
- Tests: [test file added - e.g., tests/phase/test_edge_case.py]

---

## Common Error Patterns (Predicted)

### Pattern 1: Phase Validation False Positives
**Symptom**: Operator meets criteria but validation blocks advancement

**Likely Causes**:
- Floating point precision errors in win rate calculation
- Session count off-by-one errors
- Date range boundary issues (inclusive vs exclusive)

**Prevention**:
- Use Decimal throughout (no float conversions)
- Test boundary conditions explicitly
- UTC timezone consistency checks

---

### Pattern 2: Trade Limit Reset Timing
**Symptom**: Daily trade counter doesn't reset at market open

**Likely Causes**:
- Timezone mismatch (UTC vs EST)
- Market holiday handling missing
- Clock drift on server

**Prevention**:
- Explicit timezone conversion tests
- Mock datetime in tests
- Log all limit resets with timestamps

---

### Pattern 3: JSONL Corruption
**Symptom**: Phase history unreadable after crash

**Likely Causes**:
- Partial write during crash
- JSON serialization errors (Decimal not handled)
- File permissions issues

**Prevention**:
- Atomic writes (write to temp file, rename)
- Custom Decimal JSON encoder
- File permission checks in tests

---

### Pattern 4: Downgrade Loop
**Symptom**: System oscillates between phases (upgrade → downgrade → upgrade)

**Likely Causes**:
- Downgrade and advancement criteria overlap
- Rolling window includes downgrade trigger trades
- Circuit breaker doesn't pause long enough

**Prevention**:
- Separate advancement and downgrade windows
- Exclude downgrade-triggering trades from advancement validation
- Require manual acknowledgment after downgrade

---

## Error Tracking Guidelines

1. **Always include**:
   - Full stack trace (for crashes)
   - Input values that triggered error
   - Expected vs actual behavior
   - Related spec requirement (FR-XXX, NFR-XXX)

2. **Severity classification**:
   - **Critical**: Data loss, incorrect phase transitions, security breach
   - **High**: Phase validation broken, trade limits not enforced
   - **Medium**: Logging failures, export errors, UI glitches
   - **Low**: Minor edge cases, documentation errors

3. **Resolution tracking**:
   - Link to commit that fixes issue
   - Tests added to prevent regression
   - Documentation updated if needed
   - Related errors (duplicates, similar patterns)

4. **Handoff notes**:
   - For errors passed to /debug phase
   - Context needed for troubleshooting
   - Attempted solutions that failed
