# Tasks: Account Data Module

**Feature**: account-data-module
**Type**: Backend / Account Management
**TDD Approach**: RED → GREEN → REFACTOR

---

## [CODEBASE REUSE ANALYSIS]

**Scanned**: src/trading_bot/**/*.py, tests/**/*.py

### [EXISTING - REUSE] (8 components)

- ✅ **RobinhoodAuth** (src/trading_bot/auth/robinhood_auth.py)
  - Dependency: AccountData requires authenticated session
  - Usage: Pass auth instance via __init__

- ✅ **_retry_with_backoff()** (src/trading_bot/auth/robinhood_auth.py:40-76)
  - Pattern: Exponential backoff (1s, 2s, 4s) for network errors
  - Usage: Wrap API calls for resilience

- ✅ **_mask_credential()** (src/trading_bot/auth/robinhood_auth.py:79-88)
  - Pattern: Mask sensitive values in logs
  - Usage: Log account balances safely

- ✅ **Config dataclass** (src/trading_bot/config.py:25-67)
  - Pattern: @dataclass with from_config() factory method
  - Usage: Reference for AccountData configuration

- ✅ **bot.get_buying_power()** (src/trading_bot/bot.py:240-251)
  - Integration point: Replace $10k mock with real value
  - Usage: Return self.account_data.get_buying_power()

- ✅ **bot.execute_trade()** (src/trading_bot/bot.py:253-324)
  - Integration point: Invalidate cache after trades
  - Usage: Call self.account_data.invalidate_cache()

- ✅ **SafetyChecks** (src/trading_bot/safety_checks.py:100-150)
  - Integration point: Accept account_data parameter
  - Usage: Fetch buying_power from AccountData if available

- ✅ **Test patterns** (tests/unit/test_robinhood_auth.py)
  - Pattern: GIVEN/WHEN/THEN structure, unittest.mock
  - Usage: Follow same structure for AccountData tests

### [NEW - CREATE] (5 components)

- 🆕 **AccountData service** (src/trading_bot/account/account_data.py)
  - Purpose: Fetch and cache account data from robin-stocks API
  - Features: get_buying_power(), get_positions(), get_account_balance(), get_day_trade_count()

- 🆕 **Module exports** (src/trading_bot/account/__init__.py)
  - Exports: AccountData, AccountDataError, Position, AccountBalance

- 🆕 **Data models** (in account_data.py)
  - Position dataclass: Equity position with P&L calculations
  - AccountBalance dataclass: Cash, equity, buying_power breakdown
  - CacheEntry dataclass: TTL-based cache storage

- 🆕 **Unit tests** (tests/unit/test_account_data.py)
  - Coverage: Data models, cache logic, API fetching, P&L calculations, error handling
  - Target: ≥90% coverage

- 🆕 **Integration tests** (tests/integration/test_account_integration.py)
  - Coverage: Bot integration, SafetyChecks integration, cache invalidation
  - Scenarios: Real buying power, trade execution cache clearing

---

## Task Breakdown (40 tasks)

### Phase 3.1: Setup (T001-T005)

**T001** [P] Create account module directory structure
- **Action**: `mkdir -p src/trading_bot/account`
- **Files**: `src/trading_bot/account/__init__.py` (empty initially)
- **Pattern**: Follow src/trading_bot/auth/ structure
- **From**: plan.md [STRUCTURE] section

**T002** [P] Create test directory structure
- **Action**: `mkdir -p tests/unit tests/integration`
- **Files**: Ensure test directories exist
- **Pattern**: Match existing test structure
- **From**: plan.md [STRUCTURE] section

**T003** [P] Create custom exception class
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  class AccountDataError(Exception):
      """Custom exception for account data errors."""
      pass
  ```
- **Pattern**: Follow AuthenticationError in auth/robinhood_auth.py:92
- **From**: plan.md [NEW INFRASTRUCTURE] section

**T004** [P] Stub out AccountData class skeleton
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  class AccountData:
      def __init__(self, auth: RobinhoodAuth):
          self.auth = auth
          self._cache: Dict[str, Any] = {}
          # TODO: Implement cache logic
  ```
