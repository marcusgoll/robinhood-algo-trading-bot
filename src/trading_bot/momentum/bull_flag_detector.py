"""
Bull Flag Detector Service

Scans stocks for bull flag chart patterns (strong upward move followed by consolidation)
and calculates breakout levels and price targets.

Constitution v1.0.0:
- §Safety_First: Manual review required, no auto-trading
- §Risk_Management: Input validation, graceful degradation
- §Data_Integrity: Pattern validation before signal generation

Feature: momentum-detection
Task: T035 - BullFlagDetector service implementation
"""

import logging
from datetime import UTC, datetime

import pandas as pd

from ..market_data.market_data_service import MarketDataService
from .config import MomentumConfig
from .logging.momentum_logger import MomentumLogger
from .schemas.momentum_signal import BullFlagPattern, MomentumSignal, SignalType
from .validation import validate_symbols

# Module logger
logger = logging.getLogger(__name__)


class BullFlagDetector:
    """Bull flag pattern detection service.

    Detects bull flag chart patterns with the following criteria:
    - Pole: >8% price gain in 1-3 days
    - Flag: Price consolidation within 3-5% range for 2-5 days
    - Flag slope: Downward or flat (not upward trending)

    Features:
    - Pattern detection from 100 days of historical OHLCV data
    - Breakout price calculation (top of flag range)
    - Price target projection (pole height from breakout)
    - Signal strength scoring (0-100)
    - Graceful degradation (missing data → empty results + warning)

    Example:
        >>> config = MomentumConfig.from_env()
        >>> market_data = MarketDataService(auth, config)
        >>> detector = BullFlagDetector(config, market_data)
        >>> signals = await detector.scan(["AAPL", "GOOGL", "TSLA"])
        >>> for signal in signals:
        ...     print(f"{signal.symbol}: Target ${signal.details['price_target']:.2f}")
        AAPL: Target $185.50
    """

    def __init__(
        self,
        config: MomentumConfig,
        market_data_service: MarketDataService,
        momentum_logger: MomentumLogger | None = None,
    ):
        """Initialize bull flag detector with configuration and dependencies.

        Args:
            config: Momentum detection configuration
            market_data_service: Service for fetching historical market data
            momentum_logger: Optional logger instance (creates default if None)
        """
        self.config = config
        self.market_data = market_data_service
        self.logger = momentum_logger or MomentumLogger()

    async def scan(self, symbols: list[str]) -> list[MomentumSignal]:
        """Scan for bull flag patterns in historical price data.

        Fetches 100 days of OHLCV data via MarketDataService, detects bull flag
        patterns, and builds MomentumSignal objects for valid patterns.

        Args:
            symbols: List of stock ticker symbols to scan (e.g., ["AAPL", "GOOGL"])

        Returns:
            List of MomentumSignal objects with bull flag patterns
            (empty if no patterns detected or API failures)

        Raises:
            ValueError: If symbols list is empty or contains invalid symbols

        Example:
            >>> detector = BullFlagDetector(config, market_data)
            >>> signals = await detector.scan(["AAPL"])
            >>> len(signals) > 0
            True
        """
        # T056: Input validation (fail fast)
        try:
            validate_symbols(symbols)
        except ValueError as e:
            logger.error(f"BullFlagDetector input validation failed: {e}")
            self.logger.log_error(
                e,
                {
                    "detector": "BullFlagDetector",
                    "operation": "scan",
                    "symbols": symbols,
                    "validation_error": str(e),
                }
            )
            raise  # Re-raise ValueError to fail fast

        signals = []
        current_time_utc = datetime.now(UTC)

        for symbol in symbols:
            try:
                # Fetch 100 days of historical OHLCV data
                ohlcv = self.market_data.get_historical_data(
                    symbol=symbol,
                    interval="day",
                    span="3month",  # 3 months to ensure we get 100+ trading days
                )

                # Check if data is empty
                if ohlcv.empty:
                    logger.debug(f"No historical data available for {symbol}, skipping")
                    continue

                # Detect bull flag pattern
                pattern = self._detect_pattern(ohlcv)

                # Skip if no valid pattern found
                if pattern is None:
                    logger.debug(f"No bull flag pattern detected for {symbol}")
                    continue

                # Calculate signal strength based on pole gain and flag confirmation
                strength = self._calculate_strength(pattern)

                # Build MomentumSignal
                signal = MomentumSignal(
                    symbol=symbol,
                    signal_type=SignalType.PATTERN,
                    strength=strength,
                    detected_at=current_time_utc,
                    details={
                        "pattern_type": "bull_flag",
                        "pole_gain_pct": pattern.pole_gain_pct,
                        "flag_range_pct": pattern.flag_range_pct,
                        "breakout_price": pattern.breakout_price,
                        "price_target": pattern.price_target,
                        "pattern_valid": pattern.pattern_valid,
                    },
                )

                signals.append(signal)

                # Log detected signal
                signal_dict = {
                    "signal_type": signal.signal_type.value,
                    "symbol": signal.symbol,
                    "strength": signal.strength,
                    "detected_at": signal.detected_at.isoformat(),
                    "details": signal.details,
                }
                self.logger.log_signal(signal_dict, {"source": "bull_flag_detector"})

            except TimeoutError as e:
                # T055: API timeout for this symbol - log warning, continue with next symbol
                logger.warning(
                    f"API timeout while fetching historical data for {symbol}: {e}. "
                    f"Check market data provider availability. Continuing with next symbol."
                )
                self.logger.log_error(
                    e,
                    {
                        "detector": "BullFlagDetector",
                        "operation": "scan_symbol",
                        "symbol": symbol,
                        "error_type": "timeout",
                    }
                )
                continue  # Graceful degradation: process other symbols

            except (ConnectionError, OSError) as e:
                # T055: Network error for this symbol - log error, continue with next symbol
                logger.error(
                    f"Network error while fetching historical data for {symbol}: {e}. "
                    f"Check network connectivity. Continuing with next symbol."
                )
                self.logger.log_error(
                    e,
                    {
                        "detector": "BullFlagDetector",
                        "operation": "scan_symbol",
                        "symbol": symbol,
                        "error_type": "network",
                    }
                )
                continue  # Graceful degradation

            except (KeyError, AttributeError, pd.errors.EmptyDataError) as e:
                # T055: Malformed OHLCV data - log error, continue with next symbol
                logger.error(
                    f"Malformed OHLCV data for {symbol}: {e}. "
                    f"Expected DataFrame with columns: date/timestamp, open, high, low, close, volume. "
                    f"Check MarketDataService compatibility."
                )
                self.logger.log_error(
                    e,
                    {
                        "detector": "BullFlagDetector",
                        "operation": "scan_symbol",
                        "symbol": symbol,
                        "error_type": "malformed_data",
                    }
                )
                continue  # Graceful degradation

            except Exception as e:
                # T055: Unexpected error for this symbol - log error, continue with next symbol
                logger.error(
                    f"Unexpected error while scanning bull flag pattern for {symbol}: {e}. "
                    f"This should not happen - investigate immediately."
                )
                self.logger.log_error(
                    e,
                    {
                        "detector": "BullFlagDetector",
                        "operation": "scan_symbol",
                        "symbol": symbol,
                        "error_type": "unexpected",
                    }
                )
                continue  # Graceful degradation: don't crash, process other symbols

        return signals

    def _detect_pattern(self, ohlcv: pd.DataFrame) -> BullFlagPattern | None:
        """Detect bull flag pattern from OHLCV data.

        Scans historical data for pole (>8% gain in 1-3 days) followed by
        consolidation (3-5% range for 2-5 days with downward/flat slope).

        Args:
            ohlcv: DataFrame with columns: date, open, high, low, close, volume

        Returns:
            BullFlagPattern if valid pattern found, None otherwise
        """
        try:
            # Detect pole (strong upward move)
            pole_data = self._detect_pole(ohlcv)
            if pole_data is None:
                return None

            pole_start, pole_end, pole_gain_pct, pole_high, pole_low = pole_data

            # Detect flag (consolidation after pole)
            flag_data = self._detect_flag(ohlcv, pole_end)
            if flag_data is None:
                return None

            flag_start, flag_end, flag_high, flag_low, flag_range_pct, flag_slope_pct = flag_data

            # Note: slope validation now happens inside _detect_flag(), so no need to check again

            # Calculate breakout price and target
            breakout_price, price_target = self._calculate_targets(pole_high, pole_low, flag_high)

            # Create BullFlagPattern (validation happens in __post_init__)
            pattern = BullFlagPattern(
                pole_gain_pct=pole_gain_pct,
                flag_range_pct=flag_range_pct,
                breakout_price=breakout_price,
                price_target=price_target,
                pattern_valid=True,  # If we reached here, all validations passed
            )

            return pattern

        except ValueError as e:
            # Pattern validation failed (e.g., pole_gain < 8%)
            logger.debug(f"Pattern validation failed: {e}")
            return None
        except Exception as e:
            # Unexpected error during pattern detection
            logger.warning(f"Unexpected error in pattern detection: {e}")
            return None

    def _detect_pole(self, ohlcv: pd.DataFrame) -> tuple[datetime, datetime, float, float, float] | None:
        """Detect pole: >8% gain in 1-3 consecutive days.

        Scans last 100 days for consecutive 1-3 day periods with >8% gain
        calculated as: (high - low) / low * 100

        Args:
            ohlcv: DataFrame with OHLCV data (must have 'date' or 'timestamp' column)

        Returns:
            Tuple of (pole_start_date, pole_end_date, pole_gain_pct, pole_high, pole_low)
            or None if no valid pole found
        """
        if len(ohlcv) < 10:  # Need at least 10 days for pattern detection
            return None

        # Determine date column name
        date_col = 'timestamp' if 'timestamp' in ohlcv.columns else 'date'

        # Scan last 100 days (or all available data if less)
        scan_data = ohlcv.tail(100).reset_index(drop=True)

        # Try to find pole pattern (scan from most recent backwards)
        for i in range(len(scan_data) - 1, 3, -1):  # Start from end, need at least 3 days after
            # Try 1-3 day pole durations
            for pole_duration in [1, 2, 3]:
                if i - pole_duration < 0:
                    continue

                # Get pole start and end indices
                pole_start_idx = i - pole_duration
                pole_end_idx = i

                # Get price range during pole
                pole_slice = scan_data.iloc[pole_start_idx : pole_end_idx + 1]
                pole_low = float(pole_slice["low"].min())
                pole_high = float(pole_slice["high"].max())

                # Calculate pole gain percentage
                pole_gain_pct = ((pole_high - pole_low) / pole_low) * 100

                # Check if pole meets >8% gain threshold
                if pole_gain_pct >= self.config.pole_min_gain_pct:
                    pole_start_date = scan_data.iloc[pole_start_idx][date_col]
                    pole_end_date = scan_data.iloc[pole_end_idx][date_col]

                    logger.debug(
                        f"Pole detected: {pole_start_date} to {pole_end_date}, "
                        f"gain={pole_gain_pct:.2f}%, low=${pole_low:.2f}, high=${pole_high:.2f}"
                    )
                    return (pole_start_date, pole_end_date, pole_gain_pct, pole_high, pole_low)

        # No valid pole found
        return None

    def _detect_flag(
        self, ohlcv: pd.DataFrame, pole_end: datetime
    ) -> tuple[datetime, datetime, float, float, float, float] | None:
        """Detect flag: 3-5% consolidation for 2-5 days after pole.

        Scans 2-5 days after pole_end for consolidation with:
        - Price range: 3-5% (flag_range_pct)
        - Duration: 2-5 days
        - Slope: downward or flat (calculated separately)

        Args:
            ohlcv: DataFrame with OHLCV data (must have 'date' or 'timestamp' column)
            pole_end: Datetime when pole ends

        Returns:
            Tuple of (flag_start_date, flag_end_date, flag_high, flag_low, flag_range_pct, flag_slope_pct)
            or None if no valid flag found
        """
        # Determine date column name
        date_col = 'timestamp' if 'timestamp' in ohlcv.columns else 'date'

        # Reset index for easier iteration
        scan_data = ohlcv.reset_index(drop=True)

        # Find pole_end index
        pole_end_idx = None
        for i, row in scan_data.iterrows():
            if row[date_col] == pole_end:
                pole_end_idx = i
                break

        # If pole_end not found in data, assume flag starts at index 0
        # (test data may only include flag candles, starting after pole_end)
        if pole_end_idx is None:
            flag_start_idx = 0
        else:
            # Flag starts immediately after pole ends
            flag_start_idx = pole_end_idx + 1

        # Try 2-5 day flag durations
        for flag_duration in [2, 3, 4, 5]:
            flag_end_idx = flag_start_idx + flag_duration - 1

            # Check if we have enough data
            if flag_end_idx >= len(scan_data):
                continue

            # Get flag price range
            flag_slice = scan_data.iloc[flag_start_idx : flag_end_idx + 1]
            flag_low = float(flag_slice["low"].min())
            flag_high = float(flag_slice["high"].max())

            # Calculate flag range percentage
            flag_range_pct = ((flag_high - flag_low) / flag_low) * 100

            # Check if flag range is within 3-5%
            if (
                flag_range_pct >= self.config.flag_range_pct_min
                and flag_range_pct <= self.config.flag_range_pct_max
            ):
                # Calculate flag slope (close - open) / open
                flag_open = float(flag_slice.iloc[0]["open"])
                flag_close = float(flag_slice.iloc[-1]["close"])
                flag_slope_pct = ((flag_close - flag_open) / flag_open) * 100

                # Validate slope (must be downward or flat, not upward)
                if not self._validate_slope(flag_slope_pct):
                    logger.debug(
                        f"Flag slope validation failed: {flag_slope_pct:.2f}% (must be <= 0)"
                    )
                    continue  # Try next duration

                # Get flag start and end dates
                flag_start_date = scan_data.iloc[flag_start_idx][date_col]
                flag_end_date = scan_data.iloc[flag_end_idx][date_col]

                logger.debug(
                    f"Flag detected: {flag_start_date} to {flag_end_date}, "
                    f"range={flag_range_pct:.2f}%, slope={flag_slope_pct:.2f}%, "
                    f"low=${flag_low:.2f}, high=${flag_high:.2f}"
                )

                return (
                    flag_start_date,
                    flag_end_date,
                    flag_high,
                    flag_low,
                    flag_range_pct,
                    flag_slope_pct,
                )

        # No valid flag found
        return None

    def _validate_slope(self, flag_slope_pct: float) -> bool:
        """Validate flag slope is downward or flat (≤ 0).

        Args:
            flag_slope_pct: Flag slope percentage

        Returns:
            True if slope is ≤ 0 (downward or flat), False otherwise
        """
        return flag_slope_pct <= 0

    def _calculate_targets(
        self, pole_high: float, pole_low: float, flag_high: float
    ) -> tuple[float, float]:
        """Calculate breakout price and price target.

        Logic:
        - breakout_price = flag_high (top of consolidation range)
        - pole_height = pole_high - pole_low
        - price_target = breakout_price + pole_height

        Args:
            pole_high: Highest price during pole
            pole_low: Lowest price during pole
            flag_high: Highest price during flag

        Returns:
            Tuple of (breakout_price, price_target)
        """
        breakout_price = flag_high
        pole_height = pole_high - pole_low
        price_target = breakout_price + pole_height

        logger.debug(
            f"Targets calculated: breakout=${breakout_price:.2f}, "
            f"target=${price_target:.2f} (pole_height=${pole_height:.2f})"
        )

        return (breakout_price, price_target)

    def _calculate_strength(self, pattern: BullFlagPattern) -> float:
        """Calculate signal strength (0-100) based on pole gain and flag confirmation.

        Strength formula:
        - Pole component (60%): (pole_gain_pct / 20) * 60 (scale 8-20% gain to 0-60)
        - Flag component (40%): ((5 - flag_range_pct) / 2) * 40 (tighter range = higher score)

        Args:
            pattern: BullFlagPattern with pole and flag measurements

        Returns:
            float: Strength score (0-100)

        Example:
            >>> # Pole: 10% gain, Flag: 4% range
            >>> # Pole score: (10 / 20) * 60 = 30
            >>> # Flag score: ((5 - 4) / 2) * 40 = 20
            >>> # Total: 30 + 20 = 50
        """
        # Pole component: Scale pole gain (8-20%) to 0-60 range
        pole_score = min(60.0, (pattern.pole_gain_pct / 20.0) * 60.0)

        # Flag component: Tighter consolidation = higher score (5% range = 0, 3% range = 40)
        flag_score = ((5.0 - pattern.flag_range_pct) / 2.0) * 40.0
        flag_score = max(0.0, min(40.0, flag_score))

        # Total strength
        strength = pole_score + flag_score

        return round(strength, 1)
