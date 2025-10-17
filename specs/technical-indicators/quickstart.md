# Quickstart: technical-indicators

## Scenario 1: Calculate VWAP for Entry Validation

```python
# Setup
from trading_bot.indicators import TechnicalIndicatorsService
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.indicators.config import IndicatorConfig
from decimal import Decimal

# Initialize services
market_data = MarketDataService(auth=auth_instance)
config = IndicatorConfig()
indicators = TechnicalIndicatorsService(market_data, config)

# Calculate VWAP
vwap_result = indicators.get_vwap("AAPL")
print(f"VWAP: ${vwap_result.vwap}")
print(f"Current Price: ${vwap_result.price}")
print(f"Bars used: {vwap_result.bars_used}")

# Validate entry
if vwap_result.price > vwap_result.vwap:
    print("✅ Entry allowed: Price above VWAP")
else:
    print("❌ Entry blocked: Price below VWAP")
```

**Expected Output**:
```
VWAP: $150.25
Current Price: $152.00
Bars used: 25
✅ Entry allowed: Price above VWAP
```

---

## Scenario 2: Calculate EMAs and Detect Crossover

```python
# Calculate EMAs (9 and 20-period)
ema_result = indicators.get_emas("AAPL")
print(f"EMA-9: ${ema_result.ema_9}")
print(f"EMA-20: ${ema_result.ema_20}")
print(f"Current Price: ${ema_result.current_price}")

# Check for crossover
if ema_result.crossover:
    crossover = ema_result.crossover
    print(f"🚨 Crossover detected: {crossover.type}")
    print(f"   EMA-9: ${crossover.ema_short}, EMA-20: ${crossover.ema_long}")
else:
    print("No crossover detected")

# Check proximity to 9-EMA
from trading_bot.indicators.ema_calculator import EMACalculator
ema_calc = EMACalculator(config)
is_near = ema_calc.check_proximity(
    price=ema_result.current_price,
    ema=ema_result.ema_9,
    threshold_pct=2.0
)
if is_near:
    print("✅ Optimal entry zone: Price within 2% of 9-EMA")
```

**Expected Output**:
```
EMA-9: $151.50
EMA-20: $149.80
Current Price: $152.00
🚨 Crossover detected: bullish
   EMA-9: $151.50, EMA-20: $149.80
✅ Optimal entry zone: Price within 2% of 9-EMA
```

---

## Scenario 3: Calculate MACD and Check Exit Signals

```python
# Calculate MACD
macd_result = indicators.get_macd("AAPL")
print(f"MACD Line: {macd_result.macd_line}")
print(f"Signal Line: {macd_result.signal_line}")
print(f"Histogram: {macd_result.histogram}")

# Validate momentum for entry
from trading_bot.indicators.macd_calculator import MACDCalculator
macd_calc = MACDCalculator(config)
momentum_ok = macd_calc.validate_momentum(macd_result.macd_line)
if momentum_ok:
    print("✅ Momentum confirmed: MACD positive")
else:
    print("❌ Momentum weak: MACD negative")

# Check exit signals (requires previous MACD result)
# In real usage, you'd store previous result for comparison
previous_macd = MACDResult(
    symbol="AAPL",
    macd_line=Decimal("1.50"),
    signal_line=Decimal("1.40"),
    histogram=Decimal("0.10"),
    calculated_at=previous_timestamp
)

exit_signal = macd_calc.check_exit_signal(macd_result, previous_macd)
if exit_signal:
    print(f"🚨 Exit signal: {exit_signal.reason}")
    print(f"   MACD: {exit_signal.macd_value}, Signal: {exit_signal.signal_value}")
```

**Expected Output**:
```
MACD Line: +2.50
Signal Line: +1.80
Histogram: +0.70
✅ Momentum confirmed: MACD positive
```

---

## Scenario 4: Batch Calculate All Indicators

```python
# Calculate all indicators at once
indicator_set = indicators.get_all_indicators("AAPL")

print(f"Symbol: {indicator_set.symbol}")
print(f"Calculated at: {indicator_set.calculated_at}")
print("")
print(f"VWAP: ${indicator_set.vwap.vwap}")
print(f"EMA-9: ${indicator_set.emas.ema_9}")
print(f"EMA-20: ${indicator_set.emas.ema_20}")
print(f"MACD: {indicator_set.macd.macd_line}")
print(f"Signal: {indicator_set.macd.signal_line}")
```

**Expected Output**:
```
Symbol: AAPL
Calculated at: 2025-10-17 14:30:00+00:00

VWAP: $150.25
EMA-9: $151.50
EMA-20: $149.80
MACD: +2.50
Signal: +1.80
```

---

## Scenario 5: Validate Entry (Combined VWAP and MACD)

```python
# Validate entry with both VWAP and MACD checks
current_price = Decimal("152.00")
validation = indicators.validate_entry("AAPL", current_price)

print(f"Entry validation: {'ALLOWED' if validation.allowed else 'BLOCKED'}")
print(f"Reason: {validation.reason}")
print(f"Price: ${validation.price}")
print(f"VWAP: ${validation.vwap}")
print(f"MACD: {validation.macd}")

if validation.allowed:
    print("✅ All checks passed - proceed with entry")
else:
    print("❌ Entry blocked - skip this trade")
```

