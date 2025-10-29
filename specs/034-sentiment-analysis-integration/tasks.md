# Tasks: Sentiment Analysis Integration

## [CODEBASE REUSE ANALYSIS]
Scanned: src/trading_bot/momentum/**/*.py, tests/unit/services/momentum/**/*.py

**[EXISTING - REUSE]**
- ✅ CatalystDetector (src/trading_bot/momentum/catalyst_detector.py) - Extend scan() method
- ✅ CatalystEvent (src/trading_bot/momentum/schemas/momentum_signal.py) - Add sentiment_score field
- ✅ MomentumConfig (src/trading_bot/momentum/config.py) - Add sentiment API credentials
- ✅ MomentumLogger (src/trading_bot/momentum/logging/momentum_logger.py) - Log sentiment events
- ✅ @with_retry (src/trading_bot/error_handling/retry.py) - API error handling
- ✅ validate_symbols (src/trading_bot/momentum/validation.py) - Symbol validation
- ✅ Test patterns (tests/unit/services/momentum/test_catalyst_detector.py) - Follow existing test structure

**[NEW - CREATE]**
- 🆕 SentimentFetcher (no existing pattern - Twitter/Reddit API integration)
- 🆕 SentimentAnalyzer (no existing pattern - FinBERT model loading)
- 🆕 SentimentAggregator (no existing pattern - 30-min rolling window)
- 🆕 SentimentPost/SentimentScore models (follow pattern: src/trading_bot/momentum/schemas/momentum_signal.py)
- 🆕 logs/sentiment-analysis.jsonl (follow pattern: existing JSONL structured logs)

---

## [DEPENDENCY GRAPH]
Story completion order:
1. Phase 1: Setup (T001-T003) - Project dependencies and configuration
2. Phase 2: Foundational (T004-T007) - Data models and module structure (blocks all stories)
3. Phase 3: US2 [P1] - Twitter/Reddit API fetching (T008-T013, independent)
4. Phase 4: US3 [P1] - FinBERT sentiment analysis (T014-T019, depends on US2 models)
5. Phase 5: US4 [P2] - 30-min rolling aggregation (T020-T023, depends on US3)
6. Phase 6: US1 [P1] - CatalystDetector integration (T024-T029, depends on US2-US4)
7. Phase 7: Polish & Deployment (T030-T040) - Error handling, logs, deployment prep

---

## [PARALLEL EXECUTION OPPORTUNITIES]
- Phase 3 (US2): T009, T010, T011 (Twitter/Reddit fetchers are independent)
- Phase 4 (US3): T015, T016, T017 (FinBERT tests can run parallel)
- Phase 6 (US1): T025, T026 (CatalystDetector unit/integration tests)
- Phase 7 (Polish): T031, T032, T034, T035 (independent deployment tasks)

---

## [IMPLEMENTATION STRATEGY]
**MVP Scope**: Phase 3-6 (US1-US3 + partial US4)
**Incremental delivery**: US2 → US3 → US4 → US1 → staging validation
**Testing approach**: TDD required (>80% coverage per constitution)

---

## Phase 1: Setup

- [ ] T001 Install Python dependencies from plan.md
  - Files: requirements.txt
  - Libraries: transformers==4.35.0, torch==2.1.0, tweepy==4.14.0, praw==7.7.1
  - From: plan.md [ARCHITECTURE DECISIONS]

- [ ] T002 [P] Create sentiment module directory structure
  - Files: src/trading_bot/momentum/sentiment/__init__.py
  - Files: src/trading_bot/momentum/sentiment/models.py
  - Files: src/trading_bot/momentum/sentiment/sentiment_fetcher.py
  - Files: src/trading_bot/momentum/sentiment/sentiment_analyzer.py
  - Files: src/trading_bot/momentum/sentiment/sentiment_aggregator.py
  - Pattern: src/trading_bot/momentum/ (existing module structure)
  - From: plan.md [STRUCTURE]

- [ ] T003 [P] Create test directory structure for sentiment module
  - Files: tests/unit/services/momentum/sentiment/__init__.py
  - Files: tests/integration/momentum/sentiment/__init__.py
  - Pattern: tests/unit/services/momentum/ (existing test structure)
  - From: plan.md [STRUCTURE]

