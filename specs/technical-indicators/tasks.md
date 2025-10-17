# Tasks: Technical Indicators Module

## [CODEBASE REUSE ANALYSIS]

Scanned: D:/Coding/Stocks/src/trading_bot/**/*.py

[EXISTING - REUSE]
- ✅ MarketDataService (src/trading_bot/market_data/market_data_service.py) - OHLCV data fetching
- ✅ TradingLogger (src/trading_bot/logger.py) - Audit logging
- ✅ @with_retry decorator (src/trading_bot/error_handling/retry.py) - Automatic retry with backoff
- ✅ Custom exceptions (src/trading_bot/error_handling/exceptions.py) - DataValidationError, etc.
- ✅ Dataclass patterns (src/trading_bot/momentum/schemas/) - Validation in __post_init__

[NEW - CREATE]
- 🆕 VWAPCalculator - No existing VWAP pattern
- 🆕 EMACalculator - No existing EMA pattern (only ATR in risk_management)
- 🆕 MACDCalculator - No existing MACD pattern
- 🆕 TechnicalIndicatorsService - New facade for indicator calculations

## [DEPENDENCY GRAPH]

Story completion order:
1. Phase 1: Setup (blocks all user stories)
2. Phase 2: VWAP Calculator (US1, US2, US3 - independent foundation)
3. Phase 3: EMA Calculator (US4, US5, US6 - independent foundation)
4. Phase 4: MACD Calculator (US7, US8, US9, US10 - depends on EMACalculator)
5. Phase 5: Indicator Service Facade (US11, US12 - orchestration layer)
6. Phase 6: Testing & Validation (quality gates)

## [PARALLEL EXECUTION OPPORTUNITIES]

- Phase 1: T001, T002, T003 (different files, no dependencies)
- Phase 2: T004, T005, T006, T007, T008 (VWAP module - can work in parallel with Phase 3)
- Phase 3: T009, T010, T011, T012, T013 (EMA module - can work in parallel with Phase 2)
- Phase 4: T014-T019 (MACD module tests can run in parallel with implementation after Phase 3 complete)
- Phase 5: T021, T022, T023 (service methods - after calculators complete)

## [IMPLEMENTATION STRATEGY]

**MVP Scope**: Phases 1-5 (all calculators + service facade)
**Incremental delivery**: VWAP → EMA → MACD → Service → Testing
**Testing approach**: TDD required - Write tests before implementation per Constitution §Code_Quality
**Performance validation**: Benchmark each calculator against NFR-004 targets (<500ms VWAP, <500ms EMA, <1s MACD)

---

## Phase 1: Setup

- [ ] T001 [P] Create indicators module structure
  - Files: src/trading_bot/indicators/__init__.py, config.py, exceptions.py
  - Pattern: src/trading_bot/momentum/ (similar module structure)
  - From: plan.md [STRUCTURE]

- [ ] T002 [P] Create IndicatorConfig dataclass in src/trading_bot/indicators/config.py
  - Fields: vwap_min_bars (10), ema_periods ([9,20]), ema_proximity_threshold_pct (2.0), macd_fast_period (12), macd_slow_period (26), macd_signal_period (9), refresh_interval_seconds (300)
  - Validation: __post_init__ to check periods > 0, fast < slow, refresh >= 60
  - REUSE: Dataclass pattern from momentum/config.py
  - Pattern: src/trading_bot/momentum/config.py
  - From: plan.md [CONFIGURATION]

- [ ] T003 [P] Add InsufficientDataError exception in src/trading_bot/indicators/exceptions.py
  - Fields: symbol, required_bars, available_bars
  - REUSE: Custom exception pattern from error_handling/exceptions.py
  - Pattern: src/trading_bot/error_handling/exceptions.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 2: VWAP Calculator (User Stories 1, 2, 3)

**Goal**: Enable VWAP calculation for entry validation and dynamic support levels

**Independent Test Criteria**:
- [ ] VWAP calculated from intraday data with minimum 10 bars
- [ ] Entry validation blocks longs when price < VWAP
- [ ] Entry validation allows longs when price > VWAP
- [ ] Insufficient data raises InsufficientDataError

