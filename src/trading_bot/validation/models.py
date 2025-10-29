"""
Multi-Timeframe Validation Models

Immutable dataclasses for timeframe validation results and indicators.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class ValidationStatus(Enum):
    """Status of multi-timeframe validation decision.

    PASS: All timeframe checks passed, trade allowed
    BLOCK: One or more timeframes failed, trade blocked
    DEGRADED: Data unavailable, validation skipped with warning
    """
    PASS = "PASS"
    BLOCK = "BLOCK"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class TimeframeIndicators:
    """Indicator values calculated for a specific timeframe.

    Immutable dataclass capturing technical indicators at a point in time.

    Args:
        timeframe: Timeframe identifier (e.g., "DAILY", "4H", "5MIN")
        price: Current price of the asset
        ema_20: 20-period Exponential Moving Average
        macd_line: MACD line value (12-period EMA - 26-period EMA)
        macd_positive: True if MACD line > 0
        price_above_ema: True if current price > 20 EMA
        bar_count: Number of bars used for calculation
        timestamp: When indicators were calculated

    Example:
        >>> indicators = TimeframeIndicators(
        ...     timeframe="DAILY",
        ...     price=Decimal("150.00"),
        ...     ema_20=Decimal("148.50"),
        ...     macd_line=Decimal("0.52"),
        ...     macd_positive=True,
        ...     price_above_ema=True,
        ...     bar_count=60,
        ...     timestamp=datetime.now()
        ... )
    """
    timeframe: str
    price: Decimal
    ema_20: Decimal
    macd_line: Decimal
    macd_positive: bool
    price_above_ema: bool
    bar_count: int
    timestamp: datetime


@dataclass(frozen=True)
class TimeframeValidationResult:
    """Result of multi-timeframe validation check.

    Immutable dataclass containing validation decision and supporting data.

    Args:
        status: Validation decision (PASS/BLOCK/DEGRADED)
        aggregate_score: Combined weighted score [0.0, 1.0]
        daily_score: Daily timeframe score [0.0, 1.0]
        daily_indicators: Indicator values from daily timeframe
        symbol: Ticker symbol validated
        timestamp: When validation was performed
        h4_score: 4-hour timeframe score (optional)
        h4_indicators: Indicator values from 4H timeframe (optional)
        reasons: List of human-readable validation reasons
        validation_duration_ms: How long validation took

    Raises:
        ValueError: If aggregate_score not in range [0.0, 1.0]

    Example:
        >>> result = TimeframeValidationResult(
        ...     status=ValidationStatus.PASS,
        ...     aggregate_score=Decimal("0.8"),
        ...     daily_score=Decimal("1.0"),
        ...     daily_indicators=indicators,
        ...     symbol="AAPL",
        ...     timestamp=datetime.now(),
        ...     reasons=["Daily MACD positive", "Price above daily 20 EMA"]
        ... )
    """
    status: ValidationStatus
    aggregate_score: Decimal
    daily_score: Decimal
    daily_indicators: TimeframeIndicators
    symbol: str
    timestamp: datetime
    h4_score: Optional[Decimal] = None
    h4_indicators: Optional[TimeframeIndicators] = None
    reasons: List[str] = field(default_factory=list)
    validation_duration_ms: Optional[int] = None

    def __post_init__(self):
        """Validate aggregate_score is in range [0.0, 1.0]."""
        if not (Decimal("0.0") <= self.aggregate_score <= Decimal("1.0")):
            raise ValueError(
                f"aggregate_score must be in range [0.0, 1.0], got {self.aggregate_score}"
            )
