# Staging Validation Checklist: stop-loss-automation

**Date**: 2025-10-16 07:00
**Deployment**: Local merge to master branch
**Commit**: e3e2834 (docs(ship): complete local staging deployment)
**Project Type**: Local-only (paper trading validation)

---

## Testing Environment

**Branch**: master (local staging)
**Mode**: Paper trading
**Config**: Add `risk_management` section to config.json before testing

---

## Pre-Testing Setup

### 1. Configuration

Add to `config.json`:

```json
{
  "paper_trading": true,
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

### 2. Start Trading Bot

```bash
python -m trading_bot
```

### 3. Monitor Logs

```bash
# In separate terminal
tail -f logs/risk-management.jsonl
```

---

## Acceptance Criteria (from spec.md)

### AC-001: Entry with Automatic Stop-Loss

**Scenario**: Bot calculates position plan with pullback-based stop
- [ ] Run position plan calculation with sample data
- [ ] Verify stop-loss price identified from pullback low
- [ ] Verify position size calculated correctly: `(balance * risk%) / (entry - stop)`
- [ ] Verify 2:1 target calculated: `entry + 2 * (entry - stop)`
- [ ] Verify PositionPlan contains all required fields

**Test Command**:
```python
from src.trading_bot.risk_management.manager import RiskManager
from src.trading_bot.risk_management.config import RiskManagementConfig
from decimal import Decimal

config = RiskManagementConfig.default()
manager = RiskManager(config=config)

# Sample price data with pullback low
price_data = [
    {"timestamp": "2025-01-01 09:30", "low": 248.00, "close": 248.50},
    {"timestamp": "2025-01-01 09:31", "low": 249.00, "close": 249.50},
    {"timestamp": "2025-01-01 09:32", "low": 249.50, "close": 250.30},
]

plan = manager.calculate_position_with_stop(
    symbol="TSLA",
    entry_price=Decimal("250.30"),
    account_balance=Decimal("100000"),
    account_risk_pct=1.0,
    price_data=price_data
)

print(f"Entry: ${plan.entry_price}")
print(f"Stop: ${plan.stop_price}")
print(f"Target: ${plan.target_price}")
print(f"Quantity: {plan.quantity} shares")
print(f"Risk: ${plan.risk_amount}")
print(f"Reward Ratio: {plan.reward_ratio}")
```

**Expected**:
- Stop: $248.00 (pullback low)
- Quantity: ~434 shares
- Target: $254.90 (2:1 ratio)
- Risk: ~$1000 (1% of $100k)

---

### AC-002: Place Trade with Risk Management

**Scenario**: System places entry, stop, and target orders
- [ ] Mock OrderManager or use paper trading mode
- [ ] Call `place_trade_with_risk_management()` with plan
- [ ] Verify entry order submitted
- [ ] Verify stop-loss order submitted at correct price
- [ ] Verify target order submitted at 2:1 ratio
- [ ] Verify RiskManagementEnvelope created with all order IDs
- [ ] Verify logs written to `logs/risk-management.jsonl`

**Test Command**:
```python
# (Requires OrderManager mock or paper trading mode)
envelope = manager.place_trade_with_risk_management(
    plan=plan,
    symbol="TSLA"
)

print(f"Entry Order: {envelope.entry_order_id}")
print(f"Stop Order: {envelope.stop_order_id}")
print(f"Target Order: {envelope.target_order_id}")
print(f"Status: {envelope.status}")
print(f"Correlation ID: {envelope.correlation_id}")
```

**Expected**:
- All 3 order IDs populated
- Status: "pending"
- JSONL log entry with position plan details

---

### AC-003: Position Sizing Based on Account Risk

**Scenario**: Calculate correct position size for 1% account risk
- [ ] Test with different account balances ($10k, $50k, $100k)
- [ ] Test with different stop distances (1%, 2%, 5%)
- [ ] Verify risk never exceeds configured percentage
- [ ] Verify position size reduces if buying power insufficient

**Test Cases**:
1. $100k account, $2.30 stop distance → 434 shares, $1000 risk ✓
2. $50k account, $2.30 stop distance → 217 shares, $500 risk ✓
3. $100k account, $5.00 stop distance → 200 shares, $1000 risk ✓

---

### AC-004: Trailing Stop Adjustment

**Scenario**: Stop moves to breakeven at 50% target progress
- [ ] Create position with entry, stop, target
- [ ] Simulate price movement to 50% of target
- [ ] Call `adjust_trailing_stop()` or let TargetMonitor detect
- [ ] Verify stop moved to breakeven (entry price)
- [ ] Verify adjustment logged with reason

**Test Command**:
```python
from src.trading_bot.risk_management.stop_adjuster import StopAdjuster

