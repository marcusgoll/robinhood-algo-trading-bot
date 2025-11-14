# Tasks: Market Data and Trading Hours Module

## [CODEBASE REUSE ANALYSIS]

**Scanned**: src/trading_bot/**/*.py, tests/**/*.py

### [EXISTING - REUSE]
- ✅ @with_retry decorator (src/trading_bot/error_handling/retry.py)
- ✅ CircuitBreaker (src/trading_bot/error_handling/circuit_breaker.py)
- ✅ RetriableError, NonRetriableError, RateLimitError (src/trading_bot/error_handling/exceptions.py)
- ✅ DEFAULT_POLICY (src/trading_bot/error_handling/policies.py)
- ✅ TradingLogger (src/trading_bot/logger.py)
- ✅ is_trading_hours() (src/trading_bot/utils/time_utils.py)
- ✅ RobinhoodAuth (src/trading_bot/auth/robinhood_auth.py)
- ✅ Config (src/trading_bot/config.py)

### [NEW - CREATE]
- 🆕 MarketDataService (no existing service pattern for market data)
- 🆕 Quote, MarketStatus dataclasses (no existing market data models)
- 🆕 DataValidationError, TradingHoursError (no existing validation exceptions)
- 🆕 Market data validators (no existing data validation module)

---

## Phase 3.0: Setup

T001 [P] Create market_data package structure
- **Files**:
  - src/trading_bot/market_data/__init__.py
  - src/trading_bot/market_data/market_data_service.py
  - src/trading_bot/market_data/data_models.py
  - src/trading_bot/market_data/validators.py
  - src/trading_bot/market_data/exceptions.py
- **Pattern**: src/trading_bot/auth/ (existing package structure)
- **From**: plan.md [STRUCTURE]

T002 [P] Create test package structure
- **Files**:
  - tests/unit/test_market_data/__init__.py
  - tests/unit/test_market_data/test_market_data_service.py
  - tests/unit/test_market_data/test_data_models.py
  - tests/unit/test_market_data/test_validators.py
  - tests/unit/test_market_data/test_exceptions.py
  - tests/integration/test_market_data_integration.py
- **Pattern**: tests/unit/test_error_handling/ (existing test structure)
- **From**: plan.md [STRUCTURE]

T003 [P] Create API contract specification
- **File**: specs/market-data-module/contracts/api.yaml
- **Content**: OpenAPI spec for Quote, MarketStatus, HistoricalDataFrame schemas
- **From**: plan.md [SCHEMA]

---

## Phase 3.1: Data Models and Exceptions

T004 [RED] Write failing test: Quote dataclass immutability
- **File**: tests/unit/test_market_data/test_data_models.py
- **Test**: test_quote_is_immutable()
- **Assert**: Quote instance is frozen, cannot modify fields after creation
- **Pattern**: tests/unit/test_error_handling/test_exceptions.py (dataclass tests)
- **From**: spec.md Technical Design - Data Models

T005 [GREEN→T004] Create Quote dataclass
- **File**: src/trading_bot/market_data/data_models.py
- **Fields**: symbol (str), current_price (Decimal), timestamp_utc (datetime), market_state (str)
- **Decorator**: @dataclass(frozen=True)
- **REUSE**: Decimal from decimal, datetime from datetime
- **Pattern**: src/trading_bot/error_handling/exceptions.py (dataclass pattern)
- **From**: plan.md [SCHEMA] Quote

T006 [RED] Write failing test: MarketStatus dataclass immutability
- **File**: tests/unit/test_market_data/test_data_models.py
- **Test**: test_market_status_is_immutable()
- **Assert**: MarketStatus instance is frozen
- **From**: spec.md Technical Design - Data Models

T007 [GREEN→T006] Create MarketStatus dataclass
- **File**: src/trading_bot/market_data/data_models.py
- **Fields**: is_open (bool), next_open (datetime), next_close (datetime)
- **Decorator**: @dataclass(frozen=True)
- **From**: plan.md [SCHEMA] MarketStatus

