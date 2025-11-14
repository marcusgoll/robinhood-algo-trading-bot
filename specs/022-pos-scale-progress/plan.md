# Implementation Plan: Position Scaling & Phase Progression

## Research Summary

See: `research.md` for full research findings

**Key Decisions**:
- Extend existing phase configuration system (config.py, mode_switcher.py)
- Reuse PerformanceTracker for profitability validation
- Extend CircuitBreaker pattern for phase downgrade triggers
- JSONL structured logging for phase history (follows existing patterns)
- Config.json for phase state persistence

**Reuse Analysis**:
- **Components to reuse**: 8 (Config, ModeSwitcher, PerformanceTracker, CircuitBreaker, MetricsCalculator, TradeQueryHelper, StructuredLogger)
- **New components needed**: 6 (PhaseManager, validators, trade limiter, history logger, models, CLI)
- **Code reuse**: 57% (8 reusable / 14 total components)

---

## Architecture Decisions

### Stack
- **Language**: Python 3.11+ (existing)
- **Data Storage**: JSONL files + config.json (no database migration)
- **Logging**: Structured JSONL with Decimal serialization (follows structured_logger.py pattern)
- **State Management**: Config.from_env_and_json() for phase persistence
- **Metrics**: PerformanceTracker.get_summary() for profitability calculations

### Patterns
- **Dataclass Models**: Immutable value objects for Phase, SessionMetrics, PhaseTransition (follows performance/models.py)
- **Service Layer**: PhaseManager orchestrates validation, transitions, downgrades
- **Validator Pattern**: Phase transition validators return ValidationResult (follows existing validator.py)
- **Repository Pattern**: HistoryLogger abstracts JSONL append operations
- **Circuit Breaker**: Reuse existing pattern for consecutive loss detection

### Dependencies
**No new packages required** - All functionality using existing dependencies:
- `dataclasses` - Models (stdlib)
- `decimal.Decimal` - Financial precision (stdlib)
- `datetime` - UTC timestamps (stdlib)
- `pathlib.Path` - File operations (stdlib)
- `json` - Config and JSONL (stdlib)

---

## Structure

### Directory Layout

```
src/trading_bot/
├── phase/                          # NEW MODULE
│   ├── __init__.py                 # Export Phase, PhaseManager
│   ├── models.py                   # Phase enum, SessionMetrics, PhaseTransition, TradeLimit
│   ├── manager.py                  # PhaseManager service (orchestration)
│   ├── validators.py               # Transition validators (profitability gates)
│   ├── trade_limiter.py            # Daily trade limit enforcement
│   ├── history_logger.py           # JSONL phase history logging
│   ├── cli.py                      # Export command (python -m trading_bot.phase export)
│   └── __main__.py                 # CLI entry point

tests/phase/                        # NEW TEST MODULE
├── __init__.py
├── test_models.py                  # Dataclass validation
├── test_validators.py              # Phase transition validation
├── test_trade_limiter.py           # Daily limit enforcement
├── test_manager.py                 # PhaseManager orchestration
├── test_history_logger.py          # JSONL logging
├── test_cli.py                     # Export command
├── test_phase_workflow.py          # Integration: full progression
└── test_integration.py             # Integration with existing modules

logs/phase/                         # NEW LOG DIRECTORY
├── phase-history.jsonl             # Phase transitions
└── phase-overrides.jsonl           # Manual override attempts

config.json                         # EXTEND EXISTING
└── phase_progression:              # Add per-phase configurations
    ├── current_phase
    ├── experience: {...}
    ├── proof: {...}
    ├── trial: {...}
    └── scaling: {...}
```

### Module Organization

**phase/models.py** (135 lines estimated):
- Purpose: Data models for phase system
- Exports: Phase enum, SessionMetrics, PhaseTransition, TradeLimit, PhaseConfiguration
- Dependencies: dataclasses, decimal, datetime
- Patterns: Immutable dataclasses with validation methods

