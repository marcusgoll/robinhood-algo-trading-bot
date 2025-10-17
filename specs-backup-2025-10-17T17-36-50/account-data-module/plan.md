# Implementation Plan: Account Data Module

**Feature**: account-data-module
**Phase**: 1 - Planning
**Date**: 2025-01-08

---

## [RESEARCH DECISIONS]

### Decision 1: Service Pattern (RobinhoodAuth Model)
- **Decision**: Use service class with dependency injection, following authentication-module pattern
- **Rationale**:
  - Proven pattern in codebase (RobinhoodAuth)
  - Clean separation of concerns (data models + service logic)
  - Easy to test with mocked dependencies
  - Consistent with existing architecture
- **Alternatives**:
  - Functional approach: Rejected (harder to maintain state/cache)
  - Singleton pattern: Rejected (poor testability, global state)
- **Source**: `src/trading_bot/auth/robinhood_auth.py` (lines 96-237)

### Decision 2: Cache Implementation (In-Memory Dict with TTL)
- **Decision**: Use in-memory dict with CacheEntry dataclass for TTL tracking
- **Rationale**:
  - Simple implementation (no external dependencies)
  - Fast access (<10ms for cache hits)
  - Session-scoped data (persistence not required)
  - Easy selective invalidation (by key)
- **Alternatives**:
  - functools.lru_cache: Rejected (no TTL support, can't invalidate by key)
  - redis/memcached: Rejected (overkill for single-process bot, external dependency)
  - pickle files: Rejected (too slow for frequent access, I/O overhead)
- **Source**: Research in NOTES.md (Cache Strategy Research section)

### Decision 3: Retry Logic (Reuse _retry_with_backoff Pattern)
- **Decision**: Reuse exponential backoff pattern from authentication-module
- **Rationale**:
  - Already proven effective in auth module (network errors, rate limits)
  - Consistent error handling across modules
  - Same delays: 1s, 2s, 4s (3 attempts max)
  - Reusable function can be extracted to shared utils
- **Alternatives**:
  - Custom retry: Rejected (duplication)
  - No retry: Rejected (poor reliability)
  - Linear backoff: Rejected (less effective for rate limiting)
- **Source**: `src/trading_bot/auth/robinhood_auth.py` (lines 40-76)

### Decision 4: Data Models (Dataclasses with Decimal)
- **Decision**: Use @dataclass for Position, AccountBalance, CacheEntry with Decimal for financial values
- **Rationale**:
  - Matches existing patterns (AuthConfig, SafetyResult, PositionSize)
  - Type safety with mypy validation
  - Decimal avoids float precision issues (financial data)
  - Immutable by default (safer)
- **Alternatives**:
  - Plain dicts: Rejected (no type safety, hard to validate)
  - TypedDict: Rejected (less ergonomic than dataclass)
  - Pydantic: Rejected (adds dependency, dataclass sufficient)
- **Source**: Multiple files - auth/robinhood_auth.py:96, safety_checks.py:64-97

### Decision 5: P&L Calculation (robin-stocks build_holdings API)
- **Decision**: Use robin_stocks.robinhood.account.build_holdings() which includes prices and equity
- **Rationale**:
  - API already calculates current_value and equity
  - Single API call for all position data + prices
  - Avoids separate price fetching (fewer API calls)
- **Alternatives**:
  - Fetch positions + separate price lookup: Rejected (more API calls, higher rate limit risk)
  - Cache prices separately: Rejected (added complexity)
- **Source**: robin-stocks documentation + spec.md API Mapping section

### Decision 6: Integration Pattern (Optional Dependency Injection)
- **Decision**: Optional AccountData initialization in TradingBot, backward compatible fallback to mock
- **Rationale**:
  - Matches authentication-module pattern (optional config parameter)
  - Existing tests continue to work (no breaking changes)
  - Gradual migration path (can deploy without forcing adoption)
- **Alternatives**:
  - Required dependency: Rejected (breaks all existing tests)
  - Global singleton: Rejected (poor testability)
- **Source**: `src/trading_bot/bot.py` (lines 105-133) - auth integration pattern

### Decision 7: Cache TTLs (60s Volatile, 300s Stable)
- **Decision**:
  - 60s TTL for buying_power, positions, balance (volatile data)
  - 300s TTL for day_trade_count (stable data)
- **Rationale**:
  - 60s provides near-real-time data without hammering API
  - day_trade_count changes infrequently (once per trade session)
  - Manual invalidation on trades ensures accuracy
  - Balances freshness vs rate limiting
- **Alternatives**:
  - 30s TTL: Rejected (too aggressive, more API calls)
  - 120s TTL: Rejected (data too stale for trading decisions)
  - No cache: Rejected (risk of rate limiting)
- **Source**: NOTES.md Cache Strategy Research + robin-stocks API performance testing

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11+ (existing stack)
- API Client: robin-stocks==3.0.5 (already in requirements.txt)
- Type System: Type hints + mypy strict mode
- Testing: pytest + unittest.mock (existing test infrastructure)
- Data Types: Decimal (financial precision), datetime (timestamps)

**Patterns**:
- **Service Pattern**: AccountData class with dependency injection (auth: RobinhoodAuth)
- **Data Classes**: Position, AccountBalance, CacheEntry with type hints
- **Cache Layer**: In-memory dict with TTL-based invalidation
- **Retry Logic**: Exponential backoff (1s, 2s, 4s) for network/rate limit errors
- **Error Handling**: Graceful degradation with cached fallback
- **Security**: Credential masking in logs (reuse _mask_credential pattern)
- **Testing**: TDD with GIVEN/WHEN/THEN structure, unittest.mock for API mocking

**Dependencies** (no new packages required):
- ✅ robin-stocks==3.0.5 (already in requirements.txt)
- ✅ Standard library: datetime, typing, dataclasses, decimal, time

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── account/                    # NEW MODULE
│   ├── __init__.py            # Clean exports: AccountData, AccountDataError
│   └── account_data.py        # AccountData service + data models
├── auth/
│   ├── __init__.py
│   └── robinhood_auth.py      # REUSE: _retry_with_backoff, _mask_credential
├── bot.py                     # UPDATE: Add account_data initialization
└── safety_checks.py           # UPDATE: Accept account_data parameter

tests/
├── unit/
│   └── test_account_data.py   # NEW: Unit tests for AccountData
└── integration/
    └── test_account_integration.py  # NEW: Integration tests

specs/account-data-module/
├── spec.md                    # ✅ EXISTS
├── NOTES.md                   # ✅ EXISTS
├── plan.md                    # THIS FILE
├── tasks.md                   # NEXT: /tasks
├── contracts/
│   └── api.yaml              # OpenAPI specs (robin-stocks endpoints)
└── error-log.md              # Error tracking during implementation
```

**Module Organization**:

**account_data.py**:
- Position dataclass (symbol, quantity, prices, P&L)
- AccountBalance dataclass (cash, equity, buying_power)
- CacheEntry dataclass (value, cached_at, ttl_seconds)
- AccountDataError exception (custom error type)
- AccountData service class:
  - `__init__(auth: RobinhoodAuth)`: Initialize with authenticated session
  - `get_buying_power(use_cache=True) → float`: Fetch/cache buying power
  - `get_positions(use_cache=True) → List[Position]`: Fetch/cache positions with P&L
  - `get_account_balance(use_cache=True) → AccountBalance`: Fetch/cache balance
  - `get_day_trade_count(use_cache=True) → int`: Fetch/cache day trade count
  - `invalidate_cache(cache_type=None)`: Clear cache (all or specific type)
  - Private methods: `_fetch_*`, `_is_cache_valid`, `_update_cache`

---

## [SCHEMA]

**No database tables** - All data fetched from robin-stocks API and cached in memory.

**Data Models** (Python dataclasses):

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, Any

@dataclass
class Position:
    """Equity position with P&L calculation."""
    symbol: str
    quantity: int
    average_buy_price: Decimal
    current_price: Decimal
    current_value: Decimal  # quantity × current_price
    cost_basis: Decimal     # quantity × average_buy_price
    profit_loss: Decimal    # current_value - cost_basis
    profit_loss_pct: Decimal  # (P&L / cost_basis) × 100
    last_updated: datetime

@dataclass
class AccountBalance:
    """Account balance breakdown."""
    cash: Decimal           # Available cash
    equity: Decimal         # Total equity (cash + positions)
    buying_power: Decimal   # Available for trades
    last_updated: datetime

@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    value: Any
    cached_at: datetime
    ttl_seconds: int
```

**API Schemas** (robin-stocks endpoints):

See: `specs/account-data-module/contracts/api.yaml`

**robin-stocks API Responses**:

```python
# load_account_profile() returns:
{
    'buying_power': '10500.25',
    'equity': '12500.75',
    'cash': '5000.00',
    'day_trade_count': '1',
    # ... other fields
}

# build_holdings() returns:
{
    'AAPL': {
        'quantity': '10',
        'average_buy_price': '150.25',
        'price': '155.00',
        'equity': '1550.00',
        'percent_change': '3.16',
        'equity_change': '47.50',
        # ... other fields
    },
    'TSLA': { ... }
}
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: API response time <2s under normal network conditions
- NFR-001: Cache hits return in <10ms
- NFR-001: API call rate <10 calls/minute (via caching)

**Cache Performance**:
- Cache hit: <10ms (in-memory dict lookup)
- Cache miss: <2s (API call + parsing)
- Cache invalidation: <1ms (dict clear)

**API Call Minimization**:
- Target: <10 API calls per minute
- Strategy: 60s TTL for volatile data, 300s for stable
- Invalidation: Manual on trade execution

---

## [SECURITY]

**Authentication Strategy**:
- Uses RobinhoodAuth authenticated session (dependency injection)
- No direct credential handling (delegated to auth module)
- Session token managed by robin_stocks library

**Authorization Model**:
- Account data scoped to authenticated user's account
- No cross-account access (enforced by robin_stocks API)

**Input Validation**:
- API response validation: Check expected fields exist
- Type validation: Ensure strings convert to Decimal correctly
- Error handling: Raise AccountDataError for invalid responses

**Data Protection** (§Security compliance):
- **DO NOT log**: Account numbers, exact balances
- **DO log**: Masked values ("Buying power: $X,XXX.XX"), operation success/failure
- **Cache security**: In-memory only (not persisted to disk)
- **No PII exposure**: Only financial data (already user-scoped)

**Rate Limiting Protection**:
- Detect 429 responses from API
- Exponential backoff: 1s, 2s, 4s delays
- Cache reduces API call frequency

---

## [EXISTING INFRASTRUCTURE - REUSE] (8 components)

**Services/Modules**:
- `src/trading_bot/auth/robinhood_auth.py`: RobinhoodAuth for authenticated session
  - Dependency: AccountData requires authenticated RobinhoodAuth instance
  - Pattern: Pass auth instance via __init__
- `src/trading_bot/auth/robinhood_auth.py:40-76`: _retry_with_backoff() helper
  - Reuse: Copy/extract to shared utils for network retry logic
  - Pattern: Exponential backoff (1s, 2s, 4s) for network errors
- `src/trading_bot/auth/robinhood_auth.py:79-88`: _mask_credential() helper
  - Reuse: For masking account balances in logs
  - Pattern: Show partial value (e.g., "$X,XXX.XX")
- `src/trading_bot/config.py:25-67`: Config dataclass pattern
  - Reuse: Similar structure for AccountData configuration (TTLs)
  - Pattern: @dataclass with from_config() class method

**Integration Points**:
- `src/trading_bot/bot.py:240-251`: get_buying_power() mock method
  - Replace: Return self.account_data.get_buying_power() if available
  - Fallback: Keep mock value for backward compatibility
- `src/trading_bot/bot.py:253-324`: execute_trade() method
  - Update: Call self.account_data.invalidate_cache() after trades
  - Pattern: Invalidate buying_power and positions caches
- `src/trading_bot/safety_checks.py:100-150`: SafetyChecks class
  - Update: Accept account_data parameter in __init__
  - Integration: Fetch buying_power from account_data if available

**Test Patterns**:
- `tests/unit/test_robinhood_auth.py`: TDD test structure
  - Reuse: GIVEN/WHEN/THEN format
  - Pattern: unittest.mock for API mocking, pytest for test runner
  - Example: Mock robin_stocks.robinhood.account.* functions

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

**Backend**:
- `src/trading_bot/account/account_data.py`: AccountData service with caching
  - Purpose: Fetch and cache account data from robin-stocks API
  - Features: get_buying_power(), get_positions(), get_account_balance(), get_day_trade_count()
  - Cache: In-memory dict with TTL-based invalidation
  - Error handling: Exponential backoff retry, graceful degradation

- `src/trading_bot/account/__init__.py`: Clean module exports
  - Exports: AccountData, AccountDataError, Position, AccountBalance
  - Pattern: Follow auth/__init__.py structure

**Data Models** (in account_data.py):
- Position dataclass: Equity position with P&L calculations
- AccountBalance dataclass: Cash, equity, buying_power breakdown
- CacheEntry dataclass: TTL-based cache storage
- AccountDataError exception: Custom exception for account data errors

**Tests**:
- `tests/unit/test_account_data.py`: Unit tests for AccountData service
  - Coverage: Data models, cache logic, API fetching, P&L calculations
  - Mocking: robin_stocks.robinhood.account.* functions
  - Target: ≥90% coverage

- `tests/integration/test_account_integration.py`: Integration tests
  - Coverage: Bot integration, SafetyChecks integration, cache invalidation
  - Scenarios: Real buying power usage, trade execution cache clearing

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: No change (Python backend, no platform-specific features)
- Env vars: No new environment variables (uses existing auth)
- Breaking changes: **NO** - Backward compatible, optional feature
- Migration: **NO** - No database, cache is ephemeral

**Build Commands**:
- No changes required (existing pytest, mypy, ruff workflows)

**Environment Variables**:
- No new variables required
- Reuses existing: ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, ROBINHOOD_MFA_SECRET

**Database Migrations**:
- **N/A** - No database changes (in-memory cache only)

**Smoke Tests** (for CI):
- Unit tests: `pytest tests/unit/test_account_data.py -v`
- Integration tests: `pytest tests/integration/test_account_integration.py -v`
- Type checking: `mypy src/trading_bot/account/ --strict`
- Coverage: `pytest --cov=src/trading_bot/account --cov-report=term-missing`

**Platform Coupling**:
- None - Pure Python module, no platform dependencies

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- Backward compatibility: TradingBot works with or without AccountData
- No breaking API changes: Existing bot.py methods unchanged
- Cache is ephemeral: No persistent state (safe to restart)
- Authentication required: AccountData fails safely if auth missing

**Testing Checklist**:
```gherkin
Given bot is authenticated with Robinhood
When get_buying_power() is called
Then real buying power is returned (not $10k mock)
  And value matches Robinhood account
  And response time <2s
  And subsequent calls use cache (<10ms)

Given bot executes a trade
When trade completes successfully
Then account cache is invalidated
  And next get_buying_power() call fetches fresh data
  And new balance reflects trade impact

Given API rate limit is hit (429)
When get_buying_power() is called
Then exponential backoff is applied (1s, 2s, 4s)
  And cached value is returned if available
  And no errors are raised to user
```

**Rollback Plan**:
- **Rollback command**: Remove AccountData initialization from bot.py
  - Revert bot.py changes (lines with account_data)
  - Revert SafetyChecks changes (account_data parameter)
- **Rollback time**: <5 minutes (code-only change, no state)
- **Special considerations**: None - no database, no external state
- **Verification**: `pytest tests/unit/test_bot.py` passes with mock buying_power

---

## [INTEGRATION SCENARIOS]

**From developer/tester perspective:**

### Scenario 1: Development Setup
```bash
# No new dependencies required
cd D:\Coding\Stocks

# Verify existing dependencies
pip list | grep robin-stocks  # Should show 3.0.5

# Run tests
pytest tests/unit/test_account_data.py -v
pytest tests/integration/test_account_integration.py -v

# Type checking
mypy src/trading_bot/account/ --strict
```

### Scenario 2: Bot Integration Test
```python
from src.trading_bot.bot import TradingBot
from src.trading_bot.config import Config

# Load config with credentials
config = Config.from_env_and_json()

# Create bot (automatically initializes AccountData)
bot = TradingBot(config=config, paper_trading=True)

# Start bot (authenticates first)
bot.start()

# Get real buying power (not $10k mock)
buying_power = bot.get_buying_power()
print(f"Real buying power: ${buying_power:,.2f}")

# Get positions with P&L
if bot.account_data:
    positions = bot.account_data.get_positions()
    for pos in positions:
        print(f"{pos.symbol}: {pos.quantity} shares, P&L: ${pos.profit_loss:.2f}")

# Stop bot (logs out)
bot.stop()
```

### Scenario 3: Cache Behavior Validation
```python
import time
from src.trading_bot.account import AccountData
from src.trading_bot.auth import RobinhoodAuth
from src.trading_bot.config import Config

config = Config.from_env()
auth = RobinhoodAuth(config)
auth.login()

account = AccountData(auth=auth)

# First call: Cache miss (API call)
start = time.time()
bp1 = account.get_buying_power(use_cache=True)
time1 = time.time() - start
print(f"Cache miss: {time1:.3f}s")  # ~1-2s

# Second call: Cache hit (no API call)
start = time.time()
bp2 = account.get_buying_power(use_cache=True)
time2 = time.time() - start
print(f"Cache hit: {time2:.3f}s")  # <0.01s

assert bp1 == bp2
assert time2 < 0.1  # Cache hit should be <100ms

# Force refresh
account.invalidate_cache('buying_power')
bp3 = account.get_buying_power(use_cache=True)
# This will be another API call
```

### Scenario 4: Error Handling Validation
```python
# Test network error retry
with patch('robin_stocks.robinhood.account.load_account_profile') as mock_api:
    # Simulate 2 network errors, then success
    mock_api.side_effect = [
        Exception("Network error"),
        Exception("Network error"),
        {'buying_power': '10000.50'}
    ]

    account = AccountData(auth=auth)
    bp = account.get_buying_power()

    # Should succeed after 2 retries
    assert bp == 10000.50
    assert mock_api.call_count == 3
```

---

## [RISK MITIGATION]

### Risk 1: API Rate Limiting (Probability: Medium, Impact: High)
**Mitigation**:
- Aggressive caching (60s TTL for volatile data)
- Exponential backoff on 429 errors
- API call monitoring/logging
- Fallback to cached values when rate limited

**Testing**:
- Unit test: Simulate 429 response → verify backoff
- Integration test: Rapid successive calls → verify cache reduces API load

### Risk 2: Stale Data After Trades (Probability: Low, Impact: Medium)
**Mitigation**:
- Manual cache invalidation in bot.execute_trade()
- 60s TTL ensures data <1 minute old
- Manual invalidate_cache() method available

**Testing**:
- Integration test: Execute trade → verify cache cleared
- Unit test: Trade execution → get_buying_power returns fresh value

### Risk 3: robin-stocks API Changes (Probability: Low, Impact: High)
**Mitigation**:
- Pinned version: robin-stocks==3.0.5
- API response validation (check expected fields)
- Comprehensive error handling with clear messages

**Testing**:
- Unit test: Malformed API response → AccountDataError raised
- Unit test: Missing fields → graceful handling with defaults

### Risk 4: Network Failures (Probability: Medium, Impact: Medium)
**Mitigation**:
- Retry with exponential backoff (1s, 2s, 4s)
- Return cached value as fallback
- Clear error messages for troubleshooting

**Testing**:
- Unit test: Network timeout → retry with backoff
- Unit test: Persistent network error → return cached value or raise

---

## [TESTING STRATEGY]

### Unit Tests (test_account_data.py)

**Test Categories** (Target: 25-30 tests, ≥90% coverage):

1. **Data Model Tests** (5 tests):
   - Position P&L calculation: profit scenario
   - Position P&L calculation: loss scenario
   - Position P&L percentage calculation
   - AccountBalance all fields populated
   - CacheEntry TTL validation

2. **Cache Logic Tests** (8 tests):
   - Cache miss: fetch from API, store in cache
   - Cache hit (valid TTL): return cached value, no API call
   - Cache stale (expired TTL): fetch fresh data, update cache
   - Manual invalidation (single type): specific cache cleared
   - Manual invalidation (all types): all caches cleared
   - Concurrent access: cache thread-safe (future)
   - Cache size limits: prevent memory bloat (future)
   - _is_cache_valid() with various TTLs

3. **API Fetch Tests** (7 tests):
   - Fetch buying power: returns float from API
   - Fetch positions: returns list of Position objects
   - Fetch account balance: returns AccountBalance object
   - Fetch day trade count: returns int (0-3)
   - Empty positions: returns empty list (no error)
   - Network error: retry with exponential backoff
   - Rate limit (429): backoff and retry

4. **P&L Calculation Tests** (4 tests):
   - Profit calculation: (current > entry) × quantity
   - Loss calculation: (current < entry) × quantity
   - Percentage calculation: (P&L / cost_basis) × 100
   - Zero quantity: P&L = 0

5. **Error Handling Tests** (5 tests):
   - Invalid API response: raise AccountDataError
   - Missing required fields: use defaults or raise
   - Authentication error (401): re-auth trigger
   - Malformed JSON: parse error handling
   - Unexpected data types: type validation

### Integration Tests (test_account_integration.py)

**Test Scenarios** (Target: 5-7 tests):

1. **Bot Integration** (3 tests):
   - Bot.get_buying_power() returns real value (not $10k)
   - Trade execution triggers cache invalidation
   - Bot startup with AccountData initialization

2. **SafetyChecks Integration** (2 tests):
   - validate_trade() uses AccountData.get_buying_power()
   - Fallback to parameter if AccountData not available

3. **Auth Integration** (2 tests):
   - AccountData uses RobinhoodAuth session
   - Re-auth on 401 error during account data fetch

### Performance Tests

**Cache Performance Validation**:
- Cache hit: <10ms response time
- Cache miss: <2s API call time
- Invalidation: <1ms operation time

**API Call Minimization**:
- Measure API call frequency over 10 minutes
- Verify <10 calls/minute with normal bot operation
- Confirm cache reduces load vs no-cache scenario

---

## [OPEN QUESTIONS]

None - All requirements clear from spec.md and codebase research.

---

## [NEXT STEPS]

1. **Phase 2: /tasks** - Generate concrete TDD task list (T001-T050)
2. **Phase 3: /implement** - Execute tasks with RED → GREEN → REFACTOR
3. **Phase 4: /analyze** - Code review and validation
4. **Phase 5: /optimize** - Performance tuning and final review
5. **Phase 6: /ship** - Deployment and documentation

---

**Planning Complete**: 2025-01-08
**Next Phase**: `/tasks account-data-module`
