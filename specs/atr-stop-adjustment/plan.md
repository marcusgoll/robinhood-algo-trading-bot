# Implementation Plan: ATR-based Dynamic Stop-Loss Adjustment

## [RESEARCH DECISIONS]

### Decision: ATR Calculation Method
- **Decision**: Implement Wilder's smoothed ATR using standard 14-period formula with three true range components
- **Rationale**: Industry-standard volatility measure; proven effectiveness in stop-loss adaptation; widely validated across market conditions
- **Alternatives**: Standard deviation rejected (less robust to outliers); Bollinger Bands rejected (focus on price bands not volatility); Keltner Channels rejected (redundant with ATR)
- **Source**: specs/atr-stop-adjustment/spec.md FR-001, FR-014; Industry standard (J. Welles Wilder, "New Concepts in Technical Trading Systems")

### Decision: Decimal Precision for ATR Calculations
- **Decision**: Use Python's `Decimal` type for all ATR calculations (matching existing Calculator pattern)
- **Rationale**: Maintains 2 decimal place precision ($0.01); prevents floating-point rounding errors in financial calculations; consistent with existing risk_management package
- **Alternatives**: Float rejected (rounding errors accumulate); Integer cents rejected (requires conversion overhead)
- **Source**: src/trading_bot/risk_management/calculator.py:1-264 (uses Decimal throughout)

### Decision: Backward Compatible Integration
- **Decision**: ATR stops are opt-in via `atr_enabled` config flag; pullback/percentage stops remain default behavior
- **Rationale**: Zero breaking changes; allows gradual rollout; preserves existing working stop-loss automation (v1.1.0 just shipped)
- **Alternatives**: Replace pullback analysis rejected (too aggressive, unproven); Hybrid mode rejected (overcomplicated)
- **Source**: specs/atr-stop-adjustment/spec.md Hypothesis, FR-004, Deployment Considerations

