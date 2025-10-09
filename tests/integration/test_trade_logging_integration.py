"""
Integration tests for structured trade logging in TradingBot.

Tests verify that TradingBot properly integrates with StructuredTradeLogger
and maintains backwards compatibility with existing text logging.

Constitution v1.0.0:
- §Audit_Everything: All trades logged to both text and JSONL
- §Data_Integrity: JSONL records contain all required fields
- §Safety_First: Backwards compatibility maintained

Feature: trade-logging
Tasks: T031 [RED], T033 [RED] - Integration tests
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import json
import tempfile
import shutil

from src.trading_bot.bot import TradingBot
from src.trading_bot.logging import TradeRecord


class TestTradeLoggingIntegration:
    """Integration tests for TradingBot + StructuredTradeLogger."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def trading_bot(self, temp_log_dir, monkeypatch):
        """Create TradingBot instance with test log directory."""
        # Create bot with paper trading enabled
        bot = TradingBot(
            paper_trading=True,
            max_position_pct=5.0,
            max_daily_loss_pct=3.0,
            max_consecutive_losses=3,
        )

        # Mock safety checks to always pass (for testing logging integration)
        from unittest.mock import Mock
        mock_result = Mock()
        mock_result.is_safe = True
        mock_result.reason = None
        mock_result.circuit_breaker_triggered = False
        monkeypatch.setattr(bot.safety_checks, 'validate_trade', lambda **kwargs: mock_result)

        # Start bot to enable trading
        bot.start()

        yield bot

        # Stop bot after test
        bot.stop()

    def test_trade_execution_creates_structured_log(self, trading_bot, temp_log_dir):
        """
        T031 [RED]: Verify trade execution logs to JSONL file.

        Given: TradingBot initialized with config
        When: bot.execute_trade() called
        Then: JSONL record exists with correct data

        EXPECTED TO FAIL: execute_trade() doesn't build TradeRecord yet
        """
        # Override bot's structured logger to use temp directory
        from src.trading_bot.logging import StructuredTradeLogger
        trading_bot.structured_logger = StructuredTradeLogger(log_dir=temp_log_dir)

        # Execute test trade
        symbol = "AAPL"
        action = "BUY"
        shares = 100
        price = Decimal("150.50")
        reason = "Test trade execution"

        trading_bot.execute_trade(
            symbol=symbol,
            action=action,
            shares=shares,
            price=price,
            reason=reason
        )

        # Verify JSONL file created
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        jsonl_file = temp_log_dir / f"{today}.jsonl"

        assert jsonl_file.exists(), f"JSONL file not created: {jsonl_file}"

        # Read and verify JSONL content
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 1, f"Expected 1 trade record, found {len(lines)}"

        # Parse JSONL line
        trade_data = json.loads(lines[0])

        # Verify core trade data
        assert trade_data['symbol'] == symbol
        assert trade_data['action'] == action.upper()
        assert trade_data['quantity'] == shares
        assert Decimal(trade_data['price']) == price
        assert Decimal(trade_data['total_value']) == price * shares

        # Verify execution context
        assert trade_data['execution_mode'] in ['PAPER', 'LIVE']
        assert 'order_id' in trade_data
        assert len(trade_data['order_id']) > 0

        # Verify strategy metadata
        assert 'strategy_name' in trade_data
        assert 'entry_type' in trade_data

        # Verify decision audit trail
        assert 'decision_reasoning' in trade_data
        assert trade_data['decision_reasoning'] == reason

        # Verify compliance fields
        assert 'session_id' in trade_data
        assert 'bot_version' in trade_data
        assert 'config_hash' in trade_data

        # Verify timestamp format (ISO 8601 UTC)
        timestamp = trade_data['timestamp']
        assert timestamp.endswith('Z'), "Timestamp must be UTC with 'Z' suffix"
        # Parse timestamp to verify it's valid ISO 8601
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_text_logging_still_works(self, trading_bot, temp_log_dir, caplog):
        """
        T033 [RED]: Verify backwards compatibility with text logs.

        Given: TradingBot initialized
        When: bot.execute_trade() called
        Then: BOTH text logs AND JSONL logs created

        EXPECTED TO FAIL: Need to verify dual logging works
        """
        import logging
        caplog.set_level(logging.INFO)

        # Override bot's structured logger to use temp directory
        from src.trading_bot.logging import StructuredTradeLogger
        trading_bot.structured_logger = StructuredTradeLogger(log_dir=temp_log_dir)

        # Execute test trade
        trading_bot.execute_trade(
            symbol="TSLA",
            action="SELL",
            shares=50,
            price=Decimal("200.75"),
            reason="Test backwards compatibility"
        )

        # Verify text logging (captured by caplog)
        assert "TRADE EXECUTED" in caplog.text
        assert "TSLA" in caplog.text
        assert "SELL" in caplog.text

        # Verify JSONL logging
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        jsonl_file = temp_log_dir / f"{today}.jsonl"

        assert jsonl_file.exists(), "JSONL file not created"

        # Read JSONL content
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 1, "Expected 1 JSONL record"

        # Parse and verify JSONL data
        trade_data = json.loads(lines[0])
        assert trade_data['symbol'] == "TSLA"
        assert trade_data['action'] == "SELL"
        assert trade_data['quantity'] == 50

    def test_multiple_trades_append_to_jsonl(self, trading_bot, temp_log_dir):
        """
        Verify multiple trades append to same daily JSONL file.

        Given: TradingBot initialized
        When: Multiple trades executed on same day
        Then: All trades appended to same JSONL file
        """
        # Override bot's structured logger
        from src.trading_bot.logging import StructuredTradeLogger
        trading_bot.structured_logger = StructuredTradeLogger(log_dir=temp_log_dir)

        # Execute 3 trades
        trades = [
            ("AAPL", "BUY", 100, Decimal("150.00")),
            ("GOOGL", "BUY", 50, Decimal("2800.00")),
            ("MSFT", "SELL", 75, Decimal("380.00")),
        ]

        for symbol, action, shares, price in trades:
            trading_bot.execute_trade(
                symbol=symbol,
                action=action,
                shares=shares,
                price=price,
                reason=f"Test trade {symbol}"
            )

        # Verify all trades in JSONL file
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        jsonl_file = temp_log_dir / f"{today}.jsonl"

        assert jsonl_file.exists()

        with open(jsonl_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 3, f"Expected 3 trades, found {len(lines)}"

        # Verify each trade
        symbols = [json.loads(line)['symbol'] for line in lines]
        assert symbols == ["AAPL", "GOOGL", "MSFT"]
