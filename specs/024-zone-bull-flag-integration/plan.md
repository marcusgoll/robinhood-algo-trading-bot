# Implementation Plan: Bull Flag Profit Target Integration with Resistance Zones

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11+ with Decimal arithmetic for price precision
- Components to reuse: 7 (BullFlagDetector, ProximityChecker, ZoneDetector, Zone model, MomentumLogger, BullFlagPattern pattern, Decimal)
- New components needed: 3 (TargetCalculation dataclass, _adjust_target_for_zones method, integration tests)
- Architecture pattern: Constructor dependency injection (optional ZoneDetector)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+
- Dependency Injection: Optional constructor parameter (existing pattern)
- Price Precision: `decimal.Decimal` (financial calculations)
- Data Models: Immutable dataclasses with `__post_init__` validation
- Logging: JSONL structured logging via MomentumLogger
- Testing: pytest with 90%+ coverage requirement

**Patterns**:
- **Dependency Injection**: Optional `zone_detector` parameter in `BullFlagDetector.__init__` enables graceful degradation
  - Rationale: Matches existing `momentum_logger: MomentumLogger | None = None` pattern
  - Benefit: Easy testing (mock injection) + production flexibility (zones optional)

- **Immutable Data Models**: `TargetCalculation` dataclass with `frozen=True`
  - Rationale: Follows `BullFlagPattern` and `MomentumSignal` patterns in codebase
  - Benefit: Audit trail integrity (cannot mutate after creation)

- **Decimal Arithmetic**: Use `Decimal` for all price/percentage calculations
  - Rationale: Zone models use Decimal; financial precision required (constitution §Data_Integrity)
  - Benefit: Avoid floating-point precision errors in profit target calculations

- **Separation of Concerns**: `ProximityChecker.find_nearest_resistance()` for zone lookup
  - Rationale: Reuse existing, tested method instead of duplicating logic
  - Benefit: Single responsibility (BullFlagDetector focuses on pattern detection, not zone queries)

**Dependencies** (new packages required):
- None (all dependencies already in project: pandas, numpy, decimal stdlib)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── momentum/
│   ├── bull_flag_detector.py         # MODIFIED: Add zone_detector param, _adjust_target_for_zones()
│   ├── schemas/
│   │   └── momentum_signal.py        # MODIFIED: Add TargetCalculation dataclass
│   └── logging/
│       └── momentum_logger.py        # REUSED: Log target calculations
└── support_resistance/
    ├── zone_detector.py              # REUSED: Detect zones (injected dependency)
    ├── proximity_checker.py          # REUSED: find_nearest_resistance()
    └── models.py                     # REUSED: Zone dataclass

tests/
├── unit/
│   ├── momentum/
│   │   └── schemas/
│   │       └── test_target_calculation.py  # NEW: TargetCalculation validation tests
│   └── services/
│       └── momentum/
│           └── test_bull_flag_target_adjustment.py  # NEW: Zone integration logic tests
└── integration/
    └── momentum/
        └── test_bull_flag_zone_integration.py  # NEW: End-to-end integration tests
