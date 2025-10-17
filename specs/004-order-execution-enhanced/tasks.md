# Tasks: Order Execution Enhanced

## Codebase Reuse Analysis

**Scanned**: api/src/**/*.py, api/src/**/*.ts, apps/app/**/*.tsx

### [EXISTING - REUSE]

✅ **DatabaseService** (api/src/services/database_service.py)
- Purpose: PostgreSQL connection management
- Usage: Order CRUD operations

✅ **AuthMiddleware** (api/src/middleware/auth.py)
- Purpose: Trader authentication verification
- Usage: Protect order endpoints

✅ **EventBus** (api/src/lib/event_bus.py)
- Purpose: Redis pub/sub for order events
- Usage: Publish status updates

✅ **BaseModel** (api/src/models/base.py)
- Purpose: SQLAlchemy base with id, created_at, updated_at
- Usage: Order, Fill, ExecutionLog entities

✅ **SWR Hook** (apps/app/lib/hooks/useOrders.ts)
- Purpose: Data fetching with real-time updates
- Usage: Order list + WebSocket subscription

✅ **ExchangeAdapter** (api/src/services/exchange_adapter.py)
- Purpose: Exchange API integration
- Usage: Submit orders, check fills

### [NEW - CREATE]

🆕 **OrderValidator** (api/src/services/order_validator.py)
- No existing pattern; straightforward validation logic

🆕 **OrderExecutor** (api/src/services/order_executor.py)
- No existing pattern; retry + idempotency unique to orders

🆕 **StatusOrchestrator** (api/src/services/status_orchestrator.py)
- No existing pattern; WebSocket + event coordination

🆕 **Order Model** (api/src/models/order.py)
- Pattern: api/src/models/notification.py

🆕 **Fill Model** (api/src/models/fill.py)
- Pattern: api/src/models/notification.py

🆕 **ExecutionLog Model** (api/src/models/execution_log.py)
- Pattern: api/src/models/audit_entry.py (immutable)

🆕 **Database Migration** (api/alembic/versions/001_create_order_tables.py)
- Pattern: api/alembic/versions/existing_migration.py

---

## Dependency Graph

**Story completion order**:

1. **Phase 2: Foundational** (blocks all stories)
   - Database migration + models
   - Validation service
   - Executor service

2. **Phase 3: US1 [P1]** - Robust Order Validation (independent)
   - Validation logic
   - Error messages
   - API endpoint: POST /api/v1/orders

3. **Phase 4: US2 [P2]** - Real-Time Status Updates (depends on US1 models)
   - Status orchestrator
   - WebSocket handler
   - Status endpoint: GET /api/v1/orders/{id}

4. **Phase 5: US3 [P1]** - Graceful Error Handling & Recovery (independent)
   - Retry logic
   - State reconciliation
   - Recovery event handling

---

## Parallel Execution Opportunities

- **US1 (Validation)**: T015, T016, T017 can run in parallel (different files, no deps)
- **US2 (Status Updates)**: T025, T026, T027 (after US1 models)
- **US3 (Error Recovery)**: T035, T036 (independent, uses US1 models)
- **Tests**: T040-T050 (after implementation, parallel)
- **UI Integration**: T060-T065 (after API endpoints)

---

## Implementation Strategy

**MVP Scope**: Phase 3 (US1: Validation) only

**Incremental Delivery**:
1. Phase 2: Database + foundation (not exposed to traders)
2. Phase 3: Validation + order submission (traders can submit orders)
3. Staging validation + feedback
4. Phase 4: Status updates (real-time visibility)
5. Phase 5: Error recovery (resilience)

**Testing Approach**: TDD-required (tests before implementation)

**Deployment**: Feature flag `ORDER_EXECUTION_V2_ENABLED` (0% → 100% ramp)

---

# Phase 1: Setup

- [ ] **T001** Create project structure per plan.md architecture
  - Directories: api/src/modules/orders/, api/src/services/order_*, apps/app/app/orders/
  - Pattern: Existing feature module structure
  - From: plan.md [DIRECTORY STRUCTURE]

- [ ] **T002** [P] Install required dependencies (if any new)
  - Python: websockets (for WebSocket support)
  - TypeScript: ws (WebSocket client)
  - Check: plan.md [STACK DECISIONS] - all existing in current stack
  - From: plan.md [DEPENDENCIES ANALYSIS]

---

# Phase 2: Foundational (blocking prerequisites)

**Goal**: Infrastructure that unblocks all user stories (US1, US2, US3)

## Database Setup

