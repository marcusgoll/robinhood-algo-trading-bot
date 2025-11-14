"""
OrderExecutor service for executing orders with retry and idempotency.

This service implements exponential backoff retry logic and idempotent key deduplication
to handle network failures gracefully (FR-008, FR-009, FR-010).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Protocol
from uuid import UUID


class ErrorCode(str, Enum):
    """Error codes for execution failures."""

    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    EXCHANGE_ERROR = "EXCHANGE_ERROR"
    DUPLICATE_ORDER = "DUPLICATE_ORDER"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class ExecutionResult:
    """
    Result of order execution.

    Attributes:
        success: Whether the order executed successfully
        order_id: Exchange order ID if successful
        fill_price: Price at which order was filled (if filled)
        error: Human-readable error message if failed
        retry_count: Number of retry attempts made
        error_code: Exchange error code if applicable
    """

    success: bool
    order_id: Optional[str] = None
    fill_price: Optional[Decimal] = None
    error: str = ""
    retry_count: int = 0
    error_code: Optional[str] = None


@dataclass
class OrderRequest:
    """
    Order request data for submission.

    Attributes:
        symbol: Stock symbol (e.g., "AAPL")
        quantity: Number of shares
        order_type: Type of order (MARKET, LIMIT, STOP)
        price: Limit price (nullable for market orders)
    """

    symbol: str
    quantity: int
    order_type: str
    price: Optional[Decimal] = None


@dataclass
class OrderStatus:
    """
    Order status from exchange.

    Attributes:
        order_id: Exchange order ID
        status: Current status (PENDING, FILLED, REJECTED)
        filled_quantity: Quantity filled so far
        fill_price: Average fill price
    """

    order_id: str
    status: str
    filled_quantity: int = 0
    fill_price: Optional[Decimal] = None


class ExchangeAdapterProtocol(Protocol):
    """Protocol for exchange adapter dependency."""

    def submit_order(self, order_request: OrderRequest, idempotent_key: str) -> OrderStatus:
        """Submit order to exchange with idempotent key."""
        ...

    def get_order_by_idempotent_key(self, idempotent_key: str) -> Optional[OrderStatus]:
        """Check if order exists by idempotent key."""
        ...


class EventBusProtocol(Protocol):
    """Protocol for event bus dependency."""

    def publish(self, channel: str, event: dict[str, Any]) -> None:
        """Publish event to channel."""
        ...


class NetworkError(Exception):
    """Network connectivity error."""

    pass


class TimeoutError(Exception):
    """Request timeout error."""

    pass


class ExchangeError(Exception):
    """Exchange-side error."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class OrderExecutor:
    """
    Service for executing orders with exponential backoff retry and idempotency.

    This is a critical component for FR-008, FR-009, FR-010 (error handling and recovery).
    Implements automatic retry with duplicate prevention using idempotent keys.
    """

    # Fatal error codes that should not trigger retry
    FATAL_ERROR_CODES = {
        "INVALID_SYMBOL",
        "UNAUTHORIZED",
        "INSUFFICIENT_FUNDS",
        "RISK_VIOLATION",
    }

    def __init__(
        self,
        exchange_adapter: ExchangeAdapterProtocol,
        event_bus: EventBusProtocol,
        max_attempts: int = 3,
        initial_backoff_seconds: float = 1.0,
    ):
        """
        Initialize OrderExecutor.

        Args:
            exchange_adapter: Service for submitting orders to exchange
            event_bus: Service for publishing execution events
            max_attempts: Maximum number of retry attempts (default: 3)
            initial_backoff_seconds: Initial backoff delay in seconds (default: 1.0)
        """
        self.exchange_adapter = exchange_adapter
        self.event_bus = event_bus
        self.max_attempts = max_attempts
        self.initial_backoff_seconds = initial_backoff_seconds

    def execute_order(
        self, trader_id: str, validated_order: OrderRequest
    ) -> ExecutionResult:
        """
        Main entry point for order execution.

        Generates idempotent key and attempts submission with retry logic.

        Args:
            trader_id: ID of trader submitting order
            validated_order: Validated order request

        Returns:
            ExecutionResult with success status and details
        """
        # Generate idempotent key for deduplication
        timestamp = int(time.time() * 1000)  # Millisecond precision
        price_str = str(validated_order.price) if validated_order.price else "MARKET"
        idempotent_key = (
            f"{trader_id}:{validated_order.symbol}:"
            f"{validated_order.quantity}:{price_str}:{timestamp}:v1"
        )

        # Log execution attempt
        self.event_bus.publish(
            "orders.events",
            {
                "event": "order.execution_started",
                "trader_id": trader_id,
                "idempotent_key": idempotent_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Attempt submission with retry
        result = self.submit_to_exchange_with_retry(validated_order, idempotent_key)

        # Log execution result
        event_type = "order.executed" if result.success else "order.execution_failed"
        self.event_bus.publish(
            "orders.events",
            {
                "event": event_type,
                "trader_id": trader_id,
                "idempotent_key": idempotent_key,
                "success": result.success,
                "order_id": result.order_id,
                "retry_count": result.retry_count,
                "error": result.error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return result

    def submit_to_exchange_with_retry(
        self, order_request: OrderRequest, idempotent_key: str
    ) -> ExecutionResult:
        """
        Retry orchestrator with exponential backoff.

        Implements retry strategy:
        - Max 3 attempts with exponential backoff: 1s, 2s, 4s
        - On timeout/network error: Check exchange for duplicate first
        - Returns: ExecutionResult

        Args:
            order_request: Order request to submit
            idempotent_key: Unique key for deduplication

        Returns:
            ExecutionResult with execution details
        """
        last_error = None
        last_error_code = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                # Attempt submission
                order_status = self.submit_to_exchange(order_request, idempotent_key)

                # Success - publish recovery event if this was a retry
                if attempt > 1:
                    self.event_bus.publish(
                        "orders.events",
                        {
                            "event": "order.recovered",
                            "idempotent_key": idempotent_key,
                            "attempt": attempt,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

                return ExecutionResult(
                    success=True,
                    order_id=order_status.order_id,
                    fill_price=order_status.fill_price,
                    retry_count=attempt - 1,
                )

            except (NetworkError, TimeoutError) as e:
                last_error = str(e)
                last_error_code = (
                    ErrorCode.TIMEOUT_ERROR.value
                    if isinstance(e, TimeoutError)
                    else ErrorCode.NETWORK_ERROR.value
                )

                # Before retry, check if order was already submitted
                if attempt < self.max_attempts:
                    existing_order = self.check_exchange_for_duplicate(idempotent_key)
                    if existing_order:
                        # Order exists - return success
                        return ExecutionResult(
                            success=True,
                            order_id=existing_order.order_id,
                            fill_price=existing_order.fill_price,
                            retry_count=attempt - 1,
                        )

                    # Wait before retry with exponential backoff
                    backoff_seconds = self.initial_backoff_seconds * (2 ** (attempt - 1))
                    time.sleep(backoff_seconds)

            except ExchangeError as e:
                last_error = str(e)
                last_error_code = e.error_code

                # Check if this is a fatal error that shouldn't be retried
                if e.error_code in self.FATAL_ERROR_CODES:
                    return ExecutionResult(
                        success=False,
                        error=last_error,
                        error_code=last_error_code,
                        retry_count=attempt - 1,
                    )

                # Non-fatal exchange error - retry
                if attempt < self.max_attempts:
                    backoff_seconds = self.initial_backoff_seconds * (2 ** (attempt - 1))
                    time.sleep(backoff_seconds)

            except Exception as e:
                # Unexpected error - don't retry
                return ExecutionResult(
                    success=False,
                    error=f"Unexpected error: {str(e)}",
                    error_code=ErrorCode.UNKNOWN_ERROR.value,
                    retry_count=attempt - 1,
                )

        # All retries exhausted
        return ExecutionResult(
            success=False,
            error=f"Order execution failed after {self.max_attempts} attempts: {last_error}",
            error_code=last_error_code,
            retry_count=self.max_attempts - 1,
        )

    def check_exchange_for_duplicate(
        self, idempotent_key: str
    ) -> Optional[OrderStatus]:
        """
        Deduplication check - query exchange for existing order.

        Args:
            idempotent_key: Unique key to lookup

        Returns:
            OrderStatus if found, None if not found
        """
        try:
            return self.exchange_adapter.get_order_by_idempotent_key(idempotent_key)
        except Exception:
            # If check fails, assume order doesn't exist
            return None

    def submit_to_exchange(
        self, order_request: OrderRequest, idempotent_key: str
    ) -> OrderStatus:
        """
        Single attempt submission to exchange.

        Args:
            order_request: Order request to submit
            idempotent_key: Unique key for deduplication

        Returns:
            OrderStatus from exchange

        Raises:
            TimeoutError: If submission times out (>5s)
            NetworkError: If network connectivity fails
            ExchangeError: If exchange rejects order
        """
        return self.exchange_adapter.submit_order(order_request, idempotent_key)
