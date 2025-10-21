# Tasks: Position Scaling & Phase Progression

## [CODEBASE REUSE ANALYSIS]

**Scanned**: src/trading_bot/**/*.py, tests/**/*.py

**[EXISTING - REUSE]**
- ✅ Config (src/trading_bot/config.py) - Phase enum validation, config.json loading
- ✅ ModeSwitcher (src/trading_bot/mode_switcher.py) - Phase-based paper/live switching
- ✅ PerformanceTracker (src/trading_bot/performance/tracker.py) - Session metrics aggregation
- ✅ PerformanceSummary (src/trading_bot/performance/models.py) - Dataclass with Decimal precision
- ✅ MetricsCalculator (src/trading_bot/dashboard/metrics_calculator.py) - Win rate, R:R calculations
- ✅ CircuitBreaker (src/trading_bot/error_handling/circuit_breaker.py) - Sliding window failure tracking
- ✅ StructuredLogger (src/trading_bot/logging/structured_logger.py) - JSONL logging pattern
- ✅ TradeQueryHelper (src/trading_bot/logging/query_helper.py) - JSONL query by date

**[NEW - CREATE]**
- 🆕 PhaseManager (src/trading_bot/phase/manager.py) - Phase transitions, downgrades, position sizing
- 🆕 Phase validators (src/trading_bot/phase/validators.py) - Profitability gate validation
- 🆕 TradeLimiter (src/trading_bot/phase/trade_limiter.py) - PoC 1 trade/day enforcement
- 🆕 HistoryLogger (src/trading_bot/phase/history_logger.py) - Phase transition JSONL logging
- 🆕 Phase models (src/trading_bot/phase/models.py) - Phase enum, SessionMetrics, PhaseTransition
- 🆕 Phase CLI (src/trading_bot/phase/cli.py) - CSV/JSON export command

---

## [DEPENDENCY GRAPH]

**Story completion order:**
1. **Phase 1**: Setup (project structure, directories)
2. **Phase 2**: Foundational (models, config extension) - blocks all stories
3. **Phase 3**: US1 [P1] - Phase system foundation (independent)
4. **Phase 4**: US2 [P1] - Trade limit enforcement (depends on US1 models)
5. **Phase 5**: US3 [P1] - Profitability tracking (depends on US1 models)
6. **Phase 6**: US4 [P2] - Position size scaling (depends on US1, US3)
7. **Phase 7**: US5 [P2] - Automatic downgrades (depends on US1, US3)
8. **Phase 8**: US6 [P3] - Export and CLI (depends on US1, US3)
9. **Phase 9**: Polish & Integration

---

## [PARALLEL EXECUTION OPPORTUNITIES]

- **Phase 2**: T010, T011, T012 (different model files, no dependencies)
- **US1 Tests**: T020, T021, T022 (independent test files)
- **US1 Implementation**: T025, T026 (validators and history logger are independent)
- **US2**: T040, T041 (test and implementation for trade limiter)
- **US3 Tests**: T050, T051, T052 (independent test files)
- **Polish**: T120, T121, T122, T123 (error handling, health check, smoke tests)

---

## [IMPLEMENTATION STRATEGY]

**MVP Scope**: Phases 3-5 (US1-US3) only
**Incremental delivery**: US1 → US2 → US3 → validate with paper trading → US4-US6 based on feedback
**Testing approach**: TDD required (90%+ coverage target per constitution)
**Deployment model**: Local-only (no remote deployment needed)

---

## Phase 1: Setup

- [ ] T001 Create phase module structure
  - **Files**: src/trading_bot/phase/__init__.py, tests/phase/__init__.py, logs/phase/
  - **Directories**: src/trading_bot/phase/, tests/phase/, logs/phase/
  - **Pattern**: src/trading_bot/performance/ structure
  - **From**: plan.md [STRUCTURE]

- [ ] T002 [P] Create phase logs directory with .gitkeep
  - **Files**: logs/phase/.gitkeep, logs/phase/phase-history.jsonl (empty), logs/phase/phase-overrides.jsonl (empty)
  - **Purpose**: Ensure logs/phase/ tracked in git
  - **Pattern**: logs/performance/ structure

- [ ] T003 [P] Add phase module exports to __init__.py
  - **File**: src/trading_bot/phase/__init__.py
  - **Exports**: Phase, PhaseManager, TradeLimitExceeded, PhaseValidationError
  - **Pattern**: src/trading_bot/performance/__init__.py
  - **From**: plan.md [MODULE ORGANIZATION]

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Core models and configuration that block all user stories

### Models

- [ ] T010 [P] [TDD] Write tests for Phase enum
  - **File**: tests/phase/test_models.py::test_phase_enum_values
  - **Tests**: Valid phase values, string conversion, invalid phase handling
  - **Pattern**: tests/performance/test_models.py
  - **Coverage**: 100% (4 enum values + error cases)

- [ ] T011 [P] [TDD] Write tests for SessionMetrics dataclass
  - **File**: tests/phase/test_models.py::TestSessionMetrics
  - **Tests**: Field validation, Decimal precision, date constraints, UTC timestamps
  - **Pattern**: tests/performance/test_models.py::TestPerformanceSummary
  - **Coverage**: 100% (all fields + validation rules)

- [ ] T012 [P] [TDD] Write tests for PhaseTransition dataclass
  - **File**: tests/phase/test_models.py::TestPhaseTransition
  - **Tests**: Transition validation, metrics snapshot serialization, atomic operations
  - **Pattern**: tests/performance/test_models.py
  - **Coverage**: 100% (all fields + edge cases)