T008 [RED] Write failing test: MarketDataConfig with defaults
- **File**: tests/unit/test_market_data/test_data_models.py
- **Test**: test_market_data_config_defaults()
- **Assert**: Config has default values (rate_limit_retries=3, trading_window_start=7, etc.)
- **From**: plan.md [SCHEMA] MarketDataConfig

T009 [GREEN→T008] Create MarketDataConfig dataclass
- **File**: src/trading_bot/market_data/data_models.py
- **Fields**: rate_limit_retries, rate_limit_backoff_base, quote_staleness_threshold, trading_window_start, trading_window_end, trading_timezone
- **Defaults**: rate_limit_retries=3, backoff_base=1.0, staleness=300, start=7, end=10, timezone="America/New_York"
- **From**: plan.md [SCHEMA] MarketDataConfig

T010 [RED] Write failing test: DataValidationError is NonRetriableError
- **File**: tests/unit/test_market_data/test_exceptions.py
- **Test**: test_data_validation_error_inheritance()
- **Assert**: isinstance(DataValidationError("test"), NonRetriableError)
- **REUSE**: NonRetriableError from src/trading_bot/error_handling/exceptions.py
- **Pattern**: tests/unit/test_error_handling/test_exceptions.py
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] Exceptions

T011 [GREEN→T010] Create DataValidationError exception
- **File**: src/trading_bot/market_data/exceptions.py
- **Class**: DataValidationError(NonRetriableError)
- **REUSE**: from trading_bot.error_handling.exceptions import NonRetriableError
- **Pattern**: src/trading_bot/error_handling/exceptions.py (custom exceptions)
- **From**: plan.md [RESEARCH DECISIONS] Custom Market Data Exceptions

T012 [RED] Write failing test: TradingHoursError is NonRetriableError
- **File**: tests/unit/test_market_data/test_exceptions.py
- **Test**: test_trading_hours_error_inheritance()
- **Assert**: isinstance(TradingHoursError("test"), NonRetriableError)
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] Exceptions

T013 [GREEN→T012] Create TradingHoursError exception
- **File**: src/trading_bot/market_data/exceptions.py
- **Class**: TradingHoursError(NonRetriableError)
- **REUSE**: NonRetriableError base class
- **From**: plan.md [RESEARCH DECISIONS] Custom Market Data Exceptions

---

## Phase 3.2: Data Validators (TDD Red-Green-Refactor)

T014 [RED] Write failing test: validate_price rejects zero
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_price_rejects_zero()
- **Assert**: validate_price(0.0) raises DataValidationError
- **From**: spec.md FR-005 Market Data Validation

T015 [RED] Write failing test: validate_price rejects negative
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_price_rejects_negative()
- **Assert**: validate_price(-1.0) raises DataValidationError
- **From**: spec.md FR-005

T016 [RED] Write failing test: validate_price accepts positive
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_price_accepts_positive()
- **Assert**: validate_price(150.25) returns None (no exception)
- **From**: spec.md FR-005

T017 [GREEN→T014,T015,T016] Implement validate_price
- **File**: src/trading_bot/market_data/validators.py
- **Function**: validate_price(price: float) -> None
- **Logic**: if price <= 0: raise DataValidationError(f"Price must be > 0, got {price}")
- **REUSE**: DataValidationError from exceptions.py
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] Validation

T018 [RED] Write failing test: validate_timestamp rejects non-UTC
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_timestamp_rejects_non_utc()
- **Assert**: validate_timestamp(datetime.now()) raises DataValidationError (no timezone)
- **From**: spec.md FR-005 timestamps must be UTC

T019 [RED] Write failing test: validate_timestamp rejects stale quotes
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_timestamp_rejects_stale()
- **Assert**: validate_timestamp(now_utc - 10min, max_age=300) raises DataValidationError
- **From**: spec.md FR-005 timestamps recent <5 minutes

T020 [RED] Write failing test: validate_timestamp accepts recent UTC
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_timestamp_accepts_recent_utc()
- **Assert**: validate_timestamp(now_utc - 1min, max_age=300) returns None
- **From**: spec.md FR-005

