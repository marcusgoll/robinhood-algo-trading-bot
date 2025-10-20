# Feature: strategy-orchestrator

## Overview
Strategy orchestration system to manage, coordinate, and execute multiple trading strategies within the backtesting engine framework.

## Research Findings

### Finding 1: Existing Strategy Protocol
Source: src/trading_bot/backtest/strategy_protocol.py
- IStrategy protocol defines should_enter() and should_exit() interfaces
- Strategies are stateless: all state passed via parameters
- Strategies receive chronological data (no look-ahead bias)
- Currently designed for single-strategy execution

Decision: Orchestrator should support multiple IStrategy implementations simultaneously

### Finding 2: Sample Strategy Patterns
Source: examples/sample_strategies.py
- BuyAndHoldStrategy: Simple baseline (single trade, hold forever)
- MomentumStrategy: MA crossover (short/long window configurable)
- Strategies use clean, focused logic without side effects

Decision: Orchestrator should remain strategy-agnostic (works with any IStrategy)

### Finding 3: Backtesting Engine Architecture
Source: src/trading_bot/backtest/engine.py
- BacktestEngine executes single strategy chronologically
- Tracks portfolio state, positions, equity curve
- Generates comprehensive performance metrics
- Currently single-strategy focused

Implication: Orchestrator needs to coordinate multiple strategy instances while maintaining single execution timeline

### Finding 4: Similar Orchestration Pattern
Source: api/app/services/status_orchestrator.py
- StatusOrchestrator coordinates multiple status check services
- Aggregates results from parallel operations
- Provides unified interface for multi-component systems

Decision: Apply similar coordination pattern for strategy management

## System Components Analysis
**Reusable Components**:
- IStrategy protocol (existing interface)
- BacktestEngine (execution engine)
- HistoricalDataBar, Position, Trade models (data structures)
- PerformanceCalculator (metrics generation)

**New Components Needed**:
- StrategyOrchestrator (main coordinator)
- Strategy allocation/weighting system
- Multi-strategy portfolio aggregator
- Strategy conflict resolution logic

**Rationale**: System-first approach leverages existing backtesting infrastructure while adding coordination layer

## Feature Classification
- UI screens: false (backend system, no UI)
- Improvement: false (new capability, not improving existing)
- Measurable: true (strategy performance metrics, portfolio returns)
- Deployment impact: false (library code, no infrastructure changes)

## Research Mode
Standard (backend feature with measurable outcomes)

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-20
- Phase 1 (Plan): 2025-10-20
  - Artifacts: research.md, data-model.md, quickstart.md, plan.md, contracts/api.yaml, error-log.md
  - Research decisions: 5 key architectural choices
  - Migration required: No

## Phase 1 Summary
- Research depth: 120 lines
- Key decisions: 5 (composition pattern, protocol preservation, result aggregation, allocation tracking, structured logging)
- Components to reuse: 9 (BacktestEngine, IStrategy, PerformanceCalculator, ReportGenerator, models, test patterns)
- New components: 6 (StrategyOrchestrator, 3 dataclasses, 2 test modules)
- Migration needed: No

## Last Updated
2025-10-20T15:45:00-05:00
