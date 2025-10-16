# Feature Specification: ATR-based Dynamic Stop-Loss Adjustment

**Branch**: `atr-stop-adjustment`
**Created**: 2025-10-16
**Status**: Draft
**Area**: Risk Management
**From Roadmap**: No (Enhancement to existing stop-loss-automation)

## User Scenarios

### Primary User Story
As a trading bot operator, I need ATR-based dynamic stop-loss calculation that automatically adjusts stop distances based on market volatility, so stops widen during volatile periods to avoid premature stop-outs and tighten during calm periods for better capital protection, improving win rates and reducing unnecessary losses.

### Acceptance Scenarios
1. **Given** price data for `TSLA` shows recent ATR of `$5.20` and current entry price is `$250.30`, **When** the bot calls `calculate_atr_stop(symbol="TSLA", entry_price=250.30, atr_value=5.20, atr_multiplier=2.0)`, **Then** the system calculates stop price as `$239.90` (entry - 2.0 * ATR), validates it falls within acceptable stop distance bounds (4.2% from entry, within 0.7%-10% range), and returns an `ATRStopData` with stop_price, atr_value, multiplier, and source="atr".

2. **Given** the bot is planning a position with ATR-calculated stop at `$239.90` for entry `$250.30`, **When** it calls `calculate_position_plan(symbol="TSLA", entry_price=250.30, stop_price=239.90, account_balance=100000, risk_pct=1.0, atr_enabled=true)`, **Then** the system calculates position size as `96 shares` (risk $1000 over $10.40 distance), computes 2:1 target at `$271.10`, logs "stop_source=atr, atr_value=5.20, atr_multiplier=2.0" to risk-management.jsonl, and returns a PositionPlan with pullback_source="atr".

3. **Given** price data for `NVDA` has only 8 candles available (less than required 14-period ATR), **When** the bot attempts ATR calculation with `calculate_atr_from_bars(price_bars, period=14)`, **Then** the system raises `ATRCalculationError` with message "Insufficient data: 8 bars available, 14 required for ATR(14)", logs the failure with symbol and bar count, and the calling code falls back to pullback or percentage-based stop calculation.

4. **Given** ATR calculation for `AAPL` produces stop distance of 0.3% (too tight, likely low-volatility period with small ATR), **When** the system validates the ATR-based stop with `validate_stop_distance(entry=180.50, stop=180.00)`, **Then** it raises `PositionPlanningError` with "Stop distance 0.3% is too tight (minimum: exactly 0.5% or >= 0.7%)", logs the rejection with ATR details, and falls back to default 2% stop OR skips the trade if no fallback configured.

5. **Given** a live position in `MSFT` with ATR-based initial stop and ATR now increased by 40% due to earnings volatility, **When** the `StopAdjuster` recalculates with `adjust_stop_with_atr(current_price=420.00, position_plan, latest_atr=8.50)` and position has reached 50% to target, **Then** the system compares ATR-adjusted stop ($420.00 - 2.0 * 8.50 = $403.00) with breakeven stop ($410.00 entry), chooses the wider stop ($403.00) to accommodate increased volatility, updates the stop order, logs "adjusted for ATR increase from 6.50 to 8.50", and updates RiskManagementEnvelope.

### Edge Cases
- What happens if ATR is zero or negative due to data errors? → Raise ATRCalculationError, log the invalid data with details, fall back to percentage-based stop, and emit warning to caller.
- How does the system handle ATR that results in stop distance >10% (excessive risk)? → Validate in `validate_stop_distance`, reject the position plan with actionable error, log the rejection with ATR value and calculated distance, suggest increasing account risk or reducing multiplier.
- What if ATR calculation succeeds but MarketDataService provides stale price data (>15 minutes old)? → Validate timestamps in price bars, raise `StaleDataError` if any bar is older than threshold, fall back to cached ATR if available within tolerance, otherwise skip trade.
- How are ATR-based stops integrated with existing pullback analysis? → ATR is a separate stop source; when atr_enabled=true, ATR calculation takes precedence; pullback analysis remains available as fallback or alternative strategy via configuration.
- What happens during extended low-volatility periods where ATR suggests <0.7% stop? → System rejects the stop as "too tight", logs the rejection, and uses configurable fallback (percentage-based stop OR skip trade with warning).

