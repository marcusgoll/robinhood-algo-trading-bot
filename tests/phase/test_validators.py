"""Phase transition validator tests (TDD RED → GREEN).

Tests the validation logic for phase transitions based on profitability gates.

Test Coverage:
- T030: ValidationResult dataclass
- T031: ExperienceToPoCValidator (20 sessions, 60% win, 1.5 R:R)
- T032: PoCToTrialValidator (30 sessions, 50 trades, 65% win, 1.8 R:R)
- T033: TrialToScalingValidator (60 sessions, 100 trades, 70% win, 2.0 R:R, <5% drawdown)
"""

import pytest
from decimal import Decimal

from src.trading_bot.phase.validators import (
    ValidationResult,
    ExperienceToPoCValidator,
    PoCToTrialValidator,
    TrialToScalingValidator,
)


class TestValidationResult:
    """Test ValidationResult dataclass (T030)."""

    def test_validation_result_all_criteria_met(self):
        """Test ValidationResult when all criteria are met."""
        result = ValidationResult(
            can_advance=True,
            criteria_met={"session_count": True, "win_rate": True, "avg_rr": True},
            missing_requirements=[],
            metrics_summary={"session_count": 25, "win_rate": "0.65", "avg_rr": "1.8"}
        )

        assert result.can_advance is True
        assert len(result.criteria_met) == 3
        assert all(result.criteria_met.values())
        assert len(result.missing_requirements) == 0
        assert result.metrics_summary["session_count"] == 25

    def test_validation_result_some_criteria_missing(self):
        """Test ValidationResult when some criteria are missing."""
        result = ValidationResult(
            can_advance=False,
            criteria_met={"session_count": True, "win_rate": False, "avg_rr": True},
            missing_requirements=["win_rate"],
            metrics_summary={"session_count": 25, "win_rate": "0.55", "avg_rr": "1.8"}
        )

        assert result.can_advance is False
        assert result.criteria_met["win_rate"] is False
        assert "win_rate" in result.missing_requirements
        assert len(result.missing_requirements) == 1

    def test_validation_result_all_criteria_missing(self):
        """Test ValidationResult when all criteria are missing."""
        result = ValidationResult(
            can_advance=False,
            criteria_met={"session_count": False, "win_rate": False, "avg_rr": False},
            missing_requirements=["session_count", "win_rate", "avg_rr"],
            metrics_summary={"session_count": 10, "win_rate": "0.40", "avg_rr": "1.0"}
        )

        assert result.can_advance is False
        assert not any(result.criteria_met.values())
        assert len(result.missing_requirements) == 3


class TestExperienceToPoCValidator:
    """Test Experience → Proof of Concept transition validator (T031)."""

    def test_experience_to_poc_all_criteria_met(self):
        """Test Experience → PoC when all criteria are met."""
        validator = ExperienceToPoCValidator()
        result = validator.validate(
            session_count=20,
            win_rate=Decimal("0.60"),
            avg_rr=Decimal("1.5")
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())
        assert len(result.missing_requirements) == 0
        assert result.metrics_summary["session_count"] == 20
        assert result.metrics_summary["win_rate"] == "0.60"
        assert result.metrics_summary["avg_rr"] == "1.5"

    def test_experience_to_poc_exceed_criteria(self):
        """Test Experience → PoC when exceeding minimum criteria."""
        validator = ExperienceToPoCValidator()
        result = validator.validate(
            session_count=30,
            win_rate=Decimal("0.75"),
            avg_rr=Decimal("2.0")
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())
        assert len(result.missing_requirements) == 0

    def test_experience_to_poc_insufficient_sessions(self):
        """Test Experience → PoC with insufficient sessions."""
        validator = ExperienceToPoCValidator()
        result = validator.validate(
            session_count=15,
            win_rate=Decimal("0.65"),
            avg_rr=Decimal("1.6")
        )

        assert result.can_advance is False
        assert result.criteria_met["session_count"] is False
        assert "session_count" in result.missing_requirements

    def test_experience_to_poc_low_win_rate(self):
        """Test Experience → PoC with insufficient win rate."""
        validator = ExperienceToPoCValidator()
        result = validator.validate(
            session_count=25,
            win_rate=Decimal("0.55"),
            avg_rr=Decimal("1.7")
        )

        assert result.can_advance is False
        assert result.criteria_met["win_rate"] is False
        assert "win_rate" in result.missing_requirements

    def test_experience_to_poc_low_rr(self):
        """Test Experience → PoC with insufficient risk-reward ratio."""
        validator = ExperienceToPoCValidator()
        result = validator.validate(
            session_count=25,
            win_rate=Decimal("0.65"),
            avg_rr=Decimal("1.2")
        )

        assert result.can_advance is False
        assert result.criteria_met["avg_rr"] is False
        assert "avg_rr" in result.missing_requirements

    def test_experience_to_poc_multiple_criteria_missing(self):
        """Test Experience → PoC with multiple criteria missing."""
        validator = ExperienceToPoCValidator()
        result = validator.validate(
            session_count=10,
            win_rate=Decimal("0.50"),
            avg_rr=Decimal("1.0")
        )

        assert result.can_advance is False
        assert not any(result.criteria_met.values())
        assert len(result.missing_requirements) == 3
        assert "session_count" in result.missing_requirements
        assert "win_rate" in result.missing_requirements
        assert "avg_rr" in result.missing_requirements

    def test_experience_to_poc_exact_boundary_values(self):
        """Test Experience → PoC with exact boundary values."""
        validator = ExperienceToPoCValidator()
        result = validator.validate(
            session_count=20,  # Exactly 20
            win_rate=Decimal("0.60"),  # Exactly 60%
            avg_rr=Decimal("1.5")  # Exactly 1.5
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())


