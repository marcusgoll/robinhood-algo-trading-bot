# Implementation Plan: Order Management Foundation

## Summary
- Deliver a production-ready order pipeline for the trading bot that computes configurable limit
  prices, submits them via `robin_stocks`, cancels in-flight orders, and exposes normalized status
  tracking.
- Reuse existing safety primitives (`SafetyChecks`, `AccountData`, structured logging, error handling)
  so live trading inherits duplicate-prevention, cache invalidation, and retry behavior without new
  risk surfaces.
- Ship the feature behind configuration defaults that keep limit orders as the only supported type,
  with optional per-strategy offset overrides so strategies can tune aggressiveness without code
  changes.

Spec reference: `specs/order-management/spec.md`

## Technical Context
- **Language/Runtime**: Python 3.11 (project standard)
- **Key Dependencies**: `robin_stocks` (existing), `src/trading_bot/error_handling.with_retry`
- **Storage**: JSONL trade logs (`logs/` directory); no database impact
- **Testing Stack**: `pytest`, `unittest.mock`, existing fixtures in `tests/`
- **Execution Environment**: Railway-hosted API worker (same as trading bot runtime)
- **Performance Goals**: Submission latency ≤750 ms P95, cancel batch ≤5 s, poll interval 15 s
- **Constraints**: Must respect Constitution (§Safety_First, §Audit_Everything, §Security) and stay
  backward compatible with paper trading mode

## Research Decisions
1. **Dedicated order_management package**  
   - *Decision*: Create `src/trading_bot/order_management/` with `models.py`, `manager.py`,
     `gateways.py`.  
   - *Rationale*: Keeps broker integration isolated, simplifies mocking, aligns with existing module
     layout (see `account/`, `auth/`).  
   - *Source*: Code scan of `src/trading_bot` modules.

2. **Reuse error_handling retry decorator**  
   - *Decision*: Wrap all broker calls with `error_handling.retry.with_retry` using default policy.  
   - *Rationale*: Satisfies FR-008 without reinventing backoff; leverages circuit breaker telemetry.  
   - *Source*: `src/trading_bot/error_handling/retry.py`.

3. **Per-strategy offset overrides via config**  
   - *Decision*: Extend `Config` with `order_management` block (`offset_mode`, `buy_offset`,
     `sell_offset`, `max_slippage_pct`, optional `strategy_overrides`).  
   - *Rationale*: Meets FR-003 global defaults while enabling strategy-specific tuning.  
   - *Source*: Spec decision + `config.py` pattern for nested dataclasses.

4. **Limit-only v1 scope**  
   - *Decision*: Explicitly reject stop/market orders with structured `NotImplemented` errors while
     logging attempts.  
   - *Rationale*: Controls complexity (no stop triggers) and meets FR-014.  
   - *Source*: Team recommendation captured in NOTES.md decisions.

5. **Structured order logging**  
   - *Decision*: Write `logs/orders.jsonl` entries that complement `StructuredTradeLogger`.  
   - *Rationale*: Supports audit trails (FR-004/FR-010) without altering existing trade log schema.  
   - *Source*: Logging patterns in `src/trading_bot/logging/structured_logger.py`.

## Architecture Decisions
- **Module Layout**  
  ```
  src/trading_bot/order_management/
    __init__.py
    models.py              # OrderRequest, PriceOffsetConfig, OrderEnvelope, OrderStatus
    calculator.py          # Price calculations, offset application, validation
    gateways.py            # Robinhood gateway functions, wrapped with @with_retry
    manager.py             # OrderManager service (submit, cancel, status, synchronize)
  ```
- **Configuration**  
  - Extend `Config` dataclass with nested `OrderManagementConfig`.  
  - Load from `config.json` under `"order_management"` block, plus optional
    `"strategy_overrides": {"bull_flag_breakout": {...}}`.  
  - Provide sane defaults when block absent to avoid breaking paper users.

- **Integration Points**  
  - `TradingBot.__init__`: Instantiate `OrderManager` when `auth` is available and pass dependencies
    (config, auth, account_data, safety_checks, structured_logger/session metadata).  
  - `TradingBot.execute_trade`:  
    - Paper mode: unchanged (log + short-circuit).  
    - Live mode: delegate to `OrderManager.place_limit_order(...)`, handle envelope + errors, update
      SafetyChecks pending state, and preserve structured logging.  
  - `SafetyChecks`: add helper methods (`register_pending`, `clear_pending`) or reuse existing map
    with new calls from order manager on submission/cancel/fill.  
  - `AccountData`: reuse `invalidate_cache` calls on fills/cancels (FR-011).

- **Error Handling**  
  - Custom exceptions in `order_management/exceptions.py` deriving from `RetriableError` /
    `OrderError`.  
  - Map robin_stocks responses to these exceptions before raising.

- **Logging & Observability**  
  - Use existing `logger = logging.getLogger(__name__)` pattern.  
  - Order JSONL entries include: session_id, order_id, symbol, side, limit_price, quantity, mode,
    attempt, latency_ms, status transitions.

## Implementation Phases

### Phase A: Configuration & Data Shapes
1. Introduce `OrderManagementConfig` dataclass in `src/trading_bot/config.py` with validation and
   defaults; update `Config.from_env_and_json` to hydrate it.  
