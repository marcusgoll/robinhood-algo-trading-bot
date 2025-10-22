# Tasks: Zone Breakout Detection with Volume Confirmation

## [CODEBASE REUSE ANALYSIS]
Scanned: D:\Coding\Stocks\src\trading_bot\support_resistance\**\*.py

[EXISTING - REUSE]
- ✅ ZoneDetector (src/trading_bot/support_resistance/zone_detector.py)
- ✅ Zone, ZoneType, TouchType, Timeframe models (src/trading_bot/support_resistance/models.py)
- ✅ ZoneLogger with thread-safe JSONL logging (src/trading_bot/support_resistance/zone_logger.py)
- ✅ ZoneDetectionConfig pattern (src/trading_bot/support_resistance/config.py)
- ✅ MarketDataService (src/trading_bot/market_data/market_data_service.py)
- ✅ @with_retry decorator (src/trading_bot/error_handling/retry.py)
- ✅ Test fixtures and patterns (tests/unit/support_resistance/test_zone_detector.py)
- ✅ Test infrastructure (tests/unit/support_resistance/test_models.py, test_zone_logger.py)

[NEW - CREATE]
- 🆕 BreakoutDetector service (no existing breakout detection)
- 🆕 BreakoutEvent, BreakoutStatus models (new entities)
- 🆕 BreakoutConfig configuration (new config pattern)
- 🆕 log_breakout_event() method extension to ZoneLogger

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 1: Setup (project structure verification)
2. Phase 2: Foundational (data models, config - blocks all stories)
3. Phase 3: US1 [P1] - Breakout detection logic (independent)
4. Phase 4: US2 [P1] - Zone flipping (depends on US1 BreakoutDetector)
5. Phase 5: US3 [P1] - Event logging (depends on US1, US2 models)
6. Phase 6: US4 [P2] - Breakout history (depends on US1-US3, optional)
7. Phase 7: US5 [P2] - Whipsaw validation (depends on US1-US3, optional)
8. Phase 8: US6 [P3] - Bidirectional breakouts (depends on US1-US3, optional)
9. Phase 9: Polish & validation

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 2: T003, T004, T005 (different files, no dependencies)
- Phase 3 (US1): T010, T011, T012 (test files can be written in parallel)
- Phase 4 (US2): T020, T021 (tests + implementation can run in parallel after models exist)
- Phase 5 (US3): T030, T031 (logger extension + tests in parallel)
- Phase 9: T080, T081, T082, T083 (polish tasks are independent)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phase 2-5 (US1-US3) only - breakout detection, zone flipping, event logging
**Incremental delivery**: US1 → US2 → US3 → validate with historical data → US4-US6 if needed
**Testing approach**: TDD required (Constitution §Testing_Requirements - 90% coverage target)
**Estimated effort**: 16-24 hours for MVP (US1-US3)

---

## Phase 1: Setup

- [ ] T001 Verify project structure matches plan.md
  - Directories: src/trading_bot/support_resistance/, tests/unit/support_resistance/, logs/zones/
  - Pattern: existing module structure (zone_detector.py, models.py, config.py)
  - From: plan.md [STRUCTURE]

- [ ] T002 [P] Verify parent feature (support-resistance-mapping) is available
  - Import: from src.trading_bot.support_resistance import ZoneDetector, Zone, ZoneType
  - Test: ZoneDetector.detect_zones() callable
  - From: NOTES.md Finding 1 (parent feature already implemented)

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Data models and configuration infrastructure that blocks all user stories

- [ ] T003 [P] Create BreakoutEvent dataclass in src/trading_bot/support_resistance/breakout_models.py
  - Fields: event_id (str), zone_id (str), timestamp (datetime UTC), breakout_price (Decimal), close_price (Decimal), volume (Decimal), volume_ratio (Decimal), old_zone_type (ZoneType), new_zone_type (ZoneType), status (BreakoutStatus), symbol (str), timeframe (Timeframe)
  - Validation: __post_init__() checks price > 0, volume >= 0, timestamp is UTC, status is valid
  - Methods: to_dict(), to_jsonl_line()
  - Pattern: src/trading_bot/support_resistance/models.py (Zone dataclass)
  - From: data-model.md BreakoutEvent entity

