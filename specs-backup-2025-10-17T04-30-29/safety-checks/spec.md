# Specification: Pre-Trade Safety Checks & Risk Management

**Feature**: safety-checks
**Type**: Backend / Risk Management
**Area**: api
**Blocked by**: account-data-module, market-data-module
**Constitution**: v1.0.0

---

## Overview

Implements comprehensive pre-trade safety checks and circuit breakers to enforce Constitution §Safety_First and §Risk_Management requirements. Prevents trades that violate risk limits, trading hours, buying power constraints, or circuit breaker conditions.

**Problem**: Currently no automated safety checks before trade execution - risk of:
- Trading outside allowed hours (7am-10am EST)
- Exceeding buying power
- Violating daily loss limits
- Continuing after consecutive losses
- Duplicate order submissions

**Solution**: Safety validation layer that runs before every trade, blocking invalid orders and triggering circuit breakers when limits are hit.

---

## User Scenarios

### Scenario 1: Buying Power Check
**Given** user has $1,000 buying power
**When** bot attempts to buy 100 shares @ $15/share ($1,500 total)
**Then** order is BLOCKED with reason "Insufficient buying power: $1,000 available, $1,500 required"
**And** error is logged to errors.log

### Scenario 2: Trading Hours Enforcement
**Given** current time is 6:45 AM EST
**When** bot attempts to place any order
**Then** order is BLOCKED with reason "Outside trading hours (7am-10am EST)"
**And** bot waits until 7:00 AM to resume

### Scenario 3: Daily Loss Circuit Breaker
**Given** daily loss limit is 3% of portfolio
**And** current loss is 3.5%
**When** bot attempts any new trade
**Then** order is BLOCKED with reason "Daily loss limit exceeded: 3.5% (limit: 3.0%)"
**And** circuit breaker is triggered
**And** manual restart is required

### Scenario 4: Consecutive Loss Detector
**Given** last 3 trades were losses
**When** bot attempts to enter new position
**Then** order is BLOCKED with reason "3 consecutive losses detected"
**And** circuit breaker is triggered
**And** notification logged: "Trading halted after 3 consecutive losses"
**And** manual restart required

### Scenario 5: Position Size Validation
**Given** max position size is 5% of portfolio ($5,000)
**When** bot calculates position size based on stop loss
**Then** position size is capped at $5,000
**And** share quantity adjusted to fit limit

### Scenario 6: Duplicate Order Prevention
**Given** pending buy order for 100 AAPL shares exists
**When** bot attempts to place another buy order for AAPL
**Then** order is BLOCKED with reason "Duplicate order detected for AAPL"
**And** existing order ID is logged

---

## Requirements

### Functional Requirements

**FR-001: Buying Power Check**
- MUST verify sufficient buying power before placing order
- MUST calculate: (shares × price) + fees ≤ available_buying_power
- MUST reject orders exceeding buying power
- MUST log rejection reason

**FR-002: Trading Hours Enforcement**
- MUST enforce trading window: 7:00 AM - 10:00 AM EST
- MUST reject orders outside trading hours
- MUST use market calendar (account for holidays/weekends)
- MUST support timezone conversion (UTC → EST)

**FR-003: Daily Loss Circuit Breaker**
- MUST track daily P&L from market open
- MUST compare against max_daily_loss_pct from config
- MUST halt all trading when limit exceeded
- MUST require manual reset to resume

**FR-004: Consecutive Loss Detector**
- MUST track last N trades (configurable, default: 3)
- MUST detect consecutive loss pattern
- MUST trigger circuit breaker on pattern match
- MUST log each loss in sequence

**FR-005: Position Size Calculator**
- MUST calculate position size based on:
  - Account balance
  - Stop loss distance
  - Max risk per trade (from config)
- MUST enforce max_position_pct limit (5% default)
- MUST return both dollar amount and share quantity

