# Tasks: Stock Screener

**Feature**: stock-screener
**Branch**: 001-stock-screener
**Created**: 2025-10-16
**Total Tasks**: 32
**MVP Scope**: Phase 3 (US1-US5) - Core filtering functionality

---

## Codebase Reuse Analysis

**Scanned**: `src/trading_bot/**/*.py`, `tests/test_*.py`

### Existing - Reuse

✅ **MarketDataService** (src/trading_bot/services/market_data_service.py)
- Provides Quote dataclass, get_quote(), historical data
- Used by: All screener filter tasks
- Integration: Direct import + usage

✅ **@with_retry Decorator** (src/trading_bot/error_handling/__init__.py)
- Exponential backoff, rate limit handling, circuit breaker
- Used by: ScreenerService.filter()
- Integration: Decorator on method

✅ **TradingLogger & StructuredTradeLogger** (src/trading_bot/logging/structured_trade_logger.py)
- JSONL pattern, daily rotation, thread-safe writes
- Used by: ScreenerLogger.log_query()
- Integration: Inherit pattern, adapt for screener events

✅ **SafetyChecks Module** (src/trading_bot/services/safety_checks.py)
- Multi-criteria validation pattern
- Used by: ScreenerQuery validation
- Integration: Copy validation pattern (bounds checking, constraint checking)

✅ **error-handling-framework** (src/trading_bot/error_handling/)
- RetriableError, RateLimitError, CircuitBreaker
- Used by: Exception handling in ScreenerService
- Integration: Import exception types

✅ **AccountData Service** (src/trading_bot/services/account_data.py)
- Buying power retrieval, caching pattern
- Used by: Optional context in screener results
- Integration: Optional integration for future enhancements

### New - Create

🆕 **ScreenerService** (src/trading_bot/services/screener_service.py)
- No existing pattern; core orchestration layer
- Tasks: T010-T015

🆕 **screener_schemas.py** (src/trading_bot/schemas/screener_schemas.py)
- New: ScreenerQuery, StockScreenerMatch, ScreenerResult dataclasses
- Tasks: T001-T003

🆕 **ScreenerLogger** (src/trading_bot/logging/screener_logger.py)
- New: JSONL audit trail specialized for screener
- Tasks: T016-T017

---

## Dependency Graph

**Story completion order** (sequential phases):

1. **Phase 1: Setup** (T001-T003) - Shared infrastructure
   - ScreenerQuery, StockScreenerMatch, ScreenerResult dataclasses
   - Blocks: All other tasks (everyone depends on schemas)

2. **Phase 2: Foundational** (T004-T009) - Logging & configuration
   - ScreenerLogger, configuration initialization
   - Blocks: Phase 3 (needs logging for all queries)

3. **Phase 3: US1-US5 (MVP)** (T010-T025) - Core filtering
   - T010-T015: ScreenerService (core orchestration)
   - T016-T020: Individual filters (price, volume, float, daily_change, combined)
   - T021-T025: Pagination, error handling, integration tests
   - **Independent**: All filter tasks can run in parallel

4. **Phase 4: US6 (Enhancement)** (T026-T028) - Caching
   - Result caching (60-second TTL)
   - Depends: Phase 3 (needs working screener first)

5. **Phase 5: US7 (Enhancement)** (T029-T031) - CSV export
   - Export functionality
   - Depends: Phase 3 (needs screener results)

6. **Phase 6: Polish** (T032) - Error handling & resilience
   - Circuit breaker integration, comprehensive error logging

---

## Parallel Execution Opportunities

**High parallelization potential:**

- **Phase 1**: T001, T002, T003 (independent dataclass definitions)
- **Phase 2**: T004, T005, T006 (independent setup files)
- **Phase 3 Filters**: T016-T020 (all independent, different filter logic)
- **Phase 3 Tests**: T021-T025 (tests for different scenarios)

**Optimal Parallelization** (3 developers):
- Developer 1: T001-T003 (schemas), T010-T015 (ScreenerService core)
- Developer 2: T004-T006 (logging), T016-T020 (filters)
- Developer 3: T021-T025 (tests), T026-T032 (enhancements + polish)

---

