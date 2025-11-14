# Implementation Plan: Pre-Trade Safety Checks & Risk Management

## [RESEARCH DECISIONS]

### Decision: Extend Existing CircuitBreaker vs New Safety Module
- **Decision**: Create new `SafetyChecks` module, refactor existing `CircuitBreaker` into it
- **Rationale**: Existing CircuitBreaker in bot.py is tightly coupled; safety checks need reusability across bot lifecycle
- **Alternatives**:
  - Keep circuit breaker in bot.py → Rejected: Poor separation of concerns
  - Duplicate circuit breaker logic → Rejected: Violates DRY principle
- **Source**: `src/trading_bot/bot.py:18-73` (existing CircuitBreaker class)

### Decision: Trading Hours Enforcement Strategy
- **Decision**: Use `pytz` for timezone handling, validate against market calendar
- **Rationale**: Config already has timezone-aware trading hours (America/New_York)
- **Alternatives**:
  - Use naive datetime → Rejected: Daylight saving time issues
  - Hard-code EST offset → Rejected: Doesn't handle DST
- **Source**: `src/trading_bot/config.py:45-47` (trading_start_time, trading_end_time, trading_timezone)

### Decision: Buying Power Data Source
- **Decision**: Accept buying power as parameter to `validate_trade()` (provided by account_data_module)
- **Rationale**: Safety checks module shouldn't directly call APIs (violates single responsibility)
- **Alternatives**:
  - Call Robinhood API directly → Rejected: Blocked by account-data-module dependency
  - Cache buying power internally → Rejected: Adds state management complexity
- **Source**: Roadmap (blocked by account-data-module)

### Decision: Trade History Tracking for Consecutive Losses
- **Decision**: Parse `logs/trades.log` on init, maintain in-memory list
- **Rationale**: Reuse existing logging infrastructure, survive bot restarts
- **Alternatives**:
  - Store in database → Rejected: Overkill for simple list
  - Store in JSON file → Rejected: logs/trades.log already has this data
- **Source**: `src/trading_bot/logger.py` (log_trade function, trades.log)

### Decision: Circuit Breaker State Persistence
- **Decision**: Save to `logs/circuit_breaker.json`, load on bot restart
- **Rationale**: Manual reset requirement means state must survive restarts
- **Alternatives**:
  - In-memory only → Rejected: Loses state on restart
  - Database → Rejected: Overengineering for boolean flag
- **Source**: Spec requirement FR-007 (manual reset)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (existing)
- Trading: robin_stocks library (existing)
- Time handling: pytz for timezone conversion
- Logging: Existing logger.py infrastructure
- Config: Existing config.py dual-configuration system

**Patterns**:
- **Dependency Injection**: SafetyChecks receives config, account data, market data as params
- **Fail-Safe Design**: All validation failures block trade (§Safety_First)
- **Single Responsibility**: Safety checks don't execute trades, only validate
- **State Management**: Minimal state (circuit breaker flag, last N trades)

**Dependencies** (new packages required):
- pytz@2024.1: Timezone handling for trading hours
- (Note: robin_stocks, pytest, mypy already in requirements.txt)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── safety_checks.py          # NEW: SafetyChecks class
├── bot.py                     # MODIFIED: Integrate SafetyChecks, remove CircuitBreaker
├── config.py                  # EXISTING: Reuse risk parameters
├── logger.py                  # EXISTING: Reuse log_trade(), log_error()
└── utils/                     # NEW: Utility functions
    └── time_utils.py          # NEW: Trading hours validation

tests/unit/
├── test_safety_checks.py      # NEW: Safety checks tests (95% coverage target)
└── test_time_utils.py         # NEW: Time utilities tests

logs/
├── trades.log                 # EXISTING: Trade history for consecutive loss tracking
├── circuit_breaker.json       # NEW: Circuit breaker state persistence
└── errors.log                 # EXISTING: Safety check failures
```

**Module Organization**:
- `safety_checks.py`: Core safety validation logic
  - SafetyChecks class with all validation methods
  - SafetyResult, PositionSize dataclasses
  - Circuit breaker state management

- `utils/time_utils.py`: Trading hours utilities
  - is_trading_hours(timezone) → bool
  - get_market_hours(date, timezone) → tuple
  - is_market_day(date) → bool

---

## [SCHEMA]

**No Database Tables Required** (file-based storage)

**State Files**:

`logs/circuit_breaker.json`:
```json
{
  "active": false,
  "triggered_at": null,
  "reason": null,
  "reset_at": null
}
```

**Data Classes**:

```python
from dataclasses import dataclass
from typing import Optional

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