---

## Phase 2: Foundational (blocking prerequisites)

**Goal**: Data models and configuration that block all user stories

- [ ] T004 Create SentimentPost dataclass in src/trading_bot/momentum/sentiment/models.py
  - Fields: text (str), author (str), timestamp (datetime), source (str), symbol (str)
  - Validation: Non-empty text, source in ("Twitter", "Reddit"), timestamp within 30 min, valid symbol
  - REUSE: BaseModel pattern from src/trading_bot/momentum/schemas/momentum_signal.py
  - Pattern: CatalystEvent dataclass with __post_init__ validation
  - From: data-model.md SentimentPost entity

- [ ] T005 [P] Create SentimentScore dataclass in src/trading_bot/momentum/sentiment/models.py
  - Fields: symbol (str), score (float), confidence (float), post_count (int), timestamp (datetime)
  - Validation: score in [-1.0, 1.0], confidence in [0.0, 1.0], post_count >= 10
  - REUSE: BaseModel pattern from src/trading_bot/momentum/schemas/momentum_signal.py
  - Pattern: CatalystEvent dataclass with __post_init__ validation
  - From: data-model.md SentimentScore entity

- [ ] T006 Add sentiment_score field to CatalystEvent in src/trading_bot/momentum/schemas/momentum_signal.py
  - Field: sentiment_score: float | None = None
  - Validation: If not None, must be in range [-1.0, 1.0]
  - Pattern: Existing CatalystEvent __post_init__ validation
  - From: data-model.md CatalystEvent (Extended) entity

- [ ] T007 [P] Extend MomentumConfig with sentiment credentials in src/trading_bot/momentum/config.py
  - New fields: twitter_api_key, twitter_api_secret, twitter_bearer_token, reddit_client_id, reddit_client_secret, reddit_user_agent, sentiment_threshold (default 0.6), sentiment_enabled (default True)
  - Pattern: Existing MomentumConfig fields with from_env() classmethod
  - From: plan.md [CI/CD IMPACT] Environment Variables

---

## Phase 3: User Story 2 [P1] - Fetch Twitter/Reddit posts

**Story Goal**: Fetch social media posts for sentiment analysis

**Independent Test Criteria**:
- [ ] Twitter API returns last 30 min of posts for symbol
- [ ] Reddit API returns last 30 min of posts for symbol
- [ ] Graceful degradation on API rate limit (429 error)

### Tests

- [ ] T008 [P] [US2] Write unit test: SentimentFetcher initializes Twitter/Reddit clients
  - File: tests/unit/services/momentum/sentiment/test_sentiment_fetcher.py
  - Given-When-Then: Given valid API credentials, When SentimentFetcher.__init__, Then clients initialized
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥80% (new code must be 100%)

- [ ] T009 [P] [US2] Write unit test: fetch_twitter_posts returns SentimentPost list
  - File: tests/unit/services/momentum/sentiment/test_sentiment_fetcher.py
  - Given-When-Then: Given mocked Twitter API, When fetch_twitter_posts("AAPL"), Then returns list[SentimentPost]
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py (mock httpx responses)
  - Coverage: ≥80%

- [ ] T010 [P] [US2] Write unit test: fetch_reddit_posts returns SentimentPost list
  - File: tests/unit/services/momentum/sentiment/test_sentiment_fetcher.py
  - Given-When-Then: Given mocked Reddit API, When fetch_reddit_posts("AAPL"), Then returns list[SentimentPost]
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥80%

- [ ] T011 [P] [US2] Write unit test: fetch_all combines Twitter and Reddit posts
  - File: tests/unit/services/momentum/sentiment/test_sentiment_fetcher.py
  - Given-When-Then: Given both APIs return posts, When fetch_all("AAPL"), Then combined list returned
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥80%

### Implementation

