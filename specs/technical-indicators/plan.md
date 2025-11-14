# Implementation Plan: Technical Indicators Module

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11+, pandas, numpy (NEW dependency), Decimal for precision
- Components to reuse: 5 (MarketDataService, TradingLogger, error_handling, dataclass patterns)
- New components needed: 4 (VWAPCalculator, EMACalculator, MACDCalculator, TechnicalIndicatorsService)
- Integration: MarketDataService for all OHLCV fetching, no direct robin_stocks calls
- Entry validation: AND logic (price > VWAP AND MACD > 0) per Constitution §Risk_Management

**Key Research Decisions**:
1. Market data integration: Reuse MarketDataService (retry, validation, rate limiting)
2. Service architecture: Separate calculators with facade pattern (SRP, testability)
3. Decimal precision: All financial values use Decimal (Constitution §Data_Integrity)
4. Entry validation: Conservative AND gate for VWAP and MACD checks (Constitution §Risk_Management)
5. Refresh interval: 5-minute updates (balance freshness vs API load)
6. Historical data: Minimum 50 days for accurate EMA/MACD (2x period warmup rule)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11+ (existing project stack)
- Data Analysis: pandas 2.1.4 (existing), numpy 1.26.3 (existing - check requirements.txt)
- Financial Precision: Decimal (Python standard library)
- Logging: TradingLogger (existing)
- Error Handling: @with_retry, custom exceptions (existing)
- Testing: pytest, pytest-cov, pytest-mock (existing)

**Patterns**:
- **Service Facade**: TechnicalIndicatorsService provides clean API, delegates to calculators
  - Rationale: Single entry point, hides calculator complexity, easier mocking
  - Example: `indicators.get_all_indicators(symbol)` calls VWAP, EMA, MACD calculators internally
- **Calculator Pattern**: Separate calculator classes for VWAP, EMA, MACD
  - Rationale: Single Responsibility Principle, independent testing, independent evolution
  - Example: VWAPCalculator.calculate(ohlcv) → VWAPResult
- **Dataclass Results**: Immutable result objects with validation
  - Rationale: Type safety, validation in __post_init__, follows momentum module pattern
  - Example: @dataclass VWAPResult with Decimal fields
- **Dependency Injection**: Calculators receive config, market_data, logger via __init__
  - Rationale: Testable (mock dependencies), configurable, follows existing patterns

**Dependencies** (new packages required):
- numpy>=1.26.0: Already in requirements.txt (version 1.26.3), no changes needed

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/indicators/
├── __init__.py                      # TechnicalIndicatorsService facade, public API
├── config.py                        # IndicatorConfig dataclass
├── vwap_calculator.py               # VWAP calculation and validation
├── ema_calculator.py                # EMA calculation and crossover detection
├── macd_calculator.py               # MACD calculation and signal detection
└── exceptions.py                    # InsufficientDataError (if not in error_handling)

