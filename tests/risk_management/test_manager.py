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


def test_correlation_id_generated_for_position_plan(tmp_path: Path) -> None:
    """
    Test that RiskManager generates correlation_id for position lifecycle tracking.

    T033 Enhancement: Every position should have a unique correlation_id (UUID)
    that traces the complete lifecycle: plan → entry → stop → target → fill.

    Given:
        - PositionPlan created for TSLA
        - RiskManager configured with log_dir=tmp_path

    When:
        log_position_plan() is called

    Then:
        - Log entry contains correlation_id field
        - correlation_id is a valid UUID4
        - correlation_id is consistent across all log entries for same position

    Rationale:
        Correlation IDs enable tracing position lifecycle across distributed logs,
        simplifying debugging, audit compliance, and performance analysis.

    Pattern: src/trading_bot/logging/structured_logger.py correlation_id usage
    From: tasks.md T033
    Phase: TDD RED - test MUST FAIL until correlation_id implemented
    """
    # Arrange
    from src.trading_bot.risk_management.manager import RiskManager

    symbol = "TSLA"
    entry_price = Decimal("250.30")
    stop_price = Decimal("248.00")
    account_balance = Decimal("100000.00")
    account_risk_pct = 1.0
    target_rr = 2.0

    position_plan = calculate_position_plan(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        target_rr=target_rr,
        account_balance=account_balance,
        risk_pct=account_risk_pct
    )

    log_file = tmp_path / "risk-management.jsonl"
    risk_manager = RiskManager(log_dir=tmp_path)

    # Act - Log position plan
    risk_manager.log_position_plan(position_plan, pullback_source="detected")

    # Assert - Verify correlation_id exists and is valid UUID
    assert log_file.exists(), f"Expected log file at {log_file}"

    with open(log_file, 'r', encoding='utf-8') as f:
        log_lines = f.readlines()

    assert len(log_lines) >= 1, "Expected at least one log entry"
    log_entry = json.loads(log_lines[-1])

    # Verify correlation_id field exists
    assert "correlation_id" in log_entry, "Expected correlation_id field in log entry"

    # Verify correlation_id is a valid UUID4
    correlation_id = log_entry["correlation_id"]
    import uuid
    try:
        uuid_obj = uuid.UUID(correlation_id, version=4)
        assert str(uuid_obj) == correlation_id, "correlation_id should be valid UUID4 string"
    except ValueError:
        pytest.fail(f"correlation_id '{correlation_id}' is not a valid UUID4")


