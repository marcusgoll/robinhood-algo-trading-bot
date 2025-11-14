# Research & Discovery: Position Scaling & Phase Progression

## Research Mode
**Full research** - Complex feature with multiple integration points

## Research Decisions

### Decision 1: Extend existing phase configuration system
- **Decision**: Build on top of existing `config.py` phase system and `mode_switcher.py`
- **Rationale**: Foundation already exists - Config.current_phase enum validation and ModeSwitcher phase checks already implemented. Extending proven infrastructure reduces risk and maintains consistency.
- **Alternatives Rejected**:
  - Separate phase management module: Would duplicate logic already in config.py lines 165-166, 221-222, 251-252, 322-328
  - Database-backed phase state: Spec requires JSONL logs only (no DB migration)
- **Source**: src/trading_bot/config.py:165-166, src/trading_bot/mode_switcher.py:87-99

### Decision 2: Reuse PerformanceTracker for profitability validation
- **Decision**: Use existing PerformanceTracker.get_summary() for session metrics (win rate, R:R, P&L)
- **Rationale**: Already calculates all required metrics via MetricsCalculator (src/trading_bot/performance/tracker.py:75-85). Provides rolling windows, caching, and Decimal precision matching FR-004 requirements.
- **Alternatives Rejected**:
  - Build custom metrics calculator: Duplicate functionality, violates DRY principle
  - Direct JSONL parsing: TradeQueryHelper already provides this (tracker.py:35, 73)
- **Source**: src/trading_bot/performance/tracker.py, src/trading_bot/dashboard/metrics_calculator.py

### Decision 3: Extend CircuitBreaker for phase downgrade triggers
- **Decision**: Reuse existing CircuitBreaker class for consecutive loss detection, add phase-specific thresholds
- **Rationale**: CircuitBreaker already tracks consecutive errors in sliding window (error_handling/circuit_breaker.py:54-95). Pattern directly applicable to consecutive loss tracking (FR-006).
- **Alternatives Rejected**:
  - Separate loss tracker: Duplicate sliding window logic
  - Manual loss counting: Less robust, no window cleanup
- **Source**: src/trading_bot/error_handling/circuit_breaker.py:19-99

### Decision 4: JSONL structured logging for phase history
- **Decision**: Follow existing structured logging pattern (structured_logger.py) for phase transitions
- **Rationale**: Consistent with audit trail requirements (§Audit_Everything). Uses Decimal serialization, UTC timestamps, append-only logs matching constitution.
- **Alternatives Rejected**:
  - SQLite database: Spec explicitly requires JSONL (FR-004, FR-008)
  - Plain text logs: Not structured, harder to query
- **Source**: src/trading_bot/logging/structured_logger.py, constitution.md:§Audit_Everything

### Decision 5: Config.json for phase state persistence
- **Decision**: Store current phase in existing config.json structure under phase_progression.current_phase
- **Rationale**: Config.from_env_and_json already loads phase from JSON (config.py:221-222, 251). No new persistence mechanism needed.
- **Alternatives Rejected**:
  - Separate phase_state.json: Unnecessary file proliferation
  - Environment variables: Not suitable for frequently changing state
- **Source**: src/trading_bot/config.py:221-252, tests/fixtures/startup/config.valid.json:3

### Decision 6: Trade limit enforcement via existing validation pipeline
- **Decision**: Add phase-specific trade limits to validator.py validation chain
- **Rationale**: Validator.py already validates trades (§Code_Quality). Phase limit check fits naturally before risk management checks.
- **Alternatives Rejected**:
  - Separate trade limiter service: Violates single responsibility
  - Bot-level enforcement: Too late in execution flow
- **Source**: src/trading_bot/validator.py, spec.md FR-003

---

## Components to Reuse (8 components found)

### Configuration Management
- **src/trading_bot/config.py (Config class)**: Phase enum validation (lines 165-166, 322-328), config.json loading (221-252), dual .env + JSON system
- **src/trading_bot/mode_switcher.py (ModeSwitcher)**: Phase-based paper/live switching (87-99), mode validation, safety banners

### Performance Tracking
- **src/trading_bot/performance/tracker.py (PerformanceTracker)**: Session metrics aggregation, win rate calculation, risk-reward ratios, rolling windows
- **src/trading_bot/performance/models.py (PerformanceSummary)**: Dataclass for metrics with Decimal precision
- **src/trading_bot/dashboard/metrics_calculator.py (MetricsCalculator)**: Core metric calculations (win rate, R:R, streak detection)
- **src/trading_bot/logging/query_helper.py (TradeQueryHelper)**: JSONL trade log ingestion, date range queries

