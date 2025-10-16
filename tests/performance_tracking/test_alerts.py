"""
Tests for AlertEvaluator service.

Tests T008, T009 - RED phase
"""

import pytest
from datetime import datetime
from decimal import Decimal

from trading_bot.performance.alerts import AlertEvaluator
from trading_bot.performance.models import PerformanceSummary


class TestAlertEvaluatorWinRateBreach:
    """T008: Alert evaluator triggers win rate breach."""

    def test_win_rate_below_target_triggers_alert(self, caplog):
        """
        Win rate below target emits WARN alert.

        Expected behavior (RED phase):
        - Summary with win_rate < target
        - Alert event emitted
        - WARN log entry created
        - JSONL structure matches schema
        """
        evaluator = AlertEvaluator()

        summary = PerformanceSummary(
            window="rolling",
            start_date=datetime(2025, 10, 1),
            end_date=datetime(2025, 10, 15),
            total_trades=20,
            total_wins=11,
            total_losses=9,
            win_rate=Decimal("0.55"),  # Below 60% target
            current_streak=1,
            streak_type="win",
            avg_profit_per_win=Decimal("100.00"),
            avg_loss_per_loss=Decimal("-50.00"),
            avg_risk_reward_ratio=Decimal("2.0"),
            realized_pnl=Decimal("650.00"),
            unrealized_pnl=Decimal("0.00"),
            alert_status="OK",
            generated_at=datetime(2025, 10, 15, 16, 0, 0),
        )

        alerts = evaluator.evaluate(summary)

        assert len(alerts) > 0
        assert alerts[0].metric == "win_rate"
        assert alerts[0].severity == "WARN"
        assert "WARN" in caplog.text or "warn" in caplog.text.lower()


class TestAlertEvaluatorNoAlertAboveTarget:
    """T009: Alert evaluator suppresses when above targets."""

    def test_metrics_above_targets_no_alert(self):
        """
        No alerts when all metrics meet or exceed targets.

        Expected behavior (RED phase):
        - Summary with all metrics above targets
        - No alert events emitted
        - Verify FR-006 guardrail
        """
        evaluator = AlertEvaluator()

        summary = PerformanceSummary(
            window="rolling",
            start_date=datetime(2025, 10, 1),
            end_date=datetime(2025, 10, 15),
            total_trades=20,
            total_wins=14,
            total_losses=6,
            win_rate=Decimal("0.70"),  # Above 60% target
            current_streak=3,
            streak_type="win",
            avg_profit_per_win=Decimal("150.00"),
            avg_loss_per_loss=Decimal("-50.00"),
            avg_risk_reward_ratio=Decimal("3.0"),  # Above 1.0 target
            realized_pnl=Decimal("1800.00"),
            unrealized_pnl=Decimal("0.00"),
            alert_status="OK",
            generated_at=datetime(2025, 10, 15, 16, 0, 0),
        )

        alerts = evaluator.evaluate(summary)

        assert len(alerts) == 0
