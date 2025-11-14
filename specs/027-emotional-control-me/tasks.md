# Tasks: Emotional Control Mechanisms

## [CODEBASE REUSE ANALYSIS]
Scanned: D:\Coding\Stocks

[EXISTING - REUSE]
- ✅ DailyProfitTracker (src/trading_bot/profit_goal/tracker.py) - State persistence pattern, JSONL logging, update_state() orchestration
- ✅ RiskManager (src/trading_bot/risk_management/manager.py) - Position sizing calculation integration point
- ✅ CircuitBreaker (src/trading_bot/error_handling/circuit_breaker.py) - Sliding window pattern for streak tracking
- ✅ PerformanceTracker (src/trading_bot/performance/tracker.py) - Trade outcome tracking for win/loss detection
- ✅ AccountData (src/trading_bot/account/account_data.py) - Account balance retrieval
- ✅ JSONL logging patterns - Daily rotation, Decimal serialization
- ✅ Atomic file writes - Temp file + rename pattern from DailyProfitTracker
- ✅ pytest, pytest-mock - Existing test framework

[NEW - CREATE]
- 🆕 EmotionalControl tracker class - No existing emotional control mechanism
- 🆕 EmotionalControl data models (State, Event, Config) - New domain entities
- 🆕 EmotionalControl CLI commands - New command interface
- 🆕 logs/emotional_control/ directory - New log storage location
- 🆕 Integration with RiskManager.calculate_position_plan() - New multiplier application

## [DEPENDENCY GRAPH]
Task completion order:
1. Phase 1: Setup (T001-T003) - Creates project structure, blocks all implementation
2. Phase 2: Data Models (T004-T006) - Creates entities, blocks tracker implementation
3. Phase 3: Core Tracker Logic (T007-T015) - Main feature implementation
4. Phase 4: RiskManager Integration (T016-T017) - Position sizing integration
5. Phase 5: CLI Commands (T018-T020) - User interface
6. Phase 6: Testing (T021-T029) - Quality verification
7. Phase 7: Deployment Preparation (T030-T033) - Production readiness

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 2: T004, T005, T006 (different model files, no dependencies)
- Phase 3: T010, T011 (different methods, no dependencies)
- Phase 4: T016, T017 (different integration points)
- Phase 5: T018, T019, T020 (different CLI commands)
- Phase 6: T021, T022, T023, T024, T025, T026, T027, T028 (independent test suites)
- Phase 7: T030, T031, T032 (different deployment artifacts)

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Full feature (single release, no phased rollout)
**Incremental delivery**: Complete implementation → staging validation → production
**Testing approach**: TDD required (unit + integration + performance tests per Constitution §Testing_Requirements)
**Coverage target**: ≥90% per Constitution §Code_Quality

---

## Phase 1: Setup

- [ ] T001 Create project directory structure
  - Directories: src/trading_bot/emotional_control/, tests/emotional_control/, logs/emotional_control/
  - Files: __init__.py (module exports)
  - Pattern: src/trading_bot/profit_goal/ structure
  - From: plan.md [STRUCTURE]

- [ ] T002 [P] Create log directory with proper permissions
  - Directory: logs/emotional_control/
  - Permissions: chmod 700 (user read/write/execute only)
  - Files: .gitkeep (track directory in git)
  - Pattern: logs/profit-protection/ directory
  - From: plan.md [STRUCTURE]

- [ ] T003 [P] Update .env.example with configuration variables
  - File: .env.example
  - Variables: EMOTIONAL_CONTROL_ENABLED=true
  - Documentation: Add comment explaining feature flag
  - Pattern: Existing .env.example entries
  - From: plan.md [CI/CD IMPACT]

---

## Phase 2: Data Models

**Goal**: Create data structures for state, events, and configuration

- [ ] T004 [P] Create EmotionalControlState data model
  - File: src/trading_bot/emotional_control/models.py
  - Fields: is_active, activated_at, trigger_reason, account_balance_at_activation, loss_amount, consecutive_losses, consecutive_wins, last_updated
  - Type hints: All fields with proper Decimal/str/int types
  - Validation: Field constraints from data-model.md
  - REUSE: @dataclass decorator pattern from profit_goal/models.py
  - Pattern: src/trading_bot/profit_goal/models.py DailyProfitState
  - From: data-model.md EmotionalControlState entity

