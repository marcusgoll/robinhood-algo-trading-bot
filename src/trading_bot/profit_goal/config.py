"""
Profit Goal Configuration Loading

Loads profit goal settings from environment variables with validation.

Constitution v1.0.0:
- §Security: Configuration from environment variables
- §Data_Integrity: Validate all configuration inputs
- §Risk_Management: Profit protection thresholds validated

Feature: daily-profit-goal-ma
Task: T008 - Configuration loader following dual loading pattern
"""

import logging
import os
from decimal import Decimal, InvalidOperation

from trading_bot.profit_goal.models import ProfitGoalConfig

logger = logging.getLogger(__name__)


def load_profit_goal_config() -> ProfitGoalConfig:
    """Load profit goal configuration from environment variables.

    Reads configuration from:
        - PROFIT_TARGET_DAILY: Daily profit target in dollars (default: 0 = disabled)
        - PROFIT_GIVEBACK_THRESHOLD: Drawdown threshold 0.10-0.90 (default: 0.50)

    Returns:
        ProfitGoalConfig: Validated configuration

    Raises:
        ValueError: If configuration values are invalid

    Example:
        >>> os.environ["PROFIT_TARGET_DAILY"] = "500"
        >>> os.environ["PROFIT_GIVEBACK_THRESHOLD"] = "0.50"
        >>> config = load_profit_goal_config()
        >>> assert config.target == Decimal("500")
        >>> assert config.threshold == Decimal("0.50")
        >>> assert config.enabled is True

    Note:
        Invalid values log warnings and fall back to safe defaults:
        - Invalid target → $0 (feature disabled)
        - Invalid threshold → 0.50 (50% giveback)
    """
    # Load target from environment (default: $0 = disabled)
    target_str = os.getenv("PROFIT_TARGET_DAILY", "0")
    target = _parse_decimal_with_fallback(
        value_str=target_str,
        field_name="PROFIT_TARGET_DAILY",
        default=Decimal("0"),
    )

    # Load threshold from environment (default: 0.50 = 50%)
    threshold_str = os.getenv("PROFIT_GIVEBACK_THRESHOLD", "0.50")
    threshold = _parse_decimal_with_fallback(
        value_str=threshold_str,
        field_name="PROFIT_GIVEBACK_THRESHOLD",
        default=Decimal("0.50"),
    )

    # Create and validate config (validation happens in __post_init__)
    try:
        config = ProfitGoalConfig(target=target, threshold=threshold)
        _log_config_loaded(config)
        return config
    except ValueError as e:
        # Validation failed - fall back to safe defaults
        logger.warning(
            "Profit goal config validation failed: %s. Using safe defaults "
            "(target=$0, threshold=0.50)",
            str(e),
        )
        return ProfitGoalConfig(target=Decimal("0"), threshold=Decimal("0.50"))


def _parse_decimal_with_fallback(
    value_str: str, field_name: str, default: Decimal
) -> Decimal:
    """Parse decimal value with fallback on error.

    Args:
        value_str: String value to parse
        field_name: Name of config field (for logging)
        default: Default value if parsing fails

    Returns:
        Decimal: Parsed value or default
    """
    try:
        return Decimal(value_str)
    except (InvalidOperation, ValueError) as e:
        logger.warning(
            "Invalid %s value '%s': %s. Using default: %s",
            field_name,
            value_str,
            str(e),
            default,
        )
        return default


def _log_config_loaded(config: ProfitGoalConfig) -> None:
    """Log loaded configuration for audit trail.

    Args:
        config: Loaded configuration
    """
    if config.enabled:
        logger.info(
            "Profit goal config loaded: target=$%s, threshold=%s (protection enabled)",
            config.target,
            config.threshold,
        )
    else:
        logger.info(
            "Profit goal config loaded: target=$0 (protection disabled)",
        )
