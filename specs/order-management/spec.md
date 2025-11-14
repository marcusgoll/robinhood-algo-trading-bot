# Feature Specification: Order Management Foundation

**Branch**: `order-management`
**Created**: 2025-10-10
**Status**: Draft
**Area**: API
**From Roadmap**: Yes (Impact: 5, Effort: 3, Confidence: 0.8, Score: 1.33)

## User Scenarios

### Primary User Story
As a trading bot operator, I need a resilient order management service that can submit, cancel, and
track limit orders with configurable offsets so the bot can execute live trades safely without manual
intervention.

### Acceptance Scenarios
1. **Given** the bot is authenticated and live trading is enabled, **When** the strategy requests a
   limit BUY for `TSLA` with quantity `50`, reference price `$250.30`, and the config buy offset is
   `15` basis points, **Then** the service computes a limit price of `$249.93` (rounded to broker
   precision), submits it via `robin_stocks.orders.order_buy_limit`, and returns an order envelope
   containing the broker order id, computed limit price, and submission timestamp.
2. **Given** a position exit requires a limit SELL, **When** the bot calls
   `place_limit_sell(symbol="TSLA", quantity=50, reference_price=252.10)` and the sell offset is
   configured as `$0.04`, **Then** the order manager submits a limit sell at `$252.14`, records the
   `order_id`, and logs the action with structured metadata for downstream reconciliation.
3. **Given** multiple open orders exist across symbols, **When** `/phase-1-ship` triggers the kill
   switch and calls `cancel_all_open_orders()`, **Then** the service retrieves all open equity orders,
   issues cancel requests, confirms cancellations (or partial fills), and clears matching entries from
   `SafetyChecks._pending_orders`.
4. **Given** a strategy polls an order after partial fills, **When** `get_order_status(order_id)`
   executes, **Then** it returns a dataclass with current state (`partially_filled`), filled quantity,
   average fill price, last update timestamp, and raw payload snapshot for audit.
5. **Given** `robin_stocks` returns a network timeout, **When** a submission attempt fails after the
   configured retries, **Then** the service raises a domain `OrderSubmissionError`, logs the failure
   with masked payload, leaves SafetyChecks state untouched, and surfaces actionable guidance to the
   caller.

### Edge Cases
- What happens when the computed limit price is ≤0 or rounds below exchange minimum? → Reject the
  order and surface a validation error.
- How does the system react if an order fills while cancellations are processing? → Treat as filled,
  capture final fill info, and skip redundant cancellation calls.
- How are duplicate submissions prevented if the caller retries immediately? → Reuse the pending
  order cache keyed by symbol + side + normalized price to ensure idempotency.
- What is the strategy when Robinhood reports `rejected` with `insufficient_funds`? → Bubble the
  status to caller, trigger SafetyChecks circuit breaker, and do not retry automatically.
- How are fractional shares or options tickers handled? → Validate inputs against equity-only rules
  (integer quantity, uppercase ticker) and decline unsupported asset classes.

## Visual References
N/A – backend service (no UI components).

## Success Metrics (HEART Framework)

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce manual trading interventions | Count of `manual_override=true` events in trade logs | ≤1 per trading week | >3 in a week triggers postmortem |
| **Engagement** | Keep automation as primary execution path | Share of live trades executed via OrderManager | ≥95% automated | <90% for 2 days triggers rollback |
| **Adoption** | Ensure all live strategies use the module | Callers using `OrderManager` APIs vs legacy stubs | 100% of live pathways | Track weekly until parity confirmed |
| **Retention** | Maintain reliable submissions | `% of submitted orders returning broker status success` | ≥99% success rate | <97% requires incident review |
| **Task Success** | Deliver timely submissions | `P95 order_submission_duration_ms` from logs | ≤750 ms | >1500 ms sustained 10 min triggers alert |

**Performance Targets**:
- Cancel all open equity orders (≤25 orders) in under 5 seconds end-to-end.
- Status poller detects fills within 15 seconds of broker update.
- Order manager adds <5% overhead to `TradingBot.execute_trade` paper-mode path.

## Hypothesis

**Problem**: Live trading currently lacks a production-ready order path, forcing manual execution and
disjointed safety coordination.
- Evidence: `TradingBot.execute_trade` logs a TODO instead of calling the broker
  (src/trading_bot/bot.py:445-450).
