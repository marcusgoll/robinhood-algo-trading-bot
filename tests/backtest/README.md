# Backtest Integration Tests

Integration tests for the backtesting engine's end-to-end data loading functionality.

## Overview

This directory contains integration tests for the backtesting engine, specifically focused on:
- Real API calls to Alpaca (primary) and Yahoo Finance (fallback)
- Data quality validation with real market data
- Performance benchmarking (NFR-002: <60s for 10 stocks)
- Cache persistence and performance

## Test Files

### `test_integration_data.py`
**Task**: T018 [US1] - End-to-end data loading integration tests

Tests REAL API calls to external services (Alpaca, Yahoo Finance) to validate:
1. Data fetching for one year (252 trading days)
2. Multi-stock loading performance (<30s for 5 stocks)
3. Data quality validation (OHLC relationships, gaps, chronological order)
4. API fallback (Alpaca → Yahoo Finance)
5. Error handling (invalid symbols, missing credentials)

## Running Integration Tests

### Prerequisites

1. **Alpaca API Credentials** (required for primary API tests):
   ```bash
   export ALPACA_API_KEY="your_key_here"
   export ALPACA_SECRET_KEY="your_secret_here"
   ```

2. **Python Dependencies**:
   ```bash
   pip install -e ".[dev,backtest]"
   pip install alpaca-py yfinance pyarrow
   ```

### Run All Integration Tests

```bash
# Run with coverage disabled (integration tests don't need coverage)
pytest tests/backtest/test_integration_data.py -v -m integration --no-cov

# Run with detailed output
pytest tests/backtest/test_integration_data.py -v -m integration --no-cov -s

# Run specific test
pytest tests/backtest/test_integration_data.py::TestEndToEndDataLoading::test_load_one_year_data -v --no-cov
```

### Skip Integration Tests

Integration tests are automatically skipped if `ALPACA_API_KEY` is not set:

```bash
# Without credentials - tests will be skipped
pytest tests/backtest/test_integration_data.py -v -m integration --no-cov
# Output: 5 skipped in 0.85s
```

## Test Coverage

### Test: `test_load_one_year_data`
**What it tests**:
- Fetch AAPL data for entire year 2023 (Jan 1 - Dec 31)
- Verify ~252 bars returned (252 trading days in 2023)
- Validate all OHLCV fields populated correctly
- Check no gaps in trading days (max 3 days for weekends/holidays)
- Verify data quality (positive prices, high >= low, etc.)
- Test cache persistence (second call uses cache, <1s)

**Performance**: First call ~5-10s (API + cache write), subsequent calls <1s (cache hit)

### Test: `test_load_multiple_stocks_performance`
**What it tests**:
- Load 5 stocks (AAPL, MSFT, GOOGL, TSLA, NVDA) for 2023
- Verify all stocks have ~252 bars
- Performance: <30s total (extrapolates to <60s for 10 stocks per NFR-002)
- Cache hit performance (<1s for cached symbol)

**Performance Target**: <30s for 5 stocks, <60s for 10 stocks (NFR-002)

### Test: `test_data_quality_validation_integration`
**What it tests**:
- Fetch recent data (last 30 days)
- Validate OHLC relationships with real data
- Ensure chronological order
- Verify no data quality errors raised

### Test: `test_api_fallback_to_yahoo_finance`
**What it tests**:
- Force Alpaca failure (invalid credentials)
- Verify Yahoo Finance fallback succeeds
- Validate data structure and quality from Yahoo

**Note**: Yahoo Finance does not require API keys, so this test always runs.

### Test: `test_insufficient_data_error`
**What it tests**:
- Invalid symbol (INVALID_SYMBOL_XYZ123)
- Verify InsufficientDataError raised
- Test error handling for both API sources failing

## Performance Benchmarks

Based on NFR-002 requirements:

| Operation | Target | Typical Performance |
|-----------|--------|---------------------|
| Load 1 stock (1 year) | <10s | ~5-10s (first call), <1s (cached) |
| Load 5 stocks (1 year) | <30s | ~15-25s (first call), <5s (cached) |
| Load 10 stocks (1 year) | <60s | ~30-50s (first call), <10s (cached) |
| Cache hit | <1s | ~0.1-0.5s |

## Pytest Markers

Integration tests use these markers:

- `@pytest.mark.integration` - Marks test as integration (real API calls)
- `@pytest.mark.slow` - Marks test as slow (may take >10 seconds)
- `@pytest.mark.skipif` - Auto-skip if ALPACA_API_KEY not set

Configure in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests (make real API calls, can be slow)",
    "slow: marks tests as slow (may take >10 seconds)",
    "smoke: marks tests as smoke tests (quick validation of critical paths)",
]
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev,backtest]"
      - run: pip install alpaca-py yfinance pyarrow
      - run: pytest tests/backtest/test_integration_data.py -v -m integration --no-cov
        env:
          ALPACA_API_KEY: ${{ secrets.ALPACA_API_KEY }}
          ALPACA_SECRET_KEY: ${{ secrets.ALPACA_SECRET_KEY }}
```

### Skip Integration Tests in CI

To run only unit tests (skip integration):

```bash
pytest tests/backtest/ -v -m "not integration" --no-cov
```

## Troubleshooting

### Tests Skipped

**Issue**: All tests show `SKIPPED`
**Solution**: Set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` environment variables

```bash
export ALPACA_API_KEY="your_key_here"
export ALPACA_SECRET_KEY="your_secret_here"
pytest tests/backtest/test_integration_data.py -v -m integration --no-cov
```

### API Rate Limits

**Issue**: Tests fail with rate limit errors
**Solution**: Alpaca free tier allows 200 requests/minute. Space out test runs or upgrade to paid tier.

### Slow Tests

**Issue**: Tests take too long (>60s for 5 stocks)
**Solution**:
1. Check internet connection
2. Use cache (second run should be fast)
3. Reduce date range (test last 30 days instead of full year)

### Data Quality Errors

**Issue**: Tests fail with DataQualityError
**Solution**: This indicates real issues with market data:
- Check if market was closed on test dates
- Verify symbol is valid and has trading history
- Check for corporate actions (splits, dividends) that may cause gaps

## API Documentation

### Alpaca API
- Free tier: 200 requests/minute
- Historical data: Daily bars, split/dividend adjusted
- Docs: https://alpaca.markets/docs/api-references/market-data-api/

### Yahoo Finance (yfinance)
- Free, no API key required
- Historical data: Daily bars, auto-adjusted
- Fallback when Alpaca fails
- Docs: https://pypi.org/project/yfinance/

## Related Documentation

- `src/trading_bot/backtest/historical_data_manager.py` - Data manager implementation
- `specs/001-backtesting-engine/spec.md` - Feature specification
- `specs/001-backtesting-engine/tasks.md` - Task T018 details
