# Quickstart: level-2-order-flow-i

## Scenario 1: Initial Setup

```bash
# 1. Install Polygon.io SDK dependency
pip install polygon-api-client==1.12.5

# 2. Update requirements.txt
echo "polygon-api-client==1.12.5  # Level 2 order book and Time & Sales data (order-flow-integration)" >> requirements.txt

# 3. Set environment variables
# Windows (PowerShell)
$env:POLYGON_API_KEY="your-api-key-here"
$env:ORDER_FLOW_DATA_SOURCE="polygon"
$env:ORDER_FLOW_LARGE_ORDER_SIZE="10000"
$env:ORDER_FLOW_VOLUME_SPIKE_THRESHOLD="3.0"
$env:ORDER_FLOW_RED_BURST_THRESHOLD="4.0"
$env:ORDER_FLOW_ALERT_WINDOW_SECONDS="120"
$env:ORDER_FLOW_MONITORING_MODE="positions_only"

# Linux/macOS
export POLYGON_API_KEY="your-api-key-here"
export ORDER_FLOW_DATA_SOURCE="polygon"
export ORDER_FLOW_LARGE_ORDER_SIZE="10000"
export ORDER_FLOW_VOLUME_SPIKE_THRESHOLD="3.0"
export ORDER_FLOW_RED_BURST_THRESHOLD="4.0"
export ORDER_FLOW_ALERT_WINDOW_SECONDS="120"
export ORDER_FLOW_MONITORING_MODE="positions_only"

# 4. Create logs directory
mkdir -p logs/order_flow

# 5. Verify configuration loads
python -c "from trading_bot.order_flow.config import OrderFlowConfig; c = OrderFlowConfig.from_env(); print(f'Config loaded: {c.data_source}')"
```

## Scenario 2: Validation

```bash
# 1. Run unit tests
pytest tests/order_flow/ -v

# 2. Run integration tests (requires valid POLYGON_API_KEY)
pytest tests/order_flow/test_polygon_client.py -v --integration

# 3. Check type hints
mypy src/trading_bot/order_flow/

# 4. Lint code
ruff check src/trading_bot/order_flow/
pylint src/trading_bot/order_flow/

# 5. Security audit
bandit -r src/trading_bot/order_flow/

# 6. Test coverage (target: ≥90%)
pytest tests/order_flow/ --cov=src/trading_bot/order_flow --cov-report=term-missing
```

## Scenario 3: Manual Testing (Paper Trading)

### Step 1: Start Trading Bot with Order Flow Monitoring

```bash
# 1. Start bot in paper trading mode
python -m trading_bot --mode paper

# Expected: Bot logs "OrderFlowDetector initialized" with config summary
# Expected: Bot logs "Monitoring mode: positions_only"
```

### Step 2: Simulate Active Position

```python
# In Python REPL or test script
from trading_bot.order_flow.order_flow_detector import OrderFlowDetector
from trading_bot.order_flow.config import OrderFlowConfig
from datetime import datetime, UTC

# Initialize detector
config = OrderFlowConfig.from_env()
detector = OrderFlowDetector(config)

# Simulate active position (replace with actual position from bot)
test_symbol = "AAPL"

# Fetch Level 2 snapshot (will hit Polygon.io API)
snapshot = detector.fetch_level2_snapshot(test_symbol)
print(f"Level 2 snapshot: {len(snapshot.bids)} bids, {len(snapshot.asks)} asks")

# Analyze for large sellers
alerts = detector.detect_large_sellers(snapshot)
if alerts:
    for alert in alerts:
        print(f"ALERT: {alert.alert_type} - {alert.symbol} @ ${alert.price_level} ({alert.order_size} shares)")
else:
    print("No large sellers detected")
```

### Step 3: Verify Alert Logging

```bash
# Check logs directory
ls -la logs/order_flow/

# View today's alerts (replace {date} with today's date in YYYY-MM-DD format)
cat logs/order_flow/{date}.jsonl | jq '.'

# Count alerts by type
grep '"alert_type":"large_seller"' logs/order_flow/*.jsonl | wc -l
grep '"alert_type":"red_burst"' logs/order_flow/*.jsonl | wc -l

# Check alert latency (should be <2 seconds per NFR-001)
cat logs/order_flow/*.jsonl | jq '.latency_ms' | awk '{sum+=$1; count++} END {print "Avg latency: " sum/count " ms"}'
```

