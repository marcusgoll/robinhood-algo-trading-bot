# Feature: Multi-Timeframe Confirmation for Momentum Trades

## Overview
Multi-timeframe analysis adds higher-timeframe confirmation to momentum trades by validating bull flag patterns detected on lower timeframes (5-minute) against daily and 4-hour trend alignment. This reduces false signals and improves trade quality by ensuring trades align with broader market structure.

## Research Findings

### Finding 1: Existing Bull Flag Detection on Single Timeframe
**Source**: D:\Coding\Stocks\src\trading_bot\patterns\bull_flag.py

- Current BullFlagDetector operates on single timeframe (typically 5-minute bars)
- Three-phase detection: flagpole → consolidation → breakout
- Technical indicator validation (VWAP, MACD, EMA) on single timeframe only
- No higher-timeframe trend validation

**Decision**: Extend bull_flag.py pattern with multi-timeframe validation layer

### Finding 2: Market Data Service Supports Multiple Intervals
**Source**: D:\Coding\Stocks\src\trading_bot\market_data\market_data_service.py:118-123

- `get_historical_data()` accepts interval parameter: "day", "week", "10minute", "5minute"
- Supports span parameter: "day", "week", "month", "3month"
- Returns pandas DataFrame with OHLCV data
- Already integrated with @with_retry for resilience

**Decision**: Leverage existing market data infrastructure for multi-timeframe fetching

### Finding 3: Technical Indicators Service is Stateful
**Source**: D:\Coding\Stocks\src\trading_bot\indicators\service.py

- TechnicalIndicatorsService maintains state (_last_ema_9, _last_macd, etc.)
- Single instance per service lifecycle
- validate_entry() checks: price > VWAP AND MACD > 0

**Decision**: Create separate indicator service instances per timeframe to avoid state collision

### Finding 4: Similar Pattern in Support/Resistance Mapping
**Source**: specs/023-support-resistance-mapping/spec.md (grep results)

- Zone detection uses daily + 4H timeframes for support/resistance levels
- Establishes pattern for multi-timeframe coordination
- Institutional-level zone identification

**Decision**: Reuse multi-timeframe approach from support/resistance feature

### Finding 5: Constitution Compliance Requirements
**Source**: D:\Coding\Stocks\.spec-flow\memory\constitution.md

- §Data_Integrity: Validate all timeframe data before analysis
- §Risk_Management: Position sizing, stop losses mandatory
- §Testing_Requirements: 90% coverage, backtesting required
- §Safety_First: Fail-fast on validation errors

**Implication**: Must validate higher-timeframe data availability before trade entry

### Finding 6: Backtesting Engine Supports Multi-Timeframe
**Source**: specs/001-backtesting-engine/spec.md (roadmap shipped features)

- Event-driven backtesting with chronological execution
- Multi-source data support (Alpaca + Yahoo Finance)
- Parquet caching for performance
- Strategy Protocol for type-safe strategy interface

**Decision**: Use backtesting engine to validate multi-timeframe strategy performance

## System Components Analysis

**Reusable Components**:
- MarketDataService (timeframe data fetching)
- TechnicalIndicatorsService (per-timeframe indicator calculation)
- BullFlagDetector (lower-timeframe pattern detection)
- BacktestEngine (strategy validation)

**New Components Needed**:
- MultiTimeframeValidator (orchestrates cross-timeframe checks)
- TimeframeAlignment dataclass (stores alignment status)
- HigherTimeframeTrend enum (BULLISH, BEARISH, NEUTRAL, UNKNOWN)

**Rationale**: Composition pattern - extend existing pattern detection with higher-timeframe validation layer without modifying core bull flag logic.

## Feature Classification
- UI screens: false (backend strategy logic)
- Improvement: true (enhances existing bull flag pattern detection)
- Measurable: true (win rate, false positive reduction trackable via trade logs)
- Deployment impact: false (additive feature, no breaking changes)

## Checkpoints
- Phase 0 (Specification): 2025-10-28

## Last Updated
2025-10-28T23:05:00Z

## Phase 1: Planning (2025-10-28)

**Summary**:
- Architecture: Composition pattern with weighted scoring (Daily 60% + 4H 40%)
- Components: 6 reusable (MarketDataService, TechnicalIndicatorsService, BullFlagDetector, @with_retry, test patterns, JSONL logging)
- New infrastructure: 4 components (MultiTimeframeValidator, models, logger, config)
- Performance target: <2s P95 validation latency
- Key decision: Separate TechnicalIndicatorsService instances per timeframe (prevents state collision)
- Test strategy: TDD with 90% coverage (13 unit + 4 integration tests)

**Checkpoint**:
- ✅ Plan document created: specs/033-multi-timeframe-confirmation/plan.md
- ✅ Research completed: 6 findings documented
- ✅ Architecture designed: Composition pattern, weighted scoring
- ✅ Reuse analysis: 6 existing components identified
- ✅ Performance budget defined: <2s P95 (daily 300ms + 4H 500ms + indicators 200ms)
- 📋 Ready for: /tasks

## Phase 2: Tasks (2025-10-28)

**Summary**:
- Total tasks: 50
- User story tasks: 30 (US1: 13, US2: 4, US3: 6, US4: 4, US5: 3)
- Parallel opportunities: 27 tasks marked [P]
- Setup tasks: 2
- Task file: specs/033-multi-timeframe-confirmation/tasks.md

**Checkpoint**:
- ✅ Tasks generated: 50 tasks
- ✅ User story organization: Complete (5 stories prioritized P1-P3)
- ✅ Dependency graph: Created (7 phases with clear blocking relationships)
- ✅ MVP strategy: Defined (US1 + US2 - daily validation + JSONL logging)
- ✅ Test guardrails: Speed requirements, coverage requirements (90%+), quality gates
- ✅ Parallel execution: 27 tasks marked [P] for concurrent execution
- 📋 Ready for: /analyze

**Task Breakdown**:
- Phase 1 (Setup): 2 tasks (directory structure, dependency verification)
- Phase 2 (Foundational): 4 tasks (models, config - blocks all stories)
- Phase 3 (US1 - Daily validation): 13 tasks (tests + implementation)
- Phase 4 (US2 - JSONL logging): 4 tasks (logger + integration)
- Phase 5 (US3 - 4H validation): 6 tasks (weighted scoring extension)
- Phase 6 (US4 - Graceful degradation): 4 tasks (retry + fallback logic)
- Phase 7 (US5 - Backtest comparison): 3 tasks (win rate validation)
- Phase 8 (BullFlag Integration): 5 tasks (composition pattern integration)
- Phase 9 (Polish): 9 tasks (performance, docs, deployment prep)

**Key Decisions**:
- TDD approach: Write failing tests first (100% coverage on new code)
- Separate TechnicalIndicatorsService instances per timeframe (avoid state collision)
- Weighted scoring: Daily 60% + 4H 40% (prioritizes institutional over intraday)
- Graceful degradation: 3 retries with exponential backoff, then DEGRADED status
- MVP scope: US1 + US2 (daily validation + logging), defer 4H to Phase 5

**Next Steps**:
1. /analyze - Cross-artifact consistency validation, risk identification
2. /implement - Execute tasks with TDD, 90%+ test coverage
3. /optimize - Performance tuning (<2s P95), code quality review
4. /preview - Manual testing with paper trading, JSONL log analysis
