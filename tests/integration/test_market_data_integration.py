"""
Integration tests for market data module

Tests end-to-end flows including:
- Quote retrieval with full validation pipeline
- Historical data fetching with DataFrame processing
- Rate limiting and retry handling
- Trading hours blocking

T052-T055: Complete integration test coverage

Constitution v1.0.0 - §Testing_Requirements: Integration tests for critical paths
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pandas as pd

from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.market_data.data_models import Quote, MarketStatus
from trading_bot.market_data.exceptions import DataValidationError, TradingHoursError
from trading_bot.error_handling.exceptions import RateLimitError


class TestEndToEndQuoteRetrieval:
    """T052: Test complete quote retrieval flow."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_end_to_end_quote_retrieval(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T052: End-to-end test for quote retrieval flow.

        GIVEN: MarketDataService with mock robin_stocks
        WHEN: get_quote called with "AAPL"
        THEN: Returns validated Quote with correct data types and values

        Tests complete flow:
        1. Trading hours validation
        2. API call to robin_stocks
        3. Price extraction and conversion
        4. Quote validation
        5. Dataclass construction
        """
        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["175.50"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called
        quote = service.get_quote("AAPL")

        # Then: Returns Quote with correct structure
        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.current_price == Decimal("175.50")
        assert isinstance(quote.timestamp_utc, datetime)
        assert quote.timestamp_utc.tzinfo == timezone.utc
        assert quote.market_state == "regular"

        # And: robin_stocks called with correct parameters
        mock_get_latest_price.assert_called_once_with("AAPL", includeExtendedHours=True)

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_end_to_end_quote_validation_failure(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T052: Test quote retrieval fails on invalid data.

        GIVEN: MarketDataService with mock robin_stocks
        WHEN: get_quote called and robin_stocks returns invalid price (0.0)
        THEN: Raises DataValidationError from validation layer
        """
        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns invalid price
        mock_get_latest_price.return_value = ["0.0"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises DataValidationError
        with pytest.raises(DataValidationError, match="Price must be > 0"):
            service.get_quote("INVALID")


class TestEndToEndHistoricalData:
    """T053: Test complete historical data retrieval flow."""

    @patch('robin_stocks.robinhood.get_stock_historicals')
    def test_end_to_end_historical_data(self, mock_get_stock_historicals):
        """
        T053: End-to-end test for historical data retrieval.

        GIVEN: MarketDataService with mock robin_stocks
        WHEN: get_historical_data called with "TSLA"
        THEN: Returns validated DataFrame with normalized columns

        Tests complete flow:
        1. API call to robin_stocks
        2. DataFrame creation
        3. Column normalization
        4. Historical data validation
        5. Return validated DataFrame
        """
        # Given: robin_stocks returns valid historical data
        mock_data = [
            {
                'begins_at': '2024-01-01T00:00:00Z',
                'open_price': '250.00',
                'high_price': '255.00',
                'low_price': '248.00',
                'close_price': '252.50',
                'volume': 50000000
            },
            {
                'begins_at': '2024-01-02T00:00:00Z',
                'open_price': '252.50',
                'high_price': '258.00',
                'low_price': '251.00',
                'close_price': '257.00',
                'volume': 48000000
            }
        ]
        mock_get_stock_historicals.return_value = mock_data

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_historical_data called
        df = service.get_historical_data("TSLA", interval="day", span="week")

        # Then: Returns DataFrame with normalized columns
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['date', 'open', 'high', 'low', 'close', 'volume']

        # And: Data values correct
        assert df.iloc[0]['date'] == '2024-01-01T00:00:00Z'
        assert df.iloc[0]['open'] == '250.00'
        assert df.iloc[0]['close'] == '252.50'

        # And: robin_stocks called with correct parameters
        mock_get_stock_historicals.assert_called_once_with("TSLA", interval="day", span="week")

    @patch('robin_stocks.robinhood.get_stock_historicals')
    def test_end_to_end_historical_data_validation_failure(self, mock_get_stock_historicals):
        """
        T053: Test historical data retrieval fails on incomplete data.

        GIVEN: MarketDataService with mock robin_stocks
        WHEN: get_historical_data called and robin_stocks returns incomplete data
        THEN: Raises DataValidationError from validation layer
        """
        # Given: robin_stocks returns incomplete data (missing columns)
        mock_data = [
            {
                'begins_at': '2024-01-01T00:00:00Z',
                'open_price': '250.00',
                # Missing required columns
            }
        ]
        mock_get_stock_historicals.return_value = mock_data

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_historical_data raises DataValidationError
        with pytest.raises(DataValidationError, match="Missing required columns"):
            service.get_historical_data("INVALID")


class TestRateLimitHandling:
    """T054: Test rate limit retry behavior."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_rate_limit_handling_with_retry_success(
        self, mock_sleep, mock_get_latest_price, mock_is_trading_hours
    ):
        """
        T054: Test rate limit triggers retry and succeeds.

        GIVEN: MarketDataService with @with_retry decorator
        WHEN: get_quote fails with RateLimitError then succeeds
        THEN: Retries automatically and returns Quote

        Tests:
        1. First call raises RateLimitError (HTTP 429)
        2. @with_retry catches error and waits
        3. Second call succeeds and returns Quote
        """
        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks fails with 429, then succeeds
        mock_get_latest_price.side_effect = [
            RateLimitError("Rate limit exceeded", retry_after=1),
            ["180.00"]  # Success on retry
        ]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called
        quote = service.get_quote("MSFT")

        # Then: Returns Quote after retry
        assert isinstance(quote, Quote)
        assert quote.symbol == "MSFT"
        assert quote.current_price == Decimal("180.00")

        # And: Retried (called twice)
        assert mock_get_latest_price.call_count == 2

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    @patch('time.sleep')
    def test_rate_limit_handling_exhausts_retries(
        self, mock_sleep, mock_get_latest_price, mock_is_trading_hours
    ):
        """
        T054: Test rate limit exhausts retries and fails.

        GIVEN: MarketDataService with max_retries=3
        WHEN: get_quote fails with RateLimitError 3 times
        THEN: Raises RateLimitError after exhausting retries
        """
        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks always fails with 429
        mock_get_latest_price.side_effect = RateLimitError("Rate limit exceeded", retry_after=1)

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises RateLimitError after retries
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            service.get_quote("AAPL")

        # And: Tried 4 times (1 initial + 3 retries)
        assert mock_get_latest_price.call_count == 4


class TestTradingHoursBlocking:
    """T055: Test trading hours validation blocks requests."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_trading_hours_blocking_outside_hours(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T055: Test get_quote blocks requests outside trading hours.

        GIVEN: MarketDataService with trading hours check
        WHEN: get_quote called outside trading hours (7am-10am EST)
        THEN: Raises TradingHoursError before calling robin_stocks
        """
        # Given: Outside trading hours
        mock_is_trading_hours.return_value = False

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises TradingHoursError
        with pytest.raises(TradingHoursError, match="Trading blocked outside 7am-10am EST"):
            service.get_quote("AAPL")

        # And: robin_stocks NOT called (blocked before API call)
        mock_get_latest_price.assert_not_called()

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_trading_hours_blocking_during_hours(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T055: Test get_quote allows requests during trading hours.

        GIVEN: MarketDataService with trading hours check
        WHEN: get_quote called during trading hours (7am-10am EST)
        THEN: Proceeds to API call and returns Quote
        """
        # Given: During trading hours
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["150.00"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called
        quote = service.get_quote("GOOGL")

        # Then: Returns Quote (no TradingHoursError)
        assert isinstance(quote, Quote)
        assert quote.symbol == "GOOGL"

        # And: robin_stocks called (not blocked)
        mock_get_latest_price.assert_called_once()
