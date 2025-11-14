# Tasks: Multi-Timeframe Confirmation for Momentum Trades

## [CODEBASE REUSE ANALYSIS]
Scanned: D:\Coding\Stocks\src\trading_bot

[EXISTING - REUSE]
- ✅ MarketDataService (src/trading_bot/market_data/market_data_service.py) - fetch daily and 10minute data
- ✅ TechnicalIndicatorsService (src/trading_bot/indicators/service.py) - MACD and EMA calculations
- ✅ BullFlagDetector (src/trading_bot/patterns/bull_flag.py) - integration point for validation
- ✅ @with_retry decorator (src/trading_bot/error_handling/retry.py) - exponential backoff for API calls
- ✅ Test patterns (tests/patterns/test_bull_flag.py, tests/indicators/test_service.py)
- ✅ JSONL logging pattern (from spec: zone_logger.py for daily rotation)

[NEW - CREATE]
- 🆕 src/trading_bot/validation/ directory (no existing validation module)
- 🆕 MultiTimeframeValidator class (orchestration logic)
- 🆕 TimeframeIndicators, TimeframeValidationResult models (dataclasses)
- 🆕 TimeframeValidationLogger (JSONL daily rotation)
- 🆕 MultiTimeframeConfig (environment-based configuration)

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 2: Foundational (models, config - blocks all stories)
2. Phase 3: US1 [P1] - Daily validation (core MVP feature)
3. Phase 4: US2 [P1] - JSONL logging (requires US1 validation logic)
4. Phase 5: US3 [P2] - 4H validation (extends US1 with weighted scoring)
5. Phase 6: US4 [P2] - Graceful degradation (requires US1 + US3)
6. Phase 7: US5 [P3] - Backtest comparison (requires all validation complete)

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 1: T001, T002 (structure + dependencies)
- Phase 2: T003, T004, T005, T006 (different files, no dependencies)
- US1 Tests: T007, T008, T009 (unit tests on different modules)
- US1 Implementation: T013 (model), T014 (config) run before T015 (validator)
- US2: T018, T019 (logger module + tests)
- US3: T022, T023, T024 (4H extension tasks)
- US4: T027, T028 (degradation logic + tests)
- US5: T030, T031, T032 (backtest tasks)
- Polish: T035, T036, T037 (documentation, health check, smoke tests)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phase 3 + Phase 4 (US1 + US2) - Daily validation with JSONL logging
**Incremental delivery**:
1. US1 + US2 → manual validation → verify daily blocking works
2. US3 → integrate 4H timeframe → validate weighted scoring
3. US4 → test degradation scenarios → verify resilience
4. US5 → backtest comparison → quantify win rate improvement

**Testing approach**: TDD required (90% coverage target, 13 unit tests + 4 integration tests from plan.md)

---

## Phase 1: Setup

- [ ] T001 Create validation module directory structure
  - Directories: src/trading_bot/validation/, tests/unit/validation/, tests/integration/validation/
  - Files: __init__.py in each directory
  - Pattern: src/trading_bot/patterns/ (module organization)
  - From: plan.md [STRUCTURE]

- [ ] T002 [P] Verify existing dependencies (no new packages required)
  - Files: requirements.txt
  - Verify: pandas, robin_stocks already present
  - Check: python -c "import pandas; import robin_stocks"
  - From: plan.md [ARCHITECTURE DECISIONS] (dependencies: None)

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Core data structures and configuration that block all user stories

- [ ] T003 [P] Create ValidationStatus enum in src/trading_bot/validation/models.py
  - Enum values: PASS, BLOCK, DEGRADED
  - Docstring: Status of multi-timeframe validation decision
  - Pattern: src/trading_bot/patterns/models.py (enum definitions)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T004 [P] Create TimeframeIndicators dataclass in src/trading_bot/validation/models.py
  - Fields: timeframe (str), price (Decimal), ema_20 (Decimal), macd_line (Decimal), macd_positive (bool), price_above_ema (bool), bar_count (int), timestamp (datetime)
  - Immutable: frozen=True
  - Pattern: src/trading_bot/patterns/models.py (dataclass structure)
  - From: plan.md [DATA MODEL]

