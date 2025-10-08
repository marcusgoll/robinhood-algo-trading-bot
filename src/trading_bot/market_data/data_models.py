"""
Market Data Models

Dataclasses for market data: Quote, MarketStatus, MarketDataConfig

These immutable dataclasses represent validated market data from Robinhood API.
All timestamps are in UTC, prices use Decimal for precision.
"""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime


@dataclass(frozen=True)
class Quote:
    """
    Immutable real-time stock quote.

    Attributes:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        current_price: Current stock price in USD (Decimal for precision)
        timestamp_utc: Quote timestamp in UTC
        market_state: Trading state ('regular', 'pre_market', 'after_hours', 'closed')
    """
    symbol: str
    current_price: Decimal
    timestamp_utc: datetime
    market_state: str


@dataclass(frozen=True)
class MarketStatus:
    """
    Immutable market hours status.

    Attributes:
        is_open: Whether market is currently open for trading
        next_open: Next market open time in UTC
        next_close: Next market close time in UTC
    """
    is_open: bool
    next_open: datetime
    next_close: datetime


@dataclass(frozen=True)
class MarketDataConfig:
    """
    Configuration for market data service.

    All fields have sensible defaults for production use.

    Attributes:
        rate_limit_retries: Number of retry attempts on rate limit (default: 3)
        rate_limit_backoff_base: Base backoff time in seconds for exponential backoff (default: 1.0)
        quote_staleness_threshold: Maximum quote age in seconds before considered stale (default: 300)
        trading_window_start: Trading window start hour in EST, 24-hour format (default: 7 for 7am)
        trading_window_end: Trading window end hour in EST, 24-hour format (default: 10 for 10am)
        trading_timezone: Timezone for trading hours enforcement (default: 'America/New_York')
    """
    rate_limit_retries: int = 3
    rate_limit_backoff_base: float = 1.0
    quote_staleness_threshold: int = 300
    trading_window_start: int = 7
    trading_window_end: int = 10
    trading_timezone: str = "America/New_York"
