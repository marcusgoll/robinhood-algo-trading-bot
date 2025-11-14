# Specification: Account Data Module

**Feature**: account-data-module
**Type**: Backend / Account Management
**Area**: api
**Blocked by**: authentication-module (✅ SHIPPED)
**Constitution**: v1.0.0

---

## Overview

Implements account data fetching from Robinhood API to provide real-time portfolio information, buying power, positions with P&L, and day trade count tracking. This module is critical for risk management and trading decisions.

**Problem**: Bot currently uses mocked buying power ($10k hardcoded in bot.py:251) and cannot access real account data. This prevents:
- Accurate position sizing based on actual buying power
- Portfolio P&L tracking
- Position monitoring with current values
- Day trade count enforcement (§Risk_Management)
- Real-time account balance validation

**Solution**: Account data service that fetches portfolio information using authenticated robin-stocks API calls, caches data to minimize API calls, provides typed data models for account information, and integrates seamlessly with existing SafetyChecks and TradingBot modules.

---

## User Scenarios

### Scenario 1: Fetch Buying Power for Trade Validation
**Given** bot is authenticated with Robinhood
**When** bot validates a trade via SafetyChecks.validate_trade()
**Then** account data service:
- Fetches current buying power from API
- Returns actual available cash amount
- Updates cached value for next check
**And** SafetyChecks uses real buying power (not $10k mock)

### Scenario 2: Get All Open Positions with P&L
**Given** user has open positions in Robinhood account
**When** bot requests position data
**Then** account data service:
- Fetches all equity positions from API
- Calculates current P&L for each position (current_price - avg_buy_price) × quantity
- Returns list of positions with symbol, quantity, entry price, current price, P&L
**And** logs "Fetched X positions" to audit trail

### Scenario 3: Check Day Trade Count Before Trade
**Given** bot is planning to execute a day trade
**When** bot checks if day trade limit will be exceeded
**Then** account data service:
- Fetches account profile with day_trade_count
- Compares against PDT limit (3 day trades per 5 rolling days)
- Returns True if safe to trade, False if PDT limit reached
**And** logs "Day trade count: X/3" (§Risk_Management)

### Scenario 4: Retrieve Total Account Balance
**Given** bot needs to calculate circuit breaker thresholds
**When** bot requests account balance
**Then** account data service:
- Fetches account profile from API
- Returns total equity (cash + positions market value)
- Caches balance for performance
**And** SafetyChecks uses actual portfolio value for daily loss % calculation

### Scenario 5: Cache Invalidation on Trade Execution
**Given** account data is cached from previous fetch
**And** bot executes a trade (buy or sell)
**When** trade completes
**Then** account data service:
- Invalidates cached buying power
- Invalidates cached positions
- Forces fresh fetch on next request
**And** ensures data accuracy after account changes

### Scenario 6: API Rate Limit Handling
**Given** bot makes multiple rapid API calls
**And** Robinhood rate limit is reached (429 Too Many Requests)
**When** API returns rate limit error
**Then** account data service:
- Detects 429 response
- Waits with exponential backoff (1s, 2s, 4s)
- Retries request after cooldown
**And** logs "Rate limit hit, retrying in Xs"

### Scenario 7: Stale Data Detection
**Given** cached account data is older than 5 minutes
**When** bot requests account data
**Then** account data service:
- Detects cache is stale (last_fetch > 5 minutes ago)
- Fetches fresh data from API
- Updates cache with new data and timestamp
**And** logs "Cache stale, refreshing data"

---

## Requirements

### Functional Requirements

**FR-001: Buying Power Fetching**
- MUST fetch current buying power from robin-stocks API
- MUST return buying_power as float (available cash for trades)
- MUST cache buying power for 60 seconds to minimize API calls
- MUST invalidate cache on trade execution
- MUST handle API errors gracefully (return cached value or raise)

**FR-002: Position Tracking**
- MUST fetch all equity positions from robin-stocks API
- MUST return list of Position objects with:
  - symbol: str
  - quantity: int
  - average_buy_price: Decimal
  - current_price: Decimal
  - current_value: Decimal (quantity × current_price)
  - total_equity: Decimal (current_value for position)
  - profit_loss: Decimal (current_value - cost_basis)
  - profit_loss_pct: Decimal (P&L as percentage)
