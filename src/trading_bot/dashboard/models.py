"""
Data models for CLI dashboard.

Defines dataclasses for dashboard state, account status, position display,
performance metrics, and configuration targets.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal


@dataclass
class AccountStatus:
    """Current account snapshot."""

    buying_power: Decimal
    account_balance: Decimal
    cash_balance: Decimal
    day_trade_count: int
    last_updated: datetime


@dataclass
class PositionDisplay:
    """Position with calculated P&L for display."""

    symbol: str
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    unrealized_pl: Decimal
    unrealized_pl_pct: Decimal


@dataclass
class PerformanceMetrics:
    """Aggregated trading performance."""

    win_rate: float
    avg_risk_reward: float
    total_realized_pl: Decimal
    total_unrealized_pl: Decimal
    total_pl: Decimal
    current_streak: int
    streak_type: Literal["WIN", "LOSS", "NONE"]
    trades_today: int
    session_count: int


@dataclass
class DashboardTargets:
    """Performance targets for comparison."""

    win_rate_target: float
    daily_pl_target: Decimal
    trades_per_day_target: int
    max_drawdown_target: Decimal
    avg_risk_reward_target: float


@dataclass
class DashboardState:
    """Complete dashboard state aggregation."""

    account_status: AccountStatus
    positions: list[PositionDisplay]
    performance_metrics: PerformanceMetrics
    market_status: Literal["OPEN", "CLOSED"]
    timestamp: datetime
    targets: DashboardTargets | None = None
