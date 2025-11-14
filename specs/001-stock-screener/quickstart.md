# Quickstart: Stock Screener

## Setup & Installation

```bash
# Navigate to project
cd /path/to/Stocks

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if new)
pip install -e .

# Verify MarketDataService is available
python -c "from trading_bot.services.market_data_service import MarketDataService; print('✓ MarketDataService ready')"
```

## Scenario 1: Unit Test Verification

**Validate core screener functionality without live market data:**

```bash
# Run all screener tests
pytest tests/test_screener/ -v --cov=src/trading_bot/services/screener_service --cov=src/trading_bot/schemas/screener_schemas --cov-report=html

# Run specific test file
pytest tests/test_screener/test_screener_service.py::test_price_range_filter -v

# Run with fixtures (mock stock data)
pytest tests/test_screener/ -v -k "test_price_range_filter or test_combined_filters"
```

**Expected Output**:
```
test_screener_service.py::test_price_range_filter PASSED
test_screener_service.py::test_relative_volume_filter PASSED
test_screener_service.py::test_float_size_filter PASSED
test_screener_service.py::test_daily_change_filter PASSED
test_screener_service.py::test_combined_filters PASSED
...
======================== 25 passed in 1.23s ========================
Coverage: 94% (target: 90%)
```

## Scenario 2: Integration Test (With Mock Market Data)

**Test screener with realistic market data (mocked):**

```python
# tests/test_screener/test_screener_integration.py

import pytest
from trading_bot.services.screener_service import ScreenerService
from trading_bot.schemas.screener_schemas import ScreenerQuery
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_market_data():
    """Mock MarketDataService with realistic stock data"""
    mock_service = MagicMock()
    mock_service.get_quote.side_effect = lambda symbol: Quote(
        symbol=symbol,
        bid=Decimal("5.50"),
        ask=Decimal("5.51"),
        volume=2500000,  # 2.5M shares (5x 500k baseline)
        # ... other fields
    )
    return mock_service

@pytest.fixture
def screener(mock_market_data):
    return ScreenerService(market_data_service=mock_market_data)

def test_screener_with_mocked_data(screener):
    result = screener.filter(ScreenerQuery(
        min_price=2.0,
        max_price=20.0,
        relative_volume=5.0
    ))
    assert result.result_count > 0
    assert all(s.bid_price >= 2.0 for s in result.stocks)
```

Run:
```bash
pytest tests/test_screener/test_screener_integration.py -v
```

## Scenario 3: Live Testing (Development Environment)

**Test screener with live Robinhood API during market hours:**

```python
# Manual test in Python REPL

from trading_bot.services.screener_service import ScreenerService
from trading_bot.services.market_data_service import MarketDataService
from trading_bot.schemas.screener_schemas import ScreenerQuery
from trading_bot.logging.screener_logger import ScreenerLogger
from decimal import Decimal

# Initialize services
market_data_service = MarketDataService(robinhood_session)
logger = ScreenerLogger()
screener = ScreenerService(market_data_service, logger)

# Test 1: Simple price range
print("Test 1: Price range filter ($2-$20)")
result = screener.filter(ScreenerQuery(
    min_price=Decimal("2.00"),
    max_price=Decimal("20.00"),
    limit=10  # Just first 10 for quick test
))
print(f"✓ Found {result.result_count} candidates")
print(f"  Execution time: {result.execution_time_ms:.1f}ms")
assert result.execution_time_ms < 500, "Performance acceptable"

# Test 2: Volume spike (5x average)
print("\nTest 2: Relative volume filter (5x+ average)")
result = screener.filter(ScreenerQuery(
    relative_volume=5.0,
    limit=10
))
print(f"✓ Found {result.result_count} high-volume candidates")

# Test 3: Combined filters (realistic trading setup)
print("\nTest 3: Combined filters (realistic setup)")
result = screener.filter(ScreenerQuery(
    min_price=Decimal("2.00"),
    max_price=Decimal("20.00"),
    relative_volume=5.0,
    float_max=20,  # Under 20M shares
    min_daily_change=10.0  # 10%+ movers
))
print(f"✓ Found {result.result_count} setup candidates")
print(f"  Top 3: {[(s.symbol, s.bid_price, f'+{s.daily_change_pct:.1f}%') for s in result.stocks[:3]]}")
print(f"  Execution time: {result.execution_time_ms:.1f}ms")

# Test 4: Pagination
print("\nTest 4: Pagination (500 max per page)")
result = screener.filter(ScreenerQuery(
    limit=500,
    offset=0
))
print(f"✓ Page 1: {result.result_count} results")
print(f"  Has more pages: {result.page_info.has_more}")
print(f"  Total candidates: {result.total_count}")

# Test 5: Error handling (invalid parameters)
print("\nTest 5: Error handling")
try:
    result = screener.filter(ScreenerQuery(
        min_price=Decimal("20.00"),
        max_price=Decimal("2.00")  # Invalid: min > max
    ))
except ValueError as e:
    print(f"✓ Caught validation error: {e}")
```

