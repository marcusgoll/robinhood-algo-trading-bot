"""
Configuration for Pattern Detection Module

Dataclass-based configuration with validation in __post_init__.

Pattern: src/trading_bot/indicators/config.py (dataclass with validation)
Constitution §Data_Integrity: Validate all configuration parameters
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class BullFlagConfig:
    """
    Configuration for bull flag pattern detection.

    Attributes:
        min_flagpole_gain: Minimum flagpole gain percentage (default: 5.0%)
        max_flagpole_gain: Maximum flagpole gain percentage (default: 25.0%)
        min_flagpole_bars: Minimum bars in flagpole (default: 3)
        max_flagpole_bars: Maximum bars in flagpole (default: 15)
        min_consolidation_bars: Minimum bars in consolidation (default: 3)
        max_consolidation_bars: Maximum bars in consolidation (default: 10)
        min_retracement_pct: Minimum retracement percentage (default: 20.0%)
        max_retracement_pct: Maximum retracement percentage (default: 50.0%)
        min_breakout_volume_increase: Minimum volume increase on breakout (default: 30.0%)
        min_breakout_move_pct: Minimum price move on breakout (default: 1.0%)
        min_quality_score: Minimum pattern quality score (default: 60)
        min_risk_reward_ratio: Minimum risk/reward ratio (default: 2.0)
        volume_decay_threshold: Max volume increase threshold during
            consolidation (default: 0.9)

    Example:
        config = BullFlagConfig(min_flagpole_gain=Decimal('7.0'), min_quality_score=70)
    """

    min_flagpole_gain: Decimal = Decimal("5.0")
    max_flagpole_gain: Decimal = Decimal("25.0")
    min_flagpole_bars: int = 3
    max_flagpole_bars: int = 15
    min_consolidation_bars: int = 3
    max_consolidation_bars: int = 10
    min_retracement_pct: Decimal = Decimal("20.0")
    max_retracement_pct: Decimal = Decimal("50.0")
    min_breakout_volume_increase: Decimal = Decimal("30.0")
    min_breakout_move_pct: Decimal = Decimal("1.0")
    min_quality_score: int = 60
    min_risk_reward_ratio: Decimal = Decimal("2.0")
    volume_decay_threshold: Decimal = Decimal("0.9")

    def __post_init__(self) -> None:
        """
        Validate configuration parameters after initialization.

        Raises:
            ValueError: If any parameter violates constraints

        Validation Rules:
            - min_flagpole_gain < max_flagpole_gain
            - min_flagpole_bars < max_flagpole_bars
            - min_consolidation_bars < max_consolidation_bars
            - All numeric values must be positive
            - Retracement percentages must be 0-100
            - Quality score must be 0-100
            - Risk/reward ratio must be > 1
        """
        # Validate flagpole gain range
        if self.min_flagpole_gain <= 0:
            raise ValueError(
                f"min_flagpole_gain must be > 0, got {self.min_flagpole_gain}"
            )

        if self.max_flagpole_gain <= 0:
            raise ValueError(
                f"max_flagpole_gain must be > 0, got {self.max_flagpole_gain}"
            )

        if self.min_flagpole_gain >= self.max_flagpole_gain:
            min_gain = self.min_flagpole_gain
            max_gain = self.max_flagpole_gain
            raise ValueError(
                f"min_flagpole_gain ({min_gain}) must be < "
                f"max_flagpole_gain ({max_gain})"
            )

        # Validate flagpole bars range
        if self.min_flagpole_bars <= 0:
            raise ValueError(
                f"min_flagpole_bars must be > 0, got {self.min_flagpole_bars}"
            )

        if self.max_flagpole_bars <= 0:
            raise ValueError(
                f"max_flagpole_bars must be > 0, got {self.max_flagpole_bars}"
            )

        if self.min_flagpole_bars >= self.max_flagpole_bars:
            min_bars = self.min_flagpole_bars
            max_bars = self.max_flagpole_bars
            raise ValueError(
                f"min_flagpole_bars ({min_bars}) must be < "
                f"max_flagpole_bars ({max_bars})"
            )

        # Validate consolidation bars range
        if self.min_consolidation_bars <= 0:
            raise ValueError(
                f"min_consolidation_bars must be > 0, got {self.min_consolidation_bars}"
            )

        if self.max_consolidation_bars <= 0:
            raise ValueError(
                f"max_consolidation_bars must be > 0, got {self.max_consolidation_bars}"
            )

        if self.min_consolidation_bars >= self.max_consolidation_bars:
            min_cons = self.min_consolidation_bars
            max_cons = self.max_consolidation_bars
            raise ValueError(
                f"min_consolidation_bars ({min_cons}) must be < "
                f"max_consolidation_bars ({max_cons})"
            )

        # Validate retracement percentages
        if self.min_retracement_pct < 0 or self.min_retracement_pct > 100:
            raise ValueError(
                f"min_retracement_pct must be 0-100, got {self.min_retracement_pct}"
            )

        if self.max_retracement_pct < 0 or self.max_retracement_pct > 100:
            raise ValueError(
                f"max_retracement_pct must be 0-100, got {self.max_retracement_pct}"
            )

        if self.min_retracement_pct >= self.max_retracement_pct:
            min_ret = self.min_retracement_pct
            max_ret = self.max_retracement_pct
            raise ValueError(
                f"min_retracement_pct ({min_ret}) must be < "
                f"max_retracement_pct ({max_ret})"
            )

        # Validate breakout volume increase
        if self.min_breakout_volume_increase <= 0:
            vol_inc = self.min_breakout_volume_increase
            raise ValueError(
                f"min_breakout_volume_increase must be > 0, got {vol_inc}"
            )

        # Validate breakout move percentage
        if self.min_breakout_move_pct <= 0:
            raise ValueError(
                f"min_breakout_move_pct must be > 0, got {self.min_breakout_move_pct}"
            )

        # Validate quality score
        if self.min_quality_score < 0 or self.min_quality_score > 100:
            raise ValueError(
                f"min_quality_score must be 0-100, got {self.min_quality_score}"
            )

        # Validate risk/reward ratio
        if self.min_risk_reward_ratio <= 1:
            raise ValueError(
                f"min_risk_reward_ratio must be > 1, got {self.min_risk_reward_ratio}"
            )

        # Validate volume decay threshold
        if self.volume_decay_threshold <= 0:
            raise ValueError(
                f"volume_decay_threshold must be > 0, got {self.volume_decay_threshold}"
            )
