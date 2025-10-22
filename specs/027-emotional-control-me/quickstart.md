# Quickstart: emotional-control-me

## Scenario 1: Initial Setup and Testing

```bash
# 1. Ensure Python environment activated
cd D:/Coding/Stocks
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# 2. Install dependencies (if new)
pip install -r requirements.txt

# 3. Configure emotional control in .env
cat >> .env <<EOF
# Emotional Control Configuration
EMOTIONAL_CONTROL_ENABLED=true
EOF

# 4. Create log directory structure
mkdir -p logs/emotional_control

# 5. Run unit tests
pytest tests/emotional_control/ -v

# 6. Run integration tests
pytest tests/emotional_control/test_integration.py -v

# 7. Start bot with emotional control enabled
python -m trading_bot.main --mode paper
```

---

## Scenario 2: Manual Testing - Activation Flow

```bash
# Terminal 1: Start bot
python -m trading_bot.main --mode paper

# Terminal 2: Monitor emotional control status
watch -n 5 'python -m trading_bot.emotional_control status'

# Terminal 3: Trigger activation manually (for testing)
# Simulate large loss
python -m trading_bot.emotional_control test-trigger --type single_loss --amount 3000

# Expected output:
# ✅ Emotional control ACTIVATED
# Reason: Single loss of $3000.00 (3.00% of account)
# Position size reduced to 25%

# Verify state file
cat logs/emotional_control/state.json

# Verify event log
tail -f logs/emotional_control/events-$(date +%Y-%m-%d).jsonl
```

---

## Scenario 3: Manual Testing - Recovery Flow

```bash
# Prerequisite: Emotional control is ACTIVE

# Simulate 3 consecutive profitable trades
python -m trading_bot.emotional_control test-recovery --wins 3

# Expected output:
# ✅ Emotional control DEACTIVATED
# Reason: 3 consecutive profitable trades
# Position size restored to 100%

# Verify state file shows is_active = false
cat logs/emotional_control/state.json | jq '.is_active'

# Verify deactivation event logged
tail -n 1 logs/emotional_control/events-$(date +%Y-%m-%d).jsonl | jq '.'
```

---

## Scenario 4: Manual Reset (Admin Override)

```bash
# Prerequisite: Emotional control is ACTIVE

# Execute manual reset with reason
python -m trading_bot.emotional_control reset \
  --admin-id "trader@example.com" \
  --reason "Completed strategy review and risk assessment"

# Confirmation prompt:
# ⚠️  WARNING: Manual reset will restore position sizing to 100%
# Current state: ACTIVE (triggered 2 hours ago by SINGLE_LOSS)
# Consecutive wins: 1 (need 2 more for automatic recovery)
#
# Are you sure you want to reset? (yes/no): yes

# Expected output:
# ✅ Emotional control manually reset
# Position size restored to 100%
# Event logged with admin ID and reason

# Verify event log contains manual reset entry
tail -n 1 logs/emotional_control/events-$(date +%Y-%m-%d).jsonl | \
  jq '{event_type, trigger_reason, admin_id, reset_reason}'
```

---

## Scenario 5: Bot Restart and State Recovery

```bash
# Prerequisite: Emotional control was ACTIVE before shutdown

# 1. Stop bot (Ctrl+C)

# 2. Verify state file persists
cat logs/emotional_control/state.json

# 3. Restart bot
python -m trading_bot.main --mode paper

# Expected startup log:
# INFO: Emotional control state loaded from file
# INFO: Emotional control is ACTIVE (triggered 3 hours ago by STREAK_LOSS)
# INFO: Position sizing: 25% of normal
# INFO: Recovery progress: 2/3 consecutive wins needed

# 4. Verify bot continues with 25% position sizing
python -m trading_bot.emotional_control status
```

---

## Scenario 6: Validation - Position Size Integration

```bash
# Test that position sizes are correctly multiplied

# 1. With emotional control INACTIVE (normal sizing)
python -c "
from trading_bot.risk_management import RiskManager
from trading_bot.emotional_control import EmotionalControl
from decimal import Decimal

rm = RiskManager()
ec = EmotionalControl()

# Ensure INACTIVE
ec._state.is_active = False

# Calculate position
plan = rm.calculate_position_plan(
    symbol='AAPL',
    entry_price=Decimal('150.00'),
    account_balance=Decimal('100000.00'),
    account_risk_pct=1.0,
    price_data=[...]
)

print(f'Normal position size: {plan.quantity} shares')
"

# 2. With emotional control ACTIVE (25% sizing)
python -c "
from trading_bot.risk_management import RiskManager
from trading_bot.emotional_control import EmotionalControl
from decimal import Decimal

rm = RiskManager()
ec = EmotionalControl()

# Ensure ACTIVE
ec._state.is_active = True

# Calculate position with multiplier
multiplier = ec.get_position_multiplier()
plan = rm.calculate_position_plan(
    symbol='AAPL',
    entry_price=Decimal('150.00'),
    account_balance=Decimal('100000.00'),
    account_risk_pct=1.0,
    price_data=[...]
)

adjusted_quantity = int(plan.quantity * multiplier)
print(f'Reduced position size: {adjusted_quantity} shares (25% of normal)')
"

# Expected: Second output shows 25% of first output
```

