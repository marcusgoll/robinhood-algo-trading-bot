# Feature Specification: Support/Resistance Zone Mapping

**Branch**: `feature/023-support-resistance-mapping`
**Created**: 2025-10-21
**Status**: Draft

## User Scenarios

### Primary User Story
As a trader using the bot, I want to identify key support and resistance zones from daily and 4-hour price action so that I can better time entries near support, set realistic profit targets at resistance, and avoid entering positions in low-probability areas between zones.

### Acceptance Scenarios
1. **Given** historical OHLCV data for a symbol, **When** the bot analyzes daily and 4-hour timeframes, **Then** the system identifies major price levels where price has repeatedly bounced or reversed
2. **Given** identified support/resistance zones, **When** the current price approaches within 2% of a zone, **Then** the bot flags this as a high-probability entry or exit area
3. **Given** a bull flag pattern with breakout signal, **When** the nearest resistance zone is at 3% gain, **Then** the bot adjusts the profit target to reflect realistic resistance rather than using fixed 2:1 ratios
4. **Given** price breaking through a resistance zone with increased volume, **When** the breakout is confirmed, **Then** the old resistance becomes new support and the bot updates zone classifications

### Edge Cases
- What happens when insufficient historical data is available (less than 30 days for daily zones)?
- How does the system handle ranges without clear support/resistance (sideways choppy markets)?
- What happens when multiple zones cluster within 1-2% of each other?
- How does the system differentiate between weak touches and strong rejections at zones?

## User Stories (Prioritized)

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As a trader, I want to identify daily support/resistance zones from the past 30-90 days so that I can see the most significant price levels that institutions and other traders are watching
  - **Acceptance**:
    - System analyzes daily OHLCV data for past 60 days (minimum 30, optimal 90)
    - Identifies price levels with 3+ touches (swing highs or swing lows within 1.5% tolerance)
    - Returns list of zones with price level, strength score (number of touches), and type (support/resistance)
    - Each zone includes first touch date and most recent touch date
  - **Independent test**: Run analysis on AAPL with 60 days of data, verify 3-5 zones identified with correct touch counts
  - **Effort**: M (6-8 hours)

- **US2** [P1]: As a trader, I want to see zone strength scored by number of touches and volume profile so that I can prioritize the most reliable zones for trade decisions
  - **Acceptance**:
    - Each zone has a strength score: Base score = touch count, bonus +1 for each high-volume touch (volume >1.5x average)
    - Zones sorted by strength score descending
    - Zone metadata includes average volume at touches and highest volume touch
  - **Independent test**: Given 5 identified zones, verify strength scores correctly rank by touches + volume bonus
  - **Effort**: S (3-4 hours)

- **US3** [P1]: As a trader, I want the bot to alert me when current price is within 2% of a support or resistance zone so that I can prepare for potential entry or exit decisions
  - **Acceptance**:
    - Real-time price proximity check: calculate distance from current price to each zone
    - Flag zones within 2% as "approaching" with direction (price moving toward support vs resistance)
    - Log proximity alerts: "Price $152.00 approaching resistance zone at $155.00 (+1.97%)"
    - Return list of approaching zones sorted by distance (closest first)
  - **Independent test**: Given current price $150 and resistance at $153, verify proximity alert triggers correctly
  - **Effort**: S (2-3 hours)

**Priority 2 (Enhancement)**

- **US4** [P2]: As a trader, I want 4-hour support/resistance zones in addition to daily zones so that I can identify intraday levels for more precise entries and exits
  - **Acceptance**:
    - Analyzes 4-hour OHLCV data for past 30 days (approximately 180 four-hour bars)
    - Identifies zones with 2+ touches (lower threshold than daily due to shorter timeframe)
    - Differentiates daily vs 4-hour zones in output (zone_timeframe field)
    - Daily zones take priority over 4-hour zones when both exist at same level
  - **Depends on**: US1
  - **Effort**: M (4-6 hours)

- **US5** [P2]: As a trader, I want the bot to detect breakouts through resistance zones with volume confirmation so that I can identify when old resistance becomes new support
  - **Acceptance**:
    - Detects when price closes above resistance zone by >1% with volume >1.3x average
    - Flips zone classification: resistance → support
    - Logs breakout event with timestamp, price, volume ratio, and zone flip
    - Maintains breakout history for each zone
  - **Depends on**: US1, US2
  - **Effort**: M (5-7 hours)

**Priority 3 (Nice-to-have)**

