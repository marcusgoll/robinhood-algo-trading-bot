"""PhaseManager orchestration service.

Central service for managing phase transitions, validation, and progression.
Coordinates validators, config updates, and transition logging.

Based on specs/022-pos-scale-progress/contracts/phase-api.yaml
Tasks: T045-T047, T080-T081 (TradeLimiter integration)
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, Tuple
from uuid import uuid4

from trading_bot.config import Config
from trading_bot.phase.models import Phase, PhaseTransition
from trading_bot.phase.trade_limiter import TradeLimiter
from trading_bot.phase.validators import (
    ExperienceToPoCValidator,
    PoCToTrialValidator,
    TrialToScalingValidator,
    ValidationResult,
)


class PhaseValidationError(Exception):
    """Raised when phase transition validation fails.

    Attributes:
        result: ValidationResult containing detailed failure information
    """

    def __init__(self, validation_result: ValidationResult):
        """Initialize with validation result.

        Args:
            validation_result: Result of failed validation
        """
        self.result = validation_result
        super().__init__(self._format_error())

    def _format_error(self) -> str:
        """Format error message with missing requirements.

        Returns:
            Formatted error message string
        """
        return f"Phase validation failed: {', '.join(self.result.missing_requirements)}"


class PhaseManager:
    """Phase management orchestration service.

    Coordinates phase transitions, validation, and progression tracking.

    Attributes:
        config: Trading bot configuration
        validators: Map of (from_phase, to_phase) tuples to validator instances
        _metrics: Current metrics for validation (mocked in tests, from tracker in prod)
    """

    # Phase progression order for sequential validation
    PHASE_ORDER = [
        Phase.EXPERIENCE,
        Phase.PROOF_OF_CONCEPT,
        Phase.REAL_MONEY_TRIAL,
        Phase.SCALING
    ]

    def __init__(self, config: Config):
        """Initialize PhaseManager with configuration.

        Args:
            config: Trading bot configuration instance
        """
        self.config = config

        # Validator registry for each valid transition
        self.validators = {
            ("experience", "proof"): ExperienceToPoCValidator(),
            ("proof", "trial"): PoCToTrialValidator(),
            ("trial", "scaling"): TrialToScalingValidator()
        }

        # Trade limiter for PoC phase enforcement
        self.trade_limiter = TradeLimiter(config)

        # Metrics storage (for testing - in production this comes from PerformanceTracker)
        self._metrics: Dict[str, any] = {}

    def _is_sequential(self, from_phase: Phase, to_phase: Phase) -> bool:
        """Check if phase transition is sequential.

        Args:
            from_phase: Current phase
            to_phase: Target phase

        Returns:
            True if transition is to the next phase in sequence
        """
        try:
            from_idx = self.PHASE_ORDER.index(from_phase)
            to_idx = self.PHASE_ORDER.index(to_phase)
            return to_idx == from_idx + 1
        except ValueError:
            return False

    def _get_metrics(self) -> Dict[str, any]:
        """Get current metrics for validation.

        In production, this would call PerformanceTracker.get_summary().
        In tests, this uses the mocked _metrics attribute.

        Returns:
            Dictionary of metrics for validation
        """
        return self._metrics

    def validate_transition(self, to_phase: Phase) -> ValidationResult:
        """Validate if current phase can transition to target phase.

        Args:
            to_phase: Target phase to validate transition to

        Returns:
            ValidationResult with can_advance, criteria_met, missing_requirements

        Raises:
            ValueError: If transition is non-sequential or no validator exists
        """
        from_phase = Phase.from_string(self.config.current_phase)

        # Check sequential progression
        if not self._is_sequential(from_phase, to_phase):
            raise ValueError(
                f"Non-sequential transition: {from_phase.value} → {to_phase.value}"
            )

        # Get appropriate validator
        validator_key = (from_phase.value, to_phase.value)
        validator = self.validators.get(validator_key)

        if not validator:
            raise ValueError(
                f"No validator for {from_phase.value} → {to_phase.value}"
            )

        # Get metrics from tracker (or mock in tests)
        metrics = self._get_metrics()

        # Validate based on transition type
        if validator_key == ("experience", "proof"):
            return validator.validate(
                session_count=metrics.get("session_count", 0),
                win_rate=metrics.get("win_rate", Decimal("0")),
                avg_rr=metrics.get("avg_rr", Decimal("0"))
            )
        elif validator_key == ("proof", "trial"):
            return validator.validate(
                session_count=metrics.get("session_count", 0),
                trade_count=metrics.get("trade_count", 0),
                win_rate=metrics.get("win_rate", Decimal("0")),
                avg_rr=metrics.get("avg_rr", Decimal("0"))
            )
        elif validator_key == ("trial", "scaling"):
            return validator.validate(
                session_count=metrics.get("session_count", 0),
                trade_count=metrics.get("trade_count", 0),
                win_rate=metrics.get("win_rate", Decimal("0")),
                avg_rr=metrics.get("avg_rr", Decimal("0")),
                max_drawdown=metrics.get("max_drawdown", Decimal("0"))
            )
        else:
            raise ValueError(f"Unexpected validator key: {validator_key}")

    def advance_phase(self, to_phase: Phase, force: bool = False) -> PhaseTransition:
        """Advance to next phase after validation.

        Args:
            to_phase: Target phase to advance to
            force: Bypass validation (requires override password in production)

        Returns:
            PhaseTransition record with transition details

        Raises:
            PhaseValidationError: If validation fails and force=False
            ValueError: If transition is non-sequential
        """
        from_phase = Phase.from_string(self.config.current_phase)

        # Validate unless forced
        validation_result = None
        if not force:
            validation_result = self.validate_transition(to_phase)
            if not validation_result.can_advance:
                raise PhaseValidationError(validation_result)

        # Create transition record
        transition = PhaseTransition(
            transition_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            from_phase=from_phase,
            to_phase=to_phase,
            trigger="manual" if force else "auto",
            validation_passed=True,  # Either forced or validation passed
            metrics_snapshot=self._get_metrics(),
            override_password_used=force
        )

        # Update config (in-memory only, not persisted in this task)
        self.config.current_phase = to_phase.value

        return transition

    def enforce_trade_limit(self, phase: Phase, trade_date: date) -> None:
        """Enforce daily trade limit for given phase.

        Delegates to TradeLimiter for phase-specific limit checking.

        Args:
            phase: Current trading phase
            trade_date: Date of proposed trade

        Raises:
            TradeLimitExceeded: If daily limit exceeded for this phase
        """
        self.trade_limiter.check_limit(phase, trade_date)
