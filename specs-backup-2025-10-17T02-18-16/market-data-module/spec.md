# Specification: Market Data and Trading Hours Module

**Feature**: market-data-module
**Type**: Backend / Market Data API
**Area**: api
**Blocked by**: None (authentication-module shipped)
**Constitution**: v1.0.0

---

## Overview

Implements market data retrieval from Robinhood API with trading hours validation and 7am-10am EST trading window enforcement. Enforces Constitution Data_Integrity and Risk_Management requirements by validating all market data (timestamps, bounds, completeness) and blocking trades outside peak volatility hours.

**Problem**: Bot needs real-time and historical market data to make trading decisions. Current system lacks:
- Real-time stock quote retrieval
- Historical price data for backtesting
- Market open/close status checking
- Trading hours enforcement (7am-10am EST peak volatility window)
- Market data validation (timestamps, bounds, missing data)
- Rate limit protection for API calls

**Solution**: Market data service that fetches real-time quotes, historical OHLCV data, validates market hours, enforces 7am-10am EST trading window, validates all data integrity, and implements rate limit protection with backoff.

---

## User Scenarios

### Scenario 1: Fetch Real-Time Stock Quote
**Given** authenticated Robinhood session
**And** valid stock symbol (e.g., "AAPL")
**When** bot requests current quote
**Then** market data service:
- Calls robin_stocks.stocks.get_latest_price(symbol)
- Validates quote data (price > 0, timestamp recent)
- Returns quote with: current_price, timestamp_utc, market_state
**And** logs "Quote retrieved: AAPL at $150.25"

### Scenario 2: Fetch Historical Price Data for Backtesting
**Given** authenticated Robinhood session
**And** valid stock symbol and date range
**When** bot requests historical data for backtesting
**Then** market data service:
- Calls robin_stocks.stocks.get_stock_historicals(symbol, interval, span)
- Validates data completeness (no gaps in dates)
- Validates OHLCV data (open/high/low/close > 0, volume >= 0)
- Returns DataFrame with: date, open, high, low, close, volume
**And** logs "Historical data retrieved: AAPL, 90 days, 252 records"

### Scenario 3: Check If Market Is Open
**Given** current time
**When** bot checks market status
**Then** market data service:
- Gets market hours from robin_stocks.markets.get_market_hours()
- Checks if current time (UTC) is within market hours
- Returns boolean is_open and next_open/next_close timestamps
**And** logs "Market status: open" or "Market status: closed until 2025-10-09 13:30 UTC"

### Scenario 4: Enforce 7am-10am EST Trading Window
**Given** current time is 11:30am EST (4:30pm UTC)
**When** bot attempts to place trade
**Then** trading hours validator:
- Converts current time to EST
- Checks if within 7am-10am EST window
- Returns False (outside window)
- Raises TradingHoursError with message "Trading blocked outside 7am-10am EST peak volatility window"
**And** bot does NOT place trade (Safety_First)
**And** logs "Trade blocked: outside trading hours (current: 11:30 EST)"

### Scenario 5: Allow Trade During 7am-10am EST Window
**Given** current time is 8:15am EST (1:15pm UTC)
**And** market is open
**When** bot attempts to place trade
**Then** trading hours validator:
- Converts current time to EST
- Checks if within 7am-10am EST window
- Returns True (within window)
- Allows trade to proceed
**And** logs "Trade allowed: within 7am-10am EST window"

### Scenario 6: Handle Missing Market Data
**Given** API returns incomplete historical data (gaps in dates)
**When** bot requests historical data
**Then** market data service:
- Detects missing dates in sequence
- Logs warning "Missing data detected: 5 gaps in 90-day range"
- Raises DataValidationError
**And** bot does NOT use incomplete data for backtesting (Data_Integrity)

### Scenario 7: Handle API Rate Limit
**Given** bot makes multiple rapid API calls
**And** Robinhood API returns 429 Too Many Requests
**When** API call fails with rate limit error
**Then** market data service:
- Catches rate limit exception
- Implements exponential backoff (1s, 2s, 4s, 8s)
- Retries request up to 3 times
- Logs "Rate limit hit, retrying in 2s (attempt 2/3)"
**And** returns data if retry succeeds
**Or** raises RateLimitError after 3 failed attempts

### Scenario 8: Validate Quote Data Integrity
**Given** API returns quote data
**When** market data service receives quote
**Then** data validator:
- Checks price > 0
- Checks timestamp is recent (<5 minutes old)
- Checks timestamp is UTC
- Checks required fields present (price, timestamp, symbol)
- Logs validation result
**And** raises DataValidationError if any check fails

---

## Requirements

### Functional Requirements

