# Feature: Bull flag profit target integration with resistance zones

## Overview
Integration of ZoneDetector service with BullFlagDetector to dynamically adjust profit targets based on nearby resistance zones. This feature addresses the problem of fixed 2:1 R:R targets failing at known resistance levels by adjusting targets to 90% of the nearest resistance zone when it's closer than the calculated 2:1 target.

## Research Findings

### Finding 1: Existing ZoneDetector Service (US1-US3 Shipped)
**Source**: specs/023-support-resistance-mapping/spec.md, src/trading_bot/support_resistance/zone_detector.py

**Key Details**:
- ZoneDetector.detect_zones() identifies support/resistance zones from historical OHLCV
- ProximityChecker.check_proximity() alerts when price within 2% of zone
- Zone model includes: price_level, strength_score, zone_type, touches
- Service already production-ready with 97.5% test coverage

**Decision**: Reuse existing ZoneDetector, no modifications needed. Add new method find_nearest_resistance() for bull flag integration.

**Implication**: Integration effort reduced - focus on BullFlagDetector changes only

---

### Finding 2: Existing BullFlagDetector Architecture
**Source**: src/trading_bot/momentum/bull_flag_detector.py, specs/003-entry-logic-bull-flag/spec.md

**Key Details**:
- BullFlagDetector uses constructor injection for dependencies (MarketDataService, MomentumLogger)
- Current target calculation: 2:1 R:R (entry + 2 * risk_amount)
- Returns MomentumSignal with details dict containing price_target
- Service uses async/await for market data fetching

**Decision**: Add ZoneDetector as optional constructor parameter, inject during initialization

**Implication**: Backward compatible - existing code without ZoneDetector continues to work

---

### Finding 3: Constitution Requirements
**Source**: .spec-flow/memory/constitution.md

**Relevant Sections**:
- §Risk_Management: "Validate all inputs" - Must validate zone prices before adjustment
- §Audit_Everything: "Every trade decision must be logged with reasoning" - JSONL logging required
- §Code_Quality: "Test coverage ≥90%" - Integration tests required
- §Safety_First: "Fail safe, not fail open" - Graceful degradation if zone detection fails

**Decision**: Implement graceful fallback (use 2:1 if zone detection unavailable), comprehensive logging, 90%+ test coverage

**Implication**: Non-negotiable quality gates for production deployment

---

### Finding 4: Performance Constraints
**Source**: GitHub Issue #31, NFR requirements

**Key Details**:
- Target calculation must complete in <50ms P95
- Zone detection adds overhead to bull flag processing
- Original BullFlagDetector already queries market data (100 days)

**Decision**: Set 50ms P95 target for zone detection query, cache zones during bull flag scan batch

**Implication**: Performance testing required, may need zone result caching

---

## System Components Analysis

**Reusable (existing services)**:
- ZoneDetector (src/trading_bot/support_resistance/zone_detector.py)
- ProximityChecker (src/trading_bot/support_resistance/proximity_checker.py)
- BullFlagDetector (src/trading_bot/momentum/bull_flag_detector.py)
- MomentumLogger (src/trading_bot/momentum/logging/momentum_logger.py)

**New Components Needed**:
- TargetCalculation data model (new model in bull_flag.py or models.py)
- ZoneDetector.find_nearest_resistance() method (new method in existing service)

**Rationale**: Minimal new code required - integration pattern follows existing dependency injection in BullFlagDetector

---

## Feature Classification
- UI screens: false
- Improvement: true (improves existing bull flag entry logic)
- Measurable: true (win rate, target hit rate)
- Deployment impact: false (code-only change, no infrastructure)

---

## Key Decisions

1. **Integration Pattern**: Constructor injection of ZoneDetector (optional dependency)
   - Rationale: Consistent with existing BullFlagDetector architecture, enables testing, graceful degradation

2. **Target Adjustment Threshold**: 90% of resistance zone price
   - Rationale: Provides buffer below resistance to increase hit probability (from GitHub issue)
   - Note: Backtest will validate 85%, 90%, 95% to optimize threshold

3. **Search Range**: 5% above entry price
   - Rationale: Balances relevance (nearby zones) with performance (limit search scope)
   - Note: Zones beyond 5% unlikely to affect 2:1 target (3% typical gain)

4. **Fallback Strategy**: Use standard 2:1 R:R if zone detection unavailable/fails
   - Rationale: §Safety_First - trading continues even if zone service down
   - Implementation: Try-except with logged fallback reason

5. **Metadata Preservation**: Return TargetCalculation object with both adjusted and original targets
   - Rationale: Enables backtesting comparison, satisfies §Audit_Everything
   - Format: JSONL structured logs for query analysis

6. **Backward Compatibility**: ZoneDetector is optional constructor parameter (default None)
   - Rationale: Existing code without zone integration continues to work unchanged
   - Migration: Gradual rollout, inject ZoneDetector when ready

---

## Assumptions

1. Resistance zones are more reliable than fixed 2:1 calculations for profit targets
   - Validation: Backtest will confirm >5% win rate improvement

2. 90% of zone price provides sufficient buffer to avoid rejection
   - Validation: Backtest will test 85%, 90%, 95% thresholds

3. Zone detection completes within <50ms P95
   - Validation: Performance testing with historical data queries

4. Bull flag traders prefer higher win rates over maximum R:R
   - Assumption: Taking profit before resistance better than holding for 2:1 and getting rejected

5. ZoneDetector service is stable and production-ready
   - Evidence: 023-support-resistance-mapping shipped with 97.5% coverage

---

## Checkpoints
- Phase 0 (Specification): 2025-10-21

## Last Updated
2025-10-21T00:00:00Z