- [ ] T015 [RED] Create Phase enum in models.py
  - **File**: src/trading_bot/phase/models.py
  - **Values**: EXPERIENCE, PROOF_OF_CONCEPT, REAL_MONEY_TRIAL, SCALING
  - **Methods**: to_string(), from_string(), is_valid()
  - **Pattern**: Enum with string conversion (stdlib)
  - **From**: data-model.md Phase entity

- [ ] T016 [RED] Create SessionMetrics dataclass
  - **File**: src/trading_bot/phase/models.py::SessionMetrics
  - **Fields**: session_date (date), phase (Phase), trades_executed (int), win_rate (Decimal), average_rr (Decimal), total_pnl (Decimal), position_sizes (List[Decimal]), circuit_breaker_trips (int), created_at (datetime)
  - **REUSE**: Decimal from decimal module, dataclass pattern
  - **Pattern**: PerformanceSummary (src/trading_bot/performance/models.py)
  - **From**: data-model.md SessionMetrics entity

- [ ] T017 [RED] Create PhaseTransition dataclass
  - **File**: src/trading_bot/phase/models.py::PhaseTransition
  - **Fields**: transition_id (str/UUID), timestamp (datetime UTC), from_phase (Phase), to_phase (Phase), trigger (str), validation_passed (bool), metrics_snapshot (Dict), failure_reasons (List[str] | None), operator_id (str | None), override_password_used (bool)
  - **Pattern**: PerformanceSummary (src/trading_bot/performance/models.py)
  - **From**: data-model.md PhaseTransition entity

- [ ] T018 [GREEN] Run tests - all Phase model tests should pass
  - **Command**: pytest tests/phase/test_models.py -v --cov=src/trading_bot/phase/models
  - **Expected**: All tests pass, 100% coverage on models.py
  - **Fix**: Adjust implementations until all tests green

### Configuration Extension

- [ ] T020 [P] [TDD] Write tests for Config phase_progression loading
  - **File**: tests/unit/test_config.py::test_phase_progression_from_json
  - **Tests**: Load phase config from JSON, default values, validation errors
  - **Pattern**: tests/unit/test_config.py (existing config tests)
  - **Coverage**: Phase-specific config loading

- [ ] T021 [RED] Extend config.json schema with phase configurations
  - **File**: config.json (if exists, otherwise create tests/fixtures/config.phase_test.json)
  - **Add**: phase_progression.experience, phase_progression.proof, phase_progression.trial, phase_progression.scaling
  - **Structure**: max_trades_per_day, position_size_min/max, advancement_criteria, downgrade_triggers
  - **Pattern**: Existing config.json structure
  - **From**: data-model.md PhaseConfiguration

- [ ] T022 [GREEN] Verify Config.from_env_and_json loads phase config
  - **Command**: pytest tests/unit/test_config.py::test_phase_progression_from_json -v
  - **Expected**: Config loads phase configurations correctly
  - **Fix**: Adjust Config.from_env_and_json if needed

---

## Phase 3: US1 [P1] - Phase System Foundation

**Story Goal**: Operators must progress through Experience → PoC → Trial → Scaling with profitability gates

**Independent Test Criteria**:
- [ ] Create bot in Experience phase, attempt to switch to PoC without criteria (20 sessions, 60% win rate) → should block
- [ ] Meet all criteria (20 sessions, 60% win rate, R:R ≥1.5) → should advance to PoC
- [ ] Manual phase change without criteria → should block and log override attempt

### Tests (TDD - Write First)

- [ ] T030 [P] [TDD] Write tests for ValidationResult dataclass
  - **File**: tests/phase/test_validators.py::TestValidationResult
  - **Tests**: can_advance bool, criteria_met dict, missing_requirements list
  - **Pattern**: tests/performance/test_models.py
  - **Coverage**: 100% dataclass fields

- [ ] T031 [P] [TDD] Write tests for ExperienceToPoCValidator
  - **File**: tests/phase/test_validators.py::TestExperienceToPoCValidator
  - **Tests**:
    - validate() with 20 sessions, 60% win rate, 1.5 R:R → ValidationResult(can_advance=True)
    - validate() with 15 sessions → ValidationResult(can_advance=False, missing="session_count")
    - validate() with 20 sessions, 55% win rate → ValidationResult(can_advance=False, missing="win_rate")
  - **Mock**: PerformanceTracker.get_summary()
  - **Pattern**: tests/performance/test_tracker.py (mocking pattern)
  - **Coverage**: All validation branches

- [ ] T032 [P] [TDD] Write tests for PoCToTrialValidator
  - **File**: tests/phase/test_validators.py::TestPoCToTrialValidator
  - **Tests**: 30 sessions, 50 trades, 65% win rate, 1.8 R:R criteria
  - **Mock**: PerformanceTracker.get_summary()
  - **Coverage**: All validation branches

- [ ] T033 [P] [TDD] Write tests for TrialToScalingValidator
  - **File**: tests/phase/test_validators.py::TestTrialToScalingValidator
  - **Tests**: 60 sessions, 100 trades, 70% win rate, 2.0 R:R, <5% drawdown criteria
  - **Mock**: PerformanceTracker.get_summary()
  - **Coverage**: All validation branches + drawdown logic

### Implementation

