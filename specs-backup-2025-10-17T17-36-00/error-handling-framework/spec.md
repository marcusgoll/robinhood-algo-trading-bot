# Feature Specification: API Error Handling Framework

**Branch**: `error-handling-framework`
**Created**: 2025-01-08
**Status**: Draft
**Area**: Infrastructure
**From Roadmap**: Yes (Impact: 5, Effort: 2, Confidence: 0.9, Score: 2.25)

## User Scenarios

### Primary User Story

As a trading bot developer, I want a centralized error handling framework so that all API failures, network errors, and rate limits are handled consistently across modules without duplicating retry logic in each module.

### Acceptance Scenarios

1. **Given** an API call to Robinhood fails with a network error, **When** the error handler processes it, **Then** the system retries with exponential backoff (1s, 2s, 4s) up to 3 attempts before raising the exception

2. **Given** an API call receives HTTP 429 (rate limit), **When** the error handler detects this, **Then** the system waits for the specified retry-after duration before retrying

3. **Given** multiple consecutive API failures occur, **When** the error count exceeds the threshold, **Then** the framework triggers graceful shutdown to prevent cascade failures

4. **Given** a recoverable error occurs during trading, **When** the retry logic exhausts all attempts, **Then** the system logs the full error context (stack trace, parameters, attempt history) and degrades gracefully without crashing

5. **Given** a critical system error occurs (database connection lost, authentication failed), **When** the framework detects this, **Then** the system halts all trading operations and triggers the circuit breaker

### Edge Cases

- What happens when rate limit header is missing from 429 response? → Use default backoff (60s)
- How does system handle intermittent network failures? → Exponential backoff with jitter to prevent thundering herd
- What happens if retry logic itself fails? → Fail fast with clear error message, log to error.log
- How does system handle non-retriable errors (400, 401, 403)? → Raise immediately without retry
- What happens during graceful shutdown if API call is in progress? → Wait for current retry attempt to complete (max 10s timeout), then force shutdown

## Visual References

N/A - Backend-only infrastructure feature

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce error rates | Fewer unhandled exceptions | `% of API calls that fail permanently` | <1% (down from ~3%) | <5% error spike |
| **Engagement** | Maintain bot uptime | Successful recovery from transient errors | `% of API calls that succeed after retry` | >95% recovery rate | >90% minimum |
| **Adoption** | Developer usage | Modules using error framework | `# modules migrated to framework` | 100% (all 7 modules) | Track migration |
| **Retention** | Bot reliability | Continuous operation time | `Mean time between critical failures` | >7 days (up from 2 days) | <1 day unacceptable |
| **Task Success** | API call reliability | API requests completed successfully | `Overall API success rate` | >99% (including retries) | >95% minimum |

**Performance Targets**:
- Retry overhead: <100ms per attempt (logging + backoff calculation)
- Error detection: <10ms (regex matching for rate limit headers)
- Graceful shutdown: <30s (complete current operations safely)

## Hypothesis

**Problem**: Duplicate retry logic across modules causes inconsistent error handling
- Evidence: Found identical `_retry_with_backoff` in AccountData and RobinhoodAuth (DRY violation)
- Evidence: 7 modules with custom error classes, no standard retry pattern
- Evidence: Logs show ~3% API failure rate, many could be recovered with retry
- Impact: All API-dependent modules (account, auth, market data, orders)

**Solution**: Centralized error handling framework with configurable retry policies
- Change: Extract retry logic to `src/trading_bot/error_handling/` module
- Change: Define error hierarchy (Retriable vs NonRetriable errors)
- Change: Implement rate limit detection (HTTP 429, Retry-After header)
- Change: Add graceful shutdown mechanism for critical errors
- Mechanism: Decorator pattern (`@with_retry`) for easy adoption
- Mechanism: Exponential backoff with jitter prevents thundering herd
- Mechanism: Circuit breaker integration prevents cascade failures

**Prediction**: Centralized error handling will reduce permanent API failures from 3% to <1%
- Primary metric: API success rate >99% (including retries), up from ~97%
- Expected improvement: +67% reduction in permanent failures (3% → 1%)
- Secondary metric: Mean time between critical failures >7 days (up from 2 days)
- Confidence: High (proven pattern from industry best practices, similar to Stripe/AWS SDKs)

## Context Strategy & Signal Design

- **System prompt altitude**: Implementation-level (Python error handling patterns, decorators, exception hierarchies)
- **Tool surface**: Grep (find existing error patterns), Read (examine current retry logic), Edit (migrate modules), Bash (run tests)
- **Examples in scope**:
  1. Current retry pattern in AccountData._retry_with_backoff
  2. Error classes across modules (AccountDataError, AuthenticationError)
  3. Rate limit handling pattern from industry SDKs (Stripe, AWS)
