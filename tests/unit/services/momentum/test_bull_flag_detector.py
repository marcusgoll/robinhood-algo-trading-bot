"""
Unit tests for BullFlagDetector service.

Tests:
- T032: _detect_flag() validates consolidation criteria (3-5% range, 2-5 days, downward/flat slope)
- T033: _calculate_targets() computes breakout price and price target from pole/flag data

Feature: momentum-detection
Task: T032 [RED] - Write test for BullFlagDetector._detect_flag()
Task: T033 [RED] - Write test for BullFlagDetector._calculate_targets()
"""

import pytest
from datetime import datetime, timedelta, UTC
import pandas as pd
from typing import Optional, Tuple

from src.trading_bot.momentum.bull_flag_detector import BullFlagDetector
from src.trading_bot.momentum.config import MomentumConfig
from src.trading_bot.momentum.logging.momentum_logger import MomentumLogger


class TestBullFlagDetectorDetectFlag:
    """Test suite for BullFlagDetector._detect_flag() method."""

    def _create_consolidation_candles(
        self,
        start_date: datetime,
        num_days: int,
        range_pct: float,
        slope_direction: str,
        base_price: float = 100.0,
    ) -> pd.DataFrame:
        """
        Helper to create synthetic OHLCV data for flag pattern testing.

        Args:
            start_date: Starting datetime for candles
            num_days: Number of consolidation days
            range_pct: Price range as percentage (e.g., 4.0 for 4%)
            slope_direction: "downward", "flat", or "upward"
            base_price: Starting price level

        Returns:
            DataFrame with OHLCV data
        """
        candles = []

        # Calculate price range
        flag_low = base_price
        flag_high = base_price * (1 + range_pct / 100)

        for i in range(num_days):
            date = start_date + timedelta(days=i)

            # Calculate open and close based on slope
            if slope_direction == "downward":
                # Gradual downward slope
                open_price = flag_high - (flag_high - flag_low) * (i / num_days) * 0.5
                close_price = flag_high - (flag_high - flag_low) * ((i + 1) / num_days) * 0.6
            elif slope_direction == "flat":
                # Flat consolidation
                open_price = (flag_high + flag_low) / 2
                close_price = (flag_high + flag_low) / 2
            else:  # upward
                # Upward slope (invalid for bull flag)
                open_price = flag_low + (flag_high - flag_low) * (i / num_days) * 0.5
                close_price = flag_low + (flag_high - flag_low) * ((i + 1) / num_days) * 0.6

            # Set high and low within range
            high = max(open_price, close_price) * 1.01
            low = min(open_price, close_price) * 0.99

            candles.append({
                "timestamp": date,
                "open": open_price,
                "high": min(high, flag_high),
                "low": max(low, flag_low),
                "close": close_price,
                "volume": 1_000_000,
            })

        return pd.DataFrame(candles)

    @pytest.mark.parametrize(
        "range_pct,num_days,slope_direction,expected_valid",
        [
            # Test case 1: 4% range, 3 days, downward slope → Valid flag
            (4.0, 3, "downward", True),
            # Test case 2: 6% range, 3 days, downward slope → Invalid (range too wide)
            (6.0, 3, "downward", False),
            # Test case 3: 4% range, 1 day, downward slope → Invalid (duration too short)
            (4.0, 1, "downward", False),
            # Test case 4: 4% range, 6 days, downward slope → Invalid (duration too long)
            (4.0, 6, "downward", False),
            # Test case 5: 4% range, 3 days, upward slope → Invalid (slope wrong direction)
            (4.0, 3, "upward", False),
            # Test case 6: 3.0% range (boundary) → Valid
            (3.0, 3, "downward", True),
            # Test case 7: 5.0% range (boundary) → Valid
            (5.0, 3, "downward", True),
        ],
    )
    def test_detect_flag_validates_consolidation(
        self, range_pct: float, num_days: int, slope_direction: str, expected_valid: bool
    ):
        """
        Test that _detect_flag() validates consolidation criteria correctly.

        Valid flag criteria:
        - Price range: 3-5%
        - Duration: 2-5 days
        - Slope: downward or flat (not upward)
        """
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        # Mock market_data_service (not needed for internal _detect_flag test)
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # Given: Historical OHLCV data with consolidation pattern after pole
        pole_end = datetime(2024, 1, 10, tzinfo=UTC)
        flag_start = pole_end + timedelta(days=1)

        # Create consolidation candles with specified characteristics
        flag_candles = self._create_consolidation_candles(
            start_date=flag_start,
            num_days=num_days,
            range_pct=range_pct,
            slope_direction=slope_direction,
            base_price=100.0,
        )

        # When: _detect_flag() called with pole_end datetime
        result = detector._detect_flag(flag_candles, pole_end)

        # Then: Returns tuple or None based on validity
        if expected_valid:
            assert result is not None, (
                f"Expected valid flag with range={range_pct}%, "
                f"days={num_days}, slope={slope_direction}"
            )

            flag_start_dt, flag_end_dt, flag_high, flag_low, flag_range_pct, flag_slope_pct = result

            # Verify returned values
            assert isinstance(flag_start_dt, datetime)
            assert isinstance(flag_end_dt, datetime)
            assert isinstance(flag_high, float)
            assert isinstance(flag_low, float)
            assert isinstance(flag_range_pct, float)
            assert isinstance(flag_slope_pct, float)

            # Verify flag range is within expected bounds
            assert 2.5 <= flag_range_pct <= 5.5, (
                f"Flag range {flag_range_pct}% outside 3-5% bounds"
            )

            # Verify flag duration
            flag_duration_days = (flag_end_dt - flag_start_dt).days + 1
            assert 2 <= flag_duration_days <= 5, (
                f"Flag duration {flag_duration_days} days outside 2-5 day range"
            )

            # Verify slope direction (should be ≤ 0 for downward/flat)
            if slope_direction in ["downward", "flat"]:
                assert flag_slope_pct <= 0, (
                    f"Expected downward/flat slope, got {flag_slope_pct}%"
                )
        else:
            assert result is None, (
                f"Expected invalid flag with range={range_pct}%, "
                f"days={num_days}, slope={slope_direction}"
            )

    def test_detect_flag_calculates_range_correctly(self):
        """Test that _detect_flag() calculates flag_range_pct correctly."""
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # Given: Flag candles with known high/low
        pole_end = datetime(2024, 1, 10, tzinfo=UTC)
        flag_start = pole_end + timedelta(days=1)

        # Create candles with precise range: low=100, high=104 → 4% range
        candles_data = []
        for i in range(3):
            date = flag_start + timedelta(days=i)
            candles_data.append({
                "timestamp": date,
                "open": 102.0,
                "high": 104.0,
                "low": 100.0,
                "close": 101.0,
                "volume": 1_000_000,
            })

        flag_candles = pd.DataFrame(candles_data)

        # When: _detect_flag() called
        result = detector._detect_flag(flag_candles, pole_end)

        # Then: flag_range_pct should be (104 - 100) / 100 = 4.0%
        assert result is not None
        _, _, flag_high, flag_low, flag_range_pct, _ = result

        assert flag_high == 104.0
        assert flag_low == 100.0
        assert abs(flag_range_pct - 4.0) < 0.01, f"Expected 4.0%, got {flag_range_pct}%"

    def test_detect_flag_calculates_slope_correctly(self):
        """Test that _detect_flag() calculates flag_slope_pct correctly."""
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # Given: Flag candles with known open/close for slope calculation
        pole_end = datetime(2024, 1, 10, tzinfo=UTC)
        flag_start = pole_end + timedelta(days=1)

        # Create candles with downward slope: open=105, close=100 → -4.76% slope
        candles_data = []
        for i in range(3):
            date = flag_start + timedelta(days=i)
            candles_data.append({
                "timestamp": date,
                "open": 105.0 if i == 0 else 103.0,
                "high": 106.0,
                "low": 99.0,
                "close": 100.0 if i == 2 else 104.0,
                "volume": 1_000_000,
            })

        flag_candles = pd.DataFrame(candles_data)

        # When: _detect_flag() called
        result = detector._detect_flag(flag_candles, pole_end)

        # Then: flag_slope_pct should be (close - open) / open
        assert result is not None
        _, _, _, _, _, flag_slope_pct = result

        # Slope should be negative (downward)
        assert flag_slope_pct < 0, f"Expected negative slope, got {flag_slope_pct}%"

    def test_detect_flag_handles_empty_dataframe(self):
        """Test that _detect_flag() handles empty DataFrame gracefully."""
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # Given: Empty DataFrame
        pole_end = datetime(2024, 1, 10, tzinfo=UTC)
        empty_df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        # When: _detect_flag() called with empty data
        result = detector._detect_flag(empty_df, pole_end)

        # Then: Should return None (no flag detected)
        assert result is None

    def test_detect_flag_handles_insufficient_data(self):
        """Test that _detect_flag() returns None when data < 2 days."""
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # Given: Only 1 day of data (insufficient for 2-5 day flag)
        pole_end = datetime(2024, 1, 10, tzinfo=UTC)
        flag_start = pole_end + timedelta(days=1)

        single_candle = pd.DataFrame([{
            "timestamp": flag_start,
            "open": 100.0,
            "high": 104.0,
            "low": 100.0,
            "close": 102.0,
            "volume": 1_000_000,
        }])

        # When: _detect_flag() called
        result = detector._detect_flag(single_candle, pole_end)

        # Then: Should return None (insufficient duration)
        assert result is None

    def test_detect_flag_rejects_flat_upward_slope(self):
        """Test that _detect_flag() rejects flags with upward slope."""
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # Given: Flag candles with upward slope (open < close)
        pole_end = datetime(2024, 1, 10, tzinfo=UTC)
        flag_start = pole_end + timedelta(days=1)

        # Create candles with strong upward slope
        candles_data = []
        for i in range(3):
            date = flag_start + timedelta(days=i)
            candles_data.append({
                "timestamp": date,
                "open": 100.0,  # Open at low end
                "high": 104.0,
                "low": 100.0,
                "close": 104.0,  # Close at high end (upward slope)
                "volume": 1_000_000,
            })

        flag_candles = pd.DataFrame(candles_data)

        # When: _detect_flag() called
        result = detector._detect_flag(flag_candles, pole_end)

        # Then: Should return None (invalid upward slope)
        assert result is None


