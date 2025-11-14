# Implementation Plan: Level 2 Order Flow Integration

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11+, Polygon.io API, detector pattern architecture, file-based JSONL logging
- Components to reuse: 5 (MarketDataService patterns, @with_retry decorator, TradingLogger, config patterns)
- New components needed: 6 (OrderFlowDetector, TapeMonitor, PolygonClient, validators, data models, config)

**Key Decisions**:
1. Polygon.io API for Level 2 and Time & Sales (Robinhood API does NOT support this data)
2. Detector pattern following existing CatalystDetector architecture
3. Monitor active positions only (not continuous watchlist) to reduce API costs
4. File-based JSONL logging (no database schema) for audit trail
5. Frozen dataclass config pattern with from_env() class method
6. Python type hints with dataclasses for all data models

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (Constitution §Stack requirement)
- Data Provider: Polygon.io API ($99/month starter plan)
- SDK: polygon-api-client==1.12.5
- Logging: Structured JSONL to logs/order_flow/*.jsonl
- Configuration: Frozen dataclass + environment variables
- Error Handling: @with_retry decorator with exponential backoff
- Type System: Full type hints + mypy validation

**Patterns**:
- **Detector Pattern**: OrderFlowDetector follows CatalystDetector pattern (proven architecture for real-time scanning with alerts, structured logging, graceful degradation)
- **Repository Pattern**: PolygonClient abstracts API access for testability and future provider swapping
- **Configuration Pattern**: Frozen dataclass with from_env() class method (immutable, validated, environment-aware)
- **Validation Pattern**: Dedicated validators.py module following market_data/validators.py pattern (fail-fast on bad data per Constitution §Safety_First)
- **Retry Pattern**: @with_retry decorator with DEFAULT_POLICY (3 retries, exponential backoff, jitter)

**Dependencies** (new packages required):
- polygon-api-client==1.12.5: Official Polygon.io SDK for Level 2 and Time & Sales data

**Rationale**: All patterns follow existing codebase conventions from market_data and momentum modules. Zero architectural novelty reduces implementation risk and ensures Constitution compliance.

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/order_flow/
├── __init__.py                 # Module exports
├── order_flow_detector.py      # OrderFlowDetector class (large seller detection)
├── tape_monitor.py             # TapeMonitor class (red burst detection)
├── polygon_client.py           # PolygonClient class (API wrapper)
├── config.py                   # OrderFlowConfig dataclass
├── data_models.py              # OrderFlowAlert, OrderBookSnapshot, TimeAndSalesRecord
└── validators.py               # validate_level2_data(), validate_tape_data()

tests/order_flow/
├── test_order_flow_detector.py # OrderFlowDetector unit tests
├── test_tape_monitor.py        # TapeMonitor unit tests
├── test_polygon_client.py      # PolygonClient unit + integration tests
├── test_config.py              # OrderFlowConfig validation tests
├── test_validators.py          # Validator function tests
└── test_performance.py         # Performance benchmarks (latency, memory)

logs/order_flow/
└── {date}.jsonl                # Daily alert logs (e.g., 2025-10-22.jsonl)
```

**Module Organization**:
- **order_flow_detector.py**: Analyzes Level 2 order book snapshots, detects large sellers (>10k shares at bid), calculates alert severity, maintains alert history for exit signal evaluation
- **tape_monitor.py**: Processes Time & Sales tape, calculates 5-minute rolling average volume, detects red burst patterns (>300% volume spike with >60% sells)
- **polygon_client.py**: Wraps Polygon.io API calls, handles authentication, rate limiting, error handling, data normalization
- **config.py**: Immutable configuration dataclass with validation and environment variable loading
- **data_models.py**: Type-safe data models (OrderFlowAlert, OrderBookSnapshot, TimeAndSalesRecord, OrderFlowConfig)
- **validators.py**: Data integrity validation (timestamp freshness, price bounds, chronological sequence)

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 4 (OrderFlowAlert, OrderBookSnapshot, TimeAndSalesRecord, OrderFlowConfig)
- Relationships: OrderFlowAlert published to risk management module, logged to JSONL files
- Migrations required: No (file-based logging, no database schema)

**Key Entities**:
- **OrderFlowAlert**: Immutable alert record with symbol, alert_type, severity, order_size, price_level, volume_ratio, timestamp_utc
- **OrderBookSnapshot**: Level 2 data with bids (list[tuple[Decimal, int]]), asks (list[tuple[Decimal, int]]), timestamp_utc
- **TimeAndSalesRecord**: Tick data with symbol, price, size, side, timestamp_utc
- **OrderFlowConfig**: Configuration with large_order_size_threshold, volume_spike_threshold, red_burst_threshold, alert_window_seconds, data_source, polygon_api_key, monitoring_mode

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs** (or defaults from design/systems/budgets.md):
- NFR-001: Alert latency <2 seconds from data arrival to alert logged (P95)
- NFR-002: Data validation errors MUST halt order flow monitoring (fail-fast)
- NFR-003: All alerts MUST be logged to structured JSONL with UTC timestamps
- NFR-004: Thresholds MUST be configurable via environment variables
- NFR-005: API calls MUST respect rate limits with exponential backoff
- NFR-006: Memory usage MUST not exceed +50MB additional overhead

**Polygon.io Rate Limits** (Starter Plan $99/month):
- 5 requests per second
- Unlimited monthly requests
- Real-time data updates

**Measurement**:
- Latency: Extract from logs/order_flow/*.jsonl field `latency_ms`, calculate P95
- Memory: `ps aux | grep trading_bot | awk '{print $6}'` before and after feature enabled
- Alert frequency: `grep '"event":"order_flow_alert"' logs/order_flow/*.jsonl | wc -l`
- False positive rate: Manual validation of alerts against price drops

---

## [SECURITY]

**Authentication Strategy**:
- Polygon.io API key stored in environment variable POLYGON_API_KEY
- Never log API key (Constitution §Security)
- Validate API key presence at startup, fail fast if missing
- API key passed via query parameter (Polygon.io standard)

**Authorization Model**:
- N/A (internal Python module, no multi-user access)

**Input Validation**:
- All API responses validated before use (Constitution §Data_Integrity)
- Price bounds: >$0 (reject negative/zero prices)
- Order size bounds: >0 shares (reject negative/zero sizes)
- Timestamp freshness: <10 seconds (warn), <30 seconds (reject)
- Chronological sequence: Later ticks must have later timestamps
- Validation failures raise DataValidationError (fail-fast per Constitution §Safety_First)

**Rate Limiting**:
- Respect Polygon.io rate limits: 5 req/sec
- Use @with_retry decorator for HTTP 429 handling
- Exponential backoff with jitter (1s, 2s, 4s delays)
- Retry-After header respected if present
- After 3 retries: Graceful degradation (skip alert generation, log error)

**Data Protection**:
- No PII in order flow data (only ticker symbols, prices, volumes)
- Alert logs contain no user-identifiable information
- All timestamps in UTC (consistent timezone handling per Constitution §Data_Integrity)

---

## [EXISTING INFRASTRUCTURE - REUSE] (5 components)

**Services/Modules**:
- src/trading_bot/market_data/market_data_service.py:32-273: MarketDataService class patterns - @with_retry decorator usage, validation before use, _log_request() helper, _determine_market_state() logic
- src/trading_bot/error_handling/retry.py:30-148: @with_retry decorator - Exponential backoff with jitter, rate limit detection (HTTP 429), retry callbacks, circuit breaker integration
- src/trading_bot/error_handling/policies.py:16-94: DEFAULT_POLICY (3 retries, 1s/2s/4s delays), RetryPolicy dataclass with validation

**Logging**:
- src/trading_bot/logger.py:TradingLogger.get_logger(): Structured JSONL logging with UTC timestamps, extra fields support, Constitution §Audit_Everything compliance

**Configuration**:
- src/trading_bot/momentum/config.py:16-102: MomentumConfig pattern - Frozen dataclass, from_env() class method, __post_init__ validation, sensible defaults

---

## [NEW INFRASTRUCTURE - CREATE] (6 components)

**Backend** (Python modules):
- src/trading_bot/order_flow/order_flow_detector.py: OrderFlowDetector class
  - fetch_level2_snapshot(symbol: str) -> OrderBookSnapshot: Fetch Level 2 data via PolygonClient
  - detect_large_sellers(snapshot: OrderBookSnapshot) -> list[OrderFlowAlert]: Scan bids for orders >threshold
  - should_trigger_exit(alerts: list[OrderFlowAlert]) -> bool: Evaluate if 3+ alerts within window
  - _calculate_alert_severity(order_size: int) -> Literal["warning", "critical"]: Severity logic based on order size

- src/trading_bot/order_flow/tape_monitor.py: TapeMonitor class
  - fetch_tape_data(symbol: str, start_time: datetime, end_time: datetime) -> list[TimeAndSalesRecord]: Fetch Time & Sales via PolygonClient
  - calculate_rolling_average(window_minutes: int = 5) -> float: Calculate 5-minute rolling average volume
  - detect_red_burst(current_volume: float, avg_volume: float) -> OrderFlowAlert | None: Detect volume spikes >300% with >60% sells
  - _calculate_sell_ratio(ticks: list[TimeAndSalesRecord]) -> float: Calculate % of volume on sell side

- src/trading_bot/order_flow/polygon_client.py: PolygonClient class
  - __init__(api_key: str): Initialize with API key
  - get_level2_snapshot(symbol: str) -> dict: Raw API call to /v2/snapshot/locale/us/markets/stocks/tickers/{symbol}
  - get_time_and_sales(symbol: str, start_time: datetime, end_time: datetime) -> dict: Raw API call to /v3/trades/{symbol}
  - _handle_rate_limit(response: Response) -> None: Extract retry_after, raise RateLimitError
  - _normalize_level2_response(raw_data: dict) -> OrderBookSnapshot: Convert API response to OrderBookSnapshot dataclass
  - _normalize_tape_response(raw_data: dict) -> list[TimeAndSalesRecord]: Convert API response to TimeAndSalesRecord list

- src/trading_bot/order_flow/config.py: OrderFlowConfig dataclass
  - Fields: large_order_size_threshold, volume_spike_threshold, red_burst_threshold, alert_window_seconds, data_source, polygon_api_key, monitoring_mode
  - __post_init__(): Validate thresholds (large_order_size >=1000, volume_spike 1.5-10.0x, alert_window 30-300s)
  - from_env() classmethod: Load from ORDER_FLOW_* environment variables with sensible defaults

- src/trading_bot/order_flow/data_models.py: Data model dataclasses
  - OrderFlowAlert: symbol, alert_type, severity, order_size, price_level, volume_ratio, timestamp_utc
  - OrderBookSnapshot: symbol, bids, asks, timestamp_utc
  - TimeAndSalesRecord: symbol, price, size, side, timestamp_utc

- src/trading_bot/order_flow/validators.py: Validation functions
  - validate_level2_data(snapshot: OrderBookSnapshot) -> None: Validate timestamp freshness (<10s warn, <30s reject), price bounds (>$0), order size bounds (>0)
  - validate_tape_data(ticks: list[TimeAndSalesRecord]) -> None: Validate chronological sequence, price bounds, side values ("buy"/"sell")
  - validate_order_flow_config(config: OrderFlowConfig) -> None: Validate configuration constraints

**Rationale**: All new components follow existing patterns. OrderFlowDetector mirrors CatalystDetector structure. PolygonClient follows MarketDataService patterns. Config follows MomentumConfig pattern. Zero architectural novelty.

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local Python execution (not Railway-hosted, not Vercel-deployed)
- Env vars: 7 new ORDER_FLOW_* variables + POLYGON_API_KEY
- Breaking changes: No (new feature, opt-in, backward compatible)
- Migration: No (file-based logging, no database schema)

**Build Commands**:
- No changes (Python module, no build step required)

**Environment Variables** (update secrets.schema.json):
```json
{
  "order_flow": {
    "data_source": {
      "required": true,
      "default": "polygon",
      "description": "Data provider for Level 2 and Time & Sales (polygon only for MVP)"
    },
    "polygon_api_key": {
      "required": true,
      "secret": true,
      "description": "API key for Polygon.io Level 2/Time & Sales data"
    },
    "large_order_size": {
      "required": false,
      "default": "10000",
      "description": "Threshold for large order detection (shares)"
    },
    "volume_spike_threshold": {
      "required": false,
      "default": "3.0",
      "description": "Minimum volume ratio for red burst detection (multiplier)"
    },
    "red_burst_threshold": {
      "required": false,
      "default": "4.0",
      "description": "Critical volume spike threshold for exit signal (multiplier)"
    },
    "alert_window_seconds": {
      "required": false,
      "default": "120",
      "description": "Time window for consecutive alert detection (seconds)"
    },
    "monitoring_mode": {
      "required": false,
      "default": "positions_only",
      "description": "Monitoring scope (positions_only or watchlist)"
    }
  }
}
```

**New required**: ORDER_FLOW_DATA_SOURCE, POLYGON_API_KEY
**Changed variables**: None
**Schema update**: Yes - Add order_flow section to config/config.schema.json

**Database Migrations**:
- No (file-based logging, no database schema)

**Smoke Tests** (for deploy-staging.yml and promote.yml):
- N/A (local Python module, not web-deployed)

**Platform Coupling**:
- Vercel: None (backend-only feature)
- Railway: None (local execution, not Railway-hosted)
- Dependencies: New: polygon-api-client==1.12.5

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- ORDER_FLOW_* env vars configured with production values
- POLYGON_API_KEY valid and has sufficient API quota
- logs/order_flow/ directory exists and is writable
- No breaking changes to existing modules (order flow is opt-in)
- Feature gracefully degrades if API unavailable (no crashes)

**Staging Smoke Tests** (Given/When/Then):
```gherkin
Given trading bot running in paper mode with active position in AAPL
When OrderFlowDetector fetches Level 2 snapshot
Then snapshot contains valid bids and asks
  And snapshot timestamp is <10 seconds old
  And no DataValidationError raised
  And alert logged to logs/order_flow/{date}.jsonl if large seller detected

Given TapeMonitor analyzing Time & Sales data
When volume spike >300% with >60% sells detected
Then red burst alert logged with volume_ratio field
  And alert severity is "critical"
  And alert timestamp is UTC timezone-aware

Given 3 large seller alerts within 2 minutes
When should_trigger_exit() evaluated
Then exit signal returns True
  And risk management module receives exit recommendation
```

**Rollback Plan**:
- Deploy IDs tracked in: specs/028-level-2-order-flow-i/NOTES.md (Deployment Metadata)
- Rollback commands: `git revert <commit-sha>` (3-command rollback)
- Special considerations: No database rollback needed (file-based logging). Remove ORDER_FLOW_* env vars to disable feature entirely (graceful degradation)

**Artifact Strategy** (build-once-promote-many):
- N/A (local Python module, no build artifacts, no staging/production promotion)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Initial setup: Install polygon-api-client, set env vars, create logs directory
- Validation: Unit tests, integration tests, type checking, linting, security audit, coverage ≥90%
- Manual testing: Paper trading with simulated positions, verify alert logging, test exit signal logic, graceful degradation validation
- Performance testing: Latency benchmarks (<2s P95), memory profiling (<50MB), rate limit handling

---

## [INTEGRATION POINTS]

**Risk Management Module Integration**:
- OrderFlowDetector publishes OrderFlowAlert events
- Risk management module subscribes to alerts
- Exit evaluation logic: 3+ large seller alerts within 2 minutes OR red burst >400% volume spike
- Exit signal triggers position exit recommendation (not automatic exit, human-in-loop per Constitution §Safety_First)

**Position Manager Integration**:
- OrderFlowDetector queries active positions via PositionManager.get_active_positions()
- Monitors order flow only for symbols with active positions (FR-013, monitoring_mode="positions_only")
- If monitoring_mode="watchlist" (future enhancement), queries PositionManager.get_watchlist()

**Logging Integration**:
- All alerts logged via TradingLogger.get_logger(__name__)
- Log structure: `{"event": "order_flow_alert", "symbol": str, "alert_type": str, "severity": str, "order_size": int | null, "price_level": float | null, "volume_ratio": float | null, "timestamp_utc": str, "latency_ms": float}`
- Log files: logs/order_flow/{date}.jsonl (daily rotation)

**Configuration Integration**:
- OrderFlowConfig.from_env() loads ORDER_FLOW_* environment variables
- Config validation at startup, fail fast if POLYGON_API_KEY missing
- Config accessible via dependency injection (pass config to detector constructors)

---

## [TESTING STRATEGY]

**Unit Tests** (target: ≥90% coverage):
- test_order_flow_detector.py: Test large seller detection logic, alert severity calculation, exit signal evaluation, alert history management
- test_tape_monitor.py: Test rolling average calculation, red burst detection, sell ratio calculation
- test_polygon_client.py: Test API response normalization, rate limit handling, error handling (mock API calls)
- test_config.py: Test validation logic, from_env() loading, default values
- test_validators.py: Test timestamp freshness validation, price bounds validation, chronological sequence validation

**Integration Tests** (requires valid POLYGON_API_KEY):
- test_polygon_client.py (--integration flag): Test real API calls to Polygon.io, verify response structure, test rate limit handling with live API

**Performance Tests**:
- test_performance.py: Benchmark alert latency (target: <2s P95), measure memory usage (target: <50MB additional), test high-volume scenarios

**Mock Strategy**:
- Mock Polygon.io API responses using pytest-mock
- Mock time.sleep() in retry logic to speed up tests
- Mock PositionManager for active position queries
- Use fixtures for common test data (OrderBookSnapshot, TimeAndSalesRecord, OrderFlowAlert)

---

## [ERROR HANDLING]

**API Errors** (Polygon.io):
- HTTP 401 Unauthorized: Fail fast, log error, raise DataValidationError (invalid API key)
- HTTP 400 Bad Request: Skip monitoring for invalid ticker, log warning, continue
- HTTP 429 Rate Limit: Use @with_retry decorator, exponential backoff (1s/2s/4s), respect Retry-After header
- HTTP 500 Server Error: Retry up to 3 times, then graceful degradation (skip alert generation, log error)
- Network errors (ConnectionError, TimeoutError): Retry up to 3 times, then graceful degradation

**Data Validation Errors**:
- Stale timestamp (>30 seconds): Reject data, raise DataValidationError, halt monitoring for that symbol
- Invalid price (<=$0): Reject data, raise DataValidationError
- Invalid order size (<=0): Reject data, raise DataValidationError
- Chronological violation: Reject data, raise DataValidationError
- All validation errors logged with full context (Constitution §Audit_Everything)

**Graceful Degradation**:
- Missing POLYGON_API_KEY: Log warning, skip order flow monitoring, don't crash bot
- API unavailable: Retry 3 times, then disable order flow monitoring, continue with other features
- Data validation failure: Skip alert generation for that snapshot, continue monitoring other symbols

---

## [OBSERVABILITY]

**Structured Logging** (JSONL format):
```json
{
  "event": "order_flow_alert",
  "timestamp": "2025-10-22T14:35:20.123456Z",
  "symbol": "AAPL",
  "alert_type": "large_seller",
  "severity": "critical",
  "order_size": 15000,
  "price_level": 150.25,
  "volume_ratio": null,
  "latency_ms": 1234.56
}
```

**Metrics to Track**:
- Alert frequency: Count alerts by type (large_seller, red_burst)
- False positive rate: Alerts NOT followed by price drop within 5 minutes
- Alert latency: Time from API data arrival to alert logged (P50, P95, P99)
- Exit signal accuracy: % of exit signals that prevented >5% loss
- API errors: Count by error type (401, 429, 500, timeout, validation)
- Memory usage: Before and after order flow monitoring enabled

**Log Analysis Queries** (see quickstart.md Scenario 3):
- Alert frequency: `grep '"event":"order_flow_alert"' logs/order_flow/*.jsonl | wc -l`
- Alert latency P95: `cat logs/order_flow/*.jsonl | jq '.latency_ms' | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'`
- Exit signals: `grep '"event":"order_flow.exit_signal_triggered"' logs/order_flow/*.jsonl | wc -l`
- API errors: `grep '"error_type"' logs/order_flow/*.jsonl | jq -r '.error_type' | sort | uniq -c`
