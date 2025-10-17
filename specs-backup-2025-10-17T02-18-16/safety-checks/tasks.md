# Tasks: Pre-Trade Safety Checks & Risk Management

## [CODEBASE REUSE ANALYSIS]

Scanned: `src/trading_bot/**/*.py`, `tests/unit/**/*.py`

### [EXISTING - REUSE]
- ✅ Config (src/trading_bot/config.py) - Risk parameters already defined
- ✅ Logger (src/trading_bot/logger.py) - Audit logging infrastructure
- ✅ CircuitBreaker logic (src/trading_bot/bot.py:18-73) - Refactor into SafetyChecks
- ✅ Trade history (logs/trades.log) - Parse for consecutive loss detection
- ✅ Error logging (logs/errors.log) - Log safety check failures

### [NEW - CREATE]
- 🆕 SafetyChecks module (no existing safety validation layer)
- 🆕 Time utilities (no timezone-aware trading hours validation)
- 🆕 Circuit breaker persistence (no state file management)

---

## Phase 3.1: Setup & Dependencies

T001 [P] Add pytz dependency to requirements.txt
- **File**: requirements.txt
- **Add**: `pytz==2024.1  # Timezone handling for trading hours`
- **Verify**: `pip install -r requirements.txt` succeeds
- **From**: plan.md [ARCHITECTURE DECISIONS] Dependencies

T002 [P] Create utils directory structure
- **Command**: `mkdir -p src/trading_bot/utils`
- **Create**: `src/trading_bot/utils/__init__.py` (empty)
- **Pattern**: Existing src/trading_bot/ directory structure
- **From**: plan.md [STRUCTURE]

T003 [P] Initialize circuit breaker state file
- **File**: logs/circuit_breaker.json
- **Content**: `{"active": false, "triggered_at": null, "reason": null, "reset_at": null}`
- **Ensure**: logs/ directory exists
- **From**: plan.md [SCHEMA] State Files

---

## Phase 3.2: RED - Write Failing Tests

### Time Utilities Tests

T004 [RED] Write failing test: Trading hours validation with timezone
- **File**: tests/unit/test_time_utils.py
- **Test**: `test_is_trading_hours_within_hours_est()`
- **Given**: Current time is 8:00 AM EST (within 7am-10am)
- **When**: `is_trading_hours("America/New_York")` called
- **Then**: Returns True
- **Pattern**: tests/unit/test_mode_switcher.py (timezone testing)
- **From**: spec.md FR-002

T005 [RED] Write failing test: Outside trading hours returns False
- **File**: tests/unit/test_time_utils.py
- **Test**: `test_is_trading_hours_outside_hours_est()`
- **Given**: Current time is 6:59 AM EST (before 7am)
- **When**: `is_trading_hours("America/New_York")` called
- **Then**: Returns False
- **From**: spec.md FR-002

T006 [RED] Write failing test: DST transition handling
- **File**: tests/unit/test_time_utils.py
- **Test**: `test_is_trading_hours_handles_dst_transition()`
- **Given**: Mock time during DST transition (spring forward/fall back)
- **When**: `is_trading_hours("America/New_York")` called
- **Then**: Returns correct result accounting for DST offset
- **From**: plan.md [RISK MITIGATION] DST edge cases

### SafetyChecks Core Tests

T007 [RED] Write failing test: Buying power check with sufficient funds
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_check_buying_power_sufficient_funds()`
- **Given**: Buying power = $10,000, order cost = $5,000
- **When**: `check_buying_power(quantity=100, price=50.00, current_buying_power=10000)` called
- **Then**: Returns True
- **From**: spec.md FR-001

T008 [RED] Write failing test: Buying power check with insufficient funds
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_check_buying_power_insufficient_funds()`
- **Given**: Buying power = $1,000, order cost = $1,500
- **When**: `check_buying_power(quantity=100, price=15.00, current_buying_power=1000)` called
- **Then**: Returns False
- **From**: spec.md FR-001, Scenario 1

