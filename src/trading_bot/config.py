"""
Configuration Management

Enforces Constitution v1.0.0:
- §Security: No credentials in code, use environment variables
- §Code_Quality: Type hints required
- §Data_Integrity: Validate all inputs

Dual configuration system:
- .env: Credentials (username, password, MFA secret)
- config.json: Trading parameters (position sizes, hours, strategy)
"""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from trading_bot.risk_management.config import RiskManagementConfig

# Load .env file if exists (§Security: environment variables)
load_dotenv()


@dataclass
class OrderManagementConfig:
    """
    Order management configuration values.

    Supports global defaults with optional per-strategy overrides.
    """

    offset_mode: str
    buy_offset: float
    sell_offset: float
    max_slippage_pct: float
    poll_interval_seconds: int
    strategy_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    VALID_OFFSET_MODES = {"bps", "absolute"}

    @classmethod
    def default(cls) -> "OrderManagementConfig":
        """Return default configuration."""
        return cls(
            offset_mode="bps",
            buy_offset=15.0,
            sell_offset=10.0,
            max_slippage_pct=0.5,
            poll_interval_seconds=15,
            strategy_overrides={},
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "OrderManagementConfig":
        """Create configuration from JSON payload."""
        data = data or {}

        offset_mode = data.get("offset_mode", "bps")
        if offset_mode not in cls.VALID_OFFSET_MODES:
            raise ValueError(f"Invalid order_management.offset_mode: {offset_mode}")

        buy_offset = float(data.get("buy_offset", 15.0))
        sell_offset = float(data.get("sell_offset", 10.0))
        max_slippage_pct = float(data.get("max_slippage_pct", 0.5))
        poll_interval_seconds = int(data.get("poll_interval_seconds", 15))

        if buy_offset < 0:
            raise ValueError("order_management.buy_offset must be >= 0")
        if sell_offset < 0:
            raise ValueError("order_management.sell_offset must be >= 0")
        if max_slippage_pct <= 0:
            raise ValueError("order_management.max_slippage_pct must be > 0")
        if poll_interval_seconds <= 0:
            raise ValueError("order_management.poll_interval_seconds must be > 0")

        overrides: dict[str, dict[str, Any]] = {}
        overrides_raw = data.get("strategy_overrides") or {}
        if not isinstance(overrides_raw, Mapping):
            raise ValueError("order_management.strategy_overrides must be a mapping if provided")

        for strategy, override in overrides_raw.items():
            if not isinstance(override, Mapping):
                raise ValueError(
                    f"order_management.strategy_overrides.{strategy} must be an object"
                )
            override_dict: dict[str, float] = {}

            override_mode = override.get("offset_mode")
            if override_mode is not None:
                if override_mode not in cls.VALID_OFFSET_MODES:
                    raise ValueError(
                        f"Invalid offset_mode for strategy {strategy}: {override_mode}"
                    )
                override_dict["offset_mode"] = override_mode  # type: ignore[assignment]

            for key in ("buy_offset", "sell_offset", "max_slippage_pct"):
                if key in override and override[key] is not None:
                    value = float(override[key])  # type: ignore[arg-type]
                    if value < 0:
                        raise ValueError(
                            f"order_management.strategy_overrides.{strategy}.{key} must be >= 0"
                        )
                    override_dict[key] = value

            overrides[str(strategy)] = override_dict

        return cls(
            offset_mode=offset_mode,
            buy_offset=buy_offset,
            sell_offset=sell_offset,
            max_slippage_pct=max_slippage_pct,
            poll_interval_seconds=poll_interval_seconds,
            strategy_overrides=overrides,
        )

    def validate(self) -> None:
        """Validate configuration (redundant safety for runtime)."""
        if self.offset_mode not in self.VALID_OFFSET_MODES:
            raise ValueError(f"Invalid offset_mode: {self.offset_mode}")
        if self.buy_offset < 0 or self.sell_offset < 0:
            raise ValueError("buy_offset and sell_offset must be >= 0")
        if self.max_slippage_pct <= 0:
            raise ValueError("max_slippage_pct must be > 0")
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be > 0")


@dataclass
class Config:
    """
    Trading bot configuration.

    Dual configuration system:
    - .env: Credentials (§Security: from environment)
    - config.json: Trading parameters (§Risk_Management)
    """

    # Robinhood API credentials (§Security: from .env)
    robinhood_username: str
    robinhood_password: str
    robinhood_mfa_secret: str | None = None
    robinhood_device_token: str | None = None

    # Trading mode (§Risk_Management)
    paper_trading: bool = True

    # Trading hours (§Risk_Management: limit trading window)
    trading_start_time: str = "07:00"
    trading_end_time: str = "10:00"
    trading_timezone: str = "America/New_York"

    # Risk parameters (§Risk_Management)
    max_position_pct: float = 5.0
    max_daily_loss_pct: float = 3.0
    max_consecutive_losses: int = 3
    position_size_shares: int = 100
    stop_loss_pct: float = 2.0
    risk_reward_ratio: float = 2.0

    # Phase progression (§Safety_First)
    current_phase: str = "experience"
    max_trades_per_day: int = 999

    # Data paths
    data_dir: Path = Path("data")
    logs_dir: Path = Path("logs")
    backtest_dir: Path = Path("backtests")
    config_file: Path = Path("config.json")
    order_management: OrderManagementConfig = field(
        default_factory=OrderManagementConfig.default
    )
    risk_management: RiskManagementConfig = field(
        default_factory=RiskManagementConfig.default
    )

    @classmethod
    def from_env_and_json(cls, config_file: str = "config.json") -> "Config":
        """
        Load configuration from .env (credentials) and config.json (parameters).

        Dual configuration system (Constitution v1.0.0):
        - .env: Credentials (username, password, MFA secret) - §Security
        - config.json: Trading parameters (position sizes, hours, strategy)

        Args:
            config_file: Path to config.json file

        Returns:
            Config instance

        Raises:
            ValueError: If required environment variables missing
            FileNotFoundError: If config.json missing (will use defaults)
        """
        # Load credentials from .env (required)
        username = os.getenv("ROBINHOOD_USERNAME")
        password = os.getenv("ROBINHOOD_PASSWORD")

        if not username or not password:
            raise ValueError(
                "Missing required environment variables: "
                "ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD must be set in .env file"
            )

        # Load trading parameters from config.json (optional)
        config_data: dict[str, Any] = {}
        config_path = Path(config_file)

        if config_path.exists():
            with open(config_path) as f:
                config_data = json.load(f)

        # Extract parameters from JSON with defaults
        trading = config_data.get("trading", {})
        risk = config_data.get("risk_management", {})
        phase = config_data.get("phase_progression", {})
        current_phase_name = phase.get("current_phase", "experience")
        phase_config = phase.get(current_phase_name, {})
        order_management_config = OrderManagementConfig.from_dict(
            config_data.get("order_management")
        )
        risk_management_config = RiskManagementConfig.from_dict(
            config_data.get("risk_management")
        )

        # Handle max_trades_per_day: None means unlimited (999 sentinel)
        max_trades = phase_config.get("max_trades_per_day", 999)
        max_trades_per_day = 999 if max_trades is None else int(max_trades)

        return cls(
            # Credentials from .env
            robinhood_username=username,
            robinhood_password=password,
            robinhood_mfa_secret=os.getenv("ROBINHOOD_MFA_SECRET"),
            robinhood_device_token=os.getenv("ROBINHOOD_DEVICE_TOKEN"),
            # Trading mode
            paper_trading=trading.get("mode", "paper") == "paper",
            # Trading hours
            trading_start_time=trading.get("hours", {}).get("start_time", "07:00"),
            trading_end_time=trading.get("hours", {}).get("end_time", "10:00"),
            trading_timezone=trading.get("hours", {}).get("timezone", "America/New_York"),
            # Risk parameters
            max_position_pct=float(risk.get("max_position_pct", 5.0)),
            max_daily_loss_pct=float(risk.get("max_daily_loss_pct", 3.0)),
            max_consecutive_losses=int(risk.get("max_consecutive_losses", 3)),
            position_size_shares=int(risk.get("position_size_shares", 100)),
            stop_loss_pct=float(risk.get("stop_loss_pct", 2.0)),
            risk_reward_ratio=float(risk.get("risk_reward_ratio", 2.0)),
            # Phase progression
            current_phase=current_phase_name,
            max_trades_per_day=max_trades_per_day,
            # Paths
            config_file=config_path,
            order_management=order_management_config,
            risk_management=risk_management_config,
        )

    @classmethod
    def from_env(cls) -> "Config":
        """
        Backward compatibility: Load from environment variables only.

        DEPRECATED: Use from_env_and_json() for full configuration support.

        Returns:
            Config instance with default trading parameters
        """
        return cls.from_env_and_json()

    def validate(self) -> None:
        """
        Validate configuration values (§Data_Integrity).

        Raises:
            ValueError: If configuration invalid
        """
        # Risk parameter validation
        if self.max_position_pct <= 0 or self.max_position_pct > 100:
            raise ValueError(
                f"Invalid max_position_pct: {self.max_position_pct} "
                "(must be 0-100)"
            )

        if self.max_daily_loss_pct <= 0:
            raise ValueError(
                f"Invalid max_daily_loss_pct: {self.max_daily_loss_pct} "
                "(must be > 0)"
            )

        if self.max_consecutive_losses < 1:
            raise ValueError(
                f"Invalid max_consecutive_losses: {self.max_consecutive_losses} "
                "(must be >= 1)"
            )

        if self.position_size_shares < 1:
            raise ValueError(
                f"Invalid position_size_shares: {self.position_size_shares} "
                "(must be >= 1)"
            )

        if self.stop_loss_pct <= 0 or self.stop_loss_pct > 100:
            raise ValueError(
                f"Invalid stop_loss_pct: {self.stop_loss_pct} "
                "(must be 0-100)"
            )

        if self.risk_reward_ratio <= 0:
            raise ValueError(
                f"Invalid risk_reward_ratio: {self.risk_reward_ratio} "
                "(must be > 0)"
            )

        # Trading hours validation
        if not self.trading_start_time or not self.trading_end_time:
            raise ValueError(
                "Trading hours must be specified (start_time and end_time required)"
            )

        # Phase validation
        valid_phases = ["experience", "proof", "trial", "scaling"]
        if self.current_phase not in valid_phases:
            raise ValueError(
                f"Invalid current_phase: {self.current_phase} "
                f"(must be one of: {', '.join(valid_phases)})"
            )

        if self.max_trades_per_day < 1:
            raise ValueError(
                f"Invalid max_trades_per_day: {self.max_trades_per_day} "
                "(must be >= 1)"
            )

        self.order_management.validate()
        self.risk_management.validate()

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.backtest_dir.mkdir(exist_ok=True)