tests/indicators/
├── test_vwap_calculator.py          # Unit tests for VWAP
├── test_ema_calculator.py           # Unit tests for EMA
├── test_macd_calculator.py          # Unit tests for MACD
└── test_technical_indicators_service.py  # Integration tests
```

**Module Organization**:
- `__init__.py`: TechnicalIndicatorsService class (facade), exports public API
- `config.py`: IndicatorConfig dataclass with defaults and validation
- `vwap_calculator.py`: VWAPCalculator class (calculate, validate_entry, get_support_level)
- `ema_calculator.py`: EMACalculator class (calculate_ema, detect_crossover, check_proximity, calculate_trend_angle)
- `macd_calculator.py`: MACDCalculator class (calculate, validate_momentum, detect_divergence, check_exit_signal)
- `exceptions.py`: InsufficientDataError (if not already in error_handling/exceptions.py)

**Result Dataclasses** (in same files as calculators or separate models.py):
- VWAPResult, EMAResult, CrossoverSignal (vwap_calculator.py or separate)
- MACDResult, DivergenceSignal, ExitSignal (macd_calculator.py or separate)
- EntryValidation, IndicatorSet (in __init__.py or separate)

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- **Result Entities**: VWAPResult, EMAResult, MACDResult, IndicatorSet (calculation results)
- **Signal Entities**: CrossoverSignal, DivergenceSignal, ExitSignal (event detection)
- **Validation Entities**: EntryValidation (combined VWAP + MACD validation)
- **Configuration**: IndicatorConfig (thresholds, periods, refresh interval)
- **Database**: None required (stateless calculations)

**Key Relationships**:
- IndicatorSet → VWAPResult, EMAResult, MACDResult (composition)
- EMAResult → CrossoverSignal (optional, embedded)
- MACDCalculator → DivergenceSignal, ExitSignal (returned by methods)

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs** (NFR-004):
- VWAP calculation: <500ms (single symbol)
- EMA calculation: <500ms (single symbol, 2 periods)
- MACD calculation: <1 second (single symbol)
- Batch calculation (all 3 indicators): <2 seconds (single symbol)
- Indicator refresh (5 symbols): <10 seconds (batch update)

**Optimization Strategies**:
- Use pandas vectorized operations (avoid Python loops)
- Use numpy for efficient array math (already in requirements.txt)
- Cache indicator results for refresh_interval (5 minutes)
- Batch fetch historical data once for all calculations (get_all_indicators)

**Performance Testing**:
- Benchmark each calculator independently with pytest-benchmark
- Measure batch calculation performance
- Profile with cProfile if targets not met
- Verify no memory leaks with repeated calculations

---

## [SECURITY]

**Authentication Strategy**:
- No authentication needed (internal module, not API endpoint)
- Uses existing RobinhoodAuth via MarketDataService
- No credentials stored in indicator module

**Authorization Model**:
- N/A (internal calculations, no user-facing API)

**Input Validation**:
- Symbol validation: Reuse MarketDataService validation
- Price validation: Must be > 0 (Decimal)
- Data validation: Check for NaN, negative prices, zero volume
- Period validation: Must be > 0 for EMA periods
- Threshold validation: Must be > 0 for proximity checks

**Data Protection**:
- No PII handling (only OHLCV market data)
- Calculation results logged with TradingLogger (Constitution §Audit_Everything)
- No data persistence (stateless calculations)

**Error Handling** (Constitution §Fail_Safe):
- Raise InsufficientDataError for insufficient bars (fail fast)
- Raise DataValidationError for invalid data (fail fast)
- Never return invalid indicator values (validate all outputs)
- Log all errors before raising (Constitution §Audit_Everything)

---

## [EXISTING INFRASTRUCTURE - REUSE] (5 components)

**Services/Modules**:
- `src/trading_bot/market_data/market_data_service.py`: MarketDataService for OHLCV fetching
  - Methods: get_historical_data(symbol, interval, span) → pd.DataFrame
  - Provides: @with_retry, data validation, rate limit handling
  - Integration: Pass MarketDataService instance to TechnicalIndicatorsService.__init__
- `src/trading_bot/logger.py`: TradingLogger for audit logging
  - Methods: get_logger(__name__), log_trade(), log_error()
  - Provides: UTC timestamps, structured logging, file rotation
  - Integration: Pass logger instance to calculators, log all calculations
- `src/trading_bot/error_handling/retry.py`: @with_retry decorator
  - Provides: Automatic retry on rate limits, exponential backoff
  - Integration: Apply to methods that fetch market data (if needed)
- `src/trading_bot/error_handling/exceptions.py`: Custom exceptions
  - Provides: DataValidationError, RateLimitError
  - Integration: Raise DataValidationError for invalid data, add InsufficientDataError
- `src/trading_bot/error_handling/policies.py`: DEFAULT_POLICY
  - Provides: Retry policy (3 attempts, exponential backoff)
  - Integration: Use for any external API calls (via MarketDataService)

**Dataclass Patterns**:
- `src/trading_bot/momentum/schemas/`: MomentumSignal, BullFlagPattern dataclasses
  - Pattern: @dataclass with validation in __post_init__
  - Integration: Follow same pattern for VWAPResult, EMAResult, MACDResult

---

## [NEW INFRASTRUCTURE - CREATE] (4 components)

**Backend Modules**:
- `src/trading_bot/indicators/__init__.py`: TechnicalIndicatorsService facade
  - Methods: get_vwap(), get_emas(), get_macd(), get_all_indicators(), validate_entry(), check_exit_signals(), refresh_indicators()
  - Dependencies: MarketDataService, IndicatorConfig, TradingLogger, VWAPCalculator, EMACalculator, MACDCalculator
  - Exports: Public API for indicator calculations
- `src/trading_bot/indicators/config.py`: IndicatorConfig dataclass
  - Fields: vwap_min_bars, ema_periods, ema_proximity_threshold_pct, macd_fast_period, macd_slow_period, macd_signal_period, refresh_interval_seconds
  - Validation: Ensure periods > 0, fast < slow for MACD, refresh >= 60
- `src/trading_bot/indicators/vwap_calculator.py`: VWAPCalculator class
  - Methods: calculate(ohlcv), validate_entry(price, vwap), get_support_level(symbol), _validate_data(ohlcv)
  - Calculation: VWAP = sum((H+L+C)/3 * volume) / sum(volume)
  - Validation: Require >= 10 intraday bars, prices > 0, volumes >= 0
- `src/trading_bot/indicators/ema_calculator.py`: EMACalculator class
  - Methods: calculate_ema(prices, period), detect_crossover(short, long, prev_short, prev_long), check_proximity(price, ema, threshold), calculate_trend_angle(ema_series), _calculate_alpha(period)
  - Calculation: EMA = (price * alpha) + (prev_EMA * (1 - alpha)), alpha = 2/(period+1)
  - Initialization: First EMA = SMA of first N prices
- `src/trading_bot/indicators/macd_calculator.py`: MACDCalculator class
  - Methods: calculate(prices), validate_momentum(macd_line), detect_divergence(current, previous), check_exit_signal(current, previous), _calculate_histogram(macd, signal)
  - Calculation: MACD = EMA(12) - EMA(26), Signal = EMA(9) of MACD, Histogram = MACD - Signal
  - Uses: EMACalculator.calculate_ema() internally for fast/slow/signal EMAs

**Result Dataclasses** (in calculator files or separate models.py):
- VWAPResult: symbol, vwap, price, calculated_at, bars_used
- EMAResult: symbol, ema_9, ema_20, current_price, calculated_at, crossover
- CrossoverSignal: type, ema_short, ema_long, detected_at
- MACDResult: symbol, macd_line, signal_line, histogram, calculated_at
- DivergenceSignal: type, histogram_change, detected_at
- ExitSignal: reason, macd_value, signal_value, triggered_at
- EntryValidation: allowed, reason, vwap, macd, price, validated_at
- IndicatorSet: symbol, vwap, emas, macd, calculated_at

**Exception** (if not in error_handling/exceptions.py):
- InsufficientDataError(ValueError): symbol, required_bars, available_bars

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local-only (no deployment)
- Env vars: None (no new environment variables)
- Breaking changes: No (additive module, no changes to existing code)
- Migration: None (no database, stateless calculations)

**Build Commands**:
- No changes to build process (Python module, no compilation)

**Environment Variables**:
- No new environment variables required
- Uses existing MarketDataService configuration (if any)

**Database Migrations**:
- None required (no state persistence)

**Smoke Tests** (for manual validation):
- Calculate VWAP for AAPL, compare to TradingView
- Calculate EMAs (9/20) for AAPL, compare to TradingView
- Calculate MACD for AAPL, compare to TradingView
- Verify entry validation logic (allowed/blocked scenarios)
- Verify crossover detection (bullish/bearish)
- Verify exit signal triggers (MACD zero cross)

**Platform Coupling**:
- None (internal module, no deployment platform)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- All indicator values validated before return (no NaN, no invalid calculations)
- Entry validation always logs decision (Constitution §Audit_Everything)
- Exit signals always logged (Constitution §Audit_Everything)
- Failed calculations raise exceptions (Constitution §Fail_Safe)

**Testing Checklist**:
```gherkin
Given MarketDataService initialized with authenticated RobinhoodAuth
When bot calls TechnicalIndicatorsService.get_vwap("AAPL")
Then VWAP calculation completes in <500ms
  And VWAP value is positive Decimal
  And calculation logged with UTC timestamp
  And no exceptions raised