### Decision: Fail-Safe Fallback Architecture
- **Decision**: ATR calculation failures trigger graceful fallback to pullback or percentage-based stops with logging
- **Rationale**: Never block trades due to ATR issues; prioritize reliability over feature completeness; Constitution §Safety_First
- **Alternatives**: Reject trade on ATR failure rejected (too conservative, reduces trading opportunities); Retry logic rejected (insufficient data won't resolve with retries)
- **Source**: specs/atr-stop-adjustment/spec.md FR-005, FR-010, NFR-007

### Decision: Stop Distance Validation Integration
- **Decision**: Reuse existing `validate_stop_distance()` function; ATR-based stops must pass same 0.5%/0.7%-10% bounds
- **Rationale**: Consistent risk guardrails; leverages existing validation logic; prevents excessive risk from high ATR values
- **Alternatives**: Separate ATR validation rejected (duplicates logic); Wider bounds for ATR rejected (violates risk management principles)
- **Source**: src/trading_bot/risk_management/calculator.py:11-49 (validate_stop_distance), specs/atr-stop-adjustment/spec.md FR-006

### Decision: MarketDataService as Price Bar Source
- **Decision**: ATR calculation consumes price bars from existing MarketDataService (extend to provide OHLC data)
- **Rationale**: Reuses authenticated Robinhood session; centralizes market data access; follows existing service boundary pattern
- **Alternatives**: Direct robin_stocks calls rejected (bypasses abstraction); Separate ATR data service rejected (increases coupling)
- **Source**: src/trading_bot/market_data/market_data_service.py (existing Quote pattern)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.12+ (FastAPI-style type hints)
- Computation: Decimal arithmetic for precision
- Data Source: MarketDataService (Robinhood API via robin_stocks)
- Configuration: JSON-based (config.json extension)
- Logging: Structured JSONL (logs/risk-management.jsonl)

**Patterns**:
- Service Layer: ATRCalculator as isolated component (similar to PullbackAnalyzer pattern)
- Value Objects: ATRStopData dataclass (immutable, frozen=True)
- Error Hierarchy: Subclass PositionPlanningError for ATR-specific exceptions
- Optional Integration: calculate_position_plan() accepts optional atr_data parameter
- Configuration Extension: Add atr_* fields to existing RiskManagementConfig dataclass

**Dependencies** (new packages required):
- None (pure Python implementation using existing dependencies: Decimal, datetime)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── risk_management/
│   ├── __init__.py
│   ├── calculator.py             # MODIFY: extend calculate_position_plan()
│   ├── models.py                 # MODIFY: add ATRStopData dataclass
│   ├── config.py                 # MODIFY: add atr_* fields to RiskManagementConfig
│   ├── exceptions.py             # MODIFY: add ATRCalculationError, ATRValidationError, StaleDataError
│   ├── stop_adjuster.py          # MODIFY: extend calculate_adjustment() with current_atr parameter
│   ├── atr_calculator.py         # CREATE: new ATR calculation component
│   └── tests/
│       ├── test_atr_calculator.py   # CREATE: ATR calculation tests
│       └── test_calculator_atr.py   # CREATE: integration tests for calculate_position_plan()
└── market_data/
    ├── data_models.py            # MODIFY: add PriceBar dataclass
    └── market_data_service.py    # MODIFY: add get_price_bars() method
```

**Module Organization**:
- `atr_calculator.py`: ATRCalculator class with calculate_atr_from_bars(), calculate_atr_stop()
- `models.py`: ATRStopData dataclass (stop_price, atr_value, atr_multiplier, source, timestamp)
- `calculator.py`: Enhanced calculate_position_plan() with atr_data optional parameter
- `stop_adjuster.py`: Enhanced calculate_adjustment() with current_atr optional parameter for dynamic recalculation
- `exceptions.py`: ATRCalculationError, ATRValidationError, StaleDataError exception classes
- `data_models.py`: PriceBar dataclass (symbol, timestamp, open, high, low, close, volume)

---

## [SCHEMA]

**Data Models** (no database tables - in-memory only):

```python
# New in models.py
@dataclass(frozen=True)
class ATRStopData:
    """ATR-based stop calculation result."""
    stop_price: Decimal
    atr_value: Decimal
    atr_multiplier: float
    atr_period: int
    source: str = "atr"  # Literal for pullback_source field
    calculation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

# New in data_models.py
@dataclass(frozen=True)
class PriceBar:
    """OHLC price bar for ATR calculation."""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

# Extended in config.py
@dataclass
class RiskManagementConfig:
    # ... existing fields ...
    atr_enabled: bool = False
    atr_period: int = 14
    atr_multiplier: float = 2.0
    atr_recalc_threshold: float = 0.20  # 20% ATR change triggers recalc
```

**State Shape** (position plan with ATR):
```python
# Extended PositionPlan.pullback_source now accepts "atr" value
plan = PositionPlan(
    symbol="TSLA",
    entry_price=Decimal("250.30"),
    stop_price=Decimal("239.90"),  # ATR-based
    target_price=Decimal("271.10"),
    quantity=96,
    risk_amount=Decimal("1000.00"),
    reward_amount=Decimal("2000.00"),
    reward_ratio=2.0,
    pullback_source="atr",  # NEW VALUE
    pullback_price=Decimal("239.90")
)
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: ATR calculation (14-period from 20-50 bars) completes in ≤50ms
- NFR-002: Position plan with ATR stop completes in ≤250ms (includes ATR calc + validation)
- NFR-003: ATR calculation success rate ≥95% in live trading
- NFR-008: ATR calculations accurate to ±$0.01 compared to reference implementations

**Implementation Constraints**:
- Use optimized Decimal operations (avoid unnecessary precision)
- Cache ATR values when recalculating stops (avoid redundant computation)
- Validate price bar timestamps before calculation (fail fast on stale data)

---

## [SECURITY]

**Authentication Strategy**:
- Reuses existing Robinhood authentication (RobinhoodAuth.login())
- No new authentication endpoints or credentials required

**Input Validation**:
- Price bars: Validate high ≥ low, all prices non-negative, timestamps sequential (ATRCalculator)
- Configuration: Validate atr_period > 0, atr_multiplier > 0, atr_recalc_threshold 0-1 (RiskManagementConfig.from_dict)
- Stop distance: Reuse validate_stop_distance() for ATR-based stops (0.5%/0.7%-10% bounds)

**Data Protection**:
- Price data: Public market data (no PII)
- ATR values: Logged to risk-management.jsonl (masked in production logs if needed)
- Configuration: atr_* settings in config.json (no secrets, safe to version control)

**Error Handling**:
- ATRCalculationError: Raised for insufficient data, invalid values (caught and logged with fallback)
- ATRValidationError: Raised for out-of-bounds stop distances (triggers position plan rejection)
- StaleDataError: Raised for timestamps >15 minutes old (triggers fallback or trade skip)

---

## [EXISTING INFRASTRUCTURE - REUSE] (8 components)

**Services/Modules**:
- src/trading_bot/risk_management/calculator.py: Position planning logic, stop distance validation
- src/trading_bot/risk_management/config.py: Configuration parsing with strategy overrides
- src/trading_bot/risk_management/models.py: PositionPlan, RiskManagementEnvelope dataclasses
- src/trading_bot/risk_management/stop_adjuster.py: Trailing stop calculation, breakeven logic
- src/trading_bot/market_data/market_data_service.py: Robinhood API integration for price data
- src/trading_bot/market_data/data_models.py: Quote, MarketStatus dataclasses (pattern for PriceBar)

**Utilities**:
- src/trading_bot/risk_management/exceptions.py: PositionPlanningError base class for ATR exceptions
- logs/risk-management.jsonl: Structured logging destination for ATR calculation details

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

**Backend**:
- src/trading_bot/risk_management/atr_calculator.py: ATRCalculator class with calculate_atr_from_bars(), calculate_atr_stop(), validate_price_bars()
- src/trading_bot/risk_management/models.py: ATRStopData dataclass (new model)
- src/trading_bot/market_data/data_models.py: PriceBar dataclass (new model)

**Exceptions**:
- src/trading_bot/risk_management/exceptions.py: ATRCalculationError, ATRValidationError, StaleDataError (new exception classes)

**Extensions**:
- src/trading_bot/risk_management/calculator.py: calculate_position_plan() extended with atr_data parameter
- src/trading_bot/risk_management/stop_adjuster.py: calculate_adjustment() extended with current_atr parameter
- src/trading_bot/risk_management/config.py: RiskManagementConfig extended with atr_* fields
- src/trading_bot/market_data/market_data_service.py: get_price_bars() method (new method)

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Railway API service (Python backend, no Vercel impact)
- Env vars: None (all configuration via config.json risk_management block)
- Breaking changes: No (ATR features opt-in, fully backward compatible)
- Migration: Configuration update only (add atr_* fields to config.json)

**Build Commands**:
- No changes (reuses existing uv/pytest setup)

**Environment Variables** (update secrets.schema.json):
- No new environment variables required
- Configuration managed via config.json risk_management section

**Database Migrations**:
- None (ATR data persists to JSONL logs only, no database schema changes)

**Smoke Tests** (for deploy-staging.yml and promote.yml):
- Test: ATR calculation with sample price bars (14-period ATR)
- Test: Position plan with ATR stop within 0.7%-10% bounds
- Test: Fallback to percentage stop when ATR calculation fails
- Test: Configuration validation with atr_* fields

**Platform Coupling**:
- Railway: No changes (reuses existing Python runtime and dependencies)
- Dependencies: None (pure Python implementation, no new packages)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- ATR calculation failures never block trades (fallback to pullback/percentage stops)
- ATR-based stops respect existing 0.7%-10% distance bounds (safety guardrail)
- ATR features disabled by default (atr_enabled=false in config defaults)
- Existing stop-loss automation behavior unchanged when atr_enabled=false

**Staging Smoke Tests** (Given/When/Then):
```gherkin
Given price data for TSLA shows ATR of $5.20
When bot calculates position plan with atr_enabled=true
Then stop distance is 4.2% (within 0.7%-10% bounds)
  And position plan uses pullback_source="atr"
  And ATR calculation completes in <50ms
  And fallback to percentage stop works if ATR data unavailable
```

**Rollback Plan**:
- Deploy IDs tracked in: specs/atr-stop-adjustment/NOTES.md (Deployment Metadata)
- Rollback commands: Standard 3-command rollback OR set atr_enabled=false in config.json
- Special considerations: Feature flag pattern - instant rollback via config without code deployment

**Artifact Strategy** (build-once-promote-many):
- API: Docker image ghcr.io/cfipros/api:<commit-sha> (NOT :latest)
- Build in: .github/workflows/verify.yml (if CI exists)
- Deploy to staging: Railway CLI or standard deployment process
- Promote to production: Same artifact, configuration controls ATR feature

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: ATR Calculation
```python
# Initialize ATR calculator
from src.trading_bot.risk_management.atr_calculator import ATRCalculator
from src.trading_bot.market_data.data_models import PriceBar

calculator = ATRCalculator(period=14, multiplier=2.0)

# Fetch price bars (extend MarketDataService)
price_bars = market_data_service.get_price_bars(symbol="TSLA", count=20)

# Calculate ATR
atr_value = calculator.calculate_atr_from_bars(price_bars)
# Expected: Decimal("5.20") for TSLA with recent volatility

# Calculate ATR-based stop
atr_stop_data = calculator.calculate_atr_stop(
    entry_price=Decimal("250.30"),
    atr_value=atr_value,
    direction="long"
)
# Expected: ATRStopData(stop_price=Decimal("239.90"), atr_value=Decimal("5.20"), ...)
```

### Scenario 2: Position Planning with ATR
```python
# Calculate position plan with ATR stop
from src.trading_bot.risk_management.calculator import calculate_position_plan

plan = calculate_position_plan(
    symbol="TSLA",
    entry_price=Decimal("250.30"),
    stop_price=atr_stop_data.stop_price,  # $239.90 from ATR
    target_rr=2.0,
    account_balance=Decimal("100000.00"),
    risk_pct=1.0,
    pullback_source="atr"  # Mark as ATR-based
)
# Expected: PositionPlan with quantity=96, stop_price=$239.90, target_price=$271.10
```

### Scenario 3: Dynamic Stop Adjustment
```python
# Recalculate stop when ATR changes significantly
from src.trading_bot.risk_management.stop_adjuster import StopAdjuster

adjuster = StopAdjuster()
latest_atr = calculator.calculate_atr_from_bars(latest_price_bars)

# Check if ATR changed >20% (threshold from config)
if abs(latest_atr - initial_atr) / initial_atr > 0.20:
    adjustment = adjuster.calculate_adjustment(
        current_price=Decimal("420.00"),
        position_plan=plan,
        config=risk_config,
        current_atr=latest_atr  # NEW PARAMETER
    )
    # Expected: (new_stop_price, "adjusted for ATR increase from 6.50 to 8.50")
```

### Scenario 4: Fallback on ATR Failure
```python
# Graceful fallback when ATR calculation fails
from src.trading_bot.risk_management.exceptions import ATRCalculationError

try:
    atr_value = calculator.calculate_atr_from_bars(insufficient_price_bars)
except ATRCalculationError as e:
    logger.warning(f"ATR calculation failed: {e}, falling back to percentage stop")
    stop_price = entry_price * Decimal("0.98")  # 2% default stop
    pullback_source = "default"  # Mark as fallback
```

### Scenario 5: Configuration
```python
# config.json extension
{
  "risk_management": {
    "account_risk_pct": 1.0,
    "min_risk_reward_ratio": 2.0,
    "default_stop_pct": 2.0,
    "trailing_enabled": true,
    "pullback_lookback_candles": 20,
    "trailing_breakeven_threshold": 0.5,
    "atr_enabled": false,               # NEW: opt-in flag
    "atr_period": 14,                   # NEW: ATR period
    "atr_multiplier": 2.0,              # NEW: stop distance multiplier
    "atr_recalc_threshold": 0.20,       # NEW: recalc trigger (20% change)
    "strategy_overrides": {
      "volatile_stocks": {
        "atr_multiplier": 2.5           # Wider stops for high volatility
      }
    }
  }
}
```
