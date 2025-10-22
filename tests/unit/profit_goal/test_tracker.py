"""
Unit tests for DailyProfitTracker (TDD)

Tests Constitution v1.0.0 requirements:
- §Risk_Management: Peak profit tracking and protection triggers
- §Data_Integrity: State persistence survives crashes
- §Audit_Everything: All state transitions logged

Feature: daily-profit-goal-ma
Tasks: T015-T017, T021 [US2, US3] - Test profit tracking core logic
"""

import json
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.trading_bot.profit_goal.models import (
    ProfitGoalConfig,
    DailyProfitState,
)
from src.trading_bot.profit_goal.tracker import DailyProfitTracker
from src.trading_bot.performance.models import PerformanceSummary


class TestDailyProfitTrackerPeakTracking:
    """Test peak profit tracking logic (T015)."""

    # =========================================================================
    # T015 [US2]: Test DailyProfitState tracks peak profit correctly
    # =========================================================================

    def test_peak_follows_when_pnl_increases(self, tmp_path: Path) -> None:
        """Should update peak when P&L increases (T015).

        Given P&L increases from $300 to $500
        When update_state() is called
        Then peak_profit should increase to $500
        """
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=tmp_path / "test-state.json",
        )

        # Initial state: $300 profit
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("200"),
            unrealized_pnl=Decimal("100"),
        )
        tracker.update_state()
        state1 = tracker.get_current_state()
        assert state1.daily_pnl == Decimal("300")
        assert state1.peak_profit == Decimal("300")

        # P&L increases to $500
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("300"),
            unrealized_pnl=Decimal("200"),
        )
        tracker.update_state()
        state2 = tracker.get_current_state()
        assert state2.daily_pnl == Decimal("500")
        assert state2.peak_profit == Decimal("500"), "Peak should increase with P&L"

    def test_peak_stays_when_pnl_decreases(self, tmp_path: Path) -> None:
        """Should maintain peak when P&L decreases (T015).

        Given peak profit is $600 and P&L drops to $300
        When update_state() is called
        Then peak_profit should stay at $600 (high-water mark)
        """
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=tmp_path / "test-state.json",
        )

        # Reach peak: $600
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("400"),
            unrealized_pnl=Decimal("200"),
        )
        tracker.update_state()
        state1 = tracker.get_current_state()
        assert state1.peak_profit == Decimal("600")

        # P&L drops to $300
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("200"),
            unrealized_pnl=Decimal("100"),
        )
        tracker.update_state()
        state2 = tracker.get_current_state()
        assert state2.daily_pnl == Decimal("300")
        assert state2.peak_profit == Decimal("600"), "Peak should not decrease"

    def test_peak_resets_to_zero_on_reset(self, tmp_path: Path) -> None:
        """Should reset peak to $0 on daily reset (T015, T030).

        Given peak profit is $600
        When reset_daily_state() is called
        Then peak_profit should reset to $0
        """
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(config=config, performance_tracker=perf_tracker, state_file=tmp_path / "test-state.json")

        # Reach peak
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("400"),
            unrealized_pnl=Decimal("200"),
        )
        tracker.update_state()
        assert tracker.get_current_state().peak_profit == Decimal("600")

        # Reset daily state
        tracker.reset_daily_state()
        state = tracker.get_current_state()
        assert state.peak_profit == Decimal("0")
        assert state.daily_pnl == Decimal("0")
        assert state.protection_active is False


class TestDailyProfitTrackerStateUpdate:
    """Test state update from PerformanceTracker (T016)."""

    # =========================================================================
    # T016 [US2]: Test DailyProfitTracker updates state from PerformanceTracker
    # =========================================================================

    def test_update_with_positive_pnl(self, tmp_path: Path) -> None:
        """Should update state with positive P&L from PerformanceTracker (T016).

        Given PerformanceTracker returns positive realized and unrealized P&L
        When update_state() is called
        Then daily_pnl should equal realized + unrealized
        """
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(config=config, performance_tracker=perf_tracker, state_file=tmp_path / "test-state.json")

        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("400"),
            unrealized_pnl=Decimal("200"),
        )

        tracker.update_state()
        state = tracker.get_current_state()

        assert state.realized_pnl == Decimal("400")
        assert state.unrealized_pnl == Decimal("200")
        assert state.daily_pnl == Decimal("600")
        assert state.last_updated is not None

    def test_update_with_negative_pnl(self, tmp_path: Path) -> None:
        """Should update state with negative P&L (losses) (T016).

        Given PerformanceTracker returns negative P&L
        When update_state() is called
        Then daily_pnl should be negative
        """
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(config=config, performance_tracker=perf_tracker, state_file=tmp_path / "test-state.json")

        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("-150"),
            unrealized_pnl=Decimal("-50"),
        )

        tracker.update_state()
        state = tracker.get_current_state()

        assert state.daily_pnl == Decimal("-200")
        assert state.peak_profit == Decimal("0"), "Peak should not go negative"

    def test_update_with_no_positions(self, tmp_path: Path) -> None:
        """Should handle update when no trades executed (T016).

        Given PerformanceTracker returns $0 P&L
        When update_state() is called
        Then state should show $0 P&L
        """
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(config=config, performance_tracker=perf_tracker, state_file=tmp_path / "test-state.json")

        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
        )

        tracker.update_state()
        state = tracker.get_current_state()

        assert state.daily_pnl == Decimal("0")
        assert state.peak_profit == Decimal("0")


