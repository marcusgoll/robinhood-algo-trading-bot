# Tasks: ATR-based Dynamic Stop-Loss Adjustment

## [CODEBASE REUSE ANALYSIS]

Scanned: src/trading_bot/risk_management/**/*.py, src/trading_bot/market_data/**/*.py

### [EXISTING - REUSE]
- ✅ Calculator.calculate_position_plan (src/trading_bot/risk_management/calculator.py:194-264)
- ✅ Calculator.validate_stop_distance (src/trading_bot/risk_management/calculator.py:11-49)
- ✅ RiskManagementConfig (src/trading_bot/risk_management/config.py)
- ✅ PositionPlan dataclass (src/trading_bot/risk_management/models.py)
- ✅ StopAdjuster.calculate_adjustment (src/trading_bot/risk_management/stop_adjuster.py:74-108)
- ✅ MarketDataService (src/trading_bot/market_data/market_data_service.py)
- ✅ PositionPlanningError hierarchy (src/trading_bot/risk_management/exceptions.py)
- ✅ JSONL logging pattern (logs/risk-management.jsonl)

### [NEW - CREATE]
- 🆕 ATRCalculator (src/trading_bot/risk_management/atr_calculator.py)
- 🆕 ATRStopData dataclass (src/trading_bot/risk_management/models.py)
- 🆕 PriceBar dataclass (src/trading_bot/market_data/data_models.py)
- 🆕 ATRCalculationError, ATRValidationError, StaleDataError (src/trading_bot/risk_management/exceptions.py)
- 🆕 MarketDataService.get_price_bars() method (extends existing service)

---

## Phase 3.1: Setup & Foundation (T001-T004)

**Context**: Extend existing risk_management infrastructure with ATR support

T001 [P] Add PriceBar dataclass to `src/trading_bot/market_data/data_models.py`
- **Fields**: symbol (str), timestamp (datetime), open (Decimal), high (Decimal), low (Decimal), close (Decimal), volume (int)
- **Frozen**: True (immutable value object)
- **Validation**: high >= low (property validation in __post_init__)
- **REUSE**: Quote dataclass pattern (src/trading_bot/market_data/data_models.py:1-15)
- **Pattern**: src/trading_bot/risk_management/models.py (frozen dataclasses)
- **From**: plan.md [SCHEMA] PriceBar model

T002 [P] Add ATRStopData dataclass to `src/trading_bot/risk_management/models.py`
- **Fields**: stop_price (Decimal), atr_value (Decimal), atr_multiplier (float), atr_period (int), source (str = "atr"), calculation_timestamp (datetime with default_factory)
- **Frozen**: True (immutable value object)
- **REUSE**: PositionPlan dataclass pattern (src/trading_bot/risk_management/models.py:11-29)
- **Pattern**: src/trading_bot/risk_management/models.py (frozen dataclasses with field defaults)
- **From**: plan.md [SCHEMA] ATRStopData model

T003 [P] Add ATR exception classes to `src/trading_bot/risk_management/exceptions.py`
- **Classes**: ATRCalculationError (insufficient data, invalid values), ATRValidationError (stop distance out of bounds), StaleDataError (price data too old)
- **Inheritance**: All subclass PositionPlanningError
- **Fields**: symbol, details (dict with diagnostic fields)
- **REUSE**: PositionPlanningError base class (src/trading_bot/risk_management/exceptions.py:1-10)
- **Pattern**: src/trading_bot/risk_management/exceptions.py (custom exception hierarchy)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE] exception hierarchy

T004 [P] Extend RiskManagementConfig with ATR fields in `src/trading_bot/risk_management/config.py`
- **Fields**: atr_enabled (bool = False), atr_period (int = 14), atr_multiplier (float = 2.0), atr_recalc_threshold (float = 0.20)
- **Validation**: atr_period > 0, atr_multiplier > 0, atr_recalc_threshold between 0-1 (in __post_init__)
- **REUSE**: RiskManagementConfig dataclass (src/trading_bot/risk_management/config.py:7-35)
- **Pattern**: Existing field validation pattern in RiskManagementConfig
- **From**: plan.md [SCHEMA] RiskManagementConfig extension

---

## Phase 3.2: RED - Write Failing Tests (T005-T014)

**Context**: TDD RED phase - define expected ATR behavior through tests

