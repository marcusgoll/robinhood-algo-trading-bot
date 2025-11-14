# Implementation Plan: Automated Stop Loss and Targets

## [RESEARCH DECISIONS]

### Decision: Two-Tier Architecture (RiskManager + OrderManager)
- **Decision**: Create RiskManager service that orchestrates risk logic and delegates broker communication to OrderManager
- **Rationale**: Separation of concerns - risk intelligence (pullback analysis, position sizing, trailing stops) is distinct from order execution (broker API calls, retries, status tracking)
- **Alternatives**: Monolithic service embedding broker calls (rejected - violates single responsibility, makes testing harder)
- **Source**: specs/order-management/spec.md demonstrates OrderManager already provides limit order submission/cancellation

### Decision: Reuse SafetyChecks.calculate_position_size Foundation
- **Decision**: Extend existing calculate_position_size() to accept pullback data and return enhanced PositionPlan
- **Rationale**: Function already exists with correct signature (entry_price, stop_loss_price, account_balance) - avoid duplication
- **Alternatives**: Create new RiskRewardCalculator from scratch (rejected - introduces parallel position sizing logic)
- **Source**: src/trading_bot/safety_checks.py:311-350

### Decision: Pullback Analysis Uses Technical Swing Low Detection
- **Decision**: Implement PullbackAnalyzer that identifies swing lows from recent price data (last N candles with confirmation)
- **Rationale**: Aligns with Constitution §Risk_Management requirement for invalidation point identification; more adaptive than fixed percentage
- **Alternatives**: Fixed percentage only (rejected - less adaptive to market structure), ATR-based stops (deferred - adds complexity)
- **Source**: specs/stop-loss-automation/spec.md FR-014, roadmap requirement

### Decision: JSONL Logging for Risk Management Audit Trail
- **Decision**: Persist all risk decisions to logs/risk-management.jsonl following existing structured logging pattern
- **Rationale**: Matches trade-logging module pattern; append-only immutable audit; easy querying for retrospectives
- **Alternatives**: Database storage (rejected - adds dependency), in-memory only (rejected - no audit trail)
- **Source**: src/trading_bot/logging/structured_logger.py pattern

### Decision: Configuration via risk_management Section in Config
- **Decision**: Mirror OrderManagementConfig pattern with global defaults + strategy_overrides
- **Rationale**: Proven pattern for configuration extension; supports per-strategy customization
- **Alternatives**: Hardcoded constants (rejected - inflexible), separate config file (rejected - fragments config)
- **Source**: src/trading_bot/config.py:25-127 (OrderManagementConfig implementation)

### Decision: Dataclass-Based Models for Type Safety
- **Decision**: Use @dataclass for PositionPlan, RiskManagementEnvelope, PullbackData with type hints
- **Rationale**: Codebase convention (OrderRequest, OrderEnvelope, TradeRecord all use dataclasses); free validation and immutability
- **Alternatives**: Plain dicts (rejected - no type safety), Pydantic (rejected - adds dependency)
- **Source**: src/trading_bot/order_management/models.py pattern

### Decision: Trailing Stop Adjustment at 50% Progress to Target
- **Decision**: Move stop to breakeven when price reaches 50% of distance to target (configurable threshold)
- **Rationale**: Balances risk elimination (protect capital) with target achievement (avoid premature exits)
- **Alternatives**: Immediate breakeven (rejected - too aggressive), ATR trailing (deferred - complexity)
- **Source**: specs/stop-loss-automation/spec.md FR-007

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11+ (existing codebase)
- Dependencies: robin_stocks (broker API - reuse), pytz (timezone - reuse), dataclasses (type safety - stdlib)
- No new external dependencies required

**Patterns**:
- Service Layer: RiskManager orchestrates, delegates to OrderManager for broker communication
- Repository Pattern: JSONL logging with structured records (matches trade-logging module)
- Dependency Injection: RiskManager receives OrderManager, SafetyChecks, AccountData, Config as constructor params
- Error Hierarchy: Domain exceptions (PositionPlanningError, StopPlacementError) extend from base classes
- Retry Logic: Reuse error_handling decorators for transient broker failures

