# CLI Interface Contract: Emotional Control

## Commands

### 1. status - Display Current Status

**Command**:
```bash
python -m trading_bot.emotional_control status
```

**Returns**:
```
Emotional Control Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status:           ACTIVE | INACTIVE
Activated:        2025-10-22 14:30:00 UTC (3 hours ago) [if ACTIVE]
Trigger Reason:   SINGLE_LOSS | STREAK_LOSS [if ACTIVE]
Account Balance:  $100,000.00
Position Size:    25% (reduced from 100%) | 100% (normal) [if INACTIVE]

Recovery Progress: [if ACTIVE]
Consecutive Wins: 2 / 3 (need 1 more win)

Manual Reset:     python -m trading_bot.emotional_control reset [if ACTIVE]
```

**Exit Codes**:
- 0: Success
- 1: State file not found or corrupted

---

### 2. reset - Manual Deactivation

**Command**:
```bash
python -m trading_bot.emotional_control reset \
  --admin-id "trader@example.com" \
  --reason "Completed strategy review"
```

**Confirmation Prompt**:
```
⚠️  WARNING: Manual reset will restore position sizing to 100%
Current state: ACTIVE (triggered 2 hours ago by SINGLE_LOSS)
Consecutive wins: 1 (need 2 more for automatic recovery)

Are you sure you want to reset? (yes/no):
```

**Returns** (after confirmation):
```
✅ Emotional control manually reset
Position size restored to 100%
Event logged with admin ID and reason
```

**Arguments**:
- `--admin-id` (required): Admin email or identifier for audit trail
- `--reason` (required): Human-readable reason for reset
- `--force` (optional): Skip confirmation prompt
- `--no-confirm` (optional): Skip confirmation (alias for --force)

**Exit Codes**:
- 0: Success
- 1: Not currently active (nothing to reset)
- 2: User declined confirmation
- 3: Missing required arguments

---

### 3. events - View Recent Events

**Command**:
```bash
python -m trading_bot.emotional_control events [OPTIONS]
```

**Options**:
- `--tail N`: Show last N events (default: 10)
- `--date YYYY-MM-DD`: Show events for specific date (default: today)
- `--type TYPE`: Filter by event type (ACTIVATION | DEACTIVATION)
- `--reason REASON`: Filter by trigger reason (SINGLE_LOSS | STREAK_LOSS | PROFITABLE_RECOVERY | MANUAL_RESET)

**Returns**:
```json
[
  {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-22T14:30:00Z",
    "event_type": "ACTIVATION",
    "trigger_reason": "SINGLE_LOSS",
    "account_balance": "100000.00",
    "loss_amount": "3000.00",
    "position_size_multiplier": "0.25"
  },
  {
    "event_id": "660f9511-f30c-52e5-b827-557766551111",
    "timestamp": "2025-10-22T18:15:00Z",
    "event_type": "DEACTIVATION",
    "trigger_reason": "PROFITABLE_RECOVERY",
    "consecutive_wins": 3,
    "position_size_multiplier": "1.00"
  }
]
```

**Exit Codes**:
- 0: Success
- 1: No events found for criteria
- 2: Invalid date format

---

### 4. report - Generate Daily Report

**Command**:
```bash
python -m trading_bot.emotional_control report [OPTIONS]
```

**Options**:
- `--date YYYY-MM-DD`: Generate report for specific date (default: today)
- `--format TEXT|JSON`: Output format (default: TEXT)

**Returns** (TEXT format):
```
Emotional Control Report - 2025-10-22
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Activations:   2
Deactivations: 1
Manual Resets: 0

Activation Triggers:
- SINGLE_LOSS: 1 (50%)
- STREAK_LOSS: 1 (50%)

Average Active Duration: 2.5 hours
Longest Active Period:   4 hours

Position Size Impact:
- Trades during active period: 5
- Average position size reduction: 75%
- Estimated risk reduction: $7,500
```