- [ ] T005 [P] Create TimeframeValidationResult dataclass in src/trading_bot/validation/models.py
  - Fields: status (ValidationStatus), aggregate_score (Decimal), daily_score (Decimal), 4h_score (Optional[Decimal]), daily_indicators (TimeframeIndicators), 4h_indicators (Optional[TimeframeIndicators]), reasons (List[str]), timestamp (datetime), symbol (str)
  - Immutable: frozen=True
  - Validation: aggregate_score range [0.0, 1.0]
  - Pattern: src/trading_bot/patterns/models.py
  - From: plan.md [DATA MODEL]

- [ ] T006 [P] Create MultiTimeframeConfig dataclass in src/trading_bot/validation/config.py
  - Fields: enabled (bool), daily_weight (Decimal), 4h_weight (Decimal), aggregate_threshold (Decimal), max_retries (int), retry_backoff_base_ms (int)
  - Method: from_env() classmethod to load from environment variables
  - Defaults: enabled=True, daily_weight=0.6, 4h_weight=0.4, aggregate_threshold=0.5, max_retries=3, retry_backoff_base_ms=1000
  - Pattern: src/trading_bot/patterns/config.py (config dataclass structure)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 3: User Story 1 [P1] - Daily trend validation blocks counter-trend trades

**Story Goal**: Block 5-minute bull flag entries when daily trend is bearish

**Independent Test Criteria**:
- [ ] Mock daily data with MACD < 0 → verify entry blocked with "Daily MACD negative" reason
- [ ] Mock daily data with price < EMA → verify entry blocked with "Price below daily 20 EMA" reason
- [ ] Mock daily data with MACD > 0 AND price > EMA → verify entry passes (score >= 0.5)

### Tests (TDD - write failing tests first)

- [ ] T007 [P] [US1] Write test: test_timeframe_indicators_immutable
  - File: tests/unit/validation/test_models.py
  - Test: Verify TimeframeIndicators is frozen, cannot modify after creation
  - Given-When-Then: Create indicator → attempt modification → raises FrozenInstanceError
  - Pattern: tests/patterns/test_models.py
  - Coverage: 100% (new code)

- [ ] T008 [P] [US1] Write test: test_validation_result_status_transitions
  - File: tests/unit/validation/test_models.py
  - Test: Verify ValidationStatus enum has correct values (PASS, BLOCK, DEGRADED)
  - Pattern: tests/patterns/test_models.py
  - Coverage: 100%

- [ ] T009 [P] [US1] Write test: test_scoring_logic_0_to_1_range
  - File: tests/unit/validation/test_models.py
  - Test: Verify aggregate_score range validation (0.0 to 1.0)
  - Given-When-Then: Create result with score=1.5 → raises ValueError
  - Coverage: 100%

- [ ] T010 [P] [US1] Write test: test_config_from_env_loads_defaults
  - File: tests/unit/validation/test_config.py
  - Test: Verify MultiTimeframeConfig.from_env() loads default values when env vars missing
  - Mock: os.environ empty
  - Expected: enabled=True, daily_weight=0.6, 4h_weight=0.4
  - Pattern: tests/patterns/test_config.py
  - Coverage: 100%

- [ ] T011 [P] [US1] Write test: test_validate_daily_bearish_blocks_entry
  - File: tests/unit/validation/test_multi_timeframe_validator.py
  - Test: Daily MACD < 0 → status=BLOCK, reasons=["Daily MACD negative"]
  - Mock: MarketDataService returns bearish daily data
  - Pattern: tests/patterns/test_bull_flag.py (mocking pattern)
  - Coverage: 100%

- [ ] T012 [P] [US1] Write test: test_validate_daily_bullish_passes
  - File: tests/unit/validation/test_multi_timeframe_validator.py
  - Test: Daily MACD > 0 AND price > EMA → status=PASS, daily_score=1.0
  - Mock: MarketDataService returns bullish daily data
  - Coverage: 100%

