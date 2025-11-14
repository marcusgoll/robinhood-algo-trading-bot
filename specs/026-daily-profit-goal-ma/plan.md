# Implementation Plan: Daily Profit Goal Management

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11+, existing dependencies (robin_stocks, pandas, pytz)
- Components to reuse: 6 (PerformanceTracker, SafetyChecks, StructuredTradeLogger, TradeRecord pattern, Config, dataclass validation)
- New components needed: 5 (models, tracker, logger, config, tests)

**Key Research Decisions**:
1. Reuse PerformanceTracker for P&L aggregation (avoid duplicate logic)
2. Integrate with SafetyChecks circuit breaker pattern for trade blocking
3. Follow TradeRecord dataclass + validation pattern for state model
4. Use file-based JSON persistence following circuit breaker pattern
5. JSONL event logging following StructuredTradeLogger daily rotation
6. Reset at 4:00 AM EST using pytz timezone awareness

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (existing)
- Trading: robin_stocks (existing)
- Data: pandas, pytz (existing)
- Type Safety: mypy --strict (per §Code_Quality)
- Testing: pytest, pytest-mock (existing)

**Patterns**:
- **Dataclass + Validation**: Models use @dataclass with `__post_init__` validation (TradeRecord pattern)
- **Dependency Injection**: DailyProfitTracker receives PerformanceTracker, config (testability)
- **Circuit Breaker Extension**: Profit protection as additional circuit breaker condition in SafetyChecks
- **File-Based State**: JSON for state persistence, JSONL for event audit trail
- **Fail-Safe Design**: Protection mode blocks new entries but allows exits (§Safety_First)

**Dependencies** (no new packages required):
- All dependencies already installed (robin_stocks, pandas, pytz, pytest)

---

## [STRUCTURE]

**Directory Layout** (follows existing patterns):

```
src/trading_bot/profit_goal/
├── __init__.py
├── models.py           # ProfitGoalConfig, DailyProfitState, ProfitProtectionEvent
├── tracker.py          # DailyProfitTracker (main orchestrator)
├── logger.py           # ProfitProtectionLogger (JSONL event logging)
└── config.py           # Configuration loading from .env/config.json

tests/unit/profit_goal/
├── __init__.py
├── test_models.py      # Dataclass validation tests
├── test_tracker.py     # Core logic tests
├── test_logger.py      # Logging tests
└── test_config.py      # Configuration loading tests

logs/
├── profit-goal-state.json          # Runtime state (single file)
└── profit-protection/              # Event audit trail (daily JSONL)
    ├── 2025-10-21.jsonl
    └── ...
```

**Module Organization**:
- `profit_goal/models.py`: Data structures (config, state, events) with validation
- `profit_goal/tracker.py`: Core business logic (P&L tracking, protection triggers, reset)
- `profit_goal/logger.py`: Event logging infrastructure (JSONL daily rotation)
- `profit_goal/config.py`: Configuration loading and validation
- Integration point: `safety_checks.py` (add profit protection check to `validate_trade()`)

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 3 (ProfitGoalConfig, DailyProfitState, ProfitProtectionEvent)
- Relationships: State calculated from TradeRecord, controls SafetyChecks
- Migrations required: No (file-based persistence)

