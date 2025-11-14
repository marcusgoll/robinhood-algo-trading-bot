"""
Risk Management Configuration

Pattern: src/trading_bot/config.py OrderManagementConfig (lines 25-127)

Enforces Constitution v1.0.0:
- §Risk_Management: Positive risk parameters, min 1:1 risk-reward ratio
- §Code_Quality: Type hints required
- §Data_Integrity: Validate all inputs
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskManagementConfig:
    """
    Risk management configuration values.

    Supports global defaults with optional per-strategy overrides.

    ATR Configuration:
    - atr_enabled: Enable ATR-based dynamic stop calculation
    - atr_period: Lookback period for ATR calculation (Wilder's standard is 14)
    - atr_multiplier: Multiplier applied to ATR for stop distance
    - atr_recalc_threshold: % change in ATR that triggers stop recalculation

    Trade Management Rules:
    - enable_break_even_protection: Enable break-even stop adjustment
    - enable_scaling_in: Enable position scaling
    - enable_catastrophic_exit: Enable catastrophic exit protection
    - break_even_atr_multiple: ATR multiple for break-even trigger
    - scaling_atr_multiple: ATR multiple for scaling in
    - scaling_max_count: Maximum number of scale-ins
    - scaling_size_pct: Size of each scale-in as % of original position
    - catastrophic_exit_atr_multiple: ATR multiple for catastrophic exit
    """

    account_risk_pct: float
    min_risk_reward_ratio: float
    default_stop_pct: float
    trailing_enabled: bool
    pullback_lookback_candles: int
    trailing_breakeven_threshold: float
    atr_enabled: bool = False
    atr_period: int = 14
    atr_multiplier: float = 2.0
    atr_recalc_threshold: float = 0.20
    enable_break_even_protection: bool = True
    enable_scaling_in: bool = True
    enable_catastrophic_exit: bool = True
    break_even_atr_multiple: float = 2.0
    scaling_atr_multiple: float = 1.5
    scaling_max_count: int = 3
    scaling_size_pct: float = 0.5
    catastrophic_exit_atr_multiple: float = 3.0
    strategy_overrides: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "RiskManagementConfig":
        """Return default configuration."""
        return cls(
            account_risk_pct=1.0,
            min_risk_reward_ratio=2.0,
            default_stop_pct=2.0,
            trailing_enabled=True,
            pullback_lookback_candles=20,
            trailing_breakeven_threshold=0.5,
            atr_enabled=False,
            atr_period=14,
            atr_multiplier=2.0,
            atr_recalc_threshold=0.20,
            enable_break_even_protection=True,
            enable_scaling_in=True,
            enable_catastrophic_exit=True,
            break_even_atr_multiple=2.0,
            scaling_atr_multiple=1.5,
            scaling_max_count=3,
            scaling_size_pct=0.5,
            catastrophic_exit_atr_multiple=3.0,
            strategy_overrides={},
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "RiskManagementConfig":
        """Create configuration from JSON payload."""
        data = data or {}

        account_risk_pct = float(data.get("account_risk_pct", 1.0))
        min_risk_reward_ratio = float(data.get("min_risk_reward_ratio", 2.0))
        default_stop_pct = float(data.get("default_stop_pct", 2.0))
        trailing_enabled = bool(data.get("trailing_enabled", True))
        pullback_lookback_candles = int(data.get("pullback_lookback_candles", 20))
        trailing_breakeven_threshold = float(
            data.get("trailing_breakeven_threshold", 0.5)
        )
        atr_enabled = bool(data.get("atr_enabled", False))
        atr_period = int(data.get("atr_period", 14))
        atr_multiplier = float(data.get("atr_multiplier", 2.0))
        atr_recalc_threshold = float(data.get("atr_recalc_threshold", 0.20))
        enable_break_even_protection = bool(
            data.get("enable_break_even_protection", True)
        )
        enable_scaling_in = bool(data.get("enable_scaling_in", True))
        enable_catastrophic_exit = bool(data.get("enable_catastrophic_exit", True))
        break_even_atr_multiple = float(data.get("break_even_atr_multiple", 2.0))
        scaling_atr_multiple = float(data.get("scaling_atr_multiple", 1.5))
        scaling_max_count = int(data.get("scaling_max_count", 3))
        scaling_size_pct = float(data.get("scaling_size_pct", 0.5))
        catastrophic_exit_atr_multiple = float(
            data.get("catastrophic_exit_atr_multiple", 3.0)
        )

        # Validate risk parameters are positive
        if account_risk_pct <= 0:
            raise ValueError("risk_management.account_risk_pct must be > 0")
        if min_risk_reward_ratio < 1.0:
            raise ValueError("risk_management.min_risk_reward_ratio must be >= 1.0")
        if default_stop_pct <= 0:
            raise ValueError("risk_management.default_stop_pct must be > 0")
        if pullback_lookback_candles <= 0:
            raise ValueError("risk_management.pullback_lookback_candles must be > 0")
        if trailing_breakeven_threshold <= 0:
            raise ValueError("risk_management.trailing_breakeven_threshold must be > 0")

        # Validate percentages ≤ 100
        if account_risk_pct > 100:
            raise ValueError("risk_management.account_risk_pct must be <= 100")
        if default_stop_pct > 100:
            raise ValueError("risk_management.default_stop_pct must be <= 100")
        if trailing_breakeven_threshold > 100:
            raise ValueError(
                "risk_management.trailing_breakeven_threshold must be <= 100"
            )

        # Validate ATR parameters
        if atr_period <= 0:
            raise ValueError("risk_management.atr_period must be > 0")
        if atr_multiplier <= 0:
            raise ValueError("risk_management.atr_multiplier must be > 0")
        if atr_recalc_threshold <= 0:
            raise ValueError("risk_management.atr_recalc_threshold must be > 0")
        if atr_recalc_threshold > 1.0:
            raise ValueError("risk_management.atr_recalc_threshold must be <= 1.0")

        # Parse strategy overrides
        overrides: dict[str, dict[str, Any]] = {}
        overrides_raw = data.get("strategy_overrides") or {}
        if not isinstance(overrides_raw, Mapping):
            raise ValueError(
                "risk_management.strategy_overrides must be a mapping if provided"
            )

        for strategy, override in overrides_raw.items():
            if not isinstance(override, Mapping):
                raise ValueError(
                    f"risk_management.strategy_overrides.{strategy} must be an object"
                )
            override_dict: dict[str, Any] = {}

            # Validate override fields
            for key in (
                "account_risk_pct",
                "min_risk_reward_ratio",
                "default_stop_pct",
                "trailing_breakeven_threshold",
            ):
                if key in override and override[key] is not None:
                    value = float(override[key])  # type: ignore[arg-type]
                    if value <= 0:
                        raise ValueError(
                            f"risk_management.strategy_overrides.{strategy}.{key} must be > 0"
                        )
                    # Validate min_risk_reward_ratio >= 1.0
                    if key == "min_risk_reward_ratio" and value < 1.0:
                        raise ValueError(
                            f"risk_management.strategy_overrides.{strategy}.min_risk_reward_ratio must be >= 1.0"
                        )
                    # Validate percentages <= 100
                    if key in ("account_risk_pct", "default_stop_pct", "trailing_breakeven_threshold") and value > 100:
                        raise ValueError(
                            f"risk_management.strategy_overrides.{strategy}.{key} must be <= 100"
                        )
                    override_dict[key] = value

            # Boolean fields
            if "trailing_enabled" in override and override["trailing_enabled"] is not None:
                override_dict["trailing_enabled"] = bool(override["trailing_enabled"])

            # Integer fields
            if "pullback_lookback_candles" in override and override["pullback_lookback_candles"] is not None:
                value = int(override["pullback_lookback_candles"])  # type: ignore[arg-type]
                if value <= 0:
                    raise ValueError(
                        f"risk_management.strategy_overrides.{strategy}.pullback_lookback_candles must be > 0"
                    )
                override_dict["pullback_lookback_candles"] = value

            overrides[str(strategy)] = override_dict

        return cls(
            account_risk_pct=account_risk_pct,
            min_risk_reward_ratio=min_risk_reward_ratio,
            default_stop_pct=default_stop_pct,
            trailing_enabled=trailing_enabled,
            pullback_lookback_candles=pullback_lookback_candles,
            trailing_breakeven_threshold=trailing_breakeven_threshold,
            atr_enabled=atr_enabled,
            atr_period=atr_period,
            atr_multiplier=atr_multiplier,
            atr_recalc_threshold=atr_recalc_threshold,
            strategy_overrides=overrides,
        )

    def validate(self) -> None:
        """Validate configuration (redundant safety for runtime)."""
        if self.account_risk_pct <= 0:
            raise ValueError("account_risk_pct must be > 0")
        if self.min_risk_reward_ratio < 1.0:
            raise ValueError("min_risk_reward_ratio must be >= 1.0")
        if self.default_stop_pct <= 0:
            raise ValueError("default_stop_pct must be > 0")
        if self.pullback_lookback_candles <= 0:
            raise ValueError("pullback_lookback_candles must be > 0")
        if self.trailing_breakeven_threshold <= 0:
            raise ValueError("trailing_breakeven_threshold must be > 0")

        # Validate percentages ≤ 100
        if self.account_risk_pct > 100:
            raise ValueError("account_risk_pct must be <= 100")
        if self.default_stop_pct > 100:
            raise ValueError("default_stop_pct must be <= 100")
        if self.trailing_breakeven_threshold > 100:
            raise ValueError("trailing_breakeven_threshold must be <= 100")

        # Validate ATR parameters
        if self.atr_period <= 0:
            raise ValueError("atr_period must be > 0")
        if self.atr_multiplier <= 0:
            raise ValueError("atr_multiplier must be > 0")
        if self.atr_recalc_threshold <= 0:
            raise ValueError("atr_recalc_threshold must be > 0")
        if self.atr_recalc_threshold > 1.0:
            raise ValueError("atr_recalc_threshold must be <= 1.0")
