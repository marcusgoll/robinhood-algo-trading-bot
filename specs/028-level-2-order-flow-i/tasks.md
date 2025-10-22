# Tasks: Level 2 Order Flow Integration

## [CODEBASE REUSE ANALYSIS]
Scanned: D:/Coding/Stocks/src/trading_bot/**/*.py

[EXISTING - REUSE]
- ✅ CatalystDetector pattern (src/trading_bot/momentum/catalyst_detector.py) - Proven detector architecture
- ✅ MarketDataService patterns (src/trading_bot/market_data/market_data_service.py) - API wrapper patterns
- ✅ @with_retry decorator (src/trading_bot/error_handling/retry.py) - Exponential backoff, rate limit handling
- ✅ DEFAULT_POLICY (src/trading_bot/error_handling/policies.py) - 3 retries, 1s/2s/4s delays
- ✅ TradingLogger (src/trading_bot/logger.py) - Structured JSONL logging
- ✅ MomentumConfig pattern (src/trading_bot/momentum/config.py) - Frozen dataclass with from_env()
- ✅ Validator patterns (src/trading_bot/market_data/validators.py) - Fail-fast validation

[NEW - CREATE]
- 🆕 OrderFlowDetector (no existing Level 2 order book analyzer)
- 🆕 TapeMonitor (no existing Time & Sales analyzer)
- 🆕 PolygonClient (new data provider integration)
- 🆕 OrderFlowConfig (new configuration dataclass)
- 🆕 Order flow data models (OrderFlowAlert, OrderBookSnapshot, TimeAndSalesRecord)
- 🆕 Order flow validators (validate_level2_data, validate_tape_data)

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 1: Setup (project structure, dependencies)
2. Phase 2: Foundational (shared infrastructure - config, data models, validators, API client)
3. Phase 3: US1 [P1] - Large seller detection (Level 2 order book analysis)
4. Phase 4: US2 [P1] - Red burst detection (Time & Sales volume spike analysis)
5. Phase 5: US3 [P1] - Risk management integration (exit signals)
6. Phase 6: US4 [P2] - Configurable thresholds (enhancement)
7. Phase 7: US5 [P2] - Data validation (enhancement)
8. Phase 8: Polish & Cross-Cutting Concerns

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 2: T005, T006, T007 (data models, validators, config - different files)
- Phase 3 (US1): T013, T014 (tests can run while implementing detector)
- Phase 4 (US2): T019, T020 (tests can run while implementing monitor)
- Phase 6 (US4): T029, T030 (config tests + environment variable tests)
- Phase 7 (US5): T032, T033 (validator tests for Level 2 and Tape data)
- Phase 8: T035, T036, T037 (error handling, health check, smoke tests - different concerns)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phase 3-5 (US1-US3) - Core order flow monitoring with exit signals
**Incremental delivery**: US1 → staging validation → US2 → US3 → full integration validation
**Testing approach**: TDD required for all detector logic, optional integration tests (Polygon.io API key required)

---

## Phase 1: Setup

- [ ] T001 Create order_flow module directory structure
  - Directories: src/trading_bot/order_flow/, tests/order_flow/, logs/order_flow/
  - Files: __init__.py in src/trading_bot/order_flow/ and tests/order_flow/
  - Pattern: src/trading_bot/momentum/ module structure
  - From: plan.md [STRUCTURE]

- [ ] T002 [P] Install polygon-api-client dependency
  - File: requirements.txt
  - Package: polygon-api-client==1.12.5
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T003 [P] Add ORDER_FLOW_* environment variables to .env.example
  - File: .env.example
  - Variables: ORDER_FLOW_DATA_SOURCE, POLYGON_API_KEY, ORDER_FLOW_LARGE_ORDER_SIZE, ORDER_FLOW_VOLUME_SPIKE_THRESHOLD, ORDER_FLOW_RED_BURST_THRESHOLD, ORDER_FLOW_ALERT_WINDOW_SECONDS, ORDER_FLOW_MONITORING_MODE
  - From: plan.md [CI/CD IMPACT]

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Shared infrastructure that blocks all user stories