- **Context budget**: ~30k tokens (spec + research + templates), trigger compaction after implementation phase
- **Retrieval strategy**: JIT - load Constitution for safety requirements, load existing modules during migration
- **Memory artifacts**: NOTES.md updated after each module migration, error-log.md for tracking issues
- **Compaction cadence**: After research phase (preserve decisions), after implementation (preserve last 20 checkpoints)
- **Sub-agents**: None (straightforward refactoring, no complex agents needed)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST provide a `@with_retry` decorator that wraps functions with exponential backoff retry logic (max 3 attempts, 1s/2s/4s delays)
- **FR-002**: System MUST detect HTTP 429 (rate limit) responses and respect `Retry-After` header (default 60s if missing)
- **FR-003**: System MUST classify errors as `RetriableError` (network, timeout, 5xx) vs `NonRetriableError` (4xx client errors except 429)
- **FR-004**: System MUST log all retry attempts with structured data: `{attempt, max_attempts, delay, error_type, error_message}`
- **FR-005**: System MUST support custom retry policies (max_attempts, base_delay, backoff_multiplier) per function
- **FR-006**: System MUST trigger graceful shutdown when consecutive errors exceed threshold (default: 5 failures in 60s window)
- **FR-007**: System MUST provide error context for debugging: full stack trace, function parameters (redacted credentials), retry history
- **FR-008**: System MUST support error callbacks for custom handling (e.g., alert on critical failure, invalidate cache on 401)
- **FR-009**: System MUST integrate with existing logging system (TradingLogger) to write to errors.log
- **FR-010**: System MUST preserve exception chaining (`raise ... from e`) for full stack traces

### Non-Functional

- **NFR-001**: Performance: Retry overhead <100ms per attempt (logging + backoff calculation)
- **NFR-002**: Testability: All error scenarios must be unit testable with mocked API calls
- **NFR-003**: Backward Compatibility: Existing error classes (AccountDataError, AuthenticationError) must still work
- **NFR-004**: Error Handling: Framework itself must fail fast and never silently swallow errors
- **NFR-005**: Observability: All retries logged to errors.log with ISO timestamps and retry count
- **NFR-006**: Code Quality: 90% test coverage minimum, type hints on all public functions
- **NFR-007**: Documentation: Inline docstrings for all public APIs with usage examples

### Key Entities

- **RetriableError**: Base exception class for errors that should trigger retry (network, timeout, 5xx, 429)
- **NonRetriableError**: Base exception class for errors that should fail fast (4xx except 429)
- **RetryPolicy**: Configuration dataclass (max_attempts, base_delay, backoff_multiplier, jitter)
- **RetryContext**: Runtime state tracking (current_attempt, last_error, retry_delays, started_at)
- **ErrorHandler**: Core framework class with retry logic, rate limit detection, circuit breaker

## Deployment Considerations

### Platform Dependencies

**Python Dependencies**:
- None (uses standard library: time, logging, functools, dataclasses)

### Environment Variables

**New Required Variables**:
- None (configuration via code, no env vars needed)

**Changed Variables**:
- None

**Schema Update Required**: No

### Breaking Changes

**API Contract Changes**:
- No (additive only - new framework, existing code still works)

**Database Schema Changes**:
- No

