# Feature: Support/resistance zone mapping

## Overview
Support and resistance zone mapping identifies key price levels where institutional and retail traders commonly place orders. These zones represent areas of high trading activity where price has repeatedly bounced (support) or reversed (resistance). By mapping these zones from daily and 4-hour timeframes, the bot can improve entry timing, set realistic profit targets, and avoid low-probability trades in no-man's land between zones.

## Research Findings

### Finding 1: Technical Indicators Module Already Shipped
- **Source**: roadmap.md (lines 487-529), specs/technical-indicators/spec.md
- **Delivered**: VWAP, EMA (9/20-period), MACD calculators with state tracking
- **Integration Point**: Support/resistance mapping extends technical-indicators service
- **Decision**: Build as additional module in existing indicators architecture, reuse MarketDataService for OHLCV data

### Finding 2: Constitution Risk Management Principles
- **Source**: constitution.md §Risk_Management (lines 23-28)
- **Principles Applied**:
  - Position sizing mandatory (zones help determine optimal entry near support)
  - Stop losses required (zones provide logical stop-loss placement below support)
  - Validate all inputs (OHLCV data validation before zone calculation)
- **Implication**: Zone detection must fail-safe on invalid data, never proceed with corrupt zone analysis

### Finding 3: Existing Backtesting Engine
- **Source**: roadmap.md (lines 597-621), Constitution §Testing_Requirements
- **Delivered**: BacktestEngine v1.0.0 with event-driven execution, Parquet caching
- **Opportunity**: Use backtesting engine to validate zone accuracy (hit rate, breakout success rate)
- **Test Plan**: Backtest 20+ stocks over 90 days, measure zone hit rate >70% threshold

### Finding 4: Bull Flag Entry Logic Already Implemented
- **Source**: roadmap.md (lines 530-570), specs/003-entry-logic-bull-flag/
- **Integration Need**: US6 (P3) requires adjusting bull flag profit targets to nearest resistance zone
- **Current Behavior**: Fixed 2:1 risk-reward ratio calculation from flagpole height
- **Enhancement**: Replace fixed R:R with dynamic target at 90% of nearest resistance zone when closer than 2:1 target
- **Decision**: Defer US6 to P3 priority, ship MVP (US1-US3) first for validation

### Finding 5: Industry Zone Identification Algorithms
- **Common Approaches**:
  1. **Pivot Points**: Identify swing highs/lows using X-bar lookback (e.g., 5-bar pivot)
  2. **Clustering**: Group nearby pivots within tolerance (e.g., 1.5%) into zones
  3. **Strength Scoring**: Weight by touch count + volume profile
- **Selected Approach**:
  - 5-bar pivot detection (swing high has highest high within 5 bars on each side)
  - 1.5% price tolerance for zone clustering
  - Strength = touch count + volume bonus (+1 per high-volume touch)
- **Rationale**: Balances sensitivity (identifies meaningful zones) with specificity (avoids noise)

### Finding 6: Performance Budget Considerations
- **Source**: Constitution §Code_Quality (line 17-21)
- **Target**: Zone analysis <3 seconds for 90 days daily data
- **Data Volume**: 90 days = ~63 trading days = 63 OHLCV bars for daily analysis
- **Algorithm Complexity**: O(n²) for pivot detection + O(n) for clustering = O(n²) worst case
- **Optimization**: Cache pivot points, reuse between symbols if using same timeframe
- **Validation**: Include performance tests in test suite

## System Components Analysis

**Reusable (from existing codebase)**:
- MarketDataService: Historical OHLCV data fetching (already integrated with Alpaca API + Yahoo Finance fallback)
- StructuredLogger: JSONL logging for zone events
- Decimal precision utilities: Financial calculations
- BacktestEngine: Validation of zone accuracy over historical data

**New Components Needed**:
- ZoneDetector: Main service class orchestrating pivot detection, clustering, strength scoring
- PivotFinder: Identifies swing highs and swing lows using N-bar lookback
- ZoneClusterer: Merges nearby pivots into zones within tolerance
- StrengthScorer: Calculates zone strength from touch count + volume profile
- ProximityChecker: Real-time price-to-zone distance calculation
- ZoneLogger: Structured logging for zone identification and proximity events

**Rationale**: Composition pattern maintains single-responsibility principle, enables isolated testing of each component.

## Feature Classification
- UI screens: false
- Improvement: false (new feature, not improving existing flow)
- Measurable: true (zone hit rate, breakout success rate)
- Deployment impact: false (local-only, no infrastructure changes)

## Research Mode
Standard research (3-5 tools):
- Constitution.md checked
- Roadmap.md checked for dependencies
- Existing specs reviewed (technical-indicators, bull-flag-entry)
- No UI artifacts needed (backend-only)
- No deployment artifacts needed (local-only)

## Key Decisions