## Implementation Strategy

**MVP Scope**: Phase 3 (US1-US5) - Core filtering functionality
- Filter by price range ✅
- Filter by relative volume ✅
- Filter by float size ✅
- Filter by daily performance ✅
- Combine multiple filters ✅

**Incremental Delivery**:
1. Phase 3 complete → Local testing + validation
2. Phase 4 optional (caching, performance optimization)
3. Phase 5 optional (CSV export)

**Testing Approach**: TDD required
- All new code must have unit tests (100% coverage for new code)
- Integration tests for filter combinations
- E2E tests for complete screener workflows

---

# Phase 1: Setup (Shared Infrastructure)

**Goal**: Create data contracts for screener (dataclasses, validation)

- [ ] T001 Create ScreenerQuery dataclass in src/trading_bot/schemas/screener_schemas.py
  - Fields: min_price, max_price, relative_volume, float_max, min_daily_change, limit, offset, query_id
  - Validation: min_price < max_price (if both set), limit 1-500, offset >= 0
  - REUSE: Pydantic dataclass pattern from AccountData
  - Pattern: src/trading_bot/schemas/account_schemas.py
  - From: data-model.md ScreenerQuery entity

- [ ] T002 Create StockScreenerMatch dataclass in src/trading_bot/schemas/screener_schemas.py
  - Fields: symbol, bid_price, volume, volume_avg_100d, float_shares, daily_open, daily_close, daily_change_pct, daily_change_direction, matched_filters, data_gaps, timestamp
  - Validation: symbol uppercase alphanumeric (1-5 chars), bid_price > 0, daily_change_pct 0-1000
  - REUSE: Decimal precision from TradeRecord
  - Pattern: src/trading_bot/schemas/account_schemas.py Position
  - From: data-model.md StockScreenerMatch entity

- [ ] T003 Create ScreenerResult & PageInfo dataclasses in src/trading_bot/schemas/screener_schemas.py
  - ScreenerResult fields: query_id, stocks[], query_timestamp, result_count, total_count, execution_time_ms, page_info, errors[], api_calls_made, cache_hit
  - PageInfo fields: offset, limit, has_more, next_offset, page_number
  - Validation: result_count <= limit, has_more logic (total_count > offset + limit)
  - REUSE: UUID handling from trade-logging
  - Pattern: src/trading_bot/schemas/trade_schemas.py TradeRecord
  - From: data-model.md ScreenerResult entity

---

# Phase 2: Foundational (Logging & Configuration)

**Goal**: Setup logging infrastructure for audit trail

- [ ] T004 [P] Create ScreenerLogger class in src/trading_bot/logging/screener_logger.py
  - Methods: log_query(query, result, execution_time_ms), log_data_gap(symbol, field, reason), log_error(error_type, recoverable, retry_count)
  - Daily rotation: logs/screener/YYYY-MM-DD.jsonl
  - Thread-safe: Use threading.Lock for concurrent writes
  - REUSE: StructuredTradeLogger pattern (daily rotation, field validation)
  - Pattern: src/trading_bot/logging/structured_trade_logger.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T005 [P] Write unit tests for ScreenerLogger in tests/unit/logging/test_screener_logger.py
  - Test: log_query() writes valid JSONL format
  - Test: Daily rotation creates new file at midnight
  - Test: Thread-safe writes (10 concurrent threads, 100 writes each)
  - Coverage: ≥90% (ScreenerLogger class)
  - Pattern: tests/unit/logging/test_structured_trade_logger.py
  - From: spec.md §Testing_Requirements

- [ ] T006 [P] Create screener configuration in src/trading_bot/config/screener_config.py
  - Config: LOG_DIR="logs/screener", BATCH_SIZE=100, MAX_RESULTS_PER_PAGE=500, CACHE_TTL_SECONDS=60
  - From environment: Optional SCREENER_LOG_LEVEL, SCREENER_BATCH_SIZE
  - REUSE: Config pattern from src/trading_bot/config/config.py
  - Pattern: src/trading_bot/config/market_data_config.py
  - From: plan.md [ARCHITECTURE DECISIONS]

---

# Phase 3: User Story 1-5 (MVP - Core Filtering)

