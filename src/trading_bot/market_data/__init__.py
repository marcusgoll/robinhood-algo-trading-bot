"""
Market Data and Trading Hours Module

Provides real-time stock quotes, historical price data, market hours checking,
and enforces 7am-10am EST trading window for peak volatility trading.

This module ensures data integrity through validation of all market data
(timestamps, bounds, completeness) and implements rate limit protection.

Example usage:
    from trading_bot.auth.robinhood_auth import RobinhoodAuth
    from trading_bot.market_data import MarketDataService, MarketDataConfig
    from trading_bot.config import Config

    config = Config.from_env_and_json()
    auth = RobinhoodAuth(config)
    auth.login()

    market_data = MarketDataService(auth)
    quote = market_data.get_quote('AAPL')
    print(f"Quote: {quote.symbol} @ ${quote.current_price}")
"""

# T062: Package exports - complete market_data module public API
from trading_bot.market_data.data_models import MarketDataConfig, MarketStatus, Quote
from trading_bot.market_data.exceptions import DataValidationError, TradingHoursError
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.market_data.fmp_client import FMPClient, FMPRateLimitExceeded
from trading_bot.market_data.validators import (
    validate_historical_data,
    validate_price,
    validate_quote,
    validate_timestamp,
    validate_trade_time,
)

__all__ = [
    # Service
    'MarketDataService',
    'FMPClient',
    # Data models
    'Quote',
    'MarketStatus',
    'MarketDataConfig',
    # Validators
    'validate_quote',
    'validate_price',
    'validate_timestamp',
    'validate_historical_data',
    'validate_trade_time',
    # Exceptions
    'DataValidationError',
    'TradingHoursError',
    'FMPRateLimitExceeded',
]
