# Quickstart: zone-breakout-detection

## Scenario 1: Initial Setup & Integration

```bash
# No additional dependencies needed - extends existing support_resistance module
cd D:\Coding\Stocks

# Verify parent feature is available
python -c "from src.trading_bot.support_resistance import ZoneDetector, Zone; print('✓ Parent module loaded')"

# Run existing zone detector tests to verify baseline
pytest tests/unit/support_resistance/test_zone_detector.py -v
# Expected: All tests passing (parent feature already shipped)

# Install development dependencies (if not already installed)
pip install pytest pytest-mock mypy ruff bandit

# Verify market data service integration
python -c "from src.trading_bot.market_data import MarketDataService; print('✓ MarketDataService available')"
```

## Scenario 2: Development Workflow

```bash
# 1. Create breakout detector implementation
# File: src/trading_bot/support_resistance/breakout_detector.py

# 2. Create data models
# File: src/trading_bot/support_resistance/breakout_models.py

# 3. Extend zone logger
# File: src/trading_bot/support_resistance/zone_logger.py
#   Add: log_breakout_event() method

# 4. Create configuration
# File: src/trading_bot/support_resistance/breakout_config.py

# 5. Update module exports
# File: src/trading_bot/support_resistance/__init__.py
#   Add: BreakoutDetector, BreakoutEvent, BreakoutStatus to __all__

# Run type checking during development
mypy src/trading_bot/support_resistance/breakout_detector.py --strict

# Run linting
ruff check src/trading_bot/support_resistance/breakout_detector.py

# Run security scan
bandit -r src/trading_bot/support_resistance/breakout_detector.py
```

## Scenario 3: Unit Testing

```bash
# Run breakout detector tests
pytest tests/unit/support_resistance/test_breakout_detector.py -v

# Run with coverage report
pytest tests/unit/support_resistance/test_breakout_detector.py --cov=src.trading_bot.support_resistance.breakout_detector --cov-report=term-missing

# Target: ≥90% coverage per Constitution §Testing_Requirements
# Expected output:
# src/trading_bot/support_resistance/breakout_detector.py    92%

# Run all support_resistance module tests
pytest tests/unit/support_resistance/ -v

# Run integration tests (if created)
pytest tests/integration/support_resistance/ -v
```

## Scenario 4: Manual Testing (Interactive Python)

```python
# Launch Python REPL from project root
python

# Import required modules
from decimal import Decimal
from datetime import datetime, UTC
from src.trading_bot.support_resistance import (
    ZoneDetector, ZoneDetectionConfig, ZoneLogger,
    Zone, ZoneType, Timeframe
)
from src.trading_bot.support_resistance.breakout_detector import BreakoutDetector
from src.trading_bot.support_resistance.breakout_config import BreakoutConfig
from src.trading_bot.support_resistance.breakout_models import BreakoutEvent, BreakoutStatus
from src.trading_bot.market_data import MarketDataService
from src.trading_bot.auth import RobinhoodAuth

# Mock setup (using test fixtures)
# Create a test resistance zone at $155.00
test_zone = Zone(
    price_level=Decimal("155.00"),
    zone_type=ZoneType.RESISTANCE,
    strength_score=Decimal("5.0"),
    touch_count=5,
    first_touch_date=datetime(2025, 10, 1, tzinfo=UTC),
    last_touch_date=datetime(2025, 10, 20, tzinfo=UTC),
    average_volume=Decimal("1000000"),
    highest_volume_touch=Decimal("1500000"),
    timeframe=Timeframe.DAILY
)

# Initialize breakout detector (with mock dependencies for testing)
config = BreakoutConfig()  # Uses defaults: 1.0% price, 1.3x volume
detector = BreakoutDetector(
    config=config,
    market_data_service=None,  # Replace with real service for live testing
    logger=ZoneLogger()
)

# Test Case 1: Successful Breakout
current_price = Decimal("156.60")  # +1.03% above zone
current_volume = Decimal("1400000")  # 1.4x average volume
avg_volume = Decimal("1000000")

# Calculate manually
price_change_pct = (current_price - test_zone.price_level) / test_zone.price_level * 100
volume_ratio = current_volume / avg_volume

print(f"Price change: {price_change_pct:.2f}%")  # Expected: 1.03%
print(f"Volume ratio: {volume_ratio:.2f}x")       # Expected: 1.40x
print(f"Breakout? {price_change_pct > 1.0 and volume_ratio > 1.3}")  # Expected: True

# Test Case 2: Insufficient Price Move
current_price_low = Decimal("155.50")  # +0.32% (below 1% threshold)
price_change_low = (current_price_low - test_zone.price_level) / test_zone.price_level * 100
print(f"Price change (low): {price_change_low:.2f}%")  # Expected: 0.32%
print(f"Breakout? {price_change_low > 1.0}")  # Expected: False

# Test Case 3: Insufficient Volume
low_volume = Decimal("1200000")  # 1.2x average (below 1.3x threshold)
volume_ratio_low = low_volume / avg_volume
print(f"Volume ratio (low): {volume_ratio_low:.2f}x")  # Expected: 1.20x
print(f"Breakout? {volume_ratio_low > 1.3}")  # Expected: False

# Verify zone flipping logic
# After breakout, zone should flip from RESISTANCE to SUPPORT with +2 strength bonus
flipped_zone_type = ZoneType.SUPPORT if test_zone.zone_type == ZoneType.RESISTANCE else ZoneType.RESISTANCE
new_strength = test_zone.strength_score + Decimal("2.0")

print(f"Original: {test_zone.zone_type.value} @ ${test_zone.price_level}, strength {test_zone.strength_score}")
print(f"Flipped: {flipped_zone_type.value} @ ${test_zone.price_level}, strength {new_strength}")
# Expected: "Flipped: support @ $155.00, strength 7.0"
```

