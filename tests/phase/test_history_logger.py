"""HistoryLogger tests (TDD RED → GREEN).

Tests the phase history logging system for audit trail.

Test Coverage:
- T050: log_transition() appends to phase-history.jsonl
- T051: log_override_attempt() appends to phase-overrides.jsonl
- query_transitions() reads by date range
- Decimal serialization
- UTC timestamps in ISO format

Based on: specs/022-pos-scale-progress/contracts/phase-api.yaml
"""

import json
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from src.trading_bot.phase.history_logger import HistoryLogger, DecimalEncoder
from src.trading_bot.phase.models import Phase, PhaseTransition


class TestDecimalEncoder:
    """Test custom JSON encoder for Decimal types."""

    def test_decimal_encoder_serializes_decimal(self):
        """Test DecimalEncoder converts Decimal to string."""
        data = {
            "value": Decimal("123.45"),
            "amount": Decimal("0.60")
        }

        result = json.dumps(data, cls=DecimalEncoder)

        assert '"value": "123.45"' in result
        assert '"amount": "0.60"' in result

    def test_decimal_encoder_preserves_other_types(self):
        """Test DecimalEncoder preserves non-Decimal types."""
        data = {
            "string": "test",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "null": None
        }

        result = json.dumps(data, cls=DecimalEncoder)
        parsed = json.loads(result)

        assert parsed["string"] == "test"
        assert parsed["int"] == 42
        assert parsed["float"] == 3.14
        assert parsed["bool"] is True
        assert parsed["null"] is None