- [ ] T004 [P] Create BreakoutStatus enum in src/trading_bot/support_resistance/breakout_models.py
  - Values: PENDING = "pending", CONFIRMED = "confirmed", WHIPSAW = "whipsaw"
  - Pattern: src/trading_bot/support_resistance/models.py (ZoneType enum)
  - From: data-model.md BreakoutStatus entity

- [ ] T005 [P] Create BreakoutConfig dataclass in src/trading_bot/support_resistance/breakout_config.py
  - Fields: price_threshold_pct (Decimal = 1.0), volume_threshold (Decimal = 1.3), validation_bars (int = 5), strength_bonus (Decimal = 2.0)
  - frozen=True for immutability
  - Class method: from_env() loads from env vars (BREAKOUT_PRICE_THRESHOLD_PCT, BREAKOUT_VOLUME_THRESHOLD, BREAKOUT_VALIDATION_BARS, BREAKOUT_STRENGTH_BONUS)
  - Validation: __post_init__() checks all positive, reasonable ranges
  - Pattern: src/trading_bot/support_resistance/config.py (ZoneDetectionConfig)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] component 3

- [ ] T006 Update src/trading_bot/support_resistance/__init__.py exports
  - Add: BreakoutDetector, BreakoutEvent, BreakoutStatus, BreakoutConfig to __all__
  - Pattern: existing __init__.py (ZoneDetector, Zone, ZoneType exports)
  - From: plan.md [STRUCTURE]

---

## Phase 3: User Story 1 [P1] - Breakout detection with volume confirmation

**Story Goal**: Detect when price closes above resistance zone by >1% with volume >1.3x average

**Acceptance Criteria** (from spec.md US1):
- Monitor current price against all identified resistance zones
- Calculate close-to-close price change percentage from zone level
- Fetch current volume and calculate ratio vs 20-bar average volume
- Trigger breakout if: (close > zone_price * 1.01) AND (volume > avg_volume * 1.3)
- Return breakout signal with: zone_id, breakout_price, volume_ratio, timestamp

**Independent Test Criteria**:
- [ ] Given resistance at $155.00, close at $156.60 (+1.03%), volume 1.4x avg → breakout detected
- [ ] Given resistance at $200.00, close at $201.00 (+0.5%), volume 1.5x avg → no breakout (price <1%)
- [ ] Given resistance at $180.00, close at $182.00 (+1.11%), volume 0.9x avg → no breakout (volume <1.3x)

### Tests (TDD - write first)

- [ ] T010 [P] [US1] Write test: BreakoutDetector detects resistance breakout with valid price and volume
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Test: test_detect_breakout_valid_resistance_breakout()
  - Given: Zone at $155, price $156.60 (+1.03%), volume 1.4x avg
  - When: detect_breakout() called
  - Then: Returns BreakoutSignal with zone, event, flipped_zone
  - Pattern: tests/unit/support_resistance/test_zone_detector.py
  - Coverage: Happy path for breakout detection
  - From: contracts/api.yaml detect_breakout() examples

- [ ] T011 [P] [US1] Write test: BreakoutDetector rejects insufficient price move
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Test: test_detect_breakout_insufficient_price_move()
  - Given: Zone at $200, price $201 (+0.5%), volume 1.5x avg
  - When: detect_breakout() called
  - Then: Returns None (no breakout)
  - Pattern: tests/unit/support_resistance/test_zone_detector.py
  - Coverage: Price threshold validation (<1%)
  - From: spec.md Acceptance Scenario 2

- [ ] T012 [P] [US1] Write test: BreakoutDetector rejects insufficient volume
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Test: test_detect_breakout_insufficient_volume()
  - Given: Zone at $180, price $182 (+1.11%), volume 0.9x avg
  - When: detect_breakout() called
  - Then: Returns None (no breakout)
  - Pattern: tests/unit/support_resistance/test_zone_detector.py
  - Coverage: Volume threshold validation (<1.3x)
  - From: spec.md Acceptance Scenario 3

- [ ] T013 [P] [US1] Write test: BreakoutDetector validates input parameters
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Tests: test_detect_breakout_invalid_zone(), test_detect_breakout_negative_price(), test_detect_breakout_empty_volumes()
  - Given: Invalid inputs (None zone, negative price, empty volume list)
  - When: detect_breakout() called
  - Then: Raises ValueError or DataValidationError
  - Pattern: tests/unit/support_resistance/test_models.py (validation tests)
  - Coverage: Input validation edge cases
  - From: contracts/api.yaml detect_breakout() raises section

