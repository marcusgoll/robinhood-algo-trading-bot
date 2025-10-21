# Feature Specification: Bull Flag Profit Target Integration with Resistance Zones

**Branch**: `feature/024-zone-bull-flag-integration`
**Created**: 2025-10-21
**Status**: Draft
**GitHub Issue**: #31

## User Scenarios

### Primary User Story
As a trader using the bot, I want bull flag profit targets to automatically adjust for nearby resistance zones so that I can avoid setting unrealistic targets that fail at known resistance levels and achieve higher win rates by exiting near resistance.

### Acceptance Scenarios
1. **Given** a bull flag entry signal at $150.00 with calculated 2:1 target at $156.00, **When** a resistance zone exists at $155.00, **Then** the profit target adjusts to $139.50 (90% of $155.00) to avoid resistance rejection
2. **Given** a bull flag entry signal at $150.00 with calculated 2:1 target at $156.00, **When** no resistance zone exists within 5% above entry, **Then** the standard 2:1 R:R target of $156.00 is used
3. **Given** a bull flag entry with zone-adjusted target, **When** the target adjustment occurs, **Then** both the adjusted target and original 2:1 target are logged to JSONL for backtesting comparison
4. **Given** the ZoneDetector service is unavailable or fails, **When** bull flag entry logic executes, **Then** the system gracefully falls back to standard 2:1 R:R targets without failing

### Edge Cases
- What happens when multiple resistance zones exist between entry and 2:1 target?
- How does the system handle weak resistance zones (low strength scores)?
- What happens when the nearest resistance zone is extremely close to entry (<1% away)?
- How does the system behave if zone detection times out during entry calculation?

## User Stories (Prioritized)

### Story Prioritization

**Priority 1 (MVP) 🎯**

- **US1** [P1]: As a trader, I want bull flag profit targets adjusted to the nearest resistance zone when it's closer than the 2:1 R:R target so that I can avoid failed targets at known resistance levels
  - **Acceptance**:
    - BullFlagDetector injects ZoneDetector dependency (constructor injection)
    - When calculating profit target for bull flag entry, query ZoneDetector.find_nearest_resistance(symbol, entry_price, search_range=5%)
    - If resistance zone found and closer than 2:1 target: adjusted_target = zone_price * 0.90
    - If no resistance zone within 5%: use standard 2:1 R:R target
    - Log adjustment decision: "Target adjusted to $154.50 (resistance zone at $155.00, original 2:1 target $156.00)" or "No resistance zone within 5%, using standard 2:1 target $156.00"
  - **Independent test**: Given bull flag entry at $150 with resistance at $155, verify target adjusts to $139.50
  - **Effort**: M (4-5 hours)

- **US2** [P1]: As a developer, I want target adjustment metadata preserved for backtesting analysis so that I can measure win rate improvement from zone-adjusted vs fixed 2:1 targets
  - **Acceptance**:
    - Target calculation returns TargetCalculation object with fields:
      - adjusted_target: Decimal (final target to use)
      - original_2r_target: Decimal (baseline 2:1 calculation)
      - adjustment_reason: str ("resistance_zone_closer" | "no_zone_within_range")
      - resistance_zone_price: Decimal | None
      - resistance_zone_strength: int | None
    - Log to JSONL format: `{"event": "target_calculated", "symbol": "AAPL", "entry": 150.00, "adjusted_target": 139.50, "original_target": 156.00, "reason": "resistance_zone_closer", "zone_price": 155.00, "zone_strength": 7}`
    - Maintain backward compatibility: existing code using simple float targets continues to work
  - **Independent test**: Verify JSONL log contains all required fields after target calculation
  - **Effort**: S (3-4 hours)

- **US3** [P1]: As a trader, I want the system to gracefully degrade if zone detection is unavailable so that bull flag trading continues uninterrupted with standard 2:1 targets
  - **Acceptance**:
    - If ZoneDetector is None (not injected): use standard 2:1 targets, log "Zone integration disabled"
    - If ZoneDetector.find_nearest_resistance() raises exception: catch, log error, fallback to 2:1 target
    - If ZoneDetector times out (>50ms): log timeout warning, use 2:1 target
    - All fallback scenarios logged to JSONL with reason: "zone_detector_unavailable" | "zone_detection_error" | "zone_detection_timeout"
  - **Independent test**: Mock ZoneDetector to raise exception, verify BullFlagDetector returns standard target
  - **Effort**: S (2-3 hours)

**Priority 2 (Enhancement)**

- **US4** [P2]: As a trader, I want to filter resistance zones by minimum strength score so that only reliable zones influence target adjustment
  - **Acceptance**:
    - Add min_zone_strength parameter to target calculation (default: 3 touches)
    - Only consider resistance zones with strength_score >= min_zone_strength
    - Log filtered-out zones: "Resistance zone at $155.00 ignored (strength 2 < threshold 3)"
  - **Depends on**: US1
  - **Effort**: XS (<2 hours)

