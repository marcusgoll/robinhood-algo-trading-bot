# Research & Discovery: zone-breakout-detection

## Research Decisions

### Decision 1: Extend Existing ZoneDetector vs Create New BreakoutDetector

- **Decision**: Create new BreakoutDetector class that composes with ZoneDetector
- **Rationale**:
  - Breakout logic is distinct from zone identification (different concerns)
  - Preserves existing ZoneDetector contract (no breaking changes)
  - Allows independent testing and evolution
  - Follows composition over inheritance pattern
- **Alternatives**:
  - Add detect_breakouts() method to ZoneDetector: Rejected due to SRP violation (ZoneDetector already handles identification, clustering, strength scoring)
  - Create BreakoutService as standalone: Rejected due to tight coupling with Zone models
- **Source**: Constitution §Code_Quality (One function, one purpose - KISS principle)

### Decision 2: Volume Calculation Strategy

- **Decision**: Calculate 20-bar average volume using MarketDataService.get_historical_data()
- **Rationale**:
  - Spec FR-002 requires volume >1.3x of 20-bar average
  - MarketDataService already provides historical OHLCV data via get_historical_data()
  - 20-bar window matches industry standard for volume confirmation
  - Constitution §Data_Integrity: Use validated historical data, not raw API calls
- **Alternatives**:
  - Use current session volume: Rejected (not representative of recent average)
  - Store running volume average: Rejected (adds state complexity, violates stateless pattern)
- **Source**: src/trading_bot/market_data/market_data_service.py:118-194 (get_historical_data method)

### Decision 3: Zone Flipping Immutability

- **Decision**: Create new Zone instance with flipped type, do not mutate existing Zone
- **Rationale**:
  - Zone dataclass is immutable (frozen=False but designed for immutability)
  - Preserves audit trail (original zone state retained in logs)
  - Prevents race conditions in multi-threaded environments
  - Follows functional programming principles
- **Alternatives**:
  - Mutate existing Zone: Rejected (violates immutability pattern, loses historical state)
  - Add flipped_from field: Rejected (redundant with BreakoutEvent history)
- **Source**: src/trading_bot/support_resistance/models.py:36-123 (Zone dataclass design)

### Decision 4: Logging Strategy

- **Decision**: Extend ZoneLogger with log_breakout_event() method, use separate daily file (breakouts-YYYY-MM-DD.jsonl)
- **Rationale**:
  - ZoneLogger already provides thread-safe JSONL logging with daily rotation
  - Separate file allows easier query/analysis of breakout events specifically
  - Consistent pattern with existing log_zone_detection() and log_proximity_alert()
  - Constitution §Audit_Everything: All breakout decisions must be logged
- **Alternatives**:
  - Create BreakoutLogger: Rejected (unnecessary duplication of threading/rotation logic)
  - Log to same zones file: Rejected (mixing event types complicates analysis)
- **Source**: src/trading_bot/support_resistance/zone_logger.py:1-180

### Decision 5: Breakout Status Tracking (US5 - Whipsaw Detection)

- **Decision**: Implement status field in BreakoutEvent with PENDING/CONFIRMED/WHIPSAW enum
- **Rationale**:
  - Allows post-breakout validation (5-bar sustainability check per US5)
  - Provides data for 60% success rate target validation (HEART metrics)
  - Enables filtering of false breakouts in backtesting
  - Matches industry pattern (breakout → confirmation → validation)
- **Alternatives**:
  - Separate WhipsawEvent: Rejected (splits related data, complicates queries)
  - Boolean is_valid field: Rejected (loses granularity between pending and confirmed)
- **Source**: Spec.md US5 acceptance criteria (5-bar whipsaw validation)

---

## Components to Reuse (8 found)

- **src/trading_bot/support_resistance/zone_detector.py**: ZoneDetector class for zone identification
  - detect_zones() method: Returns list of identified zones
  - Pattern: Composition - BreakoutDetector will accept ZoneDetector output as input

