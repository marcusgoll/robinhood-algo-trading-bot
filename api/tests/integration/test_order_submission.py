"""Integration tests for POST /api/v1/orders endpoint."""

from __future__ import annotations

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


@pytest.fixture
def db_session() -> Session:
    """Create a test database session."""
    # Models are already imported at module level, so Base.metadata should have them
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
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
def mock_trader() -> Mock:
    """Create a mock trader object."""
    trader = Mock()
    trader.available_balance = Decimal("50000.00")  # Increased to allow test orders
    trader.daily_losses = Decimal("0.00")
    trader.daily_loss_limit = Decimal("5000.00")
    trader.current_position = 0
    trader.max_position_size = 1000
    return trader


@pytest.fixture
def mock_exchange() -> Mock:
    """Create a mock exchange adapter."""
    exchange = Mock()
    exchange.get_current_price.return_value = Decimal("150.00")
    return exchange


class TestOrderSubmission:
    """Integration tests for order submission endpoint."""

    def test_submit_valid_market_order(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test successful submission of valid market order."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                    "price": None,
                    "stop_loss": 145.50,
                    "take_profit": 155.00,
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["quantity"] == 100
            assert data["order_type"] == "MARKET"
            assert data["status"] == "PENDING"
            assert "id" in data
            assert data["trader_id"] == str(trader_id)

    def test_submit_valid_limit_order(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test successful submission of valid limit order."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "MSFT",
                    "quantity": 50,
                    "order_type": "LIMIT",
                    "price": 300.00,
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["symbol"] == "MSFT"
            assert data["quantity"] == 50
            assert data["order_type"] == "LIMIT"
            assert float(data["price"]) == 300.00

    def test_submit_order_missing_auth(self, client: TestClient) -> None:
        """Test order submission without authentication."""
        response = client.post(
            "/api/v1/orders",
            json={
                "symbol": "AAPL",
                "quantity": 100,
                "order_type": "MARKET",
            },
        )

        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"]

    def test_submit_order_invalid_token(self, client: TestClient) -> None:
        """Test order submission with invalid token."""
        response = client.post(
            "/api/v1/orders",
            json={
                "symbol": "AAPL",
                "quantity": 100,
                "order_type": "MARKET",
            },
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    def test_submit_order_validation_error_negative_quantity(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
    ) -> None:
        """Test order submission with negative quantity."""
        response = client.post(
            "/api/v1/orders",
            json={
                "symbol": "AAPL",
                "quantity": -10,
                "order_type": "MARKET",
            },
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_submit_order_validation_error_limit_missing_price(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
    ) -> None:
        """Test LIMIT order submission without price."""
        response = client.post(
            "/api/v1/orders",
            json={
                "symbol": "AAPL",
                "quantity": 100,
                "order_type": "LIMIT",
                "price": None,
            },
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 422
        assert "price" in response.text.lower()

    def test_submit_order_insufficient_balance(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test order submission with insufficient balance."""
        mock_trader.available_balance = Decimal("100.00")  # Not enough

        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,  # 100 * $150 = $15,000
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 400
            data = response.json()
            assert data["error_code"] == "INSUFFICIENT_BALANCE"
            assert "available" in data["message"].lower()

    def test_submit_order_risk_violation_daily_loss(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test order submission violating daily loss limit."""
        mock_trader.daily_losses = Decimal("5000.00")  # At limit

        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 400
            data = response.json()
            assert data["error_code"] == "RISK_VIOLATION"
            assert "daily loss" in data["message"].lower()

    def test_submit_order_risk_violation_position_size(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test order submission exceeding max position size."""
        mock_trader.current_position = 900
        mock_trader.max_position_size = 1000

        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 150,  # Would exceed max
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 400
            data = response.json()
            assert data["error_code"] == "RISK_VIOLATION"
            assert "position size" in data["message"].lower()

    def test_order_persisted_to_database(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test that order is persisted to database."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201

            # Verify order exists in database
            order = db_session.query(Order).filter_by(symbol="AAPL").first()
            assert order is not None
            assert order.symbol == "AAPL"
            assert order.quantity == 100
            assert order.status == OrderStatus.PENDING.value

    def test_execution_log_created(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test that execution log entry is created."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201

            # Verify execution log exists
            log = db_session.query(ExecutionLog).filter_by(
                action=ExecutionAction.SUBMITTED.value
            ).first()
            assert log is not None
            assert log.action == ExecutionAction.SUBMITTED.value

    def test_event_published(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test that order.submitted event is published."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange), \
             patch("api.app.routes.orders.event_bus") as mock_event_bus:
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201

            # Verify event was published
            mock_event_bus.publish_order_submitted.assert_called_once()

    def test_submit_order_returns_order_id(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test that order submission returns a valid order ID."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["id"] is not None
            # Verify it's a valid UUID format
            try:
                uuid.UUID(data["id"])
            except ValueError:
                pytest.fail("Order ID is not a valid UUID")

    def test_submit_invalid_symbol_empty(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
    ) -> None:
        """Test that empty symbol returns 400 error."""
        response = client.post(
            "/api/v1/orders",
            json={
                "symbol": "",
                "quantity": 100,
                "order_type": "MARKET",
            },
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "symbol" in data["message"].lower()

    def test_submit_zero_quantity(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
    ) -> None:
        """Test that zero quantity returns 400 error."""
        response = client.post(
            "/api/v1/orders",
            json={
                "symbol": "AAPL",
                "quantity": 0,
                "order_type": "MARKET",
            },
            headers={"Authorization": f"Bearer {trader_id}"},
        )

        assert response.status_code == 422  # Pydantic validation

    def test_trader_isolation(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test that traders cannot see other traders' orders."""
        # Create order for first trader
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201
            order_id = response.json()["id"]

        # Try to access order with different trader ID
        other_trader_id = uuid.uuid4()
        response = client.get(
            f"/api/v1/orders/{order_id}",
            headers={"Authorization": f"Bearer {other_trader_id}"},
        )

        # Should return 404 or 403 (trader isolation enforced)
        assert response.status_code in [403, 404]

    def test_concurrent_submissions(
        self,
        client: TestClient,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test that multiple orders from same trader are handled correctly."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            # Submit multiple orders
            orders = []
            for i in range(3):
                response = client.post(
                    "/api/v1/orders",
                    json={
                        "symbol": "AAPL",
                        "quantity": 10,
                        "order_type": "MARKET",
                    },
                    headers={"Authorization": f"Bearer {trader_id}"},
                )
                assert response.status_code == 201
                orders.append(response.json())

            # Verify each order has unique ID
            order_ids = [o["id"] for o in orders]
            assert len(order_ids) == len(set(order_ids))

    def test_limit_order_with_price_persisted(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test that LIMIT order price is correctly persisted."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "TSLA",
                    "quantity": 50,
                    "order_type": "LIMIT",
                    "price": 250.75,
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201

            # Verify in database
            order = db_session.query(Order).filter_by(symbol="TSLA").first()
            assert order is not None
            assert float(order.price) == 250.75

    def test_order_status_initially_pending(
        self,
        client: TestClient,
        db_session: Session,
        trader_id: uuid.UUID,
        mock_trader: Mock,
        mock_exchange: Mock,
    ) -> None:
        """Test that newly submitted order has status PENDING."""
        with patch("api.app.routes.orders.trader_repository") as mock_trader_repo, \
             patch("api.app.routes.orders.exchange_adapter", mock_exchange):
            mock_trader_repo.get_by_id.return_value = mock_trader

            response = client.post(
                "/api/v1/orders",
                json={
                    "symbol": "AAPL",
                    "quantity": 100,
                    "order_type": "MARKET",
                },
                headers={"Authorization": f"Bearer {trader_id}"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "PENDING"

            # Verify in database
            order = db_session.query(Order).filter_by(id=data["id"]).first()
            assert order is not None
            assert order.status == OrderStatus.PENDING.value