```

**Module Organization**:
- `momentum/schemas/momentum_signal.py`: Add TargetCalculation dataclass (immutable, validated)
- `momentum/bull_flag_detector.py`: Modify `__init__` (add zone_detector), `_calculate_targets` (zone adjustment), add `_adjust_target_for_zones` helper
- `tests/unit/momentum/schemas/`: Unit tests for TargetCalculation validation
- `tests/unit/services/momentum/`: Unit tests for zone integration logic (mocked dependencies)
- `tests/integration/momentum/`: Integration tests with real ZoneDetector and ProximityChecker

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 1 (TargetCalculation)
- Relationships: TargetCalculation references Zone (via resistance_zone_price/strength)
- Migrations required: No (in-memory only)

**Key Fields**:
- `adjusted_target`: Decimal - Final target (zone-adjusted or original)
- `original_2r_target`: Decimal - Baseline 2:1 R:R calculation
- `adjustment_reason`: str - Why adjusted ("resistance_zone_closer" | "no_zone_within_range" | "zone_detector_unavailable" | "zone_detection_error" | "zone_detection_timeout")
- `resistance_zone_price`: Decimal | None - Nearest resistance zone price
- `resistance_zone_strength`: int | None - Zone strength score

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Zone detection query completes in <50ms P95
- NFR-001: Total target calculation (including zone check) <100ms P95
- NFR-003: JSONL logging <5ms P95

**Measurement Strategy**:
- Zone detection: Timed in `_adjust_target_for_zones()`, logged if >50ms
- Total calculation: Measure `_calculate_targets()` execution time
- Logging: Measure `MomentumLogger.log_signal()` call

**Optimization Considerations**:
- Zone detection caching: Not implemented (zones change daily, cache invalidation complex)
- Lazy zone loading: Already implemented (only query when needed)
- Search range limit: 5% above entry (limits zone query scope)

---

## [SECURITY]

**Authentication Strategy**:
- Not applicable (internal service integration, no external API exposure)

**Authorization Model**:
- Not applicable (backend-only feature)

**Input Validation**:
- `symbol`: Validated in `BullFlagDetector.scan()` via `validate_symbols()`
- `entry_price`: Validated in TargetCalculation `__post_init__` (must be > 0)
- `zone_detector`: Type-checked (ZoneDetector | None)

**Data Protection**:
- No PII involved (only stock symbols and prices)
- Logging: JSONL format (structured, parseable)

---

## [EXISTING INFRASTRUCTURE - REUSE] (7 components)

**Services/Modules**:
- `src/trading_bot/momentum/bull_flag_detector.py`: Core pattern detection (scan, _detect_pattern, _calculate_targets)
  - Reuse: Existing bull flag detection logic, add zone integration
  - Lines 31-509: Complete BullFlagDetector implementation

- `src/trading_bot/support_resistance/proximity_checker.py:171-203`: find_nearest_resistance() method
  - Reuse: Zone lookup logic (finds resistance above current price)
  - Returns: `Zone | None` for graceful handling

- `src/trading_bot/support_resistance/zone_detector.py`: Zone detection service
  - Reuse: detect_zones() method (injected dependency)
  - Lines 32-537: Complete ZoneDetector implementation

- `src/trading_bot/support_resistance/models.py:36-123`: Zone dataclass
  - Reuse: price_level, zone_type, strength_score fields
  - Validation: Built-in `__post_init__` ensures data integrity

**Logging**:
- `src/trading_bot/momentum/logging/momentum_logger.py`: MomentumLogger.log_signal()
  - Reuse: Structured JSONL logging for target calculations
  - Pattern: Already logs bull flag signals at bull_flag_detector.py:158-165

**Data Model Patterns**:
- `src/trading_bot/momentum/schemas/momentum_signal.py:148-206`: BullFlagPattern dataclass
  - Reuse: Immutable dataclass pattern with comprehensive `__post_init__` validation
  - Template: Follow this pattern for TargetCalculation

**Utilities**:
- `decimal.Decimal`: Python standard library for price precision
  - Reuse: Already used in Zone model (models.py:18, 59)
  - Conversion: BullFlagDetector currently uses float, needs Decimal conversion

---

## [NEW INFRASTRUCTURE - CREATE] (3 components)

**Data Models**:
- `src/trading_bot/momentum/schemas/momentum_signal.py`: TargetCalculation dataclass
  - Fields: adjusted_target, original_2r_target, adjustment_reason, resistance_zone_price, resistance_zone_strength
  - Validation: Immutable, frozen=True, comprehensive `__post_init__` validation
  - Pattern: Follow BullFlagPattern (lines 148-206) for consistency

**Service Methods**:
- `src/trading_bot/momentum/bull_flag_detector.py`: _adjust_target_for_zones(symbol, entry_price, original_target)
  - Purpose: Private helper method to query zones and adjust target
  - Logic:
    1. Return fallback if zone_detector is None
    2. Detect zones via zone_detector.detect_zones(symbol, days=60)
    3. Find nearest resistance via ProximityChecker.find_nearest_resistance(entry_price, zones)
    4. Compare zone price to original target (within 5% search range)
    5. Adjust to 90% of zone price if zone closer
    6. Return TargetCalculation with metadata
  - Error Handling: Try/except with timeout check, fallback on error

**Tests**:
- `tests/unit/momentum/schemas/test_target_calculation.py`: TargetCalculation validation tests
  - Test positive/negative validation cases
  - Test immutability (frozen dataclass)
  - Test serialization (to_dict for logging)

- `tests/unit/services/momentum/test_bull_flag_target_adjustment.py`: Zone integration logic tests
  - Mock ZoneDetector and ProximityChecker
  - Test cases: zone closer, no zone, fallback scenarios
  - Test performance (zone detection <50ms)

- `tests/integration/momentum/test_bull_flag_zone_integration.py`: End-to-end integration tests
  - Real ZoneDetector and ProximityChecker (not mocked)
  - Test with actual OHLCV data
  - Verify JSONL logging format

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Not applicable (backend-only, no infrastructure changes)
- Env vars: None required
- Breaking changes: No (internal service integration only)
- Migration: No (no database changes)

**Build Commands**:
- No changes to build process

**Environment Variables**:
- No new environment variables required
- Existing: ZoneDetectionConfig uses env vars (tolerance_pct, touch_threshold, proximity_threshold_pct)

**Database Migrations**:
- No migrations required (in-memory calculations only)

**Smoke Tests**:
- Add test to verify zone integration doesn't break bull flag scanning
- Test: `test_bull_flag_scan_with_zone_integration()` in integration suite
- Expected: Bull flag signals returned with zone-adjusted targets logged

**Platform Coupling**:
- None: Pure Python service integration (no platform-specific dependencies)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- Bull flag detection works with or without ZoneDetector (graceful degradation)
- Target calculations preserve audit trail (JSONL logging)
- Performance: Zone detection <50ms P95, total calculation <100ms P95
- Backward compatibility: Existing BullFlagDetector usage unaffected (zone_detector optional)

**Staging Smoke Tests** (Given/When/Then):
```gherkin
Given BullFlagDetector initialized with ZoneDetector
When scanning symbols ["AAPL", "TSLA", "GOOGL"]
Then bull flag signals include zone-adjusted targets
  And JSONL logs contain "target_calculated" events
  And zone detection completes in <50ms P95
  And no exceptions raised

