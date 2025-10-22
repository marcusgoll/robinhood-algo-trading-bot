"""
Unit tests for OrderFlowDetector large seller detection and exit signals.

Tests:
- T010: OrderFlowDetector detects large sellers in Level 2 order book
- T024: OrderFlowDetector.should_trigger_exit() logic (3+ alerts in window)
- T025: Exit signal for red burst >400%

Feature: level-2-order-flow-i
Task: T010, T024, T025 [RED] - Write tests for OrderFlowDetector
"""

import pytest
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from unittest.mock import Mock, patch

from src.trading_bot.order_flow.config import OrderFlowConfig
from src.trading_bot.order_flow.order_flow_detector import OrderFlowDetector
from src.trading_bot.order_flow.data_models import OrderFlowAlert, OrderBookSnapshot


class TestOrderFlowDetectorLargeSellerDetection:
    """Test suite for OrderFlowDetector.detect_large_sellers() method."""

    def test_detect_large_sellers_with_10k_bid_order_creates_warning_alert(self):
        """Test that detect_large_sellers() creates warning alert for order exactly at threshold."""
        # Given: OrderFlowDetector with default config (10k threshold)
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            large_order_size_threshold=10_000
        )
        detector = OrderFlowDetector(config)

        # Given: OrderBookSnapshot with 10k bid order at $175.50
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[
                (Decimal("175.50"), 10_000),  # Exactly at threshold
                (Decimal("175.49"), 5_000)
            ],
            asks=[
                (Decimal("175.51"), 3_000)
            ],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Detecting large sellers
        alerts = detector.detect_large_sellers(snapshot)

        # Then: Should generate 1 alert with warning severity
        assert len(alerts) == 1
        alert = alerts[0]
        assert isinstance(alert, OrderFlowAlert)
        assert alert.symbol == "AAPL"
        assert alert.alert_type == "large_seller"
        assert alert.severity == "warning"
        assert alert.order_size == 10_000
        assert alert.price_level == Decimal("175.50")
        assert alert.volume_ratio is None  # Not applicable for large_seller

    def test_detect_large_sellers_with_20k_bid_order_creates_critical_alert(self):
        """Test that detect_large_sellers() creates critical alert for order >2x threshold."""
        # Given: OrderFlowDetector with default config (10k threshold)
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            large_order_size_threshold=10_000
        )
        detector = OrderFlowDetector(config)

        # Given: OrderBookSnapshot with 20k bid order (2x threshold)
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[
                (Decimal("175.50"), 20_000),  # 2x threshold = critical
                (Decimal("175.49"), 5_000)
            ],
            asks=[
                (Decimal("175.51"), 3_000)
            ],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Detecting large sellers
        alerts = detector.detect_large_sellers(snapshot)

        # Then: Should generate 1 critical alert
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.severity == "critical"
        assert alert.order_size == 20_000

    def test_detect_large_sellers_with_multiple_large_orders_creates_multiple_alerts(self):
        """Test that detect_large_sellers() creates separate alerts for each large order."""
        # Given: OrderFlowDetector with default config (10k threshold)
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            large_order_size_threshold=10_000
        )
        detector = OrderFlowDetector(config)

        # Given: OrderBookSnapshot with 3 large bid orders
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[
                (Decimal("175.50"), 15_000),  # Large order 1
                (Decimal("175.49"), 12_000),  # Large order 2
                (Decimal("175.48"), 3_000),   # Small order (ignored)
                (Decimal("175.47"), 18_000)   # Large order 3
            ],
            asks=[
                (Decimal("175.51"), 3_000)
            ],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Detecting large sellers
        alerts = detector.detect_large_sellers(snapshot)

        # Then: Should generate 3 alerts (one per large order)
        assert len(alerts) == 3
        assert all(alert.alert_type == "large_seller" for alert in alerts)
        assert alerts[0].order_size == 15_000
        assert alerts[1].order_size == 12_000
        assert alerts[2].order_size == 18_000

    def test_detect_large_sellers_with_no_large_orders_returns_empty_list(self):
        """Test that detect_large_sellers() returns empty list when no large orders detected."""
        # Given: OrderFlowDetector with default config (10k threshold)
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            large_order_size_threshold=10_000
        )
        detector = OrderFlowDetector(config)

        # Given: OrderBookSnapshot with only small bid orders
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[
                (Decimal("175.50"), 5_000),   # <10k
                (Decimal("175.49"), 3_000),   # <10k
                (Decimal("175.48"), 8_000)    # <10k
            ],
            asks=[
                (Decimal("175.51"), 3_000)
            ],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Detecting large sellers
        alerts = detector.detect_large_sellers(snapshot)

        # Then: Should return empty list
        assert len(alerts) == 0

    def test_detect_large_sellers_appends_alerts_to_alert_history(self):
        """Test that detect_large_sellers() appends alerts to alert_history for exit evaluation."""
        # Given: OrderFlowDetector with default config
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            large_order_size_threshold=10_000
        )
        detector = OrderFlowDetector(config)
        initial_history_len = len(detector.alert_history)

        # Given: OrderBookSnapshot with large bid order
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[(Decimal("175.50"), 15_000)],
            asks=[(Decimal("175.51"), 3_000)],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Detecting large sellers
        alerts = detector.detect_large_sellers(snapshot)

        # Then: alert_history should grow by 1
        assert len(detector.alert_history) == initial_history_len + 1
        assert detector.alert_history[-1] == alerts[0]


