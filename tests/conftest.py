"""
Test Configuration and Fixtures

Provides shared fixtures for all test modules.
Constitution v1.0.0: Support for startup sequence testing.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock
from typing import Generator


@pytest.fixture
def valid_env_file() -> Path:
    """Returns path to valid .env fixture."""
    return Path(__file__).parent / "fixtures" / "startup" / ".env.valid"


@pytest.fixture
def valid_config_file() -> Path:
    """Returns path to valid config.json fixture."""
    return Path(__file__).parent / "fixtures" / "startup" / "config.valid.json"


@pytest.fixture
def tmp_logs_dir(tmp_path: Path) -> Path:
    """Temporary logs directory for testing."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


@pytest.fixture
def mock_config() -> Mock:
    """Mock Config instance for testing."""
    from src.trading_bot.config import Config

    # Create a mock config with typical test values
    config = Mock(spec=Config)

    # Robinhood credentials
    config.robinhood_username = "test_user"
    config.robinhood_password = "test_pass"
    config.robinhood_mfa_secret = None
    config.robinhood_device_token = None

    # Trading mode
    config.paper_trading = True

    # Trading hours
    config.trading_start_time = "07:00"
    config.trading_end_time = "10:00"
    config.trading_timezone = "America/New_York"

    # Risk parameters
    config.max_position_pct = 5.0
    config.max_daily_loss_pct = 3.0
    config.max_consecutive_losses = 3
    config.position_size_shares = 100
    config.stop_loss_pct = 2.0
    config.risk_reward_ratio = 2.0

    # Phase progression
    config.current_phase = "experience"
    config.max_trades_per_day = 999

    # Data paths
    config.data_dir = Path("data")
    config.logs_dir = Path("logs")
    config.backtest_dir = Path("backtests")
    config.config_file = Path("config.json")

    return config