T009 [RED] Write failing test: Trading hours enforcement blocks outside hours
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_check_trading_hours_blocks_outside_hours()`
- **Given**: Current time is 6:45 AM EST (before 7am)
- **When**: `check_trading_hours()` called
- **Then**: Returns False
- **From**: spec.md FR-002, Scenario 2

T010 [RED] Write failing test: Daily loss limit triggers circuit breaker
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_check_daily_loss_limit_exceeds_threshold()`
- **Given**: Daily PnL = -3.5%, limit = 3.0%
- **When**: `check_daily_loss_limit(current_daily_pnl=-3500, portfolio_value=100000)` called
- **Then**: Returns False
- **From**: spec.md FR-003, Scenario 3

T011 [RED] Write failing test: Consecutive losses detector triggers at limit
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_check_consecutive_losses_detects_pattern()`
- **Given**: Last 3 trades are losses
- **When**: `check_consecutive_losses()` called
- **Then**: Returns False
- **From**: spec.md FR-004, Scenario 4

T012 [RED] Write failing test: Position size calculator enforces 5% limit
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_calculate_position_size_enforces_max_limit()`
- **Given**: Account balance = $100,000, max position = 5%
- **When**: `calculate_position_size(entry_price=10, stop_loss_price=9, account_balance=100000)` called
- **Then**: Returns PositionSize with dollar_amount ≤ $5,000
- **From**: spec.md FR-005

T013 [RED] Write failing test: Duplicate order prevention blocks same symbol
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_check_duplicate_order_blocks_duplicate()`
- **Given**: Pending buy order for AAPL exists
- **When**: `check_duplicate_order(symbol="AAPL", action="BUY")` called
- **Then**: Returns False
- **From**: spec.md FR-006, Scenario 6

T014 [RED] Write failing test: Circuit breaker trigger sets active flag
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_trigger_circuit_breaker_sets_active_flag()`
- **Given**: Circuit breaker is not active
- **When**: `trigger_circuit_breaker(reason="3 consecutive losses")` called
- **Then**: Circuit breaker active flag is True, reason is logged
- **From**: spec.md FR-007

T015 [RED] Write failing test: Circuit breaker reset clears flag
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_reset_circuit_breaker_clears_flag()`
- **Given**: Circuit breaker is active
- **When**: `reset_circuit_breaker()` called
- **Then**: Circuit breaker active flag is False
- **From**: spec.md FR-007

T016 [RED] Write failing test: validate_trade() orchestrates all checks
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_validate_trade_passes_all_checks()`
- **Given**: All safety checks pass
- **When**: `validate_trade(symbol="AAPL", action="BUY", quantity=100, price=150, current_buying_power=20000)` called
- **Then**: Returns SafetyResult(is_safe=True, reason=None)
- **From**: spec.md Requirements FR-001 through FR-007

