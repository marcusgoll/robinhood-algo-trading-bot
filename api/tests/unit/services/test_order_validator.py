"""Unit tests for OrderValidator service."""

import pytest
from decimal import Decimal
from uuid import uuid4
from dataclasses import dataclass
from typing import Optional

from api.app.services.order_validator import (
    OrderValidator,
    ValidationResult,
    ErrorCode,
)
from api.app.models.order import OrderType


@dataclass
class MockOrderRequest:
    """Mock order request for testing."""
    symbol: str
    quantity: int
    order_type: str
    price: Optional[Decimal] = None


@dataclass
class MockTrader:
    """Mock trader for testing."""
    id: str
    available_balance: Decimal
    daily_loss_limit: Decimal
    daily_losses: Decimal
    max_position_size: int
    current_position: int


class MockExchangeAdapter:
    """Mock exchange adapter for testing."""

    def __init__(self, price: Decimal = Decimal("150.00")):
        self._price = price

    def get_current_price(self, symbol: str) -> Decimal:
        """Return mock price."""
        return self._price


class MockTraderRepository:
    """Mock trader repository for testing."""

    def __init__(self, trader: Optional[MockTrader] = None):
        self._trader = trader

    def get_by_id(self, trader_id: str) -> Optional[MockTrader]:
        """Return mock trader."""
        return self._trader


