"""Tests for PhaseManager orchestration service.

TDD RED phase: Write failing tests for PhaseManager.
- validate_transition() tests
- advance_phase() tests
- Error handling tests
- TradeLimiter integration tests (T082)

Based on specs/022-pos-scale-progress/contracts/phase-api.yaml
Tasks: T040-T041, T082
"""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from trading_bot.phase.models import Phase, PhaseTransition
from trading_bot.phase.validators import ValidationResult
from trading_bot.phase.manager import PhaseManager, PhaseValidationError
from trading_bot.phase.trade_limiter import TradeLimiter, TradeLimitExceeded
from trading_bot.config import Config


class TestPhaseManagerValidateTransition:
    """Test PhaseManager.validate_transition() method."""

    def test_experience_to_poc_criteria_met(self):
        """Should return can_advance=True when criteria met."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Mock metrics (will be passed from PerformanceTracker in real impl)
        manager._metrics = {
            "session_count": 20,
            "win_rate": Decimal("0.60"),
            "avg_rr": Decimal("1.5")
        }

        # Act
        result = manager.validate_transition(Phase.PROOF_OF_CONCEPT)

        # Assert
        assert result.can_advance is True
        assert result.criteria_met["session_count"] is True
        assert result.criteria_met["win_rate"] is True
        assert result.criteria_met["avg_rr"] is True
        assert len(result.missing_requirements) == 0

    def test_experience_to_poc_criteria_not_met(self):
        """Should return can_advance=False when criteria not met."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Mock metrics - only 15 sessions (need 20)
        manager._metrics = {
            "session_count": 15,
            "win_rate": Decimal("0.58"),
            "avg_rr": Decimal("1.4")
        }

        # Act
        result = manager.validate_transition(Phase.PROOF_OF_CONCEPT)

        # Assert
        assert result.can_advance is False
        assert "session_count" in result.missing_requirements
        assert "win_rate" in result.missing_requirements
        assert "avg_rr" in result.missing_requirements

    def test_poc_to_trial_criteria_met(self):
        """Should validate PoC → Trial transition with all criteria met."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 30,
            "trade_count": 50,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8")
        }

        # Act
        result = manager.validate_transition(Phase.REAL_MONEY_TRIAL)

        # Assert
        assert result.can_advance is True
        assert all(result.criteria_met.values())

    def test_trial_to_scaling_criteria_met(self):
        """Should validate Trial → Scaling transition with all criteria met."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="trial"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 60,
            "trade_count": 100,
            "win_rate": Decimal("0.70"),
            "avg_rr": Decimal("2.0"),
            "max_drawdown": Decimal("0.04")
        }

        # Act
        result = manager.validate_transition(Phase.SCALING)

        # Assert
        assert result.can_advance is True
        assert all(result.criteria_met.values())

    def test_non_sequential_transition_raises_error(self):
        """Should raise ValueError for non-sequential phase transition."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Act & Assert
        with pytest.raises(ValueError, match="Non-sequential transition"):
            manager.validate_transition(Phase.SCALING)

    def test_invalid_validator_raises_error(self):
        """Should raise ValueError if no validator exists for transition."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act & Assert - trying to go backwards (non-sequential)
        # This will hit the sequential check first before checking for validator
        with pytest.raises(ValueError, match="Non-sequential transition"):
            manager.validate_transition(Phase.EXPERIENCE)