- **Pattern**: Follow RobinhoodAuth structure (auth/robinhood_auth.py:96-150)
- **From**: plan.md [ARCHITECTURE] section

**T005** [P] Create test file skeletons
- **Files**:
  - `tests/unit/test_account_data.py` (import pytest, unittest.mock)
  - `tests/integration/test_account_integration.py`
- **Pattern**: Follow tests/unit/test_robinhood_auth.py structure
- **From**: plan.md [TESTING STRATEGY] section

---

### Phase 3.2: RED - Data Models (T006-T010)

**T006** [RED] Write failing test: Position dataclass with profit calculation
- **File**: `tests/unit/test_account_data.py`
- **Test**:
  ```python
  def test_position_profit_calculation():
      """Test Position calculates profit correctly."""
      # GIVEN: Position with gain
      position = Position(
          symbol="AAPL",
          quantity=10,
          average_buy_price=Decimal("150.00"),
          current_price=Decimal("155.00"),
          # ... other fields will fail - not implemented yet
      )

      # WHEN: P&L calculated
      profit_loss = position.profit_loss

      # THEN: Profit is $50 (10 shares × $5 gain)
      assert profit_loss == Decimal("50.00")
  ```
- **Expected**: ModuleNotFoundError (Position not defined)
- **Pattern**: tests/unit/test_robinhood_auth.py:23-48
- **From**: spec.md FR-002, plan.md [SCHEMA]

**T007** [RED] Write failing test: Position dataclass with loss calculation
- **File**: `tests/unit/test_account_data.py`
- **Test**: Position with current_price < average_buy_price
- **Expected**: ModuleNotFoundError
- **Scenario**: 10 shares, bought at $150, now $145 → loss of $50
- **From**: spec.md FR-002

**T008** [RED] Write failing test: Position P&L percentage calculation
- **File**: `tests/unit/test_account_data.py`
- **Test**: Position.profit_loss_pct = (P&L / cost_basis) × 100
- **Expected**: ModuleNotFoundError
- **Scenario**: $50 profit on $1500 cost basis → 3.33%
- **From**: spec.md FR-002

**T009** [RED] Write failing test: AccountBalance dataclass fields
- **File**: `tests/unit/test_account_data.py`
- **Test**: AccountBalance with cash, equity, buying_power, last_updated
- **Expected**: ModuleNotFoundError
- **From**: spec.md FR-003, plan.md [SCHEMA]

**T010** [RED] Write failing test: CacheEntry dataclass with TTL
- **File**: `tests/unit/test_account_data.py`
- **Test**: CacheEntry stores value, cached_at, ttl_seconds
- **Expected**: ModuleNotFoundError
- **From**: spec.md FR-005, plan.md [SCHEMA]

---

### Phase 3.3: GREEN - Data Models Implementation (T011-T015)

**T011** [GREEN→T006,T007,T008] Implement Position dataclass
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  from dataclasses import dataclass
  from decimal import Decimal
  from datetime import datetime

  @dataclass
  class Position:
      """Equity position with P&L calculation."""
      symbol: str
      quantity: int
      average_buy_price: Decimal
      current_price: Decimal
      last_updated: datetime

      @property
      def cost_basis(self) -> Decimal:
          return Decimal(self.quantity) * self.average_buy_price

      @property
      def current_value(self) -> Decimal:
          return Decimal(self.quantity) * self.current_price

      @property
      def profit_loss(self) -> Decimal:
          return self.current_value - self.cost_basis

      @property
      def profit_loss_pct(self) -> Decimal:
          if self.cost_basis == 0:
              return Decimal("0")
          return (self.profit_loss / self.cost_basis) * 100
  ```
- **Verify**: T006, T007, T008 now pass
- **Pattern**: SafetyResult dataclass (safety_checks.py:64-78)
- **From**: plan.md [SCHEMA]

**T012** [GREEN→T009] Implement AccountBalance dataclass
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  @dataclass
  class AccountBalance:
      """Account balance breakdown."""
      cash: Decimal
      equity: Decimal
      buying_power: Decimal
      last_updated: datetime
  ```
- **Verify**: T009 now passes
- **From**: plan.md [SCHEMA]

