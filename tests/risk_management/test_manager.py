"""
Tests for RiskManager module.

Validates position plan calculation orchestration, order placement with stop/target,
JSONL audit logging, and error handling for stop placement failures.

From: specs/stop-loss-automation/tasks.md T014-T015, T020
"""

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.trading_bot.risk_management.calculator import calculate_position_plan
from src.trading_bot.risk_management.exceptions import StopPlacementError


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
