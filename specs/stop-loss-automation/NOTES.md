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

## Configuration Setup

The stop-loss automation feature extends the existing `risk_management` section in `config.json` with new fields for automated stop placement and target management. Follow the pattern from `config.example.json`.

**Required fields to add:**

```json
{
  "risk_management": {
    "account_risk_pct": 1.0,
    "min_risk_reward_ratio": 2.0,
    "default_stop_pct": 2.0,
    "trailing_enabled": true,
    "pullback_lookback_candles": 20,
    "trailing_breakeven_threshold": 0.5,
    "strategy_overrides": {}
  }
}
```

**Field explanations:**

- `account_risk_pct` (float): Maximum percentage of account balance to risk per trade (e.g., 1.0 = 1%). Used to calculate position size based on distance to stop-loss. Aligns with Constitution §Risk_Management.

- `min_risk_reward_ratio` (float): Minimum required risk-reward ratio for trade entry (e.g., 2.0 = target must be 2x stop distance). Ensures positive expectancy over time.

- `default_stop_pct` (float): Fallback stop-loss percentage below entry price when no clear pullback low is detected (e.g., 2.0 = 2% below entry). Used by PullbackAnalyzer as safety default.

- `trailing_enabled` (bool): Enable automatic trailing stop adjustment. When true, moves stop to breakeven at 50% target progress (configurable via `trailing_breakeven_threshold`).

- `pullback_lookback_candles` (int): Number of recent candles to analyze for swing low detection. Typical range: 10-30. Higher values capture deeper pullbacks, lower values react faster to recent price action.

- `trailing_breakeven_threshold` (float): Price progress threshold to trigger breakeven stop (e.g., 0.5 = move stop to entry when price reaches 50% to target). Prevents profitable trades from becoming losers.

- `strategy_overrides` (dict): Optional per-strategy customization. Follows same pattern as `order_management.strategy_overrides`. Example:
  ```json
  "strategy_overrides": {
    "bull_flag_breakout": {
      "account_risk_pct": 0.5,
      "min_risk_reward_ratio": 3.0
    }
  }
  ```

**Migration steps:**

1. Copy `config.example.json` to `config.json` if not exists
2. Add new fields to existing `risk_management` section (preserve existing fields like `max_position_pct`, `max_daily_loss_pct`)
3. Adjust values based on risk tolerance and trading style
4. Restart trading bot to load new configuration
5. Verify in logs: "RiskManagementConfig loaded" with field values

**Validation:**

Run config validation script (if exists) or check logs on startup for configuration errors. RiskManagementConfig uses Pydantic validation with strict types and bounds checking.

## Task Progress
✅ T001 [P]: Create risk_management package structure (commit: 90c574d)
✅ T002 [P]: Create domain exceptions (commit: 9229f75)
✅ T003 [P]: Create RiskManagementConfig dataclass (commit: 0d5a74d)
✅ T004 [P]: Extend Config to include risk_management section (commit: d7a5aea)
✅ T005 [P]: Create PositionPlan dataclass (commit: aac9c07)
✅ T006 [P]: Create RiskManagementEnvelope dataclass (commit: aac9c07)
✅ T007 [P]: Create PullbackData dataclass (commit: 690e1f0)
✅ T008 [RED]: Write failing test for swing low detection (commit: 97a918c)
✅ T009 [RED]: Write failing test for default fallback (commit: 97a918c)
✅ T010 [RED]: Write failing test for position size calculation with pullback (commit: e03c087)
✅ T011 [RED]: Write failing test for stop distance validation (commit: 44fc9eb)
✅ T012 [RED]: Write failing test for stop direction validation (commit: 5d36464)
✅ T013 [RED]: Write failing test for minimum risk-reward ratio enforcement (commit: 44fc9eb)
✅ T014 [RED]: Write failing test for RiskManager places orders (commit: bc4189f)
✅ T015 [RED]: Write failing test for position plan JSONL logging (commit: 55588a0)
✅ T016 [RED]: Write failing test for trailing stop at 50% progress (commit: 4d5d757)
✅ T017 [RED]: Write failing test for trailing disabled (commit: 4d5d757)
✅ T018 [RED]: Write failing test for target fill cleanup (commit: 4b9a08a)
✅ T019 [RED]: Write failing test for stop fill cleanup (commit: 4b9a08a)
✅ T020 [RED]: Write failing test for cancel entry on stop fail (commit: fd732bd)
✅ T021 [GREEN→T008]: Implement PullbackAnalyzer.analyze_pullback() with swing low detection (commit: 218b137)
✅ T022 [GREEN→T009]: Add fallback logic to PullbackAnalyzer for uptrend scenarios (commit: 218b137)
✅ T023 [GREEN→T010]: Implement RiskRewardCalculator.calculate_position_plan() (commit: 218b137)
✅ T024 [GREEN→T011,T012,T013]: Add validation methods to RiskRewardCalculator (commit: 218b137)
✅ T025 [GREEN→T014]: Implement RiskManager.place_trade_with_risk_management() (commit: 9b9e7ab)
✅ T026 [GREEN→T015]: Add JSONL logging to RiskManager (commit: 25252e4)
✅ T027 [GREEN→T016]: Implement StopAdjuster.calculate_adjustment() (commit: 690bb3a)
✅ T028 [GREEN→T017]: Add trailing_enabled check in StopAdjuster (commit: 690bb3a)
✅ T029 [GREEN→T018,T019]: Implement TargetMonitor.poll_and_handle_fills() (commit: 29823bf)
✅ T030 [GREEN→T020]: Add error handling to RiskManager.place_trade_with_risk_management() (commit: 5f13222)
✅ T031 [REFACTOR]: Extract position size calculation to separate method (commit: ff15484)
✅ T033 [REFACTOR]: Add comprehensive logging with correlation IDs (commit: 5b2fdbc)
✅ T034 [P]: Write integration test for end-to-end position lifecycle with target fill (commit: f261ccd)
✅ T035 [P]: Write integration test for stop-out scenario (commit: f261ccd)
✅ T036 [P]: Add performance test for position plan calculation (commit: 4c06637)
✅ T037 [P]: Integrate RiskManager into TradingBot.execute_trade (live mode) (commit: b5b7502)
✅ T038 [RED]: Write test for retry on transient broker failures (commit: d96e43f)
✅ T039 [GREEN→T038]: Apply @retry_on_transient_failure decorator (commit: 52b3163)
✅ T040 [P]: Add circuit breaker integration for stop placement failures (commit: 54c7914)
✅ T041 [P]: Add config migration instructions to NOTES.md
✅ T042 [P]: Document rollback procedure in NOTES.md