class TestOrderFlowDetectorExitSignals:
    """Test suite for OrderFlowDetector.should_trigger_exit() method."""

    def test_should_trigger_exit_with_3_alerts_within_window_returns_true(self):
        """Test that should_trigger_exit() returns True when 3+ large_seller alerts in window."""
        # Given: OrderFlowDetector with 120-second alert window
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            alert_window_seconds=120
        )
        detector = OrderFlowDetector(config)

        # Given: 3 large_seller alerts within 2-minute window
        now = datetime.now(UTC)
        alert1 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="warning",
            order_size=10_000,
            price_level=Decimal("175.50"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=30)  # 30 seconds ago
        )
        alert2 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="warning",
            order_size=12_000,
            price_level=Decimal("175.49"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=60)  # 60 seconds ago
        )
        alert3 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="critical",
            order_size=20_000,
            price_level=Decimal("175.48"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=90)  # 90 seconds ago
        )
        detector.alert_history.extend([alert1, alert2, alert3])

        # When: Evaluating exit signal
        result = detector.should_trigger_exit()

        # Then: Should return True (3 alerts within 120-second window)
        assert result is True

    def test_should_trigger_exit_with_2_alerts_within_window_returns_false(self):
        """Test that should_trigger_exit() returns False when only 2 alerts in window."""
        # Given: OrderFlowDetector with 120-second alert window
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            alert_window_seconds=120
        )
        detector = OrderFlowDetector(config)

        # Given: Only 2 large_seller alerts within window
        now = datetime.now(UTC)
        alert1 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="warning",
            order_size=10_000,
            price_level=Decimal("175.50"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=30)
        )
        alert2 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="warning",
            order_size=12_000,
            price_level=Decimal("175.49"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=60)
        )
        detector.alert_history.extend([alert1, alert2])

        # When: Evaluating exit signal
        result = detector.should_trigger_exit()

        # Then: Should return False (only 2 alerts, need 3+)
        assert result is False

    def test_should_trigger_exit_ignores_alerts_outside_window(self):
        """Test that should_trigger_exit() ignores alerts older than alert_window_seconds."""
        # Given: OrderFlowDetector with 120-second alert window
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            alert_window_seconds=120
        )
        detector = OrderFlowDetector(config)

        # Given: 3 alerts, but 1 is outside window
        now = datetime.now(UTC)
        alert1 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="warning",
            order_size=10_000,
            price_level=Decimal("175.50"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=30)   # Within window
        )
        alert2 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="warning",
            order_size=12_000,
            price_level=Decimal("175.49"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=60)   # Within window
        )
        alert3 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="critical",
            order_size=20_000,
            price_level=Decimal("175.48"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=150)  # Outside window (150s > 120s)
        )
        detector.alert_history.extend([alert1, alert2, alert3])

        # When: Evaluating exit signal
        result = detector.should_trigger_exit()

        # Then: Should return False (only 2 alerts within window)
        assert result is False

    def test_should_trigger_exit_with_empty_alert_history_returns_false(self):
        """Test that should_trigger_exit() returns False when alert_history is empty."""
        # Given: OrderFlowDetector with empty alert_history
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            alert_window_seconds=120
        )
        detector = OrderFlowDetector(config)
        assert len(detector.alert_history) == 0

        # When: Evaluating exit signal
        result = detector.should_trigger_exit()

        # Then: Should return False
        assert result is False

    def test_should_trigger_exit_ignores_red_burst_alerts(self):
        """Test that should_trigger_exit() only counts large_seller alerts, not red_burst."""
        # Given: OrderFlowDetector with 120-second alert window
        config = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            alert_window_seconds=120
        )
        detector = OrderFlowDetector(config)

        # Given: 2 large_seller alerts + 1 red_burst alert
        now = datetime.now(UTC)
        alert1 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="warning",
            order_size=10_000,
            price_level=Decimal("175.50"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=30)
        )
        alert2 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="large_seller",
            severity="warning",
            order_size=12_000,
            price_level=Decimal("175.49"),
            volume_ratio=None,
            timestamp_utc=now - timedelta(seconds=60)
        )
        alert3 = OrderFlowAlert(
            symbol="AAPL",
            alert_type="red_burst",  # Different type (should be ignored)
            severity="critical",
            order_size=None,
            price_level=None,
            volume_ratio=5.0,
            timestamp_utc=now - timedelta(seconds=90)
        )
        detector.alert_history.extend([alert1, alert2, alert3])

        # When: Evaluating exit signal
        result = detector.should_trigger_exit()

        # Then: Should return False (only 2 large_seller alerts, red_burst ignored)
        assert result is False