### Implementation

- [ ] T013 [US1] Implement TimeframeIndicators, ValidationStatus, TimeframeValidationResult in src/trading_bot/validation/models.py
  - Use @dataclass(frozen=True) for immutability
  - Add __post_init__ for aggregate_score validation (0.0 to 1.0)
  - REUSE: Pattern from src/trading_bot/patterns/models.py (dataclass structure)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T014 [US1] Implement MultiTimeframeConfig in src/trading_bot/validation/config.py
  - from_env() method: os.getenv() with type conversion (str → Decimal, str → bool)
  - Defaults match plan.md: daily_weight=0.6, 4h_weight=0.4, threshold=0.5
  - REUSE: Pattern from src/trading_bot/patterns/config.py
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T015 [US1] Implement MultiTimeframeValidator._fetch_daily_data() in src/trading_bot/validation/multi_timeframe_validator.py
  - Method signature: _fetch_daily_data(symbol: str) -> pd.DataFrame
  - Logic: Call self.market_data_service.get_historical_data(symbol, interval="day", span="3month")
  - Apply @with_retry decorator with DEFAULT_POLICY (3 retries, exponential backoff)
  - Validation: Minimum 30 bars required (raise ValueError if insufficient)
  - REUSE: MarketDataService (src/trading_bot/market_data/market_data_service.py)
  - REUSE: @with_retry (src/trading_bot/error_handling/retry.py)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T016 [US1] Implement MultiTimeframeValidator._calculate_daily_indicators() in src/trading_bot/validation/multi_timeframe_validator.py
  - Method signature: _calculate_daily_indicators(bars: pd.DataFrame, current_price: Decimal) -> TimeframeIndicators
  - Logic:
    1. Create TechnicalIndicatorsService instance (separate from other timeframes)
    2. Calculate MACD via service.get_macd(bars)
    3. Calculate EMA (20) via service.get_emas(bars)
    4. Return TimeframeIndicators(timeframe="DAILY", price=current_price, ema_20=ema_result.ema_20, macd_line=macd_result.macd_line, ...)
  - REUSE: TechnicalIndicatorsService (src/trading_bot/indicators/service.py)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T017 [US1] Implement MultiTimeframeValidator._score_timeframe() in src/trading_bot/validation/multi_timeframe_validator.py
  - Method signature: _score_timeframe(indicators: TimeframeIndicators) -> Decimal
  - Logic: score = 0.5 (if MACD > 0) + 0.5 (if price > EMA), range [0.0, 1.0]
  - Return: Decimal score
  - From: plan.md [DATA MODEL] (scoring logic)

- [ ] T018 [US1] Implement MultiTimeframeValidator.validate() orchestration (daily-only MVP)
  - Method signature: validate(symbol: str, current_price: Decimal, bars_5min: List) -> TimeframeValidationResult
  - Logic:
    1. Fetch daily data via _fetch_daily_data()
    2. Calculate daily indicators via _calculate_daily_indicators()
    3. Compute daily_score via _score_timeframe()
    4. Determine status: PASS if daily_score >= 0.5, BLOCK otherwise
    5. Build reasons list: ["Daily MACD negative"] if MACD < 0, ["Price below daily 20 EMA"] if price < EMA
    6. Return TimeframeValidationResult(status, aggregate_score=daily_score, ...)
  - REUSE: Composition pattern from plan.md
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

### Integration

- [ ] T019 [US1] Write E2E test: test_e2e_daily_validation_with_real_market_data
  - File: tests/integration/validation/test_bull_flag_multi_timeframe.py
  - Test: Use real MarketDataService (not mocked) to fetch AAPL daily data, validate indicators calculated correctly
  - Real data: Actual API call to Robinhood (test environment)
  - Expected: TimeframeIndicators has valid MACD and EMA values
  - Pattern: tests/integration/test_market_data_integration.py
  - Coverage: ≥90% critical path

---

## Phase 4: User Story 2 [P1] - JSONL logging for validation audit trail

**Story Goal**: Log all validation events to structured JSONL for analysis

