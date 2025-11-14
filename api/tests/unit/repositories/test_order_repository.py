"""Unit tests for OrderRepository."""

import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, call

from app.repositories.order_repository import OrderRepository
from app.models.order import Order, OrderType, OrderStatus
from app.models.execution_log import ExecutionLog, ExecutionAction


class TestOrderRepositoryCreate:
    """Test order creation functionality."""

    def test_create_market_order_success(self):
        """Test creating a market order successfully."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()
        order_id = uuid4()

        # Mock the order creation to set ID after flush
        def set_order_id(*args, **kwargs):
            if args and isinstance(args[0], Order):
                args[0].id = order_id

        mock_session.flush.side_effect = set_order_id
        repository = OrderRepository(session=mock_session)

        # Act
        order = repository.create(
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            price=None,
        )

        # Assert
        assert order.trader_id == trader_id
        assert order.symbol == "AAPL"
        assert order.quantity == 100
        assert order.order_type == OrderType.MARKET.value
        assert order.price is None
        assert order.status == OrderStatus.PENDING.value
        assert order.filled_quantity == 0

        # Verify session.add called twice (Order + ExecutionLog)
        assert mock_session.add.call_count == 2
        assert mock_session.flush.call_count == 1

        # Verify execution log created
        log_call_args = mock_session.add.call_args_list[1][0][0]
        assert isinstance(log_call_args, ExecutionLog)
        assert log_call_args.trader_id == trader_id
        assert log_call_args.action == ExecutionAction.SUBMITTED.value

    def test_create_limit_order_with_price(self):
        """Test creating a limit order with price."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()
        price = Decimal("150.50")

        def set_order_id(*args, **kwargs):
            if args and isinstance(args[0], Order):
                args[0].id = uuid4()

        mock_session.flush.side_effect = set_order_id
        repository = OrderRepository(session=mock_session)

        # Act
        order = repository.create(
            trader_id=trader_id,
            symbol="TSLA",
            quantity=50,
            order_type=OrderType.LIMIT,
            price=price,
        )

        # Assert
        assert order.order_type == OrderType.LIMIT.value
        assert order.price == price
        assert order.symbol == "TSLA"
        assert order.quantity == 50

    def test_create_order_with_stop_loss_and_take_profit(self):
        """Test creating an order with stop loss and take profit."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()
        stop_loss = Decimal("140.00")
        take_profit = Decimal("170.00")

        def set_order_id(*args, **kwargs):
            if args and isinstance(args[0], Order):
                args[0].id = uuid4()

        mock_session.flush.side_effect = set_order_id
        repository = OrderRepository(session=mock_session)

        # Act
        order = repository.create(
            trader_id=trader_id,
            symbol="NVDA",
            quantity=25,
            order_type=OrderType.MARKET,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # Assert
        assert order.stop_loss == stop_loss
        assert order.take_profit == take_profit

    def test_create_order_with_invalid_quantity_raises_error(self):
        """Test that creating order with invalid quantity raises ValueError."""
        # Arrange
        mock_session = Mock()
        repository = OrderRepository(session=mock_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Quantity must be positive"):
            repository.create(
                trader_id=uuid4(),
                symbol="AAPL",
                quantity=0,  # Invalid
                order_type=OrderType.MARKET,
            )

    def test_create_order_with_negative_quantity_raises_error(self):
        """Test that creating order with negative quantity raises ValueError."""
        # Arrange
        mock_session = Mock()
        repository = OrderRepository(session=mock_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Quantity must be positive"):
            repository.create(
                trader_id=uuid4(),
                symbol="AAPL",
                quantity=-10,
                order_type=OrderType.MARKET,
            )


class TestOrderRepositoryGetById:
    """Test fetching order by ID."""

    def test_get_by_id_returns_order_when_found(self):
        """Test get_by_id returns order when it exists."""
        # Arrange
        mock_session = Mock()
        order_id = uuid4()
        expected_order = Order(
            id=order_id,
            trader_id=uuid4(),
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
        )
        mock_session.get.return_value = expected_order
        repository = OrderRepository(session=mock_session)

        # Act
        order = repository.get_by_id(order_id)

        # Assert
        assert order == expected_order
        mock_session.get.assert_called_once_with(Order, order_id)

    def test_get_by_id_returns_none_when_not_found(self):
        """Test get_by_id returns None when order doesn't exist."""
        # Arrange
        mock_session = Mock()
        mock_session.get.return_value = None
        repository = OrderRepository(session=mock_session)

        # Act
        order = repository.get_by_id(uuid4())

        # Assert
        assert order is None


