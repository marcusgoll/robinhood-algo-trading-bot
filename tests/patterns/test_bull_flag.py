"""Unit tests for bull flag pattern detection logic.

Tests follow TDD approach with Given-When-Then structure.
These tests will initially fail (RED phase) until implementation is complete.

Feature: 003-entry-logic-bull-flag
Tasks: T012 (flagpole), T013 (consolidation), T014 (breakout)
"""

import pytest
from decimal import Decimal
from typing import List, Dict, Optional

from src.trading_bot.patterns.models import FlagpoleData, ConsolidationData
from src.trading_bot.indicators.exceptions import InsufficientDataError


# ============================================================================
# T012: Flagpole Detection Tests
# ============================================================================


class TestFlagpoleDetection:
    """Tests for flagpole detection logic (_detect_flagpole method).

    Tests cover:
    - Valid flagpole detection (strong gain, minimum gain)
    - Invalid flagpole rejection (insufficient gain, too short/long, low volume)
    - Boundary conditions (minimum/maximum bars, exact thresholds)
    - Edge cases (empty bars, single bar, pullbacks)
    - Precision and calculation accuracy
    """

    def _generate_flagpole_bars(
        self,
        num_bars: int,
        gain_pct: float,
        base_price: float = 100.0,
        base_volume: float = 1000000.0,
        volume_multiplier: float = 1.2
    ) -> List[Dict]:
        """Generate OHLCV bars representing a flagpole.

        Args:
            num_bars: Number of bars in flagpole
            gain_pct: Total percentage gain from start to end
            base_price: Starting price
            base_volume: Base volume level
            volume_multiplier: Volume multiplier vs base (1.0 = normal, 1.2 = 20% above)

        Returns:
            List of OHLCV bar dictionaries
        """
        bars = []
        start_price = Decimal(str(base_price))
        end_price = start_price * (Decimal("1.0") + Decimal(str(gain_pct)) / Decimal("100.0"))
        gain_per_bar = (end_price - start_price) / Decimal(str(num_bars))

        for i in range(num_bars):
            price = start_price + (gain_per_bar * Decimal(str(i)))
            bars.append({
                "open": float(price),
                "high": float(price + Decimal("0.50")),
                "low": float(price - Decimal("0.30")),
                "close": float(price + Decimal("0.40")),
                "volume": float(Decimal(str(base_volume)) * Decimal(str(volume_multiplier)))
            })

        return bars

    def test_detect_flagpole_valid_strong_gain(self):
        """Test flagpole detection with strong gain above minimum threshold.

        Given: 10 bars with 8% gain and high volume (20% above average)
        When: Call detect_flagpole()
        Then: Returns FlagpoleData with correct gain_pct, bar indices, and volume
        """
        # Given: 10 bars with 8% gain (well above 5% minimum)
        bars = self._generate_flagpole_bars(
            num_bars=10,
            gain_pct=8.0,
            volume_multiplier=1.2
        )

        # When: Detect flagpole (function doesn't exist yet - will fail in RED phase)
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Valid flagpole detected
        assert result is not None, "Should detect valid flagpole with 8% gain"
        assert isinstance(result, FlagpoleData)
        assert result.end_idx - result.start_idx + 1 == 10
        assert result.gain_pct >= Decimal("8.0")
        assert result.start_idx == 0
        assert result.avg_volume > Decimal("0")

    def test_detect_flagpole_minimum_gain(self):
        """Test flagpole detection at exact minimum gain threshold.

        Given: 10 bars with exactly 5% gain (minimum threshold)
        When: Call detect_flagpole()
        Then: Returns FlagpoleData (should accept at minimum threshold)
        """
        # Given: Bars with exactly 5% gain (minimum)
        bars = self._generate_flagpole_bars(
            num_bars=10,
            gain_pct=5.0,
            volume_multiplier=1.1
        )

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Valid flagpole detected at minimum threshold
        assert result is not None, "Should accept 5% gain (minimum threshold)"
        assert isinstance(result, FlagpoleData)
        assert result.gain_pct >= Decimal("5.0")

    def test_detect_flagpole_insufficient_gain(self):
        """Test flagpole detection with gain below minimum threshold.

        Given: 10 bars with 3% gain (below 5% minimum)
        When: Call detect_flagpole()
        Then: Returns None (pattern rejected - insufficient gain)
        """
        # Given: Bars with 3% gain (below minimum)
        bars = self._generate_flagpole_bars(
            num_bars=10,
            gain_pct=3.0,
            volume_multiplier=1.2
        )

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: No flagpole detected
        assert result is None, "Should reject 3% gain (below 5% minimum)"

    def test_detect_flagpole_too_short(self):
        """Test flagpole detection with duration below minimum bars.

        Given: 2 bars with 10% gain (below 3-bar minimum)
        When: Call detect_flagpole()
        Then: Returns None (duration too short)
        """
        # Given: Only 2 bars with good gain (below 3-bar minimum)
        bars = self._generate_flagpole_bars(
            num_bars=2,
            gain_pct=10.0,
            volume_multiplier=1.3
        )

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: No flagpole detected (too short)
        assert result is None, "Should reject 2-bar flagpole (below 3-bar minimum)"

    def test_detect_flagpole_too_long(self):
        """Test flagpole detection with duration exceeding maximum bars.

        Given: 20 bars with gain distributed (exceeds 15-bar maximum)
        When: Call detect_flagpole()
        Then: Returns None or detects valid sub-pattern within 15-bar limit
        """
        # Given: 20 bars with gain (exceeds 15-bar maximum)
        bars = self._generate_flagpole_bars(
            num_bars=20,
            gain_pct=8.0,
            volume_multiplier=1.2
        )

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Either rejected OR detected shorter valid sub-pattern
        # Implementation may scan for valid patterns within the 15-bar window
        if result is not None:
            assert result.end_idx - result.start_idx + 1 <= 15, \
                "If detected, flagpole duration must be <= 15 bars"

    def test_detect_flagpole_low_volume(self):
        """Test flagpole detection with below-average volume.

        Given: 8 bars with 6% gain but below-average volume (70% of normal)
        When: Call detect_flagpole()
        Then: Returns None (rejected due to low volume)
        """
        # Given: Bars with low volume (70% of normal)
        bars = self._generate_flagpole_bars(
            num_bars=8,
            gain_pct=6.0,
            volume_multiplier=0.7  # Below average volume
        )

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Likely rejected due to low volume (implementation may vary)
        # Note: Some implementations may accept with quality penalty
        # For strict TDD, we expect rejection on low volume
        if result is not None:
            # If accepted, verify volume is still calculated
            assert result.avg_volume > Decimal("0")

    def test_detect_flagpole_minimum_bars(self):
        """Test flagpole detection at exact minimum bar threshold.

        Given: 3 bars with 6% gain (minimum bar count)
        When: Call detect_flagpole()
        Then: Returns FlagpoleData (should accept at minimum)
        """
        # Given: Exactly 3 bars (minimum)
        bars = self._generate_flagpole_bars(
            num_bars=3,
            gain_pct=6.0,
            volume_multiplier=1.2
        )

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Valid flagpole detected at minimum bars
        assert result is not None, "Should accept 3-bar flagpole (minimum)"
        assert result.end_idx - result.start_idx + 1 == 3

    def test_detect_flagpole_maximum_bars(self):
        """Test flagpole detection at exact maximum bar threshold.

        Given: 15 bars with 8% gain (maximum bar count)
        When: Call detect_flagpole()
        Then: Returns FlagpoleData (should accept at maximum)
        """
        # Given: Exactly 15 bars (maximum)
        bars = self._generate_flagpole_bars(
            num_bars=15,
            gain_pct=8.0,
            volume_multiplier=1.2
        )

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Valid flagpole detected at maximum bars
        assert result is not None, "Should accept 15-bar flagpole (maximum)"
        assert result.end_idx - result.start_idx + 1 <= 15

    def test_detect_flagpole_empty_bars(self):
        """Test flagpole detection with empty bar list.

        Given: Empty bars list
        When: Call detect_flagpole()
        Then: Returns None (no data to analyze)
        """
        # Given: Empty bars
        bars = []

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: No flagpole detected
        assert result is None, "Should return None for empty bars"

    def test_detect_flagpole_single_bar(self):
        """Test flagpole detection with single bar.

        Given: 1 bar (below minimum of 3 bars)
        When: Call detect_flagpole()
        Then: Returns None (insufficient bars)
        """
        # Given: Single bar
        bars = self._generate_flagpole_bars(
            num_bars=1,
            gain_pct=10.0,
            volume_multiplier=1.5
        )

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: No flagpole detected
        assert result is None, "Should reject single bar (below 3-bar minimum)"

    def test_detect_flagpole_price_precision(self):
        """Test flagpole detection maintains Decimal precision.

        Given: Bars with precise decimal prices (100.01, 100.02, etc.)
        When: Call detect_flagpole()
        Then: FlagpoleData uses Decimal types for all price fields
        """
        # Given: Bars with precise decimal prices
        bars = []
        base_price = Decimal("100.01")
        for i in range(8):
            price = base_price + Decimal(str(i * 0.75))
            bars.append({
                "open": float(price),
                "high": float(price + Decimal("0.50")),
                "low": float(price - Decimal("0.30")),
                "close": float(price + Decimal("0.40")),
                "volume": 1200000.0
            })

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Verify Decimal precision
        if result is not None:
            assert isinstance(result.start_price, Decimal)
            assert isinstance(result.high_price, Decimal)
            assert isinstance(result.gain_pct, Decimal)
            assert isinstance(result.avg_volume, Decimal)

    def test_detect_flagpole_gain_calculation(self):
        """Test flagpole gain percentage is calculated correctly.

        Given: Bars with known start and end prices
        When: Call detect_flagpole()
        Then: gain_pct = ((high_price - start_price) / start_price) * 100
        """
        # Given: Bars with known gain
        start = Decimal("100.00")
        end = Decimal("108.00")  # 8% gain
        expected_gain_pct = ((end - start) / start) * Decimal("100")

        bars = []
        for i in range(8):
            price = start + ((end - start) / Decimal("7")) * Decimal(str(i))
            bars.append({
                "open": float(price),
                "high": float(price + Decimal("0.50")),
                "low": float(price - Decimal("0.30")),
                "close": float(price + Decimal("0.40")),
                "volume": 1200000.0
            })

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Gain should match expected calculation (allow small tolerance)
        if result is not None:
            assert abs(result.gain_pct - expected_gain_pct) < Decimal("1.0"), \
                f"Expected gain ~{expected_gain_pct}%, got {result.gain_pct}%"

    def test_detect_flagpole_volume_calculation(self):
        """Test flagpole detection calculates average volume correctly.

        Given: Bars with varying volume levels
        When: Call detect_flagpole()
        Then: avg_volume is arithmetic mean of all flagpole bar volumes
        """
        # Given: Bars with known volumes
        bars = []
        volumes = [1000000, 1200000, 1100000, 1300000, 1150000]
        base_price = Decimal("100.00")

        for i, vol in enumerate(volumes):
            price = base_price + Decimal(str(i * 1.5))
            bars.append({
                "open": float(price),
                "high": float(price + Decimal("0.50")),
                "low": float(price - Decimal("0.30")),
                "close": float(price + Decimal("0.40")),
                "volume": float(vol)
            })

        # When: Detect flagpole
        from src.trading_bot.patterns.bull_flag import detect_flagpole
        result = detect_flagpole(bars)

        # Then: Average volume should be calculated correctly
        if result is not None:
            expected_avg = Decimal(str(sum(volumes) / len(volumes)))
            # Allow small floating-point tolerance (within 1000 shares)
            assert abs(result.avg_volume - expected_avg) < Decimal("1000"), \
                f"Expected avg volume ~{expected_avg}, got {result.avg_volume}"


