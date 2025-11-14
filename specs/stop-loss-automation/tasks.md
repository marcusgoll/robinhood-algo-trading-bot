# Tasks: Automated Stop Loss and Targets

## [CODEBASE REUSE ANALYSIS]
Scanned: src/trading_bot/**/*.py

### [EXISTING - REUSE]
- ✅ OrderManager (src/trading_bot/order_management/manager.py) - place_limit_sell(), cancel_order(), get_order_status()
- ✅ SafetyChecks (src/trading_bot/safety_checks.py) - calculate_position_size() foundation, validate_trade()
- ✅ AccountData (src/trading_bot/account/account_data.py) - get_buying_power(), invalidate_cache()
- ✅ TradeRecord (src/trading_bot/logging/trade_record.py) - log_trade_outcome()
- ✅ StructuredTradeLogger (src/trading_bot/logging/structured_logger.py) - JSONL logging pattern
- ✅ Error hierarchy (src/trading_bot/error_handling/exceptions.py) - RetriableError, NonRetriableError
- ✅ Retry decorators (src/trading_bot/error_handling/retry.py) - @retry_on_transient_failure

### [NEW - CREATE]
- 🆕 RiskManager (src/trading_bot/risk_management/manager.py)
- 🆕 PullbackAnalyzer (src/trading_bot/risk_management/pullback_analyzer.py)
- 🆕 RiskRewardCalculator (src/trading_bot/risk_management/calculator.py)
- 🆕 StopAdjuster (src/trading_bot/risk_management/stop_adjuster.py)
- 🆕 TargetMonitor (src/trading_bot/risk_management/target_monitor.py)
- 🆕 risk_management/models.py (PositionPlan, RiskManagementEnvelope, PullbackData)
- 🆕 risk_management/exceptions.py (PositionPlanningError, StopPlacementError, TargetAdjustmentError)
- 🆕 risk_management/config.py (RiskManagementConfig dataclass)

---

## Phase 3.1: Package Setup

T001 [P] Create risk_management package structure
- **Directory**: src/trading_bot/risk_management/
- **Files**: __init__.py, manager.py, pullback_analyzer.py, calculator.py, stop_adjuster.py, target_monitor.py, models.py, exceptions.py, config.py
- **__init__.py exports**: RiskManager, PositionPlan, RiskManagementEnvelope, RiskManagementConfig
- **Pattern**: src/trading_bot/order_management/ package structure
- **From**: plan.md [STRUCTURE]

T002 [P] Create domain exceptions in risk_management/exceptions.py
- **File**: src/trading_bot/risk_management/exceptions.py
- **Classes**:
  - PositionPlanningError(NonRetriableError) - invalid risk parameters, stop distance validation failures
  - StopPlacementError(RetriableError) - broker API failures on stop order submission
  - TargetAdjustmentError(RetriableError) - trailing stop cancellation/replacement failures
- **Pattern**: src/trading_bot/order_management/exceptions.py (OrderValidationError, OrderSubmissionError)
- **REUSE**: src/trading_bot/error_handling/exceptions.py (RetriableError, NonRetriableError base classes)
- **From**: plan.md [NEW INFRASTRUCTURE]

T003 [P] Create RiskManagementConfig dataclass in risk_management/config.py
- **File**: src/trading_bot/risk_management/config.py
- **Fields**:
  - account_risk_pct: float = 1.0 (max risk per trade % of account)
  - min_risk_reward_ratio: float = 2.0 (minimum R:R ratio)
  - default_stop_pct: float = 2.0 (fallback stop % below entry)
  - trailing_enabled: bool = True
  - pullback_lookback_candles: int = 20
  - trailing_breakeven_threshold: float = 0.5 (move to BE at 50% to target)
  - strategy_overrides: Dict[str, Any] = field(default_factory=dict)
- **Validation**: All risk parameters positive, min_risk_reward_ratio ≥ 1.0, percentages ≤ 100
- **Pattern**: src/trading_bot/config.py OrderManagementConfig (lines 25-127)
- **From**: plan.md [SCHEMA]

T004 [P] Extend Config to include risk_management section
- **File**: src/trading_bot/config.py
- **Add field**: risk_management: RiskManagementConfig = field(default_factory=RiskManagementConfig)
- **Validation**: Call RiskManagementConfig validation in Config.__post_init__
- **Pattern**: Existing order_management: OrderManagementConfig field
- **From**: plan.md [RESEARCH DECISIONS] - Configuration via risk_management section

