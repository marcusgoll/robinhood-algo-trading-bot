"""
Unit tests for profit goal configuration loading (TDD)

Tests Constitution v1.0.0 requirements:
- §Security: Configuration from environment variables
- §Data_Integrity: Validate all configuration inputs
- §Risk_Management: Safe defaults for invalid values

Feature: daily-profit-goal-ma
Task: T012 [US1] - Test configuration loading from environment
"""

import os
import pytest
from decimal import Decimal
from unittest.mock import patch

from src.trading_bot.profit_goal.config import load_profit_goal_config


class TestProfitGoalConfigLoading:
    """Test load_profit_goal_config function (T012)."""

    # =========================================================================
    # T012 [US1]: Test configuration loading from environment variables
    # =========================================================================

    def test_load_config_with_env_vars_set(self) -> None:
        """Should load config from environment variables when set (T012).

        Given PROFIT_TARGET_DAILY and PROFIT_GIVEBACK_THRESHOLD env vars set
        When load_profit_goal_config() is called
        Then config should be loaded with values from env vars
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "500",
                "PROFIT_GIVEBACK_THRESHOLD": "0.50",
            },
        ):
            config = load_profit_goal_config()

            assert config.target == Decimal("500")
            assert config.threshold == Decimal("0.50")
            assert config.enabled is True

    def test_load_config_with_env_vars_missing_uses_defaults(self) -> None:
        """Should use defaults when environment variables are missing (T012).

        Given PROFIT_TARGET_DAILY and PROFIT_GIVEBACK_THRESHOLD not set
        When load_profit_goal_config() is called
        Then config should use safe defaults

        Defaults:
        - target: $0 (feature disabled)
        - threshold: 0.50 (50% giveback)
        """
        with patch.dict(os.environ, {}, clear=True):
            config = load_profit_goal_config()

            assert config.target == Decimal("0")
            assert config.threshold == Decimal("0.50")
            assert config.enabled is False

    def test_load_config_with_invalid_target_uses_default(self) -> None:
        """Should use default target when env var value is invalid (T012).

        Given PROFIT_TARGET_DAILY with non-numeric value
        When load_profit_goal_config() is called
        Then config should use default target ($0) and log warning
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "not-a-number",
                "PROFIT_GIVEBACK_THRESHOLD": "0.50",
            },
        ):
            config = load_profit_goal_config()

            # Should fall back to default target
            assert config.target == Decimal("0")
            assert config.threshold == Decimal("0.50")
            assert config.enabled is False

    def test_load_config_with_invalid_threshold_uses_default(self) -> None:
        """Should use default threshold when env var value is invalid (T012).

        Given PROFIT_GIVEBACK_THRESHOLD with non-numeric value
        When load_profit_goal_config() is called
        Then config should use default threshold (0.50) and log warning
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "500",
                "PROFIT_GIVEBACK_THRESHOLD": "invalid",
            },
        ):
            config = load_profit_goal_config()

            # Should fall back to default threshold
            assert config.target == Decimal("500")
            assert config.threshold == Decimal("0.50")
            assert config.enabled is True

    def test_load_config_with_target_out_of_range_uses_safe_defaults(self) -> None:
        """Should use safe defaults when target validation fails (T012).

        Given PROFIT_TARGET_DAILY outside valid range ($0-$10,000)
        When load_profit_goal_config() is called
        Then entire config should fall back to safe defaults
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "15000",  # Above max
                "PROFIT_GIVEBACK_THRESHOLD": "0.50",
            },
        ):
            config = load_profit_goal_config()

            # Validation failure triggers full fallback
            assert config.target == Decimal("0")
            assert config.threshold == Decimal("0.50")
            assert config.enabled is False

    def test_load_config_with_threshold_out_of_range_uses_safe_defaults(self) -> None:
        """Should use safe defaults when threshold validation fails (T012).

        Given PROFIT_GIVEBACK_THRESHOLD outside valid range (0.10-0.90)
        When load_profit_goal_config() is called
        Then entire config should fall back to safe defaults
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "500",
                "PROFIT_GIVEBACK_THRESHOLD": "0.95",  # Above max
            },
        ):
            config = load_profit_goal_config()

            # Validation failure triggers full fallback
            assert config.target == Decimal("0")
            assert config.threshold == Decimal("0.50")
            assert config.enabled is False

    def test_load_config_with_zero_target_disables_feature(self) -> None:
        """Should disable feature when target is $0 (T012).

        Given PROFIT_TARGET_DAILY = "0"
        When load_profit_goal_config() is called
        Then config.enabled should be False
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "0",
                "PROFIT_GIVEBACK_THRESHOLD": "0.50",
            },
        ):
            config = load_profit_goal_config()

            assert config.target == Decimal("0")
            assert config.enabled is False

    def test_load_config_with_decimal_precision(self) -> None:
        """Should preserve decimal precision for monetary values (T012).

        Given env vars with decimal values
        When load_profit_goal_config() is called
        Then Decimal precision should be preserved
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "500.75",  # Fractional dollars
                "PROFIT_GIVEBACK_THRESHOLD": "0.45",
            },
        ):
            config = load_profit_goal_config()

            assert config.target == Decimal("500.75")
            assert config.threshold == Decimal("0.45")
            assert config.enabled is True

    def test_load_config_edge_case_max_values(self) -> None:
        """Should accept maximum valid values (T012).

        Given env vars with max valid values
        When load_profit_goal_config() is called
        Then config should be loaded successfully
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "10000",  # Max target
                "PROFIT_GIVEBACK_THRESHOLD": "0.90",  # Max threshold
            },
        ):
            config = load_profit_goal_config()

            assert config.target == Decimal("10000")
            assert config.threshold == Decimal("0.90")
            assert config.enabled is True

    def test_load_config_edge_case_min_values(self) -> None:
        """Should accept minimum valid values (T012).

        Given env vars with min valid values
        When load_profit_goal_config() is called
        Then config should be loaded successfully
        """
        with patch.dict(
            os.environ,
            {
                "PROFIT_TARGET_DAILY": "0",  # Min target (disabled)
                "PROFIT_GIVEBACK_THRESHOLD": "0.10",  # Min threshold
            },
        ):
            config = load_profit_goal_config()

            assert config.target == Decimal("0")
            assert config.threshold == Decimal("0.10")
            assert config.enabled is False