### Safety & Error Handling
- **src/trading_bot/error_handling/circuit_breaker.py (CircuitBreaker)**: Sliding window failure tracking, threshold detection, graceful shutdown
- **src/trading_bot/logging/structured_logger.py**: JSONL structured logging, Decimal serialization, UTC timestamps

---

## New Components Needed (6 components required)

### Phase Management Service
- **src/trading_bot/phase/manager.py (PhaseManager)**: Phase transition validation, profitability gate checks, automatic downgrade logic
  - Responsibilities: Validate phase transitions against FR-002 criteria, trigger downgrades on FR-006 conditions, coordinate with PerformanceTracker for metrics

- **src/trading_bot/phase/models.py**: Phase enum (Experience, ProofOfConcept, RealMoneyTrial, Scaling), SessionMetrics dataclass, PhaseTransition dataclass
  - Aligns with spec.md Key Entities section

### Phase Validators
- **src/trading_bot/phase/validators.py**: Phase transition validators (experience_to_poc, poc_to_trial, trial_to_scaling), downgrade trigger detectors
  - Implements FR-002 profitability gate logic
  - Uses PerformanceTracker.get_summary() for metrics validation

### Trade Limit Enforcement
- **src/trading_bot/phase/trade_limiter.py**: Daily trade counter (resets at market open), limit enforcement for PoC phase (1 trade/day)
  - Implements FR-003 trade limit enforcement
  - Integrates with validator.py validation pipeline

### Phase History Logger
- **src/trading_bot/phase/history_logger.py**: Append-only JSONL logger for phase transitions (logs/phase-history.jsonl), phase transition event serialization
  - Implements FR-004 profitability tracking and FR-007 override logging
  - Follows structured_logger.py patterns

### CLI Export Tool
- **src/trading_bot/phase/cli.py**: CSV export command (python -m trading_bot.phase export), phase history aggregation
  - Implements FR-008 phase history export
  - Follows performance/cli.py patterns

---

## Unknowns & Questions

All technical questions resolved during research:

✅ **Profitability calculation method**: Use PerformanceTracker.get_summary() with configurable rolling windows (10, 20, 50, 100 sessions)

✅ **Phase state persistence**: Store in config.json under phase_progression.current_phase (existing pattern)

✅ **Trade limit reset timing**: Market open (7:00 AM EST) from Config.trading_start_time

✅ **Emergency exit handling**: ModeSwitcher already has force parameter for overrides (mode_switcher.py:115-140)

✅ **Consecutive loss detection**: Extend CircuitBreaker pattern with phase-specific thresholds

✅ **Session definition**: Trading day = market open to close (Config.trading_start_time to trading_end_time)

✅ **Downgrade trigger precedence**: Multiple triggers allowed (3 consecutive losses OR win rate <55% OR daily loss >5%)

✅ **Position size calculation**: Phase-specific logic in phase/manager.py, integrates with risk_management.calculator.py

---

## Integration Strategy

### 1. Configuration Integration
- Extend `config.json` schema to include per-phase configurations (Experience, PoC, Trial, Scaling)
- Add validation in Config.validate() for phase-specific parameters
- Maintain backward compatibility with existing phase_progression.current_phase

### 2. Performance Tracking Integration
- PhaseManager will call PerformanceTracker.get_summary(window="daily", start_date, end_date) for validation
- Reuse MetricsCalculator for win rate, R:R, streak calculations
- No changes needed to performance tracking modules

### 3. Validation Pipeline Integration
- Add PhaseValidator to validator.py validation chain
- Check trade limits BEFORE risk management checks
- Emergency exits bypass phase validations (align with ModeSwitcher.switch_to_live(force=True))

### 4. Logging Integration
- Create logs/phase/ directory alongside existing logs/ structure
- Phase history in logs/phase/phase-history.jsonl
- Override attempts in logs/phase/phase-overrides.jsonl
- Follow structured_logger.py JSONL patterns

### 5. Mode Switcher Integration
- ModeSwitcher already enforces paper trading in Experience phase (mode_switcher.py:95-96)
- PhaseManager will coordinate with ModeSwitcher for live trading permission
- No changes to ModeSwitcher required

---

## Research Metrics

- **Research depth**: 261 lines (this document)
- **Components analyzed**: 8 (Config, ModeSwitcher, PerformanceTracker, CircuitBreaker, MetricsCalculator, etc.)
- **Patterns identified**: Dataclass models, JSONL structured logging, rolling window validation, circuit breaker pattern
- **Integration points**: 5 (configuration, performance tracking, validation pipeline, logging, mode switching)
- **Code reuse**: 57% (8 reusable components / 14 total components)
