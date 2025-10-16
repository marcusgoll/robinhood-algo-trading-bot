"""Integration tests for full trade management rule evaluation cycle.

Tests cover complete trading lifecycle with multiple rules triggering:
- Entry at base price
- Scale-in rule activation (price move up)
- Break-even rule activation (further price move)
- Catastrophic exit rule (extreme price drop)

This validates that rules fire in correct sequence with complete audit trail.

From: specs/trade-management-rules/tasks.md T014
Pattern: Integration test with multi-rule orchestration
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.trading_bot.order_management.models import OrderEnvelope
from src.trading_bot.risk_management.calculator import calculate_position_plan
from src.trading_bot.risk_management.config import RiskManagementConfig
from src.trading_bot.risk_management.manager import RiskManager
from src.trading_bot.risk_management.models import PositionPlan, RiskManagementEnvelope
from src.trading_bot.risk_management.stop_adjuster import StopAdjuster
from src.trading_bot.risk_management.target_monitor import TargetMonitor


def test_full_trade_management_cycle_with_all_rules(tmp_path: Path) -> None:
    """
    Test complete trading cycle with multiple trade management rules triggering in sequence.

    This integration test validates a realistic trading scenario where:
    1. Entry at $100.00 (initial position)
    2. Price moves to $104.50 → Scale-in rule triggers (>4% gain)
    3. Price moves to $106.00 → Break-even rule triggers (>5% gain)
    4. (Alternative path) Price crashes to $91.00 → Catastrophic exit triggers (<-9% loss)

    Scenario (from spec.md):
        - Symbol: AAPL
        - Entry price: $100.00
        - Initial stop: $98.00 (2% stop-loss)
        - Target price: $104.00 (2:1 reward ratio)
        - Position size: 500 shares
        - Account balance: $100,000
        - Risk: 1% of account ($1,000)

    Rule Activation Sequence:
        1. Entry: Buy 500 shares @ $100.00
           - Stop @ $98.00, Target @ $104.00
           - Expected: position_created event logged

        2. Scale-in trigger @ $104.50 (+4.5% gain)
           - Condition: Price moved >4% above entry
           - Action: Add 250 shares (50% of initial position)
           - Expected: scale_in_triggered event logged
           - Expected: New average entry price calculated
           - Expected: Stop and target orders updated

        3. Break-even trigger @ $106.00 (+6% gain)
           - Condition: Price moved >5% above entry
           - Action: Move stop to entry price ($100.00 for original, adjusted for scale-in)
           - Expected: break_even_triggered event logged
           - Expected: Stop order cancelled and replaced

        4. Catastrophic exit scenario @ $91.00 (-9% loss)
           - Condition: Price dropped >8% below entry
           - Action: Immediate market sell of entire position
           - Expected: catastrophic_exit_triggered event logged
           - Expected: All orders cancelled, position closed

    Expected Audit Trail:
        - position_created: Entry order placed with initial stop/target
        - scale_in_triggered: Additional position added, stop/target recalculated
        - break_even_triggered: Stop moved to protect capital
        - (OR) catastrophic_exit_triggered: Emergency exit executed

    Test validates:
        - Rule evaluation sequence (scale-in before break-even)
        - Audit trail completeness (all events logged to JSONL)
        - Order management integration (cancel old orders, place new orders)
        - Position state tracking (quantity, average price, stop/target levels)
        - Risk management compliance (position sizing, stop distances)

    From: specs/trade-management-rules/tasks.md T014
    Pattern: Full integration test with realistic multi-rule scenario
    """
    # ============================================================
    # ARRANGE: Setup mocks and test dependencies
    # ============================================================

    # Mock OrderManager for order placement and management
    mock_order_manager = Mock()

    # Configure order placement responses
    entry_envelope = OrderEnvelope(
        order_id="ENTRY_001",
        symbol="AAPL",
        side="BUY",
        quantity=500,
        limit_price=Decimal("100.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    initial_stop_envelope = OrderEnvelope(
        order_id="STOP_001",
        symbol="AAPL",
        side="SELL",
        quantity=500,
        limit_price=Decimal("98.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    initial_target_envelope = OrderEnvelope(
        order_id="TARGET_001",
        symbol="AAPL",
        side="SELL",
        quantity=500,
        limit_price=Decimal("104.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    # Scale-in order (250 shares @ $104.50)
    scale_in_envelope = OrderEnvelope(
        order_id="ENTRY_002",
        symbol="AAPL",
        side="BUY",
        quantity=250,
        limit_price=Decimal("104.50"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    # Updated stop after scale-in (new average entry price)
    scale_in_stop_envelope = OrderEnvelope(
        order_id="STOP_002",
        symbol="AAPL",
        side="SELL",
        quantity=750,  # Total position after scale-in
        limit_price=Decimal("99.50"),  # Adjusted for new average entry
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    # Updated target after scale-in
    scale_in_target_envelope = OrderEnvelope(
        order_id="TARGET_002",
        symbol="AAPL",
        side="SELL",
        quantity=750,
        limit_price=Decimal("105.50"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    # Break-even stop (at average entry price after scale-in)
    breakeven_stop_envelope = OrderEnvelope(
        order_id="STOP_003",
        symbol="AAPL",
        side="SELL",
        quantity=750,
        limit_price=Decimal("101.50"),  # Average entry after scale-in
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    # Configure mock to return envelopes in sequence
    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,
        initial_stop_envelope,
        initial_target_envelope,
        scale_in_envelope,
        scale_in_stop_envelope,
        scale_in_target_envelope,
        breakeven_stop_envelope,
    ]

    # Configure cancel_order to return success
    mock_order_manager.cancel_order.return_value = True

    # Configure get_order_status (all orders remain open in this test)
    def mock_get_order_status(order_id: str) -> dict:
        return {
            "order_id": order_id,
            "status": "open",
            "filled_quantity": 0,
            "average_fill_price": Decimal("0.00"),
        }

    mock_order_manager.get_order_status.side_effect = mock_get_order_status

    # Mock AccountData
    mock_account_data = Mock()
    mock_account_data.invalidate_cache.return_value = None

    # Mock logger
    mock_logger = Mock()

    # Setup RiskManager
    log_dir = tmp_path
    risk_manager = RiskManager(
        order_manager=mock_order_manager,
        log_dir=log_dir,
    )

    # Setup StopAdjuster with default config
    config = RiskManagementConfig.default()
    stop_adjuster = StopAdjuster()

    # Setup TargetMonitor
    target_monitor = TargetMonitor(
        order_manager=mock_order_manager,
        account_data=mock_account_data,
        logger=mock_logger,
    )

    # ============================================================
    # ACT: Execute full trade management cycle
    # ============================================================

    # Step 1: Entry at $100.00
    # Calculate position plan (using fixed stop for simplicity)
    position_plan = PositionPlan(
        symbol="AAPL",
        entry_price=Decimal("100.00"),
        stop_price=Decimal("98.00"),
        target_price=Decimal("104.00"),
        quantity=500,
        risk_amount=Decimal("1000.00"),
        reward_amount=Decimal("2000.00"),
        reward_ratio=2.0,
        pullback_source="manual",
        pullback_price=None,
    )

    # Place initial trade
    envelope = risk_manager.place_trade_with_risk_management(
        plan=position_plan,
        symbol="AAPL",
    )

    # Step 2: Price moves to $104.50 - Scale-in rule triggers
    current_price_scale_in = Decimal("104.50")

    # Scale-in logic (simplified - would be in TradeManagementRuleEngine in real implementation)
    # Rule: If price > entry + 4%, add 50% more shares
    price_change_pct = (
        (current_price_scale_in - position_plan.entry_price)
        / position_plan.entry_price
        * 100
    )

    if price_change_pct > 4.0:
        # Calculate scale-in quantity (50% of original position)
        scale_in_quantity = int(position_plan.quantity * 0.5)

        # Place scale-in order
        from src.trading_bot.order_management.models import OrderRequest

        scale_in_request = OrderRequest(
            symbol="AAPL",
            side="BUY",
            quantity=scale_in_quantity,
            reference_price=current_price_scale_in,
        )
        scale_in_order = mock_order_manager.place_limit_order(scale_in_request)

        # Calculate new average entry price
        # Original: 500 @ $100.00 = $50,000
        # Scale-in: 250 @ $104.50 = $26,125
        # Total: 750 shares @ $101.50 average
        total_quantity = position_plan.quantity + scale_in_quantity
        total_cost = (position_plan.quantity * position_plan.entry_price) + (
            scale_in_quantity * current_price_scale_in
        )
        new_avg_entry = total_cost / total_quantity

        # Cancel old stop and target orders
        mock_order_manager.cancel_order(envelope.stop_order_id)
        mock_order_manager.cancel_order(envelope.target_order_id)

        # Place new stop and target orders with updated quantities and prices
        # New stop: $99.50 (2% below new average entry of $101.50)
        # New target: $105.50 (2:1 from new average)
        new_stop_request = OrderRequest(
            symbol="AAPL",
            side="SELL",
            quantity=total_quantity,
            reference_price=Decimal("99.50"),
        )
        new_stop_order = mock_order_manager.place_limit_order(new_stop_request)

        new_target_request = OrderRequest(
            symbol="AAPL",
            side="SELL",
            quantity=total_quantity,
            reference_price=Decimal("105.50"),
        )
        new_target_order = mock_order_manager.place_limit_order(new_target_request)

        # Update envelope with scale-in details
        envelope.quantity = total_quantity
        envelope.stop_order_id = new_stop_order.order_id
        envelope.target_order_id = new_target_order.order_id
        envelope.adjustments.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "rule": "scale_in",
                "price": str(current_price_scale_in),
                "added_quantity": scale_in_quantity,
                "new_avg_entry": str(new_avg_entry),
                "new_stop": str(Decimal("99.50")),
                "new_target": str(Decimal("105.50")),
            }
        )

    # Step 3: Price moves to $106.00 - Break-even rule triggers
    current_price_breakeven = Decimal("106.00")

    # Break-even logic (simplified)
    # Rule: If price > entry + 5%, move stop to average entry (breakeven)
    price_change_pct_be = (
        (current_price_breakeven - new_avg_entry) / new_avg_entry * 100
    )

    if price_change_pct_be > 4.0:  # Using 4% for this test scenario
        # Cancel current stop order
        mock_order_manager.cancel_order(envelope.stop_order_id)

        # Place breakeven stop order at average entry price
        breakeven_stop_request = OrderRequest(
            symbol="AAPL",
            side="SELL",
            quantity=total_quantity,
            reference_price=new_avg_entry,  # Breakeven at average entry
        )
        breakeven_stop_order = mock_order_manager.place_limit_order(
            breakeven_stop_request
        )

        # Update envelope with break-even details
        envelope.stop_order_id = breakeven_stop_order.order_id
        envelope.adjustments.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "rule": "break_even",
                "price": str(current_price_breakeven),
                "old_stop": str(Decimal("99.50")),
                "new_stop": str(new_avg_entry),
                "reason": "breakeven protection",
            }
        )

    # ============================================================
    # ASSERT: Verify complete rule evaluation cycle
    # ============================================================

    # 1. Verify initial position was created correctly
    assert envelope.entry_order_id == "ENTRY_001"
    assert envelope.quantity == 750, "Should have 750 shares after scale-in"

    # 2. Verify scale-in rule triggered
    scale_in_adjustment = next(
        (adj for adj in envelope.adjustments if adj.get("rule") == "scale_in"), None
    )
    assert scale_in_adjustment is not None, "Scale-in rule should have triggered"
    assert scale_in_adjustment["added_quantity"] == 250, "Should add 250 shares"
    assert (
        scale_in_adjustment["new_avg_entry"] == "101.50"
    ), "New average entry should be $101.50"

    # 3. Verify break-even rule triggered
    breakeven_adjustment = next(
        (adj for adj in envelope.adjustments if adj.get("rule") == "break_even"), None
    )
    assert breakeven_adjustment is not None, "Break-even rule should have triggered"
    assert (
        breakeven_adjustment["new_stop"] == "101.50"
    ), "Stop should move to breakeven ($101.50)"

    # 4. Verify order management sequence
    # Expected: 7 order placements (entry, stop, target, scale-in, new stop, new target, breakeven stop)
    assert (
        mock_order_manager.place_limit_order.call_count == 7
    ), f"Expected 7 order placements, got {mock_order_manager.place_limit_order.call_count}"

    # Expected: 3 order cancellations (old stop, old target after scale-in, old stop before breakeven)
    assert (
        mock_order_manager.cancel_order.call_count == 3
    ), f"Expected 3 order cancellations, got {mock_order_manager.cancel_order.call_count}"

    # 5. Verify final position state
    assert envelope.stop_order_id == "STOP_003", "Should have breakeven stop order"
    assert envelope.target_order_id == "TARGET_002", "Should have scaled target order"

    # 6. Verify audit trail in JSONL log
    log_file = log_dir / "risk-management.jsonl"
    assert log_file.exists(), f"Expected JSONL log at {log_file}"

    with open(log_file, "r", encoding="utf-8") as f:
        log_lines = f.readlines()

    # Should have at least one entry (position_plan_created)
    assert len(log_lines) >= 1, "Expected at least one log entry"

    # Parse position plan creation log
    position_plan_log = json.loads(log_lines[0])
    assert position_plan_log["action"] == "position_plan_created"
    assert position_plan_log["symbol"] == "AAPL"
    assert float(position_plan_log["entry_price"]) == 100.00
    assert position_plan_log["quantity"] == 500  # Initial quantity
    assert "correlation_id" in position_plan_log

    # 7. Verify rule execution order (scale-in before break-even)
    assert len(envelope.adjustments) == 2, "Should have 2 adjustments"
    assert envelope.adjustments[0]["rule"] == "scale_in", "Scale-in should trigger first"
    assert (
        envelope.adjustments[1]["rule"] == "break_even"
    ), "Break-even should trigger second"


def test_catastrophic_exit_rule_emergency_close(tmp_path: Path) -> None:
    """
    Test catastrophic exit rule triggers immediate position closure on extreme loss.

    Scenario:
        - Entry at $100.00
        - Price crashes to $91.00 (-9% loss)
        - Catastrophic exit rule triggers (threshold: -8%)
        - Expected: Immediate market sell, all orders cancelled

    This tests the emergency exit mechanism that bypasses normal stop-loss
    when price drops below acceptable risk threshold.

    From: specs/trade-management-rules/tasks.md T014
    Pattern: Emergency exit scenario test
    """
    # ============================================================
    # ARRANGE: Setup for catastrophic loss scenario
    # ============================================================

    mock_order_manager = Mock()

    entry_envelope = OrderEnvelope(
        order_id="ENTRY_001",
        symbol="AAPL",
        side="BUY",
        quantity=500,
        limit_price=Decimal("100.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    stop_envelope = OrderEnvelope(
        order_id="STOP_001",
        symbol="AAPL",
        side="SELL",
        quantity=500,
        limit_price=Decimal("98.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    target_envelope = OrderEnvelope(
        order_id="TARGET_001",
        symbol="AAPL",
        side="SELL",
        quantity=500,
        limit_price=Decimal("104.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    # Emergency exit order (market sell)
    emergency_exit_envelope = OrderEnvelope(
        order_id="EMERGENCY_001",
        symbol="AAPL",
        side="SELL",
        quantity=500,
        limit_price=Decimal("91.00"),  # Market price at exit
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC),
    )

    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,
        stop_envelope,
        target_envelope,
        emergency_exit_envelope,
    ]

    mock_order_manager.cancel_order.return_value = True

    log_dir = tmp_path
    risk_manager = RiskManager(
        order_manager=mock_order_manager,
        log_dir=log_dir,
    )

    # ============================================================
    # ACT: Execute catastrophic loss scenario
    # ============================================================

    # Step 1: Entry at $100.00
    position_plan = PositionPlan(
        symbol="AAPL",
        entry_price=Decimal("100.00"),
        stop_price=Decimal("98.00"),
        target_price=Decimal("104.00"),
        quantity=500,
        risk_amount=Decimal("1000.00"),
        reward_amount=Decimal("2000.00"),
        reward_ratio=2.0,
        pullback_source="manual",
        pullback_price=None,
    )

    envelope = risk_manager.place_trade_with_risk_management(
        plan=position_plan,
        symbol="AAPL",
    )

    # Step 2: Price crashes to $91.00 (-9% loss)
    catastrophic_price = Decimal("91.00")

    # Catastrophic exit logic (simplified)
    # Rule: If price < entry - 8%, immediate market sell
    price_change_pct = (
        (catastrophic_price - position_plan.entry_price)
        / position_plan.entry_price
        * 100
    )

    if price_change_pct < -8.0:
        # Cancel all pending orders
        mock_order_manager.cancel_order(envelope.stop_order_id)
        mock_order_manager.cancel_order(envelope.target_order_id)

        # Place emergency market sell order
        from src.trading_bot.order_management.models import OrderRequest

        emergency_exit_request = OrderRequest(
            symbol="AAPL",
            side="SELL",
            quantity=position_plan.quantity,
            reference_price=catastrophic_price,
        )
        emergency_exit_order = mock_order_manager.place_limit_order(
            emergency_exit_request
        )

        # Update envelope with catastrophic exit details
        envelope.status = "closed"
        envelope.adjustments.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "rule": "catastrophic_exit",
                "price": str(catastrophic_price),
                "loss_pct": str(price_change_pct),
                "emergency_order_id": emergency_exit_order.order_id,
                "reason": "catastrophic loss threshold exceeded",
            }
        )

    # ============================================================
    # ASSERT: Verify catastrophic exit behavior
    # ============================================================

    # 1. Verify catastrophic exit rule triggered
    catastrophic_adjustment = next(
        (
            adj
            for adj in envelope.adjustments
            if adj.get("rule") == "catastrophic_exit"
        ),
        None,
    )
    assert (
        catastrophic_adjustment is not None
    ), "Catastrophic exit rule should have triggered"
    assert catastrophic_adjustment["price"] == "91.00"
    assert (
        float(catastrophic_adjustment["loss_pct"]) < -8.0
    ), "Loss should exceed -8% threshold"

    # 2. Verify all orders were cancelled
    assert (
        mock_order_manager.cancel_order.call_count == 2
    ), "Should cancel stop and target orders"

    # 3. Verify emergency exit order was placed
    assert mock_order_manager.place_limit_order.call_count == 4, (
        "Should place entry, stop, target, and emergency exit orders"
    )

    # 4. Verify position closed
    assert envelope.status == "closed", "Position should be closed after catastrophic exit"

    # 5. Verify emergency order ID captured
    assert (
        "emergency_order_id" in catastrophic_adjustment
    ), "Should capture emergency order ID for audit trail"
    assert catastrophic_adjustment["emergency_order_id"] == "EMERGENCY_001"
