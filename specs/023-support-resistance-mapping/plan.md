# Implementation Plan: Support/Resistance Zone Mapping

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11+, Decimal precision, MarketDataService reuse, StructuredLogger pattern
- Components to reuse: 5 (MarketDataService, BullFlagDetector pattern, StructuredLogger, MomentumConfig pattern, retry decorator)
- New components needed: 3 (ZoneDetector service, models dataclasses, ZoneLogger)

**Key Reuse Opportunities**:
- REUSE: `MarketDataService` for historical OHLCV data fetching (avoids duplicating API integration)
- REUSE: `BullFlagDetector` service architecture pattern (config, scan method, logging integration)
- REUSE: `StructuredTradeLogger` pattern for JSONL zone event logging (thread-safe, daily rotation)
- REUSE: Decimal precision pattern from backtest/account modules (§Code_Quality compliance)
- REUSE: Error handling retry decorator from `error_handling/retry.py`

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11+ (existing project stack)
- Data Processing: pandas for OHLCV analysis, NumPy for vectorized calculations
- Precision: decimal.Decimal for all price/volume calculations (§Code_Quality + NFR-003)
- Logging: Structured JSONL with daily rotation (extends StructuredTradeLogger pattern)
- Testing: pytest with type checking via mypy, linting via ruff

**Patterns**:
- Service Layer Pattern: `SupportResistanceDetector` follows `BullFlagDetector` architecture (config injection, scan method, graceful degradation)
- Dataclass Pattern: Immutable Zone/ZoneTouch/ProximityAlert entities with validation in `__post_init__`
- Repository Pattern: Not needed for MVP (in-memory processing, no database persistence)
- Strategy Pattern: Not needed for MVP (single detection algorithm, extensibility deferred)

**Dependencies** (no new packages required):
- Existing: `robin_stocks`, `pandas`, `numpy` (already in requirements.txt)
- Existing: `pytest`, `mypy`, `ruff` (already in dev dependencies)

**Rationale for No New Dependencies**:
- All required capabilities exist in current stack
- Reduces security surface area (§Security)
- Simplifies deployment (local-only, no infrastructure changes)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── support_resistance/
│   ├── __init__.py
│   ├── zone_detector.py         # Main detection service (US1-US5)
│   ├── models.py                 # Zone, ZoneTouch, ProximityAlert dataclasses
│   ├── zone_logger.py            # Structured JSONL logger for zone events
│   └── config.py                 # ZoneDetectionConfig dataclass
└── tests/
    ├── unit/support_resistance/
    │   ├── test_zone_detector.py
    │   ├── test_models.py
    │   └── test_zone_logger.py
    └── integration/support_resistance/
        └── test_zone_detector_integration.py
