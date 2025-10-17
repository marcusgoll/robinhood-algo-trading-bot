# Tasks: Session Health Monitoring

## [CODEBASE REUSE ANALYSIS]

**Scanned**: `src/trading_bot/**/*.py`, `tests/**/*.py`

### [EXISTING - REUSE]
- ✅ `RobinhoodAuth` (src/trading_bot/auth/robinhood_auth.py) - login(), is_authenticated()
- ✅ `@with_retry` decorator (src/trading_bot/error_handling/retry.py) - Exponential backoff
- ✅ `CircuitBreaker` singleton (src/trading_bot/error_handling/circuit_breaker.py) - record_failure(), should_trip()
- ✅ `TradingLogger` (src/trading_bot/logger.py) - Event logging
- ✅ `mask_username()` (src/trading_bot/utils/security.py) - Secure logging
- ✅ `StructuredTradeLogger` (src/trading_bot/logging/structured_logger.py) - JSONL pattern
- ✅ `TradingBot` (src/trading_bot/bot.py) - Integration point

### [NEW - CREATE]
- 🆕 `SessionHealthMonitor` (src/trading_bot/health/session_health.py) - Core health check service
- 🆕 `HealthCheckLogger` (src/trading_bot/health/health_logger.py) - Structured JSONL health logs
- 🆕 `health/__init__.py` - Module exports

---

## Phase 3.1: Setup (T001-T004)

### T001 [P] Create health module directory structure
- **Action**: Create `src/trading_bot/health/` directory with `__init__.py`
- **Files**:
  - `src/trading_bot/health/__init__.py`
- **Content**: Export SessionHealthMonitor, SessionHealthStatus, HealthCheckResult
- **Pattern**: `src/trading_bot/error_handling/__init__.py` (service module exports)
- **From**: plan.md [STRUCTURE] section

### T002 [P] Create test directory structure
- **Action**: Create `tests/unit/test_health/` and `tests/integration/test_health/` directories
- **Files**:
  - `tests/unit/test_health/__init__.py`
  - `tests/integration/test_health/__init__.py`
- **Pattern**: `tests/unit/test_error_handling/` (parallel test structure)
- **From**: plan.md [STRUCTURE] section

### T003 [P] Create health check data models
- **File**: `src/trading_bot/health/session_health.py`
- **Classes**:
  - `SessionHealthStatus` (@dataclass)
    - Fields: is_healthy (bool), session_start_time (datetime), session_uptime_seconds (int), last_health_check (datetime), health_check_count (int), reauth_count (int), consecutive_failures (int)
  - `HealthCheckResult` (@dataclass)
    - Fields: success (bool), timestamp (datetime), latency_ms (int), error_message (Optional[str]), reauth_triggered (bool)
- **Pattern**: `src/trading_bot/logging/trade_record.py` (dataclass with type hints)
- **Requirements**: NFR-007 (type hints required)
- **From**: plan.md [SCHEMA] section

### T004 [P] Create HealthCheckLogger for structured JSONL logs
- **File**: `src/trading_bot/health/health_logger.py`
- **Class**: `HealthCheckLogger`
- **Methods**:
  - `log_health_check_executed(result: HealthCheckResult, context: str = "periodic")`
  - `log_health_check_passed(status: SessionHealthStatus)`
  - `log_health_check_failed(result: HealthCheckResult)`
  - `log_reauth_triggered(session_id: str)`
  - `log_reauth_success(duration_ms: int)`
  - `log_reauth_failed(error: str)`
  - `log_session_metrics_snapshot(status: SessionHealthStatus)`
- **Pattern**: `src/trading_bot/logging/structured_logger.py` (JSONL structured logging)
- **Requirements**: NFR-006 (audit all state changes), NFR-005 (never log tokens)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE] section

---

## Phase 3.2: RED - Write Failing Tests (T005-T016)

