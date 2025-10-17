"""Tests for pattern detection configuration."""

import pytest
from decimal import Decimal
from src.trading_bot.patterns.config import BullFlagConfig


class TestBullFlagConfig:
    """Tests for BullFlagConfig dataclass and validation."""

    def test_default_config_valid(self):
        """Test BullFlagConfig with default values.

        Given: No parameters to BullFlagConfig()
        When: Instantiate with defaults
        Then: Config created successfully, all defaults correct
        """
        # Given: No custom parameters

        # When: Instantiate with defaults
        config = BullFlagConfig()

        # Then: All defaults are correct
        assert config.min_flagpole_gain == Decimal("5.0")
        assert config.max_flagpole_gain == Decimal("25.0")
        assert config.min_flagpole_bars == 3
        assert config.max_flagpole_bars == 15
        assert config.min_consolidation_bars == 3
        assert config.max_consolidation_bars == 10
        assert config.min_retracement_pct == Decimal("20.0")
        assert config.max_retracement_pct == Decimal("50.0")
        assert config.min_breakout_volume_increase == Decimal("30.0")
        assert config.min_breakout_move_pct == Decimal("1.0")
        assert config.min_quality_score == 60
        assert config.min_risk_reward_ratio == Decimal("2.0")
        assert config.volume_decay_threshold == Decimal("0.9")

    def test_valid_config_with_custom_values(self):
        """Test BullFlagConfig with valid custom values.

        Given: Custom valid values
        When: Instantiate with valid overrides
        Then: Config created with custom values
        """
        # Given: Custom valid configuration parameters
        custom_params = {
            "min_flagpole_gain": Decimal("7.0"),
            "max_flagpole_gain": Decimal("30.0"),
            "min_flagpole_bars": 5,
            "max_flagpole_bars": 20,
            "min_consolidation_bars": 4,
            "max_consolidation_bars": 12,
            "min_retracement_pct": Decimal("25.0"),
            "max_retracement_pct": Decimal("45.0"),
            "min_breakout_volume_increase": Decimal("40.0"),
            "min_breakout_move_pct": Decimal("1.5"),
            "min_quality_score": 70,
            "min_risk_reward_ratio": Decimal("2.5"),
            "volume_decay_threshold": Decimal("0.8"),
        }

        # When: Instantiate with custom values
        config = BullFlagConfig(**custom_params)

        # Then: Config created with all custom values
        assert config.min_flagpole_gain == Decimal("7.0")
        assert config.max_flagpole_gain == Decimal("30.0")
        assert config.min_flagpole_bars == 5
        assert config.max_flagpole_bars == 20
        assert config.min_consolidation_bars == 4
        assert config.max_consolidation_bars == 12
        assert config.min_retracement_pct == Decimal("25.0")
        assert config.max_retracement_pct == Decimal("45.0")
        assert config.min_breakout_volume_increase == Decimal("40.0")
        assert config.min_breakout_move_pct == Decimal("1.5")
        assert config.min_quality_score == 70
        assert config.min_risk_reward_ratio == Decimal("2.5")
        assert config.volume_decay_threshold == Decimal("0.8")

    # Flagpole Gain Validation Tests

    def test_invalid_min_max_flagpole_gain_equal(self):
        """Test BullFlagConfig with min_flagpole_gain == max_flagpole_gain.

        Given: min_flagpole_gain == max_flagpole_gain
        When: Instantiate
        Then: ValueError raised with specific message
        """
        # Given: Equal min and max flagpole gain

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_flagpole_gain.*must be < max_flagpole_gain"):
            BullFlagConfig(
                min_flagpole_gain=Decimal("10.0"),
                max_flagpole_gain=Decimal("10.0")
            )

    def test_invalid_min_max_flagpole_gain_reversed(self):
        """Test BullFlagConfig with min_flagpole_gain > max_flagpole_gain.

        Given: min_flagpole_gain > max_flagpole_gain
        When: Instantiate
        Then: ValueError raised with specific message
        """
        # Given: Reversed min and max flagpole gain

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_flagpole_gain.*must be < max_flagpole_gain"):
            BullFlagConfig(
                min_flagpole_gain=Decimal("20.0"),
                max_flagpole_gain=Decimal("10.0")
            )

    def test_negative_min_flagpole_gain(self):
        """Test BullFlagConfig with negative min_flagpole_gain.

        Given: Negative min_flagpole_gain
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative min flagpole gain

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_flagpole_gain must be > 0"):
            BullFlagConfig(min_flagpole_gain=Decimal("-5.0"))

    def test_zero_min_flagpole_gain(self):
        """Test BullFlagConfig with zero min_flagpole_gain.

        Given: Zero min_flagpole_gain
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Zero min flagpole gain

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_flagpole_gain must be > 0"):
            BullFlagConfig(min_flagpole_gain=Decimal("0"))

    def test_negative_max_flagpole_gain(self):
        """Test BullFlagConfig with negative max_flagpole_gain.

        Given: Negative max_flagpole_gain
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative max flagpole gain

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="max_flagpole_gain must be > 0"):
            BullFlagConfig(max_flagpole_gain=Decimal("-10.0"))

    # Flagpole Bars Validation Tests

    def test_invalid_min_max_flagpole_bars_equal(self):
        """Test BullFlagConfig with min_flagpole_bars == max_flagpole_bars.

        Given: min_flagpole_bars == max_flagpole_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Equal min and max flagpole bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_flagpole_bars.*must be < max_flagpole_bars"):
            BullFlagConfig(min_flagpole_bars=5, max_flagpole_bars=5)

    def test_invalid_min_max_flagpole_bars_reversed(self):
        """Test BullFlagConfig with min_flagpole_bars > max_flagpole_bars.

        Given: min_flagpole_bars > max_flagpole_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Reversed min and max flagpole bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_flagpole_bars.*must be < max_flagpole_bars"):
            BullFlagConfig(min_flagpole_bars=10, max_flagpole_bars=5)

    def test_negative_min_flagpole_bars(self):
        """Test BullFlagConfig with negative min_flagpole_bars.

        Given: Negative min_flagpole_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative min flagpole bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_flagpole_bars must be > 0"):
            BullFlagConfig(min_flagpole_bars=-3)

    def test_zero_min_flagpole_bars(self):
        """Test BullFlagConfig with zero min_flagpole_bars.

        Given: Zero min_flagpole_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Zero min flagpole bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_flagpole_bars must be > 0"):
            BullFlagConfig(min_flagpole_bars=0)

    def test_negative_max_flagpole_bars(self):
        """Test BullFlagConfig with negative max_flagpole_bars.

        Given: Negative max_flagpole_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative max flagpole bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="max_flagpole_bars must be > 0"):
            BullFlagConfig(max_flagpole_bars=-15)

    # Consolidation Bars Validation Tests

    def test_invalid_min_max_consolidation_bars_equal(self):
        """Test BullFlagConfig with min_consolidation_bars == max_consolidation_bars.

        Given: min_consolidation_bars == max_consolidation_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Equal min and max consolidation bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_consolidation_bars.*must be < max_consolidation_bars"):
            BullFlagConfig(min_consolidation_bars=5, max_consolidation_bars=5)

    def test_invalid_min_max_consolidation_bars_reversed(self):
        """Test BullFlagConfig with min_consolidation_bars > max_consolidation_bars.

        Given: min_consolidation_bars > max_consolidation_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Reversed min and max consolidation bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_consolidation_bars.*must be < max_consolidation_bars"):
            BullFlagConfig(min_consolidation_bars=10, max_consolidation_bars=5)

    def test_negative_min_consolidation_bars(self):
        """Test BullFlagConfig with negative min_consolidation_bars.

        Given: Negative min_consolidation_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative min consolidation bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_consolidation_bars must be > 0"):
            BullFlagConfig(min_consolidation_bars=-3)

    def test_zero_min_consolidation_bars(self):
        """Test BullFlagConfig with zero min_consolidation_bars.

        Given: Zero min_consolidation_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Zero min consolidation bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_consolidation_bars must be > 0"):
            BullFlagConfig(min_consolidation_bars=0)

    def test_negative_max_consolidation_bars(self):
        """Test BullFlagConfig with negative max_consolidation_bars.

        Given: Negative max_consolidation_bars
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative max consolidation bars

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="max_consolidation_bars must be > 0"):
            BullFlagConfig(max_consolidation_bars=-10)

    # Retracement Percentage Validation Tests

    def test_invalid_min_max_retracement_pct_equal(self):
        """Test BullFlagConfig with min_retracement_pct == max_retracement_pct.

        Given: min_retracement_pct == max_retracement_pct
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Equal min and max retracement percentages

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_retracement_pct.*must be < max_retracement_pct"):
            BullFlagConfig(
                min_retracement_pct=Decimal("30.0"),
                max_retracement_pct=Decimal("30.0")
            )

    def test_invalid_min_max_retracement_pct_reversed(self):
        """Test BullFlagConfig with min_retracement_pct > max_retracement_pct.

        Given: min_retracement_pct > max_retracement_pct
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Reversed min and max retracement percentages

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_retracement_pct.*must be < max_retracement_pct"):
            BullFlagConfig(
                min_retracement_pct=Decimal("50.0"),
                max_retracement_pct=Decimal("30.0")
            )

    def test_min_retracement_pct_below_zero(self):
        """Test BullFlagConfig with min_retracement_pct < 0.

        Given: min_retracement_pct < 0
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative min retracement percentage

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_retracement_pct must be 0-100"):
            BullFlagConfig(min_retracement_pct=Decimal("-5.0"))

    def test_min_retracement_pct_above_100(self):
        """Test BullFlagConfig with min_retracement_pct > 100.

        Given: min_retracement_pct > 100
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Min retracement percentage over 100

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_retracement_pct must be 0-100"):
            BullFlagConfig(min_retracement_pct=Decimal("105.0"))

    def test_max_retracement_pct_below_zero(self):
        """Test BullFlagConfig with max_retracement_pct < 0.

        Given: max_retracement_pct < 0
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative max retracement percentage

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="max_retracement_pct must be 0-100"):
            BullFlagConfig(max_retracement_pct=Decimal("-10.0"))

    def test_max_retracement_pct_above_100(self):
        """Test BullFlagConfig with max_retracement_pct > 100.

        Given: max_retracement_pct > 100
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Max retracement percentage over 100

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="max_retracement_pct must be 0-100"):
            BullFlagConfig(max_retracement_pct=Decimal("110.0"))

    def test_valid_retracement_pct_at_boundaries(self):
        """Test BullFlagConfig with valid boundary values for retracement.

        Given: min_retracement_pct = 0, max_retracement_pct = 100
        When: Instantiate
        Then: Config created successfully
        """
        # Given: Boundary values for retracement

        # When: Instantiate with boundary values
        config = BullFlagConfig(
            min_retracement_pct=Decimal("0.0"),
            max_retracement_pct=Decimal("100.0")
        )

        # Then: Config created successfully
        assert config.min_retracement_pct == Decimal("0.0")
        assert config.max_retracement_pct == Decimal("100.0")

    # Quality Score Validation Tests

    def test_invalid_quality_score_below_zero(self):
        """Test BullFlagConfig with min_quality_score < 0.

        Given: min_quality_score < 0
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative quality score

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_quality_score must be 0-100"):
            BullFlagConfig(min_quality_score=-10)

    def test_invalid_quality_score_above_100(self):
        """Test BullFlagConfig with min_quality_score > 100.

        Given: min_quality_score > 100
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Quality score over 100

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_quality_score must be 0-100"):
            BullFlagConfig(min_quality_score=105)

    def test_valid_quality_score_at_boundaries(self):
        """Test BullFlagConfig with valid boundary quality scores.

        Given: min_quality_score = 0 and min_quality_score = 100
        When: Instantiate
        Then: Config created successfully
        """
        # Given: Boundary quality score values

        # When: Instantiate with quality score 0
        config_zero = BullFlagConfig(min_quality_score=0)

        # Then: Config created successfully
        assert config_zero.min_quality_score == 0

        # When: Instantiate with quality score 100
        config_hundred = BullFlagConfig(min_quality_score=100)

        # Then: Config created successfully
        assert config_hundred.min_quality_score == 100

    # Risk/Reward Ratio Validation Tests

    def test_invalid_risk_reward_ratio_equal_to_one(self):
        """Test BullFlagConfig with min_risk_reward_ratio == 1.0.

        Given: min_risk_reward_ratio == 1.0
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Risk/reward ratio equal to 1

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_risk_reward_ratio must be > 1"):
            BullFlagConfig(min_risk_reward_ratio=Decimal("1.0"))

    def test_invalid_risk_reward_ratio_below_one(self):
        """Test BullFlagConfig with min_risk_reward_ratio < 1.0.

        Given: min_risk_reward_ratio < 1.0
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Risk/reward ratio less than 1

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_risk_reward_ratio must be > 1"):
            BullFlagConfig(min_risk_reward_ratio=Decimal("0.5"))

    def test_valid_risk_reward_ratio_just_above_one(self):
        """Test BullFlagConfig with min_risk_reward_ratio just above 1.0.

        Given: min_risk_reward_ratio = 1.01
        When: Instantiate
        Then: Config created successfully
        """
        # Given: Risk/reward ratio just above 1

        # When: Instantiate with ratio just above 1
        config = BullFlagConfig(min_risk_reward_ratio=Decimal("1.01"))

        # Then: Config created successfully
        assert config.min_risk_reward_ratio == Decimal("1.01")

    # Breakout Volume Increase Validation Tests

    def test_negative_breakout_volume_increase(self):
        """Test BullFlagConfig with negative min_breakout_volume_increase.

        Given: Negative min_breakout_volume_increase
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative breakout volume increase

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_breakout_volume_increase must be > 0"):
            BullFlagConfig(min_breakout_volume_increase=Decimal("-10.0"))

    def test_zero_breakout_volume_increase(self):
        """Test BullFlagConfig with zero min_breakout_volume_increase.

        Given: Zero min_breakout_volume_increase
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Zero breakout volume increase

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_breakout_volume_increase must be > 0"):
            BullFlagConfig(min_breakout_volume_increase=Decimal("0"))

    # Breakout Move Percentage Validation Tests

    def test_negative_breakout_move_pct(self):
        """Test BullFlagConfig with negative min_breakout_move_pct.

        Given: Negative min_breakout_move_pct
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative breakout move percentage

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_breakout_move_pct must be > 0"):
            BullFlagConfig(min_breakout_move_pct=Decimal("-1.0"))

    def test_zero_breakout_move_pct(self):
        """Test BullFlagConfig with zero min_breakout_move_pct.

        Given: Zero min_breakout_move_pct
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Zero breakout move percentage

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="min_breakout_move_pct must be > 0"):
            BullFlagConfig(min_breakout_move_pct=Decimal("0"))

    # Volume Decay Threshold Validation Tests

    def test_negative_volume_decay_threshold(self):
        """Test BullFlagConfig with negative volume_decay_threshold.

        Given: Negative volume_decay_threshold
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Negative volume decay threshold

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="volume_decay_threshold must be > 0"):
            BullFlagConfig(volume_decay_threshold=Decimal("-0.5"))

    def test_zero_volume_decay_threshold(self):
        """Test BullFlagConfig with zero volume_decay_threshold.

        Given: Zero volume_decay_threshold
        When: Instantiate
        Then: ValueError raised
        """
        # Given: Zero volume decay threshold

        # When/Then: ValueError raised
        with pytest.raises(ValueError, match="volume_decay_threshold must be > 0"):
            BullFlagConfig(volume_decay_threshold=Decimal("0"))

    # Edge Cases and Complex Scenarios

    def test_multiple_validation_failures_first_reported(self):
        """Test BullFlagConfig with multiple invalid parameters.

        Given: Multiple invalid parameters
        When: Instantiate
        Then: First validation failure is raised
        """
        # Given: Multiple invalid parameters

        # When/Then: First validation error is raised (min_flagpole_gain)
        with pytest.raises(ValueError):
            BullFlagConfig(
                min_flagpole_gain=Decimal("-5.0"),  # Invalid: negative
                min_quality_score=150,  # Invalid: > 100
                min_risk_reward_ratio=Decimal("0.5")  # Invalid: < 1
            )

    def test_all_valid_edge_case_values(self):
        """Test BullFlagConfig with all valid edge case values.

        Given: All parameters at valid edge cases
        When: Instantiate
        Then: Config created successfully with all edge values
        """
        # Given: All edge case values
        edge_config = {
            "min_flagpole_gain": Decimal("0.01"),  # Just above 0
            "max_flagpole_gain": Decimal("100.0"),  # Large value
            "min_flagpole_bars": 1,  # Minimum possible
            "max_flagpole_bars": 100,  # Large value
            "min_consolidation_bars": 1,  # Minimum possible
            "max_consolidation_bars": 50,  # Large value
            "min_retracement_pct": Decimal("0.0"),  # Lower boundary
            "max_retracement_pct": Decimal("100.0"),  # Upper boundary
            "min_breakout_volume_increase": Decimal("0.01"),  # Just above 0
            "min_breakout_move_pct": Decimal("0.01"),  # Just above 0
            "min_quality_score": 0,  # Lower boundary
            "min_risk_reward_ratio": Decimal("1.01"),  # Just above 1
            "volume_decay_threshold": Decimal("0.01"),  # Just above 0
        }

        # When: Instantiate with edge values
        config = BullFlagConfig(**edge_config)

        # Then: Config created with all edge values
        assert config.min_flagpole_gain == Decimal("0.01")
        assert config.max_flagpole_gain == Decimal("100.0")
        assert config.min_flagpole_bars == 1
        assert config.max_flagpole_bars == 100
        assert config.min_consolidation_bars == 1
        assert config.max_consolidation_bars == 50
        assert config.min_retracement_pct == Decimal("0.0")
        assert config.max_retracement_pct == Decimal("100.0")
        assert config.min_breakout_volume_increase == Decimal("0.01")
        assert config.min_breakout_move_pct == Decimal("0.01")
        assert config.min_quality_score == 0
        assert config.min_risk_reward_ratio == Decimal("1.01")
        assert config.volume_decay_threshold == Decimal("0.01")
