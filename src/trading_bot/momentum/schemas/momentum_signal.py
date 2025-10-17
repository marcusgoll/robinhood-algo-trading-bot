"""
Momentum Signal Data Models

Dataclasses for momentum detection: SignalType, CatalystType, MomentumSignal,
CatalystEvent, PreMarketMover, BullFlagPattern

All dataclasses include __post_init__ validation for data integrity.
Follows patterns from src/trading_bot/market_data/data_models.py
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """
    Enumeration of momentum signal types.

    Values:
        CATALYST: News-driven catalyst event (earnings, FDA, merger, etc.)
        PREMARKET: Pre-market price and volume movement
        PATTERN: Technical analysis pattern (bull flag)
        COMPOSITE: Aggregated signal from multiple sources
    """

    CATALYST = "catalyst"
    PREMARKET = "premarket"
    PATTERN = "pattern"
    COMPOSITE = "composite"


class CatalystType(str, Enum):
    """
    Enumeration of catalyst event types.

    Values:
        EARNINGS: Earnings report or guidance
        FDA: FDA approval or drug trial results
        MERGER: Merger, acquisition, or corporate action
        PRODUCT: Product launch or announcement
        ANALYST: Analyst rating change or upgrade/downgrade
    """

    EARNINGS = "earnings"
    FDA = "fda"
    MERGER = "merger"
    PRODUCT = "product"
    ANALYST = "analyst"


@dataclass(frozen=True)
class MomentumSignal:
    """
    Immutable momentum signal representing a detected trading opportunity.

    Attributes:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA') - must be 1-5 uppercase letters
        signal_type: Type of signal (CATALYST, PREMARKET, PATTERN, COMPOSITE)
        strength: Signal quality score (0-100, higher is stronger)
        detected_at: When signal was detected (UTC timezone)
        details: Type-specific metadata (e.g., headline, price change, pattern metrics)

    Raises:
        ValueError: If validation fails (strength out of range, invalid symbol format)
    """

    symbol: str
    signal_type: SignalType
    strength: float
    detected_at: datetime
    details: dict

    def __post_init__(self) -> None:
        """Validate momentum signal after initialization."""
        # Validate strength range (0-100)
        if not (0 <= self.strength <= 100):
            raise ValueError(
                f"Invalid MomentumSignal for {self.symbol}: strength ({self.strength}) "
                f"must be between 0 and 100"
            )

        # Validate symbol format: 1-5 uppercase letters only
        if not re.match(r"^[A-Z]{1,5}$", self.symbol):
            raise ValueError(
                f"Invalid MomentumSignal: symbol ({self.symbol}) "
                f"must be 1-5 uppercase characters (A-Z only)"
            )


@dataclass(frozen=True)
class CatalystEvent:
    """
    Immutable catalyst event from news sources.

    Attributes:
        headline: News headline text
        catalyst_type: Type of catalyst (EARNINGS, FDA, MERGER, PRODUCT, ANALYST)
        published_at: When news was published (UTC timezone)
        source: News source name (e.g., 'Alpaca News', 'Finnhub')

    Raises:
        ValueError: If published_at is not a datetime object
    """

    headline: str
    catalyst_type: CatalystType
    published_at: datetime
    source: str

    def __post_init__(self) -> None:
        """Validate catalyst event after initialization."""
        # Validate published_at is a datetime object
        if not isinstance(self.published_at, datetime):
            raise ValueError(
                f"Invalid CatalystEvent: published_at must be a datetime object, "
                f"got {type(self.published_at).__name__}"
            )


@dataclass(frozen=True)
class PreMarketMover:
    """
    Immutable pre-market price and volume movement data.

    Attributes:
        change_pct: Percentage change from previous close (can be negative)
        volume_ratio: Current volume / 10-day average volume (must be positive)

    Raises:
        ValueError: If volume_ratio is not positive
    """

    change_pct: float
    volume_ratio: float

    def __post_init__(self) -> None:
        """Validate pre-market mover after initialization."""
        # Validate volume_ratio is positive (must be > 0)
        if self.volume_ratio <= 0:
            raise ValueError(
                f"Invalid PreMarketMover: volume_ratio ({self.volume_ratio}) "
                f"must be positive (> 0)"
            )


@dataclass(frozen=True)
class BullFlagPattern:
    """
    Immutable bull flag pattern technical analysis data.

    Attributes:
        pole_gain_pct: Percentage gain during pole formation (must be >= 8%)
        flag_range_pct: Price range during consolidation (must be 3-5%)
        breakout_price: Price level for breakout confirmation (must be positive)
        price_target: Projected price target if breakout occurs (must be >= breakout_price)
        pattern_valid: Whether pattern meets all validation criteria

    Raises:
        ValueError: If pattern measurements are outside valid ranges
    """

    pole_gain_pct: float
    flag_range_pct: float
    breakout_price: float
    price_target: float
    pattern_valid: bool

    def __post_init__(self) -> None:
        """Validate bull flag pattern after initialization."""
        # Validate pole_gain_pct >= 8% (from spec FR-006)
        if self.pole_gain_pct < 8.0:
            raise ValueError(
                f"Invalid BullFlagPattern: pole_gain_pct ({self.pole_gain_pct}) "
                f"must be >= 8.0%"
            )

        # Validate flag_range_pct between 3-5% (from spec FR-006)
        if not (3.0 <= self.flag_range_pct <= 5.0):
            raise ValueError(
                f"Invalid BullFlagPattern: flag_range_pct ({self.flag_range_pct}) "
                f"must be between 3.0 and 5.0%"
            )

        # Validate breakout_price is positive
        if self.breakout_price <= 0:
            raise ValueError(
                f"Invalid BullFlagPattern: breakout_price ({self.breakout_price}) "
                f"must be positive (> 0)"
            )

        # Validate price_target is positive
        if self.price_target <= 0:
            raise ValueError(
                f"Invalid BullFlagPattern: price_target ({self.price_target}) "
                f"must be positive (> 0)"
            )

        # Validate price_target >= breakout_price
        if self.price_target < self.breakout_price:
            raise ValueError(
                f"Invalid BullFlagPattern: price_target ({self.price_target}) "
                f"must be >= breakout_price ({self.breakout_price})"
            )
