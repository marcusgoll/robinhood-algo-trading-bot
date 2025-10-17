"""
Momentum Log Entry

Lightweight wrapper for momentum signal logging that mimics TradeRecord interface.

Constitution v1.0.0:
- §Data_Integrity: All log data validated and typed
- §Audit_Everything: Complete signal detection audit trail

Feature: momentum-detection
Task: T007 [GREEN] - Support MomentumLogger JSONL serialization
"""

import json
from typing import Any


class MomentumLogEntry:
    """Duck-typed log entry compatible with StructuredTradeLogger.

    Provides to_jsonl_line() interface expected by StructuredTradeLogger
    while wrapping arbitrary momentum signal data.

    This class exists to reuse StructuredTradeLogger's thread-safe file I/O
    without creating a heavyweight dataclass for every log entry type.

    Example:
        >>> entry = MomentumLogEntry({
        ...     "timestamp": "2025-10-16T14:30:00Z",
        ...     "signal_type": "catalyst",
        ...     "symbol": "AAPL"
        ... })
        >>> line = entry.to_jsonl_line()
        >>> '\\n' in line  # No trailing newline
        False
    """

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize log entry with arbitrary data dict.

        Args:
            data: Log entry data (signal, event, or error)
                Must be JSON-serializable (no Decimal, datetime objects)
        """
        self._data = data

    def to_jsonl_line(self) -> str:
        """Serialize to JSONL format.

        Produces single-line JSON with compact separators (no pretty printing).
        Compatible with StructuredTradeLogger's expected interface.

        Returns:
            str: Single-line JSON string without trailing newline.
                Caller (StructuredTradeLogger) adds '\\n' when writing to file.

        Examples:
            >>> entry = MomentumLogEntry({"symbol": "AAPL", "strength": 85.5})
            >>> line = entry.to_jsonl_line()
            >>> line
            '{"symbol":"AAPL","strength":85.5}'
        """
        return json.dumps(self._data, separators=(',', ':'))