**Module Structure**:
```
src/trading_bot/risk_management/
├── __init__.py              # Package exports
├── manager.py               # RiskManager service (orchestrator)
├── pullback_analyzer.py     # PullbackAnalyzer (swing low detection)
├── calculator.py            # Position size + risk-reward formulas
├── stop_adjuster.py         # StopAdjuster (trailing stop logic)
├── target_monitor.py        # TargetMonitor (fill detection callbacks)
├── models.py                # Dataclasses (PositionPlan, RiskManagementEnvelope, PullbackData)
├── exceptions.py            # Domain exceptions (PositionPlanningError, etc.)
└── config.py                # RiskManagementConfig dataclass
```

**Integration Points**:
- OrderManager: Submit stop-loss and target orders (place_limit_sell)
- SafetyChecks: Validate position sizes, register pending orders
- AccountData: Query buying power, invalidate caches on fills
- TradeRecord: Log position closures with realized P&L
- Config: Load risk_management settings with validation

**Dependencies** (new packages required):
- None (reuses existing dependencies)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── risk_management/              # NEW: Risk management package
│   ├── __init__.py
│   ├── manager.py                # RiskManager service
│   ├── pullback_analyzer.py      # Swing low detection
│   ├── calculator.py             # Position size + R:R calculations
│   ├── stop_adjuster.py          # Trailing stop adjustments
│   ├── target_monitor.py         # Fill monitoring + callbacks
│   ├── models.py                 # Dataclasses
│   ├── exceptions.py             # Domain exceptions
│   └── config.py                 # RiskManagementConfig
├── config.py                     # EXTEND: Add risk_management section
├── safety_checks.py              # EXTEND: calculate_position_size enhancement
└── bot.py                        # INTEGRATE: Wire RiskManager into execute_trade

tests/risk_management/
├── test_manager.py               # RiskManager orchestration tests
├── test_pullback_analyzer.py     # Swing low detection tests
├── test_calculator.py            # Position size calculation tests
├── test_stop_adjuster.py         # Trailing stop logic tests
├── test_target_monitor.py        # Fill callback tests
└── test_integration.py           # End-to-end scenario tests

logs/
├── risk-management.jsonl         # NEW: Risk decision audit log
└── orders.jsonl                  # REUSE: Order submission log
```

**Module Organization**:
- **manager.py**: RiskManager - calculate_position_with_stop(), place_trade_with_risk_management(), adjust_trailing_stop()
- **pullback_analyzer.py**: PullbackAnalyzer - identify_swing_low() with confirmation logic
- **calculator.py**: Position sizing formulas, risk-reward calculations, validation
- **stop_adjuster.py**: Trailing stop logic (breakeven at 50%, 1:1 at target)
- **target_monitor.py**: Poll order status, detect fills, trigger callbacks
- **models.py**: PositionPlan, RiskManagementEnvelope, PullbackData, RiskManagementConfig dataclasses
- **exceptions.py**: PositionPlanningError, StopPlacementError, TargetAdjustmentError

---

## [SCHEMA]

**No Database Tables** (backend-only with JSONL persistence)

**API Schemas** (Python dataclasses):

```python
@dataclass
class PositionPlan:
    """Position planning result with stop-loss and target prices."""
    symbol: str
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    quantity: int
    risk_amount: Decimal           # Dollar amount at risk
    reward_amount: Decimal          # Dollar amount at target
    reward_ratio: float             # Actual R:R ratio (e.g., 2.0)
    pullback_source: str            # "detected" | "default"
    pullback_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass
class RiskManagementEnvelope:
    """Execution record storing order IDs and status."""
    position_plan: PositionPlan
    entry_order_id: str
    stop_order_id: str
    target_order_id: str
    status: str                     # "pending" | "active" | "stopped" | "target_hit" | "cancelled"
    adjustments: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass
class PullbackData:
    """Pullback analysis result."""
    pullback_price: Decimal
    pullback_timestamp: datetime
    confirmation_candles: int       # Number of confirming candles
    lookback_window: int            # Candles analyzed
    fallback_used: bool             # True if default % used

