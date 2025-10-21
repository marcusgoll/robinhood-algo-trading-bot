"""Tests for atomic phase transitions (Critical Issue #3, NFR-002).

Validates that phase transitions are atomic:
- Config update and history logging happen together
- Rollback on failure prevents partial updates
- No audit gaps during crashes
"""
import pytest
from pathlib import Path
from datetime import date
from decimal import Decimal

from trading_bot.phase.models import Phase
from trading_bot.phase.manager import PhaseManager
from trading_bot.config import Config


class TestAtomicTransitions:
    """Test atomic transaction behavior for phase transitions."""

    def test_config_save_creates_file(self, tmp_path):
        """Config.save() should persist to disk."""
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )

        # Set config path to temp directory
        config_path = tmp_path / "config.json"
        config.config_file_path = config_path

        # Save should create file
        config.save()

        assert config_path.exists()

    def test_config_save_atomic_write(self, tmp_path):
        """Config.save() should use atomic write-then-rename."""
        import json

        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )

        config_path = tmp_path / "config.json"
        config.config_file_path = config_path

        # Save
        config.save()

        # Verify file is valid JSON (not partial write)
        with open(config_path, 'r') as f:
            data = json.load(f)

        assert data["phase_progression"]["current_phase"] == "experience"

    def test_config_save_updates_existing_file(self, tmp_path):
        """Config.save() should update existing config file."""
        import json

        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )

        config_path = tmp_path / "config.json"
        config.config_file_path = config_path

        # Initial save
        config.save()

        # Update phase
        config.current_phase = "proof"
        config.save()

        # Verify updated
        with open(config_path, 'r') as f:
            data = json.load(f)

        assert data["phase_progression"]["current_phase"] == "proof"

    def test_advance_phase_persists_to_disk(self, tmp_path, monkeypatch):
        """advance_phase() should persist config to disk."""
        import json

        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )

        config_path = tmp_path / "config.json"
        config.config_file_path = config_path

        manager = PhaseManager(config)
        manager._metrics = {
            "session_count": 25,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8")
        }

        # Set override password for force advancement
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "test123")

        # Advance phase (force to bypass validation complexity)
        from trading_bot.phase.history_logger import HistoryLogger
        manager.history_logger = HistoryLogger(log_dir=tmp_path)

        manager.advance_phase(
            Phase.PROOF_OF_CONCEPT,
            force=True,
            override_password="test123"
        )

        # Verify config persisted to disk
        assert config_path.exists()

        with open(config_path, 'r') as f:
            data = json.load(f)

        assert data["phase_progression"]["current_phase"] == "proof"

    def test_advance_phase_rollback_on_config_save_failure(
        self, tmp_path, monkeypatch, mocker
    ):
        """If config.save() fails, phase should rollback to original."""
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )

        config_path = tmp_path / "config.json"
        config.config_file_path = config_path

        manager = PhaseManager(config)

        # Set override password
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "test123")

        # Mock config.save() to raise exception
        mocker.patch.object(config, 'save', side_effect=IOError("Disk full"))

        # Set up history logger
        from trading_bot.phase.history_logger import HistoryLogger
        manager.history_logger = HistoryLogger(log_dir=tmp_path)

        # Attempt phase advance should fail
        with pytest.raises(IOError, match="Disk full"):
            manager.advance_phase(
                Phase.PROOF_OF_CONCEPT,
                force=True,
                override_password="test123"
            )

        # Config should be rolled back to original phase
        assert config.current_phase == "experience"

    def test_advance_phase_rollback_on_history_log_failure(
        self, tmp_path, monkeypatch, mocker
    ):
        """If history logging fails, phase should rollback."""
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )

        config_path = tmp_path / "config.json"
        config.config_file_path = config_path

        manager = PhaseManager(config)

        # Set override password
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "test123")

        # Set up history logger
        from trading_bot.phase.history_logger import HistoryLogger
        logger = HistoryLogger(log_dir=tmp_path)
        manager.history_logger = logger

        # Mock history logger to fail
        mocker.patch.object(logger, 'log_transition', side_effect=IOError("Log write failed"))

        # Attempt phase advance should fail
        with pytest.raises(IOError, match="Log write failed"):
            manager.advance_phase(
                Phase.PROOF_OF_CONCEPT,
                force=True,
                override_password="test123"
            )

        # Config should be rolled back to original phase
        assert config.current_phase == "experience"

        # Config file should not have been updated
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                data = json.load(f)
            assert data["phase_progression"]["current_phase"] == "experience"

    def test_advance_phase_no_partial_updates(
        self, tmp_path, monkeypatch, mocker
    ):
        """Partial updates should not occur - all or nothing."""
        import json

        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )

        config_path = tmp_path / "config.json"
        config.config_file_path = config_path

        # Create initial config file
        config.save()

        manager = PhaseManager(config)

        # Set override password
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "test123")

        # Set up history logger
        from trading_bot.phase.history_logger import HistoryLogger
        logger = HistoryLogger(log_dir=tmp_path)
        manager.history_logger = logger

        # Mock save to succeed, but log_transition to fail
        # This tests that rollback happens AFTER save
        original_save = config.save
        save_called = []

        def tracked_save():
            save_called.append(True)
            original_save()

        mocker.patch.object(config, 'save', side_effect=tracked_save)
        mocker.patch.object(logger, 'log_transition', side_effect=IOError("Log failed"))

        # Attempt advance
        with pytest.raises(IOError):
            manager.advance_phase(
                Phase.PROOF_OF_CONCEPT,
                force=True,
                override_password="test123"
            )

        # Save was called twice: once forward, once for rollback
        assert len(save_called) == 2

        # Config should be rolled back in memory
        assert config.current_phase == "experience"

        # And file should be reverted (rolled back to original)
        with open(config_path, 'r') as f:
            data = json.load(f)
        assert data["phase_progression"]["current_phase"] == "experience"

    def test_advance_phase_both_operations_succeed(
        self, tmp_path, monkeypatch
    ):
        """When both save and log succeed, transition is complete."""
        import json

        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )

        config_path = tmp_path / "config.json"
        config.config_file_path = config_path

        manager = PhaseManager(config)

        # Set override password
        monkeypatch.setenv("PHASE_OVERRIDE_PASSWORD", "test123")

        # Set up history logger
        from trading_bot.phase.history_logger import HistoryLogger
        manager.history_logger = HistoryLogger(log_dir=tmp_path)

        # Advance phase
        transition = manager.advance_phase(
            Phase.PROOF_OF_CONCEPT,
            force=True,
            override_password="test123"
        )

        # Verify in-memory update
        assert config.current_phase == "proof"

        # Verify file update
        assert config_path.exists()
        with open(config_path, 'r') as f:
            data = json.load(f)
        assert data["phase_progression"]["current_phase"] == "proof"

        # Verify history logged
        history_log = tmp_path / "phase-history.jsonl"
        assert history_log.exists()

        with open(history_log, 'r') as f:
            record = json.loads(f.readline())

        assert record["to_phase"] == "proof"
        assert record["transition_id"] == transition.transition_id
