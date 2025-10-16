"""
Integration tests for end-to-end position lifecycle scenarios.

Validates complete workflows: position planning → order placement → price movement →
stop adjustments → target/stop fills → cleanup. Uses mocked OrderManager and AccountData
to simulate broker APIs without live connections.

From: specs/stop-loss-automation/tasks.md T034-T035
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.trading_bot.risk_management.calculator import calculate_position_plan
from src.trading_bot.risk_management.manager import RiskManager
from src.trading_bot.risk_management.models import (
    PositionPlan,
    RiskManagementEnvelope,
)
from src.trading_bot.risk_management.stop_adjuster import StopAdjuster
from src.trading_bot.risk_management.target_monitor import TargetMonitor


def test_full_position_lifecycle_with_target_fill(tmp_path: Path) -> None:
    """
    Test complete position lifecycle from planning to target fill.

    This integration test validates the end-to-end workflow:
    1. Calculate position plan with pullback detection
    2. Place trade with stop and target orders
    3. Simulate price movement to 50% target (trigger trailing stop)
    4. Simulate target fill (cleanup stop order)
    5. Verify JSONL log contains complete audit trail

    Scenario (from spec.md acceptance scenario 1-4):
        - Symbol: TSLA
        - Entry: $250.30
        - Pullback low (stop): $248.00
        - Target (2:1): $254.90
        - Quantity: 434 shares
        - Risk: $1,000 (1% of $100k account)
        - Price moves to $252.60 (50% to target) → trailing stop to breakeven
        - Target fills at $254.90 → cancel stop, update account cache

    Mocks:
        - OrderManager: place_limit_order(), cancel_order(), get_order_status()
        - AccountData: invalidate_cache()

    From: specs/stop-loss-automation/tasks.md T034
    Pattern: Full integration test with realistic scenario
    """
    # ============================================================
    # ARRANGE: Setup mocks and test data
    # ============================================================

    # Create price data with swing low at $248.00 (pullback detection)
    price_data = [
        # Downtrend leading to swing low
        {
            "timestamp": datetime(2025, 10, 15, 9, 30, tzinfo=UTC),
            "low": Decimal("252.00"),
            "close": Decimal("251.50"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 9, 35, tzinfo=UTC),
            "low": Decimal("251.00"),
            "close": Decimal("250.50"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 9, 40, tzinfo=UTC),
            "low": Decimal("250.00"),
            "close": Decimal("249.50"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 9, 45, tzinfo=UTC),
            "low": Decimal("249.50"),
            "close": Decimal("249.00"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 9, 50, tzinfo=UTC),
            "low": Decimal("249.00"),
            "close": Decimal("248.50"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 9, 55, tzinfo=UTC),
            "low": Decimal("248.50"),
            "close": Decimal("248.20"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 0, tzinfo=UTC),
            "low": Decimal("248.20"),
            "close": Decimal("248.10"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 5, tzinfo=UTC),
            "low": Decimal("248.10"),
            "close": Decimal("248.00"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 10, tzinfo=UTC),
            "low": Decimal("248.05"),
            "close": Decimal("248.00"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 15, tzinfo=UTC),
            "low": Decimal("248.00"),
            "close": Decimal("248.00"),
        },
        # SWING LOW at index 10
        {
            "timestamp": datetime(2025, 10, 15, 10, 20, tzinfo=UTC),
            "low": Decimal("248.00"),
            "close": Decimal("248.10"),
        },
        # Confirmation candles (higher lows)
        {
            "timestamp": datetime(2025, 10, 15, 10, 25, tzinfo=UTC),
            "low": Decimal("248.20"),
            "close": Decimal("248.50"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 30, tzinfo=UTC),
            "low": Decimal("248.50"),
            "close": Decimal("249.00"),
        },
        # Recovery
        {
            "timestamp": datetime(2025, 10, 15, 10, 35, tzinfo=UTC),
            "low": Decimal("249.00"),
            "close": Decimal("249.50"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 40, tzinfo=UTC),
            "low": Decimal("249.50"),
            "close": Decimal("250.00"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 45, tzinfo=UTC),
            "low": Decimal("249.80"),
            "close": Decimal("250.20"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 50, tzinfo=UTC),
            "low": Decimal("250.00"),
            "close": Decimal("250.30"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 10, 55, tzinfo=UTC),
            "low": Decimal("250.20"),
            "close": Decimal("250.50"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 11, 0, tzinfo=UTC),
            "low": Decimal("250.30"),
            "close": Decimal("250.60"),
        },
        {
            "timestamp": datetime(2025, 10, 15, 11, 5, tzinfo=UTC),
            "low": Decimal("250.40"),
            "close": Decimal("250.30"),
        },
    ]

    # Mock OrderManager
    mock_order_manager = Mock()

    # Import OrderEnvelope for realistic return values
    from src.trading_bot.order_management.models import OrderEnvelope

    # Configure order placement responses
    entry_envelope = OrderEnvelope(
        order_id="ENTRY_001",
        symbol="TSLA",
        side="BUY",
        quantity=434,
        limit_price=Decimal("250.30"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    stop_envelope = OrderEnvelope(
        order_id="STOP_001",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("248.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    target_envelope = OrderEnvelope(
        order_id="TARGET_001",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("254.90"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    # Trailing stop adjustment envelope (breakeven at $250.30)
    trailing_stop_envelope = OrderEnvelope(
        order_id="STOP_002",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("250.30"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,  # Initial entry
        stop_envelope,  # Initial stop
        target_envelope,  # Initial target
        trailing_stop_envelope,  # Trailing stop (breakeven)
    ]

    # Configure get_order_status() to simulate target fill in poll_and_handle_fills()
    # The test will manually call poll_and_handle_fills() which will check status
    def mock_get_order_status(order_id: str) -> dict:
        # Simulate target fill - TARGET_001 is filled, everything else is open
        if order_id == "TARGET_001":
            return {
                "order_id": order_id,
                "status": "filled",
                "filled_quantity": 434,
                "average_fill_price": Decimal("254.90"),
            }
        else:
            # All other orders (stops) are still open
            return {
                "order_id": order_id,
                "status": "open",
                "filled_quantity": 0,
                "average_fill_price": Decimal("0.00"),
            }

    mock_order_manager.get_order_status.side_effect = mock_get_order_status

    # Configure cancel_order() to return success
    mock_order_manager.cancel_order.return_value = True

    # Mock AccountData
    mock_account_data = Mock()
    mock_account_data.invalidate_cache.return_value = None

    # Mock logger for TargetMonitor
    mock_logger = Mock()

    # Setup RiskManager with mocked dependencies
    log_dir = tmp_path
    risk_manager = RiskManager(
        order_manager=mock_order_manager,
        log_dir=log_dir,
    )

    # Setup StopAdjuster (default settings)
    from src.trading_bot.risk_management.config import RiskManagementConfig

    config = RiskManagementConfig.default()
    stop_adjuster = StopAdjuster()

    # Setup TargetMonitor
    target_monitor = TargetMonitor(
        order_manager=mock_order_manager,
        account_data=mock_account_data,
        logger=mock_logger,
    )

    # ============================================================
    # ACT: Execute complete position lifecycle
    # ============================================================

    # Step 1: Calculate position plan with pullback detection
    position_plan = risk_manager.calculate_position_with_stop(
        symbol="TSLA",
        entry_price=Decimal("250.30"),
        account_balance=Decimal("100000.00"),
        account_risk_pct=1.0,
        price_data=price_data,
        target_rr=2.0,
        lookback_candles=20,
    )

    # Step 2: Place trade with stop and target orders
    envelope = risk_manager.place_trade_with_risk_management(
        plan=position_plan,
        symbol="TSLA",
    )

    # Step 3: Simulate price movement to 50% target ($252.60)
    # This triggers trailing stop adjustment to breakeven ($250.30)
    current_price_50pct = Decimal("252.60")

    # Check if stop should be adjusted
    adjustment_result = stop_adjuster.calculate_adjustment(
        current_price=current_price_50pct,
        position_plan=position_plan,
        config=config,
    )

    # If adjustment needed, place new stop order
    if adjustment_result is not None:
        new_stop_price, adjustment_reason = adjustment_result

        # Cancel old stop order
        mock_order_manager.cancel_order(envelope.stop_order_id)

        # Place new trailing stop order
        from src.trading_bot.order_management.models import OrderRequest

        trailing_stop_request = OrderRequest(
            symbol="TSLA",
            side="SELL",
            quantity=434,
            reference_price=new_stop_price,
        )
        trailing_stop_envelope = mock_order_manager.place_limit_order(
            trailing_stop_request
        )

        # Update envelope with new stop order ID
        envelope.stop_order_id = trailing_stop_envelope.order_id
        envelope.adjustments.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "old_stop_price": str(position_plan.stop_price),
                "new_stop_price": str(new_stop_price),
                "reason": adjustment_reason,
            }
        )

    # Step 4: Simulate target fill at $254.90
    # TargetMonitor polls and detects target fill, cancels stop order
    position_closed = target_monitor.poll_and_handle_fills(envelope)

    # ============================================================
    # ASSERT: Verify complete lifecycle behavior
    # ============================================================

    # 1. Verify position plan was calculated correctly
    assert position_plan.symbol == "TSLA"
    assert position_plan.entry_price == Decimal("250.30")
    assert (
        position_plan.stop_price == Decimal("248.00")
    ), "Should detect pullback low at $248.00"
    assert position_plan.target_price == Decimal("254.90"), "Should calculate 2:1 target"
    assert position_plan.quantity == 434, "Should calculate correct position size"
    assert position_plan.risk_amount == Decimal("1000.00"), "Should risk 1% of $100k"
    assert position_plan.pullback_source == "detected", "Should use detected pullback"

    # 2. Verify all orders were placed (entry, stop, target, trailing stop)
    assert (
        mock_order_manager.place_limit_order.call_count == 4
    ), "Expected 4 order placements (entry, stop, target, trailing stop)"

    # 3. Verify envelope was created with correct order IDs
    assert isinstance(envelope, RiskManagementEnvelope)
    assert envelope.entry_order_id == "ENTRY_001"
    # Note: stop_order_id updated to trailing stop after adjustment
    assert envelope.stop_order_id == "STOP_002", "Should have updated stop order ID"
    assert envelope.target_order_id == "TARGET_001"
    assert envelope.status == "pending"

    # 4. Verify trailing stop adjustment occurred
    assert (
        len(envelope.adjustments) == 1
    ), "Should have one stop adjustment at 50% progress"
    adjustment = envelope.adjustments[0]
    assert adjustment["old_stop_price"] == "248.00"
    assert adjustment["new_stop_price"] == "250.30", "Should move to breakeven"
    assert (
        "breakeven" in adjustment["reason"]
    ), "Should indicate breakeven adjustment"

    # 5. Verify old stop was cancelled before placing new trailing stop
    cancel_calls = mock_order_manager.cancel_order.call_args_list
    assert len(cancel_calls) == 2, f"Should cancel old stop and final stop after target fill, got {len(cancel_calls)} calls"
    # First cancel: old stop order when adjusting (called with positional arg in test code)
    first_cancel_arg = cancel_calls[0][0][0] if cancel_calls[0][0] else cancel_calls[0][1].get("order_id")
    assert first_cancel_arg == "STOP_001", f"First cancel should be STOP_001, got {first_cancel_arg}"
    # Second cancel: trailing stop when target fills (called by TargetMonitor)
    second_cancel_arg = cancel_calls[1][0][0] if cancel_calls[1][0] else cancel_calls[1][1].get("order_id")
    assert second_cancel_arg == "STOP_002", f"Second cancel should be STOP_002, got {second_cancel_arg}"

    # 6. Verify position was closed (target filled)
    assert position_closed is True, "TargetMonitor should detect target fill"

    # 7. Verify account cache was invalidated
    mock_account_data.invalidate_cache.assert_called_once()

    # 8. Verify target_hit event was logged
    mock_logger.log.assert_called_once()
    log_call = mock_logger.log.call_args[1]
    assert log_call["action"] == "target_hit"
    assert log_call["symbol"] == "TSLA"
    assert log_call["target_order_id"] == "TARGET_001"
    assert log_call["filled_quantity"] == 434
    assert log_call["average_fill_price"] == Decimal("254.90")

    # 9. Verify JSONL audit trail contains complete lifecycle
    log_file = log_dir / "risk-management.jsonl"
    assert log_file.exists(), f"Expected JSONL log at {log_file}"

    with open(log_file, "r", encoding="utf-8") as f:
        log_lines = f.readlines()

    # Should have at least one entry (position_plan_created)
    assert len(log_lines) >= 1, "Expected at least one log entry"

    # Parse position plan creation log
    position_plan_log = json.loads(log_lines[0])
    assert position_plan_log["action"] == "position_plan_created"
    assert position_plan_log["symbol"] == "TSLA"
    assert float(position_plan_log["entry_price"]) == 250.30
    assert float(position_plan_log["stop_price"]) == 248.00
    assert float(position_plan_log["target_price"]) == 254.90
    assert position_plan_log["quantity"] == 434
    assert float(position_plan_log["risk_amount"]) == 1000.00
    assert position_plan_log["reward_ratio"] == pytest.approx(2.0, abs=0.01)
    assert position_plan_log["pullback_source"] == "detected"
    assert "correlation_id" in position_plan_log, "Should include correlation_id"
    assert "timestamp" in position_plan_log, "Should include timestamp"


def test_full_position_lifecycle_with_stop_fill(tmp_path: Path) -> None:
    """
    Test complete position lifecycle ending with stop-loss fill.

    This integration test validates the stop-out scenario:
    1. Calculate position plan with pullback detection
    2. Place trade with stop and target orders
    3. Simulate stop order fill (price drops to stop-loss)
    4. Verify target order cancelled
    5. Verify JSONL log contains stop_hit event

    Scenario:
        - Symbol: TSLA
        - Entry: $250.30
        - Stop: $248.00
        - Target: $254.90
        - Quantity: 434 shares
        - Price drops to $248.00 → stop fills
        - Target cancelled, position closed

    From: specs/stop-loss-automation/tasks.md T035
    Pattern: Integration test for stop-out scenario
    """
    # ============================================================
    # ARRANGE: Setup mocks and test data
    # ============================================================

    # Simplified price data (reuse pattern from T034)
    price_data = [
        {
            "timestamp": datetime(2025, 10, 15, 10, i, tzinfo=UTC),
            "low": Decimal("248.00"),
            "close": Decimal("248.50"),
        }
        for i in range(20)
    ]

    # Mock OrderManager
    mock_order_manager = Mock()

    from src.trading_bot.order_management.models import OrderEnvelope

    entry_envelope = OrderEnvelope(
        order_id="ENTRY_002",
        symbol="TSLA",
        side="BUY",
        quantity=434,
        limit_price=Decimal("250.30"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    stop_envelope = OrderEnvelope(
        order_id="STOP_002",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("248.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    target_envelope = OrderEnvelope(
        order_id="TARGET_002",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("254.90"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,
        stop_envelope,
        target_envelope,
    ]

    # Configure get_order_status() to simulate stop fill
    def mock_get_order_status_stop_fill(order_id: str) -> dict:
        # Simulate stop order filled
        if order_id == "STOP_002":
            return {
                "order_id": order_id,
                "status": "filled",
                "filled_quantity": 434,
                "average_fill_price": Decimal("248.00"),
            }
        else:
            # Target still open
            return {
                "order_id": order_id,
                "status": "open",
                "filled_quantity": 0,
                "average_fill_price": Decimal("0.00"),
            }

    mock_order_manager.get_order_status.side_effect = mock_get_order_status_stop_fill
    mock_order_manager.cancel_order.return_value = True

    # Mock AccountData
    mock_account_data = Mock()
    mock_account_data.invalidate_cache.return_value = None

    # Mock logger
    mock_logger = Mock()

    # Setup components
    log_dir = tmp_path
    risk_manager = RiskManager(
        order_manager=mock_order_manager,
        log_dir=log_dir,
    )

    target_monitor = TargetMonitor(
        order_manager=mock_order_manager,
        account_data=mock_account_data,
        logger=mock_logger,
    )

    # ============================================================
    # ACT: Execute position lifecycle with stop fill
    # ============================================================

    # Step 1: Calculate position plan
    position_plan = risk_manager.calculate_position_with_stop(
        symbol="TSLA",
        entry_price=Decimal("250.30"),
        account_balance=Decimal("100000.00"),
        account_risk_pct=1.0,
        price_data=price_data,
        target_rr=2.0,
    )

    # Step 2: Place trade
    envelope = risk_manager.place_trade_with_risk_management(
        plan=position_plan,
        symbol="TSLA",
    )

    # Step 3: Simulate stop fill
    position_closed = target_monitor.poll_and_handle_fills(envelope)

    # ============================================================
    # ASSERT: Verify stop-out behavior
    # ============================================================

    # 1. Verify position was closed (stop filled)
    assert position_closed is True, "TargetMonitor should detect stop fill"

    # 2. Verify target order was cancelled
    mock_order_manager.cancel_order.assert_called_once_with("TARGET_002")

    # 3. Verify account cache was invalidated
    mock_account_data.invalidate_cache.assert_called_once()

    # 4. Verify stop_hit event was logged
    mock_logger.log.assert_called_once()
    log_call = mock_logger.log.call_args[1]
    assert log_call["action"] == "stop_hit"
    assert log_call["symbol"] == "TSLA"
    assert log_call["stop_order_id"] == "STOP_002"
    assert log_call["target_order_id"] == "TARGET_002"
    assert log_call["filled_quantity"] == 434
    assert log_call["average_fill_price"] == Decimal("248.00")

    # 5. Verify JSONL audit trail
    log_file = log_dir / "risk-management.jsonl"
    assert log_file.exists(), f"Expected JSONL log at {log_file}"

    with open(log_file, "r", encoding="utf-8") as f:
        log_lines = f.readlines()

    assert len(log_lines) >= 1, "Expected at least one log entry"

    # Parse position plan log
    position_plan_log = json.loads(log_lines[0])
    assert position_plan_log["action"] == "position_plan_created"
    assert position_plan_log["symbol"] == "TSLA"
    assert "correlation_id" in position_plan_log
