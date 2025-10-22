# Feature Specification: Zone Breakout Detection with Volume Confirmation

**Branch**: `feature/025-zone-breakout-detection`
**Created**: 2025-10-21
**Status**: Draft
**Parent Feature**: specs/023-support-resistance-mapping

## User Scenarios

### Primary User Story
As a trader using the bot, I want the system to automatically detect when price breaks through resistance zones with strong volume confirmation so that I can identify when old resistance has become new support and adjust my trading strategy accordingly without manually monitoring every zone flip.

### Acceptance Scenarios
1. **Given** a resistance zone at $155.00 and price closes at $156.60 (+1.03%) with volume 1.4x average, **When** breakout detection runs, **Then** the zone classification flips to support, the breakout event is logged, and zone metadata is updated
2. **Given** a resistance zone at $200.00 and price closes at $201.00 (+0.5%) with volume 1.5x average, **When** breakout detection runs, **Then** no zone flip occurs because the price move is <1% threshold
3. **Given** a resistance zone at $180.00 and price closes at $182.00 (+1.11%) with volume 0.9x average, **When** breakout detection runs, **Then** no zone flip occurs because volume confirmation is missing (<1.3x threshold)
4. **Given** multiple breakout events on the same zone, **When** querying zone history, **Then** all breakout events are preserved with timestamps, prices, and volume ratios in chronological order

### Edge Cases
- What happens when price whipsaws (breaks above zone then immediately returns below within 5 bars)?
- How does the system handle support-to-resistance flips (price breaking down through support)?
- What happens when volume data is missing or unreliable?
- How does the system differentiate between intraday spikes and confirmed breakouts?

## User Stories (Prioritized)

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As a trader, I want to detect when price closes above a resistance zone by >1% with volume >1.3x average so that I can identify confirmed breakouts with institutional participation
  - **Acceptance**:
    - Monitor current price against all identified resistance zones
    - Calculate close-to-close price change percentage from zone level
    - Fetch current volume and calculate ratio vs 20-bar average volume
    - Trigger breakout if: (close > zone_price * 1.01) AND (volume > avg_volume * 1.3)
    - Return breakout signal with: zone_id, breakout_price, volume_ratio, timestamp
  - **Independent test**: Given resistance at $155.00, close at $156.60 (+1.03%), volume 1.4x avg → breakout detected
  - **Effort**: M (6-8 hours)

- **US2** [P1]: As a trader, I want the zone classification to flip from resistance to support upon confirmed breakout so that my subsequent entries use the correct zone type for risk management
  - **Acceptance**:
    - On breakout detection, create new Zone instance with zone_type flipped (RESISTANCE → SUPPORT)
    - Preserve all existing zone metadata (touch_count, dates, volumes)
    - Update zone strength_score based on breakout confirmation (bonus +2 for volume-confirmed breakout)
    - Return flipped zone to replace original in active zones list
  - **Independent test**: Verify resistance zone at $155 flips to support with strength +2 after breakout
  - **Effort**: S (3-4 hours)

- **US3** [P1]: As a trader, I want all breakout events logged with full context (timestamp, price, volume ratio, zone flip) so that I can backtest breakout patterns and validate the 60% success rate target
  - **Acceptance**:
    - Create BreakoutEvent dataclass with fields: event_id, zone_id, timestamp, breakout_price, close_price, volume_ratio, old_zone_type, new_zone_type
    - Extend ZoneLogger with log_breakout_event() method
    - Write to logs/zones/breakouts-YYYY-MM-DD.jsonl (daily rotation)
    - Include session context: bot_version, config_hash for reproducibility
  - **Independent test**: Trigger breakout, verify JSONL log contains all required fields with UTC timestamp
  - **Effort**: S (2-3 hours)

**Priority 2 (Enhancement)**

- **US4** [P2]: As a trader, I want breakout history maintained for each zone so that I can see how many times a zone has been broken and re-established
  - **Acceptance**:
    - Add breakout_events: list[BreakoutEvent] field to Zone dataclass
    - Append BreakoutEvent to zone.breakout_events list on each flip
    - Expose zone.breakout_count property (len(breakout_events))
    - Sort breakout_events chronologically (oldest first)
  - **Depends on**: US1, US2, US3
  - **Effort**: S (2-3 hours)

