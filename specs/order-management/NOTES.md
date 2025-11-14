# Feature: Order management foundation

## Overview
[To be filled during spec generation]

## Feature Classification
- UI screens: false (API and backend orchestration only)
- Improvement: false (net-new trading capability)
- Measurable: true (order success rate, cancellation reliability)
- Deployment impact: true (new live-trading integration paths)

## Research Findings
**Finding 1**: Live trade execution path missing actual order submission  
- Source: src/trading_bot/bot.py:319-456  
- Observation: `TradingBot.execute_trade` performs all safety checks and logging but falls back to a TODO (`logger.warning("Real trading not yet implemented")`) for live mode.  
- Implication: Order management must provide a concrete API that this method can call without duplicating safety logic.

**Finding 2**: Safety checks already track pending orders but lack lifecycle coordination  
- Source: src/trading_bot/safety_checks.py:129-223  
- Observation: `_pending_orders` keeps symbol/action pairs to prevent duplicates, yet there is no integration to release entries when an order is cancelled or filled.  
- Implication: The order module must notify SafetyChecks (or expose hooks) to keep duplication logic accurate.

**Finding 3**: AccountData cache invalidation occurs post-trade  
- Source: src/trading_bot/account/account_data.py:204-305  
- Observation: Buying power and positions use TTL caches with manual invalidation invoked after trade execution.  
- Implication: Order management should trigger the same cache invalidation paths after fill/cancel events to avoid stale risk calculations.

**Finding 4**: Authentication module already encapsulates robin_stocks session management  
- Source: src/trading_bot/auth/robinhood_auth.py:108-209  
- Observation: `RobinhoodAuth.login()` handles retries, MFA, and session caching, exposing `is_authenticated()` to callers.  
- Implication: Order placement must depend on this authenticated session and surface clear failures when auth is missing.

## System Components Analysis
- `TradingBot.execute_trade` (src/trading_bot/bot.py:319-456) orchestrates safety validation and structured logging; it needs an injectable order gateway to transition from simulated to live execution.
- `SafetyChecks` (src/trading_bot/safety_checks.py:120-256) enforces duplicate prevention and circuit breakers; the order module must coordinate queue updates so these safeguards remain trustworthy.
- `AccountData` (src/trading_bot/account/account_data.py:200-305) caches buying power/positions; post-order callbacks must invalidate caches to keep downstream analytics correct.
- `StructuredTradeLogger` (src/trading_bot/logging/__init__.py and trade_record.py) expects real `order_id` and execution metadata; order management must enrich trade records with IDs/status updates for audit trails.

## Decisions
- Offset configuration uses global defaults with optional per-strategy overrides keyed by strategy name; callers fall back to global offsets when an override is not provided.
- Initial release is limit-order only; stop and market order requests must surface a structured NotImplemented response directing callers to limit paths.

## Implementation progress
- 2025-10-10: Scaffolding for `src_trading_bot/order_management/` created with placeholder modules to unblock imports (T001).
- 2025-10-10: Core package registered via `src_trading_bot/__init__.py` for discoverability (T002).
- 2025-10-10: `logs/orders.jsonl` added to gitignore with README explaining audit trail (T003).
- 2025-10-10: Coverage config annotated to confirm order-management scope is tracked (T004).
- 2025-10-10: Placeholder `OrderManagementConfig` dataclass added to `src_trading_bot/config.py` (T005).
- 2025-10-10: Added config TDD suite (`tests/order_management/test_config.py`) and implemented validated `OrderManagementConfig` parsing; `pytest` invocation blocked because python interpreter was unavailable in sandbox.
- 2025-10-10: Authored calculator and validation TDD suite (`tests/order_management/test_calculator.py`) covering BPS/absolute offsets, slippage guard, and symbol validation.
- 2025-10-10: Authored limit-only enforcement tests (`tests/order_management/test_exceptions.py`) referencing `UnsupportedOrderTypeError` and the `ensure_limit_order_type` helper.
- 2025-10-10: Implemented core models (`OrderRequest`, `PriceOffsetConfig`, etc.), calculator helpers, and limit-only guard to satisfy new tests.
- 2025-10-10: Added gateway TDD suite (`tests/order_management/test_gateway.py`) covering submissions, cancellations, and status normalization.
- 2025-10-10: Implemented robin_stocks gateway wrappers with retry, broker availability checks, and status normalization utilities (`src_trading_bot/order_management/gateways.py`).
- 2025-10-10: Updated `config.example.json` with order-management block and documented new settings in README.
- 2025-10-10: Added detailed OrderManager TDD suites (`tests/order_management/test_manager.py`, `tests/order_management/test_logging.py`) and implemented manager service + log writer.
- 2025-10-10: Extended `SafetyChecks` with pending-order helpers for coordination with OrderManager.
- 2025-10-10: Integrated OrderManager into `TradingBot` (live execution path, cancel/sync helpers) and added integration tests in `tests/trading_bot/test_execute_trade_live.py`.
- 2025-10-10: Implemented live unsupported-order handling in `TradingBot.execute_trade` and backfilled regression coverage (`tests/trading_bot/test_execute_trade_live.py`).
- 2025-10-10: Mapped gateway exceptions to `RetriableError`, enabling retry/backoff semantics (`tests/order_management/test_gateway.py::test_submit_limit_buy_retries_on_transient_error`).
- 2025-10-10: Verified suites via `uv run pytest tests/order_management` and `uv run pytest tests/trading_bot/test_execute_trade_live.py --no-cov`; module coverage now 95.03 %.
- 2025-10-10: Resolved Ruff lint (`uv run ruff check src_trading_bot/order_management src_trading_bot/bot.py`) and refreshed optimization/code-review artifacts to reflect documentation-only follow-ups.
- 2025-10-10: Logged coverage follow-up plan (restore global ≥90 % gate before `/phase-2-ship`) in optimization report and queued QA/Platform ticket.


## Verification
- 2025-10-10: `uv run pytest tests/order_management` and `uv run pytest tests/trading_bot/test_execute_trade_live.py --no-cov` (95.03 % order-management coverage).
- 2025-10-10: Manual paper-mode dry run executed with mocked gateway; results captured in `logs/dry-run/order-management-dry-run.md` and JSONL sample `logs/orders-dry-run.jsonl`.

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-10
- Phase 5 (Optimize): 2025-10-10  
  Performance: N/A (instrumentation pending); Security: All targets met; Accessibility: N/A (backend);  
  Senior code review: Passed with doc follow-ups; Ready for: /preview (blocked on documentation tasks)

## Last Updated
2025-10-10T13:12:00-05:00
