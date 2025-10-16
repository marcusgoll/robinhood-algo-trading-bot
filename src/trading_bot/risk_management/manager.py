"""Core risk management orchestration."""

from __future__ import annotations

import json
import sys
import threading
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .config import RiskManagementConfig
from .models import PositionPlan, RiskManagementEnvelope

if TYPE_CHECKING:
    from src.trading_bot.order_management.manager import OrderManager


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

    def __init__(
        self,
        config: RiskManagementConfig | None = None,
        order_manager: OrderManager | None = None,
    ) -> None:
        """Initialize risk manager with configuration and optional order manager.

        Args:
            config: Risk management configuration
            order_manager: Order management dependency for order placement
        """
        self.config = config or RiskManagementConfig.default()
        self.order_manager = order_manager

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

    def place_trade_with_risk_management(
        self, plan: PositionPlan, symbol: str
    ) -> RiskManagementEnvelope:
        """Place entry, stop, and target orders for a position plan.

        Args:
            plan: Position plan with entry/stop/target prices and quantity
            symbol: Trading symbol

        Returns:
            RiskManagementEnvelope with order IDs and status

        Raises:
            ValueError: If order_manager is not configured
            StopPlacementError: If stop order placement fails (after cancelling entry)
        """
        from src.trading_bot.order_management.models import OrderRequest

        if self.order_manager is None:
            raise ValueError("OrderManager not configured")

        # Step 1: Submit entry order
        entry_request = OrderRequest(
            symbol=symbol,
            side="BUY",
            quantity=plan.quantity,
            reference_price=plan.entry_price,
        )
        entry_envelope = self.order_manager.place_limit_order(entry_request)

        # Step 2: Submit stop order
        stop_request = OrderRequest(
            symbol=symbol,
            side="SELL",
            quantity=plan.quantity,
            reference_price=plan.stop_price,
        )
        stop_envelope = self.order_manager.place_limit_order(stop_request)

        # Step 3: Submit target order
        target_request = OrderRequest(
            symbol=symbol,
            side="SELL",
            quantity=plan.quantity,
            reference_price=plan.target_price,
        )
        target_envelope = self.order_manager.place_limit_order(target_request)

        # Step 4: Create and return envelope
        return RiskManagementEnvelope(
            position_plan=plan,
            entry_order_id=entry_envelope.order_id,
            stop_order_id=stop_envelope.order_id,
            target_order_id=target_envelope.order_id,
            status="pending",
        )
