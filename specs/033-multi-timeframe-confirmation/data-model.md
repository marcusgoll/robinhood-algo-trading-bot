# Data Model: 033-multi-timeframe-confirmation

## Entities

### TimeframeValidationResult
**Purpose**: Encapsulates the decision outcome of multi-timeframe validation with scores and reasoning

**Fields**:
- `status`: Enum (PASS, BLOCK, DEGRADED) - Final validation decision
- `aggregate_score`: Decimal (0.0-1.0) - Weighted score (daily*0.6 + 4h*0.4)
- `daily_score`: Decimal (0.0-1.0) - Daily timeframe trend score
- `4h_score`: Decimal (0.0-1.0) - 4-hour timeframe trend score
- `daily_indicators`: TimeframeIndicators - Daily indicator values
- `4h_indicators`: Optional[TimeframeIndicators] - 4H indicator values (None if unavailable)
- `reasons`: List[str] - Human-readable blocking reasons (e.g., ["Daily MACD negative", "Price below daily 20 EMA"])
- `timestamp`: datetime (UTC) - Validation execution timestamp
- `symbol`: str - Stock ticker symbol validated

**Validation Rules**:
- `status = PASS` if `aggregate_score > 0.5` (from FR-007)
- `status = BLOCK` if `aggregate_score <= 0.5`
- `status = DEGRADED` if higher-timeframe data unavailable after retries (from FR-011)
- `reasons` list populated only when `status = BLOCK`

**State Transitions**:
- Initial → PASS (aggregate score > 0.5)
- Initial → BLOCK (aggregate score <= 0.5)
- Initial → DEGRADED (data fetch failure after retries)

**Example**:
```python
TimeframeValidationResult(
    status=ValidationStatus.BLOCK,
    aggregate_score=Decimal("0.36"),  # (0.3*0.6 + 0.5*0.4) = 0.36
    daily_score=Decimal("0.3"),
    4h_score=Decimal("0.5"),
    daily_indicators=TimeframeIndicators(...),
    4h_indicators=TimeframeIndicators(...),
    reasons=["Daily MACD negative (-0.52)", "Price 2.3% below daily 20 EMA"],
    timestamp=datetime(2025, 10, 28, 14, 30, 0, tzinfo=UTC),
    symbol="AAPL"
)
```

---

### TimeframeIndicators
**Purpose**: Stores technical indicator values for a specific timeframe

**Fields**:
- `timeframe`: str - Timeframe identifier ("DAILY", "4H", "5MIN")
- `price`: Decimal - Current/latest price on this timeframe
- `ema_20`: Decimal - 20-period Exponential Moving Average
- `macd_line`: Decimal - MACD indicator value (12-26-9)
- `macd_positive`: bool - Whether MACD > 0 (bullish)
- `price_above_ema`: bool - Whether price > 20 EMA (bullish alignment)
- `bar_count`: int - Number of bars available for indicator calculation
- `timestamp`: datetime (UTC) - Latest bar timestamp

**Validation Rules**:
- `bar_count >= 30` for daily data (from FR-010)
- `bar_count >= 72` for 4H data (3 days * 24 hours / 10min interval = 72 bars, from FR-010)
- `macd_positive = True` if `macd_line > 0`
- `price_above_ema = True` if `price > ema_20`

**Scoring Logic**:
```python
def calculate_score(indicators: TimeframeIndicators) -> Decimal:
    """Score = 0.5 if MACD positive + 0.5 if price > EMA"""
    score = Decimal("0.0")
    if indicators.macd_positive:
        score += Decimal("0.5")
    if indicators.price_above_ema:
        score += Decimal("0.5")
    return score  # Range: 0.0 (bearish) to 1.0 (bullish)
```

**Example**:
```python
TimeframeIndicators(
    timeframe="DAILY",
    price=Decimal("150.25"),
    ema_20=Decimal("148.50"),
    macd_line=Decimal("0.82"),
    macd_positive=True,
    price_above_ema=True,
    bar_count=60,
    timestamp=datetime(2025, 10, 28, 16, 0, 0, tzinfo=UTC)
)
```

---

### ValidationStatus (Enum)
**Purpose**: Represents the outcome of multi-timeframe validation

**Values**:
- `PASS` - All validation checks passed, trade allowed
- `BLOCK` - Validation failed, trade should not proceed
- `DEGRADED` - Higher-timeframe data unavailable, fallback to single-timeframe mode

