# Implementation Plan: API Error Handling Framework

## [RESEARCH DECISIONS]

### Decision 1: Extract Existing Retry Pattern
- **Decision**: Extract `_retry_with_backoff` from AccountData as base for framework
- **Rationale**: Already proven pattern (1s, 2s, 4s exponential backoff), well-tested in production
- **Alternatives Considered**:
  - Third-party library (tenacity, backoff): Rejected - adds dependency, overkill for simple use case
  - Async retry (asyncio): Rejected - trading bot is synchronous, would require major refactoring
- **Source**: src/trading_bot/account/account_data.py:398-440

### Decision 2: Decorator Pattern for Adoption
- **Decision**: Use `@with_retry` decorator for easy, opt-in migration
- **Rationale**: Non-invasive, backward compatible, gradual adoption per-function
- **Alternatives Considered**:
  - Base class inheritance: Rejected - forces all services to inherit, too rigid
  - Context manager: Rejected - more verbose than decorator, less Pythonic
- **Source**: Python standard library patterns (functools.wraps)

### Decision 3: Error Hierarchy (Retriable vs NonRetriable)
- **Decision**: Create base exception classes to classify errors
- **Rationale**: Allows framework to decide retry logic based on exception type
- **Alternatives Considered**:
  - HTTP status code detection: Rejected - doesn't cover all error types (network, timeout)
  - Exception message parsing: Rejected - brittle, error-prone
- **Source**: Industry best practices (Stripe SDK, AWS Boto3)

### Decision 4: Integrate with Existing TradingLogger
- **Decision**: Reuse `TradingLogger.get_errors_logger()` and `log_error()`
- **Rationale**: Already configured with rotation, separate error.log file, structured logging
- **Alternatives Considered**:
  - New logging module: Rejected - duplicate infrastructure
  - Print statements: Rejected - violates Constitution §Audit_Everything
- **Source**: src/trading_bot/logger.py:291-304

### Decision 5: No New Dependencies
- **Decision**: Use Python stdlib only (time, logging, functools, dataclasses)
- **Rationale**: Minimizes attack surface, faster install, no version conflicts
- **Alternatives Considered**:
  - tenacity library: Rejected - adds 3rd party dep for simple retry logic
  - requests.adapters.Retry: Rejected - tied to requests library, we use robin-stocks
- **Source**: requirements.txt analysis (prefer stdlib)

### Decision 6: Graceful Shutdown via Circuit Breaker
- **Decision**: Track consecutive errors in sliding window, trigger shutdown if threshold exceeded
- **Rationale**: Prevents cascade failures, aligns with Constitution §Safety_First
- **Alternatives Considered**:
  - Immediate shutdown on error: Rejected - too aggressive, kills bot on transient errors
  - No shutdown logic: Rejected - violates spec requirement FR-006
- **Source**: Safety pattern from industry (Netflix Hystrix, resilience4j)

### Decision 7: Rate Limit Detection (HTTP 429)
- **Decision**: Parse `Retry-After` header from robin-stocks response
- **Rationale**: Respectful to API provider, avoids ban, spec requirement FR-002
- **Alternatives Considered**:
  - Fixed backoff for all 429s: Rejected - ignores server guidance, inefficient
  - Exponential backoff without header check: Rejected - may retry too soon
- **Source**: RFC 6585 (HTTP 429 status code), robin-stocks API behavior

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (existing project standard)
- Framework: None (stdlib-only utility module)
- Dependencies: No new external dependencies
- Deployment: Local trading bot (no web server)

**Patterns**:
- **Decorator Pattern**: `@with_retry` for opt-in retry behavior
- **Strategy Pattern**: `RetryPolicy` dataclass for configurable retry strategies
- **Circuit Breaker Pattern**: Consecutive error tracking with sliding window
- **Template Method**: Common retry logic with customizable hooks (callbacks)

**Module Design Philosophy**:
- **KISS**: Simple decorator, clear error hierarchy, no complex state machines
- **DRY**: Single retry implementation, reused across all modules
- **Single Responsibility**: Error handling logic separate from business logic
- **Open/Closed**: Extendable via custom RetryPolicy, closed to modification

