"""
Multi-Timeframe Validation Configuration

Configuration dataclass loaded from environment variables.
"""

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MultiTimeframeConfig:
    """Configuration for multi-timeframe validation.

    Loaded from environment variables with sensible defaults.

    Args:
        enabled: Feature flag to enable/disable validation
        daily_weight: Weight for daily timeframe score (0.0-1.0)
        h4_weight: Weight for 4H timeframe score (0.0-1.0)
        aggregate_threshold: Minimum aggregate score to PASS (0.0-1.0)
        max_retries: Maximum retry attempts for data fetch
        retry_backoff_base_ms: Base delay for exponential backoff (milliseconds)

    Environment Variables:
        MULTI_TIMEFRAME_VALIDATION_ENABLED: "true"/"false" (default: true)
        DAILY_WEIGHT: Float 0.0-1.0 (default: 0.6)
        H4_WEIGHT: Float 0.0-1.0 (default: 0.4)
        AGGREGATE_THRESHOLD: Float 0.0-1.0 (default: 0.5)
        MAX_RETRIES: Integer >= 0 (default: 3)
        RETRY_BACKOFF_BASE_MS: Integer > 0 (default: 1000)

    Example:
        >>> config = MultiTimeframeConfig.from_env()
        >>> print(config.daily_weight)  # 0.6
        >>> print(config.enabled)  # True
    """
    enabled: bool
    daily_weight: Decimal
    h4_weight: Decimal
    aggregate_threshold: Decimal
    max_retries: int
    retry_backoff_base_ms: int

    @classmethod
    def from_env(cls) -> "MultiTimeframeConfig":
        """Load configuration from environment variables.

        Returns:
            MultiTimeframeConfig instance with values from env or defaults

        Example:
            >>> os.environ["DAILY_WEIGHT"] = "0.7"
            >>> config = MultiTimeframeConfig.from_env()
            >>> config.daily_weight
            Decimal('0.7')
        """
        return cls(
            enabled=os.getenv("MULTI_TIMEFRAME_VALIDATION_ENABLED", "true").lower() == "true",
            daily_weight=Decimal(os.getenv("DAILY_WEIGHT", "0.6")),
            h4_weight=Decimal(os.getenv("H4_WEIGHT", "0.4")),
            aggregate_threshold=Decimal(os.getenv("AGGREGATE_THRESHOLD", "0.5")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_backoff_base_ms=int(os.getenv("RETRY_BACKOFF_BASE_MS", "1000"))
        )
