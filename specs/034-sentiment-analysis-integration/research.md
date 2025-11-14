# Research & Discovery: 034-sentiment-analysis-integration

## Project Documentation Context

**Source**: `docs/project/` (8 project-level documents)

### Overview (from overview.md)
- **Vision**: Automated momentum trading bot with risk management for retail traders
- **Target Users**: Solo traders using day trading strategies (momentum, breakouts)
- **Success Metrics**: Win rate >50%, profit factor >1.5, max drawdown <-10%
- **Scope Boundaries**: Single-account trading, momentum strategies only, no swing trading

### System Architecture (from system-architecture.md)
- **Components**: Modular monolith with service separation (Docker Compose)
- **Integration Points**: Robinhood (execution), Alpaca (market data), Polygon.io (order flow), OpenAI (LLM)
- **Data Flows**: Bot → Scanner → Detector → Risk Manager → Order Manager → Robinhood
- **Constraints**: File-based logs (JSONL), no traditional database, single-process architecture

### Tech Stack (from tech-stack.md)
- **Frontend**: N/A (CLI dashboard via rich library)
- **Backend**: Python 3.11, FastAPI 0.104.1, Uvicorn
- **Database**: File-based logs (JSONL), no traditional database
- **Deployment**: Docker Compose on self-hosted VPS (Hetzner CX11)

### Data Architecture (from data-architecture.md)
- **Existing Entities**: MomentumSignal, CatalystEvent, PreMarketMover, BullFlagPattern
- **Relationships**: MomentumSignal contains CatalystEvent details in `details` dict
- **Naming Conventions**: snake_case for Python, PascalCase for classes
- **Migration Strategy**: Backward-compatible field additions (dataclass with Optional fields)

### API Strategy (from api-strategy.md)
- **API Style**: REST API via FastAPI (for future LLM integration)
- **Auth**: Environment variables for API keys (no user auth, single bot instance)
- **Versioning**: Not needed (internal services only)
- **Error Format**: Python exceptions with structured logging (JSONL)
- **Rate Limiting**: Managed by external APIs (Twitter 500k/month, Reddit 100 req/min)

### Capacity Planning (from capacity-planning.md)
- **Current Scale**: Micro tier (single account, <100 trades/day)
- **Performance Targets**: API response <500ms, bot loop <30s
- **Resource Limits**: 2GB RAM (Hetzner CX11), 20GB disk
- **Cost Constraints**: <$150/mo total (VPS + Polygon.io + OpenAI)

### Deployment Strategy (from deployment-strategy.md)
- **Deployment Model**: staging-prod (paper trading → live trading)
- **Platform**: Self-hosted VPS (Hetzner CX11)
- **CI/CD Pipeline**: Manual deployment (git pull + docker-compose restart)
- **Environments**: Local (dev), Staging (paper trading), Production (live trading)

### Development Workflow (from development-workflow.md)
- **Git Workflow**: Feature branches → main (no PR process, solo developer)
- **Testing Strategy**: pytest (unit + integration), target >80% coverage
- **Code Style**: ruff (linting), mypy (type checking)
- **Definition of Done**: Tests pass, type check passes, paper trading validates 24-48 hours

---

## Research Decisions

### Decision 1: Piggyback CatalystDetector architecture
- **Decision**: Extend existing `CatalystDetector.scan()` method to add sentiment analysis
- **Rationale**: Spec explicitly states "PIGGYBACK existing CatalystDetector.scan() - add sentiment_score field to CatalystSignal"
- **Alternatives**:
  - Create separate SentimentAnalyzer service (rejected: spec requires piggyback)
  - Parallel sentiment scanning (rejected: increases complexity, spec wants integration)
- **Source**: spec.md line 107, NOTES.md line 12

### Decision 2: Use FinBERT via Hugging Face Transformers
- **Decision**: Use ProsusAI/finbert pretrained model from Hugging Face Hub
- **Rationale**:
  - Spec requirement FR-002: "System MUST analyze post sentiment using FinBERT model"
  - No fine-tuning needed (assumption 2: pretrained model sufficiently accurate)
  - Standard Hugging Face library (transformers) widely used, well-documented
- **Alternatives**:
  - Fine-tune FinBERT on custom data (rejected: out of scope, assumption says pretrained sufficient)
  - Use TextBlob/VADER (rejected: spec requires FinBERT specifically)
  - Use OpenAI sentiment API (rejected: adds cost, spec requires FinBERT)
- **Source**: spec.md line 138, tech-stack.md (no existing NLP library)

