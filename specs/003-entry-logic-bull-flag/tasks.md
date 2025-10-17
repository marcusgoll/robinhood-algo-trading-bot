# Tasks: Bull Flag Pattern Detection

## [CODEBASE REUSE ANALYSIS]
Scanned: D:\Coding\Stocks\src\trading_bot\indicators\**\*.py, D:\Coding\Stocks\tests\indicators\**\*.py

[EXISTING - REUSE]
- ✅ TechnicalIndicatorsService (src/trading_bot/indicators/service.py) - VWAP/MACD/EMA validation
- ✅ InsufficientDataError (src/trading_bot/indicators/exceptions.py) - Error handling pattern
- ✅ IndicatorConfig (src/trading_bot/indicators/config.py) - Configuration pattern with __post_init__ validation
- ✅ VWAPResult/MACDResult (src/trading_bot/indicators/calculators.py) - Dataclass result pattern with Decimal

[NEW - CREATE]
- 🆕 patterns/ module - No existing pattern detection infrastructure
- 🆕 BullFlagDetector - Core detection logic (multi-phase pattern recognition)
- 🆕 BullFlagConfig - Pattern-specific configuration
- 🆕 BullFlagResult/FlagpoleData/ConsolidationData - Result models
- 🆕 PatternNotFoundError/InvalidConfigurationError - Pattern-specific exceptions
- 🆕 Pattern test infrastructure - New test module for patterns/

## [DEPENDENCY GRAPH]
Phase completion order:
1. Phase 1: Setup (create module structure, install dependencies if needed)
2. Phase 2: Foundation (exceptions, models, config - blocks all implementation)
3. Phase 3: Core Detection (flagpole, consolidation, breakout - blocks integration)
4. Phase 4: Risk & Scoring (risk parameters, quality scoring - blocks validation)
5. Phase 5: Integration (indicator validation - blocks E2E testing)
6. Phase 6: Testing & Validation (comprehensive tests, performance benchmarks)
7. Phase 7: Documentation & Polish (docstrings, error handling, final review)

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 2: T005, T006, T007 (different files, no dependencies)
- Phase 3: T012, T013, T014 (tests), T015, T016, T017 (implementation - sequential within each group)
- Phase 4: T020, T021 (tests), T022, T023 (implementation)
- Phase 6: T032, T033, T034, T035 (different test files)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Complete pattern detection with all validation phases
**Testing approach**: TDD required - write tests before implementation for core logic
**Quality gates**: >90% coverage, all existing indicator tests pass, performance <5s for 100 stocks
**Integration pattern**: Composition (instantiate TechnicalIndicatorsService, no modifications)

---

## Phase 1: Setup

- [ ] T001 Create patterns module directory structure
  - Directories: src/trading_bot/patterns/, tests/patterns/
  - Files: __init__.py in both directories
  - Pattern: src/trading_bot/indicators/ directory structure
  - From: plan.md [STRUCTURE]

- [x] T002 Verify Python dependencies are installed
  - Required: decimal, dataclasses, typing, datetime, pytest (all standard library except pytest)
  - Check: pytest installed in environment
  - No new package installations needed
  - From: plan.md [ARCHITECTURE DECISIONS]
  - Status: ✅ Complete - Python 3.11.3, pytest 8.3.2, all imports verified

---

## Phase 2: Foundation (blocking prerequisites)

**Goal**: Data structures and configuration that block all pattern detection logic

- [ ] T005 [P] Create pattern-specific exceptions in src/trading_bot/patterns/exceptions.py
  - Classes: PatternNotFoundError(Exception), InvalidConfigurationError(Exception)
  - Pattern: src/trading_bot/indicators/exceptions.py (InsufficientDataError)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T006 [P] Create result dataclasses in src/trading_bot/patterns/models.py
  - Classes: BullFlagResult, FlagpoleData, ConsolidationData (all @dataclass)
  - Fields: Use Decimal for all financial values, datetime for timestamps
  - Pattern: src/trading_bot/indicators/calculators.py (VWAPResult, MACDResult)
  - From: data-model.md entity definitions

- [ ] T007 [P] Create configuration dataclass in src/trading_bot/patterns/config.py
  - Class: BullFlagConfig with 13 configuration fields
  - Validation: __post_init__ method to validate parameter constraints
  - Defaults: Based on technical analysis standards (5% min gain, 20-50% retracement, etc.)
  - Pattern: src/trading_bot/indicators/config.py (IndicatorConfig __post_init__ pattern)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T008 Write unit tests for configuration validation in tests/patterns/test_config.py
  - Tests: Valid config acceptance, invalid parameter rejection, boundary conditions
  - Coverage: Test all 13 config fields with valid/invalid values
  - Pattern: tests/indicators/test_config.py
  - From: spec.md FR-007