### T005 [RED] Write test: SessionHealthMonitor initializes with valid auth
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_session_health_monitor_initialization`
- **Asserts**:
  - SessionHealthMonitor accepts RobinhoodAuth instance
  - Initial status: is_healthy=False, health_check_count=0, reauth_count=0
  - Raises TypeError if auth is not RobinhoodAuth
- **Pattern**: `tests/unit/test_robinhood_auth.py` (initialization tests)
- **From**: spec.md FR-001

### T006 [RED] Write test: check_health() succeeds with valid session
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_check_health_success_with_valid_session`
- **Mock**: `robin_stocks.robinhood.profiles.load_account_profile()` returns valid profile
- **Asserts**:
  - HealthCheckResult.success = True
  - HealthCheckResult.latency_ms < 2000 (NFR-001)
  - SessionHealthStatus.is_healthy = True
  - SessionHealthStatus.health_check_count += 1
  - SessionHealthStatus.consecutive_failures = 0
- **Pattern**: `tests/unit/test_robinhood_auth.py` (mock robin_stocks responses)
- **From**: spec.md FR-001, FR-002, FR-011

### T007 [RED] Write test: check_health() fails with 401 and triggers reauth
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_check_health_failure_triggers_reauth`
- **Mock**:
  - First call to `load_account_profile()` raises HTTP 401
  - `RobinhoodAuth.login()` succeeds
  - Second call to `load_account_profile()` succeeds
- **Asserts**:
  - HealthCheckResult.success = True (after reauth)
  - HealthCheckResult.reauth_triggered = True
  - SessionHealthStatus.reauth_count += 1
  - RobinhoodAuth.login() was called once
- **Pattern**: `tests/integration/test_auth_integration.py` (reauth flow)
- **From**: spec.md FR-003

### T008 [RED] Write test: check_health() uses @with_retry decorator
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_check_health_uses_retry_decorator`
- **Mock**:
  - First 2 calls to `load_account_profile()` raise network timeout
  - Third call succeeds
- **Asserts**:
  - HealthCheckResult.success = True (after retries)
  - `load_account_profile()` called 3 times
  - Delays between attempts follow exponential backoff (1s, 2s)
- **Pattern**: `tests/unit/test_error_handling/test_retry.py` (retry decorator tests)
- **From**: spec.md FR-004, plan.md [RESEARCH DECISIONS]

### T009 [RED] Write test: check_health() trips circuit breaker after retry exhaustion
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_check_health_trips_circuit_breaker_on_persistent_failure`
- **Mock**:
  - All calls to `load_account_profile()` raise network error
  - `RobinhoodAuth.login()` fails after retries
- **Asserts**:
  - HealthCheckResult.success = False
  - HealthCheckResult.reauth_triggered = True
  - `circuit_breaker.record_failure()` called
  - SessionHealthStatus.consecutive_failures += 1
- **Pattern**: `tests/unit/test_error_handling/test_circuit_breaker.py` (circuit breaker integration)
- **From**: spec.md FR-005, NFR-008

### T010 [RED] Write test: start_periodic_checks() schedules timer every 5 minutes
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_start_periodic_checks_schedules_timer`
- **Mock**: `threading.Timer` constructor and `.start()` method
- **Asserts**:
  - Timer created with 300 second interval (5 minutes)
  - Timer.start() called
  - Timer callback is `_run_periodic_check()` method
- **Pattern**: Python threading.Timer usage in production code
- **From**: spec.md FR-006, plan.md [RESEARCH DECISIONS]

### T011 [RED] Write test: stop_periodic_checks() cancels running timer
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_stop_periodic_checks_cancels_timer`
- **Setup**: Call `start_periodic_checks()` first
- **Action**: Call `stop_periodic_checks()`
- **Asserts**:
  - Timer.cancel() called
  - Internal timer reference set to None
- **Pattern**: Timer cleanup pattern
- **From**: spec.md edge case handling

### T012 [RED] Write test: get_session_status() returns current metrics
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_get_session_status_returns_metrics`
- **Setup**: Run 3 health checks (2 success, 1 failure with reauth)
- **Asserts**:
  - status.health_check_count = 3
  - status.reauth_count = 1
  - status.session_uptime_seconds > 0
  - status.last_health_check is recent datetime