```

**Module Organization**:
- `zone_detector.py`: Core service (detect_zones, check_proximity, merge_overlapping_zones methods)
- `models.py`: Immutable dataclasses with validation and serialization (to_dict, to_jsonl_line)
- `zone_logger.py`: Thread-safe JSONL logger (follows StructuredTradeLogger pattern)
- `config.py`: Configuration dataclass (touch_threshold, volume_threshold, proximity_threshold_pct, min_days)

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 3 (Zone, ZoneTouch, ProximityAlert)
- Relationships: Zone has many ZoneTouch, Zone triggers many ProximityAlert
- Migrations required: No (in-memory only, optional JSONL logging)

**In-Memory Processing**:
- Zones calculated on-demand from historical data
- No database persistence for MVP (deferred to future enhancement)
- JSONL logging for backtesting analysis and auditing

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Zone analysis completes in <3 seconds for 90 days of daily data
- NFR-002: Proximity check completes in <100ms
- NFR-003: Decimal precision for all price calculations (no floating-point errors)
- NFR-004: Graceful degradation on missing data (log warning, skip analysis, continue)
- NFR-005: JSONL logging for all zone events

**Performance Strategy**:
- Vectorized calculations via NumPy for swing point identification (avoids Python loops)
- Pre-compute zone touches during detection (avoid re-scanning in proximity checks)
- Limit historical data to 90 days max (balances accuracy vs. performance)
- Index zones by price level for O(1) proximity lookups

---

## [SECURITY]

**Authentication Strategy**:
- Reuse existing RobinhoodAuth (no changes needed)
- API credentials via environment variables (§Security compliance)

**Authorization Model**:
- N/A - Local service, no multi-user access

**Input Validation**:
- Symbol validation: Alphanumeric 1-5 characters (reuse existing pattern)
- Days parameter: Integer 30-90 range
- Timeframe: Enum validation (DAILY, FOUR_HOUR)
- Current price: Decimal > 0 validation

**Data Protection**:
- No PII handling (only public market data)
- Logs stored locally (logs/zones/ directory)
- No encryption needed (public data)

---

## [EXISTING INFRASTRUCTURE - REUSE] (5 components)

**Services/Modules**:
- `src/trading_bot/market_data/market_data_service.py`: OHLCV data fetching with retry logic, validation, UTC timestamps
- `src/trading_bot/momentum/bull_flag_detector.py`: Service architecture pattern (config, scan method, error handling)
- `src/trading_bot/error_handling/retry.py`: @with_retry decorator for API resilience

**Logging**:
- `src/trading_bot/logging/structured_logger.py`: Thread-safe JSONL logger with daily rotation, <5ms write latency

**Configuration**:
- `src/trading_bot/momentum/config.py`: MomentumConfig pattern (dataclass with from_env classmethod)

**Utilities**:
- Decimal precision pattern from `src/trading_bot/backtest/models.py` and `src/trading_bot/account/account_data.py`

---

## [NEW INFRASTRUCTURE - CREATE] (3 components)

**Backend**:
- `src/trading_bot/support_resistance/zone_detector.py`: Main detection service
  - `detect_zones(symbol, days, timeframe)`: Identify S/R zones from historical data (US1, US4)
  - `calculate_strength_score(touches, volumes)`: Score zones by touches + volume bonus (US2)
  - `check_proximity(zones, current_price, threshold_pct)`: Flag approaching zones (US3)
  - `detect_breakout(zone, current_bar)`: Identify zone flips (US5)
  - `merge_overlapping_zones(zones, tolerance_pct)`: Consolidate nearby zones (FR-009)

- `src/trading_bot/support_resistance/models.py`: Dataclasses
  - `Zone`: Support/resistance level with metadata
  - `ZoneTouch`: Single price interaction record
  - `ProximityAlert`: Current price near zone flag
  - `ZoneType`, `Timeframe`, `TouchType` enums

- `src/trading_bot/support_resistance/zone_logger.py`: Structured logger
  - `log_zone_detection(symbol, zones, analysis_metadata)`: Log identified zones
  - `log_proximity_alert(alert)`: Log approaching zone events
  - `log_breakout(zone, breakout_metadata)`: Log zone flips

**Testing**:
- Unit tests: 12-15 test cases (zone detection, strength scoring, proximity, breakout, edge cases)
- Integration test: End-to-end with live API data (requires auth)

**No Database Migrations**: In-memory processing only

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local-only feature (no Vercel/Railway deployment)
- Env vars: None (reuses existing Robinhood API credentials)
- Breaking changes: No (pure additive feature)
- Migration: No

**Build Commands**:
- No changes (Python service, no build step required)

**Environment Variables**:
- No new variables required
- Reuses existing: `ROBINHOOD_USERNAME`, `ROBINHOOD_PASSWORD`, `ROBINHOOD_MFA_CODE`

**Database Migrations**:
- No (in-memory processing, optional JSONL logging to filesystem)

**Smoke Tests**:
- Not applicable (local-only feature, no staging/production deployment)

**Platform Coupling**:
- None (pure Python service, no platform-specific dependencies)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants**:
- Not applicable (local-only feature, no production deployment)

**Local Validation**:
```bash
# Run all tests
pytest tests/unit/support_resistance/ tests/integration/support_resistance/ -v