class TestPoCToTrialValidator:
    """Test Proof of Concept → Real Money Trial transition validator (T032)."""

    def test_poc_to_trial_all_criteria_met(self):
        """Test PoC → Trial when all criteria are met."""
        validator = PoCToTrialValidator()
        result = validator.validate(
            session_count=30,
            trade_count=50,
            win_rate=Decimal("0.65"),
            avg_rr=Decimal("1.8")
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())
        assert len(result.missing_requirements) == 0
        assert result.metrics_summary["session_count"] == 30
        assert result.metrics_summary["trade_count"] == 50
        assert result.metrics_summary["win_rate"] == "0.65"
        assert result.metrics_summary["avg_rr"] == "1.8"

    def test_poc_to_trial_exceed_criteria(self):
        """Test PoC → Trial when exceeding minimum criteria."""
        validator = PoCToTrialValidator()
        result = validator.validate(
            session_count=45,
            trade_count=75,
            win_rate=Decimal("0.75"),
            avg_rr=Decimal("2.2")
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())

    def test_poc_to_trial_insufficient_sessions(self):
        """Test PoC → Trial with insufficient sessions."""
        validator = PoCToTrialValidator()
        result = validator.validate(
            session_count=20,
            trade_count=60,
            win_rate=Decimal("0.70"),
            avg_rr=Decimal("2.0")
        )

        assert result.can_advance is False
        assert result.criteria_met["session_count"] is False
        assert "session_count" in result.missing_requirements

    def test_poc_to_trial_insufficient_trades(self):
        """Test PoC → Trial with insufficient trades."""
        validator = PoCToTrialValidator()
        result = validator.validate(
            session_count=35,
            trade_count=40,
            win_rate=Decimal("0.70"),
            avg_rr=Decimal("2.0")
        )

        assert result.can_advance is False
        assert result.criteria_met["trade_count"] is False
        assert "trade_count" in result.missing_requirements

    def test_poc_to_trial_low_win_rate(self):
        """Test PoC → Trial with insufficient win rate."""
        validator = PoCToTrialValidator()
        result = validator.validate(
            session_count=35,
            trade_count=60,
            win_rate=Decimal("0.60"),
            avg_rr=Decimal("2.0")
        )

        assert result.can_advance is False
        assert result.criteria_met["win_rate"] is False
        assert "win_rate" in result.missing_requirements

    def test_poc_to_trial_low_rr(self):
        """Test PoC → Trial with insufficient risk-reward ratio."""
        validator = PoCToTrialValidator()
        result = validator.validate(
            session_count=35,
            trade_count=60,
            win_rate=Decimal("0.70"),
            avg_rr=Decimal("1.5")
        )

        assert result.can_advance is False
        assert result.criteria_met["avg_rr"] is False
        assert "avg_rr" in result.missing_requirements

    def test_poc_to_trial_exact_boundary_values(self):
        """Test PoC → Trial with exact boundary values."""
        validator = PoCToTrialValidator()
        result = validator.validate(
            session_count=30,  # Exactly 30
            trade_count=50,  # Exactly 50
            win_rate=Decimal("0.65"),  # Exactly 65%
            avg_rr=Decimal("1.8")  # Exactly 1.8
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())


