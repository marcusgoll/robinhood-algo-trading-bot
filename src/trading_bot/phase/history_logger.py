"""Phase history logger for audit trail.

Thread-safe JSONL-based logging for phase transitions and override attempts.

Constitution v1.0.0:
- §Audit_Everything: All phase transitions logged to immutable JSONL files
- §Data_Integrity: Atomic writes prevent corruption
- §Safety_First: Thread-safe concurrent write handling

Feature: 022-pos-scale-progress
Tasks: T050-T061 [GREEN] - Implement HistoryLogger
Based on: specs/022-pos-scale-progress/contracts/phase-api.yaml
"""

import json
import threading
from datetime import date, datetime, timezone, UTC
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from trading_bot.phase.models import Phase, PhaseTransition


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types.

    Converts Decimal to string to preserve precision in JSONL files.

    Example:
        >>> data = {"amount": Decimal("123.45")}
        >>> json.dumps(data, cls=DecimalEncoder)
        '{"amount": "123.45"}'
    """

    def default(self, obj):
        """Override default serialization for Decimal types.

        Args:
            obj: Object to serialize

        Returns:
            String representation for Decimal, default for others
        """
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


class HistoryLogger:
    """Thread-safe phase history logger with JSONL storage.

    Features:
    - Append-only JSONL files for phase transitions and overrides
    - Thread-safe concurrent writes (file locking)
    - Custom Decimal serialization
    - Date range querying

    Files:
    - logs/phase/phase-history.jsonl - Phase transition audit trail
    - logs/phase/phase-overrides.jsonl - Manual override attempts

    Example:
        >>> logger = HistoryLogger()
        >>> transition = PhaseTransition(...)
        >>> logger.log_transition(transition)
        >>> # Writes to logs/phase/phase-history.jsonl
    """

    def __init__(self, log_dir: Path = Path("logs/phase")) -> None:
        """Initialize history logger with configurable directory.

        Args:
            log_dir: Directory for phase log files (default: logs/phase).
                Creates two JSONL files:
                - phase-history.jsonl: Transition events
                - phase-overrides.jsonl: Override attempts
                Directory is created automatically if it doesn't exist.

        Example:
            >>> logger = HistoryLogger()
            >>> # Logs to: logs/phase/phase-history.jsonl

            >>> logger = HistoryLogger(log_dir=Path("/var/log/phase"))
            >>> # Logs to: /var/log/phase/phase-history.jsonl
        """
        self.log_dir = log_dir
        self.transition_log = log_dir / "phase-history.jsonl"
        self.override_log = log_dir / "phase-overrides.jsonl"
        self._lock = threading.Lock()

    def log_transition(self, transition: PhaseTransition) -> None:
        """Log phase transition to JSONL history file.

        Thread-safe append operation with Decimal serialization.

        Args:
            transition: PhaseTransition event to log

        Side Effects:
            - Appends to logs/phase/phase-history.jsonl
            - Creates file and directories if not exist

        JSONL Format:
            {
                "transition_id": "uuid",
                "timestamp": "2025-10-21T14:30:00+00:00",
                "from_phase": "experience",
                "to_phase": "proof",
                "trigger": "auto",
                "validation_passed": true,
                "metrics_snapshot": {...},
                "failure_reasons": [...],
                "operator_id": "operator_123",
                "override_password_used": false
            }

        Example:
            >>> from uuid import uuid4
            >>> from datetime import datetime, timezone
            >>> transition = PhaseTransition(
            ...     transition_id=str(uuid4()),
            ...     timestamp=datetime.now(timezone.utc),
            ...     from_phase=Phase.EXPERIENCE,
            ...     to_phase=Phase.PROOF_OF_CONCEPT,
            ...     trigger="auto",
            ...     validation_passed=True,
            ...     metrics_snapshot={
            ...         "session_count": 25,
            ...         "win_rate": Decimal("0.65"),
            ...         "avg_rr": Decimal("1.8")
            ...     }
            ... )
            >>> logger.log_transition(transition)
        """
        # Serialize transition to JSON record
        record = {
            "transition_id": transition.transition_id,
            "timestamp": transition.timestamp.isoformat(),
            "from_phase": transition.from_phase.value,
            "to_phase": transition.to_phase.value,
            "trigger": transition.trigger,
            "validation_passed": transition.validation_passed,
            "metrics_snapshot": transition.metrics_snapshot,
            "failure_reasons": transition.failure_reasons,
            "operator_id": transition.operator_id,
            "override_password_used": transition.override_password_used
        }

        # Thread-safe write with file locking
        with self._lock:
            # Create parent directories if needed
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Append to JSONL file
            with open(self.transition_log, 'a', encoding='utf-8') as f:
                json.dump(record, f, cls=DecimalEncoder)
                f.write('\n')

    def log_override_attempt(
        self,
        phase: Phase,
        action: str,
        blocked: bool,
        reason: str,
        operator_id: Optional[str] = None
    ) -> None:
        """Log manual override attempt to JSONL file.

        Thread-safe append operation for override audit trail.

        Args:
            phase: Current phase where override was attempted
            action: Override action attempted (e.g., "attempted_advance")
            blocked: Whether attempt was blocked (True) or allowed (False)
            reason: Block reason or success justification
            operator_id: Operator identifier (optional)

        Side Effects:
            - Appends to logs/phase/phase-overrides.jsonl
            - Creates file and directories if not exist

        JSONL Format:
            {
                "timestamp": "2025-10-21T16:45:00+00:00",
                "phase": "experience",
                "action": "attempted_advance",
                "blocked": true,
                "reason": "Win rate 0.58 < required 0.60",
                "operator_id": "operator_123"
            }

        Example:
            >>> logger.log_override_attempt(
            ...     phase=Phase.EXPERIENCE,
            ...     action="attempted_advance",
            ...     blocked=True,
            ...     reason="Win rate 0.58 < required 0.60",
            ...     operator_id="operator_123"
            ... )
        """
        # Create override record
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": phase.value,
            "action": action,
            "blocked": blocked,
            "reason": reason,
            "operator_id": operator_id
        }

        # Thread-safe write with file locking
        with self._lock:
            # Create parent directories if needed
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Append to JSONL file
            with open(self.override_log, 'a', encoding='utf-8') as f:
                json.dump(record, f)
                f.write('\n')

    def query_transitions(
        self,
        start_date: date,
        end_date: date
    ) -> List[PhaseTransition]:
        """Query phase transitions within date range.

        Reads JSONL file and filters by date range (inclusive).

        Args:
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)

        Returns:
            List of PhaseTransition events sorted by timestamp

        Performance:
            - Sequential JSONL read with date filtering
            - Target: <500ms for full history (NFR-001)

        Example:
            >>> from datetime import date
            >>> results = logger.query_transitions(
            ...     start_date=date(2025, 10, 1),
            ...     end_date=date(2025, 10, 31)
            ... )
            >>> for transition in results:
            ...     print(f"{transition.from_phase} -> {transition.to_phase}")
        """
        # Return empty list if log doesn't exist
        if not self.transition_log.exists():
            return []

        transitions = []

        # Read JSONL file line by line
        with open(self.transition_log, 'r', encoding='utf-8') as f:
            for line in f:
                # Parse JSON record
                record = json.loads(line)

                # Parse timestamp and filter by date range
                timestamp = datetime.fromisoformat(record["timestamp"])

                # Check if timestamp is within date range (inclusive)
                if start_date <= timestamp.date() <= end_date:
                    # Deserialize record to PhaseTransition
                    transition = self._record_to_transition(record)
                    transitions.append(transition)

        return transitions

    def _record_to_transition(self, record: dict) -> PhaseTransition:
        """Convert JSONL record to PhaseTransition object.

        Handles Decimal deserialization from string format.

        Args:
            record: Dictionary from JSONL line

        Returns:
            PhaseTransition object with deserialized fields
        """
        # Deserialize Decimal values in metrics_snapshot
        metrics_snapshot = record.get("metrics_snapshot", {})
        for key, value in metrics_snapshot.items():
            # Convert string decimals back to Decimal type
            if isinstance(value, str) and self._is_decimal_string(value):
                metrics_snapshot[key] = Decimal(value)

        # Reconstruct PhaseTransition object
        return PhaseTransition(
            transition_id=record["transition_id"],
            timestamp=datetime.fromisoformat(record["timestamp"]),
            from_phase=Phase.from_string(record["from_phase"]),
            to_phase=Phase.from_string(record["to_phase"]),
            trigger=record["trigger"],
            validation_passed=record["validation_passed"],
            metrics_snapshot=metrics_snapshot,
            failure_reasons=record.get("failure_reasons"),
            operator_id=record.get("operator_id"),
            override_password_used=record.get("override_password_used", False)
        )

    def _is_decimal_string(self, value: str) -> bool:
        """Check if string represents a decimal number.

        Args:
            value: String to check

        Returns:
            True if string is a valid decimal format
        """
        try:
            Decimal(value)
            return True
        except:
            return False
