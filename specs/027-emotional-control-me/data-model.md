# Data Model: emotional-control-me

## Entities

### EmotionalControlState
**Purpose**: Persistent state tracking emotional control activation status and recovery progress

**Fields**:
- `is_active`: bool - Whether emotional control is currently active (True = 25% sizing, False = 100% sizing)
- `activated_at`: str (ISO 8601) - Timestamp when emotional control was last activated
- `trigger_reason`: str - Reason for activation (SINGLE_LOSS | STREAK_LOSS)
- `account_balance_at_activation`: Decimal - Account balance when triggered (for audit)
- `loss_amount`: Decimal (optional) - Loss amount that triggered activation (if SINGLE_LOSS)
- `consecutive_losses`: int - Count of consecutive losing trades (reset on win or deactivation)
- `consecutive_wins`: int - Count of consecutive winning trades during active period (reset on loss)
- `last_updated`: str (ISO 8601) - Timestamp of last state modification

**Validation Rules**:
- `is_active`: Required, boolean (from FR-001, FR-002)
- `trigger_reason`: Must be one of [SINGLE_LOSS, STREAK_LOSS, null] (from FR-004)
- `loss_amount`: Must be ≥ 0 if present (from FR-001)
- `consecutive_losses`: Must be ≥ 0, triggers activation at 3 (from FR-001)
- `consecutive_wins`: Must be ≥ 0, triggers deactivation at 3 (from FR-003)
- `account_balance_at_activation`: Must be > 0 (from FR-001)

**State Transitions**:
- INACTIVE → ACTIVE (on single loss ≥3% OR consecutive loss streak ≥3)
- ACTIVE → INACTIVE (on 3 consecutive wins OR manual reset)

---

### EmotionalControlEvent
**Purpose**: Immutable audit record of emotional control activation/deactivation events

**Fields**:
- `event_id`: str (UUID4) - Unique event identifier for tracing
- `timestamp`: str (ISO 8601 UTC) - When event occurred
- `event_type`: str - Type of event (ACTIVATION | DEACTIVATION)
- `trigger_reason`: str - Why event occurred (SINGLE_LOSS | STREAK_LOSS | PROFITABLE_RECOVERY | MANUAL_RESET)
- `account_balance`: Decimal - Account balance at event time
- `loss_amount`: Decimal (optional) - Loss amount for SINGLE_LOSS activations
- `consecutive_losses`: int (optional) - Loss streak count for STREAK_LOSS activations
- `consecutive_wins`: int (optional) - Win streak count for PROFITABLE_RECOVERY deactivations
- `admin_id`: str (optional) - Admin identifier for MANUAL_RESET deactivations
- `reset_reason`: str (optional) - Human-provided reason for MANUAL_RESET deactivations
- `position_size_multiplier`: Decimal - New position size multiplier (0.25 or 1.00)

**Relationships**:
- Has many: EmotionalControlState (events trace state transitions over time)

**Validation Rules**:
- `event_id`: Required, must be valid UUID4 (from FR-004)
- `timestamp`: Required, must be ISO 8601 UTC format (from FR-004)
- `event_type`: Required, must be [ACTIVATION, DEACTIVATION] (from FR-004)
- `trigger_reason`: Required, must be [SINGLE_LOSS, STREAK_LOSS, PROFITABLE_RECOVERY, MANUAL_RESET] (from FR-004)
- `account_balance`: Required, must be > 0 (from FR-004)
- `loss_amount`: Required if trigger_reason = SINGLE_LOSS, else null (from FR-004)
- `consecutive_losses`: Required if trigger_reason = STREAK_LOSS, else null (from FR-004)
- `consecutive_wins`: Required if trigger_reason = PROFITABLE_RECOVERY, else null (from FR-004)
- `admin_id`: Required if trigger_reason = MANUAL_RESET, else null (from FR-006)
- `reset_reason`: Required if trigger_reason = MANUAL_RESET, else null (from FR-006)
- `position_size_multiplier`: Required, must be 0.25 or 1.00 (from FR-002, FR-003)

---

### EmotionalControlConfig
**Purpose**: Configuration for emotional control feature thresholds and behavior

**Fields**:
- `enabled`: bool - Feature flag to enable/disable emotional control
- `single_loss_threshold_pct`: Decimal - Percentage threshold for single loss activation (default: 3.0)
- `consecutive_loss_threshold`: int - Number of consecutive losses to trigger (default: 3)
- `recovery_win_threshold`: int - Number of consecutive wins to deactivate (default: 3)
- `position_size_multiplier_active`: Decimal - Position size multiplier when active (default: 0.25)
- `state_file_path`: str - Path to state persistence file (default: logs/emotional_control/state.json)
- `event_log_dir`: str - Directory for event logs (default: logs/emotional_control/)