Given BullFlagDetector initialized WITHOUT ZoneDetector
When scanning symbols ["AAPL", "TSLA", "GOOGL"]
Then bull flag signals use standard 2:1 targets
  And adjustment_reason = "zone_detector_unavailable"
  And no exceptions raised
```

**Rollback Plan**:
- Standard rollback: Revert commit, restart services
- Feature flag: Set zone_detector=None in production initialization
- Special considerations: None (no database changes, no external API dependencies)

**Artifact Strategy** (build-once-promote-many):
- Not applicable: Python source code (no build artifacts)
- Testing: Run full test suite in CI (pytest + mypy + ruff)
- Deployment: Standard git deploy (no special build process)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Initial setup: No special setup required (no new dependencies, env vars, migrations)
- Manual testing: 5 test scenarios (zone-adjusted, fallback, logging, performance, backtesting)
- Validation: pytest + mypy + ruff, 90%+ coverage target

**Key Test Scenarios**:
1. Zone-adjusted target (resistance closer than 2:1)
2. Graceful degradation (no zone detector)
3. JSONL logging verification
4. Backtesting comparison (Strategy A vs B)
5. Performance validation (<50ms zone detection, <100ms total)

---

## [IMPLEMENTATION CHECKLIST]

**Phase 1: Data Model (1-2 hours)**
- [ ] Add TargetCalculation dataclass to momentum_signal.py
- [ ] Write unit tests for TargetCalculation validation
- [ ] Verify immutability and serialization

**Phase 2: Zone Integration Logic (2-3 hours)**
- [ ] Modify BullFlagDetector.__init__ to accept zone_detector parameter
- [ ] Implement _adjust_target_for_zones() helper method
- [ ] Modify _calculate_targets() to return TargetCalculation
- [ ] Add try/except error handling with timeout check
- [ ] Write unit tests for zone integration logic (mocked)

**Phase 3: Logging (1 hour)**
- [ ] Add target_calculated event logging in _calculate_targets()
- [ ] Verify JSONL format includes all required fields
- [ ] Test logging with grep/jq queries

**Phase 4: Integration Testing (1-2 hours)**
- [ ] Write end-to-end integration tests (real ZoneDetector)
- [ ] Verify backward compatibility (existing tests pass)
- [ ] Test graceful degradation (zone_detector=None)

**Phase 5: Performance Validation (1 hour)**
- [ ] Measure zone detection time (<50ms P95)
- [ ] Measure total calculation time (<100ms P95)
- [ ] Add performance tests to test suite

**Phase 6: Documentation (1 hour)**
- [ ] Update BullFlagDetector docstring (zone_detector parameter)
- [ ] Document TargetCalculation fields
- [ ] Add usage examples to quickstart.md

**Total Estimated Effort**: 7-10 hours (M-sized task)
