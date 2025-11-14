"""
Unit tests for profit goal data models (TDD)

Tests Constitution v1.0.0 requirements:
- §Risk_Management: Profit protection thresholds validated
- §Data_Integrity: All monetary values use Decimal precision
- §Safety_First: Validation prevents invalid configurations

Feature: daily-profit-goal-ma
Task: T011 [US1] - Test ProfitGoalConfig validation
"""

import pytest
from decimal import Decimal

from src.trading_bot.profit_goal.models import (
    ProfitGoalConfig,
    DailyProfitState,
    ProfitProtectionEvent,
)


class TestProfitGoalConfigValidation:
    """Test ProfitGoalConfig dataclass validation rules (T011)."""

    # =========================================================================
    # T011 [US1]: Test ProfitGoalConfig validates target range
    # =========================================================================

    def test_valid_target_values_accepted(self) -> None:
        """Should accept valid target values in range $0-$10,000 (T011).

        Given valid target values
        When ProfitGoalConfig is created
        Then no validation error should occur

        Valid range: $0 (disabled) to $10,000 (max)
        """
        # Edge case: $0 (feature disabled)
        config = ProfitGoalConfig(target=Decimal("0"), threshold=Decimal("0.50"))
        assert config.target == Decimal("0")
        assert config.enabled is False

        # Mid-range: $500
        config = ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.50"))
        assert config.target == Decimal("500")
        assert config.enabled is True

        # Edge case: $10,000 (max)
        config = ProfitGoalConfig(target=Decimal("10000"), threshold=Decimal("0.50"))
        assert config.target == Decimal("10000")
        assert config.enabled is True

    def test_negative_target_rejected(self) -> None:
        """Should reject negative target values (T011).

        Given target < 0
        When ProfitGoalConfig is created
        Then ValueError should be raised
        """
        with pytest.raises(ValueError) as exc_info:
            ProfitGoalConfig(target=Decimal("-100"), threshold=Decimal("0.50"))

        assert "between $0 and $10,000" in str(exc_info.value)

    def test_target_above_max_rejected(self) -> None:
        """Should reject target values above $10,000 (T011).

        Given target > 10000
        When ProfitGoalConfig is created
        Then ValueError should be raised
        """
        with pytest.raises(ValueError) as exc_info:
            ProfitGoalConfig(target=Decimal("10001"), threshold=Decimal("0.50"))

        assert "between $0 and $10,000" in str(exc_info.value)

    def test_valid_threshold_values_accepted(self) -> None:
        """Should accept valid threshold values in range 0.10-0.90 (T011).

        Given valid threshold values
        When ProfitGoalConfig is created
        Then no validation error should occur

        Valid range: 0.10 (10% giveback) to 0.90 (90% giveback)
        """
        # Edge case: 0.10 (min threshold - trigger at 10% drawdown)
        config = ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.10"))
        assert config.threshold == Decimal("0.10")

        # Mid-range: 0.50 (default - 50% drawdown)
        config = ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.50"))
        assert config.threshold == Decimal("0.50")

        # Edge case: 0.90 (max threshold - trigger at 90% drawdown)
        config = ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.90"))
        assert config.threshold == Decimal("0.90")

    def test_threshold_below_min_rejected(self) -> None:
        """Should reject threshold values below 0.10 (T011).

        Given threshold < 0.10
        When ProfitGoalConfig is created
        Then ValueError should be raised
        """
        with pytest.raises(ValueError) as exc_info:
            ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.05"))

        assert "between 0.10 and 0.90" in str(exc_info.value)

    def test_threshold_above_max_rejected(self) -> None:
        """Should reject threshold values above 0.90 (T011).

        Given threshold > 0.90
        When ProfitGoalConfig is created
        Then ValueError should be raised
        """
        with pytest.raises(ValueError) as exc_info:
            ProfitGoalConfig(target=Decimal("500"), threshold=Decimal("0.95"))

        assert "between 0.10 and 0.90" in str(exc_info.value)

    def test_enabled_flag_auto_set_from_target(self) -> None:
        """Should auto-set enabled flag based on target value (T011).

        Given target value
        When ProfitGoalConfig is created
        Then enabled flag should be auto-set correctly

        Rules:
        - enabled = True if target > 0
        - enabled = False if target == 0
        """
        # Target = 0 → disabled
        config = ProfitGoalConfig(target=Decimal("0"), threshold=Decimal("0.50"))
        assert config.enabled is False

        # Target > 0 → enabled
        config = ProfitGoalConfig(target=Decimal("100"), threshold=Decimal("0.50"))
        assert config.enabled is True


