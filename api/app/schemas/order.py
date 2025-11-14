"""Pydantic schemas for order submission and response."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..models.order import OrderType, OrderStatus


class OrderSubmitRequest(BaseModel):
    """
    Request schema for order submission.

    Attributes:
        symbol: Stock symbol (1-10 characters)
        quantity: Number of shares (must be > 0)
        order_type: Type of order (MARKET, LIMIT, STOP)
        price: Limit price (required for LIMIT/STOP orders)
        stop_loss: Optional stop loss price
        take_profit: Optional take profit price
    """

    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    quantity: int = Field(..., gt=0, description="Number of shares to trade")
    order_type: OrderType = Field(..., description="Type of order")
    price: Optional[Decimal] = Field(None, gt=0, description="Limit price for LIMIT/STOP orders")
    stop_loss: Optional[Decimal] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Take profit price")

    @field_validator("price")
    @classmethod
    def validate_price_for_limit_stop(cls, v: Optional[Decimal], info: dict) -> Optional[Decimal]:
        """
        Validate that price is provided for LIMIT/STOP orders.

        Args:
            v: Price value
            info: Validation context containing other fields

        Returns:
            Optional[Decimal]: Validated price

        Raises:
            ValueError: If LIMIT/STOP order is missing price
        """
        # Access order_type from validation context
        order_type = info.data.get("order_type")
        if order_type in [OrderType.LIMIT, OrderType.STOP] and v is None:
            raise ValueError(f"Price is required for {order_type.value} orders")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                    "price": None,
                    "stop_loss": 145.50,
                    "take_profit": 155.00,
                }
            ]
        }
    }


class OrderResponse(BaseModel):
    """
    Response schema for order submission.

    Attributes:
        id: Order UUID
        trader_id: Trader UUID
        symbol: Stock symbol
        quantity: Number of shares
        order_type: Type of order
        price: Limit price (if applicable)
        status: Current order status
        filled_quantity: Number of shares filled
        created_at: Order creation timestamp
        updated_at: Order last update timestamp
    """

    id: UUID
    trader_id: UUID
    symbol: str
    quantity: int
    order_type: OrderType
    price: Optional[Decimal]
    status: OrderStatus
    filled_quantity: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,  # Enable ORM mode for SQLAlchemy models
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "trader_id": "456e7890-e89b-12d3-a456-426614174111",
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                    "price": None,
                    "status": "PENDING",
                    "created_at": "2025-10-17T12:00:00Z",
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """
    Error response schema.

    Attributes:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error context
    """

    error_code: str
    message: str
    details: Optional[dict] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "INSUFFICIENT_BALANCE",
                    "message": "Insufficient funds for $5,000 order; available: $3,200",
                    "details": {
                        "required_balance": 5000.0,
                        "available_balance": 3200.0,
                    },
                }
            ]
        }
    }
