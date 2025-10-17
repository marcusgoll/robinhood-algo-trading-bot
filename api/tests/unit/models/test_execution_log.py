"""Unit tests for ExecutionLog SQLAlchemy model - immutability enforcement."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from api.app.models.execution_log import ExecutionLog, ExecutionAction, ExecutionStatus
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
def sample_order_id():
    """Generate a sample order UUID."""
    return uuid4()


@pytest.fixture
def sample_trader_id():
    """Generate a sample trader UUID."""
    return uuid4()


@pytest.fixture
def sample_order(db_session: Session, sample_trader_id, sample_order_id):
    """Create a sample order for testing."""
    order = Order(
        id=sample_order_id,
        trader_id=sample_trader_id,
        symbol="AAPL",
        quantity=100,
        order_type=OrderType.MARKET,
        status=OrderStatus.PENDING
    )
    db_session.add(order)
    db_session.commit()
    return order


class TestExecutionLogInstantiation:
    """Test ExecutionLog model instantiation and basic field validation."""

    def test_create_valid_execution_log(self, db_session: Session, sample_order, sample_trader_id):
        """Test instantiation with valid execution log data."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.SUBMITTED,
            status=ExecutionStatus.PENDING,
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.order_id == sample_order.id
        assert log.trader_id == sample_trader_id
        assert log.action == ExecutionAction.SUBMITTED.value
        assert log.status == ExecutionStatus.PENDING.value
        # SQLite doesn't preserve timezone info, so compare timestamps without timezone
        assert log.timestamp.replace(tzinfo=None) == timestamp.replace(tzinfo=None)
        assert log.reason is None
        assert log.retry_attempt is None
        assert log.error_code is None
        assert log.created_at is not None

    def test_create_log_with_all_fields(self, db_session: Session, sample_order, sample_trader_id):
        """Test instantiation with all fields populated."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.REJECTED,
            status=ExecutionStatus.REJECTED,
            timestamp=timestamp,
            reason="Insufficient funds",
            retry_attempt=2,
            error_code="INSUFFICIENT_FUNDS"
        )

        db_session.add(log)
        db_session.commit()

        assert log.action == ExecutionAction.REJECTED.value
        assert log.status == ExecutionStatus.REJECTED.value
        assert log.reason == "Insufficient funds"
        assert log.retry_attempt == 2
        assert log.error_code == "INSUFFICIENT_FUNDS"

    def test_create_log_with_nullable_status(self, db_session: Session, sample_order, sample_trader_id):
        """Test instantiation with nullable status field."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.SUBMITTED,
            status=None,  # Status can be null
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        assert log.status is None


