"""Core risk management orchestration."""

from __future__ import annotations

import json
import sys
import threading
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from trading_bot.error_handling import RetryPolicy, with_retry
from trading_bot.error_handling.circuit_breaker import CircuitBreaker
from trading_bot.error_handling.exceptions import CircuitBreakerTripped

from .calculator import calculate_position_plan
from .config import RiskManagementConfig
from .models import PositionPlan, RiskManagementEnvelope
from .pullback_analyzer import PullbackAnalyzer

if TYPE_CHECKING:
    from trading_bot.order_management.manager import OrderManager


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
        pullback_analyzer: PullbackAnalyzer | None = None,
    ) -> None:
        """Initialize risk manager with configuration and optional dependencies.

        Args:
            config: Risk management configuration
            order_manager: Order management dependency for order placement
            log_dir: Directory for JSONL audit logs (default: logs/)
            pullback_analyzer: Pullback analyzer for stop-loss calculation (optional)
        """
        self.config = config or RiskManagementConfig.default()
        self.order_manager = order_manager
        self.log_dir = log_dir or Path("logs")
        self._log_lock = threading.Lock()
        # Note: Using default pullback threshold (5.0%) since config doesn't have this field
        self.pullback_analyzer = pullback_analyzer or PullbackAnalyzer(
            pullback_threshold_pct=5.0
        )

        # Circuit breaker for stop placement failures (T040)
        # Per spec.md guardrail: Trip if failure rate >2% (threshold=2 failures per 100 attempts)
        # Window: 100 attempts (tracks last 100 stop placement attempts)
        self._stop_placement_circuit_breaker = CircuitBreaker(
            threshold=2,  # 2 failures
            window_seconds=100  # Per 100 attempts (reused as attempt counter)
        )
        self._stop_placement_attempts = 0
        self._stop_placement_failures = 0

    def calculate_position_with_stop(
        self,
        symbol: str,
        entry_price: Decimal,
        account_balance: Decimal,
        account_risk_pct: float,
        price_data: list[dict[str, Any]],
        target_rr: float = 2.0,
        lookback_candles: int = 20,
    ) -> PositionPlan:
        """Calculate position plan with pullback-based stop-loss analysis.

        High-level orchestration method that combines pullback analysis with
        position planning logic. This is the primary entry point for position
        planning with automated stop-loss detection.

        Args:
            symbol: Stock symbol
            entry_price: Intended entry price
            account_balance: Total account balance
            account_risk_pct: Maximum risk percentage (e.g., 1.0 for 1%)
            price_data: List of price candles with 'timestamp', 'low', 'close' keys
            target_rr: Target risk-reward ratio (default: 2.0 for 2:1)
            lookback_candles: Number of candles to analyze for pullback (default: 20)

        Returns:
            PositionPlan with calculated quantities, prices, and risk metrics

        Orchestration flow:
            1. Call PullbackAnalyzer.analyze_pullback(price_data) to get stop_price
            2. Call calculate_position_plan(entry, stop, target_rr, balance, risk_pct)
            3. Log position plan to JSONL audit trail
            4. Return PositionPlan

        From: specs/stop-loss-automation/tasks.md T032
        """
        # Step 1: Analyze pullback to determine stop-loss price
        pullback_data = self.pullback_analyzer.analyze_pullback(
            price_data=price_data,
            entry_price=entry_price,
            default_stop_pct=self.config.default_stop_pct,
            lookback_candles=lookback_candles,
        )

        # Step 2: Calculate position plan using stop price from pullback analysis
        # Determine pullback source for audit trail
        pullback_source = "default" if pullback_data.fallback_used else "detected"

        position_plan = calculate_position_plan(
            symbol=symbol,
            entry_price=entry_price,
            stop_price=pullback_data.pullback_price,
            target_rr=target_rr,
            account_balance=account_balance,
            risk_pct=account_risk_pct,
            min_risk_reward_ratio=self.config.min_risk_reward_ratio,
            pullback_source=pullback_source,
        )

        # Step 3: Log position plan creation to audit trail
        self.log_position_plan(position_plan, pullback_source=pullback_source)

        # Step 4: Return the calculated position plan
        return position_plan

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

    def _track_stop_placement_failure(self) -> None:
        """Track stop placement failure and check circuit breaker threshold.

        Increments failure counter and checks if failure rate exceeds 2% threshold.
        Per spec.md guardrail: "If stop-loss orders fail to place >2% of the time,
        trigger circuit breaker and revert to paper trading."

        Raises:
            CircuitBreakerTripped: If failure rate exceeds 2% (>2 failures per 100 attempts)

        From: tasks.md T040
        """
        # Increment counters
        self._stop_placement_attempts += 1
        self._stop_placement_failures += 1

        # Record failure in circuit breaker
        self._stop_placement_circuit_breaker.record_failure()

        # Calculate failure rate
        if self._stop_placement_attempts >= 100:
            failure_rate = (self._stop_placement_failures / self._stop_placement_attempts) * 100

            # Check if failure rate exceeds 2% threshold
            if failure_rate > 2.0:
                raise CircuitBreakerTripped(
                    f"Circuit breaker tripped: stop placement failure rate "
                    f"({failure_rate:.2f}%) exceeded 2% threshold. "
                    f"Failures: {self._stop_placement_failures}/{self._stop_placement_attempts} attempts. "
                    f"Manual intervention required before resuming automated trading."
                )

    def _track_stop_placement_success(self) -> None:
        """Track successful stop placement and reset circuit breaker.

        Increments attempt counter and resets circuit breaker failure tracking
        on successful placement. This implements sliding window behavior where
        successes clear the failure window.

        From: tasks.md T040
        """
        # Increment attempt counter
        self._stop_placement_attempts += 1

        # Record success in circuit breaker (clears failure window)
        self._stop_placement_circuit_breaker.record_success()

    @with_retry(policy=RetryPolicy(max_attempts=3, base_delay=1.0))
    def _place_stop_and_target_orders(
        self, symbol: str, plan: PositionPlan
    ) -> tuple[Any, Any]:
        """Place stop and target orders with retry logic for transient failures.

        This method is decorated with @with_retry to handle transient broker failures
        (network timeouts, 5xx errors) per NFR-007. Retry policy: 3 attempts with
        exponential backoff (1s, 2s, 4s).

        Args:
            symbol: Trading symbol
            plan: Position plan with stop/target prices and quantity

        Returns:
            Tuple of (stop_envelope, target_envelope)

        Raises:
            RetriableError: Network/broker transient failures (will trigger retry)
            StopPlacementError: Permanent stop placement failure (after retries exhausted)
        """
        from trading_bot.order_management.models import OrderRequest

        # Submit stop order
        stop_request = OrderRequest(
            symbol=symbol,
            side="SELL",
            quantity=plan.quantity,
            reference_price=plan.stop_price,
        )
        stop_envelope = self.order_manager.place_limit_order(stop_request)

        # Submit target order
        target_request = OrderRequest(
            symbol=symbol,
            side="SELL",
            quantity=plan.quantity,
            reference_price=plan.target_price,
        )
        target_envelope = self.order_manager.place_limit_order(target_request)

        return stop_envelope, target_envelope

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
            CircuitBreakerTripped: If stop placement failure rate exceeds 2%
        """
        from trading_bot.order_management.models import OrderRequest

        from .exceptions import StopPlacementError

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

        # Step 2: Submit stop and target orders with error handling guardrail
        # FR-003: If stop placement fails, cancel entry to avoid unprotected positions
        try:
            # Call helper method with retry logic
            stop_envelope, target_envelope = self._place_stop_and_target_orders(
                symbol=symbol, plan=plan
            )

            # Track successful stop placement (T040)
            self._track_stop_placement_success()

        except Exception as e:
            # Track stop placement failure (T040)
            # This may raise CircuitBreakerTripped if failure rate exceeds 2%
            self._track_stop_placement_failure()

            # Guardrail: Cancel entry order to prevent unprotected position
            # Per Constitution §Risk_Management: "Never enter a position without
            # predefined exit criteria"
            self.order_manager.cancel_order(order_id=entry_envelope.order_id)

            # TODO: Log error with correlation_id once logger is integrated (T026)
            # self.logger.log_error(correlation_id, e)

            # Re-raise original exception to preserve error context
            raise

        # Step 4: Create and return envelope with correlation_id for lifecycle tracking
        correlation_id = str(uuid.uuid4())
        return RiskManagementEnvelope(
            position_plan=plan,
            entry_order_id=entry_envelope.order_id,
            stop_order_id=stop_envelope.order_id,
            target_order_id=target_envelope.order_id,
            status="pending",
            correlation_id=correlation_id,
        )

    def _write_jsonl_log(self, log_entry: dict, correlation_id: str | None = None) -> None:
        """Write a log entry to the JSONL audit trail.

        Thread-safe operation with file locking per Constitution v1.0.0 §Data_Integrity.
        Enhanced with correlation_id support for position lifecycle tracing (T033).

        Args:
            log_entry: Dictionary to log as JSON line
            correlation_id: Optional UUID4 for tracing position lifecycle
        """
        try:
            # Add correlation_id if provided
            if correlation_id:
                log_entry["correlation_id"] = correlation_id

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
    ) -> str:
        """Log position plan creation to JSONL audit trail.

        Enhanced with correlation_id generation for position lifecycle tracing (T033).

        Args:
            plan: Position plan to log
            pullback_source: Source of pullback analysis ("detected" or "default")

        Returns:
            correlation_id: UUID4 string for tracking this position's lifecycle
        """
        # Generate correlation_id for position lifecycle tracking
        correlation_id = str(uuid.uuid4())

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

        self._write_jsonl_log(log_entry, correlation_id=correlation_id)

        return correlation_id