@dataclass
class RiskManagementConfig:
    """Risk management configuration."""
    account_risk_pct: float = 1.0           # Max risk per trade (% of account)
    min_risk_reward_ratio: float = 2.0      # Minimum R:R ratio
    default_stop_pct: float = 2.0           # Fallback stop % below entry
    trailing_enabled: bool = True           # Enable trailing stops
    pullback_lookback_candles: int = 20     # Swing low lookback window
    trailing_breakeven_threshold: float = 0.5  # Move to BE at 50% to target
    strategy_overrides: Dict[str, Any] = field(default_factory=dict)
```

**JSONL Log Format** (logs/risk-management.jsonl):
```json
{
  "timestamp": "2025-10-15T14:32:15.123Z",
  "session_id": "abc123",
  "action": "position_plan_created",
  "symbol": "TSLA",
  "entry_price": 250.30,
  "stop_price": 248.00,
  "target_price": 254.90,
  "quantity": 434,
  "risk_amount": 1000.00,
  "reward_amount": 2000.00,
  "reward_ratio": 2.0,
  "pullback_source": "detected",
  "pullback_price": 248.00
}
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Position plan calculation (including pullback analysis) completes in ≤200ms
- NFR-002: Stop-loss and target orders placed within 1 second of entry fill confirmation
- NFR-003: Trailing stop adjustments execute within 10 seconds of price threshold breach
- NFR-008: Position size calculations accurate to ±1 share, risk variance ≤0.1%

**Computational Complexity**:
- Pullback analysis: O(N) where N = lookback_candles (default 20) - linear scan for swing lows
- Position size calculation: O(1) - simple arithmetic
- Risk-reward validation: O(1) - comparison checks

**Optimization Strategies**:
- Cache pullback analysis results for repeated calls with same price data
- Pre-validate config on initialization to avoid runtime validation overhead
- Batch order submissions (entry + stop + target) to reduce latency

---

## [SECURITY]

**Authentication Strategy**:
- Reuse existing RobinhoodAuth.login() - no changes required
- RiskManager depends on authenticated OrderManager instance

**Authorization Model**:
- No authorization layer (local trading bot, single operator)
- Safety enforced via Config validation and SafetyChecks integration

**Input Validation**:
- Position plan validation: Reject stop distance <0.5% or >10% of entry price (FR-005)
- Stop price validation: Must be below entry for long positions (FR-013)
- Quantity validation: Must not exceed available buying power (FR-003)
- Config validation: All risk parameters must be positive, ratios must be ≥1.0

**Data Protection**:
- Mask sensitive data in logs (account balance → "****", entry price → rounded)
- JSONL logs readable only by bot operator (file system permissions)
- No PII stored (symbol and prices only)

**Error Handling**:
- Circuit breaker integration: Stop placement failures >2% trigger SafetyChecks circuit breaker (spec.md guardrail)
- Fail-safe design: Order placement errors cancel entry order if unfilled (FR-003)
- Graceful degradation: Fallback to default stop % if pullback detection fails (FR-002)

---

## [EXISTING INFRASTRUCTURE - REUSE] (6 components)

**Services/Modules**:
- **OrderManager** (src/trading_bot/order_management/manager.py): Submit stop-loss and target orders via place_limit_sell(), cancel orders, track status
- **SafetyChecks** (src/trading_bot/safety_checks.py): Position size calculation foundation (calculate_position_size), validate trades, register pending orders
- **AccountData** (src/trading_bot/account/account_data.py): Query buying power, invalidate caches on fills/cancellations
- **TradeRecord** (src/trading_bot/logging/trade_record.py): Log trade outcomes with realized P&L

**Configuration Patterns**:
- **OrderManagementConfig** (src/trading_bot/config.py:25-127): Pattern for global defaults + strategy_overrides

**Error Handling**:
- **Error hierarchy** (src/trading_bot/error_handling/exceptions.py): RetriableError, NonRetriableError base classes for domain exceptions
- **Retry decorators** (src/trading_bot/error_handling/retry.py): Transient failure handling for broker API calls

**Logging**:
- **StructuredTradeLogger** (src/trading_bot/logging/structured_logger.py): JSONL logging pattern with daily rotation, thread-safe writes

---

## [NEW INFRASTRUCTURE - CREATE] (8 components)

