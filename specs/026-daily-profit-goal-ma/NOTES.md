# Feature: Daily profit goal management

## Overview

Daily profit goal management feature for automated profit protection. System tracks daily P&L (realized + unrealized), detects when trader has given back 50% of peak profit, and triggers protection mode to block new entries and preserve gains. Integrates with existing performance-tracking and safety-checks modules.

**Core Value**: Prevents overtrading and profit giveback by automatically protecting gains when trader experiences significant drawdown from daily peak.

**MVP Scope**: US1-US3 (configure target, track P&L, trigger protection at 50% drawdown)
**Enhancement Scope**: US4-US6 (configurable thresholds, dashboard display, historical analytics)

## Research Findings

### Finding 1: Feature exists in roadmap as "profit-goal-manager"
- **Source**: .spec-flow/memory/roadmap.md (lines 701-713)
- **ICE Score**: 1.60 (Impact: 4, Effort: 2, Confidence: 0.8)
- **Area**: strategy
- **Status**: Backlog
- **Dependencies**: performance-tracking ✅ (shipped v1.0.0), safety-checks ✅ (shipped v1.0.0)
- **Requirements from roadmap**:
  - Set daily profit target
  - Track progress to goal
  - Detect when half of profit given back
  - Trigger exit rule when threshold hit
  - Reset daily at market open (§Risk_Management)

### Finding 2: Constitution compliance required
- **Source**: .spec-flow/memory/constitution.md
- **Relevant principles**:
  - §Risk_Management: Stop losses required, position sizing mandatory, validate all inputs
  - §Safety_First: Fail safe not fail open, audit everything, circuit breakers
  - §Testing_Requirements: 90%+ test coverage, unit tests, integration tests
  - §Code_Quality: Type hints required, one function one purpose, no duplicate logic
  - §Audit_Everything: Trade decisions must be logged with reasoning

### Finding 3: Related shipped features for integration
- **Source**: roadmap.md Shipped section
- **performance-tracking** (v1.0.0 - Oct 15, 2025):
  - PerformanceTracker class with daily/weekly/monthly aggregation
  - AlertEvaluator for threshold monitoring
  - Win/loss ratio calculator
  - 92% test coverage
  - Location: src/trading_bot/performance/
- **safety-checks** (Oct 8, 2025):
  - SafetyChecks module with pre-trade validation
  - Daily loss circuit breaker (3% threshold)
  - Circuit breaker management (trigger/reset)
  - Location: src/trading_bot/safety_checks.py
- **trade-logging** (Oct 9, 2025):
  - TradeRecord dataclass with 27 fields
  - StructuredTradeLogger with daily JSONL rotation
  - TradeQueryHelper for analytics
  - Location: src/trading_bot/logging/

### Finding 4: No existing profit goal logic found
- **Source**: Grep search for "profit.*goal" patterns in src/ directory
- **Result**: No existing profit goal classes or methods
- **Decision**: This is a new feature, not an enhancement

## System Components Analysis
[Populated during system component check]

## Feature Classification
- UI screens: false
- Improvement: false
- Measurable: false
- Deployment impact: false
- Research mode: minimal

## Checkpoints
- Phase 0 (Spec): 2025-10-21

## Last Updated
2025-10-21T23:15:00
