# Implementation Plan: Session Health Monitoring

## [RESEARCH DECISIONS]

### Decision: Session Health Check Probe
- **Decision**: Use `robin_stocks.robinhood.profiles.load_account_profile()` for lightweight health check
- **Rationale**: Minimal API overhead (<100ms), authenticates session validity, available in existing robin-stocks integration
- **Alternatives**:
  - `get_open_stock_positions()` - Rejected (heavier payload, not needed for health check)
  - Custom auth token validation - Rejected (robin-stocks abstracts token management)
- **Source**: `src/trading_bot/auth/robinhood_auth.py` (robin-stocks integration patterns)

### Decision: Retry Framework
- **Decision**: Reuse existing `@with_retry` decorator from `src/trading_bot/error_handling/retry.py`
- **Rationale**: Already implements exponential backoff (1s, 2s, 4s), jitter, rate limit detection (HTTP 429), logging integration
- **Alternatives**:
  - Inline retry logic in `robinhood_auth.py._retry_with_backoff` - Rejected (duplicates existing framework)
  - No retry - Rejected (transient network failures would unnecessarily trigger circuit breaker)
- **Source**: `src/trading_bot/error_handling/retry.py` (lines 30-148)

### Decision: Circuit Breaker Integration
- **Decision**: Call `circuit_breaker.record_failure()` on health check failure, check `circuit_breaker.should_trip()` before continuing
- **Rationale**: Existing module-level singleton (`circuit_breaker`) already used by retry framework, 5 errors in 60 seconds threshold matches health check failure severity
- **Alternatives**:
  - Separate health check circuit breaker - Rejected (unnecessary complexity, same failure domain)
  - No circuit breaker integration - Rejected (violates §Safety_First principle)
- **Source**: `src/trading_bot/error_handling/circuit_breaker.py` (lines 98-99 singleton instance)

### Decision: Logging Strategy
- **Decision**: Use existing `TradingLogger` for health check events, add structured JSONL logging via `StructuredTradeLogger` pattern
- **Rationale**: Consistent with existing audit trail infrastructure, JSONL format enables measurement queries (spec.md lines 200-234)
- **Alternatives**:
  - Plain text logging only - Rejected (measurement plan requires structured logs for metrics)
  - Custom health check logger - Rejected (fragments audit trail across multiple log files)
- **Source**: `src/trading_bot/logger.py` (TradingLogger), `src/trading_bot/logging/structured_logger.py` (JSONL pattern)

### Decision: Periodic Health Check Timing
- **Decision**: Use Python `threading.Timer` with 5-minute interval (300 seconds), start timer in `TradingBot.start()`, cancel in `TradingBot.stop()`
- **Rationale**: Lightweight, built-in to Python stdlib, no external scheduler dependency, self-repeating pattern
- **Alternatives**:
  - APScheduler - Rejected (external dependency for simple periodic task)
  - Asyncio event loop - Rejected (bot is synchronous, adding async complexity for one feature)
  - Cron job - Rejected (external to bot process, harder to control start/stop)
- **Source**: Python standard library `threading.Timer`, pattern from various Python periodic task implementations

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.10+ (existing bot stack)
- API Client: robin_stocks 3.4.0 (existing integration)
- Retry Framework: `@with_retry` decorator (existing `src/trading_bot/error_handling/retry.py`)
- Circuit Breaker: `CircuitBreaker` singleton (existing `src/trading_bot/error_handling/circuit_breaker.py`)
- Logging: `TradingLogger` + new `HealthCheckLogger` for JSONL structured logs
- Scheduler: Python `threading.Timer` (stdlib, no new dependencies)

**Patterns**:
- **Service Module Pattern**: New `src/trading_bot/health/session_health.py` module following existing patterns (auth, account, error_handling)
- **Data Class Pattern**: `SessionHealthStatus` and `HealthCheckResult` as `@dataclass` (consistent with `AuthConfig`, `TradeRecord`)
- **Singleton Pattern**: `SessionHealthMonitor` instantiated once in `TradingBot.__init__()` (similar to `SafetyChecks`, `StructuredTradeLogger`)
- **Decorator Pattern**: Reuse `@with_retry` for network resilience (existing pattern in codebase)
- **Observer Pattern**: Health check notifies circuit breaker on failures (loose coupling via `circuit_breaker.record_failure()`)

