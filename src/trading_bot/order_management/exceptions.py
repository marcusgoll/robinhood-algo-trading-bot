"""Custom exceptions for order management."""

from __future__ import annotations


class OrderError(Exception):
    """Base exception for order management errors."""


class OrderSubmissionError(OrderError):
    """Raised when broker rejects or fails to accept an order."""


class OrderCancellationError(OrderError):
    """Raised when cancellation requests fail."""


class OrderStatusError(OrderError):
    """Raised when status retrieval is unsuccessful."""


class UnsupportedOrderTypeError(OrderError):
    """Raised for order types outside the supported scope (limit-only in phase one)."""

    def __init__(self, order_type: str, message: str | None = None) -> None:
        detail = message or (
            f"Order type '{order_type}' is not supported. Use limit orders for this phase."
        )
        super().__init__(detail)
        self.order_type = order_type