class TestHistoryLogger:
    """Test HistoryLogger for phase transition audit trail (T050-T051)."""

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Create temporary log directory for testing."""
        log_dir = tmp_path / "logs" / "phase"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create HistoryLogger instance with temp directory."""
        return HistoryLogger(log_dir=temp_log_dir)

    @pytest.fixture
    def sample_transition(self):
        """Create sample PhaseTransition for testing."""
        return PhaseTransition(
            transition_id=str(uuid4()),
            timestamp=datetime(2025, 10, 21, 14, 30, 0, tzinfo=timezone.utc),
            from_phase=Phase.EXPERIENCE,
            to_phase=Phase.PROOF_OF_CONCEPT,
            trigger="auto",
            validation_passed=True,
            metrics_snapshot={
                "session_count": 25,
                "win_rate": Decimal("0.65"),
                "avg_rr": Decimal("1.8"),
                "total_pnl": Decimal("1250.50")
            },
            failure_reasons=None,
            operator_id=None,
            override_password_used=False
        )

    def test_logger_initialization(self, temp_log_dir):
        """Test HistoryLogger initializes with correct paths."""
        logger = HistoryLogger(log_dir=temp_log_dir)

        assert logger.log_dir == temp_log_dir
        assert logger.transition_log == temp_log_dir / "phase-history.jsonl"
        assert logger.override_log == temp_log_dir / "phase-overrides.jsonl"

    def test_log_transition_creates_file(self, logger, sample_transition):
        """Test log_transition creates JSONL file if not exists (T050)."""
        # File should not exist initially
        assert not logger.transition_log.exists()

        # Log transition
        logger.log_transition(sample_transition)

        # File should be created
        assert logger.transition_log.exists()

    def test_log_transition_appends_to_file(self, logger, sample_transition):
        """Test log_transition appends to existing file (T050)."""
        # Log first transition
        logger.log_transition(sample_transition)

        # Log second transition
        second_transition = PhaseTransition(
            transition_id=str(uuid4()),
            timestamp=datetime(2025, 10, 22, 10, 0, 0, tzinfo=timezone.utc),
            from_phase=Phase.PROOF_OF_CONCEPT,
            to_phase=Phase.REAL_MONEY_TRIAL,
            trigger="manual",
            validation_passed=True,
            metrics_snapshot={
                "session_count": 35,
                "trade_count": 55,
                "win_rate": Decimal("0.70"),
                "avg_rr": Decimal("2.0")
            }
        )
        logger.log_transition(second_transition)

        # Read file and verify both lines
        with open(logger.transition_log, "r") as f:
            lines = f.readlines()

        assert len(lines) == 2

    def test_log_transition_correct_jsonl_format(self, logger, sample_transition):
        """Test log_transition writes correct JSONL format (T050)."""
        logger.log_transition(sample_transition)

        # Read and parse JSONL line
        with open(logger.transition_log, "r") as f:
            line = f.readline()
            record = json.loads(line)

        # Verify all required fields
        assert record["transition_id"] == sample_transition.transition_id
        assert record["timestamp"] == "2025-10-21T14:30:00+00:00"
        assert record["from_phase"] == "experience"
        assert record["to_phase"] == "proof"
        assert record["trigger"] == "auto"
        assert record["validation_passed"] is True

        # Verify Decimal serialization
        assert record["metrics_snapshot"]["win_rate"] == "0.65"
        assert record["metrics_snapshot"]["avg_rr"] == "1.8"
        assert record["metrics_snapshot"]["total_pnl"] == "1250.50"

    def test_log_transition_handles_optional_fields(self, logger):
        """Test log_transition handles optional fields correctly."""
        transition = PhaseTransition(
            transition_id=str(uuid4()),
            timestamp=datetime(2025, 10, 21, 15, 0, 0, tzinfo=timezone.utc),
            from_phase=Phase.EXPERIENCE,
            to_phase=Phase.PROOF_OF_CONCEPT,
            trigger="manual",
            validation_passed=False,
            metrics_snapshot={
                "session_count": 15,
                "win_rate": Decimal("0.55")
            },
            failure_reasons=["Win rate below threshold (0.55 < 0.60)"],
            operator_id="operator_123",
            override_password_used=True
        )

        logger.log_transition(transition)

        # Read and verify
        with open(logger.transition_log, "r") as f:
            record = json.loads(f.readline())

        assert record["failure_reasons"] == ["Win rate below threshold (0.55 < 0.60)"]
        assert record["operator_id"] == "operator_123"
        assert record["override_password_used"] is True

    def test_log_override_attempt_creates_file(self, logger):
        """Test log_override_attempt creates JSONL file if not exists (T051)."""
        # File should not exist initially
        assert not logger.override_log.exists()

        # Log override attempt
        logger.log_override_attempt(
            phase=Phase.EXPERIENCE,
            action="attempted_advance",
            blocked=True,
            reason="Win rate 0.58 < required 0.60",
            operator_id="operator_123"
        )

        # File should be created
        assert logger.override_log.exists()

    def test_log_override_attempt_correct_format(self, logger):
        """Test log_override_attempt writes correct JSONL format (T051)."""
        # Log override
        logger.log_override_attempt(
            phase=Phase.EXPERIENCE,
            action="attempted_advance",
            blocked=True,
            reason="Win rate 0.58 < required 0.60",
            operator_id="operator_123"
        )

        # Read and verify
        with open(logger.override_log, "r") as f:
            record = json.loads(f.readline())

        assert record["phase"] == "experience"
        assert record["action"] == "attempted_advance"
        assert record["blocked"] is True
        assert record["reason"] == "Win rate 0.58 < required 0.60"
        assert record["operator_id"] == "operator_123"

        # Verify timestamp is ISO format with timezone
        timestamp = datetime.fromisoformat(record["timestamp"])
        assert timestamp.tzinfo is not None

    def test_log_override_attempt_without_operator(self, logger):
        """Test log_override_attempt handles missing operator_id."""
        logger.log_override_attempt(
            phase=Phase.PROOF_OF_CONCEPT,
            action="trade_limit_override",
            blocked=False,
            reason="Emergency market conditions"
        )

        # Read and verify
        with open(logger.override_log, "r") as f:
            record = json.loads(f.readline())

        assert record["operator_id"] is None

    def test_query_transitions_empty_log(self, logger):
        """Test query_transitions returns empty list when no log exists."""
        result = logger.query_transitions(
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31)
        )

        assert result == []

    def test_query_transitions_filters_by_date_range(self, logger):
        """Test query_transitions filters by date range."""
        # Create transitions on different dates
        transitions = [
            PhaseTransition(
                transition_id=str(uuid4()),
                timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
                from_phase=Phase.EXPERIENCE,
                to_phase=Phase.PROOF_OF_CONCEPT,
                trigger="auto",
                validation_passed=True,
                metrics_snapshot={"session_count": 20}
            ),
            PhaseTransition(
                transition_id=str(uuid4()),
                timestamp=datetime(2025, 10, 25, 14, 0, 0, tzinfo=timezone.utc),
                from_phase=Phase.PROOF_OF_CONCEPT,
                to_phase=Phase.REAL_MONEY_TRIAL,
                trigger="auto",
                validation_passed=True,
                metrics_snapshot={"session_count": 30}
            ),
            PhaseTransition(
                transition_id=str(uuid4()),
                timestamp=datetime(2025, 11, 5, 9, 0, 0, tzinfo=timezone.utc),
                from_phase=Phase.REAL_MONEY_TRIAL,
                to_phase=Phase.SCALING,
                trigger="auto",
                validation_passed=True,
                metrics_snapshot={"session_count": 60}
            )
        ]

        # Log all transitions
        for transition in transitions:
            logger.log_transition(transition)

        # Query October only
        october_results = logger.query_transitions(
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31)
        )

        assert len(october_results) == 2
        assert october_results[0].from_phase == Phase.EXPERIENCE
        assert october_results[1].from_phase == Phase.PROOF_OF_CONCEPT

    def test_query_transitions_returns_correct_objects(self, logger, sample_transition):
        """Test query_transitions deserializes to PhaseTransition objects."""
        # Log transition
        logger.log_transition(sample_transition)

        # Query
        results = logger.query_transitions(
            start_date=date(2025, 10, 21),
            end_date=date(2025, 10, 21)
        )

        assert len(results) == 1
        transition = results[0]

        # Verify object type and fields (check type name to avoid import issues)
        assert type(transition).__name__ == "PhaseTransition"
        assert transition.transition_id == sample_transition.transition_id
        assert transition.timestamp == sample_transition.timestamp
        assert transition.from_phase == Phase.EXPERIENCE
        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert transition.validation_passed is True

        # Verify Decimal deserialization
        assert isinstance(transition.metrics_snapshot["win_rate"], Decimal)
        assert transition.metrics_snapshot["win_rate"] == Decimal("0.65")

    def test_query_transitions_edge_dates_inclusive(self, logger):
        """Test query_transitions includes edge dates (inclusive range)."""
        # Transition on start date
        transition1 = PhaseTransition(
            transition_id=str(uuid4()),
            timestamp=datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc),
            from_phase=Phase.EXPERIENCE,
            to_phase=Phase.PROOF_OF_CONCEPT,
            trigger="auto",
            validation_passed=True,
            metrics_snapshot={}
        )

        # Transition on end date
        transition2 = PhaseTransition(
            transition_id=str(uuid4()),
            timestamp=datetime(2025, 10, 31, 23, 59, 59, tzinfo=timezone.utc),
            from_phase=Phase.PROOF_OF_CONCEPT,
            to_phase=Phase.REAL_MONEY_TRIAL,
            trigger="auto",
            validation_passed=True,
            metrics_snapshot={}
        )

        logger.log_transition(transition1)
        logger.log_transition(transition2)

        # Query exact range
        results = logger.query_transitions(
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31)
        )

        assert len(results) == 2
