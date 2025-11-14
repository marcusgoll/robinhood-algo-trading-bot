"""
Tape Monitor

Monitors Time & Sales tape for volume spikes and red burst patterns.

Pattern: Follows detector pattern with rolling window analysis
"""

from collections import deque
from datetime import datetime, timedelta

from trading_bot.logger import TradingLogger

from .config import OrderFlowConfig
from .data_models import OrderFlowAlert, TimeAndSalesRecord
from .polygon_client import PolygonClient

# Get logger
_logger = TradingLogger.get_logger(__name__)


class TapeMonitor:
    """
    Monitors Time & Sales tape for volume spikes and red burst patterns.

    Tracks 5-minute rolling average volume and detects spikes >300% with >60% sell-side.

    Attributes:
        config: OrderFlowConfig with thresholds
        client: PolygonClient for API access
        tape_buffer: Bounded deque of recent trades (5-minute window)
        volume_history: Bounded deque of volume averages (for spike detection)

    Example:
        >>> config = OrderFlowConfig.from_env()
        >>> monitor = TapeMonitor(config)
        >>> trades = monitor.fetch_tape_data("AAPL")
        >>> alerts = monitor.detect_red_burst(trades)
    """

    def __init__(self, config: OrderFlowConfig) -> None:
        """Initialize TapeMonitor with configuration."""
        self.config = config
        self.client = PolygonClient(config)
        # 5-minute rolling window (maxlen calculated based on typical trade frequency)
        self.tape_buffer: deque[TimeAndSalesRecord] = deque(maxlen=5000)
        # Volume history for baseline calculation (last 60 minutes = 12 x 5-min buckets)
        self.volume_history: deque[float] = deque(maxlen=12)
        _logger.info("TapeMonitor initialized")

    def fetch_tape_data(
        self, symbol: str, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> list[TimeAndSalesRecord]:
        """
        Fetch Time & Sales tape data from Polygon.io API.

        Wrapper around PolygonClient.get_time_and_sales() with default time range.

        Args:
            symbol: Stock ticker symbol
            start_time: Start of time window (default: 5 minutes ago)
            end_time: End of time window (default: now)

        Returns:
            List of TimeAndSalesRecord sorted by timestamp
        """
        # TODO: T018 - Implement after PolygonClient.get_time_and_sales()
        from datetime import UTC
        end_time = end_time or datetime.now(UTC)
        start_time = start_time or (end_time - timedelta(minutes=5))
        return self.client.get_time_and_sales(symbol, start_time, end_time)

    def calculate_rolling_average(self) -> float:
        """
        Calculate 5-minute rolling average volume from tape_buffer.

        Returns:
            Average volume per minute over last 5 minutes

        Example:
            >>> monitor.tape_buffer.extend(trades)
            >>> avg_volume = monitor.calculate_rolling_average()
            >>> print(f"Average: {avg_volume:.0f} shares/min")
        """
        if not self.tape_buffer:
            return 0.0

        # Sum total volume from all trades in buffer
        total_volume = sum(trade.size for trade in self.tape_buffer)

        # Calculate time span between oldest and newest trades (in minutes)
        if len(self.tape_buffer) == 1:
            # Single trade: Treat as 1-minute worth of data
            return float(total_volume)

        oldest_trade = self.tape_buffer[0]
        newest_trade = self.tape_buffer[-1]
        time_span_seconds = (newest_trade.timestamp_utc - oldest_trade.timestamp_utc).total_seconds()

        # Convert to minutes (add 1 to include both endpoints)
        # Example: If trades are at minute 0 and minute 4, that's 5 minutes of data (0,1,2,3,4)
        time_span_minutes = (time_span_seconds / 60.0) + 1.0

        # Avoid division by zero
        if time_span_minutes <= 0.0:
            return float(total_volume)

        # Calculate average volume per minute
        avg_volume_per_minute = total_volume / time_span_minutes

        return avg_volume_per_minute

    def detect_red_burst(self, trades: list[TimeAndSalesRecord]) -> list[OrderFlowAlert]:
        """
        Detect red burst patterns (volume spike >300% with >60% sells).

        Compares current volume to rolling average and checks sell ratio.

        Args:
            trades: List of TimeAndSalesRecord for current period

        Returns:
            List of OrderFlowAlert (empty if no red burst detected)

        Example:
            >>> alerts = monitor.detect_red_burst(trades)
            >>> for alert in alerts:
            ...     print(f"{alert.symbol}: {alert.volume_ratio:.1f}x volume spike")
        """
        if not trades:
            return []

        # Calculate current period volume
        current_volume = sum(trade.size for trade in trades)

        # Get historical average volume (from volume_history)
        # If volume_history is empty, use tape_buffer for baseline
        if self.volume_history:
            avg_volume = sum(self.volume_history) / len(self.volume_history)
        elif self.tape_buffer:
            avg_volume = self.calculate_rolling_average()
        else:
            avg_volume = 1.0  # Avoid division by zero

        # Calculate volume ratio
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0.0

        # Calculate sell ratio
        sell_ratio = self._calculate_sell_ratio(trades)

        # Update volume_history with current period volume
        self.volume_history.append(float(current_volume))

        # Check for red burst pattern
        if volume_ratio < self.config.volume_spike_threshold:
            # Volume spike not high enough
            return []

        if sell_ratio < 0.60:
            # Sell-side ratio not high enough (not a red burst)
            return []

        # Red burst detected - determine severity
        severity = "warning"
        if volume_ratio >= self.config.red_burst_threshold:
            severity = "critical"

        # Extract symbol from first trade
        symbol = trades[0].symbol

        # Create alert
        alert = OrderFlowAlert(
            symbol=symbol,
            alert_type="red_burst",
            severity=severity,
            order_size=None,  # Not applicable for red burst
            price_level=None,  # Not applicable for red burst
            volume_ratio=volume_ratio,
            timestamp_utc=trades[-1].timestamp_utc  # Use latest trade timestamp
        )

        # Log alert event
        _logger.warning(
            "Red burst detected",
            extra={
                "symbol": symbol,
                "volume_ratio": volume_ratio,
                "sell_ratio": sell_ratio,
                "severity": severity,
                "current_volume": current_volume,
                "avg_volume": avg_volume
            }
        )

        return [alert]

    def _calculate_sell_ratio(self, trades: list[TimeAndSalesRecord]) -> float:
        """
        Calculate sell-side volume ratio.

        Args:
            trades: List of TimeAndSalesRecord

        Returns:
            Ratio of sell volume to total volume (0.0-1.0)
        """
        if not trades:
            return 0.0

        sell_volume = sum(t.size for t in trades if t.side == "sell")
        total_volume = sum(t.size for t in trades)
        return sell_volume / total_volume if total_volume > 0 else 0.0
