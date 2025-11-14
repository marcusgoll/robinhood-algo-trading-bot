"""Unit tests for Fill SQLAlchemy model."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from api.app.models.fill import Fill
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
def sample_order(db_session: Session):
    """Create a sample order for testing fills."""
    trader_id = uuid4()
    order = Order(
        trader_id=trader_id,
        symbol="AAPL",
        quantity=100,
        order_type=OrderType.MARKET,
        status=OrderStatus.PENDING
    )
    db_session.add(order)
    db_session.commit()
    return order


class TestFillInstantiation:
    """Test Fill model instantiation and basic field validation."""

    def test_create_valid_fill(self, db_session: Session, sample_order):
        """Test instantiation with valid fill data."""
        fill = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
            commission=Decimal("1.00")
        )

        db_session.add(fill)
        db_session.commit()

        assert fill.id is not None
        assert fill.order_id == sample_order.id
        assert fill.quantity_filled == 50
        assert fill.price_at_fill == Decimal("150.25")
        assert fill.venue == "NYSE"
        assert fill.commission == Decimal("1.00")
        assert fill.timestamp is not None
        assert fill.created_at is not None

    def test_create_fill_with_zero_commission(self, db_session: Session, sample_order):
        """Test fill with zero commission (default)."""
        fill = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=25,
            price_at_fill=Decimal("200.00"),
            venue="NASDAQ"
        )

        db_session.add(fill)
        db_session.commit()

        assert fill.commission == Decimal("0")

    def test_create_fill_multiple_venues(self, db_session: Session, sample_order):
        """Test fills can come from different venues."""
        fill1 = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=30,
            price_at_fill=Decimal("150.00"),
            venue="NYSE"
        )
        fill2 = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=20,
            price_at_fill=Decimal("150.50"),
            venue="NASDAQ"
        )

        db_session.add_all([fill1, fill2])
        db_session.commit()

        assert fill1.venue == "NYSE"
        assert fill2.venue == "NASDAQ"


class TestFillValidation:
    """Test Fill model field validation and constraints."""

    def test_quantity_filled_must_be_positive(self, db_session: Session, sample_order):
        """Test that quantity_filled > 0 constraint is enforced."""
        with pytest.raises(ValueError, match="Quantity filled must be positive"):
            fill = Fill(
                order_id=sample_order.id,
                timestamp=datetime.now(timezone.utc),
                quantity_filled=0,  # Invalid: must be > 0
                price_at_fill=Decimal("150.00"),
                venue="NYSE"
            )

    def test_negative_quantity_filled_invalid(self, db_session: Session, sample_order):
        """Test that negative quantity_filled is invalid."""
        with pytest.raises(ValueError, match="Quantity filled must be positive"):
            fill = Fill(
                order_id=sample_order.id,
                timestamp=datetime.now(timezone.utc),
                quantity_filled=-10,  # Invalid: must be > 0
                price_at_fill=Decimal("150.00"),
                venue="NYSE"
            )

    def test_price_at_fill_must_be_positive(self, db_session: Session, sample_order):
        """Test that price_at_fill > 0 constraint is enforced."""
        with pytest.raises(ValueError, match="Price at fill must be positive"):
            fill = Fill(
                order_id=sample_order.id,
                timestamp=datetime.now(timezone.utc),
                quantity_filled=50,
                price_at_fill=Decimal("0"),  # Invalid: must be > 0
                venue="NYSE"
            )

    def test_negative_price_at_fill_invalid(self, db_session: Session, sample_order):
        """Test that negative price_at_fill is invalid."""
        with pytest.raises(ValueError, match="Price at fill must be positive"):
            fill = Fill(
                order_id=sample_order.id,
                timestamp=datetime.now(timezone.utc),
                quantity_filled=50,
                price_at_fill=Decimal("-150.00"),  # Invalid: must be > 0
                venue="NYSE"
            )

    def test_commission_must_be_non_negative(self, db_session: Session, sample_order):
        """Test that commission >= 0 constraint is enforced."""
        with pytest.raises(ValueError, match="Commission must be non-negative"):
            fill = Fill(
                order_id=sample_order.id,
                timestamp=datetime.now(timezone.utc),
                quantity_filled=50,
                price_at_fill=Decimal("150.00"),
                venue="NYSE",
                commission=Decimal("-1.00")  # Invalid: must be >= 0
            )

    def test_commission_can_be_zero(self, db_session: Session, sample_order):
        """Test that commission can be exactly zero."""
        fill = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=50,
            price_at_fill=Decimal("150.00"),
            venue="NYSE",
            commission=Decimal("0")
        )

        db_session.add(fill)
        db_session.commit()

        assert fill.commission == Decimal("0")


class TestFillHelperMethods:
    """Test Fill model helper methods."""

    def test_total_value_calculation(self, db_session: Session, sample_order):
        """Test total_value() returns quantity_filled * price_at_fill."""
        fill = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
            commission=Decimal("1.00")
        )

        db_session.add(fill)
        db_session.commit()

        expected_value = Decimal("50") * Decimal("150.25")  # 7512.50
        assert fill.total_value() == expected_value

    def test_get_net_value_calculation(self, db_session: Session, sample_order):
        """Test get_net_value() returns total_value() - commission."""
        fill = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE",
            commission=Decimal("1.00")
        )

        db_session.add(fill)
        db_session.commit()

        total_value = Decimal("50") * Decimal("150.25")  # 7512.50
        expected_net = total_value - Decimal("1.00")  # 7511.50
        assert fill.get_net_value() == expected_net

    def test_get_net_value_with_zero_commission(self, db_session: Session, sample_order):
        """Test get_net_value() equals total_value() when commission is zero."""
        fill = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=100,
            price_at_fill=Decimal("200.00"),
            venue="NASDAQ",
            commission=Decimal("0")
        )

        db_session.add(fill)
        db_session.commit()

        assert fill.get_net_value() == fill.total_value()
        assert fill.get_net_value() == Decimal("20000.00")

    def test_repr_method(self, db_session: Session, sample_order):
        """Test __repr__() returns readable string."""
        fill = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE"
        )
        db_session.add(fill)
        db_session.commit()

        repr_str = repr(fill)
        assert "Fill(" in repr_str
        assert str(sample_order.id) in repr_str
        assert "50" in repr_str
        assert "150.25" in repr_str


class TestFillRelationships:
    """Test Fill model relationships with Order."""

    def test_fill_has_order_relationship(self, db_session: Session, sample_order):
        """Test that Fill has relationship to Order model."""
        fill = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=50,
            price_at_fill=Decimal("150.25"),
            venue="NYSE"
        )

        db_session.add(fill)
        db_session.commit()

        # Access relationship
        assert fill.order is not None
        assert fill.order.id == sample_order.id
        assert fill.order.symbol == "AAPL"

    def test_order_has_fills_relationship(self, db_session: Session, sample_order):
        """Test that Order has fills relationship (back_populates)."""
        fill1 = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=30,
            price_at_fill=Decimal("150.00"),
            venue="NYSE"
        )
        fill2 = Fill(
            order_id=sample_order.id,
            timestamp=datetime.now(timezone.utc),
            quantity_filled=20,
            price_at_fill=Decimal("150.50"),
            venue="NASDAQ"
        )

        db_session.add_all([fill1, fill2])
        db_session.commit()

        # Access relationship from order
        db_session.refresh(sample_order)
        assert len(sample_order.fills) == 2
        assert fill1 in sample_order.fills
        assert fill2 in sample_order.fills
