# Tasks: Support/Resistance Zone Mapping

## [CODEBASE REUSE ANALYSIS]
Scanned: D:/Coding/Stocks/src/trading_bot/**/*.py, D:/Coding/Stocks/tests/**/*.py

[EXISTING - REUSE]
- ✅ MarketDataService (src/trading_bot/market_data/market_data_service.py) - OHLCV data fetching with retry logic
- ✅ BullFlagDetector pattern (src/trading_bot/momentum/bull_flag_detector.py) - Service architecture with config injection
- ✅ StructuredLogger (src/trading_bot/logging/structured_logger.py) - Thread-safe JSONL logger with daily rotation
- ✅ MomentumConfig pattern (src/trading_bot/momentum/config.py) - Dataclass with from_env classmethod
- ✅ @with_retry decorator (src/trading_bot/error_handling/retry.py) - API resilience with exponential backoff
- ✅ Decimal precision pattern (src/trading_bot/backtest/models.py, src/trading_bot/account/account_data.py)

[NEW - CREATE]
- 🆕 SupportResistanceDetector service (no existing pattern - new zone detection algorithm)
- 🆕 Zone/ZoneTouch/ProximityAlert dataclasses (new entities)
- 🆕 ZoneLogger (extends StructuredLogger pattern for zone-specific events)

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 1: Setup (independent - project structure)
2. Phase 2: Foundational (blocks all stories - models and config)
3. Phase 3: US1 [P1] - Daily zone identification (independent)
4. Phase 4: US2 [P1] - Zone strength scoring (depends on US1 zones)
5. Phase 5: US3 [P1] - Proximity alerts (depends on US1 zones)
6. Phase 6: US4 [P2] - 4-hour zones (depends on US1 algorithm)
7. Phase 7: US5 [P2] - Breakout detection (depends on US1 zones + US2 strength)
8. Phase 8: US6 [P3] - Bull flag integration (depends on US1 + existing bull_flag_detector.py)

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 2 Foundational: T003, T004, T005 (models.py, config.py, zone_logger.py - different files)
- Phase 3 US1: T010, T011 (unit tests for swing detection vs zone clustering - independent test cases)
- Phase 4 US2: T015, T016 (strength scoring logic vs unit tests - can write tests first)
- Phase 5 US3: T020, T021 (proximity check logic vs unit tests)
- Phase 6 US4: T025, T026 (4-hour detection vs integration test)
- Phase 7 US5: T030, T031 (breakout detection vs unit tests)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phase 3-5 (US1-US3) - Daily zone identification, strength scoring, proximity alerts
**Incremental delivery**: US1-US3 → validate accuracy → US4-US5 → US6 bull flag integration
**Testing approach**: TDD required - write unit tests before implementation for all core algorithms

---

## Phase 1: Setup

- [ ] T001 Create project structure per plan.md tech stack
  - Files: src/trading_bot/support_resistance/__init__.py, tests/unit/support_resistance/, tests/integration/support_resistance/
  - Pattern: src/trading_bot/momentum/ directory structure
  - From: plan.md [STRUCTURE]

- [ ] T002 Validate no new dependencies required
  - Check: requirements.txt has robin_stocks, pandas, numpy, pytest, mypy, ruff
  - Verify: No pip install needed
  - From: plan.md [ARCHITECTURE DECISIONS]

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Core data models and configuration that block all user stories

