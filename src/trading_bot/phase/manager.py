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
from trading_bot.phase.models import Phase, PhaseTransition, SessionMetrics
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

    def calculate_session_metrics(self, session_date: date) -> SessionMetrics:
        """Calculate metrics for a trading session.

        Note: In real implementation, this would call PerformanceTracker.
        For now, returns mock data for testing.

        Args:
            session_date: Date of the trading session

        Returns:
            SessionMetrics with session performance data
        """
        # TODO: Replace with actual PerformanceTracker integration
        # summary = self.performance_tracker.get_summary(
        #     window="daily",
        #     start_date=session_date,
        #     end_date=session_date
        # )

        # Mock implementation for testing
        return SessionMetrics(
            session_date=session_date,
            phase=self.config.current_phase,
            trades_executed=5,
            total_wins=3,
            total_losses=2,
            win_rate=Decimal("0.60"),
            average_rr=Decimal("1.5"),
            total_pnl=Decimal("100.00"),
            position_sizes=[Decimal("100")] * 5,
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )

    def validate_transition(
        self,
        to_phase: Phase,
        rolling_window: Optional[int] = None
    ) -> ValidationResult:
        """Validate if current phase can transition to target phase.

        Args:
            to_phase: Target phase to validate transition to
            rolling_window: Optional window size for rolling validation (10, 20, 50, 100)

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
                avg_rr=metrics.get("avg_rr", Decimal("0")),
                rolling_window=rolling_window
            )
        elif validator_key == ("proof", "trial"):
            return validator.validate(
                session_count=metrics.get("session_count", 0),
                trade_count=metrics.get("trade_count", 0),
                win_rate=metrics.get("win_rate", Decimal("0")),
                avg_rr=metrics.get("avg_rr", Decimal("0")),
                rolling_window=rolling_window
            )
        elif validator_key == ("trial", "scaling"):
            return validator.validate(
                session_count=metrics.get("session_count", 0),
                trade_count=metrics.get("trade_count", 0),
                win_rate=metrics.get("win_rate", Decimal("0")),
                avg_rr=metrics.get("avg_rr", Decimal("0")),
                max_drawdown=metrics.get("max_drawdown", Decimal("0")),
                rolling_window=rolling_window
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

    def get_position_size(
        self,
        phase: Phase,
        consecutive_wins: int = 0,
        rolling_win_rate: Optional[Decimal] = None,
        portfolio_value: Optional[Decimal] = None
    ) -> Decimal:
        """Calculate position size based on phase and consistency metrics.

        Args:
            phase: Current trading phase
            consecutive_wins: Number of consecutive winning trades
            rolling_win_rate: Win rate over last 10 sessions (for Scaling phase)
            portfolio_value: Total portfolio value (for 5% cap)

        Returns:
            Position size in USD (Decimal)

        Rules (FR-005):
            - Experience: $0 (paper trading)
            - PoC: $100 (fixed)
            - Trial: $200 (fixed)
            - Scaling: $200-$2,000 based on consistency
              - Start: $200
              - +$100 per 5 consecutive wins
              - +$200 if 10-session win rate >=70%
              - Max: $2,000 OR 5% of portfolio (whichever lower)
        """
        if phase == Phase.EXPERIENCE:
            return Decimal("0")

        if phase == Phase.PROOF_OF_CONCEPT:
            return Decimal("100")

        if phase == Phase.REAL_MONEY_TRIAL:
            return Decimal("200")

        if phase == Phase.SCALING:
            # Start at base size
            size = Decimal("200")

            # Add $100 per 5 consecutive wins
            if consecutive_wins >= 5:
                increases = consecutive_wins // 5
                size += Decimal("100") * increases

            # Add $200 if win rate >=70%
            if rolling_win_rate and rolling_win_rate >= Decimal("0.70"):
                size += Decimal("200")

            # Cap at $2,000
            size = min(size, Decimal("2000"))

            # Cap at 5% of portfolio if provided
            if portfolio_value:
                max_from_portfolio = portfolio_value * Decimal("0.05")
                size = min(size, max_from_portfolio)

            return size

        # Default fallback
        return Decimal("0")

    def check_downgrade_triggers(self, metrics: SessionMetrics) -> Optional[Phase]:
        """Check if current metrics trigger automatic downgrade.

        Args:
            metrics: Current session metrics

        Returns:
            Target downgrade phase if triggers met, None otherwise

        Trigger conditions (FR-006):
            - 3 consecutive losses
            - Rolling 20-trade win rate <55%
            - Daily loss >5%
        """
        current_phase = Phase.from_string(self.config.current_phase)

        # Can't downgrade from Experience (lowest phase)
        if current_phase == Phase.EXPERIENCE:
            return None

        # Check consecutive losses
        if metrics.total_losses >= 3 and metrics.total_wins == 0:
            # 3 consecutive losses (no wins in session)
            return self._get_previous_phase(current_phase)

        # Check rolling win rate
        if metrics.win_rate < Decimal("0.55"):
            # Win rate below 55% threshold
            return self._get_previous_phase(current_phase)

        # Check daily loss percentage
        if metrics.total_pnl < Decimal("0"):
            # Calculate loss percentage (need portfolio value)
            # For now, use absolute threshold
            if abs(metrics.total_pnl) > Decimal("500"):  # Mock: $500 loss threshold
                return self._get_previous_phase(current_phase)

        # No downgrade needed
        return None

    def _get_previous_phase(self, current_phase: Phase) -> Phase:
        """Get the previous phase in progression.

        Args:
            current_phase: Current phase

        Returns:
            Previous phase in progression sequence
        """
        phase_order = [
            Phase.EXPERIENCE,
            Phase.PROOF_OF_CONCEPT,
            Phase.REAL_MONEY_TRIAL,
            Phase.SCALING
        ]

        current_index = phase_order.index(current_phase)
        if current_index > 0:
            return phase_order[current_index - 1]

        return Phase.EXPERIENCE  # Can't go lower

    def apply_downgrade(self, to_phase: Phase, reason: str) -> PhaseTransition:
        """Apply automatic phase downgrade.

        Creates downgrade transition record and updates config.

        Args:
            to_phase: Target phase to downgrade to
            reason: Reason for downgrade

        Returns:
            PhaseTransition record
        """
        from_phase = Phase.from_string(self.config.current_phase)

        transition = PhaseTransition(
            transition_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            from_phase=from_phase,
            to_phase=to_phase,
            trigger="auto",
            validation_passed=False,  # Downgrade, not advancement
            metrics_snapshot={},
            failure_reasons=[reason],
            override_password_used=False
        )

        # Update config
        self.config.current_phase = to_phase.value

        # TODO: Log transition with history_logger if available
        # if hasattr(self, 'history_logger'):
        #     self.history_logger.log_transition(transition)

        return transition
