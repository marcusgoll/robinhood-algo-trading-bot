# Feature: ATR-based dynamic stop-loss adjustment

## Overview

Enhancement to existing stop-loss automation that adds ATR (Average True Range) based dynamic stop calculation. ATR is a volatility indicator that adapts stop distances to market conditions - wider stops in volatile markets to avoid premature stop-outs, tighter stops in calm markets for better capital protection.

## Research Findings

### Finding 1: Existing Stop-Loss Infrastructure
- Source: specs/stop-loss-automation/spec.md
- Current implementation supports fixed stop-loss calculation based on pullback lows or percentage-based fallback
- RiskManager, StopAdjuster, and Calculator modules already exist in src/trading_bot/risk_management/
- Current stop logic: Identify pullback low OR use default 2% stop distance
- Limitation: Static stop distances don't adapt to volatility - same 2% stop applies regardless of whether market is calm or volatile

### Finding 2: Current Stop Adjustment Strategy
- Source: src/trading_bot/risk_management/stop_adjuster.py
- StopAdjuster exists with trailing stop logic (activation_pct=10%, trailing_distance_pct=5%)
- Current adjustment: Move to breakeven at 50% target progress
- Limitation: Trailing stops use fixed percentages, not volatility-adjusted

### Finding 3: Position Sizing Foundation
- Source: src/trading_bot/risk_management/calculator.py
- calculate_position_plan() already handles risk-based position sizing
- Validates stop distance bounds (0.5% exact or 0.7%-10% range)
- Calculates risk/reward ratios and validates against minimum thresholds
- Integration point: Can extend to accept ATR-based stops instead of pullback-based stops

### Finding 4: Constitution Risk Management Requirements
- Source: .spec-flow/memory/constitution.md
- §Risk_Management mandates stop losses on every position
- §Safety_First requires fail-safe design - errors must halt trading
- §Data_Integrity requires validation of market data completeness
- §Testing_Requirements demands 90%+ test coverage for financial code
- Compliance: ATR calculation must validate data quality and handle missing data gracefully

### Finding 5: ATR Implementation Strategy
- Decision: ATR (Average True Range) is a volatility indicator that measures price movement
- Calculation: ATR = average of true ranges over N periods (typically 14)
- True Range = max(high - low, |high - previous_close|, |low - previous_close|)
- Application: Use ATR multiplier for stop distance (e.g., 2.0 * ATR for wider stop in volatile markets)
- Benefit: In volatile markets, stops widen automatically to avoid premature stop-outs
- Benefit: In calm markets, stops tighten to protect capital more aggressively

## System Components Analysis

**Existing Components (from risk_management package)**:
- RiskManager (orchestrator) - Entry point for risk planning
- Calculator (position sizing and validation) - Core logic location
- StopAdjuster (trailing stop logic) - Needs ATR integration
- PullbackAnalyzer (swing low detection) - Parallel logic, not replaced
- TargetMonitor (fill detection) - No changes needed

**New Components Needed**:
- ATRCalculator: Calculate ATR from price data (high, low, close over N periods)
- ATRStopStrategy: Determine stop price using ATR multiplier instead of pullback low
- Configuration extension: Add atr_enabled, atr_period, atr_multiplier to RiskManagementConfig

**Integration Strategy**:
- Enhance calculate_position_plan() to accept optional atr_data parameter
- When atr_enabled=true, use ATR-based stop calculation instead of pullback analysis
- Fall back to pullback/percentage stops when ATR data unavailable
- Maintain backward compatibility - existing pullback logic remains default

## Feature Classification
- UI screens: false
- Improvement: true
- Measurable: true
- Deployment impact: false

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-16

## Last Updated
2025-10-16T00:00:00
