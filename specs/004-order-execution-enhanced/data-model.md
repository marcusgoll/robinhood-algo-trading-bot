# Data Model: order-execution-enhanced

## Core Entities

### Order
**Purpose**: Represents a trader's order request with full execution lifecycle tracking

**Fields**:
- `id`: UUID (PK) - Unique order identifier
- `trader_id`: UUID (FK) - Reference to traders table
- `symbol`: String - Stock symbol (e.g., "AAPL", "MSFT")
- `quantity`: Integer - Number of shares (must be > 0, from FR-001)
- `order_type`: Enum (MARKET, LIMIT, STOP) - Type of order
- `price`: Decimal (nullable) - Limit price (null for market orders)
- `stop_loss`: Decimal (nullable) - Stop loss price (risk management, from FR-003)
- `take_profit`: Decimal (nullable) - Take profit price (risk management)
- `status`: Enum (PENDING, FILLED, PARTIAL, REJECTED, CANCELLED) - Current state
- `filled_quantity`: Integer - Quantity filled so far (0 initially)
- `average_fill_price`: Decimal (nullable) - Average price of fills
- `created_at`: Timestamp - When order was submitted
- `updated_at`: Timestamp - Last modification time
- `expires_at`: Timestamp (nullable) - Order expiration (if timeout set, from US4)

**Validation Rules**:
- `quantity` > 0 (from FR-001)
- `price` > 0 (if not market order)
- `filled_quantity` ≤ `quantity` (logical constraint)
- `status` CANNOT transition: REJECTED → PENDING, CANCELLED → PENDING, etc. (state machine)
- `trader_id` must exist in traders table (referential integrity)

**State Transitions** (if applicable):
- PENDING → FILLED (when all quantity filled)
- PENDING → PARTIAL (when some filled, more waiting)
- PENDING → REJECTED (exchange rejection, validation failure)
- PENDING → CANCELLED (user action or timeout)
- PARTIAL → FILLED (when remaining quantity fills)
- PARTIAL → REJECTED (if rejection occurs on remaining)

**Indexes**:
- (trader_id, created_at) - For filtering trader's recent orders
- (status) - For querying pending orders
- (trader_id, status) - Combined for trader's active orders

**Audit Requirements** (from FR-011 to FR-013):
- All state changes logged to execution_logs table
- Immutable record of order lifecycle

---

### Fill
**Purpose**: Records individual fill events when order executes against exchange

**Fields**:
- `id`: UUID (PK)
- `order_id`: UUID (FK) - Reference to Order
- `timestamp`: Timestamp - When fill occurred
- `quantity_filled`: Integer - Shares in this fill (must be > 0)
- `price_at_fill`: Decimal - Execution price
- `venue`: String - Exchange name (e.g., "NYSE", "NASDAQ", "Mock")
- `commission`: Decimal (≥ 0) - Transaction fee
- `created_at`: Timestamp

**Validation Rules**:
- `quantity_filled` > 0 (from FR-006)
- `quantity_filled` ≤ remaining order quantity (logical)
- `price_at_fill` > 0
- `commission` ≥ 0
- `order_id` must exist and status != REJECTED/CANCELLED
- `timestamp` must be ≤ now() (fills cannot be backdated)

**Relationships**:
- Belongs to: Order (many fills per order for partial fills)
- Used by: Order.filled_quantity (sum of fill quantities)

**Audit**: Each fill creates execution_log entry with action="filled"

---

### ExecutionLog
**Purpose**: Immutable append-only audit trail for compliance (SEC Rule 4530, from FR-011)

**Fields**:
- `id`: UUID (PK)
- `order_id`: UUID (FK) - Reference to Order
- `trader_id`: UUID (FK) - Reference to traders
- `action`: Enum (SUBMITTED, APPROVED, EXECUTED, FILLED, REJECTED, CANCELLED, RECOVERED)
- `status`: Enum - Order status AT TIME of action (PENDING, FILLED, etc.)
- `timestamp`: Timestamp - Precise moment of event
- `reason`: String (nullable) - Why (e.g., "Insufficient funds", "Exchange timeout")
- `retry_attempt`: Integer (nullable) - Which retry (0=initial, 1=first retry, etc., from FR-008)
- `error_code`: String (nullable) - Exchange error code if applicable

**Constraints**:
- NO UPDATE or DELETE allowed (application-level enforcement)
- Only INSERT allowed
- Indexed on (trader_id, timestamp) for audit queries
- Indexed on (order_id) for order history

**Immutability Strategy**:
- Application code: Check audit before allowing updates (fails early)
- Database: RLS policy prevents any updates/deletes even if app logic fails
- Backup: Daily exports to compliance system

**Audit Requirements** (from FR-011 to FR-013):
- Trader visibility: Can only see their own logs (RLS policy)
- Compliance visibility: Dedicated compliance role can query all logs
- Export capability: SQL queries available for regulatory reporting

---

## Relationships Diagram

```
traders (existing table)
    ↓ 1:N
orders
    ├→ 1:N fills (order split into multiple fills)
    └→ 1:N execution_logs (append-only audit)

fills
    └→ execution_logs (fill events logged)

Constraints:
- order.trader_id → traders.id (FK)
- fill.order_id → orders.id (FK)
- execution_log.order_id → orders.id (FK)
- execution_log.trader_id → traders.id (FK)
```

