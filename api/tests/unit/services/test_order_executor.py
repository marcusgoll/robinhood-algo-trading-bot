"""Unit tests for OrderExecutor service."""

from decimal import Decimal
from unittest.mock import Mock, MagicMock, call
import time

import pytest

from api.app.services.order_executor import (
    OrderExecutor,
    ExecutionResult,
    OrderRequest,
    OrderStatus,
    NetworkError,
    TimeoutError,
    ExchangeError,
    ErrorCode,
)


class MockExchangeAdapter:
    """Mock exchange adapter for testing."""

    def __init__(self):
        self.submit_order_called = 0
        self.get_order_by_idempotent_key_called = 0
        self.should_fail = False
        self.failure_type = None
        self.failure_count = 0
        self.existing_order = None

    def submit_order(self, order_request: OrderRequest, idempotent_key: str) -> OrderStatus:
        """Mock submit_order method."""
        self.submit_order_called += 1

        if self.should_fail and self.submit_order_called <= self.failure_count:
            if self.failure_type == "timeout":
                raise TimeoutError("Request timed out")
            elif self.failure_type == "network":
                raise NetworkError("Network connection failed")
            elif self.failure_type == "invalid_symbol":
                raise ExchangeError("Invalid symbol", error_code="INVALID_SYMBOL")
            elif self.failure_type == "exchange":
                raise ExchangeError("Exchange error", error_code="EXCHANGE_ERROR")

        # Success case
        return OrderStatus(
            order_id="order_123",
            status="FILLED",
            filled_quantity=order_request.quantity,
            fill_price=order_request.price or Decimal("150.00"),
        )

    def get_order_by_idempotent_key(self, idempotent_key: str) -> OrderStatus | None:
        """Mock get_order_by_idempotent_key method."""
        self.get_order_by_idempotent_key_called += 1
        return self.existing_order


class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self):
        self.published_events = []

    def publish(self, channel: str, event: dict) -> None:
        """Mock publish method."""
        self.published_events.append({"channel": channel, "event": event})


@pytest.fixture
def mock_exchange_adapter():
    """Fixture providing mock exchange adapter."""
    return MockExchangeAdapter()


@pytest.fixture
def mock_event_bus():
    """Fixture providing mock event bus."""
    return MockEventBus()


@pytest.fixture
def order_executor(mock_exchange_adapter, mock_event_bus):
    """Fixture providing OrderExecutor instance."""
    return OrderExecutor(
        exchange_adapter=mock_exchange_adapter,
        event_bus=mock_event_bus,
        max_attempts=3,
        initial_backoff_seconds=0.1,  # Short backoff for testing
    )


class TestExecuteOrder:
    """Tests for execute_order method."""

    def test_execute_order_success(self, order_executor, mock_exchange_adapter, mock_event_bus):
        """Test successful order execution on first attempt."""
        # Arrange
        trader_id = "trader_123"
        order_request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            order_type="MARKET",
            price=None,
        )

        # Act
        result = order_executor.execute_order(trader_id, order_request)

        # Assert
        assert result.success is True
        assert result.order_id == "order_123"
        assert result.fill_price == Decimal("150.00")
        assert result.retry_count == 0
        assert result.error == ""

        # Verify exchange adapter was called once
        assert mock_exchange_adapter.submit_order_called == 1

        # Verify events were published
        assert len(mock_event_bus.published_events) == 2
        assert mock_event_bus.published_events[0]["event"]["event"] == "order.execution_started"
        assert mock_event_bus.published_events[1]["event"]["event"] == "order.executed"
        assert mock_event_bus.published_events[1]["event"]["success"] is True

    def test_execute_order_with_limit_price(self, order_executor, mock_exchange_adapter):
        """Test order execution with limit price."""
        # Arrange
        trader_id = "trader_456"
        order_request = OrderRequest(
            symbol="MSFT",
            quantity=50,
            order_type="LIMIT",
            price=Decimal("250.00"),
        )

        # Act
        result = order_executor.execute_order(trader_id, order_request)

        # Assert
        assert result.success is True
        assert result.order_id == "order_123"
        assert result.fill_price == Decimal("250.00")
        assert result.retry_count == 0

    def test_idempotent_key_generation(self, order_executor, mock_event_bus):
        """Test that idempotent key is generated correctly."""
        # Arrange
        trader_id = "trader_789"
        order_request = OrderRequest(
            symbol="GOOGL",
            quantity=25,
            order_type="LIMIT",
            price=Decimal("2500.00"),
        )

        # Act
        order_executor.execute_order(trader_id, order_request)

        # Assert
        start_event = mock_event_bus.published_events[0]["event"]
        idempotent_key = start_event["idempotent_key"]

        # Verify key format: {trader_id}:{symbol}:{quantity}:{price}:{timestamp}:v1
        parts = idempotent_key.split(":")
        assert parts[0] == trader_id
        assert parts[1] == "GOOGL"
        assert parts[2] == "25"
        assert parts[3] == "2500.00"
        assert parts[5] == "v1"


