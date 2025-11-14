# Quickstart: Momentum and Catalyst Detection

**Feature**: 002-momentum-detection
**Status**: Ready for implementation

---

## Scenario 1: Initial Setup

### Prerequisites

- Python 3.9+
- Existing `trading_bot` codebase environment set up
- Access to Alpaca API (market data and pre-market quotes)
- Optional: News API key (NewsAPI, Finnhub, or Alpaca news endpoint)

### Setup Steps

```bash
# 1. Navigate to project root
cd /path/to/Stocks

# 2. Install dependencies (if new packages needed)
pip install -r requirements.txt
# Note: MVP uses existing dependencies only

# 3. Set environment variables
export NEWS_API_KEY="your-news-api-key-here"
export MARKET_DATA_API_KEY="your-alpaca-key-here"

# 4. Verify market data service works
python -c "
from src.trading_bot.services.market_data_service import MarketDataService
mds = MarketDataService()
quote = mds.get_quote('AAPL')
print(f'✅ Market data OK: {quote.symbol} @ {quote.last_trade_price}')
"

# 5. Run unit tests for momentum module
pytest tests/unit/services/momentum/ -v

# 6. Verify logging directory exists
mkdir -p logs/momentum

# 7. Start trading bot
python -m trading_bot
```

### Expected Output

```
✅ Market data OK: AAPL @ 195.42
collected 24 items
test_catalyst_detector.py::test_fetch_news PASSED
test_premarket_scanner.py::test_identify_movers PASSED
test_bull_flag_detector.py::test_detect_pattern PASSED
[INFO] Trading bot started on http://localhost:8000
[INFO] Momentum detection engine initialized
```

---

## Scenario 2: Validation & Testing

### Unit Tests

```bash
# Run all momentum tests
pytest tests/unit/services/momentum/ -v

# Run with coverage
pytest tests/unit/services/momentum/ --cov=src.trading_bot.momentum --cov-report=html

# Run specific test
pytest tests/unit/services/momentum/test_bull_flag_detector.py::test_detect_valid_pattern -v
```

### Integration Tests

```bash
# Run with mock APIs (recommended for CI/CD)
pytest tests/integration/momentum/ -v -m "mock_api"

# Run with real APIs (requires credentials)
pytest tests/integration/momentum/ -v -m "live_api"
```

### Type Checking

```bash
# Verify type hints
mypy src/trading_bot/momentum/ --strict

# Show any type errors
mypy src/trading_bot/momentum/ --show-error-codes
```

### Code Quality

```bash
# Run linter
flake8 src/trading_bot/momentum/ --max-line-length=100

# Run formatter check
black --check src/trading_bot/momentum/

# Format code
black src/trading_bot/momentum/
```

---

## Scenario 3: Manual Testing via API

### Start Development Server

```bash
# Terminal 1: Start bot with debug logging
RUST_LOG=debug python -m trading_bot

# Terminal 2: Run test commands
```

### Test Catalyst Detection

```bash
# Query signals API (should be empty initially)
curl -s http://localhost:8000/api/v1/momentum/signals | jq .

# Trigger catalyst scan for specific stocks
curl -X POST http://localhost:8000/api/v1/momentum/scan \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "GOOGL", "TSLA"],
    "scan_types": ["catalyst"]
  }' | jq .

# Response:
# {
#   "scan_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "queued",
#   "estimated_completion": "2025-10-16T14:35:00Z"
# }

# Poll for results
curl -s http://localhost:8000/api/v1/momentum/scan/550e8400-e29b-41d4-a716-446655440000 | jq .
```

### Test Pre-Market Scanner

```bash
# Run pre-market scan (only works 4:00-9:30 AM EST)
curl -X POST http://localhost:8000/api/v1/momentum/scan \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "GOOGL", "TSLA"],
    "scan_types": ["premarket"]
  }' | jq .

# Outside pre-market hours: expects empty results
# {"signals": [], "total": 0}
```

