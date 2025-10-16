"""Core risk management orchestration."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from .config import RiskManagementConfig
from .models import PositionPlan, RiskManagementEnvelope


class AccountProvider(Protocol):
    """Interface for retrieving account information."""

    def get_buying_power(self) -> Decimal:
        """Return available buying power."""
        ...

    def get_portfolio_value(self) -> Decimal:
        """Return total portfolio value."""
        ...


class RiskManager:
    """Manages position sizing, stop-loss calculation, and target monitoring."""

    def __init__(self, config: RiskManagementConfig | None = None) -> None:
        """Initialize risk manager with configuration."""
        self.config = config or RiskManagementConfig()

    def create_position_plan(
        self,
        symbol: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        target_price: Decimal,
        account_value: Decimal,
    ) -> PositionPlan:
        """Create a risk-adjusted position plan.

        Args:
            symbol: Trading symbol
            entry_price: Intended entry price
            stop_loss: Initial stop-loss price
            target_price: Price target
            account_value: Current account value for position sizing

        Returns:
            PositionPlan with calculated position size and risk metrics
        """
        # Placeholder implementation - will be filled in implementation tasks
        risk_amount = account_value * Decimal(self.config.max_risk_per_trade_pct / 100)
        risk_per_share = abs(entry_price - stop_loss)
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0

        reward_per_share = abs(target_price - entry_price)
        risk_reward_ratio = (
            float(reward_per_share / risk_per_share) if risk_per_share > 0 else 0.0
        )

        return PositionPlan(
            symbol=symbol,
            entry_price=entry_price,
            initial_stop_loss=stop_loss,
            target_price=target_price,
            position_size=position_size,
            risk_amount=risk_amount,
            risk_reward_ratio=risk_reward_ratio,
        )

    def log_action(
        self,
        action_type: str,
        symbol: str,
        details: dict | None = None,
        position_plan: PositionPlan | None = None,
    ) -> RiskManagementEnvelope:
        """Create an audit record for risk management actions."""
        return RiskManagementEnvelope(
            action_type=action_type,
            symbol=symbol,
            timestamp=datetime.now(),
            details=details or {},
            position_plan=position_plan,
        )