- [ ] T003 [P] Create Zone, ZoneTouch, ProximityAlert dataclasses in src/trading_bot/support_resistance/models.py
  - Entities: Zone (price_level, zone_type, strength_score, touch_count, first_touch_date, last_touch_date, average_volume, highest_volume_touch, timeframe)
  - Entities: ZoneTouch (zone_id, touch_date, price, volume, touch_type)
  - Entities: ProximityAlert (symbol, zone_id, current_price, zone_price, distance_percent, direction, timestamp)
  - Enums: ZoneType (SUPPORT, RESISTANCE), Timeframe (DAILY, FOUR_HOUR), TouchType (BOUNCE, REJECTION, BREAKOUT)
  - Validation: __post_init__ with price_level > 0, first_touch <= last_touch, distance_percent <= 2.0
  - Serialization: to_dict() and to_jsonl_line() methods
  - REUSE: Decimal precision pattern from src/trading_bot/backtest/models.py
  - Pattern: src/trading_bot/momentum/schemas/momentum_signal.py (dataclass structure)
  - From: plan.md [DATA MODEL], spec.md Key Entities

- [ ] T004 [P] Create ZoneDetectionConfig dataclass in src/trading_bot/support_resistance/config.py
  - Fields: touch_threshold (int, default=3), volume_threshold (Decimal, default=1.5), proximity_threshold_pct (Decimal, default=2.0), min_days (int, default=30), tolerance_pct (Decimal, default=1.5)
  - Method: from_env() classmethod for environment variable loading
  - Validation: min_days >= 30, tolerance_pct > 0
  - REUSE: MomentumConfig pattern from src/trading_bot/momentum/config.py
  - Pattern: src/trading_bot/momentum/config.py (dataclass with from_env)
  - From: plan.md [ALGORITHM DESIGN]

- [ ] T005 [P] Create ZoneLogger in src/trading_bot/support_resistance/zone_logger.py
  - Methods: log_zone_detection(symbol, zones, analysis_metadata), log_proximity_alert(alert), log_breakout(zone, breakout_metadata)
  - Features: Thread-safe file locking, daily rotation (logs/zones/YYYY-MM-DD-zones.jsonl), <5ms write latency
  - REUSE: StructuredLogger pattern from src/trading_bot/logging/structured_logger.py
  - Pattern: src/trading_bot/logging/structured_logger.py (thread-safe JSONL)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T006 Write unit tests for models validation in tests/unit/support_resistance/test_models.py
  - Test: Zone with negative price_level raises ValueError
  - Test: Zone with first_touch > last_touch raises ValueError
  - Test: ProximityAlert with distance > 2% raises ValueError
  - Test: Zone.to_dict() serializes all fields correctly
  - Test: ZoneTouch.to_jsonl_line() produces valid JSON
  - Pattern: tests/unit/services/momentum/test_momentum_signal.py
  - Coverage: 100% of new __post_init__ validation logic
  - From: plan.md [TDD APPROACH]

- [ ] T007 Write unit tests for ZoneLogger in tests/unit/support_resistance/test_zone_logger.py
  - Test: log_zone_detection writes valid JSONL to daily file
  - Test: Concurrent writes from 5 threads succeed without corruption
  - Test: Daily rotation creates new file at midnight
  - Pattern: tests/unit/test_structured_logger.py
  - Coverage: ≥80% line coverage
  - From: plan.md [TDD APPROACH]

---

## Phase 3: User Story 1 [P1] - Daily zone identification

**Story Goal**: Identify daily support/resistance zones from past 30-90 days with 3+ touches

**Independent Test Criteria**:
- [ ] System analyzes 60 days of daily OHLCV data successfully
- [ ] Identifies 3-5 zones with correct touch counts for AAPL test case
- [ ] Each zone includes price level, strength score, type, first/last touch dates

### Implementation

- [ ] T010 [P] Implement swing point detection in src/trading_bot/support_resistance/zone_detector.py
  - Method: _identify_swing_highs(ohlcv: pd.DataFrame) -> list[tuple[datetime, Decimal]]
  - Method: _identify_swing_lows(ohlcv: pd.DataFrame) -> list[tuple[datetime, Decimal]]
  - Logic: Swing high = bar.high > (prev_bar.high AND next_bar.high), Swing low = bar.low < (prev_bar.low AND next_bar.low)
  - REUSE: MarketDataService for OHLCV data (src/trading_bot/market_data/market_data_service.py)
  - Pattern: src/trading_bot/momentum/bull_flag_detector.py (_detect_pole method for DataFrame scanning)
  - From: plan.md [ALGORITHM DESIGN] Zone Detection Algorithm step 2