**Goal**: Implement core screener functionality (all filters + combination)

## 3a: Foundation (ScreenerService Core)

- [ ] T010 [P] Create ScreenerService class skeleton in src/trading_bot/services/screener_service.py
  - Constructor: __init__(market_data_service, logger, config)
  - Main method: filter(query: ScreenerQuery) -> ScreenerResult
  - Helper methods: _apply_price_filter(), _apply_volume_filter(), _apply_float_filter(), _apply_daily_change_filter(), _paginate_results()
  - Decorator: @with_retry(policy=RetryPolicy.DEFAULT)
  - REUSE: MarketDataService injection pattern from SafetyChecks
  - Pattern: src/trading_bot/services/market_data_service.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T011 Write unit test scaffold for ScreenerService in tests/unit/services/test_screener_service.py
  - Setup: Mock market_data_service, logger
  - Fixtures: mock_quote_list (10 stocks with varied data)
  - Tests structure: One test per filter (price, volume, float, daily_change, combined)
  - Pattern: tests/unit/services/test_market_data_service.py
  - From: spec.md §Testing_Requirements

- [ ] T012 Create mock stock data fixtures in tests/unit/services/fixtures/mock_stocks.py
  - 10 mock Quote objects with realistic data
  - Range: Price $1-$30, volumes 100k-5M, floats 1M-100M, daily changes -20% to +20%
  - Names: TSLA_5x_volume, IPO_no_float, Gapper_up, Gapper_down, Normal_volume, etc.
  - REUSE: Quote dataclass from MarketDataService
  - Pattern: tests/fixtures/mock_trades.py
  - From: data-model.md Stock entity

## 3b: Individual Filters (Independent, Can Parallelize)

- [ ] T013 [P] [US3] Implement price range filter in ScreenerService._apply_price_filter()
  - Logic: Filter by bid_price >= min_price AND bid_price <= max_price
  - Edge cases: Handle None (skip filter), min=max (single price point), exact boundaries
  - REUSE: Decimal comparison from AccountData.get_buying_power()
  - Pattern: src/trading_bot/services/safety_checks.py validate methods
  - From: spec.md FR-003

- [ ] T014 [P] [US2] Implement relative volume filter in ScreenerService._apply_volume_filter()
  - Logic: Filter by current_volume >= (avg_volume_100d * relative_volume_multiplier)
  - Edge cases: Missing 100d avg (IPO) → use 1M default baseline, log data gap
  - REUSE: Arithmetic from PerformanceTracker (volume calculations)
  - Pattern: src/trading_bot/services/performance_tracking.py
  - From: spec.md FR-004

- [ ] T015 [P] [US3] Implement float size filter in ScreenerService._apply_float_filter()
  - Logic: Filter by public_float < float_max
  - Edge cases: Missing float (skip filter, log data gap), float=None → skip
  - REUSE: Optional type handling from AccountData
  - Pattern: src/trading_bot/services/account_data.py
  - From: spec.md FR-005

- [ ] T016 [P] [US4] Implement daily performance filter in ScreenerService._apply_daily_change_filter()
  - Logic: Filter by abs((daily_close - daily_open) / daily_open * 100) >= min_daily_change
  - Edge cases: Open price = 0 (skip), gap limits (stock moved >500%), negative changes (use abs)
  - REUSE: Percentage math from PerformanceTracker
  - Pattern: src/trading_bot/services/performance_tracking.py win_rate calculation
  - From: spec.md FR-006

- [ ] T017 [P] [US5] Implement combined filter logic in ScreenerService.filter()
  - Logic: Apply filters sequentially (price → volume → float → daily_change), AND logic
  - Results: Sort by volume descending (highest first)
  - Metadata: Include matched_filters list, data_gaps list per stock
  - REUSE: Filter chaining pattern from SafetyChecks
  - Pattern: src/trading_bot/services/safety_checks.py validation chain
  - From: spec.md FR-001, FR-007, FR-009

## 3c: Pagination & Response Building