## Visual References
N/A - backend service (no UI components).

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce premature stop-outs from volatility spikes | % of stopped-out trades where price returned to profit within 1 hour | <= 15% false stops | > 25% indicates poor ATR calibration |
| **Engagement** | Increase adoption of volatility-aware stops | % of live trades using ATR stops vs fixed stops | >= 60% ATR adoption after 2 weeks | < 40% adoption triggers review |
| **Adoption** | Ensure ATR calculation is reliable | ATR calculation success rate (valid ATR / attempts) | >= 95% success rate | < 90% for 2 days triggers data quality review |
| **Retention** | Maintain capital protection effectiveness | % of ATR-stopped trades that honor max risk limit | >= 99% within risk tolerance | > 2% exceeding risk triggers incident |
| **Task Success** | Improve win rate vs fixed stops | % of ATR-based positions reaching target vs stopped out | >= 45% target hit rate (vs 40% baseline) | < 38% for 30 trades triggers strategy review |

**Performance Targets**:
- ATR calculation (14-period from price bars) completes in <50ms for typical dataset (20-50 candles).
- Position plan with ATR stop completes in <250ms (including ATR calculation + validation).
- Stop adjustment with ATR recalculation executes in <100ms for live position monitoring.
- ATR-based stops must never exceed 10% distance OR fall below 0.7% distance (safety bounds).

## Hypothesis

**Problem**: Current stop-loss system uses fixed percentage stops (2% default) or pullback-based stops that don't adapt to market volatility, causing premature stop-outs in high-volatility environments and inadequate protection in low-volatility periods.
- Evidence: Existing stop-loss-automation (specs/stop-loss-automation/spec.md) implements pullback detection and 2% fallback, but no volatility adjustment.
- Evidence: StopAdjuster (src/trading_bot/risk_management/stop_adjuster.py) uses fixed trailing percentages (activation_pct=10%, trailing_distance_pct=5%).
- Evidence: Volatile stocks like TSLA with daily ranges of 5-8% frequently hit 2% stops prematurely, while low-volatility stocks like KO with 1% ranges get inadequate protection.
- Impact: Estimated 20-30% of stopped-out trades in volatile markets could have been winners with wider stops; conversely, calm-market positions risk excessive drawdown with fixed 2% stops.

**Solution**: Add ATR-based stop calculation that dynamically adjusts stop distance using Average True Range (volatility indicator) multiplied by a configurable factor.
- Change: Create `ATRCalculator` component to compute ATR from price data (high, low, close over N periods, typically 14).
- Change: Enhance `calculate_position_plan()` to accept optional ATR data and use ATR-based stop when `atr_enabled=true` in config.
- Change: Extend `StopAdjuster` to recalculate stops using current ATR when volatility changes significantly (>20% ATR change).
- Change: Add configuration: `atr_enabled` (bool), `atr_period` (int, default 14), `atr_multiplier` (float, default 2.0) to RiskManagementConfig.
- Change: Maintain backward compatibility - pullback/percentage stops remain default; ATR is opt-in enhancement.
- Mechanism: In volatile markets (high ATR), stop distance widens automatically (e.g., 2.0 * $5.20 ATR = $10.40 stop distance); in calm markets (low ATR), stops tighten (e.g., 2.0 * $2.00 ATR = $4.00 stop distance).

**Prediction**: ATR-based stops will reduce premature stop-outs in volatile markets while maintaining capital protection, improving overall win rate and risk-adjusted returns.
- Primary metric: Target hit rate >= 45% for ATR-based positions (up from 40% baseline with fixed stops).
- Expected improvement: -30% reduction in false stop-outs (premature stops where price reversed to profit).
- Secondary metric: Average stop distance adapts to volatility - volatile stocks get 3-6% stops, low-volatility stocks get 1-2.5% stops.
- Guardrail: ATR calculation success rate >= 95%; if ATR data unavailable, system falls back gracefully to pullback/percentage stops.
- Confidence: High (ATR is industry-standard volatility indicator; reuses proven risk management infrastructure from stop-loss-automation).

## Context Strategy & Signal Design

- **System prompt altitude**: Implementation-level Python (service layer, ATR calculation logic, integration with existing Calculator and StopAdjuster).
- **Tool surface**: `rg` for integration points in risk_management package, `python -m pytest` for TDD workflow, ATR calculation validation scripts.
- **Examples in scope**:
  1. Calculator.calculate_position_plan (src/trading_bot/risk_management/calculator.py:194-264) - extend with atr_data parameter.
  2. StopAdjuster.calculate_adjustment (src/trading_bot/risk_management/stop_adjuster.py:74-108) - integrate ATR recalculation logic.
  3. RiskManagementConfig (src/trading_bot/risk_management/config.py) - add ATR configuration fields.
  4. MarketDataService (src/trading_bot/market_data/market_data_service.py) - source of price bars for ATR calculation.
