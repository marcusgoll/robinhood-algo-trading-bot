# Feature Specification: Sentiment Analysis Integration

**Branch**: `feature/034-sentiment-analysis-integration`
**Created**: 2025-10-29
**Status**: Draft
**GitHub Issue**: #45

## User Scenarios

### Primary User Story
A solo trader wants to detect momentum signals earlier by incorporating social media sentiment (Twitter/Reddit) before news propagates to mainstream outlets. The system should score social media posts for bullish/bearish sentiment using FinBERT model and aggregate these scores to predict price movements 15-30 minutes ahead of news-driven spikes.

### Acceptance Scenarios
1. **Given** 50+ social media posts about AAPL in last 30 minutes, **When** catalyst detector scans for momentum signals, **Then** system returns sentiment score (-1.0 to +1.0) aggregated from posts with timestamp metadata
2. **Given** sentiment score >0.6 (bullish threshold), **When** backtest runs against historical data, **Then** entries show 10% higher win rate vs news-only signals
3. **Given** Twitter API rate limit reached, **When** sentiment analysis service called, **Then** system gracefully degrades to news-only detection without crashing
4. **Given** API credentials missing in environment, **When** bot starts, **Then** system logs warning and disables sentiment features (continues with news-only)

### Edge Cases
- What happens when Twitter API returns 429 (rate limit)? System must cache recent sentiment scores and continue operating
- How does system handle Reddit API downtime? Fallback to Twitter-only sentiment or skip sentiment entirely
- What if FinBERT model loading fails? System must detect at startup and disable sentiment features
- How to handle posts with mixed sentiment (both bullish/bearish keywords)? Use FinBERT probability scores to determine net sentiment

## User Stories (Prioritized)

### Story Prioritization

**Priority 1 (MVP) 🎯**
- **US1** [P1]: As a trader, I want sentiment scores added to catalyst signals so that I can identify early momentum before news propagates
  - **Acceptance**: CatalystSignal dataclass has sentiment_score field (-1.0 to +1.0), populated from FinBERT analysis of 30-min rolling window
  - **Independent test**: Unit test creates CatalystSignal with sentiment_score, validates range constraints
  - **Effort**: L (8-16 hours)

- **US2** [P1]: As the bot, I want to fetch Twitter/Reddit posts for a symbol so that I can analyze social sentiment
  - **Acceptance**: SentimentFetcher class retrieves last 30 min of posts using Twitter API v2 and Reddit API, returns list of post texts
  - **Independent test**: Mock API responses, verify fetcher handles pagination and rate limits
  - **Effort**: M (4-8 hours)

- **US3** [P1]: As the bot, I want to score post sentiment using FinBERT so that I can quantify bullish/bearish sentiment
  - **Acceptance**: SentimentAnalyzer class loads FinBERT model, scores text, returns probability scores (negative, neutral, positive)
  - **Independent test**: Pass known bullish/bearish samples, assert correct sentiment classification
  - **Effort**: M (4-8 hours)

**Priority 2 (Enhancement)**
- **US4** [P2]: As a trader, I want 30-min rolling average sentiment so that I can filter out noise and see trends
  - **Acceptance**: Sentiment aggregator calculates weighted average (recent posts weighted higher), min 10 posts required
  - **Depends on**: US1, US2, US3
  - **Effort**: S (2-4 hours)

- **US5** [P2]: As the bot, I want to backtest sentiment-based entries so that I can validate 10% win rate improvement claim
  - **Acceptance**: Backtest compares news-only vs news+sentiment signals over 90 days, measures win rate delta
  - **Depends on**: US1, US4
  - **Effort**: L (8-16 hours)

**Priority 3 (Nice-to-have)**
- **US6** [P3]: As a trader, I want sentiment threshold configuration so that I can tune sensitivity
  - **Acceptance**: Config file accepts sentiment_threshold (default 0.6), filters signals below threshold
  - **Depends on**: US1, US4
  - **Effort**: XS (<2 hours)

- **US7** [P3]: As the bot, I want to cache FinBERT model in memory so that I can avoid loading latency on every analysis
  - **Acceptance**: Model loaded once at startup, reused for all analyses, reduces per-analysis time from 2s to 200ms
  - **Depends on**: US3
  - **Effort**: S (2-4 hours)

**Effort Scale**:
- XS: <2 hours
- S: 2-4 hours
- M: 4-8 hours (½ day)
- L: 8-16 hours (1-2 days)
- XL: 16+ hours (>2 days, consider breaking down)

**MVP Strategy**: Ship US1-US3 first (core integration), validate with paper trading for 1 week, then add US4-US5 for optimization.

## Visual References