- **US5** [P2]: As a trader, I want to validate breakout sustainability by checking for whipsaws (price returning below zone within 5 bars) so that I can filter false breakouts
  - **Acceptance**:
    - After breakout detection, monitor price for next 5 bars (5 hours for daily, 5x4h for 4-hour zones)
    - If price closes below original zone level within 5 bars, mark breakout as "whipsaw" (failed)
    - Update BreakoutEvent.status field: "confirmed", "whipsaw", or "pending" (within 5-bar window)
    - Log whipsaw events separately for analysis
  - **Depends on**: US1, US3
  - **Effort**: M (5-7 hours)

**Priority 3 (Nice-to-have)**

- **US6** [P3]: As a trader, I want support-to-resistance breakdowns detected (price breaking down through support) using the same volume confirmation logic
  - **Acceptance**:
    - Detect when price closes below support zone by >1% with volume >1.3x average
    - Flip zone: SUPPORT → RESISTANCE
    - Log breakdown event (same structure as breakout)
    - Maintain symmetry with breakout logic (reuse same validation, logging, flipping code)
  - **Depends on**: US1, US2, US3
  - **Effort**: S (3-4 hours - refactor breakout code to handle bidirectional flips)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (breakout detection, zone flipping, event logging), validate with historical data against 60% success rate target, then add US4-US6 based on whipsaw frequency and trader feedback.

## Hypothesis

**Problem**: Traders manually monitor resistance zones for breakouts, leading to missed flip opportunities and outdated zone classifications in the bot's risk management logic. Without automated detection, entries above old resistance treat the level as resistance rather than new support, causing premature exits and poor R:R ratios.

- **Evidence**: US5 from parent spec (specs/023-support-resistance-mapping/spec.md) identified this gap: "Detect when price breaks through a resistance zone with volume confirmation... flip zone classification"
- **Impact**: All traders using zone-based entries (100% of bull flag entries per specs/003-entry-logic-bull-flag/)

**Solution**: Real-time breakout detection with volume confirmation (>1% move + >1.3x volume) automatically flips zone classification from resistance to support, maintaining accurate zone types for entry/exit logic.

- **Change**: Add ZoneDetector.detect_breakout() method to monitor price vs zones, flip on confirmation
- **Mechanism**: Volume filter (1.3x average) ensures institutional participation, reducing false breakouts. 1% threshold filters intraday noise.

**Prediction**: Automated zone flipping will improve R:R ratio by 15-20% on entries above flipped zones by treating old resistance as new support (wider stop placement allowable).

- **Primary metric**: Breakout success rate >60% (no return below zone within 5 bars) - per US5 acceptance criteria from parent spec
- **Expected improvement**: 15-20% better R:R on zone-based entries (from treating flipped zones correctly)
- **Confidence**: High - Volume confirmation is standard institutional signal, 1% threshold validated by parent spec's 1.5% zone tolerance

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Task Success** | Accurate breakout detection | Breakouts sustain without reversal | Breakout success rate (no return below zone within 5 bars) | >60% successful breakouts | Whipsaw rate <40% |
| **Task Success** | Reliable zone flipping | Flipped zones correctly classify price action | Zone flip accuracy (flipped zones match manual classification) | >85% accuracy on flip decisions | False flip rate <15% |
| **Engagement** | Breakout integration with trading | Trades using flipped zones | % of entries referencing flipped zones | >20% of zone-based entries use flipped zones | Breakout signals don't degrade overall win rate |
| **Retention** | Flipped zones remain valid | Zones stay flipped without reverting | Flipped zone lifespan (days until re-flip) | Average >21 days active | <10% re-flip within 7 days |

**Measurement Plan**:
- **Breakout success rate**: Query logs/zones/breakouts-*.jsonl, filter by status="confirmed", calculate percentage
  ```bash
  grep '"status":"confirmed"' logs/zones/breakouts-*.jsonl | wc -l
  ```
- **Whipsaw rate**: Inverse of success rate
  ```bash
  grep '"status":"whipsaw"' logs/zones/breakouts-*.jsonl | wc -l
  ```
- **Zone flip accuracy**: Manual review of 20 random breakouts vs manual chart analysis
- **Entry integration**: Query trade_records, count entries with zone_context field containing "flipped_zone"