**Dependencies** (new packages required):
- None - Feature uses existing stdlib and robin-stocks integration

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── health/
│   ├── __init__.py              # Export SessionHealthMonitor, SessionHealthStatus, HealthCheckResult
│   ├── session_health.py        # SessionHealthMonitor service
│   └── health_logger.py         # HealthCheckLogger for structured JSONL logs
└── bot.py                       # Integration point: call health checks before trades

tests/
├── unit/
│   └── test_session_health.py   # Unit tests for SessionHealthMonitor
└── integration/
    └── test_health_integration.py  # Integration tests with mock robin_stocks
```

**Module Organization**:
- `health/session_health.py`: Core health check logic, reauth triggering, metrics tracking
- `health/health_logger.py`: Structured JSONL logging for health check events (measurement queries)
- `bot.py`: Integration - call `health_monitor.check_health()` before `execute_trade()` and start periodic timer

---

## [SCHEMA]

**Database Tables** (if applicable):
Not applicable - In-memory session metrics only, no database persistence

**API Schemas** (Internal Python API):

```python
# health/session_health.py

@dataclass
class SessionHealthStatus:
    """Session health metrics (FR-008)."""
    is_healthy: bool                    # Current session validity
    session_start_time: datetime        # When session established (UTC)
    session_uptime_seconds: int         # Duration since session start
    last_health_check: datetime         # Timestamp of last check (UTC)
    health_check_count: int             # Total checks this session
    reauth_count: int                   # Number of reauths this session
    consecutive_failures: int           # Current failure streak

@dataclass
class HealthCheckResult:
    """Health check outcome (FR-009)."""
    success: bool                       # Health check passed/failed
    timestamp: datetime                 # When check executed (UTC)
    latency_ms: int                     # Check duration (NFR-001)
    error_message: Optional[str]        # If failed, error details
    reauth_triggered: bool              # Whether reauth was attempted
```

**State Shape** (SessionHealthMonitor):
```python
class SessionHealthMonitor:
    def __init__(self, auth: RobinhoodAuth):
        self._auth: RobinhoodAuth = auth
        self._status: SessionHealthStatus = SessionHealthStatus(...)
        self._timer: Optional[threading.Timer] = None
        self._lock: threading.Lock = threading.Lock()  # Thread-safe timer management
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Health check completes in <2s (P95), <5s (P99)
- NFR-002: Health check adds <100ms overhead to trade execution path
- NFR-003: Health check pass rate >95% (excluding actual auth failures)