**Key Dataclasses**:
- ProfitGoalConfig: target (Decimal), threshold (Decimal), enabled (bool)
- DailyProfitState: 8 fields tracking session P&L and protection status
- ProfitProtectionEvent: 8 fields for audit trail logging

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: P&L calculation <100ms per update (leveraging PerformanceTracker's existing optimization)
- NFR-002: State persistence survives bot crashes (file-based with atomic writes)
- NFR-003: Decimal precision for all monetary values (no floating-point errors)

**Lighthouse Targets**: Not applicable (no UI, backend-only feature)

**Benchmarks**:
- State update latency: <100ms (target from NFR-001)
- State persistence: <10ms (JSON write with buffering)
- Event logging: <5ms (JSONL append, following StructuredTradeLogger pattern)

---

## [SECURITY]

**Authentication Strategy**: Not applicable (local module, no auth surface)

**Authorization Model**: Not applicable (single-user bot)

**Input Validation**:
- Configuration: Pydantic-style validation in `__post_init__` (target range $0-$10,000, threshold 10%-90%)
- State fields: Type hints + validation (Decimal for money, str for timestamps)
- Event fields: Validated before JSONL write

**Rate Limiting**: Not applicable (internal module)

**Data Protection**:
- PII handling: No PII stored (only monetary values and timestamps)
- Encryption: Not required (local files, no sensitive data beyond trade amounts)
- File permissions: Standard OS permissions (logs/ directory)

---

## [EXISTING INFRASTRUCTURE - REUSE] (6 components)

**Services/Modules**:
- `src/trading_bot/performance/tracker.py:PerformanceTracker` - Daily P&L aggregation (realized + unrealized)
  - Methods: `get_summary()`, delegates to `MetricsCalculator.calculate_total_pl()`
  - Usage: Query current daily P&L to update profit goal state
- `src/trading_bot/safety_checks.py:SafetyChecks` - Circuit breaker pattern for trade validation
  - Method: `validate_trade()` - Add profit protection check as new validation rule
  - Pattern: Fail-safe design (any failure blocks trade)
- `src/trading_bot/logging/structured_logger.py:StructuredTradeLogger` - Daily JSONL logging pattern
  - Pattern: Thread-safe writes, daily file rotation, <5ms latency
  - Usage: Adapt pattern for profit protection event logging
- `src/trading_bot/logging/trade_record.py:TradeRecord` - Dataclass + validation pattern
  - Pattern: `@dataclass` with `__post_init__` validation, Decimal fields, JSON serialization
  - Usage: Follow same pattern for DailyProfitState and ProfitProtectionEvent

**Configuration**:
- `src/trading_bot/config.py:Config` - Dual config system (.env + config.json)
  - Pattern: Load from environment variables or JSON file
  - Usage: Extend to load PROFIT_TARGET_DAILY and PROFIT_GIVEBACK_THRESHOLD

**Data Models**:
- `src/trading_bot/performance/models.py:PerformanceSummary` - Dataclass with Decimal fields
  - Pattern: Decimal for monetary values, datetime for timestamps
  - Usage: Follow same pattern for profit goal models

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

**Core Module** (`src/trading_bot/profit_goal/`):

1. **models.py** - Data structures
   - `ProfitGoalConfig` dataclass (target, threshold, enabled)
   - `DailyProfitState` dataclass (8 fields: session_date, daily_pnl, realized_pnl, unrealized_pnl, peak_profit, protection_active, last_reset, last_updated)
   - `ProfitProtectionEvent` dataclass (8 fields: event_id, timestamp, session_date, peak_profit, current_profit, drawdown_percent, threshold, session_id)
   - Each with `__post_init__` validation following TradeRecord pattern

2. **tracker.py** - Core orchestrator
   - `DailyProfitTracker` class
   - Methods:
     - `__init__(config, performance_tracker)` - Dependency injection
     - `update_state() -> DailyProfitState` - Fetch P&L, update peak, check threshold
     - `get_current_state() -> DailyProfitState` - Read state without update
     - `reset_daily_state() -> None` - Reset at market open (4:00 AM EST)
     - `is_protection_active() -> bool` - Query protection status
     - `_persist_state()` - Save state to logs/profit-goal-state.json
     - `_load_state()` - Load state from file (crash recovery)

3. **logger.py** - Event logging
   - `ProfitProtectionLogger` class
   - Methods:
     - `__init__(log_dir)` - Initialize with directory
     - `log_event(event: ProfitProtectionEvent)` - Write to JSONL
     - `_get_daily_file_path()` - Daily rotation (YYYY-MM-DD.jsonl)
   - Pattern: Thread-safe, daily rotation, following StructuredTradeLogger

4. **config.py** - Configuration management
   - `load_profit_goal_config() -> ProfitGoalConfig` - Load from .env or config.json
   - Default values: target=$0 (disabled), threshold=0.50 (50%)
   - Validation: target $0-$10,000, threshold 10%-90%

**Integration**:

5. **Modify** `src/trading_bot/safety_checks.py`:
   - Add optional `profit_tracker: DailyProfitTracker | None` parameter to `validate_trade()`
   - Add profit protection check:
     ```python
     if profit_tracker and action == "BUY":
         if profit_tracker.is_protection_active():
             return SafetyResult(
                 is_safe=False,
                 reason="Profit protection active - new entries blocked"
             )
     ```

**Tests** (`tests/unit/profit_goal/`):
- `test_models.py` - Dataclass validation (valid/invalid inputs)
- `test_tracker.py` - Core logic (P&L updates, peak tracking, protection triggers, reset)
- `test_logger.py` - Event logging (JSONL format, daily rotation, thread safety)
- `test_config.py` - Configuration loading (env vars, config.json, defaults)
- Target: ≥90% coverage per §Testing_Requirements

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: None (local-only feature, no Railway/Vercel changes)
- Env vars: Optional (PROFIT_TARGET_DAILY, PROFIT_GIVEBACK_THRESHOLD with defaults)
- Breaking changes: No (feature is opt-in, disabled by default)
- Migration: No (file-based persistence, starts fresh)

**Build Commands**: No changes (Python module, no build step)

**Environment Variables** (optional, not required):
- New optional:
  - `PROFIT_TARGET_DAILY` (default: "0" = disabled)
  - `PROFIT_GIVEBACK_THRESHOLD` (default: "0.50" = 50%)
- No schema update required (optional config, graceful defaults)

**Database Migrations**: None (file-based persistence)

**Smoke Tests**: Not applicable (no deployment, local-only feature)

**Platform Coupling**: None (pure Python module, no platform dependencies)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- Feature disabled by default (target=$0) - no behavior change for existing users
- State file corruption does not crash bot (graceful fallback to fresh state)
- Protection mode never blocks exits (only new entries per FR-007)
- Daily reset at 4:00 AM EST regardless of bot restart timing

**Manual Testing Checklist**:
```gherkin
Given bot configured with PROFIT_TARGET_DAILY=500 and PROFIT_GIVEBACK_THRESHOLD=0.50
When daily profit reaches $600 (peak)
  And profit drops to $300 (50% drawdown)
Then profit protection triggers
  And protection event logged to JSONL
  And state file updated (protection_active=true)
  And new BUY orders blocked by SafetyChecks
  And existing positions can still be exited

Given protection active
When market opens next day (4:00 AM EST)
Then state resets (daily_pnl=0, peak=0, protection=false)
  And new trading session begins fresh

Given bot crashes during trading session
When bot restarts
Then state reloaded from logs/profit-goal-state.json
  And protection status preserved
  And peak profit preserved
```

**Rollback Plan**:
- Deploy IDs: Not applicable (no deployment, local feature)
- Rollback: 3-command rollback (delete module, remove config, restart bot)
- Special considerations: State file deleted during rollback (no migration needed)

**Artifact Strategy**: Not applicable (no build artifacts, Python source only)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Initial setup: Configure env vars, no migrations needed
- Validation: pytest + mypy for quality gates
- Manual testing: Profit protection trigger, trade blocking, daily reset
- Monitoring: Query JSONL logs, check state file
- Troubleshooting: Validate config, verify state, manual reset procedures

---

## [RISK MITIGATION]

**Risk 1: State file corruption during bot crash**
- Mitigation: Atomic writes with temporary file + rename
- Fallback: If JSON invalid, initialize fresh state (log warning)
- Testing: Kill bot mid-write, verify state recovery

**Risk 2: P&L calculation drift between PerformanceTracker and profit goal**
- Mitigation: Single source of truth (PerformanceTracker), profit goal reads not calculates
- Testing: Compare values, assert consistency within 0.01

**Risk 3: Timezone issues with market open detection**
- Mitigation: Use pytz for Eastern timezone, UTC for all file timestamps
- Testing: Test reset at DST boundaries (March/November)

**Risk 4: Protection triggers on small profits (false positives)**
- Mitigation: Only trigger if peak_profit > threshold * target (e.g., >$250 for $500 target)
- Testing: Verify no triggers when profit below meaningful threshold

**Risk 5: Race condition with concurrent state updates**
- Mitigation: Single-threaded bot design (no concurrency expected)
- Backup: File locking if concurrency added later
- Testing: Unit tests only (integration tests would require threading)

---

## [QUALITY GATES]

Before marking `/plan` complete:
- ✅ All research questions resolved (no unknowns in research.md)
- ✅ Constitution alignment verified (§Risk_Management, §Safety_First, §Audit_Everything)
- ✅ Reuse analysis complete (6 components identified)
- ✅ Architecture decisions documented with rationale
- ✅ Data model defined with validation rules
- ✅ Integration points identified (SafetyChecks extension)
- ✅ No new dependencies required
- ✅ Risk mitigation strategies defined

Next: `/tasks` (generate TDD tasks from this plan)