### Tests (TDD - Write First)

- [ ] T004 [P] [US1] Write test: Calculate VWAP with valid 20-bar intraday data
  - File: tests/unit/indicators/test_vwap_calculator.py
  - Test: Given 20 intraday bars → VWAP = sum(typical_price * volume) / sum(volume)
  - Pattern: tests/integration/momentum/test_bull_flag_detector_integration.py
  - Coverage: ≥90% (new code must be 90%+)

- [ ] T005 [P] [US11] Write test: Insufficient intraday data raises InsufficientDataError
  - File: tests/unit/indicators/test_vwap_calculator.py
  - Test: Given 5 bars (< 10 minimum) → raise InsufficientDataError
  - Pattern: tests/integration/momentum/test_bull_flag_detector_integration.py

- [ ] T006 [P] [US2] Write test: Entry validation allows when price above VWAP
  - File: tests/unit/indicators/test_vwap_calculator.py
  - Test: price=$152, VWAP=$150 → validate_entry returns True
  - Pattern: tests/integration/momentum/test_bull_flag_detector_integration.py

- [ ] T007 [P] [US3] Write test: Entry validation blocks when price below VWAP
  - File: tests/unit/indicators/test_vwap_calculator.py
  - Test: price=$148, VWAP=$150 → validate_entry returns False
  - Pattern: tests/integration/momentum/test_bull_flag_detector_integration.py

### Implementation

- [ ] T008 [US1] Create VWAPCalculator class in src/trading_bot/indicators/vwap_calculator.py
  - Dataclasses: VWAPResult (symbol, vwap, price, calculated_at, bars_used)
  - Methods: calculate(ohlcv), validate_entry(price, vwap), _validate_data(ohlcv)
  - Calculation: typical_price = (high + low + close) / 3; VWAP = sum(typical_price * volume) / sum(volume)
  - Validation: Require >= 10 bars, prices > 0, volumes >= 0
  - REUSE: MarketDataService for OHLCV, Decimal for precision, TradingLogger for audit
  - Pattern: src/trading_bot/risk_management/atr_calculator.py (similar calculator pattern)
  - From: spec.md FR-001, FR-002, data-model.md VWAPResult

---

## Phase 3: EMA Calculator (User Stories 4, 5, 6)

**Goal**: Calculate EMAs, detect crossovers, identify optimal entry zones near 9-EMA

**Independent Test Criteria**:
- [ ] 9-period and 20-period EMAs calculated using exponential smoothing
- [ ] Bullish crossover detected when 9-EMA crosses above 20-EMA
- [ ] Bearish crossover detected when 9-EMA crosses below 20-EMA
- [ ] Price proximity to 9-EMA calculated (within 2% threshold)

### Tests (TDD - Write First)

- [ ] T009 [P] [US4] Write test: Calculate 9 and 20-period EMAs with 50 days historical data
  - File: tests/unit/indicators/test_ema_calculator.py
  - Test: Given 50 days close prices → EMA-9 and EMA-20 calculated, matches pandas.ewm()
  - Pattern: tests/integration/momentum/test_momentum_ranker_integration.py

- [ ] T010 [P] [US5] Write test: Detect bullish crossover when 9-EMA crosses above 20-EMA
  - File: tests/unit/indicators/test_ema_calculator.py
  - Test: prev(9<20), current(9>20) → CrossoverSignal(type="bullish")
  - Pattern: tests/integration/momentum/test_momentum_ranker_integration.py

- [ ] T011 [P] [US5] Write test: Detect bearish crossover when 9-EMA crosses below 20-EMA
  - File: tests/unit/indicators/test_ema_calculator.py
  - Test: prev(9>20), current(9<20) → CrossoverSignal(type="bearish")
  - Pattern: tests/integration/momentum/test_momentum_ranker_integration.py