- [ ] **T005** [P] Create Alembic migration for order tables
  - Files: api/alembic/versions/001_create_order_tables.py
  - Tables: orders, fills, execution_logs (see data-model.md for schema)
  - Enums: order_type, order_status, action
  - Constraints: PK, FK, check constraints, RLS policies
  - Pattern: api/alembic/versions/existing_migration.py
  - From: plan.md [DATA MODEL]

- [ ] **T006** [P] Create Order model in api/src/models/order.py
  - Fields: id, trader_id, symbol, quantity, order_type, price, status, filled_quantity, created_at, updated_at
  - Validation: quantity > 0, price > 0 (if not market), status enum
  - Methods: get_by_id, create, update_status
  - REUSE: BaseModel (api/src/models/base.py)
  - Pattern: api/src/models/notification.py
  - From: data-model.md Order entity

- [ ] **T007** [P] Create Fill model in api/src/models/fill.py
  - Fields: id, order_id, timestamp, quantity_filled, price_at_fill, venue, commission
  - Validation: quantity_filled > 0, price > 0
  - REUSE: BaseModel (api/src/models/base.py)
  - Pattern: api/src/models/order_history.py
  - From: data-model.md Fill entity

- [ ] **T008** [P] Create ExecutionLog model in api/src/models/execution_log.py
  - Fields: id, order_id, trader_id, action, status, timestamp, reason, retry_attempt
  - Immutability: No update/delete (app-level + DB RLS)
  - REUSE: BaseModel (api/src/models/base.py)
  - Pattern: api/src/models/audit_entry.py
  - From: data-model.md ExecutionLog entity

## Core Services

- [ ] **T010** [P] Create OrderValidator service in api/src/services/order_validator.py
  - Methods: validate_order(), validate_balance(), validate_risk_limits()
  - Returns: ValidationResult (valid: bool, error_code, message)
  - Validation rules: From spec.md FR-001, FR-002, FR-003
  - Pattern: api/src/services/payment_validator.py
  - From: plan.md [VALIDATION LAYERING]

- [ ] **T011** [P] Create OrderExecutor service in api/src/services/order_executor.py
  - Methods: execute_order(), retry_order(), check_duplicate()
  - Idempotent key: `{trader_id}:{symbol}:{quantity}:{price}:{timestamp}:v1`
  - Retry logic: 3 attempts, exponential backoff (1s, 2s, 4s)
  - REUSE: ExchangeAdapter (api/src/services/exchange_adapter.py), EventBus (api/src/lib/event_bus.py)
  - Pattern: api/src/services/payment_executor.py
  - From: plan.md [ORDER RETRY WITH IDEMPOTENCY]

- [ ] **T012** [P] Create StatusOrchestrator service in api/src/services/status_orchestrator.py
  - Methods: publish_status(), subscribe_to_updates(), handle_fill_event()
  - Event types: order.submitted, order.filled, order.rejected
  - Latency target: < 500ms (NFR-002)
  - REUSE: EventBus (api/src/lib/event_bus.py)
  - Pattern: api/src/services/notification_coordinator.py
  - From: plan.md [EVENT-DRIVEN STATUS UPDATES]

---

# Phase 3: User Story 1 [P1] - Robust Order Validation

**Story Goal**: Traders submit orders with validation and clear error feedback

**Independent Test Criteria**:
- [ ] Valid order submits successfully → returns 201 with order ID
- [ ] Invalid quantity (0 or negative) → returns 400 with clear error
- [ ] Insufficient balance → returns 400 with balance details
- [ ] Risk violation (max position exceeded) → returns 400 with limit info

## Database & Models

- [ ] **T015** [P] [US1] Initialize OrderRepository in api/src/modules/orders/repository.py
  - Methods: create(), get_by_id(), get_by_trader(), update_status()
  - REUSE: BaseRepository pattern
  - Pattern: api/src/modules/notifications/repository.py
  - From: data-model.md [DATA ACCESS PATTERNS]

## API Endpoint

- [ ] **T020** [US1] Create POST /api/v1/orders endpoint in api/src/modules/orders/controller.py
  - Request schema: OrderSubmitRequest (symbol, quantity, order_type, price, stop_loss, take_profit)
  - Response: OrderResponse (id, status, created_at)
  - Error responses: 400 (validation), 401 (auth), 500 (server)
  - Validation: Input syntax + business rules (via OrderValidator)
  - REUSE: AuthMiddleware (api/src/middleware/auth.py)
  - Pattern: api/src/modules/notifications/controller.py POST endpoint
  - From: contracts/api.yaml /api/v1/orders POST

## Tests