class TestSubmitToExchangeWithRetry:
    """Tests for submit_to_exchange_with_retry method."""

    def test_retry_on_timeout_success_on_second_attempt(
        self, order_executor, mock_exchange_adapter, mock_event_bus
    ):
        """Test retry succeeds on second attempt after timeout."""
        # Arrange
        mock_exchange_adapter.should_fail = True
        mock_exchange_adapter.failure_type = "timeout"
        mock_exchange_adapter.failure_count = 1  # Fail first attempt, succeed second

        order_request = OrderRequest(
            symbol="TSLA",
            quantity=10,
            order_type="MARKET",
        )

        # Act
        result = order_executor.submit_to_exchange_with_retry(
            order_request, "test_key"
        )

        # Assert
        assert result.success is True
        assert result.order_id == "order_123"
        assert result.retry_count == 1
        assert mock_exchange_adapter.submit_order_called == 2

        # Verify recovery event published
        recovery_events = [
            e for e in mock_event_bus.published_events
            if e["event"]["event"] == "order.recovered"
        ]
        assert len(recovery_events) == 1
        assert recovery_events[0]["event"]["attempt"] == 2

    def test_retry_on_network_error_success_on_third_attempt(
        self, order_executor, mock_exchange_adapter
    ):
        """Test retry succeeds on third attempt after network errors."""
        # Arrange
        mock_exchange_adapter.should_fail = True
        mock_exchange_adapter.failure_type = "network"
        mock_exchange_adapter.failure_count = 2  # Fail first 2 attempts

        order_request = OrderRequest(
            symbol="NVDA",
            quantity=20,
            order_type="MARKET",
        )

        # Act
        result = order_executor.submit_to_exchange_with_retry(
            order_request, "test_key"
        )

        # Assert
        assert result.success is True
        assert result.retry_count == 2
        assert mock_exchange_adapter.submit_order_called == 3

    def test_all_retries_exhausted(self, order_executor, mock_exchange_adapter):
        """Test failure when all retry attempts are exhausted."""
        # Arrange
        mock_exchange_adapter.should_fail = True
        mock_exchange_adapter.failure_type = "timeout"
        mock_exchange_adapter.failure_count = 3  # Fail all attempts

        order_request = OrderRequest(
            symbol="AMD",
            quantity=15,
            order_type="MARKET",
        )

        # Act
        result = order_executor.submit_to_exchange_with_retry(
            order_request, "test_key"
        )

        # Assert
        assert result.success is False
        assert result.error.startswith("Order execution failed after 3 attempts")
        assert result.error_code == ErrorCode.TIMEOUT_ERROR.value
        assert result.retry_count == 2
        assert mock_exchange_adapter.submit_order_called == 3

    def test_fatal_error_no_retry(self, order_executor, mock_exchange_adapter):
        """Test that fatal errors (invalid symbol) are not retried."""
        # Arrange
        mock_exchange_adapter.should_fail = True
        mock_exchange_adapter.failure_type = "invalid_symbol"
        mock_exchange_adapter.failure_count = 3

        order_request = OrderRequest(
            symbol="INVALID",
            quantity=10,
            order_type="MARKET",
        )

        # Act
        result = order_executor.submit_to_exchange_with_retry(
            order_request, "test_key"
        )

        # Assert
        assert result.success is False
        assert result.error == "Invalid symbol"
        assert result.error_code == "INVALID_SYMBOL"
        assert result.retry_count == 0
        assert mock_exchange_adapter.submit_order_called == 1  # Only one attempt

    def test_exponential_backoff_timing(self, order_executor, mock_exchange_adapter, monkeypatch):
        """Test that exponential backoff increases wait time correctly."""
        # Arrange
        mock_exchange_adapter.should_fail = True
        mock_exchange_adapter.failure_type = "network"
        mock_exchange_adapter.failure_count = 2

        sleep_calls = []

        def mock_sleep(seconds):
            sleep_calls.append(seconds)

        monkeypatch.setattr(time, "sleep", mock_sleep)

        order_request = OrderRequest(
            symbol="INTC",
            quantity=30,
            order_type="MARKET",
        )

        # Act
        order_executor.submit_to_exchange_with_retry(order_request, "test_key")

        # Assert - Verify backoff times: 0.1s, 0.2s
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 0.1  # 1st retry: initial_backoff * 2^0
        assert sleep_calls[1] == 0.2  # 2nd retry: initial_backoff * 2^1


