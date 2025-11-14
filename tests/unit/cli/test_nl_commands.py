"""
Unit tests for Natural Language Command CLI.

Tests intent extraction from natural language queries.
"""

import pytest

from src.trading_bot.cli.nl_commands import (
    Intent,
    extract_intent,
    format_response,
    ParsedIntent,
)


class TestIntentExtraction:
    """Unit tests for intent extraction."""

    def test_extract_status_intent(self):
        """Test status intent recognition."""
        test_cases = [
            "show bot status",
            "what is the current status",
            "bot overview",
            "show me the bot",
            "how is the bot doing",
        ]

        for command in test_cases:
            intent = extract_intent(command)
            assert intent.intent == Intent.STATUS, f"Failed for: {command}"
            assert intent.confidence > 0.7
            assert intent.original_text == command

    def test_extract_performance_intent(self):
        """Test performance intent recognition."""
        test_cases = [
            "show performance",
            "what is my P&L",
            "how am I doing",
            "show today's performance",
            "daily pnl",
        ]

        for command in test_cases:
            intent = extract_intent(command)
            assert intent.intent == Intent.PERFORMANCE, f"Failed for: {command}"
            assert intent.confidence > 0.7

    def test_extract_positions_intent(self):
        """Test positions intent recognition."""
        test_cases = [
            "what positions are open",
            "show my holdings",
            "list current positions",
            "what trades are active",
        ]

        for command in test_cases:
            intent = extract_intent(command)
            assert intent.intent == Intent.POSITIONS, f"Failed for: {command}"
            assert intent.confidence > 0.7

    def test_extract_health_intent(self):
        """Test health intent recognition."""
        test_cases = [
            "check health",
            "is the bot running",
            "is bot healthy",
            "health check",
        ]

        for command in test_cases:
            intent = extract_intent(command)
            assert intent.intent == Intent.HEALTH, f"Failed for: {command}"
            assert intent.confidence > 0.7

    def test_extract_errors_intent(self):
        """Test errors intent recognition."""
        test_cases = [
            "show errors",
            "what went wrong",
            "show issues",
            "any problems",
        ]

        for command in test_cases:
            intent = extract_intent(command)
            assert intent.intent == Intent.ERRORS, f"Failed for: {command}"
            assert intent.confidence > 0.7

    def test_extract_config_intent(self):
        """Test config intent recognition."""
        test_cases = [
            "show configuration",
            "what are the settings",
            "show config",
        ]

        for command in test_cases:
            intent = extract_intent(command)
            assert intent.intent == Intent.CONFIG, f"Failed for: {command}"
            assert intent.confidence > 0.7

    def test_unknown_intent(self):
        """Test unknown intent for unrecognized commands."""
        test_cases = [
            "buy AAPL",
            "sell everything",
            "what time is it",
            "hello world",
        ]

        for command in test_cases:
            intent = extract_intent(command)
            # Should either be UNKNOWN or have low confidence
            assert intent.intent == Intent.UNKNOWN or intent.confidence < 0.5

    def test_extract_timeframe_entity(self):
        """Test timeframe entity extraction."""
        # Today
        intent = extract_intent("show today's performance")
        assert intent.entities.get("timeframe") == "today"

        # Weekly
        intent = extract_intent("show this week's performance")
        assert intent.entities.get("timeframe") == "week"

        # Monthly
        intent = extract_intent("show monthly performance")
        assert intent.entities.get("timeframe") == "month"

    def test_extract_symbol_entity(self):
        """Test stock symbol entity extraction."""
        intent = extract_intent("show AAPL position")
        assert intent.entities.get("symbol") == "AAPL"

        intent = extract_intent("how is TSLA doing")
        assert intent.entities.get("symbol") == "TSLA"


