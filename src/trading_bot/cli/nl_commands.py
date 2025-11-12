"""
Natural Language Command Interface for trading bot operations.

Provides intent extraction, API routing, and response formatting for
conversational bot queries.
"""

import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import httpx


class Intent(str, Enum):
    """Recognized intents from natural language commands."""

    STATUS = "status"
    PERFORMANCE = "performance"
    POSITIONS = "positions"
    HEALTH = "health"
    ERRORS = "errors"
    CONFIG = "config"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """
    Parsed intent from natural language command.

    Attributes:
        intent: Recognized intent type
        confidence: Confidence score (0-1)
        entities: Extracted entities (e.g., symbol, timeframe)
        original_text: Original command text
    """

    intent: Intent
    confidence: float
    entities: Dict[str, Any]
    original_text: str


def extract_intent(command: str) -> ParsedIntent:
    """
    Extract intent from natural language command using keyword matching.

    Args:
        command: Natural language command string

    Returns:
        ParsedIntent with recognized intent and entities

    Examples:
        >>> extract_intent("show bot status")
        ParsedIntent(intent=Intent.STATUS, confidence=0.9, ...)
        >>> extract_intent("what positions are open")
        ParsedIntent(intent=Intent.POSITIONS, confidence=0.85, ...)
    """
    command_lower = command.lower().strip()
    entities: Dict[str, Any] = {}

    # Intent patterns (keyword-based for MVP)
    intent_patterns = [
        # Status intent
        (
            Intent.STATUS,
            [
                r"\b(status|state|current|overview|summary)\b",
                r"\bshow\s+(me\s+)?(the\s+)?bot\b",
                r"\bhow\s+is\s+the\s+bot\b",
            ],
        ),
        # Performance intent
        (
            Intent.PERFORMANCE,
            [
                r"\b(performance|pnl|profit|loss|returns)\b",
                r"\bhow\s+(am\s+i|is\s+it)\s+doing\b",
                r"\b(today|daily|weekly|monthly)\s+(performance|pnl)\b",
            ],
        ),
        # Positions intent
        (
            Intent.POSITIONS,
            [
                r"\b(positions?|holdings?|trades?)\b",
                r"\bwhat\s+.*(open|active|current)\s+(positions?|trades?)\b",
                r"\bshow\s+.*(positions?|holdings?)\b",
            ],
        ),
        # Health intent
        (
            Intent.HEALTH,
            [
                r"\b(health|healthcheck|healthy|alive|running)\b",
                r"\bis\s+(the\s+)?bot\s+(ok|working|running|healthy)\b",
                r"\bcheck\s+health\b",
            ],
        ),
        # Errors intent
        (
            Intent.ERRORS,
            [
                r"\b(errors?|issues?|problems?|failures?)\b",
                r"\bwhat\s+(went\s+)?wrong\b",
                r"\bshow\s+.*(errors?|issues?)\b",
            ],
        ),
        # Config intent
        (
            Intent.CONFIG,
            [
                r"\b(config|configuration|settings?)\b",
                r"\bwhat\s+(are\s+)?(the\s+)?settings?\b",
                r"\bshow\s+.*(config|configuration)\b",
            ],
        ),
    ]

    # Match patterns
    best_intent = Intent.UNKNOWN
    best_confidence = 0.0

    for intent, patterns in intent_patterns:
        for pattern in patterns:
            if re.search(pattern, command_lower):
                # Simple confidence based on pattern specificity
                confidence = 0.7 + (len(pattern) / 200)  # Longer patterns = higher confidence
                if confidence > best_confidence:
                    best_intent = intent
                    best_confidence = min(confidence, 1.0)

    # Extract entities (timeframes, symbols)
    if re.search(r"\btoday\b", command_lower):
        entities["timeframe"] = "today"
    elif re.search(r"\b(weekly|this\s+week)\b", command_lower):
        entities["timeframe"] = "week"
    elif re.search(r"\b(monthly|this\s+month)\b", command_lower):
        entities["timeframe"] = "month"

    # Extract stock symbols (simple pattern for MVP)
    symbol_match = re.search(r"\b([A-Z]{1,5})\b", command)
    if symbol_match:
        entities["symbol"] = symbol_match.group(1)

    return ParsedIntent(
        intent=best_intent,
        confidence=best_confidence,
        entities=entities,
        original_text=command,
    )