## Context Strategy & Signal Design

- **System prompt altitude**: Mid-level - Focus on breakout detection algorithm (volume comparison, price threshold, zone flipping mechanics)
- **Tool surface**: MarketDataService (real-time quotes, historical volume), ZoneDetector (zone lookup), ZoneLogger (breakout events)
- **Examples in scope**:
  1. Resistance breakout with volume confirmation (US1 acceptance criteria)
  2. No breakout on insufficient price move (<1%) - rejection case
  3. No breakout on low volume (<1.3x) - rejection case
- **Context budget**: 50k tokens (planning phase) - minimal spec, focus on algorithm details
- **Retrieval strategy**: JIT - Fetch zones on-demand, no persistent cache needed
- **Memory artifacts**: NOTES.md (breakout events), TODO.md (US1-US6 task breakdown)
- **Compaction cadence**: Not needed (simple extension, no large context)
- **Sub-agents**: None (straightforward algorithm implementation)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST detect when price closes above resistance zone by >1.0% (close_price > zone_price * 1.01)
- **FR-002**: System MUST confirm breakout with volume >1.3x of 20-bar average volume
- **FR-003**: System MUST flip zone classification from RESISTANCE to SUPPORT on confirmed breakout
- **FR-004**: System MUST create new Zone instance preserving all metadata (touch_count, dates, volumes) when flipping
- **FR-005**: System MUST update zone strength_score by adding +2 bonus for volume-confirmed breakout
- **FR-006**: System MUST log all breakout events with: event_id, zone_id, timestamp (UTC), breakout_price, close_price, volume_ratio, old_zone_type, new_zone_type
- **FR-007**: System MUST write breakout events to logs/zones/breakouts-YYYY-MM-DD.jsonl (daily rotation)
- **FR-008**: System MUST maintain chronological breakout history for each zone (breakout_events list)
- **FR-009**: System MUST gracefully handle missing volume data (skip volume confirmation check, log warning, proceed with price-only detection)
- **FR-010**: System MUST validate all price calculations using Decimal precision (no float arithmetic)

### Non-Functional

- **NFR-001**: Performance: Breakout detection MUST complete in <200ms for single zone check
- **NFR-002**: Performance: Bulk zone checks (all zones for symbol) MUST complete in <1 second
- **NFR-003**: Data Integrity: All timestamps MUST use UTC timezone with ISO 8601 format
- **NFR-004**: Error Handling: System MUST gracefully degrade on missing data (log warning, skip check, continue bot operation)
- **NFR-005**: Logging: All breakout events MUST be logged to structured JSONL format for backtesting
- **NFR-006**: Constitution Compliance:
  - §Data_Integrity: UTC timestamps, Decimal precision, data validation
  - §Safety_First: Fail-safe on errors (no crashes)
  - §Audit_Everything: Structured logs for all breakout events
  - §Testing_Requirements: 90% coverage, unit + integration tests

### Key Entities

- **BreakoutEvent**: Represents a single zone breakout occurrence
  - Attributes: event_id (str), zone_id (str), timestamp (datetime), breakout_price (Decimal), close_price (Decimal), volume (Decimal), volume_ratio (Decimal), old_zone_type (ZoneType), new_zone_type (ZoneType), status (Enum: PENDING/CONFIRMED/WHIPSAW)
  - Relationships: Belongs to a Zone

- **Zone** (extended): Add breakout tracking to existing Zone dataclass
  - New attributes: breakout_events (list[BreakoutEvent]), is_flipped (bool), flip_date (datetime | None)
  - Relationships: Has many BreakoutEvents

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [x] Requirements testable, no [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (§Data_Integrity, §Safety_First, §Audit_Everything, §Testing_Requirements)
- [x] No implementation details (tech stack, APIs, code)

### Conditional: Success Metrics
- [x] HEART metrics defined with Claude Code-measurable sources (JSONL logs, grep queries)
- [x] Hypothesis stated (Problem → Solution → Prediction with magnitude: 15-20% R:R improvement, 60% success rate)

### Conditional: UI Features (Skip - backend-only)
- [ ] N/A - No UI screens

### Conditional: Deployment Impact (Skip - no infrastructure changes)
- [ ] N/A - Pure logic extension, no deployment changes
