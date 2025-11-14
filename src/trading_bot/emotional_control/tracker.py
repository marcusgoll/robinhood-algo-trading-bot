"""
Emotional Control Tracker

Core orchestrator for emotional control state management and position sizing adjustment.

Constitution v1.0.0:
- §Safety_First: Fail-safe default to ACTIVE state on corruption
- §Data_Integrity: State persistence survives crashes, atomic file writes
- §Audit_Everything: All state transitions logged with reasoning

Feature: emotional-control-me
Tasks: T007-T015 - Core tracker implementation
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple

from src.trading_bot.emotional_control.models import (
    EmotionalControlState,
    EmotionalControlEvent,
)
from src.trading_bot.emotional_control.config import EmotionalControlConfig

logger = logging.getLogger(__name__)


class EmotionalControl:
    """Orchestrates emotional control state tracking and position size adjustment (T007).

    Responsibilities:
    - Track consecutive win/loss streaks
    - Detect activation triggers (single loss ≥3% OR 3 consecutive losses)
    - Detect recovery triggers (3 consecutive wins OR manual reset)
    - Apply position size multiplier (0.25 when active, 1.00 when inactive)
    - Persist state to file for crash recovery
    - Log all state transitions for audit trail

    Integration:
    - Provides position_multiplier to RiskManager for position sizing
    - Receives trade outcomes from trading loop for streak tracking
    - Writes state to logs/emotional_control/state.json
    - Writes events to logs/emotional_control/events-YYYY-MM-DD.jsonl

    Example:
        >>> config = EmotionalControlConfig.default()
        >>> ec = EmotionalControl(config)
        >>>
        >>> # After each trade
        >>> ec.update_state(
        ...     trade_pnl=Decimal("-3500"),
        ...     account_balance=Decimal("100000"),
        ...     is_win=False
        ... )
        >>> multiplier = ec.get_position_multiplier()  # Returns 0.25 if triggered
    """

    def __init__(
        self,
        config: EmotionalControlConfig,
        state_file: Optional[Path] = None,
        log_dir: Optional[Path] = None,
    ) -> None:
        """Initialize emotional control tracker.

        Args:
            config: Emotional control configuration (thresholds, multipliers)
            state_file: Path to state persistence file (default: config.state_file_path)
            log_dir: Directory for event logs (default: config.event_log_dir)
        """
        self._config = config
        self._state_file = state_file or config.state_file_path
        self._log_dir = log_dir or config.event_log_dir

        # Load or create state
        self._state = self._load_state()

        logger.info(
            "EmotionalControl initialized: enabled=%s, single_loss_threshold=%s%%, "
            "consecutive_loss_threshold=%d, recovery_win_threshold=%d, "
            "active_multiplier=%s, state=%s",
            config.enabled,
            config.single_loss_threshold_pct,
            config.consecutive_loss_threshold,
            config.recovery_win_threshold,
            config.position_size_multiplier_active,
            "ACTIVE" if self._state.is_active else "INACTIVE",
        )

    def update_state(
        self, trade_pnl: Decimal, account_balance: Decimal, is_win: bool
    ) -> None:
        """Update emotional control state after trade execution (T013).

        Args:
            trade_pnl: Trade profit/loss in dollars (negative for losses)
            account_balance: Current account balance before trade
            is_win: Whether trade was profitable (True) or loss (False)

        Side effects:
        - Updates consecutive win/loss counters
        - Checks activation triggers (single loss OR streak)
        - Checks recovery triggers (win streak OR manual reset)
        - Updates in-memory state
        - Persists state to file
        - Logs events if state transitions occur

        Performance: Target <10ms per spec.md NFR-001
        """
        if not self._config.enabled:
            logger.debug("Emotional control disabled, skipping update")
            return

        try:
            # Update consecutive counters
            if is_win:
                self._state.consecutive_wins += 1
                self._state.consecutive_losses = 0  # Reset loss streak
            else:
                self._state.consecutive_losses += 1
                self._state.consecutive_wins = 0  # Reset win streak

            # Update timestamp
            self._state.last_updated = datetime.now(timezone.utc).isoformat()

            logger.debug(
                "Trade outcome: pnl=$%s, win=%s, consecutive_losses=%d, consecutive_wins=%d",
                trade_pnl,
                is_win,
                self._state.consecutive_losses,
                self._state.consecutive_wins,
            )

            # Check activation trigger (if not already active)
            if not self._state.is_active:
                should_activate, trigger_reason = self._check_activation_trigger(
                    trade_pnl, account_balance, self._state.consecutive_losses
                )

                if should_activate:
                    self._activate_control(
                        trigger_reason, account_balance, trade_pnl
                    )

            # Check recovery trigger (if currently active)
            elif self._state.is_active:
                should_deactivate = self._check_recovery_trigger(
                    self._state.consecutive_wins
                )

                if should_deactivate:
                    self._deactivate_control("PROFITABLE_RECOVERY")

            # Persist state (atomic write)
            self._persist_state()

        except Exception as e:
            logger.error(
                "Failed to update emotional control state: %s. Maintaining previous state.",
                str(e),
                exc_info=True,
            )
            # Don't crash - maintain previous state (§Safety_First)

    def get_position_multiplier(self) -> Decimal:
        """Get current position size multiplier (T014).

        Returns:
            Decimal: 0.25 if emotional control active, 1.00 if inactive

        Performance: Target <1ms (in-memory lookup)
        """
        if not self._config.enabled:
            return Decimal("1.00")

        if self._state.is_active:
            return self._config.position_size_multiplier_active
        else:
            return Decimal("1.00")

    def reset_manual(self, admin_id: str, reset_reason: str, confirm: bool) -> None:
        """Manually reset emotional control (admin override) (T015).

        Args:
            admin_id: Administrator user ID performing reset
            reset_reason: Human-readable reason for manual reset
            confirm: Safety confirmation flag (must be True)

        Raises:
            ValueError: If confirm is not True

        Side effects:
        - Deactivates emotional control
        - Resets consecutive counters to 0
        - Creates MANUAL_RESET event with admin context
        - Persists state to file
        """
        if not confirm:
            raise ValueError(
                "Manual reset requires confirm=True. This is a safety check."
            )

        if not self._state.is_active:
            logger.warning(
                "Manual reset requested but emotional control already inactive. "
                "Admin: %s, Reason: %s",
                admin_id,
                reset_reason,
            )
            return

        logger.warning(
            "MANUAL RESET: Emotional control deactivated by admin. "
            "Admin: %s, Reason: %s",
            admin_id,
            reset_reason,
        )

        # Deactivate control
        self._state.is_active = False
        self._state.activated_at = None
        self._state.trigger_reason = None
        self._state.account_balance_at_activation = None
        self._state.loss_amount = None
        self._state.consecutive_wins = 0
        self._state.consecutive_losses = 0
        self._state.last_updated = datetime.now(timezone.utc).isoformat()

        # Log manual reset event
        event = EmotionalControlEvent.create(
            event_type="MANUAL_RESET",
            trigger_reason="MANUAL_RESET",
            account_balance=Decimal("0"),  # Not applicable for manual reset
            consecutive_losses=0,
            consecutive_wins=0,
            position_size_multiplier=Decimal("1.00"),
            admin_id=admin_id,
            reset_reason=reset_reason,
        )
        self._log_event(event)

        # Persist state
        self._persist_state()

    def _check_activation_trigger(
        self, trade_pnl: Decimal, account_balance: Decimal, consecutive_losses: int
    ) -> Tuple[bool, str]:
        """Check if emotional control should activate (T010).

        Activation triggers:
        1. Single loss ≥3% of account balance (SINGLE_LOSS)
        2. Consecutive losses ≥3 trades (STREAK_LOSS)

        Args:
            trade_pnl: Trade profit/loss (negative for losses)
            account_balance: Account balance before trade
            consecutive_losses: Current consecutive loss count

        Returns:
            Tuple[bool, str]: (should_activate, trigger_reason)
        """
        # Check single loss trigger (≥3% of account)
        if trade_pnl < 0:
            loss_pct = abs(trade_pnl) / account_balance * 100
            if loss_pct >= self._config.single_loss_threshold_pct:
                logger.info(
                    "Single loss trigger: $%s loss (%.2f%% of $%s account) >= %s%% threshold",
                    abs(trade_pnl),
                    loss_pct,
                    account_balance,
                    self._config.single_loss_threshold_pct,
                )
                return (True, "SINGLE_LOSS")

        # Check consecutive loss streak trigger
        if consecutive_losses >= self._config.consecutive_loss_threshold:
            logger.info(
                "Consecutive loss trigger: %d losses >= %d threshold",
                consecutive_losses,
                self._config.consecutive_loss_threshold,
            )
            return (True, "STREAK_LOSS")

        return (False, "")

    def _check_recovery_trigger(self, consecutive_wins: int) -> bool:
        """Check if emotional control should deactivate (recovery) (T011).

        Recovery trigger:
        - Consecutive wins ≥3 trades (PROFITABLE_RECOVERY)

        Args:
            consecutive_wins: Current consecutive win count

        Returns:
            bool: True if recovery conditions met
        """
        if consecutive_wins >= self._config.recovery_win_threshold:
            logger.info(
                "Recovery trigger: %d consecutive wins >= %d threshold",
                consecutive_wins,
                self._config.recovery_win_threshold,
            )
            return True

        return False

    def _activate_control(
        self, trigger_reason: str, account_balance: Decimal, loss_amount: Decimal
    ) -> None:
        """Activate emotional control and log event.

        Args:
            trigger_reason: Why control activated (SINGLE_LOSS or STREAK_LOSS)
            account_balance: Account balance at activation
            loss_amount: Loss amount that triggered (if SINGLE_LOSS)
        """
        self._state.is_active = True
        self._state.activated_at = datetime.now(timezone.utc).isoformat()
        self._state.trigger_reason = trigger_reason
        self._state.account_balance_at_activation = account_balance
        self._state.loss_amount = abs(loss_amount) if loss_amount < 0 else None

        logger.warning(
            "EMOTIONAL CONTROL ACTIVATED: Reason=%s, AccountBalance=$%s, "
            "ConsecutiveLosses=%d, PositionMultiplier=%s",
            trigger_reason,
            account_balance,
            self._state.consecutive_losses,
            self._config.position_size_multiplier_active,
        )

        # Log activation event
        event = EmotionalControlEvent.create(
            event_type="ACTIVATION",
            trigger_reason=trigger_reason,
            account_balance=account_balance,
            consecutive_losses=self._state.consecutive_losses,
            consecutive_wins=self._state.consecutive_wins,
            position_size_multiplier=self._config.position_size_multiplier_active,
            loss_amount=self._state.loss_amount,
        )
        self._log_event(event)

    def _deactivate_control(self, trigger_reason: str) -> None:
        """Deactivate emotional control and log event.

        Args:
            trigger_reason: Why control deactivated (PROFITABLE_RECOVERY or MANUAL_RESET)
        """
        self._state.is_active = False
        self._state.activated_at = None
        self._state.trigger_reason = None
        self._state.account_balance_at_activation = None
        self._state.loss_amount = None

        logger.info(
            "EMOTIONAL CONTROL DEACTIVATED: Reason=%s, ConsecutiveWins=%d, PositionMultiplier=1.00",
            trigger_reason,
            self._state.consecutive_wins,
        )

        # Log recovery event
        event = EmotionalControlEvent.create(
            event_type="RECOVERY",
            trigger_reason=trigger_reason,
            account_balance=Decimal("0"),  # Not tracked for recovery
            consecutive_losses=self._state.consecutive_losses,
            consecutive_wins=self._state.consecutive_wins,
            position_size_multiplier=Decimal("1.00"),
        )
        self._log_event(event)

    def _log_event(self, event: EmotionalControlEvent) -> None:
        """Log event to JSONL audit trail (T012).

        Args:
            event: Event to log

        Daily rotation: Filename includes date (events-YYYY-MM-DD.jsonl)
        """
        try:
            # Ensure log directory exists
            self._log_dir.mkdir(parents=True, exist_ok=True)

            # Daily rotation: include date in filename
            log_date = datetime.now(timezone.utc).date().isoformat()
            log_file = self._log_dir / f"events-{log_date}.jsonl"

            # Serialize event to JSON line
            event_data = {
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "trigger_reason": event.trigger_reason,
                "account_balance": str(event.account_balance),
                "loss_amount": str(event.loss_amount) if event.loss_amount else None,
                "consecutive_losses": event.consecutive_losses,
                "consecutive_wins": event.consecutive_wins,
                "admin_id": event.admin_id,
                "reset_reason": event.reset_reason,
                "position_size_multiplier": str(event.position_size_multiplier),
            }

            # Append to JSONL file
            with open(log_file, "a") as f:
                f.write(json.dumps(event_data) + "\n")

            logger.debug(
                "Event logged: %s (%s) to %s",
                event.event_id,
                event.event_type,
                log_file,
            )

        except Exception as e:
            logger.error(
                "Failed to log event: %s. Event data: %s",
                str(e),
                event,
                exc_info=True,
            )
            # Don't crash on logging failure (§Safety_First)

    def _persist_state(self) -> None:
        """Persist state to JSON file with atomic write (T009).

        Uses temp file + rename for atomic writes to prevent corruption.
        Pattern: DailyProfitTracker._persist_state()

        Raises:
            None - logs errors but doesn't crash (§Safety_First)
        """
        try:
            # Ensure parent directory exists
            self._state_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare state data
            state_data = {
                "is_active": self._state.is_active,
                "activated_at": self._state.activated_at,
                "trigger_reason": self._state.trigger_reason,
                "account_balance_at_activation": (
                    str(self._state.account_balance_at_activation)
                    if self._state.account_balance_at_activation
                    else None
                ),
                "loss_amount": (
                    str(self._state.loss_amount) if self._state.loss_amount else None
                ),
                "consecutive_losses": self._state.consecutive_losses,
                "consecutive_wins": self._state.consecutive_wins,
                "last_updated": self._state.last_updated,
            }

            # Atomic write: temp file + rename
            temp_file = self._state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(state_data, f, indent=2)

            temp_file.replace(self._state_file)

            logger.debug("State persisted to %s", self._state_file)

        except Exception as e:
            logger.error(
                "Failed to persist emotional control state: %s. State will be lost on crash.",
                str(e),
                exc_info=True,
            )
            # Don't crash - continue operating with in-memory state

    def _load_state(self) -> EmotionalControlState:
        """Load state from JSON file or create fresh state (T008).

        Fail-safe behavior (spec.md FR-013):
        - File not found → INACTIVE state (normal startup)
        - JSON parse error → ACTIVE state with alert (fail-safe, conservative)
        - Missing fields → ACTIVE state with alert (fail-safe, conservative)
        - Valid file → Loaded state

        Returns:
            EmotionalControlState: Loaded state or fail-safe default

        Error handling:
        - Corruption → Default to ACTIVE (fail-safe per spec.md FR-013)
        - ACTIVE state prevents overtrading during recovery from corruption
        """
        if not self._state_file.exists():
            logger.info("No state file found. Creating fresh INACTIVE state.")
            return EmotionalControlState(
                is_active=False,
                activated_at=None,
                trigger_reason=None,
                account_balance_at_activation=None,
                loss_amount=None,
                consecutive_losses=0,
                consecutive_wins=0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )

        try:
            with open(self._state_file, "r") as f:
                data = json.load(f)

            # Parse state fields
            return EmotionalControlState(
                is_active=data["is_active"],
                activated_at=data.get("activated_at"),
                trigger_reason=data.get("trigger_reason"),
                account_balance_at_activation=(
                    Decimal(data["account_balance_at_activation"])
                    if data.get("account_balance_at_activation")
                    else None
                ),
                loss_amount=(
                    Decimal(data["loss_amount"]) if data.get("loss_amount") else None
                ),
                consecutive_losses=data["consecutive_losses"],
                consecutive_wins=data["consecutive_wins"],
                last_updated=data["last_updated"],
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "STATE CORRUPTION DETECTED: Failed to load state from %s: %s. "
                "FAIL-SAFE: Defaulting to ACTIVE state (conservative position sizing).",
                self._state_file,
                str(e),
                exc_info=True,
            )

            # Fail-safe: Default to ACTIVE state (spec.md FR-013)
            # This prevents overtrading during recovery from corruption
            return EmotionalControlState(
                is_active=True,  # FAIL-SAFE: Conservative default
                activated_at=datetime.now(timezone.utc).isoformat(),
                trigger_reason="STREAK_LOSS",  # Arbitrary reason for fail-safe
                account_balance_at_activation=None,
                loss_amount=None,
                consecutive_losses=self._config.consecutive_loss_threshold,
                consecutive_wins=0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error(
                "UNEXPECTED ERROR loading state from %s: %s. "
                "FAIL-SAFE: Defaulting to ACTIVE state.",
                self._state_file,
                str(e),
                exc_info=True,
            )

            # Fail-safe: Default to ACTIVE state
            return EmotionalControlState(
                is_active=True,  # FAIL-SAFE: Conservative default
                activated_at=datetime.now(timezone.utc).isoformat(),
                trigger_reason="STREAK_LOSS",
                account_balance_at_activation=None,
                loss_amount=None,
                consecutive_losses=self._config.consecutive_loss_threshold,
                consecutive_wins=0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
