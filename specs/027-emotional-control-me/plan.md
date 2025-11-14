# Implementation Plan: Emotional Control Mechanisms

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11+, Decimal precision, file-based storage (JSONL + JSON)
- Components to reuse: 8 (DailyProfitTracker pattern, RiskManager integration, CircuitBreaker, AccountData, logging patterns)
- New components needed: 5 (EmotionalControl tracker, models, config, state file, event logs)
- Pattern: Follow DailyProfitTracker v1.5.0 architecture for consistency

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (existing)
- Financial Calculations: Decimal type (Constitution §Code_Quality)
- State Persistence: JSON files with atomic writes (temp + rename pattern)
- Event Logging: JSONL with daily rotation
- Testing: pytest, pytest-mock (existing)
- Type Checking: mypy --strict (Constitution §Code_Quality)
- Security Scanning: bandit (Constitution §Pre_Commit)

**Patterns**:
- **Tracker Pattern**: EmotionalControl class follows DailyProfitTracker architecture (state management, update_state() method, event logging)
- **Multiplier Pattern**: Position size adjustment via multiplier (0.25 or 1.00) applied to RiskManager calculations
- **Fail-Safe Pattern**: Default to ACTIVE state on corruption (conservative approach per §Safety_First)
- **Atomic Writes**: Temp file + rename for crash-safe persistence
- **Event Sourcing**: JSONL append-only log for audit trail

**Dependencies** (new packages required):
- None - all dependencies already in requirements.txt

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── emotional_control/
│   ├── __init__.py          # Module exports
│   ├── tracker.py           # EmotionalControl class (core logic)
│   ├── models.py            # Data models (State, Event, Config)
│   ├── config.py            # Configuration loader
│   └── cli.py               # CLI commands (status, reset, events, report)
└── tests/
    └── emotional_control/
        ├── __init__.py
        ├── test_tracker.py          # Unit tests for tracker
        ├── test_models.py           # Unit tests for models
        ├── test_integration.py      # Integration with RiskManager
        └── test_performance.py      # Performance benchmarks

