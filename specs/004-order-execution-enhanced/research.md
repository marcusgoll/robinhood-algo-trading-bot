# Research & Discovery: order-execution-enhanced

## Research Mode
Full research (complex backend feature with reliability + error handling requirements)

## Key Research Decisions

### Decision 1: Order Retry Strategy with Idempotency
- **Decision**: Exponential backoff (1s, 2s, 4s) with idempotent key-based deduplication
- **Rationale**: Balances resilience (handles transient failures) with safety (prevents duplicate orders)
- **Alternatives**:
  - Infinite retry (rejected: masks persistent issues)
  - Fixed retry (rejected: less effective for network variance)
- **Source**: Existing error-handling patterns in order-management module

### Decision 2: Event-Driven Status Updates via WebSocket
- **Decision**: Publish order events to Redis → subscribe via WebSocket in frontend
- **Rationale**: Real-time updates without polling; scales to 100+ concurrent traders
- **Alternatives**:
  - HTTP polling (rejected: inefficient, higher latency)
  - Server-Sent Events (rejected: harder to manage connection recovery)
- **Source**: Existing WebSocket infrastructure in Railway deployment

### Decision 3: Audit Trail as Immutable Event Log
- **Decision**: Append-only `execution_logs` table (no update/delete); application-level enforcement
- **Rationale**: Regulatory compliance (SEC Rule 4530); prevents accidental data loss
- **Alternatives**:
  - Updateable logs with audit triggers (rejected: complex, harder to verify)
  - CSV export only (rejected: not queryable, loses audit trail)
- **Source**: Compliance requirements from spec.md FR-011 to FR-013

### Decision 4: Validation Layering (Frontend + Backend + Database)
- **Decision**: Input validation at all 3 layers (user feedback, security, compliance)
- **Rationale**: User experience (fast feedback) + security (no malicious bypass) + compliance (immutable trail)
- **Alternatives**:
  - Backend-only validation (rejected: poor UX, slow feedback)
  - Database constraints only (rejected: no user-facing feedback)
- **Source**: NFR-006 (Accessibility), NFR-007 (Security), FR-001 to FR-003

### Decision 5: Risk Management as Pre-Execution Guard
- **Decision**: Check daily loss limit + max position size before order submission (separate service)
- **Rationale**: Prevents traders from exceeding risk appetite; reduces support escalations
- **Alternatives**:
  - Post-execution risk audit (rejected: allows rule violations, harder to reverse)
  - Manual approval workflow (rejected: adds latency, doesn't scale)
- **Source**: FR-003, spec hypothesis (reduce support by 40%)

---

## Components to Reuse (6 found)

### Backend Services

1. **api/src/services/auth.py**
   - Purpose: Trader authentication/authorization
   - Usage: Verify trader identity + permissions for order execution
   - Status: Existing, proven pattern

2. **api/src/services/exchange_adapter.py**
   - Purpose: Exchange API integration (mock for testing, real for production)
   - Usage: Route orders to exchange/broker API
   - Status: Existing, handles rate limiting

3. **api/src/lib/event_bus.py**
   - Purpose: Pub/sub event system (Redis-backed)
   - Usage: Publish order events (submitted, filled, rejected) → subscriber services
   - Status: Existing, used by other modules

### Data Persistence

4. **api/src/models/base.py**
   - Purpose: SQLAlchemy base model with `id`, `created_at`, `updated_at`
   - Usage: Inherit in Order, Fill, ExecutionLog entities
   - Status: Existing pattern across all tables

5. **api/src/database.py**
   - Purpose: PostgreSQL connection, session management
   - Usage: Database transactions for order execution (ACID guarantees)
   - Status: Existing, production-tested

### Frontend/UI

6. **apps/app/lib/swr.ts**
   - Purpose: Data fetching with caching, revalidation
   - Usage: Fetch order list, real-time status updates
   - Status: Existing, used in other feature modules

---

## New Components Needed (7 required)

### Backend Services (New)

1. **api/src/services/order_validator.py**
   - Purpose: Validate orders against trader constraints
   - Responsibility: Check quantity, price, risk limits, account balance
   - Implementation: Runs pre-submission; returns specific error messages
   - Related requirement: FR-001, FR-002, FR-003

2. **api/src/services/order_executor.py**
   - Purpose: Execute validated orders with retry logic
   - Responsibility: Submit to exchange, handle retries, reconcile state
   - Implementation: Idempotent key-based deduplication; exponential backoff
   - Related requirement: FR-004, FR-008, FR-009

3. **api/src/services/status_orchestrator.py**
   - Purpose: Coordinate status updates from exchange → frontend
   - Responsibility: Poll exchange, publish events, track fill lifecycle
   - Implementation: Event-driven (Redis pub/sub); WebSocket push to traders
   - Related requirement: FR-005, FR-006

### Database Models/Migrations (New)

4. **api/src/models/order.py**
   - Purpose: Order entity definition
   - Fields: id, trader_id, symbol, quantity, order_type, price, status, created_at, updated_at
   - Validation rules: Foreign key to traders, enum status, check quantity > 0

5. **api/src/models/fill.py**
   - Purpose: Fill event tracking
   - Fields: id, order_id, timestamp, quantity_filled, price_at_fill, venue, commission
   - Validation rules: Foreign key to orders, commission ≥ 0

6. **api/src/models/execution_log.py**
   - Purpose: Immutable audit trail
   - Fields: id, order_id, trader_id, action, status, timestamp, reason
   - Validation rules: Foreign key to orders/traders, append-only (no update/delete)

### Database Migrations (New)

7. **api/alembic/versions/XXXX_create_order_tables.py**
   - Purpose: Create orders, fills, execution_logs tables
   - Constraints: Primary keys, foreign keys, check constraints for enums
   - RLS policies: Traders can only see their own orders/fills/logs

---

## Unknowns Resolved ✅

1. ✅ **Exchange connection strategy**: Use existing exchange_adapter.py mock + real
2. ✅ **Retry idempotency**: UUID-based order client ID prevents duplicate submission
3. ✅ **WebSocket vs polling**: WebSocket chosen (existing infrastructure)
4. ✅ **Audit trail persistence**: Immutable event log (execution_logs table)
5. ✅ **Rate limiting**: 100 orders/minute per trader (configured in middleware)
6. ✅ **Error message clarity**: Specific messages for each validation failure (tested in PR)

**Status**: All technical questions resolved. Ready to proceed to `/tasks`.

---

## Stack Decisions

- **Language**: Python (FastAPI backend, existing standard)
- **Database**: PostgreSQL (existing; new tables with RLS)
- **State Management**: Redis (event bus for order events)
- **Frontend**: React + SWR (fetch + subscribe to WebSocket)
- **Deployment**: Railway (API), Vercel (frontend) - no changes needed

---

## Dependencies Analysis

**Existing**:
- sqlalchemy, fastapi, pydantic, redis, websockets (all present)

**New Packages** (if needed):
- None (all capabilities exist in current stack)

**Version Bumps**:
- None (backward compatible)

