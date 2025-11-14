# Feature Specification: Momentum and Catalyst Detection

**Branch**: `002-momentum-detection`
**Created**: 2025-10-16
**Status**: Draft

## User Scenarios

### Primary User Story
A day trader wants to identify high-probability trading opportunities by finding stocks with breaking news catalysts, strong pre-market momentum, and bullish chart patterns (bull flags) that indicate potential continuation moves.

### Acceptance Scenarios
1. **Given** a list of stocks with recent news, **When** the system scans for catalyst events, **Then** it identifies stocks with breaking news within the last 24 hours and flags catalyst type (earnings, FDA approval, merger, etc.)
2. **Given** pre-market trading hours (4:00 AM - 9:30 AM EST), **When** the system monitors price action, **Then** it identifies stocks with >5% pre-market price movement and unusual volume (>200% average)
3. **Given** a stock with upward momentum, **When** the system scans for chart patterns, **Then** it detects bull flag formations (consolidation after strong move) and calculates breakout price targets
4. **Given** multiple momentum signals across different stocks, **When** the system ranks opportunities, **Then** it prioritizes stocks with multiple confluent signals (catalyst + momentum + pattern)

### Edge Cases
- What happens when pre-market data is unavailable or delayed?
- How does system handle stocks with news but no price movement?
- What if a bull flag pattern forms but breaks down instead of breaking out?
- How to handle conflicting signals (positive catalyst but weak price action)?
- What happens during market hours when pre-market momentum has already played out?

## User Stories (Prioritized)

> **Purpose**: Break down feature into independently deliverable stories for MVP-first delivery.
> **Format**: [P1] = MVP (ship first), [P2] = Enhancement, [P3] = Nice-to-have

### Story Prioritization

**Priority 1 (MVP) 🎯**
- **US1** [P1]: As a trader, I want to scan for stocks with breaking news catalysts so that I can identify potential trading opportunities driven by fundamental events
  - **Acceptance**:
    - System fetches news from reliable sources (NewsAPI, Finnhub, or Alpaca)
    - Identifies catalyst types: earnings, FDA approval, merger/acquisition, product launch, analyst upgrades
    - Filters news to last 24 hours
    - Returns list of stocks with catalyst type and news headline
  - **Independent test**: Can run news scan standalone and return catalyst data
  - **Effort**: M (4-8 hours)

- **US2** [P1]: As a trader, I want to track pre-market movers so that I can identify stocks with strong momentum before regular market hours
  - **Acceptance**:
    - Monitors pre-market trading (4:00 AM - 9:30 AM EST)
    - Identifies stocks with >5% price change from previous close
    - Detects unusual volume (>200% of 10-day average pre-market volume)
    - Returns list ranked by magnitude of move and volume
  - **Independent test**: Can fetch pre-market data and identify movers independently
  - **Effort**: M (4-8 hours)

- **US3** [P1]: As a trader, I want to scan for bull flag patterns so that I can identify stocks in consolidation with potential for continuation breakouts
  - **Acceptance**:
    - Detects strong upward move (pole): >8% gain in 1-3 days
    - Identifies consolidation (flag): Price range within 3-5% for 2-5 days
    - Flag slope is downward or flat (not upward)
    - Calculates breakout level (top of flag range)
    - Provides price target (pole height projected from breakout)
  - **Independent test**: Can analyze historical price data and identify bull flag patterns
  - **Effort**: L (8-16 hours)

**Priority 2 (Enhancement)**
- **US4** [P2]: As a trader, I want to see momentum signals combined across all detection methods so that I can focus on stocks with multiple confluent signals
  - **Acceptance**:
    - Aggregates signals from catalyst, pre-market, and pattern detection
    - Scores each stock based on signal strength (0-100)
    - Ranks stocks by composite score
    - Displays all active signals for each stock
  - **Depends on**: US1, US2, US3
  - **Effort**: S (2-4 hours)