---

## Phase 3.2: Models (Data Structures)

T005 [P] Create PositionPlan dataclass in risk_management/models.py
- **File**: src/trading_bot/risk_management/models.py
- **Fields**:
  - symbol: str
  - entry_price: Decimal
  - stop_price: Decimal
  - target_price: Decimal
  - quantity: int
  - risk_amount: Decimal (dollar amount at risk)
  - reward_amount: Decimal (dollar amount at target)
  - reward_ratio: float (actual R:R ratio, e.g., 2.0)
  - pullback_source: str ("detected" | "default")
  - pullback_price: Optional[Decimal] = None
  - created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
- **Pattern**: src/trading_bot/order_management/models.py OrderRequest dataclass
- **From**: plan.md [SCHEMA]

T006 [P] Create RiskManagementEnvelope dataclass in risk_management/models.py
- **File**: src/trading_bot/risk_management/models.py
- **Fields**:
  - position_plan: PositionPlan
  - entry_order_id: str
  - stop_order_id: str
  - target_order_id: str
  - status: str ("pending" | "active" | "stopped" | "target_hit" | "cancelled")
  - adjustments: List[Dict[str, Any]] = field(default_factory=list)
  - created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
  - updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
- **Pattern**: src/trading_bot/order_management/models.py OrderEnvelope
- **From**: plan.md [SCHEMA]

T007 [P] Create PullbackData dataclass in risk_management/models.py
- **File**: src/trading_bot/risk_management/models.py
- **Fields**:
  - pullback_price: Decimal
  - pullback_timestamp: datetime
  - confirmation_candles: int (number of confirming candles)
  - lookback_window: int (candles analyzed)
  - fallback_used: bool (True if default % used)
- **Pattern**: src/trading_bot/order_management/models.py dataclass pattern
- **From**: plan.md [SCHEMA]

---

## Phase 3.3: RED - Write Failing Tests

T008 [RED] Write failing test: PullbackAnalyzer identifies swing low with confirmation
- **File**: tests/risk_management/test_pullback_analyzer.py
- **Test**: test_identify_swing_low_with_confirmation()
- **Given**: Price data with swing low at $248.00, confirmed by 2 higher lows
- **When**: analyze_pullback(price_data, lookback_candles=20)
- **Then**: Returns PullbackData with pullback_price=$248.00, confirmation_candles=2, fallback_used=False
- **Pattern**: tests/order_management/test_manager.py test structure
- **From**: spec.md FR-014, plan.md smoke test scenario 1

T009 [RED] Write failing test: PullbackAnalyzer falls back to default % when no swing low
- **File**: tests/risk_management/test_pullback_analyzer.py
- **Test**: test_fallback_to_default_when_no_pullback()
- **Given**: Price data showing strong uptrend, no pullback in 20 candles
- **When**: analyze_pullback(price_data, default_stop_pct=2.0, entry_price=150.00)
- **Then**: Returns PullbackData with pullback_price=$147.00 (2% below entry), fallback_used=True
- **From**: spec.md FR-002, plan.md smoke test scenario 2

T010 [RED] Write failing test: Calculator computes position size with pullback stop
- **File**: tests/risk_management/test_calculator.py
- **Test**: test_calculate_position_size_with_pullback()
- **Given**: entry_price=$250.30, stop_price=$248.00, account_balance=$100,000, account_risk_pct=1.0%
- **When**: calculate_position_plan(symbol="TSLA", entry_price, stop_price, target_rr=2.0, account_balance, risk_pct)
- **Then**: Returns PositionPlan with quantity=434 shares, risk_amount=$1,000, target_price=$254.90, reward_ratio=2.0
- **REUSE**: src/trading_bot/safety_checks.py calculate_position_size() as foundation
- **From**: spec.md FR-003, plan.md smoke test scenario 1

T011 [RED] Write failing test: Calculator validates stop distance (min 0.5%, max 10%)
- **File**: tests/risk_management/test_calculator.py
- **Test**: test_validate_stop_distance_bounds()
- **Given**: entry_price=$100.00
- **When**: calculate_position_plan with stop_price=$99.50 (0.5% - valid), $99.40 (0.6% - invalid), $89.00 (11% - invalid)
- **Then**: Raises PositionPlanningError for stops <0.5% or >10% of entry
- **From**: spec.md FR-005, plan.md [SECURITY]

