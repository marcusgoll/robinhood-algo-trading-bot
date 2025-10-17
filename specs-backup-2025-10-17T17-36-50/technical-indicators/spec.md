# Specification: Technical Indicators Module

**Feature**: technical-indicators
**Type**: Backend / Technical Analysis API
**Area**: api
**Blocked by**: None (market-data-module shipped)
**Constitution**: v1.0.0

---

## Overview

Implements technical indicators (VWAP, EMA, MACD) for trade entry validation and position management. Enforces Constitution Risk_Management by providing mathematical confirmation before entry decisions and dynamic support levels for risk control.

**Problem**: Bot needs technical indicators to validate entry points and manage positions. Current system lacks:
- VWAP calculation for dynamic support levels
- EMA (9/20-period) for trend confirmation and entry timing
- MACD for momentum validation and exit signals
- Real-time indicator updates during trading hours
- Integration with market data for historical calculations

**Solution**: Technical indicators service that calculates VWAP, EMA, and MACD from market data, validates entries above VWAP for longs, detects EMA crossovers for trend confirmation, monitors MACD for momentum validation, and provides real-time indicator values during trading hours.

---

## User Scenarios

### Scenario 1: Calculate Current VWAP for Entry Validation
**Given** authenticated Robinhood session
**And** valid stock symbol (e.g., "AAPL")
**And** current time is within trading hours (7am-10am EST)
**When** bot requests current VWAP for entry validation
**Then** VWAP calculator:
- Fetches intraday OHLCV data (1-minute or 5-minute bars from market open)
- Calculates cumulative VWAP: sum(price * volume) / sum(volume)
- Returns current VWAP value with timestamp
**And** logs "VWAP calculated: AAPL at $150.25 (11:30am EST)"

### Scenario 2: Verify Price Above VWAP for Long Entry
**Given** current price is $152.00
**And** current VWAP is $150.25
**When** bot evaluates long entry signal
**Then** VWAP validator:
- Compares current price to VWAP ($152.00 > $150.25)
- Returns True (price above VWAP, entry allowed)
- Logs "Entry allowed: Price $152.00 above VWAP $150.25 (+1.17%)"
**And** bot proceeds with entry evaluation

### Scenario 3: Reject Entry Below VWAP
**Given** current price is $148.00
**And** current VWAP is $150.25
**When** bot evaluates long entry signal
**Then** VWAP validator:
- Compares current price to VWAP ($148.00 < $150.25)
- Returns False (price below VWAP, entry blocked)
- Logs "Entry blocked: Price $148.00 below VWAP $150.25 (-1.50%)"
**And** bot skips entry (Risk_Management)

### Scenario 4: Calculate 9-period and 20-period EMAs
**Given** 100 days of historical OHLCV data for symbol
**When** bot requests EMA indicators
**Then** EMA calculator:
- Fetches historical data from MarketDataService
- Calculates 9-period EMA using exponential smoothing (multiplier = 2/(9+1))
- Calculates 20-period EMA using exponential smoothing (multiplier = 2/(20+1))
- Returns both EMA values with current price
**And** logs "EMAs calculated: AAPL EMA-9=$151.50, EMA-20=$149.80, Price=$152.00"

### Scenario 5: Detect EMA Crossover (Bullish Signal)
**Given** previous EMA-9 was $149.00 and EMA-20 was $149.50 (9 < 20)
**And** current EMA-9 is $150.00 and EMA-20 is $149.80 (9 > 20)
**When** bot checks for crossover signals
**Then** EMA crossover detector:
- Compares previous and current EMA relationship
- Detects bullish crossover (9 crossed above 20)
- Returns CrossoverSignal with type="bullish" and timestamp
**And** logs "Bullish EMA crossover detected: 9-period crossed above 20-period at $150.00"