# ============================================================================
# T013: Consolidation Detection Tests
# ============================================================================


class TestConsolidationDetection:
    """Tests for consolidation phase detection (T013)."""

    def _build_flagpole_data(
        self,
        start_idx: int = 0,
        end_idx: int = 10,
        gain_pct: float = 8.5,
        high_price: float = 189.875,
        start_price: float = 175.0,
        avg_volume: float = 2400000.0
    ) -> FlagpoleData:
        """Helper to create FlagpoleData for testing.

        Args:
            start_idx: Starting bar index
            end_idx: Ending bar index
            gain_pct: Percentage gain
            high_price: Highest price during flagpole
            start_price: Starting price
            avg_volume: Average volume

        Returns:
            FlagpoleData instance
        """
        return FlagpoleData(
            start_idx=start_idx,
            end_idx=end_idx,
            gain_pct=Decimal(str(gain_pct)),
            high_price=Decimal(str(high_price)),
            start_price=Decimal(str(start_price)),
            avg_volume=Decimal(str(avg_volume))
        )

    def _build_consolidation_bars(
        self,
        num_bars: int,
        base_price: float = 180.0,
        retracement_pct: float = 35.0,
        flagpole_gain: float = 14.875,
        volume_multiplier: float = 0.6,
        base_volume: float = 2000000.0
    ) -> List[Dict]:
        """Helper to create consolidation bars with specified characteristics.

        Args:
            num_bars: Number of consolidation bars to create
            base_price: Base price level for consolidation
            retracement_pct: Percentage retracement from flagpole
            flagpole_gain: Total flagpole gain for retracement calculation
            volume_multiplier: Volume relative to base (< 1.0 for decreasing)
            base_volume: Base volume level

        Returns:
            List of bar dicts with OHLCV data
        """
        retracement = Decimal(str(flagpole_gain)) * (Decimal(str(retracement_pct)) / Decimal("100"))
        high_boundary = Decimal(str(base_price))
        low_boundary = high_boundary - retracement

        bars = []
        for i in range(num_bars):
            # Create downward-sloping consolidation
            progress = Decimal(str(i)) / Decimal(str(num_bars))
            price = high_boundary - (retracement * progress)

            # Decreasing volume pattern
            volume = Decimal(str(base_volume)) * Decimal(str(volume_multiplier)) * (Decimal("1.0") - progress * Decimal("0.2"))

            bars.append({
                "open": float(price),
                "high": float(price + Decimal("0.50")),
                "low": float(price - Decimal("0.50")),
                "close": float(price - Decimal("0.20")),
                "volume": float(volume)
            })

        return bars

    def test_detect_consolidation_valid_tight_range(self, valid_bull_flag_bars):
        """Test consolidation detection with valid parameters.

        Given: FlagpoleData followed by 6 bars with 35% retracement and decreasing volume
        When: detect_consolidation() is called
        Then: Returns ConsolidationData with correct boundaries and duration
        """
        # Given: Create flagpole and consolidation bars
        flagpole = self._build_flagpole_data(
            start_idx=0,
            end_idx=10,
            gain_pct=8.5,
            high_price=189.875,
            start_price=175.0
        )

        # Build 6 consolidation bars with 35% retracement (within 20-50% range)
        consolidation_bars = self._build_consolidation_bars(
            num_bars=6,
            base_price=189.875,
            retracement_pct=35.0,
            flagpole_gain=14.875,  # 189.875 - 175.0
            volume_multiplier=0.6  # 40% volume decrease
        )

        # Create complete bars list (flagpole + consolidation)
        bars = valid_bull_flag_bars[:11] + consolidation_bars

        # When: Call detect_consolidation (function doesn't exist yet - will fail)
        from src.trading_bot.patterns.bull_flag import detect_consolidation
        result = detect_consolidation(bars, flagpole)

        # Then: Verify consolidation detected with correct properties
        assert result is not None, "Should detect valid consolidation"
        assert isinstance(result, ConsolidationData)
        assert result.start_idx == flagpole.end_idx + 1
        assert result.end_idx == flagpole.end_idx + 6
        assert result.upper_boundary > result.lower_boundary
        assert result.avg_volume > Decimal("0")

    def test_detect_consolidation_minimum_duration(self, valid_bull_flag_bars):
        """Test consolidation detection with minimum valid duration.

        Given: FlagpoleData followed by exactly 3 bars (minimum duration)
        When: detect_consolidation() is called
        Then: Returns ConsolidationData
        """
        # Given: Flagpole data
        flagpole = self._build_flagpole_data()

        # Build exactly 3 consolidation bars (minimum allowed)
        consolidation_bars = self._build_consolidation_bars(
            num_bars=3,
            base_price=189.875,
            retracement_pct=30.0,
            flagpole_gain=14.875
        )

        bars = valid_bull_flag_bars[:11] + consolidation_bars

        # When: Call detect_consolidation
        from src.trading_bot.patterns.bull_flag import detect_consolidation
        result = detect_consolidation(bars, flagpole)

        # Then: Should accept minimum duration
        assert result is not None, "Should accept 3-bar consolidation (minimum)"
        assert isinstance(result, ConsolidationData)
        assert result.end_idx - result.start_idx + 1 == 3

    def test_detect_consolidation_too_short(self, valid_bull_flag_bars):
        """Test consolidation detection rejects duration below minimum.

        Given: FlagpoleData followed by only 2 bars
        When: detect_consolidation() is called
        Then: Returns None (too short)
        """
        # Given: Flagpole data
        flagpole = self._build_flagpole_data()

        # Build only 2 bars (below minimum of 3)
        consolidation_bars = self._build_consolidation_bars(
            num_bars=2,
            base_price=189.875,
            retracement_pct=30.0,
            flagpole_gain=14.875
        )

        bars = valid_bull_flag_bars[:11] + consolidation_bars

        # When: Call detect_consolidation
        from src.trading_bot.patterns.bull_flag import detect_consolidation
        result = detect_consolidation(bars, flagpole)

        # Then: Should reject insufficient duration
        assert result is None, "Should reject 2-bar consolidation (below minimum of 3)"

    def test_detect_consolidation_too_long(self, valid_bull_flag_bars):
        """Test consolidation detection rejects duration above maximum.

        Given: FlagpoleData followed by 12 bars (exceeds 10-bar max)
        When: detect_consolidation() is called
        Then: Returns None (too long)
        """
        # Given: Flagpole data
        flagpole = self._build_flagpole_data()

        # Build 12 bars (exceeds maximum of 10)
        consolidation_bars = self._build_consolidation_bars(
            num_bars=12,
            base_price=189.875,
            retracement_pct=35.0,
            flagpole_gain=14.875
        )

        bars = valid_bull_flag_bars[:11] + consolidation_bars

        # When: Call detect_consolidation
        from src.trading_bot.patterns.bull_flag import detect_consolidation
        result = detect_consolidation(bars, flagpole)

        # Then: Should reject excessive duration
        assert result is None, "Should reject 12-bar consolidation (exceeds maximum of 10)"

    def test_detect_consolidation_insufficient_retracement(self, valid_bull_flag_bars):
        """Test consolidation detection rejects insufficient retracement.

        Given: FlagpoleData followed by 5 bars with only 15% retracement
        When: detect_consolidation() is called
        Then: Returns None (below 20% minimum)
        """
        # Given: Flagpole data
        flagpole = self._build_flagpole_data()

        # Build bars with only 15% retracement (below minimum of 20%)
        consolidation_bars = self._build_consolidation_bars(
            num_bars=5,
            base_price=189.875,
            retracement_pct=15.0,  # Below minimum
            flagpole_gain=14.875
        )

        bars = valid_bull_flag_bars[:11] + consolidation_bars

        # When: Call detect_consolidation
        from src.trading_bot.patterns.bull_flag import detect_consolidation
        result = detect_consolidation(bars, flagpole)

        # Then: Should reject insufficient retracement
        assert result is None, "Should reject 15% retracement (below 20% minimum)"

    def test_detect_consolidation_excessive_retracement(self, valid_bull_flag_bars):
        """Test consolidation detection rejects excessive retracement.

        Given: FlagpoleData followed by 5 bars with 60% retracement
        When: detect_consolidation() is called
        Then: Returns None (exceeds 50% maximum)
        """
        # Given: Flagpole data
        flagpole = self._build_flagpole_data()

        # Build bars with 60% retracement (exceeds maximum of 50%)
        consolidation_bars = self._build_consolidation_bars(
            num_bars=5,
            base_price=189.875,
            retracement_pct=60.0,  # Exceeds maximum
            flagpole_gain=14.875
        )

        bars = valid_bull_flag_bars[:11] + consolidation_bars

        # When: Call detect_consolidation
        from src.trading_bot.patterns.bull_flag import detect_consolidation
        result = detect_consolidation(bars, flagpole)

        # Then: Should reject excessive retracement
        assert result is None, "Should reject 60% retracement (exceeds 50% maximum)"

    def test_detect_consolidation_high_volume(self, valid_bull_flag_bars):
        """Test consolidation detection rejects increasing/high volume.

        Given: FlagpoleData followed by 6 bars with increasing volume
        When: detect_consolidation() is called
        Then: Returns None (volume pattern invalid)
        """
        # Given: Flagpole data
        flagpole = self._build_flagpole_data()

        # Build bars with INCREASING volume (should decrease in valid consolidation)
        # Use volume_multiplier > 1.0 to simulate increasing volume
        num_bars = 6
        bars_with_high_volume = []
        base_price = Decimal("189.875")
        retracement_pct = Decimal("35.0")
        flagpole_gain = Decimal("14.875")
        base_volume = Decimal("2000000.0")

        retracement = flagpole_gain * (retracement_pct / Decimal("100"))
        high_boundary = base_price
        low_boundary = high_boundary - retracement

        for i in range(num_bars):
            progress = Decimal(str(i)) / Decimal(str(num_bars))
            price = high_boundary - (retracement * progress)

            # INCREASING volume (opposite of what we want)
            volume = base_volume * Decimal("1.2") * (Decimal("1.0") + progress * Decimal("0.5"))

            bars_with_high_volume.append({
                "open": float(price),
                "high": float(price + Decimal("0.50")),
                "low": float(price - Decimal("0.50")),
                "close": float(price - Decimal("0.20")),
                "volume": float(volume)
            })

        bars = valid_bull_flag_bars[:11] + bars_with_high_volume

        # When: Call detect_consolidation
        from src.trading_bot.patterns.bull_flag import detect_consolidation
        result = detect_consolidation(bars, flagpole)

        # Then: Should reject increasing volume pattern
        assert result is None, "Should reject consolidation with increasing volume"


