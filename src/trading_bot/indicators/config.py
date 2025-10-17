"""
Configuration for Technical Indicators Module

Dataclass-based configuration with validation in __post_init__.

Pattern: src/trading_bot/momentum/config.py (dataclass with validation)
Constitution §Data_Integrity: Validate all configuration parameters
"""

from dataclasses import dataclass, field


@dataclass
class IndicatorConfig:
    """
    Configuration for technical indicators (VWAP, EMA, MACD).

    Attributes:
        vwap_min_bars: Minimum intraday bars required for VWAP (default: 10)
        ema_periods: EMA period lengths to calculate (default: [9, 20])
        ema_proximity_threshold_pct: Threshold for "near EMA" detection (default: 2.0%)
        macd_fast_period: MACD fast EMA period (default: 12)
        macd_slow_period: MACD slow EMA period (default: 26)
        macd_signal_period: MACD signal line EMA period (default: 9)
        refresh_interval_seconds: Intraday indicator refresh interval (default: 300 = 5 minutes)

    Example:
        config = IndicatorConfig(vwap_min_bars=15, ema_proximity_threshold_pct=1.5)
    """

    vwap_min_bars: int = 10
    ema_periods: list[int] = field(default_factory=lambda: [9, 20])
    ema_proximity_threshold_pct: float = 2.0
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    refresh_interval_seconds: int = 300  # 5 minutes

    def __post_init__(self) -> None:
        """
        Validate configuration parameters after initialization.

        Raises:
            ValueError: If any parameter violates constraints

        Validation Rules:
            - All periods must be > 0
            - MACD fast < slow (standard MACD formula)
            - Refresh interval >= 60 seconds (minimum 1 minute)
            - EMA proximity threshold >= 0
            - VWAP minimum bars >= 1
        """
        # Validate VWAP minimum bars
        if self.vwap_min_bars < 1:
            raise ValueError(f"vwap_min_bars must be >= 1, got {self.vwap_min_bars}")

        # Validate EMA periods
        if not self.ema_periods:
            raise ValueError("ema_periods cannot be empty")

        for period in self.ema_periods:
            if period <= 0:
                raise ValueError(f"All EMA periods must be > 0, got {period}")

        # Validate EMA proximity threshold
        if self.ema_proximity_threshold_pct < 0:
            raise ValueError(
                f"ema_proximity_threshold_pct must be >= 0, got {self.ema_proximity_threshold_pct}"
            )

        # Validate MACD periods
        if self.macd_fast_period <= 0:
            raise ValueError(f"macd_fast_period must be > 0, got {self.macd_fast_period}")

        if self.macd_slow_period <= 0:
            raise ValueError(f"macd_slow_period must be > 0, got {self.macd_slow_period}")

        if self.macd_signal_period <= 0:
            raise ValueError(f"macd_signal_period must be > 0, got {self.macd_signal_period}")

        # Validate MACD fast < slow (standard MACD formula requirement)
        if self.macd_fast_period >= self.macd_slow_period:
            raise ValueError(
                f"macd_fast_period ({self.macd_fast_period}) must be < macd_slow_period ({self.macd_slow_period})"
            )

        # Validate refresh interval
        if self.refresh_interval_seconds < 60:
            raise ValueError(
                f"refresh_interval_seconds must be >= 60, got {self.refresh_interval_seconds}"
            )
