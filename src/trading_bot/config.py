"""
Configuration Management

Enforces Constitution v1.0.0:
- §Security: No credentials in code, use environment variables
- §Code_Quality: Type hints required
- §Data_Integrity: Validate all inputs
"""

from typing import Optional
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file if exists (§Security: environment variables)
load_dotenv()


@dataclass
class Config:
    """
    Trading bot configuration.

    All sensitive values loaded from environment variables (§Security).
    """

    # Robinhood API credentials (§Security: from environment)
    robinhood_username: str
    robinhood_password: str
    robinhood_device_token: Optional[str] = None

    # Trading parameters (§Risk_Management)
    paper_trading: bool = True
    max_position_pct: float = 5.0
    max_daily_loss_pct: float = 3.0
    max_consecutive_losses: int = 3

    # Data paths
    data_dir: Path = Path("data")
    logs_dir: Path = Path("logs")
    backtest_dir: Path = Path("backtests")

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables (§Security).

        Required environment variables:
        - ROBINHOOD_USERNAME
        - ROBINHOOD_PASSWORD

        Optional:
        - ROBINHOOD_DEVICE_TOKEN
        - PAPER_TRADING (default: True)
        - MAX_POSITION_PCT (default: 5.0)
        - MAX_DAILY_LOSS_PCT (default: 3.0)
        - MAX_CONSECUTIVE_LOSSES (default: 3)

        Returns:
            Config instance

        Raises:
            ValueError: If required environment variables missing
        """
        username = os.getenv("ROBINHOOD_USERNAME")
        password = os.getenv("ROBINHOOD_PASSWORD")

        if not username or not password:
            raise ValueError(
                "Missing required environment variables: "
                "ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD must be set"
            )

        return cls(
            robinhood_username=username,
            robinhood_password=password,
            robinhood_device_token=os.getenv("ROBINHOOD_DEVICE_TOKEN"),
            paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
            max_position_pct=float(os.getenv("MAX_POSITION_PCT", "5.0")),
            max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "3.0")),
            max_consecutive_losses=int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3")),
        )

    def validate(self) -> None:
        """
        Validate configuration values (§Data_Integrity).

        Raises:
            ValueError: If configuration invalid
        """
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

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.backtest_dir.mkdir(exist_ok=True)
