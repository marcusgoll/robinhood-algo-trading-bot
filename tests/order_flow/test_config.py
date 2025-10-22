"""
Unit tests for OrderFlowConfig validation.

Tests:
- T008: OrderFlowConfig validates large_order_size_threshold
- T029: OrderFlowConfig validates threshold ranges
- T030: OrderFlowConfig.from_env() loads environment variables

Feature: level-2-order-flow-i
Task: T008, T029, T030 [RED] - Write tests for OrderFlowConfig
"""

import os
import pytest
from unittest.mock import patch

from src.trading_bot.order_flow.config import OrderFlowConfig


class TestOrderFlowConfigValidation:
    """Test suite for OrderFlowConfig validation rules."""

    def test_large_order_size_threshold_minimum_1000_shares(self):
        """Test that large_order_size_threshold must be >= 1000 shares."""
        # Given: OrderFlowConfig with invalid threshold
        # When: Creating config with threshold <1000
        # Then: Should raise ValueError

        with pytest.raises(ValueError, match="large_order_size_threshold.*must be >= 1000"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                large_order_size_threshold=999  # Invalid: <1000
            )

        with pytest.raises(ValueError, match="large_order_size_threshold.*must be >= 1000"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                large_order_size_threshold=500  # Invalid: <1000
            )

    def test_large_order_size_threshold_accepts_valid_values(self):
        """Test that large_order_size_threshold accepts valid values >= 1000."""
        # Given: OrderFlowConfig with valid thresholds
        # When: Creating config with threshold >=1000
        # Then: Should succeed without error

        config_1000 = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            large_order_size_threshold=1_000
        )
        assert config_1000.large_order_size_threshold == 1_000

        config_10k = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            large_order_size_threshold=10_000
        )
        assert config_10k.large_order_size_threshold == 10_000

        config_100k = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            large_order_size_threshold=100_000
        )
        assert config_100k.large_order_size_threshold == 100_000

    def test_volume_spike_threshold_range_validation(self):
        """Test that volume_spike_threshold must be between 1.5 and 10.0x."""
        # Given: OrderFlowConfig with invalid volume_spike_threshold
        # When: Creating config with threshold outside 1.5-10.0 range
        # Then: Should raise ValueError

        with pytest.raises(ValueError, match="volume_spike_threshold.*must be between 1.5 and 10.0"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                volume_spike_threshold=1.4  # Invalid: <1.5
            )

        with pytest.raises(ValueError, match="volume_spike_threshold.*must be between 1.5 and 10.0"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                volume_spike_threshold=10.1  # Invalid: >10.0
            )

        with pytest.raises(ValueError, match="volume_spike_threshold.*must be between 1.5 and 10.0"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                volume_spike_threshold=0.5  # Invalid: <1.5
            )

    def test_volume_spike_threshold_accepts_valid_range(self):
        """Test that volume_spike_threshold accepts valid range 1.5-10.0x."""
        # Given: OrderFlowConfig with valid volume_spike_threshold
        # When: Creating config with threshold in 1.5-10.0 range
        # Then: Should succeed without error

        config_min = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            volume_spike_threshold=1.5
        )
        assert config_min.volume_spike_threshold == 1.5

        config_mid = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            volume_spike_threshold=5.0,
            red_burst_threshold=5.0  # Must be >= volume_spike_threshold
        )
        assert config_mid.volume_spike_threshold == 5.0

        config_max = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            volume_spike_threshold=10.0,
            red_burst_threshold=10.0  # Must be >= volume_spike_threshold
        )
        assert config_max.volume_spike_threshold == 10.0

    def test_red_burst_threshold_must_exceed_volume_spike_threshold(self):
        """Test that red_burst_threshold must be >= volume_spike_threshold."""
        # Given: OrderFlowConfig with red_burst < volume_spike
        # When: Creating config with invalid threshold relationship
        # Then: Should raise ValueError

        with pytest.raises(ValueError, match="red_burst_threshold.*must be >= volume_spike_threshold"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                volume_spike_threshold=3.0,
                red_burst_threshold=2.5  # Invalid: <volume_spike_threshold
            )

    def test_red_burst_threshold_accepts_valid_values(self):
        """Test that red_burst_threshold accepts values >= volume_spike_threshold."""
        # Given: OrderFlowConfig with valid threshold relationship
        # When: Creating config with red_burst >= volume_spike
        # Then: Should succeed without error

        config_equal = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            volume_spike_threshold=3.0,
            red_burst_threshold=3.0  # Valid: equal
        )
        assert config_equal.red_burst_threshold == 3.0

        config_greater = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            volume_spike_threshold=3.0,
            red_burst_threshold=4.0  # Valid: greater
        )
        assert config_greater.red_burst_threshold == 4.0

    def test_alert_window_seconds_range_validation(self):
        """Test that alert_window_seconds must be between 30 and 300 seconds."""
        # Given: OrderFlowConfig with invalid alert_window_seconds
        # When: Creating config with window outside 30-300 range
        # Then: Should raise ValueError

        with pytest.raises(ValueError, match="alert_window_seconds.*must be between 30 and 300"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                alert_window_seconds=29  # Invalid: <30
            )

        with pytest.raises(ValueError, match="alert_window_seconds.*must be between 30 and 300"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                alert_window_seconds=301  # Invalid: >300
            )

    def test_alert_window_seconds_accepts_valid_range(self):
        """Test that alert_window_seconds accepts valid range 30-300 seconds."""
        # Given: OrderFlowConfig with valid alert_window_seconds
        # When: Creating config with window in 30-300 range
        # Then: Should succeed without error

        config_min = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            alert_window_seconds=30
        )
        assert config_min.alert_window_seconds == 30

        config_mid = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            alert_window_seconds=120
        )
        assert config_mid.alert_window_seconds == 120

        config_max = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            alert_window_seconds=300
        )
        assert config_max.alert_window_seconds == 300

    def test_polygon_api_key_required_when_data_source_polygon(self):
        """Test that polygon_api_key is required when data_source='polygon'."""
        # Given: OrderFlowConfig with data_source='polygon' but no API key
        # When: Creating config without polygon_api_key
        # Then: Should raise ValueError

        with pytest.raises(ValueError, match="polygon_api_key is required"):
            OrderFlowConfig(
                data_source="polygon",
                polygon_api_key=""  # Invalid: empty
            )

    def test_monitoring_mode_validation(self):
        """Test that monitoring_mode must be valid option."""
        # Given: OrderFlowConfig with invalid monitoring_mode
        # When: Creating config with unsupported monitoring_mode
        # Then: Should raise ValueError

        with pytest.raises(ValueError, match="monitoring_mode.*must be one of"):
            OrderFlowConfig(
                polygon_api_key="test_key_1234567890",
                monitoring_mode="continuous"  # Invalid: not in VALID_MONITORING_MODES
            )

    def test_monitoring_mode_accepts_valid_options(self):
        """Test that monitoring_mode accepts valid options."""
        # Given: OrderFlowConfig with valid monitoring_mode
        # When: Creating config with supported monitoring_mode
        # Then: Should succeed without error

        config_positions = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            monitoring_mode="positions_only"
        )
        assert config_positions.monitoring_mode == "positions_only"

        config_watchlist = OrderFlowConfig(
            polygon_api_key="test_key_1234567890",
            monitoring_mode="watchlist"
        )
        assert config_watchlist.monitoring_mode == "watchlist"


