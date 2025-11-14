# Data Model: daily-profit-goal-ma

## Entities

### ProfitGoalConfig
**Purpose**: Configuration for daily profit target and protection threshold

**Fields**:
- `target`: Decimal - Daily profit target in dollars (e.g., Decimal("500.00"))
- `threshold`: Decimal - Profit giveback threshold as decimal 0-1 (e.g., Decimal("0.50") for 50%)
- `enabled`: bool - Feature enabled flag (False when target = $0)

**Validation Rules**:
- `target`: Must be Decimal ≥ 0, range $0-$10,000 (from FR-010)
- `threshold`: Must be Decimal 0.10-0.90 (10%-90% range)
- `enabled`: Auto-calculated as target > 0

**State Transitions**:
- Disabled → Enabled (when target configured > $0)
- Enabled → Disabled (when target set to $0)

**Persistence**: Loaded from environment variables or config.json

---

### DailyProfitState
**Purpose**: Runtime state tracking for daily P&L and protection status

**Fields**:
- `session_date`: str - Current session date (ISO format YYYY-MM-DD)
- `daily_pnl`: Decimal - Total daily P&L (realized + unrealized)
- `realized_pnl`: Decimal - P&L from closed trades
- `unrealized_pnl`: Decimal - P&L from open positions
- `peak_profit`: Decimal - Highest daily_pnl value reached (high-water mark)
- `protection_active`: bool - Whether profit protection mode is triggered
- `last_reset`: str - Last reset timestamp (ISO 8601 UTC)
- `last_updated`: str - Last state update timestamp (ISO 8601 UTC)

**Relationships**:
- Calculated from: TradeRecord (via PerformanceTracker)
- Controls: SafetyChecks trade validation

**Validation Rules**:
- `daily_pnl`: Decimal (no bounds, can be negative)
- `peak_profit`: Must be ≥ daily_pnl at all times (monotonically increasing until reset)
- `session_date`: Must be valid ISO date (YYYY-MM-DD)
- `last_reset`, `last_updated`: Must be valid ISO 8601 UTC timestamps

**State Transitions**:
- Initial (reset) → Tracking (on first P&L update)
- Tracking → Protection Active (when drawdown ≥ threshold)
- Protection Active → Initial (reset at 4:00 AM EST)

**Persistence**: `logs/profit-goal-state.json` (crash recovery per NFR-002)

---

### ProfitProtectionEvent
**Purpose**: Audit log entry for profit protection trigger events

**Fields**:
- `event_id`: str - Unique event identifier (UUID)
- `timestamp`: str - Event timestamp (ISO 8601 UTC)
- `session_date`: str - Trading session date (YYYY-MM-DD)
- `peak_profit`: Decimal - Daily peak profit at trigger time
- `current_profit`: Decimal - Daily P&L at trigger time
- `drawdown_percent`: Decimal - Calculated drawdown (peak - current) / peak
- `threshold`: Decimal - Configured threshold that was breached
- `session_id`: str - Links to trading session (for correlation)

**Validation Rules**:
- `peak_profit`: Must be > 0 (can't trigger protection on zero profit)
- `current_profit`: Must be < peak_profit
- `drawdown_percent`: Must be ≥ threshold
- `timestamp`, `session_date`: Valid ISO format

**Persistence**: `logs/profit-protection/YYYY-MM-DD.jsonl` (one event per line)

---

## Database Schema

Not applicable - File-based persistence only (no database).

**File Structure**:
```
logs/
├── profit-goal-state.json          # Runtime state (single file, overwrite)
└── profit-protection/              # Event audit trail (append-only JSONL)
    ├── 2025-10-21.jsonl
    ├── 2025-10-22.jsonl
    └── ...
```

---

## State Shape

**Configuration State** (loaded at bot startup):
```python
@dataclass
class ProfitGoalConfig:
    target: Decimal          # e.g., Decimal("500.00")
    threshold: Decimal       # e.g., Decimal("0.50")
    enabled: bool            # target > 0
```

**Runtime State** (updated on every trade event):
```python
@dataclass
class DailyProfitState:
    session_date: str        # "2025-10-21"
    daily_pnl: Decimal       # Decimal("350.75")
    realized_pnl: Decimal    # Decimal("200.00")
    unrealized_pnl: Decimal  # Decimal("150.75")
    peak_profit: Decimal     # Decimal("600.00")
    protection_active: bool  # True if drawdown ≥ threshold
    last_reset: str          # "2025-10-21T09:00:00Z"
    last_updated: str        # "2025-10-21T14:32:15Z"
```

**Event Log Entry** (written to JSONL on protection trigger):
```python
@dataclass
class ProfitProtectionEvent:
    event_id: str            # "550e8400-e29b-41d4-a716-446655440000"
    timestamp: str           # "2025-10-21T14:32:15.123Z"
    session_date: str        # "2025-10-21"
    peak_profit: Decimal     # Decimal("600.00")
    current_profit: Decimal  # Decimal("300.00")
    drawdown_percent: Decimal  # Decimal("0.50")
    threshold: Decimal       # Decimal("0.50")
    session_id: str          # Links to session tracking
```