- [ ] T004 Create OrderFlowConfig dataclass in src/trading_bot/order_flow/config.py
  - Fields: large_order_size_threshold, volume_spike_threshold, red_burst_threshold, alert_window_seconds, data_source, polygon_api_key, monitoring_mode
  - Methods: __post_init__() validation, from_env() classmethod
  - REUSE: MomentumConfig pattern (src/trading_bot/momentum/config.py:16-102)
  - Pattern: Frozen dataclass with sensible defaults
  - From: data-model.md OrderFlowConfig entity

- [ ] T005 [P] Create data models in src/trading_bot/order_flow/data_models.py
  - Classes: OrderFlowAlert, OrderBookSnapshot, TimeAndSalesRecord
  - Fields: Per data-model.md entity definitions
  - REUSE: Dataclass pattern from market_data/data_models.py
  - From: data-model.md [ENTITIES]

- [ ] T006 [P] Create validators in src/trading_bot/order_flow/validators.py
  - Functions: validate_level2_data(), validate_tape_data(), validate_order_flow_config()
  - Validation: Timestamp freshness, price bounds, chronological sequence
  - REUSE: Validator pattern (src/trading_bot/market_data/validators.py)
  - Pattern: Fail-fast with DataValidationError
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] validators.py

- [ ] T007 [P] Create PolygonClient in src/trading_bot/order_flow/polygon_client.py
  - Methods: get_level2_snapshot(), get_time_and_sales(), _handle_rate_limit(), _normalize_level2_response(), _normalize_tape_response()
  - REUSE: @with_retry decorator (src/trading_bot/error_handling/retry.py:30-148)
  - REUSE: MarketDataService patterns (src/trading_bot/market_data/market_data_service.py:32-273)
  - Pattern: Repository pattern for API abstraction
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] polygon_client.py

---

## Phase 3: User Story 1 [P1] - Detect large sell orders in Level 2 order book

**Story Goal**: Identify institutional selling pressure before price drops

**Independent Test Criteria**:
- [ ] System fetches Level 2 order book data from Polygon.io API
- [ ] Identifies sell orders >10,000 shares at bid or below
- [ ] Logs alert with symbol, order size, price level, timestamp (UTC)
- [ ] Returns OrderFlowAlert dataclass with alert type and severity

### Tests

- [ ] T008 [P] [US1] Write test: OrderFlowConfig validates large_order_size_threshold
  - File: tests/order_flow/test_config.py
  - Test: Invalid threshold (<1000) raises ValueError
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py structure
  - Coverage: ≥90% (new code must be 100%)

- [ ] T009 [P] [US1] Write test: PolygonClient normalizes Level 2 API response
  - File: tests/order_flow/test_polygon_client.py
  - Test: Raw API response → OrderBookSnapshot dataclass
  - Mock: polygon-api-client responses
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py mocking strategy
  - Coverage: ≥90%

- [ ] T010 [P] [US1] Write test: OrderFlowDetector detects large sellers
  - File: tests/order_flow/test_order_flow_detector.py
  - Test: OrderBookSnapshot with >10k bid → OrderFlowAlert
  - Given-When-Then structure
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py test structure
  - Coverage: ≥90%

### Implementation

- [ ] T011 [US1] Implement PolygonClient.get_level2_snapshot() method
  - File: src/trading_bot/order_flow/polygon_client.py
  - API: /v2/snapshot/locale/us/markets/stocks/tickers/{symbol}
  - REUSE: @with_retry decorator for rate limit handling
  - Pattern: MarketDataService._log_request() helper
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] polygon_client.py

- [ ] T012 [US1] Implement PolygonClient._normalize_level2_response()
  - File: src/trading_bot/order_flow/polygon_client.py
  - Convert: Raw API dict → OrderBookSnapshot dataclass
  - Validation: Call validate_level2_data() before returning
  - Pattern: Data normalization from market_data_service.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] polygon_client.py

- [ ] T013 [US1] Create OrderFlowDetector class in src/trading_bot/order_flow/order_flow_detector.py
  - Methods: fetch_level2_snapshot(), detect_large_sellers(), should_trigger_exit(), _calculate_alert_severity()
  - REUSE: CatalystDetector pattern (src/trading_bot/momentum/catalyst_detector.py)
  - Pattern: Detector pattern with alert history (deque)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] order_flow_detector.py

