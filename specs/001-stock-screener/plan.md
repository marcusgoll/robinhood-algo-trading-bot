# Implementation Plan: Stock Screener

**Feature**: stock-screener
**Branch**: 001-stock-screener
**Created**: 2025-10-16
**Phase**: 1 (Planning)

---

## Research Decisions Summary

See `research.md` for full research findings.

**Key Decisions**:
- **Reuse**: MarketDataService (quote fetching), @with_retry (resilience), TradingLogger (JSONL audit), error-handling-framework (exceptions)
- **Stack**: Pure Python (existing trading_bot stack)
- **Database**: In-memory MVP (no new tables); optional JSONL audit trail
- **Error Handling**: Graceful missing data (skip filter, log gap); @with_retry automatic backoff
- **Type Safety**: Pydantic dataclasses (ScreenerQuery, StockScreenerMatch, ScreenerResult)

**Components to Reuse**: 6
**New Components Needed**: 3 (ScreenerService, schemas, ScreenerLogger)

---

## Architecture Decisions

### Stack

- **Language**: Python 3.11+ (existing trading_bot standard)
- **Data Processing**: In-memory filtering (no database for MVP)
- **API Client**: Existing MarketDataService (robin_stocks under the hood)
- **Type Checking**: Pydantic v2 dataclasses (mypy strict mode compatible)
- **Logging**: Structured JSONL (StructuredTradeLogger pattern)
- **Error Handling**: @with_retry decorator (exponential backoff + jitter)
- **Testing**: pytest (existing test framework)

### Patterns

**Pattern 1: Layered Service Architecture**
- Controller/CLI entry point → ScreenerService (orchestration) → Filter methods
- Separation of concerns: HTTP layer separate from business logic
- Rationale: Matches existing trading_bot patterns (SafetyChecks, AccountData service layers)

**Pattern 2: Immutable Query/Result Objects**
- ScreenerQuery (request) and ScreenerResult (response) as immutable dataclasses
- Validation in `__post_init__()` (Pydantic @validator pattern)
- Rationale: Type-safe contracts, JSON serialization built-in, mypy compatible

**Pattern 3: Graceful Degradation**
- Missing data → skip that filter, apply others, log gap
- API error → @with_retry handles backoff, circuit breaker stops after 5 failures in 60s
- Rationale: Real market data is messy (IPOs, halts); screener should be forgiving

**Pattern 4: Audit Trail via JSONL**
- Every query logged to `logs/screener/YYYY-MM-DD.jsonl`
- Includes params, results, latency, errors (Constitution §Audit_Everything)
- Rationale: Enables measurement (HEART framework), trader behavior analytics

**Pattern 5: Filter Pipeline (Functional)**
- Apply filters sequentially: price → volume → float → daily_change
- Each filter receives stock set, returns filtered subset
- Filters are pure functions (no side effects)
- Rationale: Easy to test independently, easy to extend with new filters

---

## Directory Structure

**Follow existing trading_bot patterns:**

```
src/trading_bot/
├── services/
│   ├── screener_service.py       [NEW] Core screener orchestration
│   ├── market_data_service.py    [EXISTING] Quote fetching
│   └── __init__.py
├── schemas/
│   ├── screener_schemas.py       [NEW] ScreenerQuery, ScreenerResult dataclasses
│   └── __init__.py
├── logging/
│   ├── screener_logger.py        [NEW] JSONL audit trail
│   ├── structured_trade_logger.py [EXISTING] Parent pattern
│   └── __init__.py
└── tests/
    └── test_screener/
        ├── test_screener_service.py    [NEW] 90%+ coverage
        ├── test_screener_schemas.py    [NEW] Validation tests
        ├── test_screener_logger.py     [NEW] JSONL write tests
        ├── fixtures/
        │   ├── mock_quotes.json
        │   └── mock_stocks.py
        └── __init__.py

logs/
└── screener/                      [NEW] JSONL audit trail location
    └── 2025-10-16.jsonl           (daily files)
```

**Module Organization**:

| Module | Purpose | Depends On |
|--------|---------|-----------|
| ScreenerService | Query orchestration, filter application | MarketDataService, ScreenerLogger |
| ScreenerQuery | Request contract | Pydantic |
| StockScreenerMatch | Result item contract | Decimal, datetime |
| ScreenerResult | Response contract | ScreenerQuery, PageInfo |
| ScreenerLogger | JSONL audit trail | TradingLogger pattern |