**Returns** (JSON format):
```json
{
  "date": "2025-10-22",
  "activations": 2,
  "deactivations": 1,
  "manual_resets": 0,
  "triggers": {
    "SINGLE_LOSS": 1,
    "STREAK_LOSS": 1
  },
  "avg_active_duration_hours": 2.5,
  "longest_active_period_hours": 4.0,
  "trades_during_active": 5,
  "avg_size_reduction_pct": 75.0,
  "estimated_risk_reduction": "7500.00"
}
```

**Exit Codes**:
- 0: Success
- 1: No data for requested date
- 2: Invalid date format

---

### 5. analyze - Historical Analysis

**Command**:
```bash
python -m trading_bot.emotional_control analyze [OPTIONS]
```

**Options**:
- `--metric METRIC`: Metric to analyze (duration | frequency | recovery_rate)
- `--start DATE`: Start date for analysis (default: 30 days ago)
- `--end DATE`: End date for analysis (default: today)

**Returns** (duration metric):
```
Emotional Control Analysis - Duration Metrics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Period: 2025-09-22 to 2025-10-22 (30 days)

Average Active Duration:   3.2 hours
Median Active Duration:    2.5 hours
Shortest Active Period:    0.5 hours
Longest Active Period:     8.0 hours

Total Active Time:         45.5 hours (6.3% of trading hours)
Total Activations:         14
```

**Exit Codes**:
- 0: Success
- 1: Insufficient data for analysis
- 2: Invalid date range

---

### 6. test-trigger - Manual Testing (Dev Only)

**Command**:
```bash
python -m trading_bot.emotional_control test-trigger [OPTIONS]
```

**Options**:
- `--type TYPE`: Trigger type (single_loss | streak_loss)
- `--amount AMOUNT`: Loss amount for single_loss (default: 3000.00)
- `--account-balance BALANCE`: Account balance for percentage calculation (default: 100000.00)

**Returns**:
```
✅ Emotional control ACTIVATED (test mode)
Reason: Single loss of $3000.00 (3.00% of account)
Position size reduced to 25%
Event logged to test event log
```

**Exit Codes**:
- 0: Success
- 1: Already active
- 2: Invalid arguments

---

### 7. test-recovery - Manual Testing (Dev Only)

**Command**:
```bash
python -m trading_bot.emotional_control test-recovery [OPTIONS]
```

**Options**:
- `--wins N`: Number of consecutive wins to simulate (default: 3)

**Returns**:
```
✅ Emotional control DEACTIVATED (test mode)
Reason: 3 consecutive profitable trades (simulated)
Position size restored to 100%
Event logged to test event log
```

**Exit Codes**:
- 0: Success
- 1: Not currently active
- 2: Invalid arguments

---

## Python API Contract

### EmotionalControl Class

```python
from trading_bot.emotional_control import EmotionalControl
from decimal import Decimal

# Initialize
ec = EmotionalControl(
    config=None,  # Optional: Loads from env vars if None
    state_file=None,  # Optional: Defaults to logs/emotional_control/state.json
    log_dir=None  # Optional: Defaults to logs/emotional_control/
)

# Get current position size multiplier (0.25 or 1.00)
multiplier: Decimal = ec.get_position_multiplier()

# Update state after trade execution
ec.update_state(
    trade_pnl: Decimal,  # Trade P&L (negative for loss, positive for win)
    account_balance: Decimal,  # Current account balance
    is_win: bool  # True if profitable, False if loss
) -> None

# Check if emotional control is currently active
is_active: bool = ec.is_active()

# Get current state
from trading_bot.emotional_control.models import EmotionalControlState
state: EmotionalControlState = ec.get_current_state()

# Manual reset (requires confirmation in interactive mode)
ec.reset_manual(
    admin_id: str,  # Admin identifier for audit trail
    reason: str,  # Human-readable reset reason
    confirm: bool = True  # Skip confirmation if False
) -> None
```

---

## Configuration Contract

### Environment Variables

