"""
Smoke Test: Risk Management System

Tests the complete risk management system for stop-loss automation.
Validates all components work together correctly in realistic scenario.

Feature: stop-loss-automation
Task: T043 [P] - Add smoke test script for risk management
Constitution v1.0.0:
- §Risk_Management: Validate stop-loss calculations and position sizing
- §Data_Integrity: Validate all data correct through pipeline
- §Safety_First: Ensure risk checks prevent invalid trades
"""

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

import pytest

from src.trading_bot.config import Config
from src.trading_bot.risk_management.calculator import calculate_position_plan
from src.trading_bot.risk_management.config import RiskManagementConfig
from src.trading_bot.risk_management.exceptions import PositionPlanningError


class TestRiskManagementSmoke:
    """End-to-end smoke tests for risk management system."""

    def test_config_loads_risk_management_section(self, tmp_path: Path) -> None:
        """
        Test that config.json properly loads risk_management section.

        Workflow:
        1. Create minimal config.json with risk_management section
        2. Load config using Config.from_env_and_json()
        3. Verify RiskManagementConfig populated correctly
        4. Validate all fields match expected values

        Expected: <30s execution time

        Constitution compliance:
        - §Risk_Management: Config validation prevents invalid parameters
        - §Data_Integrity: All config fields validated
        """
        start_time = time.time()

        # Create minimal config.json with risk_management section
        config_data: Dict[str, Any] = {
            "risk_management": {
                "account_risk_pct": 1.5,
                "min_risk_reward_ratio": 2.5,
                "default_stop_pct": 2.5,
                "trailing_enabled": True,
                "pullback_lookback_candles": 25,
                "trailing_breakeven_threshold": 1.0,
                "strategy_overrides": {
                    "breakout": {
                        "account_risk_pct": 2.0,
                        "min_risk_reward_ratio": 3.0,
                    }
                },
            }
        }

        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Load config from file
        config = Config.from_env_and_json(str(config_file))

        # Verify RiskManagementConfig populated correctly
        assert config.risk_management is not None, (
            "RiskManagementConfig should be populated"
        )

        risk_config = config.risk_management

        # Validate global defaults
        assert risk_config.account_risk_pct == 1.5, (
            f"account_risk_pct mismatch: expected 1.5, got {risk_config.account_risk_pct}"
        )
        assert risk_config.min_risk_reward_ratio == 2.5, (
            f"min_risk_reward_ratio mismatch: expected 2.5, got {risk_config.min_risk_reward_ratio}"
        )
        assert risk_config.default_stop_pct == 2.5, (
            f"default_stop_pct mismatch: expected 2.5, got {risk_config.default_stop_pct}"
        )
        assert risk_config.trailing_enabled is True, (
            f"trailing_enabled should be True, got {risk_config.trailing_enabled}"
        )
        assert risk_config.pullback_lookback_candles == 25, (
            f"pullback_lookback_candles mismatch: expected 25, got {risk_config.pullback_lookback_candles}"
        )
        assert risk_config.trailing_breakeven_threshold == 1.0, (
            f"trailing_breakeven_threshold mismatch: expected 1.0, got {risk_config.trailing_breakeven_threshold}"
        )

        # Validate strategy overrides
        assert "breakout" in risk_config.strategy_overrides, (
            "breakout strategy override should exist"
        )

        breakout_override = risk_config.strategy_overrides["breakout"]
        assert breakout_override["account_risk_pct"] == 2.0, (
            f"breakout account_risk_pct mismatch: expected 2.0, got {breakout_override['account_risk_pct']}"
        )
        assert breakout_override["min_risk_reward_ratio"] == 3.0, (
            f"breakout min_risk_reward_ratio mismatch: expected 3.0, got {breakout_override['min_risk_reward_ratio']}"
        )

        # Validate config passes validation
        risk_config.validate()

        elapsed_time = time.time() - start_time
        assert elapsed_time < 30.0, (
            f"Config loading took {elapsed_time:.2f}s (expected <30s)"
        )

        print(f"\n[PASS] Config loading smoke test completed in {elapsed_time:.3f}s")
        print("   - risk_management section loaded: OK")
        print("   - Global defaults validated: OK")
        print("   - Strategy overrides validated: OK")
        print("   - Config validation passed: OK")

    def test_calculate_position_plan_with_mock_data(self) -> None:
        """
        Test calculate_position_plan() with realistic mock data.

        Workflow:
        1. Create realistic entry/stop/target parameters
        2. Calculate position plan using calculate_position_plan()
        3. Verify all fields populated correctly
        4. Validate risk-reward ratio meets minimum
        5. Verify position sizing math is correct

        Expected: <30s execution time

        Constitution compliance:
        - §Risk_Management: Position sizing calculated correctly
        - §Data_Integrity: All fields validated
        - §Safety_First: Risk limits enforced
        """
        start_time = time.time()

        # Realistic mock data for AAPL trade
        symbol = "AAPL"
        entry_price = Decimal("150.00")
        stop_price = Decimal("147.00")  # 2% stop (3.00 risk per share)
        target_rr = 2.0  # 2:1 risk-reward ratio
        account_balance = Decimal("10000.00")
        risk_pct = 1.0  # Risk 1% of account ($100)

        # Calculate position plan
        plan = calculate_position_plan(
            symbol=symbol,
            entry_price=entry_price,
            stop_price=stop_price,
            target_rr=target_rr,
            account_balance=account_balance,
            risk_pct=risk_pct,
            min_risk_reward_ratio=2.0,
            pullback_source="manual",
        )

        # Verify all fields populated
        assert plan.symbol == symbol, (
            f"Symbol mismatch: expected {symbol}, got {plan.symbol}"
        )
        assert plan.entry_price == entry_price, (
            f"Entry price mismatch: expected {entry_price}, got {plan.entry_price}"
        )
        assert plan.stop_price == stop_price, (
            f"Stop price mismatch: expected {stop_price}, got {plan.stop_price}"
        )

        # Validate position sizing calculation
        # Risk per share = entry - stop = $150.00 - $147.00 = $3.00
        # Risk amount = $10,000 * 1% = $100.00
        # Quantity = $100.00 / $3.00 = 33.33 -> 33 shares (int)
        expected_quantity = 33
        assert plan.quantity == expected_quantity, (
            f"Quantity mismatch: expected {expected_quantity}, got {plan.quantity}"
        )

        expected_risk_amount = Decimal("100.00")
        assert plan.risk_amount == expected_risk_amount, (
            f"Risk amount mismatch: expected {expected_risk_amount}, got {plan.risk_amount}"
        )

        # Validate target price calculation
        # Risk per share = $3.00
        # Target = entry + (risk_per_share * target_rr) = $150.00 + ($3.00 * 2.0) = $156.00
        expected_target = Decimal("156.00")
        assert plan.target_price == expected_target, (
            f"Target price mismatch: expected {expected_target}, got {plan.target_price}"
        )

        # Validate reward calculation
        # Reward per share = target - entry = $156.00 - $150.00 = $6.00
        # Reward amount = 33 * $6.00 = $198.00
        expected_reward = Decimal("198.00")
        assert plan.reward_amount == expected_reward, (
            f"Reward amount mismatch: expected {expected_reward}, got {plan.reward_amount}"
        )

        # Validate actual reward ratio
        # Actual ratio = reward_amount / risk_amount = $198.00 / $100.00 = 1.98
        # (Slightly less than 2.0 due to integer quantity rounding)
        expected_ratio = 1.98
        assert abs(plan.reward_ratio - expected_ratio) < 0.01, (
            f"Reward ratio mismatch: expected ~{expected_ratio}, got {plan.reward_ratio}"
        )

        # Validate metadata
        assert plan.pullback_source == "manual", (
            f"Pullback source mismatch: expected 'manual', got {plan.pullback_source}"
        )
        assert plan.pullback_price == stop_price, (
            f"Pullback price should equal stop price: expected {stop_price}, got {plan.pullback_price}"
        )

        # Validate created_at timestamp exists
        assert plan.created_at is not None, "created_at should not be None"

        elapsed_time = time.time() - start_time
        assert elapsed_time < 30.0, (
            f"Position plan calculation took {elapsed_time:.2f}s (expected <30s)"
        )

        print(f"\n[PASS] Position plan calculation smoke test completed in {elapsed_time:.3f}s")
        print(f"   - Symbol: {plan.symbol}")
        print(f"   - Entry: ${plan.entry_price}, Stop: ${plan.stop_price}, Target: ${plan.target_price}")
        print(f"   - Quantity: {plan.quantity} shares")
        print(f"   - Risk: ${plan.risk_amount}, Reward: ${plan.reward_amount}")
        print(f"   - Reward ratio: {plan.reward_ratio:.2f}:1")
        print("   - All calculations validated: OK")

    def test_jsonl_logging_works(self, tmp_path: Path) -> None:
        """
        Test that position plan data can be logged to JSONL format.

        Workflow:
        1. Calculate position plan
        2. Convert to JSON-serializable dict
        3. Write to JSONL file
        4. Read back and verify data integrity
        5. Validate all Decimal fields preserved correctly

        Expected: <30s execution time

        Constitution compliance:
        - §Audit_Everything: Position plans logged for audit trail
        - §Data_Integrity: All data preserved correctly in JSONL
        """
        start_time = time.time()

        # Create position plan
        plan = calculate_position_plan(
            symbol="MSFT",
            entry_price=Decimal("380.50"),
            stop_price=Decimal("372.69"),  # 2.05% stop
            target_rr=2.0,
            account_balance=Decimal("50000.00"),
            risk_pct=1.0,
            min_risk_reward_ratio=2.0,
            pullback_source="pullback_analyzer",
        )

        # Convert to JSON-serializable dict
        plan_dict = {
            "symbol": plan.symbol,
            "entry_price": str(plan.entry_price),
            "stop_price": str(plan.stop_price),
            "target_price": str(plan.target_price),
            "quantity": plan.quantity,
            "risk_amount": str(plan.risk_amount),
            "reward_amount": str(plan.reward_amount),
            "reward_ratio": plan.reward_ratio,
            "pullback_source": plan.pullback_source,
            "pullback_price": str(plan.pullback_price) if plan.pullback_price else None,
            "created_at": plan.created_at.isoformat(),
        }

        # Write to JSONL file
        log_dir = tmp_path / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "position_plans.jsonl"

        with open(log_file, "w") as f:
            f.write(json.dumps(plan_dict) + "\n")

        # Verify file exists
        assert log_file.exists(), f"JSONL log file not created: {log_file}"

        # Read back and verify data integrity
        with open(log_file, "r") as f:
            lines = [line for line in f.read().split("\n") if line.strip()]

        assert len(lines) == 1, f"Expected 1 record, found {len(lines)}"

        loaded_data = json.loads(lines[0])

        # Validate all fields preserved
        assert loaded_data["symbol"] == "MSFT", (
            f"Symbol mismatch: expected MSFT, got {loaded_data['symbol']}"
        )
        assert loaded_data["entry_price"] == "380.50", (
            f"Entry price mismatch: expected '380.50', got {loaded_data['entry_price']}"
        )
        assert loaded_data["stop_price"] == "372.69", (
            f"Stop price mismatch: expected '372.69', got {loaded_data['stop_price']}"
        )
        assert loaded_data["pullback_source"] == "pullback_analyzer", (
            f"Pullback source mismatch: expected 'pullback_analyzer', got {loaded_data['pullback_source']}"
        )

        # Validate Decimal fields can be restored
        restored_entry = Decimal(loaded_data["entry_price"])
        assert restored_entry == plan.entry_price, (
            f"Decimal restoration failed: expected {plan.entry_price}, got {restored_entry}"
        )

        restored_stop = Decimal(loaded_data["stop_price"])
        assert restored_stop == plan.stop_price, (
            f"Decimal restoration failed: expected {plan.stop_price}, got {restored_stop}"
        )

        restored_risk = Decimal(loaded_data["risk_amount"])
        assert restored_risk == plan.risk_amount, (
            f"Decimal restoration failed: expected {plan.risk_amount}, got {restored_risk}"
        )

        elapsed_time = time.time() - start_time
        assert elapsed_time < 30.0, (
            f"JSONL logging test took {elapsed_time:.2f}s (expected <30s)"
        )

        print(f"\n[PASS] JSONL logging smoke test completed in {elapsed_time:.3f}s")
        print(f"   - Position plan serialized to JSONL: OK")
        print(f"   - Data read back successfully: OK")
        print(f"   - Decimal precision preserved: OK")
        print(f"   - All fields validated: OK")

    def test_risk_validation_prevents_invalid_trades(self) -> None:
        """
        Test that risk validation prevents invalid trade setups.

        Workflow:
        1. Test stop distance too tight (<0.5%)
        2. Test stop distance in dead zone (0.5%-0.7%)
        3. Test stop distance too wide (>10%)
        4. Test stop in wrong direction (above entry for long)
        5. Test risk-reward ratio below minimum
        6. Verify all raise PositionPlanningError

        Expected: <30s execution time

        Constitution compliance:
        - §Risk_Management: Invalid trades rejected
        - §Safety_First: Prevent high-risk setups
        """
        start_time = time.time()

        # Test 1: Stop distance too tight (0.4% < 0.5% minimum)
        with pytest.raises(PositionPlanningError, match="too tight"):
            calculate_position_plan(
                symbol="AAPL",
                entry_price=Decimal("100.00"),
                stop_price=Decimal("99.60"),  # 0.4% stop (too tight)
                target_rr=2.0,
                account_balance=Decimal("10000.00"),
                risk_pct=1.0,
            )

        # Test 2: Stop distance in dead zone (0.6% between 0.5% and 0.7%)
        with pytest.raises(PositionPlanningError, match="too tight"):
            calculate_position_plan(
                symbol="AAPL",
                entry_price=Decimal("100.00"),
                stop_price=Decimal("99.40"),  # 0.6% stop (dead zone)
                target_rr=2.0,
                account_balance=Decimal("10000.00"),
                risk_pct=1.0,
            )

        # Test 3: Stop distance too wide (>10%)
        with pytest.raises(PositionPlanningError, match="above maximum"):
            calculate_position_plan(
                symbol="AAPL",
                entry_price=Decimal("100.00"),
                stop_price=Decimal("89.00"),  # 11% stop (too wide)
                target_rr=2.0,
                account_balance=Decimal("10000.00"),
                risk_pct=1.0,
            )

        # Test 4: Stop in wrong direction (above entry for long)
        with pytest.raises(PositionPlanningError, match="must be below entry"):
            calculate_position_plan(
                symbol="AAPL",
                entry_price=Decimal("100.00"),
                stop_price=Decimal("102.00"),  # Stop above entry (invalid for long)
                target_rr=2.0,
                account_balance=Decimal("10000.00"),
                risk_pct=1.0,
            )

        # Test 5: Risk-reward ratio below minimum
        with pytest.raises(PositionPlanningError, match="below minimum"):
            calculate_position_plan(
                symbol="AAPL",
                entry_price=Decimal("100.00"),
                stop_price=Decimal("98.00"),  # 2% stop
                target_rr=1.5,  # 1.5:1 ratio (below 2.0 minimum)
                account_balance=Decimal("10000.00"),
                risk_pct=1.0,
                min_risk_reward_ratio=2.0,
            )

        elapsed_time = time.time() - start_time
        assert elapsed_time < 30.0, (
            f"Risk validation test took {elapsed_time:.2f}s (expected <30s)"
        )

        print(f"\n[PASS] Risk validation smoke test completed in {elapsed_time:.3f}s")
        print("   - Stop distance too tight: REJECTED ✓")
        print("   - Stop distance in dead zone: REJECTED ✓")
        print("   - Stop distance too wide: REJECTED ✓")
        print("   - Stop in wrong direction: REJECTED ✓")
        print("   - Risk-reward ratio too low: REJECTED ✓")
        print("   - All invalid trades prevented: OK")
