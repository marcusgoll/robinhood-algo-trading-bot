"""
Stock Screener Schemas

Dataclasses for stock screener request/response contracts:
- ScreenerQuery: Filter parameters and validation
- StockScreenerMatch: Single stock match result
- PageInfo: Pagination metadata
- ScreenerResult: Complete screener response
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import uuid4


@dataclass
class ScreenerQuery:
    """
    Stock screener filter parameters (request contract).

    Attributes:
        min_price: Minimum bid price filter (e.g., 2.00)
        max_price: Maximum bid price filter (e.g., 20.00)
        relative_volume: Volume multiplier vs 100-day avg (e.g., 5.0 = 5x)
        float_max: Maximum public float in millions (e.g., 20 = under 20M shares)
        min_daily_change: Minimum daily % move (e.g., 10.0 = ±10%)
        limit: Results per page (1-500, default 500)
        offset: Pagination offset (default 0)
        query_id: Unique query identifier for audit trail

    Raises:
        ValueError: If validation rules violated
    """

    min_price: Decimal | None = None
    max_price: Decimal | None = None
    relative_volume: float | None = None
    float_max: int | None = None
    min_daily_change: float | None = None
    limit: int = 500
    offset: int = 0
    query_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Validate filter parameters after initialization."""
        # Validate price range consistency
        if self.min_price is not None and self.max_price is not None:
            if self.min_price >= self.max_price:
                raise ValueError(
                    f"min_price ({self.min_price}) >= max_price ({self.max_price}), "
                    "must have min < max"
                )

        # Validate limit bounds
        if not (1 <= self.limit <= 500):
            raise ValueError(f"limit must be 1-500, got {self.limit}")

        # Validate offset is non-negative
        if self.offset < 0:
            raise ValueError(f"offset must be >= 0, got {self.offset}")


@dataclass
class StockScreenerMatch:
    """
    Single stock that matched screener filters.

    Attributes:
        symbol: Stock ticker (e.g., "TSLA")
        bid_price: Current bid price
        volume: Current session volume (shares traded)
        daily_open: Day's opening price
        daily_close: Current price (for daily change calculation)
        daily_change_pct: Daily change percent (absolute value)
        matched_filters: Filters this stock passed (e.g., ["price_range", "volume_spike"])
        volume_avg_100d: 100-day average volume (None if unavailable)
        float_shares: Public float in shares (None if unavailable)
        daily_change_direction: "up" or "down" (default "up")
        data_gaps: Fields unavailable (e.g., ["float"])
        timestamp: Quote timestamp in ISO 8601 format with Z suffix

    Raises:
        ValueError: If validation rules violated
    """

    symbol: str
    bid_price: Decimal
    volume: int
    daily_open: Decimal
    daily_close: Decimal
    daily_change_pct: float
    matched_filters: list[str]
    volume_avg_100d: int | None = None
    float_shares: int | None = None
    daily_change_direction: str = "up"
    data_gaps: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def __post_init__(self) -> None:
        """Validate stock match data after initialization."""
        # Validate symbol length (stock tickers are 1-5 characters)
        if not (1 <= len(self.symbol) <= 5):
            raise ValueError(f"Symbol must be 1-5 chars, got {self.symbol}")

        # Validate bid price is positive
        if self.bid_price <= 0:
            raise ValueError(f"bid_price must be > 0, got {self.bid_price}")

        # Validate daily change percentage bounds
        if not (0 <= self.daily_change_pct <= 1000):
            raise ValueError(f"daily_change_pct must be 0-1000, got {self.daily_change_pct}")


@dataclass
class PageInfo:
    """
    Pagination metadata for large result sets.

    Attributes:
        offset: Current offset in results
        limit: Page size (1-500)
        has_more: True if more results available
        next_offset: Suggested offset for next page (auto-calculated if has_more)
        page_number: 1-indexed current page (auto-calculated)
    """

    offset: int
    limit: int
    has_more: bool
    next_offset: int | None = None
    page_number: int = 1

    def __post_init__(self) -> None:
        """Calculate pagination metadata after initialization."""
        # Auto-calculate next_offset if has_more and not explicitly provided
        if self.has_more and self.next_offset is None:
            self.next_offset = self.offset + self.limit

        # Calculate page number from offset and limit
        self.page_number = (self.offset // self.limit) + 1


@dataclass
class ScreenerResult:
    """
    Complete screener query result with metadata.

    Attributes:
        query_id: Matches ScreenerQuery.query_id for audit trail
        stocks: Matched stocks (0-500 per page)
        query_timestamp: When query was executed (ISO 8601 with Z suffix)
        result_count: Number of stocks in this page
        total_count: Total matches across all pages
        execution_time_ms: Query execution time (for performance monitoring)
        page_info: Pagination metadata
        errors: Data gaps encountered (e.g., ["3 stocks missing float data"])
        api_calls_made: Total API calls (for cost tracking)
        cache_hit: Whether result was cached (default False)
    """

    query_id: str
    stocks: list[StockScreenerMatch]
    query_timestamp: str
    result_count: int
    total_count: int
    execution_time_ms: float
    page_info: PageInfo
    errors: list[str] = field(default_factory=list)
    api_calls_made: int = 0
    cache_hit: bool = False
