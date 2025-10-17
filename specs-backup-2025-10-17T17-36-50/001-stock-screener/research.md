# Research & Discovery: Stock Screener

## Research Decisions

### Decision 1: Leverage MarketDataService for Quote Fetching
- **Decision**: Reuse existing MarketDataService (v1.0.0, shipped) for all quote retrieval
- **Rationale**: Provides proven resilience patterns (exponential backoff, rate limit handling), supports historical data for 100-day volume averaging, already handles Robinhood API authentication
- **Alternatives**: Build custom API client (rejected: duplicates error handling logic, reinvents retry wheel)
- **Source**: specs/market-data-module/ (shipped 2025-10-08, 93.08% test coverage)

### Decision 2: In-Memory Processing for MVP (No Database)
- **Decision**: Process screener queries in-memory; no new database tables for MVP
- **Rationale**: Screener is read-only/stateless; no persistence needed for initial release; reduces complexity, no migrations
- **Alternatives**: Add screener_queries/screener_results tables (rejected for MVP: over-engineering, can add later based on usage patterns)
- **Enhancement Path**: Add JSONL audit trail (logs/screener/) for operational insights

### Decision 3: Pagination via Offset-Based Cursors (500 max per page)
- **Decision**: Use offset/limit for pagination (standard pattern), max 500 results per page
- **Rationale**: Simple to implement, matches existing patterns (AccountData uses similar approach), handles 10,000+ stock result sets gracefully
- **Alternatives**: Keyset pagination (rejected: over-engineered for trading use case, offset sufficient)
- **Edge Case**: If screener returns 0 results, return empty array + metadata with total_count=0

### Decision 4: Structured JSONL Logging for All Screener Operations
- **Decision**: Log every screener query to JSONL (logs/screener/queries.jsonl)
- **Rationale**: Audits trader behavior, enables measurement (query frequency, filter usage, latency), aligns with Constitution §Audit_Everything
- **Alternatives**: Silent processing (rejected: violates Constitution Audit requirement)
- **Implementation**: Reuse StructuredTradeLogger pattern from specs/trade-logging/

### Decision 5: Graceful Missing Data Handling
- **Decision**: Skip filter if data unavailable (e.g., float data missing); apply other filters; log data gap
- **Rationale**: Real market data is messy (IPOs lack float history, halted stocks missing volumes); screener should be forgiving
- **Alternative**: Reject query if any field missing (rejected: too strict, reduces result count unnecessarily)
- **Default Baseline**: For IPO stocks with no 100-day average volume, use 1M shares as baseline (documented assumption)

### Decision 6: Type-First API Design with Pydantic
- **Decision**: Use Pydantic v2 dataclasses for ScreenerQuery and ScreenerResult (matching existing trading_bot patterns)
- **Rationale**: Runtime validation, mypy compatibility, Constitution §Code_Quality compliance, JSON serialization built-in
- **Alternatives**: Plain dicts (rejected: loses validation), TypedDict (rejected: runtime validation missing)
- **Source**: Existing patterns in AccountData, PerformanceTracker use Pydantic dataclasses

---

## Components to Reuse (6 found)

### 1. MarketDataService (specs/market-data-module/)
- **Provides**: Real-time quote retrieval (bid, ask, volume), historical OHLCV data, market hours detection, 100-day average volume
- **Used for**: Fetching stock data for filtering
- **Integration**: `market_data_service.get_quote(symbol)` → `Quote` dataclass with all filtering fields
- **Reliability**: 93.08% test coverage, 100% contract compliance, 0 security vulnerabilities
- **Rate Limiting**: Built-in @with_retry decorator handles Robinhood API backoff automatically

### 2. @with_retry Decorator (specs/error-handling-framework/)
- **Provides**: Exponential backoff (1s, 2s, 4s) + jitter, rate limit detection (HTTP 429), circuit breaker integration
- **Used for**: Wrapping ScreenerService.filter() to handle API failures gracefully
- **Pattern**: `@with_retry(policy=RetryPolicy.DEFAULT)` on screener methods
- **Benefit**: Zero additional code; existing resilience automatically applied
- **Testing**: 27 unit tests, 87-96% coverage per module

### 3. TradingLogger + StructuredTradeLogger (specs/trade-logging/)
- **Provides**: JSONL audit trail, daily file rotation (logs/trades/YYYY-MM-DD.jsonl), thread-safe writes, field validation
- **Used for**: Screener query logging (timestamp, filters, results, latency, errors)
- **Pattern**: `screener_logger.log_query(query_params, result_count, execution_time_ms)`
- **Benefit**: Audit trail for measurement (HEART framework), trader behavior analytics
- **Performance**: 0.405ms write latency (target <5ms), 10-thread concurrent tested

### 4. SafetyChecks Module (specs/safety-checks/)
- **Provides**: Multi-criteria validation pattern, circuit breaker management
- **Used for**: Validating screener query parameters (type checking, range bounds, constraint checking)
- **Pattern**: `SafetyChecks.validate_parameters(query)` → ValueError if invalid
- **Benefit**: Reuses proven validation logic, fail-safe error handling
- **Integration**: Existing error handling already tested; no new validation code needed