class TestPhaseManagerAdvancePhase:
    """Test PhaseManager.advance_phase() method."""

    def test_advance_with_validation_pass(self):
        """Should advance phase when validation passes."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 20,
            "win_rate": Decimal("0.60"),
            "avg_rr": Decimal("1.5")
        }

        # Act
        transition = manager.advance_phase(Phase.PROOF_OF_CONCEPT)

        # Assert
        assert isinstance(transition, PhaseTransition)
        assert transition.from_phase == Phase.EXPERIENCE
        assert transition.to_phase == Phase.PROOF_OF_CONCEPT
        assert transition.validation_passed is True
        assert transition.trigger == "auto"
        assert UUID(transition.transition_id)  # Valid UUID
        assert isinstance(transition.timestamp, datetime)

        # Config should be updated
        assert config.current_phase == "proof"

    def test_advance_with_validation_fail_raises_error(self):
        """Should raise PhaseValidationError when validation fails."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 10,  # Not enough sessions
            "win_rate": Decimal("0.50"),
            "avg_rr": Decimal("1.2")
        }

        # Act & Assert
        with pytest.raises(PhaseValidationError) as exc_info:
            manager.advance_phase(Phase.PROOF_OF_CONCEPT)

        # Check error details
        error = exc_info.value
        assert error.result.can_advance is False
        assert len(error.result.missing_requirements) > 0
        assert "Phase validation failed" in str(error)

    def test_advance_with_force_bypasses_validation(self):
        """Should bypass validation when force=True."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Bad metrics that would fail validation
        manager._metrics = {
            "session_count": 5,
            "win_rate": Decimal("0.40"),
            "avg_rr": Decimal("1.0")
        }

        # Act
        transition = manager.advance_phase(Phase.PROOF_OF_CONCEPT, force=True)

        # Assert
        assert transition.validation_passed is True  # Force passed
        assert transition.trigger == "manual"
        assert transition.override_password_used is True
        assert config.current_phase == "proof"

    def test_advance_phase_creates_transition_record(self):
        """Should create complete PhaseTransition record."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)

        manager._metrics = {
            "session_count": 30,
            "trade_count": 50,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.8")
        }

        # Act
        transition = manager.advance_phase(Phase.REAL_MONEY_TRIAL)

        # Assert - verify all transition fields
        assert transition.transition_id is not None
        assert transition.timestamp.tzinfo == timezone.utc
        assert transition.from_phase == Phase.PROOF_OF_CONCEPT
        assert transition.to_phase == Phase.REAL_MONEY_TRIAL
        assert transition.trigger == "auto"
        assert transition.validation_passed is True
        assert isinstance(transition.metrics_snapshot, dict)

    def test_advance_phase_non_sequential_fails(self):
        """Should fail for non-sequential phase advancement."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Act & Assert
        with pytest.raises(ValueError, match="Non-sequential transition"):
            manager.advance_phase(Phase.SCALING)


class TestPhaseValidationError:
    """Test PhaseValidationError exception."""

    def test_error_message_includes_missing_requirements(self):
        """Should format error message with missing requirements."""
        # Arrange
        result = ValidationResult(
            can_advance=False,
            criteria_met={
                "session_count": False,
                "win_rate": False,
                "avg_rr": True
            },
            missing_requirements=["session_count", "win_rate"],
            metrics_summary={}
        )

        # Act
        error = PhaseValidationError(result)

        # Assert
        assert "Phase validation failed" in str(error)
        assert "session_count" in str(error)
        assert "win_rate" in str(error)
        assert error.result == result


class TestTradeLimiterIntegration:
    """Test TradeLimiter integration with PhaseManager (T082)."""

    def test_enforce_trade_limit_poc_first_trade_allowed(self):
        """PoC phase: First trade should be allowed."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)
        trade_date = date(2025, 1, 15)

        # Act & Assert - should not raise exception
        manager.enforce_trade_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        # Verify counter incremented
        assert manager.trade_limiter._trade_counts[trade_date] == 1

    def test_enforce_trade_limit_poc_second_trade_blocked(self):
        """PoC phase: Second trade should raise TradeLimitExceeded."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)
        trade_date = date(2025, 1, 15)

        # First trade allowed
        manager.enforce_trade_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        # Act & Assert - second trade should fail
        with pytest.raises(TradeLimitExceeded) as exc_info:
            manager.enforce_trade_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        # Verify exception details
        exc = exc_info.value
        assert exc.phase == Phase.PROOF_OF_CONCEPT
        assert exc.limit == 1

    def test_enforce_trade_limit_experience_phase_unlimited(self):
        """Experience phase: Multiple trades should be allowed."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)
        trade_date = date(2025, 1, 15)

        # Act - execute 5 trades
        for _ in range(5):
            manager.enforce_trade_limit(Phase.EXPERIENCE, trade_date)

        # Assert - no exceptions raised, no counter tracked
        assert trade_date not in manager.trade_limiter._trade_counts

    def test_enforce_trade_limit_trial_phase_unlimited(self):
        """Trial phase: Multiple trades should be allowed."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="trial"
        )
        manager = PhaseManager(config)
        trade_date = date(2025, 1, 15)

        # Act - execute 5 trades
        for _ in range(5):
            manager.enforce_trade_limit(Phase.REAL_MONEY_TRIAL, trade_date)

        # Assert - no exceptions raised, no counter tracked
        assert trade_date not in manager.trade_limiter._trade_counts

    def test_enforce_trade_limit_scaling_phase_unlimited(self):
        """Scaling phase: Multiple trades should be allowed."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)
        trade_date = date(2025, 1, 15)

        # Act - execute 5 trades
        for _ in range(5):
            manager.enforce_trade_limit(Phase.SCALING, trade_date)

        # Assert - no exceptions raised, no counter tracked
        assert trade_date not in manager.trade_limiter._trade_counts

    def test_enforce_trade_limit_delegates_to_trade_limiter(self):
        """Should delegate limit checking to TradeLimiter instance."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)
        trade_date = date(2025, 1, 15)

        # Verify TradeLimiter instance exists
        assert manager.trade_limiter is not None
        assert isinstance(manager.trade_limiter, TradeLimiter)

        # Act - use enforce_trade_limit
        manager.enforce_trade_limit(Phase.PROOF_OF_CONCEPT, trade_date)

        # Assert - counter should be in TradeLimiter instance
        assert manager.trade_limiter._trade_counts[trade_date] == 1


class TestSessionMetrics:
    """Test session metrics calculation (T090-T097, US3)."""

    def test_calculate_session_metrics_returns_session_metrics(self):
        """Should return SessionMetrics with correct fields (T090)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)
        session_date = date(2025, 1, 15)

        # Act
        metrics = manager.calculate_session_metrics(session_date)

        # Assert - verify SessionMetrics structure
        from trading_bot.phase.models import SessionMetrics
        assert isinstance(metrics, SessionMetrics)
        assert metrics.session_date == session_date
        assert metrics.phase == "proof"
        assert isinstance(metrics.trades_executed, int)
        assert isinstance(metrics.total_wins, int)
        assert isinstance(metrics.total_losses, int)
        assert isinstance(metrics.win_rate, Decimal)
        assert isinstance(metrics.average_rr, Decimal)
        assert isinstance(metrics.total_pnl, Decimal)
        assert isinstance(metrics.position_sizes, list)
        assert isinstance(metrics.circuit_breaker_trips, int)
        assert isinstance(metrics.created_at, datetime)

    def test_calculate_session_metrics_decimal_precision(self):
        """Should maintain Decimal precision for financial values (T091)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="trial"
        )
        manager = PhaseManager(config)
        session_date = date(2025, 1, 15)

        # Act
        metrics = manager.calculate_session_metrics(session_date)

        # Assert - verify Decimal types (no float conversion)
        assert isinstance(metrics.win_rate, Decimal)
        assert isinstance(metrics.average_rr, Decimal)
        assert isinstance(metrics.total_pnl, Decimal)

        # Verify position_sizes are all Decimals
        for size in metrics.position_sizes:
            assert isinstance(size, Decimal)

    def test_calculate_session_metrics_utc_timestamp(self):
        """Should use UTC timezone for created_at timestamp (T091)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)
        session_date = date(2025, 1, 15)

        # Act
        metrics = manager.calculate_session_metrics(session_date)

        # Assert - verify UTC timezone
        assert metrics.created_at.tzinfo == timezone.utc

    def test_validate_transition_with_rolling_window_10_sessions(self):
        """Should validate using last 10 sessions when rolling_window=10 (T092)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Mock metrics with rolling_window parameter
        manager._metrics = {
            "session_count": 10,  # Last 10 sessions
            "win_rate": Decimal("0.62"),
            "avg_rr": Decimal("1.6"),
            "rolling_window": 10
        }

        # Act
        result = manager.validate_transition(
            Phase.PROOF_OF_CONCEPT,
            rolling_window=10
        )

        # Assert - validation should fail (need 20 sessions minimum)
        # But criteria should still check the 10 sessions provided
        assert result.can_advance is False
        assert "session_count" in result.missing_requirements

    def test_validate_transition_with_rolling_window_20_sessions(self):
        """Should validate using last 20 sessions when rolling_window=20 (T092)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Mock metrics - last 20 sessions meet criteria
        manager._metrics = {
            "session_count": 20,
            "win_rate": Decimal("0.65"),
            "avg_rr": Decimal("1.7"),
            "rolling_window": 20
        }

        # Act
        result = manager.validate_transition(
            Phase.PROOF_OF_CONCEPT,
            rolling_window=20
        )

        # Assert
        assert result.can_advance is True
        assert all(result.criteria_met.values())

    def test_validate_transition_with_rolling_window_50_sessions(self):
        """Should validate using last 50 sessions when rolling_window=50 (T093)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)

        # Mock metrics - last 50 sessions for PoC -> Trial
        manager._metrics = {
            "session_count": 50,
            "trade_count": 100,
            "win_rate": Decimal("0.68"),
            "avg_rr": Decimal("1.9"),
            "rolling_window": 50
        }

        # Act
        result = manager.validate_transition(
            Phase.REAL_MONEY_TRIAL,
            rolling_window=50
        )

        # Assert
        assert result.can_advance is True

    def test_validate_transition_with_rolling_window_100_sessions(self):
        """Should validate using last 100 sessions when rolling_window=100 (T094)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="trial"
        )
        manager = PhaseManager(config)

        # Mock metrics - last 100 sessions for Trial -> Scaling
        manager._metrics = {
            "session_count": 100,
            "trade_count": 200,
            "win_rate": Decimal("0.72"),
            "avg_rr": Decimal("2.1"),
            "max_drawdown": Decimal("0.03"),
            "rolling_window": 100
        }

        # Act
        result = manager.validate_transition(
            Phase.SCALING,
            rolling_window=100
        )

        # Assert
        assert result.can_advance is True

    def test_rolling_window_edge_case_fewer_sessions_than_window(self):
        """Should use all available sessions when history < window size (T094)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Mock: Only 5 sessions available, but window requests 10
        manager._metrics = {
            "session_count": 5,  # Only 5 available
            "win_rate": Decimal("0.70"),
            "avg_rr": Decimal("1.8"),
            "rolling_window": 10  # Requested 10, got 5
        }

        # Act
        result = manager.validate_transition(
            Phase.PROOF_OF_CONCEPT,
            rolling_window=10
        )

        # Assert - should fail because need minimum 20 sessions
        assert result.can_advance is False
        assert "session_count" in result.missing_requirements


class TestPositionSizing:
    """Test graduated position sizing (US4, T110-T116)."""

    def test_experience_phase_zero_position_size(self):
        """Experience phase should return $0 (paper trading) (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="experience"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(Phase.EXPERIENCE)

        # Assert
        assert size == Decimal("0")

    def test_poc_phase_fixed_100_position_size(self):
        """PoC phase should return fixed $100 (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="proof"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(Phase.PROOF_OF_CONCEPT)

        # Assert
        assert size == Decimal("100")

    def test_trial_phase_fixed_200_position_size(self):
        """Trial phase should return fixed $200 (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="trial"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(Phase.REAL_MONEY_TRIAL)

        # Assert
        assert size == Decimal("200")

    def test_scaling_phase_base_position_size(self):
        """Scaling phase should start at $200 base (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(Phase.SCALING)

        # Assert
        assert size == Decimal("200")

    def test_scaling_phase_5_consecutive_wins_increases_to_300(self):
        """Scaling phase: 5 consecutive wins should add $100 to base (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(
            Phase.SCALING,
            consecutive_wins=5
        )

        # Assert
        assert size == Decimal("300")  # $200 base + $100 for 5 wins

    def test_scaling_phase_10_consecutive_wins_increases_to_400(self):
        """Scaling phase: 10 consecutive wins should add $200 to base (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(
            Phase.SCALING,
            consecutive_wins=10
        )

        # Assert
        assert size == Decimal("400")  # $200 base + $200 (2 * $100)

    def test_scaling_phase_70_percent_win_rate_adds_200(self):
        """Scaling phase: 70% win rate should add $200 bonus (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(
            Phase.SCALING,
            consecutive_wins=0,
            rolling_win_rate=Decimal("0.70")
        )

        # Assert
        assert size == Decimal("400")  # $200 base + $200 for 70% win rate

    def test_scaling_phase_combined_wins_and_win_rate(self):
        """Scaling phase: Combined 5 wins + 70% win rate (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(
            Phase.SCALING,
            consecutive_wins=5,
            rolling_win_rate=Decimal("0.72")
        )

        # Assert
        assert size == Decimal("500")  # $200 base + $100 (5 wins) + $200 (70% rate)

    def test_scaling_phase_10_wins_and_win_rate(self):
        """Scaling phase: Combined 10 wins + 70% win rate (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act
        size = manager.get_position_size(
            Phase.SCALING,
            consecutive_wins=10,
            rolling_win_rate=Decimal("0.72")
        )

        # Assert
        assert size == Decimal("600")  # $200 base + $200 (10 wins) + $200 (70% rate)

    def test_scaling_phase_max_cap_2000(self):
        """Scaling phase: Position size should cap at $2,000 (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act - 100 consecutive wins would exceed cap
        size = manager.get_position_size(
            Phase.SCALING,
            consecutive_wins=100,
            rolling_win_rate=Decimal("0.80")
        )

        # Assert
        assert size == Decimal("2000")  # Capped at max

    def test_scaling_phase_portfolio_cap_5_percent(self):
        """Scaling phase: Position size should cap at 5% of portfolio if lower than $2,000 (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act - Portfolio of $20,000, so 5% = $1,000 (lower than calculated $2,000)
        size = manager.get_position_size(
            Phase.SCALING,
            consecutive_wins=100,
            rolling_win_rate=Decimal("0.80"),
            portfolio_value=Decimal("20000")
        )

        # Assert
        assert size == Decimal("1000")  # 5% of $20,000

    def test_scaling_phase_portfolio_cap_not_applied_if_higher(self):
        """Scaling phase: Portfolio cap should not apply if higher than calculated size (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Act - Portfolio of $100,000, so 5% = $5,000 (higher than calculated $500)
        size = manager.get_position_size(
            Phase.SCALING,
            consecutive_wins=5,
            rolling_win_rate=Decimal("0.72"),
            portfolio_value=Decimal("100000")
        )

        # Assert
        assert size == Decimal("500")  # Not capped by portfolio, just by calculation

    def test_scaling_phase_incremental_wins_calculation(self):
        """Scaling phase: Each 5 wins adds $100 incrementally (T110)."""
        # Arrange
        config = Config(
            robinhood_username="test",
            robinhood_password="test",
            current_phase="scaling"
        )
        manager = PhaseManager(config)

        # Test various win counts
        test_cases = [
            (0, Decimal("200")),   # Base
            (4, Decimal("200")),   # Not enough for bonus
            (5, Decimal("300")),   # First bonus
            (9, Decimal("300")),   # Still first bonus
            (10, Decimal("400")),  # Second bonus
            (14, Decimal("400")),  # Still second bonus
            (15, Decimal("500")),  # Third bonus
        ]

        # Act & Assert
        for wins, expected in test_cases:
            size = manager.get_position_size(
                Phase.SCALING,
                consecutive_wins=wins
            )
            assert size == expected, f"Failed for {wins} wins: expected {expected}, got {size}"
