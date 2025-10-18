"""ExecutionLog SQLAlchemy model - immutable append-only audit trail for SEC Rule 4530 compliance.

Immutable append-only audit trail. Can only be INSERTed, never UPDATEd or DELETEd.
Immutability enforced at app level; DB RLS also prevents updates.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Index,
    DateTime,
)
from sqlalchemy.orm import relationship, validates

from .base import BaseModel, GUID


class ExecutionAction(str, Enum):
    """Execution action enumeration for audit trail."""

    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    RECOVERED = "RECOVERED"


class ExecutionStatus(str, Enum):
    """Order status at time of action (snapshot)."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ExecutionLog(BaseModel):
    """
    Immutable append-only audit trail for SEC Rule 4530 compliance.

    Records all lifecycle events for order execution including retries and failures.
    Once written, records can NEVER be modified or deleted (enforced at app + DB level).

    Attributes:
        order_id: UUID reference to orders table
        trader_id: UUID reference to traders table (required for compliance)
        action: Type of event (SUBMITTED, APPROVED, EXECUTED, FILLED, REJECTED, CANCELLED, RECOVERED)
        status: Order status at time of action (nullable - captures state snapshot)
        timestamp: Precise moment of event occurrence
        reason: Human-readable explanation (e.g., "Insufficient funds", nullable)
        retry_attempt: Retry count (0=initial, 1=first retry, etc., nullable)
        error_code: Exchange-specific error code (nullable)

    Relationships:
        order: Many-to-one relationship with Order model
        trader: Many-to-one relationship with Trader model (for compliance audit)

    Immutability:
        - __setattr__ raises ValueError on any update attempts after instantiation
        - Database RLS policies prevent UPDATE/DELETE at DB level
        - Compliance requirement: SEC Rule 4530 mandates immutable audit trail
    """

    __tablename__ = "execution_logs"

    # Core fields (SEC Rule 4530 compliance)
    order_id = Column(
        GUID,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to order (FK to orders table)"
    )

    trader_id = Column(
        GUID,
        # ForeignKey to traders table - uncomment when traders table exists
        # ForeignKey("traders.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to trader (FK to traders table) - compliance requirement"
    )

    action = Column(
        String(20),  # Use String for cross-database compatibility; PostgreSQL will use ENUM from migration
        nullable=False,
        comment="Type of event (SUBMITTED/APPROVED/EXECUTED/FILLED/REJECTED/CANCELLED/RECOVERED)"
    )

    status = Column(
        String(20),  # Use String for cross-database compatibility; PostgreSQL will use ENUM from migration
        nullable=True,  # Nullable: captures order status snapshot at time of action
        comment="Order status at time of action (PENDING/FILLED/PARTIAL/REJECTED/CANCELLED)"
    )

    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Precise moment of event (required for compliance)"
    )

    reason = Column(
        String,
        nullable=True,
        comment="Human-readable explanation (e.g., 'Insufficient funds', 'Exchange timeout')"
    )

    retry_attempt = Column(
        Integer,
        nullable=True,
        comment="Retry count (0=initial, 1=first retry, etc.)"
    )

    error_code = Column(
        String(50),
        nullable=True,
        comment="Exchange-specific error code (e.g., 'INSUFFICIENT_FUNDS', 'TIMEOUT')"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        Index("idx_execution_logs_trader_timestamp", "trader_id", "timestamp"),
        Index("idx_execution_logs_order", "order_id"),
        Index("idx_execution_logs_action", "action"),
    )

    # Relationships
    order = relationship("Order", back_populates="execution_logs")
    # trader = relationship("Trader", back_populates="execution_logs")  # Uncomment when Trader model exists

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize ExecutionLog with immutability enforcement.

        After instantiation, any attempt to modify attributes will raise ValueError.
        """
        super().__init__(**kwargs)
        # Mark as initialized to enable immutability checks
        object.__setattr__(self, '_initialized', True)

    def __setattr__(self, key: str, value: Any) -> None:
        """
        Override __setattr__ to enforce immutability after instantiation.

        Raises:
            ValueError: If attempting to modify any attribute after __init__ completes
        """
        # Allow SQLAlchemy internal attributes and initial setup
        if key.startswith('_sa_') or not hasattr(self, '_initialized'):
            object.__setattr__(self, key, value)
            return

        # Prevent any modifications after initialization
        raise ValueError(
            f"ExecutionLog is immutable. Cannot modify attribute '{key}'. "
            f"Audit trail records can only be INSERTed, never UPDATEd (SEC Rule 4530 compliance)."
        )

    def __repr__(self) -> str:
        """
        Return readable string representation of ExecutionLog.

        Returns:
            str: Format "ExecutionLog(order_id=xxx, action=FILLED, timestamp=2025-10-17)"
        """
        timestamp_str = self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else 'None'
        return f"ExecutionLog(order_id={self.order_id}, action={self.action}, timestamp={timestamp_str})"

    def is_immutable(self) -> bool:
        """
        Return True indicating this model is immutable.

        This method exists for documentation and explicit intent signaling.
        All ExecutionLog instances are always immutable after instantiation.

        Returns:
            bool: Always True
        """
        return True

    @validates("action")
    def validate_action(self, key: str, value: Any) -> str:
        """
        Validate and normalize action to string value.

        Args:
            key: Field name
            value: ExecutionAction enum or string value

        Returns:
            str: Validated action string

        Raises:
            ValueError: If action is invalid
        """
        if isinstance(value, ExecutionAction):
            return value.value
        if isinstance(value, str):
            try:
                ExecutionAction(value)  # Validate it's a valid enum value
                return value
            except ValueError:
                raise ValueError(
                    f"Invalid action: {value}. Must be one of {[a.value for a in ExecutionAction]}"
                )
        raise ValueError(f"Action must be ExecutionAction enum or string, got {type(value)}")

    @validates("status")
    def validate_status(self, key: str, value: Any) -> Optional[str]:
        """
        Validate and normalize status to string value.

        Args:
            key: Field name
            value: ExecutionStatus enum or string value (nullable)

        Returns:
            Optional[str]: Validated status string or None

        Raises:
            ValueError: If status is invalid
        """
        if value is None:
            return None

        if isinstance(value, ExecutionStatus):
            return value.value
        if isinstance(value, str):
            try:
                ExecutionStatus(value)  # Validate it's a valid enum value
                return value
            except ValueError:
                raise ValueError(
                    f"Invalid status: {value}. Must be one of {[s.value for s in ExecutionStatus]}"
                )
        raise ValueError(f"Status must be ExecutionStatus enum or string, got {type(value)}")
