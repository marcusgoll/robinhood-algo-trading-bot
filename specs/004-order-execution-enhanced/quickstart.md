# Quickstart: Order Execution Enhanced

Complete integration guide for implementing order execution with validation, retry logic, and real-time status updates.

---

## Scenario 1: Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+

### Initial Setup

```bash
# Clone and navigate to repo
cd trading-api
git checkout 004-order-execution-enhanced

# Backend setup
cd api

# Install dependencies
uv sync

# Create database
createdb trading_local

# Run migrations (creates orders, fills, execution_logs tables)
uv run alembic upgrade head

# Seed test data
uv run python scripts/seed_orders.py

# Start backend
uv run uvicorn main:app --reload --port 8000

# Frontend setup (new terminal)
cd ../apps/app
pnpm install

# Start frontend dev server
pnpm dev
# Navigate to http://localhost:3000/orders
```

### Verify Setup

```bash
# Test API endpoint
curl -X GET http://localhost:8000/api/v1/health
# Expected: {"status": "ok", "timestamp": "2025-10-17T..."}

# Test order submission
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{
    "symbol": "AAPL",
    "quantity": 100,
    "order_type": "MARKET"
  }'
# Expected: 201 with order details
```

---

## Scenario 2: Submit Market Order (Happy Path)

### Test Case: Trader submits 100 shares of AAPL

**Given**: Trader has $15,000 available, AAPL trading at $150
**When**: Trader clicks "Buy" with quantity=100, order_type=MARKET
**Then**: Order fills immediately at $150.00

### Frontend Flow

```typescript
// apps/app/app/(authed)/orders/components/OrderForm.tsx

import { useOrders } from '@/lib/hooks/useOrders';

export function OrderForm() {
  const [symbol, setSymbol] = useState('');
  const [quantity, setQuantity] = useState('');
  const { submitOrder, isLoading, error } = useOrders();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const order = await submitOrder({
        symbol,
        quantity: parseInt(quantity),
        order_type: 'MARKET'
      });
      console.log('Order submitted:', order);
      setSymbol('');
      setQuantity('');
    } catch (err) {
      console.error('Order failed:', err);
      // Show error to user: "Insufficient funds: need $15,000, have $10,000"
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="Symbol" />
      <input value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="Quantity" type="number" />
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Submitting...' : 'Buy'}
      </button>
      {error && <div className="error">{error.message}</div>}
    </form>
  );
}
```

### Backend Flow

```python
# api/src/modules/orders/controller.py

@router.post("/api/v1/orders", status_code=201)
async def submit_order(
    request: OrderSubmitRequest,
    trader_id: UUID = Depends(get_current_trader)
) -> OrderResponse:
    # 1. Validate input
    validator = OrderValidator(db_session)
    try:
        validated = await validator.validate_order(trader_id, request)
    except ValidationError as e:
        # Return 400 with specific error message
        raise HTTPException(status_code=400, detail=e.message)

    # 2. Execute order
    executor = OrderExecutor(exchange_api, db_session, event_bus)
    order = await executor.execute_order(trader_id, validated)

    # 3. Publish event (subscribers get real-time update)
    await event_bus.publish(
        f"orders:{trader_id}",
        {
            "event": "order.submitted",
            "order_id": order.id,
            "status": "PENDING"
        }
    )

    return OrderResponse.from_model(order)
```

### Expected Output

**Frontend**: Toast notification: "Order submitted - Order ID: abc123, Status: PENDING"
**Status Updates** (via WebSocket):
- T+0s: PENDING
- T+0.5s: FILLED (order filled at market price)

**Database**:
- `orders` table: New row with status=FILLED, filled_quantity=100
- `fills` table: New row with quantity_filled=100, price_at_fill=150.00
- `execution_logs` table: 3 entries (SUBMITTED, APPROVED, FILLED)

---

## Scenario 3: Validation Error (Invalid Input)

### Test Case: Trader submits order with insufficient funds

**Given**: Trader has $5,000 available, tries to buy 100 shares at $150
**When**: Trader submits order
**Then**: Validation fails with clear error message

### Steps to Reproduce

```bash
# 1. In frontend OrderForm, enter:
Symbol: AAPL
Quantity: 100
(Order type: MARKET - price will be ~$150)

# 2. Click Buy
# 3. Expect error message: "Insufficient funds for $15,000 order; available: $5,000"
```

### Backend Validation Logic

```python
# api/src/modules/order_execution/risk_manager.py

class RiskManager:
    async def check_account_balance(self, trader_id: UUID, order: Order) -> ValidationResult:
        trader = await db.get_trader(trader_id)

        # Estimate cost (market orders use current price)
        estimated_cost = order.quantity * get_market_price(order.symbol)

        if trader.available_balance < estimated_cost:
            return ValidationResult(
                valid=False,
                error_code="INSUFFICIENT_FUNDS",
                message=f"Insufficient funds for ${estimated_cost:,.2f} order; available: ${trader.available_balance:,.2f}"
            )

        return ValidationResult(valid=True)
```

