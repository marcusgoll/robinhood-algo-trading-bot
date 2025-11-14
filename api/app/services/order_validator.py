"""
OrderValidator service for validating orders before execution.

This service enforces business rules and ensures orders meet all requirements:
- Syntax validation (symbol, quantity, price, order type)
- Balance validation (sufficient funds)
- Risk management validation (position limits, daily loss limits)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Protocol


class ErrorCode(str, Enum):
    """Error codes for validation failures."""

    SYNTAX_ERROR = "SYNTAX_ERROR"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    RISK_VIOLATION = "RISK_VIOLATION"
    TRADER_NOT_FOUND = "TRADER_NOT_FOUND"


@dataclass
class ValidationResult:
    """
    Result of order validation.

    Attributes:
        valid: Whether the order passed validation
        error_code: Error code if validation failed
        message: Human-readable error message
        details: Additional context about the error
    """

    valid: bool
    error_code: Optional[str] = None
    message: str = ""
    details: Optional[dict[str, Any]] = None


class ExchangeAdapterProtocol(Protocol):
    """Protocol for exchange adapter dependency."""

    def get_current_price(self, symbol: str) -> Decimal:
        """Get current market price for symbol."""
        ...


class TraderRepositoryProtocol(Protocol):
    """Protocol for trader repository dependency."""

    def get_by_id(self, trader_id: str) -> Optional[Any]:
        """Get trader by ID."""
        ...


class OrderValidator:
    """
    Service for validating orders before execution.

    This is a critical gate for FR-001, FR-002, FR-003 (validation requirements).
    Enforces business rules and provides clear, actionable error messages.
    """

    def __init__(
        self,
        exchange_adapter: ExchangeAdapterProtocol,
        trader_repository: TraderRepositoryProtocol,
    ):
        """
        Initialize OrderValidator.

        Args:
            exchange_adapter: Service for fetching market prices
            trader_repository: Repository for trader/account data
        """
        self.exchange_adapter = exchange_adapter
        self.trader_repository = trader_repository

    def validate_order(self, trader_id: str, order_request: Any) -> ValidationResult:
        """
        Main entry point for order validation.

        Validates in order: syntax → balance → risk limits.
        Fails fast on first error encountered.

        Args:
            trader_id: ID of trader submitting order
            order_request: Order request object with symbol, quantity, order_type, price

        Returns:
            ValidationResult with valid=True if all checks pass, or valid=False with error details
        """
        # 1. Validate syntax
        syntax_result = self.validate_syntax(order_request)
        if not syntax_result.valid:
            return syntax_result

        # 2. Validate balance
        balance_result = self.validate_balance(trader_id, order_request)
        if not balance_result.valid:
            return balance_result

        # 3. Validate risk limits
        risk_result = self.validate_risk_limits(trader_id, order_request)
        if not risk_result.valid:
            return risk_result

        return ValidationResult(valid=True)

    def validate_syntax(self, order_request: Any) -> ValidationResult:
        """
        Validate order syntax and input parameters.

        Checks:
        - Symbol: non-empty, max 10 chars
        - Quantity: > 0
        - Order type: MARKET, LIMIT, or STOP
        - Price: required for LIMIT/STOP, > 0

        Args:
            order_request: Order request object

        Returns:
            ValidationResult indicating success or syntax error
        """
        # Validate symbol
        if not order_request.symbol or order_request.symbol.strip() == "":
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.SYNTAX_ERROR,
                message="Symbol cannot be empty",
            )

        if len(order_request.symbol) > 10:
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.SYNTAX_ERROR,
                message=f"Symbol must be 10 characters or less, got {len(order_request.symbol)} characters",
            )

        # Validate quantity
        if order_request.quantity <= 0:
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.SYNTAX_ERROR,
                message=f"Quantity must be greater than 0, got {order_request.quantity}",
            )

        # Validate order type
        valid_order_types = ["MARKET", "LIMIT", "STOP"]
        if order_request.order_type not in valid_order_types:
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.SYNTAX_ERROR,
                message=f"Invalid order type '{order_request.order_type}'. Must be one of: MARKET, LIMIT, STOP",
            )

        # Validate price for LIMIT/STOP orders
        if order_request.order_type in ["LIMIT", "STOP"]:
            if order_request.price is None:
                return ValidationResult(
                    valid=False,
                    error_code=ErrorCode.SYNTAX_ERROR,
                    message=f"Price is required for {order_request.order_type} orders",
                )

            if order_request.price <= 0:
                return ValidationResult(
                    valid=False,
                    error_code=ErrorCode.SYNTAX_ERROR,
                    message=f"Price must be greater than 0, got {order_request.price}",
                )

        return ValidationResult(valid=True)

    def validate_balance(self, trader_id: str, order_request: Any) -> ValidationResult:
        """
        Validate trader has sufficient balance for order.

        Checks:
        - Trader exists
        - Available balance >= estimated order cost
        - Cost calculation: quantity × current_price

        Args:
            trader_id: ID of trader
            order_request: Order request object

        Returns:
            ValidationResult indicating success or insufficient balance error
        """
        # Get trader
        trader = self.trader_repository.get_by_id(trader_id)
        if trader is None:
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.TRADER_NOT_FOUND,
                message=f"Trader not found: {trader_id}",
            )

        # Get current market price
        current_price = self.exchange_adapter.get_current_price(order_request.symbol)

        # Calculate estimated cost
        estimated_cost = Decimal(order_request.quantity) * current_price

        # Check balance
        if trader.available_balance < estimated_cost:
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.INSUFFICIENT_BALANCE,
                message=f"Insufficient funds for ${estimated_cost:,.0f} order; available: ${trader.available_balance:,.0f}",
                details={
                    "required_balance": float(estimated_cost),
                    "available_balance": float(trader.available_balance),
                    "current_price": float(current_price),
                    "quantity": order_request.quantity,
                },
            )

        return ValidationResult(valid=True)

    def validate_risk_limits(self, trader_id: str, order_request: Any) -> ValidationResult:
        """
        Validate order doesn't violate risk management rules.

        Checks:
        - Daily loss limit not exceeded
        - Max position size not exceeded

        Args:
            trader_id: ID of trader
            order_request: Order request object

        Returns:
            ValidationResult indicating success or risk violation error
        """
        # Get trader
        trader = self.trader_repository.get_by_id(trader_id)
        if trader is None:
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.TRADER_NOT_FOUND,
                message=f"Trader not found: {trader_id}",
            )

        # Check daily loss limit
        if trader.daily_losses >= trader.daily_loss_limit:
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.RISK_VIOLATION,
                message=f"Daily loss limit of ${trader.daily_loss_limit:,.0f} has been reached. Current losses: ${trader.daily_losses:,.0f}",
                details={
                    "daily_loss_limit": float(trader.daily_loss_limit),
                    "daily_losses": float(trader.daily_losses),
                },
            )

        # Check max position size
        new_position_size = trader.current_position + order_request.quantity
        if new_position_size > trader.max_position_size:
            return ValidationResult(
                valid=False,
                error_code=ErrorCode.RISK_VIOLATION,
                message=f"Max position size of {trader.max_position_size:,} would be exceeded. Current position: {trader.current_position:,}, requested: {order_request.quantity:,}",
                details={
                    "max_position_size": trader.max_position_size,
                    "current_position": trader.current_position,
                    "requested_quantity": order_request.quantity,
                    "new_position_size": new_position_size,
                },
            )

        return ValidationResult(valid=True)