class TestBullFlagDetectorCalculateTargets:
    """Test suite for BullFlagDetector._calculate_targets() method - T033."""

    @pytest.mark.parametrize(
        "pole_high,pole_low,flag_high,expected_breakout,expected_target",
        [
            # Test case from spec: Pole $100 → $120 (+$20), Flag $115-$118
            (120.0, 100.0, 118.0, 118.0, 138.0),

            # Larger pole: $100 → $150 (+$50), Flag $140-$145
            (150.0, 100.0, 145.0, 145.0, 195.0),

            # Smaller pole: $50 → $54 (+$4), Flag $52-$54
            (54.0, 50.0, 54.0, 54.0, 58.0),

            # Different pole: $200 → $240 (+$40), Flag $230-$235
            (240.0, 200.0, 235.0, 235.0, 275.0),
        ],
        ids=[
            "spec_example_pole_20_flag_118",
            "larger_pole_50_flag_145",
            "smaller_pole_4_flag_54",
            "pole_40_flag_235",
        ]
    )
    def test_calculate_targets_computes_breakout_price(
        self,
        pole_high: float,
        pole_low: float,
        flag_high: float,
        expected_breakout: float,
        expected_target: float
    ):
        """
        T033 [RED]: Test _calculate_targets() computes breakout price and target correctly.

        GIVEN: Pole high/low prices and flag high price
        WHEN: _calculate_targets() called
        THEN: Returns (breakout_price, price_target) with correct calculation

        Calculation:
        - pole_height = pole_high - pole_low
        - breakout_price = flag_high
        - price_target = breakout_price + pole_height
        """
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # When: _calculate_targets() called with pole and flag data
        breakout_price, price_target = detector._calculate_targets(
            pole_high=pole_high,
            pole_low=pole_low,
            flag_high=flag_high
        )

        # Then: breakout_price equals flag_high
        assert abs(breakout_price - expected_breakout) < 0.01, (
            f"Expected breakout_price={expected_breakout}, got {breakout_price}"
        )

        # And: price_target equals breakout_price + pole_height
        assert abs(price_target - expected_target) < 0.01, (
            f"Expected price_target={expected_target}, got {price_target}"
        )

    def test_calculate_targets_with_decimal_precision(self):
        """
        Test _calculate_targets() maintains precision with decimal prices.

        GIVEN: Prices with decimal places
        WHEN: _calculate_targets() called
        THEN: Returns precise float results (no significant floating point errors)
        """
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # When: _calculate_targets() called with decimal prices
        breakout_price, price_target = detector._calculate_targets(
            pole_high=123.45,
            pole_low=100.23,
            flag_high=120.50
        )

        # Then: Calculation is precise
        pole_height = 123.45 - 100.23  # 23.22
        expected_target = 120.50 + pole_height  # 143.72

        assert abs(breakout_price - 120.50) < 0.01
        assert abs(price_target - expected_target) < 0.01
        assert abs(price_target - 143.72) < 0.01

    def test_calculate_targets_with_zero_pole_height(self):
        """
        Test _calculate_targets() handles edge case of zero pole height.

        GIVEN: Pole high equals pole low (no gain)
        WHEN: _calculate_targets() called
        THEN: price_target equals breakout_price (no projection)
        """
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # When: _calculate_targets() called with zero pole height
        breakout_price, price_target = detector._calculate_targets(
            pole_high=100.0,
            pole_low=100.0,
            flag_high=100.0
        )

        # Then: price_target equals breakout_price (no projection)
        assert breakout_price == 100.0
        assert price_target == 100.0

    def test_calculate_targets_returns_floats(self):
        """
        Test _calculate_targets() returns float types.

        GIVEN: Float pole and flag prices
        WHEN: _calculate_targets() called
        THEN: Returns float values (not Decimal or other types)
        """
        # Given: BullFlagDetector instance
        config = MomentumConfig()
        logger = MomentumLogger()
        from unittest.mock import Mock
        mock_market_data = Mock()
        detector = BullFlagDetector(config=config, market_data_service=mock_market_data, momentum_logger=logger)

        # When: _calculate_targets() called with float inputs
        breakout_price, price_target = detector._calculate_targets(
            pole_high=120.0,
            pole_low=100.0,
            flag_high=118.0
        )

        # Then: Returns float values
        assert isinstance(breakout_price, float)
        assert isinstance(price_target, float)
        assert breakout_price == 118.0
        assert price_target == 138.0