class TestOrderFlowDetectorIntegration:
    """Integration tests for OrderFlowDetector with direct snapshot testing."""

    def test_full_workflow_detect_and_trigger_exit(self):
        """Test full workflow: create snapshot → detect large sellers → trigger exit."""
        # Given: OrderFlowDetector
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        detector = OrderFlowDetector(config)

        # Given: Create Level 2 snapshot with large seller
        from datetime import UTC
        mock_snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[(Decimal("175.50"), 15000)],  # Large seller (>10k threshold)
            asks=[(Decimal("175.51"), 3000)],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Detecting large sellers 3 times (to trigger exit)
        for _ in range(3):
            alerts = detector.detect_large_sellers(mock_snapshot)
            assert len(alerts) == 1

        # Then: Should trigger exit signal (3+ alerts within window)
        should_exit = detector.should_trigger_exit()
        assert should_exit is True

    def test_detect_large_sellers_with_small_orders(self):
        """Test that detect_large_sellers() returns no alerts for small orders."""
        # Given: OrderFlowDetector
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        detector = OrderFlowDetector(config)

        # Given: Create Level 2 snapshot with small orders
        from datetime import UTC
        mock_snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[(Decimal("175.50"), 5000)],  # Below threshold (10k)
            asks=[(Decimal("175.51"), 3000)],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Detecting large sellers
        alerts = detector.detect_large_sellers(mock_snapshot)

        # Then: Should return no alerts (size below threshold)
        assert len(alerts) == 0

    def test_detect_large_sellers_adds_alerts_to_history(self):
        """Test that detected alerts are added to alert_history deque."""
        # Given: OrderFlowDetector
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        detector = OrderFlowDetector(config)

        # Given: Create Level 2 snapshot with large seller
        from datetime import UTC
        mock_snapshot = OrderBookSnapshot(
            symbol="AAPL",
            bids=[(Decimal("175.50"), 20000)],  # Large seller
            asks=[(Decimal("175.51"), 3000)],
            timestamp_utc=datetime.now(UTC)
        )

        # When: Detecting large sellers
        initial_history_len = len(detector.alert_history)
        alerts = detector.detect_large_sellers(mock_snapshot)

        # Then: Should add alert to history
        assert len(detector.alert_history) == initial_history_len + 1
        assert detector.alert_history[-1].symbol == "AAPL"
        assert detector.alert_history[-1].alert_type == "large_seller"

    @patch('requests.get')
    def test_health_check_returns_status(self, mock_get):
        """Test that health_check() returns API connectivity status."""
        # Given: OrderFlowDetector
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        detector = OrderFlowDetector(config)

        # Given: Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # When: Running health check
        status = detector.health_check()

        # Then: Should return health status dict
        assert status["status"] == "ok"
        assert status["dependencies"]["polygon_api"] == "ok"
        assert "timestamp_utc" in status
        assert "last_alert_count" in status
        assert status["last_alert_count"] == 0  # No alerts added yet

        # Then: Should have called Polygon API for health check
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "polygon.io" in call_args[0][0].lower()  # URL contains polygon.io

    @patch('requests.get')
    def test_health_check_handles_api_timeout(self, mock_get):
        """Test that health_check() handles API timeout gracefully."""
        # Given: OrderFlowDetector
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        detector = OrderFlowDetector(config)

        # Given: Mock timeout exception
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        # When: Running health check
        status = detector.health_check()

        # Then: Should return degraded status
        assert status["status"] == "degraded"
        assert status["dependencies"]["polygon_api"] == "timeout"

    @patch('requests.get')
    def test_health_check_handles_rate_limit(self, mock_get):
        """Test that health_check() detects rate limiting."""
        # Given: OrderFlowDetector
        config = OrderFlowConfig(polygon_api_key="test_key_1234567890")
        detector = OrderFlowDetector(config)

        # Given: Mock rate limit response (429)
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        # When: Running health check
        status = detector.health_check()

        # Then: Should detect rate limiting
        assert status["status"] == "ok"  # Status OK but dependency rate limited
        assert status["dependencies"]["polygon_api"] == "rate_limited"
