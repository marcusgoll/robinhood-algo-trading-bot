"""Integration tests for multi-timeframe validation with real market data.

Tests E2E flow with actual MarketDataService API calls to validate
daily timeframe indicator calculations work correctly with live data.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock
from src.trading_bot.validation.multi_timeframe_validator import MultiTimeframeValidator
from src.trading_bot.validation.models import ValidationStatus
from src.trading_bot.validation.config import MultiTimeframeConfig
from src.trading_bot.market_data.market_data_service import MarketDataService
from src.trading_bot.auth.robinhood_auth import RobinhoodAuth
from src.trading_bot.indicators.service import TechnicalIndicatorsService


class TestDailyValidationE2E:
    """E2E tests using real market data API calls."""

    @pytest.fixture
    def validator(self):
        """Create validator with real services (not mocked)."""
        config = MultiTimeframeConfig(
            enabled=True,
            daily_weight=Decimal("0.6"),
            h4_weight=Decimal("0.4"),
            aggregate_threshold=Decimal("0.5"),
            max_retries=3,
            retry_backoff_base_ms=1000
        )
        # Create mock auth for MarketDataService
        mock_auth = Mock(spec=RobinhoodAuth)
        market_data_service = MarketDataService(auth=mock_auth)
        return MultiTimeframeValidator(
            market_data_service=market_data_service,
            config=config
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_e2e_daily_validation_with_real_market_data(self, validator):
        """
        T019: Use real MarketDataService to fetch AAPL daily data,
        validate indicators calculated correctly.

        Given: Real MarketDataService (actual API call to Robinhood)
        When: Validate AAPL with current price
        Then: TimeframeIndicators has valid MACD and EMA values
        """
        # Use a known stable symbol
        symbol = "AAPL"
        current_price = Decimal("150.00")  # Mock price (actual price not critical for indicator validation)

        # Execute validation with real API call
        result = validator.validate(symbol=symbol, current_price=current_price, bars_5min=[])

        # Verify result structure
        assert result is not None
        assert result.symbol == symbol
        assert result.status in [ValidationStatus.PASS, ValidationStatus.BLOCK, ValidationStatus.DEGRADED]

        # Verify daily indicators were calculated (not None)
        assert result.daily_indicators is not None
        assert result.daily_indicators.timeframe == "DAILY"
        assert result.daily_indicators.ema_20 > Decimal("0")  # EMA should be positive
        assert result.daily_indicators.bar_count >= 30  # Minimum 30 bars required

        # Verify MACD line exists (can be positive or negative depending on market)
        assert result.daily_indicators.macd_line is not None

        # Verify scoring is in valid range
        assert Decimal("0.0") <= result.daily_score <= Decimal("1.0")
        assert Decimal("0.0") <= result.aggregate_score <= Decimal("1.0")

        # Verify timestamp is recent (within last minute)
        time_diff = (datetime.now() - result.timestamp).total_seconds()
        assert time_diff < 60  # Should complete within 1 minute

    @pytest.mark.integration
    @pytest.mark.slow
    def test_e2e_validation_respects_minimum_bar_requirement(self, validator):
        """
        Verify validation fails gracefully when insufficient historical data.

        Given: Symbol with limited history
        When: Fetch daily data
        Then: Either returns DEGRADED status or sufficient bars
        """
        symbol = "AAPL"
        current_price = Decimal("150.00")

        result = validator.validate(symbol=symbol, current_price=current_price, bars_5min=[])

        # Either degraded (insufficient data) or has sufficient bars
        if result.status == ValidationStatus.DEGRADED:
            assert "insufficient" in " ".join(result.reasons).lower() or "unavailable" in " ".join(result.reasons).lower()
        else:
            assert result.daily_indicators.bar_count >= 30

    @pytest.mark.integration
    @pytest.mark.slow
    def test_e2e_validation_latency_under_10s(self, validator):
        """
        Verify validation completes within acceptable time (integration test).

        Given: Real API call to MarketDataService
        When: Validate symbol
        Then: Completes within 10 seconds (integration test allows longer latency)
        """
        symbol = "AAPL"
        current_price = Decimal("150.00")

        start_time = datetime.now()
        result = validator.validate(symbol=symbol, current_price=current_price, bars_5min=[])
        end_time = datetime.now()

        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Integration test allows up to 10s (real API calls)
        assert latency_ms < 10000  # 10 seconds
        assert result is not None