- MUST calculate P&L for each position
- MUST cache positions for 60 seconds
- MUST handle empty positions list (no open positions)

**FR-003: Account Balance Retrieval**
- MUST fetch total account equity from robin-stocks API
- MUST return account_balance as Decimal (cash + positions market value)
- MUST cache balance for 60 seconds
- MUST provide both cash balance and total equity
- MUST handle API errors with cached fallback

**FR-004: Day Trade Count Checking**
- MUST fetch day_trade_count from account profile API
- MUST return current count as int (0-3 for non-PDT accounts)
- MUST warn if count ≥ 3 (PDT threshold)
- MUST cache count for 5 minutes (changes infrequently)
- MUST log day trade count on each check (§Risk_Management)

**FR-005: Cache Management**
- MUST implement TTL-based cache (time-to-live)
- MUST support configurable cache durations per data type
- MUST provide invalidate_cache() method for forced refresh
- MUST track last_fetch timestamp for staleness detection
- MUST handle concurrent cache access safely

**FR-006: Integration with TradingBot**
- MUST replace bot.get_buying_power() mock with real implementation
- MUST integrate with SafetyChecks.validate_trade() for buying power validation
- MUST provide positions to status dashboard (when implemented)
- MUST support circuit breaker daily loss calculations

**FR-007: Data Validation**
- MUST validate all API responses for expected structure
- MUST handle missing fields gracefully (default values)
- MUST raise ValueError for invalid data types
- MUST sanitize inputs before API calls

### Non-Functional Requirements

**NFR-001: Performance**
- API calls SHOULD complete in <2 seconds under normal network conditions
- Cache hits MUST return in <10ms
- MUST minimize API calls via intelligent caching (target: <10 calls/minute)
- MUST NOT block trading operations during data fetch

**NFR-002: Reliability (§Error_Handling)**
- MUST handle network errors with exponential backoff retry (1s, 2s, 4s)
- MUST handle API rate limits (429) with backoff
- MUST handle authentication errors (401) with re-auth trigger
- MUST provide cached data as fallback when API unavailable
- MUST fail gracefully with clear error messages

**NFR-003: Security (§Security)**
- MUST use authenticated robin-stocks session only
- MUST NOT log sensitive account numbers
- MUST NOT expose internal account IDs
- MUST mask account values in logs (§Audit_Everything)

**NFR-004: Auditability (§Audit_Everything)**
- MUST log all API calls with timestamps
- MUST log cache hits vs misses
- MUST log cache invalidations
- MUST log day trade count checks
- MUST include operation context in logs

**NFR-005: Test Coverage (§Testing_Requirements)**
- MUST achieve ≥90% test coverage
- MUST test all API fetch scenarios
- MUST test cache behavior (hit, miss, stale, invalidation)
- MUST test error handling (network, rate limit, auth)
- MUST test integration with TradingBot and SafetyChecks

**NFR-006: Type Safety (§Code_Quality)**
- MUST use type hints on all functions
- MUST pass mypy strict mode
- MUST use dataclasses for data models

---

## Technical Design

### Architecture

```
AccountData Class
├── __init__(auth: RobinhoodAuth)
├── get_buying_power(use_cache: bool = True) → float
├── get_positions(use_cache: bool = True) → List[Position]
├── get_account_balance(use_cache: bool = True) → Decimal
├── get_day_trade_count(use_cache: bool = True) → int
├── invalidate_cache(cache_type: Optional[str] = None) → None
├── _fetch_buying_power() → float
├── _fetch_positions() → List[Position]
├── _fetch_account_balance() → Decimal
├── _fetch_day_trade_count() → int
├── _is_cache_valid(key: str) → bool
└── _update_cache(key: str, value: Any) → None
```

### Data Models

