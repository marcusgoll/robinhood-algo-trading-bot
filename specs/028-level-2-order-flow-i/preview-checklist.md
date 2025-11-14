# Preview Testing Checklist: 028-level-2-order-flow-i

**Generated**: 2025-10-22 (Manual testing session)
**Tester**: Claude Code
**Feature Type**: Backend-only (no UI routes)

---

## Backend API Testing

### PolygonClient Integration
- [ ] **Test**: Polygon.io API authentication with valid API key
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: Verify connection using health_check() method

- [ ] **Test**: Fetch Level 2 order book snapshot for active symbol
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: Test with AAPL or other liquid stock

- [ ] **Test**: Fetch Time & Sales data for 5-minute window
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: Verify chronological order and data freshness

- [ ] **Test**: Handle API rate limiting (429 responses)
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: Verify @with_retry decorator behavior

- [ ] **Test**: Handle API errors gracefully (network timeout, invalid response)
- [ ] **Result**: [Pass/Fail]
- [ ] **Notes**: Test with invalid symbol or network interruption

---

## Acceptance Scenarios (from spec.md)

### Scenario 1: Large Seller Detection

- [ ] **Test**: Given an active position, When a large sell order appears (>10,000 shares at bid), Then the system logs a "large seller alert" with order size, price level, and timestamp
- [ ] **Result**: [Pass/Fail]
- [ ] **How to test**:
  1. Create mock OrderBookSnapshot with large bid (15,000 shares at $175.50)
  2. Call `detector.detect_large_sellers(snapshot)`
  3. Verify alert created with correct severity, order size, price level
  4. Check structured log output for alert event
- [ ] **Notes**:

### Scenario 2: Red Burst Volume Spike Detection

- [ ] **Test**: Given real-time Time & Sales data, When volume spikes >300% of 5-minute average with majority sells, Then the system logs a "red burst" alert
- [ ] **Result**: [Pass/Fail]
- [ ] **How to test**:
  1. Create mock Time & Sales records with normal volume (1000 shares/min avg)
  2. Add spike records (3500 shares in 1 min, 70% sells)
  3. Call `tape_monitor.analyze_volume_spike(records)`
  4. Verify red burst alert with magnitude and sell ratio
- [ ] **Notes**:

### Scenario 3: Exit Signal Trigger

- [ ] **Test**: Given multiple large seller alerts within 2 minutes, When bid pressure builds (>3 consecutive large sells), Then the system triggers exit signal
- [ ] **Result**: [Pass/Fail]
- [ ] **How to test**:
  1. Create 3 OrderFlowAlert objects with timestamps within 120 seconds
  2. Add to detector.alert_history
  3. Call `detector.should_trigger_exit()`
  4. Verify returns True and logs critical exit signal
- [ ] **Notes**:

### Scenario 4: Normal Conditions (No False Positives)

- [ ] **Test**: Given normal order flow, When no large sellers or spikes detected, Then system continues monitoring without alerts
- [ ] **Result**: [Pass/Fail]
- [ ] **How to test**:
  1. Create OrderBookSnapshot with normal orders (<10,000 shares)
  2. Call `detector.detect_large_sellers(snapshot)`
  3. Verify empty alert list returned
  4. Check no alert logs emitted
- [ ] **Notes**:

---

## Data Validation

### Level 2 Data Validation
- [ ] Timestamp freshness (<30 seconds staleness threshold)
- [ ] Price bounds validation (>$0, reasonable values)
- [ ] Order size validation (>0 shares)
- [ ] Bid/ask spread sanity check (ask >= bid)

### Time & Sales Validation
- [ ] Chronological timestamp sequence
- [ ] Trade price within reasonable bounds
- [ ] Trade size >0
- [ ] Side classification (buy/sell) present

### Configuration Validation
- [ ] Environment variables loaded correctly
- [ ] Threshold validation (large_order_size >1000)
- [ ] Alert window validation (30-300 seconds)
- [ ] API key presence check

**Validation errors handled**: [Yes/No]
**Notes**:

---

## Performance Testing

- [ ] **Latency**: Alert generation <2 seconds from data fetch to log
- [ ] **Method**: Use `time.time()` before/after detect_large_sellers()
- [ ] **Actual p95 latency**: ___ ms (target: <2000ms)
- [ ] **Notes**:

- [ ] **Memory**: Order flow monitoring adds <50MB memory overhead
- [ ] **Method**: Run `pytest tests/order_flow/` with memory profiling
- [ ] **Actual memory delta**: ___ MB (target: <50MB)
- [ ] **Notes**:

- [ ] **API Rate Limits**: Respects Polygon.io rate limits
- [ ] **Method**: Verify @with_retry decorator with exponential backoff
- [ ] **Max retries observed**: ___ (target: ≤3)
- [ ] **Notes**:

---

## Integration Testing

### Risk Management Integration (T027)
- [ ] OrderFlowAlert published to risk management module
- [ ] Exit signal evaluated by should_trigger_exit()
- [ ] Alert severity calculated correctly (warning vs critical)
- [ ] Structured logging includes all required fields

### Active Position Monitoring (T028)
- [ ] `monitor_active_positions()` processes symbol list
- [ ] Fetches Level 2 data for each active position
- [ ] Detects large sellers across multiple symbols
- [ ] Publishes alerts for each symbol independently
- [ ] Handles errors per symbol without stopping monitoring

**Integration test results**: [All passed/X failures]
**Notes**:

---

## Error Handling & Graceful Degradation

- [ ] **API unavailable**: System logs gap and continues with reduced monitoring
- [ ] **Stale data**: DataValidationError raised, monitoring paused
- [ ] **Invalid API key**: Clear error message, feature disabled
- [ ] **Network timeout**: Retry logic with exponential backoff
- [ ] **Rate limiting**: Respects 429 responses, backs off gracefully
- [ ] **Invalid symbol**: Error logged, continues monitoring other symbols

**Degradation graceful**: [Yes/No]
**Notes**:

---

## Constitution Compliance

### §Data_Integrity
- [ ] Frozen dataclasses prevent mutation
- [ ] Input validation in `__post_init__`
- [ ] Decimal precision for prices (no float errors)
- [ ] UTC timestamps enforced

### §Audit_Everything
- [ ] All alerts logged with structured JSONL
- [ ] UTC timestamps on all events
- [ ] Alert severity levels tracked
- [ ] Exit signals logged with reasoning

### §Safety_First
- [ ] Fail-fast on validation errors
- [ ] No silent failures
- [ ] Graceful degradation when data unavailable
- [ ] No unhandled exceptions in detector

### §Risk_Management
- [ ] Rate limiting enforced (@with_retry)
- [ ] Alert cooldown prevents spam
- [ ] Exit signals require multiple confirmations
- [ ] Position-only monitoring (no continuous watchlist)

**Constitution compliant**: [Yes/No]
**Notes**:

---

## Test Coverage Validation

**Current Coverage**: 56.95% (from optimization report)
**Target Coverage**: ≥90%

**Module Breakdown**:
- config.py: 97.92% ✅
- __init__.py: 100% ✅
- validators.py: 78.26% ⚠️
- data_models.py: 79.37% ⚠️
- tape_monitor.py: 83.87% ⚠️
- polygon_client.py: 66.67% ⚠️
- order_flow_detector.py: 50.00% ❌

**Run full test suite**:
```bash
pytest tests/order_flow/ -v --cov=src/trading_bot/order_flow --cov-report=term
```

- [ ] **All unit tests passing**: ___ passed, ___ failed
- [ ] **Integration tests passing**: ___ passed, ___ failed
- [ ] **No skipped tests**: ___ skipped
- [ ] **Test runtime**: ___ seconds (target: <5s)

**Test results**: [Pass/Fail]
**Notes**:

---

## Logging & Observability

### Structured Logging Validation
- [ ] TradingLogger used throughout
- [ ] Log levels appropriate (INFO, WARNING, CRITICAL)
- [ ] Extra fields include all context (symbol, order_size, severity, etc.)
- [ ] Log format parseable (JSONL)

### Alert Log Files
- [ ] Logs written to correct location
- [ ] File permissions correct
- [ ] Log rotation configured (if applicable)
- [ ] Log size reasonable (<1MB/day)

### Sample Log Verification
```bash
# Check for large seller alerts
grep "Large seller detected" logs/*.log | tail -5

# Check for exit signals
grep "Exit signal triggered" logs/*.log | tail -5

# Check for validation errors
grep "DataValidationError" logs/*.log | tail -5
```

- [ ] **Logs parseable**: [Yes/No]
- [ ] **Sample logs reviewed**: [Yes/No]
- [ ] **No sensitive data in logs**: [Yes/No]

**Logging quality**: [Pass/Fail]
**Notes**:

---

## Environment Configuration

### Required Variables
- [ ] `POLYGON_API_KEY` set and valid
- [ ] `ORDER_FLOW_LARGE_ORDER_SIZE` configured (default: 10000)
- [ ] `ORDER_FLOW_VOLUME_SPIKE_THRESHOLD` configured (default: 3.0)
- [ ] `ORDER_FLOW_RED_BURST_THRESHOLD` configured (default: 4.0)
- [ ] `ORDER_FLOW_ALERT_WINDOW_SECONDS` configured (default: 120)
- [ ] `ORDER_FLOW_MONITORING_MODE` set to "positions_only"