- [ ] T014 [US1] Implement OrderFlowDetector.detect_large_sellers()
  - File: src/trading_bot/order_flow/order_flow_detector.py
  - Logic: Scan bids for orders >threshold at bid or below
  - Return: list[OrderFlowAlert] with severity calculation
  - REUSE: TradingLogger.get_logger() for structured logging
  - Pattern: CatalystDetector.analyze() method structure
  - From: spec.md US1 acceptance criteria

### Integration

- [ ] T015 [US1] Add integration test for PolygonClient with real API
  - File: tests/order_flow/test_polygon_client.py (--integration flag)
  - Requires: Valid POLYGON_API_KEY in environment
  - Test: Real API call to Polygon.io, verify response structure
  - Pattern: tests/integration/momentum/test_catalyst_detector_integration.py
  - Coverage: ≥80% critical path

---

## Phase 4: User Story 2 [P1] - Monitor Time & Sales tape for volume spikes

**Story Goal**: Detect red burst patterns indicating panic selling

**Independent Test Criteria**:
- [ ] System fetches real-time Time & Sales data from Polygon.io API
- [ ] Calculates 5-minute rolling average volume
- [ ] Detects volume spikes >300% of average with >60% sell-side volume
- [ ] Logs "red burst" alert with magnitude, sell ratio, timestamp

### Tests

- [ ] T016 [P] [US2] Write test: TapeMonitor calculates rolling average volume
  - File: tests/order_flow/test_tape_monitor.py
  - Test: 5-minute window of TimeAndSalesRecord → rolling average
  - Given-When-Then structure
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥90%

- [ ] T017 [P] [US2] Write test: TapeMonitor detects red burst
  - File: tests/order_flow/test_tape_monitor.py
  - Test: Volume spike >300% with >60% sells → OrderFlowAlert
  - Mock: TimeAndSalesRecord fixtures
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥90%

### Implementation

- [ ] T018 [US2] Implement PolygonClient.get_time_and_sales() method
  - File: src/trading_bot/order_flow/polygon_client.py
  - API: /v3/trades/{symbol}
  - Parameters: start_time, end_time (datetime objects)
  - REUSE: @with_retry decorator for rate limit handling
  - Pattern: MarketDataService API call patterns
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] polygon_client.py

- [ ] T019 [US2] Implement PolygonClient._normalize_tape_response()
  - File: src/trading_bot/order_flow/polygon_client.py
  - Convert: Raw API dict → list[TimeAndSalesRecord]
  - Validation: Call validate_tape_data() before returning
  - Pattern: Data normalization from market_data_service.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] polygon_client.py

- [ ] T020 [US2] Create TapeMonitor class in src/trading_bot/order_flow/tape_monitor.py
  - Methods: fetch_tape_data(), calculate_rolling_average(), detect_red_burst(), _calculate_sell_ratio()
  - State: tape_buffer (deque), volume_history (deque)
  - REUSE: CatalystDetector pattern for alert generation
  - Pattern: Rolling window with deque (bounded queue)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] tape_monitor.py

- [ ] T021 [US2] Implement TapeMonitor.calculate_rolling_average()
  - File: src/trading_bot/order_flow/tape_monitor.py
  - Logic: 5-minute rolling window, calculate average volume per minute
  - Data structure: deque with maxlen for memory efficiency
  - Pattern: Rolling average calculation patterns
  - From: spec.md US2 acceptance criteria

- [ ] T022 [US2] Implement TapeMonitor.detect_red_burst()
  - File: src/trading_bot/order_flow/tape_monitor.py
  - Logic: Volume spike >300% with >60% sells → OrderFlowAlert
  - Severity: "critical" if >400% spike (red_burst_threshold)
  - REUSE: TradingLogger for structured logging
  - Pattern: CatalystDetector alert generation
  - From: spec.md US2 acceptance criteria

### Integration

- [ ] T023 [US2] Add integration test for Time & Sales with real API
  - File: tests/order_flow/test_tape_monitor.py (--integration flag)
  - Requires: Valid POLYGON_API_KEY in environment
  - Test: Real API call, verify TimeAndSalesRecord normalization
  - Pattern: tests/integration/momentum/test_catalyst_detector_integration.py
  - Coverage: ≥80% critical path

---

## Phase 5: User Story 3 [P1] - Integrate order flow alerts with risk management

**Story Goal**: Trigger exits when selling pressure is detected

