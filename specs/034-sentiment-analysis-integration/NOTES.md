# Feature: sentiment-analysis-integration

## Overview
Integrate sentiment analysis using FinBERT model to score social media posts (Twitter/Reddit) for bullish/bearish sentiment, enabling earlier detection of momentum signals.

## Research Findings

**Finding 1**: Existing CatalystDetector implementation in src/trading_bot/momentum/catalyst_detector.py
- Source: Code inspection (catalyst_detector.py:1-536)
- Current implementation: News-driven catalyst detection using Alpaca News API
- Returns MomentumSignal objects with signal_type=CATALYST
- Decision: PIGGYBACK opportunity - add sentiment_score field to existing CatalystSignal

**Finding 2**: Project uses Python 3.11 with FastAPI and async architecture
- Source: docs/project/tech-stack.md
- Backend: Python 3.11, FastAPI 0.104.1, Uvicorn
- Market data: Alpaca Markets API (primary), Polygon.io (order flow)
- Backtesting: backtrader 1.9.78.123
- Decision: Use Python libraries for FinBERT integration (Hugging Face transformers)

**Finding 3**: System architecture is modular monolith with file-based storage
- Source: docs/project/system-architecture.md
- Data storage: JSON Lines (JSONL) files, no traditional database
- Components: momentum/, patterns/, risk_management/, order_management/
- Decision: Sentiment analysis fits in momentum/ directory alongside catalyst_detector.py

**Finding 4**: Deployment model is staging-prod (paper trading before live)
- Source: docs/project/deployment-strategy.md
- Staging: Paper trading on VPS validates changes
- Production: Live trading with real money
- Decision: Feature requires deployment impact assessment (new API credentials, config)

## System Components Analysis
[Populated during system component check]

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-29

## Last Updated
2025-10-29T00:00:00Z

## Feature Classification
- UI screens: false
- Improvement: true
- Measurable: true
- Deployment impact: true

## Phase 2: Tasks (2025-10-29 01:37)

**Summary**:
- Total tasks: 40
- User story tasks: 22 (US1: 5, US2: 7, US3: 6, US4: 4)
- Parallel opportunities: 21 tasks marked [P]
- Setup tasks: 3
- Task file: specs/034-sentiment-analysis-integration/tasks.md

**Task Breakdown**:
- Phase 1 (Setup): 3 tasks - Dependencies, module structure, test structure
- Phase 2 (Foundational): 4 tasks - Data models (SentimentPost, SentimentScore), CatalystEvent extension, MomentumConfig
- Phase 3 (US2 - Fetching): 7 tasks - Twitter/Reddit API integration with tests
- Phase 4 (US3 - Analysis): 7 tasks - FinBERT model loading and inference with tests
- Phase 5 (US4 - Aggregation): 4 tasks - 30-min rolling window with recency weighting
- Phase 6 (US1 - Integration): 5 tasks - CatalystDetector.scan() extension with E2E tests
- Phase 7 (Polish): 10 tasks - Error handling, logging, deployment prep, documentation

**Key Decisions**:
1. Story sequencing: US2 (fetch) → US3 (analyze) → US4 (aggregate) → US1 (integrate)
2. 21 tasks can run in parallel (different files, no blocking dependencies)
3. TDD approach: Write tests before implementation (constitution requirement >80% coverage)
4. MVP scope: Phases 1-6 (US1-US4), Phase 7 for production readiness
5. Reuse opportunities: 7 existing components identified (CatalystDetector, @with_retry, MomentumLogger, etc.)

**Checkpoint**:
- ✅ Tasks generated: 40
- ✅ User story organization: Complete (4 user stories mapped)
- ✅ Dependency graph: Created (7 phases with clear dependencies)
- ✅ MVP strategy: Defined (US2→US3→US4→US1 sequence)
- 📋 Ready for: /analyze

## Phase 4: Implementation (2025-10-29 01:43)

**Batch 1 (Setup Infrastructure)** - Completed
- ✅ T001: Install Python dependencies (requirements.txt updated)
- ✅ T002: Create sentiment module directory structure (src/trading_bot/momentum/sentiment/)
- ✅ T003: Create test directory structure (tests/unit/services/momentum/sentiment/)

