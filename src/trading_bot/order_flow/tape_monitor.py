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
        # TODO: T021 - Implement rolling average calculation
        # Algorithm:
        # 1. Sum size from all trades in tape_buffer
        # 2. Divide by time span (5 minutes)
        # 3. Return average volume per minute
        raise NotImplementedError("T021: calculate_rolling_average() not yet implemented")

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
        # TODO: T022 - Implement red burst detection logic
        # Algorithm:
        # 1. Calculate current period volume
        # 2. Get rolling average from calculate_rolling_average()
        # 3. Calculate volume_ratio = current / average
        # 4. Calculate sell_ratio = sell_volume / total_volume
        # 5. If volume_ratio > volume_spike_threshold AND sell_ratio > 0.60:
        #    - Create OrderFlowAlert with alert_type="red_burst"
        #    - severity="warning" if volume_ratio > 3.0x
        #    - severity="critical" if volume_ratio > red_burst_threshold (4.0x)
        # 6. Log alert event
        raise NotImplementedError("T022: detect_red_burst() not yet implemented")

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
