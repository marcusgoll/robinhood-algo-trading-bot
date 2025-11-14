"""OrderRepository for database CRUD operations on Order model."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from ..models.order import Order, OrderStatus, OrderType
from ..models.execution_log import ExecutionLog, ExecutionAction


class OrderRepository:
    """
    Repository for Order database operations with trader isolation.

    Provides CRUD operations for orders with automatic trader isolation
    and execution log creation for audit compliance.

    All queries automatically filter by trader_id to ensure data isolation
    between traders (multi-tenant security).
    """

    def __init__(self, session: Session):
        """
        Initialize OrderRepository.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create(
        self,
        trader_id: UUID,
        symbol: str,
        quantity: int,
        order_type: OrderType,
        price: Optional[Decimal] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> Order:
        """
        Create a new order in PENDING status.

        Args:
            trader_id: UUID of the trader placing the order
            symbol: Stock symbol (e.g., "AAPL", "MSFT")
            quantity: Number of shares (must be > 0)
            order_type: Type of order (MARKET, LIMIT, STOP)
            price: Limit price (required for LIMIT/STOP orders)
            stop_loss: Stop loss price for risk management
            take_profit: Take profit price for risk management

        Returns:
            Order: Created Order instance with PENDING status

        Raises:
            ValueError: If validation fails (quantity <= 0, invalid order type, etc.)
        """
        order = Order(
            trader_id=trader_id,
            symbol=symbol,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.PENDING,
            filled_quantity=0,
        )

        self.session.add(order)
        self.session.flush()  # Generate ID without committing

        # Create initial execution log entry (SUBMITTED action)
        log_entry = ExecutionLog(
            order_id=order.id,
            trader_id=trader_id,
            action=ExecutionAction.SUBMITTED,
            status=OrderStatus.PENDING,
            timestamp=datetime.now(timezone.utc),
            reason="Order created and submitted for execution",
        )
        self.session.add(log_entry)

        return order

    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """
        Fetch order by ID.

        Args:
            order_id: UUID of the order

        Returns:
            Order instance if found, None otherwise
        """
        return self.session.get(Order, order_id)

    def get_by_trader(
        self,
        trader_id: UUID,
        limit: int = 20,
        offset: int = 0,
        status: Optional[OrderStatus] = None,
    ) -> List[Order]:
        """
        List orders for a specific trader with pagination and filtering.

        Enforces trader isolation: only returns orders belonging to the
        specified trader_id.

        Args:
            trader_id: UUID of the trader
            limit: Maximum number of orders to return (default 20)
            offset: Number of orders to skip for pagination (default 0)
            status: Optional status filter (e.g., PENDING, FILLED)

        Returns:
            List of Order instances, ordered by created_at DESC
        """
        query = select(Order).where(Order.trader_id == trader_id)

        # Apply status filter if provided
        if status is not None:
            query = query.where(Order.status == status.value)

        # Order by created_at descending (most recent first)
        query = query.order_by(Order.created_at.desc())

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def update_status(self, order_id: UUID, new_status: OrderStatus) -> Order:
        """
        Update order status with state transition validation and audit logging.

        Validates state transition using Order.update_status() method, then
        creates an execution log entry for compliance.

        Valid transitions:
        - PENDING → FILLED, PARTIAL, REJECTED, CANCELLED
        - PARTIAL → FILLED, REJECTED, CANCELLED
        - FILLED, REJECTED, CANCELLED → (terminal states, no transitions)

        Args:
            order_id: UUID of the order to update
            new_status: New OrderStatus to transition to

        Returns:
            Order: Updated Order instance

        Raises:
            ValueError: If order not found or state transition is invalid
        """
        order = self.session.get(Order, order_id)
        if order is None:
            raise ValueError(f"Order not found: {order_id}")

        # Store old status for logging
        old_status_value = order.status
        old_status = OrderStatus(old_status_value) if isinstance(old_status_value, str) else old_status_value

        # Validate and update status (raises ValueError if invalid transition)
        order.update_status(new_status)

        # Create execution log entry for audit trail
        action = self._determine_action(new_status)
        log_entry = ExecutionLog(
            order_id=order_id,
            trader_id=order.trader_id,
            action=action,
            status=new_status,
            timestamp=datetime.now(timezone.utc),
            reason=f"Status changed from {old_status.value} to {new_status.value}",
        )
        self.session.add(log_entry)
        self.session.flush()

        return order

    def get_unfilled_orders(self, trader_id: UUID) -> List[Order]:
        """
        Get all pending or partially filled orders for a trader.

        Useful for checking active orders, risk calculations, or
        cancellation operations.

        Args:
            trader_id: UUID of the trader

        Returns:
            List of Order instances with status PENDING or PARTIAL
        """
        query = select(Order).where(
            and_(
                Order.trader_id == trader_id,
                Order.status.in_([OrderStatus.PENDING.value, OrderStatus.PARTIAL.value])
            )
        ).order_by(Order.created_at.desc())

        result = self.session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def _determine_action(status: OrderStatus) -> ExecutionAction:
        """
        Map order status to execution action for logging.

        Args:
            status: OrderStatus enum value

        Returns:
            ExecutionAction corresponding to the status
        """
        status_to_action = {
            OrderStatus.PENDING: ExecutionAction.SUBMITTED,
            OrderStatus.FILLED: ExecutionAction.FILLED,
            OrderStatus.PARTIAL: ExecutionAction.FILLED,  # Partial fill is still a fill action
            OrderStatus.REJECTED: ExecutionAction.REJECTED,
            OrderStatus.CANCELLED: ExecutionAction.CANCELLED,
        }
        return status_to_action.get(status, ExecutionAction.EXECUTED)
