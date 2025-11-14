# Quickstart: 023-support-resistance-mapping

## Scenario 1: Initial Setup

```bash
# No new dependencies required - uses existing robin_stocks, pandas, Decimal
# Verify Python environment
python --version  # Should be 3.11+

# Install project dependencies (if not already done)
pip install -r requirements.txt

# No database migrations needed - in-memory processing only
# No seed data needed - uses live market data via Robinhood API
```

## Scenario 2: Running Zone Detection

```python
# Example usage of SupportResistanceDetector
from trading_bot.support_resistance.zone_detector import SupportResistanceDetector
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.auth.robinhood_auth import RobinhoodAuth

# Initialize dependencies
auth = RobinhoodAuth()
auth.login()  # Uses credentials from env vars

market_data = MarketDataService(auth)
detector = SupportResistanceDetector(market_data)

# Detect zones for a symbol
zones = detector.detect_zones("AAPL", days=60, timeframe="daily")

# Print results
for zone in zones:
    print(f"{zone.zone_type.value.upper()} at ${zone.price_level:.2f}")
    print(f"  Strength: {zone.strength_score} (touches: {zone.touch_count})")
    print(f"  Last touch: {zone.last_touch_date.date()}")
    print()

# Check proximity alerts
current_price = Decimal("150.00")
alerts = detector.check_proximity(zones, current_price)

for alert in alerts:
    print(f"Alert: Price ${alert.current_price:.2f} approaching {alert.direction.value}")
    print(f"  Zone: ${alert.zone_price:.2f} ({alert.distance_percent:.2f}% away)")
```

## Scenario 3: Validation

```bash
# Run unit tests for zone detection
pytest tests/unit/support_resistance/test_zone_detector.py -v

# Run integration tests with live data (requires auth)
pytest tests/integration/support_resistance/test_zone_detector.py -v

# Check type annotations
mypy src/trading_bot/support_resistance/

# Lint code
ruff check src/trading_bot/support_resistance/
```

## Scenario 4: Manual Testing

1. **Test zone identification**:
   ```python
   # Run detection on known stock with clear S/R levels
   detector = SupportResistanceDetector(market_data)
   zones = detector.detect_zones("AAPL", days=90, timeframe="daily")

   # Verify: Should find 3-5 major zones
   # Verify: Zones should have 3+ touches each
   # Verify: Strength scores rank zones correctly
   ```

2. **Test proximity alerts**:
   ```python
   # Simulate price approaching resistance
   current_price = Decimal("155.00")
   zones = [Zone(price_level=Decimal("158.00"), zone_type=ZoneType.RESISTANCE, ...)]
   alerts = detector.check_proximity(zones, current_price)

   # Verify: Alert triggered (1.94% distance < 2% threshold)
   # Verify: Direction = APPROACHING_RESISTANCE
   ```

3. **Check log output**:
   ```bash
   # Verify structured logs created
   ls -la logs/zones/
   cat logs/zones/2025-10-21.jsonl | tail -10

   # Validate JSON format
   cat logs/zones/2025-10-21.jsonl | jq '.' | head -20
   ```

## Scenario 5: Backtesting Zone Accuracy

```python
# Test historical zone accuracy
from trading_bot.support_resistance.backtest_zones import backtest_zone_accuracy

# Analyze how often identified zones predict future reversals
results = backtest_zone_accuracy(
    symbol="AAPL",
    start_date="2024-01-01",
    end_date="2025-01-01"
)

print(f"Zone hit rate: {results['hit_rate']:.1f}%")
print(f"False positives: {results['false_positive_rate']:.1f}%")
print(f"Average zone lifespan: {results['avg_lifespan_days']:.0f} days")

# Verify: Hit rate >70% (per success metrics)
# Verify: False positives <30%
```

## Scenario 6: Integration with Bull Flag Entry Logic

```python
# Example: Adjust bull flag targets based on nearest resistance
from trading_bot.momentum.bull_flag_detector import BullFlagDetector
from trading_bot.support_resistance.zone_detector import SupportResistanceDetector

# Detect bull flag pattern
bull_flag_detector = BullFlagDetector(config, market_data)
signals = bull_flag_detector.scan(["AAPL"])

# Get resistance zones
zone_detector = SupportResistanceDetector(market_data)
zones = zone_detector.detect_zones("AAPL", days=60, timeframe="daily")
resistance_zones = [z for z in zones if z.zone_type == ZoneType.RESISTANCE]

# Adjust target if resistance nearby
if signals:
    entry_price = signals[0].details['entry_price']
    standard_target = entry_price * Decimal("1.04")  # 2:1 R:R with 2% risk

    # Find nearest resistance above entry
    nearby_resistance = [z for z in resistance_zones if z.price_level > entry_price]

    if nearby_resistance:
        nearest = min(nearby_resistance, key=lambda z: z.price_level)
        if nearest.price_level < standard_target:
            adjusted_target = nearest.price_level * Decimal("0.90")  # 90% of zone
            print(f"Target adjusted: ${standard_target:.2f} → ${adjusted_target:.2f}")
            print(f"Reason: Resistance zone at ${nearest.price_level:.2f}")
```