- **Context budget**: Target 50k tokens during implementation; trigger compaction if NOTES.md exceeds 40k tokens or when entering /optimize phase.
- **Retrieval strategy**: JIT load Constitution §Risk_Management for validation rules, reuse NOTES.md for ATR formula decisions, load Calculator contracts only when clarifying position plan integration.
- **Memory artifacts**: Update NOTES.md with ATR calculation formula validation, document stop distance bounds in `artifacts/atr-calculations.md`, capture ATR multiplier rationale in `design/queries`.
- **Compaction cadence**: Summarize NOTES.md after research handoff, compact test evidence before /preview, archive verbose ATR formula derivations after validation.
- **Sub-agents**: `backend-dev` for implementation, `qa-test` for scenario validation and edge case testing (insufficient data, extreme ATR values, data staleness).

## Requirements

### Functional (testable only)

- **FR-001**: System MUST provide `calculate_atr_from_bars(price_bars: List[PriceBar], period: int = 14)` that computes Average True Range by calculating true range for each bar (max of high-low, |high-prev_close|, |low-prev_close|), averaging over the specified period, and returning a Decimal ATR value with precision to 2 decimal places.

- **FR-002**: System MUST validate ATR calculation inputs by checking that price_bars list has length >= period (e.g., 14 bars for 14-period ATR), each bar has valid high/low/close prices (non-negative, high >= low), and timestamps are sequential, raising `ATRCalculationError` with actionable message if validation fails.

- **FR-003**: System MUST provide `calculate_atr_stop(entry_price: Decimal, atr_value: Decimal, atr_multiplier: float, direction: str = "long")` that calculates stop price as entry_price - (atr_value * atr_multiplier) for long positions, validates the result against stop distance bounds (0.7%-10%), and returns `ATRStopData` with stop_price, atr_value, multiplier, and source="atr".

- **FR-004**: System MUST extend `calculate_position_plan()` to accept optional `atr_data: Optional[ATRStopData]` parameter that, when provided and `atr_enabled=true` in config, uses atr_data.stop_price instead of pullback or percentage-based stop, updates PositionPlan.pullback_source to "atr", and logs ATR details (value, multiplier) to risk-management.jsonl.

- **FR-005**: System MUST fall back to percentage-based stop calculation when ATR calculation fails due to insufficient data, invalid values, or stale timestamps, logging the fallback reason with ATR error details, and proceeding with default 2% stop OR pullback-based stop based on configuration priority.

- **FR-006**: System MUST validate ATR-based stop distance against existing bounds (must be exactly 0.5% OR >= 0.7% and <= 10% of entry price), rejecting stops that fall outside acceptable range with `PositionPlanningError` detailing the ATR value, multiplier, and calculated distance, and suggesting configuration adjustments.

- **FR-007**: System MUST extend `StopAdjuster.calculate_adjustment()` to support ATR-based stop recalculation by accepting optional `current_atr: Optional[Decimal]` parameter that, when provided and ATR has changed by >20% from initial, recalculates stop using new ATR value, compares with breakeven/trailing stops, selects the widest (most protective) stop, and returns adjustment with reason "adjusted for ATR change".

- **FR-008**: System MUST extend RiskManagementConfig with ATR configuration fields: `atr_enabled: bool` (default false), `atr_period: int` (default 14), `atr_multiplier: float` (default 2.0), `atr_recalc_threshold: float` (default 0.20 for 20% change), supporting per-strategy overrides via `strategy_overrides` dict.

- **FR-009**: System MUST log ATR calculation details for every position plan using ATR stops, including symbol, atr_value, atr_period, atr_multiplier, calculated_stop_price, stop_distance_pct, and fallback_used (bool), to `logs/risk-management.jsonl` with correlation ID (session_id + trade_id).

- **FR-010**: System MUST handle missing or incomplete price data gracefully by attempting ATR calculation, catching `ATRCalculationError` if insufficient bars, logging the data availability issue (bars available vs required), and falling back to pullback or percentage-based stop without halting trade execution.