class TestDailyProfitTrackerPersistence:
    """Test state persistence to file (T017)."""

    # =========================================================================
    # T017 [US2]: Test DailyProfitState persists to JSON file
    # =========================================================================

    def test_state_persists_to_file(self, tmp_path: Path) -> None:
        """Should save state to JSON file (T017).

        Given state has been updated
        When _persist_state() is called
        Then state should be written to logs/profit-goal-state.json
        """
        state_file = tmp_path / "profit-goal-state.json"
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=state_file,
        )

        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("300"),
            unrealized_pnl=Decimal("200"),
        )
        tracker.update_state()

        # Verify file exists and contains valid JSON
        assert state_file.exists()
        with open(state_file) as f:
            data = json.load(f)

        assert data["daily_pnl"] == "500"
        assert data["peak_profit"] == "500"
        assert data["session_date"] is not None

    def test_state_loads_from_file(self, tmp_path: Path) -> None:
        """Should load state from JSON file on init (T017).

        Given state file exists with saved state
        When DailyProfitTracker is initialized
        Then state should be loaded from file
        """
        state_file = tmp_path / "profit-goal-state.json"

        # Pre-create state file
        state_data = {
            "session_date": "2025-10-21",
            "daily_pnl": "400",
            "realized_pnl": "300",
            "unrealized_pnl": "100",
            "peak_profit": "600",
            "protection_active": True,
            "last_reset": "2025-10-21T04:00:00Z",
            "last_updated": "2025-10-21T14:30:00Z",
        }
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=state_file,
        )

        state = tracker.get_current_state()
        assert state.daily_pnl == Decimal("400")
        assert state.peak_profit == Decimal("600")
        assert state.protection_active is True

    def test_file_not_found_returns_fresh_state(self, tmp_path: Path) -> None:
        """Should return fresh state when file doesn't exist (T017).

        Given state file does not exist
        When DailyProfitTracker is initialized
        Then fresh state should be created with defaults
        """
        state_file = tmp_path / "nonexistent.json"
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=state_file,
        )

        state = tracker.get_current_state()
        assert state.daily_pnl == Decimal("0")
        assert state.peak_profit == Decimal("0")
        assert state.protection_active is False

    def test_corrupted_json_returns_fresh_state(self, tmp_path: Path) -> None:
        """Should return fresh state when JSON is corrupted (T017, T036).

        Given state file exists but contains invalid JSON
        When DailyProfitTracker is initialized
        Then fresh state should be created and warning logged
        """
        state_file = tmp_path / "corrupted.json"

        # Write corrupted JSON
        with open(state_file, "w") as f:
            f.write("{invalid json")

        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=state_file,
        )

        state = tracker.get_current_state()
        assert state.daily_pnl == Decimal("0")
        assert state.peak_profit == Decimal("0")


class TestProtectionTrigger:
    """Test profit protection trigger logic (T021 - US3 foundation)."""

    # =========================================================================
    # T021 [US3]: Test DailyProfitTracker detects 50% drawdown
    # =========================================================================

    def test_protection_triggers_at_threshold(self, tmp_path: Path) -> None:
        """Should trigger protection when drawdown reaches threshold (T021).

        Given peak profit $600 and threshold 50%
        When P&L drops to $300 (50% drawdown)
        Then protection_active should be True
        """
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(config=config, performance_tracker=perf_tracker, state_file=tmp_path / "test-state.json")

        # Reach peak: $600
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("600"),
            unrealized_pnl=Decimal("0"),
        )
        tracker.update_state()

        # Drop to $300 (50% drawdown)
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("300"),
            unrealized_pnl=Decimal("0"),
        )
        tracker.update_state()

        state = tracker.get_current_state()
        assert state.protection_active is True
        assert tracker.is_protection_active() is True

    def test_protection_does_not_trigger_below_threshold(self, tmp_path: Path) -> None:
        """Should not trigger protection when drawdown below threshold (T021).

        Given peak profit $600 and threshold 50%
        When P&L drops to $400 (33% drawdown)
        Then protection_active should be False
        """
        config = ProfitGoalConfig(target=Decimal("1000"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(config=config, performance_tracker=perf_tracker, state_file=tmp_path / "test-state.json")

        # Reach peak: $600
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("600"),
            unrealized_pnl=Decimal("0"),
        )
        tracker.update_state()

        # Drop to $400 (33% drawdown - below 50% threshold)
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("400"),
            unrealized_pnl=Decimal("0"),
        )
        tracker.update_state()

        state = tracker.get_current_state()
        assert state.protection_active is False

    def test_protection_does_not_trigger_when_feature_disabled(self, tmp_path: Path) -> None:
        """Should not trigger protection when feature is disabled (T021).

        Given target $0 (feature disabled)
        When P&L drops 50% from peak
        Then protection should not trigger
        """
        config = ProfitGoalConfig(target=Decimal("0"), threshold=Decimal("0.50"))  # Disabled
        perf_tracker = Mock()
        tracker = DailyProfitTracker(config=config, performance_tracker=perf_tracker, state_file=tmp_path / "test-state.json")

        # Reach peak: $400
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("400"),
            unrealized_pnl=Decimal("0"),
        )
        tracker.update_state()

        # Drop to $200 (50% drawdown)
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("200"),
            unrealized_pnl=Decimal("0"),
        )
        tracker.update_state()

        # Protection should NOT trigger (feature disabled)
        state = tracker.get_current_state()
        assert state.protection_active is False


