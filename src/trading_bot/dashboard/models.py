"""
Dashboard data models shared across CLI and TUI interfaces.

Provides structured dataclasses for account status, positions, performance metrics,
configuration targets, and the reusable DashboardSnapshot payload consumed by both
the Rich-based CLI dashboard and future Textual TUI (FR-017).
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal


@dataclass
class AccountStatus:
    """Current account snapshot returned by AccountData service."""

    buying_power: Decimal
    account_balance: Decimal
    cash_balance: Decimal
    day_trade_count: int
    last_updated: datetime


@dataclass
class PositionDisplay:
    """Position with calculated P&L for dashboard presentation."""

    symbol: str
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    unrealized_pl: Decimal
    unrealized_pl_pct: Decimal
    last_updated: datetime


@dataclass
class PerformanceMetrics:
    """Aggregated trading performance derived from trade logs."""

    win_rate: float
    avg_risk_reward: float
    total_realized_pl: Decimal
    total_unrealized_pl: Decimal
    total_pl: Decimal
    current_streak: int
    streak_type: Literal["WIN", "LOSS", "NONE"]
    trades_today: int
    session_count: int
    max_drawdown: Decimal


@dataclass
class DashboardTargets:
    """Optional performance targets loaded from config/dashboard-targets.yaml."""

    win_rate_target: float
    daily_pl_target: Decimal
    trades_per_day_target: int
    max_drawdown_target: Decimal
    avg_risk_reward_target: float | None = None


@dataclass
class DashboardSnapshot:
    """
    Reusable dashboard payload (FR-017).

    Encapsulates the aggregated account, position, and performance data plus metadata
    about refresh timing, staleness, and operator warnings so downstream consumers can
    render or act on the same canonical snapshot.
    """

    account_status: AccountStatus
    positions: list[PositionDisplay]
    performance_metrics: PerformanceMetrics
    targets: DashboardTargets | None
    market_status: Literal["OPEN", "CLOSED"]
    generated_at: datetime
    data_age_seconds: float
    is_data_stale: bool
    warnings: list[str] = field(default_factory=list)
