# Feature: stop-loss-automation

## Overview
Automated stop loss and target management system that calculates position sizing based on risk, places stop-loss orders at pullback lows, and sets 2:1 risk-reward targets with auto-adjustment capabilities.

## Research Findings

### Finding 1: OrderManager foundation exists
- Source: specs/order-management/spec.md
- Evidence: OrderManager provides `place_limit_buy()` and `place_limit_sell()` with offset logic
- Decision: Build stop-loss automation on top of existing OrderManager infrastructure
- Implication: Can leverage existing order submission, cancellation, and status tracking

### Finding 2: SafetyChecks includes position sizing
- Source: src/trading_bot/safety_checks.py
- Evidence: `calculate_position_size()` exists with entry_price, stop_loss_price, account_balance params
- Current implementation: Basic risk-based position sizing
- Decision: Extend SafetyChecks with pullback analysis and automated stop placement
- Implication: Maintain existing safety validation patterns

### Finding 3: Risk management configuration exists
- Source: src/trading_bot/config.py
- Evidence: OrderManagementConfig with offset_mode, buy_offset, sell_offset, max_slippage_pct
- Decision: Add risk_management section to Config for stop-loss and target parameters
- Implication: Follow existing configuration patterns (global defaults + strategy overrides)

### Finding 4: Constitution requirements
- Source: .spec-flow/memory/roadmap.md
- Requirement: Stop loss calculator must identify pullback low as invalidation point
- Requirement: Calculate 2:1 target from entry and stop
- Requirement: Auto-adjust if stop moves
- Requirement: Auto-exit on target hit (§Risk_Management)
- Impact: All features must comply with §Safety_First and §Risk_Management principles

### Finding 5: Integration points
- OrderManager: Submit stop-loss and target orders
- SafetyChecks: Validate position sizes against account risk limits
- AccountData: Query current buying power and positions
- TradeRecord: Log stop-loss placements and target hits
- Decision: Create RiskManager service to orchestrate these components

## System Components Analysis

**Reusable (from existing codebase)**:
- OrderManager (place_limit_sell for stops and targets)
- SafetyChecks.calculate_position_size (position sizing foundation)
- Config dataclass pattern (for risk_management configuration)
- Error handling decorators (for broker retry logic)
- Structured logging (for audit trail)

**New Components Needed**:
- RiskManager service (orchestrates stop-loss and target logic)
- PullbackAnalyzer (identifies pullback lows from price data)
- RiskRewardCalculator (computes 2:1 targets)
- StopAdjuster (trailing stop logic)
- TargetMonitor (tracks progress and auto-exits)

**Rationale**: Build on proven OrderManager foundation while adding risk-specific intelligence layer.

## Feature Classification
- UI screens: false (backend service only)
- Improvement: true (enhances existing position management)
- Measurable: true (stop-loss hit rate, target achievement, drawdown reduction)
- Deployment impact: false (config-only changes, no platform dependencies)

## Key Decisions

1. **Architecture**: Two-tier design
   - RiskManager orchestrates high-level stop/target logic
   - OrderManager handles low-level broker communication
   - Rationale: Separation of risk intelligence from order execution

2. **Pullback identification**: Technical analysis approach
   - Use recent swing lows from price data (last N candles)
   - Fallback: percentage-based stop if no clear pullback (e.g., 2% below entry)
   - Rationale: Aligns with Constitution requirement for invalidation point identification

3. **Position sizing**: Risk-first calculation
   - Account risk limit: % of account per trade (e.g., 1% max risk)
   - Formula: position_size = (account_balance * risk_pct) / (entry_price - stop_price)
   - Rationale: Capital preservation as primary goal (§Risk_Management)

4. **Target management**: 2:1 minimum risk-reward
   - Calculate: target_price = entry_price + 2 * (entry_price - stop_price)
   - Place limit sell at target automatically
   - Rationale: Ensures positive expectancy over time

5. **Stop adjustment**: Trailing stop support
   - Move stop to breakeven when price moves halfway to target
   - Trail stop at 1:1 when target hit
   - Rationale: Lock in profits while allowing runners

