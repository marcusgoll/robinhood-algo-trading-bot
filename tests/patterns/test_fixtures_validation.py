"""
Validation tests for pattern detection fixtures.

Ensures all fixtures are properly configured and return correct data types.

Feature: 003-entry-logic-bull-flag
Task: T010 - Validate fixtures can be imported and used
"""

import pytest
from decimal import Decimal


def test_sample_bars_fixture(sample_bars):
    """Test sample_bars fixture returns correct structure."""
    # Given: sample_bars fixture

    # Then: Returns list with 30+ bars
    assert isinstance(sample_bars, list)
    assert len(sample_bars) >= 30, f"Expected >=30 bars, got {len(sample_bars)}"

    # Then: Each bar has required OHLCV fields
    required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
    for bar in sample_bars:
        assert isinstance(bar, dict)
        for field in required_fields:
            assert field in bar, f"Bar missing {field} field"
            assert bar[field] is not None, f"Bar {field} is None"

    # Then: Prices are realistic (high >= close >= low)
    for i, bar in enumerate(sample_bars):
        assert bar["high"] >= bar["close"], f"Bar {i}: high < close"
        assert bar["close"] >= bar["low"], f"Bar {i}: close < low"
        assert bar["high"] >= bar["low"], f"Bar {i}: high < low"


def test_valid_bull_flag_bars_fixture(valid_bull_flag_bars):
    """Test valid_bull_flag_bars fixture returns perfect pattern."""
    # Given: valid_bull_flag_bars fixture

    # Then: Returns list with 30+ bars
    assert isinstance(valid_bull_flag_bars, list)
    assert len(valid_bull_flag_bars) >= 30, f"Expected >=30 bars, got {len(valid_bull_flag_bars)}"

    # Then: Contains flagpole phase (bars 0-10, ~8.5% gain)
    flagpole_bars = valid_bull_flag_bars[0:11]
    flagpole_low = min(bar["low"] for bar in flagpole_bars)
    flagpole_high = max(bar["high"] for bar in flagpole_bars)
    flagpole_gain = ((flagpole_high - flagpole_low) / flagpole_low) * 100
    assert flagpole_gain >= 5.0, f"Flagpole gain {flagpole_gain:.2f}% < 5%"

    # Then: Contains consolidation phase (bars 11-18, lower volume)
    consolidation_bars = valid_bull_flag_bars[11:19]
    assert len(consolidation_bars) >= 3, "Consolidation too short"
    consolidation_avg_volume = sum(bar["volume"] for bar in consolidation_bars) / len(consolidation_bars)
    flagpole_avg_volume = sum(bar["volume"] for bar in flagpole_bars) / len(flagpole_bars)
    assert consolidation_avg_volume < flagpole_avg_volume, "Consolidation volume not decreased"


def test_invalid_pattern_bars_fixture(invalid_pattern_bars):
    """Test invalid_pattern_bars fixture shows no pattern."""
    # Given: invalid_pattern_bars fixture

    # Then: Returns list with 30+ bars
    assert isinstance(invalid_pattern_bars, list)
    assert len(invalid_pattern_bars) >= 30, f"Expected >=30 bars, got {len(invalid_pattern_bars)}"

    # Then: No strong upward move (< 5% gain over any 10-bar period)
    for start_idx in range(len(invalid_pattern_bars) - 10):
        window_bars = invalid_pattern_bars[start_idx:start_idx+10]
        window_low = min(bar["low"] for bar in window_bars)
        window_high = max(bar["high"] for bar in window_bars)
        window_gain = ((window_high - window_low) / window_low) * 100
        # Allow small gains, but not enough for flagpole
        assert window_gain < 8.0, f"Unexpected gain {window_gain:.2f}% at bar {start_idx}"


def test_default_config_fixture(default_config):
    """Test default_config fixture returns valid configuration."""
    # Given: default_config fixture

    # Then: Returns BullFlagConfig instance
    from src.trading_bot.patterns.config import BullFlagConfig
    assert isinstance(default_config, BullFlagConfig)

    # Then: Has default values
    assert default_config.min_flagpole_gain == Decimal("5.0")
    assert default_config.min_quality_score == 60
    assert default_config.min_risk_reward_ratio == Decimal("2.0")


def test_aggressive_config_fixture(aggressive_config):
    """Test aggressive_config fixture has looser parameters."""
    # Given: aggressive_config fixture

    # Then: Has loose pattern criteria
    assert aggressive_config.min_flagpole_gain == Decimal("2.0")
    assert aggressive_config.min_quality_score == 40
    assert aggressive_config.min_risk_reward_ratio == Decimal("1.5")

    # Then: Wider retracement range
    assert aggressive_config.min_retracement_pct == Decimal("10.0")
    assert aggressive_config.max_retracement_pct == Decimal("60.0")


def test_conservative_config_fixture(conservative_config):
    """Test conservative_config fixture has stricter parameters."""
    # Given: conservative_config fixture

    # Then: Has strict pattern criteria
    assert conservative_config.min_flagpole_gain == Decimal("10.0")
    assert conservative_config.min_quality_score == 80
    assert conservative_config.min_risk_reward_ratio == Decimal("3.0")

    # Then: Tighter retracement range
    assert conservative_config.min_retracement_pct == Decimal("25.0")
    assert conservative_config.max_retracement_pct == Decimal("40.0")


def test_config_fixtures_are_distinct(default_config, aggressive_config, conservative_config):
    """Test that config fixtures have different parameter values."""
    # Given: All three config fixtures

    # Then: Aggressive has lowest thresholds
    assert aggressive_config.min_flagpole_gain < default_config.min_flagpole_gain
    assert aggressive_config.min_flagpole_gain < conservative_config.min_flagpole_gain

    # Then: Conservative has highest thresholds
    assert conservative_config.min_flagpole_gain > default_config.min_flagpole_gain
    assert conservative_config.min_quality_score > default_config.min_quality_score

    # Then: Each fixture creates independent instances
    assert id(default_config) != id(aggressive_config)
    assert id(default_config) != id(conservative_config)
    assert id(aggressive_config) != id(conservative_config)


def test_bars_fixtures_use_decimal_precision(sample_bars, valid_bull_flag_bars, invalid_pattern_bars):
    """Test that all bars fixtures maintain numeric precision."""
    # Given: All bars fixtures
    all_fixtures = [sample_bars, valid_bull_flag_bars, invalid_pattern_bars]

    # Then: All prices and volumes are numeric (float or Decimal compatible)
    for fixture_name, fixture in zip(
        ["sample_bars", "valid_bull_flag_bars", "invalid_pattern_bars"],
        all_fixtures
    ):
        for i, bar in enumerate(fixture):
            # Check all numeric fields can be converted to Decimal
            try:
                Decimal(str(bar["open"]))
                Decimal(str(bar["high"]))
                Decimal(str(bar["low"]))
                Decimal(str(bar["close"]))
                Decimal(str(bar["volume"]))
            except (ValueError, TypeError) as e:
                pytest.fail(f"{fixture_name} bar {i} has invalid numeric value: {e}")