**Independent Test Criteria**:
- [ ] Trigger validation → verify event written to logs/timeframe-validation/YYYY-MM-DD.jsonl
- [ ] Event contains: timestamp, symbol, decision, aggregate_score, daily_macd, reasons
- [ ] Query 3 events by symbol → verify filtering works

### Tests

- [ ] T020 [P] [US2] Write test: test_logger_writes_to_daily_file
  - File: tests/unit/validation/test_logger.py
  - Test: Call logger.log_validation_event(result) → verify file created at logs/timeframe-validation/2024-10-28.jsonl
  - Mock: datetime.now() to fixed date
  - Verify: File contains JSON line with all required fields
  - Pattern: tests/unit/test_logger.py (if exists, else create new)
  - Coverage: 100%

- [ ] T021 [P] [US2] Write test: test_logger_includes_all_indicator_values
  - File: tests/unit/validation/test_logger.py
  - Test: Log event → verify JSON contains daily_macd, daily_ema_20, price_vs_ema, reasons
  - Coverage: 100%

### Implementation

- [ ] T022 [US2] Create TimeframeValidationLogger class in src/trading_bot/validation/logger.py
  - Method: log_validation_event(result: TimeframeValidationResult) -> None
  - Logic:
    1. Generate log filename: logs/timeframe-validation/{date}.jsonl
    2. Create log directory if missing
    3. Build event dict with 15 fields: event="timeframe_validation", symbol, timestamp, decision, aggregate_score, daily_macd, daily_ema_20, daily_price_vs_ema, reasons, validation_duration_ms, degraded_mode, etc.
    4. Append JSON line to daily file (use json.dumps() + file.write())
  - Pattern: src/trading_bot/support_resistance/zone_logger.py (JSONL daily rotation)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T023 [US2] Integrate logger into MultiTimeframeValidator.validate()
  - Modification: Add self.logger = TimeframeValidationLogger() to __init__
  - Logic: Call self.logger.log_validation_event(result) before returning result
  - Timing: Measure validation duration with datetime.now() before/after
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 5: User Story 3 [P2] - 4H timeframe adds intraday momentum confirmation

**Story Goal**: Use weighted scoring (Daily 60% + 4H 40%) for nuanced decisions

**Independent Test Criteria**:
- [ ] Daily bullish + 4H bearish → aggregate_score = 0.6 * 1.0 + 0.4 * 0.0 = 0.6 (PASS)
- [ ] Daily bearish + 4H bullish → aggregate_score = 0.6 * 0.0 + 0.4 * 1.0 = 0.4 (BLOCK)
- [ ] Both bullish → aggregate_score = 1.0 (PASS)

### Tests

- [ ] T024 [P] [US3] Write test: test_validate_conflicting_signals_uses_weighted_score
  - File: tests/unit/validation/test_multi_timeframe_validator.py
  - Test: Mock daily bullish (score=1.0), 4H bearish (score=0.0) → verify aggregate_score=0.6, status=PASS
  - Verify: Weighted scoring formula correct
  - Coverage: 100%

- [ ] T025 [P] [US3] Write test: test_validate_both_bullish_passes
  - File: tests/unit/validation/test_multi_timeframe_validator.py
  - Test: Mock daily + 4H both bullish → aggregate_score=1.0, status=PASS
  - Coverage: 100%

- [ ] T026 [P] [US3] Write test: test_validate_insufficient_4h_bars_raises_error
  - File: tests/unit/validation/test_multi_timeframe_validator.py
  - Test: Mock 4H data with <72 bars → raises InsufficientDataError
  - Verify: Error message includes "4H timeframe requires 72 bars"
  - Coverage: 100%

### Implementation

