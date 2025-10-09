"""
Trade Record Dataclass

Structured trade execution record with validation and serialization.

Constitution v1.0.0:
- §Data_Integrity: All trade data validated and typed
- §Audit_Everything: Complete decision audit trail
- §Safety_First: Validation prevents invalid trade records

Feature: trade-logging
Tasks: T009-T013 [GREEN] - Implement TradeRecord dataclass
"""

from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Optional
import json


@dataclass
class TradeRecord:
    """Structured trade execution record (FR-001).

    All 27 fields as per plan.md [SCHEMA]:
    - Core Trade Data (6 fields)
    - Execution Context (3 fields)
    - Strategy Metadata (4 fields)
    - Decision Audit Trail (3 fields)
    - Outcome Tracking (5 fields)
    - Performance Metrics (3 fields)
    - Compliance & Audit (3 fields)
    """

    # Core Trade Data (FR-002)
    timestamp: str              # ISO 8601 UTC (e.g., "2025-01-09T14:32:15.123Z")
    symbol: str                 # Stock ticker (e.g., "AAPL")
    action: str                 # "BUY" | "SELL"
    quantity: int               # Number of shares
    price: Decimal              # Execution price
    total_value: Decimal        # quantity * price

    # Execution Context (FR-003)
    order_id: str               # Unique order identifier
    execution_mode: str         # "PAPER" | "LIVE"
    account_id: Optional[str]   # Robinhood account ID (if live)

    # Strategy Metadata (FR-004)
    strategy_name: str          # "bull-flag-breakout" | "manual" | etc.
    entry_type: str             # "breakout" | "pullback" | "reversal" | etc.
    stop_loss: Optional[Decimal]  # Stop loss price (if set)
    target: Optional[Decimal]    # Profit target price (if set)

    # Decision Audit Trail (FR-005, §Audit_Everything)
    decision_reasoning: str     # Why this trade was taken
    indicators_used: list[str]  # ["VWAP", "EMA-9", "MACD"] etc.
    risk_reward_ratio: Optional[float]  # Planned R:R (e.g., 2.0 for 2:1)

    # Outcome Tracking (FR-006)
    outcome: Optional[str]      # "win" | "loss" | "breakeven" | "open"
    profit_loss: Optional[Decimal]  # Realized P&L (if closed)
    hold_duration_seconds: Optional[int]  # Time in trade
    exit_timestamp: Optional[str]  # When position closed (ISO 8601 UTC)
    exit_reasoning: Optional[str]   # Why position was exited

    # Performance Metrics (FR-007)
    slippage: Optional[Decimal]     # Difference from expected price
    commission: Optional[Decimal]   # Trading fees
    net_profit_loss: Optional[Decimal]  # P&L - commission

    # Compliance & Audit (NFR-002, §Audit_Everything)
    session_id: str             # Links to trading session
    bot_version: str            # Software version for reproducibility
    config_hash: str            # Hash of config at trade time

    def __post_init__(self) -> None:
        """Validate trade record fields after initialization.

        Validation rules (T010, T011):
        - Symbol: Uppercase 1-5 chars, alphanumeric only
        - Quantity: Positive integer, max 10,000 shares
        - Price: Positive Decimal

        Raises:
            ValueError: If validation fails
        """
        # T010: Symbol validation
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")

        if not self.symbol.isupper():
            raise ValueError(f"Symbol must be uppercase: {self.symbol}")

        if len(self.symbol) < 1 or len(self.symbol) > 5:
            raise ValueError(f"Symbol must be 1-5 characters: {self.symbol} (length: {len(self.symbol)})")

        if not self.symbol.isalnum():
            raise ValueError(f"Symbol must be alphanumeric only: {self.symbol}")

        # T011: Numeric constraint validation
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive: {self.quantity}")

        if self.quantity > 10000:
            raise ValueError(f"Quantity must not exceed 10000: {self.quantity}")

        if self.price <= 0:
            raise ValueError(f"Price must be positive: {self.price}")

    def to_json(self) -> dict:
        """Serialize to JSON-safe dict (T012).

        Converts Decimal fields to strings for JSON compatibility.

        Returns:
            dict: JSON-safe dictionary with all 27 fields
        """
        data = asdict(self)

        # Convert Decimal fields to strings
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = str(value)

        return data

    def to_jsonl_line(self) -> str:
        """Serialize to JSONL format (T013).

        Single-line JSON with compact separators (no pretty printing).

        Returns:
            str: Single-line JSON string
        """
        return json.dumps(self.to_json(), separators=(',', ':'))
