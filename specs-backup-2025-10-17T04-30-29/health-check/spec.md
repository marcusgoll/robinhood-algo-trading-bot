# Feature Specification: Session Health Monitoring

**Branch**: `health-check`
**Created**: 2025-10-09
**Status**: Draft

## User Scenarios

### Primary User Story
As a trading bot operator, I need the bot to maintain an active Robinhood session and detect authentication failures proactively, so that trades are never attempted with invalid credentials and the bot fails safely rather than failing silently.

### Acceptance Scenarios

1. **Given** the bot is running with valid credentials, **When** a health check runs, **Then** the session is verified as active and no reauth is needed
2. **Given** the bot's session token has expired, **When** a health check runs, **Then** the bot automatically reauthenticates and logs the event
3. **Given** reauth fails after retries, **When** the health check detects this, **Then** the bot halts trading and trips the circuit breaker
4. **Given** the bot is within trading hours (7am-10am EST), **When** 5 minutes elapse, **Then** a periodic health check runs automatically
5. **Given** the bot is about to execute a trade, **When** the execute_trade method is called, **Then** a health check runs first to verify session validity
6. **Given** health checks have been running, **When** an operator requests status, **Then** session metrics are displayed (uptime, last check time, reauth count)

### Edge Cases

- What happens when the API is temporarily unavailable (503 errors)?
  - Answer: Retry with exponential backoff (1s, 2s, 4s), then fail-safe halt
- What happens when the network connection is lost?
  - Answer: Retry logic handles transient failures, logs error, halts if persistent
- What happens when credentials are changed during operation?
  - Answer: Reauth will fail, bot halts with clear error message (restart required)
- What happens during market hours but outside trading window (10am-4pm)?
  - Answer: Health checks still run but at reduced frequency (every 15 minutes)

## Visual References

Not applicable - CLI/background service feature with no UI components.

## Success Metrics (HEART Framework)

> **Purpose**: Define quantified success criteria using Google's HEART framework.
> **Constraint**: All metrics MUST be Claude Code-measurable (SQL, logs, Lighthouse).

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce auth-related errors | Auth failure detection | Error rate for invalid session trades | <0.1% (zero trades with invalid session) | P95 health check latency <2s |
| **Engagement** | Maintain continuous operation | Health check execution | Health checks per session | 12+ checks/hour (5 min interval) | Max 1 reauth/day |
| **Adoption** | Enable safe bot operation | Bot runtime with health | Sessions with health monitoring | 100% (all sessions monitored) | N/A |
| **Retention** | Prevent session expiry | Session uptime | Average session duration | >4 hours (covers full trading window) | <3 reauths/session |
| **Task Success** | Detect failures proactively | Failed trade prevention | Trades attempted with invalid session | 0 (100% prevention) | Health check pass rate >95% |

**Performance Targets**:
- Health check latency: P95 <2s, P99 <5s
- Reauth latency: P95 <10s (includes MFA/push notification time)
- No performance regression on trade execution latency

## Hypothesis

**Problem**: Bot assumes session is valid after initial login, leading to failed trades if token expires during operation
- Evidence: No periodic session validation in current implementation (auth/robinhood_auth.py)
- Impact: All trades could fail silently if session expires, violating §Safety_First principle

**Solution**: Periodic health checks (every 5 minutes) with automatic reauth on failure
- Change: Add SessionHealthMonitor service that pings Robinhood API and verifies authentication status
- Mechanism: Proactive detection prevents attempting trades with invalid session (fail-safe behavior)

**Prediction**: Zero trades attempted with invalid session (100% prevention)
- Primary metric: Invalid session trades = 0 (currently undefined, likely >0 if session expires)
- Expected improvement: Reduces auth-related trade failures from potential failures to 0
- Confidence: High (similar pattern used in production trading systems)

## Context Strategy & Signal Design