- [ ] T005 [P] Create EmotionalControlEvent data model
  - File: src/trading_bot/emotional_control/models.py (same file as T004)
  - Fields: event_id, timestamp, event_type, trigger_reason, account_balance, loss_amount, consecutive_losses, consecutive_wins, admin_id, reset_reason, position_size_multiplier
  - Factory method: create() for UUID generation and timestamp creation
  - Validation: Enum validation for event_type and trigger_reason
  - REUSE: @dataclass pattern, UUID4 generation from profit_goal/models.py
  - Pattern: src/trading_bot/profit_goal/models.py ProfitProtectionEvent
  - From: data-model.md EmotionalControlEvent entity

- [ ] T006 [P] Create EmotionalControlConfig data model
  - File: src/trading_bot/emotional_control/config.py
  - Fields: enabled, single_loss_threshold_pct, consecutive_loss_threshold, recovery_win_threshold, position_size_multiplier_active, state_file_path, event_log_dir
  - Factory method: default() with hardcoded v1.0 values (3.0%, 3 losses, 3 wins, 0.25 multiplier)
  - Factory method: from_env() to load EMOTIONAL_CONTROL_ENABLED from environment
  - REUSE: Config loading pattern from risk_management/config.py
  - Pattern: src/trading_bot/risk_management/config.py RiskManagementConfig
  - From: data-model.md EmotionalControlConfig entity

---

## Phase 3: Core Tracker Logic

**Goal**: Implement main EmotionalControl class with state management and event logging

- [ ] T007 Create EmotionalControl class skeleton
  - File: src/trading_bot/emotional_control/tracker.py
  - Methods: __init__, update_state, get_position_multiplier, reset_manual, _check_activation_trigger, _check_recovery_trigger, _persist_state, _load_state, _log_event
  - Constructor args: config (EmotionalControlConfig), state_file (Path), log_dir (Path)
  - Instance variables: _state (EmotionalControlState), _config (EmotionalControlConfig)
  - REUSE: Class structure from DailyProfitTracker
  - Pattern: src/trading_bot/profit_goal/tracker.py DailyProfitTracker
  - From: plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T008 Implement _load_state method with fail-safe recovery
  - File: src/trading_bot/emotional_control/tracker.py
  - Logic: Load state.json, validate fields, handle corruption → default to ACTIVE (fail-safe per spec.md FR-013)
  - Error handling: FileNotFoundError → create fresh INACTIVE state, JSONDecodeError → ACTIVE with alert
  - Return: EmotionalControlState instance
  - REUSE: Atomic file read pattern from DailyProfitTracker._load_state()
  - Pattern: src/trading_bot/profit_goal/tracker.py _load_state method
  - From: plan.md [ERROR HANDLING]

- [ ] T009 Implement _persist_state method with atomic writes
  - File: src/trading_bot/emotional_control/tracker.py
  - Logic: Serialize state to JSON, write to temp file, rename to state.json (atomic operation)
  - Temp file: state.json.tmp (same directory)
  - Error handling: OSError → log error, continue with in-memory state
  - REUSE: Atomic write pattern (temp + rename) from DailyProfitTracker
  - Pattern: src/trading_bot/profit_goal/tracker.py _persist_state implementation
  - From: plan.md [EXISTING INFRASTRUCTURE - REUSE]

- [ ] T010 [P] Implement _check_activation_trigger method
  - File: src/trading_bot/emotional_control/tracker.py
  - Args: trade_pnl (Decimal), account_balance (Decimal), consecutive_losses (int)
  - Logic: Check single loss ≥3% OR consecutive losses ≥3 (from spec.md FR-001)
  - Return: tuple[bool, str] (should_activate, trigger_reason: "SINGLE_LOSS" | "STREAK_LOSS")
  - Calculation: loss_pct = abs(trade_pnl) / account_balance * 100
  - REUSE: Decimal precision calculations
  - Pattern: Similar threshold checking from risk_management/calculator.py
  - From: spec.md FR-001, data-model.md activation triggers