- [ ] T035 [RED] Create ValidationResult dataclass
  - **File**: src/trading_bot/phase/validators.py::ValidationResult
  - **Fields**: can_advance (bool), criteria_met (Dict[str, bool]), missing_requirements (List[str]), metrics_summary (Dict[str, Any])
  - **Pattern**: Dataclass with validation helper methods
  - **From**: contracts/phase-api.yaml Validator Protocol

- [ ] T036 [RED] Implement ExperienceToPoCValidator
  - **File**: src/trading_bot/phase/validators.py::ExperienceToPoCValidator
  - **Method**: validate(from_phase, to_phase, session_count, trade_count, win_rate, avg_rr) → ValidationResult
  - **Logic**: Check session_count ≥20, win_rate ≥0.60, avg_rr ≥1.5
  - **REUSE**: PerformanceTracker for metrics (pass as dependency)
  - **Pattern**: Strategy pattern validator
  - **From**: spec.md FR-002, plan.md [PHASE VALIDATORS]

- [ ] T037 [RED] Implement PoCToTrialValidator
  - **File**: src/trading_bot/phase/validators.py::PoCToTrialValidator
  - **Method**: validate(...) → ValidationResult
  - **Logic**: Check session_count ≥30, trade_count ≥50, win_rate ≥0.65, avg_rr ≥1.8
  - **Pattern**: Same as ExperienceToPoCValidator
  - **From**: spec.md FR-002

- [ ] T038 [RED] Implement TrialToScalingValidator
  - **File**: src/trading_bot/phase/validators.py::TrialToScalingValidator
  - **Method**: validate(..., max_drawdown) → ValidationResult
  - **Logic**: Check session_count ≥60, trade_count ≥100, win_rate ≥0.70, avg_rr ≥2.0, max_drawdown <0.05
  - **Pattern**: Same as ExperienceToPoCValidator + drawdown check
  - **From**: spec.md FR-002

- [ ] T039 [GREEN] Run validator tests - all should pass
  - **Command**: pytest tests/phase/test_validators.py -v --cov=src/trading_bot/phase/validators
  - **Expected**: All tests pass, 100% coverage on validators.py
  - **Fix**: Adjust validator logic until all tests green

### Phase Manager

- [ ] T040 [P] [TDD] Write tests for PhaseManager.validate_transition
  - **File**: tests/phase/test_manager.py::TestPhaseManager::test_validate_transition
  - **Tests**:
    - validate_transition(Phase.PROOF_OF_CONCEPT) with criteria met → ValidationResult(can_advance=True)
    - validate_transition(Phase.PROOF_OF_CONCEPT) without criteria → ValidationResult(can_advance=False)
    - validate_transition(Phase.SCALING) from Experience → ValueError (non-sequential)
  - **Mock**: Config, PerformanceTracker, validators
  - **Coverage**: All validation paths

- [ ] T041 [P] [TDD] Write tests for PhaseManager.advance_phase
  - **File**: tests/phase/test_manager.py::TestPhaseManager::test_advance_phase
  - **Tests**:
    - advance_phase(Phase.PROOF_OF_CONCEPT) with validation pass → PhaseTransition logged
    - advance_phase(Phase.PROOF_OF_CONCEPT) with validation fail → raises PhaseValidationError
    - advance_phase(Phase.PROOF_OF_CONCEPT, force=True) → requires override password
  - **Mock**: Config, HistoryLogger, validators
  - **Coverage**: Success path, validation failure, force override

- [ ] T045 [RED] Create PhaseManager class
  - **File**: src/trading_bot/phase/manager.py::PhaseManager
  - **Init**: __init__(config: Config, tracker: PerformanceTracker, history_logger: HistoryLogger)
  - **Dependencies**: Config, PerformanceTracker, HistoryLogger, validators
  - **Pattern**: Service orchestrator
  - **From**: plan.md [PHASE MANAGEMENT SERVICE]

- [ ] T046 [RED] Implement PhaseManager.validate_transition
  - **File**: src/trading_bot/phase/manager.py::PhaseManager.validate_transition
  - **Method**: validate_transition(self, to_phase: Phase) → ValidationResult
  - **Logic**:
    1. Get current_phase from config
    2. Select appropriate validator (Experience→PoC, PoC→Trial, Trial→Scaling)
    3. Get metrics from PerformanceTracker.get_summary()
    4. Call validator.validate() with metrics
    5. Return ValidationResult
  - **REUSE**: PerformanceTracker, validators (T036-T038)
  - **From**: contracts/phase-api.yaml PhaseManagerProtocol

- [ ] T047 [RED] Implement PhaseManager.advance_phase
  - **File**: src/trading_bot/phase/manager.py::PhaseManager.advance_phase
  - **Method**: advance_phase(self, to_phase: Phase, force: bool = False) → PhaseTransition
  - **Logic**:
    1. If not force: validate_transition(), raise PhaseValidationError if fail
    2. If force: check override password (env var PHASE_OVERRIDE_PASSWORD)
    3. Create PhaseTransition record with metrics snapshot
    4. Update config.json (phase_progression.current_phase)
    5. Log transition to HistoryLogger
    6. Return PhaseTransition
  - **REUSE**: Config, HistoryLogger (T060)
  - **From**: contracts/phase-api.yaml PhaseManagerProtocol

- [ ] T048 [GREEN] Run PhaseManager tests - all should pass
  - **Command**: pytest tests/phase/test_manager.py::TestPhaseManager -v --cov=src/trading_bot/phase/manager
  - **Expected**: validate_transition and advance_phase tests pass
  - **Fix**: Adjust PhaseManager until all tests green

