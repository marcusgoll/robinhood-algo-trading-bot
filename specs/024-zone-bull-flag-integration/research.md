# Research & Discovery: zone-bull-flag-integration

## Research Decisions

### Decision: Constructor injection for ZoneDetector dependency

- **Decision**: Use optional constructor injection (`zone_detector: ZoneDetector | None = None`) in `BullFlagDetector.__init__`
- **Rationale**:
  - Matches existing pattern in BullFlagDetector (line 60: `momentum_logger: MomentumLogger | None = None`)
  - Enables graceful degradation when zone detection unavailable (spec requirement NFR-002)
  - Facilitates testing with dependency injection (easier to mock ZoneDetector)
- **Alternatives**:
  - Service locator pattern (rejected: adds complexity, less explicit)
  - Always-required dependency (rejected: violates graceful degradation requirement)
- **Source**: `src/trading_bot/momentum/bull_flag_detector.py:56-71`

### Decision: Use ProximityChecker.find_nearest_resistance() method

- **Decision**: Leverage existing `ProximityChecker.find_nearest_resistance()` method for zone lookup
- **Rationale**:
  - Method already exists at `src/trading_bot/support_resistance/proximity_checker.py:171-203`
  - Implements exact logic needed: find resistance zone above current price
  - Returns `Zone | None` for graceful handling
- **Alternatives**:
  - Create new `ZoneDetector.find_nearest_resistance()` (rejected: duplicates existing functionality)
  - Query zones directly in BullFlagDetector (rejected: violates separation of concerns)
- **Source**: `src/trading_bot/support_resistance/proximity_checker.py:171-203`

### Decision: Decimal arithmetic for price calculations

- **Decision**: Use Python `Decimal` type for all price/target calculations
- **Rationale**:
  - ZoneDetector and ProximityChecker already use Decimal throughout (models.py:18, 59)
  - BullFlagDetector currently uses float (bull_flag_detector.py:450-477), needs conversion
  - Financial calculations require precision (constitution §Data_Integrity)
- **Alternatives**:
  - Continue using float (rejected: precision loss in financial calculations)
  - Mixed float/Decimal (rejected: conversion errors, confusing API)
- **Source**: `src/trading_bot/support_resistance/models.py:18`, `constitution.md:35-40`

### Decision: Create TargetCalculation dataclass in momentum schemas

- **Decision**: Add `TargetCalculation` dataclass to `src/trading_bot/momentum/schemas/momentum_signal.py`
- **Rationale**:
  - Preserves both adjusted and original targets for backtesting (spec US2)
  - Follows existing pattern: all data models in schemas directory with `__post_init__` validation
  - Immutable dataclass ensures audit trail integrity
- **Alternatives**:
  - Return tuple (rejected: unclear field semantics, no validation)
  - Modify BullFlagPattern (rejected: breaks backward compatibility, violates SRP)
- **Source**: `src/trading_bot/momentum/schemas/momentum_signal.py:148-206` (BullFlagPattern pattern)

### Decision: JSONL logging for all target calculations

- **Decision**: Use MomentumLogger to log all target calculations with adjustment metadata
- **Rationale**:
  - MomentumLogger already logs signals at bull_flag_detector.py:158-165
  - Spec requires structured logging for backtesting analysis (NFR-003)
  - Follows constitution §Audit_Everything
- **Alternatives**:
  - Create separate TargetLogger (rejected: over-engineering, logging is ancillary)
  - No logging (rejected: violates spec NFR-003 and constitution §Audit_Everything)
- **Source**: `src/trading_bot/momentum/bull_flag_detector.py:158-165`, `constitution.md:14`

### Decision: 5% search range for resistance zones

- **Decision**: Search for resistance zones within 5% above entry price
- **Rationale**:
  - Spec FR-003 specifies 5% range explicitly
  - Balances relevance (zones too far don't matter) with coverage (capture meaningful resistance)
  - Formula: `search_ceiling = entry_price * Decimal('1.05')`
- **Alternatives**:
  - Dynamic range based on volatility (rejected: adds complexity, no spec requirement)
  - Fixed dollar amount (rejected: doesn't scale with stock price)
- **Source**: `specs/024-zone-bull-flag-integration/spec.md:150` (FR-003)

### Decision: 90% resistance zone adjustment factor

- **Decision**: Adjust profit target to 90% of resistance zone price when zone is closer than 2:1 target
- **Rationale**:
  - Spec specifies 90% buffer (FR-002)
  - Provides safety margin below resistance to increase fill probability
  - Backtest will validate 85%, 90%, 95% thresholds (US5)
- **Alternatives**:
  - Use exact zone price (rejected: too aggressive, high rejection risk)
  - Use 95% (rejected: less margin for slippage)
- **Source**: `specs/024-zone-bull-flag-integration/spec.md:149` (FR-002)

---

## Components to Reuse (7 found)

- `src/trading_bot/momentum/bull_flag_detector.py`: Core pattern detection logic (scan, _detect_pattern, _calculate_targets)
- `src/trading_bot/support_resistance/proximity_checker.py:171-203`: find_nearest_resistance() method for zone lookup
- `src/trading_bot/support_resistance/zone_detector.py`: Zone detection service (dependency injection)
- `src/trading_bot/support_resistance/models.py:36-123`: Zone dataclass with price_level, strength_score, zone_type
- `src/trading_bot/momentum/logging/momentum_logger.py`: Structured JSONL logging (log_signal method)
- `src/trading_bot/momentum/schemas/momentum_signal.py:148-206`: BullFlagPattern dataclass pattern (for TargetCalculation design)
- `decimal.Decimal`: Python standard library for price precision

---

## New Components Needed (3 required)

- `src/trading_bot/momentum/schemas/momentum_signal.py`: TargetCalculation dataclass (adjusted_target, original_2r_target, adjustment_reason, resistance_zone_price, resistance_zone_strength)
- `src/trading_bot/momentum/bull_flag_detector.py`: New method `_adjust_target_for_zones(entry_price, original_target, symbol)` (private helper)
- `tests/unit/services/momentum/test_bull_flag_target_adjustment.py`: Unit tests for zone integration logic

---

## Unknowns & Questions

None - all technical questions resolved during research phase.

- ✅ How to integrate ZoneDetector with BullFlagDetector? → Constructor injection (established pattern)
- ✅ How to find nearest resistance zone? → Reuse ProximityChecker.find_nearest_resistance()
- ✅ What data structure for target metadata? → New TargetCalculation dataclass following BullFlagPattern
- ✅ How to handle ZoneDetector unavailability? → Optional dependency + try/except fallback
- ✅ Where to log target calculations? → MomentumLogger (existing logger)