- [ ] T011 [P] Implement swing point clustering in src/trading_bot/support_resistance/zone_detector.py
  - Method: _cluster_swing_points(swing_points: list[tuple[datetime, Decimal]], tolerance_pct: Decimal) -> list[list[tuple[datetime, Decimal]]]
  - Logic: Group swing points within tolerance_pct (default 1.5%) into clusters
  - Algorithm: Iterate swing points, group if abs((price_a - price_b) / price_a) * 100 <= tolerance_pct
  - Pattern: plan.md [ALGORITHM DESIGN] Zone Merging Algorithm (similar clustering logic)
  - From: plan.md [ALGORITHM DESIGN] Zone Detection Algorithm step 3

- [ ] T012 Implement zone filtering and metadata calculation in src/trading_bot/support_resistance/zone_detector.py
  - Method: _build_zones_from_clusters(clusters: list, zone_type: ZoneType, ohlcv: pd.DataFrame, touch_threshold: int) -> list[Zone]
  - Logic: Filter clusters with >= touch_threshold touches (3 for daily)
  - Calculate: price_level (median of cluster), first_touch_date (min date), last_touch_date (max date)
  - Calculate: average_volume, highest_volume_touch from OHLCV data at touch dates
  - From: plan.md [ALGORITHM DESIGN] Zone Detection Algorithm steps 4-5

- [ ] T013 Implement main detect_zones method in src/trading_bot/support_resistance/zone_detector.py
  - Method: detect_zones(symbol: str, days: int, timeframe: Timeframe) -> list[Zone]
  - Steps: 1) Fetch OHLCV via MarketDataService, 2) Identify swings, 3) Cluster, 4) Filter by touches, 5) Build Zone objects
  - Error handling: Return empty list + warning if days < 30 (FR-008)
  - REUSE: @with_retry decorator from src/trading_bot/error_handling/retry.py for API calls
  - REUSE: MarketDataService from src/trading_bot/market_data/market_data_service.py
  - Pattern: src/trading_bot/momentum/bull_flag_detector.py (scan method structure)
  - From: plan.md [ALGORITHM DESIGN] Zone Detection Algorithm full flow

### Tests

- [ ] T014 [P] Write unit tests for swing point detection in tests/unit/support_resistance/test_zone_detector.py
  - Test: Given sample OHLCV with 2 swing highs and 3 swing lows, verify correct identification
  - Test: Edge case - first/last bars cannot be swing points (need prev/next for comparison)
  - Test: Swing high detection ignores bars where high <= prev.high OR high <= next.high
  - Given-When-Then structure
  - Pattern: tests/unit/services/momentum/test_bull_flag_detector.py (_detect_pole tests)
  - Coverage: 100% of swing detection logic

- [ ] T015 [P] Write unit tests for swing point clustering in tests/unit/support_resistance/test_zone_detector.py
  - Test: Swing points at [100.00, 101.00, 100.50] with 1.5% tolerance → single cluster
  - Test: Swing points at [100.00, 103.00] with 1.5% tolerance → two clusters (>2% apart)
  - Test: Empty swing_points list → empty clusters
  - Coverage: 100% of clustering logic

- [ ] T016 Write unit tests for zone filtering and metadata in tests/unit/support_resistance/test_zone_detector.py
  - Test: Cluster with 2 touches + touch_threshold=3 → filtered out (not enough touches)
  - Test: Cluster with 4 touches → Zone created with strength_score=4, correct first/last dates
  - Test: Volume calculation - average_volume matches mean of touch volumes
  - Coverage: 100% of zone building logic

---

## Phase 4: User Story 2 [P1] - Zone strength scoring

