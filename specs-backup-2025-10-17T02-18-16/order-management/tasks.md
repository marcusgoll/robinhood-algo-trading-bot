# Tasks: Order Management Foundation

## [CODEBASE REUSE ANALYSIS]

**From plan.md decisions (Existing/New):**

**[EXISTING - REUSE]**
- ✅ `src/trading_bot/config.Config` loader patterns (extend with `OrderManagementConfig`)
- ✅ `src/trading_bot/safety_checks.SafetyChecks` pending order tracking helpers
- ✅ `src/trading_bot/account/account_data.py` cache invalidation utilities (`invalidate_cache`)
- ✅ `src/trading_bot/error_handling.retry.with_retry` decorator and policies
- ✅ `src/trading_bot/logging/structured_logger.StructuredTradeLogger`
- ✅ `src/trading_bot/bot.TradingBot` execution flow and session metadata

**[NEW - CREATE]**
- 🆕 `src/trading_bot/order_management/` package (models, calculator, gateways, manager, exceptions)
- 🆕 JSONL order log writer for submissions (`logs/orders.jsonl`)
- 🆕 Per-strategy override handling in configuration
- 🆕 Synchronization/polling utilities for open orders

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

---

## Phase 3.1: Setup & Quality Gates

- [x] T001 Create package scaffolding `src/trading_bot/order_management/` with empty modules (`__init__.py`, `models.py`, `calculator.py`, `gateways.py`, `manager.py`, `exceptions.py`) to unblock imports.
- [x] T002 [P] Register new package in `src/trading_bot/__init__.py` (export stub) and ensure mypy/ruff configs include the module if they enumerate packages.
- [x] T003 [P] Add `.gitignore` entry for `logs/orders.jsonl` and create `logs/README.md` note about the new audit log if missing.
- [x] T004 [P] Update `dashboard.coveragerc` (or coverage config) to include `src/trading_bot/order_management` paths so coverage gates track new code.
- [x] T005 [P] Add placeholder `OrderManagementConfig` dataclass in `src/trading_bot/config.py` (fields with default `None` / TODO) so forthcoming tests import cleanly without logic.

---

## Phase 3.2: Tests - TDD (must fail before implementation)

- [x] T006 Create failing config tests in `tests/order_management/test_config.py` covering defaults, per-strategy overrides, and invalid payloads for `OrderManagementConfig`.
- [x] T007 [P] Create failing price-calculation tests in `tests/order_management/test_calculator.py` for BPS vs absolute offsets, rounding, and slippage guard enforcement.
- [x] T008 [P] Add failing validation tests in `tests/order_management/test_calculator.py` for invalid symbols, non-positive prices/quantities, and unsupported offset modes.
- [x] T009 [P] Add failing tests in `tests/order_management/test_exceptions.py` asserting limit-only behavior raises `UnsupportedOrderTypeError` with guidance for stop/market orders.
- [x] T010 [P] Create failing gateway tests in `tests/order_management/test_gateway.py` verifying retry behavior, rate-limit handling, and error translation for `submit_limit_buy` / `submit_limit_sell`.
- [x] T011 [P] Add failing cancellation tests in `tests/order_management/test_gateway.py` for `cancel_all_equity_orders` ensuring partial failures raise `OrderCancellationError`.
- [x] T012 [P] Create failing status fetch tests in `tests/order_management/test_gateway.py` to normalize robin_stocks payloads into `OrderStatus`.
- [x] T013 [P] Add failing OrderManager submission tests in `tests/order_management/test_manager.py` asserting pending registration, envelope logging, and retry escalations.
- [x] T014 [P] Add failing OrderManager cancellation & cache tests in `tests/order_management/test_manager.py` verifying SafetyChecks clearing and AccountData invalidation.
- [x] T015 [P] Create failing synchronization tests in `tests/order_management/test_manager.py` for polling open orders and invoking completion callbacks.
- [x] T016 [P] Add failing TradingBot integration test in `tests/trading_bot/test_execute_trade_live.py` confirming live mode delegates to `OrderManager` and handles `OrderError`.
- [x] T017 [P] Add failing log output test in `tests/order_management/test_logging.py` ensuring JSONL writer masks sensitive values and includes correlation IDs.

---

## Phase 3.3: Implementation

- [x] T018 Implement fully validated `OrderManagementConfig` in `src/trading_bot/config.py`, hydrate from `config.json`, and expose per-strategy overrides.
- [x] T019 Update `config.example.json` with `"order_management"` block (offset mode, offsets, max slippage, poll interval, strategy overrides) plus inline comments.
- [x] T020 [P] Implement order management dataclasses in `src/trading_bot/order_management/models.py` (`OrderRequest`, `PriceOffsetConfig`, `OrderEnvelope`, `OrderStatus`, helper enums).
- [x] T021 [P] Implement price/validation helpers in `src/trading_bot/order_management/calculator.py` (offset arithmetic, rounding, slippage guard, strategy override selection).
- [x] T022 [P] Implement custom exceptions hierarchy in `src/trading_bot/order_management/exceptions.py` (`OrderError`, `OrderSubmissionError`, `OrderCancellationError`, `OrderStatusError`, `UnsupportedOrderTypeError`).
- [x] T023 [P] Implement robin_stocks gateway wrappers in `src/trading_bot/order_management/gateways.py` using `@with_retry`, including payload normalization and error translation.
- [x] T024 [P] Implement JSONL order log writer / helper in `src/trading_bot/order_management/manager.py` (or dedicated `logging.py`) to satisfy FR-004/FR-010.
- [x] T025 Implement `OrderManager` service in `src/trading_bot/order_management/manager.py` (submission, cancellation, status fetch, synchronization, NotImplemented guard).
- [x] T026 [P] Integrate SafetyChecks pending hooks: add `register_pending_order` / `clear_pending_order` helpers in `src/trading_bot/safety_checks.py` and ensure backwards compatibility.
- [x] T027 [P] Wire AccountData cache invalidation hooks inside `OrderManager` for fills/cancels (reuse `invalidate_cache`).
- [x] T028 Integrate `OrderManager` into `src/trading_bot/bot.py`: instantiate in constructor when auth present, update `execute_trade` live path, and surface order envelopes/errors.
- [x] T029 Expose cancel-all entry point and poller wiring in `src/trading_bot/bot.py` / `startup.py` to trigger `OrderManager.cancel_all()` and `synchronize_open_orders()` on demand.
- [x] T030 [P] Ensure `StructuredTradeLogger` entries incorporate broker `order_id` and computed limit price after order submission (update `TradeRecord` usage if needed).
- [x] T031 [P] Implement `UnsupportedOrderTypeError` handling path returning structured response for stop/market requests while logging attempt.

---

## Phase 3.4: Documentation & Verification

- [x] T032 Update `README.md` and `QUICKSTART.md` with new configuration block, usage examples, and limit-only guidance.
- [x] T033 [P] Document order log format and operational runbook in `specs/order-management/artifacts/order-log.md` (create file) referencing JSONL schema.
- [x] T034 [P] Append implementation evidence (tests run, manual dry-run notes) to `specs/order-management/NOTES.md`.
- [x] T035 Conduct manual paper-trading dry run script (simulate order submission via mocks) and record results in `logs/` + `NOTES.md` for future QA handoff.