```python
@dataclass
class Position:
    """Equity position with P&L calculation."""
    symbol: str
    quantity: int
    average_buy_price: Decimal
    current_price: Decimal
    current_value: Decimal  # quantity × current_price
    cost_basis: Decimal  # quantity × average_buy_price
    profit_loss: Decimal  # current_value - cost_basis
    profit_loss_pct: Decimal  # (P&L / cost_basis) × 100
    last_updated: datetime

@dataclass
class AccountBalance:
    """Account balance breakdown."""
    cash: Decimal  # Available cash
    equity: Decimal  # Total equity (cash + positions)
    buying_power: Decimal  # Available for trades
    last_updated: datetime

@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    value: Any
    cached_at: datetime
    ttl_seconds: int
```

### Dependencies

**External Libraries**:
- `robin-stocks==3.0.5` (already in requirements.txt)
- Standard library: `datetime`, `typing`, `dataclasses`, `decimal`

**Internal Modules**:
- `src/trading_bot/auth/robinhood_auth.py`: RobinhoodAuth for authenticated API calls
- `src/trading_bot/bot.py`: TradingBot integration (replace get_buying_power mock)
- `src/trading_bot/safety_checks.py`: SafetyChecks integration (buying power validation)

### API Mapping

**robin-stocks API Reference**:

```python
# Buying power
robin_stocks.robinhood.account.load_account_profile()['buying_power']

# Positions
robin_stocks.robinhood.account.build_holdings()
# Returns: {
#   'AAPL': {
#     'quantity': '10',
#     'average_buy_price': '150.25',
#     'equity': '1550.00',
#     'percent_change': '3.25',
#     'price': '155.00',
#     ...
#   }
# }

# Account balance
robin_stocks.robinhood.account.load_account_profile()['equity']

# Day trade count
robin_stocks.robinhood.account.load_account_profile()['day_trade_count']
```

### Cache Strategy

**Cache TTLs**:
- `buying_power`: 60 seconds (changes on trades)
- `positions`: 60 seconds (changes on trades and price updates)
- `account_balance`: 60 seconds (changes on trades)
- `day_trade_count`: 300 seconds (5 minutes - changes infrequently)

**Cache Invalidation**:
- Manual: `invalidate_cache(cache_type='buying_power')`
- Automatic: On trade execution via bot integration
- Staleness: TTL expiry triggers auto-refresh

**Cache Implementation**:
```python
self._cache: Dict[str, CacheEntry] = {
    'buying_power': None,
    'positions': None,
    'account_balance': None,
    'day_trade_count': None,
}
```

---

## Implementation Plan

### Phase 1: Core Data Models (RED - Tests First)
1. Create `src/trading_bot/account/account_data.py`
2. Define Position dataclass with P&L calculations
3. Define AccountBalance dataclass
4. Define CacheEntry dataclass
5. Write failing tests for data models

### Phase 2: Cache Layer (RED)
1. Implement cache storage structure
2. Implement `_is_cache_valid()` with TTL check
3. Implement `_update_cache()` with timestamp
4. Implement `invalidate_cache()` for manual refresh
5. Write failing tests for cache behavior

### Phase 3: API Fetching (GREEN)
1. Implement `_fetch_buying_power()` using robin-stocks
2. Implement `_fetch_positions()` with P&L calculation
3. Implement `_fetch_account_balance()` using load_account_profile
4. Implement `_fetch_day_trade_count()` from profile
5. Add exponential backoff retry logic
6. Make cache tests pass

### Phase 4: Public API (GREEN)
1. Implement `get_buying_power(use_cache=True)`
2. Implement `get_positions(use_cache=True)`
3. Implement `get_account_balance(use_cache=True)`
4. Implement `get_day_trade_count(use_cache=True)`
5. Make all public API tests pass

### Phase 5: Integration (GREEN)
1. Update `bot.py` to use AccountData.get_buying_power()
2. Update SafetyChecks to accept AccountData instance
3. Update bot.execute_trade() to invalidate cache after trades
4. Make integration tests pass

### Phase 6: REFACTOR
1. Add comprehensive type hints
2. Extract common retry logic to helper
3. Add detailed logging for all operations
4. Optimize cache hit ratio