### Expected Output

**Frontend**: Red error banner: "Insufficient funds for $15,000 order; available: $5,000"
**Status Code**: 400 Bad Request
**Response**:
```json
{
  "error": "INSUFFICIENT_FUNDS",
  "message": "Insufficient funds for $15,000 order; available: $5,000",
  "details": {
    "required_balance": 15000,
    "available_balance": 5000
  }
}
```

**Database**: No entries created (validation failed before submission)

---

## Scenario 4: Network Failure & Retry

### Test Case: Exchange API timeout, order retries successfully

**Given**: Order submitted to exchange
**When**: Exchange API times out (response > 5 seconds)
**Then**: System retries with exponential backoff and recovers

### Manual Testing (with Mock Exchange)

```python
# api/src/services/exchange_adapter.py (mock mode for testing)

class ExchangeAdapter:
    async def submit_order(self, order: Order) -> OrderResult:
        if order.symbol == "TEST_TIMEOUT":
            # Simulate timeout on first attempt
            if not hasattr(self, '_retry_count'):
                self._retry_count = 0

            self._retry_count += 1
            if self._retry_count == 1:
                await asyncio.sleep(6)  # Timeout > 5s
            else:
                # Retry succeeds
                return OrderResult(status="filled", fill_price=100.0)
```

### Retry Flow

```
T+0s: Order submitted to exchange
T+5s: Timeout detected
T+1s: Check exchange for duplicate (idempotent key)
      → Not found
T+2s: Retry 1 (wait 1s)
      → Exchange returns timeout again
T+3s: Check exchange again
T+4s: Retry 2 (wait 2s)
      → Exchange returns filled!
T+5s: Update order status, publish event
```

### Expected Output

**execution_logs entries**:
1. action=SUBMITTED, status=PENDING, retry_attempt=null
2. action=EXECUTED, status=PENDING, error_code="TIMEOUT", retry_attempt=0
3. action=RECOVERED, status=PENDING, retry_attempt=1
4. action=FILLED, status=FILLED, retry_attempt=1

**Frontend**: User sees "Order filled at $100.00" (recovery invisible to trader)

**Database**: Single order entry (no duplicate), single fill entry

---

## Scenario 5: Real-Time Status Updates via WebSocket

### Test Case: Subscribe to order updates, see fills in real-time

### Frontend Subscription

```typescript
// apps/app/app/(authed)/orders/components/OrderStatusSocket.tsx

import { useEffect, useState } from 'react';

export function OrderStatusSocket({ orderId }: { orderId: string }) {
  const [status, setStatus] = useState('PENDING');
  const [fills, setFills] = useState([]);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8000/ws/orders/events?token=${getJWT()}`,
      ['order-updates']
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.order_id === orderId) {
        if (data.event === 'order.filled') {
          setStatus('FILLED');
          setFills((prev) => [
            ...prev,
            {
              quantity: data.quantity_filled,
              price: data.price_at_fill,
              timestamp: new Date(data.timestamp)
            }
          ]);
        } else if (data.event === 'order.partial') {
          setStatus('PARTIAL');
        }
      }
    };

    return () => ws.close();
  }, [orderId]);

  return (
    <div>
      <h3>Order Status: {status}</h3>
      {fills.map((fill, i) => (
        <div key={i}>
          Filled {fill.quantity} @ ${fill.price.toFixed(2)} at {fill.timestamp.toLocaleTimeString()}
        </div>
      ))}
    </div>
  );
}
```

### Backend WebSocket Handler

```python
# api/src/websocket/handlers/order_events.py

class OrderEventHandler:
    async def handle_order_update(self, trader_id: UUID, event: OrderEvent):
        # Publish to Redis channel
        await redis.publish(
            f"orders:{trader_id}",
            json.dumps({
                "event": event.type,  # "order.filled", "order.partial", etc.
                "order_id": str(event.order_id),
                "quantity_filled": event.quantity,
                "price_at_fill": float(event.price),
                "timestamp": event.timestamp.isoformat()
            })
        )
```

### Expected Output

**WebSocket Messages** (in real-time):
1. Connection established: {"type": "connection_acknowledged"}
2. Fill event 1: {"event": "order.partial", "quantity_filled": 50, "price": 150.00}
3. Fill event 2: {"event": "order.filled", "quantity_filled": 50, "price": 150.05}

**Frontend Display**:
```
Order Status: PARTIAL (50/100)
Filled 50 @ $150.00 at 12:00:05
Filled 50 @ $150.05 at 12:00:06

Order Status: FILLED (100/100)
```

---

## Scenario 6: Audit Trail for Compliance

### Test Case: Generate execution audit report

### Query Example

```bash
# Get audit trail for specific order
curl -X GET http://localhost:8000/api/v1/orders/abc123/audit \
  -H "Authorization: Bearer <JWT>"

