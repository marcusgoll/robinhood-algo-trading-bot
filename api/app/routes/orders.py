"""Orders API routes for order submission and management."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.auth import get_current_trader_id
from ..core.database import get_db
from ..core.events import event_bus
from ..models.order import OrderType, OrderStatus
from ..repositories.order_repository import OrderRepository
from ..schemas.order import ErrorResponse, OrderResponse, OrderSubmitRequest
from ..services.order_validator import OrderValidator

# Module-level dependencies (will be patched in tests)
# In production, these would be properly initialized
trader_repository: Any = None  # type: ignore
exchange_adapter: Any = None  # type: ignore

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"description": "Unauthorized"},
        500: {"description": "Server error"},
    },
)
async def submit_order(
    order_request: OrderSubmitRequest,
    trader_id: UUID = Depends(get_current_trader_id),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """
    Submit a new order for execution.

    Validation pipeline:
    1. Extract trader_id from JWT token (authentication)
    2. Parse and validate request body (Pydantic validation)
    3. Validate business rules (OrderValidator)
    4. Create order in database (OrderRepository)
    5. Log execution (ExecutionLog)
    6. Publish event (EventBus)

    Args:
        order_request: Order submission request
        trader_id: Trader ID from JWT token
        db: Database session

    Returns:
        OrderResponse: Created order with PENDING status

    Raises:
        HTTPException: 400 for validation errors, 401 for auth errors
    """
    # Initialize validator
    validator = OrderValidator(
        exchange_adapter=exchange_adapter,
        trader_repository=trader_repository,
    )

    # Validate order
    validation_result = validator.validate_order(
        trader_id=str(trader_id),
        order_request=order_request,
    )

    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": validation_result.error_code,
                "message": validation_result.message,
                "details": validation_result.details,
            },
        )

    # Create order
    repository = OrderRepository(db)
    order = repository.create(
        trader_id=trader_id,
        symbol=order_request.symbol,
        quantity=order_request.quantity,
        order_type=OrderType(order_request.order_type),
        price=order_request.price,
        stop_loss=order_request.stop_loss,
        take_profit=order_request.take_profit,
    )

    # Publish order.submitted event
    event_bus.publish_order_submitted(
        order_id=order.id,
        trader_id=trader_id,
        symbol=order.symbol,
        quantity=order.quantity,
        order_type=order.order_type,
    )

    # Return response
    return OrderResponse.model_validate(order)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Order not in PENDING status"},
        401: {"description": "Unauthorized"},
        404: {"description": "Order not found"},
        500: {"description": "Server error"},
    },
)
async def cancel_order(
    order_id: UUID,
    trader_id: UUID = Depends(get_current_trader_id),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """
    Cancel a pending order.

    Only orders in PENDING status can be cancelled. Cancellation is logged
    for audit trail (SEC Rule 4530) and an event is published for real-time updates.

    Args:
        order_id: UUID of the order to cancel
        trader_id: Trader ID from JWT token (authentication)
        db: Database session

    Returns:
        OrderResponse: Updated order with status=CANCELLED

    Raises:
        HTTPException: 404 if order not found or not owned by trader
        HTTPException: 400 if order not in PENDING status
        HTTPException: 500 for database errors
    """
    # Initialize repository
    repository = OrderRepository(db)

    # Step 1: Fetch order
    order = repository.get_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Step 2: Verify ownership (security - trader isolation)
    if order.trader_id != trader_id:
        # Don't expose other traders' orders
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Step 3: Check status (only PENDING orders can be cancelled)
    current_status_value = order.status
    current_status = (
        OrderStatus(current_status_value)
        if isinstance(current_status_value, str)
        else current_status_value
    )

    if current_status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CANNOT_CANCEL",
                "message": f"Cannot cancel order in {current_status.value} status. Only PENDING orders can be cancelled.",
                "current_status": current_status.value,
            },
        )

    # Step 4: Update status to CANCELLED
    try:
        order = repository.update_status(order_id, OrderStatus.CANCELLED)
    except ValueError as e:
        # Should not happen after status check, but handle gracefully
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_TRANSITION", "message": str(e)},
        )

    # Step 5: Commit transaction
    db.commit()

    # Step 6: Publish event for real-time updates
    event_bus.publish_order_cancelled(
        order_id=order.id,
        trader_id=trader_id,
        symbol=order.symbol,
    )

    # Step 7: Return response
    return OrderResponse.model_validate(order)
