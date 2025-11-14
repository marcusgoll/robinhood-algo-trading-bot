# Research & Discovery: 003-entry-logic-bull-flag

## Research Decisions

### Decision: Reuse TechnicalIndicatorsService without modification

- **Decision**: Use composition pattern - BullFlagDetector instantiates TechnicalIndicatorsService and calls validate_entry(), get_vwap(), get_macd()
- **Rationale**: Preserves existing service interface, maintains test coverage, follows established integration pattern
- **Alternatives**: Modify TechnicalIndicatorsService to include bull flag logic (rejected - violates single responsibility), create standalone pattern detector without indicators (rejected - duplicates validation logic)
- **Source**: src/trading_bot/indicators/service.py, specs/003-entry-logic-bull-flag/NOTES.md

### Decision: Follow dataclass result pattern with Decimal precision

- **Decision**: Create BullFlagResult dataclass following VWAPResult/MACDResult pattern, use Decimal for all price calculations
- **Rationale**: Maintains consistency with existing indicator module, ensures financial calculation precision, provides structured output
- **Alternatives**: Return dictionary (rejected - less type-safe), use float (rejected - precision loss for financial calculations)
- **Source**: src/trading_bot/indicators/calculators.py (VWAPResult, EMAResult, MACDResult)

### Decision: Configuration via dataclass with __post_init__ validation

- **Decision**: Create BullFlagConfig dataclass with __post_init__ validation following IndicatorConfig pattern
- **Rationale**: Matches existing configuration pattern, validates parameters on initialization, provides clear error messages for invalid configurations
- **Alternatives**: Environment variables (rejected - less flexible for tuning), hardcoded values (rejected - no customization), JSON config file (rejected - adds file I/O complexity)
- **Source**: src/trading_bot/indicators/config.py (IndicatorConfig pattern)

### Decision: Quality scoring (0-100) to differentiate pattern reliability

- **Decision**: Implement multi-factor scoring considering: flagpole strength (0-25 pts), consolidation tightness (0-25 pts), volume profile (0-25 pts), indicator alignment (0-25 pts)
- **Rationale**: Not all bull flags have equal success rates, scoring helps filter low-probability setups (< 60), prioritize high-quality signals (80+)
- **Alternatives**: Binary valid/invalid (rejected - misses quality gradations), simple scoring (rejected - insufficient granularity)
- **Source**: Technical analysis best practices, backtesting research

### Decision: Minimum 30 bars required for reliable detection

- **Decision**: Require 30 bars minimum to cover: flagpole (3-15 bars) + consolidation (3-10 bars) + MACD calculation (26 bars) + breakout confirmation (2 bars)
- **Rationale**: Ensures sufficient data for pattern phases and indicator validation, prevents false positives from insufficient data
- **Alternatives**: 20 bars (rejected - insufficient for MACD), 50 bars (rejected - unnecessarily restrictive)
- **Source**: MACD requires 26 bars minimum (src/trading_bot/indicators/service.py), pattern phases require additional bars

---

## Components to Reuse (4 found)

- src/trading_bot/indicators/service.py: TechnicalIndicatorsService - validate_entry(), get_vwap(), get_macd() methods
- src/trading_bot/indicators/exceptions.py: InsufficientDataError exception class
- src/trading_bot/indicators/config.py: Dataclass configuration pattern with __post_init__ validation
- src/trading_bot/indicators/calculators.py: Dataclass result pattern (VWAPResult, MACDResult), Decimal precision calculations

---

## New Components Needed (6 required)

- src/trading_bot/patterns/__init__.py: Package initialization (new patterns module)
- src/trading_bot/patterns/bull_flag.py: BullFlagDetector class with detect_flagpole(), detect_consolidation(), confirm_breakout() methods
- src/trading_bot/patterns/config.py: BullFlagConfig dataclass with validation
- src/trading_bot/patterns/exceptions.py: Pattern-specific exceptions (PatternNotFoundError, InvalidConfigurationError)
- src/trading_bot/patterns/models.py: BullFlagResult, FlagpoleData, ConsolidationData dataclasses
- tests/patterns/test_bull_flag.py: Comprehensive unit tests for pattern detection logic

---

## Unknowns & Questions

None - all technical questions resolved
