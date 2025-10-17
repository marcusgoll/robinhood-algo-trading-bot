# Feature: Momentum and Catalyst Detection

## Overview
This feature implements a three-pronged approach to identifying high-probability trading opportunities:
1. **Catalyst Detection**: Scans breaking news for fundamental events (earnings, FDA approvals, mergers)
2. **Pre-Market Momentum**: Tracks unusual price and volume activity before market open
3. **Pattern Recognition**: Identifies bull flag chart patterns indicating potential breakouts

The system is designed for manual review and paper trading validation before any live trading integration.

## Research Findings

### System Architecture Context
- **Existing modules**: TradingBot, SafetyChecks, TradingLogger already implemented
- **Missing dependencies**: market-data-module, technical-indicators not yet built
- **Integration point**: Will plug into existing TradingBot as a signal provider

### Similar Features
- **stock-screener** (sibling feature, shipped v1.0.0): Demonstrates market data fetching patterns
- **Pattern**: Can reuse data provider abstraction and caching strategy

### Data Provider Options
**News APIs**:
- NewsAPI: Free tier (100 req/day), good categorization
- Finnhub: Free tier (60 req/min), real-time news feed
- Alpaca: Free with trading account, integrated with market data

**Market Data Providers**:
- Alpaca: Supports pre-market data, free with account
- Polygon: Rich data but paid tier required for pre-market
- IEX Cloud: Limited pre-market support

**Recommendation**: Alpaca for both news and market data (single provider, free tier)

### Technical Indicators Research
**Bull Flag Pattern Detection**:
- Industry standard: 8%+ pole, 3-5% flag range, downward/flat slope
- False positive risk: Need volume confirmation on breakout
- Timeframe: Daily candles for MVP, can add intraday later

**Volume Analysis**:
- Pre-market volume typically 10-20% of regular session
- >200% of average is strong signal
- Need rolling average (10-day) for comparison

### Constitution Compliance
- §Safety_First: Manual review required, no auto-trading ✅
- §Code_Quality: Type hints, ≥90% coverage, DRY principle ✅
- §Risk_Management: Input validation, rate limiting ✅
- §Security: API keys in env vars only ✅
- §Data_Integrity: UTC timestamps, data validation ✅
- §Testing_Requirements: Unit + integration tests ✅

## System Components Analysis

**Reusable Components**:
- TradingLogger: For logging all detected signals
- SafetyChecks: For validating input data
- Config: For API key management

**New Components Needed**:
- CatalystDetector: News scanning and categorization
- PreMarketScanner: Pre-market momentum detection
- PatternRecognizer: Bull flag pattern detection
- MomentumScorer: Composite signal aggregation

**Rationale**: Modular design allows independent testing and validation of each signal type.

## Feature Classification
- UI screens: false (backend-only)
- Improvement: false (new feature)
- Measurable: false (internal tool, trading performance measured separately)
- Deployment impact: false (no infrastructure changes)

## Key Decisions

1. **Data Provider Choice**: Alpaca selected for unified API (news + market data)
   - Rationale: Single API key, free tier, supports pre-market data
   - Alternative: Multiple providers (NewsAPI + Polygon) adds complexity

2. **Pattern Detection Timeframe**: Daily candles for MVP
   - Rationale: Simpler implementation, less data required
   - Future: Can add intraday patterns after validation

3. **Signal Scoring Method**: Composite score (0-100) based on signal strength
   - Rationale: Allows ranking and filtering by confidence
   - Implementation: Weighted average of individual signal scores

4. **MVP Scope**: Manual review of signals, no automatic trading
   - Rationale: Validates accuracy before risking capital
   - Safety: Aligns with §Safety_First (paper trading first)

5. **Dependency Strategy**: Stub missing modules (market-data, technical-indicators) for MVP
   - Rationale: Don't block on unfinished dependencies
   - Technical debt: Replace stubs when modules available

## Assumptions

1. **API Access**: User will obtain Alpaca API key before testing
2. **Data Availability**: Alpaca provides reliable pre-market data
3. **News Quality**: Alpaca news feed includes categorized events (or we categorize manually)
4. **Pattern Validity**: Bull flag criteria are based on industry standards (may need tuning)
5. **Performance**: 500-stock scan completes in <90 seconds (needs validation)
6. **Manual Review**: Trader will review all signals before trading (no automation)

## Blockers and Mitigation

