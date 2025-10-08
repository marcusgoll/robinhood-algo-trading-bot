"""
Market Data Service

Main service class for retrieving real-time and historical market data
from Robinhood API with validation and error handling.

Constitution v1.0.0:
- §Data_Integrity: All market data validated before use
- §Audit_Everything: All API calls logged
- §Safety_First: Fail-fast on validation errors
"""

from typing import Optional
import logging
from datetime import datetime, timezone
from decimal import Decimal

import robin_stocks.robinhood as r

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.market_data.data_models import MarketDataConfig, Quote
from trading_bot.market_data.validators import validate_quote
from trading_bot.logger import TradingLogger
from trading_bot.error_handling.retry import with_retry
from trading_bot.error_handling.policies import DEFAULT_POLICY


class MarketDataService:
    """
    Market data service for fetching and validating stock market data.

    Handles real-time quotes, historical data, and market status with
    built-in validation and error handling.
    """

    def __init__(
        self,
        auth: RobinhoodAuth,
        config: Optional[MarketDataConfig] = None,
        logger: Optional[logging.Logger] = None
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

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")

        Returns:
            Quote: Validated Quote dataclass with current price and timestamp

        Raises:
            DataValidationError: If price is invalid or timestamp is stale
            RateLimitError: After 3 retries on HTTP 429
        """
        # Fetch latest price from robin_stocks
        price_list = r.get_latest_price(symbol, includeExtendedHours=True)

        # Extract price (robin_stocks returns list with single string)
        price_str = price_list[0]
        price = float(price_str)

        # Get current timestamp in UTC
        timestamp_utc = datetime.now(timezone.utc)

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
