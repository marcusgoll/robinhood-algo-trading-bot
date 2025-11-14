# Feature Specification: Automated Stop Loss and Targets

**Branch**: `stop-loss-automation`
**Created**: 2025-10-15
**Status**: Draft
**Area**: API
**From Roadmap**: Yes (Impact: 5, Effort: 2, Confidence: 0.9, Score: 2.25)

## User Scenarios

### Primary User Story
As a trading bot operator, I need automated stop-loss and profit target management that calculates position sizes based on account risk, identifies pullback lows as invalidation points, and auto-exits at 2:1 risk-reward targets so I can protect capital while maximizing winning trades without manual intervention.

### Acceptance Scenarios
1. **Given** a strategy signals a BUY entry for `TSLA` at `$250.30` and recent price data shows a pullback low at `$248.00`, **When** the bot calls `calculate_position_with_stop(symbol="TSLA", entry_price=250.30, account_balance=100000, account_risk_pct=1.0)`, **Then** the system identifies `$248.00` as the stop-loss price, calculates position size as `434 shares` (risk $1000 over $2.30 distance), computes 2:1 target at `$254.90`, and returns a `PositionPlan` with all three prices and quantities.

2. **Given** a position plan exists with entry `$250.30`, stop `$248.00`, target `$254.90`, and quantity `434 shares`, **When** the bot executes `place_trade_with_risk_management(plan, symbol="TSLA")`, **Then** the system (a) submits a limit BUY at entry price via OrderManager, (b) immediately places a stop-loss sell order at `$248.00` for `434 shares`, (c) places a limit sell target order at `$254.90` for `434 shares`, (d) records all three order IDs in a `RiskManagementEnvelope`, and (e) logs the complete risk profile to `logs/risk-management.jsonl`.

3. **Given** a live position in `TSLA` with entry `$250.30`, stop at `$248.00`, and target `$254.90`, **When** price moves to `$252.60` (halfway to target) and `adjust_trailing_stop=true` is configured, **Then** the `TargetMonitor` cancels the original stop order at `$248.00`, places a new stop at breakeven `$250.30`, updates the `RiskManagementEnvelope` with the new stop order ID, and logs the adjustment with reason "moved to breakeven - price reached 50% of target".

4. **Given** a position with target order at `$254.90` is being monitored, **When** `OrderManager.synchronize_open_orders()` detects the target order filled, **Then** the `TargetMonitor` callback (a) cancels any remaining stop-loss order, (b) marks the position as closed in the risk tracking log, (c) calculates realized P&L as `+$1996` (434 shares * $4.60 gain), (d) updates AccountData cache to reflect new buying power, and (e) emits a completion event to TradeRecord.

5. **Given** no clear pullback low exists in recent price data (e.g., strong uptrend with no retrace), **When** the bot requests a position plan, **Then** the system falls back to a percentage-based stop at `2%` below entry price (configurable via `default_stop_pct`), calculates position size accordingly, logs a warning "No pullback detected - using default 2% stop", and proceeds with the trade setup.

### Edge Cases
- What happens if the calculated position size exceeds available buying power? → Reduce position size to fit buying power, recalculate risk amount, log the adjustment, and warn if risk falls below minimum threshold.
- How does the system handle a stop-loss order rejection (e.g., price already below stop)? → Cancel the entry order if unfilled, log the failure, mark the trade as aborted, and surface a detailed error to the caller.
- What if both stop and target fill simultaneously (volatile market)? → Process fills in the order detected (first-wins), handle the second as a redundant cancel, reconcile final state in logs.
- How are partial fills on stop or target orders managed? → Track filled vs. remaining quantity in `RiskManagementEnvelope`, adjust remaining orders proportionally, maintain risk-reward ratio on remaining shares.
- What happens if pullback analysis identifies multiple swing lows? → Use the most recent swing low within the last N candles (configurable), prioritize recency over depth.

