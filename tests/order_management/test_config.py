import json
from pathlib import Path

import pytest

from src.trading_bot.config import Config


@pytest.fixture(autouse=True)
def _credentials_env(monkeypatch):
    monkeypatch.setenv("ROBINHOOD_USERNAME", "test@example.com")
    monkeypatch.setenv("ROBINHOOD_PASSWORD", "super-secret")


def _write_config(tmp_path: Path, payload: dict) -> Path:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload))
    return config_path


def test_order_management_config_defaults_when_missing(tmp_path: Path):
    config_path = _write_config(
        tmp_path,
        {
            "trading": {},
            "risk_management": {},
        },
    )

    cfg = Config.from_env_and_json(config_file=str(config_path))

    assert cfg.order_management.offset_mode == "bps"
    assert cfg.order_management.buy_offset == pytest.approx(15.0)
    assert cfg.order_management.sell_offset == pytest.approx(10.0)
    assert cfg.order_management.max_slippage_pct == pytest.approx(0.5)
    assert cfg.order_management.poll_interval_seconds == 15
    assert cfg.order_management.strategy_overrides == {}


def test_order_management_strategy_override_applied(tmp_path: Path):
    config_path = _write_config(
        tmp_path,
        {
            "order_management": {
                "offset_mode": "bps",
                "buy_offset": 20,
                "sell_offset": 5,
                "max_slippage_pct": 0.4,
                "poll_interval_seconds": 12,
                "strategy_overrides": {
                    "bull_flag_breakout": {
                        "buy_offset": 30,
                        "sell_offset": 12,
                    }
                },
            }
        },
    )

    cfg = Config.from_env_and_json(config_file=str(config_path))

    assert cfg.order_management.buy_offset == pytest.approx(20.0)
    assert cfg.order_management.strategy_overrides["bull_flag_breakout"]["buy_offset"] == pytest.approx(30.0)
    assert cfg.order_management.strategy_overrides["bull_flag_breakout"]["sell_offset"] == pytest.approx(12.0)
    assert cfg.order_management.strategy_overrides["bull_flag_breakout"].get("max_slippage_pct") is None


def test_order_management_invalid_offset_mode_raises(tmp_path: Path):
    config_path = _write_config(
        tmp_path,
        {
            "order_management": {
                "offset_mode": "invalid",
                "buy_offset": 10,
                "sell_offset": 10,
                "max_slippage_pct": 1.0,
            }
        },
    )

    with pytest.raises(ValueError, match="offset_mode"):
        Config.from_env_and_json(config_file=str(config_path))