- [ ] T011 [P] Implement _check_recovery_trigger method
  - File: src/trading_bot/emotional_control/tracker.py
  - Args: consecutive_wins (int)
  - Logic: Check consecutive wins ≥3 (from spec.md FR-003)
  - Return: bool (should_deactivate)
  - REUSE: Simple counter comparison
  - Pattern: Similar streak detection from error_handling/circuit_breaker.py
  - From: spec.md FR-003, data-model.md recovery triggers

- [ ] T012 Implement _log_event method with JSONL append
  - File: src/trading_bot/emotional_control/tracker.py
  - Args: event (EmotionalControlEvent)
  - Logic: Serialize event to JSON line, append to logs/emotional_control/events-YYYY-MM-DD.jsonl
  - Daily rotation: Use datetime.now(UTC).strftime("%Y-%m-%d") for filename
  - Error handling: OSError → log to stderr, don't crash
  - REUSE: JSONL append pattern, daily rotation from DailyProfitTracker
  - Pattern: src/trading_bot/profit_goal/tracker.py event logging implementation
  - From: plan.md [EXISTING INFRASTRUCTURE - REUSE]

- [ ] T013 Implement update_state method
  - File: src/trading_bot/emotional_control/tracker.py
  - Args: trade_pnl (Decimal), account_balance (Decimal), is_win (bool)
  - Logic: Update consecutive counters, check activation/recovery triggers, update state, persist, log event
  - Side effects: Updates _state, writes to state.json, appends to event log
  - Performance: Target <10ms per spec.md NFR-001
  - REUSE: Orchestration pattern from DailyProfitTracker.update_state()
  - Pattern: src/trading_bot/profit_goal/tracker.py update_state method
  - From: spec.md FR-001 to FR-005, plan.md [NEW INFRASTRUCTURE - CREATE]

- [ ] T014 Implement get_position_multiplier method
  - File: src/trading_bot/emotional_control/tracker.py
  - Args: None
  - Return: Decimal (0.25 if active, 1.00 if inactive)
  - Logic: Check _state.is_active, return appropriate multiplier
  - Performance: Target <1ms (in-memory lookup)
  - REUSE: Simple accessor pattern
  - Pattern: Getter methods from risk_management/manager.py
  - From: spec.md FR-002, FR-008

- [ ] T015 Implement reset_manual method with confirmation
  - File: src/trading_bot/emotional_control/tracker.py
  - Args: admin_id (str), reset_reason (str), confirm (bool)
  - Logic: Require confirm=True, deactivate emotional control, create MANUAL_RESET event, persist state
  - Validation: raise ValueError if not confirm
  - Audit trail: Log event with admin_id and reset_reason
  - REUSE: Manual intervention pattern
  - Pattern: Admin override methods from risk_management/manager.py
  - From: spec.md FR-006, data-model.md MANUAL_RESET event

---

## Phase 4: RiskManager Integration

**Goal**: Integrate EmotionalControl multiplier with RiskManager position sizing

- [ ] T016 [P] Add emotional_control_tracker parameter to RiskManager.__init__
  - File: src/trading_bot/risk_management/manager.py
  - Parameter: emotional_control_tracker (Optional[EmotionalControl])
  - Instance variable: self.emotional_control = emotional_control_tracker
  - Default: None (backward compatible)
  - Pattern: Similar optional dependency injection from __init__ method
  - From: spec.md FR-008

- [ ] T017 [P] Apply emotional control multiplier in RiskManager.calculate_position_plan
  - File: src/trading_bot/risk_management/manager.py
  - Location: After PositionPlan creation, before return
  - Logic: If self.emotional_control, multiply quantity by get_position_multiplier()
  - Code: `if self.emotional_control: plan.quantity = int(Decimal(plan.quantity) * self.emotional_control.get_position_multiplier())`
  - Validation: Ensure quantity remains positive integer
  - REUSE: Decimal precision calculation pattern
  - Pattern: Position size adjustment logic from calculate_position_plan
  - From: spec.md FR-008, plan.md [INTEGRATION SCENARIOS]

---

## Phase 5: CLI Commands

**Goal**: Create command-line interface for monitoring and manual control