### Scenario 6: Identify Price Near 9-EMA (Optimal Entry)
**Given** current price is $151.50
**And** 9-period EMA is $150.00
**When** bot evaluates entry timing
**Then** EMA proximity detector:
- Calculates distance: (price - EMA) / EMA * 100 = 1.0%
- Checks if within threshold (default 2%)
- Returns True (price within 1% of 9-EMA)
**And** logs "Optimal entry zone: Price $151.50 within 1.0% of 9-EMA $150.00"

### Scenario 7: Calculate MACD Line and Signal Line
**Given** 100 days of historical OHLCV data for symbol
**When** bot requests MACD indicator
**Then** MACD calculator:
- Calculates 12-period EMA (fast) and 26-period EMA (slow)
- Calculates MACD line: EMA-12 - EMA-26
- Calculates signal line: 9-period EMA of MACD line
- Calculates histogram: MACD - Signal
- Returns MACD components with timestamp
**And** logs "MACD calculated: Line=+2.50, Signal=+1.80, Histogram=+0.70"

### Scenario 8: Verify MACD Positive for Long Entry
**Given** MACD line is +2.50
**And** signal line is +1.80
**When** bot evaluates momentum confirmation
**Then** MACD validator:
- Checks if MACD line > 0 (+2.50 > 0)
- Returns True (positive momentum confirmed)
- Logs "Entry allowed: MACD +2.50 confirms positive momentum"
**And** bot proceeds with entry evaluation

### Scenario 9: Detect MACD Divergence (Lines Moving Apart)
**Given** previous MACD line was +1.50 and signal was +1.40 (diff=+0.10)
**And** current MACD line is +2.50 and signal is +1.80 (diff=+0.70)
**When** bot checks for divergence signals
**Then** MACD divergence detector:
- Calculates histogram change: +0.70 - (+0.10) = +0.60
- Detects bullish divergence (histogram expanding)
- Returns DivergenceSignal with type="bullish_divergence"
**And** logs "Bullish divergence: MACD histogram expanding (+0.60 increase)"

### Scenario 10: Trigger Exit When MACD Crosses Negative
**Given** previous MACD line was +0.50
**And** current MACD line is -0.20
**When** bot monitors exit conditions
**Then** MACD exit detector:
- Detects MACD line crossed below zero
- Returns ExitSignal with reason="MACD crossed negative"
**And** logs "Exit signal: MACD crossed negative (momentum reversal)"
**And** bot triggers position exit (Risk_Management)

### Scenario 11: Handle Missing Intraday Data for VWAP
**Given** API returns insufficient intraday bars (< 10 data points)
**When** bot requests VWAP calculation
**Then** VWAP calculator:
- Detects insufficient data (< 10 bars required)
- Logs warning "Insufficient intraday data for VWAP: 5 bars (minimum 10)"
- Raises InsufficientDataError
**And** bot skips VWAP validation (fails safely)

### Scenario 12: Update Indicators Intraday
**Given** bot is running during trading hours
**And** indicators were calculated at 9:30am EST
**When** current time reaches 10:00am EST (30 minutes later)
**Then** indicator refresh service:
- Fetches latest market data for watched symbols
- Recalculates VWAP with new intraday bars
- Recalculates EMAs with latest close prices
- Recalculates MACD with latest EMA values
- Updates indicator cache with new values
**And** logs "Indicators refreshed: 5 symbols updated at 10:00am EST"

---

## Requirements

### Functional Requirements

**FR-001: VWAP Calculation**
- MUST calculate VWAP from intraday OHLCV data (1-minute or 5-minute bars)
- MUST use cumulative formula: VWAP = sum(price * volume) / sum(volume)
- MUST use typical price for calculation: (high + low + close) / 3
- MUST require minimum 10 intraday bars for valid calculation
- MUST return current VWAP value with timestamp
- MUST handle market open data gap (use available bars from open)

**FR-002: VWAP Entry Validation**
- MUST compare current price to VWAP for long entry decisions
- MUST reject long entries if price < VWAP (Risk_Management)
- MUST allow long entries if price > VWAP
- MUST calculate percentage above/below VWAP for logging
- MUST log all VWAP validation decisions with price and VWAP values