T012 [RED] Write failing test: Calculator validates stop below entry for long positions
- **File**: tests/risk_management/test_calculator.py
- **Test**: test_stop_must_be_below_entry_for_longs()
- **Given**: entry_price=$250.30, stop_price=$251.00 (above entry)
- **When**: calculate_position_plan(...)
- **Then**: Raises PositionPlanningError("Stop price must be below entry for long positions")
- **From**: spec.md FR-013, plan.md [SECURITY]

T013 [RED] Write failing test: Calculator enforces minimum risk-reward ratio
- **File**: tests/risk_management/test_calculator.py
- **Test**: test_enforce_minimum_risk_reward_ratio()
- **Given**: entry=$100, stop=$98 (2% risk), target=$101 (1% reward), min_rr=2.0
- **When**: calculate_position_plan with target_rr=0.5 (below minimum)
- **Then**: Raises PositionPlanningError("Risk-reward ratio 0.5 below minimum 2.0")
- **From**: spec.md FR-006, plan.md [SCHEMA]

T014 [RED] Write failing test: RiskManager places entry, stop, and target orders
- **File**: tests/risk_management/test_manager.py
- **Test**: test_place_trade_with_risk_management()
- **Given**: PositionPlan with entry=$250.30, stop=$248.00, target=$254.90, quantity=434
- **When**: place_trade_with_risk_management(plan, symbol="TSLA")
- **Then**:
  - Calls OrderManager.place_limit_buy(symbol="TSLA", price=250.30, quantity=434)
  - Calls OrderManager.place_limit_sell(symbol="TSLA", price=248.00, quantity=434) for stop
  - Calls OrderManager.place_limit_sell(symbol="TSLA", price=254.90, quantity=434) for target
  - Returns RiskManagementEnvelope with 3 order IDs
- **Mock**: OrderManager dependency
- **REUSE**: OrderManager.place_limit_buy(), place_limit_sell()
- **From**: spec.md FR-001, plan.md smoke test scenario 3

T015 [RED] Write failing test: RiskManager logs position plan to JSONL
- **File**: tests/risk_management/test_manager.py
- **Test**: test_log_position_plan_to_jsonl()
- **Given**: PositionPlan created
- **When**: calculate_position_with_stop(...) completes
- **Then**: logs/risk-management.jsonl contains entry with:
  - action="position_plan_created"
  - symbol, entry_price, stop_price, target_price, quantity, risk_amount, reward_ratio, pullback_source
- **Pattern**: src/trading_bot/logging/structured_logger.py JSONL logging
- **From**: plan.md [RESEARCH DECISIONS] - JSONL logging

T016 [RED] Write failing test: StopAdjuster moves stop to breakeven at 50% progress
- **File**: tests/risk_management/test_stop_adjuster.py
- **Test**: test_adjust_to_breakeven_at_50_percent()
- **Given**: Position with entry=$250.30, stop=$248.00, target=$254.90 (distance to target=$4.60)
- **When**: current_price=$252.60 (50% progress: entry + $4.60 * 0.5 = $252.60)
- **Then**:
  - Returns new_stop_price=$250.30 (breakeven)
  - adjustment_reason="moved to breakeven - price reached 50% of target"
- **From**: spec.md FR-007, plan.md [RESEARCH DECISIONS]

T017 [RED] Write failing test: StopAdjuster respects trailing_enabled=False
- **File**: tests/risk_management/test_stop_adjuster.py
- **Test**: test_no_adjustment_when_trailing_disabled()
- **Given**: Config with trailing_enabled=False, price at 50% progress
- **When**: should_adjust_stop(current_price, position_plan)
- **Then**: Returns False (no adjustment)
- **From**: spec.md FR-007, plan.md [SCHEMA] RiskManagementConfig

T018 [RED] Write failing test: TargetMonitor detects target fill and triggers cleanup
- **File**: tests/risk_management/test_target_monitor.py
- **Test**: test_detect_target_fill_and_cleanup()
- **Given**: Position with target_order_id="ORDER123"
- **When**: poll_order_status() detects order status="filled"
- **Then**:
  - Calls OrderManager.cancel_order(stop_order_id)
  - Logs to risk-management.jsonl with action="target_hit"
  - Calls AccountData.invalidate_cache()
  - Returns position_closed=True
