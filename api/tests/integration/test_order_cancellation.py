"""Integration tests for POST /api/v1/orders/{order_id}/cancel endpoint."""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.app.main import app
from api.app.models.order import Order, OrderStatus, OrderType
from api.app.models.execution_log import ExecutionLog, ExecutionAction
from api.app.models.fill import Fill  # Import all models first
from api.app.models.base import Base  # Import Base after models
from api.app.core.database import get_db


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create a test database session."""
    # Force models to be registered with Base.metadata by importing them
    # This ensures Base.metadata.tables is populated
    from api.app.models import Order as _Order, Fill as _Fill, ExecutionLog as _ExecutionLog  # noqa: F401

    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
        session.commit()  # Commit any pending changes
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Create a test client with test database."""

    def override_get_db() -> Session:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def trader_id() -> uuid.UUID:
    """Generate a test trader ID."""
    return uuid.uuid4()


@pytest.fixture
def pending_order(db_session: Session, trader_id: uuid.UUID) -> Order:
    """Create a PENDING order in the database."""
    # Import again to ensure models are registered for this fixture execution
    from api.app.models import Order as OrderModel

    order = OrderModel(
        trader_id=trader_id,
        symbol="AAPL",
        quantity=100,
        order_type=OrderType.MARKET,
        price=None,
        status=OrderStatus.PENDING,
        filled_quantity=0,
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def filled_order(db_session: Session, trader_id: uuid.UUID) -> Order:
    """Create a FILLED order in the database."""
    order = Order(
        trader_id=trader_id,
        symbol="MSFT",
        quantity=50,
        order_type=OrderType.LIMIT,
        price=Decimal("300.00"),
        status=OrderStatus.FILLED,
        filled_quantity=50,
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def cancelled_order(db_session: Session, trader_id: uuid.UUID) -> Order:
    """Create a CANCELLED order in the database."""
    order = Order(
        trader_id=trader_id,
        symbol="TSLA",
        quantity=25,
        order_type=OrderType.MARKET,
        price=None,
        status=OrderStatus.CANCELLED,
        filled_quantity=0,
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


class TestOrderCancellation:
    """Integration tests for order cancellation endpoint."""

    def test_cancel_pending_order_success(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
        pending_order: Order,
    ) -> None:
        """Test successful cancellation of a PENDING order."""
        order_id = pending_order.id

        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(order_id)
        assert data["status"] == "CANCELLED"
        assert data["symbol"] == "AAPL"
        assert data["quantity"] == 100

        # Verify database updated
        db_session.expire(pending_order)
        db_session.refresh(pending_order)
        assert pending_order.status == OrderStatus.CANCELLED.value

    def test_cancel_filled_order_error(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        filled_order: Order,
    ) -> None:
        """Test that cancelling a FILLED order returns 400 error."""
        order_id = filled_order.id

        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "CANNOT_CANCEL"
        assert "FILLED" in data["message"]
        assert "PENDING" in data["message"]
        assert data["current_status"] == "FILLED"

    def test_cancel_cancelled_order_error(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        cancelled_order: Order,
    ) -> None:
        """Test that cancelling an already CANCELLED order returns 400 error."""
        order_id = cancelled_order.id

        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "CANNOT_CANCEL"
        assert "CANCELLED" in data["message"]

    def test_cancel_nonexistent_order_error(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
    ) -> None:
        """Test that cancelling a non-existent order returns 404 error."""
        fake_order_id = uuid.uuid4()

        response = client.post(
            f"/api/v1/orders/{fake_order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"

    def test_cancel_other_trader_order_error(
        self,
        client: TestClient,
        pending_order: Order,
    ) -> None:
        """Test that cancelling another trader's order returns 404 error (security)."""
        other_trader_id = uuid.uuid4()
        order_id = pending_order.id

        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {other_trader_id}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"

    def test_cancel_order_missing_auth(
        self,
        client: TestClient,
        pending_order: Order,
    ) -> None:
        """Test that cancelling without authentication returns 401 error."""
        order_id = pending_order.id

        response = client.post(f"/api/v1/orders/{order_id}/cancel")

        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"]

    def test_cancel_order_invalid_token(
        self,
        client: TestClient,
        pending_order: Order,
    ) -> None:
        """Test that cancelling with invalid token returns 401 error."""
        order_id = pending_order.id

        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    def test_execution_log_created_on_cancel(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
        pending_order: Order,
    ) -> None:
        """Test that execution log entry is created with action=CANCELLED."""
        order_id = pending_order.id

        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 200

        # Verify execution log exists
        log = (
            db_session.query(ExecutionLog)
            .filter_by(
                order_id=order_id,
                action=ExecutionAction.CANCELLED.value,
            )
            .first()
        )
        assert log is not None
        assert log.action == ExecutionAction.CANCELLED.value
        assert log.trader_id == trader_id
        assert log.status == OrderStatus.CANCELLED.value
        assert "PENDING to CANCELLED" in log.reason

    def test_event_published_on_cancel(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        pending_order: Order,
    ) -> None:
        """Test that order.cancelled event is published."""
        order_id = pending_order.id

        with patch("api.app.routes.orders.event_bus") as mock_event_bus:
            response = client.post(
                f"/api/v1/orders/{order_id}/cancel",
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 200

            # Verify event was published
            mock_event_bus.publish_order_cancelled.assert_called_once()
            call_args = mock_event_bus.publish_order_cancelled.call_args
            assert call_args[1]["order_id"] == order_id
            assert call_args[1]["trader_id"] == trader_id
            assert call_args[1]["symbol"] == "AAPL"

    def test_cancel_order_latency(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        pending_order: Order,
    ) -> None:
        """Test that order cancellation completes within 500ms latency requirement."""
        order_id = pending_order.id

        start_time = time.perf_counter()

        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        assert response.status_code == 200
        assert latency_ms < 500, f"Latency {latency_ms:.2f}ms exceeds 500ms requirement"

    def test_cancel_order_idempotency(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        pending_order: Order,
    ) -> None:
        """Test that cancelling an already cancelled order is handled gracefully."""
        order_id = pending_order.id

        # First cancellation
        response1 = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )
        assert response1.status_code == 200

        # Second cancellation attempt
        response2 = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )
        assert response2.status_code == 400
        assert "CANCELLED" in response2.json()["message"]

    def test_cancel_multiple_pending_orders(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
    ) -> None:
        """Test cancelling multiple pending orders."""
        # Create multiple pending orders
        orders = []
        for i in range(3):
            order = Order(
                trader_id=trader_id,
                symbol=f"SYM{i}",
                quantity=100,
                order_type=OrderType.MARKET,
                price=None,
                status=OrderStatus.PENDING,
                filled_quantity=0,
            )
            db_session.add(order)
            orders.append(order)

        db_session.commit()

        # Cancel each order
        for order in orders:
            db_session.refresh(order)
            response = client.post(
                f"/api/v1/orders/{order.id}/cancel",
                headers={"Authorization": f"Bearer {trader_id}"},
            )
            assert response.status_code == 200

        # Verify all are cancelled
        for order in orders:
            db_session.expire(order)
            db_session.refresh(order)
            assert order.status == OrderStatus.CANCELLED.value

    def test_cancel_order_returns_updated_timestamp(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
        pending_order: Order,
    ) -> None:
        """Test that cancelled order returns updated updated_at timestamp."""
        order_id = pending_order.id
        original_updated_at = pending_order.updated_at

        response = client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data

        # Note: We don't include updated_at in OrderResponse schema by default,
        # but it's updated in the database
        # Verify in database
        from sqlalchemy import select

        updated_order = db_session.execute(
            select(Order).where(Order.id == order_id)
        ).scalar_one()
        assert updated_order.updated_at > original_updated_at

    def test_partial_order_cannot_be_cancelled(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
    ) -> None:
        """Test that PARTIAL orders cannot be cancelled (business rule)."""
        # Create a PARTIAL order
        order = Order(
            trader_id=trader_id,
            symbol="GOOGL",
            quantity=100,
            order_type=OrderType.LIMIT,
            price=Decimal("2800.00"),
            status=OrderStatus.PARTIAL,
            filled_quantity=50,
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)

        response = client.post(
            f"/api/v1/orders/{order.id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "CANNOT_CANCEL"
        assert "PARTIAL" in data["message"]

    def test_rejected_order_cannot_be_cancelled(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
    ) -> None:
        """Test that REJECTED orders cannot be cancelled."""
        # Create a REJECTED order
        order = Order(
            trader_id=trader_id,
            symbol="AMZN",
            quantity=10,
            order_type=OrderType.MARKET,
            price=None,
            status=OrderStatus.REJECTED,
            filled_quantity=0,
        )
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)

        response = client.post(
            f"/api/v1/orders/{order.id}/cancel",
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "CANNOT_CANCEL"
        assert "REJECTED" in data["message"]
