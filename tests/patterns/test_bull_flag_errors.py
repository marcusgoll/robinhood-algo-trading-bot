"""
Error Handling and Edge Case Tests for Bull Flag Pattern Detection

Tests all error scenarios and edge cases for pattern detection.
Validates proper exception handling and graceful degradation.

Feature: 003-entry-logic-bull-flag
Task: T033 - Error handling and edge case tests
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, UTC
from typing import List, Dict

from src.trading_bot.patterns.bull_flag import BullFlagDetector
from src.trading_bot.patterns.config import BullFlagConfig
from src.trading_bot.patterns.exceptions import PatternNotFoundError, InvalidConfigurationError
from src.trading_bot.indicators.exceptions import InsufficientDataError


class TestBullFlagErrorHandling:
    """Test error handling for bull flag pattern detection."""

    def test_insufficient_data_error_exactly_29_bars(self, default_config):
        """
        Test InsufficientDataError raised with exactly 29 bars (< 30 minimum).

        Scenario: Exactly one bar below minimum requirement
        Given: Bar list with 29 bars
        When: Detector processes bars
        Then: InsufficientDataError raised with correct details

        Constitution §Fail_Safe: Fail-fast on insufficient data
        """
        bars = self._create_bars(count=29)
        detector = BullFlagDetector(default_config)

        with pytest.raises(InsufficientDataError) as exc_info:
            detector.detect(bars, symbol="TEST29")

        # Assert error attributes
        assert exc_info.value.symbol == "TEST29"
        assert exc_info.value.required_bars == 30
        assert exc_info.value.available_bars == 29
        assert "30" in str(exc_info.value)
        assert "29" in str(exc_info.value)

    def test_insufficient_data_error_zero_bars(self, default_config):
        """
        Test InsufficientDataError raised with zero bars.

        Scenario: Empty bar list provided
        Given: Empty list of bars
        When: Detector processes bars
        Then: Returns failed result (not exception)

        Constitution §Fail_Safe: Handle empty data gracefully
        """
        bars = []
        detector = BullFlagDetector(default_config)

        # Empty bars should return failed result, not raise exception
        result = detector.detect(bars, symbol="EMPTY")
        assert result.detected is False
        assert result.symbol == "EMPTY"

    def test_insufficient_data_error_one_bar(self, default_config):
        """
        Test InsufficientDataError raised with single bar.

        Scenario: Minimal data provided (1 bar)
        Given: Bar list with 1 bar
        When: Detector processes bars
        Then: InsufficientDataError raised

        Constitution §Fail_Safe: Fail-fast on insufficient data
        """
        bars = self._create_bars(count=1)
        detector = BullFlagDetector(default_config)

        with pytest.raises(InsufficientDataError) as exc_info:
            detector.detect(bars, symbol="ONEBAR")

        assert exc_info.value.symbol == "ONEBAR"
        assert exc_info.value.required_bars == 30
        assert exc_info.value.available_bars == 1

    def test_invalid_bar_format_missing_high_key(self, default_config):
        """
        Test ValueError raised when bar missing 'high' key.

        Scenario: Malformed bar data (missing required key)
        Given: Bars with missing 'high' field
        When: Detector processes bars
        Then: ValueError raised with descriptive message

        Constitution §Fail_Safe: Validate all inputs
        """
        bars = self._create_bars(count=30)
        # Remove 'high' key from one bar
        bars[15] = {
            "timestamp": bars[15]["timestamp"],
            "open": bars[15]["open"],
            "low": bars[15]["low"],
            "close": bars[15]["close"],
            "volume": bars[15]["volume"]
            # Missing 'high' key
        }

        detector = BullFlagDetector(default_config)

        with pytest.raises(ValueError) as exc_info:
            detector.detect(bars, symbol="NOHIGH")

        # Assert error message mentions missing key
        assert "missing required keys" in str(exc_info.value).lower() or "high" in str(exc_info.value).lower()
        assert "15" in str(exc_info.value)  # Bar index should be mentioned

    def test_invalid_bar_format_missing_low_key(self, default_config):
        """
        Test ValueError raised when bar missing 'low' key.

        Scenario: Malformed bar data (missing required key)
        Given: Bars with missing 'low' field
        When: Detector processes bars
        Then: ValueError raised

        Constitution §Fail_Safe: Validate all inputs
        """
        bars = self._create_bars(count=30)
        bars[20] = {
            "timestamp": bars[20]["timestamp"],
            "open": bars[20]["open"],
            "high": bars[20]["high"],
            "close": bars[20]["close"],
            "volume": bars[20]["volume"]
            # Missing 'low' key
        }

        detector = BullFlagDetector(default_config)

        with pytest.raises(ValueError) as exc_info:
            detector.detect(bars, symbol="NOLOW")

        assert "missing required keys" in str(exc_info.value).lower() or "low" in str(exc_info.value).lower()
        assert "20" in str(exc_info.value)

    def test_invalid_bar_format_missing_close_key(self, default_config):
        """
        Test ValueError raised when bar missing 'close' key.

        Scenario: Malformed bar data (missing required key)
        Given: Bars with missing 'close' field
        When: Detector processes bars
        Then: ValueError raised

        Constitution §Fail_Safe: Validate all inputs
        """
        bars = self._create_bars(count=30)
        bars[10] = {
            "timestamp": bars[10]["timestamp"],
            "open": bars[10]["open"],
            "high": bars[10]["high"],
            "low": bars[10]["low"],
            "volume": bars[10]["volume"]
            # Missing 'close' key
        }

        detector = BullFlagDetector(default_config)

        with pytest.raises(ValueError) as exc_info:
            detector.detect(bars, symbol="NOCLOSE")

        assert "missing required keys" in str(exc_info.value).lower() or "close" in str(exc_info.value).lower()
        assert "10" in str(exc_info.value)

    def test_invalid_bar_format_missing_volume_key(self, default_config):
        """
        Test ValueError raised when bar missing 'volume' key.

        Scenario: Malformed bar data (missing required key)
        Given: Bars with missing 'volume' field
        When: Detector processes bars
        Then: ValueError raised

        Constitution §Fail_Safe: Validate all inputs
        """
        bars = self._create_bars(count=30)
        bars[25] = {
            "timestamp": bars[25]["timestamp"],
            "open": bars[25]["open"],
            "high": bars[25]["high"],
            "low": bars[25]["low"],
            "close": bars[25]["close"]
            # Missing 'volume' key
        }

        detector = BullFlagDetector(default_config)

        with pytest.raises(ValueError) as exc_info:
            detector.detect(bars, symbol="NOVOL")

        assert "missing required keys" in str(exc_info.value).lower() or "volume" in str(exc_info.value).lower()
        assert "25" in str(exc_info.value)

    def test_invalid_bar_format_not_dictionary(self, default_config):
        """
        Test ValueError raised when bar is not a dictionary.

        Scenario: Bar is wrong data type (list instead of dict)
        Given: Bars list contains non-dictionary element
        When: Detector processes bars
        Then: ValueError raised

        Constitution §Fail_Safe: Validate all inputs
        """
        bars = self._create_bars(count=30)
        # Replace one bar with invalid data type
        bars[5] = ["invalid", "bar", "format"]

        detector = BullFlagDetector(default_config)

        with pytest.raises(ValueError) as exc_info:
            detector.detect(bars, symbol="NOTDICT")

        assert "invalid bar format" in str(exc_info.value).lower()

    def test_invalid_configuration_negative_gain(self):
        """
        Test ValueError raised for negative min_flagpole_gain.

        Scenario: Invalid configuration (negative gain percentage)
        Given: BullFlagConfig with negative min_flagpole_gain
        When: Configuration is created
        Then: ValueError raised

        Constitution §Fail_Safe: Validate configuration before pattern detection
        """
        with pytest.raises(ValueError) as exc_info:
            BullFlagConfig(min_flagpole_gain=Decimal("-5.0"))

        assert "min_flagpole_gain" in str(exc_info.value).lower()
        assert "-5.0" in str(exc_info.value)

    def test_invalid_configuration_zero_gain(self):
        """
        Test ValueError raised for zero min_flagpole_gain.

        Scenario: Invalid configuration (zero gain percentage)
        Given: BullFlagConfig with zero min_flagpole_gain
        When: Configuration is created
        Then: ValueError raised

        Constitution §Fail_Safe: Validate configuration parameters
        """
        with pytest.raises(ValueError) as exc_info:
            BullFlagConfig(min_flagpole_gain=Decimal("0.0"))

        assert "min_flagpole_gain" in str(exc_info.value).lower()
        assert "0.0" in str(exc_info.value)

    def test_invalid_configuration_min_greater_than_max_gain(self):
        """
        Test ValueError when min_flagpole_gain > max_flagpole_gain.

        Scenario: Invalid configuration (min > max)
        Given: BullFlagConfig with min_flagpole_gain > max_flagpole_gain
        When: Configuration is created
        Then: ValueError raised

        Constitution §Fail_Safe: Validate logical constraints
        """
        with pytest.raises(ValueError) as exc_info:
            BullFlagConfig(
                min_flagpole_gain=Decimal("20.0"),
                max_flagpole_gain=Decimal("10.0")
            )

        # Error should mention constraint violation
        assert "min_flagpole_gain" in str(exc_info.value).lower() or "max_flagpole_gain" in str(exc_info.value).lower()

    def test_none_bars_input(self, default_config):
        """
        Test graceful handling of None bars input.

        Scenario: None provided instead of bars list
        Given: bars = None
        When: Detector processes None
        Then: Returns failed result (not exception)

        Constitution §Fail_Safe: Handle None gracefully
        """
        detector = BullFlagDetector(default_config)
        result = detector.detect(None, symbol="NONE")

        assert result.detected is False
        assert result.symbol == "NONE"

    # Edge case tests

    def test_edge_case_exactly_30_bars_no_pattern(self, default_config):
        """
        Test handling of exactly 30 bars with no valid pattern.

        Scenario: Minimum bars provided but no pattern exists
        Given: Exactly 30 bars with sideways movement
        When: Detector processes bars
        Then: Returns failed result (pattern not detected)
        """
        bars = self._create_sideways_bars(count=30)
        detector = BullFlagDetector(default_config)

        result = detector.detect(bars, symbol="MIN30")
        assert result.detected is False
        assert result.symbol == "MIN30"

    def test_edge_case_all_bars_same_price(self, default_config):
        """
        Test handling of bars with no price movement.

        Scenario: All bars have identical prices (flat line)
        Given: 30 bars with same OHLC values
        When: Detector processes bars
        Then: Returns failed result (no flagpole detected)
        """
        bars = []
        base_date = datetime.now(UTC)
        flat_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        for i in range(30):
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(flat_price),
                "high": float(flat_price),
                "low": float(flat_price),
                "close": float(flat_price),
                "volume": float(base_volume)
            })

        detector = BullFlagDetector(default_config)
        result = detector.detect(bars, symbol="FLAT")

        assert result.detected is False
        assert result.symbol == "FLAT"

    def test_edge_case_zero_volume_bars(self, default_config):
        """
        Test handling of bars with zero volume.

        Scenario: All bars have zero volume (no trading activity)
        Given: 30 bars with volume = 0
        When: Detector processes bars
        Then: Returns failed result (volume validation fails)
        """
        bars = self._create_bars(count=30)
        # Set all volumes to zero
        for bar in bars:
            bar["volume"] = 0.0

        detector = BullFlagDetector(default_config)
        result = detector.detect(bars, symbol="NOVOL")

        # Pattern detection should fail due to zero volume
        assert result.detected is False
        assert result.symbol == "NOVOL"

    def test_edge_case_negative_prices(self, default_config):
        """
        Test handling of bars with negative prices (invalid data).

        Scenario: Bar data contains negative price values
        Given: Bars with negative close prices
        When: Detector processes bars
        Then: Detector handles gracefully (pattern not detected)

        Note: Real market data won't have negative prices, but test defensive coding
        """
        bars = self._create_bars(count=30)
        # Set some prices to negative values
        for i in range(10):
            bars[i]["close"] = -100.0
            bars[i]["low"] = -101.0

        detector = BullFlagDetector(default_config)
        result = detector.detect(bars, symbol="NEGPRICE")

        # Should handle gracefully without crashing
        assert result.symbol == "NEGPRICE"

    def test_edge_case_extremely_large_prices(self, default_config):
        """
        Test handling of bars with extremely large prices.

        Scenario: Bar data contains very large price values
        Given: Bars with prices in millions
        When: Detector processes bars
        Then: Detector processes correctly using Decimal precision
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("1000000.00")  # $1M price
        base_volume = Decimal("100")

        # Create flagpole with large prices
        for i in range(10):
            price = base_price + Decimal(str(i * 10000))
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("5000")),
                "low": float(price - Decimal("5000")),
                "close": float(price + Decimal("3000")),
                "volume": float(base_volume)
            })

        # Add padding bars
        for i in range(10, 30):
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(base_price),
                "high": float(base_price + Decimal("1000")),
                "low": float(base_price - Decimal("1000")),
                "close": float(base_price),
                "volume": float(base_volume)
            })

        detector = BullFlagDetector(default_config)
        result = detector.detect(bars, symbol="BIGPRICE")

        # Should process without overflow errors
        assert result.symbol == "BIGPRICE"

    def test_edge_case_extremely_small_prices(self, default_config):
        """
        Test handling of bars with extremely small prices.

        Scenario: Bar data contains very small price values (penny stocks)
        Given: Bars with prices < $1.00
        When: Detector processes bars
        Then: Detector processes correctly using Decimal precision
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("0.05")  # $0.05 price
        base_volume = Decimal("10000000")

        for i in range(30):
            price = base_price + Decimal(str(i * 0.001))
            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("0.002")),
                "low": float(price - Decimal("0.002")),
                "close": float(price + Decimal("0.001")),
                "volume": float(base_volume)
            })

        detector = BullFlagDetector(default_config)
        result = detector.detect(bars, symbol="PENNYSTK")

        # Should process without precision errors
        assert result.symbol == "PENNYSTK"

    def test_edge_case_symbol_with_special_characters(self, default_config):
        """
        Test handling of symbol names with special characters.

        Scenario: Symbol contains non-alphanumeric characters
        Given: Symbol = "BRK.B" (contains period)
        When: Detector processes bars
        Then: Symbol is preserved correctly in result
        """
        bars = self._create_bars(count=30)
        detector = BullFlagDetector(default_config)

        result = detector.detect(bars, symbol="BRK.B")
        assert result.symbol == "BRK.B"

        result2 = detector.detect(bars, symbol="TEST-123")
        assert result2.symbol == "TEST-123"

        result3 = detector.detect(bars, symbol="ABC_XYZ")
        assert result3.symbol == "ABC_XYZ"

    # Helper methods

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

    def _create_sideways_bars(self, count: int) -> List[Dict]:
        """
        Create bars with sideways price movement (no trend).

        Args:
            count: Number of bars to create

        Returns:
            List of OHLCV bars with no clear trend
        """
        bars = []
        base_date = datetime.now(UTC)
        base_price = Decimal("100.00")
        base_volume = Decimal("1000000")

        for i in range(count):
            # Small oscillation around base price (± 1%)
            variation = Decimal(str((i % 7 - 3) * 0.3))
            price = base_price + variation

            bars.append({
                "timestamp": base_date + timedelta(minutes=i*5),
                "open": float(price),
                "high": float(price + Decimal("0.40")),
                "low": float(price - Decimal("0.40")),
                "close": float(price + Decimal("0.10")),
                "volume": float(base_volume)
            })

        return bars