T005 [RED] Write test: ATR calculation with valid 14-period data
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_calculate_atr_from_bars_valid_data()
- **Given**: 20 price bars with known high/low/close values
- **When**: calculate_atr_from_bars(price_bars, period=14)
- **Then**: Returns Decimal ATR value accurate to ±$0.01 vs reference (NFR-008)
- **Pattern**: src/trading_bot/risk_management/tests/test_calculator.py (Decimal precision tests)
- **From**: spec.md FR-001, NFR-008

T006 [RED] Write test: ATR calculation fails with insufficient data
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_calculate_atr_insufficient_data()
- **Given**: 8 price bars (less than 14-period requirement)
- **When**: calculate_atr_from_bars(price_bars, period=14)
- **Then**: Raises ATRCalculationError with "Insufficient data: 8 bars available, 14 required"
- **Pattern**: Exception testing pattern from existing tests
- **From**: spec.md Acceptance Scenario 3, FR-002

T007 [RED] Write test: ATR calculation validates price bar integrity
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_calculate_atr_invalid_price_bars()
- **Given**: Price bars with high < low OR negative prices
- **When**: calculate_atr_from_bars(price_bars, period=14)
- **Then**: Raises ATRCalculationError with "Invalid price data: high < low"
- **Pattern**: Input validation tests from calculator.py tests
- **From**: spec.md FR-002

T008 [RED] Write test: ATR stop calculation for long position
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_calculate_atr_stop_long()
- **Given**: entry_price=$250.30, atr_value=$5.20, atr_multiplier=2.0, direction="long"
- **When**: calculate_atr_stop(entry_price, atr_value, atr_multiplier, direction)
- **Then**: Returns ATRStopData(stop_price=$239.90, atr_value=$5.20, atr_multiplier=2.0)
- **Pattern**: Position plan calculation tests
- **From**: spec.md Acceptance Scenario 1, FR-003

T009 [RED] Write test: ATR stop validation rejects stop distance <0.7%
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_calculate_atr_stop_too_tight()
- **Given**: entry_price=$180.50, atr_value=$0.50, atr_multiplier=1.0 (produces 0.28% stop)
- **When**: calculate_atr_stop(entry_price, atr_value, atr_multiplier, direction="long")
- **Then**: Raises ATRValidationError with "Stop distance 0.28% is too tight (minimum: 0.7%)"
- **Pattern**: validate_stop_distance() integration tests
- **From**: spec.md Acceptance Scenario 4, FR-006

T010 [RED] Write test: ATR stop validation rejects stop distance >10%
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_calculate_atr_stop_too_wide()
- **Given**: entry_price=$50.00, atr_value=$6.00, atr_multiplier=2.5 (produces 30% stop)
- **When**: calculate_atr_stop(entry_price, atr_value, atr_multiplier, direction="long")
- **Then**: Raises ATRValidationError with "Stop distance 30% exceeds maximum 10%"
- **Pattern**: validate_stop_distance() boundary tests
- **From**: spec.md Edge Cases, FR-006

T011 [RED] Write test: Position plan integration with ATR stop
- **File**: src/trading_bot/risk_management/tests/test_calculator_atr.py
- **Test**: test_calculate_position_plan_with_atr_data()
- **Given**: atr_data=ATRStopData(stop_price=$239.90, atr_value=$5.20, ...), atr_enabled=true in config
- **When**: calculate_position_plan(symbol="TSLA", entry_price=$250.30, stop_price=$239.90, atr_data=atr_data, config=config)
- **Then**: PositionPlan.pullback_source="atr", stop_price=$239.90, quantity=96, logs ATR details to risk-management.jsonl
- **Pattern**: src/trading_bot/risk_management/tests/test_calculator.py integration tests
- **From**: spec.md Acceptance Scenario 2, FR-004

T012 [RED] Write test: Stale data detection for price bars
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_validate_price_bars_stale_data()
- **Given**: Price bars with timestamps >15 minutes old
- **When**: validate_price_bars(price_bars, max_age_minutes=15)
- **Then**: Raises StaleDataError with "Latest bar is 23 minutes old (threshold: 15 minutes)"
- **Pattern**: Timestamp validation pattern
- **From**: spec.md Edge Cases, FR-011