class TestOrderFlowConfigFromEnv:
    """Test suite for OrderFlowConfig.from_env() class method."""

    @patch.dict(os.environ, {
        "ORDER_FLOW_DATA_SOURCE": "polygon",
        "POLYGON_API_KEY": "test_api_key_from_env",
        "ORDER_FLOW_LARGE_ORDER_SIZE": "15000",
        "ORDER_FLOW_VOLUME_SPIKE_THRESHOLD": "3.5",
        "ORDER_FLOW_RED_BURST_THRESHOLD": "5.0",
        "ORDER_FLOW_ALERT_WINDOW_SECONDS": "180",
        "ORDER_FLOW_MONITORING_MODE": "watchlist"
    })
    def test_from_env_loads_all_environment_variables(self):
        """Test that from_env() loads all OrderFlowConfig fields from environment."""
        # Given: Environment variables set for all config fields
        # When: Loading config from environment
        config = OrderFlowConfig.from_env()

        # Then: All fields should match environment values
        assert config.data_source == "polygon"
        assert config.polygon_api_key == "test_api_key_from_env"
        assert config.large_order_size_threshold == 15_000
        assert config.volume_spike_threshold == 3.5
        assert config.red_burst_threshold == 5.0
        assert config.alert_window_seconds == 180
        assert config.monitoring_mode == "watchlist"

    @patch.dict(os.environ, {
        "POLYGON_API_KEY": "test_api_key_minimal"
    }, clear=True)
    def test_from_env_uses_defaults_when_env_vars_missing(self):
        """Test that from_env() uses sensible defaults when env vars missing."""
        # Given: Only POLYGON_API_KEY set (minimum required)
        # When: Loading config from environment
        config = OrderFlowConfig.from_env()

        # Then: Should use defaults from spec.md
        assert config.data_source == "polygon"  # Default
        assert config.polygon_api_key == "test_api_key_minimal"  # From env
        assert config.large_order_size_threshold == 10_000  # Default
        assert config.volume_spike_threshold == 3.0  # Default
        assert config.red_burst_threshold == 4.0  # Default
        assert config.alert_window_seconds == 120  # Default
        assert config.monitoring_mode == "positions_only"  # Default

    @patch.dict(os.environ, {
        "POLYGON_API_KEY": "test_key_12345",
        "ORDER_FLOW_LARGE_ORDER_SIZE": "5000"  # Valid override
    })
    def test_from_env_partial_override_uses_defaults_for_rest(self):
        """Test that from_env() mixes env vars and defaults correctly."""
        # Given: Only some environment variables set
        # When: Loading config from environment
        config = OrderFlowConfig.from_env()

        # Then: Should use env var for overridden field, defaults for rest
        assert config.polygon_api_key == "test_key_12345"  # From env
        assert config.large_order_size_threshold == 5_000  # From env (overridden)
        assert config.volume_spike_threshold == 3.0  # Default
        assert config.red_burst_threshold == 4.0  # Default

    @patch.dict(os.environ, {
        "POLYGON_API_KEY": "test_key_12345",
        "ORDER_FLOW_LARGE_ORDER_SIZE": "invalid_number"  # Invalid: not an int
    })
    def test_from_env_raises_error_on_invalid_type_conversion(self):
        """Test that from_env() raises error when env var cannot be converted to expected type."""
        # Given: Environment variable with invalid type (non-integer for int field)
        # When: Loading config from environment
        # Then: Should raise ValueError during int() conversion

        with pytest.raises(ValueError):
            OrderFlowConfig.from_env()

    @patch.dict(os.environ, {
        "POLYGON_API_KEY": "test_key_12345",
        "ORDER_FLOW_LARGE_ORDER_SIZE": "500"  # Valid conversion, but fails validation (<1000)
    })
    def test_from_env_validates_after_loading(self):
        """Test that from_env() validates config after loading from environment."""
        # Given: Environment variable with value that converts but fails validation
        # When: Loading config from environment
        # Then: Should raise ValueError during __post_init__ validation

        with pytest.raises(ValueError, match="large_order_size_threshold.*must be >= 1000"):
            OrderFlowConfig.from_env()


