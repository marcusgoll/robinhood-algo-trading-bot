"""
Momentum Logger Wrapper

Thread-safe JSONL-based momentum signal logging with daily file rotation.

Constitution v1.0.0:
- §Audit_Everything: All signals logged to immutable JSONL files
- §Data_Integrity: Atomic writes with file locking prevent corruption
- §Safety_First: Thread-safe concurrent write handling

Feature: momentum-detection
Task: T007 [GREEN] - Create MomentumLogger wrapper
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...logging.structured_logger import StructuredTradeLogger


class MomentumLogger:
    """Thread-safe momentum signal logger wrapping StructuredTradeLogger.

    Provides specialized logging methods for momentum detection events:
    - Signal detection (catalyst, pre-market, pattern)
    - Scan lifecycle events (started, completed)
    - Error tracking with context

    Features:
    - Daily JSONL files (logs/momentum/YYYY-MM-DD.jsonl)
    - Thread-safe concurrent writes (via StructuredTradeLogger)
    - UTC timestamps only (NFR-004)
    - Append-only mode (immutable audit trail)

    Example:
        >>> logger = MomentumLogger(log_dir=Path("logs/momentum"))
        >>> signal = {"signal_type": "catalyst", "symbol": "AAPL", "strength": 85.5}
        >>> logger.log_signal(signal, {"scan_id": "123"})
        >>> # Writes to logs/momentum/2025-10-16.jsonl
    """

    def __init__(self, log_dir: Path = Path("logs/momentum")) -> None:
        """Initialize momentum logger with configurable directory.

        Creates a thread-safe logger instance for writing momentum signal records
        to daily JSONL files. Delegates to StructuredTradeLogger for file handling,
        rotation, and thread safety.

        Args:
            log_dir: Directory for momentum log files (default: ./logs/momentum).
                Daily JSONL files created with naming pattern: YYYY-MM-DD.jsonl.
                Directory created automatically if it doesn't exist.

        Examples:
            Default logs directory:
            >>> logger = MomentumLogger()
            >>> # Logs to: logs/momentum/2025-10-16.jsonl

            Custom directory:
            >>> logger = MomentumLogger(log_dir=Path("/var/log/momentum"))
            >>> # Logs to: /var/log/momentum/2025-10-16.jsonl

        Notes:
            - Thread-safe: Multiple scanner instances can share same logger
            - Auto-rotation: New file created daily at midnight UTC
            - Directory creation: Parent directories created automatically
        """
        self._base_logger = StructuredTradeLogger(log_dir=log_dir)

    def log_signal(self, signal: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
        """Log a momentum signal detection event to daily JSONL file.

        Thread-safe operation per Constitution v1.0.0 §Data_Integrity and §Safety_First.
        Implements append-only immutable audit trail with graceful error handling.

        Log format:
        {
            "timestamp": "2025-10-16T14:30:00.123456Z",
            "event_type": "signal_detected",
            "signal_type": "catalyst|premarket_mover|bull_flag",
            "symbol": "AAPL",
            "strength": 85.5,
            "details": {...signal data...},
            ...metadata
        }

        Args:
            signal: Signal data dict with at minimum:
                - signal_type: str ("catalyst", "premarket_mover", "bull_flag")
                - symbol: str (stock ticker)
                - strength: float (0-100 composite score)
            metadata: Optional additional fields to include in log entry

        Raises:
            None: All errors caught and logged to stderr. Scanner continues
                operating even if signal logging fails (graceful degradation).

        Examples:
            Basic signal logging:
            >>> logger = MomentumLogger()
            >>> signal = {
            ...     "signal_type": "catalyst",
            ...     "symbol": "AAPL",
            ...     "strength": 85.5,
            ...     "catalyst_type": "earnings"
            ... }
            >>> logger.log_signal(signal)

            With metadata:
            >>> logger.log_signal(signal, {"scan_id": "abc123", "detector_version": "1.0.0"})

        Performance:
            - Typical latency: <5ms (inherited from StructuredTradeLogger)
            - Thread-safe: No data corruption from concurrent writes
        """
        try:
            # Build log entry with UTC timestamp
            log_entry = self._format_signal_for_log(signal, metadata)

            # Convert to JSONL-compatible object (mimicking TradeRecord pattern)
            # Since StructuredTradeLogger expects a TradeRecord, we create a minimal
            # duck-typed object with to_jsonl_line() method
            from ...logging.momentum_log_entry import MomentumLogEntry
            entry = MomentumLogEntry(log_entry)

            # Delegate to base logger (thread-safe, handles file I/O)
            self._base_logger.log_trade(entry)

        except Exception as e:
            # Graceful degradation: Log error but don't crash scanner
            print(f"ERROR: Failed to log momentum signal: {e}", file=sys.stderr)

    def log_scan_event(self, event_type: str, metadata: dict[str, Any]) -> None:
        """Log a scan lifecycle event to daily JSONL file.

        Used to track scan start, completion, and intermediate milestones.

        Log format:
        {
            "timestamp": "2025-10-16T14:30:00.123456Z",
            "event_type": "scan_started|scan_completed|detector_finished",
            "metadata": {...event-specific data...}
        }

        Args:
            event_type: Event identifier ("scan_started", "scan_completed", etc.)
            metadata: Event-specific data (e.g., symbols scanned, duration, errors)

        Raises:
            None: All errors caught and logged to stderr.

        Examples:
            Scan start:
            >>> logger = MomentumLogger()
            >>> logger.log_scan_event("scan_started", {
            ...     "scan_id": "abc123",
            ...     "symbols": ["AAPL", "GOOGL"],
            ...     "scan_types": ["catalyst", "premarket"]
            ... })

            Scan completion:
            >>> logger.log_scan_event("scan_completed", {
            ...     "scan_id": "abc123",
            ...     "signals_found": 5,
            ...     "duration_ms": 245
            ... })
        """
        try:
            log_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "event_type": event_type,
                "metadata": metadata
            }

            from ...logging.momentum_log_entry import MomentumLogEntry
            entry = MomentumLogEntry(log_entry)
            self._base_logger.log_trade(entry)

        except Exception as e:
            print(f"ERROR: Failed to log scan event: {e}", file=sys.stderr)

    def log_error(self, error: Exception, context: dict[str, Any]) -> None:
        """Log an error event with full context for debugging.

        Log format:
        {
            "timestamp": "2025-10-16T14:30:00.123456Z",
            "event_type": "error",
            "error_type": "APIError",
            "message": "Failed to fetch news data",
            "context": {...error-specific data...}
        }

        Args:
            error: Exception instance that occurred
            context: Contextual data (e.g., symbol being processed, detector name)

        Raises:
            None: All errors caught and logged to stderr.

        Examples:
            API error:
            >>> logger = MomentumLogger()
            >>> try:
            ...     # API call fails
            ...     raise ConnectionError("News API timeout")
            ... except Exception as e:
            ...     logger.log_error(e, {
            ...         "detector": "CatalystDetector",
            ...         "symbol": "AAPL",
            ...         "retry_attempt": 3
            ...     })
        """
        try:
            log_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "event_type": "error",
                "error_type": type(error).__name__,
                "message": str(error),
                "context": context
            }

            from ...logging.momentum_log_entry import MomentumLogEntry
            entry = MomentumLogEntry(log_entry)
            self._base_logger.log_trade(entry)

        except Exception as e:
            print(f"ERROR: Failed to log error event: {e}", file=sys.stderr)

    def _format_signal_for_log(self, signal: dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any]:
        """Convert signal dict to standardized log entry format.

        Helper method to ensure consistent log structure across all signal types.
        Adds UTC timestamp and merges metadata into top-level log entry.

        Args:
            signal: Signal data dict (must contain signal_type, symbol, strength)
            metadata: Optional additional fields to merge into log entry

        Returns:
            dict: Standardized log entry with timestamp, event_type, and all signal fields

        Examples:
            >>> logger = MomentumLogger()
            >>> signal = {"signal_type": "catalyst", "symbol": "AAPL", "strength": 85.5}
            >>> entry = logger._format_signal_for_log(signal, {"scan_id": "123"})
            >>> entry["event_type"]
            'signal_detected'
            >>> entry["timestamp"]  # ISO 8601 UTC format
            '2025-10-16T14:30:00.123456Z'
        """
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": "signal_detected",
            **signal  # Spread all signal fields into log entry
        }

        # Merge metadata if provided
        if metadata:
            log_entry.update(metadata)

        return log_entry