def test_correlation_id_included_in_risk_management_envelope() -> None:
    """
    Test that RiskManagementEnvelope tracks correlation_id for position lifecycle.

    T033 Enhancement: correlation_id should be included in RiskManagementEnvelope
    for consistent tracking across entry/stop/target orders.

    Given:
        - PositionPlan with entry/stop/target prices
        - Mocked OrderManager

    When:
        place_trade_with_risk_management() is called

    Then:
        - RiskManagementEnvelope contains correlation_id field
        - correlation_id is a valid UUID4
        - Same correlation_id used for all order placements

    Rationale:
        Envelope must carry correlation_id for downstream order tracking
        and log correlation across order lifecycle events.

    From: tasks.md T033
    Phase: TDD RED - test MUST FAIL until RiskManagementEnvelope updated
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

    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,
        stop_envelope,
        target_envelope
    ]

    risk_manager = RiskManager(order_manager=mock_order_manager)

    # Act
    envelope = risk_manager.place_trade_with_risk_management(
        plan=position_plan,
        symbol="TSLA"
    )

    # Assert - Verify correlation_id exists in envelope
    assert hasattr(envelope, 'correlation_id'), \
        "RiskManagementEnvelope should have correlation_id attribute"
    assert envelope.correlation_id is not None, \
        "correlation_id should not be None"

    # Verify correlation_id is valid UUID4
    import uuid
    try:
        uuid_obj = uuid.UUID(envelope.correlation_id, version=4)
        assert str(uuid_obj) == envelope.correlation_id, \
            "correlation_id should be valid UUID4 string"
    except ValueError:
        pytest.fail(f"correlation_id '{envelope.correlation_id}' is not a valid UUID4")


def test_calculate_position_with_stop_orchestration(tmp_path: Path) -> None:
    """
    Test that calculate_position_with_stop() orchestrates pullback analysis and position planning.

    T032 Implementation: High-level method should:
    1. Call PullbackAnalyzer.analyze_pullback() with price_data
    2. Call calculate_position_plan() with detected stop_price
    3. Log position plan to JSONL
    4. Return PositionPlan

    Given:
        - Symbol: TSLA
        - Entry: $250.30
        - Account balance: $100,000
        - Risk: 1.0%
        - Price data with swing low at $248.00
        - RiskManager with custom log_dir

    When:
        calculate_position_with_stop() is called

    Then:
        - Returns PositionPlan with:
          * stop_price=$248.00 (from pullback analysis)
          * quantity=434 shares
          * target_price=$254.90 (2:1 ratio)
        - Logs position plan to risk-management.jsonl
        - Log contains pullback_source="detected"

    From: specs/stop-loss-automation/tasks.md T032
    """
    # Arrange
    from src.trading_bot.risk_management.manager import RiskManager

    symbol = "TSLA"
    entry_price = Decimal("250.30")
    account_balance = Decimal("100000.00")
    account_risk_pct = 1.0

    # Create price data with swing low at $248.00 (from test_pullback_analyzer.py pattern)
    price_data = [
        # Downtrend leading to swing low
        {"timestamp": datetime(2025, 10, 15, 9, 30, tzinfo=UTC), "low": Decimal("252.00"), "close": Decimal("251.50")},
        {"timestamp": datetime(2025, 10, 15, 9, 35, tzinfo=UTC), "low": Decimal("251.00"), "close": Decimal("250.50")},
        {"timestamp": datetime(2025, 10, 15, 9, 40, tzinfo=UTC), "low": Decimal("250.00"), "close": Decimal("249.50")},
        {"timestamp": datetime(2025, 10, 15, 9, 45, tzinfo=UTC), "low": Decimal("249.50"), "close": Decimal("249.00")},
        {"timestamp": datetime(2025, 10, 15, 9, 50, tzinfo=UTC), "low": Decimal("249.00"), "close": Decimal("248.50")},
        {"timestamp": datetime(2025, 10, 15, 9, 55, tzinfo=UTC), "low": Decimal("248.50"), "close": Decimal("248.20")},
        {"timestamp": datetime(2025, 10, 15, 10, 0, tzinfo=UTC), "low": Decimal("248.20"), "close": Decimal("248.10")},
        {"timestamp": datetime(2025, 10, 15, 10, 5, tzinfo=UTC), "low": Decimal("248.10"), "close": Decimal("248.00")},
        {"timestamp": datetime(2025, 10, 15, 10, 10, tzinfo=UTC), "low": Decimal("248.05"), "close": Decimal("248.00")},
        {"timestamp": datetime(2025, 10, 15, 10, 15, tzinfo=UTC), "low": Decimal("248.00"), "close": Decimal("248.00")},
        # SWING LOW: Index 10
        {"timestamp": datetime(2025, 10, 15, 10, 20, tzinfo=UTC), "low": Decimal("248.00"), "close": Decimal("248.10")},
        # Confirmation candles (higher lows)
        {"timestamp": datetime(2025, 10, 15, 10, 25, tzinfo=UTC), "low": Decimal("248.20"), "close": Decimal("248.50")},
        {"timestamp": datetime(2025, 10, 15, 10, 30, tzinfo=UTC), "low": Decimal("248.50"), "close": Decimal("249.00")},
        # Recovery
        {"timestamp": datetime(2025, 10, 15, 10, 35, tzinfo=UTC), "low": Decimal("249.00"), "close": Decimal("249.50")},
        {"timestamp": datetime(2025, 10, 15, 10, 40, tzinfo=UTC), "low": Decimal("249.50"), "close": Decimal("250.00")},
        {"timestamp": datetime(2025, 10, 15, 10, 45, tzinfo=UTC), "low": Decimal("249.80"), "close": Decimal("250.20")},
        {"timestamp": datetime(2025, 10, 15, 10, 50, tzinfo=UTC), "low": Decimal("250.00"), "close": Decimal("250.30")},
        {"timestamp": datetime(2025, 10, 15, 10, 55, tzinfo=UTC), "low": Decimal("250.20"), "close": Decimal("250.50")},
        {"timestamp": datetime(2025, 10, 15, 11, 0, tzinfo=UTC), "low": Decimal("250.30"), "close": Decimal("250.60")},
        {"timestamp": datetime(2025, 10, 15, 11, 5, tzinfo=UTC), "low": Decimal("250.40"), "close": Decimal("250.30")},
    ]

    log_file = tmp_path / "risk-management.jsonl"
    risk_manager = RiskManager(log_dir=tmp_path)

    # Act - Call high-level orchestration method
    position_plan = risk_manager.calculate_position_with_stop(
        symbol=symbol,
        entry_price=entry_price,
        account_balance=account_balance,
        account_risk_pct=account_risk_pct,
        price_data=price_data,
    )

    # Assert - Verify PositionPlan structure
    assert isinstance(position_plan, PositionPlan)
    assert position_plan.symbol == "TSLA"
    assert position_plan.entry_price == Decimal("250.30")
    assert position_plan.stop_price == Decimal("248.00"), "Should detect swing low at $248.00"
    assert position_plan.quantity == 434, "Should calculate correct quantity based on risk"
    assert position_plan.target_price == Decimal("254.90"), "Should calculate 2:1 target"
    assert position_plan.risk_amount == Decimal("1000.00"), "Should risk 1% of $100k"

    # Assert - Verify JSONL logging
    assert log_file.exists(), f"Expected log file at {log_file}"

    with open(log_file, 'r', encoding='utf-8') as f:
        log_lines = f.readlines()

    assert len(log_lines) >= 1, "Expected at least one log entry"
    log_entry = json.loads(log_lines[-1])

    # Verify log structure
    assert log_entry["action"] == "position_plan_created"
    assert log_entry["symbol"] == "TSLA"
    assert float(log_entry["entry_price"]) == 250.30
    assert float(log_entry["stop_price"]) == 248.00
    assert log_entry["quantity"] == 434
    assert log_entry["pullback_source"] == "detected", "Should use detected pullback, not default"


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

    # 2. Stop order placement fails (raises StopPlacementError on all retry attempts)
    # With T039 retry decorator: max_attempts=3 means 4 total attempts (initial + 3 retries)
    # Configure to fail on all attempts so entry gets cancelled
    error_message = "Broker timeout: Failed to place stop-loss order for TSLA at $248.00"
    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,  # First call: entry succeeds
        StopPlacementError(error_message),  # Second call: stop attempt 1 fails
        StopPlacementError(error_message),  # Third call: stop retry 1 fails
        StopPlacementError(error_message),  # Fourth call: stop retry 2 fails
        StopPlacementError(error_message),  # Fifth call: stop retry 3 fails (exhausted)
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

    # 1. Entry order was placed first, then stop retried 4 times (1 initial + 3 retries)
    # With T039 retry logic: 1 entry + 4 stop attempts (1 initial + 3 retries) = 5 total
    assert mock_order_manager.place_limit_order.call_count == 5, \
        f"Expected 5 calls to place_limit_order (1 entry + 4 stop attempts), got {mock_order_manager.place_limit_order.call_count}"

    # 2. Entry order was cancelled as guardrail cleanup
    mock_order_manager.cancel_order.assert_called_once_with(
        order_id="ENTRY_ORDER_123"
    )

    # 3. Error was logged with correlation_id
    # TODO: Add logging assertion once logger is integrated (T026)
    # risk_manager.logger.log_error.assert_called_once()


def test_retry_on_transient_stop_placement_failure() -> None:
    """
    Test that RiskManager retries on transient broker failures with exponential backoff.

    This test validates the resilience requirement (NFR-007) from spec.md:
    "Stop and target placement MUST retry transient failures (network timeout, 5xx)
    up to 3 times before escalating to circuit breaker."

    Given:
        - Entry order submitted successfully (order_id="ENTRY_ORDER_123")
        - First stop placement call raises RetriableError (network timeout)
        - Second stop placement call succeeds
        - Target placement succeeds

    When:
        place_trade_with_risk_management(plan, symbol="TSLA")

    Then:
        1. Calls OrderManager.place_limit_order() for entry → succeeds
        2. Calls OrderManager.place_limit_order() for stop → fails with RetriableError
        3. Retries stop placement after exponential backoff delay
        4. Second stop placement attempt → succeeds (order_id="STOP456")
        5. Calls OrderManager.place_limit_order() for target → succeeds
        6. Returns RiskManagementEnvelope with all three order IDs
        7. Does NOT cancel entry order (transient failure recovered)

    Rationale:
        Network timeouts and 5xx errors are transient and recoverable. Implementing
        retry logic with exponential backoff improves system resilience without
        requiring manual intervention. The @with_retry decorator from
        src/trading_bot/error_handling/retry.py should be applied to the internal
        order placement logic.

    Pattern: src/trading_bot/error_handling/retry.py @with_retry decorator
    From: spec.md NFR-007, tasks.md T038
    Phase: TDD RED - test MUST FAIL until @with_retry decorator applied
    """
    # Arrange: Create sample PositionPlan (reuse spec scenario 1)
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

    # Import RetriableError from error handling framework
    from src.trading_bot.error_handling.exceptions import RetriableError

    # Create mock OrderManager with transient failure scenario
    mock_order_manager = Mock()

    # Import OrderEnvelope for realistic mock returns
    from src.trading_bot.order_management.models import OrderEnvelope

    # Configure mock behavior:
    # 1. Entry order succeeds
    entry_envelope = OrderEnvelope(
        order_id="ENTRY_ORDER_123",
        symbol="TSLA",
        side="BUY",
        quantity=434,
        limit_price=Decimal("250.30"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    # 2. Stop order succeeds on retry
    stop_envelope = OrderEnvelope(
        order_id="STOP456",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("248.00"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    # 3. Target order succeeds
    target_envelope = OrderEnvelope(
        order_id="TARGET789",
        symbol="TSLA",
        side="SELL",
        quantity=434,
        limit_price=Decimal("254.90"),
        execution_mode="LIVE",
        submitted_at=datetime.now(UTC)
    )

    # Configure place_limit_order to fail on first stop attempt, succeed on retry
    # Order of calls: entry (success), stop (fail), stop (retry success), target (success)
    mock_order_manager.place_limit_order.side_effect = [
        entry_envelope,  # First call: entry succeeds
        RetriableError("Network timeout: Connection failed after 30s"),  # Second call: stop fails
        stop_envelope,  # Third call: stop retry succeeds
        target_envelope  # Fourth call: target succeeds
    ]

    # Import RiskManager
    from src.trading_bot.risk_management.manager import RiskManager

    # Create RiskManager with mocked OrderManager
    risk_manager = RiskManager(order_manager=mock_order_manager)

    # Act: Call place_trade_with_risk_management
    # This will FAIL in RED phase because @with_retry decorator is not applied yet
    envelope = risk_manager.place_trade_with_risk_management(
        plan=position_plan,
        symbol="TSLA"
    )

    # Assert: Verify retry behavior and successful recovery
    # 1. Total of 4 calls to place_limit_order (entry + stop fail + stop retry + target)
    assert mock_order_manager.place_limit_order.call_count == 4, \
        f"Expected 4 calls (entry, stop fail, stop retry, target), got {mock_order_manager.place_limit_order.call_count}"

    # 2. Entry order was NOT cancelled (transient failure recovered)
    mock_order_manager.cancel_order.assert_not_called()

    # 3. Envelope contains all three order IDs (successful recovery)
    assert envelope.entry_order_id == "ENTRY_ORDER_123"
    assert envelope.stop_order_id == "STOP456"
    assert envelope.target_order_id == "TARGET789"
    assert envelope.status == "pending"

    # 4. Verify order call sequence (entry → stop fail → stop retry → target)
    calls = mock_order_manager.place_limit_order.call_args_list

    # Entry order (first call)
    entry_call = calls[0][0][0]
    assert entry_call.symbol == "TSLA"
    assert entry_call.side == "BUY"
    assert entry_call.quantity == 434

    # Stop order (second call - fails, third call - retries)
    stop_call_1 = calls[1][0][0]
    assert stop_call_1.symbol == "TSLA"
    assert stop_call_1.side == "SELL"
    assert stop_call_1.reference_price == Decimal("248.00")

    stop_call_2 = calls[2][0][0]
    assert stop_call_2.symbol == "TSLA"
    assert stop_call_2.side == "SELL"
    assert stop_call_2.reference_price == Decimal("248.00")

    # Target order (fourth call)
    target_call = calls[3][0][0]
    assert target_call.symbol == "TSLA"
    assert target_call.side == "SELL"
    assert target_call.reference_price == Decimal("254.90")