- [ ] T012 [P] [US6] Write test: Price within 2% of 9-EMA returns True
  - File: tests/unit/indicators/test_ema_calculator.py
  - Test: price=$151.50, EMA-9=$150 → check_proximity returns True (1% within threshold)
  - Pattern: tests/integration/momentum/test_momentum_ranker_integration.py

### Implementation

- [ ] T013 [US4] Create EMACalculator class in src/trading_bot/indicators/ema_calculator.py
  - Dataclasses: EMAResult (symbol, ema_9, ema_20, current_price, calculated_at, crossover), CrossoverSignal (type, ema_short, ema_long, detected_at)
  - Methods: calculate_ema(prices, period), detect_crossover(short, long, prev_short, prev_long), check_proximity(price, ema, threshold), _calculate_alpha(period)
  - Calculation: alpha = 2/(period+1); EMA[0] = SMA(first N); EMA[i] = price * alpha + prev_EMA * (1-alpha)
  - REUSE: Decimal for precision, TradingLogger for audit
  - Pattern: src/trading_bot/risk_management/atr_calculator.py (similar calculation pattern)
  - From: spec.md FR-004, FR-005, FR-006, data-model.md EMAResult

---

## Phase 4: MACD Calculator (User Stories 7, 8, 9, 10)

**Goal**: Calculate MACD for momentum validation and exit signals

**Independent Test Criteria**:
- [ ] MACD line, signal line, histogram calculated correctly (12/26/9 periods)
- [ ] Entry validation passes when MACD > 0
- [ ] Entry validation blocks when MACD < 0
- [ ] Exit signal triggered when MACD crosses below zero
- [ ] Divergence detected (histogram expanding/contracting)

### Tests (TDD - Write First)

- [ ] T014 [P] [US7] Write test: Calculate MACD components with 50 days historical data
  - File: tests/unit/indicators/test_macd_calculator.py
  - Test: Given 50 days → MACD = EMA(12) - EMA(26), Signal = EMA(9) of MACD, Histogram = MACD - Signal
  - Pattern: tests/integration/momentum/test_catalyst_detector_integration.py

- [ ] T015 [P] [US8] Write test: Momentum validation passes when MACD > 0
  - File: tests/unit/indicators/test_macd_calculator.py
  - Test: MACD=+2.50 → validate_momentum returns True
  - Pattern: tests/integration/momentum/test_catalyst_detector_integration.py

- [ ] T016 [P] [US8] Write test: Momentum validation blocks when MACD < 0
  - File: tests/unit/indicators/test_macd_calculator.py
  - Test: MACD=-0.20 → validate_momentum returns False
  - Pattern: tests/integration/momentum/test_catalyst_detector_integration.py

- [ ] T017 [P] [US10] Write test: Exit signal when MACD crosses below zero
  - File: tests/unit/indicators/test_macd_calculator.py
  - Test: prev_MACD=+0.50, current_MACD=-0.20 → ExitSignal(reason="MACD crossed negative")
  - Pattern: tests/integration/momentum/test_catalyst_detector_integration.py

- [ ] T018 [P] [US9] Write test: Bullish divergence when histogram expanding
  - File: tests/unit/indicators/test_macd_calculator.py
  - Test: prev_histogram=+0.10, current_histogram=+0.70 → DivergenceSignal(type="bullish_divergence")
  - Pattern: tests/integration/momentum/test_catalyst_detector_integration.py

### Implementation

- [ ] T019 [US7] Create MACDCalculator class in src/trading_bot/indicators/macd_calculator.py
  - Dataclasses: MACDResult (symbol, macd_line, signal_line, histogram, calculated_at), DivergenceSignal (type, histogram_change, detected_at), ExitSignal (reason, macd_value, signal_value, triggered_at)
  - Methods: calculate(prices), validate_momentum(macd_line), detect_divergence(current, previous), check_exit_signal(current, previous), _calculate_histogram(macd, signal)
  - Calculation: Use EMACalculator.calculate_ema() for fast(12), slow(26), signal(9); MACD = fast - slow; histogram = MACD - signal
  - REUSE: EMACalculator for EMA calculations, Decimal for precision, TradingLogger for audit
  - Pattern: src/trading_bot/risk_management/atr_calculator.py
  - From: spec.md FR-008, FR-009, FR-010, FR-011, data-model.md MACDResult