- **System prompt altitude**: Mid-level - Service implements health checking with retry logic and metrics tracking
- **Tool surface**: RobinhoodAuth (login/logout/refresh), error_handling.retry (@with_retry), TradingLogger (log events)
- **Examples in scope**:
  1. Health check success (session valid)
  2. Health check failure with reauth success
  3. Health check failure with reauth exhaustion (halt)
- **Context budget**: Low (5k tokens) - Simple service with clear responsibilities
- **Retrieval strategy**: Upfront - Load auth module, retry framework, logger on initialization
- **Memory artifacts**: NOTES.md updated with session metrics after each health check, daily summary
- **Compaction cadence**: N/A (small context footprint)
- **Sub-agents**: None (single-responsibility service)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST perform health check by calling robin_stocks API endpoint (profile or positions)
- **FR-002**: System MUST detect invalid session (401/403 responses or authentication errors)
- **FR-003**: System MUST automatically trigger reauth when health check fails
- **FR-004**: System MUST use exponential backoff retry for health check failures (1s, 2s, 4s)
- **FR-005**: System MUST halt trading and trip circuit breaker if reauth fails after retries
- **FR-006**: System MUST run health checks every 5 minutes during trading hours (7am-10am EST)
- **FR-007**: System MUST run health check before executing any trade
- **FR-008**: System MUST track session metrics (uptime, last check time, reauth count, health check count)
- **FR-009**: System MUST log all health check events (success, failure, reauth triggered)
- **FR-010**: System MUST expose session status via TradingBot.get_session_status() method
- **FR-011**: System MUST use lightweight API call for health check (minimize overhead)
- **FR-012**: System MUST handle network timeouts gracefully (log and retry)

### Non-Functional

- **NFR-001**: Performance: Health check completes in <2s (P95), <5s (P99)
- **NFR-002**: Performance: Health check adds <100ms overhead to trade execution path
- **NFR-003**: Reliability: Health check pass rate >95% (excluding actual auth failures)
- **NFR-004**: Testing: Test coverage ≥90% per Constitution v1.0.0
- **NFR-005**: Security: Never log sensitive session tokens or credentials (§Security)
- **NFR-006**: Audit: All health check state changes logged with timestamps (§Audit_Everything)
- **NFR-007**: Code Quality: Type hints required on all functions (§Code_Quality)
- **NFR-008**: Error Handling: Fail-safe behavior - halt on persistent failures (§Safety_First)

### Key Entities

- **SessionHealthStatus**: Data structure containing session metrics
  - `is_healthy`: bool (current session validity)
  - `session_start_time`: datetime (when session established)
  - `session_uptime_seconds`: int (duration since session start)
  - `last_health_check`: datetime (timestamp of last check)
  - `health_check_count`: int (total checks this session)
  - `reauth_count`: int (number of reauths this session)
  - `consecutive_failures`: int (current failure streak)

- **HealthCheckResult**: Data structure for health check outcome
  - `success`: bool (health check passed/failed)
  - `timestamp`: datetime (when check executed)
  - `latency_ms`: int (check duration)
  - `error_message`: Optional[str] (if failed)
  - `reauth_triggered`: bool (whether reauth was attempted)

## Deployment Considerations

> **Purpose**: Document deployment constraints and dependencies for planning phase.
> **Skip if**: Purely cosmetic UI changes or documentation-only changes.

### Platform Dependencies

None - This is a local-only feature with no deployment platform requirements.

### Environment Variables

No new environment variables required. Uses existing:
- `ROBINHOOD_USERNAME`
- `ROBINHOOD_PASSWORD`
- `MFA_SECRET` (optional)
- `DEVICE_TOKEN` (optional)

### Breaking Changes

**API Contract Changes**: No

**Database Schema Changes**: No