class TestResponseFormatting:
    """Unit tests for response formatting."""

    def test_format_status_response(self):
        """Test status response formatting."""
        intent = ParsedIntent(
            intent=Intent.STATUS,
            confidence=0.9,
            entities={},
            original_text="show status",
        )
        api_response = {
            "health_status": "healthy",
            "position_count": 3,
            "open_orders_count": 2,
            "daily_pnl": 1250.75,
        }

        formatted = format_response(intent, api_response)

        assert "Bot Status:" in formatted
        assert "Health: healthy" in formatted
        assert "Positions: 3" in formatted
        assert "Orders: 2" in formatted
        assert "$1250.75" in formatted

    def test_format_performance_response(self):
        """Test performance response formatting."""
        intent = ParsedIntent(
            intent=Intent.PERFORMANCE,
            confidence=0.9,
            entities={},
            original_text="show performance",
        )
        api_response = {"daily_pnl": 500.00, "account_balance": 50000.00}

        formatted = format_response(intent, api_response)

        assert "Performance:" in formatted
        assert "$500.00" in formatted
        assert "$50000.00" in formatted

    def test_format_positions_response(self):
        """Test positions response formatting."""
        intent = ParsedIntent(
            intent=Intent.POSITIONS,
            confidence=0.9,
            entities={},
            original_text="show positions",
        )
        api_response = {"position_count": 5}

        formatted = format_response(intent, api_response)

        assert "5 open positions" in formatted

    def test_format_health_response(self):
        """Test health response formatting."""
        intent = ParsedIntent(
            intent=Intent.HEALTH,
            confidence=0.9,
            entities={},
            original_text="check health",
        )
        api_response = {"status": "healthy"}

        formatted = format_response(intent, api_response)

        assert "Bot health: healthy" in formatted

    def test_format_errors_response_with_errors(self):
        """Test errors response formatting with errors present."""
        intent = ParsedIntent(
            intent=Intent.ERRORS,
            confidence=0.9,
            entities={},
            original_text="show errors",
        )
        api_response = {
            "recent_errors": [
                {"message": "Connection timeout"},
                {"message": "Order rejected"},
            ]
        }

        formatted = format_response(intent, api_response)

        assert "Recent errors (2)" in formatted
        assert "Connection timeout" in formatted
        assert "Order rejected" in formatted

    def test_format_errors_response_no_errors(self):
        """Test errors response formatting with no errors."""
        intent = ParsedIntent(
            intent=Intent.ERRORS,
            confidence=0.9,
            entities={},
            original_text="show errors",
        )
        api_response = {"recent_errors": []}

        formatted = format_response(intent, api_response)

        assert "No recent errors" in formatted

    def test_format_config_response(self):
        """Test config response formatting."""
        intent = ParsedIntent(
            intent=Intent.CONFIG,
            confidence=0.9,
            entities={},
            original_text="show config",
        )
        api_response = {"risk_per_trade": 0.02, "max_position_size": 5000}

        formatted = format_response(intent, api_response)

        assert "Configuration:" in formatted
        assert "2.0%" in formatted
        assert "$5000" in formatted

    def test_format_error_response(self):
        """Test error response formatting."""
        intent = ParsedIntent(
            intent=Intent.STATUS,
            confidence=0.9,
            entities={},
            original_text="show status",
        )
        api_response = {"error": "API_ERROR", "message": "Connection failed"}

        formatted = format_response(intent, api_response)

        assert "Error:" in formatted
        assert "Connection failed" in formatted


@pytest.mark.parametrize(
    "command,expected_intent",
    [
        ("show bot status", Intent.STATUS),
        ("what is my performance", Intent.PERFORMANCE),
        ("list positions", Intent.POSITIONS),
        ("check health", Intent.HEALTH),
        ("show errors", Intent.ERRORS),
        ("show config", Intent.CONFIG),
        ("unknown command xyz", Intent.UNKNOWN),
    ],
)
def test_intent_extraction_parametrized(command, expected_intent):
    """Parametrized test for intent extraction."""
    intent = extract_intent(command)
    assert intent.intent == expected_intent