- [ ] T027 [US3] Implement MultiTimeframeValidator._fetch_4h_data() in src/trading_bot/validation/multi_timeframe_validator.py
  - Method signature: _fetch_4h_data(symbol: str) -> pd.DataFrame
  - Logic: Call self.market_data_service.get_historical_data(symbol, interval="10minute", span="week")
  - Validation: Minimum 72 bars required (72 * 10min = 12 hours * 3 days = 4H bars via resampling)
  - Apply @with_retry decorator
  - REUSE: MarketDataService
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T028 [US3] Implement MultiTimeframeValidator._calculate_4h_indicators() in src/trading_bot/validation/multi_timeframe_validator.py
  - Method signature: _calculate_4h_indicators(bars: pd.DataFrame, current_price: Decimal) -> TimeframeIndicators
  - Logic: Same as daily but with separate TechnicalIndicatorsService instance (prevents state collision)
  - Return: TimeframeIndicators(timeframe="4H", ...)
  - REUSE: TechnicalIndicatorsService (separate instance)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T029 [US3] Update MultiTimeframeValidator.validate() to include 4H timeframe
  - Modification: After daily validation passes, fetch + score 4H data
  - Logic:
    1. If daily_score >= 0.5, fetch 4H data
    2. Calculate 4H indicators
    3. Compute 4h_score via _score_timeframe()
    4. Calculate aggregate_score = daily_score * 0.6 + 4h_score * 0.4
    5. Determine status: PASS if aggregate_score > 0.5, BLOCK otherwise
    6. Update reasons list based on both timeframes
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 6: User Story 4 [P2] - Graceful degradation on API failures

**Story Goal**: Fall back to single-timeframe mode on data fetch failures

**Independent Test Criteria**:
- [ ] Daily API returns HTTP 503 → retry 3 times → status=DEGRADED after retries exhausted
- [ ] Degraded event logged with severity=HIGH
- [ ] Trade allowed with higher_timeframe_validation_skipped=true flag

### Tests

- [ ] T030 [P] [US4] Write test: test_validate_data_fetch_failure_degrades_gracefully
  - File: tests/unit/validation/test_multi_timeframe_validator.py
  - Test: Mock MarketDataService to raise exception 3 times → verify status=DEGRADED, reasons=["Daily data unavailable after 3 retries"]
  - Verify: @with_retry decorator triggers exponential backoff
  - Coverage: 100%

- [ ] T031 [P] [US4] Write test: test_degraded_mode_logs_high_severity
  - File: tests/unit/validation/test_logger.py
  - Test: Log DEGRADED result → verify event contains severity="HIGH", degraded_mode=true
  - Coverage: 100%

### Implementation

- [ ] T032 [US4] Add graceful degradation to MultiTimeframeValidator.validate()
  - Modification: Wrap _fetch_daily_data() in try-except block
  - Logic:
    1. If data fetch fails after retries, catch exception
    2. Log warning: "Multi-timeframe validation degraded for {symbol}"
    3. Return TimeframeValidationResult(status=DEGRADED, reasons=["Daily data unavailable after 3 retries"], ...)
    4. Set aggregate_score = None (validation skipped)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T033 [US4] Add degraded_mode flag to TimeframeValidationEvent in logger
  - Modification: Add degraded_mode (bool) and severity (str) fields to JSON output
  - Logic: severity="HIGH" when status=DEGRADED
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

---

## Phase 7: User Story 5 [P3] - Backtest comparison quantifies win rate improvement

**Story Goal**: Measure 52% → 63% win rate improvement via historical data

**Independent Test Criteria**:
- [ ] Run baseline backtest (multi_timeframe=false) → win_rate ~52%
- [ ] Run enhanced backtest (multi_timeframe=true) → win_rate ~63%
- [ ] Report shows: win_rate_delta >= 8%, false_positive_reduction >= 30%

### Tests

- [ ] T034 [P] [US5] Write test: test_backtest_comparison_report_generation
  - File: tests/integration/validation/test_backtest_comparison.py
  - Test: Run mini backtest (10 trades) with baseline + enhanced → verify report contains win_rate_delta
  - Mock: Historical data for AAPL (2024-05-01 to 2024-05-10)
  - Pattern: tests/integration/test_bot_safety_integration.py (integration test structure)
  - Coverage: ≥80%

### Implementation