Given historical data available for AAPL (50+ days)
When bot calls TechnicalIndicatorsService.get_emas("AAPL")
Then EMA-9 and EMA-20 calculated successfully
  And EMA calculation completes in <500ms
  And crossover detection works (if crossover present)
  And no exceptions raised

Given historical data available for AAPL (50+ days)
When bot calls TechnicalIndicatorsService.get_macd("AAPL")
Then MACD, signal, histogram calculated successfully
  And MACD calculation completes in <1s
  And momentum validation works (MACD > 0 check)
  And no exceptions raised

Given current price = $152, VWAP = $150, MACD = +2.50
When bot calls TechnicalIndicatorsService.validate_entry("AAPL", Decimal("152"))
Then validation.allowed = True
  And validation.reason = "Price above VWAP (+1.33%) and MACD positive (+2.50)"
  And validation logged with UTC timestamp

Given current price = $148, VWAP = $150, MACD = +2.50
When bot calls TechnicalIndicatorsService.validate_entry("AAPL", Decimal("148"))
Then validation.allowed = False
  And validation.reason = "Price below VWAP (-1.33%)"
  And validation logged with UTC timestamp

Given previous MACD = +0.50, current MACD = -0.20
When bot calls TechnicalIndicatorsService.check_exit_signals("AAPL")
Then exit signal returned
  And exit_signal.reason = "MACD crossed negative"
  And exit signal logged with UTC timestamp
