# Data Model: technical-indicators

## Entities

### VWAPResult
**Purpose**: Encapsulates VWAP calculation result with context

**Fields**:
- `symbol`: str - Stock ticker symbol (e.g., "AAPL")
- `vwap`: Decimal - Calculated VWAP value (typical price weighted by volume)
- `price`: Decimal - Current market price for comparison
- `calculated_at`: datetime - UTC timestamp of calculation
- `bars_used`: int - Number of intraday bars used in calculation (min 10)

**Relationships**: None (stateless calculation result)

**Validation Rules**:
- `vwap`: Must be > 0 (from requirement FR-001)
- `price`: Must be > 0 (from requirement FR-013)
- `bars_used`: Must be >= 10 (from requirement FR-001)
- `calculated_at`: Must be in UTC timezone (Constitution §Data_Integrity)

**State Transitions**: N/A (immutable dataclass)

---

### EMAResult
**Purpose**: Encapsulates EMA calculation results with optional crossover signal

**Fields**:
- `symbol`: str - Stock ticker symbol
- `ema_9`: Decimal - 9-period exponential moving average
- `ema_20`: Decimal - 20-period exponential moving average
- `current_price`: Decimal - Latest close price
- `calculated_at`: datetime - UTC timestamp of calculation
- `crossover`: CrossoverSignal | None - Optional crossover event detected

**Relationships**:
- Has optional: CrossoverSignal (embedded, not separate entity)

**Validation Rules**:
- `ema_9`: Must be > 0 (from requirement FR-004)
- `ema_20`: Must be > 0 (from requirement FR-004)
- `current_price`: Must be > 0 (from requirement FR-013)
- `calculated_at`: Must be in UTC (Constitution §Data_Integrity)

**State Transitions**: N/A (immutable dataclass)

---

### CrossoverSignal
**Purpose**: Captures EMA crossover event (bullish or bearish)

**Fields**:
- `type`: str - Crossover type: "bullish" (9 crossed above 20) or "bearish" (9 crossed below 20)
- `ema_short`: Decimal - 9-period EMA value at crossover
- `ema_long`: Decimal - 20-period EMA value at crossover
- `detected_at`: datetime - UTC timestamp of detection

**Relationships**: Embedded in EMAResult

**Validation Rules**:
- `type`: Must be "bullish" or "bearish" (from requirement FR-005)
- Bullish: Previous(ema_short < ema_long) AND Current(ema_short > ema_long)
- Bearish: Previous(ema_short > ema_long) AND Current(ema_short < ema_long)

**State Transitions**: N/A (immutable dataclass)

---

### MACDResult
**Purpose**: Encapsulates MACD indicator components

**Fields**:
- `symbol`: str - Stock ticker symbol
- `macd_line`: Decimal - MACD line value (EMA-12 - EMA-26)
- `signal_line`: Decimal - Signal line value (9-period EMA of MACD)
- `histogram`: Decimal - Histogram value (MACD - Signal)
- `calculated_at`: datetime - UTC timestamp of calculation

**Relationships**: None (stateless calculation result)

**Validation Rules**:
- All fields can be negative (momentum indicators cross zero)
- `histogram`: Must equal macd_line - signal_line (from requirement FR-008)
- `calculated_at`: Must be in UTC (Constitution §Data_Integrity)

**State Transitions**: N/A (immutable dataclass)

---

### DivergenceSignal
**Purpose**: Captures MACD divergence event (lines moving apart or converging)

**Fields**:
- `type`: str - Divergence type: "bullish_divergence" (histogram expanding) or "bearish_divergence" (histogram contracting)
- `histogram_change`: Decimal - Change in histogram magnitude
- `detected_at`: datetime - UTC timestamp of detection

**Relationships**: Returned by MACDCalculator.detect_divergence()

**Validation Rules**:
- `type`: Must be "bullish_divergence" or "bearish_divergence" (from requirement FR-010)
- Bullish: histogram_change > 0 (lines moving apart)
- Bearish: histogram_change < 0 (lines converging)

**State Transitions**: N/A (immutable dataclass)

---

### ExitSignal
**Purpose**: Captures exit trigger from MACD momentum reversal

**Fields**:
- `reason`: str - Exit reason: "MACD crossed negative" or "MACD bearish crossover"
- `macd_value`: Decimal - Current MACD line value
- `signal_value`: Decimal - Current signal line value
- `triggered_at`: datetime - UTC timestamp of trigger

**Relationships**: Returned by MACDCalculator.check_exit_signal()

**Validation Rules**:
- `reason`: Must describe specific exit condition (from requirement FR-011)
- MACD crossed negative: previous_macd > 0 AND current_macd < 0
- MACD bearish crossover: previous_macd > signal AND current_macd < signal

**State Transitions**: N/A (immutable dataclass)

---

### EntryValidation
**Purpose**: Consolidated entry validation result combining VWAP and MACD checks

**Fields**:
- `allowed`: bool - Entry allowed (True) or blocked (False)
- `reason`: str - Human-readable explanation ("Price above VWAP and MACD positive", "Price below VWAP", etc.)
- `vwap`: Decimal - Current VWAP value
- `macd`: Decimal - Current MACD line value
- `price`: Decimal - Current market price
- `validated_at`: datetime - UTC timestamp of validation

