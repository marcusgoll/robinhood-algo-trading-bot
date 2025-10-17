# Feature: Entry logic bull flag detection

## Overview
Bull flag pattern detection for automated entry signal generation in momentum trading system. Integrates with existing technical indicators module to provide comprehensive entry validation.

## Research Findings

### Finding 1: Existing Technical Indicators Module
**Source**: src/trading_bot/indicators/
**Details**:
- Robust technical indicators service with VWAP, EMA, MACD calculators
- Service uses Decimal precision for financial calculations
- State tracking for sequential calculations (EMA, MACD)
- validate_entry() method confirms price > VWAP AND MACD > 0
- check_exit_signals() detects MACD crossing negative

**Decision**: Reuse TechnicalIndicatorsService without modification. BullFlagDetector will instantiate service and call validation methods.

### Finding 2: Data Format Convention
**Source**: src/trading_bot/indicators/calculators.py
**Details**:
- Bars format: List[dict] with keys: high, low, close, volume
- All prices converted to Decimal for precision
- Results use dataclass pattern (VWAPResult, EMAResult, MACDResult)
- InsufficientDataError raised when not enough bars

**Decision**: Follow same patterns - use List[dict] for bars input, Decimal for calculations, dataclass for results, raise InsufficientDataError when needed.

### Finding 3: Industry Standards for Bull Flag Patterns
**Source**: Technical analysis literature
**Details**:
- Flagpole: 5-15% gain over 3-15 bars
- Consolidation: 20-50% retracement of flagpole, 3-10 bars duration
- Breakout: Volume increase 30%+, price moves 1%+ above resistance
- Risk/Reward: Minimum 2:1 for valid trades

**Decision**: Use these parameters as defaults with configuration support.

### Finding 4: Pattern Quality Considerations
**Source**: Technical analysis best practices
**Details**:
- Not all bull flags have equal success rates
- Quality factors: tight consolidation, strong volume profile, indicator alignment
- Scoring helps prioritize high-probability setups

**Decision**: Implement quality scoring (0-100) based on multiple factors. Threshold at 60 for valid signals, 80+ for high-quality.

## System Components Analysis

**Reusable Components**:
- TechnicalIndicatorsService (VWAP, MACD, EMA validation)
- InsufficientDataError exception class
- Decimal precision calculation patterns
- Dataclass result pattern

**New Components Needed**:
- BullFlagDetector class (main pattern detection logic)
- BullFlagResult dataclass (pattern detection results)
- BullFlagConfig dataclass (configuration parameters)
- Helper functions: detect_flagpole(), detect_consolidation(), confirm_breakout()

**Rationale**: Follows established project patterns for calculators and services. Maintains consistency with existing indicator module design.

## Feature Classification
- UI screens: false
- Improvement: false
- Measurable: false
- Deployment impact: false

## Key Decisions

1. **Integration Strategy**: Use composition - BullFlagDetector instantiates TechnicalIndicatorsService rather than modifying it. Preserves existing service interface and tests.

2. **Configuration Approach**: Use dataclass for BullFlagConfig with reasonable defaults. Allows customization without requiring deployment for parameter tuning.

3. **Quality Scoring**: Implement multi-factor scoring (0-100) to differentiate pattern quality. Helps filter low-probability setups and prioritize high-quality signals.

4. **Risk Parameters**: Calculate stop-loss (flag low - 0.5%) and target (breakout + flagpole height) for every signal. Reject signals with risk/reward below 2:1.

5. **Data Requirements**: Require minimum 30 bars for reliable detection (covers flagpole + consolidation + breakout + indicator calculations). Raise InsufficientDataError if not met.

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-17
- Phase 2 (Tasks): 2025-10-17

## Phase 2: Tasks (2025-10-17)

**Summary**:
- Total tasks: 34
- Parallel opportunities: 14 tasks marked [P]
- Setup tasks: 2
- Foundation tasks: 6 (exceptions, models, config, test fixtures)
- Core detection: 8 (tests + implementation for flagpole, consolidation, breakout)
- Risk & scoring: 4 (risk parameters, quality scoring)
- Integration: 3 (TechnicalIndicatorsService integration)
- Testing: 5 (E2E tests, performance benchmarks, coverage validation)
- Documentation: 6 (docstrings, type hints, linting, manual validation)

**Task Distribution by Category**:
- Backend implementation: 13 tasks (exceptions, models, config, detector logic)
- Unit tests: 9 tasks (config, models, detection phases, risk/scoring)
- Integration tests: 3 tasks (TechnicalIndicatorsService integration, regression)
- Performance & validation: 5 tasks (benchmarks, coverage, E2E tests)
- Documentation & polish: 6 tasks (docstrings, type checking, linting, manual validation)

**Complexity Breakdown**:
- Simple (< 50 lines): 8 tasks (setup, exceptions, exports, error-log)
- Medium (50-150 lines): 15 tasks (models, config, tests, docstrings)
- Complex (150+ lines): 11 tasks (detector implementation, comprehensive tests, integration)

**Checkpoint**:
- ✅ Tasks generated: 34 concrete tasks with file paths
- ✅ User story organization: N/A (technical feature, no user stories)
- ✅ Dependency graph: 7-phase sequential with parallel opportunities
- ✅ MVP strategy: Complete pattern detection (all phases required for valid signals)
- ✅ REUSE analysis: 4 existing components identified
- ✅ Quality gates defined: >90% coverage, <5s for 100 stocks, zero breaking changes
- 📋 Ready for: /analyze

## Last Updated
2025-10-17
