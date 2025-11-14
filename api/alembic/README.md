# Alembic Migrations - Order Execution

## Overview

This directory contains database migrations for the CFIPros trading platform order execution system.

## Prerequisites

- PostgreSQL 15+ (Supabase recommended)
- Python 3.11+
- Alembic 1.12+
- SQLAlchemy

## Database Connection Setup

Before running migrations, configure your database connection:

```bash
# Set PostgreSQL connection string
export DATABASE_URL="postgresql://user:password@host:port/database"

# Or update alembic.ini:
# sqlalchemy.url = postgresql://user:password@host:port/database
```

## Migration Commands

### Check Current Migration Status
```bash
cd api
alembic current
```

### Run Migrations (Upgrade to Latest)
```bash
cd api
alembic upgrade head
```

### Rollback Migration (Downgrade One Version)
```bash
cd api
alembic downgrade -1
```

### View Migration History
```bash
cd api
alembic history --verbose
```

### Create New Migration
```bash
cd api
alembic revision -m "description of change"
```

## Migration 001: Create Order Tables

**File**: `versions/001_create_order_tables.py`

**Purpose**: Initialize order execution infrastructure

**Creates**:
1. **Enums**:
   - `order_type_enum`: MARKET, LIMIT, STOP
   - `order_status_enum`: PENDING, FILLED, PARTIAL, REJECTED, CANCELLED
   - `action_enum`: SUBMITTED, APPROVED, EXECUTED, FILLED, REJECTED, CANCELLED, RECOVERED

2. **Tables**:
   - `orders`: Order requests with lifecycle tracking
   - `fills`: Individual fill events for partial executions
   - `execution_logs`: Immutable audit trail (SEC Rule 4530 compliance)

3. **Constraints**:
   - PK: UUID on all tables
   - FK: order_id references in fills and execution_logs
   - Check: quantity > 0, price > 0, filled_quantity <= quantity
   - Unique: None (allows duplicate orders intentionally)

4. **Indexes**:
   - `idx_orders_trader_created`: (trader_id, created_at DESC) - Order history queries
   - `idx_orders_status`: (status) - Filter pending/active orders
   - `idx_orders_trader_status`: (trader_id, status) - Trader's active orders
   - `idx_fills_order`: (order_id) - Get fills for order
   - `idx_fills_timestamp`: (timestamp DESC) - Recent fills
   - `idx_execution_logs_trader_timestamp`: (trader_id, timestamp DESC) - Audit queries
   - `idx_execution_logs_order`: (order_id) - Order audit trail
   - `idx_execution_logs_action`: (action) - Filter by action type

5. **Row Level Security (RLS)**:
   - Enabled on all three tables
   - Policy: Traders can only access their own data
   - Policy: execution_logs is immutable (no UPDATE/DELETE)

## Testing Migration

### 1. Dry Run (Check SQL Without Executing)
```bash
cd api
alembic upgrade head --sql > migration_preview.sql
cat migration_preview.sql
```

### 2. Apply Migration
```bash
cd api
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Create order execution tables
```

### 3. Verify Tables Created
```bash
psql $DATABASE_URL -c "\d+ orders"
psql $DATABASE_URL -c "\d+ fills"
psql $DATABASE_URL -c "\d+ execution_logs"
```

**Expected**: Tables exist with correct columns, constraints, and indexes

### 4. Verify Enums Created
```bash
psql $DATABASE_URL -c "\dT+ order_type_enum"
psql $DATABASE_URL -c "\dT+ order_status_enum"
psql $DATABASE_URL -c "\dT+ action_enum"
```

### 5. Verify RLS Policies
```bash
psql $DATABASE_URL -c "SELECT schemaname, tablename, policyname FROM pg_policies WHERE tablename IN ('orders', 'fills', 'execution_logs');"
```

**Expected Policies**:
- orders_trader_isolation
- fills_trader_isolation
- execution_logs_trader_isolation
- execution_logs_immutable
- execution_logs_immutable_delete

### 6. Test Rollback
```bash
cd api
alembic downgrade -1
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Running downgrade 001 -> , Create order execution tables
```

### 7. Verify Tables Dropped
```bash
psql $DATABASE_URL -c "\d orders"
```

**Expected**: "Did not find any relation named 'orders'"

### 8. Re-Apply Migration
```bash
cd api
alembic upgrade head
```

## Performance Validation

### Query Profiling

Test query performance after migration:

```sql
-- Profile trader's recent orders (should use idx_orders_trader_created)
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE trader_id = 'test-uuid-here'
ORDER BY created_at DESC
LIMIT 20;

-- Expected:
-- Planning Time: <50ms
-- Execution Time: <200ms
-- Index Scan using idx_orders_trader_created
```

### Load Testing

```bash
# Test under load (requires pgbench)
cat > test_query.sql <<EOF
SELECT * FROM orders WHERE trader_id = 'uuid-here' LIMIT 10;
EOF

pgbench -c 10 -t 100 -f test_query.sql $DATABASE_URL

# Expected:
# Average latency: <500ms
# P95 latency: <1000ms
```

## Rollback Procedure

If migration causes issues:

```bash
# 1. Rollback database
cd api
alembic downgrade -1

# 2. Verify rollback
psql $DATABASE_URL -c "\d orders"  # Should show "relation does not exist"

# 3. Check alembic version
alembic current  # Should show no revisions

# 4. If stuck, force stamp
alembic stamp base
```

## Troubleshooting

### Migration Already Applied
```
Error: Target database is not up to date
```

**Fix**:
```bash
alembic current  # Check current version
alembic history  # View history
alembic stamp head  # Force mark as applied (if already manually applied)
```

### Foreign Key Violation
```
psycopg2.errors.ForeignKeyViolation: violates foreign key constraint
```

**Fix**:
- Ensure `traders` table exists before running migration
- Or comment out FK constraints in migration file

### RLS Policy Blocks Admin
```
No rows returned (blocked by RLS)
```

**Fix**:
```sql
-- Add admin bypass policy
CREATE POLICY admin_all ON orders
FOR ALL
TO admin_role
USING (true);
```

### Slow Queries After Migration
```
Sequential Scan detected on large table
```

**Fix**:
```sql
-- Add missing index
CREATE INDEX idx_missing ON table_name(column_name);

-- Analyze table
ANALYZE orders;
```

## Compliance Notes

### SEC Rule 4530
The `execution_logs` table provides an immutable audit trail as required by SEC Rule 4530:

- All order actions are logged with timestamp
- Logs cannot be modified or deleted (RLS policies enforce)
- Trader ID, order ID, action, and reason are captured
- Compliance team can query all logs for regulatory reporting

### Data Retention
- Execution logs: Retain indefinitely (regulatory requirement)
- Orders: Retain 7 years (SEC requirement)
- Fills: Retain 7 years (SEC requirement)

## Next Steps

After successful migration:

1. Create seed data: `seeds/dev/order_execution.sql`
2. Run tests: `pytest tests/test_order_models.py`
3. Create SQLAlchemy models: `api/app/models/order.py`
4. Implement API endpoints: `api/app/modules/orders/controller.py`

## References

- Data Model: `specs/004-order-execution-enhanced/data-model.md`
- Plan: `specs/004-order-execution-enhanced/plan.md`
- RLS Policies: `api/sql/policies/order_execution_rls.sql`
- Alembic Docs: https://alembic.sqlalchemy.org/