**Story Goal**: Score zones by touch count + volume bonus for prioritization

**Independent Test Criteria**:
- [ ] Each zone has strength score = touch_count + volume_bonus
- [ ] Zones sorted by strength score descending
- [ ] Volume bonus +1 for each touch with volume >1.5x average

### Implementation

- [ ] T017 Implement strength scoring in src/trading_bot/support_resistance/zone_detector.py
  - Method: _calculate_strength_score(touches: list[ZoneTouch], avg_volume: Decimal) -> int
  - Formula: base_score = len(touches), volume_bonus = sum(1 for touch in touches if touch.volume > avg_volume * Decimal("1.5"))
  - Return: base_score + volume_bonus
  - Pattern: plan.md [ALGORITHM DESIGN] Strength Scoring Algorithm (exact code provided)
  - From: plan.md [ALGORITHM DESIGN], spec.md FR-004

- [ ] T018 Update _build_zones_from_clusters to calculate and assign strength_score
  - Integration: Call _calculate_strength_score for each zone
  - Store: Assign result to Zone.strength_score field
  - From: plan.md [ALGORITHM DESIGN] Zone Detection Algorithm step 5

- [ ] T019 Implement zone sorting in detect_zones method
  - Logic: Sort zones by strength_score descending before returning
  - Code: zones.sort(key=lambda z: z.strength_score, reverse=True)
  - From: spec.md FR-007

### Tests

- [ ] T020 [P] Write unit tests for strength scoring in tests/unit/support_resistance/test_zone_detector.py
  - Test: 5 touches + 2 high-volume touches (>1.5x avg) → strength_score = 7
  - Test: 3 touches + 0 high-volume touches → strength_score = 3
  - Test: Empty touches list → strength_score = 0
  - Pattern: src/trading_bot/momentum/bull_flag_detector.py (_calculate_strength tests)
  - Coverage: 100% of scoring logic

- [ ] T021 [P] Write integration test for zone sorting in tests/integration/support_resistance/test_zone_detector_integration.py
  - Test: Given 5 identified zones with varying strength scores, verify sorted by strength descending
  - Real data: Mock MarketDataService with sample OHLCV
  - Pattern: tests/integration/momentum/test_bull_flag_detector_integration.py
  - Coverage: ≥80% of detect_zones method

---

## Phase 5: User Story 3 [P1] - Proximity alerts

**Story Goal**: Alert when current price is within 2% of any zone

**Independent Test Criteria**:
- [ ] Real-time proximity check calculates distance from current price to each zone
- [ ] Zones within 2% flagged as "approaching" with direction (support vs resistance)
- [ ] Approaching zones sorted by distance (closest first)

### Implementation

- [ ] T022 Implement proximity check in src/trading_bot/support_resistance/zone_detector.py
  - Method: check_proximity(zones: list[Zone], current_price: Decimal, threshold_pct: Decimal = Decimal("2.0")) -> list[ProximityAlert]
  - Logic: For each zone, calculate distance_pct = abs((current_price - zone.price_level) / zone.price_level) * 100
  - Filter: Only include zones where distance_pct <= threshold_pct
  - Direction: "APPROACHING_SUPPORT" if current_price > zone.price_level, else "APPROACHING_RESISTANCE"
  - Sort: By distance_pct ascending (closest first)
  - Pattern: plan.md [ALGORITHM DESIGN] Proximity Check Algorithm (exact code provided)
  - From: spec.md US3, FR-005

- [ ] T023 Integrate proximity alerts with ZoneLogger
  - Call: zone_logger.log_proximity_alert(alert) for each ProximityAlert
  - Log format: "Price $152.00 approaching resistance zone at $155.00 (+1.97%)"
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

### Tests

