"""
Order Flow Detector

Analyzes Level 2 order book for large seller alerts and exit signals.

Pattern: Follows CatalystDetector pattern from momentum/catalyst_detector.py
"""

from collections import deque
from datetime import datetime

from trading_bot.logger import TradingLogger

from .config import OrderFlowConfig
from .data_models import OrderFlowAlert, OrderBookSnapshot
from .polygon_client import PolygonClient

# Get logger
_logger = TradingLogger.get_logger(__name__)


class OrderFlowDetector:
    """
    Detects large seller orders in Level 2 order book.

    Monitors order book depth for institutional selling pressure and generates
    alerts when large orders appear at or below bid price.

    Attributes:
        config: OrderFlowConfig with thresholds
        client: PolygonClient for API access
        alert_history: Bounded deque of recent alerts (for exit signal evaluation)

    Example:
        >>> config = OrderFlowConfig.from_env()
        >>> detector = OrderFlowDetector(config)
        >>> snapshot = detector.fetch_level2_snapshot("AAPL")
        >>> alerts = detector.detect_large_sellers(snapshot)
    """

    def __init__(self, config: OrderFlowConfig) -> None:
        """Initialize OrderFlowDetector with configuration."""
        self.config = config
        self.client = PolygonClient(config)
        # Alert history for exit signal evaluation (last 100 alerts)
        self.alert_history: deque[OrderFlowAlert] = deque(maxlen=100)
        _logger.info("OrderFlowDetector initialized")

    def fetch_level2_snapshot(self, symbol: str) -> OrderBookSnapshot:
        """
        Fetch Level 2 order book snapshot from Polygon.io API.

        Wrapper around PolygonClient.get_level2_snapshot() with logging.

        Args:
            symbol: Stock ticker symbol

        Returns:
            OrderBookSnapshot with validated data
        """
        # TODO: T011 - Implement after PolygonClient.get_level2_snapshot()
        return self.client.get_level2_snapshot(symbol)

    def detect_large_sellers(self, snapshot: OrderBookSnapshot) -> list[OrderFlowAlert]:
        """
        Detect large seller orders in Level 2 order book.

        Scans bid orders for sizes exceeding large_order_size_threshold.
        Creates OrderFlowAlert for each large seller detected.

        Args:
            snapshot: OrderBookSnapshot with bid/ask depth

        Returns:
            List of OrderFlowAlert (empty if no large sellers detected)

        Example:
            >>> alerts = detector.detect_large_sellers(snapshot)
            >>> for alert in alerts:
            ...     print(f"{alert.symbol}: {alert.order_size} shares at ${alert.price_level}")
        """
        # TODO: T014 - Implement large seller detection logic
        # Algorithm:
        # 1. Scan snapshot.bids for orders where size > config.large_order_size_threshold
        # 2. For each large order, create OrderFlowAlert with:
        #    - alert_type="large_seller"
        #    - severity="warning" (or "critical" if order_size > 2x threshold)
        #    - order_size, price_level, timestamp_utc
        # 3. Append to alert_history
        # 4. Log alert event
        raise NotImplementedError("T014: detect_large_sellers() not yet implemented")

    def should_trigger_exit(self) -> bool:
        """
        Evaluate whether to trigger exit signal based on alert history.

        Exit signal triggered when: 3+ large_seller alerts within alert_window_seconds.

        Returns:
            True if exit signal should be triggered, False otherwise

        Example:
            >>> if detector.should_trigger_exit():
            ...     print("EXIT SIGNAL: Multiple large sellers detected")
        """
        # TODO: T026 - Implement exit signal logic
        # Algorithm:
        # 1. Filter alert_history for large_seller alerts within alert_window_seconds
        # 2. Count alerts in window
        # 3. Return True if count >= 3, False otherwise
        raise NotImplementedError("T026: should_trigger_exit() not yet implemented")

    def _calculate_alert_severity(self, order_size: int) -> str:
        """
        Calculate alert severity based on order size.

        Args:
            order_size: Size of large order in shares

        Returns:
            "warning" or "critical"
        """
        # Critical if order_size > 2x threshold
        threshold = self.config.large_order_size_threshold
        return "critical" if order_size > (threshold * 2) else "warning"