## Scenario 5: Log Verification

```bash
# Trigger breakout detection (via unit test or manual script)
pytest tests/unit/support_resistance/test_breakout_detector.py::test_log_breakout_event -v

# Check JSONL log file created
ls -lh logs/zones/breakouts-*.jsonl

# Inspect log contents
cat logs/zones/breakouts-$(date +%Y-%m-%d).jsonl | jq .

# Expected JSON structure:
# {
#   "event": "breakout_detected",
#   "timestamp": "2025-10-21T12:34:56.789Z",
#   "symbol": "AAPL",
#   "zone_id": "resistance_155.50_daily",
#   "breakout_price": "156.60",
#   "close_price": "156.60",
#   "volume": "1400000",
#   "volume_ratio": "1.40",
#   "old_zone_type": "resistance",
#   "new_zone_type": "support",
#   "status": "pending"
# }

# Query breakout events by symbol
grep '"symbol":"AAPL"' logs/zones/breakouts-*.jsonl | jq .

# Query confirmed breakouts only
grep '"status":"confirmed"' logs/zones/breakouts-*.jsonl | jq .

# Calculate breakout success rate
python -c "
import json
import glob

files = glob.glob('logs/zones/breakouts-*.jsonl')
events = []
for f in files:
    with open(f, 'r') as file:
        events.extend([json.loads(line) for line in file])

confirmed = sum(1 for e in events if e.get('status') == 'confirmed')
whipsaw = sum(1 for e in events if e.get('status') == 'whipsaw')
total = confirmed + whipsaw

if total > 0:
    success_rate = confirmed / total * 100
    print(f'Breakout Success Rate: {success_rate:.1f}%')
    print(f'Confirmed: {confirmed}, Whipsaw: {whipsaw}, Total: {total}')
else:
    print('No breakout events logged yet')
"
```

## Scenario 6: Integration with Existing Bot

```python
# Example: Integrate breakout detection into trading bot workflow

from src.trading_bot.support_resistance import (
    ZoneDetector, BreakoutDetector, ZoneLogger
)
from src.trading_bot.market_data import MarketDataService
from src.trading_bot.auth import RobinhoodAuth

# Initialize services (assuming auth already configured)
auth = RobinhoodAuth(...)
market_data = MarketDataService(auth)
zone_logger = ZoneLogger()

# Initialize detectors
zone_detector = ZoneDetector(
    config=ZoneDetectionConfig.from_env(),
    market_data_service=market_data,
    zone_logger=zone_logger
)

breakout_detector = BreakoutDetector(
    config=BreakoutConfig.from_env(),
    market_data_service=market_data,
    logger=zone_logger
)

# Daily workflow: Detect zones and check for breakouts
symbol = "AAPL"

# Step 1: Identify current zones (from parent feature)
zones = zone_detector.detect_zones(symbol, days=60, timeframe=Timeframe.DAILY)
print(f"Identified {len(zones)} zones for {symbol}")

# Step 2: Get current price and volume
quote = market_data.get_quote(symbol)
historical_data = market_data.get_historical_data(symbol, days=20)
recent_volumes = [bar.volume for bar in historical_data[-20:]]  # Last 20 bars
avg_volume = sum(recent_volumes) / len(recent_volumes)

# Step 3: Check each zone for breakouts
for zone in zones:
    breakout_signal = breakout_detector.detect_breakout(
        zone=zone,
        current_price=quote.price,
        current_volume=quote.volume,
        historical_volumes=recent_volumes
    )

    if breakout_signal:
        print(f"🚨 Breakout detected!")
        print(f"  Zone: {zone.zone_type.value} @ ${zone.price_level}")
        print(f"  Current price: ${breakout_signal.event.close_price}")
        print(f"  Volume ratio: {breakout_signal.event.volume_ratio}x")
        print(f"  Flipped to: {breakout_signal.flipped_zone.zone_type.value}")
        print(f"  New strength: {breakout_signal.flipped_zone.strength_score}")

        # Use flipped zone in subsequent analysis
        # e.g., update active zones list, adjust stop losses, etc.
```

## Scenario 7: Performance Validation

```bash
# Benchmark breakout detection performance (NFR-001: <200ms target)
python -m timeit -s "
from src.trading_bot.support_resistance.breakout_detector import BreakoutDetector
from src.trading_bot.support_resistance.breakout_config import BreakoutConfig
from decimal import Decimal

detector = BreakoutDetector(BreakoutConfig(), None, None)
zone = ...  # Create test zone
price = Decimal('156.60')
volume = Decimal('1400000')
volumes = [Decimal('1000000')] * 20
" "detector._calculate_price_change_pct(Decimal('155.00'), price)"

# Expected: <5ms per calculation (well under 200ms target)

# Profile end-to-end breakout detection
python -m cProfile -s cumtime scripts/profile_breakout_detection.py
# Create profile_breakout_detection.py script that runs detect_breakout() 100 times
# Expected: P95 latency <200ms per NFR-001
```
