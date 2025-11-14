"""
Test suite for TapeMonitor class.

Tests rolling average calculation and red burst detection logic.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest

from trading_bot.order_flow.config import OrderFlowConfig
from trading_bot.order_flow.data_models import OrderFlowAlert, TimeAndSalesRecord
from trading_bot.order_flow.tape_monitor import TapeMonitor


class TestTapeMonitorRollingAverage:
    """Test suite for TapeMonitor.calculate_rolling_average() method."""

    def test_calculate_rolling_average_with_full_5min_window(self):
        """Test calculate_rolling_average() with full 5-minute window of trades."""
        # Given: TapeMonitor with default config
        config = OrderFlowConfig(polygon_api_key="test_key")
        monitor = TapeMonitor(config)

        # Given: 5 minutes of trade data (1000 shares/min = 5000 total)
        base_time = datetime.now(UTC)
        for i in range(5):
            trade = TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=1000,  # 1000 shares per minute
                side="buy",
                timestamp_utc=base_time - timedelta(minutes=4 - i)
            )
            monitor.tape_buffer.append(trade)

        # When: Calculating rolling average
        avg_volume = monitor.calculate_rolling_average()

        # Then: Should return average volume per minute (5000 shares / 5 min = 1000 shares/min)
        assert avg_volume == 1000.0

    def test_calculate_rolling_average_with_empty_buffer(self):
        """Test calculate_rolling_average() returns 0.0 when tape_buffer is empty."""
        # Given: TapeMonitor with empty tape_buffer
        config = OrderFlowConfig(polygon_api_key="test_key")
        monitor = TapeMonitor(config)

        # When: Calculating rolling average with no data
        avg_volume = monitor.calculate_rolling_average()

        # Then: Should return 0.0
        assert avg_volume == 0.0

    def test_calculate_rolling_average_with_partial_window(self):
        """Test calculate_rolling_average() handles partial window (< 5 minutes)."""
        # Given: TapeMonitor with 2 minutes of data
        config = OrderFlowConfig(polygon_api_key="test_key")
        monitor = TapeMonitor(config)

        # Given: Only 2 minutes of trade data (500 shares/min = 1000 total)
        base_time = datetime.now(UTC)
        for i in range(2):
            trade = TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=500,
                side="buy",
                timestamp_utc=base_time - timedelta(minutes=1 - i)
            )
            monitor.tape_buffer.append(trade)

        # When: Calculating rolling average
        avg_volume = monitor.calculate_rolling_average()

        # Then: Should calculate average based on actual time span (1000 / 2 = 500)
        assert avg_volume == 500.0

    def test_calculate_rolling_average_with_uneven_volume(self):
        """Test calculate_rolling_average() handles uneven volume distribution."""
        # Given: TapeMonitor with varying trade sizes
        config = OrderFlowConfig(polygon_api_key="test_key")
        monitor = TapeMonitor(config)

        # Given: Trades with different sizes (100 + 500 + 2000 + 1000 + 1400 = 5000 total)
        base_time = datetime.now(UTC)
        sizes = [100, 500, 2000, 1000, 1400]
        for i, size in enumerate(sizes):
            trade = TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=size,
                side="buy",
                timestamp_utc=base_time - timedelta(minutes=4 - i)
            )
            monitor.tape_buffer.append(trade)

        # When: Calculating rolling average
        avg_volume = monitor.calculate_rolling_average()

        # Then: Should return average (5000 / 5 min = 1000 shares/min)
        assert avg_volume == 1000.0


class TestTapeMonitorRedBurstDetection:
    """Test suite for TapeMonitor.detect_red_burst() method."""

    def test_detect_red_burst_with_400_percent_spike_and_60_percent_sells(self):
        """Test detect_red_burst() creates critical alert for >400% volume spike with >60% sells."""
        # Given: TapeMonitor with baseline volume history
        config = OrderFlowConfig(
            polygon_api_key="test_key",
            volume_spike_threshold=3.0,  # 300%
            red_burst_threshold=4.0      # 400% (critical)
        )
        monitor = TapeMonitor(config)

        # Given: Historical average of 1000 shares/min
        monitor.volume_history.extend([1000.0] * 12)  # 12 x 5-min buckets

        # Given: Current period with 4000 shares (4x spike, 70% sells)
        base_time = datetime.now(UTC)
        current_trades = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=2800,  # 70% of 4000
                side="sell",
                timestamp_utc=base_time
            ),
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.51"),
                size=1200,  # 30% of 4000
                side="buy",
                timestamp_utc=base_time + timedelta(seconds=1)
            )
        ]

        # When: Detecting red burst
        alerts = monitor.detect_red_burst(current_trades)

        # Then: Should return 1 alert
        assert len(alerts) == 1

        # Then: Alert should have correct structure
        alert = alerts[0]
        assert isinstance(alert, OrderFlowAlert)
        assert alert.alert_type == "red_burst"
        assert alert.severity == "critical"  # >400% spike
        assert alert.symbol == "AAPL"
        assert alert.volume_ratio == pytest.approx(4.0, rel=0.1)
        assert alert.order_size is None  # Not applicable for red burst
        assert alert.price_level is None  # Not applicable for red burst

    def test_detect_red_burst_with_300_percent_spike_creates_warning_alert(self):
        """Test detect_red_burst() creates warning alert for 300-400% spike."""
        # Given: TapeMonitor with baseline volume
        config = OrderFlowConfig(
            polygon_api_key="test_key",
            volume_spike_threshold=3.0,
            red_burst_threshold=4.0
        )
        monitor = TapeMonitor(config)
        monitor.volume_history.extend([1000.0] * 12)

        # Given: Current period with 3500 shares (3.5x spike, 65% sells)
        base_time = datetime.now(UTC)
        current_trades = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=2275,  # 65% of 3500
                side="sell",
                timestamp_utc=base_time
            ),
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.51"),
                size=1225,  # 35% of 3500
                side="buy",
                timestamp_utc=base_time + timedelta(seconds=1)
            )
        ]

        # When: Detecting red burst
        alerts = monitor.detect_red_burst(current_trades)

        # Then: Should return warning alert (3.5x < 4.0x)
        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert alerts[0].alert_type == "red_burst"
        assert alerts[0].volume_ratio == pytest.approx(3.5, rel=0.1)

    def test_detect_red_burst_with_high_volume_but_low_sell_ratio_returns_empty(self):
        """Test detect_red_burst() returns empty list when sell ratio <60%."""
        # Given: TapeMonitor with baseline volume
        config = OrderFlowConfig(
            polygon_api_key="test_key",
            volume_spike_threshold=3.0,
            red_burst_threshold=4.0
        )
        monitor = TapeMonitor(config)
        monitor.volume_history.extend([1000.0] * 12)

        # Given: High volume (4x) but only 40% sells (not red burst)
        base_time = datetime.now(UTC)
        current_trades = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=1600,  # 40% sells
                side="sell",
                timestamp_utc=base_time
            ),
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.51"),
                size=2400,  # 60% buys
                side="buy",
                timestamp_utc=base_time + timedelta(seconds=1)
            )
        ]

        # When: Detecting red burst
        alerts = monitor.detect_red_burst(current_trades)

        # Then: Should return empty list (sell ratio <60%)
        assert len(alerts) == 0

    def test_detect_red_burst_with_low_volume_spike_returns_empty(self):
        """Test detect_red_burst() returns empty when volume spike <300%."""
        # Given: TapeMonitor with baseline volume
        config = OrderFlowConfig(
            polygon_api_key="test_key",
            volume_spike_threshold=3.0,
            red_burst_threshold=4.0
        )
        monitor = TapeMonitor(config)
        monitor.volume_history.extend([1000.0] * 12)

        # Given: Normal volume (2x spike, even with high sell ratio)
        base_time = datetime.now(UTC)
        current_trades = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=1400,  # 70% sells
                side="sell",
                timestamp_utc=base_time
            ),
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.51"),
                size=600,  # 30% buys
                side="buy",
                timestamp_utc=base_time + timedelta(seconds=1)
            )
        ]

        # When: Detecting red burst
        alerts = monitor.detect_red_burst(current_trades)

        # Then: Should return empty list (volume spike <300%)
        assert len(alerts) == 0

    def test_detect_red_burst_with_empty_trades_returns_empty(self):
        """Test detect_red_burst() handles empty trade list."""
        # Given: TapeMonitor with baseline volume
        config = OrderFlowConfig(polygon_api_key="test_key")
        monitor = TapeMonitor(config)
        monitor.volume_history.extend([1000.0] * 12)

        # When: Detecting red burst with no trades
        alerts = monitor.detect_red_burst([])

        # Then: Should return empty list
        assert len(alerts) == 0

    def test_detect_red_burst_appends_to_volume_history(self):
        """Test detect_red_burst() updates volume_history with current period volume."""
        # Given: TapeMonitor with partial volume history
        config = OrderFlowConfig(polygon_api_key="test_key")
        monitor = TapeMonitor(config)
        initial_history_length = 5
        monitor.volume_history.extend([1000.0] * initial_history_length)

        # Given: Current period trades
        base_time = datetime.now(UTC)
        current_trades = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=2000,
                side="sell",
                timestamp_utc=base_time
            )
        ]

        # When: Detecting red burst
        monitor.detect_red_burst(current_trades)

        # Then: volume_history should have one more entry
        assert len(monitor.volume_history) == initial_history_length + 1

    def test_detect_red_burst_respects_volume_history_maxlen(self):
        """Test volume_history respects maxlen=12 (bounded deque)."""
        # Given: TapeMonitor with full volume history (12 buckets)
        config = OrderFlowConfig(polygon_api_key="test_key")
        monitor = TapeMonitor(config)
        monitor.volume_history.extend([1000.0] * 12)  # Full history

        # Given: Current period trades
        base_time = datetime.now(UTC)
        current_trades = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=2000,
                side="sell",
                timestamp_utc=base_time
            )
        ]

        # When: Detecting red burst
        monitor.detect_red_burst(current_trades)

        # Then: volume_history should stay at maxlen (oldest evicted)
        assert len(monitor.volume_history) == 12


class TestTapeMonitorExitSignals:
    """Test suite for red burst exit signal generation (US3)."""

    def test_red_burst_alert_with_critical_severity_triggers_exit(self):
        """Test that red burst with >400% volume spike creates critical alert (exit signal)."""
        # Given: TapeMonitor with red burst threshold = 4.0x
        config = OrderFlowConfig(
            polygon_api_key="test_key",
            volume_spike_threshold=3.0,
            red_burst_threshold=4.0
        )
        monitor = TapeMonitor(config)
        monitor.volume_history.extend([1000.0] * 12)

        # Given: Current period with 5000 shares (5x spike, 70% sells)
        base_time = datetime.now(UTC)
        current_trades = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=3500,  # 70% sells
                side="sell",
                timestamp_utc=base_time
            ),
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.51"),
                size=1500,  # 30% buys
                side="buy",
                timestamp_utc=base_time + timedelta(seconds=1)
            )
        ]

        # When: Detecting red burst
        alerts = monitor.detect_red_burst(current_trades)

        # Then: Should return critical alert (exit signal)
        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert alerts[0].alert_type == "red_burst"
        assert alerts[0].volume_ratio >= 4.0  # Exceeds red_burst_threshold

    def test_red_burst_alert_with_warning_severity_does_not_trigger_exit(self):
        """Test that warning-level red burst (300-400%) does NOT trigger immediate exit."""
        # Given: TapeMonitor with thresholds
        config = OrderFlowConfig(
            polygon_api_key="test_key",
            volume_spike_threshold=3.0,
            red_burst_threshold=4.0
        )
        monitor = TapeMonitor(config)
        monitor.volume_history.extend([1000.0] * 12)

        # Given: Current period with 3500 shares (3.5x spike, 65% sells)
        base_time = datetime.now(UTC)
        current_trades = [
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.50"),
                size=2275,  # 65% sells
                side="sell",
                timestamp_utc=base_time
            ),
            TimeAndSalesRecord(
                symbol="AAPL",
                price=Decimal("175.51"),
                size=1225,  # 35% buys
                side="buy",
                timestamp_utc=base_time + timedelta(seconds=1)
            )
        ]

        # When: Detecting red burst
        alerts = monitor.detect_red_burst(current_trades)

        # Then: Should return warning alert (NOT critical - no immediate exit)
        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert alerts[0].volume_ratio < 4.0  # Below red_burst_threshold


class TestTapeMonitorIntegration:
    """Integration tests for TapeMonitor with real Polygon.io API."""

    @pytest.mark.integration
    def test_fetch_tape_data_real_api_call(self):
        """Test fetch_tape_data() with real Polygon.io API (requires POLYGON_API_KEY)."""
        # Given: TapeMonitor with real API key from environment
        import os
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key:
            pytest.skip("POLYGON_API_KEY not set in environment")

        config = OrderFlowConfig(polygon_api_key=api_key)
        monitor = TapeMonitor(config)

        # When: Fetching tape data for AAPL (last 5 minutes)
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=5)
        records = monitor.fetch_tape_data("AAPL", start_time, end_time)

        # Then: Should return list of TimeAndSalesRecord
        assert isinstance(records, list)
        # Note: May be empty if market closed, but should not raise error
        if records:
            assert all(isinstance(r, TimeAndSalesRecord) for r in records)
            assert all(r.symbol == "AAPL" for r in records)