```

**Rollback Plan**:
- N/A (no deployment, local-only module)
- If integration causes issues: Remove indicator imports from bot.py
- No state to clean up (stateless service)
- No data to migrate (no persistence)

**Artifact Strategy**:
- N/A (local-only module, no deployment artifacts)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
1. Calculate VWAP for entry validation
2. Calculate EMAs and detect crossovers
3. Calculate MACD and check exit signals
4. Batch calculate all indicators
5. Validate entry (combined VWAP + MACD)
6. Refresh indicators intraday
7. Handle insufficient data errors
8. Run tests and validate coverage
9. Manual validation against TradingView

**Integration Points**:
- MarketDataService: Pass to TechnicalIndicatorsService.__init__()
- TradingLogger: Pass to TechnicalIndicatorsService.__init__()
- Bot entry logic: Call validate_entry() before placing orders
- Bot exit logic: Call check_exit_signals() during position monitoring
- Bot watchlist: Call refresh_indicators() every 5 minutes during trading hours

---

## [CALCULATION FLOWS]

### VWAP Calculation Flow
```
1. Fetch intraday OHLCV (1min or 5min bars from market open)
   ↓ MarketDataService.get_historical_data(symbol, interval="5minute", span="day")
2. Validate data (>= 10 bars, prices > 0, volumes >= 0)
   ↓ _validate_data(ohlcv)
3. Calculate typical price for each bar: (high + low + close) / 3
   ↓ ohlcv['typical_price'] = (ohlcv['high'] + ohlcv['low'] + ohlcv['close']) / 3
4. Calculate price * volume for each bar
   ↓ ohlcv['pv'] = ohlcv['typical_price'] * ohlcv['volume']
5. Calculate cumulative sum(price * volume)
   ↓ cumulative_pv = ohlcv['pv'].cumsum()
6. Calculate cumulative sum(volume)
   ↓ cumulative_volume = ohlcv['volume'].cumsum()
