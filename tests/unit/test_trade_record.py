"""
Unit tests for TradeRecord dataclass (TDD RED Phase)

Tests Constitution v1.0.0 requirements:
- §Data_Integrity: All trade data validated and typed
- §Audit_Everything: Complete decision audit trail
- §Safety_First: Validation prevents invalid trade records

Feature: trade-logging
Tasks: T004-T008 [RED] - Write failing tests before implementation
"""

import json
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

# This import will FAIL - TradeRecord doesn't exist yet (TDD RED phase)
from src.trading_bot.logging.trade_record import TradeRecord


class TestTradeRecordValidation:
    """Test TradeRecord dataclass validation rules."""

    # =========================================================================
    # T004 [RED]: Test TradeRecord requires core fields
    # =========================================================================

    def test_trade_record_requires_core_fields(self) -> None:
        """Should raise TypeError if core fields are missing (T004).

        Core fields (FR-002):
        - timestamp: ISO 8601 UTC string
        - symbol: Stock ticker (1-5 uppercase alphanumeric)
        - action: "BUY" or "SELL"
        - quantity: Positive integer
        - price: Positive Decimal

        This test MUST FAIL because TradeRecord doesn't exist yet.
        """
        # Missing timestamp
        with pytest.raises(TypeError) as exc_info:
            TradeRecord(
                symbol="AAPL",
                action="BUY",
                quantity=100,
                price=Decimal("150.50"),
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "timestamp" in str(exc_info.value).lower()

        # Missing symbol
        with pytest.raises(TypeError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action="BUY",
                quantity=100,
                price=Decimal("150.50"),
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "symbol" in str(exc_info.value).lower()

        # Missing action
        with pytest.raises(TypeError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="AAPL",
                quantity=100,
                price=Decimal("150.50"),
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "action" in str(exc_info.value).lower()

        # Missing quantity
        with pytest.raises(TypeError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="AAPL",
                action="BUY",
                price=Decimal("150.50"),
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "quantity" in str(exc_info.value).lower()

        # Missing price
        with pytest.raises(TypeError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="AAPL",
                action="BUY",
                quantity=100,
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "price" in str(exc_info.value).lower()

    # =========================================================================
    # T005 [RED]: Test TradeRecord validates symbol format
    # =========================================================================

    def test_trade_record_validates_symbol_format(self) -> None:
        """Should raise ValueError for invalid symbol formats (T005).

        Symbol validation rules (plan.md):
        - Uppercase 1-5 chars
        - Alphanumeric only (no special chars)

        Invalid cases:
        - "aapl" (lowercase)
        - "TOOLONG" (>5 chars)
        - "AA-PL" (special char)

        This test MUST FAIL because TradeRecord doesn't exist yet.
        """
        # Lowercase symbol
        with pytest.raises(ValueError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="aapl",  # Invalid: lowercase
                action="BUY",
                quantity=100,
                price=Decimal("150.50"),
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "uppercase" in str(exc_info.value).lower() or "symbol" in str(exc_info.value).lower()

        # Too long symbol
        with pytest.raises(ValueError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="TOOLONG",  # Invalid: >5 chars
                action="BUY",
                quantity=100,
                price=Decimal("150.50"),
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "5" in str(exc_info.value) or "length" in str(exc_info.value).lower()

        # Special character in symbol
        with pytest.raises(ValueError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="AA-PL",  # Invalid: special char
                action="BUY",
                quantity=100,
                price=Decimal("150.50"),
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "alphanumeric" in str(exc_info.value).lower() or "symbol" in str(exc_info.value).lower()

    # =========================================================================
    # T006 [RED]: Test TradeRecord validates numeric constraints
    # =========================================================================

    def test_trade_record_validates_numeric_constraints(self) -> None:
        """Should raise ValueError for invalid numeric values (T006).

        Validation rules (plan.md):
        - Quantity: Positive integer, max 10,000 shares
        - Price: Positive Decimal

        Invalid cases:
        - quantity = -100 (negative)
        - price = -50.00 (negative)
        - quantity = 15000 (>10,000)

        This test MUST FAIL because TradeRecord doesn't exist yet.
        """
        # Negative quantity
        with pytest.raises(ValueError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="AAPL",
                action="BUY",
                quantity=-100,  # Invalid: negative
                price=Decimal("150.50"),
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "positive" in str(exc_info.value).lower() or "quantity" in str(exc_info.value).lower()

        # Negative price
        with pytest.raises(ValueError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="AAPL",
                action="BUY",
                quantity=100,
                price=Decimal("-50.00"),  # Invalid: negative
                total_value=Decimal("15050.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "positive" in str(exc_info.value).lower() or "price" in str(exc_info.value).lower()

        # Quantity exceeds maximum
        with pytest.raises(ValueError) as exc_info:
            TradeRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                symbol="AAPL",
                action="BUY",
                quantity=15000,  # Invalid: >10,000
                price=Decimal("150.50"),
                total_value=Decimal("2257500.00"),
                order_id="ORD123",
                execution_mode="PAPER",
                account_id=None,
                strategy_name="test",
                entry_type="breakout",
                stop_loss=None,
                target=None,
                decision_reasoning="test",
                indicators_used=[],
                risk_reward_ratio=None,
                outcome=None,
                profit_loss=None,
                hold_duration_seconds=None,
                exit_timestamp=None,
                exit_reasoning=None,
                slippage=None,
                commission=None,
                net_profit_loss=None,
                session_id="SES-001",
                bot_version="1.0.0",
                config_hash="abc123"
            )
        assert "10000" in str(exc_info.value) or "maximum" in str(exc_info.value).lower()


class TestTradeRecordSerialization:
    """Test TradeRecord JSON serialization methods."""

    # =========================================================================
    # T007 [RED]: Test TradeRecord to_json() handles Decimal fields
    # =========================================================================

    def test_trade_record_to_json_handles_decimals(self) -> None:
        """Should serialize Decimal fields as strings in JSON (T007).

        Requirements:
        - Decimal fields converted to strings (plan.md line 141-142)
        - All 27 fields present in output dict
        - Output is JSON-safe (no Decimal objects)

        This test MUST FAIL because TradeRecord.to_json() doesn't exist yet.
        """
        record = TradeRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol="AAPL",
            action="BUY",
            quantity=100,
            price=Decimal("150.50"),
            total_value=Decimal("15050.00"),
            order_id="ORD123",
            execution_mode="PAPER",
            account_id=None,
            strategy_name="test",
            entry_type="breakout",
            stop_loss=Decimal("148.00"),
            target=Decimal("156.00"),
            decision_reasoning="test",
            indicators_used=["VWAP"],
            risk_reward_ratio=2.2,
            outcome="open",
            profit_loss=None,
            hold_duration_seconds=None,
            exit_timestamp=None,
            exit_reasoning=None,
            slippage=Decimal("0.02"),
            commission=Decimal("0.00"),
            net_profit_loss=None,
            session_id="SES-001",
            bot_version="1.0.0",
            config_hash="abc123"
        )

        json_dict = record.to_json()

        # Decimal fields should be strings
        assert isinstance(json_dict["price"], str)
        assert json_dict["price"] == "150.50"
        assert isinstance(json_dict["total_value"], str)
        assert json_dict["total_value"] == "15050.00"
        assert isinstance(json_dict["stop_loss"], str)
        assert json_dict["stop_loss"] == "148.00"
        assert isinstance(json_dict["slippage"], str)
        assert json_dict["slippage"] == "0.02"

        # All 27 fields should be present
        assert len(json_dict) == 27

        # Should be JSON-serializable (no Decimal objects)
        json_str = json.dumps(json_dict)
        assert isinstance(json_str, str)

    # =========================================================================
    # T008 [RED]: Test TradeRecord to_jsonl_line() produces single line
    # =========================================================================

    def test_trade_record_to_jsonl_is_single_line(self) -> None:
        """Should serialize to single-line JSONL format (T008).

        Requirements (plan.md line 144-146):
        - Output is single line (no newlines)
        - No pretty printing (compact separators)
        - Parseable by json.loads()

        This test MUST FAIL because TradeRecord.to_jsonl_line() doesn't exist yet.
        """
        record = TradeRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol="AAPL",
            action="BUY",
            quantity=100,
            price=Decimal("150.50"),
            total_value=Decimal("15050.00"),
            order_id="ORD123",
            execution_mode="PAPER",
            account_id=None,
            strategy_name="test",
            entry_type="breakout",
            stop_loss=Decimal("148.00"),
            target=Decimal("156.00"),
            decision_reasoning="test reasoning",
            indicators_used=["VWAP", "EMA-9"],
            risk_reward_ratio=2.2,
            outcome="open",
            profit_loss=None,
            hold_duration_seconds=None,
            exit_timestamp=None,
            exit_reasoning=None,
            slippage=Decimal("0.02"),
            commission=Decimal("0.00"),
            net_profit_loss=None,
            session_id="SES-001",
            bot_version="1.0.0",
            config_hash="abc123"
        )

        jsonl_line = record.to_jsonl_line()

        # Should be single line (no newlines or whitespace)
        assert "\n" not in jsonl_line
        assert "  " not in jsonl_line  # No pretty-print spacing

        # Should be parseable by json.loads()
        parsed = json.loads(jsonl_line)
        assert isinstance(parsed, dict)
        assert parsed["symbol"] == "AAPL"
        assert parsed["price"] == "150.50"  # Decimal as string

        # Should use compact separators
        assert ", " not in jsonl_line  # Compact separator is ',' not ', '