class TestOrderFlowConfigPersistence:
    """Test suite for OrderFlowConfig save/load functionality (T031)."""

    def test_save_creates_config_file(self, tmp_path):
        """Test that save() creates a JSON config file."""
        # Given: OrderFlowConfig instance
        config = OrderFlowConfig(
            polygon_api_key="test_key_save",
            large_order_size_threshold=15_000,
            volume_spike_threshold=3.5
        )

        # When: Saving config to temp path
        config_path = tmp_path / "test_config.json"
        config.save(config_path)

        # Then: File should exist and contain valid JSON
        assert config_path.exists()
        with open(config_path, "r") as f:
            data = f.read()
            assert "test_key_save" in data
            assert "15000" in data

    def test_load_reads_config_from_file(self, tmp_path):
        """Test that load() reads config from JSON file."""
        # Given: Saved config file
        config_path = tmp_path / "test_config.json"
        original_config = OrderFlowConfig(
            polygon_api_key="test_key_load",
            large_order_size_threshold=20_000,
            volume_spike_threshold=4.5,
            red_burst_threshold=5.5
        )
        original_config.save(config_path)

        # When: Loading config from file
        loaded_config = OrderFlowConfig.load(config_path)

        # Then: Should match original config
        assert loaded_config.polygon_api_key == "test_key_load"
        assert loaded_config.large_order_size_threshold == 20_000
        assert loaded_config.volume_spike_threshold == 4.5
        assert loaded_config.red_burst_threshold == 5.5

    @patch.dict(os.environ, {"POLYGON_API_KEY": "env_key_fallback"})
    def test_load_falls_back_to_env_when_file_missing(self, tmp_path):
        """Test that load() falls back to from_env() when file doesn't exist."""
        # Given: Non-existent config file
        config_path = tmp_path / "missing_config.json"
        assert not config_path.exists()

        # When: Loading config from missing file
        config = OrderFlowConfig.load(config_path)

        # Then: Should use environment variables
        assert config.polygon_api_key == "env_key_fallback"
        assert config.large_order_size_threshold == 10_000  # Default

    def test_save_load_round_trip_preserves_all_fields(self, tmp_path):
        """Test that save() followed by load() preserves all config fields."""
        # Given: OrderFlowConfig with non-default values
        config_path = tmp_path / "round_trip_config.json"
        original_config = OrderFlowConfig(
            data_source="polygon",
            polygon_api_key="test_key_round_trip",
            large_order_size_threshold=25_000,
            volume_spike_threshold=5.0,
            red_burst_threshold=6.0,
            alert_window_seconds=180,
            monitoring_mode="watchlist"
        )

        # When: Save and then load
        original_config.save(config_path)
        loaded_config = OrderFlowConfig.load(config_path)

        # Then: All fields should match
        assert loaded_config.data_source == original_config.data_source
        assert loaded_config.polygon_api_key == original_config.polygon_api_key
        assert loaded_config.large_order_size_threshold == original_config.large_order_size_threshold
        assert loaded_config.volume_spike_threshold == original_config.volume_spike_threshold
        assert loaded_config.red_burst_threshold == original_config.red_burst_threshold
        assert loaded_config.alert_window_seconds == original_config.alert_window_seconds
        assert loaded_config.monitoring_mode == original_config.monitoring_mode
