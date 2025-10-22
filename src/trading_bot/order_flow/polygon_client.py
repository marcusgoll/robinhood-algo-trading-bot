"""
Polygon.io API Client

Wrapper for Polygon.io API calls with authentication, rate limiting, and error handling.

Pattern: Follows MarketDataService patterns from market_data/market_data_service.py
"""

from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.error_handling.policies import DEFAULT_POLICY
from trading_bot.error_handling.retry import with_retry
from trading_bot.logger import TradingLogger

from .config import OrderFlowConfig
from .data_models import OrderBookSnapshot, TimeAndSalesRecord
from .validators import validate_level2_data, validate_tape_data

# Get logger
_logger = TradingLogger.get_logger(__name__)


class PolygonClient:
    """
    Polygon.io API client for Level 2 order book and Time & Sales data.

    Provides abstraction layer for API access with automatic retry, rate limiting,
    and data normalization.

    Attributes:
        config: OrderFlowConfig with API key and settings

    Example:
        >>> config = OrderFlowConfig.from_env()
        >>> client = PolygonClient(config)
        >>> snapshot = client.get_level2_snapshot("AAPL")
    """

    def __init__(self, config: OrderFlowConfig) -> None:
        """
        Initialize PolygonClient with configuration.

        Args:
            config: OrderFlowConfig with polygon_api_key
        """
        self.config = config
        _logger.info(
            "PolygonClient initialized",
            extra={"data_source": config.data_source},
        )

    @with_retry(policy=DEFAULT_POLICY)
    def get_level2_snapshot(self, symbol: str) -> OrderBookSnapshot:
        """
        Get Level 2 order book snapshot for a symbol.

        Fetches bid/ask depth from Polygon.io API, normalizes response to
        OrderBookSnapshot dataclass, and validates data integrity.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")

        Returns:
            OrderBookSnapshot with bids, asks, and timestamp

        Raises:
            DataValidationError: If data is stale or invalid
            ConnectionError: If API is unavailable (after retries)

        Example:
            >>> snapshot = client.get_level2_snapshot("AAPL")
            >>> len(snapshot.bids)  # Number of bid levels
            10
        """
        # TODO: T011 - Implement actual API call
        # Endpoint: GET /v2/snapshot/locale/us/markets/stocks/tickers/{symbol}
        # Headers: { "Authorization": f"Bearer {self.config.polygon_api_key}" }
        raise NotImplementedError("T011: get_level2_snapshot() not yet implemented")

    def _normalize_level2_response(self, raw_response: dict) -> OrderBookSnapshot:
        """
        Normalize Polygon.io Level 2 API response to OrderBookSnapshot.

        Converts raw API dict with {"ticker": {..., "bids": [...], "asks": [...], "updated": ...}}
        to OrderBookSnapshot dataclass with proper types.

        Args:
            raw_response: Raw API response dict from Polygon.io

        Returns:
            OrderBookSnapshot with normalized data

        Raises:
            DataValidationError: If response is malformed or validation fails
        """
        # TODO: T012 - Implement normalization logic
        # Extract: ticker.bids, ticker.asks, ticker.updated
        # Convert: updated (unix ms) → datetime UTC
        # Map: {"p": price, "s": size} → (Decimal, int) tuples
        raise NotImplementedError("T012: _normalize_level2_response() not yet implemented")

    @with_retry(policy=DEFAULT_POLICY)
    def get_time_and_sales(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> list[TimeAndSalesRecord]:
        """
        Get Time & Sales tape data for a symbol within time range.

        Fetches executed trades from Polygon.io API, normalizes response to
        list of TimeAndSalesRecord, and validates chronological sequence.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            start_time: Start of time window (UTC)
            end_time: End of time window (UTC)

        Returns:
            List of TimeAndSalesRecord sorted by timestamp

        Raises:
            DataValidationError: If data is out of order or invalid
            ConnectionError: If API is unavailable (after retries)

        Example:
            >>> start = datetime.now(UTC) - timedelta(minutes=5)
            >>> end = datetime.now(UTC)
            >>> trades = client.get_time_and_sales("AAPL", start, end)
            >>> len(trades)  # Number of trades in 5-minute window
            127
        """
        # TODO: T018 - Implement actual API call
        # Endpoint: GET /v3/trades/{symbol}
        # Query params: timestamp >= start_time, timestamp <= end_time
        raise NotImplementedError("T018: get_time_and_sales() not yet implemented")

    def _normalize_tape_response(self, raw_response: dict) -> list[TimeAndSalesRecord]:
        """
        Normalize Polygon.io Time & Sales API response to list of TimeAndSalesRecord.

        Converts raw API dict with {"results": [{"t": timestamp, "p": price, "s": size, ...}, ...]}
        to list of TimeAndSalesRecord dataclasses.

        Args:
            raw_response: Raw API response dict from Polygon.io

        Returns:
            List of TimeAndSalesRecord sorted by timestamp

        Raises:
            DataValidationError: If response is malformed or validation fails
        """
        # TODO: T019 - Implement normalization logic
        # Extract: results array
        # Convert: t (unix ns) → datetime UTC, p → Decimal, s → int
        # Infer: side ("buy" or "sell") from conditions array
        raise NotImplementedError("T019: _normalize_tape_response() not yet implemented")

    def _handle_rate_limit(self, retry_after_seconds: int) -> None:
        """
        Handle HTTP 429 rate limit response.

        Logs rate limit event and sleeps for Retry-After duration.
        Used by @with_retry decorator rate limit callback.

        Args:
            retry_after_seconds: Seconds to wait before retry (from Retry-After header)
        """
        _logger.warning(
            "Polygon.io rate limit hit",
            extra={
                "retry_after_seconds": retry_after_seconds,
                "data_source": self.config.data_source,
            },
        )