**Expected Output**:
```
Test 1: Price range filter ($2-$20)
✓ Found 47 candidates
  Execution time: 187.3ms

Test 2: Relative volume filter (5x+ average)
✓ Found 12 high-volume candidates

Test 3: Combined filters (realistic setup)
✓ Found 3 setup candidates
  Top 3: [('TSLA', 248.50, '+5.3%'), ('NVDA', 142.25, '+3.8%'), ('AMZN', 201.75, '+2.1%')]
  Execution time: 234.5ms

Test 4: Pagination (500 max per page)
✓ Page 1: 500 results
  Has more pages: True
  Total candidates: 2847

Test 5: Error handling
✓ Caught validation error: min_price (20.0) >= max_price (2.0), must have min < max
```

## Scenario 4: JSONL Audit Trail Validation

**Verify all queries are logged to JSONL:**

```bash
# Check latest screener logs
tail -f logs/screener/2025-10-16.jsonl

# Parse specific event
cat logs/screener/2025-10-16.jsonl | jq 'select(.event=="screener.query_completed")'

# Query statistics
cat logs/screener/2025-10-16.jsonl | jq -r '.execution_time_ms' | awk '{sum+=$1; count++} END {print "Avg latency:", sum/count, "ms"}'
```

**Expected Output** (JSONL entry):
```json
{
  "timestamp": "2025-10-16T14:32:15.234Z",
  "event": "screener.query_completed",
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "query_params": {
    "min_price": 2.0,
    "max_price": 20.0,
    "relative_volume": 5.0,
    "float_max": 20,
    "min_daily_change": null,
    "limit": 500,
    "offset": 0
  },
  "result_count": 42,
  "total_count": 42,
  "execution_time_ms": 187.5,
  "api_calls": 3,
  "data_gaps": [],
  "error": null,
  "retry_count": 0,
  "filters_active": ["price_range", "relative_volume", "float_size"]
}
```

## Scenario 5: Type Checking & Linting

**Validate code quality before commit:**

```bash
# Type checking (strict mode)
mypy src/trading_bot/services/screener_service.py --strict
mypy src/trading_bot/schemas/screener_schemas.py --strict
mypy src/trading_bot/logging/screener_logger.py --strict

# Linting
ruff check src/trading_bot/services/screener_service.py
ruff check src/trading_bot/schemas/screener_schemas.py

# Fix auto-fixable issues
ruff check --fix src/trading_bot/services/screener_service.py

# All tests + coverage
pytest tests/test_screener/ --cov=src/trading_bot/services/screener_service --cov-report=term-missing
```

**Expected Output**:
```
Success: no issues found in mypy
Success: no linting issues found
======================== 25 passed in 1.23s ========================
Name                                  Stmts   Miss  Cover
screener_service.py                     42      3    93%
screener_schemas.py                     18      0   100%
screener_logger.py                      28      2    93%
TOTAL                                   88      5    94%
```

## Scenario 6: Backtesting (Historical Validation)

**Optional P2: Validate screener setup accuracy against historical data:**

```python
# backtests/test_screener_setup_accuracy.py

from trading_bot.backtesting import BacktestScreener
from trading_bot.schemas.screener_schemas import ScreenerQuery
from datetime import datetime, timedelta

backtest = BacktestScreener(screener)

# Run screener on each market day last 50 days
results = backtest.run(
    start_date=datetime.now() - timedelta(days=50),
    end_date=datetime.now(),
    query=ScreenerQuery(
        min_price=2.0,
        max_price=20.0,
        relative_volume=5.0,
        min_daily_change=10.0
    )
)

print(f"Backtest Results (50 trading days)")
print(f"Setup success rate: {results.setup_success_rate:.1%}")  # % preceded +5% moves
print(f"False positive rate: {results.false_positive_rate:.1%}")
print(f"Avg drawdown from miss: {results.avg_drawdown:.1%}")
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'trading_bot.services.screener_service'"

**Solution**: Ensure you've completed setup:
```bash
pip install -e .
python -c "from trading_bot.services.screener_service import ScreenerService; print('OK')"
```

### Issue: "AssertionError: Latency 567ms exceeds 500ms target"

**Solution**: Screener hit rate limiting from Robinhood API. Check:
```bash
# View retry attempts in logs
grep "RateLimitError\|retry" logs/trading_bot.log | tail -20

# Reduce candidate set or wait for rate limit window
# @with_retry will exponential backoff (1s, 2s, 4s) and retry up to 3 times
```

### Issue: "ValueError: No quotes available for symbol XYZ"

**Solution**: Stock halted or data unavailable. Screener logs data gap:
```bash
grep "data_gap\|XYZ" logs/screener/2025-10-16.jsonl
# Should see: "XYZ: float unavailable" or similar

# Screener continues with other stocks (graceful degradation)
```

---

## Next: Run Tests & Commit

When ready to move to `/tasks` phase:

```bash
# Run all tests
pytest tests/test_screener/ -v --cov

# Type check
mypy src/trading_bot/services/screener_service.py --strict

# Lint
ruff check --fix src/trading_bot/services/screener_service.py

# Commit
git add -A
git commit -m "feat: add screener service with tests"

# Next phase
# /tasks
```
