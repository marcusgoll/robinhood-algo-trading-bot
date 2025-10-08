"""
Unit tests for ModeSwitcher

Tests Constitution v1.0.0 requirements:
- §Safety_First: Paper trading by default, live mode requires validation
- §Risk_Management: Phase-based progression to live trading
"""

import pytest
from src.trading_bot.config import Config
from src.trading_bot.mode_switcher import ModeSwitcher, ModeSwitchError, ModeStatus


class TestModeSwitcher:
    """Test ModeSwitcher functionality."""

    def test_initialization_paper_mode(self) -> None:
        """Should initialize in paper mode when config.paper_trading=True."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True
        )
        switcher = ModeSwitcher(config)

        assert switcher.current_mode == "paper"
        assert switcher.is_paper_trading is True
        assert switcher.is_live_trading is False

    def test_initialization_live_mode(self) -> None:
        """Should initialize in live mode when config.paper_trading=False."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=False,
            current_phase="proof"  # Not experience phase
        )
        switcher = ModeSwitcher(config)

        assert switcher.current_mode == "live"
        assert switcher.is_paper_trading is False
        assert switcher.is_live_trading is True

    def test_get_status_paper_mode(self) -> None:
        """get_status should return correct status for paper mode."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True,
            current_phase="proof"
        )
        switcher = ModeSwitcher(config)
        status = switcher.get_status()

        assert isinstance(status, ModeStatus)
        assert status.current_mode == "paper"
        assert status.phase == "proof"
        assert status.can_switch_to_live is True
        assert status.switch_blocked_reason is None

    def test_get_status_experience_phase_blocks_live(self) -> None:
        """get_status should block live trading in experience phase."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True,
            current_phase="experience"
        )
        switcher = ModeSwitcher(config)
        status = switcher.get_status()

        assert status.can_switch_to_live is False
        assert "experience" in status.switch_blocked_reason.lower()

    def test_switch_to_paper_from_live(self) -> None:
        """Should allow switching from live to paper (safer direction)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=False,
            current_phase="proof"
        )
        switcher = ModeSwitcher(config)

        assert switcher.is_live_trading is True

        switcher.switch_to_paper()

        assert switcher.is_paper_trading is True
        assert switcher.is_live_trading is False

    def test_switch_to_paper_when_already_paper(self) -> None:
        """Should handle switching to paper when already in paper mode."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True
        )
        switcher = ModeSwitcher(config)

        switcher.switch_to_paper()  # Should not raise

        assert switcher.is_paper_trading is True

    def test_switch_to_live_allowed_in_proof_phase(self) -> None:
        """Should allow switching to live in proof phase."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True,
            current_phase="proof"
        )
        switcher = ModeSwitcher(config)

        assert switcher.is_paper_trading is True

        switcher.switch_to_live()

        assert switcher.is_live_trading is True
        assert switcher.is_paper_trading is False

    def test_switch_to_live_allowed_in_trial_phase(self) -> None:
        """Should allow switching to live in trial phase."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True,
            current_phase="trial"
        )
        switcher = ModeSwitcher(config)

        switcher.switch_to_live()

        assert switcher.is_live_trading is True

    def test_switch_to_live_allowed_in_scaling_phase(self) -> None:
        """Should allow switching to live in scaling phase."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True,
            current_phase="scaling"
        )
        switcher = ModeSwitcher(config)

        switcher.switch_to_live()

        assert switcher.is_live_trading is True

    def test_switch_to_live_blocked_in_experience_phase(self) -> None:
        """Should block switching to live in experience phase (§Safety_First)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True,
            current_phase="experience"
        )
        switcher = ModeSwitcher(config)

        with pytest.raises(ModeSwitchError) as exc_info:
            switcher.switch_to_live()

        assert "experience" in str(exc_info.value).lower()
        assert switcher.is_paper_trading is True  # Should remain in paper mode

    def test_switch_to_live_force_override(self) -> None:
        """Should allow force override of phase checks (emergency use)."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True,
            current_phase="experience"
        )
        switcher = ModeSwitcher(config)

        # Force switch despite being in experience phase
        switcher.switch_to_live(force=True)

        assert switcher.is_live_trading is True

    def test_switch_to_live_when_already_live(self) -> None:
        """Should handle switching to live when already in live mode."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=False,
            current_phase="proof"
        )
        switcher = ModeSwitcher(config)

        switcher.switch_to_live()  # Should not raise

        assert switcher.is_live_trading is True

    def test_display_mode_banner_paper(self) -> None:
        """Should display paper trading banner."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True
        )
        switcher = ModeSwitcher(config)
        banner = switcher.display_mode_banner()

        assert "PAPER TRADING MODE" in banner
        assert "Simulation" in banner
        assert "No Real Money" in banner

    def test_display_mode_banner_live(self) -> None:
        """Should display live trading warning banner."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=False,
            current_phase="proof"
        )
        switcher = ModeSwitcher(config)
        banner = switcher.display_mode_banner()

        assert "LIVE TRADING MODE" in banner
        assert "REAL MONEY" in banner
        assert "⚠️" in banner

    def test_get_mode_indicator_paper(self) -> None:
        """Should return short indicator for paper mode."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True
        )
        switcher = ModeSwitcher(config)
        indicator = switcher.get_mode_indicator()

        assert indicator == "[PAPER]"

    def test_get_mode_indicator_live(self) -> None:
        """Should return short indicator for live mode."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=False,
            current_phase="proof"
        )
        switcher = ModeSwitcher(config)
        indicator = switcher.get_mode_indicator()

        assert indicator == "[⚠️  LIVE ⚠️]"

    def test_mode_transitions(self) -> None:
        """Test multiple mode transitions work correctly."""
        config = Config(
            robinhood_username="test_user",
            robinhood_password="test_pass",
            paper_trading=True,
            current_phase="proof"
        )
        switcher = ModeSwitcher(config)

        # Start in paper
        assert switcher.is_paper_trading is True

        # Switch to live
        switcher.switch_to_live()
        assert switcher.is_live_trading is True

        # Switch back to paper
        switcher.switch_to_paper()
        assert switcher.is_paper_trading is True

        # Switch to live again
        switcher.switch_to_live()
        assert switcher.is_live_trading is True
