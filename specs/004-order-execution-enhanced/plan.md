# Implementation Plan: Order Execution Enhanced

**Status**: Ready for Task Generation
**Last Updated**: 2025-10-17
**Feature Branch**: `004-order-execution-enhanced`

---

## Research Summary

See: `research.md` for full research findings

**Key Decisions**:
- Exponential backoff retry with idempotent key deduplication
- Event-driven status updates via WebSocket (Redis pub/sub)
- Immutable append-only audit trail (execution_logs table)
- Validation layering: frontend + backend + database
- Risk management as pre-execution guard (daily loss, max position)

**Components to Reuse**: 6 services (auth, exchange_adapter, event_bus, db, models, swr)
**New Components**: 7 (order_validator, order_executor, status_orchestrator, + 3 models + 1 migration)

---

## Architecture Decisions

### Stack

**Backend**:
- Framework: FastAPI (Python, existing standard)
- Database: PostgreSQL (existing; 3 new tables: orders, fills, execution_logs)
- Event Bus: Redis (existing; publish order events)
- HTTP Server: Uvicorn (existing)

**Frontend**:
- Framework: React + Next.js App Router (existing)
- Data Fetching: SWR with WebSocket subscription
- State: Local component state (orders list) + server state (status)
- Real-time: WebSocket for status updates

**Deployment**:
- Frontend: Vercel (existing, no changes)
- Backend: Railway (existing, no changes)
- No new environment-specific dependencies

### Architectural Patterns

#### 1. **Pre-Execution Validation Pipeline**
```
Trader submits order
    ↓
[Frontend validation] Quick feedback for bad input
    ↓
[Backend validation] Authoritative check (FR-001 to FR-003)
    ├→ Check syntax (quantity > 0, valid symbol)
    ├→ Check account (balance sufficient)
    ├→ Check risk (daily loss < limit, position < max)
    └→ Return specific error or approve
    ↓
[Database constraints] Final safety net (check constraints, FKs, RLS)
    ↓
Ready to execute
```