**Expected Output (allowed)**:
```
Entry validation: ALLOWED
Reason: Price above VWAP (+1.17%) and MACD positive (+2.50)
Price: $152.00
VWAP: $150.25
MACD: +2.50
✅ All checks passed - proceed with entry
```

**Expected Output (blocked)**:
```
Entry validation: BLOCKED
Reason: Price below VWAP (-1.50%)
Price: $148.00
VWAP: $150.25
MACD: +2.50
❌ Entry blocked - skip this trade
```

---

## Scenario 6: Intraday Indicator Refresh

```python
# Refresh indicators for multiple symbols during trading hours
watchlist = ["AAPL", "GOOGL", "TSLA", "MSFT", "NVDA"]

print("Refreshing indicators for watchlist...")
indicators.refresh_indicators(watchlist)
print("✅ Indicators refreshed")

# Now get fresh indicators for any symbol
fresh_indicators = indicators.get_all_indicators("AAPL")
print(f"Fresh VWAP: ${fresh_indicators.vwap.vwap}")
print(f"Calculated at: {fresh_indicators.calculated_at}")
```

**Expected Output**:
```
Refreshing indicators for watchlist...
✅ Indicators refreshed
Fresh VWAP: $151.80
Calculated at: 2025-10-17 14:35:00+00:00
```

---

## Scenario 7: Error Handling (Insufficient Data)

```python
try:
    # Try to calculate indicators for newly listed stock with <50 days history
    indicators.get_emas("NEWSTOCK")
except InsufficientDataError as e:
    print(f"❌ Error: {e}")
    print(f"   Symbol: {e.symbol}")
    print(f"   Required: {e.required_bars} bars")
    print(f"   Available: {e.available_bars} bars")
    print("   Skipping this symbol...")
```

**Expected Output**:
```
❌ Error: Insufficient data for EMA calculation
   Symbol: NEWSTOCK
   Required: 40 bars
   Available: 15 bars
   Skipping this symbol...
```

---

## Scenario 8: Run Tests

```bash
# Unit tests
pytest tests/indicators/test_vwap_calculator.py -v
pytest tests/indicators/test_ema_calculator.py -v
pytest tests/indicators/test_macd_calculator.py -v

# Integration tests
pytest tests/indicators/test_technical_indicators_service.py -v

# Coverage report
pytest tests/indicators/ --cov=src/trading_bot/indicators --cov-report=term-missing

# Type checking
mypy src/trading_bot/indicators/

# Security scan
bandit -r src/trading_bot/indicators/
```

**Expected Output**:
```
============================= test session starts ==============================
collected 45 items

tests/indicators/test_vwap_calculator.py::test_calculate_vwap PASSED     [  2%]
tests/indicators/test_vwap_calculator.py::test_validate_entry_above_vwap PASSED [  4%]
tests/indicators/test_vwap_calculator.py::test_validate_entry_below_vwap PASSED [  6%]
...
tests/indicators/test_macd_calculator.py::test_check_exit_signal_zero_cross PASSED [100%]

============================== 45 passed in 2.34s ===============================

----------- coverage: platform win32, python 3.11.5 -----------
Name                                              Stmts   Miss  Cover   Missing
-------------------------------------------------------------------------------
src/trading_bot/indicators/__init__.py               45      2    96%   123-124
src/trading_bot/indicators/vwap_calculator.py        38      1    97%   89
src/trading_bot/indicators/ema_calculator.py         52      2    96%   145-146
src/trading_bot/indicators/macd_calculator.py        47      1    98%   178
-------------------------------------------------------------------------------
TOTAL                                               182      6    97%

Success: no issues found in 4 source files
[bandit] No issues identified.
```

---

## Scenario 9: Manual Validation Against TradingView

```python
# Compare calculated values to TradingView for accuracy validation
import pandas as pd

symbol = "AAPL"
indicators = TechnicalIndicatorsService(market_data, config)

# Calculate our indicators
result = indicators.get_all_indicators(symbol)

print("Our calculations:")
print(f"  EMA-9: ${result.emas.ema_9:.2f}")
print(f"  EMA-20: ${result.emas.ema_20:.2f}")
print(f"  MACD: {result.macd.macd_line:.2f}")
print(f"  Signal: {result.macd.signal_line:.2f}")
print("")
print("TradingView values (manually check):")
print("  Navigate to: https://www.tradingview.com/chart/?symbol=AAPL")
print("  Add indicators: EMA(9), EMA(20), MACD(12,26,9)")
print("  Compare values to ensure accuracy")
print("")
print("✅ Values should match within 0.5% (minor calculation differences acceptable)")
```

---

## Integration Notes

**Prerequisites**:
- Authenticated RobinhoodAuth instance
- MarketDataService initialized
- Trading hours (7am-10am EST) for VWAP calculations
- Minimum 50 days of historical data for EMA/MACD

**Common Pitfalls**:
1. Calling `get_vwap()` outside trading hours → Use `market_data.is_market_open()` first
2. New stocks with <50 days history → Catch `InsufficientDataError`
3. API rate limits → MarketDataService handles retries automatically
4. Float precision issues → Always use Decimal for price comparisons

**Performance**:
- VWAP calculation: <500ms
- EMA calculation: <500ms
- MACD calculation: <1s
- Batch (all indicators): <2s
- Refresh (5 symbols): <10s
