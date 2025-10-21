"""Integration tests for full phase workflow (T060-T061).

Tests complete phase progression with HistoryLogger integration.

Integration Coverage:
- Full progression: Experience → PoC → Trial → Scaling
- PhaseManager + HistoryLogger coordination
- JSONL audit trail verification
- Config updates during transitions

Based on: specs/022-pos-scale-progress/tasks.md (US1 T060-T061)
"""

import json
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.trading_bot.config import Config
from src.trading_bot.phase.history_logger import HistoryLogger
from src.trading_bot.phase.manager import PhaseManager
from src.trading_bot.phase.models import Phase


class TestPhaseWorkflowIntegration:
    """Integration tests for full phase progression workflow (T060-T061)."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """Create temporary log directory."""
        log_dir = tmp_path / "logs" / "phase"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @pytest.fixture
    def test_config(self, temp_config_dir):
        """Create test configuration starting in experience phase."""
        config_file = temp_config_dir / "config.json"
        config_data = {
            "trading": {
                "paper_trading": True,
                "trading_start_time": "07:00",
                "trading_end_time": "10:00"
            },
            "risk_management": {
                "max_position_pct": 5.0,
                "max_daily_loss_pct": 3.0
            },
            "phase_progression": {
                "current_phase": "experience",
                "experience": {
                    "max_trades_per_day": 999
                }
            }
        }

        # Write config file
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        return config_file

    @pytest.fixture
    def manager(self, test_config):
        """Create PhaseManager with test config."""
        config = Config.from_env_and_json(config_file=str(test_config))
        return PhaseManager(config)

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create HistoryLogger with temp directory."""
        return HistoryLogger(log_dir=temp_log_dir)

    def test_full_phase_progression_experience_to_poc(self, manager, logger):
        """Test progression from Experience to PoC with logging (T060)."""
        # Verify starting phase
        assert manager.config.current_phase == "experience"

        # Mock metrics that meet PoC criteria
        # Experience → PoC: 20 sessions, 60% win, 1.5 R:R
        manager._metrics = {
            "session_count": 25,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8")
        }

        # Validate transition
        result = manager.validate_transition(Phase.PROOF_OF_CONCEPT)
        assert result.can_advance is True
        assert result.criteria_met["session_count"] is True
        assert result.criteria_met["win_rate"] is True
        assert result.criteria_met["avg_rr"] is True

        # Advance phase
        transition = manager.advance_phase(Phase.PROOF_OF_CONCEPT)

        # Verify transition details
        assert transition.from_phase == Phase.EXPERIENCE
        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert transition.trigger == "auto"
        assert transition.validation_passed is True
        assert transition.metrics_snapshot["session_count"] == 25

        # Log transition
        logger.log_transition(transition)

        # Verify config updated
        assert manager.config.current_phase == "proof"

        # Verify JSONL logged correctly
        assert logger.transition_log.exists()

        # Read and verify JSONL content
        with open(logger.transition_log, "r") as f:
            record = json.loads(f.readline())

        assert record["from_phase"] == "experience"
        assert record["to_phase"] == "proof"
        assert record["trigger"] == "auto"
        assert record["validation_passed"] is True
        assert record["metrics_snapshot"]["session_count"] == 25
        assert record["metrics_snapshot"]["win_rate"] == "0.65"

    def test_full_phase_progression_poc_to_trial(self, manager, logger):
        """Test progression from PoC to Trial with logging (T060)."""
        # Start in PoC phase
        manager.config.current_phase = "proof"

        # Mock metrics that meet Trial criteria
        # PoC → Trial: 30 sessions, 50 trades, 65% win, 1.8 R:R
        manager._metrics = {
            "session_count": 35,
            "trade_count": 55,
            "win_rate": Decimal("0.70"),
            "avg_rr": Decimal("2.0")
        }

        # Validate and advance
        result = manager.validate_transition(Phase.REAL_MONEY_TRIAL)
        assert result.can_advance is True

        transition = manager.advance_phase(Phase.REAL_MONEY_TRIAL)
        logger.log_transition(transition)

        # Verify transition
        assert transition.from_phase == Phase.PROOF_OF_CONCEPT
        assert transition.to_phase == Phase.REAL_MONEY_TRIAL
        assert manager.config.current_phase == "trial"

        # Verify JSONL
        with open(logger.transition_log, "r") as f:
            record = json.loads(f.readline())

        assert record["from_phase"] == "proof"
        assert record["to_phase"] == "trial"

    def test_full_phase_progression_trial_to_scaling(self, manager, logger):
        """Test progression from Trial to Scaling with logging (T060)."""
        # Start in Trial phase
        manager.config.current_phase = "trial"

        # Mock metrics that meet Scaling criteria
        # Trial → Scaling: 60 sessions, 100 trades, 70% win, 2.0 R:R, <5% drawdown
        manager._metrics = {
            "session_count": 65,
            "trade_count": 110,
            "win_rate": Decimal("0.75"),
            "avg_rr": Decimal("2.2"),
            "max_drawdown": Decimal("0.035")  # 3.5% drawdown
        }

        # Validate and advance
        result = manager.validate_transition(Phase.SCALING)
        assert result.can_advance is True

        transition = manager.advance_phase(Phase.SCALING)
        logger.log_transition(transition)

        # Verify transition
        assert transition.from_phase == Phase.REAL_MONEY_TRIAL
        assert transition.to_phase == Phase.SCALING
        assert manager.config.current_phase == "scaling"

        # Verify JSONL
        with open(logger.transition_log, "r") as f:
            record = json.loads(f.readline())

        assert record["from_phase"] == "trial"
        assert record["to_phase"] == "scaling"

    def test_complete_progression_sequence_with_history(self, manager, logger):
        """Test complete progression sequence: Experience → PoC → Trial → Scaling (T060)."""
        # Start in Experience
        assert manager.config.current_phase == "experience"

        # Progression 1: Experience → PoC
        manager._metrics = {
            "session_count": 25,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8")
        }
        transition1 = manager.advance_phase(Phase.PROOF_OF_CONCEPT)
        logger.log_transition(transition1)

        # Progression 2: PoC → Trial
        manager._metrics = {
            "session_count": 35,
            "trade_count": 55,
            "win_rate": Decimal("0.70"),
            "avg_rr": Decimal("2.0")
        }
        transition2 = manager.advance_phase(Phase.REAL_MONEY_TRIAL)
        logger.log_transition(transition2)

        # Progression 3: Trial → Scaling
        manager._metrics = {
            "session_count": 65,
            "trade_count": 110,
            "win_rate": Decimal("0.75"),
            "avg_rr": Decimal("2.2"),
            "max_drawdown": Decimal("0.035")  # 3.5% drawdown
        }
        transition3 = manager.advance_phase(Phase.SCALING)
        logger.log_transition(transition3)

        # Verify final phase
        assert manager.config.current_phase == "scaling"

        # Verify complete history in JSONL
        with open(logger.transition_log, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify progression sequence
        record1 = json.loads(lines[0])
        record2 = json.loads(lines[1])
        record3 = json.loads(lines[2])

        assert record1["from_phase"] == "experience"
        assert record1["to_phase"] == "proof"

        assert record2["from_phase"] == "proof"
        assert record2["to_phase"] == "trial"

        assert record3["from_phase"] == "trial"
        assert record3["to_phase"] == "scaling"

    def test_query_transitions_after_progression(self, manager, logger):
        """Test querying transitions after full progression (T061)."""
        # Perform complete progression
        manager._metrics = {
            "session_count": 25,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8")
        }
        transition1 = manager.advance_phase(Phase.PROOF_OF_CONCEPT)
        logger.log_transition(transition1)

        manager._metrics = {
            "session_count": 35,
            "trade_count": 55,
            "win_rate": Decimal("0.70"),
            "avg_rr": Decimal("2.0")
        }
        transition2 = manager.advance_phase(Phase.REAL_MONEY_TRIAL)
        logger.log_transition(transition2)

        # Query all transitions
        today = date.today()
        results = logger.query_transitions(
            start_date=today,
            end_date=today
        )

        # Verify results
        assert len(results) == 2
        assert results[0].from_phase == Phase.EXPERIENCE
        assert results[0].to_phase == Phase.PROOF_OF_CONCEPT
        assert results[1].from_phase == Phase.PROOF_OF_CONCEPT
        assert results[1].to_phase == Phase.REAL_MONEY_TRIAL

        # Verify Decimal deserialization
        assert isinstance(results[0].metrics_snapshot["win_rate"], Decimal)
        assert results[0].metrics_snapshot["win_rate"] == Decimal("0.65")

    def test_override_attempt_logged_with_transition(self, manager, logger):
        """Test override attempts are logged separately (T061)."""
        # Mock insufficient metrics
        manager._metrics = {
            "session_count": 15,
            "win_rate": Decimal("0.55"),  # Below 0.60 threshold
            "avg_rr": Decimal("1.8")
        }

        # Validate transition (should fail)
        result = manager.validate_transition(Phase.PROOF_OF_CONCEPT)
        assert result.can_advance is False

        # Log override attempt
        logger.log_override_attempt(
            phase=Phase.EXPERIENCE,
            action="attempted_advance_to_poc",
            blocked=True,
            reason="Win rate 0.55 < required 0.60",
            operator_id="test_operator"
        )

        # Verify override log exists
        assert logger.override_log.exists()

        # Read and verify override record
        with open(logger.override_log, "r") as f:
            record = json.loads(f.readline())

        assert record["phase"] == "experience"
        assert record["action"] == "attempted_advance_to_poc"
        assert record["blocked"] is True
        assert record["reason"] == "Win rate 0.55 < required 0.60"
        assert record["operator_id"] == "test_operator"

        # Verify timestamp format
        timestamp = datetime.fromisoformat(record["timestamp"])
        assert timestamp.tzinfo is not None

    def test_jsonl_file_format_verification(self, manager, logger):
        """Test JSONL files are correctly formatted and parseable (T061)."""
        # Create transition
        manager._metrics = {
            "session_count": 25,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8"),
            "total_pnl": Decimal("1250.50")
        }
        transition = manager.advance_phase(Phase.PROOF_OF_CONCEPT)
        logger.log_transition(transition)

        # Verify file is valid JSONL
        with open(logger.transition_log, "r") as f:
            line = f.readline()

            # Should not have trailing newline after strip
            assert line.endswith("\n")

            # Should parse as valid JSON
            record = json.loads(line)

            # Should have all required fields
            required_fields = [
                "transition_id",
                "timestamp",
                "from_phase",
                "to_phase",
                "trigger",
                "validation_passed",
                "metrics_snapshot"
            ]
            for field in required_fields:
                assert field in record

            # Decimal values should be strings
            assert isinstance(record["metrics_snapshot"]["win_rate"], str)
            assert isinstance(record["metrics_snapshot"]["avg_rr"], str)
            assert isinstance(record["metrics_snapshot"]["total_pnl"], str)

            # Timestamp should be ISO format with timezone
            timestamp = datetime.fromisoformat(record["timestamp"])
            assert timestamp.tzinfo is not None

    def test_concurrent_logging_integration(self, manager, logger):
        """Test that concurrent phase transitions are logged correctly (T061)."""
        # Simulate rapid progression (stress test)
        progressions = [
            (Phase.PROOF_OF_CONCEPT, {
                "session_count": 25,
                "win_rate": Decimal("0.65"),
                "avg_rr": Decimal("1.8")
            }),
            (Phase.REAL_MONEY_TRIAL, {
                "session_count": 35,
                "trade_count": 55,
                "win_rate": Decimal("0.70"),
                "avg_rr": Decimal("2.0")
            }),
            (Phase.SCALING, {
                "session_count": 65,
                "trade_count": 110,
                "win_rate": Decimal("0.75"),
                "avg_rr": Decimal("2.2"),
                "max_drawdown": Decimal("0.035")  # 3.5% drawdown
            })
        ]

        # Execute progressions
        for target_phase, metrics in progressions:
            manager._metrics = metrics
            transition = manager.advance_phase(target_phase)
            logger.log_transition(transition)

        # Verify all logged
        with open(logger.transition_log, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify all lines are valid JSON
        for line in lines:
            record = json.loads(line)
            assert "transition_id" in record
            assert "timestamp" in record

    def test_automatic_downgrade_trial_to_poc(self, manager, logger):
        """Test automatic downgrade from Trial to PoC after 3 losses (T130-T131)."""
        # Start in Trial phase
        manager.config.current_phase = "trial"

        # Mock metrics: 3 consecutive losses (trigger downgrade)
        from trading_bot.phase.models import SessionMetrics
        metrics = SessionMetrics(
            session_date=date(2025, 1, 15),
            phase="trial",
            trades_executed=3,
            total_wins=0,
            total_losses=3,
            win_rate=Decimal("0.00"),
            average_rr=Decimal("0.00"),
            total_pnl=Decimal("-150.00")
        )

        # Check if downgrade is triggered
        target_phase = manager.check_downgrade_triggers(metrics)
        assert target_phase == Phase.PROOF_OF_CONCEPT  # Trial → PoC

        # Apply downgrade
        transition = manager.apply_downgrade(
            to_phase=target_phase,
            reason="3 consecutive losses"
        )

        # Verify transition details
        assert transition.from_phase == Phase.REAL_MONEY_TRIAL
        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert transition.trigger == "auto"
        assert transition.validation_passed is False  # Downgrade
        assert "3 consecutive losses" in transition.failure_reasons

        # Log transition
        logger.log_transition(transition)

        # Verify config updated
        assert manager.config.current_phase == "proof"

        # Verify JSONL logged correctly
        assert logger.transition_log.exists()

        # Read and verify JSONL content
        with open(logger.transition_log, "r") as f:
            record = json.loads(f.readline())

        assert record["from_phase"] == "trial"
        assert record["to_phase"] == "proof"
        assert record["trigger"] == "auto"
        assert record["validation_passed"] is False
        assert "3 consecutive losses" in record["failure_reasons"]

    def test_automatic_downgrade_scaling_to_trial_win_rate(self, manager, logger):
        """Test automatic downgrade from Scaling to Trial due to low win rate (T130-T131)."""
        # Start in Scaling phase
        manager.config.current_phase = "scaling"

        # Mock metrics: Win rate below 55% threshold
        from trading_bot.phase.models import SessionMetrics
        metrics = SessionMetrics(
            session_date=date(2025, 1, 15),
            phase="scaling",
            trades_executed=20,
            total_wins=10,
            total_losses=10,
            win_rate=Decimal("0.52"),  # Below 0.55 threshold
            average_rr=Decimal("1.5"),
            total_pnl=Decimal("50.00")
        )

        # Check if downgrade is triggered
        target_phase = manager.check_downgrade_triggers(metrics)
        assert target_phase == Phase.REAL_MONEY_TRIAL  # Scaling → Trial

        # Apply downgrade
        transition = manager.apply_downgrade(
            to_phase=target_phase,
            reason="Win rate 52% below 55% threshold"
        )

        # Verify transition
        assert transition.from_phase == Phase.SCALING
        assert transition.to_phase == Phase.REAL_MONEY_TRIAL
        assert manager.config.current_phase == "trial"

        # Log and verify
        logger.log_transition(transition)

        with open(logger.transition_log, "r") as f:
            record = json.loads(f.readline())

        assert record["from_phase"] == "scaling"
        assert record["to_phase"] == "trial"
        assert record["validation_passed"] is False

    def test_automatic_downgrade_daily_loss_threshold(self, manager, logger):
        """Test automatic downgrade due to daily loss >5% (T130-T131)."""
        # Start in Trial phase
        manager.config.current_phase = "trial"

        # Mock metrics: Daily loss exceeds threshold
        from trading_bot.phase.models import SessionMetrics
        metrics = SessionMetrics(
            session_date=date(2025, 1, 15),
            phase="trial",
            trades_executed=5,
            total_wins=1,
            total_losses=4,
            win_rate=Decimal("0.20"),
            average_rr=Decimal("0.5"),
            total_pnl=Decimal("-600.00")  # Critical loss (>5% of $10k)
        )

        # Check if downgrade is triggered
        target_phase = manager.check_downgrade_triggers(metrics)
        assert target_phase == Phase.PROOF_OF_CONCEPT  # Trial → PoC

        # Apply downgrade
        transition = manager.apply_downgrade(
            to_phase=target_phase,
            reason="Daily loss $600 exceeds 5% threshold"
        )

        # Verify transition
        assert transition.from_phase == Phase.REAL_MONEY_TRIAL
        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert manager.config.current_phase == "proof"

        # Log and verify
        logger.log_transition(transition)

        with open(logger.transition_log, "r") as f:
            record = json.loads(f.readline())

        assert record["from_phase"] == "trial"
        assert record["to_phase"] == "proof"
        assert "Daily loss $600 exceeds 5% threshold" in record["failure_reasons"]

    def test_no_downgrade_when_metrics_acceptable(self, manager):
        """Test no downgrade when metrics are within thresholds (T130-T131)."""
        # Start in Trial phase
        manager.config.current_phase = "trial"

        # Mock metrics: Good performance (no downgrade needed)
        from trading_bot.phase.models import SessionMetrics
        metrics = SessionMetrics(
            session_date=date(2025, 1, 15),
            phase="trial",
            trades_executed=10,
            total_wins=6,
            total_losses=4,
            win_rate=Decimal("0.60"),  # Above 0.55 threshold
            average_rr=Decimal("1.5"),
            total_pnl=Decimal("200.00")  # Positive P&L
        )

        # Check if downgrade is triggered
        target_phase = manager.check_downgrade_triggers(metrics)

        # Should not trigger downgrade
        assert target_phase is None

        # Config should remain unchanged
        assert manager.config.current_phase == "trial"
