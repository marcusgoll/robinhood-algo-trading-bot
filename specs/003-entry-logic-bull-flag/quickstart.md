# Quickstart: 003-entry-logic-bull-flag

## Scenario 1: Initial Setup

```bash
# Install dependencies (if needed)
cd /d/Coding/Stocks
pip install -r requirements.txt

# Verify existing indicators module
python -c "from src.trading_bot.indicators import TechnicalIndicatorsService; print('Indicators OK')"

# Run unit tests for existing indicators (baseline)
pytest tests/indicators/ -v

# Expected: All existing tests pass (no breaking changes)
```

## Scenario 2: Development Workflow

```bash
# Create new patterns module structure
mkdir -p src/trading_bot/patterns
touch src/trading_bot/patterns/__init__.py
touch src/trading_bot/patterns/bull_flag.py
touch src/trading_bot/patterns/config.py
touch src/trading_bot/patterns/models.py
touch src/trading_bot/patterns/exceptions.py

# Create test directory
mkdir -p tests/patterns
touch tests/patterns/__init__.py
touch tests/patterns/test_bull_flag.py
touch tests/patterns/conftest.py

# Run pattern detection tests (TDD approach)
pytest tests/patterns/test_bull_flag.py -v --cov=src.trading_bot.patterns

# Expected: Test coverage > 90%
```

## Scenario 3: Integration Testing

```bash
# Test integration with TechnicalIndicatorsService
pytest tests/patterns/test_bull_flag_integration.py -v

# Verify no breaking changes to indicators module
pytest tests/indicators/ -v

# Run full test suite
pytest tests/ -v --cov=src.trading_bot

# Expected: All tests pass, coverage > 85%
```

## Scenario 4: Manual Pattern Detection

```python
# test_manual_detection.py
from decimal import Decimal
from src.trading_bot.patterns import BullFlagDetector
from src.trading_bot.patterns.config import BullFlagConfig

# Initialize detector with default config
detector = BullFlagDetector(config=BullFlagConfig())

# Sample OHLCV data (minimum 30 bars)
bars = [
    {"open": "175.00", "high": "176.50", "low": "174.80", "close": "176.20", "volume": "2000000"},
    # ... 28 more bars
]

# Detect pattern
result = detector.detect(bars, symbol="AAPL")

# Check results
if result.pattern_detected:
    print(f"Bull flag detected! Quality: {result.quality_score}")
    print(f"Entry: {result.entry_price}, Stop: {result.stop_loss}, Target: {result.target_price}")
    print(f"Risk/Reward: {result.risk_reward_ratio}:1")
else:
    print("No valid pattern detected")
```

## Scenario 5: Configuration Tuning

```python
# test_custom_config.py
from decimal import Decimal
from src.trading_bot.patterns import BullFlagDetector
from src.trading_bot.patterns.config import BullFlagConfig

# Custom configuration for aggressive detection
aggressive_config = BullFlagConfig(
    flagpole_min_gain_pct=Decimal("3.0"),  # Lower threshold
    quality_score_threshold=Decimal("50.0"),  # Lower quality threshold
    min_risk_reward_ratio=Decimal("1.5")  # Lower risk/reward requirement
)

detector = BullFlagDetector(config=aggressive_config)
result = detector.detect(bars, symbol="AAPL")

# Custom configuration for conservative detection
conservative_config = BullFlagConfig(
    flagpole_min_gain_pct=Decimal("8.0"),  # Higher threshold
    quality_score_threshold=Decimal("75.0"),  # Higher quality threshold
    min_risk_reward_ratio=Decimal("3.0")  # Higher risk/reward requirement
)

detector = BullFlagDetector(config=conservative_config)
result = detector.detect(bars, symbol="AAPL")
```

## Scenario 6: Error Handling

```python
# test_error_handling.py
from src.trading_bot.patterns import BullFlagDetector
from src.trading_bot.indicators.exceptions import InsufficientDataError

detector = BullFlagDetector()

# Test insufficient data
try:
    result = detector.detect(bars=[], symbol="AAPL")
except InsufficientDataError as e:
    print(f"Expected error: {e}")
    # Output: Insufficient data for AAPL: 0 bars available, 30 required

# Test with only 20 bars
short_bars = [{"open": "100", "high": "101", "low": "99", "close": "100.5", "volume": "1000000"}] * 20
try:
    result = detector.detect(bars=short_bars, symbol="AAPL")
except InsufficientDataError as e:
    print(f"Expected error: {e}")
    # Output: Insufficient data for AAPL: 20 bars available, 30 required
```

## Scenario 7: Quality Score Analysis

```python
# test_quality_scoring.py
from src.trading_bot.patterns import BullFlagDetector

detector = BullFlagDetector()
result = detector.detect(bars, symbol="AAPL")

if result.pattern_detected:
    print(f"Overall Quality Score: {result.quality_score}/100")

    # Score breakdown (calculated internally):
    # - Flagpole strength: 0-25 points (based on gain % and volume)
    # - Consolidation tightness: 0-25 points (based on retracement % and duration)
    # - Volume profile: 0-25 points (based on volume decrease during consolidation)
    # - Indicator alignment: 0-25 points (VWAP, MACD, EMA confirmation)

    if result.quality_score >= 80:
        print("High-quality pattern (priority entry)")
    elif result.quality_score >= 60:
        print("Valid pattern (acceptable entry)")
    else:
        print("Low-quality pattern (consider skipping)")
```

## Scenario 8: Validation Checklist

**Pre-merge checklist**:
- [ ] All unit tests pass (`pytest tests/patterns/ -v`)
- [ ] Integration tests pass (`pytest tests/patterns/test_bull_flag_integration.py -v`)
- [ ] No breaking changes to indicators module (`pytest tests/indicators/ -v`)
- [ ] Test coverage > 90% (`pytest --cov=src.trading_bot.patterns --cov-report=term-missing`)
- [ ] Type hints present on all public methods
- [ ] Docstrings follow numpy style (existing project pattern)
- [ ] Code passes linting (`flake8 src/trading_bot/patterns/`)
- [ ] Manual testing with sample data shows expected behavior

**Pre-deployment checklist**:
- [ ] Performance test: Process 100 stocks in < 5 seconds (NFR-001)
- [ ] Accuracy validation: False positive rate < 15% on test dataset (NFR-002)
- [ ] Configuration validation: All invalid configs raise ValueError
- [ ] Error handling: InsufficientDataError raised for < 30 bars
- [ ] Documentation updated in module docstrings