- [ ] T018 [P] Create CLI status command
  - File: src/trading_bot/emotional_control/cli.py
  - Function: status() - Display current emotional control state
  - Output: Active/Inactive, trigger reason, consecutive counters, position multiplier
  - Format: Human-readable text with color coding (green=inactive, yellow=active)
  - REUSE: CLI formatting patterns
  - Pattern: src/trading_bot/profit_goal/cli.py status commands
  - From: spec.md FR-011

- [ ] T019 [P] Create CLI reset command
  - File: src/trading_bot/emotional_control/cli.py
  - Function: reset(admin_id: str, reason: str, force: bool) - Manual reset with confirmation
  - Confirmation: Prompt user "Confirm reset? (yes/no)" unless --force flag
  - Validation: Require admin_id and reason arguments
  - Output: Success message with new state
  - REUSE: CLI interaction patterns, confirmation prompts
  - Pattern: Admin commands from existing CLI tools
  - From: spec.md FR-006

- [ ] T020 [P] Create CLI events command
  - File: src/trading_bot/emotional_control/cli.py
  - Function: events(days: int) - Display recent events from JSONL logs
  - Args: --days N (default: 7) - Number of days to display
  - Output: Table with timestamp, event_type, trigger_reason, position_multiplier
  - Format: Reverse chronological order (newest first)
  - REUSE: JSONL parsing, table formatting
  - Pattern: Log viewing commands from performance tracking CLI
  - From: spec.md FR-004, FR-011

---

## Phase 6: Testing

**Goal**: Achieve ≥90% test coverage per Constitution §Testing_Requirements

### Unit Tests

- [ ] T021 [P] Write unit tests for EmotionalControlState model
  - File: tests/emotional_control/test_models.py
  - Tests: Field validation, default values, state transitions
  - Coverage: 100% (all fields and validation rules)
  - Pattern: tests/unit/profit_goal/test_tracker.py model tests
  - From: spec.md AC-001 to AC-004

- [ ] T022 [P] Write unit tests for EmotionalControlEvent model
  - File: tests/emotional_control/test_models.py (same file as T021)
  - Tests: create() factory, UUID generation, timestamp formatting, field validation
  - Coverage: 100% (all event types and trigger reasons)
  - Pattern: tests/unit/profit_goal/test_tracker.py event tests
  - From: spec.md AC-017

- [ ] T023 [P] Write unit tests for EmotionalControlConfig
  - File: tests/emotional_control/test_config.py
  - Tests: default() factory, from_env() loading, threshold validation
  - Mocking: Mock os.environ for environment variable tests
  - Coverage: 100% (all config fields and defaults)
  - Pattern: tests/risk_management/test_config.py
  - From: spec.md Configuration section

- [ ] T024 [P] Write unit tests for _load_state fail-safe behavior
  - File: tests/emotional_control/test_tracker.py
  - Tests: Missing file → INACTIVE, corrupted JSON → ACTIVE (fail-safe), valid file → correct state
  - Mocking: Mock file I/O with pytest tmp_path fixture
  - Coverage: All error paths (FileNotFoundError, JSONDecodeError, KeyError)
  - Pattern: tests/unit/profit_goal/test_tracker.py state loading tests
  - From: spec.md AC-013, FR-013

- [ ] T025 [P] Write unit tests for _persist_state atomic writes
  - File: tests/emotional_control/test_tracker.py (same file as T024)
  - Tests: Successful write, temp file creation, rename operation, error handling
  - Mocking: Mock file operations to verify atomic pattern
  - Coverage: All write paths including errors
  - Pattern: tests/unit/profit_goal/test_tracker.py persistence tests
  - From: spec.md AC-014, NFR-002

- [ ] T026 [P] Write unit tests for activation triggers
  - File: tests/emotional_control/test_tracker.py (same file as T024)
  - Tests: Single loss ≥3% activates, <3% doesn't activate, 3 consecutive losses activate, 2 consecutive don't
  - Test data: Various account balances and loss amounts from spec.md scenarios
  - Coverage: All activation paths (SINGLE_LOSS, STREAK_LOSS)
  - Pattern: tests/unit/profit_goal/test_tracker.py trigger tests
  - From: spec.md AC-001 to AC-004