**T013** [GREEN→T010] Implement CacheEntry dataclass
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  @dataclass
  class CacheEntry:
      """Cache entry with TTL."""
      value: Any
      cached_at: datetime
      ttl_seconds: int
  ```
- **Verify**: T010 now passes
- **From**: plan.md [SCHEMA]

**T014** [P] Export data models from __init__.py
- **File**: `src/trading_bot/account/__init__.py`
- **Code**:
  ```python
  from src.trading_bot.account.account_data import (
      AccountData,
      AccountDataError,
      Position,
      AccountBalance,
  )

  __all__ = ["AccountData", "AccountDataError", "Position", "AccountBalance"]
  ```
- **Pattern**: auth/__init__.py:12-14
- **From**: plan.md [STRUCTURE]

**T015** [P] Run mypy type checking on data models
- **Command**: `mypy src/trading_bot/account/ --strict`
- **Expected**: No errors (all types properly annotated)
- **Fix**: Add type hints where missing
- **From**: spec.md NFR-006

---

### Phase 3.4: RED - Cache Logic (T016-T020)

**T016** [RED] Write failing test: Cache miss triggers API fetch
- **File**: `tests/unit/test_account_data.py`
- **Test**:
  ```python
  @patch('robin_stocks.robinhood.account.load_account_profile')
  def test_cache_miss_fetches_from_api(mock_api):
      """Test cache miss triggers API call."""
      # GIVEN: Empty cache
      mock_api.return_value = {'buying_power': '10000.50'}
      account = AccountData(auth=mock_auth)

      # WHEN: get_buying_power called
      result = account.get_buying_power()

      # THEN: API called and result returned
      assert result == 10000.50
      mock_api.assert_called_once()
  ```
- **Expected**: AttributeError (get_buying_power not implemented)
- **Pattern**: tests/unit/test_robinhood_auth.py:114-154
- **From**: spec.md FR-005

**T017** [RED] Write failing test: Cache hit returns cached value
- **File**: `tests/unit/test_account_data.py`
- **Test**: Call get_buying_power twice, API called only once
- **Expected**: AttributeError
- **Scenario**: First call caches, second call uses cache
- **From**: spec.md FR-005

**T018** [RED] Write failing test: Stale cache (expired TTL) triggers refetch
- **File**: `tests/unit/test_account_data.py`
- **Test**: Mock time, cache entry older than TTL → API called again
- **Expected**: AttributeError
- **From**: spec.md FR-005

**T019** [RED] Write failing test: Manual cache invalidation clears specific key
- **File**: `tests/unit/test_account_data.py`
- **Test**: invalidate_cache('buying_power') → next call fetches fresh
- **Expected**: AttributeError
- **From**: spec.md FR-005

**T020** [RED] Write failing test: Manual cache invalidation clears all keys
- **File**: `tests/unit/test_account_data.py`
- **Test**: invalidate_cache(None) → all caches cleared
- **Expected**: AttributeError
- **From**: spec.md FR-005

---

### Phase 3.5: GREEN - Cache Implementation (T021-T025)

**T021** [GREEN→T016,T017,T018,T019,T020] Implement cache helper methods
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  def _is_cache_valid(self, key: str) -> bool:
      """Check if cache entry is valid (not expired)."""
      if key not in self._cache:
          return False

      entry = self._cache[key]
      age_seconds = (datetime.utcnow() - entry.cached_at).total_seconds()
      return age_seconds < entry.ttl_seconds

  def _update_cache(self, key: str, value: Any, ttl_seconds: int) -> None:
      """Update cache with new value and timestamp."""
      self._cache[key] = CacheEntry(
          value=value,
          cached_at=datetime.utcnow(),
          ttl_seconds=ttl_seconds
      )

  def invalidate_cache(self, cache_type: Optional[str] = None) -> None:
      """Invalidate cache (all or specific type)."""
      if cache_type is None:
          self._cache.clear()
      elif cache_type in self._cache:
          del self._cache[cache_type]
  ```
- **Verify**: T019, T020 now pass (invalidate_cache tests)
- **From**: plan.md [ARCHITECTURE] Cache Layer