6. **Configuration**: Extend Config with risk_management section
   - Global defaults: account_risk_pct, min_risk_reward_ratio, trailing_enabled
   - Strategy overrides: Allow per-strategy customization
   - Rationale: Consistency with existing OrderManagementConfig pattern

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-15
- Phase 1 (Plan): 2025-10-15
  - Artifacts: plan.md, contracts/api.yaml, error-log.md
  - Research decisions: 7 (architecture, reuse, pullback, logging, config, models, trailing)
  - Components to reuse: 6 (OrderManager, SafetyChecks, AccountData, TradeRecord, error handling, logging)
  - New components: 8 (RiskManager, PullbackAnalyzer, calculator, stop_adjuster, target_monitor, models, exceptions, config)
  - Migration needed: No (config-only changes)
- Phase 2 (Tasks): 2025-10-15
  - Artifacts: tasks.md
  - Total tasks: 43
  - TDD breakdown: 14 RED tests, 11 GREEN implementations, 3 REFACTOR cleanups (60% TDD coverage)
  - Parallel tasks: 15 (setup, models, independent tests)
  - Phases: Setup (4), Models (3), RED (14), GREEN (11), REFACTOR (3), Integration (4), Error Handling (3), Deployment (3)
  - Ready for: /analyze

## Phase 1 Summary
Research depth: Analyzed OrderManager, SafetyChecks, Config patterns from existing codebase. Identified 6 reusable components (OrderManager for broker communication, SafetyChecks for position sizing foundation, error handling decorators, structured logging). Designed 8 new components following established patterns (RiskManager orchestrator, PullbackAnalyzer for swing low detection, StopAdjuster for trailing logic). Key architectural decision: Two-tier design separates risk intelligence (RiskManager) from order execution (OrderManager). No database changes required - uses JSONL logging (logs/risk-management.jsonl) following trade-logging module pattern. Configuration extends Config with risk_management section mirroring OrderManagementConfig pattern.

## Phase 2 Summary
Task generation: Created 43 concrete implementation tasks following TDD cycle (RED → GREEN → REFACTOR). TDD coverage: 14 failing tests specify behavior (pullback detection, position sizing, order placement, trailing stops, fill monitoring, error handling), 11 minimal implementations to pass tests, 3 refactoring tasks for clean architecture. Key task decisions: (1) Reuse OrderManager for broker communication, SafetyChecks for position sizing foundation, (2) Phase ordering: Setup → Models → Tests → Implementation → Integration → Error Handling → Deployment, (3) Parallel execution opportunities in setup (T001-T004), models (T005-T007), and tests (T008-T020), (4) Integration tests (T034-T037) validate end-to-end lifecycle with mocked broker APIs, (5) Performance test (T036) ensures position plan calculation ≤200ms (NFR-001). All tasks reference specific files, methods, patterns from existing codebase. Task file: specs/stop-loss-automation/tasks.md.

## Phase 3 Summary
Cross-artifact analysis: Validated 100% requirement coverage (14 functional, 8 non-functional requirements all mapped to tasks). TDD discipline confirmed with strict RED → GREEN → REFACTOR sequence (14 RED tests, 11 GREEN implementations, 3 REFACTOR cleanups). Architecture consistency verified: Two-tier design (RiskManager + OrderManager) maintained across spec, plan, and tasks. Reuse validation: All 7 existing components (OrderManager, SafetyChecks, AccountData, TradeRecord, StructuredTradeLogger, error hierarchy, retry decorators) confirmed available. New components: All 8 specified (RiskManager, PullbackAnalyzer, RiskRewardCalculator, StopAdjuster, TargetMonitor, models, exceptions, config). Edge cases: All 5 covered with tests. Performance targets: 4 benchmarks included. Terminology: No drift detected. Integration points: TradingBot and OrderManager integration fully specified. Zero critical, high, medium, or low issues found. Status: Ready for implementation. Analysis report: specs/stop-loss-automation/analysis-report.md.

## Task Progress
✅ T001 [P]: Create risk_management package structure (commit: 90c574d)
✅ T002 [P]: Create domain exceptions (commit: 9229f75)
✅ T003 [P]: Create RiskManagementConfig dataclass (commit: 0d5a74d)
✅ T004 [P]: Extend Config to include risk_management section (commit: d7a5aea)
✅ T005 [P]: Create PositionPlan dataclass (commit: aac9c07)
✅ T006 [P]: Create RiskManagementEnvelope dataclass (commit: aac9c07)
✅ T007 [P]: Create PullbackData dataclass (commit: 690e1f0)

## Last Updated
2025-10-15T23:45:00-05:00