T017 [RED] Write failing test: validate_trade() blocks on any failure
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_validate_trade_blocks_on_buying_power_failure()`
- **Given**: Buying power check fails
- **When**: `validate_trade(...)` called
- **Then**: Returns SafetyResult(is_safe=False, reason="Insufficient buying power...")
- **From**: spec.md NFR-002 (fail-safe design)

---

## Phase 3.3: GREEN - Minimal Implementation

### Time Utilities Implementation

T018 [GREEN→T004,T005,T006] Implement time utilities module
- **File**: src/trading_bot/utils/time_utils.py
- **Functions**:
  - `is_trading_hours(timezone: str) → bool`
  - `get_current_time_in_tz(timezone: str) → datetime`
- **Logic**: Use pytz to convert UTC to target timezone, check 7am-10am range
- **Pattern**: Simple timezone conversion with bounds checking
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE]

### SafetyChecks Core Implementation

T019 [GREEN→T007,T008] Implement buying power check
- **File**: src/trading_bot/safety_checks.py (create)
- **Method**: `SafetyChecks.check_buying_power(quantity, price, current_buying_power) → bool`
- **Logic**: Calculate (quantity × price) ≤ current_buying_power
- **REUSE**: None (simple arithmetic)
- **From**: spec.md FR-001

T020 [GREEN→T009] Implement trading hours check
- **File**: src/trading_bot/safety_checks.py
- **Method**: `SafetyChecks.check_trading_hours() → bool`
- **Logic**: Get config.trading_timezone, call time_utils.is_trading_hours()
- **REUSE**: src/trading_bot/utils/time_utils.py (T018)
- **REUSE**: src/trading_bot/config.py (trading_start_time, trading_end_time, trading_timezone)
- **From**: spec.md FR-002

T021 [GREEN→T010] Implement daily loss limit check
- **File**: src/trading_bot/safety_checks.py
- **Method**: `SafetyChecks.check_daily_loss_limit(current_daily_pnl, portfolio_value) → bool`
- **Logic**: Calculate loss_pct = abs(current_daily_pnl / portfolio_value) * 100, compare to config.max_daily_loss_pct
- **REUSE**: src/trading_bot/config.py (max_daily_loss_pct)
- **From**: spec.md FR-003

T022 [GREEN→T011] Implement consecutive loss detector
- **File**: src/trading_bot/safety_checks.py
- **Method**: `SafetyChecks.check_consecutive_losses() → bool`
- **Logic**: Parse last N trades from logs/trades.log, count consecutive losses
- **REUSE**: logs/trades.log (existing trade history)
- **From**: spec.md FR-004

T023 [GREEN→T012] Implement position size calculator
- **File**: src/trading_bot/safety_checks.py
- **Method**: `SafetyChecks.calculate_position_size(entry_price, stop_loss_price, account_balance) → PositionSize`
- **Logic**: Calculate risk_amount = (entry_price - stop_loss_price) × shares, enforce max 5% portfolio
- **REUSE**: src/trading_bot/config.py (max_position_pct)
- **From**: spec.md FR-005

T024 [GREEN→T013] Implement duplicate order prevention
- **File**: src/trading_bot/safety_checks.py
- **Method**: `SafetyChecks.check_duplicate_order(symbol, action) → bool`
- **Logic**: Track pending orders in memory (dict), check if symbol+action exists
- **State**: In-memory dict `self._pending_orders: Dict[str, str]`
- **From**: spec.md FR-006

T025 [GREEN→T014,T015] Implement circuit breaker management
- **File**: src/trading_bot/safety_checks.py
- **Methods**:
  - `SafetyChecks.trigger_circuit_breaker(reason) → None`
  - `SafetyChecks.reset_circuit_breaker() → None`
- **Logic**: Read/write logs/circuit_breaker.json, set active flag, log to trades.log
- **REUSE**: src/trading_bot/logger.py (get_trades_logger)
- **Pattern**: JSON file read/write with atomic operations
- **From**: spec.md FR-007

T026 [GREEN→T016,T017] Implement validate_trade() orchestration
- **File**: src/trading_bot/safety_checks.py
- **Method**: `SafetyChecks.validate_trade(symbol, action, quantity, price, current_buying_power) → SafetyResult`
- **Logic**: Call all check methods in sequence, return first failure or success
- **Order**: Circuit breaker → Trading hours → Buying power → Duplicate → All other checks
- **REUSE**: All check methods from T019-T025
- **From**: spec.md (all FR requirements)

---

## Phase 3.4: REFACTOR - Clean Up

T027 [REFACTOR] Extract CircuitBreaker logic from bot.py to SafetyChecks
- **Remove**: src/trading_bot/bot.py:18-73 (CircuitBreaker class)
- **Migrate**: Logic to SafetyChecks.check_daily_loss_limit() and consecutive loss detector
- **Update**: bot.py imports to use SafetyChecks instead
- **Verify**: All tests still pass, no functionality change
- **From**: plan.md [REFACTORING STRATEGY]

T028 [REFACTOR] Create data classes for SafetyResult and PositionSize
- **File**: src/trading_bot/safety_checks.py
- **Add**: @dataclass definitions at top of file
- **Classes**: SafetyResult, PositionSize (from contracts/api.yaml)
- **Verify**: Type hints work correctly with mypy
- **From**: plan.md [SCHEMA] Data Classes

T029 [REFACTOR] Add comprehensive docstrings with examples
- **Files**: src/trading_bot/safety_checks.py, src/trading_bot/utils/time_utils.py
- **Add**: Class docstring, method docstrings with Args/Returns/Raises
- **Include**: Usage examples in module docstring
- **Pattern**: Existing src/trading_bot/logger.py docstring style
- **From**: Constitution §Documentation (docstrings required)

---

## Phase 3.5: Integration & Testing

T030 [P] Write integration test: SafetyChecks with real config
- **File**: tests/integration/test_safety_checks_integration.py (create)
- **Test**: `test_safety_checks_with_real_config()`
- **Given**: Load config from config.json
- **When**: Initialize SafetyChecks(config)
- **Then**: All methods work with real risk parameters
- **Pattern**: tests/unit/test_validator.py (config integration)
- **From**: spec.md NFR-004 (integration tests required)

T031 [P] Write integration test: Trade history parsing from logs
- **File**: tests/integration/test_safety_checks_integration.py
- **Test**: `test_consecutive_losses_parses_trades_log()`
- **Given**: Mock trades.log with 3 consecutive losses
- **When**: SafetyChecks initialized and check_consecutive_losses() called
- **Then**: Correctly identifies consecutive loss pattern
- **From**: plan.md [RISK MITIGATION] Parse errors in trades.log

T032 [P] Write integration test: Circuit breaker state persistence
- **File**: tests/integration/test_safety_checks_integration.py
- **Test**: `test_circuit_breaker_persists_across_restarts()`
- **Given**: Circuit breaker triggered, state saved to logs/circuit_breaker.json
- **When**: New SafetyChecks instance created (simulates restart)
- **Then**: Circuit breaker still active, blocks all trades
- **From**: spec.md FR-007 (manual reset requirement)

T033 [P] Integrate SafetyChecks into bot.py main loop
- **File**: src/trading_bot/bot.py
- **Add**: Import SafetyChecks
- **Add**: Initialize in TradingBot.__init__()
- **Add**: Call safety.validate_trade() before every order
- **Block**: If is_safe=False, log reason and skip trade
- **Pattern**: Dependency injection pattern
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 2

T034 [P] Update bot.py to log safety check rejections
- **File**: src/trading_bot/bot.py
- **Add**: When trade blocked, call log_error(reason)
- **Add**: If circuit breaker triggered, call log_trade() with "CIRCUIT_BREAKER" event
- **REUSE**: src/trading_bot/logger.py (log_error, log_trade)
- **From**: spec.md NFR-003 (Auditability)

---

## Phase 3.6: Error Handling & Resilience

T035 [RED] Write failing test: Corrupt circuit breaker state fails safe
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_corrupt_state_file_trips_circuit_breaker()`
- **Given**: logs/circuit_breaker.json contains invalid JSON
- **When**: SafetyChecks initialized
- **Then**: Circuit breaker automatically trips (fail-safe)
- **From**: spec.md NFR-002, plan.md [RISK MITIGATION]