### History Logging

- [ ] T050 [P] [TDD] Write tests for HistoryLogger.log_transition
  - **File**: tests/phase/test_history_logger.py::TestHistoryLogger::test_log_transition
  - **Tests**:
    - log_transition() appends to logs/phase/phase-history.jsonl
    - JSONL format valid (one JSON object per line)
    - Decimal fields serialized as strings
    - UTC timestamps in ISO format
  - **Pattern**: tests/performance/test_tracker.py (JSONL testing)
  - **Coverage**: Append operation, serialization

- [ ] T051 [P] [TDD] Write tests for HistoryLogger.log_override_attempt
  - **File**: tests/phase/test_history_logger.py::TestHistoryLogger::test_log_override_attempt
  - **Tests**:
    - log_override_attempt() appends to logs/phase/phase-overrides.jsonl
    - Blocked attempts logged correctly
    - Successful overrides logged with operator_id
  - **Coverage**: Both blocked and successful cases

- [ ] T055 [RED] Create HistoryLogger class
  - **File**: src/trading_bot/phase/history_logger.py::HistoryLogger
  - **Init**: __init__(log_dir: Path = Path("logs/phase"))
  - **Fields**: transition_log_path (Path), override_log_path (Path)
  - **Pattern**: Append-only JSONL logger
  - **From**: plan.md [PHASE HISTORY LOGGER]

- [ ] T056 [RED] Implement HistoryLogger.log_transition
  - **File**: src/trading_bot/phase/history_logger.py::HistoryLogger.log_transition
  - **Method**: log_transition(self, transition: PhaseTransition) → None
  - **Logic**:
    1. Serialize PhaseTransition to JSON (Decimal → string)
    2. Append to logs/phase/phase-history.jsonl
    3. Ensure atomic write (no partial records)
  - **REUSE**: JSON encoder with Decimal handler
  - **Pattern**: StructuredLogger (src/trading_bot/logging/structured_logger.py)
  - **From**: contracts/phase-api.yaml HistoryLoggerProtocol

- [ ] T057 [RED] Implement HistoryLogger.log_override_attempt
  - **File**: src/trading_bot/phase/history_logger.py::HistoryLogger.log_override_attempt
  - **Method**: log_override_attempt(self, phase, action, blocked, reason, operator_id=None) → None
  - **Logic**: Append override attempt to logs/phase/phase-overrides.jsonl
  - **Pattern**: Same as log_transition
  - **From**: spec.md FR-007

- [ ] T058 [GREEN] Run HistoryLogger tests - all should pass
  - **Command**: pytest tests/phase/test_history_logger.py -v --cov=src/trading_bot/phase/history_logger
  - **Expected**: All logging tests pass, logs/phase/ files created
  - **Fix**: Adjust HistoryLogger until all tests green

### Integration Test

- [ ] T060 [TDD] Write integration test for full phase progression
  - **File**: tests/phase/test_phase_workflow.py::test_full_phase_progression
  - **Test**: Experience → PoC → Trial → Scaling with real PerformanceTracker and Config
  - **Steps**:
    1. Start in Experience phase
    2. Simulate 20 profitable sessions with 65% win rate
    3. Validate transition to PoC (should succeed)
    4. Advance to PoC
    5. Verify config.json updated
    6. Verify phase-history.jsonl logged
  - **Pattern**: Integration test with real components (no mocks except external APIs)
  - **Coverage**: End-to-end phase transition workflow

- [ ] T061 [GREEN] Run integration test - should pass
  - **Command**: pytest tests/phase/test_phase_workflow.py::test_full_phase_progression -v
  - **Expected**: Full progression test passes
  - **Fix**: Debug integration issues until test passes

---

## Phase 4: US2 [P1] - Trade Limit Enforcement

**Story Goal**: PoC phase enforces 1 trade/day maximum

**Independent Test Criteria**:
- [ ] Place 1 trade in PoC phase → should succeed
- [ ] Attempt 2nd trade same day → should block with countdown message
- [ ] Emergency exit override → should always work regardless of limit

### Tests

- [ ] T070 [P] [TDD] Write tests for TradeLimiter.check_limit
  - **File**: tests/phase/test_trade_limiter.py::TestTradeLimiter::test_check_limit
  - **Tests**:
    - check_limit(Phase.PROOF_OF_CONCEPT) with 0 trades → should pass
    - check_limit(Phase.PROOF_OF_CONCEPT) with 1 trade → should raise TradeLimitExceeded
    - check_limit(Phase.EXPERIENCE) with 10 trades → should pass (no limit)
  - **Pattern**: Exception testing with pytest.raises
  - **Coverage**: All phases, limit reached, limit not reached

- [ ] T071 [P] [TDD] Write tests for TradeLimiter.reset_daily_counter
  - **File**: tests/phase/test_trade_limiter.py::TestTradeLimiter::test_reset_daily_counter
  - **Tests**:
    - reset_daily_counter() at market open → counter resets to 0
    - reset_daily_counter() before market open → counter remains
  - **Mock**: datetime.now() to control time
  - **Coverage**: Reset timing logic

### Implementation

- [ ] T075 [RED] Create TradeLimiter class
  - **File**: src/trading_bot/phase/trade_limiter.py::TradeLimiter
  - **Init**: __init__(config: Config)
  - **Fields**: _trade_counts (Dict[date, int]), _last_reset (datetime)
  - **Pattern**: Service with daily state reset
  - **From**: plan.md [TRADE LIMIT ENFORCEMENT]

