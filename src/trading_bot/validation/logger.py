"""
TimeframeValidationLogger - JSONL logging for multi-timeframe validation events.

Thread-safe structured logger with daily file rotation for auditing validation decisions.

Constitution v1.0.0:
- §Audit_Everything: All validation events logged to immutable JSONL files
- §Data_Integrity: Atomic writes with file locking prevent corruption
- §Safety_First: Thread-safe concurrent write handling

Pattern: Based on ZoneLogger (src/trading_bot/support_resistance/zone_logger.py)
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from typing import Any, Dict

from .models import TimeframeValidationResult, ValidationStatus


class TimeframeValidationLogger:
    """Thread-safe structured validation logger with daily file rotation.

    Features:
    - Daily JSONL files (logs/timeframe-validation/YYYY-MM-DD.jsonl)
    - Thread-safe concurrent writes (file locking)
    - Append-only mode (no overwriting)
    - Structured events with 15+ fields for analytics

    Example:
        >>> logger = TimeframeValidationLogger()
        >>> result = validator.validate("AAPL", Decimal("150.00"), [])
        >>> logger.log_validation_event(result)
    """

    def __init__(self, log_dir: Path = Path("logs/timeframe-validation")) -> None:
        """Initialize structured validation logger with configurable directory.

        Args:
            log_dir: Directory for validation log files (default: ./logs/timeframe-validation).
                Daily JSONL files created with naming pattern: YYYY-MM-DD.jsonl

        Notes:
            - Thread-safe: Multiple validation runs can share same logger
            - Auto-rotation: New file created daily at midnight UTC
            - Directory creation: Parent directories created automatically
        """
        self.log_dir = log_dir
        self._lock = threading.Lock()

        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_daily_file_path(self) -> Path:
        """Get path to today's JSONL log file based on UTC date.

        Returns:
            Path: Path to daily log file in format: log_dir/YYYY-MM-DD.jsonl

        Example:
            >>> logger._get_daily_file_path()
            Path('logs/timeframe-validation/2024-10-28.jsonl')
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"{today}.jsonl"

    def log_validation_event(self, result: TimeframeValidationResult) -> None:
        """Log validation event to daily JSONL file.

        Thread-safe append operation with file locking. Writes single JSON line
        with 15+ fields for analytics and debugging.

        Args:
            result: TimeframeValidationResult to log

        Event Schema:
            - event (str): "timeframe_validation"
            - timestamp (str): ISO 8601 timestamp
            - symbol (str): Stock symbol validated
            - decision (str): PASS, BLOCK, or DEGRADED
            - aggregate_score (str): Final weighted score [0.0-1.0]
            - daily_score (str): Daily timeframe score
            - h4_score (str|null): 4H timeframe score (if available)
            - daily_macd (str|null): Daily MACD line value
            - daily_ema_20 (str|null): Daily 20 EMA value
            - daily_price_vs_ema (bool|null): Price above daily EMA
            - h4_macd (str|null): 4H MACD line value
            - h4_ema_20 (str|null): 4H 20 EMA value
            - h4_price_vs_ema (bool|null): Price above 4H EMA
            - reasons (list[str]): List of blocking/degradation reasons
            - degraded_mode (bool): True if validation degraded
            - severity (str): HIGH for degraded, NORMAL for others

        Thread Safety:
            Uses threading.Lock to prevent concurrent write corruption.
            Multiple threads can safely share same logger instance.

        Example:
            >>> result = TimeframeValidationResult(...)
            >>> logger.log_validation_event(result)
            # Appends to logs/timeframe-validation/2024-10-28.jsonl
        """
        # Build event dict (15 fields for analytics)
        event = self._build_event_dict(result)

        # Thread-safe write with locking
        with self._lock:
            log_file = self._get_daily_file_path()
            with open(log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')

    def _build_event_dict(self, result: TimeframeValidationResult) -> Dict[str, Any]:
        """Build event dictionary with all validation fields.

        Args:
            result: TimeframeValidationResult to serialize

        Returns:
            Dict with 15+ fields for JSONL logging
        """
        # Determine severity and degraded mode
        degraded_mode = result.status == ValidationStatus.DEGRADED
        severity = "HIGH" if degraded_mode else "NORMAL"

        # Extract daily indicators (if available)
        daily_macd = None
        daily_ema_20 = None
        daily_price_vs_ema = None
        if result.daily_indicators:
            daily_macd = str(result.daily_indicators.macd_line)
            daily_ema_20 = str(result.daily_indicators.ema_20)
            daily_price_vs_ema = result.daily_indicators.price_above_ema

        # Extract 4H indicators (if available)
        h4_macd = None
        h4_ema_20 = None
        h4_price_vs_ema = None
        if result.h4_indicators:
            h4_macd = str(result.h4_indicators.macd_line)
            h4_ema_20 = str(result.h4_indicators.ema_20)
            h4_price_vs_ema = result.h4_indicators.price_above_ema

        return {
            "event": "timeframe_validation",
            "timestamp": result.timestamp.isoformat(),
            "symbol": result.symbol,
            "decision": result.status.value,
            "aggregate_score": str(result.aggregate_score),
            "daily_score": str(result.daily_score),
            "h4_score": str(result.h4_score) if result.h4_score is not None else None,
            "daily_macd": daily_macd,
            "daily_ema_20": daily_ema_20,
            "daily_price_vs_ema": daily_price_vs_ema,
            "h4_macd": h4_macd,
            "h4_ema_20": h4_ema_20,
            "h4_price_vs_ema": h4_price_vs_ema,
            "reasons": result.reasons,
            "degraded_mode": degraded_mode,
            "severity": severity
        }