@dataclass
class TradeRecord:
    """Trade record for consecutive loss tracking."""
    symbol: str
    action: str  # BUY, SELL
    outcome: str  # win, loss
    pnl: float
    timestamp: str  # ISO 8601
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Safety checks complete in <100ms
  - Buying power check: <10ms (simple arithmetic)
  - Trading hours check: <5ms (datetime comparison)
  - Consecutive loss check: <10ms (iterate last N trades, max 10)
  - Circuit breaker check: <5ms (boolean flag check)
  - Position size calculation: <20ms (risk-based math)
  - **Total budget**: ~50ms (well under 100ms target)

**Optimization Strategies**:
- Cache buying power for 30s (avoid repeated API calls from account module)
- Keep trade history list small (max 10 recent trades for consecutive loss detection)
- Lazy load circuit breaker state (only on bot startup)

---

## [SECURITY]

**Input Validation**:
- All numeric inputs validated (positive numbers, percentage ranges)
- Symbol validated (uppercase alphanumeric, max 5 chars)
- Price validated (>0, reasonable range 0.01-10000)
- Quantity validated (positive integer)

**Fail-Safe Behavior** (§Safety_First):
- If buying power unknown → BLOCK trade
- If time validation fails → BLOCK trade
- If circuit breaker state file corrupt → TRIP circuit breaker (safe default)
- If trade history parse fails → Assume 0 consecutive losses (allow trading, log error)

**Audit Trail** (§Audit_Everything):
- Log every safety check result to errors.log
- Log circuit breaker triggers to trades.log
- Include rejection reasons in all blocked trades
- Timestamp all events in UTC

---

## [EXISTING INFRASTRUCTURE - REUSE] (5 components)

**Modules**:
- `src/trading_bot/config.py`: Risk parameters (max_daily_loss_pct, max_consecutive_losses, max_position_pct, trading hours)
- `src/trading_bot/logger.py`: Audit logging (log_trade, log_error, get_logger)
- `src/trading_bot/bot.py:CircuitBreaker`: Existing circuit breaker logic (refactor into SafetyChecks)

**Config Values** (from config.py):
- max_daily_loss_pct: 3.0
- max_consecutive_losses: 3
- max_position_pct: 5.0
- trading_start_time: "07:00"
- trading_end_time: "10:00"
- trading_timezone: "America/New_York"

**Infrastructure**:
- logs/trades.log: Trade history storage
- logs/errors.log: Error logging

---

## [NEW INFRASTRUCTURE - CREATE] (3 components)

**Backend Modules**:
- `src/trading_bot/safety_checks.py`: SafetyChecks class
  - validate_trade() → SafetyResult
  - check_buying_power() → bool
  - check_trading_hours() → bool
  - check_daily_loss_limit() → bool
  - check_consecutive_losses() → bool
  - calculate_position_size() → PositionSize
  - check_duplicate_order() → bool
  - trigger_circuit_breaker(reason) → None
  - reset_circuit_breaker() → None

- `src/trading_bot/utils/time_utils.py`: Time utilities
  - is_trading_hours(timezone) → bool
  - get_current_time_in_tz(timezone) → datetime
  - is_market_day(date) → bool

**State Files**:
- logs/circuit_breaker.json: Circuit breaker persistence

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: No changes (Python module, no deployment config needed)
- Env vars: None (uses existing config.json and .env)
- Breaking changes: No (additive module, bot.py integration is non-breaking)
- Migration: No (file-based storage, no DB)

**Dependencies** (update requirements.txt):
- Add: pytz==2024.1 (timezone handling)

**Testing Requirements**:
- Unit tests: 95% coverage (safety-critical code)
- Integration tests: Mock account_data_module, market_data_module
- Manual tests: Trigger each circuit breaker scenario

**No CI/CD Changes Required**:
- No new build commands
- No environment variables
- No platform configuration
- Standard pytest run in existing pipeline

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- Safety checks never accidentally allow invalid trades
- Circuit breaker state persists across restarts
- All rejections are logged with reasons
- Fail-safe behavior on any validation failure

**Testing Checklist**:
```gherkin
Given bot has $1,000 buying power
When bot attempts to buy $1,500 worth of stock
Then order is BLOCKED
  And reason logged: "Insufficient buying power"
  And circuit breaker NOT triggered

Given current time is 6:59 AM EST
When bot attempts any trade
Then order is BLOCKED
  And reason logged: "Outside trading hours"

Given bot has 3 consecutive losses
When bot attempts new trade
Then order is BLOCKED
  And circuit breaker IS triggered
  And manual reset required

Given daily loss is 3.5% (limit: 3.0%)
When bot attempts any trade
Then order is BLOCKED
  And circuit breaker IS triggered
  And all future trades blocked until reset
```