**Validation Rules**:
- `enabled`: Required, boolean (from FR-002)
- `single_loss_threshold_pct`: Must be > 0, typically 1.0-10.0 (from FR-001)
- `consecutive_loss_threshold`: Must be > 0, typically 2-5 (from FR-001)
- `recovery_win_threshold`: Must be > 0, typically 2-5 (from FR-003)
- `position_size_multiplier_active`: Must be > 0 and < 1, typically 0.10-0.50 (from FR-002)

---

## Database Schema

No database required - file-based storage only.

**File Structure**:
```
logs/
  emotional_control/
    state.json                    # Current state (single record, atomic writes)
    events-2025-10-22.jsonl       # Daily event audit trail (append-only)
    events-2025-10-23.jsonl
    ...
```

---

## State File Schema (state.json)

```json
{
  "is_active": true,
  "activated_at": "2025-10-22T14:30:00Z",
  "trigger_reason": "SINGLE_LOSS",
  "account_balance_at_activation": "100000.00",
  "loss_amount": "3000.00",
  "consecutive_losses": 0,
  "consecutive_wins": 2,
  "last_updated": "2025-10-22T16:45:00Z"
}
```

---

## Event Log Schema (events-YYYY-MM-DD.jsonl)

**Activation Event**:
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-22T14:30:00Z",
  "event_type": "ACTIVATION",
  "trigger_reason": "SINGLE_LOSS",
  "account_balance": "100000.00",
  "loss_amount": "3000.00",
  "consecutive_losses": null,
  "consecutive_wins": null,
  "admin_id": null,
  "reset_reason": null,
  "position_size_multiplier": "0.25"
}
```

**Deactivation Event (Profitable Recovery)**:
```json
{
  "event_id": "660f9511-f30c-52e5-b827-557766551111",
  "timestamp": "2025-10-22T18:15:00Z",
  "event_type": "DEACTIVATION",
  "trigger_reason": "PROFITABLE_RECOVERY",
  "account_balance": "102500.00",
  "loss_amount": null,
  "consecutive_losses": null,
  "consecutive_wins": 3,
  "admin_id": null,
  "reset_reason": null,
  "position_size_multiplier": "1.00"
}
```

**Deactivation Event (Manual Reset)**:
```json
{
  "event_id": "770fa622-g41d-63f6-c938-668877662222",
  "timestamp": "2025-10-22T20:00:00Z",
  "event_type": "DEACTIVATION",
  "trigger_reason": "MANUAL_RESET",
  "account_balance": "98000.00",
  "loss_amount": null,
  "consecutive_losses": null,
  "consecutive_wins": 1,
  "admin_id": "user@example.com",
  "reset_reason": "completed trading review session and adjusted strategy",
  "position_size_multiplier": "1.00"
}
```

---

## Data Flow Diagram

```
Trade Execution
    ↓
PerformanceTracker (update P&L, win/loss counters)
    ↓
EmotionalControl.update_state()
    ├─→ AccountData.get_portfolio_value() [account balance]
    ├─→ Check single loss threshold (≥3%)
    ├─→ Check consecutive loss streak (≥3)
    ├─→ Check consecutive win streak (≥3)
    ├─→ Determine state transition (ACTIVATE or DEACTIVATE)
    ├─→ Create EmotionalControlEvent
    ├─→ Write event to logs/emotional_control/events-YYYY-MM-DD.jsonl
    └─→ Persist EmotionalControlState to logs/emotional_control/state.json (atomic write)

Next Trade Planning
    ↓
RiskManager.calculate_position_plan()
    ├─→ EmotionalControl.get_position_multiplier() [returns 0.25 or 1.00]
    └─→ Apply multiplier: position_size = base_size × multiplier
```

---

## Concurrency Considerations

**Thread Safety**: File-based storage requires atomic operations
- **State writes**: Use temp file + rename for atomic updates (prevents partial writes on crash)
- **Event log writes**: Append-only, no lock required (OS guarantees atomic appends <4KB)
- **State reads**: Single-threaded bot, no read locking needed

**Race Conditions**: None expected in single-threaded bot architecture
- If multi-threading added in future: Add file locks for state.json writes

---

## Performance Characteristics

**Memory**:
- EmotionalControlState: ~200 bytes (in-memory)
- EmotionalControlConfig: ~150 bytes (in-memory)
- Event log: ~300 bytes per event (disk only)

**Disk**:
- state.json: <1 KB (single record)
- events-YYYY-MM-DD.jsonl: ~300 bytes per event × daily trades (~30-50 events/day = 15 KB/day)
- Daily rotation keeps disk usage manageable (30 days × 15 KB = 450 KB)

**I/O**:
- State read (bot startup): 1 file read (<1ms)
- State write (per update): 1 temp file write + 1 rename (<10ms)
- Event log write (per event): 1 append (<5ms)

---

## Data Retention

**State File**: Overwritten on each update (single current state only)
**Event Logs**: Daily rotation, retain 30 days (configurable)
**Compliance**: Event logs provide complete audit trail per Constitution §Audit_Everything
