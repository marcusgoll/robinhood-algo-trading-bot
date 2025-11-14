"""Phase transition validators.

Implements profitability gate validation logic for phase progressions.
Each validator enforces specific criteria for advancing between phases.

Validators:
- ExperienceToPoCValidator: Experience → Proof of Concept
- PoCToTrialValidator: Proof of Concept → Real Money Trial
- TrialToScalingValidator: Real Money Trial → Scaling

Based on spec.md FR-002 (lines 169-186).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class ValidationResult:
    """Result of phase transition validation.

    Attributes:
        can_advance: Whether the trader can advance to the next phase
        criteria_met: Dictionary of criterion name to pass/fail status
        missing_requirements: List of criteria that were not met
        metrics_summary: Dictionary of metric values used in validation
    """
    can_advance: bool
    criteria_met: Dict[str, bool]
    missing_requirements: List[str]
    metrics_summary: Dict[str, any]


class ExperienceToPoCValidator:
    """Validator for Experience → Proof of Concept transition.

    Requirements (FR-002):
    - Minimum 20 profitable simulated sessions
    - Win rate ≥60%
    - Average risk-reward ratio ≥1.5
    """

    def validate(
        self,
        session_count: int,
        win_rate: Decimal,
        avg_rr: Decimal,
        rolling_window: Optional[int] = None
    ) -> ValidationResult:
        """Validate if trader can advance from Experience to PoC phase.

        Args:
            session_count: Number of completed trading sessions
            win_rate: Win rate as decimal (0.60 = 60%)
            avg_rr: Average risk-reward ratio
            rolling_window: If provided, only consider last N sessions

        Returns:
            ValidationResult with can_advance status and details
        """
        criteria_met = {
            "session_count": session_count >= 20,
            "win_rate": win_rate >= Decimal("0.60"),
            "avg_rr": avg_rr >= Decimal("1.5")
        }

        can_advance = all(criteria_met.values())
        missing = [k for k, v in criteria_met.items() if not v]

        return ValidationResult(
            can_advance=can_advance,
            criteria_met=criteria_met,
            missing_requirements=missing,
            metrics_summary={
                "session_count": session_count,
                "win_rate": str(win_rate),
                "avg_rr": str(avg_rr)
            }
        )


class PoCToTrialValidator:
    """Validator for Proof of Concept → Real Money Trial transition.

    Requirements (FR-002):
    - Minimum 30 trading days in PoC
    - Minimum 50 trades executed
    - Win rate ≥65% over last 50 trades
    - Average R:R ≥1.8
    """

    def validate(
        self,
        session_count: int,
        trade_count: int,
        win_rate: Decimal,
        avg_rr: Decimal,
        rolling_window: Optional[int] = None
    ) -> ValidationResult:
        """Validate if trader can advance from PoC to Trial phase.

        Args:
            session_count: Number of trading days in PoC phase
            trade_count: Total number of trades executed
            win_rate: Win rate as decimal (0.65 = 65%)
            avg_rr: Average risk-reward ratio
            rolling_window: If provided, only consider last N sessions

        Returns:
            ValidationResult with can_advance status and details
        """
        criteria_met = {
            "session_count": session_count >= 30,
            "trade_count": trade_count >= 50,
            "win_rate": win_rate >= Decimal("0.65"),
            "avg_rr": avg_rr >= Decimal("1.8")
        }

        can_advance = all(criteria_met.values())
        missing = [k for k, v in criteria_met.items() if not v]

        return ValidationResult(
            can_advance=can_advance,
            criteria_met=criteria_met,
            missing_requirements=missing,
            metrics_summary={
                "session_count": session_count,
                "trade_count": trade_count,
                "win_rate": str(win_rate),
                "avg_rr": str(avg_rr)
            }
        )


class TrialToScalingValidator:
    """Validator for Real Money Trial → Scaling transition.

    Requirements (FR-002):
    - Minimum 60 trading days in Trial
    - Minimum 100 trades executed
    - Win rate ≥70% over last 100 trades
    - Average R:R ≥2.0
    - Maximum drawdown <5%
    """

    def validate(
        self,
        session_count: int,
        trade_count: int,
        win_rate: Decimal,
        avg_rr: Decimal,
        max_drawdown: Decimal,
        rolling_window: Optional[int] = None
    ) -> ValidationResult:
        """Validate if trader can advance from Trial to Scaling phase.

        Args:
            session_count: Number of trading days in Trial phase
            trade_count: Total number of trades executed
            win_rate: Win rate as decimal (0.70 = 70%)
            avg_rr: Average risk-reward ratio
            max_drawdown: Maximum drawdown as decimal (0.05 = 5%)
            rolling_window: If provided, only consider last N sessions

        Returns:
            ValidationResult with can_advance status and details
        """
        criteria_met = {
            "session_count": session_count >= 60,
            "trade_count": trade_count >= 100,
            "win_rate": win_rate >= Decimal("0.70"),
            "avg_rr": avg_rr >= Decimal("2.0"),
            "max_drawdown": max_drawdown < Decimal("0.05")
        }

        can_advance = all(criteria_met.values())
        missing = [k for k, v in criteria_met.items() if not v]

        return ValidationResult(
            can_advance=can_advance,
            criteria_met=criteria_met,
            missing_requirements=missing,
            metrics_summary={
                "session_count": session_count,
                "trade_count": trade_count,
                "win_rate": str(win_rate),
                "avg_rr": str(avg_rr),
                "max_drawdown": str(max_drawdown)
            }
        )
