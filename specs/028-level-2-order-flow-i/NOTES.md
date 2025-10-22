# Feature: Level 2 order flow integration

## Overview
Integrate Level 2 order book data and Time & Sales (tape) data to provide real-time order flow analysis for detecting large seller alerts and volume spikes. This enhances the trading bot's ability to detect institutional selling pressure and trigger exits before significant price drops.

## Feature Classification
- UI screens: false
- Improvement: false
- Measurable: true
- Deployment impact: true

## Research Findings

### Finding 1: Robinhood API Limitations
**Source**: .spec-flow/memory/roadmap.md (level2-integration entry)
**Finding**: Roadmap already flags "[CLARIFY: Does Robinhood API provide Level 2 data?]" as a blocker
**Decision**: CRITICAL - Need to investigate if robin_stocks library or Robinhood API supports Level 2 order book data

### Finding 2: Existing Market Data Infrastructure
**Source**: src/trading_bot/market_data/market_data_service.py
**Finding**: MarketDataService uses robin_stocks.robinhood.get_latest_price() for quotes and get_stock_historicals() for OHLCV data
**Components**: MarketDataService, Quote dataclass, validators, @with_retry decorator
**Decision**: Can extend existing MarketDataService with Level 2 methods if API supports it

### Finding 3: Constitution Compliance Requirements
**Source**: .spec-flow/memory/constitution.md
**Key Principles**:
- §Data_Integrity: All market data validated before use
- §Audit_Everything: All API calls logged
- §Safety_First: Fail-fast on validation errors
- §Rate_Management: Respect Robinhood API limits, implement backoff
**Decision**: Any Level 2 integration must follow existing patterns (validators, retry logic, logging)

### Finding 4: Similar Feature Pattern
**Source**: specs/002-momentum-detection/spec.md
**Pattern**: Real-time data scanning with alerts (PreMarketScanner tracks >5% price change, >200% volume)
**Reusable Approach**:
- Detector pattern (CatalystDetector, PreMarketScanner, BullFlagDetector)
- Structured JSONL logging
- Configuration validation with env vars
- Graceful degradation on missing data
**Decision**: Level 2 order flow should follow detector pattern

### Finding 5: Roadmap Dependencies
**Source**: .spec-flow/memory/roadmap.md
**Blocker**: [BLOCKED: market-data-module] (but market-data-module is now shipped as of v1.1.0)
**Status**: Blocker resolved - market-data-module is operational
**Decision**: Can proceed with Level 2 integration now that dependency is shipped

## System Components Analysis

**Backend-only feature (no UI components)**

**Reusable Components** (from existing codebase):
- MarketDataService (src/trading_bot/market_data/market_data_service.py) - Extend with Level 2 methods
- TradingLogger (src/trading_bot/logger.py) - Structured JSONL logging
- @with_retry decorator (src/trading_bot/error_handling/retry.py) - Rate limit handling
- DEFAULT_POLICY (src/trading_bot/error_handling/policies.py) - Retry policy
- RobinhoodAuth (src/trading_bot/auth/robinhood_auth.py) - Authentication

**New Components Needed**:
- OrderFlowDetector - Analyze Level 2 order book for large seller alerts
- TapeMonitor - Track Time & Sales for volume spikes
- OrderFlowConfig - Configuration dataclass for thresholds
- OrderFlowValidator - Validate Level 2 data integrity
- OrderFlowAlert - Dataclass for alert structure

**Rationale**: System-first approach reduces implementation time and ensures Constitution compliance

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-22

## Last Updated
2025-10-22T00:00:00Z
