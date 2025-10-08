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

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.market_data.data_models import MarketDataConfig
from trading_bot.logger import TradingLogger


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
