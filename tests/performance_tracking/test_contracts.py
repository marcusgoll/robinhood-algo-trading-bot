"""
Tests for schema validation and contract compliance.

Test T015 - RED phase
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from trading_bot.performance.models import PerformanceSummary, AlertEvent


class TestSchemaValidation:
    """T015: Schema validation of generated JSON summaries."""

    def test_summary_json_validates_against_schema(self):
        """
        Generated summary JSON validates against schema.

        Expected behavior (RED phase):
        - Create summary instance
        - Serialize to JSON
        - Validate against performance-summary.schema.json
        - Pass jsonschema validation
        """
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        # Load schema
        schema_path = Path("specs/performance-tracking/artifacts/performance-summary.schema.json")
        if not schema_path.exists():
            pytest.skip("Schema file not found")

        with open(schema_path) as f:
            schema = json.load(f)

        # Create summary
        summary = PerformanceSummary(
            window="daily",
            start_date=datetime(2025, 10, 15, 0, 0, 0),
            end_date=datetime(2025, 10, 15, 23, 59, 59),
            total_trades=12,
            total_wins=8,
            total_losses=4,
            win_rate=Decimal("0.6667"),
            current_streak=3,
            streak_type="win",
            avg_profit_per_win=Decimal("125.50"),
            avg_loss_per_loss=Decimal("-45.25"),
            avg_risk_reward_ratio=Decimal("2.77"),
            realized_pnl=Decimal("823.00"),
            unrealized_pnl=Decimal("0.00"),
            alert_status="OK",
            generated_at=datetime(2025, 10, 15, 16, 0, 0),
        )

        # Serialize (implementation pending)
        from trading_bot.performance.tracker import PerformanceTracker

        tracker = PerformanceTracker()
        json_data = tracker.serialize_summary(summary)

        # Validate
        jsonschema.validate(instance=json_data, schema=schema)

        pytest.fail("T015: RED phase - test should fail until GREEN implementation")

    def test_alert_json_validates_against_schema(self):
        """
        Generated alert JSON validates against schema.

        Expected behavior (RED phase):
        - Create alert event
        - Serialize to JSON
        - Validate against performance-alert.schema.json
        """
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        schema_path = Path("specs/performance-tracking/artifacts/performance-alert.schema.json")
        if not schema_path.exists():
            pytest.skip("Schema file not found")

        with open(schema_path) as f:
            schema = json.load(f)

        alert = AlertEvent(
            id="alert-12345678-1234-1234-1234-123456789abc",
            window="rolling",
            metric="win_rate",
            actual=Decimal("0.55"),
            target=Decimal("0.60"),
            severity="WARN",
            raised_at=datetime(2025, 10, 15, 16, 5, 0),
            acknowledged_at=None,
        )

        # Serialize (implementation pending)
        from trading_bot.performance.alerts import AlertEvaluator

        evaluator = AlertEvaluator()
        json_data = evaluator.serialize_alert(alert)

        # Validate
        jsonschema.validate(instance=json_data, schema=schema)

        pytest.fail("T015: RED phase - test should fail until GREEN implementation")