**T022** [GREEN→T016] Implement get_buying_power with cache
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  def get_buying_power(self, use_cache: bool = True) -> float:
      """Fetch current buying power with optional caching."""
      cache_key = 'buying_power'

      # Check cache if enabled
      if use_cache and self._is_cache_valid(cache_key):
          return self._cache[cache_key].value

      # Fetch from API
      buying_power = self._fetch_buying_power()

      # Update cache
      self._update_cache(cache_key, buying_power, ttl_seconds=60)

      return buying_power

  def _fetch_buying_power(self) -> float:
      """Fetch buying power from robin-stocks API."""
      import robin_stocks.robinhood as rh
      profile = rh.account.load_account_profile()
      return float(profile['buying_power'])
  ```
- **Verify**: T016 now passes (cache miss test)
- **From**: spec.md FR-001

**T023** [GREEN→T017] Add cache hit behavior
- **Action**: No code change needed - T017 should pass with T022 implementation
- **Verify**: Second call to get_buying_power uses cache (API not called)
- **From**: spec.md FR-005

**T024** [GREEN→T018] Add TTL expiry logic
- **Action**: No code change needed - _is_cache_valid already checks TTL
- **Verify**: Mock time.time(), advance past TTL → cache refetches
- **From**: spec.md FR-005

**T025** [P] Add logging for cache operations
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  import logging
  logger = logging.getLogger(__name__)

  # In get_buying_power:
  if use_cache and self._is_cache_valid(cache_key):
      logger.debug(f"Cache hit: {cache_key}")
      return self._cache[cache_key].value

  logger.debug(f"Cache miss: {cache_key}, fetching from API")
  ```
- **Pattern**: auth/robinhood_auth.py logging style
- **From**: spec.md NFR-004

---

### Phase 3.6: RED - API Fetching (T026-T032)

**T026** [RED] Write failing test: Fetch positions from API
- **File**: `tests/unit/test_account_data.py`
- **Test**:
  ```python
  @patch('robin_stocks.robinhood.account.build_holdings')
  def test_fetch_positions_returns_list(mock_api):
      """Test get_positions returns list of Position objects."""
      # GIVEN: API returns holdings
      mock_api.return_value = {
          'AAPL': {
              'quantity': '10',
              'average_buy_price': '150.25',
              'price': '155.00',
              'equity': '1550.00'
          }
      }

      # WHEN: get_positions called
      positions = account.get_positions()

      # THEN: Returns list with Position object
      assert len(positions) == 1
      assert positions[0].symbol == 'AAPL'
      assert positions[0].quantity == 10
      assert positions[0].profit_loss == Decimal("47.50")
  ```
- **Expected**: AttributeError (get_positions not implemented)
- **From**: spec.md FR-002

**T027** [RED] Write failing test: Empty positions returns empty list
- **File**: `tests/unit/test_account_data.py`
- **Test**: build_holdings returns {} → get_positions returns []
- **Expected**: AttributeError
- **From**: spec.md FR-002 edge case

**T028** [RED] Write failing test: Fetch account balance from API
- **File**: `tests/unit/test_account_data.py`
- **Test**: get_account_balance returns AccountBalance object
- **Expected**: AttributeError
- **From**: spec.md FR-003

**T029** [RED] Write failing test: Fetch day trade count from API
- **File**: `tests/unit/test_account_data.py`
- **Test**: get_day_trade_count returns int (0-3)
- **Expected**: AttributeError
- **From**: spec.md FR-004

**T030** [RED] Write failing test: Network error triggers retry
- **File**: `tests/unit/test_account_data.py`
- **Test**:
  ```python
  @patch('robin_stocks.robinhood.account.load_account_profile')
  @patch('time.sleep')  # Mock sleep to speed up test
  def test_network_error_retries_with_backoff(mock_sleep, mock_api):
      """Test network error triggers exponential backoff retry."""
      # GIVEN: 2 network errors, then success
      mock_api.side_effect = [
          Exception("Network timeout"),
          Exception("Network timeout"),
          {'buying_power': '10000.50'}
      ]

      # WHEN: get_buying_power called
      result = account.get_buying_power(use_cache=False)

      # THEN: Retried 3 times, succeeded
      assert result == 10000.50
      assert mock_api.call_count == 3
      assert mock_sleep.call_count == 2  # Slept after 1st and 2nd attempt
      mock_sleep.assert_any_call(1.0)  # 1s after 1st failure
      mock_sleep.assert_any_call(2.0)  # 2s after 2nd failure
  ```