logs/
├── emotional_control/
│   ├── state.json                   # Current state (atomic writes)
│   └── events-YYYY-MM-DD.jsonl      # Daily event logs
```

**Module Organization**:
- **tracker.py**: Core orchestration (loss detection, recovery tracking, state persistence, event logging)
- **models.py**: Data classes (EmotionalControlState, EmotionalControlEvent, EmotionalControlConfig)
- **config.py**: Configuration loading from env vars and defaults
- **cli.py**: Command-line interface for status monitoring and manual reset

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 3 (EmotionalControlState, EmotionalControlEvent, EmotionalControlConfig)
- Relationships: Events trace State transitions over time
- Storage: File-based (state.json, events-YYYY-MM-DD.jsonl)
- Migrations required: No (new feature, no schema changes)

**Key Schemas**:
- State: `{is_active, activated_at, trigger_reason, account_balance_at_activation, loss_amount, consecutive_losses, consecutive_wins, last_updated}`
- Event: `{event_id, timestamp, event_type, trigger_reason, account_balance, loss_amount, consecutive_losses, consecutive_wins, admin_id, reset_reason, position_size_multiplier}`

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Position size calculation with emotional control check <10ms (P95)
- NFR-002: State persistence using atomic writes (crash recovery guarantee)
- NFR-004: Unit test coverage ≥90% per Constitution §Testing_Requirements

**Component Benchmarks**:
- `EmotionalControl.update_state()`: <10ms (NFR-001)
- `EmotionalControl.get_position_multiplier()`: <1ms (in-memory lookup)
- State file write (atomic): <10ms (temp + rename)
- Event log append: <5ms (JSONL append)

**Memory Footprint**:
- EmotionalControlState: ~200 bytes
- EmotionalControlConfig: ~150 bytes
- Event log (daily): ~15 KB (50 events × 300 bytes)

---

## [SECURITY]

**Authentication Strategy**:
- CLI commands: OS-level permissions (no separate auth)
- Manual reset: Requires confirmation prompt (prevent accidental resets)
- Admin ID: Captured from env var or CLI arg (audit trail)

**Authorization Model**:
- Single-user bot: No role-based access control
- Manual reset: Confirmation prompt as safeguard

**Input Validation**:
- Account balance: Must be > 0 (Decimal type)
- Loss amount: Must be ≥ 0 (Decimal type)
- Consecutive counters: Must be ≥ 0 (int type)
- Trigger reasons: Enum validation (SINGLE_LOSS, STREAK_LOSS, PROFITABLE_RECOVERY, MANUAL_RESET)
- Event IDs: UUID4 validation

**Data Protection**:
- PII handling: Account balances logged (not sensitive for single-user bot)
- File permissions: State and event files readable by bot user only (chmod 600)
- No encryption required: Local file system, single-user bot

---

## [EXISTING INFRASTRUCTURE - REUSE] (8 components)

**Services/Modules**:
- `src/trading_bot/profit_goal/tracker.py`: DailyProfitTracker pattern (state persistence, JSONL logging, update_state() orchestration)
- `src/trading_bot/risk_management/manager.py`: RiskManager position sizing calculations (integration point for multiplier)
- `src/trading_bot/error_handling/circuit_breaker.py`: CircuitBreaker sliding window pattern (for streak tracking inspiration)
- `src/trading_bot/account/account_data.py`: AccountData balance retrieval (for loss percentage calculation)
- `src/trading_bot/performance/tracker.py`: PerformanceTracker trade outcome tracking (for win/loss streak detection)

**Logging Patterns**:
- JSONL append-only logging (from DailyProfitTracker, RiskManager)
- Daily log rotation pattern (`logs/*/YYYY-MM-DD.jsonl`)
- Decimal serialization (`str(decimal_value)` in JSON)

**Persistence Patterns**:
- Atomic file writes (temp + rename from DailyProfitTracker)
- State file validation on load (handle corruption gracefully)
- Fresh state creation on missing/corrupted file

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

**Backend**:
- `src/trading_bot/emotional_control/tracker.py`: EmotionalControl class (loss detection, position multiplier, state management)
  - Methods: `update_state()`, `get_position_multiplier()`, `reset_manual()`, `_check_activation_trigger()`, `_check_recovery_trigger()`, `_persist_state()`, `_load_state()`, `_log_event()`
  - ~400 LOC (similar to DailyProfitTracker)

- `src/trading_bot/emotional_control/models.py`: Data models
  - EmotionalControlState (dataclass, ~40 LOC)
  - EmotionalControlEvent (dataclass with `create()` factory, ~60 LOC)
  - EmotionalControlConfig (dataclass with `default()` factory, ~50 LOC)

- `src/trading_bot/emotional_control/config.py`: Configuration loader
  - `load_config()` function (reads env vars, applies defaults, ~50 LOC)

- `src/trading_bot/emotional_control/cli.py`: CLI commands
  - Commands: `status`, `reset`, `events`, `report`, `analyze`
  - ~200 LOC total

**File Storage**:
- `logs/emotional_control/state.json`: Current state (atomic writes, <1 KB)
- `logs/emotional_control/events-YYYY-MM-DD.jsonl`: Daily event logs (append-only, ~15 KB/day)

**Tests**:
- `tests/emotional_control/test_tracker.py`: Unit tests for tracker logic (~500 LOC)
- `tests/emotional_control/test_models.py`: Unit tests for data models (~200 LOC)
- `tests/emotional_control/test_integration.py`: Integration with RiskManager (~300 LOC)
- `tests/emotional_control/test_performance.py`: Performance benchmarks (~150 LOC)

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local deployment (Windows/Linux), no cloud infrastructure
- Env vars: `EMOTIONAL_CONTROL_ENABLED` (default: true)
- Breaking changes: No (new feature, opt-in via config)
- Migration: No (file-based storage, auto-created on first run)

**Build Commands**:
- No changes to build process (pure Python module)

**Environment Variables** (update .env.example):
```bash
# Emotional Control Configuration
EMOTIONAL_CONTROL_ENABLED=true  # Enable/disable emotional control safeguards
```

**Database Migrations**:
- No database changes (file-based storage)

**Deployment Steps**:
1. Pull code changes
2. Add `EMOTIONAL_CONTROL_ENABLED=true` to `.env`
3. Create log directory: `mkdir -p logs/emotional_control`
4. Run tests: `pytest tests/emotional_control/ -v`
5. Restart bot: `python -m trading_bot.main --mode paper`
6. Verify: `python -m trading_bot.emotional_control status`

**Smoke Tests**:
- State file creation: Verify `logs/emotional_control/state.json` exists after startup
- Position multiplier: Verify `get_position_multiplier()` returns 1.00 when INACTIVE
- Activation trigger: Simulate loss, verify state changes to ACTIVE
- Recovery trigger: Simulate 3 wins, verify state changes to INACTIVE
- Manual reset: Execute reset command, verify deactivation event logged

**Platform Coupling**:
- None: Pure Python, no platform-specific dependencies

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- State file must survive bot crashes (atomic writes guarantee)
- Event logs must be append-only (no overwrites, audit trail integrity)
- Fail-safe default: Corruption → ACTIVE state (never skip safety check)
- Position size multiplier: Always between 0.25 and 1.00 (no invalid values)

**Staging Smoke Tests**:
```gherkin
Given emotional control is INACTIVE
When a trade loses ≥3% of account balance
Then emotional control activates within 100ms
  And position size multiplier = 0.25
  And activation event logged to JSONL
  And state persisted to state.json

Given emotional control is ACTIVE
When 3 consecutive profitable trades occur
Then emotional control deactivates within 100ms
  And position size multiplier = 1.00
  And deactivation event logged to JSONL
  And state persisted to state.json

Given bot is running with emotional control ACTIVE
When bot is restarted
Then state is restored from state.json
  And position size multiplier remains 0.25
  And startup log confirms ACTIVE state
```

**Rollback Plan**:
- **Immediate**: Set `EMOTIONAL_CONTROL_ENABLED=false` in `.env`, restart bot (position sizing returns to normal)
- **Code Rollback**: `git revert <commit-sha>`, restart bot (state files preserved for analysis)
- **State Reset**: Delete `logs/emotional_control/state.json` to clear persisted state
- **Emergency**: Manual reset via CLI: `python -m trading_bot.emotional_control reset --force`

**Special Considerations**:
- State file corruption: Bot defaults to ACTIVE (fail-safe), manual reset required
- Event log corruption: Bot continues, logs error to stderr, no crash
- PerformanceTracker unavailable: Skip streak detection, log warning

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Initial setup: Create log directory, configure env var, run tests
- Manual testing: Trigger activation/recovery, verify state persistence
- Bot restart: Verify state recovery from file
- Position sizing: Verify multiplier applied to RiskManager calculations
- Monitoring: CLI status command, event log tailing

**Key Integration Points**:
1. **After Trade Execution**: Call `EmotionalControl.update_state(trade_pnl, account_balance, is_win)`
2. **Before Position Planning**: Call `EmotionalControl.get_position_multiplier()` → apply to `PositionPlan.quantity`
3. **Bot Startup**: Call `EmotionalControl.__init__()` → loads state from file
4. **Manual Intervention**: CLI command `emotional_control reset` → deactivates with audit trail

---

## [TESTING STRATEGY]

**Unit Tests** (test_tracker.py):
- Activation triggers: Single loss ≥3%, consecutive loss streak ≥3
- Deactivation triggers: 3 consecutive wins, manual reset
- State persistence: Atomic writes, corruption recovery, fresh state creation
- Event logging: Activation/deactivation events with correct fields
- Edge cases: Zero balance, negative values, missing files

**Integration Tests** (test_integration.py):
- RiskManager integration: Multiplier applied to position size calculations
- AccountData integration: Balance retrieval for loss percentage calculation
- PerformanceTracker integration: Win/loss streak tracking
- CLI commands: Status, reset, events, report

**Performance Tests** (test_performance.py):
- `update_state()` execution time: <10ms (P95) per NFR-001
- `get_position_multiplier()` execution time: <1ms (P95)
- State persistence time: <50ms (P95)
- Event logging time: <5ms (P95)

**Acceptance Criteria Coverage**:
- AC-001 to AC-023: All acceptance criteria from spec.md mapped to test cases
- Coverage target: ≥90% per Constitution §Testing_Requirements

---

## [ERROR HANDLING]

**State File Errors**:
- **Not found**: Create fresh state (INACTIVE, all counters = 0)
- **JSON parse error**: Log warning, create fresh state
- **Missing fields**: Log warning, create fresh state
- **Corrupted**: Default to ACTIVE (fail-safe), alert logged

**Event Log Errors**:
- **Directory missing**: Create directory, log event
- **Write failure**: Log error to stderr, continue operation (don't crash)
- **Disk full**: Log error, continue with in-memory state (graceful degradation)

**Integration Errors**:
- **AccountData unavailable**: Maintain previous state, skip update, log warning
- **PerformanceTracker unavailable**: Skip streak detection, log warning
- **RiskManager failure**: Don't apply multiplier, log error, continue

**Recovery Actions**:
- State corruption → Manual reset required (CLI command with confirmation)
- Event log corruption → Manual review of logs, no automated recovery
- Integration failures → Transient, retry on next update cycle

---

## [OBSERVABILITY]

**Logging**:
- Activation events: WARNING level (important state change)
- Deactivation events: INFO level (recovery success)
- State updates: DEBUG level (frequent operations)
- Errors: ERROR level (with stack trace)

**Metrics** (for future monitoring):
- Activation count (daily, weekly, monthly)
- Average active duration
- Recovery rate (automatic vs manual)
- Position size reduction impact (estimated risk savings)

**Alerts** (for future implementation):
- State file corruption detected (immediate)
- Multiple activations in short period (e.g., 3 in 1 hour - potential strategy issue)
- Long active duration (e.g., >24 hours - may need manual intervention)

**Audit Trail**:
- Event logs: Complete history of activations/deactivations
- Retention: 30 days (configurable)
- Format: JSONL (parseable by jq, Python, analytics tools)

---

## [FUTURE ENHANCEMENTS]

**Out of Scope for v1.0** (from spec.md):
- Configurable thresholds (hardcoded 3% / 3 consecutive for v1.0)
- Graduated recovery (25% → 50% → 75% → 100%)
- Web UI dashboard (CLI only for v1.0)
- Email/SMS alerts (logs only for v1.0)
- Multi-user support (single-user bot)
- Historical analysis (forward-looking only)

**Potential v2.0 Features**:
- Adaptive thresholds based on account size
- Machine learning for optimal recovery timing
- Integration with paper trading mode forcing
- Real-time dashboard with charts
- Mobile app notifications

---

## [RISK MITIGATION]

**Technical Risks**:
- **State file corruption**: Mitigated by atomic writes, fail-safe default
- **Event log disk full**: Mitigated by daily rotation, graceful degradation
- **Performance degradation**: Mitigated by <10ms target, in-memory state cache
- **Integration failures**: Mitigated by error handling, graceful degradation

**Operational Risks**:
- **False positives**: Mitigated by conservative 3% threshold (avoids noise)
- **Trader frustration**: Mitigated by manual reset option, 3-trade recovery
- **Bypassing system**: Mitigated by file integrity checks, audit trail

**Testing Risks**:
- **Incomplete coverage**: Mitigated by 90% coverage target, acceptance criteria mapping
- **Performance regressions**: Mitigated by benchmark tests in CI
- **Edge cases missed**: Mitigated by property-based testing (hypothesis)

---

## [CONSTITUTION ALIGNMENT]

**§Safety_First**:
- ✅ Fail-safe default (corruption → ACTIVE state)
- ✅ Circuit breaker enhancement (reduces position size during risk periods)
- ✅ Audit trail for all state transitions

**§Code_Quality**:
- ✅ Type hints required (mypy --strict)
- ✅ Test coverage ≥90%
- ✅ Single Responsibility Principle (EmotionalControl, models, config separated)
- ✅ DRY principle (reuses DailyProfitTracker patterns)

**§Risk_Management**:
- ✅ Position sizing enforcement (25% reduction during active periods)
- ✅ Validates all inputs (Decimal precision, threshold checks)

**§Testing_Requirements**:
- ✅ Unit tests for all functions
- ✅ Integration tests with RiskManager
- ✅ Performance benchmarks for NFR validation

---

**Next Steps**: Proceed to `/tasks` phase for TDD task breakdown.
