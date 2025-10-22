# Feature: "Zone breakout detection with volume confirmation"

## Overview

This feature extends the existing support-resistance-mapping (specs/023) by implementing the breakout detection logic described in US5 (Priority 2). The feature will monitor price action against identified zones and detect when resistance is broken to become support.

## Research Findings

### Finding 1: Parent Feature Already Implemented
**Source**: specs/023-support-resistance-mapping/spec.md, src/trading_bot/support_resistance/zone_detector.py

The parent feature (support-resistance-mapping) has been implemented with:
- ZoneDetector class: Identifies support/resistance zones from OHLCV data
- Zone model: Immutable dataclass with price_level, zone_type, strength_score, touch_count, timestamps
- ZoneTouch model: Records individual price interactions with zones (BOUNCE, REJECTION, BREAKOUT)
- TouchType enum: Already includes BREAKOUT as a valid touch type
- ZoneLogger: Structured JSONL logging for zone events

**Decision**: This feature will extend the existing ZoneDetector with a new breakout detection method, reusing all existing models and infrastructure.

### Finding 2: Breakout Detection Specified But Not Implemented
**Source**: specs/023-support-resistance-mapping/spec.md (US5)

US5 specification requirements:
- Detect when price closes above resistance zone by >1% with volume >1.3x average
- Flip zone classification: resistance → support
- Log breakout event with timestamp, price, volume ratio, zone flip
- Maintain breakout history for each zone

**Decision**: Implement exactly per US5 spec - no deviation needed.

### Finding 3: Market Data Service Integration Points
**Source**: src/trading_bot/market_data/market_data_service.py

MarketDataService provides:
- Historical OHLCV data fetching
- Real-time quote retrieval
- Data validation pipeline

**Decision**: Use existing MarketDataService for real-time price and volume data.

### Finding 4: Existing Logging Infrastructure
**Source**: src/trading_bot/support_resistance/zone_logger.py

ZoneLogger already provides:
- Structured JSONL logging
- Daily rotation (logs/zones/YYYY-MM-DD.jsonl)
- log_zone_detection() method

**Decision**: Extend ZoneLogger with new log_breakout_event() method for breakout-specific logging.

### Finding 5: Constitution Compliance Requirements
**Source**: .spec-flow/memory/constitution.md

Required compliance:
- §Safety_First: No auto-trading, manual review required
- §Data_Integrity: UTC timestamps, Decimal precision, data validation
- §Audit_Everything: Structured logs for all events
- §Testing_Requirements: 90% coverage, unit + integration tests

**Decision**: Follow same patterns as parent feature (zone-detector has comprehensive test coverage).

## Feature Classification

- UI screens: false (Backend API feature)
- Improvement: true (Extends existing zone detection with breakout tracking)
- Measurable: true (Breakout success rate metric from spec)
- Deployment impact: false (No infrastructure changes, pure logic extension)

## System Components Analysis

**Reusable (from existing codebase)**:
- ZoneDetector (extend with breakout method)
- Zone dataclass (add breakout metadata)
- ZoneTouch dataclass (TouchType.BREAKOUT already exists)
- ZoneLogger (extend with log_breakout_event)
- MarketDataService (real-time price/volume fetching)

**New Components Needed**:
- BreakoutDetector class or ZoneDetector.detect_breakouts() method
- BreakoutEvent dataclass (track breakout metadata: timestamp, price, volume_ratio, old_type, new_type)
- Zone flipping logic (create new Zone instance with flipped type to preserve immutability)

**Rationale**: Minimize new code by extending existing well-tested infrastructure. Zone flipping will create a new Zone instance with flipped type rather than mutating existing zones (immutability preserved).

## Dependencies

- **COMPLETED**: specs/023-support-resistance-mapping (MVP shipped per roadmap)
- **AVAILABLE**: MarketDataService ✅ (market-data-module shipped)
- **AVAILABLE**: ZoneLogger ✅ (part of zone-detector module)

## Phase Summaries

### Phase 0: Specification (Complete)
- Requirements: 16 documented (10 FR + 6 NFR)
- User stories: 6 prioritized (US1-US3 MVP, US4-US6 enhancements)
- HEART metrics: 4 dimensions with measurement queries
- Parent feature analysis: Complete (specs/023-support-resistance-mapping)

### Phase 1: Planning (Complete)
- Research decisions: 5 documented
- Components to reuse: 8 (ZoneDetector, models, logger, market data, retry, test fixtures)
- New components needed: 4 (BreakoutDetector, BreakoutEvent, BreakoutConfig, tests)
- Architecture pattern: Composition over inheritance (Decision 1)
- Estimated effort: 16-24 hours (MVP US1-US3)

### Phase 2: Tasks (Complete)
- Total tasks: 41
- User story tasks: 8 (US1), 4 (US2), 5 (US3), 2 (US4), 2 (US5), 1 (US6)
- Parallel opportunities: 21 tasks marked [P]
- Setup tasks: 2 (verify structure, verify parent feature)
- Foundational tasks: 4 (models, config, exports)
- Test tasks: 15 (TDD approach with tests-first)
- Polish tasks: 11 (validation, documentation, quality gates)

**Task Breakdown by Phase**:
- Phase 1 (Setup): 2 tasks
- Phase 2 (Foundational): 4 tasks - blocking models and config
- Phase 3 (US1 - Breakout Detection): 8 tasks (4 tests + 4 implementation)
- Phase 4 (US2 - Zone Flipping): 4 tasks (2 tests + 2 implementation)
- Phase 5 (US3 - Event Logging): 5 tasks (2 tests + 3 implementation)
- Phase 6-8 (US4-US6 Optional): 7 tasks (enhancement features)
- Phase 9 (Polish): 11 tasks (validation, quality, documentation)

**MVP Scope** (US1-US3): 23 tasks
**Optional Enhancements** (US4-US6): 7 tasks
**Infrastructure** (Setup + Foundational): 6 tasks
**Quality Gates** (Polish): 11 tasks

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-21 ✅
- Phase 1 (Plan): 2025-10-21 ✅
- Phase 2 (Tasks): 2025-10-21 ✅

## Last Updated
2025-10-21