## Visual References
N/A – backend service (no UI components).

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce manual stop-loss placement | Count of `manual_stop_placement=true` events in logs | ≤1 per trading week | >3 in a week triggers review |
| **Engagement** | Maintain automation as primary risk path | % of live trades with auto-placed stops | ≥95% automated | <90% for 2 days triggers rollback |
| **Adoption** | Ensure all live strategies use RiskManager | Callers using `RiskManager` APIs vs legacy position sizing | 100% of live pathways | Track weekly until parity |
| **Retention** | Protect capital via effective stops | % of stopped-out trades that honored max risk | ≥99% within tolerance | >5% exceeding risk limit triggers incident |
| **Task Success** | Achieve 2:1 targets consistently | % of target orders filled vs stopped out | ≥40% target hit rate | <30% for 20 trades triggers strategy review |

**Performance Targets**:
- Position plan calculation (with pullback analysis) completes in <200ms.
- Stop-loss and target orders placed within 1 second of entry fill confirmation.
- Trailing stop adjustments execute within 10 seconds of price threshold breach.
- Maximum drawdown per trade never exceeds configured account_risk_pct (e.g., 1%).

## Hypothesis

**Problem**: Trading currently lacks automated stop-loss and profit target management, forcing manual risk decisions and exposing capital to uncontrolled drawdowns.
- Evidence: SafetyChecks.calculate_position_size exists but is never called in live execution flow (src/trading_bot/safety_checks.py:89-120).
- Evidence: OrderManager supports limit orders but has no stop-loss or target automation (specs/order-management/spec.md).
- Evidence: Roadmap identifies stop-loss automation as highest priority (Score: 2.25, Impact: 5) blocked only by order-management foundation.
- Impact: Without automated stops, a single runaway loss can wipe out multiple wins; without targets, winners exit prematurely or turn into losers.

**Solution**: Introduce a RiskManager service that integrates pullback analysis, position sizing, and automated stop/target placement with the existing OrderManager.
- Change: Create `src/trading_bot/risk_management/` package with RiskManager, PullbackAnalyzer, RiskRewardCalculator, StopAdjuster, and TargetMonitor.
- Change: Extend SafetyChecks.calculate_position_size to accept pullback data and return enhanced PositionPlan with stop/target prices.
- Change: Add `risk_management` section to Config with account_risk_pct, min_risk_reward_ratio, default_stop_pct, trailing_enabled, pullback_lookback_candles.
- Change: Wire RiskManager into TradingBot.execute_trade so every live trade includes automatic stop-loss and target orders.
- Change: Implement TargetMonitor.synchronize_positions() poller that detects fills and adjusts stops based on price progress.
- Mechanism: Reuse OrderManager for all broker communication, SafetyChecks for validation, and structured logging for audit trail.

**Prediction**: Automated risk management will reduce max drawdown while increasing win rate and average win size.
- Primary metric: Max drawdown per trade ≤ configured risk limit (1% of account) with ≥99% compliance.
- Expected improvement: Target hit rate ≥40% (up from ~25% manual exits observed in backtest notes).
- Secondary metric: Average risk-reward ratio on closed trades ≥1.8 (approaching 2:1 target).
- Guardrail: If stop-loss orders fail to place >2% of the time, trigger circuit breaker and revert to paper trading.
- Confidence: High (relies on proven OrderManager foundation, extends existing SafetyChecks patterns, aligns with Constitution §Risk_Management).

## Context Strategy & Signal Design

- **System prompt altitude**: Implementation-level Python (service layer, dataclasses, integration with OrderManager/SafetyChecks/AccountData).
- **Tool surface**: `rg` for integration points, `python -m pytest` for TDD workflow, risk simulation scripts for backtesting stop/target logic.
- **Examples in scope**:
  1. OrderManager.place_limit_sell (specs/order-management/spec.md FR-002) – reuse for stop and target orders.
  2. SafetyChecks.calculate_position_size (src/trading_bot/safety_checks.py:89-120) – extend with pullback analysis.
  3. Config.order_management (src/trading_bot/config.py:15-90) – mirror pattern for risk_management config.
  4. TradingBot.execute_trade (references in order-management spec) – integration point for RiskManager.
- **Context budget**: Target 40k tokens during implementation; trigger compaction if NOTES.md exceeds 32k tokens or when entering /optimize phase.
- **Retrieval strategy**: JIT load Constitution §Risk_Management for risk rules, reuse NOTES.md for pullback analysis decisions, load OrderManager contracts only when clarifying order placement.
- **Memory artifacts**: Update NOTES.md after pullback algorithm selection, document risk formulas in `artifacts/risk-calculations.md`, capture stop adjustment rules in `design/queries`.
- **Compaction cadence**: Summarize NOTES.md after research handoff, compact test evidence before /preview, archive verbose pullback analysis after validation.
- **Sub-agents**: `backend-dev` for implementation, `qa-test` for scenario validation and edge case testing (partial fills, simultaneous stop/target hits).