**Backend Services**:
- **RiskManager** (src/trading_bot/risk_management/manager.py): Orchestrator for risk logic - calculate_position_with_stop(), place_trade_with_risk_management(), adjust_trailing_stop()
- **PullbackAnalyzer** (src/trading_bot/risk_management/pullback_analyzer.py): Identify swing lows from price data with confirmation logic
- **RiskRewardCalculator** (src/trading_bot/risk_management/calculator.py): Position sizing formulas, target price calculations, validation
- **StopAdjuster** (src/trading_bot/risk_management/stop_adjuster.py): Trailing stop adjustment logic (breakeven, 1:1)
- **TargetMonitor** (src/trading_bot/risk_management/target_monitor.py): Poll for fills, trigger callbacks on stop/target hits

**Models**:
- **risk_management/models.py**: PositionPlan, RiskManagementEnvelope, PullbackData dataclasses
- **risk_management/config.py**: RiskManagementConfig dataclass with validation

**Exceptions**:
- **risk_management/exceptions.py**: PositionPlanningError, StopPlacementError, TargetAdjustmentError domain exceptions

**Logs**:
- **logs/risk-management.jsonl**: Audit trail for position plans, stop placements, trailing adjustments, fills

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Railway API service (reuses existing deployment)
- Env vars: None required (all configuration via risk_management section in config.json)
- Breaking changes: TradingBot.execute_trade live path requires initialized RiskManager; paper trading unchanged
- Migration: Add risk_management block to config.json with recommended defaults

**Build Commands**:
- No changes (Python package, no build step)

**Environment Variables** (update secrets.schema.json):
- No new environment variables required
- Configuration via config.json only

**Database Migrations**:
- None (JSONL logging only, no database)

**Smoke Tests** (for integration validation):
- Test: Calculate position plan with pullback detection
  - Given: Price data with clear swing low at $248.00
  - When: calculate_position_with_stop(symbol="TSLA", entry_price=250.30, account_balance=100000, account_risk_pct=1.0, price_data=...)
  - Then: Returns PositionPlan with stop=$248.00, target=$254.90, quantity=434, risk_amount=$1000

- Test: Place trade with stop and target orders
  - Given: PositionPlan with entry/stop/target
  - When: place_trade_with_risk_management(plan, symbol="TSLA")
  - Then: Submits 3 orders (entry limit buy, stop limit sell, target limit sell), returns RiskManagementEnvelope with order IDs

- Test: Trailing stop adjustment at 50% progress
  - Given: Position with entry=$250.30, stop=$248.00, target=$254.90
  - When: Price moves to $252.60 (50% to target)
  - Then: Cancels old stop, places new stop at breakeven ($250.30), logs adjustment

**Platform Coupling**:
- Railway: No changes (backend-only)
- Dependencies: None (reuses existing robin_stocks, pytz)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- Risk per trade never exceeds configured account_risk_pct (e.g., 1.0%)
- Stop-loss orders placed within 1 second of entry fill (99% compliance)
- Position size calculations accurate to ±1 share
- All risk decisions logged to risk-management.jsonl with correlation IDs

**Smoke Tests** (Given/When/Then):
```gherkin
Scenario: Position plan calculation with pullback detection
  Given price data shows swing low at $248.00
  When calculate_position_with_stop(symbol="TSLA", entry_price=250.30, account_balance=100000, account_risk_pct=1.0, price_data=...)
  Then returns PositionPlan:
    - stop_price = $248.00
    - target_price = $254.90 (2:1 R:R)
    - quantity = 434 shares (risk $1000 over $2.30 distance)
    - pullback_source = "detected"

Scenario: Fallback to default stop when no pullback detected
  Given price data shows strong uptrend with no pullback
  When calculate_position_with_stop(symbol="AAPL", entry_price=150.00, account_balance=100000, account_risk_pct=1.0, price_data=...)
  Then returns PositionPlan:
    - stop_price = $147.00 (2% below entry)
    - target_price = $156.00 (2:1 R:R)
    - pullback_source = "default"
    - logs warning "No pullback detected - using default 2% stop"

Scenario: Stop and target order placement
  Given PositionPlan with entry=$250.30, stop=$248.00, target=$254.90, quantity=434
  When place_trade_with_risk_management(plan, symbol="TSLA")
  Then:
    - Submits entry limit buy at $250.30 for 434 shares
    - Submits stop limit sell at $248.00 for 434 shares
    - Submits target limit sell at $254.90 for 434 shares
    - Returns RiskManagementEnvelope with 3 order IDs
    - Logs to risk-management.jsonl with correlation ID

Scenario: Trailing stop adjustment at 50% progress
  Given position with entry=$250.30, stop=$248.00, target=$254.90
  When price moves to $252.60 (50% to target) and adjust_trailing_stop() called
  Then:
    - Cancels original stop order at $248.00
    - Places new stop order at breakeven $250.30
    - Updates RiskManagementEnvelope with new stop_order_id
    - Logs adjustment with reason "moved to breakeven - price reached 50% of target"

Scenario: Target fill detection and position closure
  Given position with target order at $254.90
  When target order fills (detected by TargetMonitor)
  Then:
    - Cancels remaining stop-loss order
    - Marks position as closed in risk tracking log
    - Calculates realized P&L = +$1996 (434 shares * $4.60 gain)
    - Updates AccountData cache (buying power, positions)
    - Emits completion event to TradeRecord
```