- [ ] T027 [P] Write unit tests for recovery triggers
  - File: tests/emotional_control/test_tracker.py (same file as T024)
  - Tests: 3 consecutive wins deactivate, 2 consecutive don't, manual reset deactivates
  - Test data: Win/loss sequences from spec.md scenarios
  - Coverage: All recovery paths (PROFITABLE_RECOVERY, MANUAL_RESET)
  - Pattern: tests/unit/profit_goal/test_tracker.py recovery tests
  - From: spec.md AC-008 to AC-011

- [ ] T028 [P] Write unit tests for position multiplier logic
  - File: tests/emotional_control/test_tracker.py (same file as T024)
  - Tests: Active → 0.25, Inactive → 1.00, type verification (returns Decimal)
  - Coverage: All multiplier paths
  - Pattern: Simple getter tests from risk_management tests
  - From: spec.md AC-005, AC-006

### Integration Tests

- [ ] T029 [P] Write integration tests with RiskManager
  - File: tests/emotional_control/test_integration.py
  - Tests: Multiplier applied to position size, full workflow (activation → sizing → recovery)
  - Setup: Real RiskManager instance with EmotionalControl tracker
  - Validation: Verify position plan quantity reduced when active
  - Coverage: End-to-end integration flow
  - Pattern: tests/integration/test_bot_safety_integration.py
  - From: spec.md AC-015

### Performance Tests

- [ ] T030 [P] Write performance benchmark for update_state
  - File: tests/emotional_control/test_performance.py
  - Test: update_state() executes in <10ms (P95 per spec.md NFR-001)
  - Measurement: Run 100 iterations, measure P95 latency
  - Assertion: assert p95_latency < 0.010 (10ms)
  - Pattern: tests/risk_management/test_performance.py
  - From: spec.md AC-018, NFR-001

---

## Phase 7: Deployment Preparation

**Goal**: Prepare production deployment artifacts and documentation

- [ ] T031 [P] Create smoke tests for deployment validation
  - File: tests/smoke/test_emotional_control_smoke.py
  - Tests: State file creation, activation trigger, recovery trigger, manual reset
  - Execution time: <90s total (smoke test requirement)
  - Real dependencies: Real file I/O, no mocking
  - Pattern: tests/smoke/test_risk_management_smoke.py
  - From: plan.md [CI/CD IMPACT]

- [ ] T032 [P] Update NOTES.md with implementation summary
  - File: specs/027-emotional-control-me/NOTES.md
  - Content: Phase 3 checkpoint, task completion summary, test coverage results
  - Metrics: Total LOC, test count, coverage percentage, performance benchmarks
  - Pattern: Existing NOTES.md phase checkpoints
  - From: /tasks command template

- [ ] T033 [P] Create deployment checklist in quickstart.md
  - File: specs/027-emotional-control-me/quickstart.md
  - Sections: Prerequisites, installation steps, configuration, smoke tests, rollback procedure
  - Commands: Exact copy-paste commands for deployment
  - Validation: Steps to verify successful deployment
  - Pattern: Existing quickstart.md deployment sections
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

---

## [TEST GUARDRAILS]

**Speed Requirements:**
- Unit tests: <2s each
- Integration tests: <10s each
- Performance tests: <30s each
- Smoke tests: <90s total
- Full suite: <6 min total

**Coverage Requirements:**
- New code: 100% coverage (no untested lines in new features per Constitution)
- Unit tests: ≥80% line coverage
- Integration tests: ≥60% line coverage
- Coverage target: ≥90% per spec.md AC-020

**Measurement:**
- Python: `pytest tests/emotional_control/ --cov=src/trading_bot/emotional_control --cov-report=term-missing`
- Coverage enforcement: CI fails if <90%

**Quality Gates:**
- All tests must pass before merge
- MyPy type checking passes with --strict mode (spec.md AC-021)
- Bandit security scan shows 0 HIGH/CRITICAL vulnerabilities (spec.md AC-022)
- Performance benchmarks meet NFR targets (<10ms update_state)

**Clarity Requirements:**
- One behavior per test
- Descriptive names: `test_single_loss_3pct_activates_emotional_control()`
- Given-When-Then structure in test body
- No skipped tests without documented reason

**Anti-Patterns:**
- ❌ NO mocking in smoke tests (use real file I/O)
- ❌ NO float arithmetic (use Decimal for all financial calculations)
- ✅ USE pytest fixtures for common test data
- ✅ USE tmp_path fixture for file I/O tests