7. Calculate VWAP: cumulative_pv / cumulative_volume
   ↓ vwap = Decimal(str(cumulative_pv.iloc[-1] / cumulative_volume.iloc[-1]))
8. Return VWAPResult with latest VWAP value
   ↓ VWAPResult(symbol, vwap, price, calculated_at, bars_used)
```

### EMA Calculation Flow
```
1. Fetch historical OHLCV (100+ days for 20-period EMA)
   ↓ MarketDataService.get_historical_data(symbol, interval="day", span="3month")
2. Extract close prices
   ↓ prices = ohlcv['close']
3. Validate data (>= period * 2 bars)
   ↓ if len(prices) < period * 2: raise InsufficientDataError
4. Calculate alpha: 2 / (period + 1)
   ↓ alpha = 2 / (period + 1)
5. Initialize EMA: first value = SMA of first N prices
   ↓ ema[0] = prices[:period].mean()
6. For each subsequent price:
      EMA = (price * alpha) + (prev_EMA * (1 - alpha))
   ↓ for i in range(period, len(prices)):
       ema[i] = (prices[i] * alpha) + (ema[i-1] * (1 - alpha))
7. Return EMA series and latest values
   ↓ EMAResult(symbol, ema_9[-1], ema_20[-1], current_price, calculated_at, crossover)
```

### EMA Crossover Detection Flow
```
1. Get current and previous EMA values (9 and 20-period)
   ↓ ema_9_current, ema_20_current, ema_9_prev, ema_20_prev
2. Determine previous relationship: 9 < 20 or 9 > 20
   ↓ prev_below = ema_9_prev < ema_20_prev
3. Determine current relationship: 9 < 20 or 9 > 20
   ↓ current_above = ema_9_current > ema_20_current
4. Detect crossover:
   - Bullish: prev_below AND current_above
   - Bearish: NOT prev_below AND NOT current_above
   ↓ if prev_below and current_above:
       return CrossoverSignal(type="bullish", ...)
5. Return CrossoverSignal or None
   ↓ CrossoverSignal(type, ema_short, ema_long, detected_at) | None
```

### MACD Calculation Flow
```
1. Fetch historical OHLCV (100+ days)
   ↓ MarketDataService.get_historical_data(symbol, interval="day", span="3month")
2. Extract close prices
   ↓ prices = ohlcv['close']
3. Calculate 12-period EMA (fast)
   ↓ ema_12 = EMACalculator.calculate_ema(prices, period=12)
4. Calculate 26-period EMA (slow)
   ↓ ema_26 = EMACalculator.calculate_ema(prices, period=26)
5. Calculate MACD line: EMA-12 - EMA-26
   ↓ macd_line = ema_12 - ema_26
6. Calculate signal line: 9-period EMA of MACD line
   ↓ signal_line = EMACalculator.calculate_ema(macd_line, period=9)
7. Calculate histogram: MACD - Signal
   ↓ histogram = macd_line - signal_line
8. Return MACDResult with all components
   ↓ MACDResult(symbol, macd_line[-1], signal_line[-1], histogram[-1], calculated_at)
```

### Entry Validation Flow
```
1. Fetch current market price (or receive as parameter)
   ↓ price = Decimal("152.00")
2. Calculate VWAP
   ↓ vwap_result = VWAPCalculator.calculate(ohlcv_intraday)
3. Calculate MACD
   ↓ macd_result = MACDCalculator.calculate(prices_historical)
4. Check VWAP condition: price > VWAP
   ↓ vwap_ok = price > vwap_result.vwap
5. Check MACD condition: MACD > 0
   ↓ macd_ok = macd_result.macd_line > 0
6. Combine conditions (AND logic)
   ↓ allowed = vwap_ok AND macd_ok
7. Generate reason string
   ↓ if allowed:
       reason = f"Price above VWAP (+{pct}%) and MACD positive (+{macd})"
     else:
       reason = f"Price below VWAP (-{pct}%)" or "MACD negative ({macd})"