### 5. error-handling-framework (specs/error-handling-framework/)
- **Provides**: Exception hierarchy (RetriableError, NonRetriableError, RateLimitError), predefined policies
- **Used for**: Typing screener exceptions, categorizing failures (API vs validation)
- **Classes**: Use `RateLimitError` for 429 responses, `RetriableError` for transient failures
- **Testing**: mypy --strict passes (100% type coverage), 0 vulnerabilities

### 6. CircuitBreaker (specs/error-handling-framework/)
- **Provides**: Sliding window failure detection (5 failures in 60s triggers shutdown)
- **Used for**: Detecting persistent API issues; stops screener from hammering Robinhood API
- **Integration**: Inherited from existing @with_retry; screener gets circuit breaker for free
- **Behavior**: If breaker trips, screener returns early with clear error message

---

## New Components Needed (3 required)

### 1. ScreenerService Class
**Purpose**: Core orchestration; applies all filters in sequence

**Location**: `src/trading_bot/services/screener_service.py`

**Responsibilities**:
- Accept ScreenerQuery with filter parameters
- Fetch quotes for candidate stocks (initially all stocks via MarketDataService bulk query)
- Apply each filter in sequence (price → volume → float → daily change)
- Return intersection of all filters (AND logic)
- Sort by volume descending
- Support pagination (offset/limit)
- Log all queries to JSONL
- Handle missing data gracefully (skip filter, log gap)

**Methods**:
- `filter(query: ScreenerQuery) → ScreenerResult`
- `_apply_price_filter(stocks, min_price, max_price) → stocks`
- `_apply_volume_filter(stocks, relative_volume) → stocks`
- `_apply_float_filter(stocks, float_max) → stocks`
- `_apply_daily_change_filter(stocks, min_daily_change) → stocks`
- `_paginate_results(stocks, offset, limit) → paginated_stocks + page_info`

### 2. ScreenerQuery and ScreenerResult Dataclasses
**Purpose**: Type-safe request/response contracts

**Location**: `src/trading_bot/schemas/screener_schemas.py`

**ScreenerQuery**:
- `min_price: Decimal | None`
- `max_price: Decimal | None`
- `relative_volume: float | None` (multiplier, e.g., 5.0 = 5x average)
- `float_max: int | None` (max shares in millions)
- `min_daily_change: float | None` (percent, e.g., 10.0 = ±10%)
- `limit: int = 500`
- `offset: int = 0`
- Validation: `__post_init__()` ensures min_price < max_price if both set

**ScreenerResult**:
- `stocks: list[StockScreenerMatch]` (symbol, price, volume, float, daily_change)
- `query_timestamp: datetime`
- `params_used: ScreenerQuery` (echo back for audit)
- `result_count: int`
- `total_count: int` (total before pagination)
- `execution_time_ms: float`
- `page_info: PageInfo` (offset, limit, has_more)
- `errors: list[str] = []` (data gaps encountered)

**StockScreenerMatch**:
- `symbol: str`
- `bid_price: Decimal`
- `volume: int`
- `float_shares: int | None` (None if unavailable)
- `daily_change_pct: float`

### 3. ScreenerLogger Class
**Purpose**: JSONL audit trail for all screener operations

**Location**: `src/trading_bot/logging/screener_logger.py`

**Responsibilities**:
- Log every query (timestamp, filters, result_count, latency)
- Log data gaps (symbol, field, reason)
- Log errors (error_type, recoverable, retry_count)
- Rotate daily (logs/screener/YYYY-MM-DD.jsonl)
- Thread-safe concurrent writes

**Methods**:
- `log_query(query: ScreenerQuery, result_count: int, execution_time_ms: float, errors: list[str])`
- `log_data_gap(symbol: str, field: str, reason: str)`
- `log_error(error_type: str, recoverable: bool, retry_count: int, symbol: str | None)`

---

## Unknowns & Questions

All critical questions resolved ✅

- ✅ Q: How many stocks to screen initially? → Answer: All available via MarketDataService (no limit set by spec; pagination handles results)
- ✅ Q: What is "float size" data source? → Answer: MarketDataService provides via Robinhood API (public float attribute)
- ✅ Q: How to handle stocks with missing float? → Answer: Skip float filter, apply others, log gap (spec edge case #3)
- ✅ Q: Should screener cache results? → Answer: No caching for MVP (enhance later), fresh queries on every request
- ✅ Q: Default parameters if not provided? → Answer: All filters optional (None = skip that filter); offset=0, limit=500 defaults

---

## Constitution Alignment Check ✅

| Principle | Status | Evidence |
|-----------|--------|----------|
| §Safety_First | ✅ Pass | Screener is read-only; no trades executed; paper-trading compatible |
| §Code_Quality | ✅ Pass | Type hints enforced (Pydantic dataclasses), KISS principle (simple filters, no ML) |
| §Risk_Management | ✅ Pass | Screener is passive (identifies candidates only); traders apply own risk rules |
| §Testing_Requirements | ✅ Pass | 90% coverage target achievable; each filter testable independently |
| §Audit_Everything | ✅ Pass | All queries logged to JSONL with params, results, latency, errors |
| §Error_Handling | ✅ Pass | Graceful missing data handling; logging of all failures; @with_retry integration |

---

**Summary**: No technical blockers. All reusable components identified. MVP scope is clear and achievable.