- **Pattern**: `tests/unit/test_account_data.py` (metrics retrieval)
- **From**: spec.md FR-008, FR-010

### T013 [RED] Write test: health check logs all events to HealthCheckLogger
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_health_check_logs_events`
- **Mock**: HealthCheckLogger methods
- **Setup**: Run successful health check
- **Asserts**:
  - `log_health_check_executed()` called with HealthCheckResult
  - `log_health_check_passed()` called with SessionHealthStatus
  - No sensitive data in logs (verify mask_username() used)
- **Pattern**: `tests/unit/test_structured_logger.py` (structured logging tests)
- **From**: spec.md FR-009, NFR-005, NFR-006

### T014 [RED] Write test: health check latency meets performance targets
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_health_check_latency_under_target`
- **Mock**: `load_account_profile()` with realistic delay (100ms)
- **Asserts**:
  - HealthCheckResult.latency_ms < 2000 (P95 target from NFR-001)
  - Timing measured correctly (start to finish)
- **Pattern**: Performance assertion pattern
- **From**: spec.md NFR-001

### T015 [RED] Write test: health check caches result for 10 seconds
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_health_check_caches_result`
- **Setup**: Run check_health() twice within 10 seconds
- **Asserts**:
  - First call hits API (`load_account_profile()` called)
  - Second call returns cached result (no API call)
  - Third call after 10 seconds hits API again
- **Pattern**: Cache expiration pattern
- **From**: plan.md [PERFORMANCE TARGETS]

### T016 [RED] Write test: thread safety for concurrent health checks
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_concurrent_health_checks_thread_safe`
- **Setup**: Start 5 concurrent threads calling check_health()
- **Asserts**:
  - All threads complete successfully
  - health_check_count increments correctly (not race condition)
  - No deadlocks or exceptions
- **Pattern**: Threading test pattern with concurrent.futures
- **From**: plan.md [SCHEMA] (threading.Lock usage)

---

## Phase 3.3: GREEN - Minimal Implementation (T017-T024)

### T017 [GREEN→T005] Implement SessionHealthMonitor.__init__() with validation
- **File**: `src/trading_bot/health/session_health.py`
- **Class**: `SessionHealthMonitor`
- **Constructor**:
  - Accept `auth: RobinhoodAuth` parameter
  - Validate auth is RobinhoodAuth instance (raise TypeError if not)
  - Initialize `_status: SessionHealthStatus` with defaults
  - Initialize `_timer: Optional[threading.Timer] = None`
  - Initialize `_lock: threading.Lock = threading.Lock()`
  - Initialize `_logger: HealthCheckLogger`
- **REUSE**: Import RobinhoodAuth from `src/trading_bot/auth/robinhood_auth.py`
- **Requirements**: NFR-007 (type hints on all parameters)
- **Pattern**: `src/trading_bot/safety_checks.py` (service initialization)
- **From**: plan.md [SCHEMA]

### T018 [GREEN→T006,T008] Implement check_health() with lightweight API probe
- **File**: `src/trading_bot/health/session_health.py`
- **Method**: `SessionHealthMonitor.check_health(context: str = "periodic") -> HealthCheckResult`
- **Implementation**:
  - Check cache (if last check <10s ago, return cached result)
  - Start timer (time.time())
  - Decorate with `@with_retry` (max_attempts=3, backoff_factor=2, start_delay=1.0)
  - Call `robin_stocks.robinhood.profiles.load_account_profile()`
  - Calculate latency_ms (end time - start time)
  - Update SessionHealthStatus (is_healthy=True, health_check_count+=1, consecutive_failures=0, last_health_check=now)
  - Log events via HealthCheckLogger
  - Return HealthCheckResult(success=True, timestamp, latency_ms, None, False)