8. Return EntryValidation
   ↓ EntryValidation(allowed, reason, vwap, macd, price, validated_at)
9. Log validation decision
   ↓ logger.info(f"Entry validation: {symbol} {'ALLOWED' if allowed else 'BLOCKED'} - {reason}")
```

### Exit Signal Detection Flow
```
1. Get current MACD result
   ↓ current_macd = MACDCalculator.calculate(prices)
2. Get previous MACD result (stored from prior calculation)
   ↓ previous_macd = cached_macd_results[symbol]
3. Check for zero cross:
   - Previous MACD > 0 AND current MACD < 0
   ↓ if previous_macd.macd_line > 0 and current_macd.macd_line < 0:
       return ExitSignal(reason="MACD crossed negative", ...)
4. Check for bearish crossover:
   - Previous MACD > signal AND current MACD < signal
   ↓ if previous_macd.macd_line > previous_macd.signal_line and
       current_macd.macd_line < current_macd.signal_line:
       return ExitSignal(reason="MACD bearish crossover", ...)
5. Return ExitSignal or None
   ↓ ExitSignal(reason, macd_value, signal_value, triggered_at) | None
6. Log exit signal if detected
   ↓ if exit_signal:
       logger.warning(f"Exit signal: {symbol} - {exit_signal.reason}")
```

---

## [TESTING STRATEGY]

### Unit Tests (target: 90% coverage)

**VWAP Tests** (test_vwap_calculator.py):
- test_calculate_vwap_valid_data: 20 bars → calculate VWAP successfully
- test_calculate_vwap_insufficient_data: 5 bars → raise InsufficientDataError
- test_calculate_vwap_zero_volume: Zero volume bar → skip bar or raise
- test_validate_entry_above_vwap: price > VWAP → entry allowed (True)
- test_validate_entry_below_vwap: price < VWAP → entry blocked (False)
- test_vwap_matches_known_value: Test data with known VWAP → verify accuracy

**EMA Tests** (test_ema_calculator.py):
- test_calculate_ema_valid_data: 50 days → calculate 9 and 20-period EMAs
- test_calculate_ema_insufficient_data: 5 days → raise InsufficientDataError
- test_ema_matches_pandas_ewm: Compare to pandas.ewm() output → values match
- test_detect_crossover_bullish: 9 crosses above 20 → CrossoverSignal(type="bullish")
- test_detect_crossover_bearish: 9 crosses below 20 → CrossoverSignal(type="bearish")
- test_detect_crossover_no_cross: No crossover → None
- test_check_proximity_within_threshold: price within 2% of EMA → True
- test_check_proximity_outside_threshold: price >2% from EMA → False
- test_calculate_trend_angle: EMA series → calculate slope and angle

**MACD Tests** (test_macd_calculator.py):
- test_calculate_macd_valid_data: 50 days → calculate MACD, signal, histogram
- test_calculate_macd_insufficient_data: 20 days → raise InsufficientDataError
- test_macd_histogram_formula: Verify histogram = MACD - Signal
- test_validate_momentum_positive: MACD > 0 → True
- test_validate_momentum_negative: MACD < 0 → False
- test_detect_divergence_bullish: Histogram expanding → DivergenceSignal(type="bullish_divergence")
- test_detect_divergence_bearish: Histogram contracting → DivergenceSignal(type="bearish_divergence")
- test_check_exit_signal_zero_cross: MACD crosses below zero → ExitSignal(reason="MACD crossed negative")
- test_check_exit_signal_bearish_crossover: MACD crosses below signal → ExitSignal(reason="MACD bearish crossover")
- test_check_exit_signal_no_trigger: No exit condition → None

### Integration Tests (test_technical_indicators_service.py)

**End-to-End Indicator Flow**:
- test_get_all_indicators_batch: Mock MarketDataService → get_all_indicators() returns IndicatorSet
- test_validate_entry_allowed: price > VWAP AND MACD > 0 → EntryValidation(allowed=True)
- test_validate_entry_blocked_vwap: price < VWAP → EntryValidation(allowed=False, reason="Price below VWAP")
- test_validate_entry_blocked_macd: MACD < 0 → EntryValidation(allowed=False, reason="MACD negative")
- test_check_exit_signals_triggered: MACD crosses negative → list[ExitSignal]
- test_refresh_indicators: Multiple symbols → no exceptions, indicators updated
- test_error_propagation: MarketDataService raises DataValidationError → exception propagated

### Validation Tests

**Calculation Accuracy**:
- test_vwap_accuracy_manual: Test data with manually calculated VWAP → values match
- test_ema_accuracy_pandas: Compare EMA to pandas.ewm() → values match within 0.01
- test_macd_accuracy_tradingview: Compare MACD to TradingView (manual verification) → values match within 0.5%

### Performance Tests (with pytest-benchmark)

- benchmark_vwap_calculation: Target <500ms
- benchmark_ema_calculation: Target <500ms
- benchmark_macd_calculation: Target <1s
- benchmark_batch_calculation: Target <2s
- benchmark_refresh_5_symbols: Target <10s

---

## [CONFIGURATION]

**Environment Variables (.env)**:
```bash
# No new environment variables required
# Uses existing market data configuration from MarketDataService
```

**IndicatorConfig (in config.py)**:
```python
from dataclasses import dataclass, field

