"""Technical indicator calculators: VWAP, EMA, MACD."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from datetime import datetime, timedelta

from .exceptions import InsufficientDataError


@dataclass
class VWAPResult:
    """Result of VWAP calculation."""
    symbol: str
    vwap: Decimal
    price: Decimal
    above_vwap: bool
    timestamp: datetime


@dataclass
class EMAResult:
    """Result of EMA calculation."""
    symbol: str
    ema_9: Decimal
    ema_20: Decimal
    price: Decimal
    near_9ema: bool  # price within 1% of 9 EMA
    crossover: Optional[str]  # "bullish" or "bearish" if crossing detected
    timestamp: datetime


@dataclass
class CrossoverSignal:
    """EMA crossover signal."""
    type: str  # "bullish" (9 crosses above 20) or "bearish" (9 crosses below 20)
    timestamp: datetime


@dataclass
class MACDResult:
    """Result of MACD calculation."""
    symbol: str
    macd_line: Decimal
    signal_line: Decimal
    histogram: Decimal
    positive: bool  # MACD > 0
    divergence: Optional[str]  # "bullish" or "bearish"
    cross: Optional[str]  # "bullish" or "bearish" if MACD crosses signal
    timestamp: datetime


@dataclass
class ExitSignal:
    """Exit signal from MACD crossing below 0."""
    type: str  # "macd_cross_negative"
    timestamp: datetime


class VWAPCalculator:
    """Volume Weighted Average Price calculator."""

    def __init__(self):
        """Initialize VWAP calculator."""
        pass

    def calculate(self, bars: List[dict]) -> VWAPResult:
        """
        Calculate VWAP from intraday bars.

        Args:
            bars: List of OHLCV bars with keys: high, low, close, volume

        Returns:
            VWAPResult with VWAP value and entry validation

        Raises:
            InsufficientDataError: If no bars provided
        """
        if not bars:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=1, available_bars=0)

        typical_price_volume_sum = Decimal("0")
        volume_sum = Decimal("0")

        for bar in bars:
            high = Decimal(str(bar["high"]))
            low = Decimal(str(bar["low"]))
            close = Decimal(str(bar["close"]))
            volume = Decimal(str(bar["volume"]))

            typical_price = (high + low + close) / Decimal("3")
            typical_price_volume_sum += typical_price * volume
            volume_sum += volume

        if volume_sum == 0:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=1, available_bars=len(bars))

        vwap = (typical_price_volume_sum / volume_sum).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        current_price = Decimal(str(bars[-1]["close"]))
        above_vwap = current_price > vwap

        return VWAPResult(
            symbol="UNKNOWN",
            vwap=vwap,
            price=current_price,
            above_vwap=above_vwap,
            timestamp=datetime.utcnow()
        )


class EMACalculator:
    """Exponential Moving Average calculator (9 and 20 period)."""

    def __init__(self, period_9: int = 9, period_20: int = 20):
        """Initialize EMA calculator."""
        self.period_9 = period_9
        self.period_20 = period_20
        self._multiplier_9 = Decimal("2") / (Decimal(str(period_9)) + Decimal("1"))
        self._multiplier_20 = Decimal("2") / (Decimal(str(period_20)) + Decimal("1"))

    def _calculate_sma(self, closes: List[Decimal], period: int) -> Decimal:
        """Calculate Simple Moving Average."""
        if len(closes) < period:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=period, available_bars=len(closes))

        sma = sum(closes[-period:]) / Decimal(str(period))
        return sma.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_ema(
        self,
        closes: List[Decimal],
        period: int,
        multiplier: Decimal,
        prev_ema: Optional[Decimal] = None
    ) -> Decimal:
        """Calculate Exponential Moving Average."""
        if len(closes) < period:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=period, available_bars=len(closes))

        if prev_ema is None:
            # First EMA is SMA
            prev_ema = self._calculate_sma(closes[:period], period)

        current_close = closes[-1]
        ema = (current_close * multiplier) + (prev_ema * (Decimal("1") - multiplier))
        return ema.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate(self, bars: List[dict], prev_ema_9: Optional[Decimal] = None,
                  prev_ema_20: Optional[Decimal] = None) -> EMAResult:
        """
        Calculate 9 and 20 period EMAs.

        Args:
            bars: List of OHLCV bars with 'close' key
            prev_ema_9: Previous 9-period EMA (optional, uses SMA on first calc)
            prev_ema_20: Previous 20-period EMA (optional, uses SMA on first calc)

        Returns:
            EMAResult with both EMAs and crossover detection

        Raises:
            InsufficientDataError: If insufficient bars for calculation
        """
        if not bars:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=1, available_bars=0)

        if len(bars) < self.period_20:
            raise InsufficientDataError(
                symbol="UNKNOWN", required_bars=self.period_20, available_bars=len(bars)
            )

        closes = [Decimal(str(bar["close"])) for bar in bars]

        # Calculate EMAs
        ema_9 = self._calculate_ema(closes, self.period_9, self._multiplier_9, prev_ema_9)
        ema_20 = self._calculate_ema(closes, self.period_20, self._multiplier_20, prev_ema_20)

        # Check if price is near 9 EMA (within 1%)
        current_price = closes[-1]
        threshold = ema_9 * Decimal("0.01")
        near_9ema = abs(current_price - ema_9) <= threshold

        # Detect crossovers (if previous EMAs provided)
        crossover = None
        if prev_ema_9 is not None and prev_ema_20 is not None:
            was_above = prev_ema_9 > prev_ema_20
            is_above = ema_9 > ema_20

            if not was_above and is_above:
                crossover = "bullish"
            elif was_above and not is_above:
                crossover = "bearish"

        return EMAResult(
            symbol="UNKNOWN",
            ema_9=ema_9,
            ema_20=ema_20,
            price=current_price,
            near_9ema=near_9ema,
            crossover=crossover,
            timestamp=datetime.utcnow()
        )


class MACDCalculator:
    """MACD (Moving Average Convergence Divergence) calculator."""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        """Initialize MACD calculator."""
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.ema_calc_fast = EMACalculator(period_9=fast, period_20=fast)
        self.ema_calc_slow = EMACalculator(period_9=slow, period_20=slow)
        self.ema_calc_signal = EMACalculator(period_9=signal, period_20=signal)

    def calculate(
        self,
        bars: List[dict],
        prev_macd: Optional[Decimal] = None,
        prev_signal: Optional[Decimal] = None
    ) -> MACDResult:
        """
        Calculate MACD line, signal line, and histogram.

        Args:
            bars: List of OHLCV bars with 'close' key
            prev_macd: Previous MACD line (optional, uses SMA on first calc)
            prev_signal: Previous signal line (optional, uses SMA on first calc)

        Returns:
            MACDResult with MACD values and signal detection

        Raises:
            InsufficientDataError: If insufficient bars for calculation
        """
        if not bars:
            raise InsufficientDataError(symbol="UNKNOWN", required_bars=1, available_bars=0)

        if len(bars) < self.slow:
            raise InsufficientDataError(
                symbol="UNKNOWN", required_bars=self.slow, available_bars=len(bars)
            )

        closes = [Decimal(str(bar["close"])) for bar in bars]

        # Calculate MACD values for all bars to build signal line
        macd_values = []
        for i in range(self.slow, len(closes) + 1):
            window_closes = closes[:i]
            fast_ema = self.ema_calc_fast._calculate_ema(
                window_closes, self.fast,
                Decimal("2") / (Decimal(str(self.fast)) + Decimal("1"))
            )
            slow_ema = self.ema_calc_slow._calculate_ema(
                window_closes, self.slow,
                Decimal("2") / (Decimal(str(self.slow)) + Decimal("1"))
            )
            macd = (fast_ema - slow_ema).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            macd_values.append(macd)

        # Current MACD line is the last value
        macd_line = macd_values[-1]

        # Signal line = 9 EMA of MACD line values (use available values if < 9)
        if len(macd_values) >= self.signal:
            signal_line = self.ema_calc_signal._calculate_ema(
                macd_values, self.signal,
                Decimal("2") / (Decimal(str(self.signal)) + Decimal("1")),
                prev_signal
            )
        else:
            # Not enough MACD values for full signal EMA, use SMA of available values
            signal_line = (sum(macd_values) / Decimal(str(len(macd_values)))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        # Histogram = MACD - Signal
        histogram = (macd_line - signal_line).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Check if MACD is positive
        positive = macd_line > Decimal("0")

        # Detect divergence and crosses
        divergence = None
        cross = None

        if prev_macd is not None and prev_signal is not None:
            was_positive = prev_macd > Decimal("0")
            is_positive = macd_line > Decimal("0")

            # Detect divergence (lines moving apart)
            prev_histogram = prev_macd - prev_signal
            if abs(histogram) > abs(prev_histogram):
                if is_positive:
                    divergence = "bullish"
                else:
                    divergence = "bearish"

            # Detect crosses
            was_above_signal = prev_macd > prev_signal
            is_above_signal = macd_line > signal_line

            if not was_above_signal and is_above_signal:
                cross = "bullish"
            elif was_above_signal and not is_above_signal:
                cross = "bearish"

        return MACDResult(
            symbol="UNKNOWN",
            macd_line=macd_line,
            signal_line=signal_line,
            histogram=histogram,
            positive=positive,
            divergence=divergence,
            cross=cross,
            timestamp=datetime.utcnow()
        )