**Rollback Plan**:
- Rollback command: Revert to previous commit, restart bot in paper trading mode
- Config rollback: Remove risk_management section from config.json
- Special considerations: Live positions with active stops/targets must be manually closed before rollback

**Artifact Strategy** (build-once-promote-many):
- Not applicable (local trading bot, no build artifacts)
- Deployment: Git pull + restart Python process

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: Initial Setup
```bash
# Install dependencies (no new dependencies required)
cd api
uv sync

# Add risk_management section to config.json
cat >> config.json <<'EOF'
{
  "risk_management": {
    "account_risk_pct": 1.0,
    "min_risk_reward_ratio": 2.0,
    "default_stop_pct": 2.0,
    "trailing_enabled": true,
    "pullback_lookback_candles": 20,
    "strategy_overrides": {}
  }
}
EOF

# Run initial validation
python -m src.trading_bot.risk_management.manager --validate-config
```

### Scenario 2: TDD Workflow
```bash
# Write failing test first
pytest tests/risk_management/test_pullback_analyzer.py::test_identify_swing_low_with_confirmation -v
# Implement PullbackAnalyzer.identify_swing_low()
# Run test until green
pytest tests/risk_management/test_pullback_analyzer.py -v

# Repeat for each component
pytest tests/risk_management/ -v --cov=src/trading_bot/risk_management --cov-report=term-missing
```

### Scenario 3: Manual Testing
```bash
# Start bot in paper trading mode
python -m src.trading_bot.main --mode=paper

# Trigger position plan calculation (via bot strategy signal)
# Verify logs/risk-management.jsonl contains position plan entry

# Simulate price movement to 50% target
# Verify trailing stop adjustment logged

# Check audit trail
tail -f logs/risk-management.jsonl | jq .
```

### Scenario 4: Integration with TradingBot
```python
# In TradingBot.execute_trade (live mode)
def execute_trade(self, symbol: str, action: str, price: float):
    if self.config.paper_trading:
        # Existing paper trading flow (unchanged)
        pass
    else:
        # NEW: Live trading with risk management
        price_data = self.market_data.get_recent_candles(symbol, limit=20)

        position_plan = self.risk_manager.calculate_position_with_stop(
            symbol=symbol,
            entry_price=price,
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

---

## [VALIDATION CHECKLIST]

Before marking plan complete, verify:

- [x] Research decisions documented with rationale and alternatives
- [x] Architecture decisions specify stack, patterns, and integration points
- [x] Reusable components identified (6 components from existing codebase)
- [x] New components specified (8 new components to create)
- [x] Schema/models defined with type hints
- [x] Performance targets extracted from spec.md NFRs
- [x] Security considerations addressed (validation, error handling, logging)
- [x] CI/CD impact assessed (no env vars, config-only changes)
- [x] Smoke tests defined for deployment acceptance
- [x] Integration scenarios documented from quickstart perspective

---

## [NEXT PHASE: TASKS]

Ready to proceed to task generation:
- Input: plan.md (this file), spec.md, research findings from NOTES.md
- Output: tasks.md with 20-30 concrete implementation tasks
- Task structure: Each task has clear acceptance criteria, dependencies, estimated effort

Command: `/tasks stop-loss-automation`
