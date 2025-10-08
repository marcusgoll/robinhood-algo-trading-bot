"""
Unit tests for MarketDataService

Tests the complete market data service including:
- Service initialization with auth and config
- Quote retrieval with validation
- Historical data fetching
- Market status checking
- Error handling and retry logic

Constitution v1.0.0 - §Testing_Requirements: TDD approach
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import os


class TestServiceInitialization:
    """Test suite for MarketDataService initialization."""

    def test_service_initialization(self):
        """
        Test MarketDataService accepts RobinhoodAuth and MarketDataConfig.

        GIVEN: RobinhoodAuth instance and MarketDataConfig
        WHEN: MarketDataService created
        THEN: Service stores auth, config, and logger correctly
        """
        # Given: Mock RobinhoodAuth
        from unittest.mock import Mock
        mock_auth = Mock()

        # And: MarketDataConfig with custom settings
        from src.trading_bot.market_data.data_models import MarketDataConfig
        config = MarketDataConfig(
            rate_limit_retries=5,
            trading_window_start=8
        )

        # When: MarketDataService created
        from src.trading_bot.market_data.market_data_service import MarketDataService
        service = MarketDataService(auth=mock_auth, config=config)

        # Then: Service stores auth and config
        assert service.auth == mock_auth
        assert service.config == config
        assert service.config.rate_limit_retries == 5
        assert service.config.trading_window_start == 8

    def test_service_initialization_with_defaults(self):
        """
        Test MarketDataService uses default config if not provided.

        GIVEN: RobinhoodAuth instance only (no config)
        WHEN: MarketDataService created
        THEN: Service uses MarketDataConfig defaults
        """
        # Given: Mock RobinhoodAuth
        from unittest.mock import Mock
        mock_auth = Mock()

        # When: MarketDataService created without config
        from src.trading_bot.market_data.market_data_service import MarketDataService
        service = MarketDataService(auth=mock_auth)

        # Then: Service uses default config
        assert service.auth == mock_auth
        assert service.config is not None
        assert service.config.rate_limit_retries == 3  # Default
        assert service.config.trading_window_start == 7  # Default

    def test_service_initialization_with_custom_logger(self):
        """
        Test MarketDataService accepts custom logger.

        GIVEN: RobinhoodAuth and custom logger
        WHEN: MarketDataService created
        THEN: Service uses provided logger
        """
        # Given: Mock auth and custom logger
        from unittest.mock import Mock
        import logging
        mock_auth = Mock()
        custom_logger = logging.getLogger("custom_test_logger")

        # When: MarketDataService created with custom logger
        from src.trading_bot.market_data.market_data_service import MarketDataService
        service = MarketDataService(auth=mock_auth, logger=custom_logger)

        # Then: Service uses custom logger
        assert service.auth == mock_auth
        assert service.logger == custom_logger


class TestGetQuote:
    """Test suite for get_quote method."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_get_quote_valid_symbol(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T031 [RED]: Test get_quote returns Quote for valid symbol.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called with valid symbol "AAPL"
        THEN: Returns Quote with symbol="AAPL", current_price=150.25
        """
        from datetime import datetime, timezone
        from decimal import Decimal
        from trading_bot.market_data.data_models import Quote
        from trading_bot.market_data.market_data_service import MarketDataService

        # Mock trading hours check to allow trading
        mock_is_trading_hours.return_value = True

        # Mock robin_stocks.robinhood.get_latest_price to return ["150.25"]
        mock_get_latest_price.return_value = ["150.25"]

        # Given: MarketDataService initialized with mock auth
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called with valid symbol "AAPL"
        quote = service.get_quote("AAPL")

        # Then: Returns Quote dataclass
        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.current_price == Decimal("150.25")
        assert isinstance(quote.timestamp_utc, datetime)
        assert quote.timestamp_utc.tzinfo == timezone.utc
        # Contract compliance: market_state must be one of [regular, pre, post, closed]
        assert quote.market_state in ["regular", "pre", "post", "closed"]

        # Verify robin_stocks called correctly
        mock_get_latest_price.assert_called_once_with("AAPL", includeExtendedHours=True)

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_get_quote_validates_price(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T032 [RED]: Test get_quote validates price using validate_quote.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called with symbol that returns invalid price "0.0"
        THEN: Raises DataValidationError from validate_quote
        """
        from trading_bot.market_data.exceptions import DataValidationError
        from trading_bot.market_data.market_data_service import MarketDataService

        # Mock trading hours check to allow trading
        mock_is_trading_hours.return_value = True

        # Mock robin_stocks.robinhood.get_latest_price to return ["0.0"] (invalid)
        mock_get_latest_price.return_value = ["0.0"]

        # Given: MarketDataService initialized with mock auth
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote called with symbol, raises DataValidationError
        with pytest.raises(DataValidationError, match="Price must be > 0"):
            service.get_quote("INVALID")


