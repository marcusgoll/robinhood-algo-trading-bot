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

        Performs comprehensive validation per Constitution v1.0.0 §Data_Integrity.
        Ensures all trade data meets format and constraint requirements before
        logging to prevent corrupted audit trail.

        Validation rules (T010, T011):
        - Symbol: Uppercase 1-5 chars, alphanumeric only (e.g., "AAPL", "MSFT")
        - Quantity: Positive integer, max 10,000 shares (position sizing limit)
        - Price: Positive Decimal (must be greater than zero)

        Raises:
            ValueError: If any validation rule fails with descriptive error message

        Examples:
            Valid trade record:
            >>> record = TradeRecord(
            ...     timestamp="2025-01-09T14:32:15.123Z",
            ...     symbol="AAPL",  # Valid: uppercase, 1-5 chars
            ...     action="BUY",
            ...     quantity=100,  # Valid: positive, <= 10000
            ...     price=Decimal("150.25"),  # Valid: positive
            ...     # ... other fields
            ... )

            Invalid symbol (lowercase):
            >>> record = TradeRecord(..., symbol="aapl", ...)  # doctest: +SKIP
            ValueError: Symbol must be uppercase: aapl

            Invalid quantity (exceeds limit):
            >>> record = TradeRecord(..., quantity=15000, ...)  # doctest: +SKIP
            ValueError: Quantity must not exceed 10000: 15000
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

        Converts Decimal fields to strings for JSON compatibility while preserving
        precision. Required for JSONL logging per Constitution v1.0.0 §Audit_Everything.

        Decimal-to-string conversion necessary because JSON doesn't natively support
        Python's Decimal type. This prevents floating-point precision loss in financial
        calculations (e.g., "150.25" vs 150.24999999999997).

        Returns:
            dict: JSON-safe dictionary with all 27 TradeRecord fields.
                Decimal fields converted to strings for lossless serialization.

        Examples:
            >>> from decimal import Decimal
            >>> record = TradeRecord(
            ...     timestamp="2025-01-09T14:32:15.123Z",
            ...     symbol="AAPL",
            ...     action="BUY",
            ...     quantity=100,
            ...     price=Decimal("150.25"),
            ...     total_value=Decimal("15025.00"),
            ...     # ... other fields
            ... )
            >>> json_dict = record.to_json()
            >>> json_dict["price"]
            '150.25'
            >>> json_dict["quantity"]  # Non-Decimal fields unchanged
            100
        """
        data = asdict(self)

        # Convert Decimal fields to strings
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = str(value)

        return data

    def to_jsonl_line(self) -> str:
        """Serialize to JSONL format (T013).

        Produces single-line JSON with compact separators (no pretty printing).
        JSONL (JSON Lines) format enables efficient streaming reads and grep queries
        for Claude Code-measurable analytics per spec requirements.

        Format: One JSON object per line, no trailing newline
        Separators: Compact (',' and ':') for minimal file size
        Performance: <1ms serialization for typical trade record

        Returns:
            str: Single-line JSON string without trailing newline.
                Caller must add '\\n' when writing to file.

        Examples:
            >>> from decimal import Decimal
            >>> record = TradeRecord(
            ...     timestamp="2025-01-09T14:32:15.123Z",
            ...     symbol="AAPL",
            ...     action="BUY",
            ...     quantity=100,
            ...     price=Decimal("150.25"),
            ...     # ... other fields
            ... )
            >>> line = record.to_jsonl_line()
            >>> '\\n' in line  # No newline in output
            False
            >>> line.startswith('{"timestamp":')  # Compact JSON
            True

        See Also:
            StructuredTradeLogger.log_trade(): Writes JSONL lines to daily files
        """
        return json.dumps(self.to_json(), separators=(',', ':'))
