# Implementation Plan: Market Data and Trading Hours Module

## [RESEARCH DECISIONS]

### Decision: Reuse Error Handling Framework
- **Decision**: Use existing error-handling-framework (retry, circuit breaker, exceptions)
- **Rationale**: Framework provides exponential backoff, rate limit detection, and retriable error patterns - exactly what market data API calls need. Prevents duplication of retry logic.
- **Alternatives**: Implement custom retry logic (rejected - violates DRY, duplicates T034-T037)
- **Source**: src/trading_bot/error_handling/retry.py, src/trading_bot/error_handling/exceptions.py

### Decision: Reuse Logging Infrastructure
- **Rationale**: Existing TradingLogger provides UTC timestamps, audit trail separation, and Constitution compliance (Audit_Everything). No need to duplicate logging setup.
- **Alternatives**: Create custom logging for market data (rejected - violates Constitution §Audit_Everything consistency)
- **Source**: src/trading_bot/logger.py

### Decision: Reuse Time Utilities for Trading Hours
- **Decision**: Extend existing time_utils.py instead of creating duplicate timezone logic
- **Rationale**: time_utils.py already implements 7am-10am EST trading hours checking with is_trading_hours(). Satisfies FR-004 requirement without duplication.
- **Alternatives**: Create TradingHoursValidator class (rejected - unnecessary abstraction, duplicates existing utility)
- **Source**: src/trading_bot/utils/time_utils.py (lines 14-35)

### Decision: Reuse RobinhoodAuth Session Management
- **Decision**: Accept RobinhoodAuth instance in MarketDataService constructor
- **Rationale**: Authentication module handles session caching, MFA, token refresh. Market data service should only consume authenticated session, not manage it.
- **Alternatives**: Embed auth in market data service (rejected - violates separation of concerns, duplicates T014-T023)
- **Source**: src/trading_bot/auth/robinhood_auth.py

### Decision: pytz Already Available
- **Decision**: No new dependency needed for timezone handling
- **Rationale**: pytz==2024.1 already in requirements.txt (line 36), used by time_utils.py
- **Alternatives**: Add redundant pytz dependency (rejected - already satisfied)
- **Source**: requirements.txt line 36, time_utils.py imports