### Implementation

- [ ] T014 [US1] Create BreakoutDetector class in src/trading_bot/support_resistance/breakout_detector.py
  - Class: BreakoutDetector with __init__(config, market_data_service, logger)
  - Dependencies: BreakoutConfig, MarketDataService, ZoneLogger (dependency injection)
  - Pattern: src/trading_bot/support_resistance/zone_detector.py (ZoneDetector class)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] component 1

- [ ] T015 [US1] Implement _calculate_price_change_pct() helper in BreakoutDetector
  - Signature: _calculate_price_change_pct(zone_price: Decimal, current_price: Decimal) -> Decimal
  - Logic: (current_price - zone_price) / zone_price * 100
  - Return: Percentage as Decimal (e.g., Decimal("1.03") for +1.03%)
  - Pattern: Decimal arithmetic (no float) for precision
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] component 1

- [ ] T016 [US1] Implement _calculate_volume_ratio() helper in BreakoutDetector
  - Signature: _calculate_volume_ratio(current_volume: Decimal, historical_volumes: list[Decimal]) -> Decimal
  - Logic: avg_volume = sum(historical_volumes) / len(historical_volumes); return current_volume / avg_volume
  - Validation: historical_volumes must have >=20 bars (raise DataValidationError if less)
  - Return: Ratio as Decimal (e.g., Decimal("1.40") for 1.4x average)
  - Pattern: Decimal arithmetic, validate input length
  - From: research.md Decision 2 (20-bar volume average)

- [ ] T017 [US1] Implement detect_breakout() method in BreakoutDetector
  - Signature: detect_breakout(zone, current_price, current_volume, historical_volumes) -> BreakoutSignal | None
  - Logic:
    - price_change = _calculate_price_change_pct(zone.price_level, current_price)
    - volume_ratio = _calculate_volume_ratio(current_volume, historical_volumes)
    - if price_change > config.price_threshold_pct AND volume_ratio > config.volume_threshold:
      - create BreakoutEvent with all metadata
      - flip_zone() to create flipped zone
      - return BreakoutSignal(zone, event, flipped_zone)
    - else: return None
  - REUSE: _calculate_price_change_pct(), _calculate_volume_ratio()
  - Pattern: src/trading_bot/support_resistance/zone_detector.py (detect_zones method)
  - From: contracts/api.yaml detect_breakout() specification

---

## Phase 4: User Story 2 [P1] - Zone flipping upon breakout

**Story Goal**: Flip zone classification from resistance to support with strength bonus

**Acceptance Criteria** (from spec.md US2):
- On breakout detection, create new Zone instance with zone_type flipped (RESISTANCE → SUPPORT)
- Preserve all existing zone metadata (touch_count, dates, volumes)
- Update zone strength_score based on breakout confirmation (bonus +2 for volume-confirmed breakout)
- Return flipped zone to replace original in active zones list

**Independent Test Criteria**:
- [ ] Verify resistance zone at $155 flips to support with strength +2 after breakout

### Tests (TDD - write first)

- [ ] T020 [P] [US2] Write test: flip_zone() creates new Zone with flipped type
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Test: test_flip_zone_resistance_to_support()
  - Given: Zone(zone_type=RESISTANCE, strength=5.0), BreakoutEvent(old=RESISTANCE, new=SUPPORT)
  - When: flip_zone() called
  - Then: Returns new Zone with zone_type=SUPPORT, strength=7.0, all other fields preserved
  - Pattern: tests/unit/support_resistance/test_models.py (Zone immutability tests)
  - Coverage: Zone flipping logic, immutability preservation
  - From: contracts/api.yaml flip_zone() examples

- [ ] T021 [P] [US2] Write test: flip_zone() validates zone_type matches breakout event
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Test: test_flip_zone_type_mismatch_raises_error()
  - Given: Zone(zone_type=RESISTANCE), BreakoutEvent(old=SUPPORT, new=RESISTANCE)
  - When: flip_zone() called
  - Then: Raises ValueError (type mismatch)
  - Pattern: tests/unit/support_resistance/test_models.py (validation tests)
  - Coverage: Input validation for zone flipping
  - From: contracts/api.yaml flip_zone() raises section

