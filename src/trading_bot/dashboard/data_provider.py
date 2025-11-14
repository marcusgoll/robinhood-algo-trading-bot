"""
Dashboard data provider service.

Aggregates account data, open positions, trade performance metrics, and configuration
targets into a reusable `DashboardSnapshot` payload that downstream interfaces
can consume (FR-017). Handles graceful degradation scenarios (missing trade logs,
stale cache values) and enforces Constitution requirements for logging and safety.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, DecimalException
from pathlib import Path
from typing import Literal, cast

import yaml

from ..account.account_data import AccountData, Position
from ..logging.query_helper import TradeQueryHelper
from ..logging.trade_record import TradeRecord
from ..utils.time_utils import is_market_open
from .metrics_calculator import MetricsCalculator
from .models import (
    AccountStatus,
    DashboardSnapshot,
    DashboardTargets,
    PerformanceMetrics,
    PositionDisplay,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration knobs for DashboardDataProvider (internal use)."""

    staleness_ttl_seconds: int = 60
    targets_path: Path = Path("config/dashboard-targets.yaml")


class DashboardDataProvider:
    """
    Aggregate dashboard data into a reusable snapshot (FR-017).

    Responsibilities:
        - Load account status (balances, buying power, day-trade count)
        - Transform positions into display-friendly structures
        - Query trade logs and compute performance metrics
        - Load optional dashboard targets from YAML config
        - Detect stale account data (>60 seconds) and raise warnings
        - Surface warnings for missing/corrupt trade logs

    Instances of this provider are shared between the Rich CLI dashboard and the
    upcoming Textual TUI so both surfaces render the same canonical snapshot.
    """

    def __init__(
        self,
        account_data: AccountData,
        trade_helper: TradeQueryHelper,
        metrics_calculator: MetricsCalculator | None = None,
        *,
        config: ProviderConfig | None = None,
    ) -> None:
        self._account_data = account_data
        self._trade_helper = trade_helper
        self._metrics_calculator = metrics_calculator or MetricsCalculator()
        self._config = config or ProviderConfig()

    # ---------------------------------------------------------------------#
    # Public API
    # ---------------------------------------------------------------------#
    def get_snapshot(self, targets: DashboardTargets | None = None) -> DashboardSnapshot:
        """
        Build a dashboard snapshot with current account, position, and performance data.

        Args:
            targets: Optional dashboard targets loaded via `load_targets`.

        Returns:
            DashboardSnapshot populated with all dashboard data and metadata.

        Raises:
            AccountDataError: Propagates critical account data failures (caller handles).
        """
        generated_at = datetime.now(UTC)

        account_status = self._build_account_status()
        positions_raw = self._account_data.get_positions()
        positions_display = self._to_position_displays(positions_raw)

        metrics, warnings = self._compute_metrics(
            positions_raw=positions_raw,
            generated_at=generated_at,
        )

        data_age_seconds = max(
            0.0,
            (generated_at - account_status.last_updated).total_seconds(),
        )
        is_data_stale = data_age_seconds > self._config.staleness_ttl_seconds

        # Propagate stale-data warning for UI to display prominently.
        if is_data_stale:
            warnings.append(
                f"⚠️ Data may be stale: last updated "
                f"{int(data_age_seconds)}s ago (TTL={self._config.staleness_ttl_seconds}s)"
            )

        market_status: Literal["OPEN", "CLOSED"] = (
            "OPEN" if is_market_open(generated_at) else "CLOSED"
        )

        return DashboardSnapshot(
            account_status=account_status,
            positions=positions_display,
            performance_metrics=metrics,
            targets=targets,
            market_status=market_status,
            generated_at=generated_at,
            data_age_seconds=data_age_seconds,
            is_data_stale=is_data_stale,
            warnings=warnings,
        )

    def load_targets(self, config_path: Path | None = None) -> DashboardTargets | None:
        """
        Load dashboard targets from YAML configuration with graceful degradation.

        Args:
            config_path: Optional override path. Defaults to ProviderConfig.targets_path.

        Returns:
            DashboardTargets on success, otherwise None (missing/invalid file).
        """
        path = config_path or self._config.targets_path

        if not path.exists():
            logger.info(
                "Dashboard targets config not found at %s; proceeding without targets",
                path,
            )
            return None

        try:
            with path.open(encoding="utf-8") as handle:
                raw_config = yaml.safe_load(handle)
        except (OSError, yaml.YAMLError) as exc:
            logger.warning(
                "Failed to load dashboard targets from %s: %s", path, exc, exc_info=True
            )
            return None

        if not isinstance(raw_config, dict):
            logger.warning(
                "Dashboard targets config %s invalid: expected mapping root", path
            )
            return None

        required_fields = {
            "win_rate_target",
            "daily_pl_target",
            "trades_per_day_target",
            "max_drawdown_target",
        }

        if not required_fields.issubset(raw_config):
            missing = ", ".join(sorted(required_fields - set(raw_config)))
            logger.warning(
                "Dashboard targets config %s missing required fields: %s",
                path,
                missing,
            )
            return None

        try:
            avg_rr = raw_config.get("avg_risk_reward_target")
            return DashboardTargets(
                win_rate_target=float(raw_config["win_rate_target"]),
                daily_pl_target=Decimal(str(raw_config["daily_pl_target"])),
                trades_per_day_target=int(raw_config["trades_per_day_target"]),
                max_drawdown_target=Decimal(str(raw_config["max_drawdown_target"])),
                avg_risk_reward_target=float(avg_rr) if avg_rr is not None else None,
            )
        except (TypeError, ValueError, DecimalException) as exc:
            logger.warning(
                "Dashboard targets config %s contains invalid numeric values: %s",
                path,
                exc,
                exc_info=True,
            )
            return None
        except Exception as exc:  # Defensive catch for Decimal quantization errors
            logger.warning(
                "Dashboard targets config %s failed validation: %s",
                path,
                exc,
                exc_info=True,
            )
            return None

    # ---------------------------------------------------------------------#
    # Internal helpers
    # ---------------------------------------------------------------------#
    def _build_account_status(self) -> AccountStatus:
        """Fetch and compose account status dataclass."""
        account_balance = self._account_data.get_account_balance()

        buying_power_float = self._account_data.get_buying_power()
        buying_power = Decimal(str(buying_power_float))

        day_trade_count = self._account_data.get_day_trade_count()

        last_updated = account_balance.last_updated
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=UTC)
        else:
            last_updated = last_updated.astimezone(UTC)

        return AccountStatus(
            buying_power=buying_power,
            account_balance=account_balance.equity,
            cash_balance=account_balance.cash,
            day_trade_count=day_trade_count,
            last_updated=last_updated,
        )

    def _to_position_displays(
        self, positions: Iterable[Position]
    ) -> list[PositionDisplay]:
        """Convert AccountData positions into PositionDisplay structures."""
        displays: list[PositionDisplay] = []

        for position in positions:
            last_updated = position.last_updated
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=UTC)
            else:
                last_updated = last_updated.astimezone(UTC)

            displays.append(
                PositionDisplay(
                    symbol=position.symbol,
                    quantity=position.quantity,
                    entry_price=position.average_buy_price,
                    current_price=position.current_price,
                    unrealized_pl=position.profit_loss,
                    unrealized_pl_pct=position.profit_loss_pct,
                    last_updated=last_updated,
                )
            )

        # Sort by unrealized P&L descending for more actionable view (FR-002).
        displays.sort(key=lambda pos: pos.unrealized_pl, reverse=True)
        return displays

    def _compute_metrics(
        self,
        *,
        positions_raw: Iterable[Position],
        generated_at: datetime,
    ) -> tuple[PerformanceMetrics, list[str]]:
        """Load trades, calculate metrics, and surface any operator warnings."""
        warnings: list[str] = []
        trades: list[TradeRecord] = []

        today = generated_at.strftime("%Y-%m-%d")
        todays_log = self._trade_helper.log_dir / f"{today}.jsonl"

        try:
            trades = self._trade_helper.query_by_date_range(today, today)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Trade log query failed: %s", exc, exc_info=True)
            warnings.append(
                "Trade log query failed; performance metrics may be incomplete"
            )

        if not todays_log.exists():
            warnings.append(
                "Trade log not found, performance metrics unavailable"
                if not trades
                else "Trade log file missing; metrics calculated from in-memory data"
            )

        session_count = len(
            {trade.session_id for trade in trades if getattr(trade, "session_id", None)}
        )

        metrics = self._metrics_calculator.aggregate_metrics(
            trades=trades,
            positions=list(positions_raw),
            session_count=session_count,
        )

        return metrics, warnings
