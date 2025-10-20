"""
Tests for HistoricalDataManager.

Tests data fetching from Alpaca API, Yahoo Finance fallback, data validation,
and parquet caching functionality.
"""

import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch, MagicMock

import pytest
import pandas as pd

from trading_bot.backtest.models import HistoricalDataBar
from trading_bot.backtest.exceptions import InsufficientDataError


class TestCachePersistence:
    """Test parquet caching persists and loads data."""

    def test_cache_persistence(self, tmp_path: Path):
        """
        Test that Parquet caching persists data and loads from cache on second call.

        TDD RED PHASE: This test is expected to FAIL because HistoricalDataManager
        and its caching logic don't exist yet.

        Test Requirements:
        1. First call to fetch_data() makes API call and saves to cache
        2. Second call to fetch_data() loads from cache (no API call)
        3. Cache file exists at .backtest_cache/{symbol}_{start}_{end}.parquet
        4. Second call is much faster (no API delay)
        5. Data integrity: same data from cache and API

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        # ARRANGE: Setup test parameters and mock data
        symbol = "AAPL"
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)

        # Create mock historical data (252 trading days in 2023)
        mock_bars = self._create_mock_historical_bars(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            num_bars=252
        )

        # Configure cache directory in temporary path
        cache_dir = tmp_path / ".backtest_cache"

        # Expected cache file path
        cache_file = cache_dir / f"{symbol}_{start_date.date()}_{end_date.date()}.parquet"

        # Mock API call with realistic delay (simulates network latency)
        def mock_api_call(*args, **kwargs) -> List[HistoricalDataBar]:
            """Simulate API call with 2-second delay."""
            time.sleep(2.0)  # Simulate network latency
            return mock_bars

        # ACT & ASSERT: Try to import HistoricalDataManager
        # RED PHASE: This will fail because the module doesn't exist yet
        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            # If import succeeds, we're in GREEN/REFACTOR phase - run the full test
            # Create manager instance with custom cache directory
            manager = HistoricalDataManager(cache_dir=str(cache_dir))

            # FIRST CALL: Should make API call and cache the data
            with patch.object(manager, '_fetch_alpaca_data', side_effect=mock_api_call) as mock_fetch:
                start_time = time.time()
                first_call_data = manager.fetch_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                first_call_duration = time.time() - start_time

                # Verify API was called exactly once
                assert mock_fetch.call_count == 1, "First call should make API request"

                # Verify cache file was created
                assert cache_file.exists(), f"Cache file should exist at {cache_file}"

                # Verify data was returned correctly
                assert len(first_call_data) == 252, "Should return 252 trading days"
                assert first_call_data[0].symbol == symbol
                assert first_call_data[0].timestamp >= start_date
                assert first_call_data[-1].timestamp <= end_date

                # Verify first call took significant time (API delay)
                assert first_call_duration >= 2.0, "First call should include API delay"

            # SECOND CALL: Should load from cache (no API call)
            with patch.object(manager, '_fetch_alpaca_data', side_effect=mock_api_call) as mock_fetch:
                start_time = time.time()
                second_call_data = manager.fetch_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                second_call_duration = time.time() - start_time

                # Verify API was NOT called (cache hit)
                assert mock_fetch.call_count == 0, "Second call should load from cache (no API call)"

                # Verify second call was much faster (no network delay)
                assert second_call_duration < 0.5, "Cache load should be fast (<500ms)"
                assert second_call_duration < first_call_duration / 4, "Cache should be 4x+ faster than API"

                # Verify data integrity: cache data matches original
                assert len(second_call_data) == len(first_call_data), "Cache should return same number of bars"

                for i, (cached_bar, original_bar) in enumerate(zip(second_call_data, first_call_data)):
                    assert cached_bar.symbol == original_bar.symbol, f"Bar {i}: Symbol mismatch"
                    assert cached_bar.timestamp == original_bar.timestamp, f"Bar {i}: Timestamp mismatch"
                    assert cached_bar.open == original_bar.open, f"Bar {i}: Open price mismatch"
                    assert cached_bar.high == original_bar.high, f"Bar {i}: High price mismatch"
                    assert cached_bar.low == original_bar.low, f"Bar {i}: Low price mismatch"
                    assert cached_bar.close == original_bar.close, f"Bar {i}: Close price mismatch"
                    assert cached_bar.volume == original_bar.volume, f"Bar {i}: Volume mismatch"

        except (ImportError, ModuleNotFoundError) as e:
            # RED PHASE: Expected failure - implementation doesn't exist yet
            pytest.fail(
                f"TDD RED PHASE: HistoricalDataManager not implemented yet.\n"
                f"Import error: {e}\n\n"
                f"Expected behavior (for GREEN phase implementation):\n"
                f"1. HistoricalDataManager class in src/trading_bot/backtest/historical_data_manager.py\n"
                f"2. fetch_data() method that caches to parquet files\n"
                f"3. Cache path: {{cache_dir}}/{{symbol}}_{{start}}_{{end}}.parquet\n"
                f"4. Second call should load from cache without API call\n"
                f"5. Cache should be 4x+ faster than API call"
            )

    def test_cache_disabled_always_calls_api(self, tmp_path: Path):
        """
        Test that disabling cache forces API calls every time.

        TDD RED PHASE: Expected to FAIL (HistoricalDataManager doesn't exist).

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        symbol = "TSLA"
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)

        cache_dir = tmp_path / ".backtest_cache"

        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            # Expected behavior for GREEN phase:
            manager = HistoricalDataManager(cache_dir=str(cache_dir), cache_enabled=False)

            mock_data = self._create_mock_historical_bars(symbol, start_date, end_date, 252)

            with patch.object(manager, '_fetch_alpaca_data', return_value=mock_data) as mock_fetch:
                # First call
                manager.fetch_data(symbol, start_date, end_date)
                assert mock_fetch.call_count == 1

                # Second call should also hit API (cache disabled)
                manager.fetch_data(symbol, start_date, end_date)
                assert mock_fetch.call_count == 2, "Should make API call both times when cache disabled"

        except (ImportError, ModuleNotFoundError) as e:
            pytest.fail(f"TDD RED PHASE: HistoricalDataManager not implemented yet. Error: {e}")

    def test_cache_invalidation_on_different_date_range(self, tmp_path: Path):
        """
        Test that different date ranges create separate cache entries.

        TDD RED PHASE: Expected to FAIL (HistoricalDataManager doesn't exist).

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        symbol = "AAPL"
        start_date_1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date_1 = datetime(2023, 6, 30, tzinfo=timezone.utc)
        start_date_2 = datetime(2023, 7, 1, tzinfo=timezone.utc)
        end_date_2 = datetime(2023, 12, 31, tzinfo=timezone.utc)

        cache_dir = tmp_path / ".backtest_cache"

        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            manager = HistoricalDataManager(cache_dir=str(cache_dir))

            mock_data_1 = self._create_mock_historical_bars(symbol, start_date_1, end_date_1, 126)
            mock_data_2 = self._create_mock_historical_bars(symbol, start_date_2, end_date_2, 126)

            with patch.object(manager, '_fetch_alpaca_data') as mock_fetch:
                # First date range
                mock_fetch.return_value = mock_data_1
                manager.fetch_data(symbol, start_date_1, end_date_1)

                # Second date range (different) - should make new API call
                mock_fetch.return_value = mock_data_2
                manager.fetch_data(symbol, start_date_2, end_date_2)

                # Both calls should hit API (different cache keys)
                assert mock_fetch.call_count == 2, "Different date ranges should create separate cache entries"

                # Verify two cache files exist
                cache_file_1 = cache_dir / f"{symbol}_{start_date_1.date()}_{end_date_1.date()}.parquet"
                cache_file_2 = cache_dir / f"{symbol}_{start_date_2.date()}_{end_date_2.date()}.parquet"
                assert cache_file_1.exists(), "First cache file should exist"
                assert cache_file_2.exists(), "Second cache file should exist"

        except (ImportError, ModuleNotFoundError) as e:
            pytest.fail(f"TDD RED PHASE: HistoricalDataManager not implemented yet. Error: {e}")

    def _create_mock_historical_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        num_bars: int
    ) -> List[HistoricalDataBar]:
        """
        Create mock historical data bars for testing.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date for data
            end_date: End date for data
            num_bars: Number of bars to generate

        Returns:
            List of HistoricalDataBar objects with realistic data
        """
        bars = []
        base_price = Decimal("150.00")

        for i in range(num_bars):
            # Simulate price movement
            price_change = Decimal(str((i % 10 - 5) * 0.5))  # +/- $2.50 variation
            close_price = base_price + price_change

            # Create realistic OHLC with proper relationships
            bar = HistoricalDataBar(
                symbol=symbol,
                timestamp=start_date.replace(hour=9, minute=30) + pd.Timedelta(days=i),
                open=close_price - Decimal("0.50"),
                high=close_price + Decimal("1.00"),
                low=close_price - Decimal("1.50"),
                close=close_price,
                volume=1000000 + (i * 10000),  # Varying volume
                split_adjusted=True,
                dividend_adjusted=True
            )
            bars.append(bar)

        return bars


class TestAlpacaFetch:
    """T010 [RED]: Test fetching data from Alpaca API."""

    @patch('alpaca.data.historical.StockHistoricalDataClient')
    def test_fetch_alpaca_data_full_year(self, mock_alpaca_client_class):
        """
        T010 [RED]: Test HistoricalDataManager.fetch_data() calls Alpaca API and returns HistoricalDataBar list.

        GIVEN: HistoricalDataManager initialized with Alpaca credentials
        WHEN: fetch_data called with symbol="AAPL", date range 2023-01-01 to 2023-12-31
        THEN: Returns List[HistoricalDataBar] with 252 trading days of OHLCV data
        AND: Each bar has symbol, timestamp, open, high, low, close, volume
        AND: Prices are Decimal type for precision
        AND: Timestamps are UTC timezone-aware

        TDD RED PHASE: This test is expected to FAIL because HistoricalDataManager._fetch_alpaca_data()
        doesn't exist yet.
        """
        # Mock Alpaca API response (simulate 5 bars for testing)
        mock_bars = []
        base_date = datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc)  # First trading day of 2023
        for i in range(5):
            mock_bar = Mock()
            mock_bar.timestamp = base_date.replace(day=base_date.day + i)
            mock_bar.open = 150.0 + i
            mock_bar.high = 152.0 + i
            mock_bar.low = 149.0 + i
            mock_bar.close = 151.0 + i
            mock_bar.volume = 1000000 + (i * 100000)
            mock_bars.append(mock_bar)

        # Setup mock Alpaca client
        mock_client_instance = MagicMock()
        # Alpaca API returns dict with symbol as key
        mock_client_instance.get_stock_bars.return_value = {'AAPL': mock_bars}
        mock_alpaca_client_class.return_value = mock_client_instance

        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            # Given: HistoricalDataManager initialized (cache disabled to force API call)
            manager = HistoricalDataManager(api_key="test_key", api_secret="test_secret", cache_enabled=False)

            # When: fetch_data called for full year
            start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            result = manager.fetch_data(symbol="AAPL", start_date=start_date, end_date=end_date)

            # Then: Returns list of HistoricalDataBar
            assert isinstance(result, list)
            assert len(result) == 5  # Mock returns 5 bars
            assert all(isinstance(bar, HistoricalDataBar) for bar in result)

            # And: Each bar has correct structure
            first_bar = result[0]
            assert first_bar.symbol == "AAPL"
            assert isinstance(first_bar.timestamp, datetime)
            assert first_bar.timestamp.tzinfo == timezone.utc
            assert isinstance(first_bar.open, Decimal)
            assert isinstance(first_bar.high, Decimal)
            assert isinstance(first_bar.low, Decimal)
            assert isinstance(first_bar.close, Decimal)
            assert isinstance(first_bar.volume, int)

            # And: Prices are in correct OHLC relationship
            assert first_bar.high >= first_bar.open
            assert first_bar.high >= first_bar.close
            assert first_bar.low <= first_bar.open
            assert first_bar.low <= first_bar.close

            # And: Alpaca API called with correct parameters
            mock_client_instance.get_stock_bars.assert_called_once()
            call_args = mock_client_instance.get_stock_bars.call_args
            assert 'symbol' in call_args.kwargs or len(call_args.args) > 0
            # Symbol should be passed either as arg or kwarg

        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            # RED PHASE: Expected failure - implementation doesn't exist yet
            pytest.fail(
                f"TDD RED PHASE: HistoricalDataManager._fetch_alpaca_data() not implemented yet.\n"
                f"Error: {e}\n\n"
                f"Expected behavior (for GREEN phase implementation):\n"
                f"1. HistoricalDataManager class with _fetch_alpaca_data() method\n"
                f"2. Method should call Alpaca StockHistoricalDataClient.get_stock_bars()\n"
                f"3. Return List[HistoricalDataBar] with proper OHLCV data\n"
                f"4. All prices must be Decimal type (not float)\n"
                f"5. All timestamps must be UTC timezone-aware\n"
                f"6. Validate OHLC relationships (high >= open/close, low <= open/close)"
            )

    @patch('alpaca.data.historical.StockHistoricalDataClient')
    def test_fetch_alpaca_data_validates_date_range(self, mock_alpaca_client_class):
        """
        T010 [RED]: Test fetch_data validates date range (start < end, UTC timezone).

        GIVEN: HistoricalDataManager initialized
        WHEN: fetch_data called with invalid date range (start >= end)
        THEN: Raises ValueError before calling Alpaca API

        TDD RED PHASE: Expected to FAIL (HistoricalDataManager doesn't exist).
        """
        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            # Given: HistoricalDataManager initialized (cache disabled to force API call)
            manager = HistoricalDataManager(api_key="test_key", api_secret="test_secret", cache_enabled=False)

            # When/Then: Invalid date range raises ValueError
            start_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
            end_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            with pytest.raises(ValueError, match="start_date.*must be.*end_date"):
                manager.fetch_data(symbol="AAPL", start_date=start_date, end_date=end_date)

        except (ImportError, ModuleNotFoundError) as e:
            pytest.fail(f"TDD RED PHASE: HistoricalDataManager not implemented yet. Error: {e}")

    @patch('alpaca.data.historical.StockHistoricalDataClient')
    def test_fetch_alpaca_data_requires_utc_timezone(self, mock_alpaca_client_class):
        """
        T010 [RED]: Test fetch_data requires UTC timezone-aware datetimes.

        GIVEN: HistoricalDataManager initialized
        WHEN: fetch_data called with timezone-naive datetime
        THEN: Raises ValueError with helpful message

        TDD RED PHASE: Expected to FAIL (HistoricalDataManager doesn't exist).
        """
        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            # Given: HistoricalDataManager initialized (cache disabled to force API call)
            manager = HistoricalDataManager(api_key="test_key", api_secret="test_secret", cache_enabled=False)

            # When/Then: Timezone-naive datetime raises ValueError
            start_date = datetime(2023, 1, 1)  # No timezone
            end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
            with pytest.raises(ValueError, match="timezone-naive|UTC"):
                manager.fetch_data(symbol="AAPL", start_date=start_date, end_date=end_date)

        except (ImportError, ModuleNotFoundError) as e:
            pytest.fail(f"TDD RED PHASE: HistoricalDataManager not implemented yet. Error: {e}")

    @patch('alpaca.data.historical.StockHistoricalDataClient')
    def test_fetch_alpaca_data_handles_api_errors(self, mock_alpaca_client_class):
        """
        T010 [RED]: Test fetch_data handles Alpaca API errors gracefully.

        GIVEN: HistoricalDataManager initialized
        WHEN: fetch_data called and Alpaca API raises exception
        THEN: Raises InsufficientDataError with original error context

        TDD RED PHASE: Expected to FAIL (HistoricalDataManager doesn't exist).
        """
        from trading_bot.backtest.exceptions import InsufficientDataError

        # Setup mock to raise API error
        mock_client_instance = MagicMock()
        mock_client_instance.get_stock_bars.side_effect = Exception("Alpaca API rate limit exceeded")
        mock_alpaca_client_class.return_value = mock_client_instance

        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            # Given: HistoricalDataManager initialized (cache disabled to force API call)
            manager = HistoricalDataManager(api_key="test_key", api_secret="test_secret", cache_enabled=False)

            # When/Then: API error raises InsufficientDataError
            start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
            with pytest.raises((InsufficientDataError, Exception), match="Alpaca|rate limit"):
                manager.fetch_data(symbol="AAPL", start_date=start_date, end_date=end_date)

        except (ImportError, ModuleNotFoundError) as e:
            pytest.fail(f"TDD RED PHASE: HistoricalDataManager not implemented yet. Error: {e}")

    @patch('alpaca.data.historical.StockHistoricalDataClient')
    def test_fetch_alpaca_data_validates_symbol(self, mock_alpaca_client_class):
        """
        T010 [RED]: Test fetch_data validates symbol format.

        GIVEN: HistoricalDataManager initialized
        WHEN: fetch_data called with empty or invalid symbol
        THEN: Raises ValueError before calling API

        TDD RED PHASE: Expected to FAIL (HistoricalDataManager doesn't exist).
        """
        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            # Given: HistoricalDataManager initialized (cache disabled to force API call)
            manager = HistoricalDataManager(api_key="test_key", api_secret="test_secret", cache_enabled=False)

            # When/Then: Empty symbol raises ValueError
            start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
            with pytest.raises(ValueError, match="Symbol.*required|invalid"):
                manager.fetch_data(symbol="", start_date=start_date, end_date=end_date)

        except (ImportError, ModuleNotFoundError) as e:
            pytest.fail(f"TDD RED PHASE: HistoricalDataManager not implemented yet. Error: {e}")

    @patch('alpaca.data.historical.StockHistoricalDataClient')
    def test_fetch_alpaca_data_empty_response(self, mock_alpaca_client_class):
        """
        T010 [RED]: Test fetch_data handles empty API response (no data available).

        GIVEN: HistoricalDataManager initialized
        WHEN: fetch_data called and Alpaca returns no bars
        THEN: Raises InsufficientDataError with helpful message

        TDD RED PHASE: Expected to FAIL (HistoricalDataManager doesn't exist).
        """
        from trading_bot.backtest.exceptions import InsufficientDataError

        # Setup mock to return empty dict (no data for symbol)
        mock_client_instance = MagicMock()
        mock_client_instance.get_stock_bars.return_value = {}  # No symbol key = no data
        mock_alpaca_client_class.return_value = mock_client_instance

        try:
            from trading_bot.backtest.historical_data_manager import HistoricalDataManager

            # Given: HistoricalDataManager initialized (cache disabled to force API call)
            manager = HistoricalDataManager(api_key="test_key", api_secret="test_secret", cache_enabled=False)

            # When/Then: Empty response raises InsufficientDataError
            start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
            with pytest.raises((InsufficientDataError, ValueError), match="No data|empty"):
                manager.fetch_data(symbol="AAPL", start_date=start_date, end_date=end_date)

        except (ImportError, ModuleNotFoundError) as e:
            pytest.fail(f"TDD RED PHASE: HistoricalDataManager not implemented yet. Error: {e}")



class TestYahooFinanceFallback:
    """Test Yahoo Finance fallback when Alpaca API fails."""

    def test_fetch_yahoo_fallback(self):
        """
        Test automatic fallback to Yahoo Finance when Alpaca API fails.

        TDD RED PHASE: This test is expected to FAIL because:
        1. HistoricalDataManager module does not exist yet
        2. Fallback logic is not implemented

        Scenario:
        - Given: Alpaca API raises an exception (network error, API down, rate limit)
        - When: HistoricalDataManager.fetch_data() is called
        - Then: Automatically falls back to Yahoo Finance without manual intervention
        - And: Returns List[HistoricalDataBar] with Yahoo Finance data
        - And: No exception is raised to the caller (fallback is transparent)
        """
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager

        # ARRANGE: Configure test parameters
        symbol = "AAPL"
        start_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 4, tzinfo=timezone.utc)

        # Create manager instance
        manager = HistoricalDataManager(cache_enabled=False)

        # Create mock Yahoo data to return
        mock_yahoo_bars = [
            HistoricalDataBar(
                symbol=symbol,
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
                open=Decimal("185.50"),
                high=Decimal("187.25"),
                low=Decimal("184.75"),
                close=Decimal("186.80"),
                volume=52000000,
                split_adjusted=True,
                dividend_adjusted=True
            ),
            HistoricalDataBar(
                symbol=symbol,
                timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc),
                open=Decimal("186.90"),
                high=Decimal("188.10"),
                low=Decimal("186.00"),
                close=Decimal("187.50"),
                volume=48000000,
                split_adjusted=True,
                dividend_adjusted=True
            ),
            HistoricalDataBar(
                symbol=symbol,
                timestamp=datetime(2024, 1, 4, tzinfo=timezone.utc),
                open=Decimal("187.60"),
                high=Decimal("189.30"),
                low=Decimal("187.20"),
                close=Decimal("188.90"),
                volume=51000000,
                split_adjusted=True,
                dividend_adjusted=True
            ),
        ]

        # ACT: Mock Alpaca to fail, Yahoo to succeed
        with patch.object(manager, '_fetch_alpaca_data', side_effect=Exception("Alpaca API unavailable")):
            with patch.object(manager, '_fetch_yahoo_data', return_value=mock_yahoo_bars) as mock_yahoo:
                result = manager.fetch_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )

                # ASSERT: Verify fallback behavior
                # 1. Yahoo Finance was called as fallback
                mock_yahoo.assert_called_once_with(symbol, start_date, end_date)

                # 2. Returns List[HistoricalDataBar] with Yahoo data
                assert isinstance(result, list)
                assert len(result) == 3
                assert all(isinstance(bar, HistoricalDataBar) for bar in result)

                # 3. Verify first bar data matches Yahoo Finance response
                first_bar = result[0]
                assert first_bar.symbol == symbol
                assert first_bar.timestamp == datetime(2024, 1, 2, tzinfo=timezone.utc)
                assert first_bar.open == Decimal("185.50")
                assert first_bar.high == Decimal("187.25")
                assert first_bar.low == Decimal("184.75")
                assert first_bar.close == Decimal("186.80")
                assert first_bar.volume == 52000000

    def test_fetch_yahoo_fallback_both_fail(self):
        """
        Test that InsufficientDataError is raised when both Alpaca and Yahoo fail.

        TDD RED PHASE: This test will also fail initially.

        Scenario:
        - Given: Both Alpaca API and Yahoo Finance raise exceptions
        - When: HistoricalDataManager.fetch_data() is called
        - Then: Raises InsufficientDataError with descriptive message
        """
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager

        # ARRANGE
        symbol = "AAPL"
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 5, tzinfo=timezone.utc)

        # Create manager instance
        manager = HistoricalDataManager(cache_enabled=False)

        # ACT & ASSERT: Mock both sources to fail
        exception_caught = None
        with patch.object(manager, '_fetch_alpaca_data', side_effect=Exception("Alpaca API error")):
            with patch.object(manager, '_fetch_yahoo_data', side_effect=Exception("Yahoo Finance error")):
                # Expect InsufficientDataError with both error messages
                try:
                    manager.fetch_data(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    pytest.fail("Should have raised InsufficientDataError")
                except InsufficientDataError as e:
                    exception_caught = e

        # Verify exception was raised
        assert exception_caught is not None, "InsufficientDataError should have been raised"

        # Verify error message mentions both sources failed
        error_msg = str(exception_caught)
        assert "both" in error_msg.lower() or ("Alpaca" in error_msg and "Yahoo" in error_msg), \
            f"Error message should mention both sources: {error_msg}"
        assert "Alpaca API error" in error_msg, f"Error message should mention Alpaca error: {error_msg}"
        assert "Yahoo Finance error" in error_msg, f"Error message should mention Yahoo error: {error_msg}"







# T012: Data validation tests
class TestDataValidation:
    """
    Test suite for data quality validation in HistoricalDataManager.

    Tests verify that validate_data() correctly detects and handles:
    - Missing dates (gaps in trading days)
    - Negative prices
    - Zero volume
    - Invalid OHLC relationships (high < low)
    - Non-chronological data

    Following pattern from tests/unit/test_market_data/test_validators.py
    """

    def test_validation_detects_missing_dates(self):
        """
        Test that validate_data() raises DataQualityError for gaps in trading days.

        GIVEN: Historical data with significant gap (5+ trading days missing)
        WHEN: validate_data() is called
        THEN: Raises DataQualityError with "gap" in message

        This is RED phase - method doesn't exist yet, test will fail.
        """
        # Import will fail because HistoricalDataManager doesn't exist yet
        # This is intentional for TDD RED phase
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager
        from trading_bot.backtest.exceptions import DataQualityError

        # Given: Data with 10-day gap (2025-01-02 to 2025-01-15)
        data_with_gaps = [
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
                open=Decimal("150.0"),
                high=Decimal("155.0"),
                low=Decimal("149.0"),
                close=Decimal("154.0"),
                volume=1000000,
            ),
            # Missing ~10 trading days here (gap)
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 15, tzinfo=timezone.utc),
                open=Decimal("151.0"),
                high=Decimal("156.0"),
                low=Decimal("150.0"),
                close=Decimal("155.0"),
                volume=1100000,
            ),
        ]

        manager = HistoricalDataManager()

        # When/Then: validate_data() raises DataQualityError
        with pytest.raises(DataQualityError, match="gap"):
            manager.validate_data(data_with_gaps, symbol="AAPL")

    def test_validation_detects_negative_prices(self):
        """
        Test that validate_data() raises DataQualityError for negative prices.

        GIVEN: Historical data with negative price in any OHLC field
        WHEN: validate_data() is called
        THEN: Raises DataQualityError with "negative price" in message

        This is RED phase - method doesn't exist yet, test will fail.
        """
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager
        from trading_bot.backtest.exceptions import DataQualityError

        # Given: Raw data with negative price (simulating bad API data)
        raw_data = [
            {
                'symbol': 'AAPL',
                'timestamp': datetime(2025, 1, 2, tzinfo=timezone.utc),
                'open': 150.0,
                'high': 155.0,
                'low': 149.0,
                'close': 154.0,
                'volume': 1000000,
            },
            {
                'symbol': 'AAPL',
                'timestamp': datetime(2025, 1, 3, tzinfo=timezone.utc),
                'open': 155.0,
                'high': 160.0,
                'low': 154.0,
                'close': -5.0,  # Negative price (data error)
                'volume': 1100000,
            },
        ]

        manager = HistoricalDataManager()

        # When/Then: validate_data() raises DataQualityError
        with pytest.raises(DataQualityError, match="negative|invalid price"):
            manager.validate_data(raw_data, symbol="AAPL")

    def test_validation_warns_on_zero_volume(self, caplog):
        """
        Test that validate_data() logs warning for zero volume but doesn't fail.

        GIVEN: Historical data with zero volume on some bars
        WHEN: validate_data() is called
        THEN: Logs warning message but does NOT raise exception

        Zero volume is suspicious but not necessarily invalid (halted stocks, holidays).
        This is RED phase - method doesn't exist yet, test will fail.
        """
        import logging
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager

        # Given: Data with zero volume on second bar
        data_with_zero_volume = [
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
                open=Decimal("150.0"),
                high=Decimal("155.0"),
                low=Decimal("149.0"),
                close=Decimal("154.0"),
                volume=1000000,
            ),
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 3, tzinfo=timezone.utc),
                open=Decimal("154.0"),
                high=Decimal("156.0"),
                low=Decimal("153.0"),
                close=Decimal("155.0"),
                volume=0,  # Zero volume - warning but not error
            ),
        ]

        manager = HistoricalDataManager()

        # When: validate_data() is called
        with caplog.at_level(logging.WARNING):
            # Should not raise, just warn
            manager.validate_data(data_with_zero_volume, symbol="AAPL")

        # Then: Warning was logged
        assert any("zero volume" in record.message.lower() for record in caplog.records)

    def test_validation_detects_high_less_than_low(self):
        """
        Test that validate_data() raises DataQualityError when high < low.

        GIVEN: Historical data where high price < low price (impossible)
        WHEN: validate_data() is called
        THEN: Raises DataQualityError with "high" and "low" in message

        This is RED phase - method doesn't exist yet, test will fail.
        """
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager
        from trading_bot.backtest.exceptions import DataQualityError

        # Given: Raw data with high < low (bypassing HistoricalDataBar validation)
        raw_data = [
            {
                'symbol': 'AAPL',
                'timestamp': datetime(2025, 1, 2, tzinfo=timezone.utc),
                'open': 150.0,
                'high': 155.0,
                'low': 149.0,
                'close': 154.0,
                'volume': 1000000,
            },
            {
                'symbol': 'AAPL',
                'timestamp': datetime(2025, 1, 3, tzinfo=timezone.utc),
                'open': 155.0,
                'high': 154.0,  # High < low (impossible)
                'low': 160.0,
                'close': 156.0,
                'volume': 1100000,
            },
        ]

        manager = HistoricalDataManager()

        # When/Then: validate_data() raises DataQualityError
        with pytest.raises(DataQualityError, match="high.*low|invalid.*OHLC"):
            manager.validate_data(raw_data, symbol="AAPL")

    def test_validation_detects_non_chronological_data(self):
        """
        Test that validate_data() raises DataQualityError for out-of-order timestamps.

        GIVEN: Historical data with timestamps not in chronological order
        WHEN: validate_data() is called
        THEN: Raises DataQualityError with "chronological" or "order" in message

        This is RED phase - method doesn't exist yet, test will fail.
        """
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager
        from trading_bot.backtest.exceptions import DataQualityError

        # Given: Data with timestamps out of order (2025-01-05 before 2025-01-03)
        non_chronological_data = [
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
                open=Decimal("150.0"),
                high=Decimal("155.0"),
                low=Decimal("149.0"),
                close=Decimal("154.0"),
                volume=1000000,
            ),
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 5, tzinfo=timezone.utc),  # Out of order (should be after 1/3)
                open=Decimal("156.0"),
                high=Decimal("158.0"),
                low=Decimal("155.0"),
                close=Decimal("157.0"),
                volume=1200000,
            ),
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 3, tzinfo=timezone.utc),  # Goes back in time
                open=Decimal("154.0"),
                high=Decimal("156.0"),
                low=Decimal("153.0"),
                close=Decimal("155.0"),
                volume=1100000,
            ),
        ]

        manager = HistoricalDataManager()

        # When/Then: validate_data() raises DataQualityError
        with pytest.raises(DataQualityError, match="chronological|order"):
            manager.validate_data(non_chronological_data, symbol="AAPL")

    def test_validation_passes_clean_data(self):
        """
        Test that validate_data() succeeds with clean, valid data.

        GIVEN: Historical data with no quality issues (consecutive days, valid prices)
        WHEN: validate_data() is called
        THEN: Returns None (no exception raised)

        This is RED phase - method doesn't exist yet, test will fail.
        """
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager

        # Given: Clean data - consecutive trading days (Mon-Fri)
        clean_data = [
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),  # Thursday
                open=Decimal("150.0"),
                high=Decimal("155.0"),
                low=Decimal("149.0"),
                close=Decimal("154.0"),
                volume=1000000,
            ),
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 3, tzinfo=timezone.utc),  # Friday
                open=Decimal("154.0"),
                high=Decimal("156.0"),
                low=Decimal("153.0"),
                close=Decimal("155.0"),
                volume=1100000,
            ),
            # Weekend skipped (normal)
            HistoricalDataBar(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 6, tzinfo=timezone.utc),  # Monday
                open=Decimal("155.0"),
                high=Decimal("157.0"),
                low=Decimal("154.0"),
                close=Decimal("156.0"),
                volume=1200000,
            ),
        ]

        manager = HistoricalDataManager()

        # When: validate_data() is called
        result = manager.validate_data(clean_data, symbol="AAPL")

        # Then: Returns None (no exception)
        assert result is None

    def test_validation_detects_multiple_issues(self):
        """
        Test that validate_data() reports first critical issue found.

        GIVEN: Historical data with multiple quality issues (gaps + negative price)
        WHEN: validate_data() is called
        THEN: Raises DataQualityError (doesn't need to report all issues, just fail fast)

        This is RED phase - method doesn't exist yet, test will fail.
        """
        from trading_bot.backtest.historical_data_manager import HistoricalDataManager
        from trading_bot.backtest.exceptions import DataQualityError

        # Given: Data with both gap and negative price
        raw_data_with_multiple_issues = [
            {
                'symbol': 'AAPL',
                'timestamp': datetime(2025, 1, 2, tzinfo=timezone.utc),
                'open': 150.0,
                'high': 155.0,
                'low': 149.0,
                'close': 154.0,
                'volume': 1000000,
            },
            # Missing ~10 trading days (gap)
            {
                'symbol': 'AAPL',
                'timestamp': datetime(2025, 1, 15, tzinfo=timezone.utc),
                'open': 155.0,
                'high': 160.0,
                'low': 154.0,
                'close': -5.0,  # Also negative price
                'volume': 1100000,
            },
        ]

        manager = HistoricalDataManager()

        # When/Then: Raises DataQualityError (for either issue)
        with pytest.raises(DataQualityError):
            manager.validate_data(raw_data_with_multiple_issues, symbol="AAPL")
