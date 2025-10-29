"""
Tests for multi-timeframe validation configuration (MultiTimeframeConfig).

TDD approach: Write failing tests before implementation.
"""

import os
import pytest
from decimal import Decimal
from unittest.mock import patch

from src.trading_bot.validation.config import MultiTimeframeConfig


class TestMultiTimeframeConfig:
    """Tests for MultiTimeframeConfig dataclass."""

    def test_config_from_env_loads_defaults(self):
        """Test: from_env() loads default values when environment variables are missing.

        Given: Empty environment (no config vars set)
        When: Calling MultiTimeframeConfig.from_env()
        Then: Instance created with default values
        """
        # Given: Mock empty environment
        with patch.dict(os.environ, {}, clear=True):
            # When
            config = MultiTimeframeConfig.from_env()

            # Then: Verify defaults
            assert config.enabled is True
            assert config.daily_weight == Decimal("0.6")
            assert config.h4_weight == Decimal("0.4")
            assert config.aggregate_threshold == Decimal("0.5")
            assert config.max_retries == 3
            assert config.retry_backoff_base_ms == 1000

    def test_config_from_env_loads_custom_values(self):
        """Test: from_env() loads custom values from environment variables.

        Given: Environment variables with custom config values
        When: Calling MultiTimeframeConfig.from_env()
        Then: Instance created with custom values from env
        """
        # Given: Mock custom environment
        env_vars = {
            "MULTI_TIMEFRAME_VALIDATION_ENABLED": "false",
            "DAILY_WEIGHT": "0.7",
            "H4_WEIGHT": "0.3",
            "AGGREGATE_THRESHOLD": "0.6",
            "MAX_RETRIES": "5",
            "RETRY_BACKOFF_BASE_MS": "2000"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # When
            config = MultiTimeframeConfig.from_env()

            # Then: Verify custom values
            assert config.enabled is False
            assert config.daily_weight == Decimal("0.7")
            assert config.h4_weight == Decimal("0.3")
            assert config.aggregate_threshold == Decimal("0.6")
            assert config.max_retries == 5
            assert config.retry_backoff_base_ms == 2000

    def test_config_enabled_flag_parsing(self):
        """Test: enabled flag correctly parses "true"/"false" strings (case-insensitive).

        Given: Different case variations of "true"/"false"
        When: Calling from_env()
        Then: Boolean parsed correctly
        """
        # Test: "true"
        with patch.dict(os.environ, {"MULTI_TIMEFRAME_VALIDATION_ENABLED": "true"}, clear=True):
            config = MultiTimeframeConfig.from_env()
            assert config.enabled is True

        # Test: "TRUE"
        with patch.dict(os.environ, {"MULTI_TIMEFRAME_VALIDATION_ENABLED": "TRUE"}, clear=True):
            config = MultiTimeframeConfig.from_env()
            assert config.enabled is True

        # Test: "false"
        with patch.dict(os.environ, {"MULTI_TIMEFRAME_VALIDATION_ENABLED": "false"}, clear=True):
            config = MultiTimeframeConfig.from_env()
            assert config.enabled is False

        # Test: "FALSE"
        with patch.dict(os.environ, {"MULTI_TIMEFRAME_VALIDATION_ENABLED": "FALSE"}, clear=True):
            config = MultiTimeframeConfig.from_env()
            assert config.enabled is False

        # Test: Any other value defaults to False
        with patch.dict(os.environ, {"MULTI_TIMEFRAME_VALIDATION_ENABLED": "yes"}, clear=True):
            config = MultiTimeframeConfig.from_env()
            assert config.enabled is False

    def test_config_is_immutable(self):
        """Test: MultiTimeframeConfig is frozen and cannot be modified.

        Given: A MultiTimeframeConfig instance
        When: Attempting to modify a field
        Then: FrozenInstanceError is raised
        """
        # Given
        from dataclasses import FrozenInstanceError

        with patch.dict(os.environ, {}, clear=True):
            config = MultiTimeframeConfig.from_env()

            # When/Then
            with pytest.raises(FrozenInstanceError):
                config.enabled = False

    def test_config_weights_sum_to_one(self):
        """Test: Default daily_weight + 4h_weight sum to 1.0.

        Given: Default config
        When: Loading config
        Then: Weights sum to 1.0 (0.6 + 0.4)
        """
        # Given/When
        with patch.dict(os.environ, {}, clear=True):
            config = MultiTimeframeConfig.from_env()

            # Then
            assert config.daily_weight + config.h4_weight == Decimal("1.0")