T036 [GREEN→T035] Implement fail-safe circuit breaker loading
- **File**: src/trading_bot/safety_checks.py
- **Method**: `SafetyChecks._load_circuit_breaker_state()`
- **Logic**: Try JSON parse, on error trip circuit breaker and log error
- **REUSE**: src/trading_bot/logger.py (log_error)
- **From**: spec.md NFR-002 (fail-safe design)

T037 [RED] Write failing test: Missing trades.log gracefully handled
- **File**: tests/unit/test_safety_checks.py
- **Test**: `test_missing_trades_log_assumes_zero_losses()`
- **Given**: logs/trades.log does not exist
- **When**: check_consecutive_losses() called
- **Then**: Returns True (assume 0 losses), logs warning
- **From**: plan.md [RISK MITIGATION] Parse errors in trades.log

T038 [GREEN→T037] Implement graceful trades.log parsing
- **File**: src/trading_bot/safety_checks.py
- **Method**: `SafetyChecks._parse_trade_history()`
- **Logic**: Try to read/parse, on FileNotFoundError return empty list, log warning
- **REUSE**: src/trading_bot/logger.py (log_error)
- **From**: spec.md NFR-002 (fail-safe design)

T039 [P] Add input validation for all safety check methods
- **File**: src/trading_bot/safety_checks.py
- **Add**: Validate quantity > 0, price > 0, symbol is alphanumeric, action in ["BUY", "SELL"]
- **Raise**: ValueError with clear message on invalid input
- **Pattern**: src/trading_bot/config.py:validate() method
- **From**: spec.md NFR-005 (Type Safety)