- [ ] T035 [US5] Create backtest comparison script in src/trading_bot/backtest/compare_multi_timeframe.py
  - Script: CLI tool to run baseline vs enhanced backtests
  - Args: --symbols AAPL,TSLA,NVDA --start-date 2024-05-01 --end-date 2024-10-28
  - Output: JSON report with win_rate_delta, false_positive_reduction, trades_filtered_count
  - REUSE: Existing backtest engine (src/trading_bot/backtest/)
  - From: plan.md [BACKTEST VALIDATION PLAN]

- [ ] T036 [US5] Generate Markdown report from backtest results
  - Script: src/trading_bot/backtest/generate_comparison_report.py
  - Input: backtests/results/baseline.json, backtests/results/enhanced.json
  - Output: backtests/reports/multi-timeframe-improvement.md
  - Format: Table with win_rate, total_trades, trades_filtered, false_positive_reduction
  - From: plan.md [BACKTEST VALIDATION PLAN]

---

## Phase 8: Integration with BullFlagDetector

**Goal**: Wire multi-timeframe validation into existing bull flag detection flow

- [ ] T037 Add MultiTimeframeValidator to BullFlagDetector.__init__ in src/trading_bot/patterns/bull_flag.py
  - Modification: Add optional parameter: multi_timeframe_validator: Optional[MultiTimeframeValidator] = None
  - Logic: If validator provided, store as self.multi_timeframe_validator
  - REUSE: Composition pattern (validator as dependency, not inheritance)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T038 Call validator in BullFlagDetector.detect() before returning result
  - Modification: Before returning BullFlagResult, check if self.multi_timeframe_validator exists
  - Logic:
    1. If validator exists, call validation_result = self.multi_timeframe_validator.validate(symbol, current_price, bars)
    2. If status == BLOCK, return self._create_failed_result(symbol, f"Multi-timeframe validation blocked: {', '.join(validation_result.reasons)}")
    3. If status == DEGRADED, log warning but allow trade to proceed
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T039 [P] Write test: test_bull_flag_with_multi_timeframe_pass
  - File: tests/patterns/test_bull_flag.py
  - Test: Mock validator to return PASS → verify bull flag detection proceeds normally
  - Pattern: Existing bull flag tests
  - Coverage: 100%

- [ ] T040 [P] Write test: test_bull_flag_with_multi_timeframe_block
  - File: tests/patterns/test_bull_flag.py
  - Test: Mock validator to return BLOCK → verify bull flag returns detected=False with blocking reason
  - Coverage: 100%

- [ ] T041 [P] Write test: test_bull_flag_multi_timeframe_disabled_via_flag
  - File: tests/patterns/test_bull_flag.py
  - Test: MultiTimeframeConfig.enabled=false → verify validator not called, trade proceeds
  - Coverage: 100%

---

## Phase 9: Polish & Cross-Cutting Concerns

### Performance Validation

- [ ] T042 Write test: test_latency_under_2s_p95
  - File: tests/integration/validation/test_multi_timeframe_performance.py
  - Test: Run 100 validations, measure validation_duration_ms, verify P95 < 2000ms
  - Real data: Actual MarketDataService API calls
  - Pattern: tests/performance/test_validator_performance.py
  - Coverage: Performance SLA validation

- [ ] T043 Write test: test_concurrent_validations_no_state_collision
  - File: tests/integration/validation/test_multi_timeframe_concurrency.py
  - Test: Run 10 parallel validations for different symbols, verify no indicator state collision
  - Logic: Each validation creates separate TechnicalIndicatorsService instances
  - Verify: All results correct (no cross-contamination)
  - Coverage: Concurrency safety

### Error Handling & Resilience

- [ ] T044 [P] Add input validation to MultiTimeframeValidator.validate()
  - Validation: symbol non-empty, current_price > 0, bars_5min not empty
  - Error: Raise ValueError with descriptive message if invalid
  - From: plan.md [SECURITY] (input validation)

- [ ] T045 [P] Write test: test_validate_invalid_symbol_raises_valueerror
  - File: tests/unit/validation/test_multi_timeframe_validator.py
  - Test: Call validate(symbol="", ...) → raises ValueError("Symbol cannot be empty")
  - Coverage: 100%