- **src/trading_bot/support_resistance/models.py**: Immutable dataclasses
  - Zone: price_level, zone_type, strength_score, touch_count, timestamps, volume metadata
  - ZoneType enum: SUPPORT, RESISTANCE
  - TouchType enum: BOUNCE, REJECTION, BREAKOUT (already defined!)
  - Timeframe enum: DAILY, FOUR_HOUR

- **src/trading_bot/support_resistance/zone_logger.py**: Thread-safe structured logger
  - _get_daily_file_path(): Daily rotation logic
  - _lock: Threading.Lock for concurrent writes
  - Pattern: Extend with log_breakout_event() method

- **src/trading_bot/support_resistance/config.py**: Configuration loading
  - ZoneDetectionConfig.from_env(): Load from environment variables
  - Pattern: Create BreakoutConfig extending this pattern

- **src/trading_bot/market_data/market_data_service.py**: Market data fetching
  - get_quote(symbol): Real-time price with validation (NFR-001: <200ms)
  - get_historical_data(symbol, days): OHLCV bars for volume calculation
  - Pattern: Dependency injection via constructor

- **src/trading_bot/market_data/data_models.py**: Quote dataclass
  - Quote(symbol, price, timestamp, bid, ask, volume)
  - Pattern: Use for current price/volume fetching

- **src/trading_bot/error_handling/retry.py**: @with_retry decorator
  - Exponential backoff for API failures
  - Circuit breaker integration
  - Pattern: Apply to detect_breakout() method

- **tests/unit/support_resistance/test_zone_detector.py**: Test patterns
  - Mock fixtures for Zone objects
  - Test helpers for volume/price calculations
  - Pattern: Reuse fixtures for breakout detector tests

---

## New Components Needed (4 required)

- **src/trading_bot/support_resistance/breakout_detector.py**: Core breakout detection logic
  - BreakoutDetector class
  - detect_breakout(zone, current_price, current_volume, historical_volume): Breakout validation
  - _calculate_price_change_pct(zone_price, current_price): Price movement calculation
  - _calculate_volume_ratio(current_volume, avg_volume): Volume confirmation
  - flip_zone(zone, breakout_event): Create new Zone with flipped type + strength bonus

- **src/trading_bot/support_resistance/breakout_models.py**: New data models
  - BreakoutEvent dataclass: event_id, zone_id, timestamp, breakout_price, close_price, volume_ratio, old_zone_type, new_zone_type, status (PENDING/CONFIRMED/WHIPSAW)
  - BreakoutStatus enum: PENDING, CONFIRMED, WHIPSAW
  - Pattern: Follow Zone/ZoneTouch pattern from models.py

- **src/trading_bot/support_resistance/breakout_config.py**: Configuration
  - BreakoutConfig dataclass: price_threshold_pct (1.0%), volume_threshold (1.3x), validation_bars (5)
  - from_env() class method for environment variable loading
  - Pattern: Mirror ZoneDetectionConfig structure

- **tests/unit/support_resistance/test_breakout_detector.py**: Unit tests
  - test_detect_breakout_success: Price >1%, volume >1.3x → breakout
  - test_detect_breakout_insufficient_price: Price <1% → no breakout
  - test_detect_breakout_insufficient_volume: Volume <1.3x → no breakout
  - test_flip_zone: Verify RESISTANCE → SUPPORT flip with strength bonus
  - test_log_breakout_event: Verify JSONL logging
  - Target: 90% coverage per Constitution §Testing_Requirements

---

## Unknowns & Questions

None - all technical questions resolved during research phase.

---

## Constitution Alignment Check

✅ §Safety_First: No auto-trading, manual review required (breakout detection is advisory, not execution)
✅ §Code_Quality: Type hints required (all new code will use mypy --strict)
✅ §Risk_Management: No position sizing changes (breakout detection informs, doesn't execute)
✅ §Security: No credential handling (pure calculation logic)
✅ §Data_Integrity: Decimal precision for price/volume (avoiding float errors)
✅ §Testing_Requirements: 90% coverage target (unit + integration tests planned)
✅ §Audit_Everything: All breakout events logged to JSONL (FR-006, FR-007)

**Violations**: None detected