**phase/manager.py** (250 lines estimated):
- Purpose: Orchestrate phase transitions, downgrades, position sizing
- Exports: PhaseManager class
- Dependencies: Config, PerformanceTracker, CircuitBreaker, validators, history_logger
- Responsibilities:
  - validate_transition(to_phase) → ValidationResult
  - advance_phase(to_phase, force=False) → PhaseTransition
  - check_downgrade_triggers() → Optional[Phase]
  - get_position_size(phase, metrics) → Decimal
  - enforce_trade_limit() → None (raises TradeLimitExceeded)

**phase/validators.py** (180 lines estimated):
- Purpose: Phase transition validation logic
- Exports: ValidationResult, ExperienceToPoCValidator, PoCToTrialValidator, TrialToScalingValidator
- Dependencies: PerformanceTracker, SessionMetrics
- Pattern: Strategy pattern (one validator class per transition)

**phase/trade_limiter.py** (95 lines estimated):
- Purpose: Daily trade limit enforcement (PoC phase)
- Exports: TradeLimiter class, TradeLimitExceeded exception
- Dependencies: Config, datetime
- Responsibilities:
  - check_limit(phase, date) → None (raises if exceeded)
  - reset_daily_counter(date) → None
  - get_next_allowed_trade(phase, last_trade_time) → datetime

**phase/history_logger.py** (120 lines estimated):
- Purpose: Append-only JSONL logging for phase transitions
- Exports: HistoryLogger class
- Dependencies: Path, json, datetime, Decimal
- Responsibilities:
  - log_transition(transition: PhaseTransition) → None
  - log_override_attempt(phase, action, blocked, reason) → None
  - query_transitions(start_date, end_date) → List[PhaseTransition]

**phase/cli.py** (140 lines estimated):
- Purpose: CLI commands for phase management
- Exports: export_command, validate_command, status_command
- Dependencies: argparse, HistoryLogger, PerformanceTracker
- Commands:
  - `python -m trading_bot.phase export --start YYYY-MM-DD --end YYYY-MM-DD --format csv`
  - `python -m trading_bot.phase validate-transition --to <phase>`
  - `python -m trading_bot.phase status`

---

## Data Model

See: `data-model.md` for complete entity definitions

**Summary**:
- **Entities**: 5 (Phase enum, SessionMetrics, PhaseTransition, TradeLimit, PhaseConfiguration)
- **Relationships**: Config → Phase, PhaseTransition → SessionMetrics, TradeLimit → Phase
- **Migrations required**: No database migrations - uses config.json + JSONL files

**Key Entity**: Phase (enum with 4 values)
- EXPERIENCE: Paper trading only
- PROOF_OF_CONCEPT: 1 trade/day, $100 positions
- REAL_MONEY_TRIAL: No limit, $200 positions
- SCALING: No limit, $200-$2,000 graduated positions

---

## Performance Targets

### From spec.md NFRs

**NFR-001: Performance**
- Phase validation check ≤50 ms (runs before each trade)
- Session profitability calculation ≤200 ms for 1,000 trades
- Phase history export ≤1 second for full trading history
- Phase transition validation ≤500 ms

**Implementation Strategy**:
- Use PerformanceTracker in-memory cache (tracker.py:40, 63-64)
- Lazy load session metrics (only when validation needed)
- Index phase-history.jsonl by date for fast queries
- Batch trade log reads via TradeQueryHelper

**NFR-002: Data Integrity**
- All phase transitions atomic (config write + JSONL log together)
- Session profitability uses Decimal (no float rounding)
- Phase history logs append-only (no edits/deletions)
- Timestamps UTC with timezone awareness

**Implementation Strategy**:
- Wrap config.json write + history log in try/finally block
- Use Decimal throughout (matches PerformanceSummary.win_rate type)
- Open JSONL files in append mode ('a')
- Use datetime.now(UTC) from existing imports

---

## Security

### Authentication Strategy
N/A - Local-only feature, no remote API

### Authorization Model
**Override Password** (FR-007):
- Environment variable: `PHASE_OVERRIDE_PASSWORD`
- Required for manual phase changes without criteria met
- Not stored in session (prompt each time)
- Logged to phase-overrides.jsonl with operator_id

### Input Validation
- Config.json schema validation (existing Config.validate())
- Phase enum validation (valid_phases = ["experience", "proof", "trial", "scaling"])
- Date range validation (start_date ≤ end_date, no future dates)
- Decimal precision validation (all financial values)