---

## Phase 5: Indicator Service Facade (User Stories 11, 12)

**Goal**: Unified service API for batch calculations, entry validation, exit signals, intraday refresh

**Independent Test Criteria**:
- [ ] get_all_indicators() returns IndicatorSet with VWAP, EMA, MACD in one call
- [ ] validate_entry() checks price > VWAP AND MACD > 0 (AND gate per Constitution §Risk_Management)
- [ ] check_exit_signals() returns list of exit signals from MACD
- [ ] refresh_indicators() updates multiple symbols without errors

### Tests (TDD - Write First)

- [ ] T020 [P] [US12] Write test: get_all_indicators batch calculation
  - File: tests/integration/indicators/test_technical_indicators_service.py
  - Test: Mock MarketDataService → get_all_indicators("AAPL") → IndicatorSet with vwap, emas, macd
  - Pattern: tests/integration/momentum/test_momentum_engine_e2e.py

- [ ] T021 [P] Write test: Entry validation allowed when price > VWAP AND MACD > 0
  - File: tests/integration/indicators/test_technical_indicators_service.py
  - Test: price=$152, VWAP=$150, MACD=+2.50 → EntryValidation(allowed=True)
  - Pattern: tests/integration/momentum/test_momentum_engine_e2e.py

- [ ] T022 [P] Write test: Entry validation blocked when price < VWAP
  - File: tests/integration/indicators/test_technical_indicators_service.py
  - Test: price=$148, VWAP=$150, MACD=+2.50 → EntryValidation(allowed=False, reason="Price below VWAP")
  - Pattern: tests/integration/momentum/test_momentum_engine_e2e.py

- [ ] T023 [P] Write test: Entry validation blocked when MACD < 0
  - File: tests/integration/indicators/test_technical_indicators_service.py
  - Test: price=$152, VWAP=$150, MACD=-0.20 → EntryValidation(allowed=False, reason="MACD negative")
  - Pattern: tests/integration/momentum/test_momentum_engine_e2e.py

- [ ] T024 [P] [US11] Write test: Error propagation from MarketDataService
  - File: tests/integration/indicators/test_technical_indicators_service.py
  - Test: MarketDataService raises DataValidationError → exception propagated to caller
  - Pattern: tests/integration/dashboard/test_dashboard_error_handling.py

### Implementation

- [ ] T025 Create TechnicalIndicatorsService facade in src/trading_bot/indicators/__init__.py
  - Dataclasses: EntryValidation (allowed, reason, vwap, macd, price, validated_at), IndicatorSet (symbol, vwap, emas, macd, calculated_at)
  - Methods: __init__(market_data, config, logger), get_vwap(symbol), get_emas(symbol, periods=None), get_macd(symbol), get_all_indicators(symbol), validate_entry(symbol, price), check_exit_signals(symbol), refresh_indicators(symbols)
  - Dependencies: VWAPCalculator, EMACalculator, MACDCalculator, MarketDataService, IndicatorConfig, TradingLogger
  - Entry Logic: allowed = (price > VWAP) AND (MACD > 0) per Constitution §Risk_Management
  - REUSE: All three calculators, MarketDataService for batch data fetch, TradingLogger for audit
  - Pattern: src/trading_bot/momentum/__init__.py (facade pattern)
  - From: spec.md FR-012, data-model.md IndicatorSet, EntryValidation

---

## Phase 6: Testing & Validation

**Goal**: Achieve 90% test coverage, validate calculations against TradingView, verify performance targets

### Unit Test Coverage

- [ ] T026 [P] Run pytest with coverage for VWAP module
  - Command: pytest tests/unit/indicators/test_vwap_calculator.py --cov=src/trading_bot/indicators/vwap_calculator --cov-report=term-missing
  - Target: ≥90% line coverage
  - Pattern: Existing test commands from momentum module