**Implementation Strategies**:
- Use lightweight API call (`load_account_profile()`) instead of heavy data fetches
- Cache health check result for 10 seconds (avoid duplicate checks in rapid trade sequences)
- Async health check on timer (doesn't block trade execution)
- Timeout robin_stocks API call at 10 seconds (fail fast if API unresponsive)

**Measurement**:
- Log `latency_ms` in every `HealthCheckResult` (line 127 in spec.md)
- Query P95/P99 from JSONL logs:
  ```bash
  grep '"event":"health_check.executed"' logs/health_check.log |
    jq -r '.latency_ms' | sort -n |
    awk '{a[NR]=$1} END {print a[int(NR*0.95)] " ms (P95), " a[int(NR*0.99)] " ms (P99)"}'
  ```

---

## [SECURITY]

**Authentication Strategy**:
- Reuse existing `RobinhoodAuth` module (no changes to auth flow)
- Health check uses existing authenticated session (no additional credentials)

**Authorization Model**:
- Not applicable - Health check operates in context of already-authenticated session

**Input Validation**:
- No external inputs - Health check is internal bot operation
- Validate `RobinhoodAuth` instance passed to `SessionHealthMonitor.__init__()` (raise `TypeError` if invalid)

**Rate Limiting**:
- Health check every 5 minutes = 12 requests/hour (well below Robinhood API limits)
- Cache health check result for 10 seconds (avoid duplicate checks if multiple trades queued)
- Retry with exponential backoff on rate limit (429) errors (handled by `@with_retry`)

**Data Protection**:
- NFR-005: Never log session tokens or credentials
- Mask sensitive data in error messages using existing `mask_username()` utility
- Log only: timestamp, success/failure, latency, generic error type (not error payload)

---

## [EXISTING INFRASTRUCTURE - REUSE] (7 components)

**Services/Modules**:
- `src/trading_bot/auth/robinhood_auth.py`: `RobinhoodAuth.login()` for reauth, `is_authenticated()` check
- `src/trading_bot/error_handling/retry.py`: `@with_retry` decorator for exponential backoff (1s, 2s, 4s)
- `src/trading_bot/error_handling/circuit_breaker.py`: `circuit_breaker.record_failure()`, `circuit_breaker.should_trip()`
- `src/trading_bot/logger.py`: `TradingLogger` for health check event logging

**Utilities**:
- `src/trading_bot/utils/security.py`: `mask_username()` for secure logging (NFR-005)
- `src/trading_bot/logging/structured_logger.py`: `StructuredTradeLogger` pattern for JSONL logs (measurement queries)

**Integration Points**:
- `src/trading_bot/bot.py`: `TradingBot.start()` (initialize health monitor), `execute_trade()` (pre-trade health check)

---

## [NEW INFRASTRUCTURE - CREATE] (3 components)

**Backend**:
- `src/trading_bot/health/session_health.py`: `SessionHealthMonitor` service with health check logic
- `src/trading_bot/health/health_logger.py`: `HealthCheckLogger` for structured JSONL event logging
- `src/trading_bot/health/__init__.py`: Module exports (`SessionHealthMonitor`, `SessionHealthStatus`, `HealthCheckResult`)

**Tests**:
- `tests/unit/test_session_health.py`: Unit tests (90%+ coverage per NFR-004)
- `tests/integration/test_health_integration.py`: Integration tests with mock robin_stocks API responses

**Database**:
Not applicable - No database changes

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local-only feature, no deployment platform requirements
- Env vars: No new environment variables (reuses existing `ROBINHOOD_USERNAME`, `ROBINHOOD_PASSWORD`, `MFA_SECRET`, `DEVICE_TOKEN`)
- Breaking changes: No - Feature extends existing bot functionality without changing API contracts
- Migration: Not required - No database or config file changes

**Build Commands**:
- No changes - Feature is pure Python code, no build step

**Environment Variables** (update secrets.schema.json):
- No new variables required
- Uses existing: `ROBINHOOD_USERNAME`, `ROBINHOOD_PASSWORD`, `MFA_SECRET`, `DEVICE_TOKEN`

**Database Migrations**:
- No migrations required - In-memory session state only

**Smoke Tests** (for future CI/CD if applicable):
Not applicable - Local-only feature, no deployment pipeline

**Platform Coupling**:
- None - Feature uses Python stdlib and existing robin-stocks integration (already local-only)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- Health check failures do not crash bot (graceful degradation, log error and continue)
- Circuit breaker trips after 5 consecutive health check failures in 60 seconds (fail-safe halt)
- Health check never logs sensitive session tokens or credentials (NFR-005)
- Health check latency <2s (P95) to avoid blocking trade execution (NFR-001)

**Rollback Plan**:
- Standard rollback: Remove health check calls from `bot.py`, delete `src/trading_bot/health/` module
- No special considerations: Feature is additive, no data persistence or external dependencies
- Rollback commands: `git revert <commit-sha>` or disable feature flag in config (if implemented)

**Artifact Strategy** (local-only feature):
Not applicable - No build artifacts or deployment process (local Python bot)

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: Initial Setup
```bash
# No changes to setup - Feature uses existing dependencies
pip install -r requirements.txt

# Validate health check module loads
python -c "from src.trading_bot.health import SessionHealthMonitor; print('✓ Health check module loaded')"
```

### Scenario 2: Validation
```bash
# Run health check tests
pytest tests/unit/test_session_health.py -v

# Run integration tests
pytest tests/integration/test_health_integration.py -v

# Check test coverage
pytest --cov=src.trading_bot.health --cov-report=term-missing

# Expected: ≥90% coverage per NFR-004
```

### Scenario 3: Manual Testing
1. Start bot with health checks enabled:
   ```bash
   python -m src.trading_bot.main
   ```
2. Verify periodic health checks in logs:
   ```bash
   tail -f logs/trading_bot.log | grep "health_check"
   ```
3. Expected output (every 5 minutes):
   ```
   2025-10-09 14:32:15 UTC | INFO     | health | health_check.executed | latency_ms=127
   2025-10-09 14:32:15 UTC | INFO     | health | health_check.passed | session_uptime=3600s
   ```
4. Simulate auth failure (invalid credentials):
   ```bash
   # Edit .env to use invalid password
   # Restart bot
   # Verify reauth triggered, circuit breaker trips after 5 failures
   ```
5. Check structured logs for metrics:
   ```bash
   grep '"event":"health_check.executed"' logs/health_check.log | jq -r '.latency_ms'
   ```

### Scenario 4: Pre-Trade Health Check
1. Execute a trade via bot CLI/API
2. Verify health check runs before trade execution
3. Expected log sequence:
   ```
   2025-10-09 14:35:00 UTC | INFO     | health | health_check.executed | context=pre_trade | latency_ms=95
   2025-10-09 14:35:00 UTC | INFO     | health | health_check.passed | session_valid=true
   2025-10-09 14:35:00 UTC | INFO     | bot | TRADE EXECUTED | symbol=AAPL | action=BUY | shares=10
   ```

---

## [TESTING STRATEGY]

**Unit Tests** (`tests/unit/test_session_health.py`):
- Test `SessionHealthMonitor.check_health()` success (mock robin_stocks API)
- Test `SessionHealthMonitor.check_health()` failure + reauth trigger
- Test `SessionHealthMonitor.check_health()` retry exhaustion + circuit breaker trip
- Test `SessionHealthMonitor.start_periodic_checks()` timer scheduling
- Test `SessionHealthMonitor.stop_periodic_checks()` timer cancellation
- Test `SessionHealthMonitor.get_session_status()` metrics accuracy
- Test thread safety (concurrent health check calls)

**Integration Tests** (`tests/integration/test_health_integration.py`):
- Test health check + reauth flow with mock robin_stocks responses
- Test health check + circuit breaker integration (failure threshold)
- Test health check before trade execution in `TradingBot.execute_trade()`
- Test periodic health checks run on 5-minute timer
- Test health check JSONL logging and measurement queries

**Edge Cases** (from spec.md):
- API temporarily unavailable (503 errors) - Retry with exponential backoff
- Network connection lost - Retry logic handles transient failures, halt if persistent
- Credentials changed during operation - Reauth fails, bot halts with clear error message
- Market hours but outside trading window - Health checks still run (every 15 minutes per spec edge case)

**Coverage Target**: ≥90% per NFR-004

---

## [REUSE ANALYSIS SUMMARY]

**Reusable Components**: 7
- RobinhoodAuth (login, is_authenticated)
- @with_retry decorator (exponential backoff)
- CircuitBreaker (failure tracking)
- TradingLogger (event logging)
- mask_username() (secure logging)
- StructuredTradeLogger pattern (JSONL logs)
- TradingBot integration points (start, execute_trade)

**New Components**: 3
- SessionHealthMonitor service
- HealthCheckLogger (JSONL structured logs)
- Health check tests (unit + integration)

**Duplication Prevented**:
- Avoided duplicating `_retry_with_backoff` in `robinhood_auth.py` (reuse `@with_retry`)
- Avoided custom circuit breaker (reuse existing singleton)
- Avoided custom logging infrastructure (reuse TradingLogger + StructuredTradeLogger pattern)

**Architecture Alignment**:
- Follows existing service module pattern (`auth/`, `account/`, `error_handling/`)
- Uses existing data class pattern (`@dataclass` for `SessionHealthStatus`, `HealthCheckResult`)
- Integrates with existing circuit breaker and retry framework (no new error handling patterns)
- Maintains existing security practices (credential masking, no token logging)