**Rollback Plan**:
- Deploy IDs tracked in: specs/safety-checks/NOTES.md
- Rollback: Remove import from bot.py, revert to inline circuit breaker
- Special considerations: If circuit breaker state exists, safe to delete (no data loss)

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: Initial Setup
```bash
# No additional setup required
# Safety checks integrate with existing bot.py

# Verify config has risk parameters
cat config.json | grep -A 5 "risk_management"

# Expected output:
# "risk_management": {
#   "max_daily_loss_pct": 3.0,
#   "max_consecutive_losses": 3,
#   "max_position_pct": 5.0
# }
```

### Scenario 2: Bot Integration
```python
from src.trading_bot.safety_checks import SafetyChecks
from src.trading_bot.config import Config

# Initialize
config = Config.from_env_and_json()
safety = SafetyChecks(config)

# Before placing order
result = safety.validate_trade(
    symbol="AAPL",
    action="BUY",
    quantity=100,
    price=150.00,
    current_buying_power=10000.00  # From account_data_module
)

if result.is_safe:
    # Place order
    pass
else:
    logger.error(f"Trade blocked: {result.reason}")
    if result.circuit_breaker_triggered:
        logger.critical("Circuit breaker triggered - manual reset required")
```

### Scenario 3: Testing
```bash
# Run unit tests (target: 95% coverage)
pytest tests/unit/test_safety_checks.py -v --cov=src/trading_bot/safety_checks --cov-report=term-missing

# Expected output:
# ✅ All tests pass
# ✅ Coverage ≥95%

# Run integration tests
pytest tests/integration/ -v

# Manual circuit breaker test
python scripts/test_circuit_breaker.py
```

### Scenario 4: Circuit Breaker Reset
```bash
# Check circuit breaker status
cat logs/circuit_breaker.json

# If tripped, reset manually
python -c "
from src.trading_bot.safety_checks import SafetyChecks
from src.trading_bot.config import Config
config = Config.from_env_and_json()
safety = SafetyChecks(config)
safety.reset_circuit_breaker()
print('Circuit breaker reset')
"
```

---

## [IMPLEMENTATION PHASES]

### Phase 1: Core Safety Checks (Days 1-2)
1. Create `src/trading_bot/safety_checks.py`
2. Implement SafetyChecks class skeleton
3. Implement `check_buying_power()`
4. Implement `check_trading_hours()`
5. Create `src/trading_bot/utils/time_utils.py`
6. Write unit tests for Phase 1 (target: 95%)

### Phase 2: Circuit Breakers (Day 3)
1. Refactor CircuitBreaker from bot.py into SafetyChecks
2. Implement `check_daily_loss_limit()`
3. Implement `check_consecutive_losses()`
4. Implement circuit breaker state persistence
5. Implement `trigger_circuit_breaker()` and `reset_circuit_breaker()`
6. Write unit tests for Phase 2

### Phase 3: Position Sizing (Day 4)
1. Implement `calculate_position_size()`
2. Add risk-based sizing logic
3. Enforce max_position_pct limit
4. Write unit tests for Phase 3

### Phase 4: Integration & Polish (Day 5)
1. Implement `validate_trade()` (orchestrates all checks)
2. Implement `check_duplicate_order()`
3. Integrate with bot.py main loop
4. Write integration tests
5. Manual testing of all scenarios
6. Documentation updates

---

## [REFACTORING STRATEGY]

**Existing CircuitBreaker in bot.py:**
- Lines 18-73 contain CircuitBreaker class
- Strategy: Extract, enhance, move to safety_checks.py
- Bot.py will import from safety_checks instead

**Migration Steps**:
1. Copy CircuitBreaker logic to safety_checks.py
2. Enhance with state persistence
3. Update bot.py to import from safety_checks
4. Remove original CircuitBreaker class from bot.py
5. Update bot.py imports and usage

**Backward Compatibility**:
- No breaking changes (bot.py interface unchanged)
- Add deprecation warning if old CircuitBreaker is accessed

---

## [RISK MITIGATION]

**High-Risk Areas**:
1. **Trading hours validation**: DST edge cases
   - Mitigation: Use pytz library, extensive timezone tests

2. **Consecutive loss tracking**: Parse errors in trades.log
   - Mitigation: Graceful failure (assume 0 losses), log error

3. **Circuit breaker state corruption**: JSON file corruption
   - Mitigation: Fail-safe (trip breaker if uncertain)

**Testing Strategy**:
- 95% unit test coverage (safety-critical)
- Mock account_data_module, market_data_module in integration tests
- Manual testing of all circuit breaker scenarios
- Edge case testing: DST transitions, corrupt state files, missing logs
