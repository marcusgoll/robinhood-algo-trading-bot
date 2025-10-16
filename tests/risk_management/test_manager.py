"""
Tests for RiskManager module.

Validates position plan calculation orchestration, order placement with stop/target,
JSONL audit logging, and error handling for stop placement failures.

From: specs/stop-loss-automation/tasks.md T014-T015, T020
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.trading_bot.risk_management.calculator import calculate_position_plan
from src.trading_bot.risk_management.exceptions import StopPlacementError
from src.trading_bot.risk_management.models import PositionPlan, RiskManagementEnvelope


def test_place_trade_with_risk_management() -> None:
    """
    Test that RiskManager places entry, stop, and target orders via OrderManager.

    Given:
        - PositionPlan with:
          * symbol="TSLA"
          * entry_price=$250.30
          * stop_price=$248.00
          * target_price=$254.90
          * quantity=434 shares
          * risk_amount=$1,000
          * reward_ratio=2.0
        - Mocked OrderManager dependency

    When:
        place_trade_with_risk_management(plan, symbol="TSLA") is called

    Then:
        - Calls OrderManager.place_limit_order() for entry BUY at $250.30, qty=434
        - Calls OrderManager.place_limit_order() for stop SELL at $248.00, qty=434
        - Calls OrderManager.place_limit_order() for target SELL at $254.90, qty=434
        - Returns RiskManagementEnvelope with:
          * entry_order_id="ENTRY123"
          * stop_order_id="STOP456"
          * target_order_id="TARGET789"
          * status="pending"
          * position_plan=plan

    Rationale:
        Core orchestration test ensures RiskManager correctly delegates to OrderManager
        for each order type (entry/stop/target) and constructs proper audit envelope.
        This validates FR-004: automated stop/target placement with OrderManager reuse.

    Pattern: tests/order_management/test_manager.py test structure
    Reuse: OrderManager.place_limit_order() for all three order types
    From: spec.md FR-004, tasks.md T014
    Phase: TDD RED - test MUST FAIL until RiskManager.place_trade_with_risk_management() implemented
    """
    # Arrange
    # Create a realistic PositionPlan matching the spec scenario
    position_plan = PositionPlan(
        symbol="TSLA",
        entry_price=Decimal("250.30"),
        stop_price=Decimal("248.00"),
        target_price=Decimal("254.90"),
        quantity=434,
        risk_amount=Decimal("1000.00"),
        reward_amount=Decimal("1996.40"),
        reward_ratio=2.0,
        pullback_source="detected",
        pullback_price=Decimal("248.00"),
        created_at=datetime.now(UTC)
    )

    # Mock OrderManager
    mock_order_manager = Mock()

    # Configure mock to return different OrderEnvelopes for each call
    # We need to import OrderEnvelope to construct realistic return values
    from src.trading_bot.order_management.models import OrderEnvelope

    entry_envelope = OrderEnvelope(
        order_id="ENTRY123",
        symbol="TSLA",
        side="BUY",
        quantity=434,
        limit_price=Decimal("250.30"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    stop_envelope = OrderEnvelope(
        order_id="STOP456",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("248.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    target_envelope = OrderEnvelope(
        order_id="TARGET789",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("254.90"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    # Configure place_limit_order to return different envelopes based on call order
    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,   # First call: entry order
        stop_envelope,    # Second call: stop order
        target_envelope   # Third call: target order
    ]

    # Import RiskManager (this will FAIL - not fully implemented yet)
    from src.trading_bot.risk_management.manager import RiskManager

    # Create RiskManager with mocked OrderManager
    risk_manager = RiskManager(order_manager=mock_order_manager)

    # Act
    envelope = risk_manager.place_trade_with_risk_management(
        plan=position_plan,
        symbol="TSLA"
    )

    # Assert - Verify OrderManager was called correctly for all three orders
    assert mock_order_manager.place_limit_order.call_count == 3, \
        f"Expected 3 calls to place_limit_order, got {mock_order_manager.place_limit_order.call_count}"

    # Verify entry order call (first call)
    entry_call = mock_order_manager.place_limit_order.call_args_list[0]
    entry_order_request = entry_call[0][0]  # First positional argument
    assert entry_order_request.symbol == "TSLA"
    assert entry_order_request.side == "BUY"
    assert entry_order_request.quantity == 434
    assert entry_order_request.reference_price == Decimal("250.30")

    # Verify stop order call (second call)
    stop_call = mock_order_manager.place_limit_order.call_args_list[1]
    stop_order_request = stop_call[0][0]
    assert stop_order_request.symbol == "TSLA"
    assert stop_order_request.side == "SELL"
    assert stop_order_request.quantity == 434
    assert stop_order_request.reference_price == Decimal("248.00")

    # Verify target order call (third call)
    target_call = mock_order_manager.place_limit_order.call_args_list[2]
    target_order_request = target_call[0][0]
    assert target_order_request.symbol == "TSLA"
    assert target_order_request.side == "SELL"
    assert target_order_request.quantity == 434
    assert target_order_request.reference_price == Decimal("254.90")

    # Verify returned RiskManagementEnvelope structure
    assert isinstance(envelope, RiskManagementEnvelope), \
        f"Expected RiskManagementEnvelope, got {type(envelope)}"
    assert envelope.entry_order_id == "ENTRY123"
    assert envelope.stop_order_id == "STOP456"
    assert envelope.target_order_id == "TARGET789"
    assert envelope.status == "pending"
    assert envelope.position_plan == position_plan


def test_log_position_plan_to_jsonl(tmp_path: Path) -> None:
    """
    Test that RiskManager logs position plan to JSONL audit trail.

    Given:
        - PositionPlan created with:
          * symbol="TSLA"
          * entry_price=$250.30
          * stop_price=$248.00
          * target_price=$254.90
          * quantity=434 shares
          * risk_amount=$1,000
          * reward_ratio=2.0
          * pullback_source="detected"
        - RiskManager configured with log_dir=tmp_path

    When:
        calculate_position_with_stop() completes

    Then:
        logs/risk-management.jsonl contains entry with:
        - action="position_plan_created"
        - symbol="TSLA"
        - entry_price=250.30
        - stop_price=248.00
        - target_price=254.90
        - quantity=434
        - risk_amount=1000.00
        - reward_ratio=2.0
        - pullback_source="detected"
        - timestamp in ISO 8601 format

    Rationale:
        Audit trail requirement (spec.md FR-011, NFR-004) mandates complete
        risk profile logging for regulatory compliance and post-trade analysis.
        JSONL format enables efficient querying and analysis of position planning
        decisions over time.

    Pattern: src/trading_bot/logging/structured_logger.py JSONL logging
    From: spec.md FR-011, NFR-004, tasks.md T015
    Phase: TDD RED - test MUST FAIL until RiskManager logging implemented
    """
    # Arrange
    symbol = "TSLA"
    entry_price = Decimal("250.30")
    stop_price = Decimal("248.00")
    account_balance = Decimal("100000.00")
    account_risk_pct = 1.0
    target_rr = 2.0

    # Create position plan (this part works via T010)
    position_plan = calculate_position_plan(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        target_rr=target_rr,
        account_balance=account_balance,
        risk_pct=account_risk_pct
    )

    # Mock RiskManager (not yet implemented)
    # This is where the test will FAIL - RiskManager doesn't exist yet
    from src.trading_bot.risk_management.manager import RiskManager

    log_file = tmp_path / "risk-management.jsonl"

    # Create RiskManager with custom log directory
    risk_manager = RiskManager(log_dir=tmp_path)

    # Act - This should log position plan creation
    # calculate_position_with_stop orchestrates pullback analysis + position planning
    # For this test, we'll call a logging method directly since we already have the plan
    risk_manager.log_position_plan(position_plan, pullback_source="detected")

    # Assert - Verify JSONL log entry
    assert log_file.exists(), f"Expected log file at {log_file}"

    # Read JSONL log
    with open(log_file, 'r', encoding='utf-8') as f:
        log_lines = f.readlines()

    assert len(log_lines) >= 1, "Expected at least one log entry"

    # Parse last log entry (most recent)
    log_entry = json.loads(log_lines[-1])

    # Verify log structure
    assert log_entry["action"] == "position_plan_created", \
        f"Expected action='position_plan_created', got '{log_entry['action']}'"
    assert log_entry["symbol"] == "TSLA"
    assert float(log_entry["entry_price"]) == 250.30
    assert float(log_entry["stop_price"]) == 248.00
    assert float(log_entry["target_price"]) == 254.90
    assert log_entry["quantity"] == 434
    assert float(log_entry["risk_amount"]) == 1000.00
    assert log_entry["reward_ratio"] == pytest.approx(2.0, abs=0.01)
    assert log_entry["pullback_source"] == "detected"

    # Verify timestamp exists and is valid ISO 8601 format
    assert "timestamp" in log_entry, "Expected timestamp field"
    assert "T" in log_entry["timestamp"], "Expected ISO 8601 timestamp format"
    assert "Z" in log_entry["timestamp"] or "+" in log_entry["timestamp"], \
        "Expected timezone in timestamp"


def test_cancel_entry_on_stop_placement_failure() -> None:
    """
    Test that RiskManager cancels entry order when stop placement fails.

    This is a critical guardrail (FR-003): If we cannot place a stop-loss order,
    we must cancel the entry to avoid unprotected positions.

    Given:
        - Entry order submitted successfully (order_id="ENTRY_ORDER_123")
        - Stop placement raises StopPlacementError (broker failure)

    When:
        place_trade_with_risk_management(plan, symbol="TSLA")

    Then:
        1. Calls OrderManager.place_limit_order() for entry → succeeds
        2. Calls OrderManager.place_limit_order() for stop → raises StopPlacementError
        3. Calls OrderManager.cancel_order(entry_order_id="ENTRY_ORDER_123") → cleanup
        4. Logs error with correlation_id for audit trail
        5. Re-raises StopPlacementError to caller

    Guardrail rationale:
        Without this safety mechanism, we could have open entry orders or filled
        positions without protective stop-loss orders. This violates the
        Constitution's §Risk_Management principle: "Never enter a position
        without predefined exit criteria."

    From: spec.md FR-003 guardrail, tasks.md T020
    Pattern: TDD RED phase - test MUST FAIL until manager error handling implemented
    """
    # Arrange: Create sample PositionPlan
    # Based on spec.md acceptance scenario 1:
    # - Symbol: TSLA
    # - Entry: $250.30
    # - Stop: $248.00 (pullback low)
    # - Target: $254.90 (2:1 risk-reward)
    # - Quantity: 434 shares
    position_plan = PositionPlan(
        symbol="TSLA",
        entry_price=Decimal("250.30"),
        stop_price=Decimal("248.00"),
        target_price=Decimal("254.90"),
        quantity=434,
        risk_amount=Decimal("1000.00"),
        reward_amount=Decimal("1996.40"),
        reward_ratio=2.0,
        pullback_source="detected",
        pullback_price=Decimal("248.00"),
        created_at=datetime.now(UTC)
    )

    # Create mock OrderManager
    mock_order_manager = Mock()

    # Import OrderEnvelope for realistic mock returns
    from src.trading_bot.order_management.models import OrderEnvelope

    # Configure mock behavior:
    # 1. Entry order succeeds (returns OrderEnvelope)
    entry_envelope = OrderEnvelope(
        order_id="ENTRY_ORDER_123",
        symbol="TSLA",
        side="BUY",
        quantity=434,
        limit_price=Decimal("250.30"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    # 2. Stop order placement fails (raises StopPlacementError on second call)
    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,  # First call succeeds
        StopPlacementError(
            "Broker timeout: Failed to place stop-loss order for TSLA at $248.00"
        )  # Second call fails
    ]

    # 3. Cancel order should succeed when called
    mock_order_manager.cancel_order.return_value = True

    # Import RiskManager (this will work since manager.py exists)
    from src.trading_bot.risk_management.manager import RiskManager

    # Create RiskManager with mocked OrderManager
    # NOTE: This will FAIL because RiskManager constructor doesn't accept
    # order_manager parameter yet (will be added in T025 GREEN phase)
    risk_manager = RiskManager(order_manager=mock_order_manager)

    # Act & Assert: Expect StopPlacementError to be raised
    with pytest.raises(StopPlacementError, match="Broker timeout.*stop-loss"):
        # This will FAIL in RED phase because place_trade_with_risk_management
        # doesn't exist yet OR doesn't implement the guardrail logic
        # (will be implemented in T025/T030 GREEN phase)
        risk_manager.place_trade_with_risk_management(
            plan=position_plan,
            symbol="TSLA"
        )

    # Assert guardrail behavior (once implemented in T030):
    # These assertions document expected behavior

    # 1. Entry order was placed first
    assert mock_order_manager.place_limit_order.call_count == 2, \
        "Expected 2 calls to place_limit_order (entry succeeded, stop failed)"

    # 2. Entry order was cancelled as guardrail cleanup
    mock_order_manager.cancel_order.assert_called_once_with(
        order_id="ENTRY_ORDER_123"
    )

    # 3. Error was logged with correlation_id
    # TODO: Add logging assertion once logger is integrated (T026)
    # risk_manager.logger.log_error.assert_called_once()
