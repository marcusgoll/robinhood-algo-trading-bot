# Implementation Plan: Zone Breakout Detection with Volume Confirmation

## [RESEARCH DECISIONS]

See: research.md for full research findings (5 decisions documented)

**Summary**:
- Stack: Python 3.11+, extends existing support_resistance module
- Components to reuse: 8 (ZoneDetector, Zone models, ZoneLogger, MarketDataService, @with_retry, test fixtures)
- New components needed: 4 (BreakoutDetector, BreakoutEvent model, BreakoutConfig, unit tests)
- Key Decision: Create new BreakoutDetector class that composes with ZoneDetector (preserves SRP, no breaking changes)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+ (Constitution §Stack requirement)
- Module: Extends src/trading_bot/support_resistance/ (parent feature 023)
- Data Models: Immutable dataclasses with Decimal precision (Constitution §Data_Integrity)
- Testing: pytest with 90% coverage target (Constitution §Testing_Requirements)
- Type Safety: mypy --strict compliance (Constitution §Code_Quality)

**Patterns**:
- **Composition over Inheritance**: BreakoutDetector composes with ZoneDetector, doesn't extend it
  - Rationale: Breakout detection is a separate concern from zone identification (SRP)
  - Source: Research Decision 1, Constitution §Code_Quality (One function, one purpose)

- **Dependency Injection**: Constructor injection for MarketDataService, ZoneLogger
  - Rationale: Testability (mock dependencies), loose coupling
  - Source: Constitution §Architecture (Dependency injection - Testable components)

- **Immutability**: Zone flipping creates new Zone instance, doesn't mutate existing
  - Rationale: Preserves audit trail, prevents race conditions, functional programming principles
  - Source: Research Decision 3, Zone dataclass design pattern

- **Stateless Service**: BreakoutDetector has no mutable state, pure functions only
  - Rationale: Thread-safe, predictable, easier to test and reason about
  - Source: Constitution §Code_Quality (No duplicate logic - DRY), functional design

- **Structured Logging**: JSONL format with daily rotation, thread-safe writes
  - Rationale: Machine-readable, queryable, immutable audit trail
  - Source: Constitution §Audit_Everything, existing ZoneLogger pattern

**Dependencies** (all existing, no new packages required):
- robin_stocks: Market data fetching (already used by MarketDataService)
- pandas: Historical data processing (already used by ZoneDetector)
- numpy: Volume calculations (already available)
- pytest: Testing framework (already configured)
- mypy: Type checking (already configured)
- ruff: Linting (already configured)
- bandit: Security scanning (already configured)

---

## [STRUCTURE]

**Directory Layout** (extends existing support_resistance module):

```
src/trading_bot/support_resistance/
├── __init__.py                    # Add BreakoutDetector, BreakoutEvent to exports
├── zone_detector.py               # EXISTING - no changes
├── models.py                      # EXISTING - no changes
├── zone_logger.py                 # MODIFY - add log_breakout_event() method
├── config.py                      # EXISTING - no changes
├── proximity_checker.py           # EXISTING - no changes
├── breakout_detector.py           # NEW - core breakout detection logic
├── breakout_models.py             # NEW - BreakoutEvent, BreakoutStatus dataclasses
└── breakout_config.py             # NEW - BreakoutConfig with from_env()

tests/unit/support_resistance/
├── test_zone_detector.py          # EXISTING - no changes
├── test_zone_logger.py            # MODIFY - add test_log_breakout_event
├── test_models.py                 # EXISTING - no changes
└── test_breakout_detector.py     # NEW - breakout detector unit tests

logs/zones/
├── YYYY-MM-DD-zones.jsonl         # EXISTING - zone detection logs
└── YYYY-MM-DD-breakouts.jsonl     # NEW - breakout event logs
```

**Module Organization**:
- **breakout_detector.py**: BreakoutDetector service class
  - detect_breakout(): Main detection logic (FR-001, FR-002)
  - flip_zone(): Zone type flipping with strength bonus (FR-003, FR-004, FR-005)
  - _calculate_price_change_pct(): Price movement calculation
  - _calculate_volume_ratio(): Volume confirmation calculation

- **breakout_models.py**: Data models
  - BreakoutEvent dataclass: All breakout metadata (FR-006)
  - BreakoutStatus enum: PENDING, CONFIRMED, WHIPSAW (US5)

