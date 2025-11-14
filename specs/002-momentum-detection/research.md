# Research & Discovery: 002-momentum-detection

## Research Decisions

### Decision: News API Provider Selection

- **Decision**: Alpaca Markets as primary news source, with Finnhub as fallback
- **Rationale**: Alpaca provides free market data API with news feeds, pre-market data, and technical analysis all in one place. Integrated with existing market data infrastructure.
- **Alternatives**:
  - NewsAPI: General-purpose news but requires separate integration
  - Finnhub: Good for international, but requires separate news fetch
  - IEX Cloud: Expensive for news data
- **Source**: Specification mentions Alpaca as recommended provider; existing market-data-module likely already uses Alpaca

### Decision: Bull Flag Detection Algorithm

- **Decision**: Use daily OHLCV candles with manual pattern detection (no external library)
- **Rationale**:
  - Intraday data would require streaming and add complexity
  - Daily patterns more reliable for swing trading strategies
  - Manual implementation keeps dependencies minimal
  - Can be optimized later with technical-indicators library
- **Alternatives**:
  - TA-Lib: Heavy dependency, requires compiled bindings
  - technical-indicators library: In roadmap, can upgrade later
  - ML-based pattern recognition: Too complex for MVP
- **Source**: Specification explicitly states "daily candles" for MVP

### Decision: Pre-Market Time Zone Handling

- **Decision**: Hardcode EST timezone, convert all timestamps to UTC for storage/logging
- **Rationale**:
  - US markets only (pre-market hours 4:00 AM - 9:30 AM EST)
  - UTC timestamps ensure consistency across systems
  - Reduces timezone-related bugs
- **Alternatives**:
  - Support multiple timezones: Adds complexity, not needed for MVP
  - Use local time throughout: Breaks logging/auditing requirement
- **Source**: Specification requirement NFR-004 (UTC timestamps)

### Decision: Signal Scoring Model

- **Decision**: Linear composite score (weighted sum) of normalized signal strengths
- **Rationale**:
  - Simple to understand and debug
  - Easily adjustable weights for different signal types
  - Can be upgraded to ML model later without API changes
- **Alternatives**:
  - Bayesian model: Requires probability estimates we don't have
  - Machine learning: Too complex for MVP
  - Boolean (all-or-nothing): Loses nuance of partial signals
- **Source**: Specification US4 mentions "composite score"

## Components to Reuse (3 found)

- ✅ **MarketDataService** (src/trading_bot/services/market_data_service.py): Quote fetching, historical OHLCV data with @with_retry resilience
- ✅ **TradingLogger** (src/trading_bot/logging/trading_logger.py): JSONL audit trail for all trading decisions, daily rotation
- ✅ **@with_retry decorator** (src/trading_bot/utils/resilience.py): Automatic exponential backoff for API failures, circuit breaker

## New Components Needed (4 required)

- 🆕 **CatalystDetector** (src/trading_bot/momentum/catalyst_detector.py): Fetches news, categorizes catalyst types, returns CatalystEvent objects
- 🆕 **PreMarketScanner** (src/trading_bot/momentum/premarket_scanner.py): Monitors pre-market data 4:00-9:30 AM EST, identifies movers >5% and >200% volume
- 🆕 **BullFlagDetector** (src/trading_bot/momentum/bull_flag_detector.py): Pattern detection on daily OHLCV, calculates breakout targets
- 🆕 **MomentumRanker** (src/trading_bot/momentum/momentum_ranker.py): Aggregates signals, computes composite score, ranks candidates

## Unknowns & Questions

- ⚠️ **News API Rate Limits**: Unclear how many news items returned per day and rate limit structure (NewsAPI has 500 requests/day free tier). Recommendation: Implement caching and deduplication.
- ⚠️ **Bull Flag Validation Thresholds**: Specification gives ranges (pole >8%, flag 3-5% range, 2-5 days) but these are initial estimates. May need tuning after backtesting.
- ⚠️ **Market Hours Edge Case**: System behavior when run during market hours (not pre-market). Should cache pre-market results or return stale data?
- ⚠️ **API Failure Strategy**: If news API fails, should we skip catalyst detection or use cached results? Specification says "handle gracefully" but doesn't specify strategy.

---

## Dependencies Status

| Dependency | Status | Blocker | Workaround |
|-----------|--------|---------|-----------|
| market-data-module | Not implemented | US2, US3 | Stub with Alpaca direct API calls |
| technical-indicators | In roadmap | US3 (partial) | Implement pattern detection manually |
| news-api-integration | Not implemented | US1 | Use direct Alpaca/Finnhub API calls |

---

## Architecture Context

**Stack**:
- Language: Python 3.9+ (existing trading_bot codebase)
- Runtime: FastAPI + APScheduler (for periodic scans)
- Data Storage: JSONL logs (src/trading_bot/logging/)
- Market Data: Alpaca API (existing MarketDataService)
- Error Handling: @with_retry decorator with exponential backoff

**Patterns**:
- Service-oriented architecture: Each detector is independent service
- Composition: MomentumRanker composes results from 3 detectors
- Resilience: All API calls use @with_retry with circuit breaker
- Auditability: All signals logged via TradingLogger to persistent JSONL

**Integration Points**:
- Input: Market data from Alpaca (stocks list, pre-market quotes, historical prices)
- Output: MomentumSignal objects (logged to JSONL, exposed via API)
- Dependencies: Existing MarketDataService, TradingLogger, error-handling framework