- [ ] T027 [P] Run pytest with coverage for EMA module
  - Command: pytest tests/unit/indicators/test_ema_calculator.py --cov=src/trading_bot/indicators/ema_calculator --cov-report=term-missing
  - Target: ≥90% line coverage

- [ ] T028 [P] Run pytest with coverage for MACD module
  - Command: pytest tests/unit/indicators/test_macd_calculator.py --cov=src/trading_bot/indicators/macd_calculator --cov-report=term-missing
  - Target: ≥90% line coverage

- [ ] T029 [P] Run pytest with coverage for service facade
  - Command: pytest tests/integration/indicators/ --cov=src/trading_bot/indicators --cov-report=term-missing
  - Target: ≥90% line coverage overall

### Manual Validation

- [ ] T030 Manual test: Calculate VWAP for AAPL and compare to TradingView
  - Script: Create manual_test_vwap.py to fetch AAPL intraday data and calculate VWAP
  - Validation: VWAP value matches TradingView within 0.5%
  - From: spec.md Success Criteria

- [ ] T031 Manual test: Calculate EMAs (9/20) for AAPL and compare to TradingView
  - Script: Create manual_test_ema.py to fetch AAPL historical data and calculate EMAs
  - Validation: EMA-9 and EMA-20 match TradingView within 0.5%
  - From: spec.md Success Criteria

- [ ] T032 Manual test: Calculate MACD for AAPL and compare to TradingView
  - Script: Create manual_test_macd.py to fetch AAPL historical data and calculate MACD
  - Validation: MACD line, signal, histogram match TradingView within 0.5%
  - From: spec.md Success Criteria

### Type Safety & Code Quality

- [ ] T033 [P] Run mypy strict mode on indicators module
  - Command: mypy src/trading_bot/indicators --strict
  - Target: No errors
  - From: spec.md NFR-006

- [ ] T034 [P] Run bandit security scan on indicators module
  - Command: bandit -r src/trading_bot/indicators
  - Target: No high-severity vulnerabilities
  - From: spec.md Quality Gates

### Performance Validation

- [ ] T035 [P] Benchmark VWAP calculation performance
  - Tool: pytest-benchmark or time module
  - Target: <500ms for single symbol (NFR-004)
  - From: spec.md NFR-004

- [ ] T036 [P] Benchmark EMA calculation performance
  - Tool: pytest-benchmark or time module
  - Target: <500ms for single symbol, 2 periods (NFR-004)
  - From: spec.md NFR-004

- [ ] T037 [P] Benchmark MACD calculation performance
  - Tool: pytest-benchmark or time module
  - Target: <1 second for single symbol (NFR-004)
  - From: spec.md NFR-004

- [ ] T038 [P] Benchmark batch calculation (get_all_indicators) performance
  - Tool: pytest-benchmark or time module
  - Target: <2 seconds for single symbol, all 3 indicators (NFR-004)
  - From: spec.md NFR-004

---

## [TEST GUARDRAILS]

**Speed Requirements**:
- Unit tests: <2s each
- Integration tests: <10s each
- Full suite: <6 min total

**Coverage Requirements**:
- New code: ≥90% coverage (spec.md NFR-005)
- Unit tests: ≥90% line coverage
- Integration tests: ≥60% line coverage

**Measurement**:
- Python: `pytest --cov=src/trading_bot/indicators --cov-report=term-missing`

**Quality Gates**:
- All tests must pass before merge
- Coverage thresholds enforced (90%+)
- mypy strict mode passes (NFR-006)
- bandit scan passes (no high-severity)

**Clarity Requirements**:
- One behavior per test
- Descriptive names: `test_calculate_vwap_with_valid_intraday_data()`
- Given-When-Then structure in test body

**Anti-Patterns**:
- ❌ NO bare except clauses (Constitution §Fail_Safe)
- ❌ NO float arithmetic for financial calculations (use Decimal)
- ✅ USE Decimal for all price/volume/indicator values
- ✅ USE pandas vectorized operations (avoid Python loops for performance)

**Reference**: Tests follow patterns from tests/integration/momentum/ for structure and mocking
