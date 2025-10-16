"""Tests for PullbackAnalyzer component.

Tests cover:
- Swing low detection with confirmation candles
- Fallback to default % when no pullback detected
- Edge cases (multiple swing lows, volatile data)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.trading_bot.risk_management.models import PullbackData
from src.trading_bot.risk_management.pullback_analyzer import PullbackAnalyzer


class TestPullbackAnalyzer:
    """Test suite for PullbackAnalyzer pullback detection logic."""

    def test_identify_swing_low_with_confirmation(self) -> None:
        """Test swing low detection with 2+ confirming candles.

        Scenario (from spec.md FR-014 and tasks.md T008):
        - Given: Price data with swing low at $248.00, confirmed by 2 higher lows
        - When: analyze_pullback(price_data, lookback_candles=20)
        - Then: Returns PullbackData with:
            - pullback_price=$248.00
            - confirmation_candles=2
            - fallback_used=False

        Test data structure:
        - 20 candles showing swing low pattern
        - Candle at index 10: low=$248.00 (swing low)
        - Candles 11-12: higher lows (confirmation)
        - Current price: $250.30
        """
        # Arrange: Create price data with clear swing low at $248.00
        price_data = [
            # Earlier candles (index 0-9) - downtrend leading to swing low
            {"timestamp": datetime(2025, 10, 15, 9, 30, tzinfo=UTC), "low": Decimal("252.00"), "close": Decimal("251.50")},
            {"timestamp": datetime(2025, 10, 15, 9, 35, tzinfo=UTC), "low": Decimal("251.00"), "close": Decimal("250.50")},
            {"timestamp": datetime(2025, 10, 15, 9, 40, tzinfo=UTC), "low": Decimal("250.00"), "close": Decimal("249.50")},
            {"timestamp": datetime(2025, 10, 15, 9, 45, tzinfo=UTC), "low": Decimal("249.50"), "close": Decimal("249.00")},
            {"timestamp": datetime(2025, 10, 15, 9, 50, tzinfo=UTC), "low": Decimal("249.00"), "close": Decimal("248.50")},
            {"timestamp": datetime(2025, 10, 15, 9, 55, tzinfo=UTC), "low": Decimal("248.50"), "close": Decimal("248.20")},
            {"timestamp": datetime(2025, 10, 15, 10, 0, tzinfo=UTC), "low": Decimal("248.20"), "close": Decimal("248.10")},
            {"timestamp": datetime(2025, 10, 15, 10, 5, tzinfo=UTC), "low": Decimal("248.10"), "close": Decimal("248.00")},
            {"timestamp": datetime(2025, 10, 15, 10, 10, tzinfo=UTC), "low": Decimal("248.05"), "close": Decimal("248.00")},
            {"timestamp": datetime(2025, 10, 15, 10, 15, tzinfo=UTC), "low": Decimal("248.00"), "close": Decimal("248.00")},
            # SWING LOW: Index 10 - lowest point
            {"timestamp": datetime(2025, 10, 15, 10, 20, tzinfo=UTC), "low": Decimal("248.00"), "close": Decimal("248.10")},
            # Confirmation candles (index 11-12) - higher lows after swing low
            {"timestamp": datetime(2025, 10, 15, 10, 25, tzinfo=UTC), "low": Decimal("248.20"), "close": Decimal("248.50")},
            {"timestamp": datetime(2025, 10, 15, 10, 30, tzinfo=UTC), "low": Decimal("248.50"), "close": Decimal("249.00")},
            # Recovery (index 13-19) - continued uptrend
            {"timestamp": datetime(2025, 10, 15, 10, 35, tzinfo=UTC), "low": Decimal("249.00"), "close": Decimal("249.50")},
            {"timestamp": datetime(2025, 10, 15, 10, 40, tzinfo=UTC), "low": Decimal("249.50"), "close": Decimal("250.00")},
            {"timestamp": datetime(2025, 10, 15, 10, 45, tzinfo=UTC), "low": Decimal("249.80"), "close": Decimal("250.20")},
            {"timestamp": datetime(2025, 10, 15, 10, 50, tzinfo=UTC), "low": Decimal("250.00"), "close": Decimal("250.30")},
            {"timestamp": datetime(2025, 10, 15, 10, 55, tzinfo=UTC), "low": Decimal("250.20"), "close": Decimal("250.50")},
            {"timestamp": datetime(2025, 10, 15, 11, 0, tzinfo=UTC), "low": Decimal("250.30"), "close": Decimal("250.60")},
            {"timestamp": datetime(2025, 10, 15, 11, 5, tzinfo=UTC), "low": Decimal("250.40"), "close": Decimal("250.30")},
        ]

        analyzer = PullbackAnalyzer()

        # Act: Call analyze_pullback with lookback window of 20 candles
        result = analyzer.analyze_pullback(
            price_data=price_data,
            lookback_candles=20,
            default_stop_pct=2.0,
            entry_price=Decimal("250.30"),
        )

        # Assert: Verify swing low detected correctly
        assert isinstance(result, PullbackData), "Should return PullbackData instance"
        assert result.pullback_price == Decimal("248.00"), "Should identify swing low at $248.00"
        assert result.confirmation_candles >= 2, "Should have at least 2 confirmation candles"
        assert result.lookback_window == 20, "Should use specified lookback window"
        assert result.fallback_used is False, "Should NOT use fallback when swing low detected"
        assert result.pullback_timestamp == datetime(2025, 10, 15, 10, 20, tzinfo=UTC), (
            "Should capture timestamp of swing low candle"
        )

    def test_fallback_to_default_when_no_pullback(self) -> None:
        """Fallback to default % stop when no swing low detected.

        Scenario: Strong uptrend with no pullback in 20 candles
        Given: Price data with continuous upward movement (no swing low)
        When: analyze_pullback() is called with default_stop_pct=2.0
        Then: Returns PullbackData with:
            - pullback_price = $147.00 (2% below entry of $150.00)
            - fallback_used = True
            - confirmation_candles = 0 (no swing low detected)
            - lookback_window = 20

        References:
        - spec.md FR-002: Fallback to percentage-based stop
        - tasks.md T009: Test fallback behavior
        """
        # Arrange: Create strong uptrend price data (no pullback)
        base_timestamp = datetime.now(UTC)
        entry_price = Decimal("150.00")
        default_stop_pct = 2.0
        lookback_candles = 20

        # Strong uptrend: each candle higher than previous (no swing low)
        price_data = []
        base_price = 145.00  # Start below entry
        for i in range(lookback_candles):
            timestamp = base_timestamp - timedelta(minutes=(lookback_candles - i))
            price = base_price + (i * 0.25)  # +$0.25 per candle = consistent uptrend
            price_data.append({
                "timestamp": timestamp,
                "open": price,
                "high": price + 0.10,
                "low": price - 0.05,
                "close": price + 0.05,
            })

        analyzer = PullbackAnalyzer()

        # Act: Analyze pullback with fallback enabled
        result = analyzer.analyze_pullback(
            price_data=price_data,
            entry_price=entry_price,
            default_stop_pct=default_stop_pct,
            lookback_candles=lookback_candles,
        )

        # Assert: Fallback to default percentage-based stop
        expected_pullback_price = entry_price * Decimal("0.98")  # 2% below entry
        assert result.pullback_price == expected_pullback_price
        assert result.fallback_used is True
        assert result.confirmation_candles == 0  # No swing low detected
        assert result.lookback_window == lookback_candles

        # Timestamp should be recent (not from historical data)
        time_delta = datetime.now(UTC) - result.pullback_timestamp
        assert time_delta.total_seconds() < 5  # Generated in last 5 seconds
