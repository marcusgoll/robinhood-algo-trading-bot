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
        alerts = []

        # Scan bids for large orders
        for price_level, order_size in snapshot.bids:
            if order_size >= self.config.large_order_size_threshold:
                # Calculate severity
                severity = self._calculate_alert_severity(order_size)

                # Create alert
                alert = OrderFlowAlert(
                    symbol=snapshot.symbol,
                    alert_type="large_seller",
                    severity=severity,
                    order_size=order_size,
                    price_level=price_level,
                    volume_ratio=None,  # Not applicable for large_seller
                    timestamp_utc=snapshot.timestamp_utc
                )

                alerts.append(alert)

                # Append to alert_history for exit signal evaluation
                self.alert_history.append(alert)

                # Log alert event
                _logger.warning(
                    "Large seller detected",
                    extra={
                        "symbol": snapshot.symbol,
                        "order_size": order_size,
                        "price_level": str(price_level),
                        "severity": severity,
                        "alert_type": "large_seller"
                    }
                )

        return alerts

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
        from datetime import timedelta, UTC

        # Get current time
        now = datetime.now(UTC)

        # Calculate window start time
        window_start = now - timedelta(seconds=self.config.alert_window_seconds)

        # Filter alert_history for large_seller alerts within window
        recent_large_seller_alerts = [
            alert for alert in self.alert_history
            if alert.alert_type == "large_seller" and alert.timestamp_utc >= window_start
        ]

        # Count alerts in window
        alert_count = len(recent_large_seller_alerts)

        # Return True if 3+ alerts
        should_exit = alert_count >= 3

        if should_exit:
            _logger.critical(
                "Exit signal triggered",
                extra={
                    "alert_count": alert_count,
                    "window_seconds": self.config.alert_window_seconds,
                    "trigger_threshold": 3
                }
            )

        return should_exit

    def publish_alert_to_risk_management(self, alert: OrderFlowAlert) -> None:
        """
        Publish OrderFlowAlert to risk management module (T027).

        In production, this would integrate with RiskManager to trigger exits.
        For MVP, this logs the alert with structured logging for audit trail.

        Args:
            alert: OrderFlowAlert to publish

        Example:
            >>> alert = OrderFlowAlert(...)
            >>> detector.publish_alert_to_risk_management(alert)
        """
        # Log alert for risk management consumption
        _logger.critical(
            "Order flow alert published to risk management",
            extra={
                "symbol": alert.symbol,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "order_size": alert.order_size,
                "price_level": str(alert.price_level) if alert.price_level else None,
                "volume_ratio": alert.volume_ratio,
                "timestamp_utc": alert.timestamp_utc.isoformat(),
                "exit_signal": self.should_trigger_exit()
            }
        )

        # TODO: T027 - In production, integrate with RiskManager
        # Example:
        # from trading_bot.risk_management import RiskManager
        # risk_manager = RiskManager()
        # risk_manager.process_order_flow_alert(alert)

    def monitor_active_positions(self, symbols: list[str]) -> dict[str, list[OrderFlowAlert]]:
        """
        Monitor order flow for active positions only (T028).

        Fetches Level 2 data and detects large sellers for symbols with active positions.
        Reduces API costs by monitoring only positions_only mode (FR-013).

        Args:
            symbols: List of ticker symbols with active positions

        Returns:
            Dictionary mapping symbol to list of OrderFlowAlert

        Example:
            >>> active_symbols = ["AAPL", "TSLA", "NVDA"]
            >>> alerts_by_symbol = detector.monitor_active_positions(active_symbols)
            >>> for symbol, alerts in alerts_by_symbol.items():
            ...     if alerts:
            ...         print(f"{symbol}: {len(alerts)} alerts")
        """
        alerts_by_symbol = {}

        for symbol in symbols:
            try:
                # Fetch Level 2 snapshot
                snapshot = self.fetch_level2_snapshot(symbol)

                # Detect large sellers
                alerts = self.detect_large_sellers(snapshot)

                # Store alerts
                alerts_by_symbol[symbol] = alerts

                # Publish alerts to risk management
                for alert in alerts:
                    self.publish_alert_to_risk_management(alert)

            except Exception as e:
                # Log error and continue monitoring other symbols
                _logger.error(
                    f"Error monitoring order flow for {symbol}",
                    extra={"symbol": symbol, "error": str(e)}
                )
                alerts_by_symbol[symbol] = []

        return alerts_by_symbol

    def _calculate_alert_severity(self, order_size: int) -> str:
        """
        Calculate alert severity based on order size.

        Args:
            order_size: Size of large order in shares

        Returns:
            "warning" or "critical"
        """
        # Critical if order_size >= 2x threshold
        threshold = self.config.large_order_size_threshold
        return "critical" if order_size >= (threshold * 2) else "warning"