### Implementation

- [ ] T022 [US2] Implement flip_zone() method in BreakoutDetector
  - Signature: flip_zone(zone: Zone, breakout_event: BreakoutEvent) -> Zone
  - Validation: zone.zone_type must match breakout_event.old_zone_type (raise ValueError if not)
  - Logic:
    - new_type = ZoneType.SUPPORT if zone.zone_type == ZoneType.RESISTANCE else ZoneType.RESISTANCE
    - new_strength = zone.strength_score + config.strength_bonus
    - return Zone(...) with all fields from zone except zone_type and strength_score
  - REUSE: Zone dataclass (immutable pattern)
  - Pattern: Create new instance rather than mutate (immutability)
  - From: contracts/api.yaml flip_zone() specification

- [ ] T023 [US2] Create BreakoutSignal dataclass in src/trading_bot/support_resistance/breakout_models.py
  - Fields: zone (Zone), event (BreakoutEvent), flipped_zone (Zone)
  - Purpose: Return value for detect_breakout() containing original zone, event, and flipped zone
  - Pattern: src/trading_bot/support_resistance/models.py (dataclass pattern)
  - From: contracts/api.yaml BreakoutSignal structure

---

## Phase 5: User Story 3 [P1] - Event logging with full context

**Story Goal**: Log all breakout events to JSONL with full metadata for backtesting

**Acceptance Criteria** (from spec.md US3):
- Create BreakoutEvent dataclass with fields: event_id, zone_id, timestamp, breakout_price, close_price, volume_ratio, old_zone_type, new_zone_type
- Extend ZoneLogger with log_breakout_event() method
- Write to logs/zones/breakouts-YYYY-MM-DD.jsonl (daily rotation)
- Include session context: bot_version, config_hash for reproducibility

**Independent Test Criteria**:
- [ ] Trigger breakout, verify JSONL log contains all required fields with UTC timestamp

### Tests (TDD - write first)

- [ ] T030 [P] [US3] Write test: ZoneLogger.log_breakout_event() writes to daily JSONL file
  - File: tests/unit/support_resistance/test_zone_logger.py
  - Test: test_log_breakout_event_creates_jsonl_file()
  - Given: BreakoutEvent with all fields populated, ZoneLogger initialized
  - When: log_breakout_event(event) called
  - Then: File logs/zones/breakouts-YYYY-MM-DD.jsonl exists with JSON line containing all event fields
  - Pattern: tests/unit/support_resistance/test_zone_logger.py (existing log tests)
  - Coverage: File creation, JSON serialization, daily rotation
  - From: contracts/api.yaml log_breakout_event() file format

- [ ] T031 [P] [US3] Write test: BreakoutEvent.to_jsonl_line() serializes correctly
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Test: test_breakout_event_to_jsonl_line()
  - Given: BreakoutEvent with sample data
  - When: to_jsonl_line() called
  - Then: Returns single-line JSON string with ISO timestamps, Decimal as strings, lowercase enum values
  - Pattern: tests/unit/support_resistance/test_models.py (Zone serialization tests)
  - Coverage: Serialization format, timestamp format, Decimal handling
  - From: contracts/api.yaml log_breakout_event() file format example

### Implementation

- [ ] T032 [US3] Extend ZoneLogger with log_breakout_event() method
  - File: src/trading_bot/support_resistance/zone_logger.py
  - Method: log_breakout_event(event: BreakoutEvent) -> None
  - Logic:
    - log_file = self.log_dir / f"breakouts-{datetime.now(UTC).strftime('%Y-%m-%d')}.jsonl"
    - thread-safe write: with self._lock, append event.to_jsonl_line()
    - graceful degradation: catch OSError, log to stderr, continue (no raise)
  - REUSE: Existing ZoneLogger thread-safety pattern (self._lock)
  - Pattern: src/trading_bot/support_resistance/zone_logger.py (log_zone_detection method)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] logging extension

- [ ] T033 [US3] Implement BreakoutEvent.to_jsonl_line() serialization
  - File: src/trading_bot/support_resistance/breakout_models.py (add to BreakoutEvent)
  - Method: to_jsonl_line() -> str
  - Logic:
    - dict = self.to_dict()
    - return json.dumps(dict, ensure_ascii=False, separators=(',', ':'))
  - Format: Single-line JSON (no pretty print)
  - REUSE: to_dict() method (already created in T003)
  - Pattern: src/trading_bot/support_resistance/models.py (Zone serialization)
  - From: contracts/api.yaml log_breakout_event() file format