### Phase 7: Testing & Documentation
1. Write comprehensive unit tests (target: 90% coverage)
2. Write integration tests with bot and safety checks
3. Write error scenario tests (network, rate limit, auth)
4. Create NOTES.md with usage examples
5. Create DEPLOYMENT_READY.md checklist

---

## Testing Strategy

### Unit Tests (test_account_data.py)

**Data Model Tests**:
- ✅ Position dataclass → P&L calculated correctly
- ✅ Position with loss → negative P&L
- ✅ Position with gain → positive P&L
- ✅ AccountBalance → all fields populated

**Cache Tests**:
- ✅ Cache miss → fetch from API
- ✅ Cache hit (valid TTL) → return cached value
- ✅ Cache stale (expired TTL) → fetch fresh data
- ✅ Manual invalidation → force refresh
- ✅ Partial invalidation → only specified cache cleared

**API Fetch Tests**:
- ✅ Fetch buying power → returns float
- ✅ Fetch positions → returns list of Position objects
- ✅ Fetch account balance → returns Decimal
- ✅ Fetch day trade count → returns int (0-3)
- ✅ Empty positions → returns empty list
- ✅ Network error → retry with backoff
- ✅ Rate limit (429) → backoff and retry
- ✅ Auth error (401) → raise AuthenticationError

**P&L Calculation Tests**:
- ✅ Profit calculation → (current - entry) × quantity
- ✅ Loss calculation → negative P&L
- ✅ Percentage calculation → (P&L / cost_basis) × 100
- ✅ Zero quantity → 0 P&L

### Integration Tests (test_account_integration.py)

**Bot Integration**:
- ✅ Bot.get_buying_power() → returns real value (not $10k)
- ✅ Trade execution → cache invalidated
- ✅ SafetyChecks → uses real buying power
- ✅ Circuit breaker → uses real account balance

**Authentication Integration**:
- ✅ AccountData initialized with RobinhoodAuth
- ✅ API calls use authenticated session
- ✅ Re-auth on 401 error

### Performance Tests

**Cache Performance**:
- ✅ Cache hit → <10ms response time
- ✅ API call → <2s response time
- ✅ Multiple rapid calls → cache reduces API load

**Rate Limit Tests**:
- ✅ Excessive calls → trigger rate limit
- ✅ Rate limit → backoff and recover
- ✅ Cache → prevent rate limits

---

## Configuration

**No new environment variables required** - Uses existing RobinhoodAuth session.

**Optional Configuration** (future):
```python
# Cache TTLs (seconds)
ACCOUNT_CACHE_TTL_BUYING_POWER = 60
ACCOUNT_CACHE_TTL_POSITIONS = 60
ACCOUNT_CACHE_TTL_BALANCE = 60
ACCOUNT_CACHE_TTL_DAY_TRADES = 300
```

---

## Integration Points

### TradingBot.get_buying_power() Replacement

**Current (bot.py:240-251)**:
```python
def get_buying_power(self) -> float:
    """Get current buying power from account."""
    # TODO: Replace with real Robinhood API call
    return 10000.00  # $10k mock buying power
```

**New Implementation**:
```python
def get_buying_power(self) -> float:
    """Get current buying power from account."""
    if self.account_data is None:
        # Fallback for backward compatibility
        logger.warning("AccountData not initialized, using mock value")
        return 10000.00
    return self.account_data.get_buying_power()
```

### SafetyChecks Integration

**Update SafetyChecks.__init__()**:
```python
def __init__(self, config, account_data: Optional[AccountData] = None):
    self.config = config
    self.account_data = account_data
    # ... existing code
```

**Use real buying power in validate_trade()**:
```python
def validate_trade(self, symbol, action, quantity, price, current_buying_power=None):
    if current_buying_power is None and self.account_data:
        current_buying_power = self.account_data.get_buying_power()
    # ... existing validation logic
```

### Bot Integration

**Update TradingBot.__init__()**:
```python
def __init__(self, *, config=None, ...):
    # ... existing auth init

    # Initialize account data if authenticated
    self.account_data: Optional[AccountData] = None
    if self.auth is not None:
        self.account_data = AccountData(auth=self.auth)
        logger.info("Account data module initialized")

    # Pass account_data to SafetyChecks
    self.safety_checks = SafetyChecks(safety_config, account_data=self.account_data)
```

