# Quickstart: zone-bull-flag-integration

## Scenario 1: Initial Setup (No special setup required)

```bash
# No new dependencies to install
# No migrations to run
# No environment variables to configure

# Verify existing services work
cd "D:\Coding\Stocks"
uv run pytest tests/unit/services/momentum/test_bull_flag_detector.py -v
uv run pytest tests/unit/support_resistance/test_zone_detector.py -v
uv run pytest tests/unit/support_resistance/test_proximity_checker.py -v
```

## Scenario 2: Manual Testing (Integration)

### Test Case 1: Zone-adjusted target (resistance closer than 2:1)

```python
# In Python REPL or test script
import asyncio
from decimal import Decimal
from datetime import UTC, datetime
from trading_bot.momentum.bull_flag_detector import BullFlagDetector
from trading_bot.support_resistance.zone_detector import ZoneDetector
from trading_bot.momentum.config import MomentumConfig
from trading_bot.support_resistance.config import ZoneDetectionConfig
from trading_bot.market_data.market_data_service import MarketDataService

# Initialize services
momentum_config = MomentumConfig.from_env()
zone_config = ZoneDetectionConfig.from_env()
market_data = MarketDataService(...)  # Initialize with auth

# Create detectors
zone_detector = ZoneDetector(zone_config, market_data)
bull_flag_detector = BullFlagDetector(
    momentum_config,
    market_data,
    zone_detector=zone_detector  # Inject zone detector
)

# Scan for bull flags
signals = await bull_flag_detector.scan(["AAPL"])

# Verify target adjustment in details
for signal in signals:
    print(f"Symbol: {signal.symbol}")
    print(f"Adjusted target: ${signal.details['price_target']:.2f}")
    print(f"Original 2:1 target: ${signal.details['original_2r_target']:.2f}")
    print(f"Adjustment reason: {signal.details['adjustment_reason']}")
    if signal.details.get('resistance_zone_price'):
        print(f"Resistance zone: ${signal.details['resistance_zone_price']:.2f} (strength: {signal.details['resistance_zone_strength']})")
```

**Expected behavior**:
- If resistance zone within 5% above entry and closer than 2:1 target:
  - `price_target` = zone_price * 0.90
  - `adjustment_reason` = "resistance_zone_closer"
  - `resistance_zone_price` and `resistance_zone_strength` populated

- If no resistance zone within 5%:
  - `price_target` = original 2:1 R:R target
  - `adjustment_reason` = "no_zone_within_range"
  - `resistance_zone_price` = None

### Test Case 2: Graceful degradation (no zone detector)

```python
# Create BullFlagDetector WITHOUT zone_detector
bull_flag_detector = BullFlagDetector(
    momentum_config,
    market_data
    # zone_detector=None (default)
)

signals = await bull_flag_detector.scan(["AAPL"])

# Verify fallback to standard 2:1 targets
for signal in signals:
    assert signal.details['adjustment_reason'] == "zone_detector_unavailable"
    assert signal.details['price_target'] == signal.details['original_2r_target']
    assert signal.details['resistance_zone_price'] is None
```

### Test Case 3: Verify JSONL logging

```bash
# Run scan with zone integration
uv run python -c "
import asyncio
from trading_bot.momentum.bull_flag_detector import BullFlagDetector
# ... (setup from Test Case 1) ...
asyncio.run(bull_flag_detector.scan(['AAPL', 'TSLA', 'GOOGL']))
"

# Check logs for target_calculated events
grep '"event":"target_calculated"' logs/momentum/*.jsonl | tail -5
```

**Expected log entry**:
```json
{
  "event": "target_calculated",
  "symbol": "AAPL",
  "entry": 150.00,
  "adjusted_target": 139.50,
  "original_target": 156.00,
  "reason": "resistance_zone_closer",
  "zone_price": 155.00,
  "zone_strength": 7
}
```

## Scenario 3: Validation (Testing)

```bash
# Run unit tests
cd "D:\Coding\Stocks"

# Test new TargetCalculation dataclass
uv run pytest tests/unit/momentum/schemas/test_target_calculation.py -v

# Test zone integration logic
uv run pytest tests/unit/services/momentum/test_bull_flag_target_adjustment.py -v

# Test backward compatibility (existing tests should pass)
uv run pytest tests/unit/services/momentum/test_bull_flag_detector.py -v

# Integration tests
uv run pytest tests/integration/momentum/test_bull_flag_zone_integration.py -v

# Type checking
uv run mypy src/trading_bot/momentum/bull_flag_detector.py
uv run mypy src/trading_bot/momentum/schemas/momentum_signal.py

# Linting
uv run ruff check src/trading_bot/momentum/

# Coverage check (target: 90%+)
uv run pytest --cov=src/trading_bot/momentum --cov-report=term-missing tests/unit/services/momentum/
```

## Scenario 4: Backtesting (Post-Implementation)

```bash
# Run backtest comparison script (to be created in US5)
uv run python scripts/backtest_zone_adjusted_targets.py --days 90 --symbols AAPL,TSLA,GOOGL

# Expected output:
# Strategy A (Fixed 2:1):
#   Win rate: 58%
#   Avg R:R: 1.6
#   Target hit rate: 62%
#
# Strategy B (Zone-adjusted):
#   Win rate: 64% (+6%)
#   Avg R:R: 1.7 (+0.1)
#   Target hit rate: 72% (+10%)
#
# Threshold analysis:
#   85% adjustment: Win rate 63%
#   90% adjustment: Win rate 64% ← OPTIMAL
#   95% adjustment: Win rate 62%
```

## Scenario 5: Performance Validation

```bash
# Measure zone detection performance
uv run python -c "
import time
from decimal import Decimal
from trading_bot.support_resistance.zone_detector import ZoneDetector
# ... (setup) ...

# Time zone detection
start = time.perf_counter()
zones = zone_detector.detect_zones('AAPL', days=60)
duration_ms = (time.perf_counter() - start) * 1000
print(f'Zone detection: {duration_ms:.2f}ms')

# Target: <50ms P95 (spec NFR-001)
assert duration_ms < 50, 'Zone detection exceeds 50ms target'
"

# Run performance tests
uv run pytest tests/performance/test_zone_target_performance.py -v
```
