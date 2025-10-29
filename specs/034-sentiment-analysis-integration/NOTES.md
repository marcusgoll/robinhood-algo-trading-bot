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