### Test Bull Flag Pattern Detection

```bash
# Scan for patterns (uses historical data, works anytime)
curl -X POST http://localhost:8000/api/v1/momentum/scan \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "GOOGL", "TSLA", "AMD", "NVDA"],
    "scan_types": ["bull_flag"]
  }' | jq .

# Expected response with pattern signals
# {
#   "signals": [
#     {
#       "id": "...",
#       "symbol": "NVDA",
#       "signal_type": "bull_flag",
#       "strength": 82.5,
#       "metadata": {
#         "pole_gain_pct": 15.2,
#         "breakout_price": 875.50,
#         "price_target": 920.00
#       }
#     }
#   ]
# }
```

### Query Signals with Filters

```bash
# Get high-strength signals only
curl -s "http://localhost:8000/api/v1/momentum/signals?min_strength=80" | jq .

# Filter by signal type
curl -s "http://localhost:8000/api/v1/momentum/signals?signal_type=bull_flag" | jq .

# Filter by symbol
curl -s "http://localhost:8000/api/v1/momentum/signals?symbols=AAPL,TSLA" | jq .

# Sort and paginate
curl -s "http://localhost:8000/api/v1/momentum/signals?sort_by=timestamp&sort_order=desc&limit=10&offset=0" | jq .

# Time range query
curl -s "http://localhost:8000/api/v1/momentum/signals?start_time=2025-10-15T00:00:00Z&end_time=2025-10-16T23:59:59Z" | jq .
```

### Check Service Health

```bash
# Verify momentum detection service health
curl -s http://localhost:8000/api/v1/momentum/health | jq .

# Expected response:
# {
#   "status": "ok",
#   "dependencies": {
#     "market_data": "ok",
#     "news_api": "ok",
#     "logging": "ok"
#   }
# }
```

---

## Scenario 4: Review Logs

### JSONL Log Files

```bash
# View today's momentum signals (tail last 10 lines)
tail -10 logs/momentum/2025-10-16.jsonl

# View formatted (pretty JSON)
tail -10 logs/momentum/2025-10-16.jsonl | jq .

# Count signals by type
grep signal_detected logs/momentum/2025-10-16.jsonl | jq -r '.signal_type' | sort | uniq -c

# Find errors
grep -i error logs/momentum/2025-10-16.jsonl | jq .
```

### Extract Metrics

```bash
# Calculate average signal strength
cat logs/momentum/2025-10-16.jsonl | \
  grep signal_detected | \
  jq '.strength' | \
  awk '{ sum += $1; count++ } END { print "Average:", sum/count }'

# Find slowest scan
cat logs/momentum/2025-10-16.jsonl | \
  grep scan_completed | \
  jq '.execution_time_ms' | \
  sort -rn | head -1

# Count by symbol
cat logs/momentum/2025-10-16.jsonl | \
  grep signal_detected | \
  jq -r '.symbol' | \
  sort | uniq -c | sort -rn
```

---

## Scenario 5: Development Workflow

### Adding a New Detector

```python
# 1. Create new detector in api/src/trading_bot/momentum/
# File: my_detector.py

from typing import List
from src.trading_bot.momentum.schemas import MomentumSignal
from src.trading_bot.utils.resilience import with_retry

class MyDetector:
    """Custom momentum detector for new signal type"""

    @with_retry(max_attempts=3)
    async def scan(self, symbols: List[str]) -> List[MomentumSignal]:
        """Implement detection logic"""
        signals = []
        for symbol in symbols:
            # Your detection code here
            pass
        return signals

# 2. Add unit tests
# File: tests/unit/services/momentum/test_my_detector.py

import pytest
from src.trading_bot.momentum.my_detector import MyDetector

@pytest.mark.asyncio
async def test_detect_signal():
    detector = MyDetector()
    signals = await detector.scan(["AAPL"])
    assert len(signals) >= 0

# 3. Integrate with MomentumEngine
# File: api/src/trading_bot/momentum/__init__.py

class MomentumEngine:
    def __init__(self, config):
        # ... existing detectors ...
        self.my_detector = MyDetector(config)

    async def scan(self, symbols):
        # ... existing code ...
        my_signals = await self.my_detector.scan(symbols)
        all_signals += my_signals
        return self.ranker.rank(all_signals)

# 4. Run tests
pytest tests/unit/services/momentum/test_my_detector.py -v
```

