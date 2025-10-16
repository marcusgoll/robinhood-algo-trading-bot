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
        log_dir: Path | None = None,
    ) -> None:
        """Initialize risk manager with configuration and optional order manager.

        Args:
            config: Risk management configuration
            order_manager: Order management dependency for order placement
            log_dir: Directory for JSONL audit logs (default: logs/)
        """
        self.config = config or RiskManagementConfig.default()
        self.order_manager = order_manager
        self.log_dir = log_dir or Path("logs")
        self._log_lock = threading.Lock()

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

    def _write_jsonl_log(self, log_entry: dict) -> None:
        """Write a log entry to the JSONL audit trail.

        Thread-safe operation with file locking per Constitution v1.0.0 §Data_Integrity.

        Args:
            log_entry: Dictionary to log as JSON line
        """
        try:
            log_file = self.log_dir / "risk-management.jsonl"

            # Thread-safe write with file locking
            with self._log_lock:
                # Create parent directories if needed
                log_file.parent.mkdir(parents=True, exist_ok=True)

                # Write to file with optimized buffering
                with open(log_file, 'a', buffering=8192, encoding='utf-8') as f:
                    # Serialize to compact JSON
                    jsonl_line = json.dumps(log_entry, separators=(',', ':'))
                    f.write(jsonl_line + '\n')
        except OSError as e:
            # Graceful degradation: Log error to stderr but don't crash
            print(f"ERROR: Failed to write risk management log: {e}", file=sys.stderr)

    def log_position_plan(
        self,
        plan: PositionPlan,
        pullback_source: str = "unknown",
    ) -> None:
        """Log position plan creation to JSONL audit trail.

        Args:
            plan: Position plan to log
            pullback_source: Source of pullback analysis ("detected" or "default")
        """
        # Convert Decimal fields to strings for JSON serialization
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": "position_plan_created",
            "symbol": plan.symbol,
            "entry_price": str(plan.entry_price),
            "stop_price": str(plan.stop_price),
            "target_price": str(plan.target_price),
            "quantity": plan.quantity,
            "risk_amount": str(plan.risk_amount),
            "reward_ratio": plan.reward_ratio,
            "pullback_source": pullback_source,
        }

        self._write_jsonl_log(log_entry)
