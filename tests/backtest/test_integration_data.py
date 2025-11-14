"""
Integration tests for end-to-end data loading in backtesting engine.

Tests REAL API calls to Alpaca/Yahoo Finance for historical data fetching,
data quality validation, and performance benchmarks.

T018 [US1]: Write integration test: End-to-end data loading
- Feature: backtesting-engine
- Performance target: <60 seconds for 10 stocks (NFR-002)
- Uses real API credentials from environment variables
- Can be slow (makes network calls), marked with @pytest.mark.integration

Constitution v1.0.0:
- §Data_Integrity: Validate all data before use
- §Audit_Everything: Log all API operations
- §Safety_First: Fail-fast on validation errors
"""

import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from trading_bot.backtest.historical_data_manager import HistoricalDataManager
from trading_bot.backtest.exceptions import InsufficientDataError, DataQualityError


# Skip all tests in this file if ALPACA_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.getenv('ALPACA_API_KEY'),
    reason="ALPACA_API_KEY environment variable not set - integration tests require API credentials"
)


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndDataLoading:
    """Integration tests for real API data loading."""

    def test_load_one_year_data(self, tmp_path):
        """
        T018: Test loading one year of data for AAPL (2023) with real API call.

        GIVEN: HistoricalDataManager with real Alpaca API credentials
        WHEN: fetch_data called for AAPL (2023-01-01 to 2023-12-31)
        THEN:
        - Returns ~252 bars (252 trading days in 2023)
        - All fields populated correctly (symbol, timestamp, OHLCV)
        - No gaps in trading days (weekends/holidays excluded)
        - Data quality validated (positive prices, high >= low, etc.)
        - Data cached for subsequent calls

        Performance: First call may be slow (API + cache write)
        Subsequent calls fast (cache hit)

        Args:
            tmp_path: pytest fixture for temporary cache directory
        """
        # ARRANGE: Setup manager with real credentials and temp cache
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY')

        manager = HistoricalDataManager(
            api_key=api_key,
            api_secret=api_secret,
            cache_dir=str(tmp_path / ".backtest_cache"),
            cache_enabled=True
        )

        # Define date range for 2023 (full year)
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        symbol = "AAPL"

        # ACT: Make REAL API call to fetch AAPL data for 2023
        bars = manager.fetch_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        # ASSERT: Verify we got approximately 252 trading days
        # Allow some tolerance (250-254 bars) for market holidays/partial days
        assert 250 <= len(bars) <= 254, (
            f"Expected ~252 trading days in 2023, got {len(bars)}. "
            f"Tolerance: 250-254 bars."
        )

        # ASSERT: Verify all fields are populated for each bar
        for i, bar in enumerate(bars):
            # Verify symbol matches
            assert bar.symbol == symbol, f"Bar {i}: symbol mismatch"

            # Verify timestamp is within date range
            assert start_date <= bar.timestamp <= end_date, (
                f"Bar {i}: timestamp {bar.timestamp} outside range "
                f"{start_date} to {end_date}"
            )

            # Verify all OHLCV fields are positive
            assert bar.open > 0, f"Bar {i}: open price must be positive, got {bar.open}"
            assert bar.high > 0, f"Bar {i}: high price must be positive, got {bar.high}"
            assert bar.low > 0, f"Bar {i}: low price must be positive, got {bar.low}"
            assert bar.close > 0, f"Bar {i}: close price must be positive, got {bar.close}"
            assert bar.volume >= 0, f"Bar {i}: volume must be non-negative, got {bar.volume}"

            # Verify OHLC relationships (high >= low, etc.)
            assert bar.high >= bar.low, (
                f"Bar {i}: high ({bar.high}) must be >= low ({bar.low})"
            )
            assert bar.high >= bar.open, (
                f"Bar {i}: high ({bar.high}) must be >= open ({bar.open})"
            )
            assert bar.high >= bar.close, (
                f"Bar {i}: high ({bar.high}) must be >= close ({bar.close})"
            )
            assert bar.low <= bar.open, (
                f"Bar {i}: low ({bar.low}) must be <= open ({bar.open})"
            )
            assert bar.low <= bar.close, (
                f"Bar {i}: low ({bar.low}) must be <= close ({bar.close})"
            )

            # Verify prices are Decimal type (for precision)
            assert isinstance(bar.open, Decimal), f"Bar {i}: open must be Decimal"
            assert isinstance(bar.high, Decimal), f"Bar {i}: high must be Decimal"
            assert isinstance(bar.low, Decimal), f"Bar {i}: low must be Decimal"
            assert isinstance(bar.close, Decimal), f"Bar {i}: close must be Decimal"

            # Verify volume is integer
            assert isinstance(bar.volume, int), f"Bar {i}: volume must be int"

        # ASSERT: Verify no gaps in trading days (> 3 days)
        # Allow weekends (2 days) + 1 day for holidays
        for i in range(len(bars) - 1):
            gap_days = (bars[i + 1].timestamp - bars[i].timestamp).days
            assert gap_days <= 3, (
                f"Gap of {gap_days} days between bars {i} and {i+1}: "
                f"{bars[i].timestamp.date()} -> {bars[i + 1].timestamp.date()}. "
                f"Expected max 3 days (weekend + holiday)."
            )

        # ASSERT: Verify data is in chronological order
        for i in range(len(bars) - 1):
            assert bars[i].timestamp < bars[i + 1].timestamp, (
                f"Bars not in chronological order: bar {i} ({bars[i].timestamp}) "
                f">= bar {i+1} ({bars[i + 1].timestamp})"
            )

        # ASSERT: Verify cache was created
        cache_path = tmp_path / ".backtest_cache" / f"{symbol}_2023-01-01_2023-12-31.parquet"
        assert cache_path.exists(), "Cache file should exist after first fetch"

        # ASSERT: Verify subsequent call uses cache (should be fast)
        import time
        start_time = time.time()
        cached_bars = manager.fetch_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        cache_duration = time.time() - start_time

        # Cache hit should be < 1 second (no API call)
        assert cache_duration < 1.0, (
            f"Cache hit took {cache_duration:.2f}s, expected < 1.0s"
        )

        # Verify cached data matches original data
        assert len(cached_bars) == len(bars), "Cached data length mismatch"
        assert cached_bars[0].symbol == bars[0].symbol, "Cached symbol mismatch"
        assert cached_bars[0].close == bars[0].close, "Cached close price mismatch"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_load_multiple_stocks_performance(self, tmp_path):
        """
        T018: Test loading multiple stocks for performance benchmark.

        GIVEN: HistoricalDataManager with real Alpaca API credentials
        WHEN: fetch_data called for 5 stocks (AAPL, MSFT, GOOGL, TSLA, NVDA) for 2023
        THEN:
        - All 5 stocks load successfully
        - Each stock has ~252 bars
        - Total time < 30 seconds (caching helps after first call)
        - All data passes validation

        Performance target: <30 seconds for 5 stocks (extrapolates to <60s for 10 stocks)
        NFR-002: Backtest engine should load 10 stocks in <60 seconds

        Args:
            tmp_path: pytest fixture for temporary cache directory
        """
        # ARRANGE: Setup manager with real credentials
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY')

        manager = HistoricalDataManager(
            api_key=api_key,
            api_secret=api_secret,
            cache_dir=str(tmp_path / ".backtest_cache"),
            cache_enabled=True
        )

        # Define symbols and date range
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)

        # ACT: Load data for all symbols and measure time
        import time
        start_time = time.time()

        results = {}
        for symbol in symbols:
            bars = manager.fetch_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            results[symbol] = bars

        total_duration = time.time() - start_time

        # ASSERT: Verify performance target (< 30 seconds for 5 stocks)
        assert total_duration < 30.0, (
            f"Loading 5 stocks took {total_duration:.2f}s, expected < 30s. "
            f"This extrapolates to {total_duration * 2:.2f}s for 10 stocks "
            f"(target: <60s per NFR-002)"
        )

        # ASSERT: Verify all stocks loaded successfully
        assert len(results) == 5, f"Expected 5 stocks, got {len(results)}"

        # ASSERT: Verify each stock has ~252 bars (allow tolerance)
        for symbol, bars in results.items():
            assert 250 <= len(bars) <= 254, (
                f"{symbol}: Expected ~252 bars, got {len(bars)}"
            )

            # Verify first and last bars
            assert bars[0].symbol == symbol, f"{symbol}: symbol mismatch in first bar"
            assert bars[-1].symbol == symbol, f"{symbol}: symbol mismatch in last bar"

            # Verify data is in chronological order
            for i in range(len(bars) - 1):
                assert bars[i].timestamp < bars[i + 1].timestamp, (
                    f"{symbol}: bars not in chronological order at index {i}"
                )

        # ASSERT: Test cache hit performance (should be very fast)
        cache_start = time.time()
        cached_bars = manager.fetch_data(
            symbol="AAPL",
            start_date=start_date,
            end_date=end_date
        )
        cache_duration = time.time() - cache_start

        assert cache_duration < 1.0, (
            f"Cache hit for AAPL took {cache_duration:.2f}s, expected < 1.0s"
        )
        assert len(cached_bars) == len(results["AAPL"]), "Cache length mismatch"

    @pytest.mark.integration
    def test_data_quality_validation_integration(self, tmp_path):
        """
        T018: Test data quality validation with real API data.

        GIVEN: HistoricalDataManager with real Alpaca API credentials
        WHEN: fetch_data called for recent data (last 30 days)
        THEN:
        - Data passes all validation checks (no gaps, positive prices, etc.)
        - validate_data() does not raise DataQualityError
        - OHLC relationships are valid (high >= low, etc.)
        - Timestamps are in chronological order

        Args:
            tmp_path: pytest fixture for temporary cache directory
        """
        # ARRANGE: Setup manager
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY')

        manager = HistoricalDataManager(
            api_key=api_key,
            api_secret=api_secret,
            cache_dir=str(tmp_path / ".backtest_cache"),
            cache_enabled=True
        )

        # Use recent data (last 30 days) to ensure fresh data
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        # ACT: Fetch data for AAPL (highly liquid stock)
        bars = manager.fetch_data(
            symbol="AAPL",
            start_date=start_date,
            end_date=end_date
        )

        # ASSERT: Verify validation passed (fetch_data calls validate_data internally)
        # If we got here without exception, validation passed

        # Verify we got reasonable amount of data (at least 15 trading days in 30 calendar days)
        assert len(bars) >= 15, f"Expected at least 15 bars in 30 days, got {len(bars)}"

        # Verify data quality manually
        for i, bar in enumerate(bars):
            # Check OHLC relationships
            assert bar.high >= bar.low, f"Bar {i}: high < low"
            assert bar.high >= bar.open, f"Bar {i}: high < open"
            assert bar.high >= bar.close, f"Bar {i}: high < close"
            assert bar.low <= bar.open, f"Bar {i}: low > open"
            assert bar.low <= bar.close, f"Bar {i}: low > close"

            # Check positive prices
            assert bar.open > 0, f"Bar {i}: non-positive open"
            assert bar.high > 0, f"Bar {i}: non-positive high"
            assert bar.low > 0, f"Bar {i}: non-positive low"
            assert bar.close > 0, f"Bar {i}: non-positive close"

        # ACT: Run explicit validation (should not raise)
        try:
            manager.validate_data(bars, symbol="AAPL")
        except DataQualityError as e:
            pytest.fail(f"Data validation failed for real API data: {e}")

    @pytest.mark.integration
    def test_api_fallback_to_yahoo_finance(self, tmp_path):
        """
        T018: Test fallback to Yahoo Finance when Alpaca fails.

        GIVEN: HistoricalDataManager with invalid Alpaca credentials
        WHEN: fetch_data called (Alpaca fails, Yahoo Finance succeeds)
        THEN:
        - Data loads successfully from Yahoo Finance
        - Returns valid HistoricalDataBar objects
        - Data passes validation

        Note: This test uses INVALID Alpaca credentials to force fallback.
        Yahoo Finance does not require API keys.

        Args:
            tmp_path: pytest fixture for temporary cache directory
        """
        # ARRANGE: Create manager with INVALID Alpaca credentials (force fallback)
        manager = HistoricalDataManager(
            api_key="INVALID_KEY",
            api_secret="INVALID_SECRET",
            cache_dir=str(tmp_path / ".backtest_cache"),
            cache_enabled=True
        )

        # Define date range (last 30 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        # ACT: Fetch data (should fallback to Yahoo Finance)
        bars = manager.fetch_data(
            symbol="AAPL",
            start_date=start_date,
            end_date=end_date
        )

        # ASSERT: Verify we got data (Yahoo Finance succeeded)
        assert len(bars) >= 15, (
            f"Expected at least 15 bars from Yahoo Finance fallback, got {len(bars)}"
        )

        # Verify data structure
        assert bars[0].symbol == "AAPL", "Symbol mismatch"
        assert isinstance(bars[0].open, Decimal), "Open price should be Decimal"
        assert bars[0].split_adjusted is True, "Yahoo Finance data should be split-adjusted"
        assert bars[0].dividend_adjusted is True, "Yahoo Finance data should be dividend-adjusted"

        # Verify data quality
        for bar in bars:
            assert bar.high >= bar.low, "OHLC validation failed"
            assert bar.open > 0, "Price validation failed"

    @pytest.mark.integration
    def test_insufficient_data_error(self, tmp_path):
        """
        T018: Test InsufficientDataError raised for invalid symbol.

        GIVEN: HistoricalDataManager with real Alpaca credentials
        WHEN: fetch_data called with INVALID symbol (both APIs fail)
        THEN: Raises InsufficientDataError with descriptive message

        Args:
            tmp_path: pytest fixture for temporary cache directory
        """
        # ARRANGE: Setup manager
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY')

        manager = HistoricalDataManager(
            api_key=api_key,
            api_secret=api_secret,
            cache_dir=str(tmp_path / ".backtest_cache"),
            cache_enabled=True
        )

        # Define date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        # ACT/ASSERT: Fetch data with invalid symbol (should raise)
        with pytest.raises(InsufficientDataError, match="Failed to fetch data"):
            manager.fetch_data(
                symbol="INVALID_SYMBOL_XYZ123",
                start_date=start_date,
                end_date=end_date
            )