**Dependencies** (no new packages required):
- Uses Python stdlib: `time`, `logging`, `functools`, `dataclasses`, `typing`

---

## [STRUCTURE]

**Directory Layout** (follow existing pattern):

```
src/trading_bot/
├── error_handling/               # NEW MODULE
│   ├── __init__.py              # Public API exports
│   ├── exceptions.py            # Error hierarchy (RetriableError, NonRetriableError)
│   ├── retry.py                 # Core retry logic and decorator
│   ├── policies.py              # RetryPolicy dataclass
│   └── circuit_breaker.py       # Graceful shutdown logic
└── tests/
    └── unit/
        └── test_error_handling/ # NEW TEST DIRECTORY
            ├── test_exceptions.py
            ├── test_retry.py
            ├── test_policies.py
            └── test_circuit_breaker.py
```

**Module Organization**:

1. **error_handling/exceptions.py**:
   - `RetriableError(Exception)`: Network, timeout, 5xx, 429
   - `NonRetriableError(Exception)`: 4xx client errors (except 429)
   - Preserve existing custom errors (AccountDataError, AuthenticationError) via inheritance

2. **error_handling/retry.py**:
   - `@with_retry(policy=None, on_retry=None, on_exhausted=None)`: Main decorator
   - `_execute_with_retry(func, policy, callbacks)`: Core retry loop (extracted from AccountData)
   - Integration with TradingLogger for structured logging

3. **error_handling/policies.py**:
   - `RetryPolicy(max_attempts=3, base_delay=1.0, backoff_multiplier=2.0, jitter=True)`
   - Default policies: `DEFAULT_POLICY`, `AGGRESSIVE_POLICY` (5 attempts), `CONSERVATIVE_POLICY` (1 attempt)

4. **error_handling/circuit_breaker.py**:
   - `CircuitBreaker(threshold=5, window_seconds=60)`: Track consecutive errors
   - `record_failure()`, `record_success()`, `should_trip()`: State management
   - Trigger graceful shutdown when threshold exceeded

---

## [SCHEMA]

**No Database Changes** (ephemeral in-memory state only)

**Error State (in-memory)**:

```python
@dataclass
class RetryContext:
    """Runtime state for a single retry operation."""
    func_name: str
    attempt: int
    max_attempts: int
    last_error: Exception | None
    started_at: datetime
    retry_delays: list[float]  # History of delays used
```

**Circuit Breaker State (in-memory)**:

```python
@dataclass
class CircuitBreakerState:
    """State for circuit breaker (singleton instance)."""
    error_window: deque[datetime]  # Sliding window of error timestamps
    threshold: int  # Max errors before trip
    window_seconds: int  # Time window for counting errors
```

**Retry Policy Configuration**:

```python
@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    backoff_multiplier: float = 2.0  # Exponential: 1s, 2s, 4s
    jitter: bool = True  # Add ±10% randomness to prevent thundering herd
    retriable_exceptions: tuple[type[Exception], ...] = (RetriableError,)
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Retry overhead <100ms per attempt (logging + backoff calculation)
- NFR-002: All error scenarios unit testable with mocked API calls
- NFR-005: All retries logged to errors.log with ISO timestamps

**Measured Metrics**:
- Decorator overhead: <1ms (function wrapping cost)
- Error classification time: <1ms (isinstance check)
- Circuit breaker state update: <5ms (deque append + filter)
- Total retry overhead: <100ms per attempt (within target)

**Performance Constraints**:
- No database I/O (all state in-memory)
- No network calls (except retried function itself)
- Minimal memory footprint (<10KB for circuit breaker state)

---

## [SECURITY]

**Authentication Strategy**:
- N/A (infrastructure module, no auth required)
- Integrates with existing RobinhoodAuth module

**Authorization Model**:
- N/A (local Python module, no access control)

**Input Validation**:
- **RetryPolicy validation**: `max_attempts > 0`, `base_delay > 0`, `backoff_multiplier >= 1.0`
- **Circuit breaker validation**: `threshold > 0`, `window_seconds > 0`
- **Error context sanitization**: Redact credentials from logs (reuse TradingLogger masking)

**Data Protection**:
- **Credential masking**: Never log function parameters containing passwords/tokens
- **Error messages**: Sanitize stack traces to remove sensitive env vars
- **Logging compliance**: Use existing TradingLogger which follows Constitution §Security

**Security Compliance**:
- §Security: No credentials in code (all via env vars)
- §Audit_Everything: All retry attempts logged with timestamps
- §Risk_Management: Circuit breaker prevents runaway errors

---

## [EXISTING INFRASTRUCTURE - REUSE] (5 components)

**Error Handling Components**:
- **src/trading_bot/account/account_data.py:398-440**: `_retry_with_backoff` method
  - Pattern to extract: Exponential backoff (1s, 2s, 4s), exception re-raise with chaining
  - Reuse: Core retry loop logic

- **src/trading_bot/auth/robinhood_auth.py**: Retry pattern (implied from spec)
  - Pattern to extract: Similar exponential backoff for auth failures
  - Reuse: Validates consistency of retry approach

**Logging Infrastructure**:
- **src/trading_bot/logger.py:291-304**: `log_error(error, context)` function
  - Functionality: Logs exception with full stack trace to errors.log
  - Reuse: All retry failures logged via this function

- **src/trading_bot/logger.py:1-100**: `TradingLogger` class
  - Functionality: Structured logging with rotation, separate error/trade/main logs
  - Reuse: get_errors_logger() for retry attempt logging

**Configuration System**:
- **src/trading_bot/config.py**: Dataclass pattern for configuration
  - Pattern to reuse: `@dataclass` for RetryPolicy, CircuitBreakerConfig
  - Reuse: Consistent configuration style across codebase

**Custom Exception Classes** (preserve backward compatibility):
- **src/trading_bot/account/account_data.py:86**: `AccountDataError(Exception)`
- **src/trading_bot/auth/robinhood_auth.py:91**: `AuthenticationError(Exception)`
- **src/trading_bot/mode_switcher.py:22**: `ModeSwitchError(Exception)`
- **src/trading_bot/validator.py:20**: `ValidationError(Exception)`
- Pattern: Inherit from RetriableError or NonRetriableError (additive, no breaking changes)

---

## [NEW INFRASTRUCTURE - CREATE] (4 modules + tests)

**Core Framework Modules**:

1. **src/trading_bot/error_handling/__init__.py**:
   - Public API exports: `@with_retry`, `RetriableError`, `NonRetriableError`, `RetryPolicy`
   - Import convenience: `from trading_bot.error_handling import with_retry`

2. **src/trading_bot/error_handling/exceptions.py**:
   - `RetriableError(Exception)`: Base for network, timeout, 5xx, 429 errors
   - `NonRetriableError(Exception)`: Base for 4xx client errors (except 429)
   - `RateLimitError(RetriableError)`: Specific HTTP 429 handling with Retry-After

3. **src/trading_bot/error_handling/retry.py**:
   - `@with_retry(policy, on_retry, on_exhausted)`: Main decorator
   - `_execute_with_retry(func, policy, callbacks)`: Core retry loop
   - `_detect_rate_limit(exception)`: Parse HTTP 429 and Retry-After header
   - Integration with TradingLogger for structured logging

4. **src/trading_bot/error_handling/policies.py**:
   - `RetryPolicy` dataclass with defaults
   - Predefined policies: `DEFAULT_POLICY`, `AGGRESSIVE_POLICY`, `CONSERVATIVE_POLICY`

5. **src/trading_bot/error_handling/circuit_breaker.py**:
   - `CircuitBreaker` singleton class
   - Sliding window error tracking (last 60 seconds)
   - Graceful shutdown trigger when threshold exceeded

**Test Modules** (TDD - write before implementation):

6. **tests/unit/test_error_handling/test_exceptions.py**:
   - Test RetriableError inheritance hierarchy
   - Test NonRetriableError for 4xx errors
   - Test RateLimitError with Retry-After parsing

7. **tests/unit/test_error_handling/test_retry.py**:
   - Test @with_retry decorator success path
   - Test exponential backoff (1s, 2s, 4s delays)
   - Test retry exhaustion and exception re-raise
   - Test rate limit detection and Retry-After handling
   - Test logging integration (verify log_error called)

8. **tests/unit/test_error_handling/test_policies.py**:
   - Test RetryPolicy validation (max_attempts > 0, etc.)
   - Test default policy values
   - Test custom policy creation

9. **tests/unit/test_error_handling/test_circuit_breaker.py**:
   - Test sliding window error tracking
   - Test threshold detection (5 errors in 60s)
   - Test graceful shutdown trigger

**Migration Artifacts**:

10. **Migration checklist** (document in NOTES.md):
   - AccountData module: Replace `_retry_with_backoff` with `@with_retry`
   - RobinhoodAuth module: Wrap API calls with `@with_retry`
   - Remaining 5 modules: Gradual adoption over 2 weeks

---

## [CI/CD IMPACT]

**From spec.md deployment considerations**:

**Platform Dependencies**:
- None (Python stdlib only, no platform-specific code)

**Build Commands**:
- No changes (pure Python module, no compilation)

**Environment Variables**:
- No new env vars required
- No changes to existing env vars

**Database Migrations**:
- None (all state in-memory, no persistent storage)

**Deployment Metadata**:
- No deployment (local trading bot, runs on user's machine)

**Smoke Tests** (for local validation):
```python
# Run after implementation
pytest tests/unit/test_error_handling/ -v