### Deployment Preparation

- [ ] T046 Add environment variable examples to .env.example
  - File: .env.example (root directory)
  - Variables: MULTI_TIMEFRAME_VALIDATION_ENABLED=true, DAILY_WEIGHT=0.6, 4H_WEIGHT=0.4, AGGREGATE_THRESHOLD=0.5
  - Comments: Explain each variable purpose
  - From: plan.md [CI/CD IMPACT]

- [ ] T047 Document rollback procedure in specs/033-multi-timeframe-confirmation/NOTES.md
  - Sections: Feature flag rollback, Code rollback (git revert), Verification steps
  - Command: export MULTI_TIMEFRAME_VALIDATION_ENABLED=false (instant disable)
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] T048 [P] Create manual testing checklist in specs/033-multi-timeframe-confirmation/NOTES.md
  - Test scenarios: Daily bearish blocks entry, Both bullish passes, Degraded mode triggers
  - CLI commands: python -m src.trading_bot.main (paper trading with validation enabled)
  - Expected outcomes: Validation events in logs/timeframe-validation/*.jsonl
  - From: plan.md [INTEGRATION SCENARIOS]

### Documentation

- [ ] T049 [P] Add docstrings to all public methods
  - Files: src/trading_bot/validation/*.py
  - Format: Google-style docstrings with Args, Returns, Raises sections
  - Examples: Include usage examples in class-level docstrings
  - Pattern: src/trading_bot/patterns/bull_flag.py (docstring style)

- [ ] T050 [P] Create JSONL query examples in specs/033-multi-timeframe-confirmation/NOTES.md
  - Queries:
    1. Win rate: jq -r 'select(.timeframe_validation_enabled == true) | .outcome' logs/trades/*.jsonl | awk '/win/{w++} /loss/{l++} END {print w/(w+l)*100"%"}'
    2. Blocked trades: grep '"decision":"BLOCK"' logs/timeframe-validation/*.jsonl | wc -l
    3. Latency P95: jq -r '.validation_duration_ms' logs/timeframe-validation/*.jsonl | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'
  - From: plan.md [MEASUREMENT PLAN]

---

## [TEST GUARDRAILS]

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each (real API calls may take longer, acceptable)
- Full suite: <6 min total

**Coverage Requirements:**
- New code: 100% coverage (all new validation module code must be tested)
- Unit tests: ≥90% line coverage (13 unit tests from plan.md)
- Integration tests: ≥80% line coverage (4 integration tests from plan.md)
- Modified code: Coverage cannot decrease in bull_flag.py

**Measurement:**
- Python: `pytest --cov=src/trading_bot/validation --cov-report=term-missing`
- Target: 90%+ coverage (from spec.md)

**Quality Gates:**
- All tests must pass before merge
- Coverage thresholds enforced manually (review coverage report)
- No skipped tests without documented reason in NOTES.md

**Clarity Requirements:**
- One behavior per test
- Descriptive names: `test_validate_daily_bearish_blocks_entry()` (behavior-focused)
- Given-When-Then structure in test body (comment format)

**Anti-Patterns:**
- ❌ NO UI snapshots (backend-only feature)
- ❌ NO "prop-mirror" tests (test behavior, not implementation)
- ✅ USE mocking for MarketDataService in unit tests (fast, deterministic)
- ✅ USE real data in integration tests (validate API integration)

**Examples:**
```python
# ❌ Bad: Tests implementation details
assert validator._last_macd == Decimal("0.52")

# ✅ Good: Tests behavior/outcome
result = validator.validate("AAPL", Decimal("150.00"), bars)
assert result.status == ValidationStatus.BLOCK
assert "Daily MACD negative" in result.reasons

# ❌ Bad: Generic assertion
assert result is not None

# ✅ Good: Specific, meaningful assertion
assert result.aggregate_score == Decimal("0.6")
assert result.daily_score == Decimal("1.0")
assert result.4h_score == Decimal("0.0")
```