- [ ] T009 Write unit tests for data models in tests/patterns/test_models.py
  - Tests: Dataclass instantiation, field validation, Decimal precision
  - Coverage: All 3 model classes (BullFlagResult, FlagpoleData, ConsolidationData)
  - Pattern: tests/indicators/test_calculators.py (result model tests)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T010 Create test fixtures in tests/patterns/conftest.py
  - Fixtures: sample_bars (30+ OHLCV bars), valid_bull_flag_bars, invalid_pattern_bars
  - Fixtures: default_config, aggressive_config, conservative_config
  - Pattern: tests/indicators/conftest.py (if exists) or create new
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 3: Core Detection Logic

**Goal**: Implement multi-phase pattern detection (flagpole → consolidation → breakout)

### Tests (TDD - write before implementation)

- [ ] T012 [P] Write unit tests for flagpole detection in tests/patterns/test_bull_flag.py
  - Tests: Valid flagpole (5%+ gain, 3-15 bars, high volume), invalid flagpole (insufficient gain, too short/long, low volume)
  - Given-When-Then structure
  - Pattern: tests/indicators/test_calculators.py (unit test structure)
  - From: spec.md FR-001

- [ ] T013 [P] Write unit tests for consolidation detection in tests/patterns/test_bull_flag.py
  - Tests: Valid consolidation (3-10 bars, 20-50% retracement, decreasing volume), invalid consolidation (too short, excessive retracement, high volume)
  - Given-When-Then structure
  - Pattern: tests/indicators/test_calculators.py
  - From: spec.md FR-002

- [ ] T014 [P] Write unit tests for breakout confirmation in tests/patterns/test_bull_flag.py
  - Tests: Valid breakout (close above resistance, 30%+ volume increase, 1%+ move), invalid breakout (failed breakout, low volume, insufficient move)
  - Given-When-Then structure
  - Pattern: tests/indicators/test_calculators.py
  - From: spec.md FR-003

### Implementation

- [ ] T015 Create BullFlagDetector class stub in src/trading_bot/patterns/bull_flag.py
  - Class: BullFlagDetector with __init__(config: BullFlagConfig)
  - Method: detect(bars: List[dict], symbol: str) -> BullFlagResult
  - Dependencies: Import TechnicalIndicatorsService, models, config, exceptions
  - Pattern: src/trading_bot/indicators/service.py (class structure)
  - From: plan.md [MODULE ORGANIZATION]

- [ ] T016 Implement _detect_flagpole() method in src/trading_bot/patterns/bull_flag.py
  - Signature: _detect_flagpole(bars: List[dict]) -> Optional[FlagpoleData]
  - Logic: Scan for 5%+ gain over 3-15 bars with above-average volume
  - Return: FlagpoleData with start_idx, end_idx, gain_pct, avg_volume, high_price
  - From: spec.md FR-001 acceptance criteria

- [ ] T017 Implement _detect_consolidation() method in src/trading_bot/patterns/bull_flag.py
  - Signature: _detect_consolidation(bars: List[dict], flagpole: FlagpoleData) -> Optional[ConsolidationData]
  - Logic: Find 3-10 bars after flagpole with 20-50% retracement, decreasing volume
  - Return: ConsolidationData with start_idx, end_idx, upper_boundary, lower_boundary, avg_volume
  - From: spec.md FR-002 acceptance criteria

- [ ] T018 Implement _confirm_breakout() method in src/trading_bot/patterns/bull_flag.py
  - Signature: _confirm_breakout(bars: List[dict], consolidation: ConsolidationData) -> Optional[Decimal]
  - Logic: Verify close above upper_boundary, 30%+ volume increase, 1%+ move within 2 bars
  - Return: Breakout price (Decimal) or None if no valid breakout
  - From: spec.md FR-003 acceptance criteria

- [ ] T019 Wire detect() method to orchestrate detection phases
  - Flow: Validate input → detect_flagpole() → detect_consolidation() → confirm_breakout() → validate_with_indicators() → calculate_risk_parameters() → calculate_quality_score()
  - Error handling: Raise InsufficientDataError if len(bars) < 30, raise PatternNotFoundError if any phase fails
  - Return: Complete BullFlagResult with all metadata
  - From: plan.md [MODULE ORGANIZATION]