- [ ] T018 [P] [US5] Implement pagination in ScreenerService._paginate_results()
  - Logic: Slice stocks[offset:offset+limit], return paginated + PageInfo
  - PageInfo: offset, limit, has_more (bool), next_offset (int|None), page_number (int)
  - Edge cases: offset >= total (return empty), limit > 500 (cap at 500), offset < 0 (reject)
  - REUSE: Pagination pattern from AccountData.get_positions()
  - Pattern: src/trading_bot/services/account_data.py pagination
  - From: spec.md FR-012

- [ ] T019 [P] [US5] Build ScreenerResult with metadata in ScreenerService.filter()
  - Fields: query_id (echo), stocks[], query_timestamp (now UTC), result_count, total_count, execution_time_ms, page_info, errors[], api_calls_made
  - Execution timing: Measure start → end, record in ms
  - API call count: Track MarketDataService calls
  - REUSE: Timing from PerformanceTracker.execute()
  - Pattern: src/trading_bot/logging/structured_trade_logger.py build TradeRecord
  - From: spec.md FR-010

## 3d: Integration & Error Handling

- [ ] T020 [P] Integrate MarketDataService.get_quote() calls in ScreenerService
  - Fetch quotes for candidate symbols (initially all available)
  - Handle quote fetch errors: Missing quote → log data_gap, continue
  - Rate limiting: @with_retry automatic exponential backoff (1s, 2s, 4s)
  - REUSE: MarketDataService integration from SafetyChecks
  - Pattern: src/trading_bot/services/safety_checks.py buy power check
  - From: plan.md [EXISTING INFRASTRUCTURE - REUSE]

- [ ] T021 [P] Add input validation to ScreenerService.filter()
  - Validate query: min_price < max_price, limit 1-500, offset >= 0 (FR-002, FR-011)
  - Raise ValueError with remediation message for constraint violations
  - REUSE: Validation pattern from SafetyChecks
  - Pattern: src/trading_bot/services/safety_checks.py validate_* methods
  - From: spec.md FR-002, FR-011

- [ ] T022 [P] Add @with_retry decorator to ScreenerService.filter()
  - Catches: RetriableError, RateLimitError
  - Backoff: 1s, 2s, 4s + jitter (via @with_retry)
  - Circuit breaker: 5 failures in 60s → shutdown screener
  - REUSE: @with_retry from error-handling-framework
  - Pattern: src/trading_bot/services/market_data_service.py
  - From: spec.md NFR-002

## 3e: Logging Integration

- [ ] T023 [P] Integrate ScreenerLogger.log_query() calls in ScreenerService
  - Log every completed query: Timestamp, params, result_count, execution_time_ms, errors
  - Log data gaps: Symbol, field, reason (e.g., "AKTR: float unavailable")
  - Async future: Non-blocking writes
  - REUSE: Logging pattern from TradingLogger
  - Pattern: src/trading_bot/logging/structured_trade_logger.py log_trade()
  - From: spec.md NFR-008, FR-010

## 3f: Unit Tests (Filters & Edge Cases)

- [ ] T024 [P] [US1-US5] Write unit tests for each filter in tests/unit/services/test_screener_service.py
  - test_price_range_filter_basic: 5 stocks, verify boundaries
  - test_price_range_filter_none: Skip filter if None
  - test_relative_volume_filter: 3 cases (below, at, above threshold)
  - test_float_filter_missing_data: Skip if None, log gap
  - test_daily_change_filter_both_directions: Up and down movers
  - test_combined_filters_and_logic: 5+ combinations
  - Coverage: ≥90% (ScreenerService)
  - Pattern: tests/unit/services/test_market_data_service.py
  - From: spec.md §Testing_Requirements

- [ ] T025 [P] [US5] Write integration tests in tests/integration/test_screener_service.py
  - Setup: Mock MarketDataService (not live API)
  - test_screener_returns_paginated_results: Offset, limit, has_more
  - test_screener_handles_no_results: Empty list, correct metadata
  - test_screener_latency_under_500ms: Execution time assertion
  - test_screener_logs_all_queries: Verify JSONL written
  - Coverage: ≥80% (critical paths)
  - Pattern: tests/integration/test_market_data_service.py
  - From: spec.md NFR-001, §Testing_Requirements

---