### Decision 3: Twitter/Reddit API integration with graceful degradation
- **Decision**: Use official Twitter API v2 (tweepy) and Reddit API (praw) with fallback to news-only
- **Rationale**:
  - FR-001: "System MUST fetch social media posts (Twitter/Reddit) for a given symbol"
  - NFR-005: "Graceful degradation: System MUST continue news-only detection when sentiment unavailable"
  - Edge cases spec: Handle Twitter 429 rate limit, Reddit API downtime, missing credentials
- **Alternatives**:
  - Scrape Twitter/Reddit (rejected: violates ToS, unreliable)
  - Use premium Twitter API (rejected: cost, spec mentions free tier)
  - Only use Reddit (rejected: spec requires both)
- **Source**: spec.md line 137-147, deployment considerations line 190-197

### Decision 4: 30-min rolling window aggregation with recency weighting
- **Decision**: Aggregate sentiment scores using weighted average (recent posts weighted higher)
- **Rationale**:
  - FR-004: "System MUST aggregate sentiment scores using 30-min rolling window (weighted by recency)"
  - US4: "30-min rolling average sentiment to filter out noise"
  - Momentum trading requires recent signals (15-30 min ahead of news)
- **Alternatives**:
  - Simple average (rejected: spec requires recency weighting)
  - Exponential moving average (rejected: more complex, spec says weighted average)
  - Median (rejected: spec says average)
- **Source**: spec.md line 140, user story US4 line 46-49

### Decision 5: Feature flag for production rollback
- **Decision**: Add `SENTIMENT_ENABLED` environment variable (default: true)
- **Rationale**:
  - Rollback considerations line 240: "Feature flag: Set SENTIMENT_ENABLED=false to disable without code changes"
  - Safety-first principle (constitution §Safety_First)
  - Easy rollback without redeployment
- **Alternatives**:
  - No feature flag (rejected: harder rollback, spec requires easy disable)
  - Config file flag (rejected: env var easier to change on VPS)
- **Source**: spec.md line 198, constitution.md line 12

### Decision 6: JSONL structured logging for backtest validation
- **Decision**: Log all sentiment scores to `logs/sentiment-analysis.jsonl`
- **Rationale**:
  - FR-007: "System MUST log sentiment analysis results to logs/sentiment-analysis.jsonl for backtesting"
  - Existing pattern: logs/trades.jsonl, logs/performance-alerts.jsonl
  - Data architecture: File-based storage (no database)
- **Alternatives**:
  - Database storage (rejected: project has no database, file-based only)
  - CSV logging (rejected: JSONL standard for this project)
- **Source**: spec.md line 143, system-architecture.md line 447-454

### Decision 7: PyTorch dependency and Docker image impact
- **Decision**: Accept +1.3GB Docker image size (+800MB PyTorch, +500MB FinBERT model)
- **Rationale**:
  - Spec deployment considerations line 177-179: "PyTorch dependency (transformers library requires torch, adds ~800MB to Docker image)"
  - VPS capacity: 20GB disk, 2GB RAM (sufficient for model loading)
  - Trade-off: Larger image vs ML capability (required for feature)
- **Alternatives**:
  - ONNX runtime (rejected: more complex, not needed for MVP)
  - Remote inference API (rejected: adds latency + cost)
- **Source**: spec.md line 177-179, capacity-planning.md (20GB disk available)

### Decision 8: Model caching strategy for <200ms inference
- **Decision**: Load FinBERT model once at startup, reuse for all analyses
- **Rationale**:
  - NFR-004: "FinBERT model inference MUST complete in <200ms per post"
  - US7: "Cache FinBERT model in memory to avoid loading latency (2s → 200ms)"
  - Constitution §Performance: Fast iteration important
- **Alternatives**:
  - Load model per analysis (rejected: 2s latency unacceptable per spec)
  - Lazy loading on first use (rejected: spec wants <200ms from startup)
- **Source**: spec.md line 152, user story US7 line 62-65

---

## Components to Reuse (7 components)

1. **src/trading_bot/momentum/catalyst_detector.py** - CatalystDetector class
   - **Reuse**: Extend `scan()` method to call SentimentAnalyzer, add sentiment_score to CatalystEvent
   - **Pattern**: Async method, graceful degradation, retry logic via @with_retry
   - **Lines**: 31-100 (class structure, scan method signature)

2. **src/trading_bot/momentum/schemas/momentum_signal.py** - MomentumSignal and CatalystEvent dataclasses
   - **Reuse**: Add sentiment_score field to CatalystEvent (Optional[float], default None)
   - **Pattern**: Frozen dataclasses with __post_init__ validation
   - **Lines**: 54-121 (MomentumSignal, CatalystEvent definitions)

3. **src/trading_bot/error_handling/retry.py** - @with_retry decorator
   - **Reuse**: Apply to Twitter/Reddit API calls (handles 429 rate limits, timeouts)
   - **Pattern**: Exponential backoff with jitter, callback support
   - **Lines**: 30-50 (decorator signature, RetryPolicy)