---

## Database Schema (PostgreSQL SQL)

```sql
-- Create enums
CREATE TYPE order_type_enum AS ENUM ('MARKET', 'LIMIT', 'STOP');
CREATE TYPE order_status_enum AS ENUM ('PENDING', 'FILLED', 'PARTIAL', 'REJECTED', 'CANCELLED');
CREATE TYPE action_enum AS ENUM ('SUBMITTED', 'APPROVED', 'EXECUTED', 'FILLED', 'REJECTED', 'CANCELLED', 'RECOVERED');

-- Orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    order_type order_type_enum NOT NULL,
    price DECIMAL(10, 2) CHECK (price IS NULL OR price > 0),
    stop_loss DECIMAL(10, 2),
    take_profit DECIMAL(10, 2),
    status order_status_enum NOT NULL DEFAULT 'PENDING',
    filled_quantity INTEGER NOT NULL DEFAULT 0 CHECK (filled_quantity >= 0),
    average_fill_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,

    CHECK (filled_quantity <= quantity),
    CHECK (order_type = 'MARKET' OR price IS NOT NULL)
);

CREATE INDEX idx_orders_trader_created ON orders(trader_id, created_at DESC);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_trader_status ON orders(trader_id, status);

-- Fills table
CREATE TABLE fills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    quantity_filled INTEGER NOT NULL CHECK (quantity_filled > 0),
    price_at_fill DECIMAL(10, 2) NOT NULL CHECK (price_at_fill > 0),
    venue VARCHAR(50) NOT NULL,
    commission DECIMAL(10, 2) NOT NULL DEFAULT 0 CHECK (commission >= 0),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fills_order ON fills(order_id);
CREATE INDEX idx_fills_timestamp ON fills(timestamp DESC);

-- Execution Logs (immutable audit trail)
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    action action_enum NOT NULL,
    status order_status_enum,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    reason TEXT,
    retry_attempt INTEGER,
    error_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_execution_logs_trader_timestamp ON execution_logs(trader_id, timestamp DESC);
CREATE INDEX idx_execution_logs_order ON execution_logs(order_id);
CREATE INDEX idx_execution_logs_action ON execution_logs(action);

-- RLS Policies (Row-Level Security for traders)
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE fills ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY orders_trader_isolation ON orders
    FOR ALL USING (trader_id = current_user_id());

CREATE POLICY fills_trader_isolation ON fills
    USING (order_id IN (SELECT id FROM orders WHERE trader_id = current_user_id()));

CREATE POLICY execution_logs_trader_isolation ON execution_logs
    USING (trader_id = current_user_id());

-- Compliance role can see all (bypasses RLS)
ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT SELECT ON execution_logs TO compliance_auditor;
```

---

## Data Access Patterns

### Query 1: Get Trader's Recent Orders
```sql
SELECT * FROM orders
WHERE trader_id = $1
ORDER BY created_at DESC
LIMIT 20;
```
**Performance**: Indexed on (trader_id, created_at)

### Query 2: Get Order with All Fills
```sql
SELECT o.*, f.* FROM orders o
LEFT JOIN fills f ON o.id = f.order_id
WHERE o.id = $1
ORDER BY f.timestamp ASC;
```
**Performance**: Fills indexed on order_id

### Query 3: Calculate Average Fill Price
```sql
SELECT o.id,
       SUM(f.quantity_filled) as total_filled,
       AVG(f.price_at_fill) as avg_price
FROM orders o
LEFT JOIN fills f ON o.id = f.order_id
WHERE o.trader_id = $1 AND o.created_at > NOW() - INTERVAL '1 day'
GROUP BY o.id;
```
**Performance**: O(n fills per order), typically < 10 fills per order

### Query 4: Audit Trail for Compliance
```sql
SELECT * FROM execution_logs
WHERE trader_id = $1 AND timestamp BETWEEN $2 AND $3
ORDER BY timestamp DESC;
```
**Performance**: Indexed on (trader_id, timestamp)

---

## Measurement Queries (for HEART metrics)

### Task Success: Order Completion Rate
```sql
SELECT
    COUNT(*) FILTER (WHERE status = 'FILLED') * 100.0 / COUNT(*) as completion_rate
FROM orders
WHERE created_at > NOW() - INTERVAL '1 day';
```

### Happiness: Error Rate
```sql
SELECT
    COUNT(*) FILTER (WHERE action = 'REJECTED') * 100.0 / COUNT(*) as error_rate
FROM execution_logs
WHERE created_at > NOW() - INTERVAL '1 day';
```

### Engagement: Orders per Trader per Day
```sql
SELECT
    trader_id,
    COUNT(*) as orders_submitted
FROM orders
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY trader_id;
```

---

## Migration Strategy

- **Migration file**: `api/alembic/versions/XXXX_create_order_execution_tables.py`
- **Reversibility**: Yes (alembic downgrade available)
- **Data backfill**: Not required (new feature, no existing orders)
- **Deployment**: Run in staging first, then production
- **Testing**: Playwright smoke test verifies table creation

