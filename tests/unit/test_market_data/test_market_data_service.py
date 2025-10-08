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

    @patch('robin_stocks.robinhood.get_latest_price')
    def test_get_quote_valid_symbol(self, mock_get_latest_price):
        """
        T031 [RED]: Test get_quote returns Quote for valid symbol.

        GIVEN: MarketDataService initialized
        WHEN: get_quote called with valid symbol "AAPL"
        THEN: Returns Quote with symbol="AAPL", current_price=150.25
        """
        from datetime import datetime, timezone
        from decimal import Decimal
        from src.trading_bot.market_data.data_models import Quote

        # Mock robin_stocks.robinhood.get_latest_price to return ["150.25"]
        mock_get_latest_price.return_value = ["150.25"]

        # Given: MarketDataService initialized with mock auth
        from src.trading_bot.market_data.market_data_service import MarketDataService
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
        assert quote.market_state in ["regular", "pre_market", "after_hours", "closed"]

        # Verify robin_stocks called correctly
        mock_get_latest_price.assert_called_once_with("AAPL", includeExtendedHours=True)