- [ ] T012 [US2] Implement SentimentFetcher.__init__ in src/trading_bot/momentum/sentiment/sentiment_fetcher.py
  - Method: Initialize tweepy Client and praw Reddit instances
  - REUSE: MomentumConfig for credentials
  - Pattern: CatalystDetector.__init__ (config-based initialization)
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #1

- [ ] T013 [US2] Implement fetch_twitter_posts method in src/trading_bot/momentum/sentiment/sentiment_fetcher.py
  - Method: fetch_twitter_posts(symbol: str, minutes: int = 30) -> list[SentimentPost]
  - Use tweepy.Client.search_recent_tweets with query "$SYMBOL OR SYMBOL"
  - REUSE: @with_retry for rate limit handling
  - Pattern: CatalystDetector.scan() async method structure
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #1

- [ ] T014 [US2] Implement fetch_reddit_posts method in src/trading_bot/momentum/sentiment/sentiment_fetcher.py
  - Method: fetch_reddit_posts(symbol: str, minutes: int = 30) -> list[SentimentPost]
  - Use praw.subreddit("wallstreetbets").search with query "SYMBOL"
  - REUSE: @with_retry for rate limit handling
  - Pattern: CatalystDetector.scan() async method structure
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #1

---

## Phase 4: User Story 3 [P1] - Score posts with FinBERT

**Story Goal**: Analyze sentiment using FinBERT model

**Independent Test Criteria**:
- [ ] FinBERT model loads successfully at startup
- [ ] analyze_post returns sentiment probabilities (negative, neutral, positive)
- [ ] Batch inference completes in <200ms per post average

### Tests

- [ ] T015 [P] [US3] Write unit test: SentimentAnalyzer loads FinBERT model
  - File: tests/unit/services/momentum/sentiment/test_sentiment_analyzer.py
  - Given-When-Then: Given FinBERT available, When SentimentAnalyzer.__init__, Then model loaded
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥80%

- [ ] T016 [P] [US3] Write unit test: analyze_post returns sentiment scores
  - File: tests/unit/services/momentum/sentiment/test_sentiment_analyzer.py
  - Given-When-Then: Given bullish text, When analyze_post("AAPL to the moon!"), Then positive score >0.5
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥80%

- [ ] T017 [P] [US3] Write unit test: analyze_batch processes multiple posts
  - File: tests/unit/services/momentum/sentiment/test_sentiment_analyzer.py
  - Given-When-Then: Given 50 posts, When analyze_batch(posts), Then returns 50 sentiment scores
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥80%

### Implementation

- [ ] T018 [US3] Implement SentimentAnalyzer.__init__ in src/trading_bot/momentum/sentiment/sentiment_analyzer.py
  - Method: Load FinBERT model from Hugging Face Hub (ProsusAI/finbert)
  - Cache model instance (singleton pattern)
  - Log model loading time and memory usage
  - Pattern: Service initialization with caching
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #2

- [ ] T019 [US3] Implement analyze_post method in src/trading_bot/momentum/sentiment/sentiment_analyzer.py
  - Method: analyze_post(text: str) -> dict[str, float] (returns {negative, neutral, positive})
  - Use FinBERT tokenizer + model inference
  - REUSE: Error handling patterns
  - Pattern: Async method with error handling
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #2

- [ ] T020 [US3] Implement analyze_batch method in src/trading_bot/momentum/sentiment/sentiment_analyzer.py
  - Method: analyze_batch(posts: list[str]) -> list[dict[str, float]]
  - Batch inference for performance (<200ms per post amortized)
  - Pattern: Batch processing for efficiency
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #2

---

## Phase 5: User Story 4 [P2] - 30-min rolling average sentiment

**Story Goal**: Aggregate sentiment scores with recency weighting

**Independent Test Criteria**:
- [ ] Aggregator returns None if <10 posts
- [ ] Recent posts weighted 2x older posts (exponential decay)
- [ ] Aggregation completes in <500ms

### Tests

- [ ] T021 [P] [US4] Write unit test: aggregate returns None if post_count <10
  - File: tests/unit/services/momentum/sentiment/test_sentiment_aggregator.py
  - Given-When-Then: Given 5 posts, When aggregate(scores), Then returns None
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥80%