- [ ] **T025** [US1] Write test: OrderValidator accepts valid order
  - File: tests/unit/services/test_order_validator.py::test_valid_market_order()
  - Given: Trader with $20k balance, AAPL at $150/share
  - When: Submit market order for 100 shares
  - Then: Validation passes
  - Pattern: tests/unit/services/test_payment_validator.py
  - Coverage: 100% new code

- [ ] **T026** [US1] Write test: OrderValidator rejects insufficient balance
  - File: tests/unit/services/test_order_validator.py::test_insufficient_balance()
  - Given: Trader with $5k balance
  - When: Submit market order for 100 shares at $150
  - Then: Validation fails with error "Insufficient funds: need $15k, have $5k"
  - Coverage: 100% new code

- [ ] **T027** [US1] Write integration test: POST /api/v1/orders validates and creates order
  - File: tests/integration/test_order_submission.py::test_submit_valid_order()
  - Given: Authenticated trader with valid account
  - When: POST /api/v1/orders with valid data
  - Then: Returns 201, order created in DB, execution_log has SUBMITTED entry
  - Pattern: tests/integration/test_notification_submission.py
  - Coverage: ≥80% integration code

## Implementation

- [ ] **T030** [US1] Implement validation logic in OrderValidator
  - Methods: validate_quantity(), validate_price(), validate_balance(), validate_risk_limits()
  - Error messages: Clear, actionable (e.g., "Insufficient funds for $15,000 order; available: $3,200")
  - From: spec.md FR-001, FR-002, FR-003, NFR-006 (accessibility)

- [ ] **T031** [US1] Implement POST /api/v1/orders endpoint logic
  - 1. Authenticate trader
  - 2. Validate input syntax (Pydantic schema)
  - 3. Validate business rules (OrderValidator)
  - 4. Create Order record (OrderRepository)
  - 5. Log SUBMITTED action (ExecutionLog)
  - 6. Publish event (EventBus)
  - 7. Return 201 with OrderResponse

---

# Phase 4: User Story 2 [P2] - Real-Time Status Updates

**Story Goal**: Traders see live order status (pending, filled, rejected) within 500ms

**Independent Test Criteria**:
- [ ] Order submitted → Status PENDING visible immediately
- [ ] Order filled (exchange confirms) → Status FILLED updates within 500ms
- [ ] WebSocket disconnects → Polling fallback works
- [ ] Multiple fills → Partial status shows correctly

## WebSocket Infrastructure

- [ ] **T035** [P] [US2] Create WebSocket manager in api/src/websocket/manager.py
  - Manager class: Maintains active connections per trader
  - Subscribe method: Add trader to Redis channel `orders:{trader_id}`
  - Publish method: Broadcast event to all connected clients
  - Connection lifecycle: on_connect, on_message, on_disconnect
  - Pattern: api/src/websocket/notification_manager.py
  - From: plan.md [EVENT-DRIVEN STATUS UPDATES]

- [ ] **T036** [P] [US2] Create WebSocket endpoint in api/src/websocket/routes.py
  - Route: /ws/orders/events
  - Authentication: JWT token from query string
  - Message format: JSON { event, order_id, status, timestamp }
  - Error handling: Graceful disconnect on auth failure
  - Pattern: api/src/websocket/notification_routes.py
  - From: contracts/api.yaml /ws/orders/events

## Status Updates

- [ ] **T040** [US2] Implement StatusOrchestrator.publish_status()
  - When: Order status changes (filled, rejected, etc.)
  - What: Publish to Redis channel `orders:{trader_id}`
  - Format: { event, order_id, quantity_filled, price_at_fill, timestamp }
  - Latency: < 500ms P99 (NFR-002)
  - From: plan.md [EVENT-DRIVEN STATUS UPDATES]

- [ ] **T041** [US2] Implement order fill detection logic
  - Method: Poll exchange API or subscribe to exchange events
  - When fill detected: Create Fill record, update Order, log FILLED action, publish event
  - Idempotency: Use fill_id to prevent duplicate Fill records
  - From: plan.md [ARCHITECTURE DECISIONS]

## API Endpoint

- [ ] **T045** [US2] Create GET /api/v1/orders endpoint in api/src/modules/orders/controller.py
  - Query params: status, symbol, limit, offset
  - Response: List of OrderResponse + fills
  - Pagination: Limit 20-100
  - REUSE: AuthMiddleware (api/src/middleware/auth.py)
  - Pattern: api/src/modules/notifications/controller.py GET list endpoint
  - From: contracts/api.yaml /api/v1/orders GET

## Frontend Integration