### Performance Profiling

```bash
# Profile single symbol scan
python -m cProfile -s cumtime -c "
import asyncio
from src.trading_bot.momentum import MomentumEngine

async def profile():
    engine = MomentumEngine()
    await engine.scan(['AAPL'])

asyncio.run(profile())
" | head -20

# Expected: Most time in MarketDataService API calls

# Profile batch scan
python -m cProfile -s cumtime -c "
import asyncio
from src.trading_bot.momentum import MomentumEngine

async def profile():
    engine = MomentumEngine()
    symbols = ['AAPL', 'GOOGL', 'TSLA', 'AMZN', 'NVDA']
    await engine.scan(symbols)

asyncio.run(profile())
" | head -20
```

---

## Scenario 6: Troubleshooting

### Missing News API Key

```bash
# Symptom: Catalyst detection silently skipped
# Check logs
grep -i "api key" logs/momentum/2025-10-16.jsonl

# Solution: Set environment variable
export NEWS_API_KEY="your-key-here"
python -m trading_bot
```

### Pre-Market Scanner Returns Empty Outside Hours

```bash
# Symptom: No pre-market signals except 4:00-9:30 AM EST
# This is expected behavior - pre-market only exists in that window

# Solution: Test during market hours (fake clock for testing)
# Or: Query pre-market data for previous day
curl -s "http://localhost:8000/api/v1/momentum/signals?start_time=2025-10-15T04:00:00Z&end_time=2025-10-15T09:30:00Z&signal_type=premarket_mover" | jq .
```

### Bull Flag Detection Too Strict/Loose

```bash
# Symptom: Not enough patterns detected (or too many false positives)
# Check NOTES.md for tuning documentation

# Current thresholds:
# - Pole: >8% gain
# - Flag: 3-5% range
# - Duration: pole 1-3 days, flag 2-5 days

# To adjust thresholds:
# 1. Edit api/src/trading_bot/momentum/bull_flag_detector.py
# 2. Change POLE_MIN_GAIN_PCT, FLAG_RANGE_PCT, etc.
# 3. Run tests: pytest tests/unit/services/momentum/test_bull_flag_detector.py -v
# 4. Validate with backtesting
```

### API Rate Limit Errors

```bash
# Symptom: 429 Too Many Requests errors
# Check logs
grep 429 logs/momentum/2025-10-16.jsonl

# Solution: Enable caching (Phase 2)
# For now: Increase scan interval or reduce symbol batch size
curl -X POST http://localhost:8000/api/v1/momentum/scan \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL"],  # Smaller batch
    "scan_types": ["catalyst", "bull_flag"]
  }' | jq .

# Wait before next scan
sleep 2
```

---

## Next Steps

After completing setup and validation:

1. **Review code**: Check the generated services in `api/src/trading_bot/momentum/`
2. **Adjust thresholds**: Tune pattern detection thresholds based on historical backtesting
3. **Add alerting** (Phase 3): Implement real-time alerts when high-strength signals detected
4. **Deploy locally**: Follow deployment procedure to add to your trading pipeline
5. **Backtest**: Use historical signals to validate system accuracy before live trading

---

## References

- **API Documentation**: See `contracts/api.yaml` for full OpenAPI spec
- **Data Model**: See `data-model.md` for entity definitions
- **Architecture**: See `plan.md` for design decisions and reuse analysis
- **Troubleshooting**: See `NOTES.md` for common issues and solutions
- **Implementation**: See `tasks.md` for task breakdown and dependencies