2. Extend `config.example.json` with `"order_management"` block (offset mode, offsets, poll interval,
   retry policy knobs) and document overrides.  
3. Add unit tests covering defaults, overrides, and invalid payloads (`tests/test_config.py` or new
   module).

### Phase B: Core Order Models & Calculator
1. Create `models.py` with dataclasses for requests, envelopes, status objects, and conversion helpers.  
2. Implement `calculator.py` that:  
   - Applies offsets (bps or absolute) with rounding and slippage guard.  
   - Validates ticker (`str.isalpha()`, uppercase), quantity (>0 int), reference price (>0).  
   - Exposes helper to select per-strategy override or fallback to global config.  
3. Unit tests for price math, slippage guard, override precedence, invalid input rejection.

### Phase C: Robinhood Gateway & Exceptions
1. Add `exceptions.py` with `OrderError`, `OrderSubmissionError`, `OrderCancellationError`,
   `OrderStatusError`, `UnsupportedOrderTypeError`.  
2. Implement `gateways.py` functions: `submit_limit_buy`, `submit_limit_sell`,
   `cancel_all_equity_orders`, `fetch_order`, each wrapped with `@with_retry`.  
3. Translate `robin_stocks` responses (dict) into typed models and raise custom exceptions when API
   returns errors (e.g., `"detail": "insufficient_funds"`).  
4. Unit tests using `unittest.mock` to simulate happy path, rate limit, failure status, retries.

### Phase D: OrderManager Service
1. Implement `OrderManager` in `manager.py` with public methods:
   - `place_limit_buy()`, `place_limit_sell()`, `place_limit_order()` (internal), `cancel_all()`,
     `get_status()`, `synchronize_open_orders()`.  
2. Inject dependencies (config, auth session, safety_checks, account_data, logger, structured logger
   metadata).  
3. On successful submission:  
   - Register pending order via SafetyChecks helper.  
   - Emit JSONL log entry and return `OrderEnvelope`.  
4. On failure:  
   - Leave SafetyChecks untouched, propagate custom exception.  
5. On cancellations/fills:  
   - Clear pending entry, invalidate caches, log status snapshot.  
6. Provide NotImplemented path for stop/market (raise `UnsupportedOrderTypeError` with guidance).  
7. Add unit tests w/ patched gateways to verify interactions, logging, pending state updates.

### Phase E: TradingBot Integration
1. Update `src/trading_bot/bot.py` to instantiate `OrderManager` (passing session metadata) when live
   auth is configured.  
2. Refactor `execute_trade` live branch to:
   - Compute `reference_price` (existing price param).  
   - Call order manager instead of warning TODO.  
   - Handle returned envelope, update structured TradeRecord with `order_id`, limit price, etc.  
   - Catch `OrderError` to log and maintain safety (trigger circuit breaker on severe errors).  
3. Ensure paper trading path unchanged (regression tests).  
4. Integration tests using mocks to assert call order and error handling.

### Phase F: Cancellation & Synchronization Utilities
1. Expose `cancel_all_open_orders()` on `TradingBot` delegating to order manager.  
2. Implement `synchronize_open_orders()` scheduler (called by startup or health monitor) respecting
   poll interval from config.  
3. Update documentation (`README.md` quickstart section) with new configuration and kill-switch usage.  
4. Optional: add CLI/dry-run path or script stub for manual cancellation.

## Testing Strategy
- **Unit Tests**  
  - Config parsing and per-strategy override precedence.  
  - Price calculation guardrails (bps vs absolute, slippage guard).  
  - Gateway retry behavior (mock robin_stocks to raise `RetriableError`).  
  - OrderManager interactions with SafetyChecks + AccountData cache invalidation.
- **Integration Tests**  
  - `TradingBot.execute_trade` in live mode with mocked order manager to ensure proper logging and
    safety flows.  
  - Cancellation path releasing pending orders and invalidating caches.  
  - NotImplemented path for unsupported order types returning structured error.
- **Manual / Dry Runs**  
  - Paper trading dry run verifying logging integration.  
  - Sandbox invocation with `robin_stocks` in paper account or mocked HTTP.

## Risks & Mitigations
- **Risk**: `robin_stocks` API shape changes or returns unexpected payloads.  
  - *Mitigation*: Centralize response parsing, add defensive validation, log raw snapshots for audit.
- **Risk**: SafetyChecks pending map drifts from actual broker state.  
  - *Mitigation*: Synchronization poller reconciles statuses and clears stale entries; cancellations
    always clear via OrderManager.  
  - Additional manual command to force `synchronize_open_orders()` before trading sessions.
- **Risk**: Retry decorator misclassifies exceptions.  
  - *Mitigation*: Map broker errors to `RetriableError` or direct `OrderError` explicitly, add tests
    for each code path.  
- **Risk**: Config breaking changes for existing users.  
  - *Mitigation*: Provide defaults when `order_management` block missing, document upgrade steps.

## Deliverables
- `src/trading_bot/order_management/` package with models, calculator, gateways, manager, exceptions.
- Updated `Config` dataclass + configuration schema (including example JSON).  
- `TradingBot` integration with live order execution and cancellation entry points.  
- JSONL order log writer + documentation updates.  
- Unit/integration tests covering configuration, calculator, manager, and bot integration.  
- Updated `specs/order-management/NOTES.md` with testing evidence during later phases.
