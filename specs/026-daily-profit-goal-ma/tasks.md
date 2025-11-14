# Tasks: Daily Profit Goal Management

## [CODEBASE REUSE ANALYSIS]
Scanned: src/trading_bot/**/*.py, tests/unit/**/*.py

[EXISTING - REUSE]
- ✅ PerformanceTracker (src/trading_bot/performance/tracker.py)
- ✅ SafetyChecks (src/trading_bot/safety_checks.py)
- ✅ StructuredTradeLogger (src/trading_bot/logging/structured_logger.py)
- ✅ TradeRecord dataclass pattern (src/trading_bot/logging/trade_record.py)
- ✅ Config dual loading (src/trading_bot/config.py)
- ✅ PerformanceSummary models (src/trading_bot/performance/models.py)

[NEW - CREATE]
- 🆕 ProfitGoalConfig dataclass (no existing profit goal config)
- 🆕 DailyProfitState dataclass (no existing profit state tracking)
- 🆕 ProfitProtectionEvent dataclass (no existing protection events)
- 🆕 DailyProfitTracker service (no existing profit tracking orchestrator)
- 🆕 ProfitProtectionLogger (new JSONL logger for protection events)

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 1: Setup (non-blocking infrastructure)
2. Phase 2: Foundational (blocks all stories - core models and config)
3. Phase 3: US1 [P1] - Configure daily profit target (independent)
4. Phase 4: US2 [P1] - Track daily P&L (depends on US1 config)
5. Phase 5: US3 [P1] - Detect profit giveback (depends on US2 tracking)
6. Phase 6: Polish & Integration (depends on US1-US3)

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 2: T005, T006, T007 (different model files, no dependencies)
- Phase 3: T011, T012 (config tests can run in parallel)
- Phase 4: T015, T016 (tracker tests for different aspects)
- Phase 5: T020, T021, T022 (logger and integration tests)
- Phase 6: T030, T031, T032 (polish tasks in different files)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phases 3-5 (US1-US3 only - core profit protection logic)
**Incremental delivery**: US1 → US2 → US3 → staging validation
**Testing approach**: TDD required (≥90% coverage per spec.md NFR-005)

---

## Phase 1: Setup

- [ ] T001 Create profit_goal module structure per plan.md
  - Directories: src/trading_bot/profit_goal/, tests/unit/profit_goal/
  - Files: __init__.py in each directory
  - Pattern: src/trading_bot/performance/ structure
  - From: plan.md [STRUCTURE]

- [ ] T002 Create logs directory structure for profit goal state and events
  - Directories: logs/profit-protection/
  - Files: .gitkeep in logs/profit-protection/
  - Pattern: logs/trades/ structure
  - From: plan.md [STRUCTURE]

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Core data models and configuration infrastructure that blocks all user stories

- [ ] T005 [P] Create ProfitGoalConfig dataclass in src/trading_bot/profit_goal/models.py
  - Fields: target (Decimal), threshold (Decimal), enabled (bool)
  - Validation: target $0-$10,000, threshold 0.10-0.90
  - REUSE: TradeRecord pattern (src/trading_bot/logging/trade_record.py)
  - Pattern: src/trading_bot/performance/models.py:PerformanceSummary
  - From: data-model.md ProfitGoalConfig entity

- [ ] T006 [P] Create DailyProfitState dataclass in src/trading_bot/profit_goal/models.py
  - Fields: session_date, daily_pnl, realized_pnl, unrealized_pnl, peak_profit, protection_active, last_reset, last_updated
  - Validation: peak_profit ≥ daily_pnl, valid ISO timestamps
  - REUSE: TradeRecord pattern with __post_init__ validation
  - Pattern: src/trading_bot/performance/models.py
  - From: data-model.md DailyProfitState entity

- [ ] T007 [P] Create ProfitProtectionEvent dataclass in src/trading_bot/profit_goal/models.py
  - Fields: event_id, timestamp, session_date, peak_profit, current_profit, drawdown_percent, threshold, session_id
  - Validation: peak_profit > 0, current_profit < peak_profit, drawdown_percent ≥ threshold
  - REUSE: TradeRecord pattern
  - Pattern: src/trading_bot/logging/trade_record.py
  - From: data-model.md ProfitProtectionEvent entity

- [ ] T008 Create configuration loader in src/trading_bot/profit_goal/config.py
  - Function: load_profit_goal_config() -> ProfitGoalConfig
  - Sources: PROFIT_TARGET_DAILY, PROFIT_GIVEBACK_THRESHOLD env vars
  - Defaults: target=$0 (disabled), threshold=0.50 (50%)
  - REUSE: Config dual loading pattern (src/trading_bot/config.py)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

---

## Phase 3: User Story 1 [P1] - User can set daily profit target