---

## Phase 4: Risk Parameters & Quality Scoring

**Goal**: Calculate stop-loss, target, risk/reward ratio, and quality score

### Tests (TDD - write before implementation)

- [ ] T020 [P] Write unit tests for risk parameter calculation in tests/patterns/test_bull_flag.py
  - Tests: Stop-loss at lower boundary - 0.5%, target = breakout + flagpole height, R/R minimum 2:1
  - Tests: Reject signals with R/R < 2:1
  - Given-When-Then structure
  - From: spec.md FR-005

- [ ] T021 [P] Write unit tests for quality scoring in tests/patterns/test_bull_flag.py
  - Tests: Score 0-100 based on flagpole strength, consolidation tightness, volume profile
  - Tests: Low quality (<60), medium (60-79), high (80+)
  - Given-When-Then structure
  - From: spec.md FR-006

### Implementation

- [ ] T022 Implement _calculate_risk_parameters() in src/trading_bot/patterns/bull_flag.py
  - Signature: _calculate_risk_parameters(flagpole: FlagpoleData, consolidation: ConsolidationData, breakout_price: Decimal) -> dict
  - Calculations: stop_loss = consolidation.lower_boundary * 0.995, target = breakout_price + (flagpole.high_price - flagpole.start_price), risk_reward_ratio = (target - breakout_price) / (breakout_price - stop_loss)
  - Validation: Reject if risk_reward_ratio < 2.0
  - Return: dict with entry_price, stop_loss, target_price, risk_reward_ratio
  - From: spec.md FR-005 acceptance criteria

- [ ] T023 Implement _calculate_quality_score() in src/trading_bot/patterns/bull_flag.py
  - Signature: _calculate_quality_score(flagpole: FlagpoleData, consolidation: ConsolidationData, indicators: dict) -> int
  - Factors: Flagpole gain % (0-30 pts), consolidation tightness (0-25 pts), volume decrease (0-20 pts), indicator alignment (0-25 pts)
  - Score: Sum factors, clamp to 0-100
  - Return: int quality score
  - From: spec.md FR-006 acceptance criteria

---

## Phase 5: Indicator Integration

**Goal**: Integrate TechnicalIndicatorsService for VWAP/MACD/EMA validation

### Tests (TDD - write integration tests)

- [ ] T025 Write integration tests with TechnicalIndicatorsService in tests/patterns/test_bull_flag_integration.py
  - Tests: Valid entry (price > VWAP, MACD > 0), invalid entry (price < VWAP or MACD < 0)
  - Tests: Verify no breaking changes to indicators module (import and use existing tests)
  - Real data: Use actual TechnicalIndicatorsService, not mocks
  - Pattern: tests/indicators/test_service.py (integration test structure)
  - From: spec.md FR-004, NFR-004

### Implementation

- [ ] T026 Implement _validate_with_indicators() in src/trading_bot/patterns/bull_flag.py
  - Signature: _validate_with_indicators(bars: List[dict]) -> dict
  - Logic: Instantiate TechnicalIndicatorsService, call get_vwap(), get_macd(), get_emas()
  - Validation: Check price > VWAP, MACD > 0, price within 2% of EMA(9)
  - Return: dict with vwap, macd, ema_9 values, and validation_passed bool
  - REUSE: TechnicalIndicatorsService (src/trading_bot/indicators/service.py)
  - From: spec.md FR-004 acceptance criteria

- [ ] T027 Update patterns/__init__.py to export public API
  - Exports: BullFlagDetector, BullFlagConfig, BullFlagResult, FlagpoleData, ConsolidationData
  - Exports: PatternNotFoundError, InvalidConfigurationError
  - Pattern: src/trading_bot/indicators/__init__.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 6: Testing & Validation

**Goal**: Comprehensive tests, performance validation, regression checks

- [ ] T032 [P] Write end-to-end pattern detection tests in tests/patterns/test_bull_flag.py
  - Tests: Complete detection flow from bars → BullFlagResult
  - Tests: Multiple scenarios (perfect pattern, marginal pattern, no pattern, edge cases)
  - Coverage: All acceptance criteria from spec.md
  - Pattern: tests/indicators/test_service.py (E2E test structure)
  - From: spec.md Success Criteria