**Independent Test Criteria**:
- [ ] OrderFlowDetector publishes alerts to risk management module
- [ ] Risk management evaluates alert severity against position
- [ ] Triggers exit recommendation when: 3+ large sellers in 2 minutes OR red burst >400%
- [ ] Logs exit recommendation with reasoning (order flow pressure)

**Depends on**: US1, US2

### Tests

- [ ] T024 [P] [US3] Write test: OrderFlowDetector.should_trigger_exit() logic
  - File: tests/order_flow/test_order_flow_detector.py
  - Test: 3+ alerts within alert_window_seconds → True
  - Test: 2 alerts within window → False
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥90%

- [ ] T025 [P] [US3] Write test: Exit signal for red burst >400%
  - File: tests/order_flow/test_tape_monitor.py
  - Test: Red burst alert with volume_ratio >4.0 → exit signal
  - Mock: OrderFlowAlert fixtures
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥90%

### Implementation

- [ ] T026 [US3] Implement OrderFlowDetector.should_trigger_exit()
  - File: src/trading_bot/order_flow/order_flow_detector.py
  - Logic: Evaluate alert_history for 3+ large_seller alerts within alert_window_seconds
  - Return: bool (True if exit recommended)
  - Pattern: Alert evaluation logic from CatalystDetector
  - From: spec.md US3 acceptance criteria

- [ ] T027 [US3] Integrate OrderFlowDetector with risk management module
  - File: src/trading_bot/order_flow/order_flow_detector.py
  - Integration: Publish OrderFlowAlert events to risk management
  - Logging: Log exit signal with reasoning to logs/order_flow/{date}.jsonl
  - REUSE: TradingLogger for structured logging
  - Pattern: Risk management integration patterns
  - From: plan.md [INTEGRATION POINTS]

- [ ] T028 [US3] Add position monitoring logic to OrderFlowDetector
  - File: src/trading_bot/order_flow/order_flow_detector.py
  - Integration: Query PositionManager.get_active_positions()
  - Logic: Monitor order flow only for symbols with active positions (FR-013)
  - Pattern: Position manager integration from existing modules
  - From: spec.md FR-013

---

## Phase 6: User Story 4 [P2] - Configurable thresholds for order flow alerts

**Story Goal**: Tune sensitivity based on stock volatility and liquidity

**Depends on**: US1, US2

### Tests

- [ ] T029 [P] [US4] Write test: OrderFlowConfig validates threshold ranges
  - File: tests/order_flow/test_config.py
  - Test: large_order_size <1000 → ValueError
  - Test: volume_spike_threshold outside 1.5-10.0x → ValueError
  - Test: alert_window outside 30-300 seconds → ValueError
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py config tests
  - Coverage: ≥90%

- [ ] T030 [P] [US4] Write test: OrderFlowConfig.from_env() loads environment variables
  - File: tests/order_flow/test_config.py
  - Test: ORDER_FLOW_* env vars → OrderFlowConfig fields
  - Test: Missing env vars → sensible defaults
  - Mock: os.environ
  - Pattern: MomentumConfig.from_env() tests
  - Coverage: ≥90%

### Implementation

- [ ] T031 [US4] Add config file persistence to config/order_flow_config.json
  - File: config/order_flow_config.json (create)
  - Format: JSON with all OrderFlowConfig fields
  - Logic: Load from file if exists, else from environment variables
  - Pattern: Config file patterns from existing config modules
  - From: spec.md US4 acceptance criteria

---

## Phase 7: User Story 5 [P2] - Data validation before use

**Story Goal**: Ensure data integrity and prevent trading on stale or corrupt data

**Depends on**: US1, US2

### Tests

- [ ] T032 [P] [US5] Write test: validate_level2_data() rejects stale timestamps
  - File: tests/order_flow/test_validators.py
  - Test: Timestamp >30 seconds old → DataValidationError
  - Test: Timestamp <10 seconds old → Warning logged (not rejected)
  - Pattern: tests/unit/market_data/test_validators.py
  - Coverage: ≥90%

- [ ] T033 [P] [US5] Write test: validate_tape_data() rejects chronological violations
  - File: tests/order_flow/test_validators.py
  - Test: Later tick has earlier timestamp → DataValidationError
  - Test: Invalid price (<=0) → DataValidationError
  - Pattern: tests/unit/market_data/test_validators.py
  - Coverage: ≥90%

### Implementation