- **US6** [P3]: As a trader, I want to integrate support/resistance zones with my bull flag entry logic so that profit targets are adjusted to the nearest resistance zone rather than using fixed R:R ratios
  - **Acceptance**:
    - When bull flag generates entry signal, calculate distance to nearest resistance zone above entry
    - If resistance zone is closer than 2:1 R:R target, adjust target to 90% of zone price
    - Log target adjustment: "Target adjusted to $154.50 (resistance zone at $155.00, original 2:1 target $156.00)"
    - If no resistance zone within 5%, use standard 2:1 R:R target
  - **Depends on**: US1, existing bull flag entry logic
  - **Effort**: M (4-5 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (zone identification, strength scoring, proximity alerts), validate accuracy with historical analysis, then add US4-US6 based on trading performance improvements.

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Task Success** | Accurate zone identification | Zones correctly predict reversals | Zone hit rate (price reaches zone ±0.5%) | >70% hit rate on identified zones | False positives <30% |
| **Task Success** | Reliable breakout detection | Breakouts sustain without reversal | Breakout success rate (no return below zone within 5 bars) | >60% successful breakouts | Whipsaw rate <40% |
| **Engagement** | Zone integration with entry logic | Trades using zone analysis | % of trades considering zones | >50% of entries near support zones | Entry quality improvement measurable |
| **Retention** | Ongoing zone usefulness | Zones remain relevant over time | Zone lifespan (days until invalidated) | Average >14 days active | <10% invalidated within 3 days |

## Requirements

### Functional (testable only)

- **FR-001**: System MUST identify support zones from swing lows where price bounced 3+ times within 1.5% price tolerance
- **FR-002**: System MUST identify resistance zones from swing highs where price reversed 3+ times within 1.5% price tolerance
- **FR-003**: System MUST analyze daily timeframe OHLCV data for minimum 30 days, optimal 60-90 days
- **FR-004**: System MUST calculate zone strength score: base = touch count + bonus (+1 per high-volume touch where volume >1.5x average)
- **FR-005**: System MUST detect when current price is within 2% of any identified zone and flag as "approaching"
- **FR-006**: System MUST return zone metadata including: price level, type (support/resistance), strength score, touch count, first touch date, last touch date, average volume, highest volume touch
- **FR-007**: System MUST sort identified zones by strength score descending
- **FR-008**: System MUST handle insufficient data gracefully (return empty zones list with warning if <30 days available)
- **FR-009**: System MUST merge overlapping zones (within 1.5% of each other) into single zone using highest-strength level
- **FR-010**: System MUST log all zone identification events with symbol, timeframe, zone count, and analysis timestamp

### Non-Functional

- **NFR-001**: Performance: Zone analysis MUST complete in <3 seconds for 90 days of daily data
- **NFR-002**: Performance: Proximity check for current price MUST complete in <100ms
- **NFR-003**: Data Integrity: All price calculations MUST use Decimal precision to avoid floating-point errors
- **NFR-004**: Error Handling: System MUST gracefully degrade on missing data (log warning, skip analysis, continue bot operation)
- **NFR-005**: Logging: All zone events MUST be logged to structured JSONL format for backtesting analysis
- **NFR-006**: Constitution Compliance: MUST follow §Data_Integrity (UTC timestamps, data validation), §Safety_First (fail-safe on errors), §Audit_Everything (structured logs)

### Key Entities

- **Zone**: Represents a support or resistance level
  - Attributes: price_level (Decimal), zone_type (Enum: SUPPORT/RESISTANCE), strength_score (int), touch_count (int), first_touch_date (datetime), last_touch_date (datetime), average_volume (Decimal), highest_volume_touch (Decimal), timeframe (Enum: DAILY/FOUR_HOUR)
  - Relationships: Belongs to a symbol, can have breakout events

- **ZoneTouch**: Represents a single price interaction with a zone
  - Attributes: zone_id, touch_date (datetime), price (Decimal), volume (Decimal), touch_type (Enum: BOUNCE/REJECTION/BREAKOUT)
  - Relationships: Belongs to a Zone

- **ProximityAlert**: Represents current price near a zone
  - Attributes: symbol, zone_id, current_price (Decimal), zone_price (Decimal), distance_percent (Decimal), direction (Enum: APPROACHING_SUPPORT/APPROACHING_RESISTANCE), timestamp (datetime)
  - Relationships: References a Zone

## Context Strategy & Signal Design

- **System prompt altitude**: Mid-level - Focus on zone detection algorithm specifics (swing point identification, clustering, strength scoring)
- **Tool surface**: MarketDataService (historical OHLCV), Decimal math utilities, structured logging
- **Examples in scope**:
  1. Daily zone identification with 3+ touches
  2. Zone strength scoring with volume bonus
  3. Proximity alert triggering within 2%
- **Context budget**: ~15k tokens (light feature, minimal dependencies)
- **Retrieval strategy**: JIT - Load historical data on-demand per symbol
- **Memory artifacts**: Update NOTES.md after each phase completion
- **Compaction cadence**: Not needed (small context budget)
- **Sub-agents**: None (direct implementation)

## Deployment Considerations

### Platform Dependencies

**Local-only** (no staging/production deployment):
- None - Pure algorithm implementation, no infrastructure changes

### Environment Variables

**New Required Variables**:
- None

**Changed Variables**:
- None

**Schema Update Required**: No

### Breaking Changes

**API Contract Changes**:
- No - New service, existing services unchanged

**Database Schema Changes**:
- No - In-memory zone storage, optional JSONL logging for analysis

**Auth Flow Modifications**:
- No

**Client Compatibility**:
- N/A - Backend-only feature

### Migration Requirements

**Database Migrations**:
- Not required - Zones calculated on-demand from market data

**Data Backfill**:
- Not required

**RLS Policy Changes**:
- No

**Reversibility**:
- Fully reversible - Pure additive feature, no state changes

### Rollback Considerations

**Standard Rollback**:
- Yes - Remove zone service files, revert imports

**Special Rollback Needs**:
- None

**Deployment Metadata**:
- Local-only feature, no deployment tracking needed

---

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [x] Requirements testable, no [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (§Data_Integrity, §Safety_First, §Audit_Everything, §Risk_Management)
- [x] No implementation details (tech stack, APIs, code)

### Conditional: Success Metrics (Skip if no user tracking)
- [x] Success metrics defined with measurable targets (zone hit rate >70%, breakout success >60%)
- [ ] Hypothesis stated (N/A - new feature, not improving existing flow)

### Conditional: UI Features (Skip if backend-only)
- [x] Skipped - Backend-only feature, no UI components

### Conditional: Deployment Impact (Skip if no infrastructure changes)
- [x] Skipped - Local-only feature, no deployment impact
