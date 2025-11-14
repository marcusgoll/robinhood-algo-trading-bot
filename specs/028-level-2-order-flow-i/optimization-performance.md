# Performance Validation

## Targets (from plan.md)

**NFR-001**: Alert latency <2 seconds from data arrival to alert logged (P95)
**NFR-006**: Memory usage MUST not exceed +50MB additional overhead

### Specific Targets
- Alert latency P95: <2000ms
- Memory overhead: <50MB

## Test Results

**Status**: SKIPPED - No performance tests found

### Investigation

Searched for performance tests in the following locations:
- `tests/order_flow/test_performance.py` - **File does not exist**
- Searched all `tests/order_flow/*.py` files for performance/benchmark markers - **None found**
- No `@pytest.mark.benchmark` or `@pytest.mark.performance` decorators found

### Files Checked
```
tests/order_flow/
├── __init__.py
├── test_config.py
├── test_order_flow_detector.py
├── test_polygon_client.py
├── test_tape_monitor.py
└── test_validators.py
```

**Expected File**: `tests/order_flow/test_performance.py` (specified in plan.md line 67)
**Actual Status**: Missing

## Metrics

Cannot measure metrics without performance tests:
- Alert latency P95: **NOT MEASURED** vs target 2000ms → SKIPPED
- Memory overhead: **NOT MEASURED** vs target 50MB → SKIPPED

## Status

**SKIPPED** (not blocking)

The implementation phase did not create performance tests as specified in the plan. This is a gap in test coverage but does not block the optimization phase from continuing.

## Recommendation

Create `tests/order_flow/test_performance.py` following the pattern from `tests/emotional_control/test_performance.py`:

### Suggested Test Structure

```python
"""
Performance Tests for Order Flow Integration

Tests: Performance benchmarks for NFR validation
"""

import time
import pytest
from decimal import Decimal
from statistics import quantiles
from datetime import datetime, UTC

from src.trading_bot.order_flow.order_flow_detector import OrderFlowDetector
from src.trading_bot.order_flow.tape_monitor import TapeMonitor
from src.trading_bot.order_flow.config import OrderFlowConfig
from src.trading_bot.order_flow.data_models import OrderBookSnapshot


@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks for OrderFlowDetector (NFR-001, NFR-006)."""

    def test_detect_large_sellers_executes_under_2s_p95(self):
        """Test detect_large_sellers() P95 latency <2s (NFR-001)."""
        # Given: OrderFlowDetector with test config
        config = OrderFlowConfig(polygon_api_key="test_key")
        detector = OrderFlowDetector(config)

        # Given: Snapshot with large bid orders
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[
                (Decimal("175.50"), 15_000),
                (Decimal("175.49"), 8_000),
                (Decimal("175.48"), 12_000),
            ],
            asks=[(Decimal("175.51"), 5_000)],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Running 100 iterations
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            alerts = detector.detect_large_sellers(snapshot)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        # Calculate P95 latency
        p95_latency = quantiles(latencies, n=20)[18]  # 95th percentile

        # Then: P95 latency < 2000ms
        assert p95_latency < 2000.0, f"P95 latency {p95_latency:.2f}ms exceeds 2s target"

    def test_tape_monitor_memory_overhead_under_50mb(self):
        """Test TapeMonitor memory usage <50MB additional (NFR-006)."""
        # This test would require memory profiling tools
        # Consider using memory_profiler or tracemalloc
        pytest.skip("Memory profiling test not implemented")
```

### Running Performance Tests

Once created, run with:
```bash
pytest tests/order_flow/test_performance.py -v -m performance
```

Or run all performance tests:
```bash
pytest -v -m performance
```

## Issues

1. **Missing Test File**: `tests/order_flow/test_performance.py` was specified in plan.md but never created during implementation
2. **No Performance Validation**: Cannot verify NFR-001 (latency) or NFR-006 (memory) targets without tests
3. **Coverage Gap**: Performance testing is part of the testing strategy (plan.md line 374) but was not implemented

### Impact

- **Low Risk**: Feature is backend-only and operates asynchronously
- **Mitigation**: Manual performance testing can be done via log analysis (plan.md line 432-436)
- **Not Blocking**: Optimization phase can continue; performance tests can be added post-deployment

## Next Steps

1. Create performance test file following the recommended structure above
2. Run tests to validate latency and memory targets
3. If tests fail, profile and optimize bottlenecks
4. Re-run validation to confirm targets are met

## Manual Performance Validation (Alternative)

If performance tests remain unimplemented, manual validation can be performed using production logs:

### Alert Latency (from logs)
```bash
# Extract latency_ms from alert logs
cat logs/order_flow/*.jsonl | jq '.latency_ms' | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}'
```

### Memory Usage (runtime monitoring)
```bash
# Before enabling order flow
ps aux | grep trading_bot | awk '{print $6}'

# After enabling order flow (compare difference)
ps aux | grep trading_bot | awk '{print $6}'
```

This manual approach requires the feature to be deployed and running in production/staging.