```bash
# Enable/disable emotional control (default: true)
EMOTIONAL_CONTROL_ENABLED=true

# Note: Thresholds hardcoded for v1.0 (future enhancement)
# EMOTIONAL_CONTROL_LOSS_PCT=3.0
# EMOTIONAL_CONTROL_STREAK_COUNT=3
# EMOTIONAL_CONTROL_RECOVERY_COUNT=3
# EMOTIONAL_CONTROL_MULTIPLIER=0.25
```

### Config File (future enhancement)

```yaml
# config/emotional_control.yaml
emotional_control:
  enabled: true
  thresholds:
    single_loss_pct: 3.0
    consecutive_losses: 3
    recovery_wins: 3
  position_size:
    multiplier_active: 0.25
  storage:
    state_file: logs/emotional_control/state.json
    event_log_dir: logs/emotional_control/
    retention_days: 30
```

---

## Integration Contract

### RiskManager Integration

```python
from trading_bot.risk_management import RiskManager
from trading_bot.emotional_control import EmotionalControl
from decimal import Decimal

risk_manager = RiskManager()
emotional_control = EmotionalControl()

# Calculate base position size
position_plan = risk_manager.calculate_position_plan(
    symbol="AAPL",
    entry_price=Decimal("150.00"),
    account_balance=Decimal("100000.00"),
    account_risk_pct=1.0,
    price_data=[...]
)

# Apply emotional control multiplier
multiplier = emotional_control.get_position_multiplier()
adjusted_quantity = int(position_plan.quantity * multiplier)

# Use adjusted quantity for order placement
order = place_order(symbol, adjusted_quantity, entry_price)
```

### PerformanceTracker Integration

```python
from trading_bot.performance import PerformanceTracker
from trading_bot.emotional_control import EmotionalControl
from decimal import Decimal

perf_tracker = PerformanceTracker()
emotional_control = EmotionalControl()

# After trade execution
def on_trade_closed(trade):
    # Update performance tracker
    perf_tracker.record_trade(trade)

    # Update emotional control
    emotional_control.update_state(
        trade_pnl=trade.profit_loss,
        account_balance=perf_tracker.get_current_balance(),
        is_win=(trade.profit_loss > 0)
    )
```

---

## Error Responses

### State File Corruption

```python
# If state file is corrupted, defaults to ACTIVE (fail-safe)
ec = EmotionalControl()
# WARNING: Failed to load emotional control state (corrupted or invalid)
# WARNING: Defaulting to ACTIVE state (fail-safe mode)
# INFO: Position sizing set to 25% until manual verification

assert ec.is_active() == True  # Fail-safe default
```

### Event Log Write Failure

```python
# If event log write fails, continues operation
ec.update_state(trade_pnl=Decimal("-3000"), account_balance=Decimal("100000"), is_win=False)
# ERROR: Failed to write emotional control event: [Errno 28] No space left on device
# State updated in memory, event not persisted

# State still updated correctly
assert ec.is_active() == True
```

---

## Testing Contract

### Unit Test Interface

```python
import pytest
from trading_bot.emotional_control import EmotionalControl
from decimal import Decimal

def test_activation_single_loss():
    ec = EmotionalControl()
    assert ec.is_active() == False

    # Trigger with 3% loss
    ec.update_state(
        trade_pnl=Decimal("-3000"),
        account_balance=Decimal("100000"),
        is_win=False
    )

    assert ec.is_active() == True
    assert ec.get_position_multiplier() == Decimal("0.25")
```

### Performance Test Interface

```python
import pytest
from trading_bot.emotional_control import EmotionalControl
from decimal import Decimal
import time

def test_update_state_performance():
    ec = EmotionalControl()
    durations = []

    for _ in range(100):
        start = time.perf_counter()
        ec.update_state(
            trade_pnl=Decimal("100"),
            account_balance=Decimal("100000"),
            is_win=True
        )
        end = time.perf_counter()
        durations.append((end - start) * 1000)  # Convert to ms

    p95 = sorted(durations)[94]  # 95th percentile
    assert p95 < 10.0, f"P95 duration {p95:.2f}ms exceeds 10ms target"
```