**FR-001: Real-Time Quote Retrieval**
- MUST fetch current stock price using robin_stocks.stocks.get_latest_price()
- MUST support single symbol and batch symbol queries
- MUST return: current_price, timestamp_utc, market_state, symbol
- MUST validate quote data before returning
- MUST handle symbol not found errors gracefully

**FR-002: Historical Price Data Retrieval**
- MUST fetch historical OHLCV data using robin_stocks.stocks.get_stock_historicals()
- MUST support intervals: 5minute, 10minute, day, week
- MUST support spans: day, week, month, 3month, year, 5year
- MUST return pandas DataFrame with: date, open, high, low, close, volume
- MUST validate data completeness (no missing dates)
- MUST validate OHLCV bounds (prices > 0, volume >= 0)

**FR-003: Market Hours Status Check**
- MUST fetch market hours using robin_stocks.markets.get_market_hours()
- MUST determine if market is currently open
- MUST return: is_open (boolean), next_open (timestamp UTC), next_close (timestamp UTC)
- MUST handle market holidays correctly
- MUST convert all timestamps to UTC

**FR-004: Trading Hours Enforcement (7am-10am EST)**
- MUST validate trades only allowed 7am-10am EST (peak volatility)
- MUST convert current time to EST for comparison
- MUST return True if within window, False otherwise
- MUST raise TradingHoursError if outside window
- MUST log all trading hours checks with timestamps
- MUST account for EST/EDT daylight saving time

**FR-005: Market Data Validation (Data_Integrity)**
- MUST validate all prices > 0
- MUST validate all volumes >= 0
- MUST validate timestamps are UTC
- MUST validate timestamps are recent (<5 minutes for quotes)
- MUST check data completeness (no missing dates in historical data)
- MUST raise DataValidationError for any validation failure

**FR-006: Rate Limit Protection (Risk_Management)**
- MUST catch 429 Too Many Requests errors
- MUST implement exponential backoff (1s, 2s, 4s, 8s)
- MUST retry failed requests up to 3 times
- MUST log rate limit hits and retry attempts
- MUST raise RateLimitError after max retries exceeded

**FR-007: Error Handling (Safety_First)**
- MUST handle network errors gracefully
- MUST handle invalid symbol errors
- MUST handle API errors with clear messages
- MUST NEVER return invalid/unvalidated data
- MUST log all errors with context

### Non-Functional Requirements

**NFR-001: Data Integrity (Data_Integrity)**
- MUST validate all data before returning
- MUST use UTC for all timestamps
- MUST handle missing data by raising errors (not filling gaps)
- MUST log data validation failures
- MUST enforce data quality standards (no NaN, no negative prices)

**NFR-002: Auditability (Audit_Everything)**
- MUST log all market data requests (symbol, timestamp)
- MUST log all validation failures
- MUST log all rate limit hits
- MUST log all trading hours checks
- MUST include timestamps (UTC) in all logs

