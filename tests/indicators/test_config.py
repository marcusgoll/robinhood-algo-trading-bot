"""Tests for technical indicators configuration."""

import pytest
from src.trading_bot.indicators.config import IndicatorConfig


class TestIndicatorConfig:
    """Tests for IndicatorConfig dataclass and validation."""

    def test_default_config(self):
        """Test IndicatorConfig with default values."""
        config = IndicatorConfig()

        assert config.vwap_min_bars == 10
        assert config.ema_periods == [9, 20]
        assert config.ema_proximity_threshold_pct == 2.0
        assert config.macd_fast_period == 12
        assert config.macd_slow_period == 26
        assert config.macd_signal_period == 9
        assert config.refresh_interval_seconds == 300

    def test_custom_config(self):
        """Test IndicatorConfig with custom values."""
        config = IndicatorConfig(
            vwap_min_bars=15,
            ema_periods=[8, 17],
            ema_proximity_threshold_pct=1.5,
            macd_fast_period=10,
            macd_slow_period=25,
            macd_signal_period=8,
            refresh_interval_seconds=600
        )

        assert config.vwap_min_bars == 15
        assert config.ema_periods == [8, 17]
        assert config.ema_proximity_threshold_pct == 1.5
        assert config.macd_fast_period == 10
        assert config.macd_slow_period == 25
        assert config.macd_signal_period == 8
        assert config.refresh_interval_seconds == 600

    def test_vwap_min_bars_invalid_zero(self):
        """Test IndicatorConfig with invalid vwap_min_bars (zero)."""
        with pytest.raises(ValueError, match="vwap_min_bars must be >= 1"):
            IndicatorConfig(vwap_min_bars=0)

    def test_vwap_min_bars_invalid_negative(self):
        """Test IndicatorConfig with invalid vwap_min_bars (negative)."""
        with pytest.raises(ValueError, match="vwap_min_bars must be >= 1"):
            IndicatorConfig(vwap_min_bars=-1)

    def test_ema_periods_empty(self):
        """Test IndicatorConfig with empty ema_periods."""
        with pytest.raises(ValueError, match="ema_periods cannot be empty"):
            IndicatorConfig(ema_periods=[])

    def test_ema_periods_invalid_zero(self):
        """Test IndicatorConfig with invalid EMA period (zero)."""
        with pytest.raises(ValueError, match="All EMA periods must be > 0"):
            IndicatorConfig(ema_periods=[9, 0])

    def test_ema_periods_invalid_negative(self):
        """Test IndicatorConfig with invalid EMA period (negative)."""
        with pytest.raises(ValueError, match="All EMA periods must be > 0"):
            IndicatorConfig(ema_periods=[9, -5])

    def test_ema_proximity_threshold_negative(self):
        """Test IndicatorConfig with negative ema_proximity_threshold_pct."""
        with pytest.raises(ValueError, match="ema_proximity_threshold_pct must be >= 0"):
            IndicatorConfig(ema_proximity_threshold_pct=-0.5)

    def test_ema_proximity_threshold_valid_zero(self):
        """Test IndicatorConfig with zero ema_proximity_threshold_pct (valid)."""
        config = IndicatorConfig(ema_proximity_threshold_pct=0.0)
        assert config.ema_proximity_threshold_pct == 0.0

    def test_macd_fast_period_invalid_zero(self):
        """Test IndicatorConfig with invalid macd_fast_period (zero)."""
        with pytest.raises(ValueError, match="macd_fast_period must be > 0"):
            IndicatorConfig(macd_fast_period=0)

    def test_macd_fast_period_invalid_negative(self):
        """Test IndicatorConfig with invalid macd_fast_period (negative)."""
        with pytest.raises(ValueError, match="macd_fast_period must be > 0"):
            IndicatorConfig(macd_fast_period=-1)

    def test_macd_slow_period_invalid_zero(self):
        """Test IndicatorConfig with invalid macd_slow_period (zero)."""
        with pytest.raises(ValueError, match="macd_slow_period must be > 0"):
            IndicatorConfig(macd_slow_period=0)

    def test_macd_slow_period_invalid_negative(self):
        """Test IndicatorConfig with invalid macd_slow_period (negative)."""
        with pytest.raises(ValueError, match="macd_slow_period must be > 0"):
            IndicatorConfig(macd_slow_period=-1)

    def test_macd_signal_period_invalid_zero(self):
        """Test IndicatorConfig with invalid macd_signal_period (zero)."""
        with pytest.raises(ValueError, match="macd_signal_period must be > 0"):
            IndicatorConfig(macd_signal_period=0)

    def test_macd_signal_period_invalid_negative(self):
        """Test IndicatorConfig with invalid macd_signal_period (negative)."""
        with pytest.raises(ValueError, match="macd_signal_period must be > 0"):
            IndicatorConfig(macd_signal_period=-1)

    def test_macd_fast_not_less_than_slow(self):
        """Test IndicatorConfig with macd_fast_period >= macd_slow_period."""
        with pytest.raises(ValueError, match="macd_fast_period.*must be < macd_slow_period"):
            IndicatorConfig(macd_fast_period=26, macd_slow_period=26)

    def test_macd_fast_greater_than_slow(self):
        """Test IndicatorConfig with macd_fast_period > macd_slow_period."""
        with pytest.raises(ValueError, match="macd_fast_period.*must be < macd_slow_period"):
            IndicatorConfig(macd_fast_period=30, macd_slow_period=26)

    def test_refresh_interval_invalid_zero(self):
        """Test IndicatorConfig with invalid refresh_interval_seconds (zero)."""
        with pytest.raises(ValueError, match="refresh_interval_seconds must be >= 60"):
            IndicatorConfig(refresh_interval_seconds=0)

    def test_refresh_interval_invalid_too_low(self):
        """Test IndicatorConfig with invalid refresh_interval_seconds (too low)."""
        with pytest.raises(ValueError, match="refresh_interval_seconds must be >= 60"):
            IndicatorConfig(refresh_interval_seconds=59)

    def test_refresh_interval_valid_minimum(self):
        """Test IndicatorConfig with valid minimum refresh_interval_seconds (60)."""
        config = IndicatorConfig(refresh_interval_seconds=60)
        assert config.refresh_interval_seconds == 60

    def test_refresh_interval_valid_large(self):
        """Test IndicatorConfig with large refresh_interval_seconds."""
        config = IndicatorConfig(refresh_interval_seconds=3600)  # 1 hour
        assert config.refresh_interval_seconds == 3600

    def test_multiple_validations_combined(self):
        """Test multiple validation checks in single config."""
        # All invalid parameters - should fail on first check
        with pytest.raises(ValueError):
            IndicatorConfig(
                vwap_min_bars=0,
                ema_periods=[0],
                macd_fast_period=30,
                macd_slow_period=26,
                refresh_interval_seconds=30
            )

    def test_all_valid_custom_config(self):
        """Test IndicatorConfig with all valid custom parameters."""
        config = IndicatorConfig(
            vwap_min_bars=20,
            ema_periods=[5, 15, 30],
            ema_proximity_threshold_pct=3.0,
            macd_fast_period=10,
            macd_slow_period=30,
            macd_signal_period=7,
            refresh_interval_seconds=120
        )

        assert config.vwap_min_bars == 20
        assert config.ema_periods == [5, 15, 30]
        assert config.ema_proximity_threshold_pct == 3.0
        assert config.macd_fast_period == 10
        assert config.macd_slow_period == 30
        assert config.macd_signal_period == 7
        assert config.refresh_interval_seconds == 120