- **Mock**: OrderManager.get_order_status(), cancel_order()
- **REUSE**: OrderManager for order status polling
- **From**: spec.md FR-009, plan.md smoke test scenario 5

T019 [RED] Write failing test: TargetMonitor detects stop fill and triggers cleanup
- **File**: tests/risk_management/test_target_monitor.py
- **Test**: test_detect_stop_fill_and_cleanup()
- **Given**: Position with stop_order_id="ORDER456"
- **When**: poll_order_status() detects stop filled
- **Then**:
  - Calls OrderManager.cancel_order(target_order_id)
  - Logs action="stop_hit"
  - Returns position_closed=True
- **From**: spec.md FR-010, plan.md TargetMonitor responsibilities

T020 [RED] Write failing test: RiskManager cancels entry if stop placement fails
- **File**: tests/risk_management/test_manager.py
- **Test**: test_cancel_entry_on_stop_placement_failure()
- **Given**: Entry order submitted, stop placement raises StopPlacementError
- **When**: place_trade_with_risk_management(plan)
- **Then**:
  - Calls OrderManager.cancel_order(entry_order_id)
  - Logs error with correlation_id
  - Raises StopPlacementError
- **From**: spec.md FR-003 guardrail, plan.md [SECURITY]

---

## Phase 3.4: GREEN - Minimal Implementation

T021 [GREEN→T008] Implement PullbackAnalyzer.analyze_pullback() with swing low detection
- **File**: src/trading_bot/risk_management/pullback_analyzer.py
- **Method**: analyze_pullback(price_data: List[Dict], lookback_candles: int, default_stop_pct: float, entry_price: Decimal) -> PullbackData
- **Logic**:
  - Scan last N candles for swing low (price[i] < price[i-1] and price[i] < price[i+1])
  - Count confirmation candles (higher lows after swing low)
  - If swing low with ≥2 confirmations found: return detected pullback
  - Else: fallback to entry_price * (1 - default_stop_pct/100)
- **Complexity**: O(N) where N=lookback_candles
- **From**: plan.md [RESEARCH DECISIONS] - Pullback analysis uses swing low detection

T022 [GREEN→T009] Add fallback logic to PullbackAnalyzer for uptrend scenarios
- **File**: src/trading_bot/risk_management/pullback_analyzer.py
- **Enhancement**: Handle no-pullback case with default_stop_pct fallback
- **Logging**: logger.warning("No pullback detected - using default {default_stop_pct}% stop")
- **Return**: PullbackData with fallback_used=True
- **From**: spec.md FR-002

T023 [GREEN→T010] Implement RiskRewardCalculator.calculate_position_plan()
- **File**: src/trading_bot/risk_management/calculator.py
- **Method**: calculate_position_plan(symbol: str, entry_price: Decimal, stop_price: Decimal, target_rr: float, account_balance: Decimal, risk_pct: float) -> PositionPlan
- **Steps**:
  1. Calculate risk per share: entry_price - stop_price
  2. Calculate risk_amount: account_balance * (risk_pct / 100)
  3. Calculate quantity: int(risk_amount / risk_per_share)
  4. Calculate target_price: entry_price + (entry_price - stop_price) * target_rr
  5. Calculate reward_amount: quantity * (target_price - entry_price)
  6. Calculate actual reward_ratio: reward_amount / risk_amount
- **REUSE**: Extend src/trading_bot/safety_checks.py calculate_position_size() logic
- **From**: plan.md [RESEARCH DECISIONS] - Reuse calculate_position_size foundation

T024 [GREEN→T011,T012,T013] Add validation methods to RiskRewardCalculator
- **File**: src/trading_bot/risk_management/calculator.py
- **Methods**:
  - validate_stop_distance(entry: Decimal, stop: Decimal) -> None: Raise if stop distance <0.5% or >10%
  - validate_stop_direction(entry: Decimal, stop: Decimal, position_type: str) -> None: Raise if stop above entry for longs
  - validate_risk_reward_ratio(actual_rr: float, min_rr: float) -> None: Raise if below minimum
- **Raises**: PositionPlanningError with descriptive messages
- **Call in**: calculate_position_plan() before returning PositionPlan
- **From**: spec.md FR-005, FR-006, FR-013