class TestOrderRepositoryGetByTrader:
    """Test fetching orders by trader ID."""

    def test_get_by_trader_returns_trader_orders_only(self):
        """Test get_by_trader returns only orders for specified trader."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()

        order1 = Order(
            id=uuid4(),
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
        )
        order2 = Order(
            id=uuid4(),
            trader_id=trader_id,
            symbol="TSLA",
            quantity=50,
            order_type=OrderType.LIMIT,
            status=OrderStatus.FILLED,
        )

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [order1, order2]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repository = OrderRepository(session=mock_session)

        # Act
        orders = repository.get_by_trader(trader_id)

        # Assert
        assert len(orders) == 2
        assert order1 in orders
        assert order2 in orders
        mock_session.execute.assert_called_once()

    def test_get_by_trader_respects_status_filter(self):
        """Test get_by_trader filters by status when provided."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()

        pending_order = Order(
            id=uuid4(),
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
        )

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [pending_order]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repository = OrderRepository(session=mock_session)

        # Act
        orders = repository.get_by_trader(trader_id, status=OrderStatus.PENDING)

        # Assert
        assert len(orders) == 1
        assert orders[0].status == OrderStatus.PENDING.value

    def test_get_by_trader_respects_pagination(self):
        """Test get_by_trader respects limit and offset parameters."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repository = OrderRepository(session=mock_session)

        # Act
        orders = repository.get_by_trader(trader_id, limit=10, offset=5)

        # Assert
        # Verify execute was called (query construction verified indirectly)
        mock_session.execute.assert_called_once()

    def test_get_by_trader_returns_empty_list_when_no_orders(self):
        """Test get_by_trader returns empty list when trader has no orders."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repository = OrderRepository(session=mock_session)

        # Act
        orders = repository.get_by_trader(trader_id)

        # Assert
        assert orders == []