**NFR-003: Error Handling (Fail_Safe)**
- MUST fail safely (raise errors, don't continue with bad data)
- MUST provide clear error messages for troubleshooting
- MUST handle all exceptions explicitly
- MUST NOT use bare except clauses
- MUST log all errors before raising

**NFR-004: Performance**
- Real-time quote fetch SHOULD complete in <2 seconds
- Historical data fetch SHOULD complete in <10 seconds
- Market hours check SHOULD complete in <1 second
- Trading hours validation MUST complete in <100ms
- MUST NOT block trading operations during data fetches

**NFR-005: Test Coverage**
- MUST achieve >=90% test coverage (Code_Quality)
- MUST test all data retrieval scenarios
- MUST test all validation scenarios
- MUST test error handling (network, API, validation)
- MUST test trading hours enforcement

**NFR-006: Type Safety**
- MUST use type hints on all functions
- MUST pass mypy strict mode
- MUST use dataclasses for data models

---

## Technical Design

### Architecture

```
MarketDataService Class
├── __init__(config, auth)
├── get_quote(symbol: str) → Quote
├── get_quotes_batch(symbols: List[str]) → Dict[str, Quote]
├── get_historical_data(symbol, interval, span) → pd.DataFrame
├── is_market_open() → MarketStatus
├── _validate_quote(quote_data) → Quote
├── _validate_historical_data(df) → pd.DataFrame
├── _handle_rate_limit(func, *args, **kwargs) → Any
└── _log_request(method, params) → None

TradingHoursValidator Class
├── __init__(config)
├── is_within_trading_window(current_time: datetime) → bool
├── get_trading_window() → TradingWindow
├── _convert_to_est(utc_time: datetime) → datetime
└── validate_trade_time(current_time: datetime) → None (raises if invalid)

DataValidator Class
├── validate_quote(data: Dict) → None
├── validate_historical_data(df: pd.DataFrame) → None
├── validate_price(price: float) → None
├── validate_timestamp(timestamp: datetime) → None
└── check_data_completeness(df: pd.DataFrame) → None
```

### Data Models

```python
@dataclass
class Quote:
    """Real-time stock quote."""
    symbol: str
    current_price: Decimal
    timestamp_utc: datetime
    market_state: str  # "regular", "pre", "post", "closed"

@dataclass
class MarketStatus:
    """Market open/close status."""
    is_open: bool
    next_open: datetime  # UTC
    next_close: datetime  # UTC
    market_hours: str  # "9:30-16:00 EST"

@dataclass
class TradingWindow:
    """Trading hours window (7am-10am EST)."""
    start_hour_est: int = 7  # 7am EST
    end_hour_est: int = 10   # 10am EST
    timezone: str = "America/New_York"

@dataclass
class MarketDataConfig:
    """Configuration for market data service."""
    rate_limit_retries: int = 3
    rate_limit_backoff_base: float = 1.0  # seconds
    quote_staleness_threshold: int = 300  # 5 minutes in seconds
    trading_window_start: int = 7  # 7am EST
    trading_window_end: int = 10  # 10am EST
```

### Dependencies

**External Libraries**:
- `robin-stocks==3.0.5` (already in requirements.txt)
- `pandas>=2.0.0` (already in requirements.txt)
- `pytz` (NEW - must add to requirements.txt for timezone handling)

**Internal Modules**:
- `auth.robinhood_auth`: RobinhoodAuth class for authenticated sessions
- `config.py`: Configuration loading
- `logger.py`: Audit logging

### Market Data Flow

```
1. Bot requests market data
   ↓
2. MarketDataService validates authentication
   ↓
3. Check rate limit status
   ↓
4. Call robin_stocks API
   ↓
   If 429 → Exponential backoff retry (3 attempts)
   ↓
5. Validate returned data (DataValidator)
   ↓
   If validation fails → Raise DataValidationError
   ↓
6. Convert to typed dataclass
   ↓
7. Log request and result
   ↓
8. Return validated data
```

### Trading Hours Validation Flow

```
1. Bot attempts to place trade
   ↓
2. TradingHoursValidator.validate_trade_time(now_utc)
   ↓
3. Convert current time to EST
   ↓
4. Check if 7am <= current_hour < 10am
   ↓
   YES → Return True, allow trade
   ↓
   NO → Raise TradingHoursError, block trade
   ↓
5. Log validation result with timestamp
```

---

## Implementation Plan

### Phase 1: Core Market Data Service
1. Create `src/trading_bot/market_data/market_data_service.py`
2. Implement MarketDataConfig dataclass
3. Implement Quote and MarketStatus dataclasses
4. Implement basic API wrapper (get_quote, get_historical_data, is_market_open)

### Phase 2: Data Validation
1. Create `src/trading_bot/market_data/data_validator.py`
2. Implement quote validation (price > 0, timestamp recent)
3. Implement historical data validation (completeness, bounds)
4. Implement timestamp validation (UTC, recent)

### Phase 3: Trading Hours Enforcement
1. Create `src/trading_bot/market_data/trading_hours_validator.py`
2. Implement TradingWindow dataclass
3. Implement EST timezone conversion
4. Implement 7am-10am EST window checking
5. Implement TradingHoursError exception

### Phase 4: Rate Limit Protection
1. Implement rate limit detection (429 errors)
2. Implement exponential backoff decorator
3. Implement retry logic (max 3 attempts)
4. Implement RateLimitError exception

### Phase 5: Integration & Testing
1. Write comprehensive unit tests (target: 90% coverage)
2. Write integration tests with mocked robin_stocks
3. Test all error scenarios (network, validation, rate limits)
4. Test trading hours enforcement across EST/EDT
5. Integrate with bot.py

---

## Testing Strategy

### Unit Tests (test_market_data_service.py)

**Quote Retrieval Tests**:
- ✅ Valid symbol → fetch quote successfully
- ✅ Invalid symbol → raise clear error
- ✅ Quote with price = 0 → validation fails
- ✅ Quote with stale timestamp → validation fails
- ✅ Batch quote retrieval → all quotes valid
- ✅ Network error → handled gracefully

**Historical Data Tests**:
- ✅ Valid request → return DataFrame with OHLCV
- ✅ Missing dates in data → validation fails
- ✅ Negative price in data → validation fails
- ✅ Zero volume → allowed
- ✅ Data completeness check → detects gaps

**Market Hours Tests**:
- ✅ During market hours → is_open = True
- ✅ Outside market hours → is_open = False
- ✅ Market holiday → is_open = False
- ✅ Timestamps converted to UTC
- ✅ Next open/close calculated correctly

**Trading Hours Tests**:
- ✅ 7:00am EST → within window (True)
- ✅ 9:59am EST → within window (True)
- ✅ 10:00am EST → outside window (False)
- ✅ 6:59am EST → outside window (False)
- ✅ 11:00am EST → outside window (False)
- ✅ EST/EDT daylight saving handled
- ✅ UTC to EST conversion accurate

**Data Validation Tests**:
- ✅ Valid quote data → passes validation
- ✅ Price <= 0 → fails validation
- ✅ Missing timestamp → fails validation
- ✅ Non-UTC timestamp → fails validation
- ✅ Stale timestamp (>5min) → fails validation
- ✅ Missing OHLCV columns → fails validation

**Rate Limit Tests**:
- ✅ First 429 error → retry after 1s
- ✅ Second 429 error → retry after 2s
- ✅ Third 429 error → retry after 4s
- ✅ Fourth 429 error → raise RateLimitError
- ✅ Success after retry → return data
- ✅ Backoff timing accurate

### Integration Tests

**End-to-End Market Data Flow**:
- Mock robin_stocks responses
- Test complete quote retrieval flow with validation
- Test historical data flow with completeness check
- Test market hours check with timezone conversion
- Test trading hours enforcement across window boundaries
- Test rate limit handling with retries

### Security Tests

**Data Integrity Tests**:
- Verify all timestamps are UTC
- Verify no unvalidated data returned
- Verify errors raised for bad data
- Verify logs contain no sensitive data

---

## Configuration

**Environment Variables (.env)**:
```bash
# No new environment variables required
# Uses existing authentication from authentication-module
```

**In config.py**:
```python
class Config:
    """Configuration loaded from environment variables."""

    # Market Data Configuration
    rate_limit_retries: int = 3
    rate_limit_backoff_base: float = 1.0  # seconds
    quote_staleness_threshold: int = 300  # 5 minutes
    trading_window_start_hour: int = 7  # 7am EST
    trading_window_end_hour: int = 10  # 10am EST
```

---

## Deployment Considerations

### Dependencies

**New Dependency**:
- `pytz` - Must add to requirements.txt for timezone handling
  ```
  pytz==2023.3
  ```

**Existing Dependencies**:
- ✅ `robin-stocks==3.0.5` (already in requirements.txt)
- ✅ `pandas>=2.0.0` (already in requirements.txt)

### Breaking Changes
- ❌ **No breaking changes** (new module, additive only)
- ✅ Trading hours enforcement will block trades outside 7am-10am EST
- ✅ Bot must integrate MarketDataService before trading

### Environment Setup
- ✅ No new environment variables required
- ✅ Uses existing RobinhoodAuth from authentication-module
- ✅ Bot fails safely if market data unavailable (Fail_Safe)

### Security Considerations
- ✅ No credentials stored (uses authentication-module)
- ✅ All data validated before use (Data_Integrity)
- ✅ Rate limits respected (Risk_Management)

### Migration
- ❌ **No database migration** (stateless service)
- ✅ No state to persist
- ✅ All data fetched on-demand from Robinhood API

### Rollback
- ✅ Standard rollback (remove market data import from bot.py)
- ✅ No state to clean up (stateless service)
- ✅ No data to migrate

---

## Success Criteria

### Acceptance Criteria
- [ ] All 7 functional requirements implemented
- [ ] Test coverage >=90% (NFR-005)
- [ ] Successful real-time quote retrieval
- [ ] Successful historical data retrieval for backtesting
- [ ] Market hours check accurate
- [ ] Trading hours enforcement blocks trades outside 7am-10am EST
- [ ] All data validated before use (prices > 0, timestamps UTC)
- [ ] Rate limit protection with exponential backoff
- [ ] mypy passes with no errors (NFR-006)

### Quality Gates (Pre_Deploy)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual testing: Fetch AAPL quote
- [ ] Manual testing: Fetch 90-day historical data
- [ ] Manual testing: Check market hours
- [ ] Manual testing: Validate 7am EST allows trade
- [ ] Manual testing: Validate 11am EST blocks trade
- [ ] Manual testing: Rate limit retry works
- [ ] Manual testing: Invalid data rejected

---

## Open Questions

None - Spec is clear based on roadmap requirements and Constitution principles.

---

## References

- Constitution: `.spec-flow/memory/constitution.md` (Data_Integrity, Risk_Management, Safety_First)
- Roadmap: `.spec-flow/memory/roadmap.md` (market-data-module feature)
- Config: `config.py` (configuration loading)
- Logger: `src/trading_bot/logger.py` (audit logging)
- Auth: `src/trading_bot/auth/robinhood_auth.py` (authenticated sessions)
- robin-stocks: https://robin-stocks.readthedocs.io/ (API reference)
- pytz: https://pythonhosted.org/pytz/ (timezone handling)