class TestExecutionLogEnumValidation:
    """Test ExecutionLog enum field validation."""

    def test_action_enum_validation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that action enum values are validated."""
        timestamp = datetime.now(timezone.utc)

        # Valid enum
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.FILLED,
            status=ExecutionStatus.FILLED,
            timestamp=timestamp
        )
        assert log.action == ExecutionAction.FILLED.value

    def test_action_string_validation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that action string values are validated."""
        timestamp = datetime.now(timezone.utc)

        # Valid string
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action="CANCELLED",
            status=ExecutionStatus.CANCELLED,
            timestamp=timestamp
        )
        assert log.action == "CANCELLED"

    def test_invalid_action_raises_error(self, db_session: Session, sample_order, sample_trader_id):
        """Test that invalid action value raises ValueError."""
        timestamp = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Invalid action"):
            log = ExecutionLog(
                order_id=sample_order.id,
                trader_id=sample_trader_id,
                action="INVALID_ACTION",
                timestamp=timestamp
            )

    def test_status_enum_validation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that status enum values are validated."""
        timestamp = datetime.now(timezone.utc)

        # Valid enum
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.EXECUTED,
            status=ExecutionStatus.PARTIAL,
            timestamp=timestamp
        )
        assert log.status == ExecutionStatus.PARTIAL.value

    def test_invalid_status_raises_error(self, db_session: Session, sample_order, sample_trader_id):
        """Test that invalid status value raises ValueError."""
        timestamp = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Invalid status"):
            log = ExecutionLog(
                order_id=sample_order.id,
                trader_id=sample_trader_id,
                action=ExecutionAction.EXECUTED,
                status="INVALID_STATUS",
                timestamp=timestamp
            )


class TestExecutionLogImmutability:
    """Test ExecutionLog immutability enforcement - CRITICAL for SEC compliance."""

    def test_cannot_modify_action_after_creation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that modifying action after creation raises ValueError."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.SUBMITTED,
            status=ExecutionStatus.PENDING,
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        # Attempt to modify action - should raise ValueError
        with pytest.raises(ValueError, match="ExecutionLog is immutable"):
            log.action = ExecutionAction.CANCELLED

    def test_cannot_modify_status_after_creation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that modifying status after creation raises ValueError."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.SUBMITTED,
            status=ExecutionStatus.PENDING,
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        # Attempt to modify status - should raise ValueError
        with pytest.raises(ValueError, match="ExecutionLog is immutable"):
            log.status = ExecutionStatus.FILLED

    def test_cannot_modify_timestamp_after_creation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that modifying timestamp after creation raises ValueError."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.SUBMITTED,
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        # Attempt to modify timestamp - should raise ValueError
        with pytest.raises(ValueError, match="ExecutionLog is immutable"):
            log.timestamp = datetime.now(timezone.utc)

    def test_cannot_modify_reason_after_creation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that modifying reason after creation raises ValueError."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.REJECTED,
            reason="Original reason",
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        # Attempt to modify reason - should raise ValueError
        with pytest.raises(ValueError, match="ExecutionLog is immutable"):
            log.reason = "Modified reason"

    def test_cannot_modify_retry_attempt_after_creation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that modifying retry_attempt after creation raises ValueError."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.RECOVERED,
            retry_attempt=0,
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        # Attempt to modify retry_attempt - should raise ValueError
        with pytest.raises(ValueError, match="ExecutionLog is immutable"):
            log.retry_attempt = 1

    def test_cannot_modify_error_code_after_creation(self, db_session: Session, sample_order, sample_trader_id):
        """Test that modifying error_code after creation raises ValueError."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.REJECTED,
            error_code="TIMEOUT",
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        # Attempt to modify error_code - should raise ValueError
        with pytest.raises(ValueError, match="ExecutionLog is immutable"):
            log.error_code = "MODIFIED"


class TestExecutionLogHelperMethods:
    """Test ExecutionLog helper methods."""

    def test_repr_method(self, db_session: Session, sample_order, sample_trader_id):
        """Test __repr__() returns readable string."""
        timestamp = datetime(2025, 10, 17, 14, 30, 0, tzinfo=timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.FILLED,
            status=ExecutionStatus.FILLED,
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        repr_str = repr(log)
        assert "ExecutionLog(" in repr_str
        assert str(sample_order.id) in repr_str
        assert "FILLED" in repr_str
        assert "2025-10-17" in repr_str

    def test_is_immutable_returns_true(self, db_session: Session, sample_order, sample_trader_id):
        """Test is_immutable() always returns True."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.SUBMITTED,
            timestamp=timestamp
        )

        assert log.is_immutable() is True


class TestExecutionLogRelationships:
    """Test ExecutionLog relationships with Order model."""

    def test_relationship_to_order(self, db_session: Session, sample_order, sample_trader_id):
        """Test that ExecutionLog has relationship to Order."""
        timestamp = datetime.now(timezone.utc)
        log = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.SUBMITTED,
            status=ExecutionStatus.PENDING,
            timestamp=timestamp
        )

        db_session.add(log)
        db_session.commit()

        # Test relationship
        assert log.order is not None
        assert log.order.id == sample_order.id
        assert log.order.symbol == "AAPL"

    def test_multiple_logs_for_same_order(self, db_session: Session, sample_order, sample_trader_id):
        """Test that multiple ExecutionLogs can be created for same order."""
        timestamp1 = datetime.now(timezone.utc)
        log1 = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.SUBMITTED,
            status=ExecutionStatus.PENDING,
            timestamp=timestamp1
        )

        timestamp2 = datetime.now(timezone.utc)
        log2 = ExecutionLog(
            order_id=sample_order.id,
            trader_id=sample_trader_id,
            action=ExecutionAction.FILLED,
            status=ExecutionStatus.FILLED,
            timestamp=timestamp2
        )

        db_session.add(log1)
        db_session.add(log2)
        db_session.commit()

        # Query logs for order
        logs = db_session.query(ExecutionLog).filter_by(order_id=sample_order.id).all()
        assert len(logs) == 2
        assert logs[0].action in [ExecutionAction.SUBMITTED.value, ExecutionAction.FILLED.value]
        assert logs[1].action in [ExecutionAction.SUBMITTED.value, ExecutionAction.FILLED.value]
