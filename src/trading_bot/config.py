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

from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import os
import json
from dotenv import load_dotenv

# Load .env file if exists (§Security: environment variables)
load_dotenv()


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
    robinhood_mfa_secret: Optional[str] = None
    robinhood_device_token: Optional[str] = None

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
        config_data: Dict[str, Any] = {}
        config_path = Path(config_file)

        if config_path.exists():
            with open(config_path, "r") as f:
                config_data = json.load(f)

        # Extract parameters from JSON with defaults
        trading = config_data.get("trading", {})
        risk = config_data.get("risk_management", {})
        phase = config_data.get("phase_progression", {})
        current_phase_name = phase.get("current_phase", "experience")
        phase_config = phase.get(current_phase_name, {})

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
            max_trades_per_day=int(phase_config.get("max_trades_per_day", 999)),
            # Paths
            config_file=config_path,
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

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.backtest_dir.mkdir(exist_ok=True)