- **REUSE**:
  - `@with_retry` from `src/trading_bot/error_handling/retry.py`
  - `robin_stocks.robinhood.profiles.load_account_profile()`
- **Error Handling**: Catch exceptions in outer try/except, trigger reauth on auth errors
- **Pattern**: `src/trading_bot/auth/robinhood_auth.py` (API call patterns)
- **From**: plan.md [RESEARCH DECISIONS], spec.md FR-001, FR-011

### T019 [GREEN→T007] Implement reauth trigger on health check failure
- **File**: `src/trading_bot/health/session_health.py`
- **Method**: Enhance `check_health()` exception handler
- **Implementation**:
  - Catch HTTP 401/403 or authentication errors
  - Log `health_check.failed` event
  - Call `self._auth.login()` to reauth
  - Log `reauth_triggered` event
  - Retry health check (one attempt)
  - If success: Update reauth_count, log `reauth_success`, return success result
  - If failure: Log `reauth_failed`, call `circuit_breaker.record_failure()`, return failure result
- **REUSE**:
  - `RobinhoodAuth.login()` from auth module
  - `circuit_breaker.record_failure()` from circuit breaker module
- **Pattern**: `tests/integration/test_auth_integration.py` (reauth flow)
- **From**: spec.md FR-003, FR-005

### T020 [GREEN→T010] Implement start_periodic_checks() with threading.Timer
- **File**: `src/trading_bot/health/session_health.py`
- **Method**: `SessionHealthMonitor.start_periodic_checks()`
- **Implementation**:
  - Define internal method `_run_periodic_check()`:
    - Call `check_health(context="periodic")`
    - Schedule next timer (self-repeating pattern)
  - Create `threading.Timer(300, self._run_periodic_check)`
  - Store timer reference in `self._timer`
  - Start timer with `.start()`
  - Thread-safe: Acquire `self._lock` before modifying `self._timer`
- **Pattern**: Python stdlib threading.Timer self-repeating pattern
- **From**: plan.md [RESEARCH DECISIONS], spec.md FR-006

### T021 [GREEN→T011] Implement stop_periodic_checks() with timer cancellation
- **File**: `src/trading_bot/health/session_health.py`
- **Method**: `SessionHealthMonitor.stop_periodic_checks()`
- **Implementation**:
  - Thread-safe: Acquire `self._lock`
  - Check if `self._timer` is not None
  - Call `self._timer.cancel()`
  - Set `self._timer = None`
  - Release lock
- **Pattern**: Timer cleanup pattern
- **From**: spec.md edge case handling

### T022 [GREEN→T012] Implement get_session_status() metrics retrieval
- **File**: `src/trading_bot/health/session_health.py`
- **Method**: `SessionHealthMonitor.get_session_status() -> SessionHealthStatus`
- **Implementation**:
  - Calculate session_uptime_seconds (now - session_start_time)
  - Update SessionHealthStatus.session_uptime_seconds
  - Return copy of self._status (defensive copy to prevent external mutation)
- **Pattern**: `src/trading_bot/account/account_data.py` (metrics getter)
- **From**: spec.md FR-008, FR-010

### T023 [GREEN→T013,T014,T015,T016] Implement caching, logging, thread safety
- **File**: `src/trading_bot/health/session_health.py`
- **Enhancements to check_health()**:
  - **Caching**: Store last result with timestamp, return if <10s old
  - **Logging**: Call HealthCheckLogger methods at each step (executed, passed/failed, reauth)
  - **Thread Safety**: Wrap state mutations in `with self._lock:` blocks
  - **Secure Logging**: Use `mask_username()` when logging user info
- **REUSE**:
  - `HealthCheckLogger` methods
  - `mask_username()` from `src/trading_bot/utils/security.py`