T025 [GREEN→T014] Implement RiskManager.place_trade_with_risk_management()
- **File**: src/trading_bot/risk_management/manager.py
- **Method**: place_trade_with_risk_management(plan: PositionPlan, symbol: str) -> RiskManagementEnvelope
- **Dependencies**: OrderManager (constructor injection)
- **Steps**:
  1. Submit entry order: entry_order_id = self.order_manager.place_limit_buy(symbol, plan.entry_price, plan.quantity)
  2. Try to submit stop order: stop_order_id = self.order_manager.place_limit_sell(symbol, plan.stop_price, plan.quantity)
  3. Try to submit target order: target_order_id = self.order_manager.place_limit_sell(symbol, plan.target_price, plan.quantity)
  4. Create RiskManagementEnvelope with order IDs, status="pending"
  5. Return envelope
- **Error handling**: If stop/target placement fails, cancel entry order (T020)
- **REUSE**: OrderManager.place_limit_buy(), place_limit_sell()
- **From**: plan.md [ARCHITECTURE] - RiskManager orchestrates, delegates to OrderManager

T026 [GREEN→T015] Add JSONL logging to RiskManager
- **File**: src/trading_bot/risk_management/manager.py
- **Add**: self.logger = StructuredTradeLogger("logs/risk-management.jsonl")
- **Log events**:
  - position_plan_created (in calculate_position_with_stop)
  - stop_placed, target_placed (in place_trade_with_risk_management)
  - stop_adjusted (in adjust_trailing_stop)
  - target_hit, stop_hit (callbacks from TargetMonitor)
- **Format**: JSON with timestamp, session_id, action, symbol, prices, quantities, correlation_id
- **REUSE**: src/trading_bot/logging/structured_logger.py StructuredTradeLogger
- **From**: plan.md [RESEARCH DECISIONS] - JSONL logging for audit trail

T027 [GREEN→T016] Implement StopAdjuster.calculate_adjustment()
- **File**: src/trading_bot/risk_management/stop_adjuster.py
- **Method**: calculate_adjustment(current_price: Decimal, position_plan: PositionPlan, config: RiskManagementConfig) -> Optional[Tuple[Decimal, str]]
- **Logic**:
  - If trailing_enabled=False: return None
  - Calculate progress: (current_price - entry_price) / (target_price - entry_price)
  - If progress >= trailing_breakeven_threshold (default 0.5): return (entry_price, "moved to breakeven - price reached 50% of target")
  - Else: return None
- **From**: plan.md [RESEARCH DECISIONS] - Trailing stop at 50% progress

T028 [GREEN→T017] Add trailing_enabled check in StopAdjuster
- **File**: src/trading_bot/risk_management/stop_adjuster.py
- **Enhancement**: Return None early if config.trailing_enabled=False
- **From**: spec.md FR-007

T029 [GREEN→T018,T019] Implement TargetMonitor.poll_and_handle_fills()
- **File**: src/trading_bot/risk_management/target_monitor.py
- **Method**: poll_and_handle_fills(envelope: RiskManagementEnvelope) -> bool
- **Dependencies**: OrderManager (for get_order_status, cancel_order), AccountData (for invalidate_cache)
- **Steps**:
  1. Poll target order status: target_status = self.order_manager.get_order_status(envelope.target_order_id)
  2. If target filled: cancel stop order, log "target_hit", invalidate account cache, return True
  3. Poll stop order status: stop_status = self.order_manager.get_order_status(envelope.stop_order_id)
  4. If stop filled: cancel target order, log "stop_hit", invalidate account cache, return True
  5. Else: return False
- **REUSE**: OrderManager.get_order_status(), cancel_order(), AccountData.invalidate_cache()
- **From**: plan.md [NEW INFRASTRUCTURE] - TargetMonitor polls for fills

T030 [GREEN→T020] Add error handling to RiskManager.place_trade_with_risk_management()
- **File**: src/trading_bot/risk_management/manager.py
- **Enhancement**: Wrap stop/target placement in try-except
- **Error path**:
  ```python
  try:
      stop_order_id = self.order_manager.place_limit_sell(...)
      target_order_id = self.order_manager.place_limit_sell(...)
  except Exception as e:
      self.order_manager.cancel_order(entry_order_id)
      self.logger.log_error(correlation_id, e)
      raise StopPlacementError(f"Failed to place stop/target: {e}")
  ```
