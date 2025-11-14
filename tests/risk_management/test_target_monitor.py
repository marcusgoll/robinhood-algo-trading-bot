"""Tests for TargetMonitor component.

Tests cover:
- Target fill detection and cleanup (cancel stop order)
- Stop fill detection and cleanup (cancel target order)
- Order status polling and position closure
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest

from src.trading_bot.risk_management.models import PositionPlan, RiskManagementEnvelope
from src.trading_bot.risk_management.target_monitor import TargetMonitor


class TestTargetMonitor:
    """Test suite for TargetMonitor fill detection and cleanup logic."""

    def test_detect_target_fill_and_cleanup(self) -> None:
        """Test target fill detection triggers stop order cancellation.

        Scenario (from spec.md FR-009 and tasks.md T018):
        - Given: Position with target_order_id="ORDER123"
        - When: poll_order_status() detects target order status="filled"
        - Then:
            - Calls OrderManager.cancel_order(stop_order_id)
            - Logs to risk-management.jsonl with action="target_hit"
            - Calls AccountData.invalidate_cache()
            - Returns position_closed=True

        Test verifies:
        1. Order status polling for target order
        2. Stop order cancellation when target fills
        3. Logging of target_hit event
        4. Account cache invalidation
        5. Position closure flag returned
        """
        # Arrange: Create mocked dependencies
        mock_order_manager = Mock()
        mock_account_data = Mock()
        mock_logger = Mock()

        # Configure mock: Target order is filled
        mock_order_manager.get_order_status.return_value = {
            "order_id": "ORDER123",
            "status": "filled",
            "filled_quantity": 434,
            "average_fill_price": Decimal("254.90"),
        }

        # Create position plan for context
        position_plan = PositionPlan(
            symbol="TSLA",
            entry_price=Decimal("250.30"),
            stop_price=Decimal("248.00"),
            target_price=Decimal("254.90"),
            quantity=434,
            risk_amount=Decimal("1000.00"),
            reward_amount=Decimal("1996.00"),
            reward_ratio=2.0,
            pullback_source="detected",
        )

        # Create risk management envelope
        envelope = RiskManagementEnvelope(
            position_plan=position_plan,
            entry_order_id="ENTRY789",
            stop_order_id="STOP456",
            target_order_id="ORDER123",
            status="active",
            correlation_id="test-correlation-id-123",
        )

        # Create TargetMonitor instance with mocked dependencies
        monitor = TargetMonitor(
            order_manager=mock_order_manager,
            account_data=mock_account_data,
            logger=mock_logger,
        )

        # Act: Poll for fills
        position_closed = monitor.poll_and_handle_fills(envelope)

        # Assert: Verify target fill handling
        # 1. Should poll target order status
        mock_order_manager.get_order_status.assert_called_with("ORDER123")

        # 2. Should cancel stop order when target fills
        mock_order_manager.cancel_order.assert_called_with("STOP456")

        # 3. Should log target_hit event
        mock_logger.log.assert_called_once()
        log_call_args = mock_logger.log.call_args[1]
        assert log_call_args["action"] == "target_hit"
        assert log_call_args["symbol"] == "TSLA"
        assert log_call_args["target_order_id"] == "ORDER123"
        assert log_call_args["stop_order_id"] == "STOP456"

        # 4. Should invalidate account cache
        mock_account_data.invalidate_cache.assert_called_once()

        # 5. Should return position_closed=True
        assert position_closed is True

    def test_detect_stop_fill_and_cleanup(self) -> None:
        """Test stop fill detection triggers target order cancellation.

        Scenario (from spec.md FR-010 and tasks.md T019):
        - Given: Position with stop_order_id="ORDER456"
        - When: poll_order_status() detects stop filled
        - Then:
            - Calls OrderManager.cancel_order(target_order_id)
            - Logs action="stop_hit"
            - Returns position_closed=True

        Test verifies:
        1. Order status polling for stop order (after target not filled)
        2. Target order cancellation when stop fills
        3. Logging of stop_hit event
        4. Position closure flag returned
        """
        # Arrange: Create mocked dependencies
        mock_order_manager = Mock()
        mock_account_data = Mock()
        mock_logger = Mock()

        # Configure mock: Target not filled, stop IS filled
        def get_order_status_side_effect(order_id: str) -> dict:
            if order_id == "TARGET123":
                return {"order_id": "TARGET123", "status": "open", "filled_quantity": 0}
            elif order_id == "ORDER456":
                return {
                    "order_id": "ORDER456",
                    "status": "filled",
                    "filled_quantity": 434,
                    "average_fill_price": Decimal("248.00"),
                }
            return {}

        mock_order_manager.get_order_status.side_effect = get_order_status_side_effect

        # Create position plan
        position_plan = PositionPlan(
            symbol="TSLA",
            entry_price=Decimal("250.30"),
            stop_price=Decimal("248.00"),
            target_price=Decimal("254.90"),
            quantity=434,
            risk_amount=Decimal("1000.00"),
            reward_amount=Decimal("1996.00"),
            reward_ratio=2.0,
            pullback_source="detected",
        )

        # Create risk management envelope
        envelope = RiskManagementEnvelope(
            position_plan=position_plan,
            entry_order_id="ENTRY789",
            stop_order_id="ORDER456",
            target_order_id="TARGET123",
            status="active",
            correlation_id="test-correlation-id-456",
        )

        # Create TargetMonitor instance
        monitor = TargetMonitor(
            order_manager=mock_order_manager,
            account_data=mock_account_data,
            logger=mock_logger,
        )

        # Act: Poll for fills
        position_closed = monitor.poll_and_handle_fills(envelope)

        # Assert: Verify stop fill handling
        # 1. Should poll both target and stop order status
        assert mock_order_manager.get_order_status.call_count == 2
        mock_order_manager.get_order_status.assert_any_call("TARGET123")
        mock_order_manager.get_order_status.assert_any_call("ORDER456")

        # 2. Should cancel target order when stop fills
        mock_order_manager.cancel_order.assert_called_with("TARGET123")

        # 3. Should log stop_hit event
        mock_logger.log.assert_called_once()
        log_call_args = mock_logger.log.call_args[1]
        assert log_call_args["action"] == "stop_hit"
        assert log_call_args["symbol"] == "TSLA"
        assert log_call_args["stop_order_id"] == "ORDER456"
        assert log_call_args["target_order_id"] == "TARGET123"

        # 4. Should return position_closed=True
        assert position_closed is True