- **Expected**: Test fails (no retry logic)
- **Pattern**: tests/unit/test_robinhood_auth.py:532-584
- **From**: spec.md NFR-002

**T031** [RED] Write failing test: Rate limit (429) triggers backoff
- **File**: `tests/unit/test_account_data.py`
- **Test**: Mock 429 response → exponential backoff → retry
- **Expected**: Test fails
- **From**: spec.md NFR-002

**T032** [RED] Write failing test: Invalid API response raises AccountDataError
- **File**: `tests/unit/test_account_data.py`
- **Test**: Malformed JSON or missing fields → AccountDataError
- **Expected**: Test fails (no validation)
- **From**: spec.md FR-007

---

### Phase 3.7: GREEN - API Implementation (T033-T039)

**T033** [GREEN→T026,T027] Implement get_positions with caching
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  def get_positions(self, use_cache: bool = True) -> List[Position]:
      """Fetch all positions with P&L calculations."""
      cache_key = 'positions'

      if use_cache and self._is_cache_valid(cache_key):
          logger.debug(f"Cache hit: {cache_key}")
          return self._cache[cache_key].value

      logger.debug(f"Cache miss: {cache_key}, fetching from API")
      positions = self._fetch_positions()
      self._update_cache(cache_key, positions, ttl_seconds=60)

      return positions

  def _fetch_positions(self) -> List[Position]:
      """Fetch positions from robin-stocks API."""
      import robin_stocks.robinhood as rh
      holdings = rh.account.build_holdings()

      positions = []
      for symbol, data in holdings.items():
          position = Position(
              symbol=symbol,
              quantity=int(float(data['quantity'])),
              average_buy_price=Decimal(data['average_buy_price']),
              current_price=Decimal(data['price']),
              last_updated=datetime.utcnow()
          )
          positions.append(position)

      return positions
  ```
- **Verify**: T026, T027 now pass
- **From**: spec.md FR-002

**T034** [GREEN→T028] Implement get_account_balance with caching
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  def get_account_balance(self, use_cache: bool = True) -> AccountBalance:
      """Fetch account balance breakdown."""
      cache_key = 'account_balance'

      if use_cache and self._is_cache_valid(cache_key):
          logger.debug(f"Cache hit: {cache_key}")
          return self._cache[cache_key].value

      logger.debug(f"Cache miss: {cache_key}, fetching from API")
      balance = self._fetch_account_balance()
      self._update_cache(cache_key, balance, ttl_seconds=60)

      return balance

  def _fetch_account_balance(self) -> AccountBalance:
      """Fetch account balance from robin-stocks API."""
      import robin_stocks.robinhood as rh
      profile = rh.account.load_account_profile()

      return AccountBalance(
          cash=Decimal(profile['cash']),
          equity=Decimal(profile['equity']),
          buying_power=Decimal(profile['buying_power']),
          last_updated=datetime.utcnow()
      )
  ```
- **Verify**: T028 now passes
- **From**: spec.md FR-003

**T035** [GREEN→T029] Implement get_day_trade_count with caching
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  def get_day_trade_count(self, use_cache: bool = True) -> int:
      """Fetch day trade count (PDT tracking)."""
      cache_key = 'day_trade_count'

      if use_cache and self._is_cache_valid(cache_key):
          logger.debug(f"Cache hit: {cache_key}")
          return self._cache[cache_key].value

      logger.debug(f"Cache miss: {cache_key}, fetching from API")
      count = self._fetch_day_trade_count()
      self._update_cache(cache_key, count, ttl_seconds=300)  # 5 min TTL

      return count

  def _fetch_day_trade_count(self) -> int:
      """Fetch day trade count from robin-stocks API."""
      import robin_stocks.robinhood as rh
      profile = rh.account.load_account_profile()
      return int(profile['day_trade_count'])
  ```
- **Verify**: T029 now passes
- **From**: spec.md FR-004

**T036** [GREEN→T030,T031] Add exponential backoff retry to API fetches
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  # REUSE _retry_with_backoff from auth module
  # Can extract to shared utils or copy pattern

  def _fetch_buying_power(self) -> float:
      """Fetch buying power from robin-stocks API with retry."""
      def _fetch():
          import robin_stocks.robinhood as rh
          profile = rh.account.load_account_profile()
          return float(profile['buying_power'])

      # Apply retry with exponential backoff (1s, 2s, 4s)
      return _retry_with_backoff(_fetch, max_attempts=3, base_delay=1.0)
  ```