class TestProtectionEventLogging:
    """Test protection event logging to JSONL (T023 - US3)."""

    # =========================================================================
    # T023 [US3]: Test ProfitProtectionLogger writes JSONL events
    # =========================================================================

    def test_protection_event_logged_to_jsonl(self, tmp_path: Path) -> None:
        """Should log protection event to daily JSONL file (T023).

        Given protection trigger occurs
        When protection event is created
        Then event should be written to logs/profit-protection/YYYY-MM-DD.jsonl
        """
        log_dir = tmp_path / "profit-protection"
        config = ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=tmp_path / "test-state.json",
            log_dir=log_dir,
        )

        # Reach peak: $600
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("600"),
            unrealized_pnl=Decimal("0"),
        )
        tracker.update_state()

        # Trigger protection: drop to $300
        perf_tracker.get_summary.return_value = Mock(
            realized_pnl=Decimal("300"),
            unrealized_pnl=Decimal("0"),
        )
        tracker.update_state()

        # Verify event logged to JSONL
        state = tracker.get_current_state()
        log_file = log_dir / f"{state.session_date}.jsonl"

        assert log_file.exists(), "Event log file should be created"

        # Verify JSONL content
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 1, "Should have one event logged"

        event = json.loads(lines[0])
        assert event["peak_profit"] == "600"
        assert event["current_profit"] == "300"
        assert event["session_date"] == state.session_date
        assert "event_id" in event
        assert "timestamp" in event

    def test_protection_event_includes_drawdown_metadata(self, tmp_path: Path) -> None:
        """Should include drawdown percentage and threshold in event (T023).

        Given protection triggers at 50% drawdown
        When event is logged
        Then event should include drawdown_percent and threshold fields
        """
        log_dir = tmp_path / "profit-protection"
        config = ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=tmp_path / "test-state.json",
            log_dir=log_dir,
        )

        # Trigger protection
        perf_tracker.get_summary.return_value = Mock(realized_pnl=Decimal("800"), unrealized_pnl=Decimal("0"))
        tracker.update_state()

        perf_tracker.get_summary.return_value = Mock(realized_pnl=Decimal("400"), unrealized_pnl=Decimal("0"))
        tracker.update_state()

        # Read event
        state = tracker.get_current_state()
        log_file = log_dir / f"{state.session_date}.jsonl"

        with open(log_file) as f:
            event = json.loads(f.readline())

        assert "drawdown_percent" in event
        assert "threshold" in event
        assert event["threshold"] == "0.50"

    def test_logging_failure_does_not_crash_tracker(self, tmp_path: Path) -> None:
        """Should handle logging errors gracefully (T023, T035).

        Given log directory is read-only or inaccessible
        When protection event triggers
        Then tracker should log error but not crash
        """
        log_dir = tmp_path / "readonly-dir"
        log_dir.mkdir()
        log_dir.chmod(0o444)  # Read-only

        config = ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.50"))
        perf_tracker = Mock()
        tracker = DailyProfitTracker(
            config=config,
            performance_tracker=perf_tracker,
            state_file=tmp_path / "test-state.json",
            log_dir=log_dir,
        )

        # Trigger protection (should not crash even if logging fails)
        perf_tracker.get_summary.return_value = Mock(realized_pnl=Decimal("600"), unrealized_pnl=Decimal("0"))
        tracker.update_state()

        perf_tracker.get_summary.return_value = Mock(realized_pnl=Decimal("300"), unrealized_pnl=Decimal("0"))
        tracker.update_state()  # Should not raise exception

        # Verify protection still triggered
        assert tracker.is_protection_active() is True

        # Cleanup
        log_dir.chmod(0o755)
