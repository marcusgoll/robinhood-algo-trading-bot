"""
Tests for circuit breaker integration in risk management.

Validates stop placement failure tracking and circuit breaker triggering
when failures exceed 2% threshold per spec.md guardrail.

From: specs/stop-loss-automation/spec.md NFR-003 guardrail, tasks.md T040
"""

from decimal import Decimal
from datetime import UTC, datetime
from unittest.mock import Mock
import pytest

from src.trading_bot.risk_management.exceptions import StopPlacementError
from src.trading_bot.risk_management.models import PositionPlan
from src.trading_bot.error_handling.exceptions import CircuitBreakerTripped


def test_circuit_breaker_trips_on_stop_placement_failures() -> None:
    """
    Test circuit breaker triggers when stop placement failures exceed 2%.

    Given:
        - 100 position plans attempted
        - First 97 succeed
        - Next 3 fail (3% failure rate)

    When:
        place_trade_with_risk_management() is called for the 3rd failure

    Then:
        - CircuitBreakerTripped exception raised
        - Error message indicates stop placement failure rate exceeded 2%
        - Circuit breaker prevents further stop placements

    Rationale:
        Per spec.md guardrail: "If stop-loss orders fail to place >2% of the time,
        trigger circuit breaker and revert to paper trading."

        This prevents cascade failures and protects capital by halting
        automated trading when broker API reliability degrades.

    Pattern: src/trading_bot/error_handling/circuit_breaker.py
    From: spec.md NFR-003, tasks.md T040
    Phase: TDD RED - test MUST FAIL until circuit breaker integrated
    """
    # Arrange
    from src.trading_bot.risk_management.manager import RiskManager
    from src.trading_bot.order_management.models import OrderEnvelope

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

    # Create successful entry envelope
    entry_envelope = OrderEnvelope(
        order_id="ENTRY123",
        symbol="TSLA",
        side="BUY",
        quantity=434,
        limit_price=Decimal("250.30"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    # Create RiskManager
    risk_manager = RiskManager(order_manager=mock_order_manager)

    # Simulate 97 successful placements followed by 3 failures
    # (This tests the >2% threshold: 3/100 = 3% > 2%)

    # First 97 succeed
    for i in range(97):
        # Reset mock for each iteration
        mock_order_manager.reset_mock()

        # Configure mock for success
        stop_envelope = OrderEnvelope(
            order_id=f"STOP{i}",
            symbol="TSLA",
            side="SELL",
            quantity=434,
            limit_price=Decimal("248.00"),
            execution_mode="LIVE",
            submitted_at=datetime.now(UTC)
        )

        target_envelope = OrderEnvelope(
            order_id=f"TARGET{i}",
            symbol="TSLA",
            side="SELL",
            quantity=434,
            limit_price=Decimal("254.90"),
            execution_mode="LIVE",
            submitted_at=datetime.now(UTC)
        )

        mock_order_manager.place_limit_order.side_effect = [
            entry_envelope,
            stop_envelope,
            target_envelope
        ]

        # Should succeed
        envelope = risk_manager.place_trade_with_risk_management(
            plan=position_plan,
            symbol="TSLA"
        )
        assert envelope.stop_order_id == f"STOP{i}"

    # Next 2 failures (brings us to 2% exactly - should not trip yet)
    for i in range(2):
        mock_order_manager.reset_mock()

        # With retry decorator: max_attempts=3 means 4 total attempts (initial + 3 retries)
        # Need to provide enough failures to exhaust all retries
        error_msg = f"Broker timeout on stop placement #{i}"
        mock_order_manager.place_limit_order.side_effect = [
            entry_envelope,  # Entry succeeds
            StopPlacementError(error_msg),  # Stop attempt 1 fails
            StopPlacementError(error_msg),  # Stop retry 1 fails
            StopPlacementError(error_msg),  # Stop retry 2 fails
            StopPlacementError(error_msg),  # Stop retry 3 fails (exhausted)
        ]

        # Configure cancel to succeed
        mock_order_manager.cancel_order.return_value = True

        # Should raise StopPlacementError but NOT CircuitBreakerTripped
        with pytest.raises(StopPlacementError):
            risk_manager.place_trade_with_risk_management(
                plan=position_plan,
                symbol="TSLA"
            )

    # 3rd failure (3% > 2% threshold) - should trip circuit breaker
    mock_order_manager.reset_mock()

    error_msg3 = "Broker timeout on stop placement #3"
    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,
        StopPlacementError(error_msg3),
        StopPlacementError(error_msg3),
        StopPlacementError(error_msg3),
        StopPlacementError(error_msg3),
    ]

    mock_order_manager.cancel_order.return_value = True

    # Act & Assert - Circuit breaker should trip
    with pytest.raises(CircuitBreakerTripped, match="stop placement failure rate.*exceeded"):
        risk_manager.place_trade_with_risk_management(
            plan=position_plan,
            symbol="TSLA"
        )


def test_circuit_breaker_reset_on_success() -> None:
    """
    Test circuit breaker resets failure counter on successful placement.

    Given:
        - 1 successful stop placement
        - 2 failures (2% of 100 total attempts)
        - Another 97 successes

    When:
        Monitoring failure rate over time

    Then:
        - Circuit breaker does NOT trip
        - Failure rate remains below 2% threshold
        - Success resets the failure sliding window

    Rationale:
        Circuit breaker should use sliding window to avoid penalizing
        transient failures that self-resolve. Per circuit_breaker.py pattern,
        record_success() clears all failures.

    From: tasks.md T040
    Phase: TDD RED - test MUST FAIL until success reset implemented
    """
    # Arrange
    from src.trading_bot.risk_management.manager import RiskManager
    from src.trading_bot.order_management.models import OrderEnvelope

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

    mock_order_manager = Mock()

    entry_envelope = OrderEnvelope(
        order_id="ENTRY123",
        symbol="TSLA",
        side="BUY",
        quantity=434,
        limit_price=Decimal("250.30"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    risk_manager = RiskManager(order_manager=mock_order_manager)

    # 1 success
    stop_envelope = OrderEnvelope(
        order_id="STOP_SUCCESS",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("248.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    target_envelope = OrderEnvelope(
        order_id="TARGET_SUCCESS",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("254.90"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,
        stop_envelope,
        target_envelope
    ]

    envelope = risk_manager.place_trade_with_risk_management(
        plan=position_plan,
        symbol="TSLA"
    )
    assert envelope.stop_order_id == "STOP_SUCCESS"

    # 2 failures
    for i in range(2):
        mock_order_manager.reset_mock()

        error_msg = f"Transient failure #{i}"
        mock_order_manager.place_limit_order.side_effect = [
            entry_envelope,
            StopPlacementError(error_msg),
            StopPlacementError(error_msg),
            StopPlacementError(error_msg),
            StopPlacementError(error_msg),
        ]
        mock_order_manager.cancel_order.return_value = True

        with pytest.raises(StopPlacementError):
            risk_manager.place_trade_with_risk_management(
                plan=position_plan,
                symbol="TSLA"
            )

    # 97 more successes - circuit breaker should NOT trip
    for i in range(97):
        mock_order_manager.reset_mock()

        mock_order_manager.place_limit_order.side_effect = [
            entry_envelope,
            stop_envelope,
            target_envelope
        ]

        # Should succeed without CircuitBreakerTripped
        envelope = risk_manager.place_trade_with_risk_management(
            plan=position_plan,
            symbol="TSLA"
        )
        assert envelope.stop_order_id is not None