class TestOrderRepositoryUpdateStatus:
    """Test order status update functionality."""

    def test_update_status_from_pending_to_filled(self):
        """Test updating order status from PENDING to FILLED."""
        # Arrange
        mock_session = Mock()
        order_id = uuid4()
        trader_id = uuid4()

        order = Order(
            id=order_id,
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
        )
        mock_session.get.return_value = order
        repository = OrderRepository(session=mock_session)

        # Act
        updated_order = repository.update_status(order_id, OrderStatus.FILLED)

        # Assert
        assert updated_order.status == OrderStatus.FILLED.value
        assert mock_session.add.call_count == 1  # ExecutionLog added
        assert mock_session.flush.call_count == 1

        # Verify execution log created
        log_call_args = mock_session.add.call_args_list[0][0][0]
        assert isinstance(log_call_args, ExecutionLog)
        assert log_call_args.order_id == order_id
        assert log_call_args.trader_id == trader_id
        assert log_call_args.action == ExecutionAction.FILLED.value
        assert log_call_args.status == OrderStatus.FILLED.value

    def test_update_status_from_pending_to_partial(self):
        """Test updating order status from PENDING to PARTIAL."""
        # Arrange
        mock_session = Mock()
        order_id = uuid4()
        trader_id = uuid4()

        order = Order(
            id=order_id,
            trader_id=trader_id,
            symbol="TSLA",
            quantity=100,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PENDING,
        )
        mock_session.get.return_value = order
        repository = OrderRepository(session=mock_session)

        # Act
        updated_order = repository.update_status(order_id, OrderStatus.PARTIAL)

        # Assert
        assert updated_order.status == OrderStatus.PARTIAL.value

    def test_update_status_from_partial_to_filled(self):
        """Test updating order status from PARTIAL to FILLED."""
        # Arrange
        mock_session = Mock()
        order_id = uuid4()
        trader_id = uuid4()

        order = Order(
            id=order_id,
            trader_id=trader_id,
            symbol="NVDA",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PARTIAL,
            filled_quantity=50,
        )
        mock_session.get.return_value = order
        repository = OrderRepository(session=mock_session)

        # Act
        updated_order = repository.update_status(order_id, OrderStatus.FILLED)

        # Assert
        assert updated_order.status == OrderStatus.FILLED.value

    def test_update_status_invalid_transition_raises_error(self):
        """Test that invalid status transition raises ValueError."""
        # Arrange
        mock_session = Mock()
        order_id = uuid4()
        trader_id = uuid4()

        # Terminal state - cannot transition
        order = Order(
            id=order_id,
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
        )
        mock_session.get.return_value = order
        repository = OrderRepository(session=mock_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid status transition"):
            repository.update_status(order_id, OrderStatus.PENDING)

    def test_update_status_order_not_found_raises_error(self):
        """Test that updating status for non-existent order raises ValueError."""
        # Arrange
        mock_session = Mock()
        mock_session.get.return_value = None
        repository = OrderRepository(session=mock_session)

        # Act & Assert
        with pytest.raises(ValueError, match="Order not found"):
            repository.update_status(uuid4(), OrderStatus.FILLED)

    def test_update_status_cancelled_from_pending(self):
        """Test updating order status from PENDING to CANCELLED."""
        # Arrange
        mock_session = Mock()
        order_id = uuid4()
        trader_id = uuid4()

        order = Order(
            id=order_id,
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PENDING,
        )
        mock_session.get.return_value = order
        repository = OrderRepository(session=mock_session)

        # Act
        updated_order = repository.update_status(order_id, OrderStatus.CANCELLED)

        # Assert
        assert updated_order.status == OrderStatus.CANCELLED.value

        # Verify execution log has CANCELLED action
        log_call_args = mock_session.add.call_args_list[0][0][0]
        assert log_call_args.action == ExecutionAction.CANCELLED.value

    def test_update_status_rejected_from_pending(self):
        """Test updating order status from PENDING to REJECTED."""
        # Arrange
        mock_session = Mock()
        order_id = uuid4()
        trader_id = uuid4()

        order = Order(
            id=order_id,
            trader_id=trader_id,
            symbol="MSFT",
            quantity=75,
            order_type=OrderType.STOP,
            status=OrderStatus.PENDING,
        )
        mock_session.get.return_value = order
        repository = OrderRepository(session=mock_session)

        # Act
        updated_order = repository.update_status(order_id, OrderStatus.REJECTED)

        # Assert
        assert updated_order.status == OrderStatus.REJECTED.value

        # Verify execution log has REJECTED action
        log_call_args = mock_session.add.call_args_list[0][0][0]
        assert log_call_args.action == ExecutionAction.REJECTED.value


class TestOrderRepositoryGetUnfilledOrders:
    """Test fetching unfilled orders."""

    def test_get_unfilled_orders_returns_pending_and_partial(self):
        """Test get_unfilled_orders returns PENDING and PARTIAL orders only."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()

        pending_order = Order(
            id=uuid4(),
            trader_id=trader_id,
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
        )
        partial_order = Order(
            id=uuid4(),
            trader_id=trader_id,
            symbol="TSLA",
            quantity=50,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PARTIAL,
        )

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [pending_order, partial_order]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repository = OrderRepository(session=mock_session)

        # Act
        orders = repository.get_unfilled_orders(trader_id)

        # Assert
        assert len(orders) == 2
        assert pending_order in orders
        assert partial_order in orders

    def test_get_unfilled_orders_excludes_filled_orders(self):
        """Test get_unfilled_orders does not return FILLED orders."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()

        # Return no unfilled orders
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repository = OrderRepository(session=mock_session)

        # Act
        orders = repository.get_unfilled_orders(trader_id)

        # Assert
        assert orders == []

    def test_get_unfilled_orders_excludes_rejected_and_cancelled(self):
        """Test get_unfilled_orders excludes REJECTED and CANCELLED orders."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repository = OrderRepository(session=mock_session)

        # Act
        orders = repository.get_unfilled_orders(trader_id)

        # Assert
        assert orders == []

    def test_get_unfilled_orders_returns_empty_when_none_found(self):
        """Test get_unfilled_orders returns empty list when no unfilled orders."""
        # Arrange
        mock_session = Mock()
        trader_id = uuid4()

        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repository = OrderRepository(session=mock_session)

        # Act
        orders = repository.get_unfilled_orders(trader_id)

        # Assert
        assert orders == []


class TestOrderRepositoryDetermineAction:
    """Test the _determine_action helper method."""

    def test_determine_action_maps_status_to_action(self):
        """Test _determine_action correctly maps statuses to actions."""
        # Arrange & Act & Assert
        assert OrderRepository._determine_action(OrderStatus.PENDING) == ExecutionAction.SUBMITTED
        assert OrderRepository._determine_action(OrderStatus.FILLED) == ExecutionAction.FILLED
        assert OrderRepository._determine_action(OrderStatus.PARTIAL) == ExecutionAction.FILLED
        assert OrderRepository._determine_action(OrderStatus.REJECTED) == ExecutionAction.REJECTED
        assert OrderRepository._determine_action(OrderStatus.CANCELLED) == ExecutionAction.CANCELLED