- [ ] T022 [P] [US4] Write unit test: aggregate applies exponential recency weighting
  - File: tests/unit/services/momentum/sentiment/test_sentiment_aggregator.py
  - Given-When-Then: Given 10 posts (recent more bullish), When aggregate(scores), Then weighted avg >simple avg
  - Pattern: tests/unit/services/momentum/test_catalyst_detector.py
  - Coverage: ≥80%

### Implementation

- [ ] T023 [US4] Implement aggregate method in src/trading_bot/momentum/sentiment/sentiment_aggregator.py
  - Method: aggregate(scores: list[SentimentScore]) -> float | None
  - Formula: weighted_avg = Σ(score * weight) / Σ(weight), weight = e^(-minutes_ago / 10)
  - Validation: Requires min 10 posts (return None if <10)
  - Pattern: Aggregation logic with validation
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #3

- [ ] T024 [US4] Implement _weight_by_recency helper in src/trading_bot/momentum/sentiment/sentiment_aggregator.py
  - Method: _weight_by_recency(scores: list[SentimentScore]) -> list[float]
  - Exponential decay: recent posts weighted higher
  - Pattern: Private helper method
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #3

---

## Phase 6: User Story 1 [P1] - Integrate sentiment into CatalystDetector

**Story Goal**: Add sentiment scores to catalyst signals

**Independent Test Criteria**:
- [ ] CatalystEvent has sentiment_score field populated
- [ ] Graceful degradation when sentiment unavailable (sentiment_score=None)
- [ ] End-to-end pipeline completes in <3s

### Tests

- [ ] T025 [P] [US1] Write unit test: CatalystDetector.scan populates sentiment_score
  - File: tests/unit/services/momentum/test_catalyst_detector.py (extend existing)
  - Given-When-Then: Given sentiment available, When scan(["AAPL"]), Then sentiment_score populated
  - Pattern: Existing test_catalyst_detector.py tests
  - Coverage: ≥80%

- [ ] T026 [P] [US1] Write unit test: CatalystDetector gracefully degrades on sentiment failure
  - File: tests/unit/services/momentum/test_catalyst_detector.py (extend existing)
  - Given-When-Then: Given sentiment API fails, When scan(["AAPL"]), Then sentiment_score=None
  - Pattern: Existing graceful degradation tests
  - Coverage: ≥80%

- [ ] T027 [US1] Write integration test: End-to-end sentiment pipeline
  - File: tests/integration/momentum/sentiment/test_sentiment_end_to_end.py
  - Test: Full pipeline (fetch → analyze → aggregate → catalyst)
  - Real data: Mock APIs with realistic responses
  - Pattern: tests/integration/momentum/test_catalyst_detector_integration.py
  - Coverage: ≥90% critical path

### Implementation

- [ ] T028 [US1] Extend CatalystDetector.scan to call sentiment pipeline in src/trading_bot/momentum/catalyst_detector.py
  - Integration point: After news fetch, before return
  - Call: SentimentFetcher.fetch_all → SentimentAnalyzer.analyze_batch → SentimentAggregator.aggregate
  - Populate: CatalystEvent.sentiment_score field
  - REUSE: Existing @with_retry, graceful degradation patterns
  - Pattern: Existing CatalystDetector.scan() method structure
  - From: plan.md [EXISTING INFRASTRUCTURE - REUSE] #1

- [ ] T029 [US1] Add sentiment feature flag check in CatalystDetector.scan
  - Check: MomentumConfig.sentiment_enabled (from env SENTIMENT_ENABLED)
  - If False: Skip sentiment analysis, set sentiment_score=None
  - Log: Warning "Sentiment analysis disabled via SENTIMENT_ENABLED=false"
  - Pattern: Feature flag pattern
  - From: plan.md [ARCHITECTURE DECISIONS] Feature Flag Rollback

---

## Phase 7: Polish & Cross-Cutting Concerns

### Error Handling & Resilience

