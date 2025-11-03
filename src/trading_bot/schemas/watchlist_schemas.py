"""
Watchlist Schemas

Type-safe data structures for dynamic watchlist generation using screener + sector tags.

Constitution v1.0.0:
- §Code_Quality: Type hints required
- §Data_Integrity: Validate all inputs
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class TierCriteria:
    """Screening criteria for a watchlist tier.

    Attributes:
        min_price: Minimum bid price (optional)
        max_price: Maximum bid price (optional)
        relative_volume: Volume multiplier vs 100-day avg (optional)
        min_daily_change: Minimum daily % change (optional)
        float_max: Maximum float in millions (optional)
    """

    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    relative_volume: Optional[float] = None
    min_daily_change: Optional[float] = None
    float_max: Optional[int] = None

    def validate(self) -> None:
        """Validate criteria values.

        Raises:
            ValueError: If any criterion is invalid
        """
        if self.min_price is not None and self.min_price < 0:
            raise ValueError(f"min_price must be >= 0, got {self.min_price}")

        if self.max_price is not None and self.max_price < 0:
            raise ValueError(f"max_price must be >= 0, got {self.max_price}")

        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price:
                raise ValueError(
                    f"min_price ({self.min_price}) cannot exceed max_price ({self.max_price})"
                )

        if self.relative_volume is not None and self.relative_volume < 0:
            raise ValueError(f"relative_volume must be >= 0, got {self.relative_volume}")

        if self.min_daily_change is not None and self.min_daily_change < 0:
            raise ValueError(
                f"min_daily_change must be >= 0, got {self.min_daily_change}"
            )

        if self.float_max is not None and self.float_max <= 0:
            raise ValueError(f"float_max must be > 0, got {self.float_max}")


@dataclass
class WatchlistTier:
    """Configuration for a single watchlist tier.

    Attributes:
        name: Tier name (e.g., "mega_cap", "large_cap")
        enabled: Whether this tier is active
        sectors: List of sector tags to fetch (e.g., "technology", "biopharmaceutical")
        criteria: Screening criteria for this tier
        max_symbols: Maximum symbols to include from this tier
    """

    name: str
    enabled: bool
    sectors: list[str]
    criteria: TierCriteria
    max_symbols: int

    def validate(self) -> None:
        """Validate tier configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.name:
            raise ValueError("Tier name cannot be empty")

        if not self.sectors:
            raise ValueError(f"Tier '{self.name}' must have at least one sector")

        if self.max_symbols <= 0:
            raise ValueError(
                f"Tier '{self.name}' max_symbols must be > 0, got {self.max_symbols}"
            )

        self.criteria.validate()


@dataclass
class WatchlistConfig:
    """Complete watchlist generation configuration.

    Attributes:
        mode: "dynamic" (auto-generate) or "static" (manual list)
        auto_refresh: Whether to auto-regenerate watchlist
        refresh_schedule: Cron expression for refresh (if auto_refresh=True)
        tiers: List of tier configurations
        fallback_symbols: Static symbol list to use if generation fails
    """

    mode: str  # "dynamic" or "static"
    auto_refresh: bool
    refresh_schedule: Optional[str]  # Cron expression
    tiers: list[WatchlistTier]
    fallback_symbols: list[str]

    def validate(self) -> None:
        """Validate watchlist configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.mode not in ("dynamic", "static"):
            raise ValueError(f"Invalid mode: {self.mode} (must be 'dynamic' or 'static')")

        if self.mode == "dynamic":
            if not self.tiers:
                raise ValueError("Dynamic mode requires at least one tier")

            for tier in self.tiers:
                tier.validate()

        if self.auto_refresh and not self.refresh_schedule:
            raise ValueError("auto_refresh requires refresh_schedule cron expression")

        if not self.fallback_symbols:
            raise ValueError("fallback_symbols cannot be empty (safety requirement)")

    def get_enabled_tiers(self) -> list[WatchlistTier]:
        """Get list of enabled tiers.

        Returns:
            List of enabled WatchlistTier objects
        """
        return [tier for tier in self.tiers if tier.enabled]

    def get_max_total_symbols(self) -> int:
        """Calculate maximum total symbols across all enabled tiers.

        Returns:
            Sum of max_symbols for all enabled tiers
        """
        return sum(tier.max_symbols for tier in self.get_enabled_tiers())


@dataclass
class GeneratedWatchlist:
    """Result of watchlist generation.

    Attributes:
        symbols: List of symbols generated
        generated_at: Timestamp when watchlist was generated
        tier_breakdown: Map of tier name to symbol count
        total_symbols: Total number of symbols
        criteria_used: Map of tier name to criteria dict
        execution_time_ms: Time taken to generate (milliseconds)
        warnings: Any warnings during generation (e.g., insufficient symbols)
    """

    symbols: list[str]
    generated_at: datetime
    tier_breakdown: dict[str, int]
    total_symbols: int
    criteria_used: dict[str, dict]
    execution_time_ms: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "symbols": self.symbols,
            "generated_at": self.generated_at.isoformat(),
            "tier_breakdown": self.tier_breakdown,
            "total_symbols": self.total_symbols,
            "criteria_used": self.criteria_used,
            "execution_time_ms": self.execution_time_ms,
            "warnings": self.warnings,
        }

    def has_warnings(self) -> bool:
        """Check if generation had any warnings.

        Returns:
            True if warnings present
        """
        return len(self.warnings) > 0