### Decision: Create Custom Market Data Exceptions
- **Decision**: Define DataValidationError and TradingHoursError as NonRetriableError subclasses
- **Rationale**: Data validation failures should NOT retry (bad data won't become good). Trading hours violations should fail fast. Use existing error hierarchy from error-handling-framework.
- **Alternatives**: Use generic exceptions (rejected - loses type safety and retry decision logic)
- **Source**: src/trading_bot/error_handling/exceptions.py (NonRetriableError base class)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11+
- API Client: robin-stocks==3.0.5 (existing)
- Data Processing: pandas==2.1.4 (existing)
- Timezone: pytz==2024.1 (existing)
- Error Handling: Reuse error-handling-framework (retry.py, circuit_breaker.py)
- Logging: Reuse TradingLogger (logger.py)
- Testing: pytest==7.4.4, pytest-mock==3.12.0 (existing)

**Patterns**:
- Service pattern: MarketDataService as stateless API wrapper
- Dependency injection: Accept RobinhoodAuth instance in constructor
- Decorator pattern: Use @with_retry for rate limit resilience
- Dataclass pattern: Quote, MarketStatus, MarketDataConfig as immutable data models
- Fail-fast validation: All data validated before returning, raise NonRetriableError on failure

**Dependencies** (new packages required):
- None - all dependencies satisfied by existing requirements.txt

**REUSE Opportunities** (6 components):
- REUSE: src/trading_bot/error_handling/retry.py - @with_retry decorator for exponential backoff
- REUSE: src/trading_bot/error_handling/exceptions.py - RetriableError, NonRetriableError, RateLimitError
- REUSE: src/trading_bot/error_handling/circuit_breaker.py - Circuit breaker for fault isolation
- REUSE: src/trading_bot/logger.py - TradingLogger for audit trail
- REUSE: src/trading_bot/utils/time_utils.py - is_trading_hours() for 7am-10am EST enforcement
- REUSE: src/trading_bot/auth/robinhood_auth.py - RobinhoodAuth for authenticated sessions

---

## [STRUCTURE]

**Directory Layout**:

```
src/trading_bot/
├── market_data/
│   ├── __init__.py
│   ├── market_data_service.py  # Main service class
│   ├── data_models.py          # Quote, MarketStatus dataclasses
│   ├── exceptions.py           # DataValidationError, TradingHoursError
│   └── validators.py           # Data validation logic
└── utils/
    └── time_utils.py           # EXTEND: Add trading hours validation helpers

tests/
├── unit/
│   └── test_market_data/
│       ├── __init__.py
│       ├── test_market_data_service.py
│       ├── test_data_models.py
│       ├── test_validators.py
│       └── test_exceptions.py
└── integration/
    └── test_market_data_integration.py

specs/market-data-module/
├── contracts/
│   └── api.yaml                # OpenAPI spec for robin_stocks wrapper
├── spec.md
├── plan.md (this file)
└── error-log.md
```

**Module Organization**:
- market_data_service.py: Main API wrapper, orchestrates quote/historical data fetching with retry logic
- data_models.py: Immutable dataclasses (Quote, MarketStatus, MarketDataConfig)
- validators.py: Data validation functions (price > 0, timestamp UTC, completeness checks)
- exceptions.py: Custom exceptions (DataValidationError, TradingHoursError)
- time_utils.py: Extended to add validate_trade_time() helper

---

## [SCHEMA]

**No Database Tables** (stateless service - all data fetched on-demand)

**API Schemas** (robin_stocks wrapper):

```yaml
# contracts/api.yaml - OpenAPI spec for MarketDataService

Quote:
  type: object
  required: [symbol, current_price, timestamp_utc, market_state]
  properties:
    symbol:
      type: string
      example: "AAPL"
    current_price:
      type: number
      format: decimal
      example: 150.25
    timestamp_utc:
      type: string
      format: date-time
      example: "2025-10-08T18:30:00Z"
    market_state:
      type: string
      enum: [regular, pre, post, closed]

MarketStatus:
  type: object
  required: [is_open, next_open, next_close]
  properties:
    is_open:
      type: boolean
    next_open:
      type: string
      format: date-time
      description: "UTC timestamp"
    next_close:
      type: string
      format: date-time
      description: "UTC timestamp"

HistoricalDataFrame:
  description: "pandas DataFrame with OHLCV columns"
  columns:
    - date (datetime64[ns, UTC])
    - open (float64)
    - high (float64)
    - low (float64)
    - close (float64)
    - volume (int64)
```

**State Shape** (service configuration):
```python
@dataclass
class MarketDataConfig:
    """Configuration for market data service."""
    rate_limit_retries: int = 3
    rate_limit_backoff_base: float = 1.0  # seconds
    quote_staleness_threshold: int = 300  # 5 minutes in seconds
    trading_window_start: int = 7  # 7am EST
    trading_window_end: int = 10  # 10am EST
    trading_timezone: str = "America/New_York"
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-004: Real-time quote fetch <2 seconds (95th percentile)
- NFR-004: Historical data fetch <10 seconds (95th percentile)
- NFR-004: Market hours check <1 second (95th percentile)
- NFR-004: Trading hours validation <100ms (99th percentile)

**Service-Level Targets**:
- Retry overhead: <100ms per attempt (exponential backoff delays excluded)
- Data validation overhead: <50ms per quote validation
- DataFrame validation overhead: <500ms for 252 rows (1 year daily data)

**No Lighthouse Targets** (backend API module only)

---

## [SECURITY]

**Authentication Strategy**:
- Use existing RobinhoodAuth service (dependency injection)
- No credentials stored in market data module
- Session management delegated to RobinhoodAuth

**Authorization Model**:
- N/A (single-user trading bot, no multi-tenancy)

**Input Validation**:
- Symbol validation: Reject empty strings, validate format (uppercase letters only)
- Interval/span validation: Whitelist allowed values ("5minute", "day", "week", etc.)
- Price validation: Reject prices <= 0, reject NaN/Inf
- Timestamp validation: Require UTC timezone, reject timestamps >5min stale for quotes
- Volume validation: Reject negative volumes

**Rate Limiting**:
- Use @with_retry decorator with RateLimitError detection
- Exponential backoff: 1s, 2s, 4s delays (max 3 retries)
- Circuit breaker: Use existing circuit_breaker.py to prevent cascading failures

**Data Protection**:
- No PII handling (only market data - public information)
- No encryption needed (data is public)
- Logs: Avoid logging API credentials (handled by RobinhoodAuth)

---

## [EXISTING INFRASTRUCTURE - REUSE] (6 components)

**Error Handling**:
- src/trading_bot/error_handling/retry.py: @with_retry decorator for exponential backoff
- src/trading_bot/error_handling/exceptions.py: RetriableError, NonRetriableError, RateLimitError
- src/trading_bot/error_handling/circuit_breaker.py: Circuit breaker for fault isolation
- src/trading_bot/error_handling/policies.py: DEFAULT_POLICY (3 retries, 1s base delay)

**Infrastructure**:
- src/trading_bot/logger.py: TradingLogger.get_logger() for audit trail
- src/trading_bot/utils/time_utils.py: is_trading_hours() for 7am-10am EST enforcement
- src/trading_bot/auth/robinhood_auth.py: RobinhoodAuth for authenticated sessions
- src/trading_bot/config.py: Config.trading_timezone for timezone consistency

**Testing Patterns**:
- tests/unit/test_error_handling/: Patterns for testing retry logic with mocks
- tests/unit/test_robinhood_auth.py: Patterns for mocking robin_stocks API calls
- tests/integration/test_auth_integration.py: Patterns for integration testing with real auth

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

**Backend Services**:
- src/trading_bot/market_data/market_data_service.py: Main service class
  - get_quote(symbol: str) -> Quote
  - get_quotes_batch(symbols: List[str]) -> Dict[str, Quote]
  - get_historical_data(symbol, interval, span) -> pd.DataFrame
  - is_market_open() -> MarketStatus

**Data Models**:
- src/trading_bot/market_data/data_models.py:
  - Quote dataclass (symbol, current_price, timestamp_utc, market_state)
  - MarketStatus dataclass (is_open, next_open, next_close)
  - MarketDataConfig dataclass (rate limits, staleness threshold, trading window)

**Validation**:
- src/trading_bot/market_data/validators.py:
  - validate_quote(data: Dict) -> None (raises DataValidationError)
  - validate_historical_data(df: pd.DataFrame) -> None (raises DataValidationError)
  - validate_price(price: float) -> None
  - validate_timestamp(timestamp: datetime) -> None
  - check_data_completeness(df: pd.DataFrame) -> None

**Exceptions**:
- src/trading_bot/market_data/exceptions.py:
  - DataValidationError(NonRetriableError): Failed validation (bad data)
  - TradingHoursError(NonRetriableError): Trade outside 7am-10am EST window

**Tests** (6 new test modules):
- tests/unit/test_market_data/test_market_data_service.py
- tests/unit/test_market_data/test_data_models.py
- tests/unit/test_market_data/test_validators.py
- tests/unit/test_market_data/test_exceptions.py
- tests/integration/test_market_data_integration.py

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: N/A (local-only trading bot, no web deployment)
- Env vars: No new environment variables required (uses existing ROBINHOOD_* credentials)
- Breaking changes: No (new module, additive only)
- Migration: No (stateless service, no database)

**Build Commands**:
- No changes (pure Python module, no build step)

**Environment Variables**:
- No new variables required
- Reuses existing: ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, ROBINHOOD_MFA_SECRET

**Database Migrations**:
- No (stateless service)

**Smoke Tests** (for local validation):
- Manual test: Fetch AAPL quote (should return Quote dataclass)
- Manual test: Fetch 90-day historical data (should return 252-row DataFrame)
- Manual test: Check market hours (should return MarketStatus)
- Manual test: Validate trading hours at 8am EST (should allow trade)
- Manual test: Validate trading hours at 11am EST (should block trade with TradingHoursError)

**Platform Coupling**:
- None (pure Python module)
- Dependencies: robin-stocks==3.0.5, pandas==2.1.4, pytz==2024.1 (all existing)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants**:
- All market data validated before use (prices > 0, timestamps UTC)
- Trading hours enforced (7am-10am EST) - trades blocked outside window
- Rate limits respected (exponential backoff, max 3 retries)
- No unvalidated data returned to bot (fail-safe error handling)

**Local Testing Checklist**:
```gherkin
Given authenticated Robinhood session
When bot requests market data
Then data service fetches and validates data
  And logs all requests with UTC timestamps
  And respects rate limits with exponential backoff
  And blocks trades outside 7am-10am EST window
```

**Rollback Plan**:
- Remove market_data import from bot.py
- No state to clean up (stateless service)
- No database migration to reverse

**Artifact Strategy**:
- N/A (local-only bot, no deployment artifacts)

---

## [INTEGRATION SCENARIOS]

### Scenario 1: Initial Setup
```bash
# Install dependencies (no new dependencies)
pip install -r requirements.txt

# Validate existing dependencies
pip show robin-stocks pandas pytz  # Should show 3.0.5, 2.1.4, 2024.1

# Run type checking
mypy src/trading_bot/market_data/

# Run tests
pytest tests/unit/test_market_data/ -v --cov=src/trading_bot/market_data/
```

### Scenario 2: Integration with Bot
```python
# bot.py integration example

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.market_data.exceptions import TradingHoursError
from trading_bot.utils.time_utils import is_trading_hours

# Initialize services
auth = RobinhoodAuth(config)
auth.login()

market_data = MarketDataService(auth, config)

# Check trading hours before trading
if not is_trading_hours(config.trading_timezone):
    logger.info("Outside trading hours (7am-10am EST) - skipping trade")
    return

# Fetch quote with retry and validation
try:
    quote = market_data.get_quote("AAPL")
    logger.info(f"Quote: {quote.symbol} @ ${quote.current_price}")
except TradingHoursError as e:
    logger.error(f"Trade blocked: {e}")
except DataValidationError as e:
    logger.error(f"Invalid data: {e}")
```

### Scenario 3: Validation
```bash
# Run all tests
pytest tests/unit/test_market_data/ -v

# Check coverage (target: >=90%)
pytest tests/unit/test_market_data/ --cov=src/trading_bot/market_data/ --cov-report=term-missing

# Type checking
mypy src/trading_bot/market_data/ --strict

# Lint
ruff check src/trading_bot/market_data/
```

### Scenario 4: Manual Testing
```bash
# Test quote retrieval
python -c "
from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.config import Config

config = Config.from_env_and_json()
auth = RobinhoodAuth(config)
auth.login()

market_data = MarketDataService(auth, config)
quote = market_data.get_quote('AAPL')
print(f'Quote: {quote.symbol} @ \${quote.current_price} at {quote.timestamp_utc}')
"
```

---

## [TESTING STRATEGY]

**Unit Test Coverage Goals**:
- Overall: >=90% coverage (NFR-005)
- MarketDataService: 100% (core service)
- Validators: 100% (critical validation logic)
- Exceptions: 100% (simple dataclasses)

**Test Breakdown**:
1. test_market_data_service.py (20 tests):
   - Quote retrieval (valid, invalid, network error, rate limit)
   - Historical data (valid, missing dates, invalid prices, completeness)
   - Market hours (open, closed, holiday, UTC conversion)
   - Retry logic integration (mocked @with_retry)

2. test_validators.py (15 tests):
   - Price validation (positive, zero, negative, NaN)
   - Timestamp validation (UTC, recent, stale, timezone-aware)
   - Data completeness (no gaps, missing dates, out-of-order)
   - Volume validation (positive, zero, negative)

3. test_data_models.py (5 tests):
   - Quote dataclass (immutability, field types)
   - MarketStatus dataclass (immutability, field types)
   - MarketDataConfig dataclass (defaults, validation)

4. test_exceptions.py (3 tests):
   - DataValidationError (inheritance, message)
   - TradingHoursError (inheritance, message)

5. test_market_data_integration.py (10 tests):
   - End-to-end quote retrieval with real RobinhoodAuth mock
   - Rate limit handling with retry
   - Trading hours enforcement across time boundaries
   - Data validation rejection flows

**Mock Strategy**:
- Mock robin_stocks API calls (get_latest_price, get_stock_historicals, get_market_hours)
- Mock RobinhoodAuth.is_authenticated() to return True
- Mock datetime.now() for trading hours tests
- Mock time.sleep() to speed up retry tests

---

## [BLOCKERS]

None - all dependencies satisfied, authentication-module shipped, no technical blockers.

---

## [NEXT STEPS]

After planning complete:
1. Run `/tasks market-data-module` to generate implementation tasks
2. Tasks will break down implementation into 20-30 TDD tasks
3. Use `/implement` to execute tasks with test-first approach
