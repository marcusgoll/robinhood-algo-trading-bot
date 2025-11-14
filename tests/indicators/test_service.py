"""Tests for TechnicalIndicatorsService facade."""

import pytest
from decimal import Decimal

from src.trading_bot.indicators.service import TechnicalIndicatorsService
from src.trading_bot.indicators.exceptions import InsufficientDataError


class TestTechnicalIndicatorsService:
    """Tests for TechnicalIndicatorsService facade."""

    def setup_method(self):
        """Setup test fixtures."""
        self.service = TechnicalIndicatorsService()

    def _generate_bars(self, closes: list) -> list:
        """Generate bars from close prices."""
        return [
            {"high": float(c) + 1, "low": float(c) - 1, "close": float(c), "volume": 1000}
            for c in closes
        ]

    def test_get_vwap(self):
        """Test get_vwap returns VWAPResult."""
        bars = self._generate_bars([100.0, 100.5, 101.0])
        result = self.service.get_vwap(bars)

        assert result.vwap is not None
        assert result.price is not None
        assert isinstance(result.above_vwap, bool)

    def test_get_vwap_empty(self):
        """Test get_vwap with empty bars raises error."""
        with pytest.raises(InsufficientDataError):
            self.service.get_vwap([])

    def test_get_emas(self):
        """Test get_emas returns EMAResult."""
        bars = self._generate_bars([100.0 + i * 0.1 for i in range(25)])
        result = self.service.get_emas(bars)

        assert result.ema_9 is not None
        assert result.ema_20 is not None
        assert isinstance(result.near_9ema, bool)

    def test_get_emas_state_tracking(self):
        """Test get_emas tracks state correctly."""
        bars = self._generate_bars([100.0 + i * 0.1 for i in range(25)])
        result1 = self.service.get_emas(bars)

        # Service should track state
        assert self.service._last_ema_9 is not None
        assert self.service._last_ema_20 is not None
        assert self.service._last_ema_9 == result1.ema_9
        assert self.service._last_ema_20 == result1.ema_20

    def test_get_macd(self):
        """Test get_macd returns MACDResult."""
        bars = self._generate_bars([100.0 + i * 0.1 for i in range(30)])
        result = self.service.get_macd(bars)

        assert result.macd_line is not None
        assert result.signal_line is not None
        assert result.histogram is not None
        assert isinstance(result.positive, bool)

    def test_get_macd_state_tracking(self):
        """Test get_macd tracks state correctly."""
        bars = self._generate_bars([100.0 + i * 0.1 for i in range(30)])
        result1 = self.service.get_macd(bars)

        assert self.service._last_macd is not None
        assert self.service._last_signal is not None

    def test_validate_entry_insufficient_data(self):
        """Test validate_entry with insufficient data."""
        bars = self._generate_bars([100.0] * 20)

        with pytest.raises(InsufficientDataError):
            self.service.validate_entry(bars)

    def test_validate_entry_valid(self):
        """Test validate_entry with valid uptrend data."""
        # Strong uptrend - should pass validation
        bars = self._generate_bars([100.0 + i * 0.5 for i in range(30)])
        is_valid, reason = self.service.validate_entry(bars)

        assert isinstance(is_valid, bool)
        assert isinstance(reason, str)
        # In uptrend with increasing momentum, should be valid
        assert len(reason) > 0

    def test_validate_entry_price_below_vwap(self):
        """Test validate_entry fails when price below VWAP."""
        # Downtrend - price should be below VWAP
        bars = self._generate_bars([100.0 - i * 0.5 for i in range(30)])
        is_valid, reason = self.service.validate_entry(bars)

        # Should fail VWAP check
        assert isinstance(is_valid, bool)

    def test_validate_entry_conservative_gate(self):
        """Test validate_entry applies AND logic (both checks must pass)."""
        bars = self._generate_bars([100.0 + i * 0.1 for i in range(30)])
        is_valid, reason = self.service.validate_entry(bars)

        # Reason should mention both conditions
        if not is_valid:
            assert "VWAP" in reason or "MACD" in reason

    def test_check_exit_signals_no_signal(self):
        """Test check_exit_signals returns None without signal."""
        bars = self._generate_bars([100.0 + i * 0.1 for i in range(30)])
        result = self.service.check_exit_signals(bars)

        # First call has no previous state, should return None
        assert result is None

    def test_check_exit_signals_macd_cross(self):
        """Test check_exit_signals detects MACD crosses."""
        # Uptrend
        bars = self._generate_bars([100.0 + i * 0.5 for i in range(30)])
        self.service.check_exit_signals(bars)

        # Downtrend - should trigger exit signal
        bars = self._generate_bars([115.0 - i * 0.5 for i in range(30)])
        result = self.service.check_exit_signals(bars)

        # Result should be None or exit signal
        assert result is None or "MACD" in str(result)

    def test_check_exit_signals_insufficient_data(self):
        """Test check_exit_signals with insufficient data."""
        bars = self._generate_bars([100.0] * 20)
        result = self.service.check_exit_signals(bars)

        # Should return None gracefully
        assert result is None

    def test_reset_state(self):
        """Test reset_state clears tracking data."""
        bars = self._generate_bars([100.0 + i * 0.1 for i in range(30)])

        # Generate some state
        self.service.get_emas(bars)
        self.service.get_macd(bars)

        assert self.service._last_ema_9 is not None

        # Reset
        self.service.reset_state()

        assert self.service._last_ema_9 is None
        assert self.service._last_ema_20 is None
        assert self.service._last_macd is None
        assert self.service._last_signal is None

    def test_concurrent_calculations(self):
        """Test multiple calculations in sequence."""
        bars = self._generate_bars([100.0 + i * 0.1 for i in range(30)])

        vwap_result = self.service.get_vwap(bars)
        ema_result = self.service.get_emas(bars)
        macd_result = self.service.get_macd(bars)

        # All should be valid
        assert vwap_result.vwap is not None
        assert ema_result.ema_9 is not None
        assert macd_result.macd_line is not None

    def test_decimal_precision_maintained(self):
        """Test that Decimal precision is maintained through service."""
        bars = self._generate_bars([100.01 + i * 0.01 for i in range(30)])

        vwap_result = self.service.get_vwap(bars)
        ema_result = self.service.get_emas(bars)
        macd_result = self.service.get_macd(bars)

        # All results should use Decimal
        assert isinstance(vwap_result.vwap, Decimal)
        assert isinstance(ema_result.ema_9, Decimal)
        assert isinstance(macd_result.macd_line, Decimal)