- **Pattern**: `src/trading_bot/logging/structured_logger.py` (structured logging)
- **From**: spec.md NFR-005, NFR-006, plan.md [PERFORMANCE TARGETS]

### T024 [GREEN→T004] Implement HealthCheckLogger JSONL logging methods
- **File**: `src/trading_bot/health/health_logger.py`
- **Class**: `HealthCheckLogger`
- **Implementation**:
  - Constructor: Accept log file path (default: `logs/health_check.log`)
  - Methods write JSONL formatted events:
    - `log_health_check_executed()` - { event: "health_check.executed", latency_ms, context, timestamp }
    - `log_health_check_passed()` - { event: "health_check.passed", session_uptime, is_healthy, timestamp }
    - `log_health_check_failed()` - { event: "health_check.failed", error_message, timestamp }
    - `log_reauth_triggered()` - { event: "health_check.reauth_triggered", session_id, timestamp }
    - `log_reauth_success()` - { event: "health_check.reauth_success", duration_ms, timestamp }
    - `log_reauth_failed()` - { event: "health_check.reauth_failed", error, timestamp }
    - `log_session_metrics_snapshot()` - { event: "session.metrics_snapshot", ...status fields, timestamp }
- **Pattern**: `src/trading_bot/logging/structured_logger.py` (JSONL format, file handling)
- **From**: spec.md Measurement Plan, plan.md [EXISTING INFRASTRUCTURE - REUSE]

---

## Phase 3.4: REFACTOR - Clean Up (T025-T027)

### T025 [REFACTOR] Extract health check probe logic to separate method
- **File**: `src/trading_bot/health/session_health.py`
- **Refactoring**:
  - Extract API call logic from `check_health()` to `_probe_api() -> bool`
  - `_probe_api()` handles only robin_stocks API call and exception handling
  - `check_health()` orchestrates: cache check, probe, metrics update, logging
- **Tests**: All existing tests remain green (no behavior change)
- **Rationale**: Single Responsibility Principle - separate concerns
- **Pattern**: Extract method refactoring
- **From**: Code quality best practices

### T026 [REFACTOR] Extract reauth logic to separate method
- **File**: `src/trading_bot/health/session_health.py`
- **Refactoring**:
  - Extract reauth flow from `check_health()` to `_attempt_reauth() -> bool`
  - `_attempt_reauth()` handles login, retry, logging, circuit breaker
  - Simplifies `check_health()` exception handler
- **Tests**: All existing tests remain green
- **Rationale**: Reduce cyclomatic complexity of check_health() method
- **Pattern**: Extract method refactoring
- **From**: Code quality best practices (cyclomatic complexity reduction)

### T027 [REFACTOR] Add type hints and docstrings to all public methods
- **File**: `src/trading_bot/health/session_health.py`
- **Changes**:
  - Add Google-style docstrings to all public methods
  - Document parameters, return types, raises
  - Add examples for measurement queries in module docstring
- **Requirements**: NFR-007 (type hints required)
- **Tests**: Run mypy type checker - no errors
- **Pattern**: `src/trading_bot/auth/robinhood_auth.py` (comprehensive docstrings)
- **From**: spec.md NFR-007, code quality standards

---

## Phase 3.5: Integration & Testing (T028-T032)

### T028 [P] Integrate SessionHealthMonitor into TradingBot.__init__()
- **File**: `src/trading_bot/bot.py`
- **Changes**:
  - Import SessionHealthMonitor from health module
  - In `TradingBot.__init__()`: Instantiate `self._health_monitor = SessionHealthMonitor(self._auth)`
- **Pattern**: `src/trading_bot/bot.py` (SafetyChecks initialization)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE], spec.md integration