- [ ] T024 [P] Write unit tests for proximity check in tests/unit/support_resistance/test_zone_detector.py
  - Test: Zone at $100, current $102 → 2% distance, APPROACHING_RESISTANCE, alert triggered
  - Test: Zone at $100, current $97.50 → 2.5% distance, no alert (beyond 2% threshold)
  - Test: Zone at $100 (support), current $98.50 → 1.5% distance, APPROACHING_SUPPORT
  - Test: Multiple zones - verify sorted by distance ascending
  - Coverage: 100% of proximity check logic

- [ ] T025 [P] Write integration test for proximity logging in tests/integration/support_resistance/test_zone_detector_integration.py
  - Test: check_proximity triggers log_proximity_alert with correct JSONL format
  - Verify: Log file contains proximity event with symbol, zone_price, current_price, distance_percent
  - Pattern: tests/integration/test_trade_logging_integration.py
  - Coverage: ≥60% of logging integration

---

## Phase 6: User Story 4 [P2] - 4-hour zones

**Story Goal**: Identify 4-hour support/resistance zones for intraday precision

**Independent Test Criteria**:
- [ ] Analyzes 4-hour OHLCV data for past 30 days (~180 four-hour bars)
- [ ] Identifies zones with 2+ touches (lower threshold than daily)
- [ ] Differentiates daily vs 4-hour zones in output (zone.timeframe field)

### Implementation

- [ ] T026 Add timeframe parameter to detect_zones method
  - Signature: detect_zones(symbol: str, days: int, timeframe: Timeframe = Timeframe.DAILY) -> list[Zone]
  - Logic: If timeframe == FOUR_HOUR, use interval="4hour" for MarketDataService.get_historical_data()
  - Touch threshold: 2 for FOUR_HOUR, 3 for DAILY (conditional logic)
  - Store: Assign timeframe to Zone.timeframe field
  - From: spec.md US4, plan.md [ALGORITHM DESIGN]

- [ ] T027 Update ZoneDetectionConfig with timeframe-specific thresholds
  - Fields: daily_touch_threshold (default=3), four_hour_touch_threshold (default=2)
  - Use: Select threshold based on timeframe parameter
  - From: spec.md US4 acceptance criteria

### Tests

- [ ] T028 [P] Write unit tests for 4-hour zone detection in tests/unit/support_resistance/test_zone_detector.py
  - Test: Cluster with 2 touches + timeframe=FOUR_HOUR → Zone created
  - Test: Cluster with 2 touches + timeframe=DAILY → filtered out (needs 3+ for daily)
  - Test: Zone.timeframe field correctly set to FOUR_HOUR
  - Coverage: 100% of timeframe-specific logic

- [ ] T029 [P] Write integration test for 4-hour data fetch in tests/integration/support_resistance/test_zone_detector_integration.py
  - Test: detect_zones with timeframe=FOUR_HOUR fetches 4-hour OHLCV via MarketDataService
  - Verify: API called with interval="4hour"
  - Pattern: tests/integration/test_market_data_integration.py
  - Coverage: ≥60% of 4-hour integration

---

## Phase 7: User Story 5 [P2] - Breakout detection

**Story Goal**: Detect when price breaks through resistance with volume confirmation

**Independent Test Criteria**:
- [ ] Detects close price > resistance by 1%+ with volume >1.3x average
- [ ] Flips zone classification: resistance → support
- [ ] Logs breakout event with timestamp, price, volume ratio, zone flip

### Implementation

- [ ] T030 Implement breakout detection in src/trading_bot/support_resistance/zone_detector.py
  - Method: detect_breakout(zone: Zone, current_bar: dict, avg_volume: Decimal) -> bool
  - Logic: If zone.zone_type == RESISTANCE AND current_bar['close'] > zone.price_level * 1.01 AND current_bar['volume'] > avg_volume * 1.3
  - Return: True if breakout confirmed, False otherwise
  - Pattern: plan.md [ALGORITHM DESIGN] Breakout Detection Algorithm (exact code provided)
  - From: spec.md US5, FR-010