- [ ] T033 [P] Write error handling tests in tests/patterns/test_bull_flag.py
  - Tests: InsufficientDataError (< 30 bars), PatternNotFoundError (no valid pattern)
  - Tests: InvalidConfigurationError (invalid config), ValueError (invalid bar format)
  - Pattern: tests/indicators/test_service.py (error handling tests)
  - From: plan.md [SECURITY] input validation

- [ ] T034 [P] Create performance benchmark script in tests/patterns/test_performance.py
  - Benchmark: Process 100 stocks with 30-50 bars each, measure total time
  - Target: < 5 seconds total (50ms per stock average)
  - Output: Print timing results, assert time < 5s
  - From: spec.md NFR-001

- [ ] T035 [P] Validate test coverage with pytest --cov
  - Command: pytest --cov=src.trading_bot.patterns --cov-report=term-missing tests/patterns/
  - Target: > 90% line coverage for patterns module
  - Action: Add tests for any uncovered lines
  - From: spec.md NFR-003

- [ ] T036 Run regression tests on indicators module
  - Command: pytest tests/indicators/ -v
  - Validation: All existing tests pass (no breaking changes)
  - Document: Confirm zero breaking changes in NOTES.md
  - From: spec.md NFR-004

---

## Phase 7: Documentation & Polish

**Goal**: Production-ready code with comprehensive documentation

- [ ] T040 Add comprehensive docstrings to BullFlagDetector class
  - Docstrings: Class-level overview, method signatures with Args/Returns/Raises
  - Format: Google-style docstrings (match existing indicators module)
  - Coverage: All public methods (detect) and key private methods
  - Pattern: src/trading_bot/indicators/service.py (docstring style)
  - From: plan.md Phase 6

- [ ] T041 [P] Add type hints validation with mypy
  - Command: mypy src/trading_bot/patterns/ --strict
  - Fix: Any type errors or missing annotations
  - Target: Zero mypy errors with --strict flag
  - From: plan.md [CI/CD IMPACT] quality gates

- [ ] T042 [P] Add linting validation with flake8
  - Command: flake8 src/trading_bot/patterns/ --max-line-length=100
  - Fix: Any style violations (imports, spacing, line length)
  - Target: Zero flake8 errors
  - From: plan.md [CI/CD IMPACT] quality gates

- [ ] T043 Create error-log.md for pattern detection issues
  - File: specs/003-entry-logic-bull-flag/error-log.md
  - Structure: Date, Error Type, Description, Resolution
  - Initial entry: "No errors logged yet"
  - From: plan.md [STRUCTURE]

- [ ] T044 Update NOTES.md with Phase 2 completion checkpoint
  - Add: Task count, test coverage results, performance benchmark results
  - Add: Integration validation status (indicators tests passed)
  - Add: Ready for /analyze
  - From: /tasks command [UPDATE NOTES.md]

- [ ] T045 Manual validation with quickstart.md scenarios
  - Test: Run all integration scenarios from quickstart.md
  - Verify: Configuration tuning examples work, error handling validates correctly
  - Document: Any issues found in error-log.md
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

---

## [TEST GUARDRAILS]

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each
- Full suite: <30s total (small module)
- Performance benchmark: <5s for 100 stocks

**Coverage Requirements:**
- New code: 100% coverage (no untested lines in new patterns module)
- Overall patterns module: ≥90% line coverage
- Modified code: N/A (no modifications to existing code)

**Measurement:**
- Command: pytest --cov=src.trading_bot.patterns --cov-report=term-missing tests/patterns/
- Report: Coverage report must show >90% before merge

**Quality Gates:**
- All tests pass: pytest tests/patterns/ -v
- Coverage >90%: pytest --cov check
- No breaking changes: pytest tests/indicators/ -v (all pass)
- Performance passes: <5s for 100 stocks
- Type checking: mypy src/trading_bot/patterns/ --strict (zero errors)
- Linting: flake8 src/trading_bot/patterns/ (zero errors)

**Clarity Requirements:**
- One behavior per test
- Descriptive names: test_detect_flagpole_rejects_insufficient_gain()
- Given-When-Then structure in test body
- Use pytest fixtures from conftest.py for test data

**Anti-Patterns:**
- ❌ NO mocking TechnicalIndicatorsService in integration tests (use real service)
- ❌ NO hardcoded test data in test methods (use fixtures from conftest.py)
- ✅ USE Given-When-Then comments in test body
- ✅ USE descriptive assertion messages

**Reference**: tests/indicators/test_*.py for copy-paste test patterns