**Relationships**: Returned by TechnicalIndicatorsService.validate_entry()

**Validation Rules**:
- `allowed`: True only if (price > vwap) AND (macd > 0) (from requirements FR-002, FR-009)
- `reason`: Must explain specific failure if allowed=False (Constitution §Audit_Everything)

**State Transitions**: N/A (immutable dataclass)

---

### IndicatorSet
**Purpose**: Complete set of all indicators for a symbol (batch result)

**Fields**:
- `symbol`: str - Stock ticker symbol
- `vwap`: VWAPResult - VWAP calculation result
- `emas`: EMAResult - EMA calculation results
- `macd`: MACDResult - MACD calculation result
- `calculated_at`: datetime - UTC timestamp of batch calculation

**Relationships**:
- Has one: VWAPResult
- Has one: EMAResult
- Has one: MACDResult

**Validation Rules**:
- All components must be for same symbol
- All timestamps must be within 5 seconds (atomic batch calculation)

**State Transitions**: N/A (immutable dataclass)

---

### IndicatorConfig
**Purpose**: Configuration for indicator calculations and thresholds

**Fields**:
- `vwap_min_bars`: int = 10 - Minimum intraday bars required for VWAP
- `ema_periods`: list[int] = [9, 20] - EMA periods to calculate
- `ema_proximity_threshold_pct`: float = 2.0 - Proximity threshold (2% of EMA)
- `macd_fast_period`: int = 12 - MACD fast EMA period
- `macd_slow_period`: int = 26 - MACD slow EMA period
- `macd_signal_period`: int = 9 - MACD signal line period
- `refresh_interval_seconds`: int = 300 - Indicator refresh interval (5 minutes)

**Relationships**: Injected into calculator classes

**Validation Rules**:
- `vwap_min_bars`: Must be >= 10 (statistical significance)
- `ema_periods`: Must contain at least 2 periods
- `ema_proximity_threshold_pct`: Must be > 0
- `macd_fast_period` < `macd_slow_period` (standard MACD)
- `refresh_interval_seconds`: Must be >= 60 (avoid rate limits)

**State Transitions**: N/A (configuration object)

---

## Database Schema (Mermaid)

N/A - No database persistence required. All indicators are calculated on-demand from market data.

**Rationale**: Technical indicators are derived calculations, not stored state. OHLCV data comes from MarketDataService (robin_stocks API), calculations are stateless and reproducible.

---

## API Schemas

### TechnicalIndicatorsService API

```python
class TechnicalIndicatorsService:
    """Facade for technical indicator calculations."""

    def __init__(
        self,
        market_data: MarketDataService,
        config: IndicatorConfig,
        logger: TradingLogger
    ) -> None: ...

    def get_vwap(self, symbol: str) -> VWAPResult:
        """Calculate current VWAP for symbol."""
        ...

    def get_emas(self, symbol: str, periods: list[int] | None = None) -> EMAResult:
        """Calculate EMAs for symbol (default: 9 and 20-period)."""
        ...

    def get_macd(self, symbol: str) -> MACDResult:
        """Calculate MACD for symbol (12/26/9 periods)."""
        ...

    def get_all_indicators(self, symbol: str) -> IndicatorSet:
        """Calculate all indicators for symbol (batch operation)."""
        ...

    def validate_entry(self, symbol: str, price: Decimal) -> EntryValidation:
        """Validate entry: Check price > VWAP and MACD > 0."""
        ...

    def check_exit_signals(self, symbol: str) -> list[ExitSignal]:
        """Check for MACD exit signals (zero cross, bearish crossover)."""
        ...

    def refresh_indicators(self, symbols: list[str]) -> None:
        """Refresh indicators for multiple symbols (intraday update)."""
        ...
```

### Calculator Internal APIs

```python
class VWAPCalculator:
    def calculate(self, ohlcv: pd.DataFrame) -> VWAPResult: ...
    def validate_entry(self, price: Decimal, vwap: Decimal) -> bool: ...

class EMACalculator:
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series: ...
    def detect_crossover(
        self, ema_short: Decimal, ema_long: Decimal,
        prev_short: Decimal, prev_long: Decimal
    ) -> CrossoverSignal | None: ...
    def check_proximity(self, price: Decimal, ema: Decimal, threshold_pct: float) -> bool: ...

class MACDCalculator:
    def calculate(self, prices: pd.Series) -> MACDResult: ...
    def validate_momentum(self, macd_line: Decimal) -> bool: ...
    def detect_divergence(self, current: MACDResult, previous: MACDResult) -> DivergenceSignal | None: ...
    def check_exit_signal(self, current: MACDResult, previous: MACDResult) -> ExitSignal | None: ...
```

---

## State Shape (Not applicable)

**Rationale**: This is a backend/API module with no frontend state. All state is ephemeral calculation results returned as dataclasses.

If frontend integration needed in future, state would be:
```typescript
interface IndicatorsState {
  indicators: IndicatorSet | null
  loading: boolean
  error: Error | null
  lastRefresh: Date | null
}
```