# Type checking
mypy src/trading_bot/support_resistance/

# Linting
ruff check src/trading_bot/support_resistance/

# Manual smoke test
python -c "from trading_bot.support_resistance.zone_detector import SupportResistanceDetector; print('Import successful')"
```

**Rollback Plan**:
- Delete `src/trading_bot/support_resistance/` directory
- Remove imports from calling code (bull flag integration in US6)
- No database rollback needed (no schema changes)

**Artifact Strategy**:
- Not applicable (no build artifacts, source code only)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Initial setup: No new dependencies, uses existing stack
- Validation workflow: pytest + mypy + ruff
- Manual testing: Interactive Python session with live API data
- Backtesting: Zone accuracy analysis against historical reversals
- Bull flag integration: Adjust profit targets based on nearest resistance (US6)

---

## [ALGORITHM DESIGN]

**Zone Detection Algorithm** (US1, US4):

1. **Fetch historical data**: Get OHLCV from MarketDataService (60-90 days for daily, 30 days for 4-hour)
2. **Identify swing points**:
   - Swing high: bar.high > (prev_bar.high AND next_bar.high)
   - Swing low: bar.low < (prev_bar.low AND next_bar.low)
3. **Cluster swing points**:
   - Group swing highs within 1.5% tolerance → candidate resistance zones
   - Group swing lows within 1.5% tolerance → candidate support zones
4. **Filter by touch count**:
   - Daily timeframe: Keep zones with >= 3 touches
   - 4-hour timeframe: Keep zones with >= 2 touches
5. **Calculate zone metadata**:
   - Price level: Median of clustered swing points
   - Touch dates: First and last touch timestamps
   - Volume stats: Average and max volume across touches
6. **Return sorted zones**: Order by strength score descending

**Strength Scoring Algorithm** (US2):

```python
def calculate_strength_score(touches: list[ZoneTouch], avg_volume: Decimal) -> int:
    base_score = len(touches)
    volume_bonus = sum(1 for touch in touches if touch.volume > avg_volume * Decimal("1.5"))
    return base_score + volume_bonus
```

**Proximity Check Algorithm** (US3):

```python
def check_proximity(zones: list[Zone], current_price: Decimal, threshold_pct: Decimal = Decimal("2.0")) -> list[ProximityAlert]:
    alerts = []
    for zone in zones:
        distance_pct = abs((current_price - zone.price_level) / zone.price_level) * 100

        if distance_pct <= threshold_pct:
            direction = (
                "APPROACHING_SUPPORT" if current_price > zone.price_level
                else "APPROACHING_RESISTANCE"
            )
            alerts.append(ProximityAlert(
                symbol=zone.symbol,
                zone_price=zone.price_level,
                current_price=current_price,
                distance_percent=distance_pct,
                direction=direction,
                timestamp=datetime.now(UTC)
            ))

    return sorted(alerts, key=lambda a: a.distance_percent)  # Closest first
```

**Breakout Detection Algorithm** (US5):

```python
def detect_breakout(zone: Zone, current_bar: dict, avg_volume: Decimal) -> bool:
    if zone.zone_type != ZoneType.RESISTANCE:
        return False  # Only track resistance breakouts for MVP

    # Check if close price > zone by 1%+
    breakout_price_threshold = zone.price_level * Decimal("1.01")
    price_breakout = current_bar['close'] > breakout_price_threshold

    # Check if volume > 1.3x average
    volume_confirmation = current_bar['volume'] > avg_volume * Decimal("1.3")

    return price_breakout and volume_confirmation
