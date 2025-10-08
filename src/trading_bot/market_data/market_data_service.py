"""
Market Data Service

Main service class for retrieving real-time and historical market data
from Robinhood API with validation and error handling.

Constitution v1.0.0:
- §Data_Integrity: All market data validated before use
- §Audit_Everything: All API calls logged
- §Safety_First: Fail-fast on validation errors
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import robin_stocks.robinhood as r

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.error_handling.policies import DEFAULT_POLICY
from trading_bot.error_handling.retry import with_retry
from trading_bot.logger import TradingLogger
from trading_bot.market_data.data_models import MarketDataConfig, MarketStatus, Quote
from trading_bot.market_data.validators import (
    validate_historical_data,
    validate_quote,
    validate_trade_time,
)


class MarketDataService:
    """
    Market data service for fetching and validating stock market data.

    Handles real-time quotes, historical data, and market status with
    built-in validation and error handling.
    """

    def __init__(
        self,
        auth: RobinhoodAuth,
        config: MarketDataConfig | None = None,
        logger: logging.Logger | None = None
    ) -> None:
        """
        Initialize MarketDataService.

        Args:
            auth: Authenticated RobinhoodAuth instance
            config: Optional MarketDataConfig (uses defaults if not provided)
            logger: Optional custom logger (uses TradingLogger if not provided)
        """
        self.auth = auth
        self.config = config if config is not None else MarketDataConfig()
        self.logger = logger if logger is not None else TradingLogger.get_logger(__name__)

    @with_retry(policy=DEFAULT_POLICY)
    def get_quote(self, symbol: str) -> Quote:
        """
        Get real-time stock quote for a symbol.

        T033: Fetches latest price from robin_stocks, validates with validate_quote,
        and returns Quote dataclass.
        T035: Added @with_retry decorator for automatic retry on rate limits.
        T045-T051: Added trading hours validation.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")

        Returns:
            Quote: Validated Quote dataclass with current price and timestamp

        Raises:
            DataValidationError: If price is invalid or timestamp is stale
            RateLimitError: After 3 retries on HTTP 429
            TradingHoursError: If called outside trading hours (7am-10am EST)
        """
        # T045-T051: Validate trading hours before fetching quote
        validate_trade_time()

        # Log the request (T044)
        self._log_request("get_quote", {"symbol": symbol})

        # Fetch latest price from robin_stocks
        price_list = r.get_latest_price(symbol, includeExtendedHours=True)

        # Extract price (robin_stocks returns list with single string)
        price_str = price_list[0]
        price = float(price_str)

        # Get current timestamp in UTC
        timestamp_utc = datetime.now(UTC)

        # Determine market state (simplified for T033, full logic in later tasks)
        market_state = "regular"

        # Build quote data dict for validation
        quote_data = {
            'symbol': symbol,
            'price': price,
            'timestamp': timestamp_utc,
            'market_state': market_state
        }

        # Validate quote data (raises DataValidationError if invalid)
        validate_quote(quote_data)

        # Return validated Quote dataclass
        return Quote(
            symbol=symbol,
            current_price=Decimal(str(price)),  # Convert to Decimal for precision
            timestamp_utc=timestamp_utc,
            market_state=market_state
        )

    @with_retry(policy=DEFAULT_POLICY)
    def get_historical_data(
        self,
        symbol: str,
        interval: str = "day",
        span: str = "3month"
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data for a symbol.

        T036-T038: Fetches historical data from robin_stocks, normalizes column names,
        validates with validate_historical_data, and returns DataFrame.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")
            interval: Data interval ("day", "week", "10minute", "5minute")
            span: Time span ("day", "week", "month", "3month", "year", "5year")

        Returns:
            DataFrame with columns: date, open, high, low, close, volume

        Raises:
            DataValidationError: If historical data is invalid or incomplete
            RateLimitError: After 3 retries on HTTP 429
        """
        # Log the request (T044)
        self._log_request("get_historical_data", {"symbol": symbol, "interval": interval, "span": span})

        # Fetch historical data from robin_stocks
        data = r.get_stock_historicals(symbol, interval=interval, span=span)

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Normalize column names to standard OHLCV format
        df = df.rename(columns={
            'begins_at': 'date',
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close',
            'volume': 'volume'
        })

        # Validate historical data (raises DataValidationError if invalid)
        validate_historical_data(df)

        return df

    @with_retry(policy=DEFAULT_POLICY)
    def is_market_open(self) -> MarketStatus:
        """
        Check if market is currently open.

        T039-T041: Fetches market hours from robin_stocks and returns MarketStatus.

        Returns:
            MarketStatus with is_open, next_open, and next_close times

        Raises:
            RateLimitError: After 3 retries on HTTP 429
        """
        # Log the request (T044)
        self._log_request("is_market_open", {"date": datetime.now().strftime('%Y-%m-%d')})

        # Fetch market hours for NYSE (representative of US stock market)
        market_hours = r.get_market_hours('XNYS', datetime.now().strftime('%Y-%m-%d'))

        # Parse market status
        is_open = market_hours.get('is_open', False)
        next_open = datetime.fromisoformat(market_hours['next_open_hours'])
        next_close = datetime.fromisoformat(market_hours['next_close_hours'])

        return MarketStatus(
            is_open=is_open,
            next_open=next_open,
            next_close=next_close
        )

    def get_quotes_batch(self, symbols: list[str]) -> dict[str, Quote]:
        """
        Get quotes for multiple symbols.

        T042-T043: Fetches quotes for a list of symbols, continues on individual failures.

        Args:
            symbols: List of stock ticker symbols

        Returns:
            Dictionary mapping symbols to Quote objects (excludes failed symbols)
        """
        # Log the request (T044)
        self._log_request("get_quotes_batch", {"symbols": symbols, "count": len(symbols)})

        quotes = {}
        for symbol in symbols:
            try:
                quotes[symbol] = self.get_quote(symbol)
            except Exception as e:
                self.logger.warning(f"Failed to get quote for {symbol}: {e}")

        return quotes

    def _log_request(self, method: str, params: dict) -> None:
        """
        Log API request with method name and parameters.

        T044: Helper for standardized API request logging.

        Args:
            method: API method name (e.g., "get_quote", "get_historical_data")
            params: Request parameters dictionary
        """
        self.logger.info(f"API Request: {method}", extra={'params': params})
