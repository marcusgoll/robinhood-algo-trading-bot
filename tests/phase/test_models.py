"""
Unit Tests for Phase Progression Models

Tests the dataclass models used for position scaling and phase progression:
- Phase enum: Experience, Proof of Concept, Real Money Trial, Scaling
- SessionMetrics: Daily trading session profitability metrics

Feature: 022-pos-scale-progress
Tasks:
- T010: Write FAILING tests for Phase enum (TDD RED phase)
- T011: Write FAILING tests for SessionMetrics dataclass (TDD RED phase)
Pattern Reference: tests/patterns/test_models.py
Spec: specs/022-pos-scale-progress/data-model.md
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import date, datetime, timezone

from src.trading_bot.phase.models import Phase, PhaseTransition, SessionMetrics  # Will fail initially - no models.py yet


class TestPhaseEnum:
    """Tests for Phase enum."""

    def test_phase_enum_values(self):
        """Test that all 4 phases are defined.

        Given: Phase enum should have 4 progression phases
        When: Accessing Phase enum values
        Then: All 4 phases (EXPERIENCE, PROOF_OF_CONCEPT, REAL_MONEY_TRIAL, SCALING) exist
        """
        # Given/When: Phase enum should have all 4 values
        # Then: All phases are defined
        assert Phase.EXPERIENCE
        assert Phase.PROOF_OF_CONCEPT
        assert Phase.REAL_MONEY_TRIAL
        assert Phase.SCALING

    def test_phase_string_conversion(self):
        """Test Phase enum to/from string conversion.

        Given: Phase enum values with string representations
        When: Converting to/from strings using .value and from_string()
        Then: String conversion works bidirectionally
        """
        # Given/When: Phase.EXPERIENCE has string value "experience"
        assert Phase.EXPERIENCE.value == "experience"
        assert Phase.from_string("experience") == Phase.EXPERIENCE

        # Given/When: Phase.PROOF_OF_CONCEPT has string value "proof"
        assert Phase.PROOF_OF_CONCEPT.value == "proof"
        assert Phase.from_string("proof") == Phase.PROOF_OF_CONCEPT

        # Given/When: Phase.REAL_MONEY_TRIAL has string value "trial"
        assert Phase.REAL_MONEY_TRIAL.value == "trial"
        assert Phase.from_string("trial") == Phase.REAL_MONEY_TRIAL

        # Given/When: Phase.SCALING has string value "scaling"
        assert Phase.SCALING.value == "scaling"
        assert Phase.from_string("scaling") == Phase.SCALING

    def test_invalid_phase_handling(self):
        """Test invalid phase name raises ValueError.

        Given: An invalid phase name string
        When: Attempting to convert with from_string()
        Then: ValueError is raised
        """
        # Given: Invalid phase name
        invalid_phase = "invalid_phase"

        # When/Then: from_string() raises ValueError
        with pytest.raises(ValueError):
            Phase.from_string(invalid_phase)

    def test_phase_enum_order(self):
        """Test phase enum values are ordered correctly.

        Given: Phase enum should follow progression order
        When: Iterating through Phase values
        Then: Phases appear in order: EXPERIENCE, PROOF_OF_CONCEPT, REAL_MONEY_TRIAL, SCALING
        """
        # Given: Phase enum values in list form
        phases = list(Phase)

        # Then: Phases are in progression order
        assert phases[0] == Phase.EXPERIENCE
        assert phases[1] == Phase.PROOF_OF_CONCEPT
        assert phases[2] == Phase.REAL_MONEY_TRIAL
        assert phases[3] == Phase.SCALING

    def test_phase_enum_count(self):
        """Test that Phase enum has exactly 4 values.

        Given: Phase enum for trading progression
        When: Counting enum members
        Then: Exactly 4 phases are defined
        """
        # Given: Phase enum members
        phases = list(Phase)

        # Then: Exactly 4 phases
        assert len(phases) == 4

    def test_phase_string_values_match_spec(self):
        """Test Phase string values match data-model.md specification.

        Given: Phase enum string values from spec (experience, proof, trial, scaling)
        When: Checking .value attributes
        Then: String values match specification exactly
        """
        # Given: Expected string values from spec
        expected_values = {"experience", "proof", "trial", "scaling"}

        # When: Getting actual enum values
        actual_values = {phase.value for phase in Phase}

        # Then: Values match specification
        assert actual_values == expected_values

    def test_phase_from_string_case_sensitive(self):
        """Test from_string() is case-sensitive.

        Given: Phase string values in different cases
        When: Converting with from_string()
        Then: Only lowercase values work (case-sensitive)
        """
        # Given: Valid lowercase phase
        assert Phase.from_string("experience") == Phase.EXPERIENCE

        # When/Then: Uppercase should raise ValueError
        with pytest.raises(ValueError):
            Phase.from_string("EXPERIENCE")

        # When/Then: Mixed case should raise ValueError
        with pytest.raises(ValueError):
            Phase.from_string("Experience")


class TestSessionMetrics:
    """Tests for SessionMetrics dataclass."""

    def test_session_metrics_fields(self):
        """Test SessionMetrics has all required fields.

        Given: Valid SessionMetrics parameters with all required fields
        When: Creating a SessionMetrics instance
        Then: Object is created with correct field values
        """
        # Given: Valid session metrics parameters
        session_date = date(2025, 10, 21)
        phase = "experience"
        trades_executed = 5
        total_wins = 3
        total_losses = 2
        win_rate = Decimal("0.60")
        average_rr = Decimal("1.5")
        total_pnl = Decimal("100.00")
        position_sizes = [Decimal("100"), Decimal("100")]
        circuit_breaker_trips = 0
        created_at = datetime.now(timezone.utc)

        # When: Creating SessionMetrics instance
        metrics = SessionMetrics(
            session_date=session_date,
            phase=phase,
            trades_executed=trades_executed,
            total_wins=total_wins,
            total_losses=total_losses,
            win_rate=win_rate,
            average_rr=average_rr,
            total_pnl=total_pnl,
            position_sizes=position_sizes,
            circuit_breaker_trips=circuit_breaker_trips,
            created_at=created_at
        )

        # Then: All fields are set correctly
        assert metrics.session_date == date(2025, 10, 21)
        assert metrics.phase == "experience"
        assert metrics.trades_executed == 5
        assert metrics.total_wins == 3
        assert metrics.total_losses == 2
        assert metrics.win_rate == Decimal("0.60")
        assert metrics.average_rr == Decimal("1.5")
        assert metrics.total_pnl == Decimal("100.00")
        assert metrics.position_sizes == [Decimal("100"), Decimal("100")]
        assert metrics.circuit_breaker_trips == 0
        assert metrics.created_at == created_at

    def test_session_metrics_decimal_precision(self):
        """Test Decimal precision for financial fields.

        Given: Precise Decimal values for win_rate, average_rr, total_pnl
        When: Creating SessionMetrics instance
        Then: Decimal precision is maintained exactly (no float rounding)
        """
        # Given: Precise decimal values for financial metrics
        win_rate = Decimal("0.65")
        average_rr = Decimal("1.8")
        total_pnl = Decimal("250.50")

        # When: Creating SessionMetrics with precise decimals
        metrics = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="experience",
            trades_executed=5,
            total_wins=3,
            total_losses=2,
            win_rate=win_rate,
            average_rr=average_rr,
            total_pnl=total_pnl,
            position_sizes=[],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )

        # Then: Decimal precision is maintained
        assert isinstance(metrics.win_rate, Decimal)
        assert isinstance(metrics.average_rr, Decimal)
        assert isinstance(metrics.total_pnl, Decimal)

        # Verify no float rounding
        assert metrics.win_rate == Decimal("0.65")
        assert metrics.average_rr == Decimal("1.8")
        assert metrics.total_pnl == Decimal("250.50")

    def test_session_metrics_utc_timestamp(self):
        """Test created_at is UTC timezone-aware.

        Given: Current UTC datetime for created_at field
        When: Creating SessionMetrics with UTC timestamp
        Then: Timestamp is timezone-aware with UTC timezone
        """
        # Given: Current UTC time
        now_utc = datetime.now(timezone.utc)

        # When: Creating SessionMetrics with UTC timestamp
        metrics = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="experience",
            trades_executed=0,
            total_wins=0,
            total_losses=0,
            win_rate=Decimal("0"),
            average_rr=Decimal("0"),
            total_pnl=Decimal("0"),
            position_sizes=[],
            circuit_breaker_trips=0,
            created_at=now_utc
        )

        # Then: Timestamp is UTC timezone-aware
        assert metrics.created_at.tzinfo == timezone.utc
        assert metrics.created_at == now_utc

    def test_session_metrics_date_type(self):
        """Test session_date is date type (not datetime).

        Given: session_date as Python date object
        When: Creating SessionMetrics instance
        Then: session_date field is date type (not datetime)
        """
        # Given: Date object for session_date
        session_date = date(2025, 10, 21)

        # When: Creating SessionMetrics
        metrics = SessionMetrics(
            session_date=session_date,
            phase="proof",
            trades_executed=1,
            total_wins=1,
            total_losses=0,
            win_rate=Decimal("1.0"),
            average_rr=Decimal("2.0"),
            total_pnl=Decimal("50.00"),
            position_sizes=[Decimal("100")],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )

        # Then: session_date is date type
        assert isinstance(metrics.session_date, date)
        assert metrics.session_date == date(2025, 10, 21)

    def test_session_metrics_win_rate_validation(self):
        """Test win_rate is within valid range (0.00-1.00).

        Given: Various win_rate values (0.0, 0.5, 1.0)
        When: Creating SessionMetrics instances
        Then: Win rates are stored correctly as Decimal
        """
        # Given/When: Zero win rate (all losses)
        metrics_zero = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="experience",
            trades_executed=5,
            total_wins=0,
            total_losses=5,
            win_rate=Decimal("0.0"),
            average_rr=Decimal("0"),
            total_pnl=Decimal("-100.00"),
            position_sizes=[],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_zero.win_rate == Decimal("0.0")

        # Given/When: 50% win rate
        metrics_half = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="experience",
            trades_executed=10,
            total_wins=5,
            total_losses=5,
            win_rate=Decimal("0.50"),
            average_rr=Decimal("1.5"),
            total_pnl=Decimal("0"),
            position_sizes=[],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_half.win_rate == Decimal("0.50")

        # Given/When: 100% win rate (all wins)
        metrics_full = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="experience",
            trades_executed=5,
            total_wins=5,
            total_losses=0,
            win_rate=Decimal("1.0"),
            average_rr=Decimal("2.0"),
            total_pnl=Decimal("500.00"),
            position_sizes=[],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_full.win_rate == Decimal("1.0")

    def test_session_metrics_non_negative_trades(self):
        """Test trades_executed is non-negative integer.

        Given: trades_executed >= 0
        When: Creating SessionMetrics instance
        Then: trades_executed is stored as non-negative int
        """
        # Given: Zero trades executed (no trading day)
        metrics = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="experience",
            trades_executed=0,
            total_wins=0,
            total_losses=0,
            win_rate=Decimal("0"),
            average_rr=Decimal("0"),
            total_pnl=Decimal("0"),
            position_sizes=[],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )

        # Then: trades_executed is non-negative
        assert metrics.trades_executed == 0
        assert metrics.trades_executed >= 0

    def test_session_metrics_position_sizes_list(self):
        """Test position_sizes is list of Decimal values.

        Given: List of position sizes (Decimal values)
        When: Creating SessionMetrics with position_sizes
        Then: position_sizes stored as List[Decimal]
        """
        # Given: Multiple position sizes for scaling phase
        position_sizes = [
            Decimal("100"),
            Decimal("200"),
            Decimal("500"),
            Decimal("1000")
        ]

        # When: Creating SessionMetrics with position sizes
        metrics = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="scaling",
            trades_executed=4,
            total_wins=3,
            total_losses=1,
            win_rate=Decimal("0.75"),
            average_rr=Decimal("2.5"),
            total_pnl=Decimal("850.00"),
            position_sizes=position_sizes,
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )

        # Then: position_sizes is list of Decimals
        assert metrics.position_sizes == position_sizes
        assert all(isinstance(size, Decimal) for size in metrics.position_sizes)
        assert len(metrics.position_sizes) == 4

    def test_session_metrics_empty_position_sizes(self):
        """Test position_sizes can be empty list (paper trading).

        Given: Empty position_sizes list (experience phase)
        When: Creating SessionMetrics
        Then: position_sizes is empty list
        """
        # Given: Experience phase with no real positions
        metrics = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="experience",
            trades_executed=5,
            total_wins=3,
            total_losses=2,
            win_rate=Decimal("0.60"),
            average_rr=Decimal("1.5"),
            total_pnl=Decimal("100.00"),
            position_sizes=[],  # Empty for paper trading
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )

        # Then: position_sizes is empty
        assert metrics.position_sizes == []
        assert len(metrics.position_sizes) == 0

    def test_session_metrics_circuit_breaker_trips(self):
        """Test circuit_breaker_trips is non-negative integer.

        Given: Number of circuit breaker activations (0 or positive)
        When: Creating SessionMetrics
        Then: circuit_breaker_trips stored correctly
        """
        # Given: No circuit breaker trips (normal session)
        metrics_normal = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="proof",
            trades_executed=1,
            total_wins=1,
            total_losses=0,
            win_rate=Decimal("1.0"),
            average_rr=Decimal("2.0"),
            total_pnl=Decimal("50.00"),
            position_sizes=[Decimal("100")],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_normal.circuit_breaker_trips == 0

        # Given: Multiple circuit breaker trips (volatile session)
        metrics_volatile = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="trial",
            trades_executed=3,
            total_wins=0,
            total_losses=3,
            win_rate=Decimal("0.0"),
            average_rr=Decimal("0"),
            total_pnl=Decimal("-300.00"),
            position_sizes=[Decimal("200"), Decimal("200"), Decimal("200")],
            circuit_breaker_trips=2,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_volatile.circuit_breaker_trips == 2

    def test_session_metrics_negative_pnl(self):
        """Test total_pnl can be negative (losing session).

        Given: Negative total_pnl (losing session)
        When: Creating SessionMetrics
        Then: Negative P&L is stored correctly
        """
        # Given: Losing session with negative P&L
        metrics = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="trial",
            trades_executed=5,
            total_wins=1,
            total_losses=4,
            win_rate=Decimal("0.20"),
            average_rr=Decimal("1.0"),
            total_pnl=Decimal("-150.50"),
            position_sizes=[Decimal("200")] * 5,
            circuit_breaker_trips=1,
            created_at=datetime.now(timezone.utc)
        )

        # Then: Negative P&L stored correctly
        assert metrics.total_pnl == Decimal("-150.50")
        assert metrics.total_pnl < Decimal("0")

    def test_session_metrics_phase_values(self):
        """Test SessionMetrics with different phase values.

        Given: Different phase values (experience, proof, trial, scaling)
        When: Creating SessionMetrics for each phase
        Then: Phase values are stored correctly
        """
        # Given/When: Experience phase
        metrics_exp = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="experience",
            trades_executed=10,
            total_wins=6,
            total_losses=4,
            win_rate=Decimal("0.60"),
            average_rr=Decimal("1.5"),
            total_pnl=Decimal("100.00"),
            position_sizes=[],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_exp.phase == "experience"

        # Given/When: Proof of Concept phase
        metrics_poc = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="proof",
            trades_executed=1,
            total_wins=1,
            total_losses=0,
            win_rate=Decimal("1.0"),
            average_rr=Decimal("2.0"),
            total_pnl=Decimal("50.00"),
            position_sizes=[Decimal("100")],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_poc.phase == "proof"

        # Given/When: Trial phase
        metrics_trial = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="trial",
            trades_executed=5,
            total_wins=4,
            total_losses=1,
            win_rate=Decimal("0.80"),
            average_rr=Decimal("2.5"),
            total_pnl=Decimal("400.00"),
            position_sizes=[Decimal("200")] * 5,
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_trial.phase == "trial"

        # Given/When: Scaling phase
        metrics_scaling = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="scaling",
            trades_executed=10,
            total_wins=7,
            total_losses=3,
            win_rate=Decimal("0.70"),
            average_rr=Decimal("2.0"),
            total_pnl=Decimal("1500.00"),
            position_sizes=[Decimal("500"), Decimal("1000"), Decimal("1500")],
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )
        assert metrics_scaling.phase == "scaling"

    def test_session_metrics_equality(self):
        """Test SessionMetrics equality comparison.

        Given: Two SessionMetrics instances with identical values
        When: Comparing them with ==
        Then: They are equal (dataclass auto-generates __eq__)
        """
        # Given: Shared timestamp and parameters
        session_date = date(2025, 10, 21)
        created_at = datetime.now(timezone.utc)

        # When: Creating two identical SessionMetrics instances
        metrics1 = SessionMetrics(
            session_date=session_date,
            phase="experience",
            trades_executed=5,
            total_wins=3,
            total_losses=2,
            win_rate=Decimal("0.60"),
            average_rr=Decimal("1.5"),
            total_pnl=Decimal("100.00"),
            position_sizes=[Decimal("100"), Decimal("100")],
            circuit_breaker_trips=0,
            created_at=created_at
        )

        metrics2 = SessionMetrics(
            session_date=session_date,
            phase="experience",
            trades_executed=5,
            total_wins=3,
            total_losses=2,
            win_rate=Decimal("0.60"),
            average_rr=Decimal("1.5"),
            total_pnl=Decimal("100.00"),
            position_sizes=[Decimal("100"), Decimal("100")],
            circuit_breaker_trips=0,
            created_at=created_at
        )

        # Then: They are equal
        assert metrics1 == metrics2

    def test_session_metrics_total_wins_losses_relationship(self):
        """Test total_wins and total_losses relationship with trades_executed.

        Given: total_wins + total_losses <= trades_executed
        When: Creating SessionMetrics
        Then: Win/loss counts make sense relative to total trades
        """
        # Given: Valid win/loss counts
        metrics = SessionMetrics(
            session_date=date(2025, 10, 21),
            phase="trial",
            trades_executed=10,
            total_wins=6,
            total_losses=4,
            win_rate=Decimal("0.60"),
            average_rr=Decimal("1.8"),
            total_pnl=Decimal("200.00"),
            position_sizes=[Decimal("200")] * 10,
            circuit_breaker_trips=0,
            created_at=datetime.now(timezone.utc)
        )

        # Then: Win/loss counts valid relative to total trades
        assert metrics.total_wins + metrics.total_losses == metrics.trades_executed
        assert metrics.total_wins >= 0
        assert metrics.total_losses >= 0


class TestPhaseTransition:
    """Tests for PhaseTransition dataclass.

    Feature: 022-pos-scale-progress
    Task: T012 - Write tests for PhaseTransition dataclass (TDD RED phase)
    """

    def test_phase_transition_fields(self):
        """Test PhaseTransition has all required fields.

        Given: Complete PhaseTransition parameters
        When: Creating a PhaseTransition instance
        Then: Object is created with correct field values
        """
        # Given: Valid phase transition parameters
        transition_id = str(uuid4())
        now_utc = datetime.now(timezone.utc)

        # When: Creating PhaseTransition instance
        transition = PhaseTransition(
            transition_id=transition_id,
            timestamp=now_utc,
            from_phase=Phase.EXPERIENCE,
            to_phase=Phase.PROOF_OF_CONCEPT,
            trigger="auto",
            validation_passed=True,
            metrics_snapshot={
                "session_count": 20,
                "win_rate": "0.65",
                "avg_rr": "1.6"
            },
            failure_reasons=None,
            operator_id=None,
            override_password_used=False
        )

        # Then: All fields are set correctly
        assert transition.transition_id == transition_id
        assert transition.timestamp == now_utc
        assert transition.from_phase == Phase.EXPERIENCE
        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert transition.trigger == "auto"
        assert transition.validation_passed is True
        assert transition.metrics_snapshot["session_count"] == 20
        assert transition.failure_reasons is None
        assert transition.operator_id is None
        assert transition.override_password_used is False

    def test_phase_transition_with_failure(self):
        """Test PhaseTransition with validation failure.

        Given: Phase transition that failed validation
        When: Creating PhaseTransition with failure reasons
        Then: Failure details are stored correctly
        """
        # Given: Failed transition parameters
        transition_id = str(uuid4())
        now_utc = datetime.now(timezone.utc)
        failure_reasons = ["Session count 15 < required 20"]

        # When: Creating failed transition
        transition = PhaseTransition(
            transition_id=transition_id,
            timestamp=now_utc,
            from_phase=Phase.EXPERIENCE,
            to_phase=Phase.PROOF_OF_CONCEPT,
            trigger="manual",
            validation_passed=False,
            metrics_snapshot={"session_count": 15},
            failure_reasons=failure_reasons,
            operator_id="test_operator",
            override_password_used=False
        )

        # Then: Failure details stored correctly
        assert transition.validation_passed is False
        assert len(transition.failure_reasons) == 1
        assert "Session count" in transition.failure_reasons[0]
        assert transition.operator_id == "test_operator"

    def test_phase_transition_metrics_snapshot(self):
        """Test metrics_snapshot serialization.

        Given: Phase transition with comprehensive metrics
        When: Creating PhaseTransition with detailed metrics_snapshot
        Then: All metrics are preserved as dictionary
        """
        # Given: Comprehensive metrics snapshot
        transition_id = str(uuid4())
        now_utc = datetime.now(timezone.utc)
        metrics_snapshot = {
            "session_count": 30,
            "win_rate": "0.70",
            "avg_rr": "1.9",
            "total_pnl": "500.00"
        }

        # When: Creating transition with metrics
        transition = PhaseTransition(
            transition_id=transition_id,
            timestamp=now_utc,
            from_phase=Phase.PROOF_OF_CONCEPT,
            to_phase=Phase.REAL_MONEY_TRIAL,
            trigger="auto",
            validation_passed=True,
            metrics_snapshot=metrics_snapshot,
            failure_reasons=None,
            operator_id=None,
            override_password_used=False
        )

        # Then: Metrics preserved correctly
        assert isinstance(transition.metrics_snapshot, dict)
        assert transition.metrics_snapshot["session_count"] == 30
        assert transition.metrics_snapshot["win_rate"] == "0.70"
        assert transition.metrics_snapshot["avg_rr"] == "1.9"
        assert transition.metrics_snapshot["total_pnl"] == "500.00"