**Rationale**: User-friendly feedback + security (can't bypass) + compliance (audit trail)
**Related Requirements**: FR-001, FR-002, FR-003, NFR-006 (accessibility)

#### 2. **Order Retry with Idempotency**
```
Order submission (idempotent_key = UUID)
    ↓
Try 1 (immediate): Submit to exchange
    ├→ Success: Return order_id, status=FILLED/PARTIAL
    ├→ Timeout (>5s): Publish "retry_needed" event
    └→ Fatal error (invalid symbol): Return error, no retry
    ↓
Try 2 (after 1s): Check exchange for duplicate by idempotent_key
    ├→ Found: Fetch status, update local state
    └→ Not found: Resubmit with same idempotent_key
    ↓
Try 3 (after 2s): Repeat check/resubmit
    ↓
Try 4 (after 4s): Max retries reached, notify trader
```

**Idempotent Key Strategy**:
- Format: `{trader_id}:{symbol}:{quantity}:{price}:{timestamp}:v1`
- Exchange validates: "If I've seen this key before, return existing order_id"
- Prevents duplicate fills even if we retry

**Rationale**: Network failures don't cause duplicate orders; traders can trust execution
**Related Requirements**: FR-008, FR-009, NFR-005 (reliability)

#### 3. **Event-Driven Status Updates**
```
Order event occurs (filled, rejected, etc.)
    ↓
Exchange API / Local service detects → log to execution_logs
    ↓
Publish event to Redis channel: `orders:{trader_id}`
    ↓
Connected WebSocket subscribers receive event
    ├→ Update order status locally
    ├→ Show user notification (fill price, quantity)
    └→ Trigger balance update if needed
    ↓
Fallback: Frontend polls /api/orders every 5s for updates
```

**Why Redis pub/sub + WebSocket**:
- Real-time (< 500ms latency, from NFR-002)
- Scalable (one channel per trader)
- Existing infrastructure (no new dependencies)
- Graceful degradation (polls if WebSocket fails)

**Related Requirements**: FR-005, FR-006, NFR-002
**
#### 4. **Immutable Audit Trail**
```
Every order action → execution_logs INSERT (append-only)

Actions logged:
- SUBMITTED: When trader creates order
- APPROVED: When validation passes
- EXECUTED: When sent to exchange
- FILLED: When fills received
- REJECTED: When order rejected
- CANCELLED: When user cancels
- RECOVERED: When retry succeeds after failure

Immutability guarantees:
- Application: Checks audit before allowing updates (fail early)
- Database: RLS prevents non-compliance users from modifying logs
- Compliance: Queries traders' audit trails for regulatory reporting
```

**Rationale**: SEC Rule 4530 requires immutable execution records
**Related Requirements**: FR-011, FR-012, FR-013

---

## Directory Structure

**Backend**:
```
api/src/
├── modules/
│   ├── orders/                           # NEW
│   │   ├── controller.py                 # API endpoints
│   │   ├── service.py                    # Business logic (validation, execution)
│   │   ├── repository.py                 # Database queries
│   │   └── schemas.py                    # Pydantic request/response schemas
│   ├── order_execution/                  # NEW
│   │   ├── retry_service.py              # Idempotent retry logic
│   │   ├── risk_manager.py               # Position/loss limits
│   │   └── status_coordinator.py         # WebSocket status updates
│   └── ...existing modules...
├── models/
│   ├── order.py                          # NEW: Order SQLAlchemy model
│   ├── fill.py                           # NEW: Fill model
│   ├── execution_log.py                  # NEW: Audit trail model
│   └── ...existing...
├── websocket/
│   ├── manager.py                        # NEW: WebSocket connection manager
│   └── handlers/
│       └── order_events.py               # NEW: Order event subscription handler
├── migrations/
│   └── alembic/versions/
│       └── XXXX_create_order_tables.py   # NEW: Migration for orders, fills, logs
└── ...existing...

Frontend:
apps/app/
├── app/
│   └── (authed)/
│       └── orders/                       # NEW
│           ├── page.tsx                  # Orders list/execution page
│           ├── layout.tsx                # Orders layout
│           └── components/
│               ├── OrderForm.tsx         # NEW: Form to submit order
│               ├── OrderList.tsx         # NEW: Display active orders
│               ├── OrderStatusSocket.tsx # NEW: WebSocket listener for status updates
│               └── OrderHistory.tsx      # NEW: Past orders & fills
├── lib/
│   └── hooks/
│       └── useOrders.ts                  # NEW: SWR hook for order data + WebSocket
└── ...existing...
```

---

## Data Model

See: `data-model.md` for comprehensive entity definitions

**Core Tables**:
1. **orders** - Trader order requests (NEW)
2. **fills** - Individual fill events (NEW)
3. **execution_logs** - Immutable audit trail (NEW)

**Key Fields**:
- Order: id, trader_id, symbol, quantity, status, filled_quantity, created_at
- Fill: id, order_id, quantity_filled, price_at_fill, venue, timestamp
- ExecutionLog: id, order_id, trader_id, action, status, timestamp, reason

**Relationships**:
- Order 1:N Fills (one order can have multiple partial fills)
- Order 1:N ExecutionLogs (audit trail of order lifecycle)

**RLS Policies**:
- Traders see only their own orders/fills/logs
- Compliance role bypasses RLS for audit queries

---

## API Contracts

See: `contracts/api.yaml` for OpenAPI specification

**Key Endpoints**:
- `POST /api/v1/orders` - Submit new order
- `GET /api/v1/orders` - List trader's orders
- `GET /api/v1/orders/{id}` - Get order details + fills
- `POST /api/v1/orders/{id}/cancel` - Cancel pending order
- `GET /api/v1/orders/{id}/audit` - Audit trail for order
- `WebSocket /ws/orders/events` - Subscribe to order status updates

**Request/Response Schemas**:
```python
# Request: Submit Order
{
  "symbol": "AAPL",
  "quantity": 100,
  "order_type": "MARKET",  # or "LIMIT", "STOP"
  "price": 150.50,         # nullable for MARKET
  "stop_loss": 145.00,
  "take_profit": 160.00
}

# Response: Order Submitted
{
  "id": "uuid",
  "trader_id": "uuid",
  "status": "PENDING",
  "created_at": "2025-10-17T12:00:00Z"
}

# WebSocket Event: Order Filled
{
  "event": "order.filled",
  "order_id": "uuid",
  "quantity_filled": 50,
  "price_at_fill": 150.45,
  "total_filled": 50,
  "status": "PARTIAL",
  "timestamp": "2025-10-17T12:01:05Z"
}
```

---

## Performance Targets

**From spec.md NFRs**:
- Order execution: ≤2 seconds P95 (FR-004, NFR-001)
- Status updates: ≤500ms P99 (FR-005, NFR-002)
- Concurrent support: 100+ traders with <5% degradation (NFR-003)
- System uptime: 99.9% (NFR-004)
- Zero data loss (NFR-005)

**Database Performance**:
- Order validation query: <100ms (check account, risk limits)
- Fetch trader's orders: <200ms (index: trader_id, created_at)
- Audit query: <500ms for 1000 logs (index: trader_id, timestamp)

**Measurement Queries** (in `design/queries/`):
- `measurement_task_completion.sql` - Order fill rate
- `measurement_error_rate.sql` - Rejection rate
- `measurement_latency.sql` - Execution speed

---

## Security & Compliance

**Authentication**:
- Existing Clerk middleware (no changes)
- JWT token verified on every request

**Authorization**:
- Traders can only submit/cancel their own orders
- RLS policies enforce row-level security on database

**Input Validation**:
- Pydantic schemas validate all inputs (quantity > 0, price > 0, etc.)
- Symbolic checks prevent SQL injection
- Rate limiting: 100 orders/minute per trader

**Data Protection**:
- PII (trader IDs): Minimal exposure (audit logs only for compliance)
- Encryption: In-transit (TLS 1.3+), at-rest (PostgreSQL default encryption)
- Audit trail: Immutable, timestamped, tamper-evident

**Compliance** (SEC Rule 4530):
- All executions logged with timestamp, trader ID, order ID, symbol, quantity, price, venue
- Execution logs queryable by compliance team
- Audit exports available for regulatory reporting

---

## CI/CD Impact

**No Breaking Changes**:
- Fully backward compatible (new endpoints only)
- Feature flag: `ORDER_EXECUTION_V2_ENABLED` (default: false, then ramp to 100%)
- Existing order flow unchanged

**Environment Variables**:
- New: `EXCHANGE_API_RATE_LIMIT` (default: 100 req/min)
- New: `ORDER_RETRY_MAX_ATTEMPTS` (default: 3)
- New: `ORDER_STATUS_UPDATE_TIMEOUT` (default: 30s)
- No changes to existing env vars

**Database Migrations**:
- Create orders, fills, execution_logs tables (see migration file)
- Add RLS policies
- Create indexes for performance
- Reversible via alembic downgrade

**Build Commands**:
- No new build steps
- `pnpm build` and `uv run pytest` unchanged
- Deployment: Standard Railway deploy + Vercel deploy

**Smoke Tests** (for deploy verification):
```bash
# Route: /api/v1/orders
# Expected: 200, {"ok": true}

# Route: /api/v1/orders (POST with valid order)
# Expected: 201, {"id": "uuid", "status": "PENDING"}

# WebSocket: /ws/orders/events
# Expected: Connection accepted, ready for events
```

---

## Deployment Strategy

**Staging First**:
1. Deploy migration (create tables)
2. Deploy API (new endpoints + WebSocket)
3. Deploy frontend (order form + status listener)
4. Run smoke tests
5. Manual QA (submit orders, check fills)

**Production Rollout**:
1. Feature flag `ORDER_EXECUTION_V2_ENABLED`: 0% (disabled)
2. Healthy metrics on staging? → 10% (1 in 10 orders)
3. Monitor for 24h: errors, latency, compliance
4. 50% → 100% over 48 hours
5. Fully enabled once stable

**Rollback Plan**:
- Feature flag: Set to 0% (instant disablefold)
- Database: No data loss (immutable logs, new tables independent)
- Code: Standard git revert

---

## Integration Scenarios

See: `quickstart.md` for complete integration guide

**Scenario 1**: Trader submits market order
- Expected: Order filled within 2 seconds
- Verify: Order status = FILLED, filled_quantity = requested quantity

**Scenario 2**: Network timeout during submission
- Expected: Retry succeeds, no duplicate order
- Verify: execution_logs shows SUBMITTED + RECOVERED actions

**Scenario 3**: Trader cancels pending order
- Expected: Order cancelled, prevents further execution
- Verify: Order status = CANCELLED, execution_log has CANCELLED action

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Exchange API down | Medium | High | Retry logic, graceful degradation, manual override |
| Duplicate orders from retries | Low | High | Idempotent key-based deduplication |
| Trader sees stale status | Medium | Medium | WebSocket ensures real-time updates; polling fallback |
| Audit logs lost | Very Low | Critical | Immutable append-only table, daily backups |
| Risk limit bypass | Low | High | Pre-execution validation + database constraints |
| Performance degradation at scale | Low | Medium | Indexes on frequently queried columns, Redis caching |

---

## Success Criteria

From spec.md (all must be met before shipping to production):

1. ✅ **Execution Reliability**: ≥99% of valid orders execute without errors
2. ✅ **Error Clarity**: ≥95% of traders understand validation errors
3. ✅ **Execution Speed**: ≥95% of orders confirm within 2 seconds
4. ✅ **Status Update Latency**: ≥99% within 500ms
5. ✅ **Network Resilience**: Zero duplicate orders during recovery
6. ✅ **Risk Compliance**: 100% of orders validated against risk limits
7. ✅ **Audit Trail Completeness**: 100% of executions in audit logs
8. ✅ **Peak Performance**: 100+ traders with <5% latency increase

---

## Ready for Next Phase

**Planning artifacts complete**. Next: `/tasks` to generate concrete implementation tasks.

