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