- **FR-011**: System MUST validate price bar timestamps to detect stale data by checking that the most recent bar is within a configurable threshold (default 15 minutes for live trading, 1 day for backtesting), raising `StaleDataError` if data is too old, and logging the staleness details (latest timestamp, current time, threshold).

- **FR-012**: System MUST emit structured error events for ATR failures subclassed from `PositionPlanningError`: `ATRCalculationError` (insufficient data, invalid values), `ATRValidationError` (stop distance out of bounds), `StaleDataError` (price data too old), each with actionable error messages and diagnostic fields (symbol, bar_count, atr_value, stop_distance_pct).

- **FR-013**: System MUST support testing and backtesting by allowing ATR calculation from historical price data, accepting price_bars with any timestamp range, and returning deterministic ATR values for the same input data (no reliance on real-time API calls during testing).

- **FR-014**: System MUST document ATR calculation formula and rationale in code docstrings, including the three true range components (high-low, |high-prev_close|, |low-prev_close|), averaging method (simple moving average over period), and multiplier application (stop = entry - multiplier * ATR for longs).

### Non-Functional

- **NFR-001**: Performance: ATR calculation from 20-50 price bars (typical dataset) MUST complete in <= 50ms to avoid slowing position planning.

- **NFR-002**: Performance: Position plan calculation with ATR stop (including ATR calculation + validation) MUST complete in <= 250ms, maintaining compatibility with existing 200ms target for non-ATR plans.

- **NFR-003**: Reliability: ATR calculation success rate MUST be >= 95% in live trading (excluding cases where data genuinely unavailable), with failures triggering fallback to alternative stop methods rather than blocking trades.

- **NFR-004**: Observability: Logs MUST include complete ATR diagnostic information (value, period, multiplier, bar count, timestamps) for every position plan attempt, enabling post-trade analysis of stop effectiveness and ATR calibration.

- **NFR-005**: Maintainability: ATR calculation logic MUST be isolated in a dedicated `ATRCalculator` class with unit tests covering edge cases (insufficient data, zero ATR, extreme values, missing bars), targeting 90% coverage for ATR-specific code.

- **NFR-006**: Safety: ATR-based stops MUST never exceed 10% distance from entry price (maximum risk bound) OR fall below 0.7% distance (minimum noise threshold), with validation enforced before position plan approval.

- **NFR-007**: Resilience: System MUST handle ATR calculation failures gracefully by falling back to pullback or percentage-based stops, logging the fallback reason, and continuing trade execution without manual intervention.

- **NFR-008**: Accuracy: ATR calculations MUST be accurate to ±$0.01 (1 cent precision) compared to reference implementations (e.g., pandas-ta, ta-lib), validated through unit tests against known ATR values for sample datasets.

### Key Entities (if data involved)

- **ATRStopData**: ATR-based stop calculation result with `stop_price` (Decimal), `atr_value` (Decimal), `atr_multiplier` (float), `atr_period` (int), `source` ("atr"), `calculation_timestamp` (datetime).

- **PriceBar**: Market data point for ATR calculation with `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume` (reuses existing MarketData entity from market_data package).

- **ATRCalculator**: Component responsible for ATR calculation from price bars, validation, and error handling.

- **RiskManagementConfig** (extended): Adds `atr_enabled`, `atr_period`, `atr_multiplier`, `atr_recalc_threshold` fields to existing configuration dataclass.

- **PositionPlan** (extended): `pullback_source` field now accepts "atr" value in addition to existing "detected", "default", "manual".

- **ATRCalculationError**: Exception raised when ATR calculation fails due to insufficient data, invalid values, or data quality issues.

- **ATRValidationError**: Exception raised when ATR-based stop falls outside acceptable distance bounds (0.7%-10%).

- **StaleDataError**: Exception raised when price bar timestamps indicate data is too old for reliable ATR calculation.

## Deployment Considerations

### Platform Dependencies

**Python Dependencies**:
- Reuse existing `pandas` (if price_data uses DataFrames for ATR calculation), `pytz` for timestamp handling.
- No new external dependencies required (ATR calculation implemented in pure Python/Decimal for accuracy).

**Services**:
- Railway API service (no changes - reuses existing MarketDataService for price bars).
- No Vercel impact (backend-only).

### Environment Variables

**New Required Variables**:
- None (all configuration via `risk_management.atr_*` section in config.json).

**Changed Variables**:
- None (extends existing risk_management config structure).