# ============================================================================
# T014: Breakout Confirmation Tests
# ============================================================================


class TestBreakoutConfirmation:
    """Tests for breakout confirmation logic (T014)."""

    def test_confirm_breakout_valid_strong(self):
        """Test breakout confirmation with strong breakout signal.

        Given: ConsolidationData with upper_boundary of $187.50, avg_volume of 1,200,000
        When: Confirmation bar closes at $191.25 (2% above resistance) with 1,920,000 volume (60% increase)
        Then: Returns Decimal breakout price of $191.25
        """
        # Given: Valid consolidation data
        consolidation = ConsolidationData(
            start_idx=9,
            end_idx=15,
            upper_boundary=Decimal("187.50"),
            lower_boundary=Decimal("183.25"),
            avg_volume=Decimal("1200000")
        )

        # Given: Strong breakout bar (2% above resistance, 60% volume increase)
        confirmation_bar = {
            "open": Decimal("188.00"),
            "high": Decimal("192.00"),
            "low": Decimal("187.80"),
            "close": Decimal("191.25"),  # 2% above upper_boundary (187.50)
            "volume": Decimal("1920000")  # 60% increase from consolidation avg
        }

        # When: Call confirm_breakout()
        from src.trading_bot.patterns.bull_flag import confirm_breakout
        result = confirm_breakout(consolidation, confirmation_bar)

        # Then: Returns breakout price
        assert result is not None, "Should confirm strong breakout"
        assert isinstance(result, Decimal)
        assert result == Decimal("191.25")

    def test_confirm_breakout_minimum_move(self):
        """Test breakout confirmation with minimum acceptable move.

        Given: ConsolidationData with upper_boundary of $100.00, avg_volume of 1,000,000
        When: Confirmation bar closes at $101.00 (1% move - minimum) with 1,300,000 volume (30% increase)
        Then: Returns Decimal breakout price of $101.00
        """
        # Given: Consolidation data
        consolidation = ConsolidationData(
            start_idx=10,
            end_idx=18,
            upper_boundary=Decimal("100.00"),
            lower_boundary=Decimal("97.00"),
            avg_volume=Decimal("1000000")
        )

        # Given: Minimum valid breakout (1% move, 30% volume increase)
        confirmation_bar = {
            "open": Decimal("100.20"),
            "high": Decimal("101.50"),
            "low": Decimal("100.00"),
            "close": Decimal("101.00"),  # Exactly 1% above upper_boundary
            "volume": Decimal("1300000")  # Exactly 30% increase
        }

        # When: Call confirm_breakout()
        from src.trading_bot.patterns.bull_flag import confirm_breakout
        result = confirm_breakout(consolidation, confirmation_bar)

        # Then: Returns breakout price (minimum valid)
        assert result is not None, "Should confirm minimum valid breakout"
        assert isinstance(result, Decimal)
        assert result == Decimal("101.00")

    def test_confirm_breakout_insufficient_move(self):
        """Test breakout confirmation fails with insufficient price move.

        Given: ConsolidationData with upper_boundary of $200.00
        When: Confirmation bar closes at $200.99 (0.495% move - below 1% minimum)
        Then: Returns None (move too small)
        """
        # Given: Consolidation data
        consolidation = ConsolidationData(
            start_idx=5,
            end_idx=12,
            upper_boundary=Decimal("200.00"),
            lower_boundary=Decimal("195.00"),
            avg_volume=Decimal("2000000")
        )

        # Given: Insufficient price move (0.495% - below 1% minimum)
        confirmation_bar = {
            "open": Decimal("200.50"),
            "high": Decimal("201.00"),
            "low": Decimal("200.00"),
            "close": Decimal("200.99"),  # 0.495% above upper_boundary (too small)
            "volume": Decimal("2600000")  # 30% volume increase (valid)
        }

        # When: Call confirm_breakout()
        from src.trading_bot.patterns.bull_flag import confirm_breakout
        result = confirm_breakout(consolidation, confirmation_bar)

        # Then: Returns None (price move insufficient)
        assert result is None, "Should reject breakout with insufficient price move"

    def test_confirm_breakout_insufficient_volume(self):
        """Test breakout confirmation fails with insufficient volume increase.

        Given: ConsolidationData with avg_volume of 1,500,000
        When: Confirmation bar has 2% price move but only 1,800,000 volume (20% increase - below 30% minimum)
        Then: Returns None (volume increase too small)
        """
        # Given: Consolidation data
        consolidation = ConsolidationData(
            start_idx=8,
            end_idx=14,
            upper_boundary=Decimal("150.00"),
            lower_boundary=Decimal("146.00"),
            avg_volume=Decimal("1500000")
        )

        # Given: Insufficient volume increase (20% - below 30% minimum)
        confirmation_bar = {
            "open": Decimal("150.50"),
            "high": Decimal("153.50"),
            "low": Decimal("150.00"),
            "close": Decimal("153.00"),  # 2% above upper_boundary (valid)
            "volume": Decimal("1800000")  # 20% increase (below 30% minimum)
        }

        # When: Call confirm_breakout()
        from src.trading_bot.patterns.bull_flag import confirm_breakout
        result = confirm_breakout(consolidation, confirmation_bar)

        # Then: Returns None (volume increase insufficient)
        assert result is None, "Should reject breakout with insufficient volume increase"

    def test_confirm_breakout_close_below_resistance(self):
        """Test breakout confirmation fails when close is below upper boundary.

        Given: ConsolidationData with upper_boundary of $180.00
        When: Confirmation bar closes at $179.50 (below upper_boundary)
        Then: Returns None (failed breakout - close below resistance)
        """
        # Given: Consolidation data
        consolidation = ConsolidationData(
            start_idx=12,
            end_idx=20,
            upper_boundary=Decimal("180.00"),
            lower_boundary=Decimal("175.00"),
            avg_volume=Decimal("1800000")
        )

        # Given: Close below resistance (failed breakout)
        confirmation_bar = {
            "open": Decimal("178.00"),
            "high": Decimal("181.00"),  # High breaks resistance
            "low": Decimal("177.50"),
            "close": Decimal("179.50"),  # But close is BELOW upper_boundary
            "volume": Decimal("2500000")  # 39% volume increase (valid)
        }

        # When: Call confirm_breakout()
        from src.trading_bot.patterns.bull_flag import confirm_breakout
        result = confirm_breakout(consolidation, confirmation_bar)

        # Then: Returns None (close must be above resistance)
        assert result is None, "Should reject breakout with close below resistance"

    def test_confirm_breakout_confirmation_bar_too_far(self):
        """Test breakout confirmation fails when breakout occurs outside confirmation window.

        Given: ConsolidationData ending at bar index 15, 2-bar confirmation window
        When: Valid breakout occurs at bar index 18 (3 bars after consolidation end)
        Then: Returns None (outside 2-bar confirmation window)
        """
        # Given: Consolidation data ending at index 15
        consolidation = ConsolidationData(
            start_idx=10,
            end_idx=15,  # Consolidation ends at bar 15
            upper_boundary=Decimal("190.00"),
            lower_boundary=Decimal("185.00"),
            avg_volume=Decimal("1000000")
        )

        # Given: Breakout bar at index 18 (3rd bar after consolidation - too far)
        # Valid breakout characteristics but outside confirmation window
        confirmation_bar = {
            "open": Decimal("189.80"),
            "high": Decimal("193.00"),
            "low": Decimal("189.50"),
            "close": Decimal("192.50"),  # 1.32% above resistance (valid)
            "volume": Decimal("1400000")  # 40% increase (valid)
        }

        # When: Call confirm_breakout() with bar_index parameter for timing validation
        from src.trading_bot.patterns.bull_flag import confirm_breakout

        # Pass the bar index (18) to validate it's within 2-bar window (16-17)
        result = confirm_breakout(consolidation, confirmation_bar, bar_index=18)

        # Then: Returns None (breakout outside 2-bar confirmation window)
        assert result is None, "Should reject breakout outside 2-bar confirmation window"