T021 [GREEN→T018,T019,T020] Implement validate_timestamp
- **File**: src/trading_bot/market_data/validators.py
- **Function**: validate_timestamp(timestamp: datetime, max_age_seconds: int = 300) -> None
- **Logic**: Check tzinfo is UTC, check age < max_age_seconds
- **REUSE**: DataValidationError, datetime.now(timezone.utc)
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] Validation

T022 [RED] Write failing test: validate_quote with complete data
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_quote_with_complete_data()
- **Input**: {"symbol": "AAPL", "price": 150.25, "timestamp": utc_now, "market_state": "regular"}
- **Assert**: validate_quote(data) returns None
- **From**: spec.md FR-001 validate quote data

T023 [RED] Write failing test: validate_quote rejects missing fields
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_quote_rejects_missing_symbol()
- **Input**: {"price": 150.25} (missing symbol)
- **Assert**: raises DataValidationError("Missing required field: symbol")
- **From**: spec.md FR-005

T024 [GREEN→T022,T023] Implement validate_quote
- **File**: src/trading_bot/market_data/validators.py
- **Function**: validate_quote(data: Dict[str, Any]) -> None
- **Logic**: Check required fields (symbol, price, timestamp, market_state), call validate_price, validate_timestamp
- **REUSE**: validate_price, validate_timestamp, DataValidationError
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] validate_quote

T025 [RED] Write failing test: validate_historical_data detects missing dates
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_historical_data_detects_gaps()
- **Input**: DataFrame with dates [2025-01-01, 2025-01-03] (missing 2025-01-02)
- **Assert**: raises DataValidationError("Missing dates detected: 1 gap")
- **From**: spec.md Scenario 6 Handle Missing Market Data

T026 [RED] Write failing test: validate_historical_data accepts complete data
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_historical_data_accepts_complete()
- **Input**: DataFrame with consecutive dates, valid OHLCV
- **Assert**: validate_historical_data(df) returns None
- **From**: spec.md FR-002

T027 [GREEN→T025,T026] Implement validate_historical_data
- **File**: src/trading_bot/market_data/validators.py
- **Function**: validate_historical_data(df: pd.DataFrame) -> None
- **Logic**: Check required columns (date, open, high, low, close, volume), check date gaps, call validate_price for OHLC
- **REUSE**: validate_price, DataValidationError
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] validate_historical_data

T028 [REFACTOR] Extract common validation helpers
- **File**: src/trading_bot/market_data/validators.py
- **Refactor**: Extract _check_required_fields, _check_date_continuity helpers
- **Tests**: All previous validator tests stay green
- **From**: DRY principle

---

## Phase 3.3: Market Data Service (TDD Red-Green-Refactor)

T029 [RED] Write failing test: MarketDataService initialization
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_service_initialization()
- **Assert**: Service accepts RobinhoodAuth and MarketDataConfig
- **Pattern**: tests/unit/test_robinhood_auth.py (service initialization)
- **From**: spec.md Technical Design Architecture

T030 [GREEN→T029] Implement MarketDataService.__init__
- **File**: src/trading_bot/market_data/market_data_service.py
- **Class**: MarketDataService
- **Constructor**: __init__(self, auth: RobinhoodAuth, config: MarketDataConfig = None, logger: Logger = None)
- **REUSE**: RobinhoodAuth from src/trading_bot/auth/robinhood_auth.py
- **REUSE**: TradingLogger.get_logger() if logger not provided
- **From**: plan.md [RESEARCH DECISIONS] Reuse RobinhoodAuth Session Management

T031 [RED] Write failing test: get_quote with valid symbol
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_get_quote_valid_symbol()
- **Mock**: robin_stocks.stocks.get_latest_price("AAPL") returns "150.25"
- **Assert**: Returns Quote with symbol="AAPL", current_price=150.25
- **Pattern**: tests/unit/test_robinhood_auth.py (mocking robin_stocks)
- **From**: spec.md Scenario 1 Fetch Real-Time Stock Quote