**Schema Update Required**: Yes - extend `Config` dataclass and `config.example.json` with ATR fields under `risk_management` block: `atr_enabled`, `atr_period`, `atr_multiplier`, `atr_recalc_threshold`.

### Breaking Changes

**API Contract Changes**:
- `calculate_position_plan()` signature extends with optional `atr_data` parameter (backward compatible - defaults to None).
- `StopAdjuster.calculate_adjustment()` extends with optional `current_atr` parameter (backward compatible - defaults to None).
- Existing code continues working without changes; ATR features opt-in via configuration.

**Database Schema Changes**:
- None (ATR data persists to JSONL logs only: `logs/risk-management.jsonl`).

**Auth Flow Modifications**:
- None (depends on existing RobinhoodAuth.login() success).

**Client Compatibility**:
- Fully backward compatible - ATR stops are opt-in via `atr_enabled=true` in config; existing pullback/percentage stops remain default behavior.

### Migration Requirements

**Configuration Updates**:
- Add `atr_*` fields to `risk_management` block in config.json:
  ```json
  {
    "risk_management": {
      "account_risk_pct": 1.0,
      "min_risk_reward_ratio": 2.0,
      "default_stop_pct": 2.0,
      "trailing_enabled": true,
      "pullback_lookback_candles": 20,
      "atr_enabled": false,
      "atr_period": 14,
      "atr_multiplier": 2.0,
      "atr_recalc_threshold": 0.20,
      "strategy_overrides": {}
    }
  }
  ```
- Document ATR configuration in README with examples for volatile vs low-volatility stocks.

**Data Backfill**:
- Not required (new feature, no historical data to migrate).

**Operational Runbook**:
- Update incident response checklist to include ATR calculation failure scenarios and fallback verification.
- Add monitoring for ATR calculation success rate and stop distance distribution metrics.
- Document ATR multiplier tuning guidance (2.0 standard, 1.5 for tighter stops, 2.5-3.0 for very volatile stocks).

**Reversibility**:
- Fully reversible - set `atr_enabled=false` in config to revert to pullback/percentage stops immediately (no data migration required).

### Rollback Considerations

**Standard Rollback**:
- Yes - 3-command rollback via standard process (revert commit, redeploy, verify logs).

**Special Rollback Needs**:
- None - ATR feature is isolated in risk_management package; disabling via config sufficient for immediate reversion.
- Feature flag pattern: Use `atr_enabled` config flag for gradual rollout and instant rollback without code deployment.

**Deployment Metadata**:
- Track ATR adoption rate and effectiveness metrics in NOTES.md after deployment (target hit rate, false stop rate, ATR calculation success rate).

---

## Quality Gates (all must pass before /plan)

### Core Requirements
- [x] No implementation details (ATR calculation described at formula level, not code)
- [x] Requirements testable and unambiguous (FR-001 to FR-014 specify inputs/outputs/validations)
- [x] Context strategy documented (TDD workflow, integration points identified)
- [x] No [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (§Risk_Management: stops required, §Safety_First: fail-safe fallbacks, §Data_Integrity: timestamp validation)

### Success Metrics (HEART)
- [x] All 5 HEART dimensions have targets defined (Happiness: <=15% false stops, Engagement: >=60% adoption, Adoption: >=95% ATR success, Retention: >=99% risk compliance, Task Success: >=45% target hit rate)
- [x] Metrics are Claude Code-measurable (logs/risk-management.jsonl, trade outcome tracking)
- [x] Hypothesis is specific and testable (-30% false stop-outs, +5% target hit rate)
- [x] Performance targets specified (ATR calc <50ms, position plan <250ms)

### Screens (UI Features Only)
- [x] No UI components - backend service only (skip)

### Measurement Plan
- [x] Analytics events defined (ATR calculation success/failure, stop placement with ATR details, stop-out events with price reversal tracking)
- [x] Log queries specified (ATR success rate, stop distance distribution, false stop analysis)
- [x] Measurement sources are Claude Code-accessible (logs/risk-management.jsonl, structured logging)

### Deployment Considerations
- [x] Platform dependencies documented (no new dependencies, reuses pandas/pytz)
- [x] Environment variables listed (no new env vars, config.json extension only)
- [x] Breaking changes identified (none - fully backward compatible, opt-in via config)
- [x] Migration requirements documented (config.json update only, no data migration)
- [x] Rollback plan specified (standard rollback OR config flag atr_enabled=false)