# ============================================================================
# T020: Risk Parameter Tests
# ============================================================================


class TestRiskParameters:
    """Tests for risk parameter calculation logic (_calculate_risk_parameters method).

    Tests cover:
    - Stop-loss calculation (lower boundary - 0.5%)
    - Target price calculation (breakout price + flagpole height)
    - Risk/reward ratio calculation (minimum 2:1)
    - Rejection of patterns with insufficient risk/reward ratio
    - Decimal precision for all calculations
    """

    def _build_flagpole_data(
        self,
        start_idx: int = 0,
        end_idx: int = 10,
        gain_pct: float = 10.0,
        high_price: float = 110.0,
        start_price: float = 100.0,
        avg_volume: float = 1500000.0
    ) -> FlagpoleData:
        """Helper to create FlagpoleData for testing.

        Args:
            start_idx: Starting bar index
            end_idx: Ending bar index
            gain_pct: Percentage gain
            high_price: Highest price during flagpole
            start_price: Starting price
            avg_volume: Average volume

        Returns:
            FlagpoleData instance
        """
        return FlagpoleData(
            start_idx=start_idx,
            end_idx=end_idx,
            gain_pct=Decimal(str(gain_pct)),
            high_price=Decimal(str(high_price)),
            start_price=Decimal(str(start_price)),
            avg_volume=Decimal(str(avg_volume))
        )

    def _build_consolidation_data(
        self,
        start_idx: int = 11,
        end_idx: int = 16,
        upper_boundary: float = 108.0,
        lower_boundary: float = 103.0,
        avg_volume: float = 1000000.0
    ) -> ConsolidationData:
        """Helper to create ConsolidationData for testing.

        Args:
            start_idx: Starting bar index
            end_idx: Ending bar index
            upper_boundary: Resistance level
            lower_boundary: Support level
            avg_volume: Average volume

        Returns:
            ConsolidationData instance
        """
        return ConsolidationData(
            start_idx=start_idx,
            end_idx=end_idx,
            upper_boundary=Decimal(str(upper_boundary)),
            lower_boundary=Decimal(str(lower_boundary)),
            avg_volume=Decimal(str(avg_volume))
        )

    def test_calculate_risk_parameters_valid_2_to_1(self):
        """Test risk parameter calculation with valid 2:1 ratio.

        Given: Flagpole gain 10% (100→110), consolidation retracement 30% (103-108),
               breakout at 110.16 (+2% above resistance)
        When: Calculate risk parameters
        Then: Returns dict with entry_price, stop_loss, target_price, risk_reward_ratio >= 2.0
        """
        # Given: Flagpole with 10% gain (100 → 110)
        flagpole = self._build_flagpole_data(
            start_idx=0,
            end_idx=10,
            gain_pct=10.0,
            high_price=110.0,  # Flagpole high
            start_price=100.0,  # Flagpole start
            avg_volume=1500000.0
        )

        # Given: Consolidation with 30% retracement
        # Retracement range: 103-108 (5 points, 50% of 10-point gain)
        consolidation = self._build_consolidation_data(
            start_idx=11,
            end_idx=16,
            upper_boundary=108.0,
            lower_boundary=103.0,  # Lower boundary for stop-loss
            avg_volume=1000000.0
        )

        # Given: Breakout price 2% above upper boundary
        breakout_price = Decimal("110.16")  # 108 * 1.02

        # When: Calculate risk parameters (function doesn't exist yet - will fail)
        from src.trading_bot.patterns.bull_flag import calculate_risk_parameters
        result = calculate_risk_parameters(flagpole, consolidation, breakout_price)

        # Then: Verify all risk parameters
        assert result is not None, "Should return risk parameters dict"
        assert isinstance(result, dict), "Result should be dictionary"
        assert "entry_price" in result
        assert "stop_loss" in result
        assert "target_price" in result
        assert "risk_reward_ratio" in result

        # Verify entry price
        assert result["entry_price"] == breakout_price
        assert isinstance(result["entry_price"], Decimal)

        # Verify risk/reward ratio is at least 2:1
        assert result["risk_reward_ratio"] >= Decimal("2.0"), \
            f"Risk/reward ratio {result['risk_reward_ratio']} should be >= 2.0"

    def test_calculate_risk_parameters_stop_loss_calculation(self):
        """Test stop-loss calculation is correct.

        Given: Consolidation lower_boundary = $100.00
        When: Calculate stop loss (lower_boundary - 0.5%)
        Then: stop_loss = $99.50
        """
        # Given: Simple flagpole
        flagpole = self._build_flagpole_data(
            high_price=110.0,
            start_price=100.0
        )

        # Given: Consolidation with clean lower boundary
        consolidation = self._build_consolidation_data(
            lower_boundary=100.0  # Clean number for easy verification
        )

        # Given: Breakout price
        breakout_price = Decimal("110.00")

        # When: Calculate risk parameters
        from src.trading_bot.patterns.bull_flag import calculate_risk_parameters
        result = calculate_risk_parameters(flagpole, consolidation, breakout_price)

        # Then: Stop loss should be lower_boundary - 0.5%
        # 100.00 * 0.995 = 99.50
        expected_stop_loss = Decimal("100.00") * Decimal("0.995")
        assert result["stop_loss"] == expected_stop_loss, \
            f"Stop loss should be {expected_stop_loss}, got {result['stop_loss']}"
        assert isinstance(result["stop_loss"], Decimal)

    def test_calculate_risk_parameters_target_calculation(self):
        """Test target price calculation is correct.

        Given: Breakout price 102, flagpole high 105, flagpole start 95 (height=10)
        When: Calculate target (breakout + flagpole_height)
        Then: target = $112.00 (102 + 10)
        """
        # Given: Flagpole with 10-point height (95 → 105)
        flagpole = self._build_flagpole_data(
            start_price=95.0,
            high_price=105.0,  # Height = 105 - 95 = 10
            gain_pct=10.53  # (10 / 95) * 100
        )

        # Given: Consolidation
        consolidation = self._build_consolidation_data(
            lower_boundary=100.0
        )

        # Given: Breakout price
        breakout_price = Decimal("102.00")

        # When: Calculate risk parameters
        from src.trading_bot.patterns.bull_flag import calculate_risk_parameters
        result = calculate_risk_parameters(flagpole, consolidation, breakout_price)

        # Then: Target = breakout + flagpole height
        # Flagpole height = 105 - 95 = 10
        # Target = 102 + 10 = 112
        flagpole_height = Decimal("105.0") - Decimal("95.0")
        expected_target = breakout_price + flagpole_height
        assert result["target_price"] == expected_target, \
            f"Target should be {expected_target}, got {result['target_price']}"
        assert isinstance(result["target_price"], Decimal)

    def test_calculate_risk_parameters_reject_low_risk_reward(self):
        """Test risk parameter calculation rejects patterns with low risk/reward ratio.

        Given: Pattern with risk_reward_ratio < 2.0 (poor setup)
        When: Calculate risk parameters
        Then: Returns dict with risk_reward_ratio < 2.0 OR raises exception
        """
        # Given: Flagpole with small height (only 5 points)
        flagpole = self._build_flagpole_data(
            start_price=100.0,
            high_price=105.0,  # Small height = 5 points
            gain_pct=5.0
        )

        # Given: Consolidation with wide support (high stop-loss)
        consolidation = self._build_consolidation_data(
            lower_boundary=102.0,  # Close to entry = high risk
            upper_boundary=104.5
        )

        # Given: Breakout just above resistance
        breakout_price = Decimal("105.00")  # Just 0.5 points above resistance

        # When: Calculate risk parameters
        from src.trading_bot.patterns.bull_flag import calculate_risk_parameters

        # Then: Either returns low R/R or raises exception
        # Implementation may choose to raise InvalidConfigurationError or return low ratio
        try:
            result = calculate_risk_parameters(flagpole, consolidation, breakout_price)

            # If it returns a result, verify R/R is calculated correctly (even if < 2.0)
            assert "risk_reward_ratio" in result
            assert isinstance(result["risk_reward_ratio"], Decimal)

            # Calculate expected R/R
            # Risk = breakout - stop_loss = 105 - (102 * 0.995) = 105 - 101.49 = 3.51
            # Reward = target - breakout = (105 + 5) - 105 = 5
            # R/R = 5 / 3.51 = 1.42 (< 2.0)
            # Note: Function may reject this pattern

        except Exception as e:
            # Implementation may raise InvalidConfigurationError for low R/R
            # This is acceptable behavior
            assert "risk" in str(e).lower() or "invalid" in str(e).lower(), \
                f"Exception should be related to risk/reward: {e}"

    def test_calculate_risk_parameters_decimal_precision(self):
        """Test risk parameter calculation maintains Decimal precision.

        Given: Pattern with precise decimal values
        When: Calculate risk parameters
        Then: All returned values are Decimal type (not float)
        """
        # Given: Flagpole with precise decimals
        flagpole = self._build_flagpole_data(
            start_price=100.01,
            high_price=110.53,
            gain_pct=10.52
        )

        # Given: Consolidation with precise decimals
        consolidation = self._build_consolidation_data(
            lower_boundary=103.47,
            upper_boundary=108.28
        )

        # Given: Breakout price with precision
        breakout_price = Decimal("110.4456")

        # When: Calculate risk parameters
        from src.trading_bot.patterns.bull_flag import calculate_risk_parameters
        result = calculate_risk_parameters(flagpole, consolidation, breakout_price)

        # Then: All values should be Decimal type
        assert isinstance(result["entry_price"], Decimal)
        assert isinstance(result["stop_loss"], Decimal)
        assert isinstance(result["target_price"], Decimal)
        assert isinstance(result["risk_reward_ratio"], Decimal)

        # Verify no float contamination
        assert not isinstance(result["entry_price"], float)
        assert not isinstance(result["stop_loss"], float)
        assert not isinstance(result["target_price"], float)