def route_to_api(
    intent: ParsedIntent, api_base_url: str = "http://localhost:8000/api/v1", api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Route intent to appropriate API endpoint.

    Args:
        intent: Parsed intent
        api_base_url: Base URL for API
        api_key: Optional API key for authentication

    Returns:
        API response as dict

    Raises:
        httpx.HTTPError: If API call fails
    """
    headers = {"X-API-Key": api_key} if api_key else {}

    # Map intent to API endpoint
    endpoint_map = {
        Intent.STATUS: "/state",
        Intent.PERFORMANCE: "/metrics",
        Intent.POSITIONS: "/state",  # Extract positions from state
        Intent.HEALTH: "/health/healthz",
        Intent.ERRORS: "/summary",  # Recent errors in summary
        Intent.CONFIG: "/config",
    }

    endpoint = endpoint_map.get(intent.intent)
    if not endpoint:
        return {
            "error": "Unknown intent",
            "message": f"Cannot handle intent: {intent.intent}",
        }

    # Make API call
    try:
        url = f"{api_base_url}{endpoint}"
        response = httpx.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        return {"error": str(e), "message": "API request failed"}


def format_response(intent: ParsedIntent, api_response: Dict[str, Any]) -> str:
    """
    Format API response for human-readable output.

    Args:
        intent: Original parsed intent
        api_response: Response from API

    Returns:
        Human-readable formatted string
    """
    if "error" in api_response:
        return f"Error: {api_response.get('message', 'Unknown error')}"

    # Format based on intent
    if intent.intent == Intent.STATUS:
        health = api_response.get("health_status", "unknown")
        positions = api_response.get("position_count", 0)
        orders = api_response.get("open_orders_count", 0)
        pnl = api_response.get("daily_pnl", 0.0)
        return (
            f"Bot Status:\n"
            f"  Health: {health}\n"
            f"  Positions: {positions} open\n"
            f"  Orders: {orders} pending\n"
            f"  Daily P&L: ${pnl:.2f}"
        )

    elif intent.intent == Intent.PERFORMANCE:
        pnl = api_response.get("daily_pnl", 0.0)
        balance = api_response.get("account_balance", 0.0)
        return f"Performance:\n  Daily P&L: ${pnl:.2f}\n  Account Balance: ${balance:.2f}"

    elif intent.intent == Intent.POSITIONS:
        positions = api_response.get("position_count", 0)
        return f"You have {positions} open positions."

    elif intent.intent == Intent.HEALTH:
        status = api_response.get("status", "unknown")
        return f"Bot health: {status}"

    elif intent.intent == Intent.ERRORS:
        errors = api_response.get("recent_errors", [])
        if not errors:
            return "No recent errors."
        return (
            f"Recent errors ({len(errors)}):\n"
            + "\n".join([f"  - {err.get('message', 'Unknown')}" for err in errors])
        )

    elif intent.intent == Intent.CONFIG:
        risk = api_response.get("risk_per_trade", 0.0)
        max_pos = api_response.get("max_position_size", 0)
        return f"Configuration:\n  Risk per trade: {risk*100}%\n  Max position: ${max_pos}"

    else:
        return f"Response:\n{api_response}"


def main():
    """CLI entry point for natural language commands."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.trading_bot.cli.nl_commands \"<command>\"")
        print('Example: python -m src.trading_bot.cli.nl_commands "show bot status"')
        sys.exit(1)

    command = " ".join(sys.argv[1:])

    # Extract intent
    intent = extract_intent(command)
    print(f"Detected intent: {intent.intent.value} (confidence: {intent.confidence:.2f})")

    if intent.intent == Intent.UNKNOWN:
        print(
            f"Sorry, I don't understand '{command}'. "
            "Try commands like:\n"
            "  - show bot status\n"
            "  - what positions are open\n"
            "  - check health\n"
            "  - show today's performance"
        )
        sys.exit(1)

    # Route to API
    api_key = os.getenv("BOT_API_KEY")  # Read from environment variable
    try:
        api_response = route_to_api(intent, api_key=api_key)
    except Exception as e:
        print(f"API error: {e}")
        sys.exit(1)

    # Format and print response
    formatted_response = format_response(intent, api_response)
    print("\n" + formatted_response)


if __name__ == "__main__":
    main()