class TestCheckExchangeForDuplicate:
    """Tests for check_exchange_for_duplicate method."""

    def test_duplicate_order_found(self, order_executor, mock_exchange_adapter):
        """Test finding duplicate order on exchange."""
        # Arrange
        mock_exchange_adapter.existing_order = OrderStatus(
            order_id="existing_order_456",
            status="FILLED",
            filled_quantity=100,
            fill_price=Decimal("145.00"),
        )

        # Act
        result = order_executor.check_exchange_for_duplicate("idempotent_key_123")

        # Assert
        assert result is not None
        assert result.order_id == "existing_order_456"
        assert result.status == "FILLED"
        assert mock_exchange_adapter.get_order_by_idempotent_key_called == 1

    def test_no_duplicate_order_found(self, order_executor, mock_exchange_adapter):
        """Test when no duplicate order exists."""
        # Arrange
        mock_exchange_adapter.existing_order = None

        # Act
        result = order_executor.check_exchange_for_duplicate("idempotent_key_789")

        # Assert
        assert result is None
        assert mock_exchange_adapter.get_order_by_idempotent_key_called == 1

    def test_check_fails_returns_none(self, order_executor, mock_exchange_adapter):
        """Test that check failure returns None (assumes no duplicate)."""
        # Arrange
        def raise_error(key):
            raise Exception("API error")

        mock_exchange_adapter.get_order_by_idempotent_key = raise_error

        # Act
        result = order_executor.check_exchange_for_duplicate("key")

        # Assert
        assert result is None  # Failure assumed to mean no duplicate


class TestDuplicatePrevention:
    """Integration tests for duplicate order prevention."""

    def test_timeout_then_duplicate_found_no_resubmit(
        self, order_executor, mock_exchange_adapter
    ):
        """Test that duplicate check prevents resubmission after timeout."""
        # Arrange
        mock_exchange_adapter.should_fail = True
        mock_exchange_adapter.failure_type = "timeout"
        mock_exchange_adapter.failure_count = 1

        # Simulate order was actually created despite timeout
        mock_exchange_adapter.existing_order = OrderStatus(
            order_id="already_created_789",
            status="FILLED",
            filled_quantity=50,
            fill_price=Decimal("155.00"),
        )

        order_request = OrderRequest(
            symbol="META",
            quantity=50,
            order_type="MARKET",
        )

        # Act
        result = order_executor.submit_to_exchange_with_retry(
            order_request, "test_key"
        )

        # Assert
        assert result.success is True
        assert result.order_id == "already_created_789"
        assert result.fill_price == Decimal("155.00")

        # Verify only 1 submit attempt (timeout), then duplicate check
        assert mock_exchange_adapter.submit_order_called == 1
        assert mock_exchange_adapter.get_order_by_idempotent_key_called == 1

    def test_multiple_timeouts_multiple_duplicate_checks(
        self, order_executor, mock_exchange_adapter
    ):
        """Test that duplicate check is performed before each retry."""
        # Arrange
        mock_exchange_adapter.should_fail = True
        mock_exchange_adapter.failure_type = "timeout"
        mock_exchange_adapter.failure_count = 2

        order_request = OrderRequest(
            symbol="AMZN",
            quantity=5,
            order_type="MARKET",
        )

        # Act
        result = order_executor.submit_to_exchange_with_retry(
            order_request, "test_key"
        )

        # Assert
        assert result.success is True

        # Verify 3 submit attempts and 2 duplicate checks (before retry 2 and 3)
        assert mock_exchange_adapter.submit_order_called == 3
        assert mock_exchange_adapter.get_order_by_idempotent_key_called == 2


class TestSubmitToExchange:
    """Tests for submit_to_exchange method."""

    def test_submit_delegates_to_adapter(self, order_executor, mock_exchange_adapter):
        """Test that submit_to_exchange delegates to exchange adapter."""
        # Arrange
        order_request = OrderRequest(
            symbol="NFLX",
            quantity=8,
            order_type="LIMIT",
            price=Decimal("400.00"),
        )

        # Act
        result = order_executor.submit_to_exchange(order_request, "key_123")

        # Assert
        assert result.order_id == "order_123"
        assert result.status == "FILLED"
        assert mock_exchange_adapter.submit_order_called == 1
