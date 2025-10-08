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

# Package exports will be populated after implementation
__all__ = []
