"""
Tests for MomentumConfig dataclass

Validates configuration loading, defaults, and validation logic.
"""

import os
import pytest
from src.trading_bot.momentum.config import MomentumConfig


class TestMomentumConfigDefaults:
    """Test default values from spec.md"""

    def test_default_values_match_spec(self):
        """Verify all defaults match spec.md requirements"""
        config = MomentumConfig()

        assert config.news_api_key == ""
        assert config.market_data_source == "alpaca"
        assert config.min_catalyst_strength == 5.0
        assert config.min_premarket_change_pct == 5.0
        assert config.min_volume_ratio == 200.0
        assert config.pole_min_gain_pct == 8.0
        assert config.flag_range_pct_min == 3.0
        assert config.flag_range_pct_max == 5.0

    def test_config_is_frozen(self):
        """Verify dataclass is immutable"""
        config = MomentumConfig()

        with pytest.raises(AttributeError):
            config.min_catalyst_strength = 10.0


class TestMomentumConfigValidation:
    """Test validation rules in __post_init__"""

    def test_negative_percentage_raises_error(self):
        """Negative percentage values should raise ValueError"""
        with pytest.raises(ValueError, match="must be positive"):
            MomentumConfig(min_catalyst_strength=-5.0)

        with pytest.raises(ValueError, match="must be positive"):
            MomentumConfig(min_premarket_change_pct=-5.0)

        with pytest.raises(ValueError, match="must be positive"):
            MomentumConfig(min_volume_ratio=-200.0)

        with pytest.raises(ValueError, match="must be positive"):
            MomentumConfig(pole_min_gain_pct=-8.0)

    def test_zero_percentage_raises_error(self):
        """Zero percentage values should raise ValueError"""
        with pytest.raises(ValueError, match="must be positive"):
            MomentumConfig(min_catalyst_strength=0.0)

    def test_invalid_market_data_source_raises_error(self):
        """Invalid market data source should raise ValueError"""
        with pytest.raises(ValueError, match="must be one of"):
            MomentumConfig(market_data_source="invalid")

        with pytest.raises(ValueError, match="must be one of"):
            MomentumConfig(market_data_source="")

    def test_valid_market_data_sources_accepted(self):
        """Valid market data sources should be accepted"""
        # Should not raise
        MomentumConfig(market_data_source="alpaca")
        MomentumConfig(market_data_source="polygon")
        MomentumConfig(market_data_source="iex")

    def test_flag_range_min_greater_than_max_raises_error(self):
        """Flag range min > max should raise ValueError"""
        with pytest.raises(ValueError, match="must be <="):
            MomentumConfig(flag_range_pct_min=6.0, flag_range_pct_max=5.0)

    def test_flag_range_min_equal_to_max_accepted(self):
        """Flag range min = max should be accepted"""
        # Should not raise
        config = MomentumConfig(flag_range_pct_min=4.0, flag_range_pct_max=4.0)
        assert config.flag_range_pct_min == 4.0
        assert config.flag_range_pct_max == 4.0


class TestMomentumConfigFromEnv:
    """Test environment variable loading"""

    def test_from_env_loads_environment_variables(self, monkeypatch):
        """from_env() should load values from environment"""
        monkeypatch.setenv("NEWS_API_KEY", "test-api-key-12345")
        monkeypatch.setenv("MARKET_DATA_SOURCE", "polygon")

        config = MomentumConfig.from_env()

        assert config.news_api_key == "test-api-key-12345"
        assert config.market_data_source == "polygon"

    def test_from_env_uses_defaults_when_env_not_set(self, monkeypatch):
        """from_env() should use defaults when env vars not set"""
        monkeypatch.delenv("NEWS_API_KEY", raising=False)
        monkeypatch.delenv("MARKET_DATA_SOURCE", raising=False)

        config = MomentumConfig.from_env()

        assert config.news_api_key == ""
        assert config.market_data_source == "alpaca"

    def test_from_env_empty_news_api_key_accepted(self, monkeypatch):
        """from_env() should accept empty NEWS_API_KEY (for testing)"""
        monkeypatch.setenv("NEWS_API_KEY", "")

        config = MomentumConfig.from_env()

        assert config.news_api_key == ""

    def test_from_env_invalid_market_data_source_raises_error(self, monkeypatch):
        """from_env() should validate MARKET_DATA_SOURCE"""
        monkeypatch.setenv("MARKET_DATA_SOURCE", "invalid-source")

        with pytest.raises(ValueError, match="must be one of"):
            MomentumConfig.from_env()
