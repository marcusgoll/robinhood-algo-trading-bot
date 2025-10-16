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

from src.trading_bot.risk_management.pullback_analyzer import PullbackAnalyzer


class TestPullbackAnalyzer:
    """Test suite for PullbackAnalyzer pullback detection logic."""

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