1. **Daily timeframe priority**: Focus MVP on daily zones (US1-US3), defer 4-hour zones to P2 (US4)
   - **Rationale**: Daily zones capture institutional-level support/resistance, higher signal-to-noise ratio
   - **Trade-off**: Miss intraday levels, but reduces complexity for MVP validation

2. **Touch threshold: 3+ for daily, 2+ for 4-hour**: Daily zones require more evidence of significance
   - **Rationale**: Daily zones should represent multi-week price memory, 4-hour zones are tactical intraday levels
   - **Data-driven**: Industry standard for daily support/resistance identification

3. **1.5% price tolerance for zone clustering**: Balance between zone specificity and realistic price action
   - **Rationale**: Institutional orders cluster within 1-2% of round numbers and psychological levels
   - **Example**: $150.00 zone captures touches from $148.50 to $151.50

4. **Volume bonus in strength scoring**: Prioritize zones with high-volume rejections
   - **Rationale**: High volume indicates institutional participation, stronger zone validity
   - **Implementation**: +1 strength per touch with volume >1.5x average

5. **2% proximity threshold for alerts**: Early warning for approaching zones without excessive noise
   - **Rationale**: Gives bot 2-3% price movement to prepare entry/exit decisions
   - **Tunable**: Can be adjusted based on backtesting results

6. **No database persistence**: Calculate zones on-demand from market data
   - **Rationale**: Zones are dynamic, market structure changes, avoid stale data
   - **Performance**: Cache zones per symbol for trading session, recalculate daily
   - **Alternative considered**: Persistent storage rejected due to staleness risk

## Assumptions

1. **Historical data availability**: Assumes MarketDataService provides minimum 30 days of OHLCV data
   - **Validation**: Handle insufficient data gracefully (return empty zones with warning)

2. **Single timeframe per analysis**: Daily or 4-hour analyzed independently, not combined
   - **Reason**: Simplifies algorithm, allows timeframe-specific tuning

3. **Long-only bias**: Support zones prioritized for entries, resistance for exits
   - **Future**: Short-selling feature would invert zone usage (enter at resistance, exit at support)

4. **No zone expiration**: Zones remain valid until invalidated by breakout or data refresh
   - **Reason**: Price levels have long-term memory, zones can remain relevant for weeks/months

5. **Intraday price not considered for daily zones**: Only daily OHLCV (open, high, low, close) used
   - **Trade-off**: Miss intraday wicks, but aligns with daily chart analysis methodology

## Checkpoints
- Phase 0 (Spec): 2025-10-21

## Last Updated
2025-10-21T13:47:00Z
- Phase 2 (Tasks): 2025-10-21

## Phase 2: Tasks (2025-10-21 15:30)

**Summary**:
- Total tasks: 44
- User story tasks: 28 (organized by priority P1, P2, P3)
- Parallel opportunities: 20 tasks marked [P]
- Setup tasks: 2 (Phase 1)
- Foundational tasks: 5 (Phase 2)
- Task file: specs/023-support-resistance-mapping/tasks.md

**Task Breakdown by Phase**:
- Phase 1 (Setup): 2 tasks - Project structure, dependency validation
- Phase 2 (Foundational): 5 tasks - Models, config, logger, unit tests
- Phase 3 (US1 - Daily zones): 7 tasks - Swing detection, clustering, zone building, tests
- Phase 4 (US2 - Strength scoring): 5 tasks - Scoring algorithm, sorting, tests
- Phase 5 (US3 - Proximity alerts): 4 tasks - Proximity check, logging integration, tests
- Phase 6 (US4 - 4-hour zones): 4 tasks - Timeframe parameter, config updates, tests
- Phase 7 (US5 - Breakout detection): 5 tasks - Breakout logic, zone flip, logging, tests
- Phase 8 (US6 - Bull flag integration): 5 tasks - Target adjustment, dependency injection, tests
- Phase 9 (Polish): 7 tasks - Error handling, performance validation, local validation

**Key Task Organization Decisions**:
- TDD approach: Write tests before implementation for all core algorithms
- Reuse markers: 6 existing components identified (MarketDataService, BullFlagDetector pattern, StructuredLogger, MomentumConfig, retry decorator, Decimal precision)
- New components: 3 (ZoneDetector, models dataclasses, ZoneLogger)
- Dependency graph: Clear story completion order (Foundational → US1 → US2 → US3 → US4 → US5 → US6)
- MVP scope: Phase 3-5 (US1-US3) - Daily zone identification, strength scoring, proximity alerts

**Checkpoint**:
- ✅ Tasks generated: 44
- ✅ User story organization: Complete (6 stories across 8 phases)
- ✅ Dependency graph: Created with clear blocking relationships
- ✅ MVP strategy: Defined (US1-US3 for first release, validate before US4-US6)
- ✅ Parallel opportunities: 20 tasks marked for concurrent execution
- 📋 Ready for: /analyze