**Auth Flow Modifications**:
- No (framework wraps existing auth, doesn't change it)

**Client Compatibility**:
- Backward compatible (decorator is opt-in, existing error classes preserved)

### Migration Requirements

**Database Migrations**:
- No

**Data Backfill**:
- Not required

**RLS Policy Changes**:
- No

**Code Migration**:
- Required: Refactor 7 modules to use `@with_retry` decorator
- Modules: account_data.py, robinhood_auth.py, bot.py, safety_checks.py, mode_switcher.py, validator.py, config.py
- Approach: Gradual migration (one module at a time, keep old retry logic until verified)

**Reversibility**:
- Fully reversible (decorator can be removed, modules revert to inline retry logic)

### Rollback Considerations

**Standard Rollback**:
- Yes: Remove `@with_retry` decorators, restore inline retry logic (git revert)

**Special Rollback Needs**:
- None (no database changes, no breaking API changes)

**Deployment Metadata**:
- Deploy IDs tracked in specs/error-handling-framework/NOTES.md (Deployment Metadata section)

---

## Measurement Plan

### Data Collection

**Structured Logs** (dual instrumentation):
- TradingLogger (errors.log): `logger.error({ "event": "retry_attempt", "attempt": N, "error": type, ...})`
- TradingLogger (trading_bot.log): `logger.info({ "event": "retry_success", "attempts": N, ... })`

**Key Events to Track**:
1. `error.retry_attempt` - Each retry attempt (attempt number, error type, delay)
2. `error.retry_success` - Successful recovery after retry (total attempts, total duration)
3. `error.retry_exhausted` - All retries failed (error context, final exception)
4. `error.rate_limit_detected` - HTTP 429 detected (Retry-After value, backoff duration)
5. `error.graceful_shutdown` - Critical failure triggered shutdown (reason, error count)

### Measurement Queries

**Logs** (`logs/errors.log`, `logs/trading_bot.log`):
```bash
# Error rate (permanent failures)
grep '"event":"error.retry_exhausted"' logs/errors.log | wc -l

# Recovery success rate
retry_attempts=$(grep '"event":"error.retry_attempt"' logs/errors.log | wc -l)
retry_successes=$(grep '"event":"error.retry_success"' logs/trading_bot.log | wc -l)
recovery_rate=$((retry_successes * 100 / retry_attempts))
echo "Recovery rate: ${recovery_rate}%"

# Average retries per success
grep '"event":"error.retry_success"' logs/trading_bot.log | jq -r '.attempts' | awk '{sum+=$1; count++} END {print sum/count}'

# Rate limit incidents
grep '"event":"error.rate_limit_detected"' logs/errors.log | jq -r '.backoff_duration' | sort | uniq -c

# Mean time between critical failures (graceful shutdowns)
grep '"event":"error.graceful_shutdown"' logs/errors.log | jq -r '.timestamp' | xargs -I {} date -d {} +%s | awk '{if(NR>1) print ($1-prev)/86400; prev=$1}'
```

**Test Coverage** (`pytest --cov`):
```bash
# Test coverage must be ≥90%
pytest tests/unit/test_error_handling.py --cov=src/trading_bot/error_handling --cov-report=term-missing

# Verify all error scenarios tested
pytest tests/unit/test_error_handling.py -v --tb=short
```

### Experiment Design (Staged Migration)

**Migration Phases**:
1. **Phase 0 (Days 1-2)**: Create framework, unit tests (100% pass)
2. **Phase 1 (Days 3-4)**: Migrate AccountData module (already has retry logic, easy baseline)
3. **Phase 2 (Days 5-6)**: Migrate RobinhoodAuth module (critical auth path, monitor closely)
4. **Phase 3 (Days 7-14)**: Migrate remaining 5 modules (one per day, validate each)
5. **Phase 4 (Days 15+)**: Monitor production metrics, deprecate inline retry logic

**Kill Switch**: Error rate >5% in any migrated module → revert decorator, restore inline retry

**Success Criteria**:
- All 7 modules migrated with 0 regressions
- API success rate >99% (including retries)
- Recovery rate >95%
- Mean time between critical failures >7 days

---

## Quality Gates *(all must pass before `/plan`)*

### Core Requirements
- [x] No implementation details (tech stack, APIs, code) - Focused on behavior, not implementation
- [x] Requirements testable and unambiguous - All FR-XXX are specific and measurable
- [x] Context strategy documented - System prompt, tools, examples, budget defined
- [x] No [NEEDS CLARIFICATION] markers - All requirements clear
- [x] Constitution aligned - Satisfies §Risk_Management (retry), §Safety_First (circuit breaker), §Audit_Everything (logging)

### Success Metrics (HEART)
- [x] All 5 HEART dimensions have targets defined - See table above
- [x] Metrics are Claude Code-measurable (SQL, logs, Lighthouse) - All from logs/errors.log and logs/trading_bot.log
- [x] Hypothesis is specific and testable - 3% → <1% permanent failure rate
- [x] Performance targets from budgets.md specified - <100ms retry overhead, <10ms error detection

### Screens (UI Features Only)
- [x] Skip - Backend-only infrastructure feature (no UI)

### Measurement Plan
- [x] Analytics events defined (PostHog + logs + DB) - 5 key events defined in structured logs
- [x] SQL queries drafted for key metrics - Bash log queries provided
- [x] Experiment design complete (control, treatment, ramp) - Staged migration plan (5 phases)
- [x] Measurement sources are Claude Code-accessible - All from local log files

### Deployment Considerations
- [x] Platform dependencies documented - Python stdlib only (no new deps)
- [x] Environment variables listed - None required
- [x] Breaking changes identified - None (backward compatible)
- [x] Migration requirements documented - Code migration for 7 modules, fully reversible
- [x] Rollback plan specified - Standard git revert, no special considerations