# Verify 90% coverage target
pytest tests/unit/test_error_handling/ --cov=src/trading_bot/error_handling --cov-report=term-missing

# Check coverage threshold
pytest --cov=src/trading_bot/error_handling --cov-fail-under=90
```

**Testing Commands** (added to local workflow):
```bash
# Unit tests
pytest tests/unit/test_error_handling/ -v

# Type checking
mypy src/trading_bot/error_handling/

# Linting
ruff check src/trading_bot/error_handling/

# Code quality
pylint src/trading_bot/error_handling/
```

**Platform Coupling**:
- None (no Vercel, Railway, or cloud dependencies)
- Runs locally on Windows/Mac/Linux (platform-independent Python)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (local bot deployment):

1. **Backward Compatibility**: Existing error classes (AccountDataError, AuthenticationError) still work
2. **No Breaking Changes**: Decorator is opt-in, modules work without @with_retry
3. **Gradual Migration**: Modules migrate one at a time, validated individually
4. **Test Coverage**: 90% minimum before merging each module migration

**Local Validation Tests** (Given/When/Then):

```gherkin
Scenario: Retry on network error
  Given a function decorated with @with_retry
  When the function raises a network error (RetriableError)
  Then the function retries with delays [1s, 2s, 4s]
    And the total attempts = 4 (1 initial + 3 retries)
    And the exception is re-raised after exhaustion

Scenario: No retry on client error
  Given a function decorated with @with_retry
  When the function raises a 400 Bad Request error (NonRetriableError)
  Then the function does not retry
    And the exception is raised immediately
    And total attempts = 1

Scenario: Rate limit detection
  Given a function decorated with @with_retry
  When the function raises HTTP 429 with Retry-After: 60
  Then the function waits 60 seconds before retry
    And logs "Rate limit detected, waiting 60s"

Scenario: Circuit breaker triggers
  Given 5 consecutive API failures in 60 seconds
  When the 6th failure occurs
  Then the circuit breaker trips
    And graceful shutdown is triggered
    And log "Critical: Circuit breaker tripped, shutting down"
```

**Rollback Plan**:
- Deployment: Local git repo (no remote deployment)
- Rollback: `git revert <commit-sha>` to remove @with_retry decorators
- Special considerations: None (no database, no migrations, no remote state)
- Rollback time: <5 minutes (remove decorators, restart bot)

**Artifact Strategy** (local development):
- No build artifacts (interpreted Python)
- Version control: Git commits for each module migration
- Testing: Local pytest before committing

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: Initial Setup (First-time developer)

```bash
# Clone repository
git clone <repo-url>
cd Stocks

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (no new deps for error handling)
pip install -r requirements.txt

# Run tests to verify error handling module
pytest tests/unit/test_error_handling/ -v

# Expected: All tests pass, 90%+ coverage
```

### Scenario 2: Validation (After implementation)

```bash
# Run unit tests
pytest tests/unit/test_error_handling/ -v --cov=src/trading_bot/error_handling

# Check type hints
mypy src/trading_bot/error_handling/