- [ ] T034 [US3] Update detect_breakout() to log events
  - File: src/trading_bot/support_resistance/breakout_detector.py
  - Change: After creating BreakoutEvent, call self.logger.log_breakout_event(event)
  - Logic: if breakout detected → create event → log event → return signal
  - REUSE: ZoneLogger.log_breakout_event() (created in T032)
  - From: plan.md [IMPLEMENTATION PHASES] Phase 4

---

## Phase 6: User Story 4 [P2] - Breakout history tracking (OPTIONAL)

**Story Goal**: Maintain breakout history for each zone to track flip frequency

**Acceptance Criteria** (from spec.md US4):
- Add breakout_events: list[BreakoutEvent] field to Zone dataclass
- Append BreakoutEvent to zone.breakout_events list on each flip
- Expose zone.breakout_count property (len(breakout_events))
- Sort breakout_events chronologically (oldest first)

**Depends on**: US1, US2, US3

### Tests

- [ ] T040 [P] [US4] Write test: Zone tracks breakout_events list
  - File: tests/unit/support_resistance/test_models.py
  - Test: test_zone_breakout_events_tracking()
  - Given: Zone with breakout_events=[]
  - When: Multiple BreakoutEvents appended
  - Then: zone.breakout_count returns correct count, events sorted by timestamp
  - Pattern: tests/unit/support_resistance/test_models.py (Zone field tests)
  - Coverage: Breakout history tracking
  - From: spec.md US4 acceptance criteria

### Implementation

- [ ] T041 [US4] Add breakout_events field to Zone dataclass
  - File: src/trading_bot/support_resistance/models.py
  - Field: breakout_events: list[BreakoutEvent] = field(default_factory=list)
  - Property: breakout_count -> int (return len(self.breakout_events))
  - Pattern: Immutable list pattern (use field(default_factory=list))
  - From: data-model.md Zone extension

- [ ] T042 [US4] Update flip_zone() to append BreakoutEvent to history
  - File: src/trading_bot/support_resistance/breakout_detector.py
  - Change: When creating new Zone in flip_zone(), append breakout_event to breakout_events list
  - Logic: new_events = zone.breakout_events + [breakout_event]; Zone(..., breakout_events=new_events)
  - Pattern: Immutable list append (create new list)
  - From: spec.md US4 acceptance criteria

---

## Phase 7: User Story 5 [P2] - Whipsaw validation (OPTIONAL)

**Story Goal**: Validate breakout sustainability by detecting whipsaws (price returning below zone within 5 bars)

**Acceptance Criteria** (from spec.md US5):
- After breakout detection, monitor price for next 5 bars (5 hours for daily, 5x4h for 4-hour zones)
- If price closes below original zone level within 5 bars, mark breakout as "whipsaw" (failed)
- Update BreakoutEvent.status field: "confirmed", "whipsaw", or "pending" (within 5-bar window)
- Log whipsaw events separately for analysis

**Depends on**: US1, US3

### Tests

- [ ] T050 [P] [US5] Write test: Whipsaw detector marks failed breakouts
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Test: test_whipsaw_detection_marks_failed_breakout()
  - Given: BreakoutEvent at $156 from zone $155, next 3 bars close at $154
  - When: validate_breakout() called
  - Then: BreakoutEvent.status = WHIPSAW
  - Pattern: tests/unit/support_resistance/test_zone_detector.py
  - Coverage: Whipsaw detection logic
  - From: spec.md US5 acceptance criteria

### Implementation

- [ ] T051 [US5] Implement validate_breakout() method in BreakoutDetector
  - Signature: validate_breakout(event: BreakoutEvent, recent_closes: list[Decimal]) -> BreakoutEvent
  - Logic:
    - if len(recent_closes) < config.validation_bars: return event (status=PENDING)
    - if any close below original zone level: return BreakoutEvent(..., status=WHIPSAW)
    - else: return BreakoutEvent(..., status=CONFIRMED)
  - Pattern: Create new BreakoutEvent with updated status (immutability)
  - From: spec.md US5 acceptance criteria

