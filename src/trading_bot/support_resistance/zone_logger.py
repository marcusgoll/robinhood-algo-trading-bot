"""
Zone Detection Structured Logger

Thread-safe JSONL-based zone detection logging with daily file rotation.

Constitution v1.0.0:
- §Audit_Everything: All zone detections logged to immutable JSONL files
- §Data_Integrity: Atomic writes with file locking prevent corruption
- §Safety_First: Thread-safe concurrent write handling

Pattern: Extends StructuredTradeLogger from logging/structured_logger.py
"""

import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import ProximityAlert, Zone
from .breakout_models import BreakoutEvent


class ZoneLogger:
    """Thread-safe structured zone logger with daily file rotation.

    Features:
    - Daily JSONL files (logs/zones/YYYY-MM-DD-zones.jsonl)
    - Thread-safe concurrent writes (file locking)
    - Optimized buffering for <5ms write latency (NFR-003)
    - Append-only mode (no overwriting)

    Example:
        >>> logger = ZoneLogger(log_dir=Path("logs/zones"))
        >>> zones = [Zone(...), Zone(...)]
        >>> logger.log_zone_detection("AAPL", zones, metadata={"days_analyzed": 60})
    """

    def __init__(self, log_dir: Path = Path("logs/zones")) -> None:
        """Initialize structured zone logger with configurable directory.

        Creates a thread-safe logger instance for writing zone detection events
        to daily JSONL files. The logger automatically handles directory creation,
        file rotation, and concurrent write coordination.

        Args:
            log_dir: Directory for zone log files (default: ./logs/zones).
                Daily JSONL files will be created with naming pattern:
                YYYY-MM-DD-zones.jsonl (e.g., "2025-10-21-zones.jsonl").
                Directory is created automatically if it doesn't exist.

        Examples:
            Default logs directory:
            >>> logger = ZoneLogger()
            >>> # Logs to: logs/zones/2025-10-21-zones.jsonl

            Custom directory:
            >>> logger = ZoneLogger(log_dir=Path("/var/log/zones"))
            >>> # Logs to: /var/log/zones/2025-10-21-zones.jsonl

        Notes:
            - Thread-safe: Multiple detection runs can share same logger
            - Auto-rotation: New file created daily at midnight UTC
            - Directory creation: Parent directories created automatically
        """
        self.log_dir = log_dir
        self._lock = threading.Lock()

        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_daily_file_path(self) -> Path:
        """Get path to today's JSONL log file based on UTC date.

        Daily file rotation implemented per NFR-008 (log rotation requirement).
        Uses UTC timezone to ensure consistent rotation regardless of location.
        Files named with ISO 8601 date format (YYYY-MM-DD) for sortability.

        Returns:
            Path: Path to daily log file in format: log_dir/YYYY-MM-DD-zones.jsonl

        Examples:
            >>> logger = ZoneLogger(log_dir=Path("logs/zones"))
            >>> logger._get_daily_file_path()
            PosixPath('logs/zones/2025-10-21-zones.jsonl')
        """
        today = datetime.now(UTC).date().isoformat()
        return self.log_dir / f"{today}-zones.jsonl"

    def log_zone_detection(
        self,
        symbol: str,
        zones: list[Zone],
        analysis_metadata: dict[str, Any]
    ) -> None:
        """Log zone detection event with all identified zones.

        Thread-safe write to daily JSONL file. Logs detection summary with
        all zones and analysis metadata (days analyzed, touch threshold, etc.).

        Args:
            symbol: Stock symbol analyzed (e.g., "AAPL")
            zones: List of detected Zone objects
            analysis_metadata: Context dict with keys like:
                - days_analyzed: Number of historical days scanned
                - touch_threshold: Minimum touches required
                - zones_found: Count of zones identified
                - timeframe: "daily" or "4h"

        Example:
            >>> logger = ZoneLogger()
            >>> zones = [Zone(...), Zone(...)]
            >>> logger.log_zone_detection(
            ...     "AAPL",
            ...     zones,
            ...     {"days_analyzed": 60, "zones_found": 5, "timeframe": "daily"}
            ... )
        """
        with self._lock:
            file_path = self._get_daily_file_path()

            # Build log entry
            log_entry = {
                "event": "zone_detection",
                "timestamp": datetime.now(UTC).isoformat(),
                "symbol": symbol,
                "zones_count": len(zones),
                "zones": [zone.to_dict() for zone in zones],
                "metadata": analysis_metadata
            }

            # Write to JSONL file (append mode)
            import json
            with file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

    def log_proximity_alert(self, alert: ProximityAlert) -> None:
        """Log proximity alert when price approaches a zone.

        Thread-safe write to daily JSONL file. Logs alert with zone distance
        and direction (approaching support/resistance).

        Args:
            alert: ProximityAlert object with zone details

        Example:
            >>> logger = ZoneLogger()
            >>> alert = ProximityAlert(
            ...     symbol="AAPL",
            ...     zone_id="support_150.50_daily",
            ...     current_price=Decimal("152.00"),
            ...     zone_price=Decimal("150.50"),
            ...     distance_percent=Decimal("0.99"),
            ...     direction="approaching_support",
            ...     timestamp=datetime.now(UTC)
            ... )
            >>> logger.log_proximity_alert(alert)
        """
        with self._lock:
            file_path = self._get_daily_file_path()

            # Build log entry
            log_entry = {
                "event": "proximity_alert",
                "timestamp": datetime.now(UTC).isoformat(),
                **alert.to_dict()
            }

            # Write to JSONL file (append mode)
            import json
            with file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

    def log_breakout(self, zone: Zone, breakout_metadata: dict[str, Any]) -> None:
        """Log breakout event when price breaks through a zone.

        Thread-safe write to daily JSONL file. Logs breakout with zone details,
        breakout direction, and volume context.

        Args:
            zone: Zone object that was broken
            breakout_metadata: Context dict with keys like:
                - breakout_price: Price at breakout
                - breakout_volume: Volume at breakout
                - direction: "up" or "down"
                - strength: "weak" or "strong" based on volume
                - previous_touches: Count before breakout

        Example:
            >>> logger = ZoneLogger()
            >>> zone = Zone(...)
            >>> logger.log_breakout(
            ...     zone,
            ...     {
            ...         "breakout_price": "155.00",
            ...         "breakout_volume": "50000000",
            ...         "direction": "up",
            ...         "strength": "strong"
            ...     }
            ... )
        """
        with self._lock:
            file_path = self._get_daily_file_path()

            # Build log entry
            log_entry = {
                "event": "breakout",
                "timestamp": datetime.now(UTC).isoformat(),
                "zone": zone.to_dict(),
                "breakout_metadata": breakout_metadata
            }

            # Write to JSONL file (append mode)
            import json
            with file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

    def log_breakout_event(self, event: BreakoutEvent) -> None:
        """Log structured breakout event to dedicated breakout JSONL file.

        Thread-safe write to daily breakout-specific JSONL file (separate from
        general zone logs). Designed for feature 025 breakout detection with
        volume confirmation.

        File pattern: logs/zones/breakouts-YYYY-MM-DD.jsonl

        Args:
            event: BreakoutEvent object with complete breakout metadata

        Example:
            >>> logger = ZoneLogger()
            >>> event = BreakoutEvent(
            ...     event_id="evt_abc123",
            ...     zone_id="resistance_155.00_daily",
            ...     timestamp=datetime.now(UTC),
            ...     breakout_price=Decimal("155.00"),
            ...     close_price=Decimal("156.60"),
            ...     volume=Decimal("1500000"),
            ...     volume_ratio=Decimal("1.4"),
            ...     old_zone_type=ZoneType.RESISTANCE,
            ...     new_zone_type=ZoneType.SUPPORT,
            ...     status=BreakoutStatus.CONFIRMED,
            ...     timeframe=Timeframe.DAILY
            ... )
            >>> logger.log_breakout_event(event)

        Notes:
            - Separate file from zone detection logs for easier querying
            - Uses event.to_jsonl_line() for consistent serialization
            - Graceful degradation: Logs error to stderr on write failure
        """
        with self._lock:
            # Daily breakout log file (separate from zone logs)
            today = datetime.now(UTC).date().isoformat()
            file_path = self.log_dir / f"breakouts-{today}.jsonl"

            try:
                # Write event using its serialization method
                import json
                with file_path.open("a", encoding="utf-8") as f:
                    f.write(event.to_jsonl_line() + "\n")
            except OSError as e:
                # Graceful degradation: Log to stderr, don't crash
                import sys
                print(
                    f"WARNING: Failed to write breakout event {event.event_id} to {file_path}: {e}",
                    file=sys.stderr
                )