T032 [RED] Write failing test: get_quote validates price
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_get_quote_validates_price()
- **Mock**: robin_stocks returns "0.0"
- **Assert**: raises DataValidationError
- **From**: spec.md FR-001 MUST validate quote data

T033 [GREEN→T031,T032] Implement MarketDataService.get_quote
- **File**: src/trading_bot/market_data/market_data_service.py
- **Method**: get_quote(self, symbol: str) -> Quote
- **Logic**: Call robin_stocks.stocks.get_latest_price(symbol), validate with validate_quote, return Quote dataclass
- **REUSE**: validate_quote from validators.py
- **REUSE**: Quote from data_models.py
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] MarketDataService

T034 [RED] Write failing test: get_quote with @with_retry on rate limit
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_get_quote_retries_on_rate_limit()
- **Mock**: First call raises 429 error, second call succeeds
- **Assert**: Quote returned after retry, logger shows retry attempt
- **REUSE**: @with_retry decorator pattern from tests/unit/test_error_handling/
- **From**: spec.md Scenario 7 Handle API Rate Limit

T035 [GREEN→T034] Add @with_retry decorator to get_quote
- **File**: src/trading_bot/market_data/market_data_service.py
- **Decorator**: @with_retry(policy=DEFAULT_POLICY)
- **REUSE**: from trading_bot.error_handling.retry import with_retry
- **REUSE**: from trading_bot.error_handling.policies import DEFAULT_POLICY
- **From**: plan.md [RESEARCH DECISIONS] Reuse Error Handling Framework

T036 [RED] Write failing test: get_historical_data returns DataFrame
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_get_historical_data_returns_dataframe()
- **Mock**: robin_stocks.stocks.get_stock_historicals returns list of OHLCV dicts
- **Assert**: Returns pd.DataFrame with columns [date, open, high, low, close, volume]
- **From**: spec.md Scenario 2 Fetch Historical Price Data

T037 [RED] Write failing test: get_historical_data validates completeness
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_get_historical_data_validates_completeness()
- **Mock**: robin_stocks returns data with missing dates
- **Assert**: raises DataValidationError
- **From**: spec.md FR-002 MUST validate data completeness

T038 [GREEN→T036,T037] Implement MarketDataService.get_historical_data
- **File**: src/trading_bot/market_data/market_data_service.py
- **Method**: get_historical_data(self, symbol: str, interval: str = "day", span: str = "3month") -> pd.DataFrame
- **Logic**: Call robin_stocks.stocks.get_stock_historicals, convert to DataFrame, validate with validate_historical_data
- **REUSE**: validate_historical_data from validators.py
- **REUSE**: @with_retry decorator
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] get_historical_data

T039 [RED] Write failing test: is_market_open during hours
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_is_market_open_during_hours()
- **Mock**: robin_stocks.markets.get_market_hours returns is_open=True
- **Assert**: Returns MarketStatus(is_open=True, next_open=..., next_close=...)
- **From**: spec.md Scenario 3 Check If Market Is Open

T040 [RED] Write failing test: is_market_open outside hours
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_is_market_open_outside_hours()
- **Mock**: robin_stocks returns is_open=False, next_open in future
- **Assert**: Returns MarketStatus(is_open=False, next_open=..., next_close=...)
- **From**: spec.md FR-003

T041 [GREEN→T039,T040] Implement MarketDataService.is_market_open
- **File**: src/trading_bot/market_data/market_data_service.py
- **Method**: is_market_open(self) -> MarketStatus
- **Logic**: Call robin_stocks.markets.get_market_hours, parse timestamps to UTC, return MarketStatus
- **REUSE**: MarketStatus from data_models.py
- **REUSE**: @with_retry decorator
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] is_market_open

T042 [RED] Write failing test: get_quotes_batch returns dict
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_get_quotes_batch()
- **Mock**: robin_stocks returns prices for ["AAPL", "TSLA", "MSFT"]
- **Assert**: Returns Dict[str, Quote] with 3 quotes
- **From**: spec.md FR-001 support batch symbol queries

