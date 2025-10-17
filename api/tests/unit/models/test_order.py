"""Unit tests for Order SQLAlchemy model."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from api.app.models.order import Order, OrderType, OrderStatus
from api.app.models.base import Base


# Test database setup
@pytest.fixture(scope="module")
def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine):
    """Create a new database session for a test."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_trader_id():
    """Generate a sample trader UUID."""
    return uuid4()


class TestOrderInstantiation:
    """Test Order model instantiation and basic field validation."""

    def test_create_valid_market_order(self, db_session: Session, sample_trader_id):
        """Test instantiation with valid market order data."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING
        )

        db_session.add(order)
        db_session.commit()

        assert order.id is not None
        assert order.trader_id == sample_trader_id
        assert order.symbol == "AAPL"
        assert order.quantity == 100
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING
        assert order.filled_quantity == 0
        assert order.price is None
        assert order.created_at is not None
        assert order.updated_at is not None

    def test_create_valid_limit_order(self, db_session: Session, sample_trader_id):
        """Test instantiation with valid limit order data."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="MSFT",
            quantity=50,
            order_type=OrderType.LIMIT,
            price=Decimal("150.50"),
            status=OrderStatus.PENDING
        )

        db_session.add(order)
        db_session.commit()

        assert order.id is not None
        assert order.price == Decimal("150.50")
        assert order.order_type == OrderType.LIMIT

    def test_create_order_with_stop_loss(self, db_session: Session, sample_trader_id):
        """Test order with stop_loss and take_profit."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="TSLA",
            quantity=25,
            order_type=OrderType.LIMIT,
            price=Decimal("200.00"),
            stop_loss=Decimal("180.00"),
            take_profit=Decimal("220.00"),
            status=OrderStatus.PENDING
        )

        db_session.add(order)
        db_session.commit()

        assert order.stop_loss == Decimal("180.00")
        assert order.take_profit == Decimal("220.00")


class TestOrderValidation:
    """Test Order model field validation and constraints."""

    def test_quantity_must_be_positive(self, db_session: Session, sample_trader_id):
        """Test that quantity > 0 constraint is enforced by validator."""
        # Model-level validation should catch this immediately
        with pytest.raises(ValueError, match="Quantity must be positive"):
            order = Order(
                trader_id=sample_trader_id,
                symbol="AAPL",
                quantity=0,  # Invalid: must be > 0
                order_type=OrderType.MARKET,
                status=OrderStatus.PENDING
            )

    def test_negative_quantity_invalid(self, db_session: Session, sample_trader_id):
        """Test that negative quantity is invalid."""
        # Model-level validation should catch this immediately
        with pytest.raises(ValueError, match="Quantity must be positive"):
            order = Order(
                trader_id=sample_trader_id,
                symbol="AAPL",
                quantity=-10,  # Invalid: must be > 0
                order_type=OrderType.MARKET,
                status=OrderStatus.PENDING
            )

    def test_filled_quantity_defaults_to_zero(self, db_session: Session, sample_trader_id):
        """Test that filled_quantity defaults to 0 after commit."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING
        )

        db_session.add(order)
        db_session.commit()

        # After commit, server_default or default should be applied
        assert order.filled_quantity == 0


class TestOrderStateTransitions:
    """Test order status state transition logic."""

    def test_update_status_pending_to_filled(self, db_session: Session, sample_trader_id):
        """Test valid state transition from PENDING to FILLED."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        db_session.commit()

        # Valid transition
        order.update_status(OrderStatus.FILLED)
        assert order.status == OrderStatus.FILLED

    def test_update_status_pending_to_partial(self, db_session: Session, sample_trader_id):
        """Test valid state transition from PENDING to PARTIAL."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        db_session.commit()

        # Valid transition
        order.update_status(OrderStatus.PARTIAL)
        assert order.status == OrderStatus.PARTIAL

    def test_update_status_filled_to_pending_invalid(self, db_session: Session, sample_trader_id):
        """Test invalid state transition from FILLED to PENDING."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED
        )
        db_session.add(order)
        db_session.commit()

        # Invalid transition: FILLED -> PENDING not allowed
        with pytest.raises(ValueError, match="Invalid status transition"):
            order.update_status(OrderStatus.PENDING)

    def test_update_status_rejected_to_pending_invalid(self, db_session: Session, sample_trader_id):
        """Test invalid state transition from REJECTED to PENDING."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.REJECTED
        )
        db_session.add(order)
        db_session.commit()

        # Invalid transition: REJECTED -> PENDING not allowed
        with pytest.raises(ValueError, match="Invalid status transition"):
            order.update_status(OrderStatus.PENDING)


class TestOrderHelperMethods:
    """Test Order model helper methods."""

    def test_is_pending_returns_true(self, db_session: Session, sample_trader_id):
        """Test is_pending() returns True for PENDING status."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING
        )

        assert order.is_pending() is True

    def test_is_pending_returns_false(self, db_session: Session, sample_trader_id):
        """Test is_pending() returns False for non-PENDING status."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED
        )

        assert order.is_pending() is False

    def test_get_unfilled_quantity_full(self, db_session: Session, sample_trader_id):
        """Test get_unfilled_quantity() with no fills."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
            filled_quantity=0
        )

        assert order.get_unfilled_quantity() == 100

    def test_get_unfilled_quantity_partial(self, db_session: Session, sample_trader_id):
        """Test get_unfilled_quantity() with partial fill."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PARTIAL,
            filled_quantity=40
        )

        assert order.get_unfilled_quantity() == 60

    def test_get_unfilled_quantity_fully_filled(self, db_session: Session, sample_trader_id):
        """Test get_unfilled_quantity() with complete fill."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            filled_quantity=100
        )

        assert order.get_unfilled_quantity() == 0

    def test_repr_method(self, db_session: Session, sample_trader_id):
        """Test __repr__() returns readable string."""
        order = Order(
            trader_id=sample_trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        db_session.commit()

        repr_str = repr(order)
        assert "Order(" in repr_str
        assert "AAPL" in repr_str
        assert "100" in repr_str
        assert str(order.id) in repr_str
