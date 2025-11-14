"""Order SQLAlchemy model with validation, relationships, and helper methods."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any, Union
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
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from sqlalchemy.dialects.postgresql import TIMESTAMP, ENUM as PostgreSQL_ENUM
from sqlalchemy.orm import relationship, validates
from sqlalchemy.types import TypeDecorator, CHAR
from typing import Any
import uuid as uuid_lib

from .base import BaseModel


class GUID(TypeDecorator[UUID]):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid_lib.UUID):
                return str(value)
            return str(uuid_lib.UUID(value))

    def process_result_value(self, value: Any, dialect: Any) -> Optional[UUID]:
        if value is None:
            return value
        if isinstance(value, uuid_lib.UUID):
            return value
        return uuid_lib.UUID(value)


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# Valid state transitions for order status
VALID_STATUS_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.FILLED, OrderStatus.PARTIAL, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.PARTIAL: {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.FILLED: set(),  # Terminal state
    OrderStatus.REJECTED: set(),  # Terminal state
    OrderStatus.CANCELLED: set(),  # Terminal state
}


class Order(BaseModel):
    """
    Order model representing a trader's order request with full execution lifecycle tracking.

    Attributes:
        trader_id: UUID reference to traders table
        symbol: Stock symbol (e.g., "AAPL", "MSFT")
        quantity: Number of shares (must be > 0)
        order_type: Type of order (MARKET, LIMIT, STOP)
        price: Limit price (nullable, null for market orders)
        stop_loss: Stop loss price for risk management (nullable)
        take_profit: Take profit price for risk management (nullable)
        status: Current order status (PENDING, FILLED, PARTIAL, REJECTED, CANCELLED)
        filled_quantity: Quantity filled so far (default 0)
        average_fill_price: Average price of all fills (nullable)
        expires_at: Order expiration time (nullable)

    Relationships:
        fills: One-to-many relationship with Fill model
        execution_logs: One-to-many relationship with ExecutionLog model
    """

    __tablename__ = "orders"

    # Core fields
    trader_id = Column(
        GUID,
        nullable=False,
        comment="Reference to trader (FK to traders table)"
    )

    symbol = Column(
        String(10),
        nullable=False,
        comment="Stock symbol (e.g., AAPL, MSFT)"
    )

    quantity = Column(
        Integer,
        nullable=False,
        comment="Number of shares to trade"
    )

    order_type = Column(
        String(10),  # Use String for cross-database compatibility; PostgreSQL will use ENUM from migration
        nullable=False,
        comment="Type of order (MARKET/LIMIT/STOP)"
    )

    price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Limit price (null for market orders)"
    )

    stop_loss = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Stop loss price for risk management"
    )

    take_profit = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Take profit price for risk management"
    )

    status = Column(
        String(20),  # Use String for cross-database compatibility; PostgreSQL will use ENUM from migration
        nullable=False,
        default=OrderStatus.PENDING.value,
        comment="Current order status"
    )

    filled_quantity = Column(
        Integer,
        nullable=False,
        default=0,
        server_default='0',
        comment="Quantity filled so far"
    )

    average_fill_price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Average price of all fills"
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Order expiration time (if timeout set)"
    )

    # Table-level constraints (matching migration)
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_orders_quantity_positive"),
        CheckConstraint("price IS NULL OR price > 0", name="ck_orders_price_positive"),
        CheckConstraint("filled_quantity >= 0", name="ck_orders_filled_quantity_nonnegative"),
        CheckConstraint("filled_quantity <= quantity", name="ck_orders_filled_lte_quantity"),
        CheckConstraint(
            "order_type = 'MARKET' OR price IS NOT NULL",
            name="ck_orders_limit_requires_price"
        ),
        Index("idx_orders_trader_created", "trader_id", "created_at"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_trader_status", "trader_id", "status"),
    )

    # Relationships
    fills = relationship("Fill", back_populates="order", cascade="all, delete-orphan")
    execution_logs = relationship("ExecutionLog", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """
        Return readable string representation of Order.

        Returns:
            str: Format "Order(id=xxx, symbol=AAPL, qty=100)"
        """
        return f"Order(id={self.id}, symbol={self.symbol}, qty={self.quantity})"

    def is_pending(self) -> bool:
        """
        Check if order is in PENDING status.

        Returns:
            bool: True if status is PENDING, False otherwise
        """
        # Type ignore for Column comparison
        return bool(self.status == OrderStatus.PENDING.value or self.status == OrderStatus.PENDING)

    def get_unfilled_quantity(self) -> int:
        """
        Calculate remaining unfilled quantity.

        Returns:
            int: Quantity minus filled_quantity
        """
        # Type ignore for Column arithmetic
        return int(self.quantity - self.filled_quantity)

    def update_status(self, new_status: Union[OrderStatus, str]) -> None:
        """
        Update order status with validation of state transitions.

        Valid transitions:
        - PENDING → FILLED, PARTIAL, REJECTED, CANCELLED
        - PARTIAL → FILLED, REJECTED, CANCELLED
        - FILLED, REJECTED, CANCELLED → (terminal states, no transitions)

        Args:
            new_status: New OrderStatus to transition to

        Raises:
            ValueError: If the status transition is invalid
        """
        # Normalize status to enum
        current_status_value: Any = self.status
        current_status = OrderStatus(current_status_value) if isinstance(current_status_value, str) else current_status_value
        new_status_enum = OrderStatus(new_status) if isinstance(new_status, str) else new_status

        if current_status == new_status_enum:
            # No change needed
            return

        valid_next_states = VALID_STATUS_TRANSITIONS.get(current_status, set())

        if new_status_enum not in valid_next_states:
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status_enum.value}. "
                f"Valid transitions: {', '.join(s.value for s in valid_next_states) or 'none (terminal state)'}"
            )

        setattr(self, 'status', new_status_enum.value)
        setattr(self, 'updated_at', datetime.now(timezone.utc))

    @validates("order_type")
    def validate_order_type(self, key: str, value: Any) -> str:
        """
        Validate and normalize order_type to string value.

        Args:
            key: Field name
            value: OrderType enum or string value

        Returns:
            str: Validated order type string

        Raises:
            ValueError: If order type is invalid
        """
        if isinstance(value, OrderType):
            return value.value
        if isinstance(value, str):
            try:
                OrderType(value)  # Validate it's a valid enum value
                return value
            except ValueError:
                raise ValueError(f"Invalid order type: {value}. Must be one of {[t.value for t in OrderType]}")
        raise ValueError(f"Order type must be OrderType enum or string, got {type(value)}")

    @validates("status")
    def validate_status(self, key: str, value: Any) -> str:
        """
        Validate and normalize status to string value.

        Args:
            key: Field name
            value: OrderStatus enum or string value

        Returns:
            str: Validated status string

        Raises:
            ValueError: If status is invalid
        """
        if isinstance(value, OrderStatus):
            return value.value
        if isinstance(value, str):
            try:
                OrderStatus(value)  # Validate it's a valid enum value
                return value
            except ValueError:
                raise ValueError(f"Invalid status: {value}. Must be one of {[s.value for s in OrderStatus]}")
        raise ValueError(f"Status must be OrderStatus enum or string, got {type(value)}")

    @validates("quantity")
    def validate_quantity(self, key: str, value: int) -> int:
        """
        Validate quantity is positive.

        Args:
            key: Field name
            value: Quantity value

        Returns:
            int: Validated quantity

        Raises:
            ValueError: If quantity is not positive
        """
        if value <= 0:
            raise ValueError(f"Quantity must be positive, got {value}")
        return value

    @validates("price")
    def validate_price(self, key: str, value: Optional[Decimal]) -> Optional[Decimal]:
        """
        Validate price is positive if set.

        Args:
            key: Field name
            value: Price value

        Returns:
            Optional[Decimal]: Validated price

        Raises:
            ValueError: If price is set but not positive
        """
        if value is not None and value <= 0:
            raise ValueError(f"Price must be positive if set, got {value}")
        return value