- **breakout_config.py**: Configuration
  - BreakoutConfig dataclass: Thresholds and parameters
  - from_env() class method: Environment variable loading

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 2 (BreakoutEvent, Zone extension)
- Relationships: BreakoutEvent belongs to Zone, Zone has many BreakoutEvents
- Migrations required: No (local-only feature, JSONL storage)

**Key Design Choices**:
- BreakoutEvent: Immutable record of each breakout with full context
- Zone extension: Add breakout_events list to track history (US4)
- BreakoutStatus enum: PENDING → CONFIRMED/WHIPSAW state machine (US5)

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Breakout detection MUST complete in <200ms for single zone check
- NFR-002: Bulk zone checks (all zones for symbol) MUST complete in <1 second
- NFR-003: All timestamps MUST use UTC timezone with ISO 8601 format
- NFR-004: System MUST gracefully degrade on missing data (log warning, skip check, continue)
- NFR-005: All breakout events MUST be logged to structured JSONL format

**Performance Strategy**:
- Use Decimal arithmetic (not float) for precise price/volume calculations
- Minimize API calls: Fetch historical data once, calculate average volume in-memory
- Lazy evaluation: Only check breakouts for symbols with active zones
- No caching: Stateless service, no state overhead

**Benchmarking Plan**:
- Unit test: test_detect_breakout_performance() - measure latency for 100 breakout checks
- Target: P95 <50ms, P99 <100ms (well under 200ms NFR-001 target)
- Tools: pytest-benchmark or timeit

---

## [SECURITY]

**Authentication Strategy**:
- No authentication required (internal library, not API)
- Inherits RobinhoodAuth from MarketDataService dependency

**Authorization Model**:
- N/A - No user-facing access control (internal trading bot component)

**Input Validation**:
- Zone validation: Reuse Zone.__post_init__() validation from parent feature
- Price validation: Ensure Decimal > 0, no negative values
- Volume validation: Ensure Decimal >= 0, handle missing data gracefully (NFR-004)
- Configuration validation: BreakoutConfig.__post_init__() checks positive thresholds

**Data Protection**:
- No PII: Only stock symbols, prices, volumes (public market data)
- No encryption needed: Data is public, not sensitive
- Audit trail: All breakout events logged to JSONL (immutable, append-only)

**Security Scanning**:
- Run bandit on all new code: `bandit -r src/trading_bot/support_resistance/breakout_*.py`
- Target: 0 HIGH/CRITICAL issues (Constitution §Pre_Commit gate)

---

## [EXISTING INFRASTRUCTURE - REUSE] (8 components)

**Services/Modules**:
- src/trading_bot/support_resistance/zone_detector.py: ZoneDetector.detect_zones() - provides Zone list input
- src/trading_bot/support_resistance/zone_logger.py: Thread-safe JSONL logging infrastructure
- src/trading_bot/support_resistance/config.py: ZoneDetectionConfig pattern for breakout config
- src/trading_bot/market_data/market_data_service.py: MarketDataService for real-time quotes and historical OHLCV
- src/trading_bot/error_handling/retry.py: @with_retry decorator for API resilience

**Data Models**:
- src/trading_bot/support_resistance/models.py:
  - Zone dataclass (immutable, validated, serializable)
  - ZoneType enum (SUPPORT, RESISTANCE)
  - TouchType enum (BOUNCE, REJECTION, BREAKOUT) - already defined!
  - Timeframe enum (DAILY, FOUR_HOUR)

**Testing Infrastructure**:
- tests/unit/support_resistance/test_zone_detector.py: Zone mock fixtures
- tests/unit/support_resistance/conftest.py: Test helpers (if exists)

---

## [NEW INFRASTRUCTURE - CREATE] (4 components)

**Backend**:
1. **src/trading_bot/support_resistance/breakout_detector.py** (~150 lines)
   - BreakoutDetector class with dependency injection
   - detect_breakout(zone, current_price, current_volume, historical_volumes): Main API
   - flip_zone(zone, breakout_event): Zone flipping with strength bonus
   - _calculate_price_change_pct(zone_price, current_price): Helper (private)
   - _calculate_volume_ratio(current_volume, avg_volume): Helper (private)