- [ ] T076 [RED] Implement TradeLimiter.check_limit
  - **File**: src/trading_bot/phase/trade_limiter.py::TradeLimiter.check_limit
  - **Method**: check_limit(self, phase: Phase, trade_date: date) → None
  - **Logic**:
    1. Get phase config (max_trades_per_day)
    2. Get current count for trade_date
    3. If count >= limit: raise TradeLimitExceeded with countdown
    4. Else: increment counter
  - **REUSE**: Config for phase-specific limits
  - **From**: spec.md FR-003

- [ ] T077 [RED] Implement TradeLimiter.reset_daily_counter
  - **File**: src/trading_bot/phase/trade_limiter.py::TradeLimiter.reset_daily_counter
  - **Method**: reset_daily_counter(self, date: date) → None
  - **Logic**: Clear _trade_counts for dates before date
  - **Trigger**: Called at Config.trading_start_time (7:00 AM EST)
  - **From**: spec.md FR-003

- [ ] T078 [RED] Create TradeLimitExceeded exception
  - **File**: src/trading_bot/phase/trade_limiter.py::TradeLimitExceeded
  - **Init**: __init__(phase, limit, next_allowed)
  - **Message**: "Trade limit exceeded: {limit} trades allowed in {phase} phase. Next trade at: {next_allowed}"
  - **Pattern**: Custom exception with context
  - **From**: contracts/phase-api.yaml Exception Contracts

- [ ] T079 [GREEN] Run TradeLimiter tests - all should pass
  - **Command**: pytest tests/phase/test_trade_limiter.py -v --cov=src/trading_bot/phase/trade_limiter
  - **Expected**: All limit enforcement tests pass
  - **Fix**: Adjust TradeLimiter until all tests green

### Integration with PhaseManager

- [ ] T080 [TDD] Write test for PhaseManager.enforce_trade_limit
  - **File**: tests/phase/test_manager.py::TestPhaseManager::test_enforce_trade_limit
  - **Test**: enforce_trade_limit() calls TradeLimiter.check_limit()
  - **Mock**: TradeLimiter
  - **Coverage**: Integration between PhaseManager and TradeLimiter

- [ ] T081 [RED] Add PhaseManager.enforce_trade_limit method
  - **File**: src/trading_bot/phase/manager.py::PhaseManager.enforce_trade_limit
  - **Method**: enforce_trade_limit(self, phase: Phase, trade_date: date) → None
  - **Logic**: Delegate to TradeLimiter.check_limit()
  - **From**: contracts/phase-api.yaml PhaseManagerProtocol

- [ ] T082 [GREEN] Run PhaseManager limit enforcement test
  - **Command**: pytest tests/phase/test_manager.py::TestPhaseManager::test_enforce_trade_limit -v
  - **Expected**: Test passes
  - **Fix**: Adjust integration if needed

---

## Phase 5: US3 [P1] - Profitability Tracking

**Story Goal**: Track session profitability and validate consistency before phase advancement

**Independent Test Criteria**:
- [ ] Complete 15 sessions with 65% win rate → request phase advance → should approve
- [ ] Complete 15 sessions with 50% win rate → request phase advance → should reject
- [ ] Check progression readiness report → should show current metrics vs requirements

### Tests

- [ ] T090 [P] [TDD] Write tests for session metrics calculation
  - **File**: tests/phase/test_manager.py::TestPhaseManager::test_calculate_session_metrics
  - **Tests**:
    - calculate_session_metrics() returns SessionMetrics with correct win_rate
    - Decimal precision maintained (no float rounding)
    - UTC timestamps used
  - **Mock**: PerformanceTracker.get_summary()
  - **Coverage**: Metrics calculation logic

- [ ] T091 [P] [TDD] Write tests for rolling window validation
  - **File**: tests/phase/test_validators.py::TestRollingWindowValidation
  - **Tests**:
    - validate_rolling_window(10 sessions) uses last 10 sessions only
    - validate_rolling_window(20 sessions) uses last 20 sessions only
    - Edge case: Only 5 sessions available, window requests 10 → uses all 5
  - **Mock**: PerformanceTracker.get_summary()
  - **Coverage**: Window selection logic

### Implementation

- [ ] T095 [RED] Add PhaseManager.calculate_session_metrics method
  - **File**: src/trading_bot/phase/manager.py::PhaseManager.calculate_session_metrics
  - **Method**: calculate_session_metrics(self, session_date: date) → SessionMetrics
  - **Logic**:
    1. Get PerformanceTracker.get_summary(window="daily", start_date=session_date, end_date=session_date)
    2. Map PerformanceSummary fields to SessionMetrics
    3. Return SessionMetrics with Decimal precision
  - **REUSE**: PerformanceTracker (already integrated)
  - **From**: spec.md FR-004

- [ ] T096 [RED] Add rolling window support to validators
  - **File**: src/trading_bot/phase/validators.py (update all validators)
  - **Method**: Update validate() to accept rolling_window parameter
  - **Logic**: Query PerformanceTracker with date range (today - window_days to today)
  - **Pattern**: Time-based filtering
  - **From**: spec.md FR-004 (configurable rolling windows: 10, 20, 50, 100 sessions)

- [ ] T097 [GREEN] Run session metrics tests
  - **Command**: pytest tests/phase/test_manager.py::TestPhaseManager::test_calculate_session_metrics -v
  - **Expected**: Session metrics calculated correctly
  - **Fix**: Adjust calculation logic until tests pass