@dataclass
class IndicatorConfig:
    """Configuration for technical indicators."""

    # VWAP Configuration
    vwap_min_bars: int = 10  # Minimum intraday bars required for valid VWAP
    vwap_interval: str = "5minute"  # Intraday bar interval (1minute or 5minute)

    # EMA Configuration
    ema_periods: list[int] = field(default_factory=lambda: [9, 20])  # EMA periods to calculate
    ema_proximity_threshold_pct: float = 2.0  # Proximity threshold (% of EMA)

    # MACD Configuration
    macd_fast_period: int = 12  # MACD fast EMA period
    macd_slow_period: int = 26  # MACD slow EMA period
    macd_signal_period: int = 9  # MACD signal line period

    # Refresh Configuration
    refresh_interval_seconds: int = 300  # Indicator refresh interval (5 minutes)

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.vwap_min_bars < 10:
            raise ValueError("vwap_min_bars must be >= 10")
        if len(self.ema_periods) < 2:
            raise ValueError("ema_periods must contain at least 2 periods")
        if self.ema_proximity_threshold_pct <= 0:
            raise ValueError("ema_proximity_threshold_pct must be > 0")
        if self.macd_fast_period >= self.macd_slow_period:
            raise ValueError("macd_fast_period must be < macd_slow_period")
        if self.refresh_interval_seconds < 60:
            raise ValueError("refresh_interval_seconds must be >= 60")
```

**Usage in Bot**:
```python
from trading_bot.indicators import TechnicalIndicatorsService
from trading_bot.indicators.config import IndicatorConfig

# Create config with defaults
config = IndicatorConfig()

# Or customize
config = IndicatorConfig(
    vwap_min_bars=15,
    ema_proximity_threshold_pct=1.5,
    refresh_interval_seconds=600  # 10 minutes
)

