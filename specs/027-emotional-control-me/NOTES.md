# Feature: Emotional control mechanisms

## Overview
This feature implements emotional control safeguards to protect traders from making poor decisions during losing streaks or after significant losses. The system automatically reduces position sizes and enforces recovery periods to prevent emotional revenge trading and preserve capital during periods of drawdown.

## Research Findings

### Finding 1: Existing circuit breaker infrastructure
**Source**: src/trading_bot/safety_checks.py, src/trading_bot/error_handling/circuit_breaker.py
**Details**: Project already has circuit breaker implementation for consecutive losses and daily loss limits
**Decision**: Extend existing circuit breaker pattern rather than creating new mechanism

### Finding 2: Risk management foundation
**Source**: src/trading_bot/risk_management/manager.py
**Details**: RiskManager class with position sizing calculator and pullback analyzer
**Decision**: Integrate emotional control as risk manager extension

### Finding 3: Daily profit goal management shipped (v1.5.0)
**Source**: roadmap.md lines 649-676
**Details**: DailyProfitTracker with profit protection, giveback threshold, state persistence
**Decision**: Use similar pattern for loss tracking and position size reduction

### Finding 4: Roadmap backlog entry exists
**Source**: roadmap.md lines 715-728
**Details**: "emotional-controls" feature listed with ICE score 1.60 (Impact: 4, Effort: 2, Confidence: 0.8)
**Requirements captured**:
- Detect significant loss (threshold TBD)
- Auto-reduce position size to 25% of normal
- Require manual reset after recovery period
- Log all size adjustments
- Force simulator mode after daily loss limit hit
**Decision**: Use roadmap requirements as baseline, add details via specification

### Finding 5: Constitution §Safety_First and §Risk_Management
**Source**: .spec-flow/memory/constitution.md lines 11-27
**Principles**:
- Fail safe, not fail open (errors halt trading)
- Circuit breakers required (hard limits on losses)
- Position sizing mandatory (never exceed 5% portfolio per position)
**Decision**: Emotional controls must align with these principles

## System Components Analysis
N/A - Backend-only feature (no UI components needed)

## Feature Classification
- UI screens: false
- Improvement: true (enhances existing risk management)
- Measurable: true (track loss events, position size reductions, recovery periods)
- Deployment impact: false (pure Python logic, no infrastructure changes)

## Key Decisions

1. **Position Size Reduction**: Reduce to 25% of normal size after significant loss event (defined as single trade loss ≥3% of account OR consecutive loss streak ≥3 trades)

2. **Recovery Period**: Require 3 consecutive profitable trades OR manual admin reset to restore normal position sizing

3. **Manual Reset Authority**: Only admin/user can manually override recovery period (prevents automated premature scaling)

4. **State Persistence**: Use JSONL logging pattern (similar to DailyProfitTracker) for audit trail and state recovery

5. **Integration Point**: Extend RiskManager class with new EmotionalControl module that wraps position sizing calculations

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-22

## Last Updated
2025-10-22T09:25:00-04:00