### Query Support

- [ ] T100 [P] [TDD] Write tests for HistoryLogger.query_transitions
  - **File**: tests/phase/test_history_logger.py::TestHistoryLogger::test_query_transitions
  - **Tests**:
    - query_transitions(start_date, end_date) returns transitions in range
    - Empty date range returns empty list
    - Performance: <500ms for full history
  - **Pattern**: Date range query on JSONL
  - **Coverage**: Query logic, performance

- [ ] T101 [RED] Implement HistoryLogger.query_transitions
  - **File**: src/trading_bot/phase/history_logger.py::HistoryLogger.query_transitions
  - **Method**: query_transitions(self, start_date: date, end_date: date) → List[PhaseTransition]
  - **Logic**:
    1. Read logs/phase/phase-history.jsonl line by line
    2. Parse JSON, filter by timestamp in date range
    3. Return list of PhaseTransition objects
  - **Performance**: Sequential read with date filtering (target <500ms per NFR-001)
  - **From**: contracts/phase-api.yaml HistoryLoggerProtocol

- [ ] T102 [GREEN] Run query tests
  - **Command**: pytest tests/phase/test_history_logger.py::TestHistoryLogger::test_query_transitions -v
  - **Expected**: Query tests pass, performance target met
  - **Fix**: Optimize query if performance issues

---

## Phase 6: US4 [P2] - Position Size Scaling

**Story Goal**: Gradually increase position sizes in Scaling phase based on consistency

**Independent Test Criteria**:
- [ ] 5 consecutive wins in Scaling phase → position size increases by $100
- [ ] 10-session win rate ≥70% → position size increases by $200
- [ ] 3 consecutive losses → position size decreases by 50%

### Tests

- [ ] T110 [P] [TDD] Write tests for PhaseManager.get_position_size
  - **File**: tests/phase/test_manager.py::TestPhaseManager::test_get_position_size
  - **Tests**:
    - get_position_size(Phase.EXPERIENCE) → Decimal("0") (paper trading)
    - get_position_size(Phase.PROOF_OF_CONCEPT) → Decimal("100")
    - get_position_size(Phase.REAL_MONEY_TRIAL) → Decimal("200")
    - get_position_size(Phase.SCALING, consecutive_wins=5) → Decimal("300") (200 + 100)
    - get_position_size(Phase.SCALING, consecutive_wins=10, rolling_win_rate=0.72) → Decimal("500") (200 + 100 + 200)
    - get_position_size(Phase.SCALING, current_size=500, consecutive_losses=3) → Decimal("250") (50% reduction)
  - **Mock**: MetricsCalculator for consistency metrics
  - **Coverage**: All phases, increase triggers, decrease triggers, boundaries

### Implementation

- [ ] T115 [RED] Implement PhaseManager.get_position_size
  - **File**: src/trading_bot/phase/manager.py::PhaseManager.get_position_size
  - **Method**: get_position_size(self, phase: Phase, consistency_metrics: Dict) → Decimal
  - **Logic**:
    - Experience: return Decimal("0")
    - PoC: return Decimal("100")
    - Trial: return Decimal("200")
    - Scaling: Start at 200, +100 per 5 consecutive wins, +200 per 70%+ win rate, max $2,000 or 5% portfolio
  - **REUSE**: MetricsCalculator.calculate_current_streak() for consecutive wins/losses
  - **From**: spec.md FR-005

- [ ] T116 [GREEN] Run position size tests
  - **Command**: pytest tests/phase/test_manager.py::TestPhaseManager::test_get_position_size -v
  - **Expected**: All position size calculations correct
  - **Fix**: Adjust logic until tests pass

---

## Phase 7: US5 [P2] - Automatic Downgrades

**Story Goal**: Automatically downgrade phase when performance degrades

**Independent Test Criteria**:
- [ ] 3 consecutive losses in Trial phase → automatic downgrade to PoC
- [ ] Rolling 20-trade win rate <55% → automatic downgrade
- [ ] Daily loss >5% → automatic downgrade + circuit breaker trip

### Tests

- [ ] T120 [P] [TDD] Write tests for PhaseManager.check_downgrade_triggers
  - **File**: tests/phase/test_manager.py::TestPhaseManager::test_check_downgrade_triggers
  - **Tests**:
    - check_downgrade_triggers(metrics with 3 consecutive losses) → returns Phase.PROOF_OF_CONCEPT (downgrade from Trial)
    - check_downgrade_triggers(metrics with win_rate=0.52) → returns previous phase
    - check_downgrade_triggers(metrics with daily_loss=6%) → returns previous phase + circuit breaker trip
    - check_downgrade_triggers(metrics within thresholds) → returns None (no downgrade)
  - **Mock**: SessionMetrics, CircuitBreaker
  - **Coverage**: All downgrade triggers, circuit breaker integration

### Implementation

- [ ] T125 [RED] Implement PhaseManager.check_downgrade_triggers
  - **File**: src/trading_bot/phase/manager.py::PhaseManager.check_downgrade_triggers
  - **Method**: check_downgrade_triggers(self, metrics: SessionMetrics) → Optional[Phase]
  - **Logic**:
    1. Check consecutive_losses from metrics (via MetricsCalculator.calculate_current_streak())
    2. Check rolling_win_rate <0.55 over last 20 trades
    3. Check daily_loss > 5%
    4. If any trigger: return previous phase (Scaling→Trial, Trial→PoC, PoC→Experience)
    5. If daily loss trigger: also call circuit_breaker.record_failure()
  - **REUSE**: CircuitBreaker (src/trading_bot/error_handling/circuit_breaker.py)
  - **From**: spec.md FR-006