### T029 [P] Add health check call in TradingBot.start()
- **File**: `src/trading_bot/bot.py`
- **Changes**:
  - In `TradingBot.start()` method:
    - Call `self._health_monitor.start_periodic_checks()` after successful login
  - In `TradingBot.stop()` method:
    - Call `self._health_monitor.stop_periodic_checks()` before shutdown
- **Pattern**: Lifecycle hook pattern
- **From**: spec.md FR-006, plan.md [RESEARCH DECISIONS]

### T030 [P] Add pre-trade health check in execute_trade()
- **File**: `src/trading_bot/bot.py`
- **Changes**:
  - In `execute_trade()` method, before validation:
    - Call `result = self._health_monitor.check_health(context="pre_trade")`
    - If `not result.success`: Log error, return early (do not execute trade)
    - Check `circuit_breaker.should_trip()`: If True, halt bot
  - Update method signature to document health check requirement
- **REUSE**: `circuit_breaker.should_trip()` from error_handling module
- **Pattern**: `src/trading_bot/bot.py` (pre-trade safety checks)
- **From**: spec.md FR-007, NFR-008

### T031 [RED] Write integration test: health check + reauth flow with mock API
- **File**: `tests/integration/test_health/test_health_integration.py`
- **Test**: `test_health_check_reauth_flow_integration`
- **Setup**:
  - Mock robin_stocks API: First call 401, subsequent calls succeed
  - Mock RobinhoodAuth.login(): Success
- **Actions**:
  - Create SessionHealthMonitor with real dependencies
  - Call check_health()
- **Asserts**:
  - Health check fails initially
  - Reauth triggered automatically
  - Health check succeeds after reauth
  - All events logged to JSONL
- **Pattern**: `tests/integration/test_auth_integration.py` (integration test structure)
- **From**: spec.md FR-003, plan.md [TESTING STRATEGY]

### T032 [GREEN→T031] Wire integration test with real-ish dependencies
- **File**: `tests/integration/test_health/test_health_integration.py`
- **Implementation**:
  - Use real SessionHealthMonitor, HealthCheckLogger
  - Mock only external API calls (robin_stocks)
  - Verify JSONL logs written to test log file
  - Parse JSONL and assert event sequence
- **Pattern**: `tests/integration/test_trade_logging_integration.py` (JSONL verification)
- **From**: plan.md [TESTING STRATEGY]

---

## Phase 3.6: Error Handling & Resilience (T033-T036)