2. **src/trading_bot/support_resistance/breakout_models.py** (~80 lines)
   - BreakoutEvent dataclass with 12 fields (event_id, zone_id, timestamps, prices, volume_ratio, types, status, symbol, timeframe)
   - BreakoutStatus enum (PENDING, CONFIRMED, WHIPSAW)
   - to_dict(), to_jsonl_line() serialization methods
   - __post_init__() validation (price > 0, volume >= 0, valid status, UTC timestamps)

3. **src/trading_bot/support_resistance/breakout_config.py** (~60 lines)
   - BreakoutConfig dataclass (frozen=True for immutability)
   - Fields: price_threshold_pct (1.0%), volume_threshold (1.3x), validation_bars (5), strength_bonus (2.0)
   - from_env() class method for env var loading
   - __post_init__() validation (positive values, reasonable thresholds)

4. **tests/unit/support_resistance/test_breakout_detector.py** (~300 lines)
   - Fixtures: mock_zone, mock_quote, mock_historical_volumes
   - Test classes:
     - TestBreakoutDetection: detect_breakout() with various scenarios
     - TestZoneFlipping: flip_zone() validation
     - TestVolumeCalculation: _calculate_volume_ratio() edge cases
     - TestPriceCalculation: _calculate_price_change_pct() precision
   - Target: 90% coverage (Constitution §Testing_Requirements)

**Logging Extension**:
- src/trading_bot/support_resistance/zone_logger.py: Add log_breakout_event(event: BreakoutEvent) method (~30 lines)

---

## [CI/CD IMPACT]

**Platform**: Local-only feature (remote-direct deployment model, no staging)

**Build Commands**: No changes (pure Python extension, no build step)

**Environment Variables**: All optional (have defaults)
- BREAKOUT_PRICE_THRESHOLD_PCT: Price movement threshold % (default: 1.0)
- BREAKOUT_VOLUME_THRESHOLD: Volume multiplier threshold (default: 1.3)
- BREAKOUT_VALIDATION_BARS: Whipsaw validation window (default: 5)
- BREAKOUT_STRENGTH_BONUS: Strength score bonus on flip (default: 2.0)

**No deployment changes**:
- No database migrations (JSONL storage only)
- No API endpoint changes (internal library)
- No frontend changes (backend feature)
- No Docker changes (pure Python)
- No environment secrets (public market data only)

**Testing in CI** (.github/workflows/verify.yml - if exists):
```yaml
- name: Test breakout detection
  run: pytest tests/unit/support_resistance/test_breakout_detector.py -v --cov
```

**Smoke Tests**: Not applicable (no deployment, local-only feature)