**FR-006: Duplicate Order Prevention**
- MUST check for existing orders on same symbol
- MUST block duplicate entries
- MUST allow exits (sell) even if pending buy exists
- MUST clear tracking when order fills/cancels

**FR-007: Circuit Breaker Management**
- MUST provide `trigger_circuit_breaker(reason)` method
- MUST set circuit_breaker_active flag
- MUST log circuit breaker event with timestamp and reason
- MUST provide `reset_circuit_breaker()` for manual restart

### Non-Functional Requirements

**NFR-001: Performance**
- Safety checks MUST complete in <100ms
- MUST NOT block trading flow unnecessarily
- Buying power check MUST use cached account data (max 30s old)

**NFR-002: Reliability**
- MUST handle API failures gracefully (fail safe)
- If buying power API fails → BLOCK trade (§Safety_First)
- If time check fails → BLOCK trade
- MUST log all failures to errors.log

**NFR-003: Auditability (§Audit_Everything)**
- MUST log every safety check result
- MUST log rejection reasons
- MUST log circuit breaker events
- MUST include timestamps (UTC)

**NFR-004: Test Coverage**
- MUST achieve ≥95% test coverage (§Code_Quality)
- MUST test all rejection scenarios
- MUST test circuit breaker triggers
- MUST test edge cases (market close, API failures)

**NFR-005: Type Safety**
- MUST use type hints on all functions
- MUST pass `mypy` strict mode

---

## Technical Design

### Architecture

```
SafetyChecks Class
├── __init__(config, account_data_provider, market_data_provider)
├── validate_trade(symbol, action, quantity, price) → SafetyResult
├── check_buying_power(symbol, quantity, price) → bool
├── check_trading_hours() → bool
├── check_daily_loss_limit() → bool
├── check_consecutive_losses() → bool
├── calculate_position_size(symbol, stop_loss_price, entry_price) → PositionSize
├── check_duplicate_order(symbol, action) → bool
├── trigger_circuit_breaker(reason: str) → None
└── reset_circuit_breaker() → None
```

### Data Models

```python
@dataclass
class SafetyResult:
    """Result of safety validation."""
    is_safe: bool
    reason: Optional[str] = None
    circuit_breaker_triggered: bool = False

@dataclass
class PositionSize:
    """Position size calculation result."""
    dollar_amount: float
    share_quantity: int
    risk_amount: float
    stop_loss_price: float
```

### Dependencies

**Required Modules** (blocked by):
- `account_data_module`: For buying power, account balance
- `market_data_module`: For current time, market hours, price data

**Existing Modules**:
- `config.py`: For risk limits (max_daily_loss_pct, max_consecutive_losses, max_position_pct)
- `logger.py`: For logging safety check results

### State Management

**Circuit Breaker State**:
- Stored in `SafetyChecks` instance
- Persisted to `logs/circuit_breaker.json`:
  ```json
  {
    "active": true,
    "triggered_at": "2025-10-07T14:30:00Z",
    "reason": "3 consecutive losses detected",
    "reset_at": null
  }
  ```

**Trade History Tracking**:
- Last N trades stored in memory (for consecutive loss detection)
- Reloaded from `logs/trades.log` on bot restart
- Format: `[{"outcome": "loss", "timestamp": "..."}, ...]`

---

## Implementation Plan

### Phase 1: Core Safety Checks (Intra: No - requires careful design)
1. Create `src/trading_bot/safety_checks.py`
2. Implement SafetyChecks class with core methods
3. Implement buying power check
4. Implement trading hours enforcement
5. Implement duplicate order prevention

### Phase 2: Circuit Breakers
1. Implement daily loss circuit breaker
2. Implement consecutive loss detector
3. Implement circuit breaker state persistence
4. Add manual reset functionality

### Phase 3: Position Sizing
1. Implement position size calculator
2. Add risk-based sizing logic
3. Enforce max position percentage