**FR-003: VWAP as Dynamic Support**
- MUST provide VWAP as dynamic support level for position management
- MUST flag violations when price crosses below VWAP during position hold
- MUST calculate distance from VWAP in real-time
- MUST log support level breaches

**FR-004: EMA Calculation**
- MUST calculate 9-period EMA using exponential smoothing (alpha = 2/(n+1))
- MUST calculate 20-period EMA using exponential smoothing
- MUST support custom period lengths for future extension
- MUST use close prices for EMA calculation
- MUST require minimum (period * 2) data points for valid calculation
- MUST return current EMA values with timestamp

**FR-005: EMA Crossover Detection**
- MUST detect when 9-period EMA crosses above 20-period EMA (bullish)
- MUST detect when 9-period EMA crosses below 20-period EMA (bearish)
- MUST compare current and previous EMA relationship to identify crossovers
- MUST return crossover signal with type (bullish/bearish) and timestamp
- MUST log all crossover events

**FR-006: Price Proximity to 9-EMA**
- MUST calculate percentage distance from price to 9-EMA
- MUST identify when price is within configurable threshold (default 2%) of 9-EMA
- MUST flag as optimal entry zone when price near 9-EMA
- MUST support both above and below proximity checking

**FR-007: EMA Trend Angle Visualization**
- SHOULD calculate EMA slope (change over last N periods)
- SHOULD classify trend as steep/moderate/flat based on slope thresholds
- SHOULD provide trend angle in degrees for visualization
- SHOULD support export for charting/analysis

**FR-008: MACD Calculation**
- MUST calculate 12-period EMA (fast line) from close prices
- MUST calculate 26-period EMA (slow line) from close prices
- MUST calculate MACD line: EMA-12 - EMA-26
- MUST calculate signal line: 9-period EMA of MACD line
- MUST calculate histogram: MACD line - signal line
- MUST require minimum 35 data points (26 + 9) for valid calculation
- MUST return all MACD components with timestamp

**FR-009: MACD Momentum Validation**
- MUST verify MACD line > 0 for long entry confirmation
- MUST reject long entries if MACD < 0 (Risk_Management)
- MUST log MACD value and validation result

**FR-010: MACD Divergence Detection**
- MUST detect bullish divergence (histogram expanding, lines moving apart)
- MUST detect bearish divergence (histogram contracting, lines converging)
- MUST calculate histogram change between periods
- MUST return divergence signal with type and magnitude

**FR-011: MACD Exit Signal**
- MUST trigger exit signal when MACD crosses below zero
- MUST detect MACD/signal line bearish crossover (MACD crosses below signal)
- MUST log exit conditions with MACD values

**FR-012: Intraday Indicator Updates**
- MUST support real-time indicator refresh during trading hours
- MUST fetch latest market data on demand or scheduled intervals
- MUST recalculate all indicators with fresh data
- MUST update indicator cache atomically
- MUST log refresh operations with timestamp and symbols updated

**FR-013: Data Integrity Validation**
- MUST validate all input data (prices > 0, volumes >= 0)
- MUST check for sufficient data points before calculation
- MUST handle missing or incomplete data gracefully
- MUST raise InsufficientDataError for invalid calculations
- MUST log all validation failures

**FR-014: Error Handling**
- MUST handle market data fetch failures gracefully
- MUST handle calculation errors (division by zero, NaN values)
- MUST provide clear error messages for troubleshooting
- MUST never return invalid/unvalidated indicator values
- MUST log all errors with context

### Non-Functional Requirements

**NFR-001: Data Integrity (Data_Integrity)**
- MUST validate all market data before calculations
- MUST use Decimal for all financial calculations (avoid float rounding)
- MUST handle edge cases (insufficient data, zero volume, NaN)
- MUST log calculation inputs and outputs for audit trail
- MUST enforce data quality standards (no NaN, no negative prices)