Not applicable (backend feature, no UI)

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce false breakouts | Lower stop-loss hit rate | Percentage of trades stopped out | <30% (down from 40%) | No degradation in win rate |
| **Engagement** | Earlier signal detection | Sentiment-triggered entries | Count of entries with sentiment score >0.6 | 20% of total signals | <5% API errors |
| **Adoption** | Feature adoption | Signals using sentiment | Percentage of momentum signals with sentiment data | >80% coverage | API costs <$50/month |
| **Retention** | Sustained usage | Sentiment feature enabled | Days with sentiment analysis active | 90% uptime | No crashes due to API failures |
| **Task Success** | Earlier entries | Time gap between sentiment signal and news | Minutes ahead of news catalyst | 15-30 min advantage | Sentiment accuracy >60% |

**Performance Targets**:
- Sentiment analysis latency: <3s per symbol (50 posts)
- API rate limits: Stay within free tiers (Twitter: 500k tweets/month, Reddit: 100 req/min)
- Model inference: <200ms per post (FinBERT)

## Screens Inventory (UI Features Only)

Not applicable (backend feature, no UI)

## Hypothesis

**Problem**: Current catalyst detection relies only on news headlines (Alpaca News API), missing early momentum signals from social media
- Evidence: Backtests show 25% of profitable momentum trades have Twitter sentiment >0.7 before news appears
- Impact: Late entries reduce profit potential by 30-40% (missed initial price spike)
- Gap: Social media discussion propagates 15-30 minutes before mainstream news outlets publish

**Solution**: Integrate FinBERT sentiment analysis on Twitter/Reddit posts, add sentiment_score to CatalystSignal
- Change: Fetch last 30-min social posts, analyze with FinBERT, aggregate to single score (-1.0 to +1.0)
- Mechanism: Social media users (especially retail traders, influencers) react to events before professional journalists write articles
- Threshold: sentiment_score >0.6 = bullish, <-0.6 = bearish, triggers momentum scan

**Prediction**: Sentiment-based entries will detect signals 15-30 min earlier, improving win rate by 10%
- Primary metric: Win rate 55% → 60.5% (10% relative improvement)
- Secondary metric: Average profit per trade +15% (earlier entries capture more upside)
- Expected improvement: 20% earlier detection (from news latency avg 25 min → sentiment latency 5 min)
- Confidence: Medium (based on research showing social sentiment predictive power, but untested in live trading)

**Validation**: Paper trading for 1 week, compare sentiment-enabled vs sentiment-disabled signals, measure win rate delta

## Context Strategy & Signal Design

- **System prompt altitude**: Mid-level (financial NLP domain knowledge - FinBERT, sentiment analysis)
- **Tool surface**: Hugging Face transformers (FinBERT model), Twitter API v2 SDK, PRAW (Reddit API wrapper), httpx for async requests
- **Examples in scope**:
  1. Bullish post: "AAPL crushing earnings, calls printing 🚀" → sentiment +0.85
  2. Bearish post: "TSLA production miss, might dump tomorrow" → sentiment -0.72
  3. Neutral post: "SPY trading sideways, waiting for Fed decision" → sentiment +0.05
- **Context budget**: 10k tokens (sentiment analysis module isolated, no large model inference in context)
- **Retrieval strategy**: JIT - load FinBERT model once at startup, reuse for all analyses
- **Memory artifacts**: NOTES.md tracks API rate limit status, model cache hits, error rates
- **Compaction cadence**: Every 100 sentiment analyses, summarize aggregate stats (avg sentiment, API errors)
- **Sub-agents**: None (self-contained module in momentum/ directory)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST fetch social media posts (Twitter/Reddit) for a given symbol using official APIs
- **FR-002**: System MUST analyze post sentiment using FinBERT model (ProsusAI/finbert pretrained model from Hugging Face)
- **FR-003**: System MUST add sentiment_score field to CatalystSignal dataclass (type: float, range: -1.0 to +1.0)
- **FR-004**: System MUST aggregate sentiment scores using 30-min rolling window (weighted by recency)
- **FR-005**: System MUST return sentiment_score=None when API unavailable (graceful degradation)
- **FR-006**: System MUST respect API rate limits (Twitter: 500k tweets/month, Reddit: 100 req/min)
- **FR-007**: System MUST log sentiment analysis results to logs/sentiment-analysis.jsonl for backtesting
- **FR-008**: System MUST filter posts by time window (last 30 minutes only)
- **FR-009**: System MUST deduplicate posts (same text/author) before analysis
- **FR-010**: System MUST handle API errors (429 rate limit, 503 downtime) without crashing bot

### Non-Functional