4. **src/trading_bot/momentum/logging/momentum_logger.py** - MomentumLogger class
   - **Reuse**: Log sentiment analysis events (sentiment.analysis_started, sentiment.api_error)
   - **Pattern**: Structured JSONL logging with thread safety
   - **Found**: Grep result shows existing momentum logger

5. **src/trading_bot/momentum/config.py** - MomentumConfig dataclass
   - **Reuse**: Add sentiment API credentials (TWITTER_API_KEY, REDDIT_CLIENT_ID, etc.)
   - **Pattern**: Load from environment variables via `from_env()` classmethod
   - **Assumption**: Based on catalyst_detector.py line 63 usage pattern

6. **src/trading_bot/momentum/validation.py** - validate_symbols() function
   - **Reuse**: Validate symbol input before fetching social posts
   - **Pattern**: Raises ValueError for invalid symbols
   - **Lines**: Used in catalyst_detector.py line 99

7. **src/trading_bot/logging/structured_logger.py** - Structured logging utilities
   - **Reuse**: JSONL file writing, log rotation patterns
   - **Pattern**: Append-only writes, JSON serialization
   - **Found**: Grep result shows existing structured logger

---

## New Components Needed (5 components)

1. **src/trading_bot/momentum/sentiment/sentiment_fetcher.py** - SentimentFetcher class
   - **Purpose**: Fetch Twitter/Reddit posts for a symbol using official APIs
   - **Dependencies**: tweepy (Twitter API v2), praw (Reddit API)
   - **Methods**:
     - `fetch_twitter_posts(symbol: str, minutes: int = 30) -> list[SentimentPost]`
     - `fetch_reddit_posts(symbol: str, minutes: int = 30) -> list[SentimentPost]`
     - `fetch_all(symbol: str) -> list[SentimentPost]` (combines both sources)
   - **Error Handling**: @with_retry for rate limits, graceful degradation for auth failures

2. **src/trading_bot/momentum/sentiment/sentiment_analyzer.py** - SentimentAnalyzer class
   - **Purpose**: Score posts using FinBERT model, return sentiment probability scores
   - **Dependencies**: transformers (Hugging Face), torch (PyTorch)
   - **Methods**:
     - `__init__()`: Load FinBERT model once at startup
     - `analyze_post(text: str) -> dict[str, float]` (returns {negative, neutral, positive})
     - `analyze_batch(posts: list[str]) -> list[dict[str, float]]` (batch inference)
   - **Caching**: Model loaded once, stored as instance variable

3. **src/trading_bot/momentum/sentiment/sentiment_aggregator.py** - SentimentAggregator class
   - **Purpose**: Aggregate sentiment scores with 30-min rolling window (weighted by recency)
   - **Methods**:
     - `aggregate(scores: list[SentimentScore]) -> float` (returns -1.0 to +1.0)
     - `_weight_by_recency(scores: list[SentimentScore]) -> list[float]` (exponential decay)
   - **Validation**: Requires min 10 posts (per US4)

4. **src/trading_bot/momentum/sentiment/models.py** - SentimentPost and SentimentScore dataclasses
   - **Purpose**: Data models for sentiment analysis pipeline
   - **Entities**:
     - `SentimentPost`: text, author, timestamp, source (Twitter|Reddit), symbol
     - `SentimentScore`: symbol, score (-1.0 to +1.0), confidence (0-1), post_count, timestamp
   - **Validation**: __post_init__ checks (timestamp within 30 min, score in range)

5. **logs/sentiment-analysis.jsonl** - Structured log file
   - **Purpose**: Log sentiment scores for backtest validation (FR-007)
   - **Events**:
     - sentiment.analysis_started (symbol, timestamp, post_count)
     - sentiment.analysis_completed (symbol, score, confidence, duration_ms)
     - sentiment.api_error (source, error_type, symbol)
     - sentiment.model_loaded (model_name, load_duration_ms, memory_mb)
   - **Pattern**: Append-only JSONL, same format as logs/trades.jsonl

---

## Unknowns & Questions

None - all technical questions resolved

**Resolved during research**:
- ✅ Tech stack decision: FinBERT via Hugging Face (spec requirement)
- ✅ Integration point: Extend CatalystDetector.scan() (spec PIGGYBACK requirement)
- ✅ Data model: Add Optional[float] sentiment_score to CatalystEvent (backward compatible)
- ✅ Deployment: Docker image +1.3GB acceptable (VPS has 20GB disk)
- ✅ Performance: Model caching reduces latency from 2s → <200ms (spec NFR-004)
- ✅ API credentials: 8 new env vars required (spec line 190-197)
- ✅ Rollback: Feature flag SENTIMENT_ENABLED=false (spec line 240)