**NFR-002: Auditability (Audit_Everything)**
- MUST log all indicator calculations (symbol, timestamp, values)
- MUST log all validation decisions (entry allowed/blocked, exit triggered)
- MUST log all crossover and divergence detections
- MUST log all errors and warnings
- MUST include UTC timestamps in all logs

**NFR-003: Error Handling (Fail_Safe)**
- MUST fail safely (raise errors, don't continue with invalid indicators)
- MUST provide actionable error messages
- MUST handle all exceptions explicitly
- MUST NOT use bare except clauses
- MUST log all errors before raising

**NFR-004: Performance**
- VWAP calculation MUST complete in <500ms
- EMA calculation MUST complete in <500ms
- MACD calculation MUST complete in <1 second
- Batch indicator calculation (all 3 indicators) SHOULD complete in <2 seconds
- Indicator refresh (5 symbols) SHOULD complete in <10 seconds

**NFR-005: Test Coverage**
- MUST achieve >=90% test coverage (Code_Quality)
- MUST test all calculation scenarios (VWAP, EMA, MACD)
- MUST test all validation scenarios (entry/exit conditions)
- MUST test edge cases (insufficient data, zero volume, crossovers)
- MUST test error handling (network, API, calculation errors)

**NFR-006: Type Safety**
- MUST use type hints on all functions
- MUST pass mypy strict mode
- MUST use dataclasses for indicator results

---

## Success Criteria

### Acceptance Criteria
- All 14 functional requirements implemented
- Test coverage >=90% (NFR-005)
- VWAP calculation validated against known values
- EMA calculation matches standard exponential smoothing formula
- MACD calculation matches standard formula (12/26/9 periods)
- All entry validation scenarios pass (price above/below VWAP, MACD positive/negative)
- Crossover detection works for all test cases
- Exit signal triggers correctly on MACD zero cross
- Intraday updates work during trading hours
- mypy passes with no errors (NFR-006)

### Quality Gates (Pre_Deploy)
- All unit tests pass
- All integration tests pass
- Manual testing: Calculate VWAP for AAPL
- Manual testing: Calculate EMAs (9/20) for AAPL
- Manual testing: Calculate MACD for AAPL
- Manual testing: Verify entry validation logic
- Manual testing: Verify crossover detection
- Manual testing: Verify exit signal triggers
- Manual testing: Indicator values match TradingView or similar platform
- No high-severity vulnerabilities (bandit scan)

---

## Technical Design

### Architecture

```
TechnicalIndicatorsService Class (Facade)
├── __init__(market_data, config)
├── get_vwap(symbol: str) → VWAPResult
├── get_emas(symbol: str, periods: list[int]) → EMAResult
├── get_macd(symbol: str) → MACDResult
├── get_all_indicators(symbol: str) → IndicatorSet
├── validate_entry(symbol: str, price: float) → EntryValidation
├── check_exit_signals(symbol: str) → list[ExitSignal]
└── refresh_indicators(symbols: list[str]) → None

VWAPCalculator Class
├── __init__(config)
├── calculate(ohlcv: pd.DataFrame) → VWAPResult
├── validate_entry(price: float, vwap: float) → bool
├── get_support_level(symbol: str) → float
└── _validate_data(ohlcv: pd.DataFrame) → None

EMACalculator Class
├── __init__(config)
├── calculate_ema(prices: pd.Series, period: int) → pd.Series
├── detect_crossover(ema_short: float, ema_long: float, prev_short: float, prev_long: float) → CrossoverSignal | None
├── check_proximity(price: float, ema: float, threshold_pct: float) → bool
├── calculate_trend_angle(ema_series: pd.Series) → float
└── _calculate_alpha(period: int) → float

MACDCalculator Class
├── __init__(config)
├── calculate(prices: pd.Series) → MACDResult
├── validate_momentum(macd_line: float) → bool
├── detect_divergence(current: MACDResult, previous: MACDResult) → DivergenceSignal | None
├── check_exit_signal(current: MACDResult, previous: MACDResult) → ExitSignal | None
└── _calculate_histogram(macd_line: float, signal_line: float) → float
```

### Data Models

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass
class VWAPResult:
    """VWAP calculation result."""
    symbol: str
    vwap: Decimal
    price: Decimal
    calculated_at: datetime  # UTC
    bars_used: int  # Number of intraday bars

@dataclass
class EMAResult:
    """EMA calculation result."""
    symbol: str
    ema_9: Decimal
    ema_20: Decimal
    current_price: Decimal
    calculated_at: datetime  # UTC
    crossover: CrossoverSignal | None = None

@dataclass
class CrossoverSignal:
    """EMA crossover signal."""
    type: str  # "bullish" or "bearish"
    ema_short: Decimal  # 9-period
    ema_long: Decimal  # 20-period
    detected_at: datetime  # UTC

@dataclass
class MACDResult:
    """MACD calculation result."""
    symbol: str
    macd_line: Decimal  # EMA-12 - EMA-26
    signal_line: Decimal  # 9-period EMA of MACD
    histogram: Decimal  # MACD - Signal
    calculated_at: datetime  # UTC

@dataclass
class DivergenceSignal:
    """MACD divergence signal."""
    type: str  # "bullish_divergence" or "bearish_divergence"
    histogram_change: Decimal
    detected_at: datetime  # UTC

@dataclass
class ExitSignal:
    """Position exit signal."""
    reason: str  # "MACD crossed negative", "MACD bearish crossover"
    macd_value: Decimal
    signal_value: Decimal
    triggered_at: datetime  # UTC

@dataclass
class EntryValidation:
    """Entry validation result."""
    allowed: bool
    reason: str  # "Price above VWAP", "Price below VWAP", "MACD negative"
    vwap: Decimal
    macd: Decimal
    price: Decimal
    validated_at: datetime  # UTC

@dataclass
class IndicatorSet:
    """Complete set of indicators for a symbol."""
    symbol: str
    vwap: VWAPResult
    emas: EMAResult
    macd: MACDResult
    calculated_at: datetime  # UTC

@dataclass
class IndicatorConfig:
    """Configuration for technical indicators."""
    vwap_min_bars: int = 10
    ema_periods: list[int] = field(default_factory=lambda: [9, 20])
    ema_proximity_threshold_pct: float = 2.0
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    refresh_interval_seconds: int = 300  # 5 minutes
```

### Dependencies

**External Libraries**:
- `pandas>=2.0.0` (already in requirements.txt)
- `numpy>=1.24.0` (NEW - must add for efficient array calculations)

**Internal Modules**:
- `market_data.market_data_service`: MarketDataService for OHLCV data
- `logger`: TradingLogger for audit logging
- `error_handling.exceptions`: Custom exceptions

### Calculation Flows

**VWAP Calculation Flow**:
```
1. Fetch intraday OHLCV (1min or 5min bars from market open)
   ↓
2. Calculate typical price: (high + low + close) / 3
   ↓
3. Calculate price * volume for each bar
   ↓
4. Calculate cumulative sum(price * volume)
   ↓
5. Calculate cumulative sum(volume)
   ↓
6. Calculate VWAP: cumulative_pv / cumulative_volume
   ↓
7. Return latest VWAP value
```

**EMA Calculation Flow**:
```
1. Fetch historical OHLCV (100+ days for 20-period EMA)
   ↓
2. Extract close prices
   ↓
3. Calculate alpha: 2 / (period + 1)
   ↓
4. Initialize EMA: first value = SMA of first N prices
   ↓
5. For each subsequent price:
      EMA = (price * alpha) + (prev_EMA * (1 - alpha))
   ↓
6. Return EMA series and latest values
```

**MACD Calculation Flow**:
```
1. Fetch historical OHLCV (100+ days)
   ↓
2. Calculate 12-period EMA (fast)
   ↓
3. Calculate 26-period EMA (slow)
   ↓
4. Calculate MACD line: EMA-12 - EMA-26
   ↓
5. Calculate signal line: 9-period EMA of MACD line
   ↓
6. Calculate histogram: MACD - Signal
   ↓
7. Return all components
```

---

## Implementation Plan

### Phase 1: VWAP Calculator
1. Create `src/trading_bot/indicators/vwap_calculator.py`
2. Implement VWAPResult dataclass
3. Implement VWAP calculation with typical price formula
4. Implement entry validation (price vs VWAP)
5. Implement data validation (minimum bars, valid prices)
6. Write unit tests for VWAP calculations

### Phase 2: EMA Calculator
1. Create `src/trading_bot/indicators/ema_calculator.py`
2. Implement EMAResult and CrossoverSignal dataclasses
3. Implement exponential smoothing algorithm
4. Implement 9-period and 20-period EMA calculations
5. Implement crossover detection logic
6. Implement price proximity checking
7. Write unit tests for EMA calculations

### Phase 3: MACD Calculator
1. Create `src/trading_bot/indicators/macd_calculator.py`
2. Implement MACDResult, DivergenceSignal, ExitSignal dataclasses
3. Implement MACD line calculation (EMA-12 - EMA-26)
4. Implement signal line calculation (9-period EMA of MACD)
5. Implement histogram calculation
6. Implement divergence detection
7. Implement exit signal logic
8. Write unit tests for MACD calculations

### Phase 4: Indicator Service Facade
1. Create `src/trading_bot/indicators/__init__.py`
2. Implement TechnicalIndicatorsService facade
3. Implement get_all_indicators() batch calculation
4. Implement validate_entry() with VWAP and MACD checks
5. Implement check_exit_signals()
6. Implement refresh_indicators() for intraday updates
7. Write integration tests

### Phase 5: Testing & Validation
1. Validate calculations against TradingView values
2. Write comprehensive unit tests (target: 90% coverage)
3. Write integration tests with mocked market data
4. Test all validation scenarios (entry/exit)
5. Test error handling (insufficient data, API failures)
6. Run performance benchmarks
7. Run mypy strict mode
8. Run bandit security scan

---

## Testing Strategy

### Unit Tests

**VWAP Tests** (test_vwap_calculator.py):
- Valid intraday data (20 bars) → calculate VWAP successfully
- Insufficient data (5 bars) → raise InsufficientDataError
- Zero volume bar → handle gracefully (skip bar or raise)
- Price above VWAP → entry allowed
- Price below VWAP → entry blocked
- VWAP calculation matches known value

**EMA Tests** (test_ema_calculator.py):
- Valid historical data (50 days) → calculate 9 and 20-period EMAs
- Insufficient data (5 days) → raise InsufficientDataError
- EMA calculation matches standard formula
- Bullish crossover (9 crosses above 20) → detect correctly
- Bearish crossover (9 crosses below 20) → detect correctly
- Price within 2% of 9-EMA → proximity returns True
- Price >2% from 9-EMA → proximity returns False
- Trend angle calculation for visualization

**MACD Tests** (test_macd_calculator.py):
- Valid historical data (50 days) → calculate MACD, signal, histogram
- Insufficient data (20 days) → raise InsufficientDataError
- MACD calculation matches standard formula (12/26/9)
- MACD > 0 → momentum validation passes
- MACD < 0 → momentum validation fails
- Histogram expanding → detect bullish divergence
- Histogram contracting → detect bearish divergence
- MACD crosses below zero → trigger exit signal
- MACD crosses below signal line → trigger exit signal

### Integration Tests

**End-to-End Indicator Flow**:
- Mock MarketDataService responses
- Test get_all_indicators() batch calculation
- Test validate_entry() with combined VWAP and MACD checks
- Test check_exit_signals() with MACD exit conditions
- Test refresh_indicators() for intraday updates
- Test error propagation from market data failures

### Validation Tests

**Calculation Accuracy**:
- Compare VWAP values to known test data
- Compare EMA values to pandas.ewm() output
- Compare MACD values to TradingView platform
- Verify all formulas match industry standard

---

## Configuration

**Environment Variables (.env)**:
```bash
# No new environment variables required
# Uses existing market data configuration
```

**In config.py or IndicatorConfig**:
```python
class IndicatorConfig:
    """Configuration for technical indicators."""

    # VWAP Configuration
    vwap_min_bars: int = 10  # Minimum intraday bars required
    vwap_interval: str = "5minute"  # 1minute or 5minute

    # EMA Configuration
    ema_periods: list[int] = [9, 20]
    ema_proximity_threshold_pct: float = 2.0  # 2% threshold for "near EMA"

    # MACD Configuration
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9

    # Refresh Configuration
    refresh_interval_seconds: int = 300  # 5 minutes
```

---

## Deployment Considerations

### Dependencies

**New Dependency**:
- `numpy>=1.24.0` - Must add to requirements.txt for efficient calculations
  ```
  numpy==1.26.4
  ```

**Existing Dependencies**:
- ✅ `pandas>=2.0.0` (already in requirements.txt)
- ✅ `robin-stocks` via market-data-module (already integrated)

### Breaking Changes
- ❌ **No breaking changes** (new module, additive only)
- ✅ Bot must integrate TechnicalIndicatorsService for entry validation
- ✅ Entry logic changes: Will block trades below VWAP or negative MACD

### Environment Setup
- ✅ No new environment variables required
- ✅ Uses existing MarketDataService for data fetching
- ✅ Bot fails safely if indicators unavailable (Fail_Safe)

### Security Considerations
- ✅ No credentials stored (uses market-data-module)
- ✅ All calculations validated before use (Data_Integrity)
- ✅ Read-only operations (no state modification)

### Migration
- ❌ **No database migration** (stateless calculations)
- ✅ No state to persist
- ✅ All indicators calculated on-demand from market data

### Rollback
- ✅ Standard rollback (remove indicator imports from bot.py)
- ✅ No state to clean up (stateless service)
- ✅ No data to migrate

---

## Open Questions

None - Spec is clear based on roadmap requirements and Constitution principles.

---

## Assumptions

1. **VWAP Calculation Method**: Using typical price (H+L+C)/3 for VWAP calculation (industry standard)
2. **EMA Initialization**: First EMA value uses SMA of first N prices (standard practice)
3. **MACD Periods**: Using standard 12/26/9 periods (industry default)
4. **Intraday Data Interval**: Defaulting to 5-minute bars for VWAP (balance of granularity and API calls)
5. **Entry Validation Logic**: Both VWAP and MACD conditions must pass for entry (conservative approach per Risk_Management)
6. **Indicator Refresh Frequency**: 5-minute refresh interval during trading hours (balance of freshness and API load)
7. **Decimal Precision**: Using Decimal for all financial calculations to avoid float rounding errors (Data_Integrity)
8. **Historical Data Requirement**: Minimum 50 days for EMA/MACD calculations to ensure accurate indicators

---

## References

- Constitution: `.spec-flow/memory/constitution.md` (Risk_Management, Data_Integrity, Safety_First)
- Roadmap: `.spec-flow/memory/roadmap.md` (technical-indicators feature)
- Market Data Module: `specs/market-data-module/spec.md` (integration point)
- Momentum Detection: `src/trading_bot/momentum/` (similar technical analysis patterns)
- Industry Standards:
  - VWAP: https://www.investopedia.com/terms/v/vwap.asp
  - EMA: https://www.investopedia.com/terms/e/ema.asp
  - MACD: https://www.investopedia.com/terms/m/macd.asp
