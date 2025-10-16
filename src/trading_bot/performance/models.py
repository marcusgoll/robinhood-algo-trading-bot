"""
Performance tracking data models.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class PerformanceSummary:
    """Aggregated performance metrics for a given time window."""

    window: str  # "daily", "weekly", "monthly"
    start_date: datetime
    end_date: datetime
    total_trades: int
    total_wins: int
    total_losses: int
    win_rate: Decimal
    current_streak: int
    streak_type: str  # "win" or "loss"
    avg_profit_per_win: Decimal
    avg_loss_per_loss: Decimal
    avg_risk_reward_ratio: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    alert_status: str  # "OK", "WARN", "BREACH"
    generated_at: datetime


@dataclass
class AlertEvent:
    """Alert event structure for threshold breaches."""

    id: str
    window: str
    metric: str  # "win_rate", "avg_risk_reward", etc.
    actual: Decimal
    target: Decimal
    severity: str  # "WARN", "CRITICAL"
    raised_at: datetime
    acknowledged_at: Optional[datetime] = None