- [ ] T031 Implement zone flip logic
  - Method: flip_zone_type(zone: Zone) -> Zone
  - Logic: Create new Zone with zone_type = SUPPORT (if was RESISTANCE), maintain all other fields
  - Add: breakout_events list to Zone dataclass for history tracking
  - From: spec.md US5 acceptance criteria

- [ ] T032 Integrate breakout logging
  - Call: zone_logger.log_breakout(zone, breakout_metadata) when detect_breakout returns True
  - Metadata: timestamp, close_price, volume_ratio, previous_type, new_type
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

### Tests

- [ ] T033 [P] Write unit tests for breakout detection in tests/unit/support_resistance/test_zone_detector.py
  - Test: Resistance at $100, close $101.50 with 1.5x volume → breakout detected
  - Test: Resistance at $100, close $101.50 with 0.9x volume → no breakout (volume too low)
  - Test: Resistance at $100, close $100.50 with 1.5x volume → no breakout (price <1% above)
  - Test: Support zone → no breakout (only tracks resistance breakouts for MVP)
  - Coverage: 100% of breakout detection logic

- [ ] T034 [P] Write integration test for zone flip in tests/integration/support_resistance/test_zone_detector_integration.py
  - Test: Breakout triggers zone_type flip from RESISTANCE → SUPPORT
  - Test: Breakout event logged to JSONL with correct metadata
  - Pattern: tests/integration/momentum/test_bull_flag_detector_integration.py
  - Coverage: ≥60% of breakout integration

---

## Phase 8: User Story 6 [P3] - Bull flag integration

**Story Goal**: Adjust bull flag profit targets based on nearest resistance zone

**Independent Test Criteria**:
- [ ] When bull flag generates entry signal, calculate distance to nearest resistance zone
- [ ] If resistance zone closer than 2:1 R:R target, adjust target to 90% of zone price
- [ ] If no resistance within 5%, use standard 2:1 R:R target

### Implementation

- [ ] T035 Add zone integration method to BullFlagDetector in src/trading_bot/momentum/bull_flag_detector.py
  - Method: _adjust_target_for_zones(entry_price: Decimal, default_target: Decimal, zones: list[Zone]) -> Decimal
  - Logic: Find nearest resistance zone above entry_price
  - If zone.price_level < default_target AND zone within 5% of entry → adjusted_target = zone.price_level * 0.9
  - Else → return default_target
  - From: spec.md US6

- [ ] T036 Update BullFlagDetector.__init__ to accept SupportResistanceDetector dependency
  - Parameter: zone_detector: SupportResistanceDetector | None = None
  - Store: self.zone_detector = zone_detector
  - From: plan.md [INTEGRATION SCENARIOS]

- [ ] T037 Integrate zone detection in BullFlagDetector.scan method
  - If self.zone_detector is not None, call detect_zones(symbol, days=90, timeframe=DAILY)
  - Pass zones to _adjust_target_for_zones when calculating price_target
  - Log: "Target adjusted to $154.50 (resistance zone at $155.00, original 2:1 target $156.00)"
  - From: spec.md US6 acceptance criteria

### Tests

- [ ] T038 [P] Write unit tests for target adjustment in tests/unit/services/momentum/test_bull_flag_detector.py
  - Test: Entry $150, default target $156, resistance zone at $155 → adjusted to $139.50 (90% of $155)
  - Test: Entry $150, default target $156, no resistance within 5% → target unchanged at $156
  - Test: Entry $150, resistance at $160 (>5% away) → target unchanged (resistance too far)
  - Coverage: 100% of target adjustment logic

- [ ] T039 [P] Write integration test for bull flag + zone integration in tests/integration/momentum/test_bull_flag_detector_integration.py
  - Test: Bull flag scan with zone_detector → price_target adjusted based on resistance
  - Test: Log output includes target adjustment message
  - Pattern: tests/integration/momentum/test_bull_flag_detector_integration.py (existing structure)
  - Coverage: ≥60% of integration path