## Requirements

### Functional (testable only)

- **FR-001**: System MUST provide `calculate_position_with_stop(symbol, entry_price, account_balance, account_risk_pct, price_data)` that identifies the pullback low from recent price data (last N candles), calculates stop-loss price, computes position size using `(account_balance * risk_pct) / (entry_price - stop_price)`, calculates 2:1 target as `entry_price + 2 * (entry_price - stop_price)`, and returns a `PositionPlan` dataclass with all prices and quantities.

- **FR-002**: System MUST fall back to percentage-based stop calculation (default 2% below entry) when no pullback low is detected in price data, log a warning with details, and proceed with position sizing using the default stop distance.

- **FR-003**: System MUST validate calculated position size against available buying power and reduce quantity if needed, recalculating risk amount proportionally and logging the adjustment with original vs. adjusted values.

- **FR-004**: System MUST provide `place_trade_with_risk_management(plan: PositionPlan, symbol: str)` that (a) submits entry order via OrderManager, (b) places stop-loss sell order immediately after entry confirmation, (c) places target sell order, (d) stores all order IDs in a `RiskManagementEnvelope`, and (e) persists to `logs/risk-management.jsonl`.

- **FR-005**: System MUST reject position plans where calculated stop distance is <0.5% of entry price (too tight, likely noise) or >10% of entry price (excessive risk), returning a validation error with actionable guidance.

- **FR-006**: System MUST support configurable risk-reward ratios (default 2:1) via `min_risk_reward_ratio` config, allowing strategies to require 3:1 or higher targets if specified.

- **FR-007**: System MUST provide `adjust_trailing_stop(symbol, current_price, risk_envelope)` that cancels the existing stop order and places a new stop at (a) breakeven when price reaches 50% to target, or (b) 1:1 risk-reward when target is hit, updating the envelope with new order ID and logging the reason.

- **FR-008**: System MUST integrate with OrderManager.synchronize_open_orders() poller to detect stop or target fills, triggering callbacks that (a) cancel opposing orders, (b) update position state, (c) calculate realized P&L, and (d) emit events to TradeRecord and AccountData.

- **FR-009**: System MUST handle partial fills on stop or target orders by tracking filled vs. remaining quantity in the envelope, adjusting opposing orders proportionally, and maintaining risk-reward ratio on the remaining position.

- **FR-010**: System MUST extend Config with a `risk_management` section containing `account_risk_pct` (default 1.0), `min_risk_reward_ratio` (default 2.0), `default_stop_pct` (default 2.0), `trailing_enabled` (default true), `pullback_lookback_candles` (default 20), and support per-strategy overrides.

- **FR-011**: System MUST emit structured logs for every position plan calculation, stop/target placement, trailing adjustment, and fill detection with masked sensitive data, correlation IDs (session_id + trade_id), and risk metrics (risk_amount, risk_pct, reward_ratio).

- **FR-012**: System MUST raise `PositionPlanningError`, `StopPlacementError`, or `TargetAdjustmentError` subclasses with actionable messages when risk calculations or order placements fail.

- **FR-013**: System MUST validate that stop-loss price is below entry price for long positions and above entry price for short positions (future), rejecting invalid plans with detailed error messages.

- **FR-014**: System MUST implement `PullbackAnalyzer` that identifies swing lows by detecting price levels where subsequent candles close above the low (confirmation), prioritizing the most recent swing low within the lookback window.

### Non-Functional

- **NFR-001**: Performance: Position plan calculation (including pullback analysis) MUST complete in ≤200ms for typical price data (20-50 candles).

- **NFR-002**: Performance: Stop-loss and target orders MUST be placed within 1 second of entry fill confirmation to minimize slippage risk.

- **NFR-003**: Reliability: ≥99% of position plans MUST result in successful stop-loss order placement; failures MUST trigger entry order cancellation if unfilled.

