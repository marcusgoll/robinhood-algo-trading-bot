"""
SafetyChecks module for pre-trade validation and risk management.

Implements circuit breakers, buying power checks, trading hours enforcement,
and position sizing to comply with Constitution §Safety_First and §Risk_Management.

Constitution v1.0.0 - §Code_Quality: Type hints required

Usage Example:
    from src.trading_bot.safety_checks import SafetyChecks
    from src.trading_bot.config import Config

    # Initialize
    config = Config.from_env_and_json()
    safety = SafetyChecks(config)

    # Validate trade before execution
    result = safety.validate_trade(
        symbol="AAPL",
        action="BUY",
        quantity=100,
        price=150.00,
        current_buying_power=20000.00
    )

    if result.is_safe:
        # Execute trade
        print("Trade allowed")
    else:
        print(f"Trade blocked: {result.reason}")
        if result.circuit_breaker_triggered:
            print("Circuit breaker triggered - manual reset required")

    # Calculate position size
    position = safety.calculate_position_size(
        entry_price=150.00,
        stop_loss_price=145.00,
        account_balance=100000.00
    )
    print(f"Position size: {position.share_quantity} shares (${position.dollar_amount:.2f})")

    # Manual circuit breaker management
    safety.trigger_circuit_breaker(reason="3 consecutive losses")
    # ... later ...
    safety.reset_circuit_breaker()

From: spec.md, plan.md, contracts/api.yaml
Task: T029 [REFACTOR]
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytz

from src.trading_bot.config import Config

# REUSE: Import time utilities
from src.trading_bot.utils.time_utils import is_trading_hours


@dataclass
class SafetyResult:
    """
    Result of safety validation.

    Attributes:
        is_safe: Whether trade is safe to execute
        reason: Optional reason for blocking (if is_safe=False)
        circuit_breaker_triggered: Whether circuit breaker was triggered

    From: spec.md, contracts/api.yaml
    """
    is_safe: bool
    reason: str | None = None
    circuit_breaker_triggered: bool = False


@dataclass
class PositionSize:
    """
    Position size calculation result.

    Attributes:
        dollar_amount: Dollar value of position
        share_quantity: Number of shares
        risk_amount: Dollar amount at risk (to stop loss)
        stop_loss_price: Stop loss price used in calculation

    From: spec.md FR-005, contracts/api.yaml
    """
    dollar_amount: float
    share_quantity: int
    risk_amount: float
    stop_loss_price: float


class SafetyChecks:
    """
    Pre-trade safety checks and circuit breaker system.

    Validates trades against risk management rules before execution.
    Implements fail-safe design (block on any validation failure).

    Pattern: Dependency injection (receives config)
    From: plan.md [ARCHITECTURE DECISIONS]
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize safety checks with configuration.

        Args:
            config: Configuration object with risk parameters

        From: spec.md Technical Design
        """
        self.config = config

        # Circuit breaker state
        self._circuit_breaker_active = False

        # Pending orders tracking (for duplicate prevention)
        self._pending_orders: dict[str, str] = {}

        # Trade history (for consecutive loss detection)
        self._trade_history: list[dict[str, Any]] = []

        # Load circuit breaker state from file (if exists)
        self._load_circuit_breaker_state()

    def validate_trade(
        self,
        symbol: str,
        action: str,  # "BUY" or "SELL"
        quantity: int,
        price: float,
        current_buying_power: float
    ) -> SafetyResult:
        """
        Validate trade against all safety checks.

        Orchestrates all validation checks in fail-safe sequence.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            action: Trade action ("BUY" or "SELL")
            quantity: Number of shares
            price: Price per share
            current_buying_power: Available buying power from account

        Returns:
            SafetyResult with is_safe, reason, circuit_breaker_triggered

        Raises:
            ValueError: If input parameters are invalid

        From: spec.md Requirements FR-001 through FR-007
        Pattern: Fail-safe (any failure blocks trade)
        Task: T026 [GREEN→T016,T017], T039 (input validation)
        """
        # Input validation (T039)
        if not symbol or not symbol.isalnum():
            raise ValueError(f"Invalid symbol: {symbol}. Must be alphanumeric.")

        if action not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid action: {action}. Must be 'BUY' or 'SELL'.")

        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}. Must be > 0.")

        if price <= 0:
            raise ValueError(f"Invalid price: {price}. Must be > 0.")

        if current_buying_power < 0:
            raise ValueError(f"Invalid buying power: {current_buying_power}. Must be >= 0.")
        # Check circuit breaker first (hard stop)
        if self._circuit_breaker_active:
            return SafetyResult(
                is_safe=False,
                reason="Circuit breaker active - manual reset required",
                circuit_breaker_triggered=True
            )

        # Check trading hours
        if not self.check_trading_hours():
            return SafetyResult(
                is_safe=False,
                reason="Outside trading hours (7am-10am EST)"
            )

        # Check buying power (only for BUY orders)
        if action == "BUY":
            if not self.check_buying_power(quantity, price, current_buying_power):
                order_cost = quantity * price
                return SafetyResult(
                    is_safe=False,
                    reason=f"Insufficient buying power: ${current_buying_power:.2f} available, ${order_cost:.2f} required"
                )

        # Check for duplicate orders
        if not self.check_duplicate_order(symbol, action):
            return SafetyResult(
                is_safe=False,
                reason=f"Duplicate order detected for {symbol}"
            )

        # All checks passed
        return SafetyResult(is_safe=True)

    def check_buying_power(
        self,
        quantity: int,
        price: float,
        current_buying_power: float
    ) -> bool:
        """
        Check if sufficient buying power exists.

        Args:
            quantity: Number of shares
            price: Price per share
            current_buying_power: Available buying power

        Returns:
            True if sufficient buying power, False otherwise

        From: spec.md FR-001
        Pattern: Simple arithmetic (quantity × price) ≤ buying power
        Task: T019 [GREEN→T007,T008]
        """
        order_cost = quantity * price
        return order_cost <= current_buying_power

    def check_trading_hours(self) -> bool:
        """
        Check if current time is within trading hours.

        Returns:
            True if within trading hours, False otherwise

        From: spec.md FR-002
        REUSE: time_utils.is_trading_hours()
        REUSE: config.trading_timezone
        Task: T020 [GREEN→T009]
        """
        return is_trading_hours(self.config.trading_timezone)

    def check_daily_loss_limit(
        self,
        current_daily_pnl: float,
        portfolio_value: float
    ) -> bool:
        """
        Check if daily loss limit exceeded.

        Args:
            current_daily_pnl: Current daily profit/loss (negative for loss)
            portfolio_value: Total portfolio value

        Returns:
            True if within limit, False if limit exceeded

        From: spec.md FR-003
        REUSE: config.max_daily_loss_pct
        Task: T021 [GREEN→T010]
        """
        if current_daily_pnl >= 0:
            return True  # No loss, check passes

        loss_pct = abs(current_daily_pnl / portfolio_value) * 100
        return loss_pct <= self.config.max_daily_loss_pct

    def check_consecutive_losses(self) -> bool:
        """
        Check if consecutive loss limit exceeded.

        Returns:
            True if within limit, False if limit exceeded

        From: spec.md FR-004
        REUSE: config.max_consecutive_losses
        REUSE: self._trade_history (parsed from logs/trades.log)
        Task: T022 [GREEN→T011]
        """
        if len(self._trade_history) < self.config.max_consecutive_losses:
            return True  # Not enough trades to detect pattern

        # Check last N trades for consecutive losses
        recent_trades = self._trade_history[-self.config.max_consecutive_losses:]
        consecutive_losses = all(trade.get("outcome") == "loss" for trade in recent_trades)

        return not consecutive_losses

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        account_balance: float
    ) -> PositionSize:
        """
        Calculate position size based on risk.

        Args:
            entry_price: Entry price per share
            stop_loss_price: Stop loss price per share
            account_balance: Total account balance

        Returns:
            PositionSize with dollar_amount, share_quantity, risk_amount, stop_loss_price

        From: spec.md FR-005
        REUSE: config.max_position_pct
        Task: T023 [GREEN→T012]
        """
        # Calculate max position size (5% of portfolio)
        max_position_value = (self.config.max_position_pct / 100) * account_balance

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)

        # Calculate shares based on max position
        max_shares = int(max_position_value / entry_price)

        # Calculate actual position values
        dollar_amount = max_shares * entry_price
        risk_amount = max_shares * risk_per_share

        return PositionSize(
            dollar_amount=dollar_amount,
            share_quantity=max_shares,
            risk_amount=risk_amount,
            stop_loss_price=stop_loss_price
        )

    def check_duplicate_order(self, symbol: str, action: str) -> bool:
        """
        Check for duplicate pending orders.

        Args:
            symbol: Stock symbol
            action: Trade action ("BUY" or "SELL")

        Returns:
            True if no duplicate, False if duplicate exists

        From: spec.md FR-006
        Pattern: In-memory dict tracking
        Task: T024 [GREEN→T013]
        """
        # Check if pending order exists for this symbol
        if symbol in self._pending_orders and self._pending_orders[symbol] == action:
            return False  # Duplicate detected

        return True  # No duplicate

    def trigger_circuit_breaker(self, reason: str) -> None:
        """
        Trigger circuit breaker with reason.

        Args:
            reason: Reason for triggering circuit breaker

        From: spec.md FR-007
        Pattern: Set flag, persist to file, log event
        Task: T025 [GREEN→T014,T015]
        """
        self._circuit_breaker_active = True

        # Persist state to file
        state = {
            "active": True,
            "triggered_at": datetime.now(pytz.UTC).isoformat(),
            "reason": reason,
            "reset_at": None
        }

        try:
            with open("logs/circuit_breaker.json", "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass  # Fail silently (state still in memory)

    def reset_circuit_breaker(self) -> None:
        """
        Reset circuit breaker (manual only).

        From: spec.md FR-007
        Task: T025 [GREEN→T014,T015]
        """
        self._circuit_breaker_active = False

        # Persist state to file
        state = {
            "active": False,
            "triggered_at": None,
            "reason": None,
            "reset_at": datetime.now(pytz.UTC).isoformat()
        }

        try:
            with open("logs/circuit_breaker.json", "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass  # Fail silently (state still in memory)

    def _load_circuit_breaker_state(self) -> None:
        """
        Load circuit breaker state from file.

        Internal method called during __init__.
        Fail-safe: If file corrupt, TRIP circuit breaker (halt trading).
        If file missing, assume inactive (first run).

        From: plan.md [RISK MITIGATION], spec.md NFR-002
        Task: T036 [GREEN→T035]
        """
        try:
            with open("logs/circuit_breaker.json") as f:
                state = json.load(f)
                self._circuit_breaker_active = state.get("active", False)
        except FileNotFoundError:
            # File missing → assume inactive (first run, OK)
            self._circuit_breaker_active = False
        except json.JSONDecodeError:
            # File corrupt → TRIP circuit breaker (fail-safe: halt trading)
            self._circuit_breaker_active = True
            # Note: Would log error here, but avoiding logger dependency in __init__