**Story Goal**: Trader configures daily profit target so system knows achievement goal

**Independent Test Criteria**:
- [ ] User configures target to $300, verify config loads correctly
- [ ] Restart bot and verify target persistence (from env vars)
- [ ] Invalid targets (negative, >$10k) are rejected with validation error

### Tests

- [ ] T011 [P] [US1] Write test: ProfitGoalConfig validates target range in tests/unit/profit_goal/test_models.py
  - Test cases: valid ($0, $500, $10000), invalid (negative, $10001, non-decimal)
  - Given-When-Then structure
  - Pattern: tests/unit/test_trade_record.py
  - Coverage: ≥90% for ProfitGoalConfig validation

- [ ] T012 [P] [US1] Write test: load_profit_goal_config loads from env vars in tests/unit/profit_goal/test_config.py
  - Test cases: env vars set, env vars missing (defaults), invalid values
  - Mock: os.environ
  - Pattern: tests/unit/test_config.py
  - Coverage: ≥90% for config loading

### Implementation

- [ ] T013 [US1] Implement ProfitGoalConfig validation in __post_init__
  - Logic: Raise ValueError if target < 0 or target > 10000
  - Logic: Raise ValueError if threshold < 0.10 or threshold > 0.90
  - Logic: Set enabled = (target > 0)
  - From: spec.md FR-010, data-model.md validation rules

- [ ] T014 [US1] Implement load_profit_goal_config function
  - Logic: Read PROFIT_TARGET_DAILY env var (default "0")
  - Logic: Read PROFIT_GIVEBACK_THRESHOLD env var (default "0.50")
  - Logic: Convert to Decimal, create ProfitGoalConfig
  - Error handling: Invalid values → log warning, use defaults
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] config.py

---

## Phase 4: User Story 2 [P1] - System tracks daily P&L

**Story Goal**: System tracks realized and unrealized P&L to know progress toward goal

**Independent Test Criteria**:
- [ ] Execute 2 trades (1 closed winner +$100, 1 open position +$50)
- [ ] Verify daily_pnl = $150 (realized + unrealized)
- [ ] Verify peak_profit = $150 (high-water mark)

### Tests

- [ ] T015 [P] [US2] Write test: DailyProfitState tracks peak profit correctly in tests/unit/profit_goal/test_tracker.py
  - Test cases: P&L increases (peak follows), P&L decreases (peak stays), reset (peak to 0)
  - Given-When-Then structure
  - Pattern: tests/unit/test_safety_checks.py
  - Coverage: ≥90% for peak tracking logic

- [ ] T016 [P] [US2] Write test: DailyProfitTracker updates state from PerformanceTracker in tests/unit/profit_goal/test_tracker.py
  - Test cases: update with positive P&L, update with negative P&L, no positions
  - Mock: PerformanceTracker.get_summary()
  - Pattern: tests/unit/test_safety_checks.py
  - Coverage: ≥90% for state update logic

- [ ] T017 [US2] Write test: DailyProfitState persists to JSON file in tests/unit/profit_goal/test_tracker.py
  - Test cases: save state, load state, file not found (defaults), corrupted JSON (fallback)
  - Mock: file I/O operations
  - Pattern: tests/unit/test_error_handling/test_circuit_breaker.py (state persistence)
  - Coverage: ≥90% for persistence logic

### Implementation

- [ ] T018 [US2] Create DailyProfitTracker class in src/trading_bot/profit_goal/tracker.py
  - Methods: __init__(config, performance_tracker), update_state(), get_current_state(), is_protection_active()
  - REUSE: PerformanceTracker (src/trading_bot/performance/tracker.py)
  - Pattern: src/trading_bot/safety_checks.py (validation orchestrator)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] tracker.py

- [ ] T019 [US2] Implement update_state method in DailyProfitTracker
  - Logic: Call performance_tracker.get_summary() to get current P&L
  - Logic: Update daily_pnl, realized_pnl, unrealized_pnl from summary
  - Logic: Update peak_profit = max(peak_profit, daily_pnl)
  - Logic: Set last_updated timestamp (UTC)
  - Logic: Call _persist_state() to save
  - From: spec.md FR-002, FR-003

- [ ] T020 [US2] Implement state persistence methods in DailyProfitTracker
  - Method: _persist_state() - Write state to logs/profit-goal-state.json
  - Method: _load_state() - Read state from JSON (fallback to fresh state)
  - Logic: Atomic writes (temp file + rename)
  - Error handling: JSON parse error → log warning, return fresh state
  - REUSE: File I/O patterns from existing modules
  - From: spec.md NFR-002, plan.md [RISK MITIGATION] risk 1

---

## Phase 5: User Story 3 [P1] - Detect profit giveback

**Story Goal**: System detects when trader has given back 50% of daily profit