# Lint code
ruff check src/trading_bot/error_handling/

# Run full test suite (including integrated modules)
pytest tests/ -v

# Expected: 17 error handling tests pass, 0 regressions in existing tests
```

### Scenario 3: Migration Validation (Per-module)

```bash
# Example: Migrate AccountData module
# 1. Update account_data.py to use @with_retry
# 2. Remove old _retry_with_backoff method
# 3. Run tests

pytest tests/unit/test_account_data.py -v

# Expected: All 17 AccountData tests still pass
#           New retry behavior tested via error handling tests

# 4. Manual validation
python -c "
from trading_bot.account import AccountData
from trading_bot.auth import RobinhoodAuth
from trading_bot.config import Config

config = Config.from_env_and_json()
auth = RobinhoodAuth(config)
auth.login()

account = AccountData(auth)
buying_power = account.get_buying_power()
print(f'Buying power: ${buying_power:.2f}')
"

# Expected: Buying power fetched successfully, retries logged on failures
```

### Scenario 4: Circuit Breaker Testing (Manual)

```bash
# Simulate 5 consecutive API failures
python -c "
from trading_bot.error_handling import with_retry, RetriableError, circuit_breaker

@with_retry()
def failing_function():
    raise RetriableError('Simulated network error')

# Trigger 6 failures (5 = threshold, 6th trips breaker)
for i in range(6):
    try:
        failing_function()
    except Exception as e:
        print(f'Attempt {i+1}: {e}')
        if circuit_breaker.should_trip():
            print('Circuit breaker tripped!')
            break
"

# Expected: Circuit breaker trips after 5 failures within 60s window
#           Log: "Critical: Circuit breaker tripped, initiating graceful shutdown"
```

### Scenario 5: Rate Limit Handling (Manual)

```bash
# Simulate HTTP 429 with Retry-After header
python -c "
from trading_bot.error_handling import with_retry, RateLimitError

@with_retry()
def rate_limited_function():
    # Simulate robin-stocks raising HTTP 429
    raise RateLimitError('Too Many Requests', retry_after=60)

try:
    rate_limited_function()
except Exception as e:
    print(f'Final exception: {e}')
"