## Rollback Runbook

**⚠️ WARNING: Before rolling back, manually close any live positions with active stop-loss or target orders via the Robinhood UI. Automated rollback WILL NOT cancel open orders or close positions.**

### Rollback Steps

Execute in order when reverting stop-loss automation:

1. **Stop the trading bot**
   ```bash
   systemctl stop trading-bot
   ```

2. **Manually close all live positions**
   - Log in to Robinhood UI
   - Review all open positions with active stop-loss or target orders
   - Cancel stop-loss orders via Orders & History → Cancel Order
   - Cancel target limit sell orders via Orders & History → Cancel Order
   - Close positions at market if needed (evaluate exit strategy first)
   - Document closed positions and final P&L in trade journal

3. **Revert to previous commit**
   ```bash
   git log --oneline -5  # Identify commit before stop-loss automation
   git revert HEAD~N     # Revert N commits back (adjust based on log)
   ```

4. **Remove risk_management configuration**
   - Edit `config.json`
   - Delete the entire `risk_management` section
   - Validate JSON syntax: `python -m json.tool config.json`

5. **Restart bot in paper trading mode**
   - Edit `config.json`
   - Set `paper_trading: true`
   - Restart: `systemctl start trading-bot`

6. **Verify paper trading active**
   ```bash
   tail -f logs/trading-bot.log | grep "paper_trading"
   # Expected: "paper_trading mode ENABLED"
   ```

### Rollback Verification Checklist

After rollback, verify:

- [ ] Trading bot running: `systemctl status trading-bot` shows `active (running)`
- [ ] Paper trading enabled: `grep "paper_trading.*true" config.json` returns match
- [ ] No risk_management section: `grep "risk_management" config.json` returns empty
- [ ] Logs confirm paper mode: `tail -20 logs/trading-bot.log` shows "paper_trading mode ENABLED"
- [ ] No open positions: Check Robinhood UI → Holdings (should be empty or pre-rollback state)
- [ ] No pending orders: Check Robinhood UI → Orders & History (should be empty)
- [ ] No risk-management log files actively written: `ls -lt logs/risk-management.jsonl` (file may exist but no new entries)

### Post-Rollback Actions

1. **Document rollback reason**
   - Update `specs/stop-loss-automation/NOTES.md` with:
     - Timestamp of rollback
     - Reason for rollback (bug description, performance issue, etc.)
     - Positions affected (symbol, entry, stop, target, exit, P&L)

2. **Review error logs**
   - Check `logs/trading-bot.log` for errors leading to rollback
   - Save relevant error stack traces to `specs/stop-loss-automation/error-log.md`

3. **Notify stakeholders**
   - Alert team via communication channel
   - Include: rollback reason, current bot status (paper trading), next steps

### Rollback Risk Assessment

**Low Risk:**
- No open positions at rollback time
- Bot already in paper trading mode
- Config changes only (no code deployed)

**Medium Risk:**
- 1-3 open positions with active stop/target orders
- Live trading mode active
- Positions can be manually closed within 5 minutes

**High Risk:**
- >3 open positions with complex order structures
- Market hours with high volatility
- Positions require immediate attention (approaching stop-loss levels)

**Emergency Rollback Protocol (High Risk):**
1. Immediately stop bot: `systemctl stop trading-bot`
2. Screenshot all open positions and orders (Robinhood UI)
3. Close positions at market (accept slippage)
4. Proceed with standard rollback steps
5. Post-mortem review within 24 hours

## Last Updated
2025-10-16T10:30:00-05:00