### Step 4: Test Exit Signal Integration

```python
# Test risk management integration
from trading_bot.order_flow.order_flow_detector import OrderFlowDetector
from trading_bot.order_flow.data_models import OrderFlowAlert
from datetime import datetime, UTC, timedelta
from decimal import Decimal

# Create mock alerts (3 large sellers within 2 minutes)
alerts = [
    OrderFlowAlert(
        symbol="AAPL",
        alert_type="large_seller",
        severity="warning",
        order_size=12000,
        price_level=Decimal("150.25"),
        volume_ratio=None,
        timestamp_utc=datetime.now(UTC) - timedelta(seconds=90)
    ),
    OrderFlowAlert(
        symbol="AAPL",
        alert_type="large_seller",
        severity="warning",
        order_size=15000,
        price_level=Decimal("150.20"),
        volume_ratio=None,
        timestamp_utc=datetime.now(UTC) - timedelta(seconds=60)
    ),
    OrderFlowAlert(
        symbol="AAPL",
        alert_type="large_seller",
        severity="critical",
        order_size=20000,
        price_level=Decimal("150.15"),
        volume_ratio=None,
        timestamp_utc=datetime.now(UTC)
    )
]

# Check if exit signal should trigger (FR-008: 3+ alerts within 2 minutes)
should_exit = detector.should_trigger_exit(alerts)
print(f"Exit signal: {should_exit}")  # Expected: True

# Verify alert window logic
old_alert = OrderFlowAlert(
    symbol="AAPL",
    alert_type="large_seller",
    severity="warning",
    order_size=10000,
    price_level=Decimal("150.00"),
    volume_ratio=None,
    timestamp_utc=datetime.now(UTC) - timedelta(seconds=150)  # >2 minutes ago
)
alerts_with_old = [old_alert, alerts[1], alerts[2]]
should_exit_with_old = detector.should_trigger_exit(alerts_with_old)
print(f"Exit signal with old alert: {should_exit_with_old}")  # Expected: False (only 2 alerts within window)
```

### Step 5: Verify Graceful Degradation

```bash
# Test 1: Missing API key (should log warning, not crash)
unset POLYGON_API_KEY
python -m trading_bot --mode paper
# Expected: Log "POLYGON_API_KEY not configured, order flow detection skipped"

# Test 2: Invalid API key (should retry, then graceful degradation)
export POLYGON_API_KEY="invalid-key"
python -m trading_bot --mode paper
# Expected: Log "API authentication failed after 3 retries, skipping order flow"

# Test 3: Network failure (should retry with exponential backoff)
# Simulate by disconnecting network, then:
python -m trading_bot --mode paper
# Expected: Log "Network error, retrying in 1s... (attempt 1/3)"
# Expected: Log "Network error, retrying in 2s... (attempt 2/3)"
# Expected: Log "Network error, retrying in 4s... (attempt 3/3)"
# Expected: Log "All retries exhausted, order flow monitoring disabled"
```

## Scenario 4: Performance Testing

```bash
# 1. Measure alert latency (target: <2 seconds P95)
python tests/order_flow/test_performance.py --measure-latency

# 2. Measure memory usage (target: <50MB additional)
python tests/order_flow/test_performance.py --measure-memory

# 3. Test rate limit handling
python tests/order_flow/test_rate_limits.py --simulate-high-volume

# 4. Benchmark API response times
python tests/order_flow/test_polygon_client.py --benchmark
```

## Scenario 5: Production Deployment Checklist

```bash
# Pre-deployment validation
- [ ] All tests pass (unit + integration + performance)
- [ ] Type checking clean (mypy)
- [ ] Linting clean (ruff + pylint)
- [ ] Security audit clean (bandit)
- [ ] Test coverage ≥90%
- [ ] Paper trading validation: 24+ hours with zero crashes
- [ ] Alert accuracy: <10% false positive rate
- [ ] Alert latency: <2 seconds (P95)
- [ ] Memory usage: <50MB additional
- [ ] POLYGON_API_KEY configured in production secrets
- [ ] All ORDER_FLOW_* env vars set with production values
- [ ] Logs directory writable: logs/order_flow/
- [ ] Rollback plan documented in NOTES.md
- [ ] Circuit breakers tested (API failures, rate limits, data staleness)
```