**Independent Test Criteria**:
- [ ] Simulate peak profit $600, drop current profit to $300
- [ ] Verify protection triggers (protection_active = true)
- [ ] Attempt new trade and verify blocked by SafetyChecks
- [ ] Verify protection event logged to JSONL

### Tests

- [ ] T021 [P] [US3] Write test: DailyProfitTracker detects 50% drawdown in tests/unit/profit_goal/test_tracker.py
  - Test cases: drawdown at threshold (trigger), below threshold (no trigger), peak < target (no trigger)
  - Given-When-Then structure
  - Pattern: tests/unit/test_safety_checks.py
  - Coverage: ≥90% for protection trigger logic

- [ ] T022 [P] [US3] Write test: SafetyChecks blocks trades when protection active in tests/unit/test_safety_checks.py
  - Test cases: protection active + BUY (blocked), protection active + SELL (allowed), protection inactive (allowed)
  - Mock: DailyProfitTracker.is_protection_active()
  - Pattern: tests/unit/test_safety_checks.py existing tests
  - Coverage: Extend existing SafetyChecks coverage

- [ ] T023 [P] [US3] Write test: ProfitProtectionLogger writes JSONL events in tests/unit/profit_goal/test_logger.py
  - Test cases: log event, daily file rotation, thread safety
  - Mock: file operations
  - Pattern: tests/unit/test_structured_logger.py
  - Coverage: ≥90% for logger

### Implementation

- [ ] T024 [US3] Implement drawdown detection in DailyProfitTracker.update_state
  - Logic: Calculate drawdown_percent = (peak_profit - daily_pnl) / peak_profit
  - Logic: If drawdown_percent ≥ threshold AND peak_profit > 0, set protection_active = true
  - Logic: If protection triggers, create ProfitProtectionEvent and log it
  - From: spec.md FR-004, FR-005

- [ ] T025 [US3] Create ProfitProtectionLogger class in src/trading_bot/profit_goal/logger.py
  - Methods: __init__(log_dir), log_event(event), _get_daily_file_path()
  - REUSE: StructuredTradeLogger pattern (src/trading_bot/logging/structured_logger.py)
  - Pattern: src/trading_bot/logging/structured_logger.py (JSONL daily rotation)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] logger.py

- [ ] T026 [US3] Implement log_event method in ProfitProtectionLogger
  - Logic: Convert ProfitProtectionEvent to JSON
  - Logic: Append to logs/profit-protection/YYYY-MM-DD.jsonl
  - Logic: Thread-safe writes (file locking or single-threaded assumption)
  - Error handling: File write failure → log to stderr, don't crash
  - From: spec.md FR-009, plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T027 [US3] Integrate profit protection check into SafetyChecks.validate_trade
  - Logic: Add optional profit_tracker parameter to validate_trade()
  - Logic: If profit_tracker exists and action == "BUY", check is_protection_active()
  - Logic: If protection active, return SafetyResult(is_safe=False, reason="Profit protection active")
  - Logic: Allow SELL actions even when protection active (FR-007)
  - REUSE: SafetyChecks pattern (src/trading_bot/safety_checks.py)
  - From: spec.md FR-006, FR-007, plan.md [NEW INFRASTRUCTURE - CREATE] integration

---

## Phase 6: Polish & Cross-Cutting Concerns

### Daily Reset

- [ ] T030 [P] Write test: DailyProfitTracker resets state at market open (4:00 AM EST) in tests/unit/profit_goal/test_tracker.py
  - Test cases: reset at 4:00 AM EST, no reset at other times, DST boundary handling
  - Mock: datetime.now() with pytz Eastern timezone
  - Pattern: tests/unit/utils/test_time_utils_market_hours.py
  - Coverage: ≥90% for reset logic

- [ ] T031 Implement reset_daily_state method in DailyProfitTracker
  - Logic: Reset daily_pnl, realized_pnl, unrealized_pnl, peak_profit to 0
  - Logic: Set protection_active = false
  - Logic: Update session_date to current date
  - Logic: Set last_reset timestamp (UTC)
  - Logic: Persist state to file
  - From: spec.md FR-008

- [ ] T032 Implement market open detection in DailyProfitTracker
  - Logic: Check if current time is 4:00 AM EST (pytz timezone aware)
  - Logic: Compare session_date to current date (trigger reset if different)
  - Logic: Call reset_daily_state() when market open detected
  - REUSE: pytz for Eastern timezone with DST handling
  - From: spec.md assumptions, plan.md [RISK MITIGATION] risk 3

### Error Handling & Resilience

- [ ] T035 [P] Add comprehensive error handling to DailyProfitTracker
  - Logic: Wrap PerformanceTracker calls in try/except (log error, return previous state)
  - Logic: Validate all Decimal operations (catch InvalidOperation)
  - Logic: Log all state transitions with reasoning (audit trail)
  - Pattern: src/trading_bot/safety_checks.py error handling
  - From: spec.md NFR-004, plan.md [RISK MITIGATION]

