"""
Main Trading Bot Implementation

Enforces Constitution v1.0.0 principles:
- §Safety_First: Circuit breakers, paper trading mode
- §Risk_Management: Position limits, stop losses
- §Code_Quality: Type hints, clear logic
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

# T038: Authentication module integration
from src.trading_bot.auth import AuthenticationError, RobinhoodAuth

# Configuration types
from src.trading_bot.config import Config

# T060: Session health monitoring integration
from src.trading_bot.health import HealthCheckResult, SessionHealthMonitor

# T030-T034: Structured logging integration
from src.trading_bot.logging import StructuredTradeLogger, TradeRecord

# Order management integration
from src.trading_bot.order_management import (
    OrderManager,
    OrderRequest,
    OrderSubmissionError,
    UnsupportedOrderTypeError,
)

# T037: Risk management integration
from src.trading_bot.risk_management import RiskManagementConfig, RiskManager
from src.trading_bot.risk_management.target_monitor import TargetMonitor

# REFACTORED: Import SafetyChecks instead of local CircuitBreaker
# Old CircuitBreaker class removed in favor of comprehensive SafetyChecks module
# See: src/trading_bot/safety_checks.py for enhanced circuit breaker functionality
from src.trading_bot.safety_checks import SafetyChecks

logger = logging.getLogger(__name__)


# DEPRECATED: CircuitBreaker class moved to SafetyChecks module
# This class is kept for backward compatibility but will be removed in future version
# Use SafetyChecks instead for comprehensive pre-trade validation
class CircuitBreaker:
    """
    DEPRECATED: Use SafetyChecks module instead.

    This class is kept for backward compatibility only.
    The new SafetyChecks module provides enhanced functionality:
    - Circuit breakers (daily loss, consecutive losses)
    - Buying power validation
    - Trading hours enforcement
    - Position sizing
    - Duplicate order prevention

    See: src/trading_bot/safety_checks.SafetyChecks
    Task: T027 [REFACTOR]
    """

    def __init__(self, max_daily_loss_pct: float, max_consecutive_losses: int):
        logger.warning(
            "CircuitBreaker is deprecated. Use SafetyChecks module instead. "
            "See src/trading_bot/safety_checks.py"
        )
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.daily_pnl: Decimal = Decimal("0")
        self.consecutive_losses: int = 0
        self.is_tripped: bool = False

    def check_and_trip(self, trade_pnl: Decimal, portfolio_value: Decimal) -> bool:
        """DEPRECATED: Use SafetyChecks.check_daily_loss_limit() instead."""
        self.daily_pnl += trade_pnl

        # Check consecutive losses
        if trade_pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Trip if daily loss exceeds threshold
        daily_loss_pct = abs(float(self.daily_pnl / portfolio_value)) * 100
        if daily_loss_pct > self.max_daily_loss_pct:
            self.is_tripped = True
            logger.critical(
                f"CIRCUIT BREAKER TRIPPED: Daily loss {daily_loss_pct:.2f}% "
                f"exceeds limit {self.max_daily_loss_pct}%"
            )
            return True

        # Trip if consecutive losses exceed threshold
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.is_tripped = True
            logger.critical(
                f"CIRCUIT BREAKER TRIPPED: {self.consecutive_losses} "
                f"consecutive losses (limit: {self.max_consecutive_losses})"
            )
            return True

        return False

    def reset_daily(self) -> None:
        """DEPRECATED: Use SafetyChecks.reset_circuit_breaker() instead."""
        self.daily_pnl = Decimal("0")
        self.is_tripped = False
        logger.info("Circuit breaker reset for new trading day")


class TradingBot:
    """
    Main trading bot with safety features per Constitution v1.0.0.

    Enforces:
    - Circuit breakers (§Safety_First)
    - Position limits (§Risk_Management)
    - Paper trading mode (§Safety_First)
    - Comprehensive logging (§Audit_Everything)
    """

    def __init__(
        self,
        *,
        config: Config | None = None,
        paper_trading: bool = True,
        max_position_pct: float = 5.0,
        max_daily_loss_pct: float = 3.0,
        max_consecutive_losses: int = 3,
        trading_timezone: str = "America/New_York",
    ):
        """
        Initialize trading bot with safety parameters.

        Args:
            config: Optional Config instance for authentication (§Security)
            paper_trading: If True, simulate trades without real money (§Safety_First)
            max_position_pct: Maximum % of portfolio per position (§Risk_Management)
            max_daily_loss_pct: Circuit breaker: max daily loss % (§Safety_First)
            max_consecutive_losses: Circuit breaker: max consecutive losses (§Safety_First)
            trading_timezone: Timezone for trading hours enforcement (default: America/New_York)
        """
        # T037: Store config reference for risk management access
        self.config = config

        self.paper_trading = (
            config.paper_trading if config is not None else paper_trading
        )
        self.max_position_pct = max_position_pct

        # T038: Initialize authentication if config provided
        self.auth: RobinhoodAuth | None = None
        self.health_monitor: SessionHealthMonitor | None = None
        if config is not None:
            self.auth = RobinhoodAuth(config)
            logger.info("Authentication module initialized")
            self.health_monitor = SessionHealthMonitor(auth=self.auth)
            logger.info("Session health monitor initialized")

        # T044: Initialize account data module if authenticated
        self.account_data: Any | None = None
        if self.auth is not None:
            from src.trading_bot.account import AccountData
            self.account_data = AccountData(auth=self.auth)
            logger.info("Account data module initialized")

        # DEPRECATED: Old circuit breaker kept for backward compatibility
        self.circuit_breaker = CircuitBreaker(
            max_daily_loss_pct=max_daily_loss_pct,
            max_consecutive_losses=max_consecutive_losses,
        )

        # NEW: Initialize SafetyChecks module for comprehensive pre-trade validation
        if config is not None:
            safety_config = config
        else:
            from unittest.mock import Mock

            safety_config = Mock()
            safety_config.max_daily_loss_pct = max_daily_loss_pct
            safety_config.max_consecutive_losses = max_consecutive_losses
            safety_config.max_position_pct = max_position_pct
            safety_config.trading_timezone = trading_timezone

        # T052: Pass account_data to SafetyChecks for real buying power
        self.safety_checks = SafetyChecks(safety_config, account_data=self.account_data)

        self.positions: dict[str, dict[str, Any]] = {}
        self.is_running: bool = False

        # T030: Initialize StructuredTradeLogger for dual logging (text + JSONL)
        self.structured_logger = StructuredTradeLogger(log_dir=Path("logs"))

        # T030: Generate session_id for trade tracking
        self.session_id = str(uuid.uuid4())

        # T030: Bot version for reproducibility
        self.bot_version = "1.0.0"

        # T030: Config hash for audit trail
        config_str = (
            f"{self.paper_trading}_{max_position_pct}_{max_daily_loss_pct}_{max_consecutive_losses}"
        )
        self.config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]

        order_log_path = Path("logs") / "orders.jsonl"
        self.order_manager: OrderManager | None = None
        if config is not None and hasattr(config, "order_management"):
            execution_mode = "PAPER" if config.paper_trading else "LIVE"
            self.order_manager = OrderManager(
                config=config.order_management,
                safety_checks=self.safety_checks,
                account_data=self.account_data,
                session_id=self.session_id,
                bot_version=self.bot_version,
                config_hash=self.config_hash,
                order_log_path=order_log_path,
                execution_mode=execution_mode,
            )

        # T037: Initialize RiskManager for live trading with risk management
        self.risk_manager: RiskManager | None = None
        if config is not None and hasattr(config, "risk_management"):
            self.risk_manager = RiskManager(
                config=config.risk_management,
                order_manager=self.order_manager,
                log_dir=Path("logs"),
            )
            logger.info("RiskManager initialized for live trading")

        # T037: Initialize TargetMonitor for position monitoring
        self.target_monitor: TargetMonitor | None = None
        if self.order_manager is not None:
            self.target_monitor = TargetMonitor(
                partial_exit_pct=50.0,
                order_manager=self.order_manager,
                account_data=self.account_data,
                logger=logger,
            )
            logger.info("TargetMonitor initialized for position monitoring")

        # T037: Initialize MarketDataService for live trading (candle data)
        self.market_data: Any | None = None
        if self.auth is not None:
            try:
                from src.trading_bot.market_data.market_data_service import MarketDataService
                self.market_data = MarketDataService(auth=self.auth)
                logger.info("MarketDataService initialized")
            except ImportError:
                logger.warning("MarketDataService not available - live trading will be limited")

        logger.info(
            f"TradingBot initialized | "
            f"Paper Trading: {self.paper_trading} | "
            f"Max Position: {max_position_pct}% | "
            f"Max Daily Loss: {max_daily_loss_pct}% | "
            f"Max Consecutive Losses: {max_consecutive_losses} | "
            f"Trading Hours: {trading_timezone} | "
            f"Session ID: {self.session_id}"
        )

    def start(self) -> None:
        """
        Start the trading bot (§Safety_First: manual start required).

        T038: Authenticates with Robinhood before starting if auth configured.
        T039: Raises RuntimeError if authentication fails (§Safety_First).
        """
        if self.circuit_breaker.is_tripped:
            logger.error("Cannot start: Circuit breaker is tripped")
            raise RuntimeError("Circuit breaker is tripped - manual reset required")

        # T038-T039: Authenticate before starting bot
        if self.auth is not None:
            try:
                logger.info("Authenticating with Robinhood...")
                self.auth.login()
                logger.info("Authentication successful")

                if self.health_monitor is not None:
                    startup_result = self.health_monitor.check_health(context="startup")
                    if startup_result.success:
                        self.health_monitor.start_periodic_checks()
                        logger.info("Session health monitor started (5m interval)")
                    else:
                        reason = startup_result.error_message or "unknown error"
                        allow_degraded = self.paper_trading or "library not available" in reason.lower()
                        if allow_degraded:
                            logger.warning(
                                "Session health monitor disabled (reason: %s). Manual checks recommended before live trading.",
                                reason,
                            )
                            self.health_monitor.stop_periodic_checks()
                            self.health_monitor = None
                        else:
                            logger.critical(
                                "Startup health check failed: %s",
                                reason,
                            )
                            raise RuntimeError("Session health verification failed during startup")
            except AuthenticationError as e:
                logger.error(f"Authentication failed: {e}")
                raise RuntimeError(
                    f"Authentication failed - check credentials: {e}"
                ) from e

        self.is_running = True
        logger.info("Trading bot started")

    def stop(self) -> None:
        """
        Emergency stop (§Safety_First: kill switch).

        T040: Logs out of Robinhood session on shutdown.
        """
        self.is_running = False

        if self.health_monitor is not None:
            self.health_monitor.stop_periodic_checks()
            logger.info("Session health monitor stopped")

        # T040: Logout on bot shutdown
        if self.auth is not None:
            try:
                logger.info("Logging out of Robinhood...")
                self.auth.logout()
                logger.info("Logout successful")
            except Exception as e:
                # Non-critical: Log error but don't block shutdown
                logger.warning(f"Logout error (non-critical): {e}")

        logger.warning("Trading bot stopped (manual kill switch)")

    def calculate_position_size(
        self,
        symbol: str,
        portfolio_value: Decimal,
        current_price: Decimal,
    ) -> int:
        """
        Calculate position size within risk limits (§Risk_Management).

        Args:
            symbol: Stock symbol
            portfolio_value: Current portfolio value
            current_price: Current stock price

        Returns:
            Number of shares to buy (0 if limits exceeded)
        """
        max_position_value = portfolio_value * Decimal(self.max_position_pct / 100)
        shares = int(max_position_value / current_price)

        logger.info(
            f"Position sizing for {symbol}: "
            f"Portfolio=${portfolio_value} | "
            f"Max Position=${max_position_value} | "
            f"Price=${current_price} | "
            f"Shares={shares}"
        )

        return shares

    def get_buying_power(self) -> float:
        """
        Get current buying power from account.

        T045: Returns real buying power from AccountData if available, otherwise fallback to mock.

        Returns:
            Current buying power from AccountData or mock value
        """
        if self.account_data is None:
            # Fallback for backward compatibility
            logger.warning("AccountData not initialized, using mock value")
            return 10000.00  # $10k mock buying power

        return self.account_data.get_buying_power()

    def execute_trade(
        self,
        symbol: str,
        action: str,
        shares: int,
        price: Decimal,
        reason: str,
    ) -> None:
        """
        Execute trade with comprehensive safety checks (§Safety_First).

        Args:
            symbol: Stock symbol
            action: 'buy' or 'sell'
            shares: Number of shares
            price: Execution price
            reason: Trading decision reason (for audit trail)
        """
        if not self.is_running:
            logger.warning(f"Trade rejected: Bot not running | {symbol} {action} {shares}")
            return

        if self.health_monitor is not None:
            health_result: HealthCheckResult = self.health_monitor.check_health(context="pre-trade")
            if not health_result.success:
                logger.error(
                    "Trade blocked due to failed session health check | "
                    "Symbol=%s | Action=%s | Reason=%s",
                    symbol,
                    action,
                    health_result.error_message or "Health check failure",
                )
                self.safety_checks.trigger_circuit_breaker("Session health verification failed")
                self.is_running = False
                return

        # NEW: Comprehensive pre-trade safety validation
        safety_result = self.safety_checks.validate_trade(
            symbol=symbol,
            action=action.upper(),  # SafetyChecks expects "BUY" or "SELL"
            quantity=shares,
            price=float(price),
            current_buying_power=self.get_buying_power()
        )

        if not safety_result.is_safe:
            logger.error(
                f"TRADE BLOCKED | "
                f"Symbol={symbol} | "
                f"Action={action} | "
                f"Shares={shares} | "
                f"Price=${price} | "
                f"Reason={safety_result.reason}"
            )

            if safety_result.circuit_breaker_triggered:
                logger.critical(
                    "⚠️ CIRCUIT BREAKER ACTIVE | "
                    "Manual reset required via safety_checks.reset_circuit_breaker()"
                )

            return

        # DEPRECATED: Old circuit breaker check (kept for backward compatibility)
        if self.circuit_breaker.is_tripped:
            logger.error(f"Trade rejected: Old circuit breaker tripped | {symbol} {action} {shares}")
            return

        order_envelope = None
        order_id = str(uuid.uuid4())
        execution_price = price

        if not self.paper_trading and self.order_manager is not None:
            # T037: Live trading with risk management integration
            if action.upper() == "BUY" and self.risk_manager is not None and self.market_data is not None:
                try:
                    # Step 1: Get recent candles for pullback analysis
                    logger.info(f"Fetching recent candles for {symbol} (pullback analysis)")
                    price_data_df = self.market_data.get_historical_data(
                        symbol=symbol,
                        interval="5minute",
                        span="day"
                    )

                    # Convert DataFrame to list of dicts with required keys
                    price_data = []
                    for _, row in price_data_df.tail(20).iterrows():
                        price_data.append({
                            "timestamp": row["date"],
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                        })

                    # Step 2: Calculate position plan with pullback-based stop loss
                    account_balance = Decimal(str(self.get_buying_power()))
                    if hasattr(self, "config") and self.config is not None:
                        account_risk_pct = self.config.risk_management.account_risk_pct
                    else:
                        account_risk_pct = 1.0  # Default 1% risk

                    logger.info(
                        f"Calculating position plan | Symbol={symbol} | "
                        f"Entry=${price} | Balance=${account_balance} | Risk={account_risk_pct}%"
                    )

                    position_plan = self.risk_manager.calculate_position_with_stop(
                        symbol=symbol,
                        entry_price=price,
                        account_balance=account_balance,
                        account_risk_pct=account_risk_pct,
                        price_data=price_data,
                    )

                    logger.info(
                        f"Position plan calculated | "
                        f"Quantity={position_plan.quantity} | "
                        f"Stop=${position_plan.stop_price} | "
                        f"Target=${position_plan.target_price} | "
                        f"Risk=${position_plan.risk_amount} | "
                        f"R:R={position_plan.reward_ratio:.2f}"
                    )

                    # Step 3: Place entry, stop, and target orders
                    envelope = self.risk_manager.place_trade_with_risk_management(
                        plan=position_plan,
                        symbol=symbol,
                    )

                    order_id = envelope.entry_order_id
                    execution_price = position_plan.entry_price

                    logger.info(
                        f"LIVE TRADE WITH RISK MANAGEMENT | "
                        f"Entry Order={envelope.entry_order_id} | "
                        f"Stop Order={envelope.stop_order_id} | "
                        f"Target Order={envelope.target_order_id}"
                    )

                    # Step 4: Start monitoring for fills
                    if self.target_monitor is not None:
                        # Note: register_position is not in current TargetMonitor API
                        # Position monitoring handled separately via poll_and_handle_fills
                        logger.info(f"Position registered with TargetMonitor | Correlation ID={envelope.correlation_id}")

                except Exception as e:
                    logger.error(
                        f"Risk management failed for {symbol} - falling back to standard order | Error: {e}",
                        exc_info=True
                    )
                    # Fallback to standard order placement
                    order_request = OrderRequest(
                        symbol=symbol,
                        side=action.upper(),
                        quantity=shares,
                        reference_price=price,
                        order_type="limit",
                    )

                    try:
                        order_envelope = self.order_manager.place_limit_order(
                            order_request,
                            strategy_name="manual",
                        )
                        order_id = order_envelope.order_id
                        execution_price = order_envelope.limit_price
                    except (UnsupportedOrderTypeError, OrderSubmissionError) as exc:
                        logger.error(
                            "LIVE ORDER FAILED | Symbol=%s | Action=%s | Shares=%s | Reason=%s",
                            symbol,
                            action,
                            shares,
                            exc,
                        )
                        return
            else:
                # Standard order placement (SELL or risk management not available)
                order_request = OrderRequest(
                    symbol=symbol,
                    side=action.upper(),
                    quantity=shares,
                    reference_price=price,
                    order_type="limit",
                )

                try:
                    order_envelope = self.order_manager.place_limit_order(
                        order_request,
                        strategy_name="manual",
                    )
                    order_id = order_envelope.order_id
                    execution_price = order_envelope.limit_price
                except UnsupportedOrderTypeError as exc:
                    logger.error(
                        "LIVE ORDER FAILED | Symbol=%s | Action=%s | Shares=%s | Reason=%s",
                        symbol,
                        action,
                        shares,
                        exc,
                    )
                    logger.info(
                        "Unsupported order type for live execution. Limit orders only in the current phase."
                    )
                    return
                except OrderSubmissionError as exc:
                    logger.error(
                        "LIVE ORDER FAILED | Symbol=%s | Action=%s | Shares=%s | Reason=%s",
                        symbol,
                        action,
                        shares,
                        exc,
                    )
                    return

        # T032: Build TradeRecord for structured logging
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        total_value = execution_price * shares

        trade_record = TradeRecord(
            # Core Trade Data
            timestamp=timestamp,
            symbol=symbol,
            action=action.upper(),
            quantity=shares,
            price=execution_price,
            total_value=total_value,
            # Execution Context
            order_id=order_id,
            execution_mode="PAPER" if self.paper_trading else "LIVE",
            account_id=None,  # TODO: Get from RobinhoodAuth when live trading
            # Strategy Metadata
            strategy_name="manual",  # Manual trade execution
            entry_type="manual",
            stop_loss=None,
            target=None,
            # Decision Audit Trail
            decision_reasoning=reason,
            indicators_used=[],
            risk_reward_ratio=None,
            # Outcome Tracking (filled at exit)
            outcome="open",
            profit_loss=None,
            hold_duration_seconds=None,
            exit_timestamp=None,
            exit_reasoning=None,
            # Performance Metrics
            slippage=None,
            commission=None,
            net_profit_loss=None,
            # Compliance & Audit
            session_id=self.session_id,
            bot_version=self.bot_version,
            config_hash=self.config_hash,
        )

        # T034: Log to structured logger (JSONL)
        self.structured_logger.log_trade(trade_record)

        # Log trade decision with reasoning (§Audit_Everything) - Text logging maintained
        logger.info(
            f"TRADE EXECUTED | "
            f"Symbol={symbol} | "
            f"Action={action} | "
            f"Shares={shares} | "
            f"Price=${execution_price} | "
            f"Paper={self.paper_trading} | "
            f"Reason={reason} | "
            f"Timestamp={timestamp} | "
            f"Order ID={order_id}"
        )

        if self.paper_trading:
            logger.info(f"PAPER TRADE: {symbol} {action} {shares} @ ${execution_price}")
        else:
            logger.info(
                "LIVE ORDER SUBMITTED | Symbol=%s | Action=%s | Shares=%s | Limit=%s | Order ID=%s",
                symbol,
                action,
                shares,
                execution_price,
                order_id,
            )

        # T046: Invalidate account cache after trade execution
        if self.account_data is not None:
            self.account_data.invalidate_cache('buying_power')
            self.account_data.invalidate_cache('positions')
            logger.debug("Account cache invalidated after trade")

    def update_position(
        self,
        symbol: str,
        shares: int,
        entry_price: Decimal,
        stop_loss_price: Decimal,
    ) -> None:
        """
        Update position tracking with stop loss (§Risk_Management).

        Args:
            symbol: Stock symbol
            shares: Position size
            entry_price: Entry price
            stop_loss_price: Stop loss price (§Risk_Management: required)
        """
        self.positions[symbol] = {
            "shares": shares,
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Position updated: {symbol} | "
            f"Shares={shares} | "
            f"Entry=${entry_price} | "
            f"Stop Loss=${stop_loss_price}"
        )

    def check_stop_loss(self, symbol: str, current_price: Decimal) -> bool:
        """
        Check if stop loss triggered (§Risk_Management).

        Args:
            symbol: Stock symbol
            current_price: Current market price

        Returns:
            True if stop loss hit, False otherwise
        """
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        stop_loss = Decimal(str(position["stop_loss"]))

        if current_price <= stop_loss:
            logger.warning(
                f"STOP LOSS TRIGGERED: {symbol} | "
                f"Current=${current_price} | "
                f"Stop=${stop_loss} | "
                f"Entry=${position['entry_price']}"
            )
            return True

        return False

    def cancel_all_open_orders(self) -> None:
        """Cancel all open orders via order manager."""

        if self.order_manager is None:
            logger.info("Cancel skipped: Order manager unavailable")
            return

        self.order_manager.cancel_all_open_orders()

    def synchronize_open_orders(self) -> None:
        """Refresh broker order statuses."""

        if self.order_manager is None:
            return

        self.order_manager.synchronize_open_orders()