# Pass to service
indicators = TechnicalIndicatorsService(market_data, config, logger)
```

---

## [IMPLEMENTATION PHASES]

### Phase 1: VWAP Calculator (T001-T010)
1. Create `src/trading_bot/indicators/` directory
2. Create `config.py` with IndicatorConfig dataclass
3. Create `vwap_calculator.py` with VWAPResult dataclass
4. Implement VWAP calculation with typical price formula
5. Implement entry validation (price vs VWAP)
6. Implement data validation (minimum bars, valid prices)
7. Write unit tests for VWAP calculations (test_vwap_calculator.py)
8. Verify VWAP accuracy against known values
9. Run mypy and ensure type safety
10. Achieve 90%+ test coverage for VWAP module

### Phase 2: EMA Calculator (T011-T020)
1. Create `ema_calculator.py` with EMAResult and CrossoverSignal dataclasses
2. Implement exponential smoothing algorithm (_calculate_alpha, calculate_ema)
3. Implement EMA initialization (SMA for first value)
4. Implement 9-period and 20-period EMA calculations
5. Implement crossover detection logic (detect_crossover)
6. Implement price proximity checking (check_proximity)
7. Implement trend angle calculation (calculate_trend_angle) [optional]
8. Write unit tests for EMA calculations (test_ema_calculator.py)
9. Verify EMA accuracy against pandas.ewm()
10. Achieve 90%+ test coverage for EMA module

### Phase 3: MACD Calculator (T021-T030)
1. Create `macd_calculator.py` with MACDResult, DivergenceSignal, ExitSignal dataclasses
2. Implement MACD line calculation (EMA-12 - EMA-26)
3. Implement signal line calculation (9-period EMA of MACD)
4. Implement histogram calculation (_calculate_histogram)
5. Implement momentum validation (validate_momentum)
6. Implement divergence detection (detect_divergence)
7. Implement exit signal logic (check_exit_signal)
8. Write unit tests for MACD calculations (test_macd_calculator.py)
9. Verify MACD accuracy against TradingView (manual)
10. Achieve 90%+ test coverage for MACD module

### Phase 4: Indicator Service Facade (T031-T040)
1. Create `__init__.py` with TechnicalIndicatorsService class
2. Implement constructor (inject MarketDataService, config, logger)
3. Implement get_vwap() method
4. Implement get_emas() method
5. Implement get_macd() method
6. Implement get_all_indicators() batch calculation
7. Implement validate_entry() with VWAP and MACD checks
8. Implement check_exit_signals() method
9. Implement refresh_indicators() for intraday updates [optional for v1]
10. Create EntryValidation and IndicatorSet dataclasses

### Phase 5: Testing & Validation (T041-T050)
1. Write integration tests (test_technical_indicators_service.py)
2. Test batch calculation (get_all_indicators)
3. Test entry validation (allowed/blocked scenarios)
4. Test exit signal detection
5. Test error propagation from MarketDataService
6. Validate calculations against TradingView for AAPL
7. Run comprehensive unit tests (target: 90% coverage)
8. Run mypy strict mode (no errors)
9. Run bandit security scan (no high-severity issues)
10. Run performance benchmarks (verify targets met)

---

## [SUCCESS CRITERIA]

**Acceptance Criteria** (from spec.md):
- ✅ All 14 functional requirements implemented
- ✅ Test coverage >=90% (NFR-005)
- ✅ VWAP calculation validated against known values
- ✅ EMA calculation matches pandas.ewm() output
- ✅ MACD calculation matches TradingView (within 0.5%)
- ✅ All entry validation scenarios pass (price above/below VWAP, MACD positive/negative)
- ✅ Crossover detection works for all test cases
- ✅ Exit signal triggers correctly on MACD zero cross
- ✅ Intraday updates work during trading hours (if implemented in v1)
- ✅ mypy passes with no errors (NFR-006)

**Quality Gates** (from spec.md):
- ✅ All unit tests pass (pytest tests/indicators/ -v)
- ✅ All integration tests pass
- ✅ Manual testing: Calculate VWAP for AAPL → matches TradingView
- ✅ Manual testing: Calculate EMAs (9/20) for AAPL → matches TradingView
- ✅ Manual testing: Calculate MACD for AAPL → matches TradingView
- ✅ Manual testing: Verify entry validation logic (allowed/blocked scenarios)
- ✅ Manual testing: Verify crossover detection (bullish/bearish)
- ✅ Manual testing: Verify exit signal triggers (MACD zero cross)
- ✅ No high-severity vulnerabilities (bandit scan)
- ✅ Performance targets met (VWAP <500ms, EMA <500ms, MACD <1s, batch <2s)
