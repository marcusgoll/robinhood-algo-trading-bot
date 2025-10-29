# Feature: Multi-Timeframe Confirmation for Momentum Trades

## Overview
Multi-timeframe analysis adds higher-timeframe confirmation to momentum trades by validating bull flag patterns detected on lower timeframes (5-minute) against daily and 4-hour trend alignment. This reduces false signals and improves trade quality by ensuring trades align with broader market structure.

## Research Findings

### Finding 1: Existing Bull Flag Detection on Single Timeframe
**Source**: D:\Coding\Stocks\src\trading_bot\patterns\bull_flag.py

- Current BullFlagDetector operates on single timeframe (typically 5-minute bars)
- Three-phase detection: flagpole → consolidation → breakout
- Technical indicator validation (VWAP, MACD, EMA) on single timeframe only
- No higher-timeframe trend validation

**Decision**: Extend bull_flag.py pattern with multi-timeframe validation layer

### Finding 2: Market Data Service Supports Multiple Intervals
**Source**: D:\Coding\Stocks\src\trading_bot\market_data\market_data_service.py:118-123

- `get_historical_data()` accepts interval parameter: "day", "week", "10minute", "5minute"
- Supports span parameter: "day", "week", "month", "3month"
- Returns pandas DataFrame with OHLCV data
- Already integrated with @with_retry for resilience

**Decision**: Leverage existing market data infrastructure for multi-timeframe fetching

### Finding 3: Technical Indicators Service is Stateful
**Source**: D:\Coding\Stocks\src\trading_bot\indicators\service.py

- TechnicalIndicatorsService maintains state (_last_ema_9, _last_macd, etc.)
- Single instance per service lifecycle
- validate_entry() checks: price > VWAP AND MACD > 0

**Decision**: Create separate indicator service instances per timeframe to avoid state collision

### Finding 4: Similar Pattern in Support/Resistance Mapping
**Source**: specs/023-support-resistance-mapping/spec.md (grep results)

- Zone detection uses daily + 4H timeframes for support/resistance levels
- Establishes pattern for multi-timeframe coordination
- Institutional-level zone identification

**Decision**: Reuse multi-timeframe approach from support/resistance feature

### Finding 5: Constitution Compliance Requirements
**Source**: D:\Coding\Stocks\.spec-flow\memory\constitution.md

- §Data_Integrity: Validate all timeframe data before analysis
- §Risk_Management: Position sizing, stop losses mandatory
- §Testing_Requirements: 90% coverage, backtesting required
- §Safety_First: Fail-fast on validation errors

**Implication**: Must validate higher-timeframe data availability before trade entry

### Finding 6: Backtesting Engine Supports Multi-Timeframe
**Source**: specs/001-backtesting-engine/spec.md (roadmap shipped features)

- Event-driven backtesting with chronological execution
- Multi-source data support (Alpaca + Yahoo Finance)
- Parquet caching for performance
- Strategy Protocol for type-safe strategy interface

**Decision**: Use backtesting engine to validate multi-timeframe strategy performance

## System Components Analysis

**Reusable Components**:
- MarketDataService (timeframe data fetching)
- TechnicalIndicatorsService (per-timeframe indicator calculation)
- BullFlagDetector (lower-timeframe pattern detection)
- BacktestEngine (strategy validation)

**New Components Needed**:
- MultiTimeframeValidator (orchestrates cross-timeframe checks)
- TimeframeAlignment dataclass (stores alignment status)
- HigherTimeframeTrend enum (BULLISH, BEARISH, NEUTRAL, UNKNOWN)

**Rationale**: Composition pattern - extend existing pattern detection with higher-timeframe validation layer without modifying core bull flag logic.

## Feature Classification
- UI screens: false (backend strategy logic)
- Improvement: true (enhances existing bull flag pattern detection)
- Measurable: true (win rate, false positive reduction trackable via trade logs)
- Deployment impact: false (additive feature, no breaking changes)

## Checkpoints
- Phase 0 (Specification): 2025-10-28

## Last Updated
2025-10-28T23:05:00Z
