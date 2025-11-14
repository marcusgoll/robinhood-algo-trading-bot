"""
Alert evaluator for performance threshold monitoring.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import yaml

from .models import AlertEvent, PerformanceSummary

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """
    Compares performance summaries against configured targets
    and emits structured alert events when thresholds are breached.
    """

    def __init__(
        self,
        targets_file: Path = Path("config/dashboard-targets.yaml"),
        alert_log: Path = Path("logs/performance-alerts.jsonl"),
        notification_service=None
    ) -> None:
        """
        Initialize the alert evaluator.

        Args:
            targets_file: Path to targets YAML config
            alert_log: Path to alert JSONL log file
            notification_service: Optional NotificationService for Telegram alerts (T041)
        """
        self.targets_file = targets_file
        self.alert_log = alert_log
        self.notification_service = notification_service

        # Load targets
        self.targets = self._load_targets()

    def _load_targets(self) -> dict:
        """Load performance targets from YAML config."""
        if not self.targets_file.exists():
            # Default targets if file doesn't exist
            return {
                "win_rate_target": 60.0,
                "avg_risk_reward_target": 1.0,
                "daily_pl_target": 500.0,
                "max_drawdown_target": -200.0,
                "trades_per_day_target": 10,
            }

        try:
            with open(self.targets_file, encoding='utf-8') as f:
                return yaml.safe_load(f)
        except (yaml.YAMLError, OSError):
            # Return defaults if file is corrupt
            return {
                "win_rate_target": 60.0,
                "avg_risk_reward_target": 1.0,
            }

    def evaluate(self, summary: PerformanceSummary) -> list[AlertEvent]:
        """
        Evaluate a performance summary against targets.

        Args:
            summary: PerformanceSummary to evaluate

        Returns:
            List of AlertEvent objects for any breaches
        """
        alerts: list[AlertEvent] = []

        # Check win rate
        win_rate_target = self.targets.get("win_rate_target", 60.0)
        if float(summary.win_rate) < (win_rate_target / 100):  # Convert % to decimal
            alert = AlertEvent(
                id=f"alert-{uuid.uuid4()}",
                window=summary.window,
                metric="win_rate",
                actual=summary.win_rate,
                target=Decimal(str(win_rate_target / 100)),
                severity="WARN",
                raised_at=datetime.now(UTC),
            )
            alerts.append(alert)

            # Log WARN
            logger.warning(
                f"Performance alert: Win rate {summary.win_rate:.2%} below target "
                f"{win_rate_target}% for {summary.window} window"
            )

        # Check average risk-reward ratio
        rr_target = self.targets.get("avg_risk_reward_target", 1.0)
        if float(summary.avg_risk_reward_ratio) < rr_target:
            alert = AlertEvent(
                id=f"alert-{uuid.uuid4()}",
                window=summary.window,
                metric="avg_risk_reward",
                actual=summary.avg_risk_reward_ratio,
                target=Decimal(str(rr_target)),
                severity="WARN" if rr_target >= 1.0 else "CRITICAL",
                raised_at=datetime.now(UTC),
            )
            alerts.append(alert)

            # Log WARN/CRITICAL
            logger.warning(
                f"Performance alert: Avg R:R {summary.avg_risk_reward_ratio:.2f} below target "
                f"{rr_target:.2f} for {summary.window} window"
            )

        # Write alerts to JSONL
        if alerts:
            self._write_alerts(alerts)

            # T041: Send Telegram risk alert notifications (non-blocking)
            if self.notification_service and self.notification_service.is_enabled():
                try:
                    import asyncio
                    for alert in alerts:
                        alert_event = {
                            "breach_type": f"{alert.metric}_threshold",
                            "current_value": str(alert.actual),
                            "threshold": str(alert.target),
                            "timestamp": alert.raised_at.isoformat() + "Z"
                        }
                        asyncio.create_task(self.notification_service.send_risk_alert(alert_event))
                except Exception:
                    # Never block alert evaluation on notification failure
                    pass

        return alerts

    def _write_alerts(self, alerts: list[AlertEvent]) -> None:
        """Write alerts to JSONL log file."""
        # Ensure directory exists
        self.alert_log.parent.mkdir(parents=True, exist_ok=True)

        # Append to JSONL file
        with open(self.alert_log, 'a', encoding='utf-8') as f:
            for alert in alerts:
                json_data = self.serialize_alert(alert)
                f.write(json.dumps(json_data) + '\n')

    def serialize_alert(self, alert: AlertEvent) -> dict:
        """
        Serialize AlertEvent to JSON-compatible dict.

        Args:
            alert: AlertEvent to serialize

        Returns:
            Dictionary matching performance-alert.schema.json
        """
        return {
            "id": alert.id,
            "window": alert.window,
            "metric": alert.metric,
            "actual": str(alert.actual),  # Decimal to string
            "target": str(alert.target),  # Decimal to string
            "severity": alert.severity,
            "raised_at": alert.raised_at.isoformat(),
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        }