- Evidence: Safety checks track pending orders but cannot release them without order lifecycle hooks
  (src/trading_bot/safety_checks.py:129-223).
- Evidence: Incident notes show repeated manual order adjustments due to offset slippage (roadmap
  feedback, `order-management` entry).
- Impact: Live execution, safety, analytics, and downstream reporting all depend on accurate order
  state.

**Solution**: Introduce a dedicated `OrderManager` service that encapsulates broker communication,
offset logic, cancellation, and status tracking.
- Change: Create `src/trading_bot/order_management/` package with `OrderManager`, request/response
  dataclasses, and Robinhood gateway adapters.
- Change: Extend `Config` to expose `order_management` offsets and retry policies with sane defaults.
- Change: Update `TradingBot.execute_trade` to delegate live submissions to the order manager while
  retaining paper trading flow.
- Change: Wire cancellation hooks to SafetyChecks and AccountData cache invalidation paths.
- Mechanism: Reuse shared error handling decorators for retry, and structured logging for audit.

**Prediction**: Centralized order management will enable safe live execution with measurable
reliability improvements.
- Primary metric: Broker-confirmed submission success ≥99% (currently 0% because no live path).
- Expected improvement: Reduce manual overrides from daily to ≤1 per week (≥80% reduction).
- Secondary metric: Median time from strategy signal to broker acknowledgement <400 ms.
- Confidence: Medium-high (relies on tested robin_stocks APIs and existing auth/risk primitives).

## Context Strategy & Signal Design

- **System prompt altitude**: Implementation-level Python (service layer patterns, dataclasses,
  robin_stocks API usage, integration with existing safety modules).
- **Tool surface**: `rg` for locating integration points, `python -m` for smoke tests, order
  simulation scripts for dry runs (`paper_trading` mode).
- **Examples in scope**:
  1. `TradingBot.execute_trade` live-mode branch (src/trading_bot/bot.py:319-456).
  2. SafetyChecks duplicate prevention (src/trading_bot/safety_checks.py:129-223).
  3. robin_stocks order helpers (`order_buy_limit`, `order_sell_limit`, `cancel_all_stock_orders`).
- **Context budget**: Target 35k tokens during implementation; trigger compaction if NOTES.md exceeds
  28k tokens or when entering /implement phase.
- **Retrieval strategy**: JIT load constitution excerpts for safety rules, reuse NOTES.md for config
  assumptions, fetch broker docs only when clarifying payload fields.
- **Memory artifacts**: Update NOTES.md after API contract decisions, log mappings in
  `artifacts/order-status-matrix.md`, capture offset calculations in `design/queries`.
- **Compaction cadence**: Summarize NOTES.md after research handoff, summarize testing evidence before
  /preview.
- **Sub-agents**: `backend-dev` for implementation, `qa-test` for scenario validation and cancellation
  race testing.

## Requirements

### Functional (testable only)

- **FR-001**: System MUST provide `place_limit_buy()` that accepts `symbol`, `quantity`,
  `reference_price`, and computes the broker limit price using config-driven buy offsets (bps or
  absolute), rounding to two decimals and rejecting invalid inputs.
- **FR-002**: System MUST provide `place_limit_sell()` with symmetric sell offset logic, ensuring the
  computed price is ≥ reference price and ≤ configured slippage guard.
- **FR-003**: System MUST load order offsets from `Config.order_management` with validation and
  defaults (`offset_mode={"bps"|"absolute"}`, `buy_offset=15`, `sell_offset=10`,
  `max_slippage_pct=0.5`) and support optional per-strategy overrides (`strategy_overrides` block)
  that fall back to the global defaults when unspecified.
- **FR-004**: System MUST record each submitted order in an `OrderEnvelope` (order id, symbol, side,
  quantity, limit price, submitted_at, paper/live flag) and persist to `logs/orders.jsonl`.
- **FR-005**: System MUST expose `get_order_status(order_id: str) -> OrderStatus` returning state
  (`queued`, `partially_filled`, `filled`, `cancelled`, `rejected`), filled quantity, average fill
  price, and raw response metadata.
- **FR-006**: System MUST expose `cancel_all_open_orders()` that cancels every open equity order,
  returns per-order results, and clears/updates SafetyChecks pending cache for affected symbols.