**Usage**:
```python
from enum import Enum

class ValidationStatus(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    DEGRADED = "DEGRADED"
```

---

### TimeframeValidationEvent (JSONL Log Schema)
**Purpose**: Structured log event for analytics and measurement

**Fields**:
- `event`: str - Always "timeframe_validation"
- `symbol`: str - Stock ticker
- `timestamp`: str (ISO8601) - Event timestamp
- `decision`: str - PASS | BLOCK | DEGRADED
- `aggregate_score`: float - Weighted score
- `daily_score`: float - Daily timeframe score
- `4h_score`: float | null - 4H score (null if unavailable)
- `daily_macd`: float - Daily MACD value
- `daily_price`: float - Daily latest price
- `daily_ema_20`: float - Daily 20 EMA
- `4h_macd`: float | null - 4H MACD value
- `4h_price`: float | null - 4H latest price
- `4h_ema_20`: float | null - 4H 20 EMA
- `reasons`: list[str] - Blocking reasons
- `validation_duration_ms`: int - Latency metric
- `data_fetch_retries`: int - Number of retry attempts
- `degraded_mode`: bool - Whether validation ran in degraded mode

**Example JSONL Line**:
```json
{"event":"timeframe_validation","symbol":"AAPL","timestamp":"2025-10-28T14:30:00Z","decision":"BLOCK","aggregate_score":0.36,"daily_score":0.3,"4h_score":0.5,"daily_macd":-0.52,"daily_price":150.25,"daily_ema_20":153.80,"4h_macd":0.15,"4h_price":150.25,"4h_ema_20":149.50,"reasons":["Daily MACD negative (-0.52)","Price 2.3% below daily 20 EMA"],"validation_duration_ms":1823,"data_fetch_retries":0,"degraded_mode":false}
```

---

## Relationships

```
TimeframeValidationResult (1) ----contains----> (1) TimeframeIndicators (daily)
TimeframeValidationResult (1) ----contains----> (0..1) TimeframeIndicators (4H, optional)
TimeframeValidationResult (1) ----uses----> (1) ValidationStatus (enum)

BullFlagDetector ----calls----> MultiTimeframeValidator ----returns----> TimeframeValidationResult
MultiTimeframeValidator ----creates----> TimeframeIndicators (per timeframe)
TimeframeValidationLogger ----writes----> TimeframeValidationEvent (JSONL)
```

---

## Data Flow Sequence

1. **BullFlagDetector** detects 5-minute pattern, calls MultiTimeframeValidator.validate()
2. **MultiTimeframeValidator** fetches daily OHLCV via MarketDataService (FR-001)
3. **MultiTimeframeValidator** creates TechnicalIndicatorsService instance for daily timeframe
4. **TechnicalIndicatorsService** calculates daily MACD and EMA → returns indicators
5. **MultiTimeframeValidator** creates TimeframeIndicators for daily with calculated values
6. **MultiTimeframeValidator** calculates daily_score from indicators (0.0-1.0)
7. **MultiTimeframeValidator** repeats steps 2-6 for 4H timeframe (FR-004)
8. **MultiTimeframeValidator** computes aggregate_score = daily_score * 0.6 + 4h_score * 0.4 (FR-006)
9. **MultiTimeframeValidator** determines status (PASS if score > 0.5, BLOCK otherwise) (FR-007)
10. **MultiTimeframeValidator** creates TimeframeValidationResult with all metadata
11. **TimeframeValidationLogger** writes TimeframeValidationEvent to JSONL (FR-008)
12. **MultiTimeframeValidator** returns result to BullFlagDetector

---

## Database Schema

**Not Applicable**: This feature does not require database persistence. All data is in-memory during validation, with structured logs written to JSONL files for post-hoc analytics.

---

## State Management

**Stateless Validation**: MultiTimeframeValidator has no persistent state between calls. Each validation is independent.

**Per-Timeframe Indicator State**: TechnicalIndicatorsService maintains state (_last_ema_9, _last_macd, etc.) but instances are created fresh per validation to prevent cross-timeframe pollution.

**Log Files**: TimeframeValidationEvent logs are append-only JSONL files with daily rotation:
- File: `logs/timeframe-validation/YYYY-MM-DD.jsonl`
- Rotation: Midnight UTC
- Retention: 90 days (configurable)