T043 [GREEN→T042] Implement MarketDataService.get_quotes_batch
- **File**: src/trading_bot/market_data/market_data_service.py
- **Method**: get_quotes_batch(self, symbols: List[str]) -> Dict[str, Quote]
- **Logic**: Call get_quote for each symbol, aggregate results
- **REUSE**: get_quote method (already has retry and validation)
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] get_quotes_batch

T044 [REFACTOR] Extract logging helper _log_request
- **File**: src/trading_bot/market_data/market_data_service.py
- **Refactor**: Create _log_request(self, method: str, params: Dict) -> None
- **Usage**: Called before all API calls for audit trail
- **REUSE**: self.logger from TradingLogger
- **Tests**: All service tests stay green
- **From**: spec.md NFR-002 Auditability

---

## Phase 3.4: Trading Hours Validation

T045 [RED] Write failing test: is_trading_hours validates 7am EST
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_is_trading_hours_7am_est()
- **Mock**: datetime.now(utc) = 7:00am EST (12:00pm UTC)
- **Assert**: is_trading_hours() returns True
- **REUSE**: is_trading_hours from src/trading_bot/utils/time_utils.py
- **From**: spec.md Scenario 5 Allow Trade During 7am-10am EST

T046 [RED] Write failing test: is_trading_hours rejects 10am EST
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_is_trading_hours_10am_est()
- **Mock**: datetime.now(utc) = 10:00am EST (3:00pm UTC)
- **Assert**: is_trading_hours() returns False
- **From**: spec.md Scenario 4 Enforce 7am-10am EST Trading Window

T047 [RED] Write failing test: is_trading_hours rejects 11am EST
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_is_trading_hours_11am_est()
- **Mock**: datetime.now(utc) = 11:30am EST (4:30pm UTC)
- **Assert**: is_trading_hours() returns False
- **From**: spec.md Scenario 4

T048 [GREEN→T045,T046,T047] Verify is_trading_hours implementation
- **File**: src/trading_bot/utils/time_utils.py
- **Verify**: Existing is_trading_hours() function handles 7am-10am EST window
- **Pattern**: Read existing implementation (lines 14-35)
- **Note**: If implementation missing, add logic: 7 <= current_hour_est < 10
- **From**: plan.md [RESEARCH DECISIONS] Reuse Time Utilities

T049 [RED] Write failing test: validate_trade_time raises TradingHoursError
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_trade_time_raises_outside_hours()
- **Mock**: datetime.now(utc) = 11:00am EST
- **Assert**: validate_trade_time() raises TradingHoursError
- **From**: spec.md FR-004 MUST raise TradingHoursError

T050 [RED] Write failing test: validate_trade_time allows within hours
- **File**: tests/unit/test_market_data/test_validators.py
- **Test**: test_validate_trade_time_allows_within_hours()
- **Mock**: datetime.now(utc) = 8:15am EST
- **Assert**: validate_trade_time() returns None (no exception)
- **From**: spec.md FR-004

T051 [GREEN→T049,T050] Implement validate_trade_time
- **File**: src/trading_bot/market_data/validators.py
- **Function**: validate_trade_time(current_time: datetime = None) -> None
- **Logic**: if not is_trading_hours(current_time): raise TradingHoursError("Trading blocked outside 7am-10am EST")
- **REUSE**: is_trading_hours from time_utils.py
- **REUSE**: TradingHoursError from exceptions.py
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] validate_trade_time

---

## Phase 3.5: Integration Tests

T052 [P] Write integration test: End-to-end quote retrieval
- **File**: tests/integration/test_market_data_integration.py
- **Test**: test_end_to_end_quote_retrieval()
- **Setup**: Mock RobinhoodAuth, mock robin_stocks API
- **Flow**: Initialize service → get_quote("AAPL") → validate result
- **Assert**: Returns valid Quote, logs request
- **Pattern**: tests/integration/test_auth_integration.py
- **From**: plan.md [TESTING STRATEGY] Integration Tests

