"""Fill SQLAlchemy model for individual fill events during order execution."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from uuid import UUID

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    CheckConstraint,
    ForeignKey,
    Index,
    DateTime,
)
from sqlalchemy.orm import relationship, validates

from .base import BaseModel, GUID


class Fill(BaseModel):
    """
    Fill model representing individual fill events when order executes against exchange.

    Attributes:
        order_id: UUID reference to orders table
        timestamp: When fill occurred (not null)
        quantity_filled: Number of shares in this fill (must be > 0)
        price_at_fill: Execution price (must be > 0)
        venue: Exchange name (e.g., "NYSE", "NASDAQ", "Mock")
        commission: Transaction fee (default 0, must be >= 0)

    Relationships:
        order: Many-to-one relationship with Order model
    """

    __tablename__ = "fills"

    # Core fields
    order_id = Column(
        GUID,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to Order (FK to orders table)"
    )

    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When fill occurred"
    )

    quantity_filled = Column(
        Integer,
        nullable=False,
        comment="Number of shares in this fill"
    )

    price_at_fill = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Execution price"
    )

    venue = Column(
        String(50),
        nullable=False,
        comment="Exchange name (NYSE, NASDAQ, etc.)"
    )

    commission = Column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0"),
        server_default='0',
        comment="Transaction fee"
    )

    # Table-level constraints (matching migration)
    __table_args__ = (
        CheckConstraint("quantity_filled > 0", name="ck_fills_quantity_positive"),
        CheckConstraint("price_at_fill > 0", name="ck_fills_price_positive"),
        CheckConstraint("commission >= 0", name="ck_fills_commission_nonnegative"),
        Index("idx_fills_order", "order_id"),
        Index("idx_fills_timestamp", "timestamp"),
    )

    # Relationships
    order = relationship("Order", back_populates="fills")

    def __repr__(self) -> str:
        """
        Return readable string representation of Fill.

        Returns:
            str: Format "Fill(order_id=xxx, qty=50, price=150.25)"
        """
        return f"Fill(order_id={self.order_id}, qty={self.quantity_filled}, price={self.price_at_fill})"

    def total_value(self) -> Decimal:
        """
        Calculate total value of fill (quantity * price).

        Returns:
            Decimal: quantity_filled * price_at_fill
        """
        return Decimal(str(self.quantity_filled)) * Decimal(str(self.price_at_fill))

    def get_net_value(self) -> Decimal:
        """
        Calculate net value after commission.

        Returns:
            Decimal: total_value() - commission
        """
        return self.total_value() - Decimal(str(self.commission))

    @validates("quantity_filled")
    def validate_quantity_filled(self, key: str, value: int) -> int:
        """
        Validate quantity_filled is positive.

        Args:
            key: Field name
            value: Quantity filled value

        Returns:
            int: Validated quantity

        Raises:
            ValueError: If quantity_filled is not positive
        """
        if value <= 0:
            raise ValueError(f"Quantity filled must be positive, got {value}")
        return value

    @validates("price_at_fill")
    def validate_price_at_fill(self, key: str, value: Decimal) -> Decimal:
        """
        Validate price_at_fill is positive.

        Args:
            key: Field name
            value: Price value

        Returns:
            Decimal: Validated price

        Raises:
            ValueError: If price_at_fill is not positive
        """
        if value <= 0:
            raise ValueError(f"Price at fill must be positive, got {value}")
        return value

    @validates("commission")
    def validate_commission(self, key: str, value: Decimal) -> Decimal:
        """
        Validate commission is non-negative.

        Args:
            key: Field name
            value: Commission value

        Returns:
            Decimal: Validated commission

        Raises:
            ValueError: If commission is negative
        """
        if value < 0:
            raise ValueError(f"Commission must be non-negative, got {value}")
        return value