**Key Decisions**:
1. Dependencies added: transformers==4.35.0, torch==2.1.0, tweepy==4.14.0, praw==7.7.1
2. Module structure follows existing momentum/ pattern
3. Test structure mirrors existing test organization

**Batch 2 (Foundational Models)** - Completed
- ✅ T004: Create SentimentPost dataclass with validation
- ✅ T005: Create SentimentScore dataclass with validation
- ✅ T006: Add sentiment_score field to CatalystEvent
- ✅ T007: Extend MomentumConfig with sentiment credentials

**Key Decisions**:
1. All models use frozen dataclasses with __post_init__ validation (follows existing pattern)
2. SentimentScore requires min 10 posts for reliable signal
3. CatalystEvent.sentiment_score is optional (None if unavailable)
4. MomentumConfig includes 8 sentiment fields with sensible defaults
5. Feature flag: sentiment_enabled (default True) for quick rollback

**Batch 3 (US2 - Twitter/Reddit API Integration)** - Completed
- ✅ T008: Write unit test - SentimentFetcher initializes clients
- ✅ T009: Write unit test - fetch_twitter_posts returns SentimentPost list
- ✅ T010: Write unit test - fetch_reddit_posts returns SentimentPost list
- ✅ T011: Write unit test - fetch_all combines Twitter and Reddit posts
- ✅ T012: Implement SentimentFetcher.__init__ with Twitter/Reddit clients
- ✅ T013: Implement fetch_twitter_posts with 30-min time window filtering
- ✅ T014: Implement fetch_reddit_posts with wallstreetbets+stocks search

**Key Decisions**:
1. Used @with_retry() decorator with default policy (3 attempts, exponential backoff)
2. Graceful degradation: Returns empty list on API failure, logs error
3. Twitter query format: "${symbol} OR {symbol} -is:retweet" (catches both formats)
4. Reddit searches both r/wallstreetbets and r/stocks (combined query)
5. Time window filtering: Post-API-call client-side filtering (Reddit API limitation)
6. All 9 tests passing with 100% coverage for new code

---

**Batch 4 (US3 - FinBERT Sentiment Analysis)** - Completed
- ✅ T015: Write unit test - SentimentAnalyzer loads FinBERT model
- ✅ T016: Write unit test - analyze_post returns sentiment scores
- ✅ T017: Write unit test - analyze_batch processes multiple posts
- ✅ T018: Implement SentimentAnalyzer.__init__ with model caching (singleton)
- ✅ T019: Implement analyze_post with GPU/CPU support
- ✅ T020: Implement analyze_batch with batch tokenization

**Key Decisions**:
1. Singleton pattern: Model loaded once at class level, reused across instances
2. GPU acceleration: Auto-detect CUDA, fallback to CPU gracefully
3. Batch inference: Tokenize all posts together for performance (amortized <200ms/post)
4. Empty text handling: Returns neutral sentiment (0.33/0.34/0.33)
5. Model: ProsusAI/finbert from Hugging Face Hub (~500MB)
6. All 7 tests passing with 100% coverage for new code

---

## Implementation Progress Summary

**Completed**: 20/40 tasks (50%)
**Batches Completed**: 4/7

**Phase Status**: US2 (Fetching) and US3 (Analysis) complete - Core sentiment pipeline ready

**Remaining Work** (20 tasks):
- Batch 5 (US4 Aggregation): 4 tasks - 30-min rolling window with recency weighting (T021-T024)
- Batch 6 (US1 Integration): 5 tasks - CatalystDetector.scan() extension with E2E tests (T025-T029)
- Batch 7 (Polish): 11 tasks - Error handling, logging, deployment prep, documentation (T030-T040)

**Next Steps**:
1. Continue with Batch 5 (US4 - 30-min rolling aggregation)
2. Implement SentimentAggregator.aggregate() with exponential decay weighting
3. Min 10 posts requirement for reliable signal
4. Formula: weighted_avg = Σ(score * e^(-minutes_ago/10)) / Σ(weights)