- [ ] T034 [US5] Enhance validators with comprehensive error logging
  - File: src/trading_bot/order_flow/validators.py
  - Logic: Log validation failures with specific error codes
  - Fields: error_type, error_message, invalid_data (sanitized)
  - REUSE: TradingLogger for structured logging
  - Pattern: Validator error logging from market_data/validators.py
  - From: spec.md US5 acceptance criteria

---

## Phase 8: Polish & Cross-Cutting Concerns

### Error Handling & Resilience

- [ ] T035 Add graceful degradation when Polygon.io API unavailable
  - File: src/trading_bot/order_flow/polygon_client.py
  - Logic: After 3 retries, log error and skip alert generation (don't crash bot)
  - Error types: HTTP 500, ConnectionError, TimeoutError
  - REUSE: @with_retry decorator with DEFAULT_POLICY
  - Pattern: Graceful degradation from market_data_service.py
  - From: plan.md [ERROR HANDLING]

- [ ] T036 [P] Add rate limit handling with Retry-After header
  - File: src/trading_bot/order_flow/polygon_client.py
  - Logic: Extract Retry-After from HTTP 429 response, sleep before retry
  - REUSE: @with_retry decorator rate limit detection
  - Pattern: Rate limit handling from error_handling/retry.py
  - From: plan.md [SECURITY]

### Deployment Preparation

- [ ] T037 [P] Add health check for order flow monitoring
  - File: src/trading_bot/order_flow/order_flow_detector.py
  - Method: health_check() → dict with status, last_alert_timestamp, api_connectivity
  - Return: { "status": "ok", "dependencies": { "polygon_api": "ok" } }
  - Pattern: Health check patterns from existing modules
  - From: plan.md [CI/CD IMPACT]

- [ ] T038 Document rollback procedure in NOTES.md
  - File: specs/028-level-2-order-flow-i/NOTES.md
  - Commands: Standard 3-command rollback (git revert)
  - Feature flag: Remove ORDER_FLOW_* env vars to disable entirely
  - Database: N/A (no database schema)
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

### Performance & Observability

- [ ] T039 [P] Add performance benchmarks for alert latency
  - File: tests/order_flow/test_performance.py
  - Benchmark: Time from API data arrival to alert logged (target: <2s P95)
  - Benchmark: Memory usage (target: <50MB additional)
  - Pattern: Performance testing patterns
  - From: plan.md [PERFORMANCE TARGETS]

- [ ] T040 Add structured logging for all alert events
  - Files: src/trading_bot/order_flow/order_flow_detector.py, tape_monitor.py
  - Events: order_flow.large_seller_detected, order_flow.red_burst_detected, order_flow.exit_signal_triggered
  - Format: JSONL with fields: event, timestamp, symbol, alert_type, severity, order_size, price_level, volume_ratio, latency_ms
  - REUSE: TradingLogger.get_logger() for structured logging
  - Pattern: Structured logging from Constitution §Audit_Everything
  - From: spec.md [MEASUREMENT PLAN]

---

## [TEST GUARDRAILS]

**Speed Requirements**:
- Unit tests: <2s each
- Integration tests: <10s each (requires POLYGON_API_KEY)
- Full suite: <6 min total

**Coverage Requirements**:
- New code: 100% coverage (no untested lines in new features)
- Unit tests: ≥90% line coverage
- Integration tests: ≥80% line coverage
- Modified code: Coverage cannot decrease

**Measurement**:
- Python: `pytest --cov=src/trading_bot/order_flow --cov-report=term-missing tests/order_flow/`

**Quality Gates**:
- All tests must pass before merge
- Coverage thresholds enforced in CI
- No skipped tests without justification

**Clarity Requirements**:
- One behavior per test
- Descriptive names: `test_detect_large_sellers_with_10k_bid_order_creates_warning_alert()`
- Given-When-Then structure in test body

**Anti-Patterns**:
- ❌ NO time.sleep() in tests (mock time instead)
- ❌ NO hard-coded API keys in tests (use environment variables)
- ✅ USE fixtures for common test data (OrderBookSnapshot, TimeAndSalesRecord, OrderFlowAlert)
- ✅ USE pytest-mock for external dependencies (Polygon.io API, PositionManager)

**Reference**: tests/unit/services/momentum/test_catalyst_detector.py for test structure patterns