# Expected response (SEC Rule 4530 compliant):
{
  "data": [
    {
      "id": "log-001",
      "order_id": "abc123",
      "trader_id": "trader-xyz",
      "action": "SUBMITTED",
      "status": "PENDING",
      "timestamp": "2025-10-17T12:00:00Z",
      "reason": null,
      "retry_attempt": null
    },
    {
      "id": "log-002",
      "order_id": "abc123",
      "trader_id": "trader-xyz",
      "action": "APPROVED",
      "status": "PENDING",
      "timestamp": "2025-10-17T12:00:01Z",
      "reason": null,
      "retry_attempt": null
    },
    {
      "id": "log-003",
      "order_id": "abc123",
      "trader_id": "trader-xyz",
      "action": "EXECUTED",
      "status": "PENDING",
      "timestamp": "2025-10-17T12:00:02Z",
      "reason": null,
      "retry_attempt": null
    },
    {
      "id": "log-004",
      "order_id": "abc123",
      "trader_id": "trader-xyz",
      "action": "FILLED",
      "status": "FILLED",
      "timestamp": "2025-10-17T12:00:03Z",
      "reason": null,
      "retry_attempt": null
    }
  ],
  "total": 4
}
```

### SQL for Compliance Reporting

```sql
-- Compliance officer: Get all executions for date range
SELECT
    trader_id,
    order_id,
    action,
    timestamp,
    reason
FROM execution_logs
WHERE timestamp BETWEEN '2025-10-01' AND '2025-10-31'
ORDER BY timestamp DESC;

-- Export to CSV for regulatory filing
\COPY (
    SELECT trader_id, order_id, action, timestamp, reason
    FROM execution_logs
    WHERE timestamp BETWEEN '2025-10-01' AND '2025-10-31'
) TO '/tmp/execution_report_2025_10.csv' WITH CSV HEADER;
```

---

## Scenario 7: Order Cancellation

### Test Case: Trader cancels pending order

### Steps

```bash
# 1. Submit limit order (assume it doesn't fill immediately)
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Authorization: Bearer <JWT>" \
  -d '{
    "symbol": "AAPL",
    "quantity": 100,
    "order_type": "LIMIT",
    "price": 140.00
  }'
# Response: {"id": "order-123", "status": "PENDING"}

# 2. Cancel the order
curl -X POST http://localhost:8000/api/v1/orders/order-123/cancel \
  -H "Authorization: Bearer <JWT>"
# Response: {"id": "order-123", "status": "CANCELLED"}

# 3. Verify in audit log
curl -X GET http://localhost:8000/api/v1/orders/order-123/audit \
  -H "Authorization: Bearer <JWT>"
# Should show action=CANCELLED in logs
```

### Expected Output

**Database**:
- Order status: PENDING → CANCELLED
- execution_logs: New entry with action=CANCELLED, reason="User requested cancellation"

**Frontend**: Toast: "Order cancelled"

---

## Running Tests

### Unit Tests

```bash
# Backend: Test validation logic
cd api
uv run pytest tests/test_order_validator.py -v

# Frontend: Test OrderForm component
cd apps/app
pnpm test OrderForm.test.tsx
```

### Integration Tests

```bash
# End-to-end: Submit order through full stack
uv run pytest tests/integration/test_order_flow.py -v

# WebSocket: Test real-time updates
uv run pytest tests/integration/test_websocket.py -v
```

### Load Test

```bash
# Simulate 100 concurrent traders
uv run locust -f tests/load/locustfile.py --host=http://localhost:8000 -u 100 -r 10
```

---

## Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
uv run uvicorn main:app --reload --log-level debug
```

### Check Audit Trail

```bash
# View all events for an order
psql trading_local -c "
  SELECT action, status, timestamp, reason
  FROM execution_logs
  WHERE order_id = 'your-order-id'
  ORDER BY timestamp;
"
```

### Monitor WebSocket

```bash
# Use wscat to test WebSocket connection
npm install -g wscat
wscat -c ws://localhost:8000/ws/orders/events
# Then type your JWT token when prompted
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| 401 Unauthorized | Invalid JWT | Check token expiration, re-authenticate |
| 400 Bad Request | Validation error | Check error message, adjust order parameters |
| Order not filling | Limit price too low | Increase limit price to match market |
| Status not updating | WebSocket disconnected | Check browser console, reconnect |
| Timeout during submit | Exchange slow | Wait for retry, order should recover |
| Duplicate order error | Retry key collision | Check idempotent key logic |

---

## Success Metrics to Verify

- [ ] Order submits successfully (201 response)
- [ ] Validation errors are clear and actionable
- [ ] Order fills within 2 seconds
- [ ] Status updates propagate within 500ms
- [ ] WebSocket stays connected during fills
- [ ] Audit log shows all actions with timestamps
- [ ] Traders see only their own orders (RLS working)
- [ ] 100 concurrent traders load without errors