### Blocker 1: market-data-module not implemented
- **Impact**: Cannot fetch pre-market data or historical prices
- **Mitigation**: Implement minimal data fetching inline for MVP
- **Technical Debt**: Extract to shared module when technical-indicators built

### Blocker 2: News API categorization may be unreliable
- **Impact**: May need manual mapping of news events to catalyst types
- **Mitigation**: Start with keyword-based categorization, refine over time
- **Validation**: Manual review of first 100 classified events

### Blocker 3: Pre-market data availability varies by provider
- **Impact**: May need to change provider if Alpaca insufficient
- **Mitigation**: Abstract data provider interface for easy swapping
- **Fallback**: Use Polygon or IEX Cloud if Alpaca doesn't work

## Testing Strategy

### Unit Tests (≥90% coverage)
- CatalystDetector: Test news parsing and categorization
- PreMarketScanner: Test volume calculations and filters
- PatternRecognizer: Test bull flag detection logic
- MomentumScorer: Test composite scoring algorithm

### Integration Tests
- API mocking: Test with mocked Alpaca responses
- Data validation: Test with malformed/missing data
- Rate limiting: Test with simulated API errors

### Manual Validation
- Run against historical data (last 30 days)
- Compare detected patterns to manual analysis
- Validate catalyst categorization accuracy
- Measure performance (scan time for 500 stocks)

### Paper Trading Validation
- Run live for 2 weeks in paper trading mode
- Log all signals and actual outcomes
- Calculate win rate, average return, max drawdown
- Validate composite scoring predictive power

## Performance Targets

- **Catalyst scan**: <30 seconds for 500 stocks (API rate limited)
- **Pre-market scan**: <30 seconds for 500 stocks (one API call per stock)
- **Pattern detection**: <30 seconds for 500 stocks (local computation)
- **Total scan time**: <90 seconds for complete momentum scan
- **Memory usage**: <500MB for 500-stock scan
- **API calls**: <1000 per scan (stay within Alpaca limits)

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-16 ✅
- ✅ T001: Create project structure per plan.md tech stack (2025-10-16)
- ✅ T002: Test directory structure created (2025-10-16)
- ✅ T003: Create documentation structure (2025-10-16)
- ✅ T005: Create data model schemas for momentum detection (2025-10-16)
- ✅ T006: Create MomentumConfig dataclass (2025-10-16)
- ✅ T007: Create MomentumLogger wrapper (2025-10-16)
- ✅ T015: Create CatalystDetector service with scan() and categorize() methods (2025-10-16)
- ✅ T016: Add error handling for missing NEWS_API_KEY (2025-10-16)
- ✅ T011: Write test for CatalystDetector.categorize() - 100% coverage achieved (2025-10-16)
- ✅ T012: Write test for CatalystDetector.scan() - 7 tests passing, 75.86% coverage (2025-10-16)
- ✅ T017: Write integration test for CatalystDetector - 6 integration tests, 78.89% coverage (2025-10-16)

## Last Updated
2025-10-17T02:15:00-00:00

## Phase 2: Tasks (2025-10-16)

**Summary**:
- Total tasks: 41
- User story tasks: 24 (US1: 5, US2: 6, US3: 9, US4: 4)
- Parallel opportunities: 22 tasks marked [P]
- Setup tasks: 3 (Phase 1)
- Foundational tasks: 3 (Phase 2)
- Composition/Polish: 11 tasks (Phase 7-8)
- Task file: specs/002-momentum-detection/tasks.md

**Task Breakdown by Category**:
- Backend services: 8 (CatalystDetector, PreMarketScanner, BullFlagDetector, MomentumRanker)
- Unit tests: 11 (≥90% coverage target)
- Integration tests: 5 (E2E validation)
- API routes: 2 (signals, scan endpoints)
- Configuration/logging: 3 (config, schemas, logger)
- Documentation: 1 (usage examples)
- Polish: 8 (error handling, validation, health checks)

**Checkpoint**:
- ✅ Tasks generated: 41
- ✅ User story organization: Complete (US1-US4)
- ✅ Dependency graph: Created (6 phases)
- ✅ MVP strategy: Defined (US1-US3 independently testable, US4 aggregates)
- ✅ REUSE analysis: 5 existing components identified
- 📋 Ready for: /analyze

**Key Implementation Patterns**:
- All detectors follow MarketDataService pattern (@with_retry, validation)
- All logging follows StructuredTradeLogger pattern (JSONL, thread-safe)
- All tests follow existing test structure (unit/integration separation)
- MomentumEngine follows composition root pattern from plan.md

