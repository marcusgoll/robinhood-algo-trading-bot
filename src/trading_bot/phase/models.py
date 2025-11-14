"""Phase progression data models.

Defines core entities for the four-phase trading progression system.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any


class Phase(str, Enum):
    """Trading phase enum.

    Progression: EXPERIENCE → PROOF_OF_CONCEPT → REAL_MONEY_TRIAL → SCALING
    """
    EXPERIENCE = "experience"
    PROOF_OF_CONCEPT = "proof"
    REAL_MONEY_TRIAL = "trial"
    SCALING = "scaling"

    @classmethod
    def from_string(cls, value: str) -> "Phase":
        """Convert string to Phase enum.

        Args:
            value: Phase string value (lowercase)

        Returns:
            Phase enum

        Raises:
            ValueError: If value is not a valid phase
        """
        for phase in cls:
            if phase.value == value:
                return phase
        raise ValueError(f"Invalid phase: {value}")


class PhaseOverrideError(Exception):
    """Raised when manual override attempt fails.

    Used for FR-007 override password verification.
    """
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Phase override failed: {reason}")


@dataclass
class SessionMetrics:
    """Trading session performance metrics.

    Tracks profitability, win rate, and consistency for phase validation.
    """
    session_date: date
    phase: str  # Phase enum value
    trades_executed: int
    total_wins: int = 0
    total_losses: int = 0
    win_rate: Decimal = Decimal("0")
    average_rr: Decimal = Decimal("0")  # Average risk-reward ratio
    total_pnl: Decimal = Decimal("0")  # Total profit/loss
    position_sizes: List[Decimal] = field(default_factory=list)
    circuit_breaker_trips: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PhaseTransition:
    """Phase transition event record.

    Logged to phase-history.jsonl for audit trail.
    """
    transition_id: str  # UUID
    timestamp: datetime  # UTC
    from_phase: Phase
    to_phase: Phase
    trigger: str  # "auto" or "manual"
    validation_passed: bool
    metrics_snapshot: Dict[str, Any]
    failure_reasons: Optional[List[str]] = None
    operator_id: Optional[str] = None
    override_password_used: bool = False