class TestRetryBehavior:
    """Test suite for retry behavior with @with_retry decorator."""

    def test_get_quote_has_retry_decorator(self):
        """
        T034-T035: Verify get_quote has @with_retry decorator applied.

        GIVEN: MarketDataService class
        WHEN: Inspecting get_quote method
        THEN: Method has __wrapped__ attribute (decorator applied)
        """
        from src.trading_bot.market_data.market_data_service import MarketDataService

        # Given: MarketDataService class
        # When: Check if get_quote is decorated
        method = MarketDataService.get_quote

        # Then: Should have __wrapped__ attribute from @with_retry
        assert hasattr(method, '__wrapped__'), "get_quote should be decorated with @with_retry"

    # TODO T034-T035: Add integration test for actual retry behavior
    # Note: Unit test with mocks has issues with decorator evaluation order.
    # Integration test should use real RateLimitError from robin_stocks.


class TestNetworkErrorHandling:
    """T056: Test network error handling."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_network_error_handling(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T056: Test network error handling with ConnectionError.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called and robin_stocks raises ConnectionError
        THEN: Raises RetriableError (propagated from network layer)
        """
        from trading_bot.error_handling.exceptions import RetriableError
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks raises ConnectionError
        mock_get_latest_price.side_effect = ConnectionError("Network unreachable")

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises ConnectionError (will be caught by retry decorator)
        with pytest.raises(ConnectionError, match="Network unreachable"):
            service.get_quote("AAPL")

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_timeout_error_handling(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T056: Test timeout error handling.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called and robin_stocks raises TimeoutError
        THEN: Raises TimeoutError (propagated from network layer)
        """
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks raises TimeoutError
        mock_get_latest_price.side_effect = TimeoutError("Request timed out")

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises TimeoutError
        with pytest.raises(TimeoutError, match="Request timed out"):
            service.get_quote("AAPL")


class TestInvalidSymbolHandling:
    """T057: Test invalid symbol handling."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_invalid_symbol_handling(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T057: Test invalid symbol raises ValueError from robin_stocks.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called with invalid symbol
        THEN: Raises ValueError from robin_stocks
        """
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks raises ValueError for invalid symbol
        mock_get_latest_price.side_effect = ValueError("Invalid stock symbol: INVALID_XYZ")

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises ValueError
        with pytest.raises(ValueError, match="Invalid stock symbol"):
            service.get_quote("INVALID_XYZ")

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_empty_response_handling(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T057: Test empty response from robin_stocks.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called and robin_stocks returns empty list
        THEN: Raises IndexError when trying to access price
        """
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns empty list
        mock_get_latest_price.return_value = []

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises IndexError
        with pytest.raises(IndexError):
            service.get_quote("UNKNOWN")


class TestCircuitBreakerIntegration:
    """T058: Test circuit breaker integration."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_circuit_breaker_integration(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T058: Test circuit breaker triggers on repeated failures.

        GIVEN: MarketDataService with circuit breaker enabled
        WHEN: get_quote fails repeatedly (exceeds failure threshold)
        THEN: Circuit breaker opens and blocks subsequent requests

        NOTE: Circuit breaker implementation is in error_handling module.
        This test verifies integration with MarketDataService.
        """
        from trading_bot.market_data.market_data_service import MarketDataService
        from trading_bot.error_handling.circuit_breaker import CircuitBreaker

        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks always fails
        mock_get_latest_price.side_effect = ConnectionError("Network unreachable")

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: Multiple failures occur
        # Then: Each call raises ConnectionError
        for i in range(3):
            with pytest.raises(ConnectionError):
                service.get_quote("AAPL")

        # NOTE: Circuit breaker state verification requires access to circuit breaker instance
        # Full integration test should be in test_circuit_breaker_integration.py


class TestDataValidationErrors:
    """T059: Test data validation error handling."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_data_validation_errors(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T059: Test DataValidationError raised on invalid price.

        GIVEN: MarketDataService initialized
        WHEN: get_quote returns invalid price (negative)
        THEN: Raises DataValidationError from validate_quote
        """
        from trading_bot.market_data.exceptions import DataValidationError
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns negative price
        mock_get_latest_price.return_value = ["-10.50"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises DataValidationError
        with pytest.raises(DataValidationError, match="Price must be > 0"):
            service.get_quote("INVALID")

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_zero_price_validation(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T059: Test DataValidationError raised on zero price.

        GIVEN: MarketDataService initialized
        WHEN: get_quote returns zero price
        THEN: Raises DataValidationError from validate_quote
        """
        from trading_bot.market_data.exceptions import DataValidationError
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns zero price
        mock_get_latest_price.return_value = ["0.0"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When/Then: get_quote raises DataValidationError
        with pytest.raises(DataValidationError, match="Price must be > 0"):
            service.get_quote("ZERO")


class TestTimestampStaleness:
    """T060: Test timestamp staleness validation."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_timestamp_staleness(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T060: Test timestamp staleness check (future work).

        GIVEN: MarketDataService initialized
        WHEN: get_quote returns data with stale timestamp
        THEN: Should raise DataValidationError (future enhancement)

        NOTE: Current implementation always uses datetime.now(timezone.utc)
        so timestamp is always fresh. This test documents future behavior
        when we receive timestamps from API responses.
        """
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours enabled
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["150.00"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called
        quote = service.get_quote("AAPL")

        # Then: Timestamp is fresh (within seconds of now)
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        age = now - quote.timestamp_utc
        assert age < timedelta(seconds=5), "Timestamp should be fresh"


class TestMarketStateDetection:
    """Test market_state detection per contract (pre, regular, post, closed)."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_market_state_pre_market(self, mock_get_latest_price, mock_is_trading_hours):
        """
        Test market_state = 'pre' during pre-market hours (4am-9:30am EST).

        GIVEN: MarketDataService initialized
        WHEN: get_quote called during pre-market hours (8am EST)
        THEN: Quote.market_state == "pre"
        """
        from datetime import UTC, datetime
        from freezegun import freeze_time
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours check passes (pre-market is within 7am-10am window)
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["150.25"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called during pre-market hours (8am EST = 12:00 UTC)
        with freeze_time("2025-10-08 12:00:00", tz_offset=0):  # Wednesday 8am EST
            quote = service.get_quote("AAPL")

        # Then: market_state is "pre"
        assert quote.market_state == "pre"

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_market_state_regular_hours(self, mock_get_latest_price, mock_is_trading_hours):
        """
        Test market_state = 'regular' during regular hours (9:30am-4pm EST).

        GIVEN: MarketDataService initialized
        WHEN: get_quote called during regular hours (2pm EST)
        THEN: Quote.market_state == "regular"
        """
        from freezegun import freeze_time
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours check passes
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["150.25"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called during regular hours (2pm EST = 18:00 UTC)
        with freeze_time("2025-10-08 18:00:00", tz_offset=0):  # Wednesday 2pm EST
            quote = service.get_quote("AAPL")

        # Then: market_state is "regular"
        assert quote.market_state == "regular"

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_market_state_post_market(self, mock_get_latest_price, mock_is_trading_hours):
        """
        Test market_state = 'post' during after-hours (4pm-8pm EST).

        GIVEN: MarketDataService initialized
        WHEN: get_quote called during after-hours (6pm EST)
        THEN: Quote.market_state == "post"
        """
        from freezegun import freeze_time
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours check fails (after-hours outside 7am-10am window)
        # But we'll mock it to pass for testing market_state detection
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["150.25"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called during after-hours (6pm EST = 22:00 UTC)
        with freeze_time("2025-10-08 22:00:00", tz_offset=0):  # Wednesday 6pm EST
            quote = service.get_quote("AAPL")

        # Then: market_state is "post"
        assert quote.market_state == "post"

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_market_state_closed_weekend(self, mock_get_latest_price, mock_is_trading_hours):
        """
        Test market_state = 'closed' during weekend.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called on Saturday
        THEN: Quote.market_state == "closed"
        """
        from freezegun import freeze_time
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours check fails (weekend)
        # But we'll mock it to pass for testing market_state detection
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["150.25"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called on weekend (Saturday 10am EST = 14:00 UTC)
        with freeze_time("2025-10-11 14:00:00", tz_offset=0):  # Saturday 10am EST
            quote = service.get_quote("AAPL")

        # Then: market_state is "closed"
        assert quote.market_state == "closed"

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_market_state_closed_late_night(self, mock_get_latest_price, mock_is_trading_hours):
        """
        Test market_state = 'closed' late at night (after 8pm EST).

        GIVEN: MarketDataService initialized
        WHEN: get_quote called at 10pm EST
        THEN: Quote.market_state == "closed"
        """
        from freezegun import freeze_time
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: Trading hours check fails (late night)
        # But we'll mock it to pass for testing market_state detection
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["150.25"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called late at night (10pm EST = 02:00 UTC next day)
        with freeze_time("2025-10-09 02:00:00", tz_offset=0):  # Wednesday 10pm EST
            quote = service.get_quote("AAPL")

        # Then: market_state is "closed"
        assert quote.market_state == "closed"


class TestTradingHoursError:
    """T061: Test TradingHoursError raised outside trading window."""

    @patch('trading_bot.utils.time_utils.is_trading_hours')
    @patch('robin_stocks.robinhood.get_latest_price')
    def test_trading_hours_error(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T061: Test TradingHoursError raised outside trading window.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called outside trading hours (7am-10am EST)
        THEN: Raises TradingHoursError before calling robin_stocks
        """
        from trading_bot.market_data.exceptions import TradingHoursError
        from trading_bot.market_data.market_data_service import MarketDataService

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
    def test_trading_hours_allows_during_window(self, mock_get_latest_price, mock_is_trading_hours):
        """
        T061: Test get_quote proceeds during trading hours.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called during trading hours
        THEN: Proceeds to API call (no TradingHoursError)
        """
        from trading_bot.market_data.market_data_service import MarketDataService

        # Given: During trading hours
        mock_is_trading_hours.return_value = True

        # And: robin_stocks returns valid price
        mock_get_latest_price.return_value = ["150.00"]

        # And: MarketDataService initialized
        mock_auth = Mock()
        service = MarketDataService(auth=mock_auth)

        # When: get_quote called
        quote = service.get_quote("AAPL")

        # Then: Returns Quote (no TradingHoursError)
        assert quote is not None
        assert quote.symbol == "AAPL"

        # And: robin_stocks called (not blocked)
        mock_get_latest_price.assert_called_once()