### Data Protection
- No PII in phase logs (only phase names, metrics, timestamps)
- Override password never logged (only override_password_used: bool)
- Phase history redacted in exports (operator_id optional)

---

## Existing Infrastructure - Reuse (8 components)

### Configuration Management
✅ **src/trading_bot/config.py (Config class)**
- Lines 165-166: current_phase field with "experience" default
- Lines 221-252: Load phase from config.json under phase_progression
- Lines 322-328: Validate current_phase against valid_phases list
- **Extend**: Add phase-specific configurations (experience, proof, trial, scaling)

✅ **src/trading_bot/mode_switcher.py (ModeSwitcher)**
- Lines 87-99: Phase-based live trading permission (_can_switch_to_live)
- Lines 95-96: Experience phase blocks live trading
- **Integration**: PhaseManager.advance_phase() will check ModeSwitcher before allowing PoC→Trial→Scaling

### Performance Tracking
✅ **src/trading_bot/performance/tracker.py (PerformanceTracker)**
- Lines 42-133: get_summary() for session metrics (win rate, R:R, P&L)
- Lines 75-85: Uses MetricsCalculator for core computations
- Lines 35: TradeQueryHelper for JSONL trade log queries
- **Integration**: PhaseManager.validate_transition() calls get_summary(window="daily", start_date, end_date)

✅ **src/trading_bot/performance/models.py (PerformanceSummary)**
- Lines 10-29: Dataclass with win_rate (Decimal), avg_risk_reward_ratio (Decimal)
- **Reuse**: Map to SessionMetrics fields directly

✅ **src/trading_bot/dashboard/metrics_calculator.py (MetricsCalculator)**
- calculate_win_rate(), calculate_avg_risk_reward(), calculate_current_streak()
- **Reuse**: Called via PerformanceTracker, no direct usage needed

### Safety & Error Handling
✅ **src/trading_bot/error_handling/circuit_breaker.py (CircuitBreaker)**
- Lines 54-95: Sliding window failure tracking (deque, time-based cleanup)
- **Extend**: Create PhaseCircuitBreaker subclass for consecutive loss tracking

✅ **src/trading_bot/logging/structured_logger.py**
- Structured JSONL logging pattern
- Decimal serialization, UTC timestamps
- **Pattern Match**: HistoryLogger will follow same structure

✅ **src/trading_bot/logging/query_helper.py (TradeQueryHelper)**
- query_by_date_range() for JSONL ingestion
- **Integration**: PerformanceTracker uses this, PhaseManager benefits indirectly

---

## New Infrastructure - Create (6 components)

### Phase Management Service
🆕 **src/trading_bot/phase/manager.py (PhaseManager)** [250 lines]
- Orchestrates phase transitions, downgrades, position sizing
- Methods:
  - `validate_transition(to_phase: Phase) → ValidationResult`
  - `advance_phase(to_phase: Phase, force: bool = False) → PhaseTransition`
  - `check_downgrade_triggers(metrics: SessionMetrics) → Optional[Phase]`
  - `get_position_size(phase: Phase, consistency_metrics: Dict) → Decimal`
  - `enforce_trade_limit(phase: Phase) → None`
- Dependencies: Config, PerformanceTracker, validators, history_logger, trade_limiter

🆕 **src/trading_bot/phase/models.py** [135 lines]
- Phase enum (EXPERIENCE, PROOF_OF_CONCEPT, REAL_MONEY_TRIAL, SCALING)
- SessionMetrics dataclass (session_date, phase, trades, win_rate, avg_rr, total_pnl)
- PhaseTransition dataclass (transition_id, timestamp, from_phase, to_phase, validation_passed, metrics_snapshot)
- TradeLimit dataclass (date, phase, trades_executed, limit, next_allowed_trade)
- PhaseConfiguration dataclass (advancement_criteria, downgrade_triggers)