T053 [P] Write integration test: Rate limit with retry
- **File**: tests/integration/test_market_data_integration.py
- **Test**: test_rate_limit_retry_flow()
- **Setup**: Mock 429 error on first call, success on second
- **Assert**: Service retries and succeeds, logs show retry
- **REUSE**: @with_retry behavior from error_handling
- **From**: spec.md Scenario 7 Handle API Rate Limit

T054 [P] Write integration test: Trading hours enforcement
- **File**: tests/integration/test_market_data_integration.py
- **Test**: test_trading_hours_enforcement()
- **Setup**: Mock time at 11am EST
- **Flow**: Call validate_trade_time()
- **Assert**: Raises TradingHoursError, logs block reason
- **From**: spec.md Scenario 4 Enforce Trading Window

T055 [P] Write integration test: Data validation rejection
- **File**: tests/integration/test_market_data_integration.py
- **Test**: test_data_validation_rejects_bad_data()
- **Setup**: Mock robin_stocks returns price=0
- **Flow**: Call get_quote()
- **Assert**: Raises DataValidationError, does NOT return bad data
- **From**: spec.md NFR-001 Data Integrity

---

## Phase 3.6: Error Handling and Resilience

T056 [RED] Write failing test: Service handles network error gracefully
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_get_quote_handles_network_error()
- **Mock**: robin_stocks raises ConnectionError
- **Assert**: Raises RetriableError (wrapped by @with_retry)
- **From**: spec.md FR-007 Error Handling

T057 [GREEN→T056] Add network error handling
- **File**: src/trading_bot/market_data/market_data_service.py
- **Logic**: @with_retry decorator already handles RetriableError
- **Verify**: ConnectionError triggers retry logic
- **From**: plan.md [RESEARCH DECISIONS] Reuse Error Handling Framework

T058 [RED] Write failing test: Service handles invalid symbol error
- **File**: tests/unit/test_market_data/test_market_data_service.py
- **Test**: test_get_quote_handles_invalid_symbol()
- **Mock**: robin_stocks returns None for unknown symbol
- **Assert**: Raises DataValidationError("Symbol not found: INVALID")
- **From**: spec.md FR-001 handle symbol not found

T059 [GREEN→T058] Add symbol validation
- **File**: src/trading_bot/market_data/market_data_service.py
- **Logic**: In get_quote, check if result is None, raise DataValidationError
- **From**: spec.md FR-007

T060 [RED] Write failing test: Circuit breaker opens after failures
- **File**: tests/integration/test_market_data_integration.py
- **Test**: test_circuit_breaker_opens_after_failures()
- **Mock**: robin_stocks fails 5 times consecutively
- **Assert**: Circuit breaker opens, subsequent calls fail fast
- **REUSE**: CircuitBreaker from src/trading_bot/error_handling/circuit_breaker.py
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE] Circuit breaker

T061 [GREEN→T060] Integrate circuit breaker (optional enhancement)
- **File**: src/trading_bot/market_data/market_data_service.py
- **Enhancement**: Wrap API calls with circuit breaker for fault isolation
- **REUSE**: from trading_bot.error_handling.circuit_breaker import CircuitBreaker
- **Note**: Optional - @with_retry already provides basic resilience
- **From**: plan.md [RESEARCH DECISIONS] Circuit breaker for fault isolation

---

## Phase 3.7: Package Exports and Documentation

T062 [P] Configure package exports in __init__.py
- **File**: src/trading_bot/market_data/__init__.py
- **Exports**: MarketDataService, Quote, MarketStatus, MarketDataConfig, DataValidationError, TradingHoursError
- **Pattern**: src/trading_bot/error_handling/__init__.py
- **From**: plan.md [STRUCTURE]

