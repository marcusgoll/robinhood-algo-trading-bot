# Data Model: zone-bull-flag-integration

## Entities

### TargetCalculation
**Purpose**: Preserves bull flag profit target calculation results with zone adjustment metadata for backtesting and audit trail

**Fields**:
- `adjusted_target`: Decimal - Final profit target to use for trade (either zone-adjusted or original 2:1)
- `original_2r_target`: Decimal - Baseline 2:1 R:R calculation (entry + pole_height * 2)
- `adjustment_reason`: str - Why target was/wasn't adjusted ("resistance_zone_closer" | "no_zone_within_range" | "zone_detector_unavailable" | "zone_detection_error" | "zone_detection_timeout")
- `resistance_zone_price`: Decimal | None - Price level of nearest resistance zone (None if no zone found)
- `resistance_zone_strength`: int | None - Strength score of resistance zone (None if no zone found)

**Validation Rules**:
- `adjusted_target`: Must be positive (> 0) - from requirement FR-002
- `original_2r_target`: Must be positive (> 0) - from BullFlagPattern validation
- `original_2r_target`: Must be >= adjusted_target (cannot adjust upward) - from business logic
- `adjustment_reason`: Must be one of 5 enum values - from requirement FR-005
- `resistance_zone_price`: If provided, must be positive (> 0) - from Zone model validation
- `resistance_zone_strength`: If provided, must be non-negative (>= 0) - from Zone model validation

**State Transitions** (immutable dataclass):
- Created → Frozen (no state transitions, immutable after creation)

---

## Integration Points

### BullFlagDetector → ZoneDetector (Optional Dependency)

**Dependency Injection**:
```python
class BullFlagDetector:
    def __init__(
        self,
        config: MomentumConfig,
        market_data_service: MarketDataService,
        momentum_logger: MomentumLogger | None = None,
        zone_detector: ZoneDetector | None = None  # NEW: Optional injection
    ):
        self.zone_detector = zone_detector
```

**Purpose**: Enable zone-adjusted targets when ZoneDetector available, graceful degradation when unavailable

### BullFlagDetector → ProximityChecker.find_nearest_resistance()

**Method Call**:
```python
from ..support_resistance.proximity_checker import ProximityChecker

# In BullFlagDetector._adjust_target_for_zones():
if self.zone_detector is not None:
    zones = self.zone_detector.detect_zones(symbol, days=60, timeframe=Timeframe.DAILY)
    proximity_checker = ProximityChecker(self.zone_detector.config)
    nearest_resistance = proximity_checker.find_nearest_resistance(entry_price, zones)
```

**Purpose**: Reuse existing zone lookup logic to find resistance above entry price

### TargetCalculation → JSONL Logging

**Serialization**:
```python
# Log to MomentumLogger
target_calc_dict = {
    "event": "target_calculated",
    "symbol": symbol,
    "entry": float(entry_price),
    "adjusted_target": float(target_calc.adjusted_target),
    "original_target": float(target_calc.original_2r_target),
    "reason": target_calc.adjustment_reason,
    "zone_price": float(target_calc.resistance_zone_price) if target_calc.resistance_zone_price else None,
    "zone_strength": target_calc.resistance_zone_strength
}
self.logger.log_signal(target_calc_dict, {"source": "bull_flag_target_adjustment"})
```

**Purpose**: Audit trail for backtesting comparison (spec US2, NFR-003)

---

## Database Schema

**No database changes required** - This feature only modifies in-memory calculations and logging

---

## API Schemas

**No external API changes** - Internal service integration only

**Internal Type Signatures**:

```python
# New dataclass
@dataclass(frozen=True)
class TargetCalculation:
    adjusted_target: Decimal
    original_2r_target: Decimal
    adjustment_reason: str
    resistance_zone_price: Decimal | None
    resistance_zone_strength: int | None

    def __post_init__(self) -> None:
        """Validate target calculation fields."""
        if self.adjusted_target <= 0:
            raise ValueError(f"adjusted_target must be positive, got {self.adjusted_target}")
        if self.original_2r_target <= 0:
            raise ValueError(f"original_2r_target must be positive, got {self.original_2r_target}")
        if self.adjusted_target > self.original_2r_target:
            raise ValueError(
                f"adjusted_target ({self.adjusted_target}) cannot exceed "
                f"original_2r_target ({self.original_2r_target})"
            )
        valid_reasons = {
            "resistance_zone_closer",
            "no_zone_within_range",
            "zone_detector_unavailable",
            "zone_detection_error",
            "zone_detection_timeout"
        }
        if self.adjustment_reason not in valid_reasons:
            raise ValueError(f"adjustment_reason must be one of {valid_reasons}")
        if self.resistance_zone_price is not None and self.resistance_zone_price <= 0:
            raise ValueError(f"resistance_zone_price must be positive, got {self.resistance_zone_price}")
        if self.resistance_zone_strength is not None and self.resistance_zone_strength < 0:
            raise ValueError(f"resistance_zone_strength must be non-negative, got {self.resistance_zone_strength}")

# Modified method signature
class BullFlagDetector:
    def _calculate_targets(
        self,
        pole_high: float,
        pole_low: float,
        flag_high: float,
        symbol: str,  # NEW: Required for zone lookup
        entry_price: Decimal  # NEW: Required for zone comparison
    ) -> TargetCalculation:  # CHANGED: Returns TargetCalculation instead of tuple[float, float]
        """Calculate breakout price and zone-adjusted price target."""
        ...
```

**Backward Compatibility Strategy**:
- Existing code using `_calculate_targets()` will break (it's a private method, acceptable)
- Public `scan()` method signature unchanged, returns `list[MomentumSignal]` as before
- `MomentumSignal.details` dictionary now includes both `price_target` (adjusted) and `original_2r_target`

---

## State Shape (Internal)

**BullFlagDetector State** (instance attributes):
```python
class BullFlagDetector:
    config: MomentumConfig
    market_data: MarketDataService
    logger: MomentumLogger
    zone_detector: ZoneDetector | None  # NEW: Optional zone detection service
```

**TargetCalculation State** (immutable):
```python
TargetCalculation(
    adjusted_target=Decimal("139.50"),
    original_2r_target=Decimal("156.00"),
    adjustment_reason="resistance_zone_closer",
    resistance_zone_price=Decimal("155.00"),
    resistance_zone_strength=7
)
```
