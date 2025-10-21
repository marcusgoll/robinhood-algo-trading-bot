"""CLI tests for phase history export and validation (TDD RED → GREEN).

Tests the command-line interface for:
- Export phase history to CSV/JSON
- Validate phase transition readiness
- Display current phase status

Test Coverage:
- T140: export command generates CSV with correct columns
- T141: export command generates JSON with complete data
- validate-transition displays criteria status
- validate-transition exit codes (0=ready, 1=not ready)
- status displays current phase info

Based on: specs/022-pos-scale-progress/spec.md FR-008
"""

import csv
import json
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.trading_bot.phase.cli import (
    export_command,
    validate_command,
    status_command,
    _export_csv,
    _export_json
)
from src.trading_bot.phase.models import Phase, PhaseTransition
from src.trading_bot.phase.validators import ValidationResult


class TestExportCommand:
    """Test export command functionality (T140-T141)."""

    @pytest.fixture
    def sample_transitions(self):
        """Create sample transitions for testing."""
        return [
            PhaseTransition(
                transition_id=str(uuid4()),
                timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
                from_phase=Phase.EXPERIENCE,
                to_phase=Phase.PROOF_OF_CONCEPT,
                trigger="auto",
                validation_passed=True,
                metrics_snapshot={
                    "session_count": 25,
                    "win_rate": Decimal("0.65"),
                    "avg_rr": Decimal("1.8")
                }
            ),
            PhaseTransition(
                transition_id=str(uuid4()),
                timestamp=datetime(2025, 10, 20, 14, 30, 0, tzinfo=timezone.utc),
                from_phase=Phase.PROOF_OF_CONCEPT,
                to_phase=Phase.REAL_MONEY_TRIAL,
                trigger="manual",
                validation_passed=True,
                metrics_snapshot={
                    "session_count": 50,
                    "win_rate": Decimal("0.70"),
                    "avg_rr": Decimal("2.0"),
                    "trade_count": 150
                }
            )
        ]

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create temporary output directory."""
        return tmp_path

    def test_export_csv_creates_file_with_correct_columns(
        self,
        sample_transitions,
        temp_output_dir,
        monkeypatch
    ):
        """Test CSV export creates file with spec-required columns (T140)."""
        # Change to temp directory
        monkeypatch.chdir(temp_output_dir)

        # Mock HistoryLogger.query_transitions
        with patch('src.trading_bot.phase.cli.HistoryLogger') as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger.query_transitions.return_value = sample_transitions
            mock_logger_class.return_value = mock_logger

            # Execute export
            export_command(
                start_date="2025-10-01",
                end_date="2025-10-31",
                format="csv"
            )

        # Verify file created
        expected_file = temp_output_dir / "phase-history_2025-10-01_2025-10-31.csv"
        assert expected_file.exists()

        # Verify CSV structure
        with open(expected_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)

            # Check required columns from spec FR-008
            assert header == [
                "Date",
                "From Phase",
                "To Phase",
                "Trigger",
                "Validation Passed",
                "Session Count",
                "Win Rate",
                "Avg R:R"
            ]

            # Check first data row
            row1 = next(reader)
            assert row1[0] == "2025-10-15"  # Date
            assert row1[1] == "experience"  # From Phase
            assert row1[2] == "proof"  # To Phase
            assert row1[3] == "auto"  # Trigger
            assert row1[4] == "True"  # Validation Passed
            assert row1[5] == "25"  # Session Count
            assert row1[6] == "0.65"  # Win Rate
            assert row1[7] == "1.8"  # Avg R:R

    def test_export_json_creates_file_with_complete_data(
        self,
        sample_transitions,
        temp_output_dir,
        monkeypatch
    ):
        """Test JSON export creates file with complete transition data (T141)."""
        # Change to temp directory
        monkeypatch.chdir(temp_output_dir)

        # Mock HistoryLogger.query_transitions
        with patch('src.trading_bot.phase.cli.HistoryLogger') as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger.query_transitions.return_value = sample_transitions
            mock_logger_class.return_value = mock_logger

            # Execute export
            export_command(
                start_date="2025-10-01",
                end_date="2025-10-31",
                format="json"
            )

        # Verify file created
        expected_file = temp_output_dir / "phase-history_2025-10-01_2025-10-31.json"
        assert expected_file.exists()

        # Verify JSON structure
        with open(expected_file, 'r') as f:
            data = json.load(f)

        assert len(data) == 2

        # Check first transition
        transition1 = data[0]
        assert transition1["date"] == "2025-10-15"
        assert transition1["from_phase"] == "experience"
        assert transition1["to_phase"] == "proof"
        assert transition1["trigger"] == "auto"
        assert transition1["validation_passed"] is True
        assert transition1["metrics_snapshot"]["session_count"] == 25
        assert transition1["metrics_snapshot"]["win_rate"] == "0.65"
        assert transition1["metrics_snapshot"]["avg_rr"] == "1.8"

    def test_export_custom_output_filename(
        self,
        sample_transitions,
        temp_output_dir,
        monkeypatch
    ):
        """Test export with custom output filename."""
        monkeypatch.chdir(temp_output_dir)

        with patch('src.trading_bot.phase.cli.HistoryLogger') as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger.query_transitions.return_value = sample_transitions
            mock_logger_class.return_value = mock_logger

            export_command(
                start_date="2025-10-01",
                end_date="2025-10-31",
                format="csv",
                output="custom_export.csv"
            )

        custom_file = temp_output_dir / "custom_export.csv"
        assert custom_file.exists()

    def test_export_empty_results(self, temp_output_dir, monkeypatch):
        """Test export with no transitions in date range."""
        monkeypatch.chdir(temp_output_dir)

        with patch('src.trading_bot.phase.cli.HistoryLogger') as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger.query_transitions.return_value = []
            mock_logger_class.return_value = mock_logger

            export_command(
                start_date="2025-01-01",
                end_date="2025-01-31",
                format="csv"
            )

        output_file = temp_output_dir / "phase-history_2025-01-01_2025-01-31.csv"
        assert output_file.exists()

        # Verify only header exists
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 1  # Only header

    def test_export_invalid_format_raises_error(self):
        """Test export with invalid format raises ValueError."""
        with patch('src.trading_bot.phase.cli.HistoryLogger'):
            with pytest.raises(ValueError, match="Unsupported format: xml"):
                export_command(
                    start_date="2025-10-01",
                    end_date="2025-10-31",
                    format="xml"
                )


class TestValidateCommand:
    """Test validate-transition command (T142)."""

    def test_validate_ready_returns_zero(self, capsys):
        """Test validate-transition returns 0 when ready to advance."""
        # Mock Config and PhaseManager
        with patch('src.trading_bot.phase.cli.Config') as mock_config_class, \
             patch('src.trading_bot.phase.cli.PhaseManager') as mock_manager_class:

            # Setup mocks
            mock_config = MagicMock()
            mock_config.current_phase = "experience"
            mock_config_class.from_env_and_json.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.validate_transition.return_value = ValidationResult(
                can_advance=True,
                criteria_met={
                    "session_count": True,
                    "win_rate": True,
                    "avg_rr": True
                },
                missing_requirements=[],
                metrics_summary={
                    "session_count": 25,
                    "win_rate": "0.65",
                    "avg_rr": "1.8"
                }
            )
            mock_manager_class.return_value = mock_manager

            # Execute validate
            exit_code = validate_command(to_phase="proof")

        # Verify exit code
        assert exit_code == 0

        # Verify output
        captured = capsys.readouterr()
        assert "Phase Transition Validation: experience → proof" in captured.out
        assert "✅ session_count: MET" in captured.out
        assert "✅ win_rate: MET" in captured.out
        assert "✅ avg_rr: MET" in captured.out
        assert "✅ READY to advance" in captured.out

    def test_validate_not_ready_returns_one(self, capsys):
        """Test validate-transition returns 1 when not ready to advance."""
        with patch('src.trading_bot.phase.cli.Config') as mock_config_class, \
             patch('src.trading_bot.phase.cli.PhaseManager') as mock_manager_class:

            mock_config = MagicMock()
            mock_config.current_phase = "experience"
            mock_config_class.from_env_and_json.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.validate_transition.return_value = ValidationResult(
                can_advance=False,
                criteria_met={
                    "session_count": True,
                    "win_rate": False,
                    "avg_rr": False
                },
                missing_requirements=["win_rate", "avg_rr"],
                metrics_summary={
                    "session_count": 25,
                    "win_rate": "0.55",
                    "avg_rr": "1.2"
                }
            )
            mock_manager_class.return_value = mock_manager

            exit_code = validate_command(to_phase="proof")

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "✅ session_count: MET" in captured.out
        assert "❌ win_rate: NOT MET" in captured.out
        assert "❌ avg_rr: NOT MET" in captured.out
        assert "❌ NOT READY: win_rate, avg_rr" in captured.out

    def test_validate_displays_all_criteria(self, capsys):
        """Test validate displays all validation criteria."""
        with patch('src.trading_bot.phase.cli.Config') as mock_config_class, \
             patch('src.trading_bot.phase.cli.PhaseManager') as mock_manager_class:

            mock_config = MagicMock()
            mock_config.current_phase = "proof"
            mock_config_class.from_env_and_json.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.validate_transition.return_value = ValidationResult(
                can_advance=False,
                criteria_met={
                    "session_count": True,
                    "trade_count": True,
                    "win_rate": False,
                    "avg_rr": True
                },
                missing_requirements=["win_rate"],
                metrics_summary={
                    "session_count": 50,
                    "trade_count": 150,
                    "win_rate": "0.62",
                    "avg_rr": "1.9"
                }
            )
            mock_manager_class.return_value = mock_manager

            validate_command(to_phase="trial")

        captured = capsys.readouterr()
        assert "session_count" in captured.out
        assert "trade_count" in captured.out
        assert "win_rate" in captured.out
        assert "avg_rr" in captured.out


class TestStatusCommand:
    """Test status command (T143)."""

    def test_status_displays_current_phase(self, capsys):
        """Test status displays current phase information."""
        with patch('src.trading_bot.phase.cli.Config') as mock_config_class:
            mock_config = MagicMock()
            mock_config.current_phase = "proof"
            mock_config.max_trades_per_day = 3
            mock_config_class.from_env_and_json.return_value = mock_config

            status_command()

        captured = capsys.readouterr()
        assert "Phase Progression Status" in captured.out
        assert "Current Phase: proof" in captured.out
        assert "Max Trades/Day: 3" in captured.out

    def test_status_displays_experience_phase(self, capsys):
        """Test status displays experience phase correctly."""
        with patch('src.trading_bot.phase.cli.Config') as mock_config_class:
            mock_config = MagicMock()
            mock_config.current_phase = "experience"
            mock_config.max_trades_per_day = 999
            mock_config_class.from_env_and_json.return_value = mock_config

            status_command()

        captured = capsys.readouterr()
        assert "Current Phase: experience" in captured.out
        assert "Max Trades/Day: 999" in captured.out


class TestExportHelpers:
    """Test _export_csv and _export_json helper functions."""

    def test_export_csv_handles_missing_metrics(self, tmp_path):
        """Test CSV export handles transitions with missing metrics."""
        transitions = [
            PhaseTransition(
                transition_id=str(uuid4()),
                timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
                from_phase=Phase.EXPERIENCE,
                to_phase=Phase.PROOF_OF_CONCEPT,
                trigger="auto",
                validation_passed=True,
                metrics_snapshot={}  # Empty metrics
            )
        ]

        output_file = tmp_path / "test_export.csv"
        _export_csv(transitions, str(output_file))

        # Verify file created and handles empty metrics
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            row = next(reader)
            # Empty metrics should result in empty strings
            assert row[5] == ""  # Session Count
            assert row[6] == ""  # Win Rate
            assert row[7] == ""  # Avg R:R

    def test_export_json_preserves_all_metrics(self, tmp_path):
        """Test JSON export preserves all metrics in snapshot."""
        transitions = [
            PhaseTransition(
                transition_id=str(uuid4()),
                timestamp=datetime(2025, 10, 15, 10, 0, 0, tzinfo=timezone.utc),
                from_phase=Phase.PROOF_OF_CONCEPT,
                to_phase=Phase.REAL_MONEY_TRIAL,
                trigger="auto",
                validation_passed=True,
                metrics_snapshot={
                    "session_count": 50,
                    "trade_count": 150,
                    "win_rate": Decimal("0.70"),
                    "avg_rr": Decimal("2.0"),
                    "custom_metric": "value"
                }
            )
        ]

        output_file = tmp_path / "test_export.json"
        _export_json(transitions, str(output_file))

        # Verify all metrics preserved
        with open(output_file, 'r') as f:
            data = json.load(f)

        assert len(data) == 1
        snapshot = data[0]["metrics_snapshot"]
        assert snapshot["session_count"] == 50
        assert snapshot["trade_count"] == 150
        assert snapshot["win_rate"] == "0.70"
        assert snapshot["avg_rr"] == "2.0"
        assert snapshot["custom_metric"] == "value"