### Phase 4: Integration & Testing
1. Write comprehensive unit tests (target: 95% coverage)
2. Write integration tests with mocked APIs
3. Test all circuit breaker scenarios
4. Add to bot.py main trading loop

---

## Testing Strategy

### Unit Tests (test_safety_checks.py)

**Buying Power Tests**:
- ✅ Sufficient buying power → allow trade
- ✅ Insufficient buying power → block trade
- ✅ Edge case: exact buying power match → allow trade

**Trading Hours Tests**:
- ✅ Within hours (7am-10am EST) → allow trade
- ✅ Before hours (6:59am) → block trade
- ✅ After hours (10:01am) → block trade
- ✅ Weekend/holiday → block trade

**Daily Loss Tests**:
- ✅ Under limit → allow trade
- ✅ At limit → allow trade
- ✅ Over limit → block trade + trigger circuit breaker

**Consecutive Loss Tests**:
- ✅ 0 losses → allow trade
- ✅ 2 losses → allow trade
- ✅ 3 losses → block trade + trigger circuit breaker
- ✅ Win breaks sequence → reset counter

**Position Size Tests**:
- ✅ Calculate based on stop loss distance
- ✅ Enforce max 5% portfolio limit
- ✅ Handle fractional shares (round down)

**Duplicate Order Tests**:
- ✅ No pending orders → allow trade
- ✅ Pending buy on same symbol → block buy
- ✅ Pending buy, new sell → allow sell (exit position)

**Circuit Breaker Tests**:
- ✅ Trigger circuit breaker → set active flag
- ✅ Circuit breaker active → block all trades
- ✅ Reset circuit breaker → clear flag + allow trades
- ✅ Persist state across restarts

### Integration Tests
- Mock account_data_provider responses
- Mock market_data_provider responses
- Test with real config.json values
- Test API failure scenarios (fail safe)

---

## Configuration

**In config.json**:
```json
{
  "risk_management": {
    "max_daily_loss_pct": 3.0,
    "max_consecutive_losses": 3,
    "max_position_pct": 5.0,
    "buying_power_check_enabled": true,
    "trading_hours_enforcement": true
  },
  "trading": {
    "hours": {
      "start_time": "07:00",
      "end_time": "10:00",
      "timezone": "America/New_York"
    }
  }
}
```

---

## Deployment Considerations

### Dependencies
- ✅ **Blocked by**: account-data-module, market-data-module
- ✅ **Requires**: config.py, logger.py (already implemented)

### Breaking Changes
- ❌ **No breaking changes** (new module, additive only)
- ✅ Existing bot.py will need to integrate SafetyChecks

### Migration
- ❌ **No database migration** (uses existing logs/)
- ✅ Circuit breaker state file created on first run

### Rollback
- ✅ Standard rollback (remove safety_checks.py import from bot.py)
- ✅ Circuit breaker state file can be deleted if needed

---

## Success Criteria

### Acceptance Criteria
- [ ] All 6 functional requirements implemented
- [ ] Test coverage ≥95% (NFR-004)
- [ ] All safety checks complete in <100ms (NFR-001)
- [ ] Circuit breakers trigger correctly in all scenarios
- [ ] Position size calculator enforces 5% limit
- [ ] Duplicate orders blocked correctly
- [ ] Trading hours enforced (7am-10am EST)
- [ ] mypy passes with no errors (NFR-005)

### Quality Gates (§Pre_Deploy)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] bandit security scan clean
- [ ] Manual testing: Trigger each circuit breaker
- [ ] Manual testing: Verify buying power rejection
- [ ] Manual testing: Verify trading hours block

---

## Open Questions

None - Spec is clear based on roadmap requirements.

---

## References

- Constitution: `.specify/memory/constitution.md` (§Safety_First, §Risk_Management)
- Roadmap: `.specify/memory/roadmap.md` (safety-checks feature)
- Config: `config.example.json` (risk parameters)
- Logger: `src/trading_bot/logger.py` (audit logging)