**Rollback Plan**:
- Rollback: git revert <commit-sha> (no state/data changes)
- Impact: None (additive feature, doesn't modify existing code)
- Duration: Instant (no deployment, no data migration)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- All existing tests continue to pass (no regressions in parent feature)
- Type checking passes: mypy --strict src/trading_bot/support_resistance/
- Linting clean: ruff check src/trading_bot/support_resistance/
- Security scan clean: bandit -r src/trading_bot/support_resistance/ (0 HIGH/CRITICAL)
- Test coverage ≥90%: pytest --cov=src.trading_bot.support_resistance.breakout_detector --cov-report=term-missing

**Integration Validation**:
```python
# Smoke test: Ensure BreakoutDetector integrates with existing infrastructure
from src.trading_bot.support_resistance import (
    ZoneDetector, BreakoutDetector, Zone, ZoneType
)

# Test Case 1: Module imports successfully
assert BreakoutDetector is not None

# Test Case 2: Composes with ZoneDetector output
zone = Zone(...)  # Create test zone
detector = BreakoutDetector(...)
signal = detector.detect_breakout(zone, ...)  # Should accept Zone from ZoneDetector

# Test Case 3: Logging works
from src.trading_bot.support_resistance import ZoneLogger
logger = ZoneLogger()
logger.log_breakout_event(event)  # Should write to logs/zones/breakouts-*.jsonl
assert Path("logs/zones/breakouts-*.jsonl").exists()
```

**Rollback Plan** (if issues found):
1. Identify commit: `git log --oneline src/trading_bot/support_resistance/breakout_*`
2. Revert changes: `git revert <commit-sha>`
3. Verify tests: `pytest tests/unit/support_resistance/ -v`
4. No data cleanup needed (JSONL logs are append-only, historical data preserved)

**Special Considerations**:
- No breaking changes: All new code, zero modifications to existing contracts
- No migration: Pure additive feature, no state changes
- Graceful degradation: If breakout detection fails, trading bot continues (optional feature)

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Scenario 1: Initial setup & verification (parent feature integration check)
- Scenario 2: Development workflow (mypy, ruff, bandit during dev)
- Scenario 3: Unit testing with coverage validation
- Scenario 4: Manual testing (interactive Python REPL)
- Scenario 5: Log verification (JSONL query and analysis)
- Scenario 6: Integration with existing trading bot workflow
- Scenario 7: Performance validation (NFR-001 benchmark)

---

## [SUCCESS CRITERIA] (from spec.md HEART metrics)

**Breakout Success Rate** (Primary Metric):
- Target: >60% of breakouts are CONFIRMED (no return below zone within 5 bars)
- Guardrail: Whipsaw rate <40%
- Measurement: `grep '"status":"confirmed"' logs/zones/breakouts-*.jsonl | wc -l`

**Zone Flip Accuracy**:
- Target: >85% accuracy on flip decisions (manual validation vs chart analysis)
- Measurement: Manual review of 20 random breakouts against TradingView charts

**Integration Rate**:
- Target: >20% of zone-based entries reference flipped zones
- Measurement: `grep '"zone_context":.*"flipped_zone":true' logs/trades/*.jsonl | wc -l` (requires trade logging integration)

**Flipped Zone Lifespan**:
- Target: Average >21 days active before re-flip
- Guardrail: <10% re-flip within 7 days
- Measurement: Query breakout_events list, calculate time between flips

---

## [RISKS & MITIGATION]

**Risk 1: Volume Data Availability**
- Impact: Cannot confirm breakouts without volume (FR-002 requirement)
- Likelihood: Medium (Robinhood API may have gaps)
- Mitigation: Graceful degradation (NFR-004) - skip volume check if unavailable, log warning
- Fallback: Price-only detection (>1% move) with lower confidence flag

**Risk 2: False Breakouts (Whipsaws)**
- Impact: Trades based on flipped zones may fail if breakout doesn't sustain
- Likelihood: High (40% whipsaw rate per spec assumptions)
- Mitigation: US5 validation (5-bar sustainability check), status tracking (PENDING/CONFIRMED/WHIPSAW)
- Monitoring: Track whipsaw rate in HEART metrics, adjust thresholds if >40%

**Risk 3: Performance Degradation**
- Impact: Breakout detection exceeds 200ms NFR-001 target
- Likelihood: Low (simple calculations, no complex algorithms)
- Mitigation: Benchmark in unit tests, optimize Decimal operations if needed
- Monitoring: Add performance test to CI, alert if P95 >150ms

**Risk 4: Integration Complexity**
- Impact: Difficult to integrate with existing trading bot logic
- Likelihood: Low (clean API, dependency injection)
- Mitigation: Comprehensive quickstart.md, integration test scenario
- Monitoring: Developer feedback, usage tracking in logs

---

## [IMPLEMENTATION PHASES]

**Phase 1: Core Models & Config** (US1, US2, US3 foundation)
- Create BreakoutEvent dataclass with validation
- Create BreakoutStatus enum
- Create BreakoutConfig with from_env()
- Add to __init__.py exports
- Estimated: 2-3 hours

**Phase 2: Breakout Detection Logic** (US1)
- Implement BreakoutDetector class
- Implement detect_breakout() method (FR-001, FR-002)
- Implement price/volume calculation helpers
- Add @with_retry decorator
- Estimated: 4-6 hours

**Phase 3: Zone Flipping** (US2)
- Implement flip_zone() method (FR-003, FR-004, FR-005)
- Update Zone model to support breakout_events list
- Add strength_score bonus logic (+2)
- Estimated: 2-3 hours

**Phase 4: Logging** (US3)
- Extend ZoneLogger with log_breakout_event()
- Add JSONL serialization to BreakoutEvent
- Test daily file rotation
- Estimated: 2-3 hours

**Phase 5: Testing** (Constitution §Testing_Requirements)
- Write unit tests for all components
- Add integration test for end-to-end workflow
- Achieve 90% coverage target
- Performance benchmarking
- Estimated: 4-6 hours

**Phase 6: Validation & Documentation** (US4, US5 optional)
- Manual testing via quickstart scenarios
- Log verification
- HEART metrics calculation
- Code review
- Estimated: 2-3 hours

**Total Estimated Effort**: 16-24 hours (MVP US1-US3)

**Optional Enhancements** (US4-US6): +6-12 hours
