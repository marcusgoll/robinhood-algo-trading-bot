"""
Support/Resistance Zone Detection Configuration

Configuration dataclass for zone detection system.
Provides defaults from spec.md and environment variable loading.

Pattern: Follows MomentumConfig pattern from momentum/config.py
"""

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ZoneDetectionConfig:
    """
    Configuration for support/resistance zone detection.

    All fields have sensible defaults from spec.md requirements (US1-US3).
    Use from_env() class method to load from environment variables.

    Attributes:
        touch_threshold: Minimum touches to qualify as a zone (default: 3 for daily)
        volume_threshold: Volume multiplier for high-volume bonus (default: 1.5x average)
        proximity_threshold_pct: Alert distance threshold as percentage (default: 2.0%)
        min_days: Minimum historical days for analysis (default: 30, ideally 60+)
        tolerance_pct: Price clustering tolerance as percentage (default: 1.5%)

    Raises:
        ValueError: If validation fails in __post_init__
    """

    touch_threshold: int = 3
    volume_threshold: Decimal = Decimal("1.5")
    proximity_threshold_pct: Decimal = Decimal("2.0")
    min_days: int = 30
    tolerance_pct: Decimal = Decimal("1.5")

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate positive values
        if self.touch_threshold <= 0:
            raise ValueError(
                f"Invalid ZoneDetectionConfig: touch_threshold ({self.touch_threshold}) must be positive"
            )

        if self.volume_threshold <= 0:
            raise ValueError(
                f"Invalid ZoneDetectionConfig: volume_threshold ({self.volume_threshold}) must be positive"
            )

        if self.proximity_threshold_pct <= 0:
            raise ValueError(
                f"Invalid ZoneDetectionConfig: proximity_threshold_pct ({self.proximity_threshold_pct}) must be positive"
            )

        if self.tolerance_pct <= 0:
            raise ValueError(
                f"Invalid ZoneDetectionConfig: tolerance_pct ({self.tolerance_pct}) must be positive"
            )

        # Validate min_days is sufficient for analysis
        if self.min_days < 30:
            raise ValueError(
                f"Invalid ZoneDetectionConfig: min_days ({self.min_days}) must be >= 30 "
                f"for reliable zone detection"
            )

    @classmethod
    def from_env(cls) -> "ZoneDetectionConfig":
        """
        Load configuration from environment variables.

        Environment Variables:
            ZONE_TOUCH_THRESHOLD: Minimum touches for a zone (int, default: 3)
            ZONE_VOLUME_THRESHOLD: Volume multiplier for bonus (float, default: 1.5)
            ZONE_PROXIMITY_PCT: Alert distance threshold % (float, default: 2.0)
            ZONE_MIN_DAYS: Minimum historical days (int, default: 30)
            ZONE_TOLERANCE_PCT: Price clustering tolerance % (float, default: 1.5)

        Returns:
            ZoneDetectionConfig instance with values from environment or defaults

        Example:
            >>> config = ZoneDetectionConfig.from_env()
            >>> config.touch_threshold
            3
        """
        return cls(
            touch_threshold=int(os.getenv("ZONE_TOUCH_THRESHOLD", "3")),
            volume_threshold=Decimal(os.getenv("ZONE_VOLUME_THRESHOLD", "1.5")),
            proximity_threshold_pct=Decimal(os.getenv("ZONE_PROXIMITY_PCT", "2.0")),
            min_days=int(os.getenv("ZONE_MIN_DAYS", "30")),
            tolerance_pct=Decimal(os.getenv("ZONE_TOLERANCE_PCT", "1.5")),
        )