T063 [P] Add module docstrings
- **Files**: All market_data/*.py files
- **Content**: Module-level docstring explaining purpose, usage example
- **Pattern**: src/trading_bot/auth/robinhood_auth.py (existing docstrings)
- **From**: spec.md NFR-006 Type Safety

T064 [P] Add type hints to all functions
- **Files**: All market_data/*.py files
- **Verify**: mypy --strict passes with no errors
- **REUSE**: Type hints from existing modules
- **From**: spec.md NFR-006 MUST pass mypy strict mode

---

## Phase 3.8: Testing and Coverage

T065 [P] Run unit tests with coverage
- **Command**: pytest tests/unit/test_market_data/ --cov=src/trading_bot/market_data/ --cov-report=term-missing
- **Target**: >=90% line coverage (NFR-005)
- **From**: spec.md Testing Strategy

T066 [P] Run integration tests
- **Command**: pytest tests/integration/test_market_data_integration.py -v
- **Assert**: All integration scenarios pass
- **From**: plan.md [INTEGRATION SCENARIOS]

T067 [P] Run mypy type checking
- **Command**: mypy src/trading_bot/market_data/ --strict
- **Assert**: No type errors
- **From**: spec.md NFR-006

T068 [P] Run linter
- **Command**: ruff check src/trading_bot/market_data/
- **Assert**: No lint errors
- **From**: plan.md [INTEGRATION SCENARIOS] Validation

---

## Phase 3.9: Manual Testing and Validation

T069 [P] Manual test: Fetch AAPL quote
- **Script**:
  ```python
  from trading_bot.auth.robinhood_auth import RobinhoodAuth
  from trading_bot.market_data import MarketDataService
  from trading_bot.config import Config

  config = Config.from_env_and_json()
  auth = RobinhoodAuth(config)
  auth.login()

  market_data = MarketDataService(auth)
  quote = market_data.get_quote('AAPL')
  print(f"Quote: {quote.symbol} @ ${quote.current_price} at {quote.timestamp_utc}")
  ```
- **Assert**: Quote returned with valid data
- **From**: plan.md [CI/CD IMPACT] Smoke Tests

T070 [P] Manual test: Fetch 90-day historical data
- **Script**: market_data.get_historical_data('AAPL', interval='day', span='3month')
- **Assert**: Returns DataFrame with ~63 rows (90 days - weekends/holidays)
- **From**: plan.md [CI/CD IMPACT] Smoke Tests

T071 [P] Manual test: Check market hours
- **Script**: market_data.is_market_open()
- **Assert**: Returns MarketStatus with is_open boolean
- **From**: plan.md [CI/CD IMPACT] Smoke Tests

T072 [P] Manual test: Validate 8am EST allows trade
- **Script**:
  ```python
  from trading_bot.market_data import validate_trade_time
  from datetime import datetime, timezone
  import pytz

  est = pytz.timezone('America/New_York')
  test_time = est.localize(datetime(2025, 10, 8, 8, 0)).astimezone(timezone.utc)
  validate_trade_time(test_time)  # Should not raise
  print("Trade allowed at 8am EST")
  ```
- **Assert**: No exception raised
- **From**: plan.md [CI/CD IMPACT] Smoke Tests

T073 [P] Manual test: Validate 11am EST blocks trade
- **Script**: Similar to T072 but with 11am EST
- **Assert**: Raises TradingHoursError
- **From**: plan.md [CI/CD IMPACT] Smoke Tests

---

## Summary

**Total Tasks**: 73
- Setup: 3 tasks (T001-T003)
- Data Models & Exceptions: 10 tasks (T004-T013)
- Validators TDD: 15 tasks (T014-T028)
- Market Data Service TDD: 16 tasks (T029-T044)
- Trading Hours: 7 tasks (T045-T051)
- Integration Tests: 4 tasks (T052-T055)
- Error Handling: 6 tasks (T056-T061)
- Package & Docs: 3 tasks (T062-T064)
- Testing & Coverage: 4 tasks (T065-T068)
- Manual Testing: 5 tasks (T069-T073)

**TDD Breakdown**:
- RED tests: 28 tasks
- GREEN implementations: 28 tasks
- REFACTOR: 2 tasks
- Parallel setup/tests: 15 tasks

**Estimated Effort**: ~12-16 hours (full TDD cycle with comprehensive tests)

**Dependencies**: All dependencies already satisfied (robin-stocks, pandas, pytz in requirements.txt)

**Reuse Score**: 6 existing components reused, 4 new components created
