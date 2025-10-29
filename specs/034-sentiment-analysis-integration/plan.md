# Implementation Plan: Sentiment Analysis Integration

## [RESEARCH DECISIONS]

See: research.md for full research findings

**Summary**:
- Stack: Python 3.11 + Hugging Face Transformers + PyTorch + tweepy + praw
- Components to reuse: 7 (CatalystDetector, MomentumSignal/CatalystEvent dataclasses, @with_retry, MomentumLogger, MomentumConfig, validate_symbols, structured logger)
- New components needed: 5 (SentimentFetcher, SentimentAnalyzer, SentimentAggregator, sentiment data models, sentiment-analysis.jsonl log)
- Key decision: PIGGYBACK CatalystDetector.scan() method (extend, don't replace)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11 (existing), FastAPI 0.104.1 (existing), Docker Compose (existing)
- ML Framework: PyTorch 2.1.0 (new), Hugging Face Transformers 4.35.0 (new)
- Social APIs: tweepy 4.14.0 (Twitter API v2), praw 7.7.1 (Reddit API)
- Model: ProsusAI/finbert (pretrained FinBERT from Hugging Face Hub, ~500MB)
- Logging: JSONL structured logging (existing pattern, new file: logs/sentiment-analysis.jsonl)

**Patterns**:
- **Piggyback Integration**: Extend existing CatalystDetector.scan() to add sentiment analysis
  - Rationale: Spec requirement "PIGGYBACK existing CatalystDetector.scan() - add sentiment_score field"
  - Pattern: Call SentimentAnalyzer from CatalystDetector, populate CatalystEvent.sentiment_score
  - Benefit: Minimal disruption, backward compatible

- **Graceful Degradation**: Continue news-only detection when sentiment unavailable
  - Rationale: NFR-005, constitution §Safety_First (fail safe, not fail open)
  - Pattern: sentiment_score=None when API fails, bot continues without sentiment
  - Benefit: Resilient to API failures, no trading interruption

- **Model Caching**: Load FinBERT once at startup, reuse for all analyses
  - Rationale: NFR-004 (<200ms inference), US7 (reduce latency from 2s → 200ms)
  - Pattern: Singleton model instance in SentimentAnalyzer.__init__()
  - Benefit: Fast inference, predictable memory usage

- **30-min Rolling Window with Recency Weighting**: Aggregate recent posts with exponential decay
  - Rationale: FR-004, US4 (filter out noise, see trends)
  - Pattern: Weighted average with exponential decay (recent posts weighted 2x older posts)
  - Benefit: Emphasizes recent sentiment, reduces stale signal noise

- **Feature Flag Rollback**: SENTIMENT_ENABLED env var for quick disable
  - Rationale: Deployment rollback considerations, constitution §Risk_Management
  - Pattern: Check env var, skip sentiment analysis if false, set sentiment_score=None
  - Benefit: Instant rollback without code redeployment

**Dependencies** (new packages required):
- `transformers==4.35.0`: Hugging Face library for FinBERT model loading/inference
- `torch==2.1.0`: PyTorch for FinBERT model execution
- `tweepy==4.14.0`: Twitter API v2 SDK for fetching tweets
- `praw==7.7.1`: Reddit API wrapper (Python Reddit API Wrapper)

**Docker Image Impact**: +1.3GB
- PyTorch: +800MB
- FinBERT model: +500MB (downloaded on first run, cached in container)
- Total image size: ~2.5GB (from current ~1.2GB)
- VPS capacity: 20GB disk (sufficient per capacity-planning.md)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
└── momentum/
    ├── catalyst_detector.py        # MODIFIED: Extend scan() to call sentiment
    ├── schemas/
    │   └── momentum_signal.py      # MODIFIED: Add sentiment_score to CatalystEvent
    ├── config.py                   # MODIFIED: Add sentiment API credentials
    └── sentiment/                  # NEW MODULE
        ├── __init__.py
        ├── sentiment_fetcher.py    # NEW: Twitter/Reddit API integration
        ├── sentiment_analyzer.py   # NEW: FinBERT model inference
        ├── sentiment_aggregator.py # NEW: 30-min rolling window aggregation
        └── models.py               # NEW: SentimentPost, SentimentScore dataclasses

tests/
├── unit/
│   └── momentum/
│       └── sentiment/              # NEW TEST MODULE
│           ├── test_sentiment_fetcher.py
│           ├── test_sentiment_analyzer.py
│           ├── test_sentiment_aggregator.py
│           ├── test_sentiment_models.py
│           └── test_catalyst_detector_sentiment.py
└── integration/
    └── momentum/
        └── sentiment/              # NEW INTEGRATION TESTS
            ├── test_sentiment_end_to_end.py
            └── test_api_error_handling.py

logs/
└── sentiment-analysis.jsonl        # NEW LOG FILE
```

**Module Organization**:
- `sentiment/sentiment_fetcher.py`: API integration (Twitter + Reddit), handles rate limits, authentication
- `sentiment/sentiment_analyzer.py`: FinBERT model loading, post scoring, batch inference
- `sentiment/sentiment_aggregator.py`: Aggregation logic (30-min window, recency weighting, min 10 posts)
- `sentiment/models.py`: Data models (SentimentPost, SentimentScore) with validation
- `catalyst_detector.py`: Orchestrates sentiment analysis within existing scan() method

---

## [DATA MODEL]

See: data-model.md for complete entity definitions

**Summary**:
- Entities: 3 (CatalystEvent extended, SentimentPost new, SentimentScore new)
- Relationships: SentimentPost → SentimentScore → CatalystEvent.sentiment_score
- Migrations required: No (backward-compatible field addition to CatalystEvent)

**Key Changes**:
- CatalystEvent: Add `sentiment_score: float | None = None` field
- Validation: sentiment_score must be in range [-1.0, 1.0] or None
- Backward compatibility: Existing code without sentiment_score continues working

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs** (or defaults from design/systems/budgets.md):
- NFR-001: Sentiment analysis MUST complete in <3s per symbol (50 posts)
- NFR-002: System MUST maintain >95% uptime (sentiment failures don't crash bot)
- NFR-003: API usage MUST stay within free tiers (Twitter: 500k tweets/month, Reddit: 100 req/min)
- NFR-004: FinBERT model inference MUST complete in <200ms per post
- NFR-005: Graceful degradation: System MUST continue news-only detection when sentiment unavailable
- NFR-006: All sentiment scores MUST be logged to structured logs (JSONL) for analysis
- NFR-007: Sentiment threshold MUST be configurable via environment variable (default 0.6)

**Lighthouse Targets**: N/A (backend feature, no UI)

**Performance Breakdown**:
- API fetch (Twitter + Reddit): ~1.5s (parallel requests)
- FinBERT inference (50 posts): ~1.0s (batch inference at 200ms/post amortized)
- Aggregation: ~0.5s (weighted average calculation)
- **Total**: ~3s per symbol (meets NFR-001)

---

## [SECURITY]

**Authentication Strategy**:
- Twitter API v2: Bearer token authentication (TWITTER_BEARER_TOKEN from env vars)
- Reddit API: OAuth2 client credentials (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET from env vars)
- FinBERT model: No authentication (open source, free to use)

**Authorization Model**:
- No RBAC needed (single bot instance, no multi-user support)
- API credentials stored in `.env` file (not committed to git)
- Credentials loaded via MomentumConfig.from_env() (existing pattern)

**Input Validation**:
- Symbol validation: Reuse existing `validate_symbols()` (1-5 uppercase letters)
- Post text validation: SentimentPost.__post_init__() checks non-empty text
- Timestamp validation: SentimentPost.__post_init__() checks within 30 minutes
- Sentiment score validation: CatalystEvent.__post_init__() checks range [-1.0, 1.0]

**Rate Limiting**:
- Twitter: 500k tweets/month (free tier), managed by tweepy SDK (auto-retry on 429)
- Reddit: 100 req/min (free tier), managed by praw SDK (auto-backoff)
- Retry policy: Use existing `@with_retry` decorator (exponential backoff, max 3 attempts)
- Graceful degradation: Log error, return sentiment_score=None, continue without sentiment

**Data Protection**:
- PII handling: Social media posts not persisted (ephemeral, used for analysis only)
- Sentiment scores logged without PII (only symbol, score, timestamp in logs)
- No encryption needed (public social media data, no sensitive info)

---

## [EXISTING INFRASTRUCTURE - REUSE] (7 components)

**Services/Modules**:
1. **src/trading_bot/momentum/catalyst_detector.py**: CatalystDetector class
   - Reuse: Extend `scan()` method to integrate sentiment analysis
   - Pattern: Async method with @with_retry, graceful degradation
   - Integration point: Call SentimentAnalyzer after news fetch, populate CatalystEvent.sentiment_score

2. **src/trading_bot/error_handling/retry.py**: @with_retry decorator
   - Reuse: Apply to Twitter/Reddit API calls for rate limit handling
   - Pattern: Exponential backoff with jitter, callback support
   - Benefit: Handles 429 rate limits, timeouts, transient errors

3. **src/trading_bot/momentum/logging/momentum_logger.py**: MomentumLogger class
   - Reuse: Log sentiment events (sentiment.analysis_started, sentiment.api_error)
   - Pattern: Structured JSONL logging with thread safety
   - Integration: Create SentimentLogger wrapper around MomentumLogger

**Data Models**:
4. **src/trading_bot/momentum/schemas/momentum_signal.py**: CatalystEvent dataclass
   - Reuse: Add sentiment_score field (backward-compatible Optional[float])
   - Pattern: Frozen dataclass with __post_init__ validation
   - Change: `sentiment_score: float | None = None` field + validation

5. **src/trading_bot/momentum/config.py**: MomentumConfig dataclass
   - Reuse: Add sentiment API credentials from environment variables
   - Pattern: Load from .env via `from_env()` classmethod
   - New fields: TWITTER_API_KEY, REDDIT_CLIENT_ID, SENTIMENT_ENABLED, etc.

**Utilities**:
6. **src/trading_bot/momentum/validation.py**: validate_symbols() function
   - Reuse: Validate symbol input before sentiment analysis
   - Pattern: Raises ValueError for invalid symbols
   - Usage: Call before fetch_twitter_posts(), fetch_reddit_posts()

7. **src/trading_bot/logging/structured_logger.py**: JSONL logging utilities
   - Reuse: Log structured events to logs/sentiment-analysis.jsonl
   - Pattern: Append-only JSONL writes, JSON serialization
   - Usage: Log sentiment.analysis_completed, sentiment.api_error events

---

## [NEW INFRASTRUCTURE - CREATE] (5 components)

**Backend**:
1. **src/trading_bot/momentum/sentiment/sentiment_fetcher.py**: SentimentFetcher class
   - Purpose: Fetch Twitter/Reddit posts for a symbol using official APIs
   - Methods:
     - `__init__(config: MomentumConfig)`: Initialize Twitter/Reddit API clients
     - `fetch_twitter_posts(symbol: str, minutes: int = 30) -> list[SentimentPost]`
     - `fetch_reddit_posts(symbol: str, minutes: int = 30) -> list[SentimentPost]`
     - `fetch_all(symbol: str) -> list[SentimentPost]`: Combine both sources
   - Dependencies: tweepy (Twitter), praw (Reddit)
   - Error handling: @with_retry for rate limits, return empty list on auth failure

2. **src/trading_bot/momentum/sentiment/sentiment_analyzer.py**: SentimentAnalyzer class
   - Purpose: Score posts using FinBERT model, return sentiment probability scores
   - Methods:
     - `__init__()`: Load FinBERT model once (caching)
     - `analyze_post(text: str) -> dict[str, float]`: Analyze single post
     - `analyze_batch(posts: list[str]) -> list[dict[str, float]]`: Batch inference
   - Model: ProsusAI/finbert (Hugging Face Hub)
   - Performance: <200ms per post (via batch inference)

3. **src/trading_bot/momentum/sentiment/sentiment_aggregator.py**: SentimentAggregator class
   - Purpose: Aggregate sentiment scores with 30-min rolling window (weighted by recency)
   - Methods:
     - `aggregate(scores: list[SentimentScore]) -> float`: Weighted average
     - `_weight_by_recency(scores: list[SentimentScore]) -> list[float]`: Exponential decay
   - Validation: Requires min 10 posts (return None if <10)
   - Formula: weighted_avg = Σ(score * weight) / Σ(weight), weight = e^(-minutes_ago / 10)

4. **src/trading_bot/momentum/sentiment/models.py**: SentimentPost and SentimentScore dataclasses
   - Purpose: Data models for sentiment analysis pipeline
   - Entities:
     - `SentimentPost`: text, author, timestamp, source (Twitter|Reddit), symbol
     - `SentimentScore`: symbol, score (-1.0 to +1.0), confidence (0-1), post_count, timestamp
   - Validation: __post_init__ checks (timestamp within 30 min, score in range)

5. **logs/sentiment-analysis.jsonl**: Structured log file
   - Purpose: Log sentiment scores for backtest validation (FR-007)
   - Events:
     - sentiment.analysis_started (symbol, timestamp, post_count)
     - sentiment.analysis_completed (symbol, score, confidence, duration_ms)
     - sentiment.api_error (source, error_type, symbol)
     - sentiment.model_loaded (model_name, load_duration_ms, memory_mb)
   - Format: JSONL (one JSON object per line, newline-delimited)

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Hetzner VPS (self-hosted Docker Compose, staging-prod model)
- Env vars: 8 new required variables (Twitter/Reddit API credentials, sentiment config)
- Breaking changes: No (backward-compatible field addition)
- Migration: No database migration needed (file-based storage)

**Build Commands**:
- Changed: `docker-compose build` (new dependencies in requirements.txt)
- New dependencies: transformers==4.35.0, torch==2.1.0, tweepy==4.14.0, praw==7.7.1
- Docker image size: +1.3GB (800MB PyTorch + 500MB FinBERT model)

**Environment Variables** (update .env):

**New Required Variables**:
```env
# Twitter API v2 Credentials
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here

# Reddit API Credentials
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=trading-bot:v1.0.0 (by /u/your_username)

# Sentiment Analysis Configuration
SENTIMENT_THRESHOLD=0.6         # Minimum score to trigger signal (0.0-1.0)
SENTIMENT_ENABLED=true          # Feature flag (true/false)
```

**Changed Variables**: None (new feature, no existing vars modified)

**Schema Update Required**: No (environment validation in MomentumConfig, not schema-based)

**Database Migrations**: N/A (no database, file-based logs only)

**Dry-run Required**: No (backward-compatible changes, feature flag for rollback)

**Reversible**: Yes (set SENTIMENT_ENABLED=false, bot continues news-only detection)

**Smoke Tests** (for manual deployment validation):

### Staging Smoke Tests
```bash
# 1. Bot starts without errors
docker-compose logs trading-bot | grep ERROR  # Should be empty

# 2. FinBERT model loads successfully
docker-compose logs trading-bot | grep "sentiment.model_loaded"
# Expected: {"event": "sentiment.model_loaded", "model_name": "ProsusAI/finbert", "load_duration_ms": 1200, ...}

# 3. Twitter/Reddit API credentials valid
docker-compose logs trading-bot | grep "sentiment.api_error" | grep "auth_failed"  # Should be empty

# 4. Sentiment analysis completes for test symbol
docker-compose exec trading-bot python -c "
import asyncio
from src.trading_bot.momentum.catalyst_detector import CatalystDetector
from src.trading_bot.momentum.config import MomentumConfig

async def test():
    config = MomentumConfig.from_env()
    detector = CatalystDetector(config)
    signals = await detector.scan(['AAPL'])
    assert len(signals) >= 0  # No errors
    print('Smoke test passed')

asyncio.run(test())
"
# Expected: "Smoke test passed"

# 5. Logs created and structured correctly
cat logs/sentiment-analysis.jsonl | jq .  # Should parse as valid JSON
```

**Platform Coupling**:
- Hetzner VPS: No changes (continues using Docker Compose deployment)
- Docker: New dependencies in requirements.txt, +1.3GB image size
- Dependencies: 4 new packages (transformers, torch, tweepy, praw)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- Backward compatibility: Existing code without sentiment_score continues working
- Graceful degradation: Sentiment failures don't crash bot (sentiment_score=None)
- Feature flag: SENTIMENT_ENABLED=false disables sentiment without code change
- API rate limits respected: Twitter 500k tweets/month, Reddit 100 req/min

**Staging Smoke Tests** (Given/When/Then):
```gherkin
Scenario: Sentiment analysis integration works end-to-end
  Given bot starts with SENTIMENT_ENABLED=true
  When CatalystDetector.scan() is called with symbol "AAPL"
  Then sentiment_score field is populated in CatalystEvent
    And response time is <3s
    And no errors logged
    And logs/sentiment-analysis.jsonl contains analysis_completed event

Scenario: Graceful degradation when Twitter API fails
  Given Twitter API returns 429 rate limit error
  When CatalystDetector.scan() is called
  Then sentiment_score is None (degraded mode)
    And bot continues with news-only detection
    And "sentiment.api_error" event logged with error_type="rate_limit"

Scenario: Feature flag disable works
  Given SENTIMENT_ENABLED=false in .env
  When bot starts
  Then sentiment analysis is skipped
    And sentiment_score is None for all signals
    And warning logged: "Sentiment analysis disabled via SENTIMENT_ENABLED=false"
```

**Rollback Plan**:
- Deploy IDs tracked in: specs/034-sentiment-analysis-integration/NOTES.md (Deployment Metadata section)
- Rollback commands:
  1. Quick rollback (no code change): `export SENTIMENT_ENABLED=false && docker-compose restart trading-bot` (~2 min)
  2. Code rollback: `git reset --hard <previous-commit> && docker-compose restart trading-bot` (~3 min)
  3. Full rollback: `git revert <commit-sha> && docker-compose rebuild && docker-compose restart` (~5 min)
- Special considerations: FinBERT model files (~500MB) remain in Docker image but not loaded if SENTIMENT_ENABLED=false

**Artifact Strategy** (build-once-deploy-many):
- Bot: Docker image `trading-bot:034-sentiment-<commit-sha>` (NOT :latest)
- Build in: Local development (docker-compose build)
- Deploy to staging: Manual (git pull + docker-compose build + docker-compose up)
- Promote to production: Manual approval after 24-48 hour paper trading validation
- Model caching: FinBERT model downloaded on first run, cached in Docker volume

---

## [INTEGRATION SCENARIOS]

See: quickstart.md for complete integration scenarios

**Summary**:
- Scenario 1: Initial setup - Install dependencies, configure API credentials, download FinBERT model
- Scenario 2: Validation - Run tests (unit + integration), type check, lint, verify logs
- Scenario 3: Manual testing - Test Twitter/Reddit fetching, FinBERT analysis, full catalyst detection
- Scenario 4: Docker deployment (VPS) - Build image, update .env, start bot, monitor logs
- Scenario 5: Rollback - Disable sentiment via SENTIMENT_ENABLED=false

---

## [TIMELINE ESTIMATE]

**Total Effort**: 20-40 hours (MVP: US1-US3, Enhancement: US4-US5)

**Phase Breakdown**:
- US1 (CatalystSignal extension): 8-16 hours (L effort)
  - Extend CatalystEvent dataclass: 2 hours
  - Integrate sentiment in CatalystDetector.scan(): 4 hours
  - Unit tests + integration tests: 8 hours
- US2 (SentimentFetcher): 4-8 hours (M effort)
  - Twitter API integration: 2 hours
  - Reddit API integration: 2 hours
  - Rate limit handling + tests: 4 hours
- US3 (SentimentAnalyzer): 4-8 hours (M effort)
  - FinBERT model loading: 2 hours
  - Batch inference implementation: 2 hours
  - Model caching + tests: 4 hours
- US4 (SentimentAggregator): 2-4 hours (S effort, optional)
  - 30-min rolling window: 1 hour
  - Recency weighting: 1 hour
  - Min 10 posts validation + tests: 2 hours
- US5 (Backtest validation): 8-16 hours (L effort, optional)
  - Backtest script: 4 hours
  - 90-day historical analysis: 8 hours
  - Win rate comparison: 4 hours

**MVP Strategy**: Ship US1-US3 first (16-32 hours), validate with paper trading for 1 week, then add US4-US5 if needed.

---

## [TESTING STRATEGY]

**Unit Tests** (target >80% coverage per constitution):
- test_sentiment_fetcher.py: Mock Twitter/Reddit APIs, verify post fetching, rate limit handling
- test_sentiment_analyzer.py: Mock FinBERT model, verify sentiment scoring, batch inference
- test_sentiment_aggregator.py: Test weighted averaging, recency weighting, min 10 posts validation
- test_sentiment_models.py: Test SentimentPost/SentimentScore validation, __post_init__ checks
- test_catalyst_detector_sentiment.py: Test CatalystDetector integration, graceful degradation

**Integration Tests**:
- test_sentiment_end_to_end.py: Full pipeline (fetch → analyze → aggregate → catalyst)
- test_api_error_handling.py: Simulate API failures (429 rate limit, auth failure, timeout)

**Manual Tests** (see quickstart.md):
- Twitter API: Fetch real tweets for AAPL, verify post count and content
- FinBERT: Analyze bullish/bearish posts, verify sentiment scores
- Full pipeline: Run CatalystDetector.scan() with sentiment, verify sentiment_score populated
- Graceful degradation: Disable APIs, verify sentiment_score=None and bot continues

**Performance Tests**:
- Sentiment analysis latency: Measure duration for 50 posts, verify <3s (NFR-001)
- FinBERT inference: Measure per-post inference, verify <200ms (NFR-004)
- Model caching: Verify model loads once, not per-analysis

---

## [RISKS & MITIGATIONS]

**Risk 1: FinBERT model download fails (ConnectionError)**
- Impact: Bot startup fails, sentiment unavailable
- Mitigation: Pre-download model during Docker build, cache in image
- Rollback: Set SENTIMENT_ENABLED=false, continue without sentiment

**Risk 2: Twitter/Reddit API rate limits exceeded**
- Impact: No sentiment data for some symbols
- Mitigation: Graceful degradation (sentiment_score=None), log rate limit errors
- Monitoring: Track API error rate in logs, alert if >5%

**Risk 3: Docker image too large (>3GB)**
- Impact: Slow deployments, VPS disk space issues
- Current: +1.3GB (total ~2.5GB)
- Mitigation: VPS has 20GB disk (sufficient), optimize with multi-stage Docker build if needed

**Risk 4: FinBERT inference slower than expected (>3s total)**
- Impact: Violates NFR-001 (<3s per symbol)
- Mitigation: Batch inference, model caching, skip sentiment if >5s
- Monitoring: Log duration_ms for each analysis, alert if P95 >3s

**Risk 5: Sentiment adds noise, reduces win rate**
- Impact: Feature degrades performance vs news-only
- Mitigation: Paper trading validation (1 week), A/B test in backtest (US5)
- Rollback: Set SENTIMENT_ENABLED=false if win rate drops >5%

---

## [SUCCESS CRITERIA]

**Phase 1 (MVP - US1-US3)**:
- ✅ CatalystEvent has sentiment_score field (Optional[float])
- ✅ SentimentFetcher fetches Twitter/Reddit posts (>10 posts for high-volume symbols)
- ✅ SentimentAnalyzer scores posts using FinBERT (<200ms per post)
- ✅ CatalystDetector.scan() populates sentiment_score
- ✅ Graceful degradation works (API failures → sentiment_score=None)
- ✅ Tests pass (>80% coverage)
- ✅ Docker deployment succeeds (+1.3GB image size acceptable)

**Phase 2 (Enhancement - US4-US5, optional)**:
- ✅ 30-min rolling average sentiment with recency weighting
- ✅ Backtest validates 10% win rate improvement claim
- ✅ Paper trading shows earlier detection (15-30 min ahead of news)

**Phase 3 (Production validation)**:
- ✅ Staging passes 24-48 hour paper trading (no crashes, >95% uptime)
- ✅ API error rate <5% (Twitter/Reddit rate limits respected)
- ✅ Sentiment analysis latency <3s (P95)
- ✅ Win rate improvement confirmed (production A/B test, 2-3 weeks)

---

## [REFERENCES]

- Spec: specs/034-sentiment-analysis-integration/spec.md
- Research: specs/034-sentiment-analysis-integration/research.md
- Data Model: specs/034-sentiment-analysis-integration/data-model.md
- Contracts: specs/034-sentiment-analysis-integration/contracts/sentiment-api.yaml
- Quickstart: specs/034-sentiment-analysis-integration/quickstart.md
- Constitution: .spec-flow/memory/constitution.md
- Project Architecture: docs/project/system-architecture.md
- Tech Stack: docs/project/tech-stack.md
- Deployment Strategy: docs/project/deployment-strategy.md