- [ ] **T050** [US2] Create useOrders hook in apps/app/lib/hooks/useOrders.ts
  - Methods: fetchOrders(), subscribeToUpdates()
  - WebSocket subscription: Connect to /ws/orders/events
  - Fallback: Poll /api/v1/orders every 5s if WebSocket fails
  - REUSE: SWR Hook (apps/app/lib/hooks/useOrders.ts) + WebSocket
  - Pattern: apps/app/lib/hooks/useNotifications.ts
  - From: plan.md [EVENT-DRIVEN STATUS UPDATES]

---

# Phase 5: User Story 3 [P1] - Graceful Error Handling & Recovery

**Story Goal**: Network failures don't lose orders; retries work transparently

**Independent Test Criteria**:
- [ ] Order times out on first attempt → Retried automatically
- [ ] Retry succeeds → No duplicate order
- [ ] Exchange rejects order → Clear error, no retry
- [ ] All retries fail → Notify trader

## Retry Logic

- [ ] **T055** [P] [US3] Implement exponential backoff retry in OrderExecutor
  - Strategy: 3 attempts, wait 1s → 2s → 4s between retries
  - Idempotent key: Use UUID-based deduplication
  - Before retry: Check exchange for duplicate order (prevent duplicates)
  - Fatal errors: Don't retry (invalid symbol, auth failure)
  - From: plan.md [ORDER RETRY WITH IDEMPOTENCY]

- [ ] **T056** [P] [US3] Implement state reconciliation in OrderExecutor
  - Method: reconcile_order_state()
  - Before retry: Query exchange API for order by idempotent_key
  - If found: Fetch latest status, update local DB
  - If not found: Resubmit with same key
  - From: spec.md FR-009, FR-010

## Error Handling & Logging

- [ ] **T060** [US3] Add error logging and audit trail
  - On failure: Log to execution_logs table (action=EXECUTED, error_code)
  - On recovery: Log action=RECOVERED, retry_attempt
  - Reason field: Populate with exchange error message
  - From: spec.md FR-011, FR-012, FR-013

- [ ] **T061** [US3] Add error handler middleware in api/src/middleware/error_handler.py
  - Catches OrderExecutionException, logs to error-log.md
  - Returns 500 with error_id for tracking
  - Logs order_id, trader_id, reason, retry_count
  - From: plan.md [ERROR HANDLING & RESILIENCE]

## Tests

- [ ] **T065** [US3] Write test: Retry succeeds without duplicate order
  - File: tests/integration/test_order_retry.py::test_timeout_then_success()
  - Given: Mock exchange that times out on attempt 1, succeeds on attempt 2
  - When: Submit order
  - Then: Order fills successfully, only 1 Fill record created (no duplicate)
  - Verify: execution_logs shows EXECUTED (attempt 1), RECOVERED (attempt 2)
  - Coverage: 100% retry logic

- [ ] **T066** [US3] Write test: Fatal error doesn't retry
  - File: tests/integration/test_order_retry.py::test_invalid_symbol_no_retry()
  - Given: Exchange returns 400 "Invalid symbol"
  - When: Submit order for unknown symbol
  - Then: Order rejected immediately, no retry attempts, error_log has reason
  - Coverage: 100% error classification

---

# Phase 6: UI Integration

- [ ] **T070** [US1] Create OrderForm component in apps/app/app/(authed)/orders/components/OrderForm.tsx
  - Fields: symbol, quantity, order_type (MARKET/LIMIT/STOP), price
  - Validation: Client-side (quantity > 0, symbol exists)
  - Submit: POST /api/v1/orders via useOrders hook
  - Error display: Show validation errors inline
  - Loading state: Disable button while submitting
  - Pattern: apps/app/app/[feature]/components/[FeatureForm].tsx
  - From: spec.md User Scenarios

- [ ] **T071** [US2] Create OrderList component in apps/app/app/(authed)/orders/components/OrderList.tsx
  - Display: Table of trader's orders (symbol, quantity, status, filled_qty)
  - Subscription: Subscribe to status updates via useOrders hook
  - Real-time: Update status when events arrive
  - Pagination: Implement limit/offset from plan.md
  - Pattern: apps/app/app/[feature]/components/[FeatureList].tsx
  - From: plan.md [UI INTEGRATION]

- [ ] **T072** [US2] Create OrderStatusSocket component in apps/app/app/(authed)/orders/components/OrderStatusSocket.tsx
  - WebSocket listener: Connects to /ws/orders/events
  - Event handler: Updates order status in real-time
  - Error handling: Fallback to polling if WebSocket fails
  - Reconnect: Auto-reconnect with exponential backoff
  - Pattern: apps/app/app/[feature]/components/[FeatureSocket].tsx
  - From: plan.md [EVENT-DRIVEN STATUS UPDATES]