class TestOrderValidatorSyntaxValidation:
    """Test syntax validation rules."""

    def test_valid_market_order(self):
        """Test that a valid market order passes syntax validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET.value,
            price=None
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is True
        assert result.error_code is None
        assert result.message == ""

    def test_valid_limit_order(self):
        """Test that a valid limit order passes syntax validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.LIMIT.value,
            price=Decimal("150.00")
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is True
        assert result.error_code is None

    def test_empty_symbol_fails(self):
        """Test that empty symbol fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR
        assert "symbol" in result.message.lower()
        assert "empty" in result.message.lower()

    def test_symbol_too_long_fails(self):
        """Test that symbol longer than 10 chars fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="VERYLONGSYMBOL",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR
        assert "symbol" in result.message.lower()
        assert "10 characters" in result.message.lower()

    def test_zero_quantity_fails(self):
        """Test that zero quantity fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=0,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR
        assert "quantity" in result.message.lower()
        assert "greater than 0" in result.message.lower()

    def test_negative_quantity_fails(self):
        """Test that negative quantity fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=-100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR
        assert "quantity" in result.message.lower()

    def test_invalid_order_type_fails(self):
        """Test that invalid order type fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type="INVALID"
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR
        assert "order type" in result.message.lower()
        assert "MARKET, LIMIT, STOP" in result.message

    def test_limit_order_without_price_fails(self):
        """Test that limit order without price fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.LIMIT.value,
            price=None
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR
        assert "price" in result.message.lower()
        assert "required" in result.message.lower()

    def test_stop_order_without_price_fails(self):
        """Test that stop order without price fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.STOP.value,
            price=None
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR
        assert "price" in result.message.lower()

    def test_negative_price_fails(self):
        """Test that negative price fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.LIMIT.value,
            price=Decimal("-10.00")
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR
        assert "price" in result.message.lower()
        assert "greater than 0" in result.message.lower()

    def test_zero_price_fails(self):
        """Test that zero price fails validation."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository()
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.LIMIT.value,
            price=Decimal("0.00")
        )

        # Act
        result = validator.validate_syntax(order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR


class TestOrderValidatorBalanceValidation:
    """Test balance validation rules."""

    def test_sufficient_balance_passes(self):
        """Test that order with sufficient balance passes validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("20000.00"),
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(price=Decimal("150.00")),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_balance(trader.id, order)

        # Assert
        assert result.valid is True
        assert result.error_code is None

    def test_insufficient_balance_fails(self):
        """Test that order with insufficient balance fails validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("5000.00"),
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(price=Decimal("150.00")),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,  # 100 * $150 = $15,000
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_balance(trader.id, order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.INSUFFICIENT_BALANCE
        assert "Insufficient funds" in result.message
        assert "$15,000" in result.message or "15000" in result.message
        assert "$5,000" in result.message or "5000" in result.message
        assert result.details is not None
        assert "required_balance" in result.details
        assert "available_balance" in result.details

    def test_exact_balance_passes(self):
        """Test that order with exact balance passes validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("15000.00"),
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(price=Decimal("150.00")),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,  # 100 * $150 = $15,000
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_balance(trader.id, order)

        # Assert
        assert result.valid is True

    def test_trader_not_found_fails(self):
        """Test that validation fails if trader not found."""
        # Arrange
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository(trader=None)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_balance(str(uuid4()), order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.TRADER_NOT_FOUND
        assert "trader not found" in result.message.lower()


class TestOrderValidatorRiskLimitsValidation:
    """Test risk limits validation rules."""

    def test_within_risk_limits_passes(self):
        """Test that order within risk limits passes validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("20000.00"),
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("1000.00"),
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_risk_limits(trader.id, order)

        # Assert
        assert result.valid is True
        assert result.error_code is None

    def test_exceeds_daily_loss_limit_fails(self):
        """Test that order exceeding daily loss limit fails validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("20000.00"),
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("5000.00"),  # Already at limit
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_risk_limits(trader.id, order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.RISK_VIOLATION
        assert "daily loss limit" in result.message.lower()
        assert "$5,000" in result.message or "5000" in result.message

    def test_exceeds_max_position_size_fails(self):
        """Test that order exceeding max position size fails validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("200000.00"),
            daily_loss_limit=Decimal("50000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=950
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,  # 950 + 100 = 1050 > 1000
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_risk_limits(trader.id, order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.RISK_VIOLATION
        assert "max position size" in result.message.lower()
        assert "1,000" in result.message or "1000" in result.message
        assert result.details is not None
        assert "max_position_size" in result.details
        assert "current_position" in result.details
        assert "requested_quantity" in result.details

    def test_at_max_position_size_fails(self):
        """Test that order at max position size fails validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("200000.00"),
            daily_loss_limit=Decimal("50000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=1000
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=1,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_risk_limits(trader.id, order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.RISK_VIOLATION


class TestOrderValidatorFullValidation:
    """Test full validation flow."""

    def test_valid_order_passes_all_validation(self):
        """Test that a completely valid order passes all validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("20000.00"),
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(price=Decimal("150.00")),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_order(trader.id, order)

        # Assert
        assert result.valid is True
        assert result.error_code is None
        assert result.message == ""

    def test_syntax_error_fails_early(self):
        """Test that syntax errors fail before checking balance/risk."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("20000.00"),
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="",  # Invalid
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_order(trader.id, order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.SYNTAX_ERROR

    def test_insufficient_balance_fails_after_syntax(self):
        """Test that balance check happens after syntax validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("1000.00"),  # Insufficient
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(price=Decimal("150.00")),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_order(trader.id, order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.INSUFFICIENT_BALANCE

    def test_risk_violation_fails_after_balance(self):
        """Test that risk check happens after balance validation."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("200000.00"),
            daily_loss_limit=Decimal("50000.00"),
            daily_losses=Decimal("50000.00"),  # At limit
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(price=Decimal("150.00")),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_order(trader.id, order)

        # Assert
        assert result.valid is False
        assert result.error_code == ErrorCode.RISK_VIOLATION

    def test_error_messages_are_clear_and_actionable(self):
        """Test that error messages provide clear, actionable feedback."""
        # Arrange
        trader = MockTrader(
            id=str(uuid4()),
            available_balance=Decimal("3200.00"),
            daily_loss_limit=Decimal("5000.00"),
            daily_losses=Decimal("0.00"),
            max_position_size=1000,
            current_position=0
        )
        validator = OrderValidator(
            exchange_adapter=MockExchangeAdapter(price=Decimal("150.00")),
            trader_repository=MockTraderRepository(trader=trader)
        )
        order = MockOrderRequest(
            symbol="AAPL",
            quantity=100,  # Requires $15,000
            order_type=OrderType.MARKET.value
        )

        # Act
        result = validator.validate_order(trader.id, order)

        # Assert
        assert result.valid is False
        assert "Insufficient funds" in result.message
        assert "$15,000" in result.message or "15000" in result.message
        assert "$3,200" in result.message or "3200" in result.message