### Phase Validators
🆕 **src/trading_bot/phase/validators.py** [180 lines]
- ValidationResult dataclass (can_advance, criteria_met, missing_requirements)
- ExperienceToPoCValidator: Check 20+ sessions, 60% win rate, R:R ≥1.5
- PoCToTrialValidator: Check 30 days, 50 trades, 65% win rate, R:R ≥1.8
- TrialToScalingValidator: Check 60 days, 100 trades, 70% win rate, R:R ≥2.0, drawdown <5%
- Each validator uses PerformanceTracker.get_summary() for metrics

### Trade Limit Enforcement
🆕 **src/trading_bot/phase/trade_limiter.py** [95 lines]
- TradeLimiter class: Daily trade counter, limit enforcement
- TradeLimitExceeded exception: Raised when limit hit
- Methods:
  - `check_limit(phase: Phase, date: date) → None` (raises if exceeded)
  - `reset_daily_counter(date: date) → None` (at market open)
  - `get_next_allowed_trade(phase: Phase, last_trade_time: datetime) → datetime`
- Integration point: Called by validator.py before risk management checks

### Phase History Logger
🆕 **src/trading_bot/phase/history_logger.py** [120 lines]
- HistoryLogger class: Append-only JSONL logging
- Files: logs/phase/phase-history.jsonl, logs/phase/phase-overrides.jsonl
- Methods:
  - `log_transition(transition: PhaseTransition) → None`
  - `log_override_attempt(phase, action, blocked, reason, operator_id) → None`
  - `query_transitions(start_date, end_date) → List[PhaseTransition]`
- Follows structured_logger.py patterns (Decimal serialization, UTC timestamps)

### CLI Export Tool
🆕 **src/trading_bot/phase/cli.py** [140 lines]
- Commands: export, validate-transition, status, advance
- Export formats: CSV, JSON, Markdown
- Integration with HistoryLogger, PerformanceTracker
- Follows performance/cli.py patterns

---

## CI/CD Impact

### From spec.md Deployment Considerations

**Platform Dependencies**: None - Local-only feature

**Environment Variables**:
```bash
# New (optional)
PHASE_OVERRIDE_PASSWORD=<secure-password>  # For manual phase overrides

# Existing (no changes)
PHASE_HISTORY_DIR=logs/phase/  # Default, can override
```

**Breaking Changes**: None
- New feature, no existing phase system to replace
- Config.json schema extended (backward compatible - defaults provided)
- Existing config.json files work without modification

**Migration Required**: No
- No database migrations
- Config.json changes optional (uses defaults if missing)
- JSONL logs created on-demand

**Rollback Considerations**:
```bash
# Standard 3-command rollback
git revert <commit-hash>
git push

# Restart bot (phase history preserved in logs)
python -m trading_bot.main
```