---

## Phase 8: User Story 6 [P3] - Bidirectional breakouts (OPTIONAL)

**Story Goal**: Detect support-to-resistance breakdowns (price breaking down through support)

**Acceptance Criteria** (from spec.md US6):
- Detect when price closes below support zone by >1% with volume >1.3x average
- Flip zone: SUPPORT → RESISTANCE
- Log breakdown event (same structure as breakout)
- Maintain symmetry with breakout logic (reuse same validation, logging, flipping code)

**Depends on**: US1, US2, US3

### Implementation

- [ ] T060 [US6] Refactor detect_breakout() to handle bidirectional breakouts
  - File: src/trading_bot/support_resistance/breakout_detector.py
  - Change: Add direction parameter: detect_breakout(..., direction: Literal["up", "down"] = "up")
  - Logic:
    - if direction == "up": price_change = (current - zone) / zone * 100 (existing)
    - if direction == "down": price_change = (zone - current) / zone * 100 (new)
    - Reuse existing volume, logging, flipping logic
  - Pattern: Refactor for symmetry, avoid code duplication
  - From: spec.md US6 acceptance criteria

---

## Phase 9: Polish & Cross-Cutting Concerns

### Error Handling & Resilience

- [ ] T080 [P] Add input validation to BreakoutDetector.__init__()
  - File: src/trading_bot/support_resistance/breakout_detector.py
  - Validation: config not None, market_data_service not None, logger not None
  - Raise: TypeError with descriptive message
  - Pattern: src/trading_bot/support_resistance/zone_detector.py (__init__ validation)
  - From: plan.md [SECURITY] input validation

- [ ] T081 [P] Add graceful degradation for missing volume data
  - File: src/trading_bot/support_resistance/breakout_detector.py
  - Logic: In detect_breakout(), if historical_volumes is empty or None:
    - Log warning: "Volume data unavailable, skipping volume check"
    - Fall back to price-only detection (>1% move only)
    - Add "volume_check_skipped": true to BreakoutEvent metadata
  - Pattern: Graceful degradation (NFR-004)
  - From: plan.md [RISKS & MITIGATION] Risk 1

- [ ] T082 [P] Add performance benchmark test
  - File: tests/unit/support_resistance/test_breakout_detector.py
  - Test: test_detect_breakout_performance_under_200ms()
  - Logic: Run detect_breakout() 100 times, measure P95 latency
  - Assert: P95 < 200ms (NFR-001 requirement)
  - Tools: timeit or pytest-benchmark
  - Pattern: Performance testing
  - From: plan.md [PERFORMANCE TARGETS] benchmarking plan

### Documentation & Integration

- [ ] T083 [P] Update module docstrings with usage examples
  - Files: breakout_detector.py, breakout_models.py, breakout_config.py
  - Content: Add module-level docstrings with quickstart example from quickstart.md Scenario 6
  - Pattern: src/trading_bot/support_resistance/zone_detector.py (docstring style)
  - From: quickstart.md integration example

### Type Safety & Code Quality

- [ ] T084 Run mypy --strict on all new files
  - Command: mypy src/trading_bot/support_resistance/breakout_*.py --strict
  - Target: 0 errors (Constitution §Code_Quality requirement)
  - Fix: Add type annotations for all function signatures, return types
  - Pattern: Existing type annotations in zone_detector.py
  - From: plan.md [DEPLOYMENT ACCEPTANCE] type checking

- [ ] T085 [P] Run ruff check on all new files
  - Command: ruff check src/trading_bot/support_resistance/breakout_*.py
  - Target: 0 warnings (Constitution §Code_Quality requirement)
  - Fix: Address linting issues (unused imports, line length, etc.)
  - Pattern: Existing ruff compliance in support_resistance module
  - From: plan.md [DEPLOYMENT ACCEPTANCE] linting

- [ ] T086 [P] Run bandit security scan on all new files
  - Command: bandit -r src/trading_bot/support_resistance/breakout_*.py
  - Target: 0 HIGH/CRITICAL issues (Constitution §Pre_Commit gate)
  - Fix: Address security warnings (hardcoded secrets, SQL injection, etc.)
  - Pattern: Existing bandit compliance
  - From: plan.md [SECURITY] security scanning