- **From**: spec.md FR-003 guardrail

---

## Phase 3.5: REFACTOR - Clean Up

T031 [REFACTOR] Extract position size calculation to separate method
- **File**: src/trading_bot/risk_management/calculator.py
- **Refactor**: Extract calculate_position_plan steps 1-3 into _calculate_shares() private method
- **Benefit**: Single responsibility - separate position sizing from target calculation
- **Tests**: Ensure all calculator tests still pass
- **From**: Clean code principles

T032 [REFACTOR] Create RiskManager.calculate_position_with_stop() high-level method
- **File**: src/trading_bot/risk_management/manager.py
- **Method**: calculate_position_with_stop(symbol: str, entry_price: Decimal, account_balance: Decimal, account_risk_pct: float, price_data: List[Dict]) -> PositionPlan
- **Orchestrates**:
  1. Call PullbackAnalyzer.analyze_pullback(price_data) to get stop_price
  2. Call RiskRewardCalculator.calculate_position_plan(entry, stop, target_rr, balance, risk_pct)
  3. Log position plan to JSONL
  4. Return PositionPlan
- **Benefit**: Single entry point for position planning logic
- **From**: plan.md [INTEGRATION SCENARIOS] usage pattern

T033 [REFACTOR] Add comprehensive logging with correlation IDs
- **File**: src/trading_bot/risk_management/manager.py
- **Enhancement**: Generate correlation_id (UUID) for each position, include in all log entries
- **Benefit**: Trace complete lifecycle (plan → entry → stop → target → fill) in JSONL logs
- **Pattern**: src/trading_bot/logging/structured_logger.py correlation_id usage
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] - audit trail requirement

---

## Phase 3.6: Integration & Testing

T034 [P] Write integration test: End-to-end position lifecycle
- **File**: tests/risk_management/test_integration.py
- **Test**: test_full_position_lifecycle_with_target_fill()
- **Scenario**:
  1. Calculate position plan with pullback detection
  2. Place trade with stop and target orders
  3. Simulate price movement to 50% target (trigger trailing stop)
  4. Simulate target fill (cleanup stop order)
  5. Verify JSONL log contains complete audit trail
- **Mocks**: OrderManager API calls, AccountData responses
- **From**: plan.md [INTEGRATION SCENARIOS]

T035 [P] Write integration test: Stop-out scenario
- **File**: tests/risk_management/test_integration.py
- **Test**: test_full_position_lifecycle_with_stop_fill()
- **Scenario**:
  1. Calculate position plan
  2. Place trade
  3. Simulate stop order fill
  4. Verify target order cancelled
  5. Verify risk-management.jsonl contains stop_hit event
- **From**: spec.md FR-010

T036 [P] Add performance test: Position plan calculation ≤200ms
- **File**: tests/risk_management/test_performance.py
- **Test**: test_position_plan_calculation_performance()
- **Benchmark**: 100 iterations of calculate_position_with_stop(), assert avg time ≤200ms
- **From**: spec.md NFR-001

T037 [P] Integrate RiskManager into TradingBot.execute_trade (live mode)
- **File**: src/trading_bot/bot.py
- **Integration**:
  ```python
  def execute_trade(self, symbol: str, action: str, price: float):
      if self.config.paper_trading:
          # Existing paper trading flow (unchanged)
          pass
      else:
          # NEW: Live trading with risk management
          price_data = self.market_data.get_recent_candles(symbol, limit=20)

          position_plan = self.risk_manager.calculate_position_with_stop(
              symbol=symbol,
              entry_price=Decimal(str(price)),
              account_balance=self.account_data.get_buying_power(),
              account_risk_pct=self.config.risk_management.account_risk_pct,
              price_data=price_data
          )

          envelope = self.risk_manager.place_trade_with_risk_management(
              plan=position_plan,
              symbol=symbol
          )

          # Start monitoring for fills
          self.target_monitor.register_position(envelope)
  ```
- **Constructor**: Add self.risk_manager = RiskManager(order_manager, logger, config)
- **From**: plan.md [INTEGRATION SCENARIOS] scenario 4

---

## Phase 3.7: Error Handling & Resilience