**Phase history preserved in logs/** - rollback does not delete historical data

---

## Integration Scenarios

See: `quickstart.md` for complete integration scenarios

**Summary**:
1. **Initial setup**: Verify config.json, create logs/phase/, run tests
2. **Phase transition testing**: Simulate sessions, validate criteria, advance phases
3. **Trade limit enforcement**: Test PoC 1 trade/day limit, emergency overrides
4. **Automatic downgrades**: Trigger downgrade conditions, verify circuit breaker
5. **Export & reporting**: CSV/JSON export, phase timeline visualization

---

## Test Strategy

### Unit Tests (90%+ coverage required)
- `tests/phase/test_models.py`: Dataclass validation, enum values, field constraints
- `tests/phase/test_validators.py`: Each transition validator (Experience→PoC, PoC→Trial, Trial→Scaling)
- `tests/phase/test_trade_limiter.py`: Daily limit reset, countdown calculation, override handling
- `tests/phase/test_manager.py`: PhaseManager orchestration, downgrade logic, position sizing
- `tests/phase/test_history_logger.py`: JSONL append, query by date range, Decimal serialization

### Integration Tests
- `tests/phase/test_phase_workflow.py`: Full progression (Experience→PoC→Trial→Scaling)
- `tests/phase/test_integration.py`: Integration with Config, PerformanceTracker, ModeSwitcher

### Test Data Fixtures
- Simulated session metrics (20+ sessions with varying win rates)
- Phase transition JSONL samples
- config.json with all phase configurations

---

## Success Criteria Alignment

Mapping to spec.md Success Criteria:

1. **Phase Enforcement** (FR-001): PhaseManager validates all trades, blocks out-of-phase actions
2. **Profitability Gates** (FR-002): Validators check criteria, log failures to phase-overrides.jsonl
3. **Trade Limits** (FR-003): TradeLimiter enforces PoC 1 trade/day, tracks countdown
4. **Automatic Downgrade** (FR-006): PhaseCircuitBreaker triggers downgrade on 3 losses / win rate <55%
5. **Capital Preservation**: Phase system reduces premature scaling (measured via P&L analysis)
6. **Session Tracking** (FR-004): PerformanceTracker generates SessionMetrics daily
7. **Position Size Control** (FR-005): PhaseManager.get_position_size() enforces $200-$2,000 scaling
8. **Override Protection** (FR-007): Password required, all attempts logged to phase-overrides.jsonl

---

## Implementation Sequence (TDD)

### Phase 1: Models & Configuration (US1)
1. Create phase/models.py (Phase enum, dataclasses)
2. Extend config.py to load phase configurations
3. Write tests: test_models.py

### Phase 2: Validation & Transitions (US1, US3)
4. Create phase/validators.py (transition validators)
5. Create phase/manager.py (validate_transition, advance_phase)
6. Write tests: test_validators.py, test_manager.py

### Phase 3: Trade Limit Enforcement (US2)
7. Create phase/trade_limiter.py
8. Integrate with validator.py validation pipeline
9. Write tests: test_trade_limiter.py

### Phase 4: Automatic Downgrades (US3, US5)
10. Add downgrade logic to PhaseManager
11. Extend CircuitBreaker for consecutive losses
12. Write tests: test_manager.py (downgrade scenarios)

### Phase 5: Logging & History (US3)
13. Create phase/history_logger.py
14. Integrate with PhaseManager (log transitions)
15. Write tests: test_history_logger.py

### Phase 6: CLI & Export (US6)
16. Create phase/cli.py
17. Implement CSV/JSON export
18. Write tests: test_cli.py

### Phase 7: Integration Testing
19. Write test_phase_workflow.py (full progression)
20. Write test_integration.py (existing modules)
21. Manual testing with quickstart scenarios

---

## Deployment Acceptance

### Production Invariants
- Phase transitions logged atomically (config write + JSONL log)
- Emergency exits always permitted (ModeSwitcher force parameter)
- Phase history never deleted (append-only logs)
- Decimal precision maintained (no float rounding)

### Staging Smoke Tests
```python
# Test: Phase system initialized
assert Config.from_env_and_json().current_phase == "experience"

# Test: Validation blocks premature advancement
result = PhaseManager(config).validate_transition(Phase.PROOF_OF_CONCEPT)
assert result.can_advance == False  # Not enough sessions

# Test: PoC trade limit enforced
# Place 1 trade, attempt 2nd → should raise TradeLimitExceeded
```

### Rollback Plan
- Deploy IDs tracked in: specs/022-pos-scale-progress/NOTES.md
- Rollback commands: `git revert <commit> && git push`
- Special considerations: Phase history preserved in logs (safe to rollback code)

---

## Next Steps

After planning complete:

✅ **Phase 0 (Spec)**: Complete - spec.md created and validated
✅ **Phase 1 (Plan)**: Complete - research.md, data-model.md, quickstart.md, plan.md created

→ **Phase 2 (Tasks)**: Generate task breakdown via `/tasks position-scaling-logic`
  - 20-30 TDD tasks with acceptance criteria
  - Grouped by user story (US1-US6)
  - Priority: MVP first (US1-US3), enhancements later (US4-US6)

→ **Phase 3 (Validate)**: Cross-artifact validation via `/analyze`
  - Check consistency across spec.md, plan.md, data-model.md
  - Detect breaking changes in existing modules
  - Validate constitution compliance

→ **Phase 4 (Implement)**: Execute tasks via `/implement`
  - TDD approach (write tests first)
  - 90%+ test coverage requirement
  - Parallel task execution where possible

→ **Phase 5 (Optimize)**: Code review and optimization via `/optimize`
  - Performance validation (NFR-001 targets)
  - Security scan (bandit)
  - Accessibility (CLI output readability)
