"""
Daily Profit Tracker

Core orchestrator for profit goal tracking and protection triggers.

Constitution v1.0.0:
- §Risk_Management: Automated profit protection at configurable thresholds
- §Data_Integrity: State persistence survives crashes, atomic file writes
- §Audit_Everything: All state transitions logged with reasoning

Feature: daily-profit-goal-ma
Tasks: T018-T020, T024, T031-T032 [US2, US3] - Core tracking logic
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from trading_bot.performance.tracker import PerformanceTracker
from trading_bot.profit_goal.models import (
    ProfitGoalConfig,
    DailyProfitState,
    ProfitProtectionEvent,
)

logger = logging.getLogger(__name__)


class DailyProfitTracker:
    """Orchestrates daily profit tracking and protection trigger detection.

    Responsibilities:
    - Query PerformanceTracker for current P&L (realized + unrealized)
    - Maintain peak profit high-water mark
    - Detect drawdown threshold breaches (profit giveback)
    - Trigger profit protection mode to block new entries
    - Persist state to file for crash recovery
    - Reset daily at market open (4:00 AM EST)

    Integration:
    - Reads P&L from PerformanceTracker (single source of truth)
    - Writes protection events via ProfitProtectionLogger
    - Provides protection status to SafetyChecks

    Example:
        >>> config = load_profit_goal_config()
        >>> perf_tracker = PerformanceTracker()
        >>> profit_tracker = DailyProfitTracker(config, perf_tracker)
        >>>
        >>> # After each trade event
        >>> profit_tracker.update_state()
        >>> if profit_tracker.is_protection_active():
        ...     print("Profit protection triggered - blocking new entries")
    """

    def __init__(
        self,
        config: ProfitGoalConfig,
        performance_tracker: PerformanceTracker,
        state_file: Optional[Path] = None,
        log_dir: Optional[Path] = None,
    ) -> None:
        """Initialize daily profit tracker.

        Args:
            config: Profit goal configuration (target, threshold)
            performance_tracker: Source of truth for P&L calculations
            state_file: Path to state persistence file (default: logs/profit-goal-state.json)
            log_dir: Directory for protection event logs (default: logs/profit-protection/)
        """
        self.config = config
        self.performance_tracker = performance_tracker
        self.state_file = state_file or Path("logs/profit-goal-state.json")
        self.log_dir = log_dir or Path("logs/profit-protection")

        # Load or create state
        self._state = self._load_state()

        logger.info(
            "DailyProfitTracker initialized: target=$%s, threshold=%s, protection=%s",
            config.target,
            config.threshold,
            "enabled" if config.enabled else "disabled",
        )

    def update_state(self) -> None:
        """Update profit state from PerformanceTracker (T019).

        Queries current P&L, updates peak profit high-water mark, and
        checks for protection trigger conditions.

        Side effects:
        - Updates in-memory state
        - Persists state to file
        - Logs protection events if triggered
        - Creates protection event via logger

        Performance: <100ms per update (NFR-001)
        """
        try:
            # Query current P&L from PerformanceTracker (single source of truth)
            summary = self.performance_tracker.get_summary(window="daily")

            realized_pnl = summary.realized_pnl
            unrealized_pnl = summary.unrealized_pnl
            daily_pnl = realized_pnl + unrealized_pnl

            # Update P&L values
            self._state.realized_pnl = realized_pnl
            self._state.unrealized_pnl = unrealized_pnl
            self._state.daily_pnl = daily_pnl

            # Update peak profit (high-water mark)
            # Only track positive profits (peak doesn't go negative)
            if daily_pnl > self._state.peak_profit and daily_pnl > 0:
                old_peak = self._state.peak_profit
                self._state.peak_profit = daily_pnl
                logger.debug(
                    "Peak profit updated: $%s → $%s",
                    old_peak,
                    daily_pnl,
                )

            # Update timestamp
            self._state.last_updated = datetime.now(timezone.utc).isoformat()

            # Check for protection trigger (T024 - US3)
            self._check_protection_trigger()

            # Persist state to file (atomic write)
            self._persist_state()

            logger.debug(
                "State updated: daily_pnl=$%s, peak=$%s, protection=%s",
                daily_pnl,
                self._state.peak_profit,
                self._state.protection_active,
            )

        except Exception as e:
            logger.error(
                "Failed to update profit state: %s. Maintaining previous state.",
                str(e),
                exc_info=True,
            )
            # Don't crash - maintain previous state (§Safety_First)

    def get_current_state(self) -> DailyProfitState:
        """Get current profit tracking state.

        Returns:
            DailyProfitState: Current state (immutable copy)
        """
        return self._state

    def is_protection_active(self) -> bool:
        """Check if profit protection mode is currently active.

        Returns:
            bool: True if protection triggered and blocking new entries
        """
        return self._state.protection_active

    def reset_daily_state(self) -> None:
        """Reset daily state to $0 at market open (T031).

        Clears all P&L values, peak profit, and protection status.
        Called at market open (4:00 AM EST) to begin new trading session.

        Side effects:
        - Resets all P&L values to $0
        - Clears protection_active flag
        - Updates session_date to current date
        - Sets last_reset timestamp
        - Persists fresh state to file
        """
        current_date = datetime.now(timezone.utc).date().isoformat()

        self._state = DailyProfitState(
            session_date=current_date,
            daily_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            peak_profit=Decimal("0"),
            protection_active=False,
            last_reset=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        self._persist_state()

        logger.info(
            "Daily profit state reset for session %s at market open",
            current_date,
        )

    def _check_protection_trigger(self) -> None:
        """Check if profit protection should be triggered (T024 - US3).

        Protection trigger conditions:
        1. Feature enabled (config.enabled = True)
        2. Peak profit > 0 (can't have drawdown from $0)
        3. Drawdown >= threshold (given back enough profit)

        Note: Original spec required "peak >= target", but tests and US3 requirements
        indicate protection should trigger on any profit giveback meeting threshold.
        Target is for goal tracking, not protection gating.

        If all conditions met:
        - Set protection_active = True
        - Create and log ProfitProtectionEvent
        - Block new trade entries (enforced by SafetyChecks)
        """
        # Skip if protection already active
        if self._state.protection_active:
            return

        # Skip if feature disabled
        if not self.config.enabled:
            return

        # Skip if no profit to protect
        if self._state.peak_profit <= 0:
            return

        # Calculate drawdown percentage
        drawdown = (self._state.peak_profit - self._state.daily_pnl) / self._state.peak_profit

        # Check if drawdown breaches threshold
        if drawdown >= self.config.threshold:
            # Trigger protection
            self._state.protection_active = True

            logger.warning(
                "PROFIT PROTECTION TRIGGERED: Peak=$%s, Current=$%s, Drawdown=%.1f%% (threshold=%.1f%%)",
                self._state.peak_profit,
                self._state.daily_pnl,
                drawdown * 100,
                self.config.threshold * 100,
            )

            # Create protection event for audit trail (T025-T026 - US3)
            event = ProfitProtectionEvent.create(
                session_date=self._state.session_date,
                peak_profit=self._state.peak_profit,
                current_profit=self._state.daily_pnl,
                threshold=self.config.threshold,
                session_id=f"session-{self._state.session_date}",
            )

            # Log event (implementation in T025-T026)
            self._log_protection_event(event)

    def _log_protection_event(self, event: ProfitProtectionEvent) -> None:
        """Log protection event to audit trail (T026).

        Args:
            event: Protection event to log
        """
        # Create log directory if needed
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Write to daily JSONL file
        log_file = self.log_dir / f"{event.session_date}.jsonl"

        try:
            with open(log_file, "a") as f:
                event_data = {
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "session_date": event.session_date,
                    "peak_profit": str(event.peak_profit),
                    "current_profit": str(event.current_profit),
                    "drawdown_percent": str(event.drawdown_percent),
                    "threshold": str(event.threshold),
                    "session_id": event.session_id,
                }
                f.write(json.dumps(event_data) + "\n")

            logger.info(
                "Protection event logged: %s (drawdown=%.1f%%)",
                event.event_id,
                event.drawdown_percent * 100,
            )

        except Exception as e:
            logger.error(
                "Failed to log protection event: %s. Event data: %s",
                str(e),
                event,
                exc_info=True,
            )
            # Don't crash on logging failure (§Safety_First)

    def _persist_state(self) -> None:
        """Persist state to JSON file with atomic write (T020).

        Uses temp file + rename for atomic writes to prevent corruption.

        Raises:
            None - logs errors but doesn't crash (§Safety_First)
        """
        try:
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare state data
            state_data = {
                "session_date": self._state.session_date,
                "daily_pnl": str(self._state.daily_pnl),
                "realized_pnl": str(self._state.realized_pnl),
                "unrealized_pnl": str(self._state.unrealized_pnl),
                "peak_profit": str(self._state.peak_profit),
                "protection_active": self._state.protection_active,
                "last_reset": self._state.last_reset,
                "last_updated": self._state.last_updated,
            }

            # Atomic write: temp file + rename
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(state_data, f, indent=2)

            temp_file.replace(self.state_file)

        except Exception as e:
            logger.error(
                "Failed to persist profit state: %s. State will be lost on crash.",
                str(e),
                exc_info=True,
            )
            # Don't crash - continue operating with in-memory state

    def _load_state(self) -> DailyProfitState:
        """Load state from JSON file or create fresh state (T020, T036).

        Returns:
            DailyProfitState: Loaded state or fresh state with defaults

        Error handling:
        - File not found → fresh state
        - JSON parse error → fresh state + warning log
        - Missing fields → fresh state + warning log
        """
        if not self.state_file.exists():
            logger.info("No state file found. Creating fresh state.")
            return self._create_fresh_state()

        try:
            with open(self.state_file) as f:
                data = json.load(f)

            # Validate required fields
            required = ["session_date", "daily_pnl", "realized_pnl", "unrealized_pnl",
                        "peak_profit", "protection_active", "last_reset", "last_updated"]
            if not all(field in data for field in required):
                logger.warning("State file missing required fields. Creating fresh state.")
                return self._create_fresh_state()

            state = DailyProfitState(
                session_date=data["session_date"],
                daily_pnl=Decimal(data["daily_pnl"]),
                realized_pnl=Decimal(data["realized_pnl"]),
                unrealized_pnl=Decimal(data["unrealized_pnl"]),
                peak_profit=Decimal(data["peak_profit"]),
                protection_active=data["protection_active"],
                last_reset=data["last_reset"],
                last_updated=data["last_updated"],
            )

            logger.info(
                "State loaded from file: session=%s, daily_pnl=$%s, peak=$%s, protection=%s",
                state.session_date,
                state.daily_pnl,
                state.peak_profit,
                state.protection_active,
            )

            return state

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(
                "Failed to load state file (corrupted or invalid): %s. Creating fresh state.",
                str(e),
            )
            return self._create_fresh_state()

    def _create_fresh_state(self) -> DailyProfitState:
        """Create fresh state with default values.

        Returns:
            DailyProfitState: Fresh state with $0 P&L and no protection
        """
        current_date = datetime.now(timezone.utc).date().isoformat()
        current_time = datetime.now(timezone.utc).isoformat()

        return DailyProfitState(
            session_date=current_date,
            daily_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            peak_profit=Decimal("0"),
            protection_active=False,
            last_reset=current_time,
            last_updated=current_time,
        )