- **US5** [P2]: As a trader, I want to filter momentum candidates by liquidity and volatility so that I only trade stocks that meet my risk criteria
  - **Acceptance**:
    - Filters by minimum average daily volume (e.g., >1M shares)
    - Filters by price range (e.g., $5-$500)
    - Filters by market cap (e.g., >$500M for large cap only)
    - Excludes penny stocks and low-float manipulation targets
  - **Depends on**: US1, US2, US3
  - **Effort**: S (2-4 hours)

**Priority 3 (Nice-to-have)**
- **US6** [P3]: As a trader, I want to receive real-time alerts when new momentum opportunities are detected so that I can act quickly on time-sensitive signals
  - **Acceptance**:
    - Monitors for new catalysts in real-time
    - Detects pre-market movers as they emerge
    - Sends alerts via configured channel (log, email, Discord)
    - Includes key metrics and action recommendation
  - **Depends on**: US1, US2, US4
  - **Effort**: M (4-8 hours)

- **US7** [P3]: As a trader, I want to see historical performance of momentum signals so that I can validate the system's accuracy before using it for live trading
  - **Acceptance**:
    - Backtests momentum signals against historical data
    - Tracks success rate of each signal type
    - Reports average return, win rate, and maximum drawdown
    - Provides confidence score based on historical performance
  - **Depends on**: US1, US2, US3, US4
  - **Effort**: L (8-16 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (independent momentum detection modules), validate each separately, then integrate with US4 for composite scoring. Add filtering (US5) and alerting (US6) based on usage patterns.

## Visual References

Not applicable - backend/API feature with no UI components.

## Success Metrics (HEART Framework)

> **SKIP METRICS**: This is an internal trading system component with no direct user behavior to track. Success is measured by trading performance (win rate, P&L) rather than user engagement.

## Screens Inventory (UI Features Only)

> **SKIP SCREENS**: Backend-only feature (no UI components). Outputs are logged data and API responses consumed by trading strategy.

## Hypothesis

> **Not an improvement feature**: This is a new capability addition, not improving an existing flow.

## Context Strategy & Signal Design

- **System prompt altitude**: Detailed technical context for trading domain (catalyst types, chart patterns, time zones)
- **Tool surface**: Essential tools - news API, market data API, technical analysis library, logging
- **Examples in scope**:
  1. Bull flag pattern detection example with price data
  2. Catalyst categorization example (earnings vs FDA)
  3. Pre-market volume calculation example
- **Context budget**: Target 25k tokens (API data streams are verbose)
- **Retrieval strategy**: JIT for market data (fetch on demand), upfront for pattern definitions
- **Memory artifacts**: NOTES.md with pattern definitions, TODO.md for signal validation tasks
- **Compaction cadence**: Summarize every 10 API responses to avoid token overflow
- **Sub-agents**: None - single-agent implementation

## Requirements

### Functional (testable only)

- **FR-001**: System MUST fetch news from at least one reliable source (NewsAPI, Finnhub, or Alpaca) and filter to last 24 hours
- **FR-002**: System MUST categorize news catalysts into types: earnings, FDA approval, merger/acquisition, product launch, analyst upgrade/downgrade
- **FR-003**: System MUST monitor pre-market trading data between 4:00 AM and 9:30 AM EST
- **FR-004**: System MUST identify pre-market movers with >5% price change from previous close
- **FR-005**: System MUST calculate unusual volume as >200% of 10-day average pre-market volume
- **FR-006**: System MUST detect bull flag patterns with the following criteria:
  - Pole: >8% price gain in 1-3 days
  - Flag: Price consolidation within 3-5% range for 2-5 days
  - Flag slope: Downward or flat (not upward trending)
- **FR-007**: System MUST calculate breakout price (top of flag range) and price target (pole height projected from breakout)
- **FR-008**: System MUST rank momentum candidates by composite signal strength
- **FR-009**: System MUST log all detected signals with timestamp, stock symbol, signal type, and key metrics
- **FR-010**: System MUST handle missing or delayed data gracefully without crashing
- **FR-011**: System MUST validate all input data (timestamps, prices, volumes) before processing
- **FR-012**: System MUST respect API rate limits and implement exponential backoff on failures

### Non-Functional

- **NFR-001**: Performance: Pre-market scan MUST complete within 60 seconds for up to 500 stocks
- **NFR-002**: Performance: Pattern detection MUST process 100 stocks in under 30 seconds
- **NFR-003**: Reliability: System MUST handle API failures gracefully and retry with exponential backoff (max 3 retries)
- **NFR-004**: Data Quality: All timestamps MUST be in UTC and validated for correctness
- **NFR-005**: Error Handling: All errors MUST be logged with context (symbol, signal type, error message)
- **NFR-006**: Maintainability: All detection logic MUST be unit tested with ≥90% coverage
- **NFR-007**: Security: API keys MUST be stored in environment variables, never in code
- **NFR-008**: Auditability: All detected signals MUST be logged to persistent storage for backtesting and validation

### Key Entities (if data involved)

- **MomentumSignal**: Detected trading opportunity with attributes:
  - symbol (str): Stock ticker
  - signal_type (enum): CATALYST, PREMARKET_MOVER, BULL_FLAG
  - timestamp (datetime): When signal was detected (UTC)
  - strength (float): 0-100 score indicating signal quality
  - metadata (dict): Type-specific data (news headline, price change %, pattern measurements)

- **CatalystEvent**: News-driven catalyst with attributes:
  - symbol (str): Stock ticker
  - catalyst_type (enum): EARNINGS, FDA_APPROVAL, MERGER, PRODUCT_LAUNCH, ANALYST_UPGRADE
  - headline (str): News headline
  - published_at (datetime): When news was published (UTC)
  - source (str): News source

- **PreMarketMover**: Stock with significant pre-market activity with attributes:
  - symbol (str): Stock ticker
  - price_change_pct (float): Percentage change from previous close
  - volume (int): Pre-market volume
  - avg_volume (int): 10-day average pre-market volume
  - volume_ratio (float): Current volume / average volume
  - timestamp (datetime): When measurement was taken (UTC)

- **BullFlagPattern**: Detected chart pattern with attributes:
  - symbol (str): Stock ticker
  - pole_start (datetime): Start of upward move
  - pole_end (datetime): End of upward move
  - pole_gain_pct (float): Percentage gain during pole formation
  - flag_start (datetime): Start of consolidation
  - flag_end (datetime): End of consolidation
  - flag_range_pct (float): Price range during consolidation
  - breakout_price (float): Price level for breakout confirmation
  - price_target (float): Projected target if breakout occurs
  - pattern_valid (bool): Whether pattern meets all criteria

## Deployment Considerations

> Backend-only feature with no infrastructure changes required.

### Platform Dependencies

**None** - Uses existing Python runtime and dependencies.

### Environment Variables

**New Required Variables**:
- `NEWS_API_KEY`: API key for news data provider (NewsAPI, Finnhub, or Alpaca)
  - Staging: Use test/sandbox API key
  - Production: Use production API key with rate limit allowance
- `MARKET_DATA_SOURCE`: Source for pre-market data (default: "alpaca")
  - Staging: "alpaca"
  - Production: "alpaca"

**Changed Variables**:
- None

**Schema Update Required**: Yes - Update `secrets.schema.json` in `/plan` phase

### Breaking Changes

**API Contract Changes**:
- No breaking changes - new feature only

**Database Schema Changes**:
- No database changes required (uses in-memory processing and logging)

**Auth Flow Modifications**:
- No auth changes

**Client Compatibility**:
- Backward compatible - new module only

### Migration Requirements

**Database Migrations**:
- Not required

**Data Backfill**:
- Not required

**RLS Policy Changes**:
- Not applicable

**Reversibility**:
- Fully reversible - can disable feature by not calling momentum detection modules

### Rollback Considerations

**Standard 3-command rollback**:
```bash
git revert <commit>
git push
# No database migrations to reverse
```

## Dependencies and Blockers

### Dependencies
- **market-data-module**: Required for fetching pre-market data and historical prices
  - Status: Not implemented yet (in roadmap backlog)
  - Workaround: Can stub with static data for initial implementation
  - Critical path: Yes - needed for US2 and US3

- **technical-indicators**: Required for VWAP and pattern detection calculations
  - Status: In roadmap backlog
  - Workaround: Can implement basic calculations inline for MVP
  - Critical path: Partial - needed for US3 bull flag detection

- **news-api-integration**: Required for catalyst detection
  - Status: Not implemented
  - Workaround: Can use direct API calls for MVP
  - Critical path: Yes - needed for US1

### Blockers
- **API access**: Requires API keys for news source (NewsAPI, Finnhub, or Alpaca)
  - Resolution: User must obtain API key before testing
  - Impact: Cannot test catalyst detection without API access

- **Pre-market data availability**: Not all data providers offer pre-market data
  - Resolution: Must use Alpaca or similar provider with pre-market support
  - Impact: May need to change data provider

### Assumptions
- User has access to a market data provider with pre-market data (Alpaca recommended)
- News API provides categorized news (may need manual categorization for some sources)
- Bull flag pattern detection uses daily candles (not intraday for MVP)
- Pattern detection runs on-demand, not continuously (for MVP)
- Signals are logged for manual review (no automatic trading for MVP)

## Constitution Compliance

This feature adheres to Constitution v1.0.0:

- **§Safety_First**: All signals logged for manual review, no automatic trading
- **§Code_Quality**: Will implement with type hints, ≥90% test coverage, single-purpose functions
- **§Risk_Management**: Validates all API data, handles missing data gracefully
- **§Security**: API keys in environment variables only
- **§Data_Integrity**: All timestamps in UTC, data validation before processing
- **§Testing_Requirements**: Unit tests for all detection logic, integration tests with mocked APIs

## Success Criteria

The momentum and catalyst detection feature is successful when:

1. **Catalyst Detection**: System correctly identifies and categorizes at least 90% of major news events (earnings, FDA approvals, mergers) within 24 hours of publication
2. **Pre-Market Identification**: System detects pre-market movers (>5% change, >200% volume) with 95% accuracy compared to manual analysis
3. **Pattern Recognition**: Bull flag detection identifies valid patterns with 80% precision (patterns that meet criteria) and 70% recall (doesn't miss obvious patterns)
4. **Performance**: Complete scan of 500 stocks (catalyst + pre-market + pattern) in under 90 seconds
5. **Reliability**: System handles API failures gracefully with zero crashes over 30 days of operation
6. **Data Quality**: Zero timezone errors, zero invalid price/volume data processed
7. **Composite Scoring**: Stocks with multiple confluent signals (3+) show 60%+ win rate in paper trading validation
8. **Auditability**: 100% of detected signals logged with complete metadata for backtesting

## Out of Scope

The following are explicitly NOT included in this feature:

- Automatic trade execution based on momentum signals
- Real-time streaming data (MVP uses polling)
- Intraday pattern detection (MVP uses daily candles)
- Machine learning-based pattern recognition
- Social media sentiment analysis
- Options flow or dark pool data
- Integration with broker for direct order placement
- Mobile app or web UI (backend only)
- Historical backtesting framework (separate feature)
- Alert notifications (separate P3 user story)

## Next Steps

After specification approval:
1. Run `/clarify` if ambiguities remain
2. Run `/plan` to create technical design
3. Run `/tasks` to break down into implementation tasks
4. Implement US1 (catalyst detection) first, validate independently
5. Implement US2 (pre-market movers) second, validate independently
6. Implement US3 (bull flag patterns) third, validate independently
7. Implement US4 (composite scoring) to integrate signals
8. Paper trade validation with real market data
9. Ship to production with manual review gates