**Update execute_trade()**:
```python
def execute_trade(self, symbol, action, shares, price, reason):
    # ... existing validation

    # Invalidate cache after trade execution
    if self.account_data is not None:
        self.account_data.invalidate_cache('buying_power')
        self.account_data.invalidate_cache('positions')
        logger.debug("Account cache invalidated after trade")
```

---

## Deployment Considerations

### Dependencies
- ✅ No new external dependencies
- ✅ Uses existing robin-stocks==3.0.5
- ✅ Standard library only

### Breaking Changes
- ❌ **No breaking changes** (additive module)
- ✅ Backward compatible (TradingBot works with or without AccountData)
- ✅ SafetyChecks fallback to current_buying_power parameter

### Migration
- ✅ No database migration needed
- ✅ No state migration needed
- ✅ Cache is ephemeral (in-memory)

### Rollback
- ✅ Remove AccountData initialization from bot.py
- ✅ Remove account_data parameter from SafetyChecks
- ✅ Revert to $10k mock buying power
- ✅ No state cleanup required

### Performance Impact
- ✅ Minimal - API calls cached for 60-300 seconds
- ✅ Reduces network load vs frequent direct API calls
- ✅ Cache hit <10ms (negligible overhead)

---

## Success Criteria

### Acceptance Criteria
- [ ] FR-001: Buying power fetching working with cache
- [ ] FR-002: Position tracking with P&L calculations
- [ ] FR-003: Account balance retrieval
- [ ] FR-004: Day trade count checking
- [ ] FR-005: Cache management with TTL and invalidation
- [ ] FR-006: Bot integration (replace mock buying power)
- [ ] FR-007: Data validation and error handling
- [ ] NFR-005: Test coverage ≥90%
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] mypy passes with no errors

### Quality Gates (§Pre_Deploy)
- [ ] TDD complete: RED → GREEN → REFACTOR
- [ ] Bot.get_buying_power() returns real value (not $10k)
- [ ] SafetyChecks uses real buying power for validation
- [ ] Cache reduces API calls to <10/minute
- [ ] Network error handling with retry
- [ ] Rate limit handling (429) with backoff
- [ ] Integration tests with TradingBot pass
- [ ] Manual testing: Fetch real account data
- [ ] Manual testing: Cache hit/miss behavior
- [ ] Manual testing: Trade execution → cache invalidation

---

## Risk Assessment

### Technical Risks

**API Rate Limiting** (Probability: Medium, Impact: High)
- **Mitigation**: Aggressive caching (60s TTL), exponential backoff on 429
- **Fallback**: Return cached value when rate limited

**Network Failures** (Probability: Medium, Impact: Medium)
- **Mitigation**: Retry with exponential backoff (1s, 2s, 4s)
- **Fallback**: Return cached value or raise clear error

**Stale Data** (Probability: Low, Impact: Medium)
- **Mitigation**: 60s TTL ensures data <1 minute old
- **Fallback**: Manual cache invalidation via invalidate_cache()

**robin-stocks API Changes** (Probability: Low, Impact: High)
- **Mitigation**: Pinned version (3.0.5), comprehensive error handling
- **Fallback**: Data validation catches unexpected API responses

### Security Risks

**Account Data Exposure** (Probability: Low, Impact: Critical)
- **Mitigation**: Never log account numbers, mask values in logs
- **Constitution**: §Security compliance enforced

---

## Open Questions

None - Spec is clear based on roadmap requirements and existing robin-stocks integration patterns.

---

## References

- Constitution: `.specify/memory/constitution.md` (§Risk_Management, §Security, §Audit_Everything)
- Roadmap: `.specify/memory/roadmap.md` (account-data-module feature)
- Authentication: `specs/authentication-module/spec.md` (RobinhoodAuth integration)
- Bot: `src/trading_bot/bot.py` (get_buying_power mock to replace)
- SafetyChecks: `src/trading_bot/safety_checks.py` (buying power validation)
- robin-stocks: https://robin-stocks.readthedocs.io/en/latest/functions.html (Account API)