---

## Phase 9: Polish & Cross-Cutting Concerns

### Error Handling & Resilience

- [ ] T040 Add graceful degradation for insufficient data in detect_zones
  - Check: If days < 30, log warning "Insufficient historical data for {symbol}: {available_days} days (minimum 30 required)"
  - Return: Empty list with warning log (FR-008)
  - From: plan.md [RISK MITIGATION]

- [ ] T041 [P] Add retry logic with exponential backoff for API calls
  - Apply: @with_retry decorator to MarketDataService.get_historical_data() calls
  - Config: max_attempts=3, backoff_factor=2
  - REUSE: @with_retry from src/trading_bot/error_handling/retry.py
  - Pattern: src/trading_bot/momentum/bull_flag_detector.py (existing retry usage)
  - From: plan.md [RISK MITIGATION]

### Deployment Preparation

- [ ] T042 Document rollback procedure in specs/023-support-resistance-mapping/NOTES.md
  - Command: rm -rf src/trading_bot/support_resistance/, remove imports from src/trading_bot/momentum/bull_flag_detector.py
  - Feature flag: Not applicable (local-only feature)
  - Database: No migration (in-memory processing)
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] T043 [P] Add performance validation test in tests/performance/test_zone_detector_performance.py
  - Test: detect_zones completes in <3 seconds for 90 days of daily data (NFR-001)
  - Test: check_proximity completes in <100ms for 10 zones (NFR-002)
  - Measure: Use time.perf_counter() for timing
  - Pattern: tests/performance/test_validator_performance.py
  - From: plan.md [PERFORMANCE TARGETS]

### Local Validation

- [ ] T044 Add type checking validation to pre-commit checklist
  - Command: mypy src/trading_bot/support_resistance/
  - Expected: No type errors, 100% type coverage
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] T045 [P] Add linting validation to pre-commit checklist
  - Command: ruff check src/trading_bot/support_resistance/
  - Expected: No linting errors
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] T046 Create manual smoke test script in tests/smoke/test_zone_detection_smoke.py
  - Test: Import SupportResistanceDetector successfully
  - Test: detect_zones("AAPL", days=60, timeframe=DAILY) returns 3-5 zones
  - Test: check_proximity with real zones returns correct alerts
  - Pattern: tests/smoke/test_atr_smoke.py
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

---

## [TEST GUARDRAILS]

**Speed Requirements**:
- Unit tests: <2s each
- Integration tests: <10s each
- Full suite: <6 min total

**Coverage Requirements**:
- New code: 100% coverage (no untested lines in new features)
- Unit tests: ≥80% line coverage
- Integration tests: ≥60% line coverage
- Modified code: Coverage cannot decrease

**Measurement**:
- Python: `pytest --cov=src/trading_bot/support_resistance --cov-report=term-missing`

**Quality Gates**:
- All tests must pass before merge
- Coverage thresholds enforced in local validation
- No skipped tests without tracking

**Clarity Requirements**:
- One behavior per test
- Descriptive names: `test_zone_with_negative_price_raises_value_error()`
- Given-When-Then structure in test body

**Anti-Patterns**:
- ❌ NO property-mirror tests (test behavior, not implementation)
- ✅ USE real data in integration tests (actual MarketDataService responses)
- ✅ USE Decimal precision in all test assertions (match production code)

**Examples**:
```python
# ❌ Bad: Property-mirror test
assert zone.strength_score == 5

# ✅ Good: Behavior test
assert zone.strength_score == len(zone.touches) + volume_bonus_count

# ❌ Bad: Float comparison
assert zone.price_level == 100.5

# ✅ Good: Decimal comparison
assert zone.price_level == Decimal("100.50")
```

**Reference**: plan.md [TDD APPROACH] for test-first implementation order
