"""
Mode Switcher

Manages switching between paper trading and live trading modes.

Enforces Constitution v1.0.0:
- §Safety_First: Paper trading by default, live mode requires validation
- §Risk_Management: Phase-based progression to live trading
"""

import logging
from dataclasses import dataclass
from typing import Literal, Optional

from .config import Config

logger = logging.getLogger(__name__)

TradingMode = Literal["paper", "live"]


class ModeSwitchError(Exception):
    """Raised when mode switch is not allowed."""
    pass


@dataclass
class ModeStatus:
    """Current trading mode status."""
    current_mode: TradingMode
    phase: str
    can_switch_to_live: bool
    switch_blocked_reason: str | None = None


class ModeSwitcher:
    """
    Manages trading mode switching (paper ↔ live).

    Safety Rules (Constitution v1.0.0):
    - Experience phase: Paper only, no live trading allowed
    - Proof/Trial/Scaling phases: Live trading allowed
    - Live mode requires explicit confirmation
    """

    def __init__(self, config: Config):
        """
        Initialize mode switcher.

        Args:
            config: Current configuration
        """
        self.config = config
        self._current_mode: TradingMode = "live" if not config.paper_trading else "paper"

    @property
    def current_mode(self) -> TradingMode:
        """Get current trading mode."""
        return self._current_mode

    @property
    def is_paper_trading(self) -> bool:
        """Check if currently in paper trading mode."""
        return self._current_mode == "paper"

    @property
    def is_live_trading(self) -> bool:
        """Check if currently in live trading mode."""
        return self._current_mode == "live"

    def get_status(self) -> ModeStatus:
        """
        Get current mode status with switch permissions.

        Returns:
            ModeStatus with current state and permissions
        """
        can_switch, reason = self._can_switch_to_live()

        return ModeStatus(
            current_mode=self._current_mode,
            phase=self.config.current_phase,
            can_switch_to_live=can_switch,
            switch_blocked_reason=reason
        )

    def _can_switch_to_live(self) -> tuple[bool, str | None]:
        """
        Check if switching to live trading is allowed.

        Returns:
            Tuple of (can_switch: bool, reason: Optional[str])
        """
        # Experience phase: Paper trading only
        if self.config.current_phase == "experience":
            return False, "Experience phase requires paper trading (§Safety_First)"

        # All other phases allow live trading
        return True, None

    def switch_to_paper(self) -> None:
        """
        Switch to paper trading mode.

        This is always allowed (safer mode).
        """
        if self._current_mode == "paper":
            logger.info("Already in paper trading mode")
            return

        logger.warning("Switching from LIVE to PAPER trading mode")
        self._current_mode = "paper"
        logger.info("Now in PAPER trading mode (§Safety_First)")

    def switch_to_live(self, force: bool = False) -> None:
        """
        Switch to live trading mode.

        Args:
            force: If True, bypass phase checks (use with caution!)

        Raises:
            ModeSwitchError: If switch is not allowed
        """
        if self._current_mode == "live":
            logger.info("Already in live trading mode")
            return

        # Check if switch is allowed
        if not force:
            can_switch, reason = self._can_switch_to_live()
            if not can_switch:
                raise ModeSwitchError(
                    f"Cannot switch to live trading: {reason}"
                )

        logger.critical("⚠️  SWITCHING TO LIVE TRADING MODE - REAL MONEY WILL BE USED!")
        self._current_mode = "live"
        logger.critical("⚠️  NOW IN LIVE TRADING MODE - TRADES WILL USE REAL MONEY!")

    def display_mode_banner(self) -> str:
        """
        Generate visual mode indicator banner.

        Returns:
            Formatted banner string
        """
        if self.is_paper_trading:
            return self._paper_trading_banner()
        else:
            return self._live_trading_banner()

    def _paper_trading_banner(self) -> str:
        """Generate paper trading mode banner."""
        banner = """
╔════════════════════════════════════════════════════════════╗
║                    PAPER TRADING MODE                      ║
║                  (Simulation - No Real Money)              ║
╚════════════════════════════════════════════════════════════╝
"""
        return banner.strip()

    def _live_trading_banner(self) -> str:
        """Generate live trading mode banner."""
        banner = """
╔════════════════════════════════════════════════════════════╗
║  ⚠️  ⚠️  ⚠️       LIVE TRADING MODE       ⚠️  ⚠️  ⚠️    ║
║                                                            ║
║              REAL MONEY WILL BE USED!                      ║
║                                                            ║
║  All trades execute with actual funds in your account.     ║
║  Ensure you understand the risks before proceeding.        ║
╚════════════════════════════════════════════════════════════╝
"""
        return banner.strip()

    def get_mode_indicator(self) -> str:
        """
        Get short mode indicator for status displays.

        Returns:
            Short mode indicator string
        """
        if self.is_paper_trading:
            return "[PAPER]"
        else:
            return "[⚠️  LIVE ⚠️]"
