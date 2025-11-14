"""
Unit Tests for Emotional Control Configuration

Tests: T023 - EmotionalControlConfig validation and factory methods

Constitution v1.0.0:
- §Testing_Requirements: ≥90% coverage, TDD workflow
- §Code_Quality: One behavior per test, descriptive names
"""

import os
import pytest
from decimal import Decimal
from pathlib import Path
from src.trading_bot.emotional_control.config import EmotionalControlConfig


class TestEmotionalControlConfig:
    """Unit tests for EmotionalControlConfig model (T023)."""

    def test_default_factory_returns_v1_0_configuration(self):
        """Test default() factory returns v1.0 hardcoded thresholds."""
        # Given: Invoking default factory
        # When: Creating config via default()
        config = EmotionalControlConfig.default()

        # Then: Returns v1.0 thresholds
        assert config.enabled is True
        assert config.single_loss_threshold_pct == Decimal("3.0")
        assert config.consecutive_loss_threshold == 3
        assert config.recovery_win_threshold == 3
        assert config.position_size_multiplier_active == Decimal("0.25")
        assert config.state_file_path == Path("logs/emotional_control/state.json")
        assert config.event_log_dir == Path("logs/emotional_control")

    def test_from_env_loads_enabled_flag_from_environment(self, monkeypatch):
        """Test from_env() factory loads EMOTIONAL_CONTROL_ENABLED from env."""
        # Given: Environment variable set to "false"
        monkeypatch.setenv("EMOTIONAL_CONTROL_ENABLED", "false")

        # When: Creating config via from_env()
        config = EmotionalControlConfig.from_env()

        # Then: Enabled flag reflects environment variable
        assert config.enabled is False
        # Other fields use defaults
        assert config.single_loss_threshold_pct == Decimal("3.0")
        assert config.consecutive_loss_threshold == 3

    def test_from_env_defaults_to_enabled_if_not_set(self, monkeypatch):
        """Test from_env() defaults enabled=True if env var not set."""
        # Given: Environment variable not set
        monkeypatch.delenv("EMOTIONAL_CONTROL_ENABLED", raising=False)

        # When: Creating config via from_env()
        config = EmotionalControlConfig.from_env()

        # Then: Defaults to enabled=True
        assert config.enabled is True

    @pytest.mark.parametrize("env_value,expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", False),
        ("no", False),
        ("off", False),
    ])
    def test_from_env_parses_boolean_values_correctly(self, monkeypatch, env_value, expected):
        """Test from_env() correctly parses various boolean string values."""
        # Given: Environment variable set to various boolean strings
        monkeypatch.setenv("EMOTIONAL_CONTROL_ENABLED", env_value)

        # When: Creating config via from_env()
        config = EmotionalControlConfig.from_env()

        # Then: Boolean parsed correctly
        assert config.enabled is expected

    def test_validation_fails_for_zero_single_loss_threshold(self):
        """Test validation rejects single_loss_threshold_pct <= 0."""
        # Given: Config with zero single loss threshold
        # When: Creating config with single_loss_threshold_pct = 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="single_loss_threshold_pct must be > 0"):
            EmotionalControlConfig(
                enabled=True,
                single_loss_threshold_pct=Decimal("0"),  # INVALID
                consecutive_loss_threshold=3,
                recovery_win_threshold=3,
                position_size_multiplier_active=Decimal("0.25"),
                state_file_path=Path("logs/emotional_control/state.json"),
                event_log_dir=Path("logs/emotional_control"),
            )

    def test_validation_fails_for_negative_single_loss_threshold(self):
        """Test validation rejects negative single_loss_threshold_pct."""
        # Given: Config with negative single loss threshold
        # When: Creating config with single_loss_threshold_pct < 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="single_loss_threshold_pct must be > 0"):
            EmotionalControlConfig(
                enabled=True,
                single_loss_threshold_pct=Decimal("-1.0"),  # INVALID
                consecutive_loss_threshold=3,
                recovery_win_threshold=3,
                position_size_multiplier_active=Decimal("0.25"),
                state_file_path=Path("logs/emotional_control/state.json"),
                event_log_dir=Path("logs/emotional_control"),
            )

    def test_validation_fails_for_single_loss_threshold_over_100_percent(self):
        """Test validation rejects single_loss_threshold_pct > 100."""
        # Given: Config with single loss threshold > 100%
        # When: Creating config with single_loss_threshold_pct > 100
        # Then: ValueError raised
        with pytest.raises(ValueError, match="single_loss_threshold_pct must be <= 100"):
            EmotionalControlConfig(
                enabled=True,
                single_loss_threshold_pct=Decimal("101.0"),  # INVALID
                consecutive_loss_threshold=3,
                recovery_win_threshold=3,
                position_size_multiplier_active=Decimal("0.25"),
                state_file_path=Path("logs/emotional_control/state.json"),
                event_log_dir=Path("logs/emotional_control"),
            )

    def test_validation_fails_for_zero_consecutive_loss_threshold(self):
        """Test validation rejects consecutive_loss_threshold < 1."""
        # Given: Config with zero consecutive loss threshold
        # When: Creating config with consecutive_loss_threshold = 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="consecutive_loss_threshold must be >= 1"):
            EmotionalControlConfig(
                enabled=True,
                single_loss_threshold_pct=Decimal("3.0"),
                consecutive_loss_threshold=0,  # INVALID
                recovery_win_threshold=3,
                position_size_multiplier_active=Decimal("0.25"),
                state_file_path=Path("logs/emotional_control/state.json"),
                event_log_dir=Path("logs/emotional_control"),
            )

    def test_validation_fails_for_zero_recovery_win_threshold(self):
        """Test validation rejects recovery_win_threshold < 1."""
        # Given: Config with zero recovery win threshold
        # When: Creating config with recovery_win_threshold = 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="recovery_win_threshold must be >= 1"):
            EmotionalControlConfig(
                enabled=True,
                single_loss_threshold_pct=Decimal("3.0"),
                consecutive_loss_threshold=3,
                recovery_win_threshold=0,  # INVALID
                position_size_multiplier_active=Decimal("0.25"),
                state_file_path=Path("logs/emotional_control/state.json"),
                event_log_dir=Path("logs/emotional_control"),
            )

    def test_validation_fails_for_zero_position_multiplier(self):
        """Test validation rejects position_size_multiplier_active <= 0."""
        # Given: Config with zero position multiplier
        # When: Creating config with position_size_multiplier_active = 0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="position_size_multiplier_active must be > 0"):
            EmotionalControlConfig(
                enabled=True,
                single_loss_threshold_pct=Decimal("3.0"),
                consecutive_loss_threshold=3,
                recovery_win_threshold=3,
                position_size_multiplier_active=Decimal("0"),  # INVALID
                state_file_path=Path("logs/emotional_control/state.json"),
                event_log_dir=Path("logs/emotional_control"),
            )

    def test_validation_fails_for_position_multiplier_greater_than_one(self):
        """Test validation rejects position_size_multiplier_active >= 1.0."""
        # Given: Config with position multiplier >= 1.0
        # When: Creating config with position_size_multiplier_active = 1.0
        # Then: ValueError raised
        with pytest.raises(ValueError, match="position_size_multiplier_active must be < 1.0"):
            EmotionalControlConfig(
                enabled=True,
                single_loss_threshold_pct=Decimal("3.0"),
                consecutive_loss_threshold=3,
                recovery_win_threshold=3,
                position_size_multiplier_active=Decimal("1.0"),  # INVALID (must be reduction)
                state_file_path=Path("logs/emotional_control/state.json"),
                event_log_dir=Path("logs/emotional_control"),
            )

    def test_valid_custom_configuration(self):
        """Test creating valid custom configuration with non-default values."""
        # Given: Custom configuration values
        # When: Creating config with valid custom values
        config = EmotionalControlConfig(
            enabled=True,
            single_loss_threshold_pct=Decimal("5.0"),  # Custom: 5% threshold
            consecutive_loss_threshold=5,  # Custom: 5 losses
            recovery_win_threshold=5,  # Custom: 5 wins
            position_size_multiplier_active=Decimal("0.50"),  # Custom: 50% reduction
            state_file_path=Path("custom/path/state.json"),
            event_log_dir=Path("custom/path/logs"),
        )

        # Then: Config created successfully with custom values
        assert config.single_loss_threshold_pct == Decimal("5.0")
        assert config.consecutive_loss_threshold == 5
        assert config.recovery_win_threshold == 5
        assert config.position_size_multiplier_active == Decimal("0.50")