---

## Data Model

**See `data-model.md` for complete entity definitions.**

**Summary**:
- **ScreenerQuery**: Filter parameters (min_price, max_price, relative_volume, float_max, min_daily_change, limit, offset)
- **StockScreenerMatch**: Single stock result (symbol, bid, volume, float, daily_change, filters_matched, data_gaps)
- **ScreenerResult**: Complete response (stocks[], metadata, pagination)
- **PageInfo**: Pagination state (offset, limit, has_more, next_offset, page_number)
- **ScreenerQueryLog**: JSONL audit record (timestamp, params, results, latency, errors)

**No database migrations** for MVP (in-memory only).

---

## Performance Targets

**From spec.md NFRs**:
- **NFR-001**: Query latency P50 <200ms, P95 <500ms (including all API calls)
- **NFR-004**: Data freshness: Real-time quotes (max 1min staleness)
- **NFR-007**: Test coverage ≥90%

**Estimated Latency Breakdown** (200ms budget):
- MarketDataService bulk quote fetch: ~150ms (batch API, 1000+ stocks)
- Filter application (Python in-memory): ~30ms (all 4 filters, 100 stocks)
- Pagination + response build: ~10ms
- Logging: ~5ms (async future optimization)
- **Reserve**: ~5ms (margin of safety)

