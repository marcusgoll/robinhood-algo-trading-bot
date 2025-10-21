"""
Unit tests for Config loading phase_progression.

Tests T020: Verify Config.from_env_and_json() loads phase_progression correctly.
"""

import json
from pathlib import Path

import pytest

from src.trading_bot.config import Config


@pytest.fixture(autouse=True)
def _credentials_env(monkeypatch):
    """Set up required credentials in environment for all tests."""
    monkeypatch.setenv("ROBINHOOD_USERNAME", "test@example.com")
    monkeypatch.setenv("ROBINHOOD_PASSWORD", "super-secret")


def _write_config(tmp_path: Path, payload: dict) -> Path:
    """Helper to write a temporary config.json file."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload))
    return config_path


class TestPhaseProgressionLoading:
    """Test suite for phase_progression configuration loading."""

    def test_loads_current_phase_from_config(self, tmp_path: Path):
        """Test that Config.from_env_and_json() loads current_phase from config.json."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {
                    "current_phase": "proof",
                }
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        assert cfg.current_phase == "proof"

    def test_defaults_to_experience_when_current_phase_missing(self, tmp_path: Path):
        """Test default current_phase='experience' when phase_progression missing."""
        config_path = _write_config(
            tmp_path,
            {
                "trading": {},
                "risk_management": {},
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        assert cfg.current_phase == "experience"

    def test_defaults_to_experience_when_phase_progression_empty(self, tmp_path: Path):
        """Test default current_phase='experience' when phase_progression is empty."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {}
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        assert cfg.current_phase == "experience"

    def test_loads_max_trades_per_day_from_phase_config(self, tmp_path: Path):
        """Test that max_trades_per_day is loaded from the current phase config."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {
                    "current_phase": "proof",
                    "proof": {
                        "max_trades_per_day": 1,
                    }
                }
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        assert cfg.current_phase == "proof"
        assert cfg.max_trades_per_day == 1

    def test_defaults_max_trades_per_day_when_phase_config_missing(self, tmp_path: Path):
        """Test default max_trades_per_day=999 when phase config is missing."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {
                    "current_phase": "experience",
                }
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        assert cfg.current_phase == "experience"
        assert cfg.max_trades_per_day == 999

    def test_loads_experience_phase_config(self, tmp_path: Path):
        """Test loading experience phase configuration with null max_trades_per_day."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {
                    "current_phase": "experience",
                    "experience": {
                        "max_trades_per_day": None,
                        "position_size": 0,
                        "advancement_criteria": {
                            "min_sessions": 20,
                            "min_win_rate": 0.60,
                            "min_avg_rr": 1.5
                        }
                    }
                }
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        assert cfg.current_phase == "experience"
        # max_trades_per_day of null means unlimited (999 is our "unlimited" sentinel)
        assert cfg.max_trades_per_day == 999

    def test_loads_trial_phase_config(self, tmp_path: Path):
        """Test loading trial phase configuration."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {
                    "current_phase": "trial",
                    "trial": {
                        "max_trades_per_day": None,
                        "position_size": 200,
                    }
                }
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        assert cfg.current_phase == "trial"
        assert cfg.max_trades_per_day == 999

    def test_loads_scaling_phase_config(self, tmp_path: Path):
        """Test loading scaling phase configuration."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {
                    "current_phase": "scaling",
                    "scaling": {
                        "max_trades_per_day": None,
                        "position_size_min": 200,
                        "position_size_max": 2000,
                    }
                }
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        assert cfg.current_phase == "scaling"
        assert cfg.max_trades_per_day == 999

    def test_validates_invalid_phase_name(self, tmp_path: Path):
        """Test that validation fails for invalid phase names."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {
                    "current_phase": "invalid_phase",
                }
            },
        )

        cfg = Config.from_env_and_json(config_file=str(config_path))

        with pytest.raises(ValueError, match="Invalid current_phase"):
            cfg.validate()

    def test_backward_compatible_with_existing_scaler_state(self, tmp_path: Path):
        """Test that existing scaler_state in config.json is preserved."""
        config_path = _write_config(
            tmp_path,
            {
                "phase_progression": {
                    "current_phase": "experience",
                    "scaler_state": {
                        "current_multiplier": 10.0,
                        "milestone_count": 99,
                        "sessions_since_milestone": 0,
                        "last_scaled_at": "2025-10-19T11:36:19.750939"
                    }
                }
            },
        )

        # Should not raise any errors
        cfg = Config.from_env_and_json(config_file=str(config_path))
        cfg.validate()

        assert cfg.current_phase == "experience"