class TestTrialToScalingValidator:
    """Test Real Money Trial → Scaling transition validator (T033)."""

    def test_trial_to_scaling_all_criteria_met(self):
        """Test Trial → Scaling when all criteria are met."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=60,
            trade_count=100,
            win_rate=Decimal("0.70"),
            avg_rr=Decimal("2.0"),
            max_drawdown=Decimal("0.04")
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())
        assert len(result.missing_requirements) == 0
        assert result.metrics_summary["session_count"] == 60
        assert result.metrics_summary["trade_count"] == 100
        assert result.metrics_summary["win_rate"] == "0.70"
        assert result.metrics_summary["avg_rr"] == "2.0"
        assert result.metrics_summary["max_drawdown"] == "0.04"

    def test_trial_to_scaling_exceed_criteria(self):
        """Test Trial → Scaling when exceeding minimum criteria."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=80,
            trade_count=150,
            win_rate=Decimal("0.80"),
            avg_rr=Decimal("2.5"),
            max_drawdown=Decimal("0.02")
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())

    def test_trial_to_scaling_insufficient_sessions(self):
        """Test Trial → Scaling with insufficient sessions."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=50,
            trade_count=110,
            win_rate=Decimal("0.75"),
            avg_rr=Decimal("2.2"),
            max_drawdown=Decimal("0.03")
        )

        assert result.can_advance is False
        assert result.criteria_met["session_count"] is False
        assert "session_count" in result.missing_requirements

    def test_trial_to_scaling_insufficient_trades(self):
        """Test Trial → Scaling with insufficient trades."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=65,
            trade_count=90,
            win_rate=Decimal("0.75"),
            avg_rr=Decimal("2.2"),
            max_drawdown=Decimal("0.03")
        )

        assert result.can_advance is False
        assert result.criteria_met["trade_count"] is False
        assert "trade_count" in result.missing_requirements

    def test_trial_to_scaling_low_win_rate(self):
        """Test Trial → Scaling with insufficient win rate."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=65,
            trade_count=110,
            win_rate=Decimal("0.65"),
            avg_rr=Decimal("2.2"),
            max_drawdown=Decimal("0.03")
        )

        assert result.can_advance is False
        assert result.criteria_met["win_rate"] is False
        assert "win_rate" in result.missing_requirements

    def test_trial_to_scaling_low_rr(self):
        """Test Trial → Scaling with insufficient risk-reward ratio."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=65,
            trade_count=110,
            win_rate=Decimal("0.75"),
            avg_rr=Decimal("1.8"),
            max_drawdown=Decimal("0.03")
        )

        assert result.can_advance is False
        assert result.criteria_met["avg_rr"] is False
        assert "avg_rr" in result.missing_requirements

    def test_trial_to_scaling_high_drawdown(self):
        """Test Trial → Scaling with excessive drawdown."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=65,
            trade_count=110,
            win_rate=Decimal("0.75"),
            avg_rr=Decimal("2.2"),
            max_drawdown=Decimal("0.06")
        )

        assert result.can_advance is False
        assert result.criteria_met["max_drawdown"] is False
        assert "max_drawdown" in result.missing_requirements

    def test_trial_to_scaling_exact_boundary_values(self):
        """Test Trial → Scaling with exact boundary values."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=60,  # Exactly 60
            trade_count=100,  # Exactly 100
            win_rate=Decimal("0.70"),  # Exactly 70%
            avg_rr=Decimal("2.0"),  # Exactly 2.0
            max_drawdown=Decimal("0.049")  # Just under 5%
        )

        assert result.can_advance is True
        assert all(result.criteria_met.values())

    def test_trial_to_scaling_drawdown_at_boundary(self):
        """Test Trial → Scaling with drawdown at exactly 5%."""
        validator = TrialToScalingValidator()
        result = validator.validate(
            session_count=65,
            trade_count=110,
            win_rate=Decimal("0.75"),
            avg_rr=Decimal("2.2"),
            max_drawdown=Decimal("0.05")  # Exactly 5%
        )

        # Should fail because max_drawdown < 0.05 (strictly less than)
        assert result.can_advance is False
        assert result.criteria_met["max_drawdown"] is False
        assert "max_drawdown" in result.missing_requirements
