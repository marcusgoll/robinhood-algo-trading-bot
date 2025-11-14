"""
Screener Configuration

Environment-based configuration for stock screener module.

Constitution v1.0.0:
- §Security: No hardcoded paths, use environment variables
- §Code_Quality: Type hints required
- §Data_Integrity: Validate all inputs

Feature: stock-screener (001-stock-screener)
Tasks: T006 [GREEN] - Create screener configuration with env var support
Spec: specs/001-stock-screener/spec.md
"""

import os
from dataclasses import dataclass


@dataclass
class ScreenerConfig:
    """
    Stock screener configuration values.

    Supports environment variable overrides for deployment flexibility.
    All values have sensible defaults for local development.

    Environment Variables:
        SCREENER_LOG_DIR: Directory for screener JSONL logs (default: logs/screener)
        SCREENER_BATCH_SIZE: Number of stocks to process in batches (default: 100)
        SCREENER_MAX_RESULTS: Max results per page for pagination (default: 500)
        SCREENER_CACHE_TTL: Cache TTL in seconds (default: 60)

    Example:
        >>> config = ScreenerConfig()
        >>> print(config.LOG_DIR)  # "logs/screener"
        >>> print(config.BATCH_SIZE)  # 100

        >>> # With environment overrides:
        >>> os.environ["SCREENER_LOG_DIR"] = "/var/log/screener"
        >>> os.environ["SCREENER_BATCH_SIZE"] = "200"
        >>> config = ScreenerConfig()
        >>> print(config.LOG_DIR)  # "/var/log/screener"
        >>> print(config.BATCH_SIZE)  # 200
    """

    LOG_DIR: str = "logs/screener"
    BATCH_SIZE: int = 100
    MAX_RESULTS_PER_PAGE: int = 500
    CACHE_TTL_SECONDS: int = 60

    def __post_init__(self) -> None:
        """Apply environment variable overrides after initialization.

        Reads environment variables and overrides defaults if present.
        Validates all values to ensure they are within acceptable ranges.

        Raises:
            ValueError: If environment variable values are invalid (negative, etc.)
        """
        # Override with environment variables if present
        self.LOG_DIR = os.getenv("SCREENER_LOG_DIR", self.LOG_DIR)
        self.BATCH_SIZE = int(os.getenv("SCREENER_BATCH_SIZE", str(self.BATCH_SIZE)))
        self.MAX_RESULTS_PER_PAGE = int(
            os.getenv("SCREENER_MAX_RESULTS", str(self.MAX_RESULTS_PER_PAGE))
        )
        self.CACHE_TTL_SECONDS = int(
            os.getenv("SCREENER_CACHE_TTL", str(self.CACHE_TTL_SECONDS))
        )

        # Validate ranges
        if self.BATCH_SIZE <= 0:
            raise ValueError(
                f"SCREENER_BATCH_SIZE must be > 0, got {self.BATCH_SIZE}"
            )

        if self.MAX_RESULTS_PER_PAGE <= 0:
            raise ValueError(
                f"SCREENER_MAX_RESULTS must be > 0, got {self.MAX_RESULTS_PER_PAGE}"
            )

        if self.CACHE_TTL_SECONDS < 0:
            raise ValueError(
                f"SCREENER_CACHE_TTL must be >= 0, got {self.CACHE_TTL_SECONDS}"
            )

    @classmethod
    def default(cls) -> "ScreenerConfig":
        """Return default configuration (for testing/documentation).

        Returns:
            ScreenerConfig: Instance with default values

        Example:
            >>> config = ScreenerConfig.default()
            >>> assert config.LOG_DIR == "logs/screener"
            >>> assert config.BATCH_SIZE == 100
        """
        return cls()