**Auth Flow Modifications**: No (extends existing, doesn't change)

**Client Compatibility**: N/A (local-only feature)

### Migration Requirements

**Database Migrations**: Not required

**Data Backfill**: Not required

**RLS Policy Changes**: No

**Reversibility**: Fully reversible (feature can be disabled by removing health check calls)

### Rollback Considerations

**Standard Rollback**: Yes - Remove health check service and revert to previous behavior

**Special Rollback Needs**: None

**Deployment Metadata**: N/A (local-only feature, no deployment tracking)

---

## Measurement Plan

> **Purpose**: Define how success will be measured using Claude Code-accessible sources.
> **Sources**: Structured logs (JSONL), TradingLogger events.

### Data Collection

**Analytics Events** (structured logs via TradingLogger):
- `health_check.executed` - Every health check attempt
- `health_check.passed` - Successful health check
- `health_check.failed` - Failed health check
- `health_check.reauth_triggered` - Reauth initiated
- `health_check.reauth_success` - Reauth completed successfully
- `health_check.reauth_failed` - Reauth failed, bot halting
- `session.metrics_snapshot` - Periodic session status (every 15 minutes)

**Key Events to Track**:
1. `health_check.executed` - Engagement (frequency)
2. `health_check.passed` - Task Success
3. `health_check.failed` - Happiness (inverse)
4. `health_check.reauth_triggered` - Retention (reauth frequency)
5. `session.metrics_snapshot` - Session uptime tracking

### Measurement Queries

**Logs** (`logs/trading_bot.log`, structured JSONL format):

Health check success rate:
```bash
grep '"event":"health_check' logs/trading_bot.log | jq -r '.event' |
  awk '/passed/ {pass++} /failed/ {fail++} END {print pass/(pass+fail)*100}'
```

Reauth frequency per session:
```bash
grep '"event":"health_check.reauth_triggered"' logs/trading_bot.log |
  jq -r '.session_id' | sort | uniq -c
```

Average session uptime:
```bash
grep '"event":"session.metrics_snapshot"' logs/trading_bot.log |
  jq -r '.session_uptime_seconds' |
  awk '{sum+=$1; count++} END {print sum/count/3600 " hours"}'
```

Health check latency P95:
```bash
grep '"event":"health_check.executed"' logs/trading_bot.log |
  jq -r '.latency_ms' | sort -n |
  awk '{a[NR]=$1} END {print a[int(NR*0.95)] " ms"}'
```

Trades prevented with invalid session:
```bash
# Count health_check.failed events that triggered reauth BEFORE trade execution
grep '"event":"health_check.failed"' logs/trading_bot.log |
  jq -r 'select(.context=="pre_trade")' | wc -l
```

### Experiment Design (A/B Test)

Not applicable - Safety-critical feature deployed to 100% of sessions immediately.

**Validation Plan**:
1. Unit tests (Days 1-2): 90%+ coverage, all edge cases
2. Integration tests (Days 3-4): Mock Robinhood API responses, verify reauth flow
3. Paper trading validation (Days 5-7): Run bot with health checks enabled, monitor logs
4. Live validation (Days 8-14): Deploy with health checks, verify zero invalid session trades

**Success Criteria**:
- Health check pass rate >95%
- Zero trades attempted with invalid session
- Average session uptime >4 hours (covers trading window)
- Health check latency P95 <2s

---

## Quality Gates *(all must pass before `/plan`)*

### Core Requirements
- [x] No implementation details (tech stack, APIs, code)
- [x] Requirements testable and unambiguous
- [x] Context strategy documented
- [x] No [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (performance, UX, data, access)

### Success Metrics (HEART)
- [x] All 5 HEART dimensions have targets defined
- [x] Metrics are Claude Code-measurable (SQL, logs, Lighthouse)
- [x] Hypothesis is specific and testable
- [x] Performance targets specified

### Screens (UI Features Only)
- [x] Skip - No UI components (CLI/background service only)

### Measurement Plan
- [x] Analytics events defined (structured logs)
- [x] Log queries drafted for key metrics
- [x] Validation plan complete (unit, integration, paper trading)
- [x] Measurement sources are Claude Code-accessible

### Deployment Considerations
- [x] Platform dependencies documented (None - local-only)
- [x] Environment variables listed (None new)
- [x] Breaking changes identified (None)
- [x] Migration requirements documented (None)
- [x] Rollback plan specified (standard rollback)