- **Verify**: T030, T031 now pass
- **REUSE**: auth/robinhood_auth.py:40-76 (_retry_with_backoff pattern)
- **From**: spec.md NFR-002

**T037** [GREEN→T032] Add API response validation
- **File**: `src/trading_bot/account/account_data.py`
- **Code**:
  ```python
  def _fetch_buying_power(self) -> float:
      """Fetch buying power with validation."""
      def _fetch():
          import robin_stocks.robinhood as rh
          profile = rh.account.load_account_profile()

          # Validate response structure
          if not profile or 'buying_power' not in profile:
              raise AccountDataError("Invalid API response: missing buying_power")

          try:
              return float(profile['buying_power'])
          except (ValueError, TypeError) as e:
              raise AccountDataError(f"Invalid buying_power value: {e}")

      return _retry_with_backoff(_fetch, max_attempts=3, base_delay=1.0)
  ```
- **Verify**: T032 now passes
- **From**: spec.md FR-007

**T038** [P] Apply retry and validation to all fetch methods
- **Action**: Wrap _fetch_positions, _fetch_account_balance, _fetch_day_trade_count with _retry_with_backoff
- **Verify**: All API fetch tests pass with retry behavior
- **From**: spec.md NFR-002

**T039** [P] Run all unit tests
- **Command**: `pytest tests/unit/test_account_data.py -v`
- **Expected**: All 25-30 tests passing
- **Coverage**: `pytest tests/unit/test_account_data.py --cov=src/trading_bot/account --cov-report=term-missing`
- **Target**: ≥90% coverage
- **From**: spec.md NFR-005

---

### Phase 3.8: REFACTOR - Type Hints & Logging (T040-T043)

**T040** [REFACTOR] Add comprehensive type hints to all methods
- **File**: `src/trading_bot/account/account_data.py`
- **Action**: Add type hints to all parameters and return values
- **Verify**: `mypy src/trading_bot/account/ --strict` passes with no errors
- **Pattern**: auth/robinhood_auth.py type hint style
- **From**: spec.md NFR-006

**T041** [REFACTOR] Add comprehensive logging to all operations
- **File**: `src/trading_bot/account/account_data.py`
- **Add**:
  ```python
  # On cache hit
  logger.debug(f"Cache hit: {cache_key} (age: {age}s, TTL: {ttl}s)")

  # On cache miss
  logger.info(f"Fetching {cache_key} from API")

  # On successful fetch
  logger.info(f"Fetched {cache_key}: {masked_value}")

  # On error
  logger.error(f"Failed to fetch {cache_key}: {error}")
  ```
- **Pattern**: auth/robinhood_auth.py logging style
- **From**: spec.md NFR-004

**T042** [REFACTOR] Add docstrings to all public methods
- **File**: `src/trading_bot/account/account_data.py`
- **Style**: Google-style docstrings with Args, Returns, Raises sections
- **Pattern**: auth/robinhood_auth.py docstring style
- **From**: spec.md NFR-006

**T043** [REFACTOR] Extract _retry_with_backoff to shared utils (optional)
- **Action**: Move to src/trading_bot/utils/retry.py if reused across modules
- **Benefit**: Single source of truth for retry logic
- **Alternative**: Keep inline if only used in account_data
- **From**: plan.md Decision 3

---

### Phase 3.9: Integration - Bot & SafetyChecks (T044-T052)