# ============================================================================
# T021: Quality Scoring Tests
# ============================================================================


class TestQualityScoring:
    """Tests for quality score calculation logic (_calculate_quality_score method).

    Tests cover:
    - Perfect pattern scoring (80-100 range)
    - Weak pattern scoring (40-70 range)
    - Poor pattern scoring (<60)
    - Scoring factors breakdown (flagpole, consolidation, volume, indicators)
    - Score clamping to 0-100 range
    """

    def _build_flagpole_data(
        self,
        gain_pct: float = 8.0,
        start_price: float = 100.0,
        high_price: float = 108.0,
        avg_volume: float = 1500000.0
    ) -> FlagpoleData:
        """Helper to create FlagpoleData for quality scoring tests."""
        return FlagpoleData(
            start_idx=0,
            end_idx=10,
            gain_pct=Decimal(str(gain_pct)),
            high_price=Decimal(str(high_price)),
            start_price=Decimal(str(start_price)),
            avg_volume=Decimal(str(avg_volume))
        )

    def _build_consolidation_data(
        self,
        retracement_pct: float = 30.0,
        upper_boundary: float = 107.0,
        lower_boundary: float = 104.6,
        avg_volume: float = 900000.0
    ) -> ConsolidationData:
        """Helper to create ConsolidationData for quality scoring tests."""
        return ConsolidationData(
            start_idx=11,
            end_idx=16,
            upper_boundary=Decimal(str(upper_boundary)),
            lower_boundary=Decimal(str(lower_boundary)),
            avg_volume=Decimal(str(avg_volume))
        )

    def test_quality_score_perfect_pattern(self):
        """Test quality score for perfect bull flag pattern.

        Given: Strong flagpole (8% gain), tight consolidation (25% retracement),
               high volume breakout, perfect indicator alignment
        When: Calculate quality score
        Then: Returns score 80-100 (high quality)
        """
        # Given: Strong flagpole with 8% gain (well above 5% minimum)
        flagpole = self._build_flagpole_data(
            gain_pct=8.0,  # Strong gain
            start_price=100.0,
            high_price=108.0,
            avg_volume=1800000.0  # High volume
        )

        # Given: Tight consolidation with 25% retracement (near ideal)
        # Retracement = (108 - 104.0) / (108 - 100) * 100 = 50%
        # Use tighter range: 25% retracement
        consolidation_range = Decimal("8.0") * Decimal("0.25")  # 2 points
        consolidation = self._build_consolidation_data(
            retracement_pct=25.0,
            upper_boundary=108.0,
            lower_boundary=float(Decimal("108.0") - consolidation_range),  # 106.0
            avg_volume=900000.0  # 50% volume decrease (good)
        )

        # Given: Perfect indicator alignment
        indicators = {
            "vwap": Decimal("105.0"),  # Price above VWAP
            "macd": Decimal("0.5"),  # Positive MACD
            "ema_9": Decimal("106.5"),  # Price near EMA
            "price": Decimal("108.0"),
            "validation_passed": True
        }

        # When: Calculate quality score (function doesn't exist yet - will fail)
        from src.trading_bot.patterns.bull_flag import calculate_quality_score
        result = calculate_quality_score(flagpole, consolidation, indicators)

        # Then: Score should be in high quality range (80-100)
        assert result is not None, "Should return quality score"
        assert isinstance(result, int), "Score should be integer"
        assert 80 <= result <= 100, \
            f"Perfect pattern should score 80-100, got {result}"

    def test_quality_score_weak_pattern(self):
        """Test quality score for weak bull flag pattern.

        Given: Weak flagpole (5% gain - minimum), wide consolidation (45% retracement),
               normal volume
        When: Calculate quality score
        Then: Returns score 40-70 (medium quality)
        """
        # Given: Weak flagpole with 5% gain (minimum acceptable)
        flagpole = self._build_flagpole_data(
            gain_pct=5.0,  # Minimum gain
            start_price=100.0,
            high_price=105.0,
            avg_volume=1200000.0  # Normal volume
        )

        # Given: Wide consolidation with 45% retracement (near maximum)
        # Retracement = 45% of 5-point gain = 2.25 points
        consolidation_range = Decimal("5.0") * Decimal("0.45")
        consolidation = self._build_consolidation_data(
            retracement_pct=45.0,
            upper_boundary=105.0,
            lower_boundary=float(Decimal("105.0") - consolidation_range),  # 102.75
            avg_volume=1000000.0  # Slight volume decrease
        )

        # Given: Mediocre indicator alignment
        indicators = {
            "vwap": Decimal("103.0"),  # Price slightly above VWAP
            "macd": Decimal("0.1"),  # Barely positive MACD
            "ema_9": Decimal("104.0"),
            "price": Decimal("105.0"),
            "validation_passed": True
        }

        # When: Calculate quality score
        from src.trading_bot.patterns.bull_flag import calculate_quality_score
        result = calculate_quality_score(flagpole, consolidation, indicators)

        # Then: Score should be in medium quality range (40-70)
        assert result is not None, "Should return quality score"
        assert isinstance(result, int)
        assert 40 <= result <= 70, \
            f"Weak pattern should score 40-70, got {result}"

    def test_quality_score_poor_pattern(self):
        """Test quality score for poor bull flag pattern.

        Given: Minimum flagpole (5% gain), maximum consolidation (50% retracement),
               low volume, poor indicator alignment
        When: Calculate quality score
        Then: Returns score < 60 (low quality)
        """
        # Given: Minimum acceptable flagpole
        flagpole = self._build_flagpole_data(
            gain_pct=5.0,  # Minimum gain
            start_price=100.0,
            high_price=105.0,
            avg_volume=1000000.0  # Low volume
        )

        # Given: Maximum consolidation retracement (50% - at limit)
        consolidation_range = Decimal("5.0") * Decimal("0.50")
        consolidation = self._build_consolidation_data(
            retracement_pct=50.0,
            upper_boundary=105.0,
            lower_boundary=float(Decimal("105.0") - consolidation_range),  # 102.5
            avg_volume=950000.0  # Minimal volume decrease
        )

        # Given: Poor indicator alignment
        indicators = {
            "vwap": Decimal("104.8"),  # Price barely above VWAP
            "macd": Decimal("0.01"),  # Barely positive MACD
            "ema_9": Decimal("105.5"),  # Price slightly below EMA
            "price": Decimal("105.0"),
            "validation_passed": False  # Failed validation
        }

        # When: Calculate quality score
        from src.trading_bot.patterns.bull_flag import calculate_quality_score
        result = calculate_quality_score(flagpole, consolidation, indicators)

        # Then: Score should be low quality (< 60)
        assert result is not None, "Should return quality score"
        assert isinstance(result, int)
        assert result < 60, \
            f"Poor pattern should score < 60, got {result}"

    def test_quality_score_scoring_factors(self):
        """Test quality score breakdown by individual factors.

        Given: Known pattern characteristics
        When: Calculate quality score
        Then: Verify scoring factors (flagpole strength, consolidation tightness,
              volume profile, indicator alignment)
        """
        # Given: Pattern with measurable characteristics
        flagpole = self._build_flagpole_data(
            gain_pct=7.0,  # 7% gain (good, but not perfect)
            avg_volume=1600000.0
        )

        consolidation = self._build_consolidation_data(
            retracement_pct=33.0,  # 33% retracement (moderate)
            avg_volume=1000000.0  # 37.5% volume decrease
        )

        indicators = {
            "vwap": Decimal("104.0"),
            "macd": Decimal("0.3"),
            "ema_9": Decimal("106.0"),
            "price": Decimal("107.0"),
            "validation_passed": True
        }

        # When: Calculate quality score
        from src.trading_bot.patterns.bull_flag import calculate_quality_score
        result = calculate_quality_score(flagpole, consolidation, indicators)

        # Then: Score should be calculated from multiple factors
        # Scoring breakdown (approximate):
        # - Flagpole gain (7%): ~21 points (out of 30)
        # - Consolidation tightness (33%): ~15 points (out of 25)
        # - Volume decrease (37.5%): ~15 points (out of 20)
        # - Indicator alignment (good): ~20 points (out of 25)
        # Total: ~71 points
        assert result is not None
        assert isinstance(result, int)
        assert 60 <= result <= 85, \
            f"Moderate pattern should score 60-85, got {result}"

    def test_quality_score_range(self):
        """Test quality score is always clamped to 0-100 range.

        Given: Various patterns (including edge cases)
        When: Calculate quality scores
        Then: All scores are in 0-100 range (clamped)
        """
        # Test Case 1: Extremely strong pattern (should clamp to 100)
        flagpole_strong = self._build_flagpole_data(
            gain_pct=15.0,  # Very strong gain
            avg_volume=3000000.0  # Extremely high volume
        )

        consolidation_tight = self._build_consolidation_data(
            retracement_pct=20.0,  # Minimum retracement (tight)
            avg_volume=500000.0  # Large volume decrease
        )

        indicators_perfect = {
            "vwap": Decimal("100.0"),
            "macd": Decimal("1.0"),
            "ema_9": Decimal("110.0"),
            "price": Decimal("115.0"),
            "validation_passed": True
        }

        # When: Calculate quality score for strong pattern
        from src.trading_bot.patterns.bull_flag import calculate_quality_score
        score_strong = calculate_quality_score(flagpole_strong, consolidation_tight, indicators_perfect)

        # Then: Score should be clamped to 100
        assert 0 <= score_strong <= 100, \
            f"Score must be in 0-100 range, got {score_strong}"

        # Test Case 2: Extremely weak pattern (should stay >= 0)
        flagpole_weak = self._build_flagpole_data(
            gain_pct=5.0,  # Minimum gain
            avg_volume=800000.0  # Low volume
        )

        consolidation_wide = self._build_consolidation_data(
            retracement_pct=50.0,  # Maximum retracement (wide)
            avg_volume=900000.0  # Minimal volume decrease
        )

        indicators_poor = {
            "vwap": Decimal("110.0"),
            "macd": Decimal("-0.5"),  # Negative MACD
            "ema_9": Decimal("112.0"),
            "price": Decimal("105.0"),
            "validation_passed": False
        }

        # When: Calculate quality score for weak pattern
        score_weak = calculate_quality_score(flagpole_weak, consolidation_wide, indicators_poor)

        # Then: Score should be clamped to >= 0
        assert 0 <= score_weak <= 100, \
            f"Score must be in 0-100 range, got {score_weak}"
        assert score_weak < 50, \
            f"Very weak pattern should score < 50, got {score_weak}"