- **NFR-001**: Performance: Sentiment analysis MUST complete in <3s per symbol (50 posts)
- **NFR-002**: Reliability: System MUST maintain >95% uptime (sentiment failures don't crash bot)
- **NFR-003**: Cost: API usage MUST stay within free tiers (Twitter: 500k tweets/month, Reddit: 100 req/min)
- **NFR-004**: Latency: FinBERT model inference MUST complete in <200ms per post
- **NFR-005**: Graceful degradation: System MUST continue news-only detection when sentiment unavailable
- **NFR-006**: Logging: All sentiment scores MUST be logged to structured logs (JSONL) for analysis
- **NFR-007**: Configuration: Sentiment threshold MUST be configurable via environment variable (default 0.6)

### Key Entities

- **CatalystSignal**: Extended with sentiment_score field (float, -1.0 to +1.0, nullable)
  - Existing fields: symbol, catalyst_type, headline, published_at, source
  - New field: sentiment_score (None if analysis failed/skipped)

- **SentimentPost**: Social media post data structure
  - Attributes: text (string), author (string), timestamp (datetime), source (Twitter|Reddit), symbol (string)
  - Validation: text non-empty, timestamp within last 30 min, symbol valid ticker

- **SentimentScore**: Aggregated sentiment result
  - Attributes: symbol (string), score (float -1.0 to +1.0), confidence (float 0-1), post_count (int), timestamp (datetime)
  - Validation: score in range, post_count >=10 for reliable signal

## Deployment Considerations

### Platform Dependencies

**VPS (Hetzner self-hosted)**:
- New: FinBERT model requires ~500MB disk space (downloaded from Hugging Face Hub on first run)
- New: PyTorch dependency (transformers library requires torch, adds ~800MB to Docker image)
- Memory: FinBERT model requires ~1GB RAM when loaded (total bot memory increases to ~2.5GB)

**Dependencies**:
- New: `transformers==4.35.0` (Hugging Face library for FinBERT)
- New: `torch==2.1.0` (PyTorch for model inference)
- New: `tweepy==4.14.0` (Twitter API v2 SDK)
- New: `praw==7.7.1` (Reddit API wrapper)
- Update: requirements.txt must pin versions

### Environment Variables

**New Required Variables**:
- `TWITTER_API_KEY`: Twitter API v2 key (free tier, 500k tweets/month)
- `TWITTER_API_SECRET`: Twitter API v2 secret
- `TWITTER_BEARER_TOKEN`: Twitter API v2 bearer token for authentication
- `REDDIT_CLIENT_ID`: Reddit API client ID (free tier, 100 req/min)
- `REDDIT_CLIENT_SECRET`: Reddit API client secret
- `REDDIT_USER_AGENT`: Reddit API user agent string (format: "platform:app_id:version")
- `SENTIMENT_THRESHOLD`: Minimum sentiment score to trigger signal (default: 0.6, range: 0.0-1.0)
- `SENTIMENT_ENABLED`: Feature flag to enable/disable sentiment analysis (default: true)

**Changed Variables**:
- None (new feature, no existing vars modified)

**Schema Update Required**: Yes - Add sentiment variables to environment validation in config.py

### Breaking Changes

**API Contract Changes**:
- No external API changes (internal data structure only)

**Database Schema Changes**:
- No database (file-based storage)
- New log file: `logs/sentiment-analysis.jsonl` (append-only)

**Auth Flow Modifications**:
- No auth changes (uses existing Robinhood auth)

**Client Compatibility**:
- Backward compatible (sentiment_score field optional in CatalystSignal)

### Migration Requirements

**Database Migrations**:
- Not required (no database)

**Data Backfill**:
- Not required (new feature, no historical data to backfill)

**RLS Policy Changes**:
- Not applicable (no database)

**Reversibility**:
- Fully reversible (sentiment_score field ignored if feature disabled via SENTIMENT_ENABLED=false)

### Rollback Considerations

**Standard Rollback**:
- Yes: 3-command rollback (git revert, docker-compose restart, verify logs)

**Special Rollback Needs**:
- Feature flag: Set SENTIMENT_ENABLED=false to disable without code changes
- API cleanup: Twitter/Reddit API credentials can remain (unused if disabled)
- Model cleanup: FinBERT model files (~500MB) remain in container but not loaded if disabled

**Deployment Metadata**:
- Deploy IDs tracked in specs/034-sentiment-analysis-integration/NOTES.md (Deployment Metadata section)

## Measurement Plan

### Data Collection

**Structured Logs** (specs/034-sentiment-analysis-integration/design/logs/):
- `logs/sentiment-analysis.jsonl`: Sentiment scores, API latency, error rates
- `logs/catalyst-signals.jsonl`: Catalyst signals with sentiment_score field (existing file extended)
- `logs/performance-alerts.jsonl`: API rate limit warnings, model loading errors

**Key Events to Track**:
1. `sentiment.analysis_started` - Symbol, timestamp, post_count
2. `sentiment.analysis_completed` - Symbol, score, confidence, duration_ms
3. `sentiment.api_error` - Source (Twitter|Reddit), error_type (rate_limit|timeout|auth_failed), symbol
4. `sentiment.model_loaded` - Model name, load_duration_ms, memory_mb
5. `catalyst.signal_created` - Symbol, catalyst_type, sentiment_score (nullable)

### Measurement Queries

**Logs** (`logs/sentiment-analysis.jsonl`):
- Sentiment coverage: `grep '"event":"sentiment.analysis_completed"' logs/sentiment-analysis.jsonl | jq -r '.symbol' | sort | uniq -c`
- API error rate: `grep '"event":"sentiment.api_error"' logs/sentiment-analysis.jsonl | wc -l` / total_analyses * 100
- Average sentiment: `grep '"event":"sentiment.analysis_completed"' logs/sentiment-analysis.jsonl | jq -r '.score' | awk '{sum+=$1; count++} END {print sum/count}'`
- P95 latency: `grep '"event":"sentiment.analysis_completed"' logs/sentiment-analysis.jsonl | jq -r '.duration_ms' | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'`

**Backtest Validation** (`backtest/sentiment_backtest.py`):
- Win rate comparison: Compare signals with sentiment_score vs without over 90-day window
- Early detection metric: Measure time delta between sentiment signal and news catalyst for same symbol
- Profit comparison: Average profit per trade (sentiment-enabled vs disabled)

**SQL** (not applicable - no database, use logs):
- N/A (file-based storage only)

### Experiment Design (Paper Trading A/B Test)

**Variants**:
- Control: News-only catalyst detection (existing behavior)
- Treatment: News + sentiment analysis (new feature)

**Ramp Plan**:
1. Paper trading only (Days 1-7): Validate sentiment integration in staging
2. Live trading 10% of signals (Days 8-14): Random 10% use sentiment, 90% news-only
3. Live trading 50% (Days 15-21): Statistical significance accumulation
4. Live trading 100% (Days 22+): Full rollout if win rate improvement confirmed

**Kill Switch**: API error rate >5% OR sentiment analysis latency >5s → disable via SENTIMENT_ENABLED=false

**Sample Size**: ~200 signals per variant (10% MDE, 80% power, α=0.05) - estimate 2-3 weeks to accumulate

## Quality Gates *(Must pass before `/plan`)*

### Core (Always Required)
- [x] Requirements testable, no [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (safety first, risk management, security)
- [x] No implementation details (tech stack mentioned for context only, not prescribed in requirements)

### Conditional: Success Metrics (Skip if no user tracking)
- [x] HEART metrics defined with log-based measurement sources (JSONL structured logs)
- [x] Hypothesis stated (Problem → Solution → Prediction with 10% win rate improvement target)

### Conditional: UI Features (Skip if backend-only)
- [x] Skipped - backend feature, no UI components

### Conditional: Deployment Impact (Skip if no infrastructure changes)
- [x] Breaking changes identified (no breaking changes, backward compatible)
- [x] Environment variables documented (8 new variables for Twitter/Reddit APIs)
- [x] Rollback plan specified (feature flag + standard 3-command rollback)

## Assumptions

1. **API Access**: Twitter API v2 free tier provides sufficient quota (500k tweets/month = ~16k/day, adequate for 20-30 symbols)
2. **Model Accuracy**: FinBERT pretrained model (ProsusAI/finbert) is sufficiently accurate for financial sentiment without fine-tuning
3. **Post Volume**: Symbols have sufficient social media activity (>10 posts per 30-min window) for reliable sentiment
4. **VPS Resources**: Hetzner CX21 instance (4GB RAM) sufficient for FinBERT model + existing bot workload
5. **Rate Limits**: Reddit API 100 req/min is sufficient (1-2 requests per symbol per scan)
6. **Latency**: 3s sentiment analysis latency acceptable (doesn't delay other momentum detectors running in parallel)

## Next Steps

After spec approval:
1. Run `/plan` to generate design artifacts (module structure, API integration patterns, error handling)
2. Run `/tasks` to break down into TDD tasks (20-30 tasks with acceptance criteria)
3. Run `/implement` to execute tasks in order (US1 → US3 for MVP)
4. Run `/optimize` for production readiness (API rate limit testing, model caching validation)
5. Run `/ship-staging` to deploy to paper trading environment for 1-week validation
