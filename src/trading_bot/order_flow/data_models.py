"""
Order Flow Data Models

Type-safe data models for order flow monitoring system.

Pattern: Follows data model patterns from market_data/data_models.py
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class OrderFlowAlert:
    """
    Represents a detected order flow alert (large seller or red burst pattern).

    Immutable alert record for audit trail and risk management integration.

    Attributes:
        symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")
        alert_type: Type of alert detected
        severity: Alert severity level
        order_size: Size of large order in shares (None for red_burst)
        price_level: Price level of large order (None for red_burst)
        volume_ratio: Volume spike ratio (e.g., 3.5 = 350% of average, None for large_seller)
        timestamp_utc: When alert was detected (UTC timezone)

    Example:
        >>> alert = OrderFlowAlert(
        ...     symbol="AAPL",
        ...     alert_type="large_seller",
        ...     severity="warning",
        ...     order_size=15000,
        ...     price_level=Decimal("175.50"),
        ...     volume_ratio=None,
        ...     timestamp_utc=datetime.now(timezone.utc)
        ... )
    """

    symbol: str
    alert_type: Literal["large_seller", "red_burst"]
    severity: Literal["warning", "critical"]
    order_size: int | None
    price_level: Decimal | None
    volume_ratio: float | None
    timestamp_utc: datetime

    def __post_init__(self) -> None:
        """Validate alert data integrity."""
        # Validate symbol
        if not self.symbol or not self.symbol.isupper():
            raise ValueError(
                f"Invalid OrderFlowAlert: symbol ({self.symbol}) must be non-empty uppercase"
            )

        # Validate timezone-aware timestamp
        if self.timestamp_utc.tzinfo is None:
            raise ValueError(
                "Invalid OrderFlowAlert: timestamp_utc must be timezone-aware (UTC)"
            )

        # Validate large_seller alerts have order_size and price_level
        if self.alert_type == "large_seller":
            if self.order_size is None or self.order_size <= 0:
                raise ValueError(
                    f"Invalid OrderFlowAlert: large_seller alerts must have order_size >0 "
                    f"(got {self.order_size})"
                )
            if self.price_level is None or self.price_level <= 0:
                raise ValueError(
                    "Invalid OrderFlowAlert: large_seller alerts must have price_level >$0"
                )

        # Validate red_burst alerts have volume_ratio
        if self.alert_type == "red_burst":
            if self.volume_ratio is None or self.volume_ratio < 3.0:
                raise ValueError(
                    f"Invalid OrderFlowAlert: red_burst alerts must have volume_ratio >=3.0 "
                    f"(got {self.volume_ratio})"
                )


@dataclass(frozen=True)
class OrderBookSnapshot:
    """
    Level 2 order book snapshot with bid/ask depth.

    Snapshot data for detecting large seller orders in order book.

    Attributes:
        symbol: Stock ticker symbol
        bids: List of (price, size) bid orders, sorted by price descending
        asks: List of (price, size) ask orders, sorted by price ascending
        timestamp_utc: Snapshot timestamp from API (UTC)

    Example:
        >>> snapshot = OrderBookSnapshot(
        ...     symbol="AAPL",
        ...     bids=[(Decimal("175.50"), 10000), (Decimal("175.49"), 5000)],
        ...     asks=[(Decimal("175.51"), 3000), (Decimal("175.52"), 8000)],
        ...     timestamp_utc=datetime.now(timezone.utc)
        ... )
    """

    symbol: str
    bids: list[tuple[Decimal, int]]
    asks: list[tuple[Decimal, int]]
    timestamp_utc: datetime

    def __post_init__(self) -> None:
        """Validate order book data integrity."""
        # Validate symbol
        if not self.symbol or not self.symbol.isupper():
            raise ValueError(
                f"Invalid OrderBookSnapshot: symbol ({self.symbol}) must be non-empty uppercase"
            )

        # Validate timezone-aware timestamp
        if self.timestamp_utc.tzinfo is None:
            raise ValueError(
                "Invalid OrderBookSnapshot: timestamp_utc must be timezone-aware (UTC)"
            )

        # Validate bids
        for price, size in self.bids:
            if price <= 0:
                raise ValueError(
                    f"Invalid OrderBookSnapshot: bid price ({price}) must be >$0"
                )
            if size <= 0:
                raise ValueError(
                    f"Invalid OrderBookSnapshot: bid size ({size}) must be >0 shares"
                )

        # Validate asks
        for price, size in self.asks:
            if price <= 0:
                raise ValueError(
                    f"Invalid OrderBookSnapshot: ask price ({price}) must be >$0"
                )
            if size <= 0:
                raise ValueError(
                    f"Invalid OrderBookSnapshot: ask size ({size}) must be >0 shares"
                )


@dataclass(frozen=True)
class TimeAndSalesRecord:
    """
    Individual tick from Time & Sales tape (executed trade).

    Trade record for volume spike and red burst detection.

    Attributes:
        symbol: Stock ticker symbol
        price: Trade execution price
        size: Trade size in shares
        side: Trade side (buyer-initiated or seller-initiated)
        timestamp_utc: Trade execution timestamp (UTC)

    Example:
        >>> tick = TimeAndSalesRecord(
        ...     symbol="AAPL",
        ...     price=Decimal("175.50"),
        ...     size=5000,
        ...     side="sell",
        ...     timestamp_utc=datetime.now(timezone.utc)
        ... )
    """

    symbol: str
    price: Decimal
    size: int
    side: Literal["buy", "sell"]
    timestamp_utc: datetime

    def __post_init__(self) -> None:
        """Validate trade data integrity."""
        # Validate symbol
        if not self.symbol or not self.symbol.isupper():
            raise ValueError(
                f"Invalid TimeAndSalesRecord: symbol ({self.symbol}) must be non-empty uppercase"
            )

        # Validate price
        if self.price <= 0:
            raise ValueError(
                f"Invalid TimeAndSalesRecord: price ({self.price}) must be >$0"
            )

        # Validate size
        if self.size <= 0:
            raise ValueError(
                f"Invalid TimeAndSalesRecord: size ({self.size}) must be >0 shares"
            )

        # Validate timezone-aware timestamp
        if self.timestamp_utc.tzinfo is None:
            raise ValueError(
                "Invalid TimeAndSalesRecord: timestamp_utc must be timezone-aware (UTC)"
            )