**Optimization Strategies** (if needed):
1. Batch quote fetching (MarketDataService already supports)
2. Filter caching (P2 enhancement, 60-second TTL)
3. Lazy pagination (don't load all results until page requested)
4. Async JSONL logging (non-blocking write)

---

## Security

**Authentication Strategy**:
- Inherited from trading_bot session (already authenticated to Robinhood)
- No new auth required (screener is internal module)

**Authorization Model**:
- Single-user bot (no multi-user support for MVP)
- Future: Add user_id field for trader identification if multi-tenant

**Input Validation**:
- Request schema validation via Pydantic dataclasses (FR-002, FR-011)
- Type checking: min_price < max_price, limit 1-500, offset >= 0
- Sanitization: Stock symbol validated as uppercase alphanumeric
- Rate limiting: Inherited from MarketDataService + @with_retry

**Data Protection**:
- No PII in screener queries (only stock symbols, numeric filters)
- JSONL logs include query params (sanitize credentials if logged elsewhere)
- Credentials: Stored in .env (not in screener code)

**API Error Responses**:
- Validation errors: Return 400 with specific field + remediation (FR-011)
- Rate limit errors: Return 429, @with_retry handles backoff
- Server errors: Return 500, log error + retry count
- Example: `{"error": "min_price (2.5) >= max_price (2.0), must have min < max"}`

---

## Existing Infrastructure (Reuse)

### 6 Components to Reuse

| Component | Module | Purpose |
|-----------|--------|---------|
| MarketDataService | specs/market-data-module/ | Quote fetching (bid, ask, volume, historical) |
| @with_retry | specs/error-handling-framework/ | Exponential backoff + rate limit handling |
| TradingLogger | specs/trade-logging/ | JSONL audit trail pattern + thread safety |
| SafetyChecks | specs/safety-checks/ | Multi-criteria validation pattern |
| error-handling-framework | specs/error-handling-framework/ | Exception types (RetriableError, RateLimitError) |
| CircuitBreaker | specs/error-handling-framework/ | Failure detection (5 failures in 60s → shutdown) |

### Integration Points

**1. MarketDataService Integration**
```python
# Fetch all quotes for initial screening
quotes: List[Quote] = []
for symbol in candidate_symbols:
    quote = market_data_service.get_quote(symbol)
    quotes.append(quote)

# Each Quote has: bid, ask, volume, historical_data (for 100-day avg)
```

**2. @with_retry Decorator**
```python
from trading_bot.error_handling import with_retry, RetryPolicy

class ScreenerService:
    @with_retry(policy=RetryPolicy.DEFAULT)
    def filter(self, query: ScreenerQuery) -> ScreenerResult:
        # Automatic exponential backoff + circuit breaker
        # If 5 failures in 60s, circuit breaker trips
        ...
```

**3. TradingLogger Pattern**
```python
from trading_bot.logging import StructuredTradeLogger

class ScreenerLogger:
    # Inherit from StructuredTradeLogger
    # Add screener-specific log_query() method
    # Reuse daily rotation, thread safety, field validation
```

**4. Exception Hierarchy**
```python
from trading_bot.error_handling import RetriableError, RateLimitError

try:
    quote = market_data_service.get_quote(symbol)
except RateLimitError:
    # Handled by @with_retry
except RetriableError:
    # Handled by @with_retry
except Exception as e:
    # Non-retriable, log and fail
    logger.log_error(...)
```

---

## New Infrastructure (Create)

### 3 New Components

#### 1. ScreenerService Class
**File**: `src/trading_bot/services/screener_service.py`

**Responsibilities**:
- Accept ScreenerQuery with filter parameters
- Fetch quotes via MarketDataService
- Apply filters sequentially (AND logic)
- Return ScreenerResult with pagination
- Log all queries to JSONL
- Handle missing data gracefully

**Key Methods**:
```python
class ScreenerService:
    def filter(self, query: ScreenerQuery) -> ScreenerResult:
        """Main entry point: apply all filters, return results"""

    def _apply_price_filter(self, stocks: List[Quote], min_price, max_price) -> List[Quote]:
        """Filter by bid price range"""

    def _apply_volume_filter(self, stocks, relative_volume) -> List[Quote]:
        """Filter by relative volume (vs 100-day avg)"""

    def _apply_float_filter(self, stocks, float_max) -> List[Quote]:
        """Filter by float size (public shares)"""

    def _apply_daily_change_filter(self, stocks, min_daily_change) -> List[Quote]:
        """Filter by daily % move (abs value)"""

    def _paginate_results(self, stocks, offset, limit) -> tuple[List[Quote], PageInfo]:
        """Return paginated subset + page info"""
```

#### 2. ScreenerQuery & StockScreenerMatch Dataclasses
**File**: `src/trading_bot/schemas/screener_schemas.py`

**Responsibilities**:
- Type-safe request/response contracts
- Pydantic validation (min < max, bounds checking)
- JSON serialization for JSONL logging
- Immutable (dataclass frozen=False, but treat as immutable)

**Key Classes**:
```python
@dataclass
class ScreenerQuery:
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    # ... (see data-model.md for full fields)

@dataclass
class StockScreenerMatch:
    symbol: str
    bid_price: Decimal
    # ... (see data-model.md)

@dataclass
class ScreenerResult:
    query_id: str
    stocks: List[StockScreenerMatch]
    # ... (see data-model.md)
```

#### 3. ScreenerLogger Class
**File**: `src/trading_bot/logging/screener_logger.py`

**Responsibilities**:
- Log every query to JSONL (logs/screener/YYYY-MM-DD.jsonl)
- Daily file rotation
- Thread-safe concurrent writes
- Field validation before writing

**Key Methods**:
```python
class ScreenerLogger:
    def log_query(self, query: ScreenerQuery, result: ScreenerResult) -> None:
        """Log completed screener query"""

    def log_data_gap(self, symbol: str, field: str, reason: str) -> None:
        """Log missing data encountered during filtering"""

    def log_error(self, error_type: str, recoverable: bool, retry_count: int) -> None:
        """Log API/validation errors"""
```

---

## Deployment Model

**Project Type**: `local-only` (no remote staging/production)

**Implications**:
- No CI/CD required for `/phase-1-ship` or `/phase-2-ship`
- Deploy to local trading environment only
- Feature validated via local testing + backtesting
- Manual deployment: `git pull + python -m trading_bot`

**Environment Variables**:
- None new (screener uses existing ROBINHOOD_* credentials)
- Optional future: SCREENER_LOG_LEVEL, SCREENER_BATCH_SIZE

**Dependencies**:
- Existing: `robin_stocks`, `pandas`, `numpy`, `pydantic`
- New: None (use existing libraries)

**Build Command**:
- No changes (pure Python, no compilation)

**Smoke Tests** (local manual):
```python
# Run after implementation
screener = ScreenerService(market_data_service, logger)

# Smoke test 1: Price filter
result = screener.filter(ScreenerQuery(min_price=2.0, max_price=20.0))
assert result.result_count > 0, "Should find penny stocks"
assert all(2.0 <= s.bid_price <= 20.0 for s in result.stocks), "All should be in price range"

# Smoke test 2: Combined filters
result = screener.filter(ScreenerQuery(
    min_price=2.0, max_price=20.0,
    relative_volume=5.0,
    min_daily_change=10.0
))
assert result.execution_time_ms < 500, f"Latency {result.execution_time_ms}ms exceeds 500ms target"

# Smoke test 3: Error handling
result = screener.filter(ScreenerQuery(min_price=20.0, max_price=2.0))  # Invalid
# Should reject with clear error message (FR-011)
```

---

## Deployment Acceptance

**Production Invariants** (must hold true):
- ✅ Screener only identifies candidates (does not execute trades)
- ✅ No breaking API changes (backward compatible)
- ✅ No new environment variables required
- ✅ Paper trading compatible (no real money at risk)

**Testing Acceptance** (from Constitution):
- ✅ 90%+ test coverage (§Testing_Requirements)
- ✅ Type hints 100% (mypy strict mode, §Code_Quality)
- ✅ All queries logged (§Audit_Everything)
- ✅ Graceful error handling (§Error_Handling_Framework)

**Artifact Strategy** (local-only, no cross-platform builds):
- **Source**: Latest code from 001-stock-screener branch
- **Build**: No separate build step (pure Python)
- **Deployment**: `git pull + restart trading_bot`
- **Rollback**: `git revert + restart` (simple 2-command rollback)

---

## Integration Scenarios

### Scenario 1: Initial Setup

```bash
# Prerequisites
cd /path/to/Stocks
source venv/bin/activate

# Run tests
pytest tests/test_screener/ -v --cov=src/trading_bot/services/screener_service --cov=src/trading_bot/schemas/screener_schemas

# Lint
ruff check src/trading_bot/services/screener_service.py

# Type check
mypy src/trading_bot/services/screener_service.py --strict
```

### Scenario 2: Manual Testing

```python
# In Python REPL after running trading_bot startup
from trading_bot.services.screener_service import ScreenerService
from trading_bot.schemas.screener_schemas import ScreenerQuery

# Get screener instance (initialized during bot startup)
screener = trading_bot.screener

# Test 1: Price range filter
result = screener.filter(ScreenerQuery(min_price=5.0, max_price=15.0))
print(f"Found {result.result_count} stocks in $5-$15 range")
print(f"Top 3: {[s.symbol for s in result.stocks[:3]]}")

# Test 2: Volume spike detection
result = screener.filter(ScreenerQuery(relative_volume=5.0))
print(f"Found {result.result_count} stocks with 5x+ average volume")

# Test 3: Combined filters (your trading rules)
result = screener.filter(ScreenerQuery(
    min_price=2.0,
    max_price=20.0,
    relative_volume=5.0,
    float_max=20,
    min_daily_change=10.0
))
print(f"Setup candidates matching all criteria: {result.result_count}")
for stock in result.stocks[:5]:
    print(f"  {stock.symbol}: ${stock.bid_price} (+{stock.daily_change_pct}%)")
```

### Scenario 3: Backtesting (Optional P2)

```python
# Test screener against historical data
# Run filter on each day of market open in last 50 days
# Track % of screener matches that preceded +5% moves next day

from trading_bot.backtesting import BacktestScreener

backtest = BacktestScreener(screener)
results = backtest.run(
    start_date="2025-08-01",
    end_date="2025-10-15",
    filters={
        "min_price": 2.0,
        "max_price": 20.0,
        "relative_volume": 5.0,
    }
)

print(f"Setup accuracy: {results.setup_success_rate:.1%}")  # % preceded +5% moves
print(f"False positive rate: {results.false_positive_rate:.1%}")
```

---

## Summary

| Aspect | Status |
|--------|--------|
| **Architecture** | Layered services (ScreenerService → Filters) |
| **Data Model** | 5 dataclasses (Query, Match, Result, PageInfo, Log) |
| **Reusable Components** | 6 (MarketDataService, @with_retry, TradingLogger, SafetyChecks, exceptions, CircuitBreaker) |
| **New Components** | 3 (ScreenerService, schemas, ScreenerLogger) |
| **Database** | In-memory MVP (JSONL audit trail) |
| **Performance** | P50 <200ms, P95 <500ms per NFR-001 |
| **Test Coverage** | 90%+ target per Constitution |
| **Deployment** | Local-only (no staging/production infrastructure) |
| **Rollback** | Simple 2-command: `git revert + restart` |

---

**Next Phase**: `/tasks` (generate 20-30 TDD tasks for implementation)