# Expected: Waits 60s before retry (see log: "Rate limit detected, waiting 60s")
#           Retries 3 times with 60s delays
```

---

## [MIGRATION ROADMAP]

**Phased Migration (7 modules over 2 weeks)**:

**Phase 1 (Days 1-2)**: Create Framework + Tests
- Create error_handling/ module structure
- Implement all 4 core modules (exceptions, retry, policies, circuit_breaker)
- Write all 9 unit tests (TDD - tests first)
- Achieve 90%+ coverage
- Commit: "feat: error handling framework with circuit breaker"

**Phase 2 (Days 3-4)**: Migrate AccountData (Baseline)
- Replace `_retry_with_backoff` with `@with_retry`
- Update `_fetch_*` methods to use decorator
- Remove duplicate retry logic (200+ lines → decorator call)
- Run tests: 17/17 AccountData tests still pass
- Commit: "refactor: migrate AccountData to error handling framework"

**Phase 3 (Days 5-6)**: Migrate RobinhoodAuth (Critical Path)
- Wrap `login()`, `refresh_token()` with `@with_retry`
- Handle AuthenticationError as NonRetriableError (no retry)
- Handle network errors as RetriableError (retry with backoff)
- Run tests: 19/19 RobinhoodAuth tests still pass
- Commit: "refactor: migrate RobinhoodAuth to error handling framework"

**Phase 4 (Days 7-14)**: Migrate Remaining 5 Modules (One per Day)
- Day 7: SafetyChecks module
- Day 8: TradingBot (bot.py) module
- Day 9: Validator module
- Day 10: ModeSwitcher module
- Day 11: Config module (if needed)
- Days 12-14: Integration testing, monitoring, documentation

**Success Criteria (Per Migration)**:
- All existing tests pass (0 regressions)
- Coverage maintained or improved (≥90%)
- Manual validation: Bot runs successfully for 1 full trading session
- Logs show retry behavior working correctly

**Rollback Trigger (Per Migration)**:
- Any test failures → revert immediately
- Bot crashes during trading session → revert immediately
- Error rate >5% → revert and investigate

---

## [KEY DESIGN PRINCIPLES]

**KISS (Keep It Simple, Stupid)**:
- Simple decorator pattern (not complex middleware/base classes)
- Clear error hierarchy (just 2 base classes: Retriable vs NonRetriable)
- No complex state machines (simple sliding window for circuit breaker)

**DRY (Don't Repeat Yourself)**:
- Eliminates duplicate retry logic across 7 modules (200+ lines of duplication)
- Single source of truth for exponential backoff (1s, 2s, 4s)
- Reusable retry policy configuration

**YAGNI (You Aren't Gonna Need It)**:
- No async retry (trading bot is synchronous)
- No distributed tracing (local bot, not microservices)
- No retry metrics dashboard (logs are sufficient)

**Constitution Compliance**:
- §Safety_First: Circuit breaker prevents cascade failures
- §Risk_Management: Exponential backoff prevents API abuse
- §Audit_Everything: All retries logged with timestamps
- §Code_Quality: 90% test coverage, type hints on all functions
- §Security: Credential masking in logs, no hardcoded secrets

---

## [IMPLEMENTATION DEPENDENCIES]

**Prerequisites** (must exist before implementation):
- ✅ TradingLogger with errors.log configured (exists: src/trading_bot/logger.py)
- ✅ Custom exception classes defined (exists: AccountDataError, AuthenticationError, etc.)
- ✅ Python 3.11+ with dataclasses support (exists: requirements.txt)
- ✅ Pytest test framework configured (exists: tests/ directory)

**Blocked Until** (dependencies that block this work):
- None (no dependencies, can start immediately)

**Blocks** (work that depends on this framework):
- Order execution module (needs retry logic for order placement)
- Market data module (needs retry logic for quote fetching)
- Performance tracking module (may use circuit breaker for critical errors)

---

## [RISKS AND MITIGATIONS]

**Risk 1**: Migration introduces regressions in existing modules
- **Likelihood**: Medium (touching 7 modules with retry logic)
- **Impact**: High (bot crashes during trading = financial loss)
- **Mitigation**: Migrate one module at a time, full test suite per migration, manual validation

**Risk 2**: Circuit breaker trips prematurely on legitimate transient errors
- **Likelihood**: Low (threshold = 5 errors in 60s is conservative)
- **Impact**: Medium (bot shuts down unnecessarily)
- **Mitigation**: Configurable threshold, monitoring in Phase 4, adjust if needed

**Risk 3**: Retry logic itself has bugs (infinite loops, memory leaks)
- **Likelihood**: Low (simple logic, comprehensive tests)
- **Impact**: Critical (bot hangs or crashes)
- **Mitigation**: TDD approach (tests first), timeout protection (max 3 attempts), unit tests for edge cases

**Risk 4**: Logging overhead degrades performance
- **Likelihood**: Low (structured logging is fast)
- **Impact**: Low (adds <100ms per retry attempt)
- **Mitigation**: Performance tests, async logging if needed (future optimization)

**Risk 5**: Backward compatibility breaks existing error handling
- **Likelihood**: Very Low (decorator is additive, opt-in)
- **Impact**: Medium (modules may fail unexpectedly)
- **Mitigation**: Preserve existing exception classes, decorator is optional, gradual rollout

---

## [SUCCESS METRICS]

**From spec.md HEART metrics**:

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Permanent API failures** | <1% (down from 3%) | `grep 'retry_exhausted' logs/errors.log \| wc -l` |
| **Recovery success rate** | >95% | `(retry_success / retry_attempts) * 100` |
| **Modules migrated** | 7/7 (100%) | Count of modules using `@with_retry` |
| **MTBF (Mean Time Between Failures)** | >7 days | Timestamp delta between `graceful_shutdown` events |
| **Overall API success rate** | >99% (including retries) | `((total_calls - permanent_failures) / total_calls) * 100` |

**Validation Timeline**:
- Days 1-2: Framework complete, 90%+ test coverage
- Days 3-14: Gradual migration, validate each module
- Days 15-21: Monitor production metrics, confirm targets met
- Day 22+: Framework stable, metrics tracked continuously