**T044** [P] Update TradingBot to initialize AccountData
- **File**: `src/trading_bot/bot.py`
- **Change** (lines ~129-133):
  ```python
  # Add after auth initialization
  self.account_data: Optional[AccountData] = None
  if self.auth is not None:
      from src.trading_bot.account import AccountData
      self.account_data = AccountData(auth=self.auth)
      logger.info("Account data module initialized")
  ```
- **Pattern**: Follow auth initialization pattern (bot.py:130-133)
- **From**: plan.md [INTEGRATION POINTS]

**T045** [P] Replace bot.get_buying_power() mock with real implementation
- **File**: `src/trading_bot/bot.py`
- **Change** (lines 240-251):
  ```python
  def get_buying_power(self) -> float:
      """Get current buying power from account."""
      if self.account_data is None:
          # Fallback for backward compatibility
          logger.warning("AccountData not initialized, using mock value")
          return 10000.00  # Mock value
      return self.account_data.get_buying_power()
  ```
- **Verify**: bot.get_buying_power() returns real value when authenticated
- **From**: plan.md [INTEGRATION POINTS]

**T046** [P] Add cache invalidation to bot.execute_trade()
- **File**: `src/trading_bot/bot.py`
- **Change** (after line 324):
  ```python
  # After successful trade execution
  if self.account_data is not None:
      self.account_data.invalidate_cache('buying_power')
      self.account_data.invalidate_cache('positions')
      logger.debug("Account cache invalidated after trade")
  ```
- **Verify**: Trade execution clears cache
- **From**: plan.md [INTEGRATION POINTS]

**T047** [RED] Write integration test: Bot uses real buying power
- **File**: `tests/integration/test_account_integration.py`
- **Test**:
  ```python
  @patch('robin_stocks.robinhood.account.load_account_profile')
  def test_bot_uses_real_buying_power(mock_api):
      """Test bot.get_buying_power() returns real value (not $10k mock)."""
      # GIVEN: Authenticated bot with AccountData
      mock_api.return_value = {'buying_power': '15000.50'}
      config = Mock()
      config.robinhood_username = "user@example.com"
      config.robinhood_password = "password"

      bot = TradingBot(config=config, paper_trading=True)

      # WHEN: get_buying_power called
      buying_power = bot.get_buying_power()

      # THEN: Returns real value, not $10k mock
      assert buying_power == 15000.50
      assert buying_power != 10000.00  # Not the mock value
  ```
- **Expected**: Test fails (integration not complete)
- **From**: plan.md [INTEGRATION SCENARIOS]

**T048** [GREEN→T047] Fix bot initialization to work with tests
- **Action**: Ensure bot.start() authenticates properly in integration tests
- **Verify**: T047 passes
- **From**: plan.md [INTEGRATION POINTS]

**T049** [RED] Write integration test: Trade execution invalidates cache
- **File**: `tests/integration/test_account_integration.py`
- **Test**: execute_trade() → get_buying_power() fetches fresh data (API called again)
- **Expected**: Test fails
- **From**: plan.md [INTEGRATION SCENARIOS]

**T050** [GREEN→T049] Verify cache invalidation works
- **Action**: No code change needed - T046 already implemented
- **Verify**: T049 passes
- **From**: plan.md [INTEGRATION POINTS]

**T051** [P] Update SafetyChecks to accept AccountData
- **File**: `src/trading_bot/safety_checks.py`
- **Change** (line ~100):
  ```python
  def __init__(self, config, account_data: Optional[AccountData] = None):
      self.config = config
      self.account_data = account_data
      # ... existing init code
  ```
- **From**: plan.md [INTEGRATION POINTS]

**T052** [P] Update SafetyChecks.validate_trade() to use AccountData
- **File**: `src/trading_bot/safety_checks.py`
- **Change** (in validate_trade method):
  ```python
  def validate_trade(self, symbol, action, quantity, price, current_buying_power=None):
      # Fetch buying_power from AccountData if not provided
      if current_buying_power is None and self.account_data is not None:
          current_buying_power = self.account_data.get_buying_power()

      # ... existing validation logic
  ```
- **From**: plan.md [INTEGRATION POINTS]

---

### Phase 3.10: Testing & Coverage (T053-T056)

**T053** [P] Run full test suite
- **Command**: `pytest tests/ -v`
- **Expected**: All tests passing (unit + integration)
- **Fix**: Any failing tests
- **From**: spec.md NFR-005

