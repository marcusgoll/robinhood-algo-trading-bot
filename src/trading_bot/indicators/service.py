"""Technical indicators service facade."""

from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from .calculators import VWAPCalculator, EMACalculator, MACDCalculator
from .calculators import VWAPResult, EMAResult, MACDResult
from .exceptions import InsufficientDataError


class TechnicalIndicatorsService:
    """Facade service for technical indicators (VWAP, EMA, MACD)."""

    def __init__(self) -> None:
        """Initialize technical indicators service."""
        self.vwap_calc = VWAPCalculator()
        self.ema_calc = EMACalculator(period_9=9, period_20=20)
        self.macd_calc = MACDCalculator(fast=12, slow=26, signal=9)

        # State tracking for sequential calculations
        self._last_ema_9: Optional[Decimal] = None
        self._last_ema_20: Optional[Decimal] = None
        self._last_macd: Optional[Decimal] = None
        self._last_signal: Optional[Decimal] = None

    def get_vwap(self, bars: List[Dict[str, Any]]) -> VWAPResult:
        """
        Calculate VWAP for entry validation.

        Args:
            bars: List of OHLCV bars

        Returns:
            VWAPResult with current VWAP and entry validation

        Raises:
            InsufficientDataError: If insufficient data
        """
        if not bars:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=1, available_bars=0)

        return self.vwap_calc.calculate(bars)

    def get_emas(self, bars: List[Dict[str, Any]]) -> EMAResult:
        """
        Calculate 9 and 20 period EMAs.

        Args:
            bars: List of OHLCV bars

        Returns:
            EMAResult with both EMAs and crossover detection

        Raises:
            InsufficientDataError: If insufficient data
        """
        if not bars:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=1, available_bars=0)

        result = self.ema_calc.calculate(
            bars,
            prev_ema_9=self._last_ema_9,
            prev_ema_20=self._last_ema_20
        )

        # Update state
        self._last_ema_9 = result.ema_9
        self._last_ema_20 = result.ema_20

        return result

    def get_macd(self, bars: List[Dict[str, Any]]) -> MACDResult:
        """
        Calculate MACD with signal line and histogram.

        Args:
            bars: List of OHLCV bars

        Returns:
            MACDResult with MACD values and signals

        Raises:
            InsufficientDataError: If insufficient data
        """
        if not bars:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=1, available_bars=0)

        result = self.macd_calc.calculate(
            bars,
            prev_macd=self._last_macd,
            prev_signal=self._last_signal
        )

        # Update state
        self._last_macd = result.macd_line
        self._last_signal = result.signal_line

        return result

    def validate_entry(self, bars: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Conservative entry validation: price > VWAP AND MACD > 0.

        Args:
            bars: List of OHLCV bars (minimum 26 bars for MACD)

        Returns:
            Tuple of (is_valid, reason_string)

        Raises:
            InsufficientDataError: If insufficient data
        """
        if len(bars) < 26:
            raise InsufficientDataError(
                symbol="UNKNOWN", required_bars=26, available_bars=len(bars)
            )

        # Check VWAP
        vwap_result = self.get_vwap(bars)
        if not vwap_result.above_vwap:
            return False, f"Price {vwap_result.price} below VWAP {vwap_result.vwap}"

        # Check MACD
        macd_result = self.get_macd(bars)
        if not macd_result.positive:
            return False, f"MACD {macd_result.macd_line} is not positive"

        return True, f"Valid entry: price > VWAP ({vwap_result.price} > {vwap_result.vwap}) AND MACD > 0 ({macd_result.macd_line})"

    def check_exit_signals(self, bars: List[Dict[str, Any]]) -> Optional[str]:
        """
        Check for exit signals (MACD crossing negative).

        Args:
            bars: List of OHLCV bars

        Returns:
            Exit signal reason or None if no signal

        Raises:
            InsufficientDataError: If insufficient data
        """
        if len(bars) < 26:
            return None

        try:
            macd_result = self.get_macd(bars)

            # Exit on MACD crossing negative
            if self._last_macd is not None:
                was_positive = self._last_macd > Decimal("0")
                is_negative = macd_result.macd_line < Decimal("0")

                if was_positive and is_negative:
                    return f"MACD crossed negative: {self._last_macd} → {macd_result.macd_line}"

            return None
        except InsufficientDataError:
            return None

    def reset_state(self) -> None:
        """Reset state tracking (useful for new trading sessions)."""
        self._last_ema_9 = None
        self._last_ema_20 = None
        self._last_macd = None
        self._last_signal = None