---

## Phase 3.7: Deployment Preparation

T040 [P] Run mypy strict mode and fix all type errors
- **Command**: `mypy src/trading_bot/safety_checks.py src/trading_bot/utils/time_utils.py --strict`
- **Fix**: All type hints, return types, Optional types
- **Verify**: mypy passes with 0 errors
- **From**: spec.md NFR-005, Constitution §Code_Quality

T041 [P] Achieve 95% test coverage for safety_checks.py
- **Command**: `pytest tests/unit/test_safety_checks.py --cov=src/trading_bot/safety_checks --cov-report=term-missing --cov-fail-under=95`
- **Add**: Additional tests for edge cases if coverage < 95%
- **Verify**: Coverage ≥ 95%
- **From**: spec.md NFR-004, plan.md [RISK MITIGATION]

T042 [P] Create manual testing script for circuit breakers
- **File**: scripts/test_circuit_breaker.py (create)
- **Script**: Simulate all circuit breaker scenarios (daily loss, consecutive losses)
- **Output**: Clear pass/fail for each scenario
- **Usage**: `python scripts/test_circuit_breaker.py`
- **From**: spec.md [QUALITY GATES] Manual testing required

T043 [P] Document rollback procedure in NOTES.md
- **File**: specs/safety-checks/NOTES.md
- **Add**: Deployment Metadata section with rollback commands
- **Commands**:
  1. Remove SafetyChecks import from bot.py
  2. Restore CircuitBreaker class in bot.py
  3. Delete logs/circuit_breaker.json (safe, no data loss)
- **From**: plan.md [DEPLOYMENT ACCEPTANCE]

T044 [P] Update requirements.txt with final dependencies
- **File**: requirements.txt
- **Verify**: pytz==2024.1 is included
- **Add comments**: `# Safety checks - timezone validation`
- **From**: plan.md [CI/CD IMPACT]

---

## Task Summary

- **Total**: 44 tasks
- **Setup**: 3 tasks (T001-T003)
- **RED (Tests)**: 14 tasks (T004-T017)
- **GREEN (Impl)**: 9 tasks (T018-T026)
- **REFACTOR**: 3 tasks (T027-T029)
- **Integration**: 5 tasks (T030-T034)
- **Error Handling**: 5 tasks (T035-T039)
- **Deployment**: 5 tasks (T040-T044)

**TDD Coverage**: 14 behaviors with RED → GREEN → REFACTOR cycles
**Reuse**: 5 existing modules/files
**New**: 3 new modules/files

**Dependencies**:
- T018 must complete before T020 (time utils used in trading hours check)
- T019-T026 must complete before T027 (refactor depends on new implementation)
- T027-T029 must complete before T030-T034 (integration needs clean code)
- All tasks must complete before T040-T044 (deployment prep is final)

**Estimated Duration**: 3-4 days (per plan.md implementation phases)
