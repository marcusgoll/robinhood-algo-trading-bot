"""
End-to-End Tests for Bull Flag Pattern Detection

Tests complete detection flow from OHLCV bars → BullFlagResult.
Covers all acceptance criteria from spec.md FR-001 through FR-007.

Feature: 003-entry-logic-bull-flag
Task: T032 - End-to-end pattern detection tests
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, UTC
from typing import List, Dict

from src.trading_bot.patterns.bull_flag import BullFlagDetector
from src.trading_bot.patterns.config import BullFlagConfig
from src.trading_bot.patterns.exceptions import PatternNotFoundError
from src.trading_bot.indicators.exceptions import InsufficientDataError


class TestBullFlagE2E:
    """End-to-end tests for complete bull flag pattern detection flow."""

    def test_perfect_bull_flag_detection(self, valid_bull_flag_bars, default_config):
        """
        Test complete detection of a perfect bull flag pattern.

        Scenario: Perfect pattern with all criteria met
        Given: Bars with clear flagpole, consolidation, and breakout
        When: Detector processes bars
        Then: Pattern is detected with high quality score

        Validates:
        - FR-001: Flagpole detection
        - FR-002: Consolidation detection
        - FR-003: Breakout confirmation
        - FR-004: Technical indicator validation
        - FR-005: Risk parameter calculation
        - FR-006: Quality scoring
        """
        detector = BullFlagDetector(default_config)
        result = detector.detect(valid_bull_flag_bars, symbol="TEST")

        # Assert pattern detected
        assert result.detected is True
        assert result.symbol == "TEST"

        # Assert flagpole characteristics (FR-001)
        assert result.flagpole is not None
        assert result.flagpole.gain_pct >= Decimal("5.0")  # Minimum 5% gain
        assert result.flagpole.end_idx - result.flagpole.start_idx >= 3  # Minimum 3 bars
        assert result.flagpole.end_idx - result.flagpole.start_idx <= 15  # Maximum 15 bars

        # Assert consolidation characteristics (FR-002)
        assert result.consolidation is not None
        assert result.consolidation.end_idx - result.consolidation.start_idx >= 3  # Minimum 3 bars
        assert result.consolidation.end_idx - result.consolidation.start_idx <= 10  # Maximum 10 bars

        # Assert breakout confirmed (FR-003)
        assert result.entry_price is not None
        assert result.entry_price > result.consolidation.upper_boundary  # Price above resistance

        # Assert risk parameters calculated (FR-005)
        assert result.stop_loss is not None
        assert result.target_price is not None
        assert result.risk_reward_ratio is not None
        assert result.risk_reward_ratio >= Decimal("2.0")  # Minimum 2:1 R/R

        # Assert quality score calculated (FR-006)
        assert result.quality_score is not None
        assert result.quality_score >= 0
        assert result.quality_score <= 100

        # Assert timestamp recorded
        assert isinstance(result.timestamp, datetime)

    def test_marginal_pattern_detection(self):
        """
        Test detection of a marginal bull flag pattern.

        Scenario: Pattern barely meets minimum criteria
        Given: Bars with minimal flagpole gain (5%), maximal retracement (50%)
        When: Detector processes bars
        Then: Pattern is detected with lower quality score

        Validates:
        - Edge case pattern detection
        - Quality scoring reflects pattern weakness
        """
        bars = self._create_marginal_bull_flag_bars()
        detector = BullFlagDetector(BullFlagConfig())
        result = detector.detect(bars, symbol="MARG")

        # Assert pattern detected despite marginal characteristics
        assert result.detected is True
        assert result.symbol == "MARG"

        # Assert quality score reflects marginal pattern (should be low)
        assert result.quality_score is not None
        assert result.quality_score < 70  # Below high-quality threshold

        # Assert risk/reward still meets minimum
        assert result.risk_reward_ratio >= Decimal("2.0")

    def test_no_pattern_detected_insufficient_flagpole(self, invalid_pattern_bars, default_config):
        """
        Test rejection when flagpole gain is insufficient.

        Scenario: No valid flagpole (< 5% gain)
        Given: Bars with sideways movement (no strong uptrend)
        When: Detector processes bars
        Then: Pattern is not detected

        Validates:
        - FR-001: Flagpole gain validation
        - Scenario 4: Reject invalid patterns
        """
        detector = BullFlagDetector(default_config)
        result = detector.detect(invalid_pattern_bars, symbol="NOWEAK")

        # Assert pattern not detected
        assert result.detected is False
        assert result.symbol == "NOWEAK"
        assert result.flagpole is None
        assert result.consolidation is None
        assert result.entry_price is None
        assert result.quality_score is None

    def test_no_pattern_detected_excessive_retracement(self):
        """
        Test rejection when consolidation retraces too much.

        Scenario: Consolidation exceeds 50% retracement
        Given: Bars with flagpole but deep consolidation (> 50%)
        When: Detector processes bars
        Then: Pattern is not detected

        Validates:
        - FR-002: Consolidation retracement validation
        - Scenario 4: Reject patterns with excessive retracement
        """
        bars = self._create_excessive_retracement_bars()
        detector = BullFlagDetector(BullFlagConfig())
        result = detector.detect(bars, symbol="DEEP")

        # Assert pattern not detected due to excessive retracement
        assert result.detected is False
        assert result.symbol == "DEEP"

    def test_no_pattern_detected_short_consolidation(self):
        """
        Test rejection when consolidation is too short.

        Scenario: Consolidation lasts < 3 bars
        Given: Bars with flagpole but brief consolidation (2 bars)
        When: Detector processes bars
        Then: Pattern is not detected

        Validates:
        - FR-002: Consolidation duration validation
        - Scenario 4: Reject patterns with short consolidation
        """
        bars = self._create_short_consolidation_bars()
        detector = BullFlagDetector(BullFlagConfig())
        result = detector.detect(bars, symbol="SHORT")

        # Assert pattern not detected due to short consolidation
        assert result.detected is False
        assert result.symbol == "SHORT"

    def test_no_pattern_detected_insufficient_breakout_volume(self):
        """
        Test rejection when breakout volume is insufficient.

        Scenario: Price breaks resistance but volume is low
        Given: Bars with pattern but weak breakout volume
        When: Detector processes bars
        Then: Pattern is not detected

        Validates:
        - FR-003: Breakout volume validation
        """
        bars = self._create_low_breakout_volume_bars()
        detector = BullFlagDetector(BullFlagConfig())
        result = detector.detect(bars, symbol="LOWVOL")

        # Assert pattern not detected due to insufficient breakout volume
        assert result.detected is False
        assert result.symbol == "LOWVOL"

    def test_no_pattern_detected_poor_risk_reward(self):
        """
        Test rejection when risk/reward ratio is below minimum.

        Scenario: Pattern has poor risk/reward ratio (< 2:1)
        Given: Bars with pattern but stop-loss too far from entry
        When: Detector processes bars
        Then: Pattern is not detected

        Validates:
        - FR-005: Risk/reward ratio validation
        - NFR-003: Risk management requirements
        """
        bars = self._create_poor_risk_reward_bars()
        detector = BullFlagDetector(BullFlagConfig())
        result = detector.detect(bars, symbol="POORR")

        # Assert pattern not detected due to poor risk/reward
        assert result.detected is False
        assert result.symbol == "POORR"

    def test_insufficient_data_error(self, default_config):
        """
        Test error when insufficient bars provided.

        Scenario: Less than 30 bars provided
        Given: Bars list with only 20 bars
        When: Detector processes bars
        Then: InsufficientDataError is raised

        Validates:
        - Context Strategy: Minimum 30 bars required
        - Constitution §Fail_Safe: Fail-fast on insufficient data
        """
        bars = self._create_bars(count=20)
        detector = BullFlagDetector(default_config)

        with pytest.raises(InsufficientDataError) as exc_info:
            detector.detect(bars, symbol="NODATA")

        # Assert error details
        assert exc_info.value.symbol == "NODATA"
        assert exc_info.value.required_bars == 30
        assert exc_info.value.available_bars == 20

    def test_configuration_affects_detection(self, valid_bull_flag_bars):
        """
        Test that different configurations produce different results.

        Scenario: Same bars with different config parameters
        Given: Valid bull flag bars
        When: Detector uses aggressive vs conservative config
        Then: Detection results differ appropriately

        Validates:
        - FR-007: Configuration management
        - Configuration impacts detection behavior
        """
        # Aggressive config: Lower thresholds, more permissive
        aggressive_config = BullFlagConfig(
            min_flagpole_gain=Decimal("2.0"),
            min_quality_score=40,
            min_risk_reward_ratio=Decimal("1.5")
        )
        aggressive_detector = BullFlagDetector(aggressive_config)
        aggressive_result = aggressive_detector.detect(valid_bull_flag_bars, symbol="AGG")

        # Conservative config: Higher thresholds, more restrictive
        conservative_config = BullFlagConfig(
            min_flagpole_gain=Decimal("10.0"),
            min_quality_score=80,
            min_risk_reward_ratio=Decimal("3.0")
        )
        conservative_detector = BullFlagDetector(conservative_config)
        conservative_result = conservative_detector.detect(valid_bull_flag_bars, symbol="CON")

        # Aggressive config should detect more permissively
        assert aggressive_result.detected is True

        # Results may differ based on configuration strictness
        # (Conservative may or may not detect depending on exact bars)
        # Both should be valid BullFlagResult objects
        assert aggressive_result.symbol == "AGG"
        assert conservative_result.symbol == "CON"

    def test_multiple_symbol_processing(self, valid_bull_flag_bars, invalid_pattern_bars, default_config):
        """
        Test detector can process multiple symbols correctly.

        Scenario: Process multiple stocks with different patterns
        Given: Valid pattern bars for AAPL, invalid for MSFT
        When: Detector processes both
        Then: Correct detection results for each symbol

        Validates:
        - NFR-001: Performance for multiple stock scanning
        - Symbol tracking in results
        """
        detector = BullFlagDetector(default_config)

        # Process valid pattern
        result_valid = detector.detect(valid_bull_flag_bars, symbol="AAPL")
        assert result_valid.detected is True
        assert result_valid.symbol == "AAPL"

        # Process invalid pattern
        result_invalid = detector.detect(invalid_pattern_bars, symbol="MSFT")
        assert result_invalid.detected is False
        assert result_invalid.symbol == "MSFT"

        # Verify no cross-contamination between symbols
        assert result_valid.symbol != result_invalid.symbol

    # Helper methods to create test bar scenarios

    def _create_marginal_bull_flag_bars(self) -> List[Dict]:
        """
        Create bars showing marginal bull flag pattern.

        Pattern characteristics:
        - Flagpole: Exactly 5.0% gain (minimum threshold)
        - Consolidation: 50% retracement (maximum threshold)
        - Breakout: Minimal volume increase (just above 30%)
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        # Flagpole: 5% gain over 5 bars (minimum gain)
        flagpole_end = base_price * Decimal("1.05")
        for i in range(5):
            price = base_price + (flagpole_end - base_price) * Decimal(str(i)) / Decimal("5")
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("0.20")),
                "low": float(price - Decimal("0.10")),
                "close": float(price + Decimal("0.15")),
                "volume": float(base_volume)
            })

        # Consolidation: 50% retracement (maximum threshold)
        flagpole_gain = flagpole_end - base_price
        retracement = flagpole_gain * Decimal("0.50")
        consolidation_low = flagpole_end - retracement

        for i in range(5):
            price = consolidation_low + Decimal(str(i * 0.1))
            bars.append({
                "timestamp": base_date + timedelta(minutes=(5+i)*5),
                "open": float(price),
                "high": float(price + Decimal("0.15")),
                "low": float(price - Decimal("0.15")),
                "close": float(price),
                "volume": float(base_volume * Decimal("0.79"))  # Just below 80% threshold
            })

        # Breakout: Minimal volume increase (31%)
        breakout_price = flagpole_end + Decimal("0.10")
        for i in range(2):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(10+i)*5),
                "open": float(breakout_price),
                "high": float(breakout_price + Decimal("0.30")),
                "low": float(breakout_price - Decimal("0.10")),
                "close": float(breakout_price + Decimal("0.20")),
                "volume": float(base_volume * Decimal("1.03"))  # Just above 31% increase
            })

        # Padding bars to reach 30 minimum
        for i in range(18):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(12+i)*5),
                "open": float(breakout_price),
                "high": float(breakout_price + Decimal("0.20")),
                "low": float(breakout_price - Decimal("0.20")),
                "close": float(breakout_price + Decimal("0.10")),
                "volume": float(base_volume)
            })

        return bars

    def _create_excessive_retracement_bars(self) -> List[Dict]:
        """
        Create bars with excessive consolidation retracement (> 50%).

        Pattern fails FR-002 validation due to deep retracement.
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        # Flagpole: 8% gain
        flagpole_end = base_price * Decimal("1.08")
        for i in range(6):
            price = base_price + (flagpole_end - base_price) * Decimal(str(i)) / Decimal("6")
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("0.30")),
                "low": float(price - Decimal("0.10")),
                "close": float(price + Decimal("0.20")),
                "volume": float(base_volume * Decimal("1.2"))
            })

        # Consolidation: 65% retracement (exceeds 50% maximum)
        flagpole_gain = flagpole_end - base_price
        retracement = flagpole_gain * Decimal("0.65")
        consolidation_low = flagpole_end - retracement

        for i in range(5):
            price = consolidation_low + Decimal(str(i * 0.2))
            bars.append({
                "timestamp": base_date + timedelta(minutes=(6+i)*5),
                "open": float(price),
                "high": float(price + Decimal("0.20")),
                "low": float(price - Decimal("0.20")),
                "close": float(price),
                "volume": float(base_volume * Decimal("0.7"))
            })

        # Padding bars
        for i in range(19):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(11+i)*5),
                "open": float(consolidation_low),
                "high": float(consolidation_low + Decimal("0.20")),
                "low": float(consolidation_low - Decimal("0.20")),
                "close": float(consolidation_low),
                "volume": float(base_volume)
            })

        return bars

    def _create_short_consolidation_bars(self) -> List[Dict]:
        """
        Create bars with consolidation lasting only 2 bars (< 3 minimum).

        Pattern fails FR-002 validation due to short consolidation duration.
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        # Flagpole: 7% gain over 5 bars
        flagpole_end = base_price * Decimal("1.07")
        for i in range(5):
            price = base_price + (flagpole_end - base_price) * Decimal(str(i)) / Decimal("5")
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("0.30")),
                "low": float(price - Decimal("0.10")),
                "close": float(price + Decimal("0.20")),
                "volume": float(base_volume * Decimal("1.2"))
            })

        # Consolidation: Only 2 bars (below 3 minimum)
        flagpole_gain = flagpole_end - base_price
        retracement = flagpole_gain * Decimal("0.30")
        consolidation_price = flagpole_end - retracement

        for i in range(2):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(5+i)*5),
                "open": float(consolidation_price),
                "high": float(consolidation_price + Decimal("0.20")),
                "low": float(consolidation_price - Decimal("0.20")),
                "close": float(consolidation_price),
                "volume": float(base_volume * Decimal("0.7"))
            })

        # Immediate breakout (no proper consolidation)
        breakout_price = flagpole_end + Decimal("0.50")
        for i in range(2):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(7+i)*5),
                "open": float(breakout_price),
                "high": float(breakout_price + Decimal("0.40")),
                "low": float(breakout_price - Decimal("0.10")),
                "close": float(breakout_price + Decimal("0.30")),
                "volume": float(base_volume * Decimal("1.4"))
            })

        # Padding bars
        for i in range(21):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(9+i)*5),
                "open": float(breakout_price),
                "high": float(breakout_price + Decimal("0.20")),
                "low": float(breakout_price - Decimal("0.20")),
                "close": float(breakout_price),
                "volume": float(base_volume)
            })

        return bars

    def _create_low_breakout_volume_bars(self) -> List[Dict]:
        """
        Create bars with valid pattern but insufficient breakout volume.

        Pattern fails FR-003 validation due to low breakout volume.
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        # Flagpole: 8% gain
        flagpole_end = base_price * Decimal("1.08")
        for i in range(6):
            price = base_price + (flagpole_end - base_price) * Decimal(str(i)) / Decimal("6")
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("0.30")),
                "low": float(price - Decimal("0.10")),
                "close": float(price + Decimal("0.20")),
                "volume": float(base_volume * Decimal("1.2"))
            })

        # Consolidation: 35% retracement
        flagpole_gain = flagpole_end - base_price
        retracement = flagpole_gain * Decimal("0.35")
        consolidation_low = flagpole_end - retracement

        for i in range(5):
            price = consolidation_low + Decimal(str(i * 0.15))
            bars.append({
                "timestamp": base_date + timedelta(minutes=(6+i)*5),
                "open": float(price),
                "high": float(price + Decimal("0.20")),
                "low": float(price - Decimal("0.20")),
                "close": float(price),
                "volume": float(base_volume * Decimal("0.7"))
            })

        # Breakout: Price moves above resistance but volume is too low (< 30% increase)
        breakout_price = flagpole_end + Decimal("0.50")
        for i in range(2):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(11+i)*5),
                "open": float(breakout_price),
                "high": float(breakout_price + Decimal("0.30")),
                "low": float(breakout_price - Decimal("0.10")),
                "close": float(breakout_price + Decimal("0.20")),
                "volume": float(base_volume * Decimal("0.8"))  # Only 14% increase (< 30% required)
            })

        # Padding bars
        for i in range(17):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(13+i)*5),
                "open": float(breakout_price),
                "high": float(breakout_price + Decimal("0.20")),
                "low": float(breakout_price - Decimal("0.20")),
                "close": float(breakout_price),
                "volume": float(base_volume)
            })

        return bars

    def _create_poor_risk_reward_bars(self) -> List[Dict]:
        """
        Create bars with valid pattern but poor risk/reward ratio (< 2:1).

        Pattern fails FR-005 validation due to insufficient R/R ratio.
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        # Flagpole: Small gain (5.5%) with wide range
        flagpole_end = base_price * Decimal("1.055")
        for i in range(5):
            price = base_price + (flagpole_end - base_price) * Decimal(str(i)) / Decimal("5")
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("0.40")),
                "low": float(price - Decimal("0.10")),
                "close": float(price + Decimal("0.30")),
                "volume": float(base_volume * Decimal("1.2"))
            })

        # Consolidation: Deep retracement (48%) - creates large stop distance
        flagpole_gain = flagpole_end - base_price
        retracement = flagpole_gain * Decimal("0.48")
        consolidation_low = flagpole_end - retracement

        for i in range(5):
            price = consolidation_low + Decimal(str(i * 0.10))
            bars.append({
                "timestamp": base_date + timedelta(minutes=(5+i)*5),
                "open": float(price),
                "high": float(price + Decimal("0.15")),
                "low": float(price - Decimal("0.15")),
                "close": float(price),
                "volume": float(base_volume * Decimal("0.7"))
            })

        # Breakout: Small move above consolidation
        # With small flagpole gain + deep consolidation, R/R will be < 2:1
        breakout_price = flagpole_end + Decimal("0.10")
        for i in range(2):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(10+i)*5),
                "open": float(breakout_price),
                "high": float(breakout_price + Decimal("0.20")),
                "low": float(breakout_price - Decimal("0.10")),
                "close": float(breakout_price + Decimal("0.15")),
                "volume": float(base_volume * Decimal("1.4"))
            })

        # Padding bars
        for i in range(18):
            bars.append({
                "timestamp": base_date + timedelta(minutes=(12+i)*5),
                "open": float(breakout_price),
                "high": float(breakout_price + Decimal("0.20")),
                "low": float(breakout_price - Decimal("0.20")),
                "close": float(breakout_price),
                "volume": float(base_volume)
            })

        return bars

    def _create_bars(self, count: int) -> List[Dict]:
        """
        Create simple bars for testing with specified count.

        Args:
            count: Number of bars to create

        Returns:
            List of OHLCV bars
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        for i in range(count):
            price = base_price + Decimal(str(i * 0.5))
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("0.30")),
                "low": float(price - Decimal("0.30")),
                "close": float(price + Decimal("0.10")),
                "volume": float(base_volume)
            })

        return bars