---

## Scenario 7: Error Handling - Corrupted State File

```bash
# 1. Corrupt state file (simulate crash during write)
echo "invalid json {" > logs/emotional_control/state.json

# 2. Start bot
python -m trading_bot.main --mode paper

# Expected log output:
# WARNING: Failed to load emotional control state (corrupted or invalid)
# WARNING: Defaulting to ACTIVE state (fail-safe mode)
# INFO: Position sizing set to 25% until manual verification

# 3. Verify fail-safe behavior
python -m trading_bot.emotional_control status

# Expected output:
# Status: ACTIVE (fail-safe mode)
# Reason: State file corrupted, defaulted to conservative sizing
# Position size: 25%
# Action: Review logs and manually reset if appropriate
```

---

## Scenario 8: Monitoring and Observability

```bash
# 1. Check current status
python -m trading_bot.emotional_control status

# Output format:
# Emotional Control Status
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Status:           ACTIVE
# Activated:        2025-10-22 14:30:00 UTC (3 hours ago)
# Trigger Reason:   SINGLE_LOSS ($3000.00)
# Account Balance:  $100,000.00
# Position Size:    25% (reduced from 100%)
#
# Recovery Progress:
# Consecutive Wins: 2 / 3 (need 1 more win)
#
# Manual Reset:     python -m trading_bot.emotional_control reset

# 2. View recent events
python -m trading_bot.emotional_control events --tail 10

# 3. Generate daily report
python -m trading_bot.emotional_control report --date 2025-10-22

# Output:
# Emotional Control Report - 2025-10-22
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Activations:   2
# Deactivations: 1
# Manual Resets: 0
#
# Activation Triggers:
# - SINGLE_LOSS: 1 (50%)
# - STREAK_LOSS: 1 (50%)
#
# Average Active Duration: 2.5 hours
# Longest Active Period:   4 hours
#
# Position Size Impact:
# - Trades during active period: 5
# - Average position size reduction: 75%
# - Estimated risk reduction: $7,500

# 4. Tail event log in real-time
tail -f logs/emotional_control/events-$(date +%Y-%m-%d).jsonl | jq '.'
```

---

## Scenario 9: Integration with Existing Risk Manager

```python
# Example: Using EmotionalControl in risk management workflow

from trading_bot.risk_management import RiskManager
from trading_bot.emotional_control import EmotionalControl
from decimal import Decimal

# Initialize components
risk_manager = RiskManager()
emotional_control = EmotionalControl()

# After trade execution
def execute_trade_with_emotional_control(symbol, entry_price, account_balance):
    # Step 1: Calculate base position size
    position_plan = risk_manager.calculate_position_plan(
        symbol=symbol,
        entry_price=entry_price,
        account_balance=account_balance,
        account_risk_pct=1.0,
        price_data=get_price_data(symbol)
    )

    # Step 2: Apply emotional control multiplier
    multiplier = emotional_control.get_position_multiplier()
    adjusted_quantity = int(position_plan.quantity * multiplier)

    # Step 3: Execute trade
    order = place_order(symbol, adjusted_quantity, entry_price)

    # Step 4: Update emotional control state
    emotional_control.update_state(
        trade_pnl=order.profit_loss,
        account_balance=account_balance,
        is_win=order.profit_loss > 0
    )

    return order
```

---

## Debugging Commands

```bash
# View current state (raw JSON)
cat logs/emotional_control/state.json | jq '.'

# Count activation events
jq -r 'select(.event_type == "ACTIVATION")' \
  logs/emotional_control/events-*.jsonl | wc -l

# Find all manual resets
jq -r 'select(.trigger_reason == "MANUAL_RESET")' \
  logs/emotional_control/events-*.jsonl

# Calculate average active duration
python -m trading_bot.emotional_control analyze --metric duration

# Check for state file corruption
python -c "
import json
try:
    with open('logs/emotional_control/state.json') as f:
        json.load(f)
    print('✅ State file valid')
except Exception as e:
    print(f'❌ State file corrupted: {e}')
"

# Force state reset (emergency)
python -m trading_bot.emotional_control reset --force --no-confirm
```

---

## Type Checking and Linting

```bash
# Run MyPy type checking (strict mode)
mypy src/trading_bot/emotional_control/ --strict

# Expected: 0 errors

# Run Ruff linter
ruff check src/trading_bot/emotional_control/

# Expected: 0 warnings

# Run Bandit security scan
bandit -r src/trading_bot/emotional_control/

# Expected: 0 HIGH/CRITICAL vulnerabilities
```

---

## Performance Benchmarking

```bash
# Benchmark state update performance (NFR-001: <10ms)
python -m pytest tests/emotional_control/test_performance.py::test_update_state_performance -v

# Expected output:
# test_update_state_performance PASSED (95th percentile: 8.2ms) ✅

# Benchmark position multiplier lookup (expected: <1ms)
python -m pytest tests/emotional_control/test_performance.py::test_multiplier_lookup_performance -v

# Expected output:
# test_multiplier_lookup_performance PASSED (95th percentile: 0.3ms) ✅
```