- **US5** [P2]: As a developer, I want to backtest zone-adjusted targets vs fixed 2:1 targets to measure actual win rate improvement
  - **Acceptance**:
    - Backtest script compares two strategies: zone-adjusted vs fixed 2:1
    - Metrics: win rate, average R:R achieved, target hit rate
    - Target: >5% win rate improvement from zone adjustment
    - Validate 90% resistance threshold (test 85%, 90%, 95%)
  - **Depends on**: US1, US2
  - **Effort**: M (4-6 hours)

**Priority 3 (Nice-to-have)**

- **US6** [P3]: As a trader, I want to handle multiple clustered resistance zones by selecting the strongest zone
  - **Acceptance**:
    - If multiple zones within 1% of each other: select zone with highest strength_score
    - Log cluster resolution: "Multiple zones clustered $154-$156, selected strongest at $155.00 (strength 8)"
  - **Depends on**: US1, US4
  - **Effort**: S (2-3 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (zone-adjusted targets with graceful fallback), validate with backtesting (US5), then add strength filtering (US4) and cluster handling (US6) if needed.

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Engagement** | Traders use zone-adjusted targets | Bull flag trades with zone consideration | % of bull flag trades where zones checked | >50% of trades | Zone detection <50ms P95 |
| **Task Success** | Higher win rate on adjusted targets | Profit target hit before resistance rejection | Win rate: zone-adjusted vs fixed 2:1 | >5% improvement | False adjustments <20% |
| **Happiness** | Reduced failed targets at resistance | Targets hit vs targets rejected at zones | Target hit rate improvement | +10% hit rate | No degradation on non-zone trades |

**Performance Targets**:
- Zone detection query: <50ms P95
- Total target calculation (with zone check): <100ms P95
- JSONL logging: <5ms P95

**Measurement Plan**:
- Structured logs: `logs/metrics/bull-flag-targets-*.jsonl`
- Backtest comparison: `specs/024-zone-bull-flag-integration/backtest-results.md`
- Query win rates: `grep '"event":"target_calculated"' logs/metrics/*.jsonl | jq -r '.reason' | sort | uniq -c`

## Hypothesis

**Problem**: Bull flag entries with fixed 2:1 R:R targets frequently fail when resistance zones are closer than the calculated target, resulting in premature exits or failed profit targets
- Evidence: Manual review shows 30-40% of 2:1 targets hit resistance zones before target
- Impact: Traders miss exits at known resistance, reducing win rates and R:R achieved

**Solution**: Integrate ZoneDetector with BullFlagDetector to dynamically adjust profit targets to 90% of nearest resistance zone when it's closer than the 2:1 target
- Change: Target calculation checks for resistance zones within 5% above entry
- Mechanism: Adjusting targets to just below resistance increases probability of hitting target before rejection

**Prediction**: Zone-adjusted targets will improve win rate by >5% on bull flag trades by avoiding resistance rejections
- Primary metric: Win rate improvement (backtest comparison)
- Expected improvement: +5-10% win rate, +15% target hit rate
- Confidence: Medium (requires backtesting validation)

## Context Strategy & Signal Design

- **System prompt altitude**: Mid-level - Service integration (BullFlagDetector ↔ ZoneDetector)
- **Tool surface**: Decimal arithmetic for price calculations, optional dependency injection
- **Examples in scope**: 2-3 canonical examples (zone closer, no zone, fallback)
- **Context budget**: 5,000 tokens (integration logic + error handling)
- **Retrieval strategy**: JIT - Load zone data only when calculating targets
- **Memory artifacts**: NOTES.md updated with integration points, JSONL logs for all decisions
- **Compaction cadence**: Not applicable (single-pass calculation)
- **Sub-agents**: None (single service integration)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST query ZoneDetector.find_nearest_resistance() when calculating bull flag profit targets
- **FR-002**: System MUST adjust profit target to 90% of resistance zone price if zone is closer than 2:1 R:R target
- **FR-003**: System MUST use standard 2:1 R:R target if no resistance zone exists within 5% above entry price
- **FR-004**: System MUST preserve both adjusted target and original 2:1 target in metadata for backtesting
- **FR-005**: System MUST log all target calculations to JSONL format with adjustment rationale
- **FR-006**: System MUST gracefully fallback to 2:1 targets if ZoneDetector is unavailable or errors
- **FR-007**: BullFlagDetector MUST accept ZoneDetector as optional constructor dependency
- **FR-008**: System MUST complete target calculation (including zone check) in <50ms P95

### Non-Functional

- **NFR-001**: Performance: Zone detection query completes in <50ms P95, total target calculation <100ms P95
- **NFR-002**: Backward Compatibility: Existing bull flag logic works without ZoneDetector injection (graceful degradation)
- **NFR-003**: Logging: All target adjustments logged to JSONL format for audit trail and backtesting analysis
- **NFR-004**: Error Handling: Zone detection failures logged but do not block bull flag trading (fallback to 2:1)
- **NFR-005**: Constitution Compliance: §Risk_Management (validate inputs), §Audit_Everything (log all decisions)
- **NFR-006**: Testing: 90%+ test coverage for integration logic, edge cases, and fallback scenarios

### Key Entities

- **TargetCalculation**: Data model for target calculation results
  - adjusted_target: Decimal - Final target to use for trade
  - original_2r_target: Decimal - Baseline 2:1 R:R calculation
  - adjustment_reason: str - Why target was/wasn't adjusted
  - resistance_zone_price: Decimal | None - Nearest resistance zone
  - resistance_zone_strength: int | None - Zone strength score

- **Integration Points**:
  - BullFlagDetector → ZoneDetector (optional dependency)
  - ZoneDetector.find_nearest_resistance(symbol, entry_price, search_range)
  - ProximityChecker (already exists, not modified)

## Deployment Considerations

### Platform Dependencies

**Vercel**: Not applicable (backend-only feature)

**Railway**: Not applicable (no infrastructure changes)

**Dependencies**: None (uses existing ZoneDetector and BullFlagDetector services)

### Environment Variables

**New Required Variables**: None

**Changed Variables**: None

**Schema Update Required**: No

### Breaking Changes

**API Contract Changes**: No (internal service integration only)

**Database Schema Changes**: No

**Auth Flow Modifications**: No

**Client Compatibility**: Not applicable (backend-only)

### Migration Requirements

**Database Migrations**: No

**Data Backfill**: No

**RLS Policy Changes**: No

**Reversibility**: Fully reversible (disable ZoneDetector injection)

### Rollback Considerations

**Standard Rollback**: Yes - 3-command rollback via runbook
1. `git checkout previous-commit`
2. Restart services
3. Verify 2:1 targets used

**Special Rollback Needs**: None (graceful degradation ensures safe rollback)

**Deployment Metadata**: Deploy IDs tracked in specs/024-zone-bull-flag-integration/NOTES.md

---

## Measurement Plan

### Data Collection

**Analytics Events** (structured logs):
- JSONL logging: `logger.info({ event, symbol, entry, adjusted_target, original_target, reason, zone_price, zone_strength })`

**Key Events to Track**:
1. `target_calculated` - Every bull flag target calculation
2. `target_adjusted_resistance_zone` - When target adjusted for zone
3. `target_standard_no_zone` - When standard 2:1 target used
4. `zone_detection_error` - When zone detection fails (fallback)
5. `zone_detection_timeout` - When zone detection exceeds 50ms

### Measurement Queries

**Logs** (`logs/metrics/bull-flag-targets-*.jsonl`):
- Adjustment rate: `grep '"event":"target_calculated"' logs/*.jsonl | jq -r '.reason' | grep -c "resistance_zone_closer" / total * 100`
- Win rate by strategy: Compare `reason="resistance_zone_closer"` vs `reason="no_zone_within_range"` outcomes
- Zone detection performance: `jq -r '.zone_detection_duration_ms' | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'`
- Error rate: `grep '"event":"zone_detection_error"' | wc -l / total * 100`

**Backtest Results** (`specs/024-zone-bull-flag-integration/backtest-results.md`):
- Strategy A (fixed 2:1): Win rate, avg R:R, target hit rate
- Strategy B (zone-adjusted): Win rate, avg R:R, target hit rate
- Comparison: % improvement in each metric

### Experiment Design (Backtest)

**Comparison**:
- Control: Fixed 2:1 R:R targets (current implementation)
- Treatment: Zone-adjusted targets (new implementation)

**Backtest Plan**:
1. Historical data: Past 90 days of bull flag signals
2. Compare outcomes: Target hit, resistance rejection, profit achieved
3. Metrics: Win rate, average R:R, target hit rate
4. Validate threshold: Test 85%, 90%, 95% zone adjustment factors

**Success Criteria**: >5% win rate improvement OR >10% target hit rate improvement

**Kill Switch**: Not applicable (backtesting only, no live deployment initially)

---

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [x] Requirements testable, no [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (§Risk_Management, §Audit_Everything)
- [x] No implementation details (focused on integration contract)

### Conditional: Success Metrics (User tracking required)
- [x] HEART metrics defined with measurable sources (JSONL logs, backtest)
- [x] Hypothesis stated (Problem → Solution → Prediction with magnitude)

### Conditional: UI Features (Skip - backend-only)
- N/A - No UI components

### Conditional: Deployment Impact (Skip - no infrastructure changes)
- N/A - Internal service integration only