**T054** [P] Check test coverage
- **Command**: `pytest tests/unit/test_account_data.py --cov=src/trading_bot/account --cov-report=html`
- **Target**: ≥90% line coverage
- **Action**: Add tests for uncovered lines
- **From**: spec.md NFR-005

**T055** [P] Run type checking
- **Command**: `mypy src/trading_bot/account/ --strict`
- **Expected**: No errors
- **Fix**: Add missing type hints
- **From**: spec.md NFR-006

**T056** [P] Run linter
- **Command**: `ruff check src/trading_bot/account/`
- **Expected**: No errors
- **Fix**: Address linting issues
- **From**: Constitution v1.0.0 §Code_Quality

---

### Phase 3.11: Documentation (T057-T059)

**T057** [P] Update NOTES.md with implementation summary
- **File**: `specs/account-data-module/NOTES.md`
- **Add**: Phase 3 checkpoint (implementation complete)
- **Include**: Final test count, coverage metrics, integration status
- **From**: Workflow standard

**T058** [P] Update error-log.md with any errors encountered
- **File**: `specs/account-data-module/error-log.md`
- **Action**: Document any errors from implementation (if any)
- **Format**: Use error template in file
- **From**: Workflow standard

**T059** [P] Create DEPLOYMENT_READY.md checklist
- **File**: `specs/account-data-module/DEPLOYMENT_READY.md`
- **Content**: Deployment checklist, rollback procedure, success criteria
- **Pattern**: specs/authentication-module/DEPLOYMENT_READY.md
- **From**: plan.md [DEPLOYMENT ACCEPTANCE]

---

### Phase 3.12: Final Validation (T060)

**T060** [P] Run comprehensive validation
- **Actions**:
  1. `pytest tests/ -v` (all tests pass)
  2. `pytest --cov=src/trading_bot/account --cov-report=term-missing` (≥90% coverage)
  3. `mypy src/trading_bot/account/ --strict` (no type errors)
  4. `ruff check src/trading_bot/account/` (no linting errors)
  5. Manual test: Start bot, verify real buying power returned
- **Success criteria**: All checks pass
- **From**: spec.md Success Criteria

---

## Task Dependencies

**Sequential (must complete in order)**:
- T001-T005 (Setup) → T006-T010 (RED Data Models) → T011-T015 (GREEN Data Models)
- T016-T020 (RED Cache) → T021-T025 (GREEN Cache)
- T026-T032 (RED API) → T033-T039 (GREEN API)
- T040-T043 (REFACTOR)
- T044-T052 (Integration)
- T053-T056 (Testing)
- T057-T059 (Documentation)
- T060 (Final Validation)

**Parallel (can work simultaneously)**:
- Within each RED phase, tests can be written in parallel
- Within each GREEN phase, implementations can be done in parallel if independent
- Documentation tasks (T057-T059) can be done in parallel

---

## Test Coverage Requirements

**Target**: ≥90% line coverage

**Test Categories**:
1. Data Models (5 tests): T006-T010
2. Cache Logic (5 tests): T016-T020
3. API Fetching (7 tests): T026-T032
4. Integration (5 tests): T047-T050 + additional

**Total Tests**: ~30-35 tests

**Coverage Breakdown**:
- Position dataclass: 100% (profit/loss calculations)
- AccountBalance dataclass: 100%
- CacheEntry dataclass: 100%
- Cache methods: 100% (hit, miss, stale, invalidate)
- API fetch methods: 100% (success, retry, error)
- Integration: 100% (bot, SafetyChecks)

---

## Success Criteria

- [ ] All 60 tasks completed
- [ ] All tests passing (unit + integration)
- [ ] Test coverage ≥90%
- [ ] mypy passes with --strict
- [ ] ruff linting passes
- [ ] Bot.get_buying_power() returns real value (not $10k mock)
- [ ] Trade execution invalidates cache
- [ ] SafetyChecks uses real buying power
- [ ] DEPLOYMENT_READY.md created with checklist

---

**Generated**: 2025-01-08
**Next Phase**: `/analyze` (validate architecture and identify risks)