adjuster = StopAdjuster()
adjustment = adjuster.calculate_adjustment(
    current_price=Decimal("252.60"),  # 50% to target
    position_plan=plan,
    config=config
)

if adjustment:
    new_stop, reason = adjustment
    print(f"Adjust stop to: ${new_stop}")
    print(f"Reason: {reason}")
```

**Expected**:
- New stop: $250.30 (breakeven)
- Reason: "moved to breakeven - price reached 50% of target"

---

### AC-005: Auto-Exit on Target Fill

**Scenario**: System cancels stop when target fills
- [ ] Mock target order fill
- [ ] Verify TargetMonitor detects fill
- [ ] Verify stop order cancelled
- [ ] Verify position marked closed in logs
- [ ] Verify P&L calculated correctly

**Test Command**:
```python
from src.trading_bot.risk_management.target_monitor import TargetMonitor

# (Requires OrderManager mock with fill detection)
monitor = TargetMonitor(order_manager=mock_order_manager, ...)
filled = monitor.poll_and_handle_fills(envelope)

if filled:
    print("Target hit - position closed")
```

**Expected**:
- Stop order cancelled
- P&L: ~$1996 (434 shares * $4.60 gain)
- JSONL log: "action": "target_hit"

---

## Edge Cases

### Edge Case 1: No Pullback Detected (Uptrend)
- [ ] Test with strong uptrend data (no retrace)
- [ ] Verify fallback to 2% default stop
- [ ] Verify warning logged
- [ ] Verify position sizing still works

### Edge Case 2: Position Size Exceeds Buying Power
- [ ] Test with small account balance
- [ ] Verify position size reduced to fit buying power
- [ ] Verify adjustment logged
- [ ] Verify recalculated risk < 1%

### Edge Case 3: Stop Order Rejection
- [ ] Mock stop order placement failure
- [ ] Verify entry order cancelled if unfilled
- [ ] Verify error raised: StopPlacementError
- [ ] Verify trade aborted in logs

### Edge Case 4: Stop Distance Too Tight
- [ ] Test with stop <0.5% from entry
- [ ] Verify validation error raised
- [ ] Error message: "Stop distance in dead zone"

### Edge Case 5: Stop Distance Too Wide
- [ ] Test with stop >10% from entry
- [ ] Verify validation error raised
- [ ] Error message: "Stop distance out of bounds"

---

## Performance Validation

- [ ] Position plan calculation completes in <200ms
- [ ] Run performance tests: `pytest tests/risk_management/test_performance.py`
- [ ] All 3 tests pass with <1ms average

---

## Logging Validation

- [ ] JSONL log file created: `logs/risk-management.jsonl`
- [ ] Position plan log entry has all required fields
- [ ] Correlation IDs present for lifecycle tracking
- [ ] No sensitive data leaked in logs

---

## Integration Validation

- [ ] TradingBot.execute_trade() calls RiskManager (live mode only)
- [ ] Paper trading mode bypasses RiskManager (existing flow)
- [ ] Config loads risk_management section without errors
- [ ] All existing bot tests still pass (15/15)

---

## Smoke Tests

Run automated smoke tests:

```bash
pytest tests/smoke/test_risk_management_smoke.py -v
```

**Expected**:
- [ ] test_config_loads_risk_management_section: PASSED
- [ ] test_calculate_position_plan_with_mock_data: PASSED
- [ ] test_jsonl_logging_works: PASSED
- [ ] test_risk_validation_prevents_invalid_trades: PASSED

---

## Issues Found

(Document any issues below)

### Issue 1:


### Issue 2:


---

## Validation Summary

**Tested By**: _____________________
**Date**: _____________________
**Status**: [ ] PASS [ ] FAIL (with issues)

**Ready for Production?**: [ ] Yes [ ] No

**Notes**:


---

*Checklist generated by `/validate-staging` for local-only project*