# Phase 4: User Story 6 (Enhancement - Caching)

**Goal**: Implement 60-second result caching to reduce API load

- [ ] T026 Add result caching to ScreenerService.filter() (optional, P2)
  - Cache key: Hash of query params (json.dumps sorted)
  - TTL: 60 seconds (user-configurable via config)
  - Return: Same ScreenerResult with cache_hit=True
  - Invalidation: After 60s, re-fetch from API
  - REUSE: Caching pattern from AccountData (TTL-based)
  - Pattern: src/trading_bot/services/account_data.py TTL cache
  - From: spec.md US6

- [ ] T027 Write tests for result caching in tests/unit/services/test_screener_caching.py
  - test_cache_hit_within_60s: Returns cached result
  - test_cache_miss_after_60s: Refreshes from API
  - test_cache_miss_different_params: Separate cache entries
  - Coverage: ≥85%

- [ ] T028 [P] Update screener_config.py with cache settings
  - CACHE_ENABLED=True, CACHE_TTL_SECONDS=60, MAX_CACHE_SIZE=100
  - From environment: Optional SCREENER_CACHE_TTL

---

# Phase 5: User Story 7 (Enhancement - CSV Export)

**Goal**: Export screener results to CSV for analysis

- [ ] T029 Add export_to_csv() method in ScreenerService (optional, P2)
  - Fields: symbol, bid_price, volume, float, daily_change_pct, timestamp
  - Format: UTF-8 encoded, header row, comma-separated
  - File naming: screener_YYYYMMDD_HHMMSS.csv
  - REUSE: CSV writing from pandas (existing dependency)
  - From: spec.md US7

- [ ] T030 Write tests for CSV export in tests/unit/services/test_screener_export.py
  - test_export_valid_rows: Correct number of rows
  - test_export_header: Column headers present
  - test_export_utf8_encoding: Non-ASCII characters handled
  - Coverage: ≥80%

- [ ] T031 [P] Add export command to CLI in src/trading_bot/cli/screener_cli.py
  - Command: `python -m trading_bot screener filter --export results.csv`
  - Options: --format (csv, json), --limit, --offset
  - From: plan.md [INTEGRATION SCENARIOS]

---

# Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Error handling, resilience, comprehensive testing

- [ ] T032 Add comprehensive error handling & logging
  - Handle missing data gracefully: Skip filter, log data_gap, continue
  - API errors: Logged with context, @with_retry handles backoff
  - Validation errors: Clear error messages with remediation
  - Update: error-log.md with error tracking strategy
  - From: spec.md FR-008, NFR-005

---

## Summary

| Phase | Tasks | User Stories | Focus |
|-------|-------|--------------|-------|
| 1 | T001-T003 | Setup | Dataclass schemas |
| 2 | T004-T006 | Foundational | Logging configuration |
| 3 | T010-T025 | US1-US5 | Core filtering (MVP) |
| 4 | T026-T028 | US6 | Caching enhancement |
| 5 | T029-T031 | US7 | CSV export enhancement |
| 6 | T032 | Polish | Error handling & resilience |

**Total**: 32 tasks
**MVP**: 16 tasks (T001-T025) for US1-US5 core functionality
**Enhancements**: 7 tasks (T026-T032) for US6-US7 + polish

**Testing**: 25%+ of tasks are tests (TDD approach)
- Unit tests: T005, T011, T012, T024, T027, T030
- Integration tests: T025
- Pattern: Test-first, implement second

**Parallelization**: 18 tasks marked [P] for parallel execution
- Phase 1: 3 parallel (T001-T003)
- Phase 2: 3 parallel (T004-T006)
- Phase 3 Filters: 5 parallel (T013-T017)
- Phase 3 Tests: Multiple parallel (T024-T025)

---

**Acceptance**:
- ✅ All tasks have concrete file paths (no `[ENTITY]` placeholders)
- ✅ REUSE markers identify existing patterns to follow
- ✅ Dependency graph enables parallel execution
- ✅ MVP scope clearly defined (US1-US5 core functionality)
- ✅ Testing approach: TDD (tests alongside implementation)

**Next Phase**: `/analyze` (cross-artifact consistency check + risk identification)