- [ ] T126 [RED] Add automatic downgrade to PhaseManager.advance_phase
  - **File**: src/trading_bot/phase/manager.py::PhaseManager.advance_phase
  - **Logic**: Before advancing, check if downgrade needed. If yes, log downgrade instead of advancement.
  - **Pattern**: Pre-transition validation hook

- [ ] T127 [GREEN] Run downgrade tests
  - **Command**: pytest tests/phase/test_manager.py::TestPhaseManager::test_check_downgrade_triggers -v
  - **Expected**: All downgrade scenarios handled correctly
  - **Fix**: Adjust logic until tests pass

### Integration Test

- [ ] T130 [TDD] Write integration test for automatic downgrade workflow
  - **File**: tests/phase/test_phase_workflow.py::test_automatic_downgrade
  - **Test**:
    1. Start in Trial phase
    2. Simulate 3 consecutive losses
    3. Verify automatic downgrade to PoC
    4. Verify circuit breaker tripped
    5. Verify downgrade logged to phase-history.jsonl
  - **Pattern**: End-to-end downgrade scenario
  - **Coverage**: Full downgrade workflow

- [ ] T131 [GREEN] Run downgrade integration test
  - **Command**: pytest tests/phase/test_phase_workflow.py::test_automatic_downgrade -v
  - **Expected**: Downgrade workflow test passes
  - **Fix**: Debug issues until test passes

---

## Phase 8: US6 [P3] - Export and CLI

**Story Goal**: Export phase history to CSV for manual review

**Independent Test Criteria**:
- [ ] Run `python -m trading_bot.phase export --start 2025-10-01 --end 2025-10-31 --format csv` → generates CSV with phase history
- [ ] CSV includes: session date, phase, trades, win rate, R:R, P&L, position size
- [ ] Export completes in <1 second for full trading history

### Tests

- [ ] T140 [P] [TDD] Write tests for CLI export command
  - **File**: tests/phase/test_cli.py::TestPhaseCLI::test_export_command
  - **Tests**:
    - export_command(format="csv") generates CSV file
    - export_command(format="json") generates JSON file
    - CSV columns match spec requirements
    - Export performance <1 second for 100 transitions
  - **Mock**: HistoryLogger.query_transitions()
  - **Coverage**: CSV export, JSON export, performance

- [ ] T141 [P] [TDD] Write tests for CLI validate command
  - **File**: tests/phase/test_cli.py::TestPhaseCLI::test_validate_command
  - **Tests**:
    - validate_command(to_phase="proof") shows criteria status
    - Displays: session count (20/20), win rate (0.65/0.60), avg R:R (1.6/1.5)
    - Returns exit code 0 if ready, 1 if not ready
  - **Mock**: PhaseManager.validate_transition()
  - **Coverage**: Validation display logic

### Implementation

- [ ] T145 [RED] Create CLI module with argparse
  - **File**: src/trading_bot/phase/cli.py
  - **Commands**: export, validate-transition, status, advance
  - **Pattern**: argparse with subcommands
  - **From**: plan.md [CLI EXPORT TOOL]

- [ ] T146 [RED] Implement export command
  - **File**: src/trading_bot/phase/cli.py::export_command
  - **Args**: --start YYYY-MM-DD, --end YYYY-MM-DD, --format csv|json, --output filename
  - **Logic**:
    1. Query HistoryLogger.query_transitions(start_date, end_date)
    2. Format as CSV or JSON
    3. Write to output file
  - **REUSE**: HistoryLogger (already implemented in T101)
  - **From**: spec.md FR-008

- [ ] T147 [RED] Implement validate-transition command
  - **File**: src/trading_bot/phase/cli.py::validate_command
  - **Args**: --to phase_name
  - **Logic**:
    1. Call PhaseManager.validate_transition(to_phase)
    2. Display ValidationResult in human-readable format
    3. Exit code 0 if can_advance=True, 1 if False
  - **Pattern**: CLI validation wrapper

- [ ] T148 [RED] Implement status command
  - **File**: src/trading_bot/phase/cli.py::status_command
  - **Logic**:
    1. Load Config
    2. Display current phase, days in phase, progression readiness
    3. Show next phase requirements
  - **Pattern**: Status dashboard

- [ ] T149 [RED] Create __main__.py entry point
  - **File**: src/trading_bot/phase/__main__.py
  - **Logic**: if __name__ == "__main__": cli.main()
  - **Pattern**: Python module execution (python -m trading_bot.phase)

- [ ] T150 [GREEN] Run CLI tests
  - **Command**: pytest tests/phase/test_cli.py -v --cov=src/trading_bot/phase/cli
  - **Expected**: All CLI commands work, export performance meets target
  - **Fix**: Adjust CLI implementation until tests pass

---

## Phase 9: Polish & Cross-Cutting Concerns

### Error Handling

- [ ] T160 [P] Add PhaseValidationError exception
  - **File**: src/trading_bot/phase/__init__.py (export from validators.py)
  - **Init**: __init__(validation_result: ValidationResult)
  - **Message**: Format from validation_result.missing_requirements
  - **Pattern**: Custom exception with context
  - **From**: contracts/phase-api.yaml Exception Contracts