T013 [RED] Write test: Stop adjustment with ATR recalculation
- **File**: src/trading_bot/risk_management/tests/test_stop_adjuster_atr.py
- **Test**: test_calculate_adjustment_with_atr_change()
- **Given**: Position with initial ATR $6.50, current ATR $8.50 (30% increase, exceeds 20% threshold)
- **When**: calculate_adjustment(current_price=$420.00, position_plan, config, current_atr=$8.50)
- **Then**: Returns (new_stop_price=$403.00, "adjusted for ATR increase from 6.50 to 8.50")
- **Pattern**: src/trading_bot/risk_management/tests/test_stop_adjuster.py
- **From**: spec.md Acceptance Scenario 5, FR-007

T014 [RED] Write test: ATR performance benchmark (<50ms)
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_atr_calculation_performance()
- **Given**: 50 price bars (typical dataset)
- **When**: calculate_atr_from_bars(price_bars, period=14) executed 100 times
- **Then**: Average execution time <=50ms (NFR-001)
- **Pattern**: Performance test pattern with time measurement
- **From**: spec.md NFR-001

---

## Phase 3.3: GREEN - Minimal Implementation (T015-T024)

**Context**: TDD GREEN phase - implement minimal code to pass tests

T015 [GREEN→T005,T006,T007] Implement ATRCalculator.calculate_atr_from_bars()
- **File**: src/trading_bot/risk_management/atr_calculator.py
- **Create**: ATRCalculator class with calculate_atr_from_bars(price_bars, period=14)
- **Logic**: Calculate true range for each bar (max of high-low, |high-prev_close|, |low-prev_close|), average over period using Wilder's smoothing
- **Validation**: Check bars >= period, high >= low, sequential timestamps
- **Precision**: Use Decimal for all calculations (2 decimal places)
- **REUSE**: Decimal pattern from calculator.py
- **Pattern**: src/trading_bot/risk_management/pullback_analyzer.py (service class structure)
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 1, FR-001

T016 [GREEN→T008,T009,T010] Implement ATRCalculator.calculate_atr_stop()
- **File**: src/trading_bot/risk_management/atr_calculator.py
- **Add**: calculate_atr_stop(entry_price, atr_value, atr_multiplier, direction="long")
- **Logic**: stop_price = entry_price - (atr_value * atr_multiplier) for long, validate distance with validate_stop_distance()
- **Returns**: ATRStopData with stop_price, atr_value, atr_multiplier, atr_period, source="atr", calculation_timestamp
- **REUSE**: validate_stop_distance() from calculator.py:11-49
- **Pattern**: Stop calculation pattern from calculator.py
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 1, FR-003

T017 [GREEN→T012] Implement ATRCalculator.validate_price_bars()
- **File**: src/trading_bot/risk_management/atr_calculator.py
- **Add**: validate_price_bars(price_bars, max_age_minutes=15)
- **Logic**: Check timestamps sequential, high >= low, latest bar within max_age_minutes threshold
- **Raises**: StaleDataError if data too old, ATRCalculationError if invalid data
- **Pattern**: Input validation pattern from config.py
- **From**: spec.md FR-011

T018 [GREEN→T011] Extend calculate_position_plan() with atr_data parameter
- **File**: src/trading_bot/risk_management/calculator.py
- **Modify**: calculate_position_plan() signature to accept atr_data: Optional[ATRStopData] = None
- **Logic**: If atr_data provided and config.atr_enabled, use atr_data.stop_price, set pullback_source="atr", log ATR details
- **REUSE**: Existing calculate_position_plan() logic (src/trading_bot/risk_management/calculator.py:194-264)
- **Pattern**: Optional parameter pattern from existing calculate_position_plan()
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 2, FR-004

T019 [GREEN→T013] Extend StopAdjuster.calculate_adjustment() with current_atr parameter
- **File**: src/trading_bot/risk_management/stop_adjuster.py
- **Modify**: calculate_adjustment() signature to accept current_atr: Optional[Decimal] = None
- **Logic**: If current_atr provided and changed >20% from initial, recalculate stop using new ATR, compare with breakeven/trailing, select widest
- **REUSE**: Existing calculate_adjustment() logic (src/trading_bot/risk_management/stop_adjuster.py:74-108)
- **Pattern**: Optional parameter with conditional logic from stop_adjuster.py
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 3, FR-007

T020 [P] [GREEN→T014] Optimize ATR calculation for performance
- **File**: src/trading_bot/risk_management/atr_calculator.py
- **Add**: Decimal context optimization (limit precision to 2 places), cache intermediate true range calculations
- **Verify**: Performance test passes (<50ms for 50 bars)
- **Pattern**: Decimal optimization from calculator.py
- **From**: spec.md NFR-001