- **FR-007**: System MUST provide `synchronize_open_orders()` (poller) that refreshes open order state
  at configurable intervals (default 15s) and invokes callbacks when fills complete.
- **FR-008**: System MUST integrate with the error handling framework so broker calls retry up to 3
  times with exponential backoff and categorize unrecoverable failures.
- **FR-009**: System MUST update `TradingBot.execute_trade` so live submissions route through
  `OrderManager`, while paper trading continues to short-circuit without hitting the broker.
- **FR-010**: System MUST emit structured logs per submission/cancel/query with masked sensitive data
  and correlation ids (session id + order id) for audit.
- **FR-011**: System MUST invalidate AccountData caches (`buying_power`, `positions`) after fills or
  cancellations to keep downstream metrics fresh.
- **FR-012**: System MUST raise `OrderSubmissionError`, `OrderCancellationError`, or
  `OrderStatusError` subclasses with actionable messages when broker operations fail.

- **FR-014**: System MUST reject stop and market order types in this phase by returning a structured
  `NotImplemented` response with guidance to use limit orders (paper mode remains unaffected).

### Non-Functional

- **NFR-001**: Performance: P95 order submission latency (client to broker response) MUST be ≤750 ms
  on paper accounts and ≤1 s on live accounts.
- **NFR-002**: Reliability: ≥99% of broker responses MUST be captured and persisted even when retries
  exhaust.
- **NFR-003**: Observability: Logs MUST mask usernames/device tokens and include `order_id`, `symbol`,
  `side`, `limit_price`, `attempt`, and `latency_ms`.
- **NFR-004**: Maintainability: All new modules MUST include type hints, docstrings, and unit tests
  targeting 90% coverage for core logic.
- **NFR-005**: Safety: Duplicate order prevention MUST remain effective; submitting an order for a
  symbol already pending MUST return an idempotent response instead of firing a second broker call.
- **NFR-006**: Resilience: Cancellation and status APIs MUST retry transient network failures (timeout
  or 5xx) up to 3 times before escalating.

### Key Entities (if data involved)

- **OrderRequest**: Incoming intent with `symbol`, `quantity`, `side`, `reference_price`,
  `time_in_force`, `extended_hours`.
- **PriceOffsetConfig**: Configuration dataclass describing `offset_mode`, `buy_offset`,
  `sell_offset`, `max_slippage_pct`.
- **OrderEnvelope**: Submission record storing broker order id, limit price, timestamps, execution
  mode, and raw payload snapshot.
- **OrderStatus**: Normalized status with `state`, `filled_quantity`, `average_fill_price`,
  `pending_quantity`, `updated_at`, `raw`.
- **OrderManager**: Service orchestrating submissions, cancellations, polling, and integration hooks.

## Deployment Considerations

### Platform Dependencies

**Python Dependencies**:
- Reuse existing `robin_stocks` dependency; verify version ≥3.1 for consistent order APIs.
- Optional: add lightweight rate limiter helper (evaluate before implementation).

**Services**:
- Railway API service must expose network egress to Robinhood endpoints.
- No Vercel impact (backend-only).

### Environment Variables

**New Required Variables**:
- None (offsets reside in config.json via `order_management` section).

**Changed Variables**:
- None (ensure documentation highlights dependence on existing Robinhood credentials).

**Schema Update Required**: Yes – extend `Config` dataclass and `config.example.json` with
`order_management` settings (offsets, retry policy, poll interval).

### Breaking Changes

**API Contract Changes**:
- `TradingBot.execute_trade` live path signature unchanged but now requires an initialized
  `OrderManager`; ensure constructor wiring provides backward-compatible defaults.

**Database Schema Changes**:
- None (new order log persists to JSONL only).

**Auth Flow Modifications**:
- None beyond depending on `RobinhoodAuth.login()` success prior to submission.

**Client Compatibility**:
- Backward compatible for paper trading; live trading requires config upgrades described above.

### Migration Requirements

**Configuration Updates**:
- Add `order_management` block to config.json with offsets and poll interval defaults.
- Document new settings in README and QUICKSTART.

**Data Backfill**:
- Not required (paper trading logs may optionally be migrated to new JSONL schema).

**Operational Runbook**:
- Update incident response checklist to include `cancel_all_open_orders` command and log locations.

- **RLS Policy Changes**: Not applicable.