T038 [RED] Write test: Retry transient broker failures with exponential backoff
- **File**: tests/risk_management/test_manager.py
- **Test**: test_retry_on_transient_stop_placement_failure()
- **Given**: First stop placement call raises RetriableError (network timeout)
- **When**: place_trade_with_risk_management()
- **Then**: Retries up to 3 times with exponential backoff, succeeds on retry 2
- **Pattern**: src/trading_bot/error_handling/retry.py @retry_on_transient_failure decorator
- **From**: plan.md [ARCHITECTURE] - Retry logic reuses error_handling decorators

T039 [GREEN→T038] Apply @retry_on_transient_failure to order placement methods
- **File**: src/trading_bot/risk_management/manager.py
- **Decorator**: @retry_on_transient_failure(max_attempts=3, backoff_seconds=1)
- **Apply to**: place_trade_with_risk_management(), adjust_trailing_stop()
- **REUSE**: src/trading_bot/error_handling/retry.py decorator
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T040 [P] Add circuit breaker integration for stop placement failures
- **File**: src/trading_bot/risk_management/manager.py
- **Integration**: Track stop placement failure rate, trigger SafetyChecks circuit breaker if failures >2%
- **Pattern**: src/trading_bot/error_handling/circuit_breaker.py
- **From**: spec.md guardrail, plan.md [SECURITY]

---

## Phase 3.8: Deployment Preparation

T041 [P] Add config migration instructions to NOTES.md
- **File**: specs/stop-loss-automation/NOTES.md
- **Section**: "Configuration Setup"
- **Instructions**:
  ```json
  // Add to config.json
  {
    "risk_management": {
      "account_risk_pct": 1.0,
      "min_risk_reward_ratio": 2.0,
      "default_stop_pct": 2.0,
      "trailing_enabled": true,
      "pullback_lookback_candles": 20,
      "trailing_breakeven_threshold": 0.5,
      "strategy_overrides": {}
    }
  }
  ```
- **From**: plan.md [CI/CD IMPACT]

T042 [P] Document rollback procedure in NOTES.md
- **File**: specs/stop-loss-automation/NOTES.md
- **Section**: "Rollback Runbook"
- **Steps**:
  1. Stop bot (systemctl stop trading-bot)
  2. Manually close any live positions with active stops/targets via Robinhood UI
  3. Git revert to previous commit
  4. Remove risk_management section from config.json
  5. Restart bot in paper trading mode (paper_trading: true)
  6. Verify logs show paper trading active
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] rollback plan

T043 [P] Add smoke test script: test_risk_management_smoke.py
- **File**: tests/smoke/test_risk_management_smoke.py
- **Tests**:
  - test_config_loads_risk_management_section()
  - test_calculate_position_plan_with_mock_data()
  - test_jsonl_logging_works()
- **Execution time**: <90 seconds total
- **From**: plan.md [CI/CD IMPACT] smoke tests

---

## Summary

**Total Tasks**: 43
- Phase 3.1 (Setup): 4 tasks (T001-T004)
- Phase 3.2 (Models): 3 tasks (T005-T007)
- Phase 3.3 (RED Tests): 13 tasks (T008-T020)
- Phase 3.4 (GREEN Implementation): 10 tasks (T021-T030)
- Phase 3.5 (REFACTOR): 3 tasks (T031-T033)
- Phase 3.6 (Integration): 4 tasks (T034-T037)
- Phase 3.7 (Error Handling): 3 tasks (T038-T040)
- Phase 3.8 (Deployment): 3 tasks (T041-T043)

**TDD Coverage**: 13 RED tests → 10 GREEN implementations → 3 REFACTOR cleanups = 26 TDD tasks (60%)

**Reuse Opportunities**: 7 existing components (OrderManager, SafetyChecks, AccountData, TradeRecord, StructuredTradeLogger, error hierarchy, retry decorators)

**Dependencies**:
- Models (T005-T007) must complete before RED tests (T008-T020)
- RED tests (T008-T020) must complete before GREEN implementations (T021-T030)
- GREEN implementations must complete before REFACTOR (T031-T033)
- Integration tests (T034-T037) require completed implementations

**Parallel Execution**:
- T001-T004 can run in parallel (different files)
- T005-T007 can run in parallel (same file, different classes)
- T008-T020 can run in parallel (different test files)
- T021-T030 dependencies: T021→T008, T022→T009, T023→T010, T024→T011/T012/T013, etc.