T021 [P] Implement get_price_bars() in MarketDataService
- **File**: src/trading_bot/market_data/market_data_service.py
- **Add**: get_price_bars(symbol: str, count: int = 20, interval: str = "day") → List[PriceBar]
- **Logic**: Call robin_stocks.get_stock_historicals(symbol, interval, span), convert to PriceBar list
- **REUSE**: Existing MarketDataService.get_quote() pattern (src/trading_bot/market_data/market_data_service.py)
- **Pattern**: src/trading_bot/market_data/market_data_service.py (API wrapper methods)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE] MarketDataService

T022 [P] Add ATR logging to risk-management.jsonl
- **File**: src/trading_bot/risk_management/calculator.py
- **Add**: Log entry when ATR stop used: {"event": "position_plan_atr", "symbol": "TSLA", "atr_value": "5.20", "atr_multiplier": 2.0, "stop_distance_pct": 4.2}
- **REUSE**: Existing JSONL logging pattern (logs/risk-management.jsonl)
- **Pattern**: Structured logging from calculator.py
- **From**: spec.md FR-009

T023 [P] Add ATR configuration validation
- **File**: src/trading_bot/risk_management/config.py
- **Add**: __post_init__ validation for atr_period > 0, atr_multiplier > 0, atr_recalc_threshold 0-1
- **Raises**: ValueError with actionable message if invalid
- **Pattern**: Existing validation in RiskManagementConfig.__post_init__
- **From**: plan.md [SECURITY] Input Validation

T024 [P] Update config.example.json with ATR fields
- **File**: config.example.json (if exists, or document in README)
- **Add**: risk_management.atr_enabled, atr_period, atr_multiplier, atr_recalc_threshold with defaults
- **Pattern**: Existing config structure
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] Configuration

---

## Phase 3.4: REFACTOR - Clean Up (T025-T027)

**Context**: TDD REFACTOR phase - improve code quality while keeping tests green

T025 [REFACTOR] Extract ATR formula constants to class attributes
- **File**: src/trading_bot/risk_management/atr_calculator.py
- **Change**: Move magic numbers (14 default period, 2.0 default multiplier) to class-level constants
- **Verify**: All tests still pass
- **Pattern**: Constants pattern from config.py
- **From**: Clean code principles

T026 [REFACTOR] Extract true range calculation to private method
- **File**: src/trading_bot/risk_management/atr_calculator.py
- **Change**: Create _calculate_true_range(bar, prev_bar) private method
- **Benefit**: Improves testability and readability of calculate_atr_from_bars()
- **Verify**: All tests still pass
- **Pattern**: Private method pattern from pullback_analyzer.py
- **From**: Single Responsibility Principle

T027 [REFACTOR] Add comprehensive docstrings with ATR formula
- **File**: src/trading_bot/risk_management/atr_calculator.py
- **Add**: Class and method docstrings documenting ATR formula (three true range components, averaging method, multiplier application)
- **Include**: Examples and references to Wilder's ATR
- **Pattern**: Docstring pattern from calculator.py
- **From**: spec.md FR-014

---

## Phase 3.5: Integration & End-to-End Testing (T028-T031)

**Context**: Verify ATR integration with full position planning workflow

T028 [RED] Write test: End-to-end ATR position planning
- **File**: src/trading_bot/risk_management/tests/test_integration_atr.py
- **Test**: test_full_atr_position_planning_workflow()
- **Given**: MarketDataService returns 20 price bars for TSLA
- **When**: Full workflow: get_price_bars() → calculate_atr_from_bars() → calculate_atr_stop() → calculate_position_plan()
- **Then**: PositionPlan with ATR stop, correct quantity, logged to risk-management.jsonl
- **Pattern**: Integration test pattern
- **From**: plan.md [INTEGRATION SCENARIOS]

T029 [GREEN→T028] Implement full ATR workflow integration
- **File**: src/trading_bot/risk_management/manager.py (or create orchestrator)
- **Add**: Helper function plan_position_with_atr(symbol, entry_price, config, market_data_service)
- **Logic**: Orchestrates get_price_bars → ATRCalculator → calculate_position_plan
- **REUSE**: Existing manager.py pattern (if exists)
- **Pattern**: Service orchestration pattern
- **From**: plan.md [INTEGRATION SCENARIOS]

