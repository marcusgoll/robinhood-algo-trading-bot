"""
Emotional Control Configuration

Configuration for emotional control thresholds and behavior.

Constitution v1.0.0:
- §Risk_Management: Configurable thresholds for loss triggers
- §Code_Quality: Type hints and validation required
- §Data_Integrity: Validate all inputs

Feature: emotional-control-me
Task: T006 - Configuration model with defaults
"""

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass
class EmotionalControlConfig:
    """Configuration for emotional control mechanisms (T006).

    Defines thresholds for activation triggers, recovery requirements,
    and position sizing adjustments.

    Attributes:
        enabled: Whether emotional control is active
        single_loss_threshold_pct: Single trade loss % to trigger (e.g., 3.0 = 3%)
        consecutive_loss_threshold: Number of consecutive losses to trigger
        recovery_win_threshold: Number of consecutive wins required for recovery
        position_size_multiplier_active: Multiplier when control is active (0.25 = 25%)
        state_file_path: Path to state persistence file
        event_log_dir: Directory for JSONL event logs

    Validation Rules (from data-model.md):
        - single_loss_threshold_pct must be > 0 and <= 100
        - consecutive_loss_threshold must be >= 1
        - recovery_win_threshold must be >= 1
        - position_size_multiplier_active must be > 0 and < 1.0
        - state_file_path and event_log_dir must be valid paths

    Example:
        >>> config = EmotionalControlConfig.default()
        >>> assert config.single_loss_threshold_pct == Decimal("3.0")
        >>> assert config.consecutive_loss_threshold == 3
        >>> assert config.recovery_win_threshold == 3
        >>> assert config.position_size_multiplier_active == Decimal("0.25")
    """

    enabled: bool
    single_loss_threshold_pct: Decimal
    consecutive_loss_threshold: int
    recovery_win_threshold: int
    position_size_multiplier_active: Decimal
    state_file_path: Path
    event_log_dir: Path

    def __post_init__(self) -> None:
        """Validate configuration values after initialization.

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate single loss threshold
        if self.single_loss_threshold_pct <= 0:
            raise ValueError(
                f"single_loss_threshold_pct must be > 0, got {self.single_loss_threshold_pct}"
            )
        if self.single_loss_threshold_pct > 100:
            raise ValueError(
                f"single_loss_threshold_pct must be <= 100, got {self.single_loss_threshold_pct}"
            )

        # Validate consecutive thresholds
        if self.consecutive_loss_threshold < 1:
            raise ValueError(
                f"consecutive_loss_threshold must be >= 1, got {self.consecutive_loss_threshold}"
            )
        if self.recovery_win_threshold < 1:
            raise ValueError(
                f"recovery_win_threshold must be >= 1, got {self.recovery_win_threshold}"
            )

        # Validate position size multiplier
        if self.position_size_multiplier_active <= 0:
            raise ValueError(
                f"position_size_multiplier_active must be > 0, got {self.position_size_multiplier_active}"
            )
        if self.position_size_multiplier_active >= 1:
            raise ValueError(
                f"position_size_multiplier_active must be < 1.0, got {self.position_size_multiplier_active}"
            )

    @classmethod
    def default(cls) -> "EmotionalControlConfig":
        """Return default v1.0 configuration with hardcoded thresholds.

        Returns:
            EmotionalControlConfig with v1.0 defaults:
            - 3% single loss threshold
            - 3 consecutive losses trigger
            - 3 consecutive wins for recovery
            - 25% position size when active
        """
        return cls(
            enabled=True,
            single_loss_threshold_pct=Decimal("3.0"),
            consecutive_loss_threshold=3,
            recovery_win_threshold=3,
            position_size_multiplier_active=Decimal("0.25"),
            state_file_path=Path("logs/emotional_control/state.json"),
            event_log_dir=Path("logs/emotional_control"),
        )

    @classmethod
    def from_env(cls) -> "EmotionalControlConfig":
        """Load configuration from environment variables.

        Environment Variables:
            EMOTIONAL_CONTROL_ENABLED: Enable/disable feature (default: true)

        Note: Thresholds are hardcoded for v1.0 - environment config reserved
        for future versions.

        Returns:
            EmotionalControlConfig with enabled flag from environment
        """
        enabled_str = os.getenv("EMOTIONAL_CONTROL_ENABLED", "true").lower()
        enabled = enabled_str in ("true", "1", "yes", "on")

        config = cls.default()
        config.enabled = enabled
        return config
