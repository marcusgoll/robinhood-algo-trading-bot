#!/usr/bin/env python3
"""
Crypto Trading Configuration

Defines crypto-specific configuration parameters for 24/7 trading.

Key differences from stock trading:
- 24/7 markets (no trading hours restrictions)
- Higher volatility (wider stops, different position sizing)
- Fractional trading (0.01 BTC, not 100 shares)
- Interval-based scheduling (every 2hr, 5min) vs time-based (9:30am, 4pm)
"""

import os
from dataclasses import dataclass, field
from typing import List
from collections.abc import Mapping
from typing import Any


@dataclass
class CryptoConfig:
    """
    Configuration for 24/7 cryptocurrency trading.

    Supports both paper and live trading via Alpaca.
    """

    # Enable/disable crypto trading
    enabled: bool = True

    # Trading mode
    mode: str = "paper"  # "paper" or "live"

    # Crypto symbols to trade (Alpaca format)
    symbols: List[str] = field(default_factory=lambda: [
        "BTC/USD",   # Bitcoin
        "ETH/USD",   # Ethereum
        "LTC/USD",   # Litecoin
        "BCH/USD",   # Bitcoin Cash
        "LINK/USD",  # Chainlink
        "UNI/USD",   # Uniswap
        "AVAX/USD",  # Avalanche
        "MATIC/USD", # Polygon
    ])

    # Scheduling intervals (24/7 operation)
    screening_interval_hours: int = 2    # Screen every 2 hours
    monitoring_interval_minutes: int = 5  # Check positions every 5 minutes
    rebalance_interval_hours: int = 24   # Daily rebalancing

    # Risk management (crypto-specific - higher volatility)
    max_position_pct: float = 3.0       # Max 3% per position (conservative)
    max_daily_loss_pct: float = 5.0     # Daily loss limit
    stop_loss_pct: float = 5.0          # Wider stops due to volatility (vs 2% stocks)
    risk_reward_ratio: float = 2.0      # 1:2 risk/reward minimum
    position_size_usd: float = 100.0    # Default position size in USD

    # Technical indicators (crypto-tuned)
    rsi_overbought: int = 75           # RSI overbought threshold
    rsi_oversold: int = 30             # RSI oversold threshold
    min_volume_ratio: float = 150.0   # Minimum 24hr volume ratio

    # LLM budget allocation (crypto share of daily budget)
    llm_budget_pct: float = 0.5  # 50% of daily LLM budget for crypto

    VALID_MODES = {"paper", "live"}

    @classmethod
    def default(cls) -> "CryptoConfig":
        """Return default crypto configuration."""
        return cls()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "CryptoConfig":
        """
        Create configuration from JSON payload (config.json).

        Args:
            data: Dictionary from config.json['crypto'] section

        Returns:
            CryptoConfig instance

        Raises:
            ValueError: If configuration is invalid
        """
        if data is None:
            return cls.default()

        # Basic settings
        enabled = bool(data.get("enabled", True))
        mode = data.get("mode", "paper")

        if mode not in cls.VALID_MODES:
            raise ValueError(f"Invalid crypto mode: {mode}. Must be 'paper' or 'live'")

        # Symbols
        symbols = data.get("symbols", cls.default().symbols)
        if not isinstance(symbols, list) or not symbols:
            raise ValueError("crypto.symbols must be a non-empty list")

        # Validate symbol format (should be like BTC/USD, ETH/USD)
        for symbol in symbols:
            if "/" not in symbol:
                raise ValueError(f"Invalid crypto symbol format: {symbol}. Expected format: BTC/USD")

        # Scheduling intervals (support both flat and nested structure)
        scheduling = data.get("scheduling", {})
        screening_interval = int(data.get("screening_interval_hours", scheduling.get("screening_interval_hours", 2)))
        monitoring_interval = int(data.get("monitoring_interval_minutes", scheduling.get("monitoring_interval_minutes", 5)))
        rebalance_interval = int(data.get("rebalance_interval_hours", scheduling.get("rebalance_interval_hours", 24)))

        if screening_interval <= 0:
            raise ValueError("screening_interval_hours must be > 0")
        if monitoring_interval <= 0:
            raise ValueError("monitoring_interval_minutes must be > 0")
        if rebalance_interval <= 0:
            raise ValueError("rebalance_interval_hours must be > 0")

        # Risk management (support both flat and nested structure)
        risk = data.get("risk_management", {})
        max_position_pct = float(data.get("max_position_pct", risk.get("max_position_pct", 3.0)))
        max_daily_loss_pct = float(data.get("max_daily_loss_pct", risk.get("max_daily_loss_pct", 5.0)))
        stop_loss_pct = float(data.get("stop_loss_pct", risk.get("stop_loss_pct", 5.0)))
        risk_reward_ratio = float(data.get("risk_reward_ratio", risk.get("risk_reward_ratio", 2.0)))
        position_size_usd = float(data.get("position_size_usd", risk.get("position_size_usd", 100.0)))

        # Validate risk parameters
        if max_position_pct <= 0 or max_position_pct > 100:
            raise ValueError("max_position_pct must be between 0 and 100")
        if max_daily_loss_pct <= 0 or max_daily_loss_pct > 100:
            raise ValueError("max_daily_loss_pct must be between 0 and 100")
        if stop_loss_pct <= 0 or stop_loss_pct > 100:
            raise ValueError("stop_loss_pct must be between 0 and 100")
        if risk_reward_ratio <= 0:
            raise ValueError("risk_reward_ratio must be > 0")
        if position_size_usd <= 0:
            raise ValueError("position_size_usd must be > 0")

        # Technical indicators
        indicators = data.get("technical_indicators", {})
        rsi_overbought = int(indicators.get("rsi_overbought", 75))
        rsi_oversold = int(indicators.get("rsi_oversold", 30))
        min_volume_ratio = float(indicators.get("min_volume_ratio", 150.0))

        if not (50 <= rsi_overbought <= 100):
            raise ValueError("rsi_overbought must be between 50 and 100")
        if not (0 <= rsi_oversold <= 50):
            raise ValueError("rsi_oversold must be between 0 and 50")
        if rsi_oversold >= rsi_overbought:
            raise ValueError("rsi_oversold must be < rsi_overbought")
        if min_volume_ratio <= 0:
            raise ValueError("min_volume_ratio must be > 0")

        # LLM budget
        llm_budget_pct = float(data.get("llm_budget_pct", 0.5))
        if not (0 < llm_budget_pct <= 1):
            raise ValueError("llm_budget_pct must be between 0 and 1")

        return cls(
            enabled=enabled,
            mode=mode,
            symbols=symbols,
            screening_interval_hours=screening_interval,
            monitoring_interval_minutes=monitoring_interval,
            rebalance_interval_hours=rebalance_interval,
            max_position_pct=max_position_pct,
            max_daily_loss_pct=max_daily_loss_pct,
            stop_loss_pct=stop_loss_pct,
            risk_reward_ratio=risk_reward_ratio,
            position_size_usd=position_size_usd,
            rsi_overbought=rsi_overbought,
            rsi_oversold=rsi_oversold,
            min_volume_ratio=min_volume_ratio,
            llm_budget_pct=llm_budget_pct,
        )

    @classmethod
    def from_env(cls) -> "CryptoConfig":
        """
        Load crypto configuration from environment variables.

        Useful for overriding config.json settings via ENV vars.

        Environment variables:
            CRYPTO_ENABLED: Enable/disable crypto trading (true/false)
            CRYPTO_MODE: Trading mode (paper/live)
            CRYPTO_SYMBOLS: Comma-separated list (BTC/USD,ETH/USD)
            CRYPTO_SCREENING_INTERVAL_HOURS: Screening interval
            CRYPTO_MONITORING_INTERVAL_MINUTES: Monitoring interval
            CRYPTO_STOP_LOSS_PCT: Stop loss percentage

        Returns:
            CryptoConfig instance
        """
        enabled = os.getenv("CRYPTO_ENABLED", "true").lower() in ("true", "1", "yes")
        mode = os.getenv("CRYPTO_MODE", "paper")

        symbols_env = os.getenv("CRYPTO_SYMBOLS")
        if symbols_env:
            symbols = [s.strip() for s in symbols_env.split(",")]
        else:
            symbols = cls.default().symbols

        screening_interval = int(os.getenv("CRYPTO_SCREENING_INTERVAL_HOURS", "2"))
        monitoring_interval = int(os.getenv("CRYPTO_MONITORING_INTERVAL_MINUTES", "5"))

        stop_loss_pct = float(os.getenv("CRYPTO_STOP_LOSS_PCT", "5.0"))
        max_position_pct = float(os.getenv("CRYPTO_MAX_POSITION_PCT", "3.0"))

        return cls(
            enabled=enabled,
            mode=mode,
            symbols=symbols,
            screening_interval_hours=screening_interval,
            monitoring_interval_minutes=monitoring_interval,
            stop_loss_pct=stop_loss_pct,
            max_position_pct=max_position_pct,
        )

    def get_crypto_budget_usd(self, total_daily_budget: float) -> float:
        """
        Calculate crypto's share of the daily LLM budget.

        Args:
            total_daily_budget: Total daily LLM budget in USD

        Returns:
            Crypto budget in USD
        """
        return total_daily_budget * self.llm_budget_pct

    def is_crypto_symbol(self, symbol: str) -> bool:
        """Check if a symbol is a cryptocurrency."""
        return "/" in symbol or symbol in self.symbols
