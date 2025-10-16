"""
ATR (Average True Range) calculator for volatility-based stop-loss calculation.

Implements Wilder's ATR formula:
1. True Range (TR) = max(high - low, |high - prev_close|, |low - prev_close|)
2. First ATR = average of first N true ranges
3. Subsequent ATRs = ((previous_ATR * (N-1)) + current_TR) / N

Pattern: src/trading_bot/risk_management/pullback_analyzer.py (service class structure)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_bot.market_data.data_models import PriceBar
from trading_bot.risk_management.exceptions import (
    ATRCalculationError,
    ATRValidationError,
    StaleDataError,
)
from trading_bot.risk_management.models import ATRStopData

logger = logging.getLogger(__name__)


class ATRCalculator:
    """
    Calculates Average True Range (ATR) for volatility-based stop-loss placement.

    ATR measures market volatility by decomposing the entire range of price
    movement for a given period. Uses Wilder's smoothing formula for consistency.

    Constants:
        DEFAULT_PERIOD: Wilder's standard 14-period lookback
        DEFAULT_MULTIPLIER: Standard 2.0x ATR for stop distance
        MIN_STOP_DISTANCE_PCT: Minimum stop distance (0.7%)
        MAX_STOP_DISTANCE_PCT: Maximum stop distance (10%)

    References:
        - Wilder, J. Wells (1978). "New Concepts in Technical Trading Systems"
        - ATR calculation: https://school.stockcharts.com/doku.php?id=technical_indicators:average_true_range_atr

    Example:
        calculator = ATRCalculator(period=14)
        atr_value = calculator.calculate(price_bars)  # Returns Decimal ATR
        atr_stop = calculator.calculate_atr_stop(
            entry_price=Decimal("250.00"),
            atr_value=atr_value,
            multiplier=2.0,
            position_type="long"
        )
    """

    # ATR formula constants (T025)
    DEFAULT_PERIOD = 14  # Wilder's standard period
    DEFAULT_MULTIPLIER = 2.0  # Standard stop distance multiplier
    MIN_STOP_DISTANCE_PCT = Decimal("0.7")  # Minimum stop distance
    MAX_STOP_DISTANCE_PCT = Decimal("10.0")  # Maximum stop distance

    def __init__(self, period: int = DEFAULT_PERIOD):
        """
        Initialize ATR calculator.

        Args:
            period: Lookback period for ATR calculation (default: 14, Wilder's standard)

        Raises:
            ValueError: If period <= 0
        """
        if period <= 0:
            raise ValueError(f"ATR period must be > 0, got {period}")

        self.period = period

    def calculate(self, price_bars: list[PriceBar]) -> Decimal:
        """
        Calculate ATR from price bars using Wilder's smoothing formula.

        Args:
            price_bars: List of PriceBar objects (oldest first, newest last)

        Returns:
            ATR value as Decimal (accurate to $0.01)

        Raises:
            ATRCalculationError: If insufficient data, invalid prices, or calculation fails

        Algorithm:
            1. Validate: Need at least (period + 1) bars for ATR calculation
            2. Calculate True Range for each bar:
               TR = max(high - low, |high - prev_close|, |low - prev_close|)
            3. First ATR = average of first 'period' TRs
            4. Subsequent ATRs = ((prev_ATR * (period-1)) + current_TR) / period
        """
        # Validation: Need at least (period + 1) bars
        if len(price_bars) < self.period:
            symbol = price_bars[0].symbol if price_bars else "UNKNOWN"
            raise ATRCalculationError(
                f"Insufficient data for {symbol}: {len(price_bars)} bars available, {self.period} required"
            )

        # Validate price bar integrity
        for i, bar in enumerate(price_bars):
            # Check for negative prices
            if bar.low < Decimal("0"):
                raise ATRCalculationError(
                    f"Invalid price data for {bar.symbol}: negative prices detected at bar {i} (low={bar.low})"
                )

        # Calculate True Range for each bar (starting from index 1, need prev_close)
        true_ranges: list[Decimal] = []

        for i in range(1, len(price_bars)):
            current_bar = price_bars[i]
            prev_bar = price_bars[i - 1]

            # Extract true range calculation to private method (T026)
            true_range = self._calculate_true_range(current_bar, prev_bar)
            true_ranges.append(true_range)

        # Need at least 'period' true ranges
        if len(true_ranges) < self.period:
            raise ATRCalculationError(
                f"Insufficient true ranges for {price_bars[0].symbol}: {len(true_ranges)} available, {self.period} required"
            )

        # Step 1: First ATR = average of first 'period' true ranges
        first_atr = sum(true_ranges[: self.period]) / Decimal(str(self.period))

        # Step 2: Subsequent ATRs use Wilder's smoothing
        # ATR = ((prev_ATR * (period-1)) + current_TR) / period
        current_atr = first_atr

        for i in range(self.period, len(true_ranges)):
            current_tr = true_ranges[i]
            current_atr = (
                (current_atr * Decimal(str(self.period - 1))) + current_tr
            ) / Decimal(str(self.period))

        # Validate ATR is positive
        if current_atr <= Decimal("0"):
            raise ATRCalculationError(
                f"Invalid ATR value for {price_bars[0].symbol}: {current_atr} (must be positive)"
            )

        # Round to 2 decimal places for $0.01 precision
        return current_atr.quantize(Decimal("0.01"))

    def _calculate_true_range(self, current_bar: PriceBar, prev_bar: PriceBar) -> Decimal:
        """
        Calculate True Range for a single bar (private helper method).

        True Range is the greatest of:
        1. Current high - current low
        2. |current high - previous close|
        3. |current low - previous close|

        This captures both intraday volatility and gaps between sessions.

        Args:
            current_bar: Current price bar
            prev_bar: Previous price bar (for close comparison)

        Returns:
            True Range as Decimal

        Formula:
            TR = max(H - L, |H - C_prev|, |L - C_prev|)

        Example:
            Current:  H=$252, L=$248, C=$250
            Previous: C=$245

            TR = max($252-$248, |$252-$245|, |$248-$245|)
               = max($4, $7, $3)
               = $7  (gap up from previous close captured)

        From: T026 - Extract true range calculation to improve testability
        """
        # Component 1: Intraday range (high - low)
        high_low = current_bar.high - current_bar.low

        # Component 2: Gap from previous close to current high
        high_prev_close = abs(current_bar.high - prev_bar.close)

        # Component 3: Gap from previous close to current low
        low_prev_close = abs(current_bar.low - prev_bar.close)

        # True Range is the maximum of the three components
        return max(high_low, high_prev_close, low_prev_close)

    @staticmethod
    def calculate_atr_stop(
        entry_price: Decimal,
        atr_value: Decimal,
        multiplier: float,
        position_type: str,
        atr_period: int = 14,
    ) -> ATRStopData:
        """
        Calculate stop-loss price using ATR multiplier.

        Args:
            entry_price: Position entry price
            atr_value: Current ATR value (from calculate() method)
            multiplier: ATR multiplier for stop distance (e.g., 2.0 = 2x ATR)
            position_type: "long" or "short"
            atr_period: ATR period used (for metadata)

        Returns:
            ATRStopData with stop price and ATR metadata

        Raises:
            ATRValidationError: If stop distance violates 0.7%-10% bounds

        Formula:
            Long:  stop_price = entry_price - (atr_value * multiplier)
            Short: stop_price = entry_price + (atr_value * multiplier)

        Example:
            entry_price = $250.00, atr_value = $5.00, multiplier = 2.0, type = "long"
            stop_price = $250.00 - ($5.00 * 2.0) = $240.00
        """
        if position_type not in ("long", "short"):
            raise ValueError(f"position_type must be 'long' or 'short', got '{position_type}'")

        # Calculate stop distance
        stop_distance = atr_value * Decimal(str(multiplier))

        # Calculate stop price
        if position_type == "long":
            stop_price = entry_price - stop_distance
        else:  # short
            stop_price = entry_price + stop_distance

        # Validate stop distance is within 0.7%-10% bounds
        stop_distance_pct = (abs(entry_price - stop_price) / entry_price) * Decimal("100")

        # Use class constants instead of local variables (T025)
        MIN_STOP_DISTANCE_PCT = ATRCalculator.MIN_STOP_DISTANCE_PCT
        MAX_STOP_DISTANCE_PCT = ATRCalculator.MAX_STOP_DISTANCE_PCT

        if stop_distance_pct < MIN_STOP_DISTANCE_PCT:
            raise ATRValidationError(
                f"Stop distance {stop_distance_pct:.2f}% is too tight (minimum: 0.7%)"
            )

        if stop_distance_pct > MAX_STOP_DISTANCE_PCT:
            raise ATRValidationError(
                f"Stop distance {stop_distance_pct:.2f}% exceeds maximum 10%"
            )

        # Return ATRStopData
        return ATRStopData(
            stop_price=stop_price.quantize(Decimal("0.01")),
            atr_value=atr_value,
            atr_multiplier=multiplier,
            atr_period=atr_period,
            source="atr",
            timestamp=datetime.now(UTC),
        )

    @staticmethod
    def validate_atr_stop(
        entry_price: Decimal,
        stop_price: Decimal,
        position_type: str,
    ) -> None:
        """
        Validate ATR-based stop price meets distance requirements.

        Args:
            entry_price: Position entry price
            stop_price: Proposed stop-loss price
            position_type: "long" or "short"

        Raises:
            ATRValidationError: If stop distance < 0.7% or > 10%

        Validation Rules:
            - Minimum distance: 0.7% (prevents stops too tight for volatility)
            - Maximum distance: 10% (prevents excessive risk per trade)
        """
        if position_type not in ("long", "short"):
            raise ValueError(f"position_type must be 'long' or 'short', got '{position_type}'")

        # Calculate stop distance percentage
        stop_distance_pct = (abs(entry_price - stop_price) / entry_price) * Decimal("100")

        # Use class constants (T025)
        MIN_STOP_DISTANCE_PCT = ATRCalculator.MIN_STOP_DISTANCE_PCT
        MAX_STOP_DISTANCE_PCT = ATRCalculator.MAX_STOP_DISTANCE_PCT

        if stop_distance_pct < MIN_STOP_DISTANCE_PCT:
            raise ATRValidationError(
                f"Stop distance {stop_distance_pct:.2f}% below 0.7% minimum"
            )

        if stop_distance_pct > MAX_STOP_DISTANCE_PCT:
            raise ATRValidationError(
                f"Stop distance {stop_distance_pct:.2f}% exceeds 10% maximum"
            )

    def validate_price_bars(
        self, price_bars: list[PriceBar], max_age_minutes: int = 15
    ) -> None:
        """
        Validate price bars are fresh and suitable for ATR calculation.

        Args:
            price_bars: List of PriceBar objects to validate
            max_age_minutes: Maximum age for latest bar (default: 15 minutes)

        Raises:
            StaleDataError: If latest price bar exceeds max_age_minutes threshold
            ATRCalculationError: If price bars are invalid

        Validation:
            - Latest bar timestamp within max_age_minutes of current time
            - Timestamps are sequential (oldest to newest)
            - high >= low for all bars
        """
        if not price_bars:
            raise ATRCalculationError("Empty price_bars list")

        # Check latest bar age
        latest_bar = price_bars[-1]
        current_time = datetime.now(UTC)
        bar_age = current_time - latest_bar.timestamp

        if bar_age > timedelta(minutes=max_age_minutes):
            age_minutes = bar_age.total_seconds() / 60
            raise StaleDataError(
                f"Stale data for {latest_bar.symbol}: latest bar is {age_minutes:.1f} minutes old (threshold: {max_age_minutes} minutes)"
            )

        # Validate sequential timestamps
        for i in range(1, len(price_bars)):
            if price_bars[i].timestamp <= price_bars[i - 1].timestamp:
                raise ATRCalculationError(
                    f"Price bars for {price_bars[i].symbol} are not in chronological order at index {i}"
                )
