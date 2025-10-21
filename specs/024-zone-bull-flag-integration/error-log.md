# Error Log: Bull Flag Profit Target Integration with Resistance Zones

## Planning Phase (Phase 0-2)
None yet.

## Implementation Phase (Phase 3-4)
[Populated during /tasks and /implement]

## Testing Phase (Phase 5)
[Populated during /debug and /preview]

## Deployment Phase (Phase 6-7)
[Populated during staging validation and production deployment]

---

## Error Template

**Error ID**: ERR-[NNN]
**Phase**: [Planning/Implementation/Testing/Deployment]
**Date**: YYYY-MM-DD HH:MM
**Component**: [api/frontend/database/deployment]
**Severity**: [Critical/High/Medium/Low]

**Description**:
[What happened]

**Root Cause**:
[Why it happened]

**Resolution**:
[How it was fixed]

**Prevention**:
[How to prevent in future]

**Related**:
- Spec: [link to requirement]
- Code: [file:line]
- Commit: [sha]

---

## Known Edge Cases (Preemptive Documentation)

### Edge Case 1: Multiple resistance zones clustered

**Scenario**: Multiple resistance zones within 1% of each other between entry and 2:1 target

**Spec Reference**: Edge case mentioned in spec.md:20-24

**Current Handling**: ProximityChecker.find_nearest_resistance() returns lowest price resistance (closest above entry)

**Potential Issue**: If zones have different strengths, may select weak zone over strong zone

**Mitigation** (Priority 3 - US6):
- Select zone with highest strength_score when multiple zones clustered
- Log cluster resolution decision

**Status**: Deferred to US6 (nice-to-have)

### Edge Case 2: Weak resistance zones (low strength scores)

**Scenario**: Nearest resistance zone has strength_score < 3 (minimal touches)

**Spec Reference**: Edge case mentioned in spec.md:21

**Current Handling**: No strength filtering in MVP (US1-US3)

**Potential Issue**: May adjust targets for unreliable zones

**Mitigation** (Priority 2 - US4):
- Add min_zone_strength parameter (default: 3 touches)
- Filter zones below threshold

**Status**: Deferred to US4 (enhancement)

### Edge Case 3: Resistance zone extremely close to entry (<1%)

**Scenario**: Resistance zone at $150.50 when entry is $150.00 (<1% away)

**Spec Reference**: Edge case mentioned in spec.md:22

**Current Handling**: Adjust target to 90% of $150.50 = $135.45

**Potential Issue**: Adjusted target may be below entry price (invalid trade)

**Mitigation**:
- Add validation in TargetCalculation.__post_init__: adjusted_target must be > entry_price
- If adjusted target < entry, use original 2:1 target instead
- Log reason: "zone_too_close_to_entry"

**Status**: Add to US1 implementation (critical validation)

### Edge Case 4: Zone detection timeout (>50ms)

**Scenario**: Zone detection takes >50ms due to large dataset or slow I/O

**Spec Reference**: US3 acceptance criteria (spec.md:58)

**Current Handling**: Timeout check in _adjust_target_for_zones(), fallback to 2:1 target

**Potential Issue**: Timeout threshold may be too strict for some symbols

**Mitigation**:
- Use time.perf_counter() to measure zone detection duration
- If >50ms: Log warning, fallback to 2:1 target, reason: "zone_detection_timeout"
- Make timeout threshold configurable in ZoneDetectionConfig (future enhancement)

**Status**: Implement in US1, make configurable in future

### Edge Case 5: Zone detector returns empty zones list

**Scenario**: detect_zones() returns [] (no zones found for symbol)

**Spec Reference**: Graceful degradation (NFR-002)

**Current Handling**: find_nearest_resistance() returns None, use original 2:1 target

**Potential Issue**: None (expected behavior)

**Mitigation**: None needed, log reason: "no_zone_within_range"

**Status**: Covered by US1 implementation

---

## Performance Monitoring Plan

**Key Metrics**:
- Zone detection duration (target: <50ms P95)
- Total target calculation duration (target: <100ms P95)
- JSONL logging duration (target: <5ms P95)

**Logging Strategy**:
```python
# In _adjust_target_for_zones()
import time
start = time.perf_counter()
zones = self.zone_detector.detect_zones(symbol, days=60)
duration_ms = (time.perf_counter() - start) * 1000

if duration_ms > 50:
    logger.warning(f"Zone detection for {symbol} took {duration_ms:.2f}ms (>50ms threshold)")
```

**Alert Thresholds**:
- Warning: Zone detection >50ms
- Error: Zone detection >100ms
- Critical: Zone detection >200ms (likely timeout or data issue)