- **NFR-004**: Observability: Logs MUST include complete risk profile (entry, stop, target, quantity, risk_amount, reward_ratio, pullback_source) for every trade with correlation to entry order ID.

- **NFR-005**: Maintainability: All new modules MUST include type hints, docstrings with risk calculation formulas, and unit tests targeting 90% coverage for core risk logic.

- **NFR-006**: Safety: Maximum risk per trade MUST never exceed configured `account_risk_pct` (e.g., 1.0%); any calculation exceeding this MUST fail-safe by rejecting the trade.

- **NFR-007**: Resilience: Stop and target placement MUST retry transient failures (network timeout, 5xx) up to 3 times before escalating to circuit breaker.

- **NFR-008**: Accuracy: Position size calculations MUST be accurate to ±1 share due to rounding, with risk amount variance ≤0.1% of target.

### Key Entities (if data involved)

- **PositionPlan**: Planning result with `symbol`, `entry_price`, `stop_price`, `target_price`, `quantity`, `risk_amount`, `reward_amount`, `reward_ratio`, `pullback_source` (detected|default).

- **RiskManagementEnvelope**: Execution record storing `entry_order_id`, `stop_order_id`, `target_order_id`, `position_plan`, `status` (pending|active|stopped|target_hit|cancelled), `created_at`, `updated_at`, `adjustments` (list of trailing stop changes).

- **PullbackData**: Analysis result with `pullback_price`, `pullback_timestamp`, `confirmation_candles`, `lookback_window`, `fallback_used` (boolean).

- **RiskManagementConfig**: Configuration dataclass with `account_risk_pct`, `min_risk_reward_ratio`, `default_stop_pct`, `trailing_enabled`, `pullback_lookback_candles`, `strategy_overrides`.

- **RiskManager**: Service orchestrating position planning, stop/target placement, trailing adjustments, and fill monitoring.

- **PullbackAnalyzer**: Component identifying swing lows from price data.

- **RiskRewardCalculator**: Component computing position size and target prices.

- **StopAdjuster**: Component managing trailing stop logic.

- **TargetMonitor**: Component polling for fills and triggering position closure.

## Deployment Considerations

### Platform Dependencies

**Python Dependencies**:
- Reuse existing `robin_stocks`, `pandas` (if price_data uses DataFrames), `pytz`.
- No new external dependencies required.

**Services**:
- Railway API service (no changes – reuses existing OrderManager broker access).
- No Vercel impact (backend-only).

### Environment Variables

**New Required Variables**:
- None (all configuration via `risk_management` section in config.json).

**Changed Variables**:
- None (extends existing config.json structure).

**Schema Update Required**: Yes – extend `Config` dataclass and `config.example.json` with `risk_management` block (account_risk_pct, min_risk_reward_ratio, default_stop_pct, trailing_enabled, pullback_lookback_candles, strategy_overrides).

### Breaking Changes

**API Contract Changes**:
- `TradingBot.execute_trade` live path will now require initialized `RiskManager` and may reject trades that don't meet risk criteria; paper trading flow remains unchanged.

**Database Schema Changes**:
- None (new risk-management logs persist to JSONL only: `logs/risk-management.jsonl`).

**Auth Flow Modifications**:
- None (depends on existing RobinhoodAuth.login() success).

**Client Compatibility**:
- Backward compatible for paper trading; live trading requires `risk_management` config block or will use hardcoded defaults (may fail validation if defaults are too conservative).

### Migration Requirements

**Configuration Updates**:
- Add `risk_management` block to config.json with recommended defaults:
  ```json
  {
    "risk_management": {
      "account_risk_pct": 1.0,
      "min_risk_reward_ratio": 2.0,
      "default_stop_pct": 2.0,
      "trailing_enabled": true,
      "pullback_lookback_candles": 20,
      "strategy_overrides": {}
    }
  }
  ```
- Document in README and QUICKSTART with risk calculation examples.

**Data Backfill**:
- Not required (new feature, no historical data to migrate).

**Operational Runbook**:
- Update incident response checklist to include `RiskManager.cancel_all_risk_orders(symbol)` command for emergency position closure.
- Add monitoring for stop-loss failure rate and target hit rate metrics.
- Document trailing stop adjustment thresholds and how to disable if causing issues.

- **RLS Policy Changes**: Not applicable (no database changes).