### T033 [RED] Write test: health check handles network timeouts gracefully
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_health_check_handles_network_timeout`
- **Mock**: `load_account_profile()` raises `requests.exceptions.Timeout`
- **Asserts**:
  - Retry logic triggered (3 attempts with backoff)
  - If all fail: HealthCheckResult.success = False
  - Error message logged (not sensitive data)
  - Circuit breaker notified
- **Pattern**: `tests/unit/test_error_handling/test_retry.py` (timeout handling)
- **From**: spec.md FR-012, edge cases

### T034 [GREEN→T033] Implement network timeout handling in check_health()
- **File**: `src/trading_bot/health/session_health.py`
- **Changes**:
  - Add `requests.exceptions.Timeout` to exception handler
  - Log timeout error (use generic message, no sensitive data)
  - Rely on @with_retry decorator for retry logic
  - After retry exhaustion: Record circuit breaker failure, return failure result
- **REUSE**: @with_retry handles retries automatically
- **Pattern**: `src/trading_bot/error_handling/retry.py` (timeout handling)
- **From**: spec.md FR-012

### T035 [RED] Write test: health check handles rate limit (429) errors
- **File**: `tests/unit/test_health/test_session_health.py`
- **Test**: `test_health_check_handles_rate_limit`
- **Mock**: `load_account_profile()` raises HTTP 429
- **Asserts**:
  - Retry with exponential backoff (longer delays for 429)
  - If persistent: Log rate limit error, halt gracefully
  - Circuit breaker NOT tripped (rate limit is external, not bot failure)
- **Pattern**: `tests/unit/test_error_handling/test_retry.py` (rate limit detection)
- **From**: plan.md [SECURITY] rate limiting

### T036 [GREEN→T035] Implement rate limit handling in check_health()
- **File**: `src/trading_bot/health/session_health.py`
- **Changes**:
  - Add HTTP 429 detection in exception handler
  - Log rate limit event (do not trip circuit breaker)
  - @with_retry decorator already handles 429 with longer backoff
  - If persistent after retries: Log warning, return failure result (graceful degradation)
- **REUSE**: @with_retry already has rate limit logic (check `src/trading_bot/error_handling/retry.py`)
- **Pattern**: Existing rate limit handling in retry decorator
- **From**: plan.md [SECURITY]

---

## Phase 3.7: Documentation & Validation (T037-T040)

### T037 [P] Add health check usage examples to module docstring
- **File**: `src/trading_bot/health/session_health.py`
- **Changes**:
  - Add module-level docstring with:
    - Overview of health check functionality
    - Usage example (initialization, start/stop periodic checks)
    - Measurement query examples (bash scripts from spec.md)
  - Add code examples for common patterns
- **Pattern**: `src/trading_bot/logging/structured_logger.py` (comprehensive module docs)
- **From**: spec.md Measurement Plan

### T038 [P] Run test coverage and verify ≥90% coverage
- **Command**: `pytest --cov=src.trading_bot.health --cov-report=term-missing --cov-report=html`
- **Target**: ≥90% line coverage per NFR-004
- **Action**: Identify uncovered lines, add missing tests if needed
- **Pattern**: Coverage validation workflow
- **From**: spec.md NFR-004, plan.md [TESTING STRATEGY]

### T039 [P] Run mypy type checker and fix type errors
- **Command**: `mypy src/trading_bot/health/`
- **Target**: Zero type errors
- **Action**: Fix any type hint issues, ensure all parameters/returns typed
- **Requirements**: NFR-007 (type hints required)
- **Pattern**: Type checking workflow
- **From**: spec.md NFR-007

### T040 [P] Document rollback procedure in specs/health-check/NOTES.md
- **File**: `specs/health-check/NOTES.md`
- **Content**:
  - Rollback commands: `git revert <commit-sha>`
  - Feature can be disabled by commenting out health check calls in bot.py
  - No special rollback considerations (additive feature, no persistence)
  - Standard 3-command rollback (git revert, restart bot, verify logs)
- **Pattern**: Rollback documentation template
- **From**: plan.md [DEPLOYMENT ACCEPTANCE]

---

## Summary

**Total Tasks**: 40
- Setup: 4 tasks (T001-T004)
- RED (Tests): 16 tasks (T005-T016, T031, T033, T035)
- GREEN (Implementation): 15 tasks (T017-T024, T032, T034, T036)
- REFACTOR: 3 tasks (T025-T027)
- Integration: 5 tasks (T028-T030, T037)
- Documentation/Validation: 4 tasks (T037-T040)

**Parallel Execution Opportunities**:
- T001, T002, T003, T004 can run in parallel (independent setup)
- All RED tests (T005-T016) can be written in parallel
- T028, T029, T030 can be implemented in parallel (different sections of bot.py)
- T037, T038, T039, T040 can run in parallel (independent validation tasks)

**TDD Coverage**:
- 16 RED phase tasks (write failing tests)
- 15 GREEN phase tasks (implement to pass tests)
- 3 REFACTOR tasks (improve code without breaking tests)
- Every behavior has test-first coverage

**Dependencies**:
- GREEN tasks depend on corresponding RED tasks (marked with GREEN→TNN notation)
- Integration tasks (T028-T030) depend on implementation tasks (T017-T024) completing
- Validation tasks (T037-T040) run after all implementation complete

**Reuse Emphasis**:
- 7 existing components reused (no duplication)
- 3 new components created (minimal new code)
- All patterns follow existing codebase conventions