```

**Zone Merging Algorithm** (FR-009):

```python
def merge_overlapping_zones(zones: list[Zone], tolerance_pct: Decimal = Decimal("1.5")) -> list[Zone]:
    merged = []
    used = set()

    for i, zone_a in enumerate(zones):
        if i in used:
            continue

        cluster = [zone_a]
        for j, zone_b in enumerate(zones[i+1:], start=i+1):
            if j in used:
                continue

            price_diff_pct = abs((zone_a.price_level - zone_b.price_level) / zone_a.price_level) * 100
            if price_diff_pct <= tolerance_pct:
                cluster.append(zone_b)
                used.add(j)

        # Merge cluster: keep highest strength zone's price level
        strongest = max(cluster, key=lambda z: z.strength_score)
        merged.append(strongest)
        used.add(i)

    return merged
```

---

## [TDD APPROACH]

**Test-First Implementation Order**:

1. **Models validation** (test dataclass validation in `__post_init__`)
   - Test: Zone with negative price_level raises ValueError
   - Test: Zone with first_touch > last_touch raises ValueError
   - Test: ProximityAlert with distance > 2% raises ValueError

2. **Zone detection core logic** (test swing point identification)
   - Test: Identify swing highs from sample OHLCV data
   - Test: Cluster swing points within 1.5% tolerance
   - Test: Filter clusters by touch count (3+ for daily)

3. **Strength scoring** (test base + volume bonus calculation)
   - Test: 5 touches + 2 high-volume touches = score of 7
   - Test: Zones sorted by strength score descending

4. **Proximity alerts** (test distance calculation and filtering)
   - Test: Zone at $100, current $102 → 2% distance, APPROACHING_RESISTANCE
   - Test: Zone at $100, current $97.50 → 2.5% distance, no alert (beyond threshold)

5. **Breakout detection** (test price + volume confirmation)
   - Test: Resistance at $100, close $101.50 with 1.5x volume → breakout detected
   - Test: Resistance at $100, close $101.50 with 0.9x volume → no breakout (volume too low)

6. **Integration test** (end-to-end with real API)
   - Test: Fetch AAPL data, detect zones, verify 3-5 zones returned with valid metadata

---

## [RISK MITIGATION]

**Technical Risks**:

| Risk | Impact | Mitigation |
|------|--------|------------|
| Insufficient historical data (<30 days) | Zone detection fails | Graceful degradation: Return empty list + warning log (FR-008) |
| API rate limiting during data fetch | Detection delays | Reuse existing @with_retry decorator with exponential backoff |
| Floating-point precision errors in price calculations | Incorrect zone levels | Use Decimal for all price/volume math (NFR-003) |
| Sideways choppy markets with no clear zones | False positives | Require minimum 3 touches + volume confirmation (FR-001, FR-004) |

**Performance Risks**:

| Risk | Impact | Mitigation |
|------|--------|------------|
| Analysis >3s for 90 days of data | Violates NFR-001 | Use NumPy vectorization for swing point detection |
| Proximity check >100ms | Violates NFR-002 | Pre-compute zones, use simple distance calculation (no API calls) |

**Operational Risks**:

| Risk | Impact | Mitigation |
|------|--------|------------|
| Log files fill disk space | Service crashes | Daily file rotation + manual cleanup (no auto-purge for MVP) |
| Zone logger thread-safety issues | Data corruption | Reuse proven StructuredTradeLogger pattern with file locking |

---

## [SUCCESS CRITERIA]

From spec.md HEART metrics:

- **Task Success**: Zone hit rate >70% (price reaches zone ±0.5% within 10 bars)
- **Task Success**: Breakout success >60% (price sustains above zone without reversal)
- **Engagement**: >50% of trades consider zone proximity before entry
- **Retention**: Average zone lifespan >14 days before invalidation

**Validation Approach**:
- Backtest zone accuracy on 6 months of historical data (Jan-Jun 2025)
- Measure hit rate, false positive rate, average lifespan
- Compare to targets before shipping bull flag integration (US6)