class TestDailyProfitStateValidation:
    """Test DailyProfitState dataclass validation rules (foundational for US2)."""

    def test_peak_profit_must_be_gte_daily_pnl(self) -> None:
        """Should reject state where peak_profit < daily_pnl.

        Given peak_profit < daily_pnl
        When DailyProfitState is created
        Then ValueError should be raised

        Peak profit is a high-water mark - it cannot be less than current P&L.
        """
        with pytest.raises(ValueError) as exc_info:
            DailyProfitState(
                session_date="2025-10-21",
                daily_pnl=Decimal("600"),  # Current: $600
                realized_pnl=Decimal("400"),
                unrealized_pnl=Decimal("200"),
                peak_profit=Decimal("300"),  # Peak: $300 (invalid - should be >= $600)
                protection_active=False,
                last_reset="2025-10-21T04:00:00Z",
                last_updated="2025-10-21T14:30:00Z",
            )

        assert "high-water mark" in str(exc_info.value).lower()

    def test_valid_state_with_peak_equal_to_pnl(self) -> None:
        """Should accept state where peak_profit == daily_pnl.

        Given peak_profit == daily_pnl
        When DailyProfitState is created
        Then no validation error should occur
        """
        state = DailyProfitState(
            session_date="2025-10-21",
            daily_pnl=Decimal("500"),
            realized_pnl=Decimal("300"),
            unrealized_pnl=Decimal("200"),
            peak_profit=Decimal("500"),  # Peak equals current (at new peak)
            protection_active=False,
            last_reset="2025-10-21T04:00:00Z",
            last_updated="2025-10-21T14:30:00Z",
        )

        assert state.peak_profit == state.daily_pnl

    def test_valid_state_with_peak_above_pnl(self) -> None:
        """Should accept state where peak_profit > daily_pnl (drawdown scenario).

        Given peak_profit > daily_pnl
        When DailyProfitState is created
        Then no validation error should occur
        """
        state = DailyProfitState(
            session_date="2025-10-21",
            daily_pnl=Decimal("300"),  # Given back profit
            realized_pnl=Decimal("200"),
            unrealized_pnl=Decimal("100"),
            peak_profit=Decimal("600"),  # Peak was $600, now down to $300
            protection_active=True,  # Protection triggered
            last_reset="2025-10-21T04:00:00Z",
            last_updated="2025-10-21T14:35:00Z",
        )

        assert state.peak_profit > state.daily_pnl
        assert state.protection_active is True


class TestProfitProtectionEventValidation:
    """Test ProfitProtectionEvent dataclass validation rules (foundational for US3)."""

    def test_peak_profit_must_be_positive(self) -> None:
        """Should reject event where peak_profit <= 0.

        Given peak_profit <= 0
        When ProfitProtectionEvent is created
        Then ValueError should be raised

        Can't have profit giveback if there was no profit to begin with.
        """
        with pytest.raises(ValueError) as exc_info:
            ProfitProtectionEvent(
                event_id="evt-001",
                timestamp="2025-10-21T14:30:00Z",
                session_date="2025-10-21",
                peak_profit=Decimal("0"),  # No profit
                current_profit=Decimal("-100"),
                drawdown_percent=Decimal("0.50"),
                threshold=Decimal("0.50"),
                session_id="session-001",
            )

        assert "peak profit must be > 0" in str(exc_info.value).lower()

    def test_current_profit_must_be_less_than_peak(self) -> None:
        """Should reject event where current_profit >= peak_profit.

        Given current_profit >= peak_profit
        When ProfitProtectionEvent is created
        Then ValueError should be raised

        Protection event requires profit drawdown.
        """
        with pytest.raises(ValueError) as exc_info:
            ProfitProtectionEvent(
                event_id="evt-001",
                timestamp="2025-10-21T14:30:00Z",
                session_date="2025-10-21",
                peak_profit=Decimal("500"),
                current_profit=Decimal("600"),  # Current > peak (impossible)
                drawdown_percent=Decimal("0.50"),
                threshold=Decimal("0.50"),
                session_id="session-001",
            )

        assert "must be less than" in str(exc_info.value).lower()

    def test_drawdown_must_be_gte_threshold(self) -> None:
        """Should reject event where drawdown_percent < threshold.

        Given drawdown_percent < threshold
        When ProfitProtectionEvent is created
        Then ValueError should be raised

        Protection should only trigger when threshold is breached.
        """
        with pytest.raises(ValueError) as exc_info:
            ProfitProtectionEvent(
                event_id="evt-001",
                timestamp="2025-10-21T14:30:00Z",
                session_date="2025-10-21",
                peak_profit=Decimal("600"),
                current_profit=Decimal("400"),  # 33% drawdown
                drawdown_percent=Decimal("0.33"),  # Below 50% threshold
                threshold=Decimal("0.50"),
                session_id="session-001",
            )

        assert "must be >= threshold" in str(exc_info.value).lower()

    def test_valid_protection_event(self) -> None:
        """Should accept valid protection event.

        Given valid event data
        When ProfitProtectionEvent is created
        Then no validation error should occur
        """
        event = ProfitProtectionEvent(
            event_id="evt-001",
            timestamp="2025-10-21T14:30:00Z",
            session_date="2025-10-21",
            peak_profit=Decimal("600"),
            current_profit=Decimal("300"),  # 50% drawdown
            drawdown_percent=Decimal("0.50"),
            threshold=Decimal("0.50"),
            session_id="session-001",
        )

        assert event.peak_profit == Decimal("600")
        assert event.current_profit == Decimal("300")
        assert event.drawdown_percent == Decimal("0.50")

    def test_factory_method_calculates_drawdown(self) -> None:
        """Should calculate drawdown_percent in factory method.

        Given peak and current profit
        When create() factory method is called
        Then drawdown_percent should be auto-calculated
        """
        event = ProfitProtectionEvent.create(
            session_date="2025-10-21",
            peak_profit=Decimal("800"),
            current_profit=Decimal("400"),  # 50% drawdown
            threshold=Decimal("0.50"),
            session_id="session-001",
        )

        expected_drawdown = (Decimal("800") - Decimal("400")) / Decimal("800")
        assert event.drawdown_percent == expected_drawdown
        assert event.event_id is not None  # UUID generated
        assert event.timestamp is not None  # Timestamp generated