### Testing & Coverage

- [ ] T087 Run pytest with coverage report
  - Command: pytest tests/unit/support_resistance/test_breakout_detector.py --cov=src.trading_bot.support_resistance.breakout_detector --cov-report=term-missing
  - Target: ≥90% coverage (Constitution §Testing_Requirements)
  - Fix: Add tests for uncovered branches/lines
  - Pattern: Existing test coverage in zone_detector tests
  - From: plan.md [DEPLOYMENT ACCEPTANCE] test coverage

- [ ] T088 [P] Create integration test for end-to-end workflow
  - File: tests/integration/support_resistance/test_breakout_integration.py
  - Test: test_breakout_detection_end_to_end()
  - Logic:
    - Initialize ZoneDetector, BreakoutDetector with real dependencies
    - Detect zones for AAPL (mock MarketDataService)
    - Trigger breakout detection
    - Verify: BreakoutSignal returned, JSONL log written, zone flipped
  - Pattern: Integration test pattern (real objects, minimal mocking)
  - From: quickstart.md Scenario 6 (integration example)

### Manual Validation

- [ ] T089 Manual testing: Run quickstart Scenario 4 (interactive Python)
  - File: quickstart.md Scenario 4
  - Steps:
    - Create test zone at $155 (RESISTANCE)
    - Test breakout detection with $156.60 (+1.03%), volume 1.4x
    - Verify: BreakoutSignal returned, zone flipped to SUPPORT, strength +2
  - Validate: All calculations match expected values
  - From: quickstart.md Scenario 4

- [ ] T090 Manual testing: Verify JSONL log format
  - File: quickstart.md Scenario 5
  - Steps:
    - Run breakout detection test
    - Inspect logs/zones/breakouts-YYYY-MM-DD.jsonl
    - Verify: JSON structure matches contracts/api.yaml example
  - Tools: cat, jq for JSON validation
  - From: quickstart.md Scenario 5

- [ ] T091 Calculate HEART metrics baseline
  - Script: quickstart.md Scenario 5 (Python script for breakout success rate)
  - Metrics:
    - Breakout success rate (target >60%)
    - Whipsaw rate (guardrail <40%)
  - Output: Log metrics to NOTES.md for baseline tracking
  - From: spec.md HEART metrics measurement plan

---

## [TEST GUARDRAILS]

**Speed Requirements**:
- Unit tests: <2s each
- Integration tests: <10s each
- Full suite: <5 min total (MVP has ~20-25 tests)

**Coverage Requirements**:
- New code: 100% coverage (no untested lines in new features)
- Unit tests: ≥90% line coverage (Constitution §Testing_Requirements)
- Integration tests: ≥60% line coverage
- Modified code: Coverage cannot decrease

**Measurement**:
- Python: `pytest --cov=src.trading_bot.support_resistance.breakout_detector --cov-report=term-missing`
- Target: All new files (breakout_detector.py, breakout_models.py, breakout_config.py) at 90%+

**Quality Gates**:
- All tests must pass before merge
- Coverage thresholds enforced in manual validation (T087)
- No skipped tests without documented reason in error-log.md

**Clarity Requirements**:
- One behavior per test
- Descriptive names: `test_detect_breakout_valid_resistance_breakout()`
- Given-When-Then structure in test body

**Anti-Patterns**:
- ❌ NO float arithmetic (use Decimal for all price/volume calculations)
- ❌ NO mutation of Zone objects (create new instances)
- ❌ NO blocking API calls in tests (mock MarketDataService)
- ✅ USE Decimal for precision
- ✅ USE immutable dataclasses
- ✅ USE pytest fixtures for test data

**Examples**:
```python
# ❌ Bad: Float arithmetic (precision loss)
price_change = (156.60 - 155.00) / 155.00 * 100

# ✅ Good: Decimal arithmetic (exact)
price_change = (Decimal("156.60") - Decimal("155.00")) / Decimal("155.00") * 100

# ❌ Bad: Mutating Zone (breaks immutability)
zone.zone_type = ZoneType.SUPPORT

# ✅ Good: Create new Zone (preserve immutability)
flipped_zone = Zone(..., zone_type=ZoneType.SUPPORT)
```

**Reference**: Constitution §Testing_Requirements, plan.md [DEPLOYMENT ACCEPTANCE]