T030 [RED] Write test: Fallback behavior on ATR failure
- **File**: src/trading_bot/risk_management/tests/test_integration_atr.py
- **Test**: test_atr_fallback_to_percentage_stop()
- **Given**: ATR calculation fails (insufficient data)
- **When**: Position planning attempted with ATR enabled
- **Then**: Falls back to percentage stop, logs fallback reason, continues without error
- **Pattern**: Error handling integration tests
- **From**: spec.md FR-005, FR-010

T031 [GREEN→T030] Implement ATR fallback logic
- **File**: src/trading_bot/risk_management/calculator.py (or orchestrator)
- **Add**: Try/except around ATR calculation, catch ATRCalculationError, log fallback reason, use default stop
- **REUSE**: Existing error handling pattern from calculator.py
- **Pattern**: Graceful degradation pattern
- **From**: plan.md [ARCHITECTURE DECISIONS] Fail-Safe Fallback Architecture

---

## Phase 3.6: Error Handling & Resilience (T032-T034)

**Context**: Ensure robust error handling and fail-safe behavior

T032 [RED] Write test: Zero or negative ATR handling
- **File**: src/trading_bot/risk_management/tests/test_atr_calculator.py
- **Test**: test_calculate_atr_zero_or_negative()
- **Given**: Price bars with zero volatility (all high=low=close) OR invalid negative ATR
- **When**: calculate_atr_from_bars(price_bars)
- **Then**: Raises ATRCalculationError with "Invalid ATR value: 0.00" (zero volatility) or "Invalid ATR value: -1.50" (negative)
- **Pattern**: Edge case testing pattern
- **From**: spec.md Edge Cases

T033 [GREEN→T032] Implement zero/negative ATR validation
- **File**: src/trading_bot/risk_management/atr_calculator.py
- **Add**: Validation after ATR calculation: if atr_value <= 0, raise ATRCalculationError
- **Verify**: Test passes
- **Pattern**: Post-calculation validation pattern
- **From**: spec.md Edge Cases

T034 [P] Add error tracking to error-log.md
- **File**: specs/atr-stop-adjustment/error-log.md
- **Add**: Document ATR-specific error scenarios (insufficient data, stale data, zero ATR, out-of-bounds stop)
- **Include**: Error codes, symptoms, resolution steps
- **Pattern**: Error documentation pattern from error-log.md
- **From**: spec.md FR-012

---

## Phase 3.7: Deployment Preparation (T035-T037)

**Context**: Final preparation for staging deployment

T035 [P] Document rollback procedure in NOTES.md
- **File**: specs/atr-stop-adjustment/NOTES.md
- **Add**: Deployment Metadata section with rollback commands
- **Include**: Standard 3-command rollback OR config flag atr_enabled=false
- **Pattern**: NOTES.md template
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] Rollback Plan

T036 [P] Add ATR smoke tests for CI pipeline
- **File**: src/trading_bot/risk_management/tests/test_atr_smoke.py
- **Tests**: (1) ATR calculation with sample data, (2) Position plan with ATR stop, (3) Fallback on failure, (4) Config validation
- **Requirement**: <90s total execution
- **Pattern**: Smoke test pattern (fast, critical path only)
- **From**: plan.md [CI/CD IMPACT] Smoke Tests

T037 [P] Update README with ATR configuration guide
- **File**: README.md (or docs/risk-management.md)
- **Add**: ATR configuration section with examples (standard 2.0 multiplier, volatile stocks 2.5-3.0, low-volatility 1.5)
- **Include**: Tuning guidance and performance characteristics
- **Pattern**: Configuration documentation pattern
- **From**: spec.md Deployment Considerations

---

## Task Summary

**Total Tasks**: 37
- **Setup**: 4 (T001-T004)
- **RED (Tests)**: 10 (T005-T014)
- **GREEN (Implementation)**: 10 (T015-T024)
- **REFACTOR**: 3 (T025-T027)
- **Integration**: 4 (T028-T031)
- **Error Handling**: 3 (T032-T034)
- **Deployment**: 3 (T035-T037)

**TDD Coverage**: 27/37 tasks (73%) follow RED→GREEN→REFACTOR cycle
**Parallel Tasks**: 14 tasks marked [P] can run in parallel (no dependencies)

**Reuse Leverage**: 8 existing components, 5 new components
**Files Modified**: 6 existing files
**Files Created**: 5 new files + 6 test files