### .env.example Updated
- [ ] All ORDER_FLOW_* variables documented
- [ ] Descriptions clear and accurate
- [ ] Default values specified
- [ ] POLYGON_API_KEY placeholder present

**Configuration complete**: [Yes/No]
**Notes**:

---

## Edge Case Testing

### Pre-market/After-hours Order Flow
- [ ] System handles reduced liquidity
- [ ] Alert thresholds adjusted or feature disabled
- [ ] Market hours validation present

### Institutional Accumulation vs Distribution
- [ ] Large orders on both bid and ask detected
- [ ] Severity calculation considers both sides
- [ ] Alert type distinguishes buy vs sell pressure

### Market-wide Selloffs
- [ ] System handles high alert volume
- [ ] Alert cooldown prevents spam
- [ ] Exit signals prioritized by position risk

### Stale/Delayed Data
- [ ] Timestamp validation catches stale data (>30s)
- [ ] DataValidationError raised and logged
- [ ] System pauses monitoring until fresh data

**Edge cases handled**: ___ / 4
**Notes**:

---

## Security Validation

### API Key Security
- [ ] No hardcoded API keys in code
- [ ] API key loaded from environment only
- [ ] API key not logged or exposed
- [ ] .env.example uses placeholder, not real key

### Input Validation
- [ ] All external data validated before use
- [ ] Price bounds enforced
- [ ] Symbol validation (valid ticker format)
- [ ] No injection vulnerabilities

**Security scan**: ✅ 0 vulnerabilities (from optimization-security.md)

**Security compliant**: [Yes/No]
**Notes**:

---

## Issues Found

*Document any issues below with format:*

### Issue 1: [Title]
- **Severity**: Critical | High | Medium | Low
- **Location**: [Module/function]
- **Description**: [What's wrong]
- **Expected**: [What should happen]
- **Actual**: [What actually happens]
- **Reproduction**: [Steps to reproduce]

---

## Test Results Summary

**Acceptance scenarios tested**: ___ / 4
**Performance targets met**: ___ / 3
**Integration tests passed**: ___ / 2
**Edge cases validated**: ___ / 4
**Issues found**: ___

**Overall status**: ✅ Ready to ship | ⚠️ Minor issues | ❌ Blocking issues

**Tester signature**: _______________
**Date**: _______________

---

## Manual Testing Commands

### Run Full Test Suite
```bash
# All tests with coverage
pytest tests/order_flow/ -v --cov=src/trading_bot/order_flow --cov-report=term --cov-report=html

# Specific module tests
pytest tests/order_flow/test_polygon_client.py -v
pytest tests/order_flow/test_order_flow_detector.py -v
pytest tests/order_flow/test_tape_monitor.py -v

# Integration tests only
pytest tests/order_flow/ -v -m integration
```

### Health Check
```bash
# Verify Polygon.io API connectivity
python -c "from src.trading_bot.order_flow import OrderFlowConfig, OrderFlowDetector; \
  config = OrderFlowConfig.from_env(); \
  detector = OrderFlowDetector(config); \
  print(detector.health_check())"
```

### Test Alert Detection (Interactive)
```python
# Run in Python REPL
from datetime import datetime, UTC
from decimal import Decimal
from src.trading_bot.order_flow import (
    OrderFlowConfig,
    OrderFlowDetector,
    OrderBookSnapshot
)

# Initialize
config = OrderFlowConfig.from_env()
detector = OrderFlowDetector(config)

# Create mock snapshot with large seller
snapshot = OrderBookSnapshot(
    symbol="AAPL",
    bids=[(Decimal("175.50"), 15000)],  # Large order
    asks=[(Decimal("175.51"), 3000)],
    timestamp_utc=datetime.now(UTC)
)

# Detect large sellers
alerts = detector.detect_large_sellers(snapshot)
print(f"Alerts: {len(alerts)}")
for alert in alerts:
    print(f"  {alert.severity}: {alert.order_size} shares at ${alert.price_level}")

# Check exit signal
should_exit = detector.should_trigger_exit()
print(f"Should exit: {should_exit}")
```

---

## Next Steps After Preview

**If all tests pass**:
1. Mark checklist items as completed ([x])
2. Document any minor issues
3. Commit preview results
4. Proceed to `/phase-1-ship` (staging deployment)

**If blocking issues found**:
1. Document issues in "Issues Found" section
2. Run `/debug` to fix issues
3. Re-run `/preview` to validate fixes
4. Then proceed to shipping

**If performance issues**:
1. Profile slow operations (use cProfile or pytest-benchmark)
2. Optimize hot paths (caching, batch operations)
3. Re-test performance targets
4. Update optimization-performance.md with results
