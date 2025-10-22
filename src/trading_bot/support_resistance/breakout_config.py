"""
Breakout Detection Configuration

Configuration dataclass for customizing breakout detection thresholds and parameters.
Supports environment variable loading for production deployments.

Example:
    >>> from decimal import Decimal
    >>> config = BreakoutConfig(
    ...     price_threshold_pct=Decimal("1.0"),
    ...     volume_threshold=Decimal("1.3"),
    ...     validation_bars=5,
    ...     strength_bonus=Decimal("2.0")
    ... )
"""

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BreakoutConfig:
    """
    Configuration for breakout detection thresholds and parameters.

    Immutable configuration object with sensible defaults based on spec.md requirements.
    All threshold values use Decimal for precision.

    Attributes:
        price_threshold_pct: Minimum price move percentage to trigger breakout (default 1.0%)
        volume_threshold: Minimum volume ratio vs 20-bar average (default 1.3x)
        validation_bars: Number of bars to monitor for whipsaw validation (default 5)
        strength_bonus: Strength score bonus for volume-confirmed breakouts (default +2.0)

    Example:
        >>> config = BreakoutConfig()
        >>> config.price_threshold_pct
        Decimal('1.0')
    """

    price_threshold_pct: Decimal = Decimal("1.0")
    volume_threshold: Decimal = Decimal("1.3")
    validation_bars: int = 5
    strength_bonus: Decimal = Decimal("2.0")

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.price_threshold_pct <= 0:
            raise ValueError(
                f"price_threshold_pct must be > 0, got {self.price_threshold_pct}"
            )
        if self.volume_threshold <= 0:
            raise ValueError(
                f"volume_threshold must be > 0, got {self.volume_threshold}"
            )
        if self.validation_bars <= 0:
            raise ValueError(
                f"validation_bars must be > 0, got {self.validation_bars}"
            )
        if self.strength_bonus < 0:
            raise ValueError(
                f"strength_bonus must be >= 0, got {self.strength_bonus}"
            )

        # Reasonableness checks
        if self.price_threshold_pct > 10:
            raise ValueError(
                f"price_threshold_pct too high (>{10}%), got {self.price_threshold_pct}"
            )
        if self.volume_threshold > 5:
            raise ValueError(
                f"volume_threshold too high (>5x), got {self.volume_threshold}"
            )
        if self.validation_bars > 20:
            raise ValueError(
                f"validation_bars too high (>20), got {self.validation_bars}"
            )

    @classmethod
    def from_env(cls) -> "BreakoutConfig":
        """
        Load configuration from environment variables.

        Environment Variables:
            BREAKOUT_PRICE_THRESHOLD_PCT: Price threshold percentage (default 1.0)
            BREAKOUT_VOLUME_THRESHOLD: Volume threshold ratio (default 1.3)
            BREAKOUT_VALIDATION_BARS: Validation bar count (default 5)
            BREAKOUT_STRENGTH_BONUS: Strength bonus for confirmed breakouts (default 2.0)

        Returns:
            BreakoutConfig instance with values from env or defaults

        Example:
            >>> os.environ["BREAKOUT_PRICE_THRESHOLD_PCT"] = "1.5"
            >>> config = BreakoutConfig.from_env()
            >>> config.price_threshold_pct
            Decimal('1.5')
        """
        return cls(
            price_threshold_pct=Decimal(
                os.getenv("BREAKOUT_PRICE_THRESHOLD_PCT", "1.0")
            ),
            volume_threshold=Decimal(
                os.getenv("BREAKOUT_VOLUME_THRESHOLD", "1.3")
            ),
            validation_bars=int(
                os.getenv("BREAKOUT_VALIDATION_BARS", "5")
            ),
            strength_bonus=Decimal(
                os.getenv("BREAKOUT_STRENGTH_BONUS", "2.0")
            ),
        )