- [ ] **T073** Create orders page in apps/app/app/(authed)/orders/page.tsx
  - Layout: OrderForm (left) + OrderList (right)
  - Title: "Order Execution"
  - Description: "Submit market/limit orders with real-time status updates"
  - Import: OrderForm, OrderList, OrderStatusSocket components
  - From: spec.md User Scenarios

- [ ] **T074** [US1] Create POST /api/v1/orders/{id}/cancel endpoint in api/src/modules/orders/controller.py
  - Request: Accept POST /api/v1/orders/{id}/cancel
  - Behavior:
    1. Verify order exists and trader owns it (authorization)
    2. Check status = PENDING (can only cancel pending orders)
    3. Update status → CANCELLED
    4. Log action=CANCELLED in execution_logs
    5. Return 200 with updated OrderResponse
  - Error handling: 400 if order not PENDING, 404 if order not found, 401 if unauthorized
  - Latency: < 500ms (FR-007)
  - Pattern: api/src/modules/orders/controller.py POST endpoint
  - From: contracts/api.yaml /api/v1/orders/{id}/cancel, spec.md FR-007

---

# Phase 7: Polish & Cross-Cutting Concerns

## Error Handling & Resilience

- [ ] **T080** Add global error handler in api/src/middleware/error_handler.py
  - Catches OrderExecutionException, logs to Sentry + error-log.md
  - Returns 500 with error_id for tracking
  - Pattern: api/src/middleware/error_handler.py
  - From: plan.md [ERROR HANDLING & RESILIENCE]

- [ ] **T081** [P] Add retry decorator in api/src/utils/retry_decorator.py
  - Decorator: @retry(max_attempts=3, backoff_factor=2)
  - Usage: @retry on order submission call
  - Pattern: api/src/utils/retry_decorator.py
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

## Deployment Preparation

- [ ] **T085** Document rollback procedure in NOTES.md
  - Standard 3-command rollback (see docs/ROLLBACK_RUNBOOK.md)
  - Feature flag kill switch: `ORDER_EXECUTION_V2_ENABLED=0`
  - Database rollback: Reversible migration (downgrade script)
  - From: plan.md [DEPLOYMENT ACCEPTANCE]

- [ ] **T086** [P] Add health check endpoint in api/src/routes/health.py
  - Endpoint: GET /api/v1/health/orders
  - Check: Database connection, exchange API available
  - Return: { status: "ok", dependencies: { database: "ok", exchange: "ok" } }
  - Pattern: api/src/routes/health.py
  - From: plan.md [CI/CD IMPACT]

- [ ] **T087** [P] Add smoke tests to CI pipeline
  - File: tests/smoke/test_order_submission.spec.ts
  - Tests: Critical path only (form submit → order created)
  - Duration: <90s total
  - Pattern: tests/smoke/test_[feature].spec.ts
  - From: plan.md [CI/CD IMPACT]

## Feature Flagging & Rollout

- [ ] **T090** Add feature flag wrapper in apps/app/app/(authed)/orders/layout.tsx
  - Flag: `NEXT_PUBLIC_ORDER_EXECUTION_ENABLED`
  - Condition: Show orders page only if enabled
  - Fallback: Redirect to previous page if disabled
  - Ramp: 0% → 5% → 25% → 50% → 100% over 3 days
  - From: plan.md [CI/CD IMPACT]

- [ ] **T091** Add analytics instrumentation
  - Events: order.submitted, order.filled, order.rejected, order.error
  - Tool: PostHog.capture() + structured logs
  - Database: POST /api/metrics for HEART tracking
  - Pattern: Triple instrumentation (PostHog + logs + DB)
  - From: spec.md Success Criteria

---

# Summary

**Total Tasks**: 36
- Setup: 2 tasks
- Foundational: 8 tasks
- US1 (Validation): 10 tasks (T015-T031, T074)
- US2 (Status Updates): 9 tasks
- US3 (Error Recovery): 4 tasks
- Polish & Deployment: 3 tasks

**Parallelizable**: 15 tasks marked [P] (T002, T005-T012, T015-T017, T025-T027, T035-T036, T055-T056, T081, T086-T087)

**MVP Scope**: Phase 3 (US1: Validation) = 12 tasks (T015-T031, T074)

**Testing**: TDD required (tests before implementation)

**Coverage Target**: 100% new code, ≥80% existing modified code

**Next Phase**: /implement (execution with TDD workflow)