- [ ] T036 [P] Add state file corruption recovery in _load_state
  - Logic: If JSON parse fails, log warning and return fresh state
  - Logic: If file not found, create new state with defaults
  - Logic: Validate loaded state (all required fields present)
  - Pattern: Circuit breaker state recovery patterns
  - From: spec.md NFR-002, plan.md [RISK MITIGATION] risk 1

### Type Safety & Documentation

- [ ] T040 [P] Add comprehensive type hints to all profit_goal modules
  - Files: models.py, tracker.py, logger.py, config.py
  - Tools: mypy --strict compliant
  - Pattern: Existing modules with strict type hints
  - From: spec.md NFR-006

- [ ] T041 [P] Add docstrings to all public methods and classes
  - Format: Google-style docstrings with Args, Returns, Raises
  - Coverage: All public APIs documented
  - Pattern: src/trading_bot/performance/tracker.py docstrings
  - From: §Code_Quality constitution

### Integration Testing

- [ ] T045 Write integration test: Full profit protection workflow in tests/unit/profit_goal/test_integration.py
  - Test: Configure target $500, execute trades to $600 profit, drop to $300, verify protection triggers and blocks trades
  - Real components: DailyProfitTracker, ProfitProtectionLogger, SafetyChecks integration
  - Mock: PerformanceTracker.get_summary() to simulate P&L changes
  - Pattern: tests/unit/test_bot.py integration patterns
  - Coverage: E2E workflow validation

- [ ] T046 Write integration test: State persistence across bot restart in tests/unit/profit_goal/test_integration.py
  - Test: Save state with protection active, create new tracker instance, verify state loaded correctly
  - Real components: File I/O, state serialization
  - Pattern: Circuit breaker persistence tests
  - Coverage: Crash recovery scenario

- [ ] T047 Write integration test: Daily reset at market open in tests/unit/profit_goal/test_integration.py
  - Test: Simulate market open time (4:00 AM EST), verify state resets, verify new session begins fresh
  - Mock: datetime.now() to simulate time progression
  - Pattern: Time-based tests in test_time_utils_market_hours.py
  - Coverage: Daily reset workflow

### Documentation & Deployment

- [ ] T050 Document rollback procedure in NOTES.md
  - Content: 3-command rollback (delete module files, remove config vars, restart bot)
  - Content: State file cleanup instructions
  - Content: Verification steps (check logs, verify no protection triggers)
  - From: spec.md rollback considerations

- [ ] T051 Add usage examples to profit_goal/__init__.py docstring
  - Content: Configuration example, integration example, monitoring example
  - Content: Link to quickstart.md for detailed guide
  - Pattern: Existing module __init__.py documentation

- [ ] T052 Update main bot to initialize DailyProfitTracker
  - File: src/trading_bot/bot.py
  - Logic: Load config, create tracker, pass to SafetyChecks
  - Logic: Call update_state() on trade events
  - Logic: Call reset_daily_state() on market open
  - REUSE: Existing bot initialization patterns
  - From: plan.md integration scenarios

---

## [TEST GUARDRAILS]

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each
- Full suite: <6 min total

**Coverage Requirements:**
- New code: 100% coverage (no untested lines in new features per spec.md NFR-005)
- Unit tests: ≥90% line coverage (from spec.md NFR-005)
- Integration tests: ≥80% coverage of critical paths
- Modified code: Coverage cannot decrease

**Measurement:**
- Python: `pytest --cov=src/trading_bot/profit_goal --cov-report=term-missing tests/unit/profit_goal/`
- Target: All new lines in src/trading_bot/profit_goal/ must be covered

**Quality Gates:**
- All tests must pass before merge
- Coverage thresholds enforced in CI
- No skipped tests without GitHub issue

**Clarity Requirements:**
- One behavior per test
- Descriptive names: `test_protection_triggers_when_drawdown_exceeds_threshold()`
- Given-When-Then structure in test body

**Anti-Patterns:**
- ❌ NO UI snapshots (not applicable - backend feature)
- ❌ NO implementation testing (test behaviors, not internals)
- ✅ USE mock for external dependencies (PerformanceTracker, file I/O)
- ✅ USE real dataclasses for validation testing

**Examples:**
```python
# ❌ Bad: Testing implementation detail
assert tracker._state.daily_pnl == Decimal("100")

# ✅ Good: Testing behavior
state = tracker.get_current_state()
assert state.daily_pnl == Decimal("100")

# ❌ Bad: Generic error message
assert result is False

# ✅ Good: Descriptive assertion
assert tracker.is_protection_active() is True, \
    "Protection should activate when drawdown exceeds 50%"
```