- [ ] T161 [P] Add global error logging integration
  - **File**: src/trading_bot/phase/manager.py (all methods)
  - **Logic**: Wrap critical operations in try/except, log to error-log.md
  - **Pattern**: Structured error logging
  - **From**: spec.md error-log.md

### Integration with Existing Systems

- [ ] T165 Integrate PhaseManager with validator.py validation pipeline
  - **File**: src/trading_bot/validator.py
  - **Logic**: Add PhaseManager.enforce_trade_limit() call before risk management checks
  - **Pattern**: Validation chain
  - **From**: plan.md [INTEGRATION SCENARIOS]

- [ ] T166 [P] Integrate phase transitions with ModeSwitcher
  - **File**: src/trading_bot/phase/manager.py::PhaseManager.advance_phase
  - **Logic**: After advancing to PoC/Trial/Scaling, check ModeSwitcher.get_status() for live trading permission
  - **REUSE**: ModeSwitcher (src/trading_bot/mode_switcher.py)
  - **From**: research.md Decision 1

- [ ] T167 [P] Add phase status to dashboard display
  - **File**: src/trading_bot/dashboard/display_renderer.py
  - **Logic**: Display current phase, days in phase, progression readiness
  - **Pattern**: Status widget in dashboard
  - **From**: quickstart.md manual testing scenarios

### Configuration & Documentation

- [ ] T170 [P] Create example phase configuration in config.json
  - **File**: config.json.example
  - **Content**: Full phase_progression configuration with all phases
  - **Pattern**: Example configuration file
  - **From**: quickstart.md Configuration Reference

- [ ] T171 [P] Update NOTES.md with implementation summary
  - **File**: specs/022-pos-scale-progress/NOTES.md
  - **Add**: Phase 4 implementation summary with task completion count
  - **Pattern**: Phase checkpoint documentation

### Smoke Tests

- [ ] T175 [P] Add smoke test for phase system initialization
  - **File**: tests/smoke/test_phase_smoke.py
  - **Test**: Load Config, create PhaseManager, validate current phase loads correctly
  - **Duration**: <5 seconds
  - **Pattern**: tests/smoke/test_trade_logging_smoke.py
  - **From**: plan.md [CI/CD IMPACT]

- [ ] T176 [P] Add smoke test for phase transition
  - **File**: tests/smoke/test_phase_smoke.py::test_phase_transition_smoke
  - **Test**: Create PhaseManager, validate_transition(), check performance <50ms
  - **Duration**: <5 seconds
  - **Coverage**: Critical path only

---

## [TEST GUARDRAILS]

**Speed Requirements**:
- Unit tests: <2s each
- Integration tests: <10s each
- Smoke tests: <5s each
- Full test suite: <2 min total

**Coverage Requirements** (per Constitution v1.0.0 §Code_Quality):
- **New code: 100% coverage** (all lines in src/trading_bot/phase/ must be tested)
- Unit tests: ≥90% line coverage
- Integration tests: ≥80% line coverage
- Modified code: Coverage cannot decrease

**Measurement**:
```bash
pytest tests/phase/ --cov=src/trading_bot/phase --cov-report=term-missing --cov-fail-under=90
```

**Quality Gates**:
- All tests must pass before commit
- Coverage thresholds enforced
- No skipped tests without documented reason

**Clarity Requirements**:
- One behavior per test
- Descriptive names: `test_experience_to_poc_validator_blocks_when_session_count_insufficient()`
- Given-When-Then structure in test body

**TDD Workflow**:
1. **RED**: Write failing test first
2. **GREEN**: Write minimum code to pass test
3. **REFACTOR**: Improve code while keeping tests green

**Anti-Patterns**:
- ❌ NO implementation before tests (violates TDD)
- ❌ NO testing implementation details (test behaviors, not internal state)
- ❌ NO brittle mocks (mock at service boundaries only)

**Examples**:
```python
# ✅ Good: Behavior test
def test_validate_transition_blocks_when_session_count_insufficient():
    # Given: Bot in Experience phase with only 15 sessions
    manager = PhaseManager(config, tracker, logger)
    tracker.get_summary.return_value = SessionMetrics(session_count=15, win_rate=0.65)

    # When: Validate transition to PoC
    result = manager.validate_transition(Phase.PROOF_OF_CONCEPT)

    # Then: Should block with missing session_count
    assert result.can_advance is False
    assert "session_count" in result.missing_requirements

# ❌ Bad: Implementation detail test
def test_validators_dict_contains_experience_to_poc_key():
    assert "experience_to_poc" in manager._validators  # Testing internal dict
```

---

## Summary

**Total Tasks**: 77
- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 13 tasks
- **Phase 3 (US1)**: 22 tasks
- **Phase 4 (US2)**: 13 tasks
- **Phase 5 (US3)**: 13 tasks
- **Phase 6 (US4)**: 7 tasks
- **Phase 7 (US5)**: 12 tasks
- **Phase 8 (US6)**: 11 tasks
- **Phase 9 (Polish)**: 12 tasks

**Parallel Opportunities**: 24 tasks marked [P]
**TDD Tasks**: 35 tasks marked [TDD]
**User Story Tasks**: 58 tasks with [US1]-[US6] labels

**MVP Scope**: Phases 1-5 (US1-US3) = 51 tasks
**Enhancement Scope**: Phases 6-8 (US4-US6) = 30 tasks

**Estimated Effort**:
- MVP (US1-US3): ~28 hours (3.5 days)
- Full feature (US1-US6): ~46 hours (5.75 days)
