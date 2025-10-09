"""
Unit tests for data models (Quote, MarketStatus, MarketDataConfig)
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError


# T004 [RED]: Write failing test for Quote immutability
def test_quote_is_immutable():
    """Test that Quote dataclass is frozen and immutable."""
    from trading_bot.market_data.data_models import Quote

    quote = Quote(
        symbol="AAPL",
        current_price=Decimal("150.25"),
        timestamp_utc=datetime.now(timezone.utc),
        market_state="regular"
    )

    # Should raise FrozenInstanceError when trying to modify
    with pytest.raises(FrozenInstanceError):
        quote.current_price = Decimal("155.00")


# T006 [RED]: Write failing test for MarketStatus immutability
def test_market_status_is_immutable():
    """Test that MarketStatus dataclass is frozen and immutable."""
    from trading_bot.market_data.data_models import MarketStatus

    now = datetime.now(timezone.utc)
    status = MarketStatus(
        is_open=True,
        next_open=now,
        next_close=now
    )

    # Should raise FrozenInstanceError when trying to modify
    with pytest.raises(FrozenInstanceError):
        status.is_open = False


# T008 [RED]: Write failing test for MarketDataConfig defaults
def test_market_data_config_defaults():
    """Test that MarketDataConfig has correct default values."""
    from trading_bot.market_data.data_models import MarketDataConfig

    config = MarketDataConfig()

    assert config.rate_limit_retries == 3
    assert config.rate_limit_backoff_base == 1.0
    assert config.quote_staleness_threshold == 300
    assert config.trading_window_start == 7
    assert config.trading_window_end == 10
    assert config.trading_timezone == "America/New_York"