- [ ] T030 Add sentiment-specific error handling in src/trading_bot/momentum/sentiment/sentiment_fetcher.py
  - Handle: Twitter 429 rate limit → return empty list, log error
  - Handle: Reddit auth failure → return empty list, log error
  - Handle: Network timeout → retry with @with_retry, fallback to empty list
  - REUSE: @with_retry decorator from src/trading_bot/error_handling/retry.py
  - Pattern: CatalystDetector error handling
  - From: plan.md [SECURITY] Rate Limiting

- [ ] T031 [P] Add model loading error handling in src/trading_bot/momentum/sentiment/sentiment_analyzer.py
  - Handle: FinBERT model download fails → log error, set sentiment_enabled=False
  - Handle: CUDA OOM error → fallback to CPU inference
  - Handle: Model inference timeout → skip sentiment for that symbol
  - Pattern: Graceful degradation
  - From: plan.md [RISKS & MITIGATIONS] Risk 1

- [ ] T032 [P] Create sentiment structured logger in src/trading_bot/momentum/sentiment/__init__.py
  - Events: sentiment.analysis_started, sentiment.analysis_completed, sentiment.api_error, sentiment.model_loaded
  - File: logs/sentiment-analysis.jsonl
  - REUSE: MomentumLogger pattern from src/trading_bot/momentum/logging/momentum_logger.py
  - Pattern: JSONL structured logging
  - From: plan.md [NEW INFRASTRUCTURE - CREATE] #5

### Deployment Preparation

- [ ] T033 Update .env.example with sentiment environment variables
  - Variables: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_BEARER_TOKEN, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, SENTIMENT_THRESHOLD, SENTIMENT_ENABLED
  - Pattern: Existing .env.example format
  - From: plan.md [CI/CD IMPACT] Environment Variables

- [ ] T034 [P] Add sentiment credentials validation in src/trading_bot/momentum/config.py
  - Validation: If sentiment_enabled=True, require Twitter/Reddit credentials
  - Log: Warning if credentials missing, auto-disable sentiment
  - Pattern: MomentumConfig.__post_init__ validation
  - From: plan.md [SECURITY] Authentication Strategy

- [ ] T035 [P] Create Dockerfile multi-stage build optimization
  - Optimize: PyTorch +800MB, FinBERT +500MB → minimize final image size
  - Cache: FinBERT model in Docker volume (not rebuilt every time)
  - Pattern: Multi-stage Docker build
  - From: plan.md [ARCHITECTURE DECISIONS] Docker Image Impact

- [ ] T036 Add health check endpoint for sentiment service
  - Endpoint: /api/health/sentiment (if API exists)
  - Check: FinBERT model loaded, Twitter/Reddit API reachable
  - Return: { status: "ok", model_loaded: true, apis: {...} }
  - Pattern: Existing health check patterns
  - From: plan.md [CI/CD IMPACT]

- [ ] T037 [P] Create smoke tests for staging validation
  - File: tests/smoke/test_sentiment_smoke.py
  - Tests: Bot starts, FinBERT loads, APIs auth valid, sentiment analysis completes
  - Pattern: Quick validation tests (<90s total)
  - From: plan.md [DEPLOYMENT ACCEPTANCE] Staging Smoke Tests

- [ ] T038 Document rollback procedure in specs/034-sentiment-analysis-integration/NOTES.md
  - Commands: Quick rollback (SENTIMENT_ENABLED=false), code rollback, full rollback
  - Feature flag: Kill switch (SENTIMENT_ENABLED=0)
  - Database: N/A (no database changes)
  - From: plan.md [DEPLOYMENT ACCEPTANCE] Rollback Plan

- [ ] T039 [P] Add sentiment analysis metrics logging
  - Metrics: duration_ms per analysis, post_count per symbol, API error rate, model inference latency
  - Log to: logs/sentiment-analysis.jsonl
  - Pattern: Performance metrics logging
  - From: plan.md [PERFORMANCE TARGETS]

- [ ] T040 Update project documentation with sentiment feature
  - Files: README.md (feature description), docs/features/sentiment-analysis.md (detailed guide)
  - Include: Setup instructions, API credential configuration, feature flag usage
  - Pattern: Existing feature documentation
  - From: plan.md [REFERENCES]
