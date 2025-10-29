"""
Multi-Timeframe Validator Service

Orchestrates cross-timeframe trend validation for bull flag pattern detection.
Composition pattern extending BullFlagDetector with daily/4H trend confirmation.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import pandas as pd

from trading_bot.error_handling.policies import DEFAULT_POLICY
from trading_bot.error_handling.retry import with_retry
from trading_bot.indicators.service import TechnicalIndicatorsService
from trading_bot.market_data.market_data_service import MarketDataService

from .config import MultiTimeframeConfig
from .models import (
    TimeframeIndicators,
    TimeframeValidationResult,
    ValidationStatus,
)


class MultiTimeframeValidator:
    """
    Validates trade entries against higher-timeframe trends.

    Composition pattern: Orchestrates MarketDataService + TechnicalIndicatorsService
    without modifying existing bull flag detection logic.

    Example:
        >>> validator = MultiTimeframeValidator(market_data_service)
        >>> result = validator.validate("AAPL", Decimal("150.00"), bars_5min)
        >>> if result.status == ValidationStatus.BLOCK:
        ...     print(f"Trade blocked: {result.reasons}")
    """

    def __init__(
        self,
        market_data_service: MarketDataService,
        config: Optional[MultiTimeframeConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize multi-timeframe validator.

        Args:
            market_data_service: Service for fetching historical data
            config: Configuration (uses defaults if not provided)
            logger: Custom logger (creates one if not provided)
        """
        self.market_data_service = market_data_service
        self.config = config if config is not None else MultiTimeframeConfig.from_env()
        self.logger = logger if logger is not None else logging.getLogger(__name__)

    @with_retry(policy=DEFAULT_POLICY)
    def _fetch_daily_data(self, symbol: str) -> pd.DataFrame:
        """
        Fetch daily historical data with retry logic.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")

        Returns:
            DataFrame with at least 30 daily bars (required for MACD calculation)

        Raises:
            ValueError: If insufficient bars returned (<30)
            RateLimitError: After 3 retries on HTTP 429
        """
        # Fetch 3 months of daily data (typically 60+ bars)
        df = self.market_data_service.get_historical_data(
            symbol=symbol,
            interval="day",
            span="3month"
        )

        # Validate minimum bar count for MACD (26-period EMA requires 26 bars minimum)
        if len(df) < 30:
            raise ValueError(
                f"Insufficient daily data for {symbol}: "
                f"got {len(df)} bars, need at least 30"
            )

        self.logger.debug(
            f"Fetched {len(df)} daily bars for {symbol}"
        )

        return df

    def _calculate_daily_indicators(
        self,
        bars: pd.DataFrame,
        current_price: Decimal
    ) -> TimeframeIndicators:
        """
        Calculate technical indicators for daily timeframe.

        Creates separate TechnicalIndicatorsService instance to avoid state collision
        with other timeframes.

        Args:
            bars: DataFrame with OHLCV data (minimum 30 bars)
            current_price: Current price of the asset

        Returns:
            TimeframeIndicators with calculated MACD and EMA values

        Raises:
            InsufficientDataError: If insufficient bars for calculation
        """
        # Create separate service instance per timeframe (prevents state collision)
        indicators_service = TechnicalIndicatorsService()

        # Convert DataFrame to list of dicts for indicators service
        bars_list = bars.to_dict('records')

        # Calculate MACD
        macd_result = indicators_service.get_macd(bars_list)

        # Calculate EMA (20-period)
        ema_result = indicators_service.get_emas(bars_list)

        # Build TimeframeIndicators dataclass
        return TimeframeIndicators(
            timeframe="DAILY",
            price=current_price,
            ema_20=ema_result.ema_20,
            macd_line=macd_result.macd_line,
            macd_positive=macd_result.positive,
            price_above_ema=current_price > ema_result.ema_20,
            bar_count=len(bars),
            timestamp=datetime.now()
        )

    def _score_timeframe(self, indicators: TimeframeIndicators) -> Decimal:
        """
        Calculate timeframe score based on indicator signals.

        Scoring logic:
        - MACD > 0: +0.5 points
        - Price > EMA_20: +0.5 points
        - Total range: [0.0, 1.0]

        Args:
            indicators: TimeframeIndicators with calculated values

        Returns:
            Decimal score in range [0.0, 1.0]
        """
        score = Decimal("0.0")

        # MACD positive contributes 0.5
        if indicators.macd_positive:
            score += Decimal("0.5")

        # Price above EMA contributes 0.5
        if indicators.price_above_ema:
            score += Decimal("0.5")

        return score

    def validate(
        self,
        symbol: str,
        current_price: Decimal,
        bars_5min: Optional[list] = None
    ) -> TimeframeValidationResult:
        """
        Validate trade entry against daily timeframe trends (MVP version).

        Daily-only validation (4H validation deferred to Phase 5 - US3).

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            current_price: Current price of the asset
            bars_5min: 5-minute bars (unused in MVP, kept for future compatibility)

        Returns:
            TimeframeValidationResult with validation decision

        Raises:
            ValueError: If invalid inputs (empty symbol, negative price)
        """
        start_time = datetime.now()

        # Input validation
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")
        if current_price <= 0:
            raise ValueError(f"Current price must be positive, got {current_price}")

        try:
            # Fetch daily data
            daily_df = self._fetch_daily_data(symbol)

            # Calculate daily indicators
            daily_indicators = self._calculate_daily_indicators(daily_df, current_price)

            # Compute daily score
            daily_score = self._score_timeframe(daily_indicators)

            # Determine validation status (daily-only MVP)
            # PASS if daily_score >= threshold (default 0.5)
            status = (
                ValidationStatus.PASS
                if daily_score >= self.config.aggregate_threshold
                else ValidationStatus.BLOCK
            )

            # Build human-readable reasons
            reasons = []
            if not daily_indicators.macd_positive:
                reasons.append("Daily MACD negative")
            if not daily_indicators.price_above_ema:
                reasons.append("Price below daily 20 EMA")

            if status == ValidationStatus.PASS:
                reasons.append("Daily timeframe validates bullish")

            # Calculate validation duration
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Return result (MVP: aggregate_score = daily_score only)
            return TimeframeValidationResult(
                status=status,
                aggregate_score=daily_score,
                daily_score=daily_score,
                daily_indicators=daily_indicators,
                symbol=symbol,
                timestamp=end_time,
                reasons=reasons,
                validation_duration_ms=duration_ms
            )

        except Exception as e:
            # Log error but don't raise (graceful degradation handled in Phase 6 - US4)
            self.logger.error(
                f"Multi-timeframe validation failed for {symbol}: {e}"
            )
            raise
