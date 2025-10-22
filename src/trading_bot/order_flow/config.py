"""
Order Flow Monitoring Configuration

Configuration dataclass for order flow detection system.
Provides defaults from spec.md and environment variable loading.

Pattern: Follows MomentumConfig pattern from momentum/config.py
"""

import os
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class OrderFlowConfig:
    """
    Configuration for order flow monitoring service.

    All fields have sensible defaults from spec.md requirements.
    Use from_env() class method to load from environment variables.

    Attributes:
        data_source: Data provider for Level 2 and Time & Sales data
        polygon_api_key: Polygon.io API key (required when data_source="polygon")
        large_order_size_threshold: Minimum shares for large seller alert (FR-001)
        volume_spike_threshold: Volume spike multiplier (3.0 = 300%) (FR-002)
        red_burst_threshold: Critical volume spike for exit signal (4.0 = 400%) (FR-003)
        alert_window_seconds: Time window for exit signal evaluation (FR-003)
        monitoring_mode: Scope of monitoring ("positions_only" or "watchlist")

    Raises:
        ValueError: If validation fails in __post_init__
    """

    data_source: str = "polygon"
    polygon_api_key: str = ""
    large_order_size_threshold: int = 10_000
    volume_spike_threshold: float = 3.0
    red_burst_threshold: float = 4.0
    alert_window_seconds: int = 120
    monitoring_mode: str = "positions_only"

    VALID_DATA_SOURCES: ClassVar[set[str]] = {"polygon"}
    VALID_MONITORING_MODES: ClassVar[set[str]] = {"positions_only", "watchlist"}

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Validate data_source
        if self.data_source not in self.VALID_DATA_SOURCES:
            raise ValueError(
                f"Invalid OrderFlowConfig: data_source ({self.data_source}) "
                f"must be one of {self.VALID_DATA_SOURCES}"
            )

        # Validate polygon_api_key required when using polygon
        if self.data_source == "polygon" and not self.polygon_api_key:
            raise ValueError(
                "Invalid OrderFlowConfig: polygon_api_key is required when data_source='polygon'"
            )

        # Validate large_order_size_threshold (minimum 1000 shares per spec US4)
        if self.large_order_size_threshold < 1_000:
            raise ValueError(
                f"Invalid OrderFlowConfig: large_order_size_threshold "
                f"({self.large_order_size_threshold}) must be >= 1000 shares"
            )

        # Validate volume_spike_threshold (range 1.5x to 10.0x per spec US4)
        if not (1.5 <= self.volume_spike_threshold <= 10.0):
            raise ValueError(
                f"Invalid OrderFlowConfig: volume_spike_threshold "
                f"({self.volume_spike_threshold}) must be between 1.5 and 10.0"
            )

        # Validate red_burst_threshold must be >= volume_spike_threshold
        if self.red_burst_threshold < self.volume_spike_threshold:
            raise ValueError(
                f"Invalid OrderFlowConfig: red_burst_threshold "
                f"({self.red_burst_threshold}) must be >= volume_spike_threshold "
                f"({self.volume_spike_threshold})"
            )

        # Validate alert_window_seconds (range 30-300 seconds per spec US4)
        if not (30 <= self.alert_window_seconds <= 300):
            raise ValueError(
                f"Invalid OrderFlowConfig: alert_window_seconds "
                f"({self.alert_window_seconds}) must be between 30 and 300"
            )

        # Validate monitoring_mode
        if self.monitoring_mode not in self.VALID_MONITORING_MODES:
            raise ValueError(
                f"Invalid OrderFlowConfig: monitoring_mode ({self.monitoring_mode}) "
                f"must be one of {self.VALID_MONITORING_MODES}"
            )

    @classmethod
    def from_env(cls) -> "OrderFlowConfig":
        """
        Load configuration from environment variables.

        Environment Variables:
            ORDER_FLOW_DATA_SOURCE: Data provider (default: "polygon")
            POLYGON_API_KEY: Polygon.io API key (required)
            ORDER_FLOW_LARGE_ORDER_SIZE: Minimum shares for large seller alert (default: 10000)
            ORDER_FLOW_VOLUME_SPIKE_THRESHOLD: Volume spike multiplier (default: 3.0)
            ORDER_FLOW_RED_BURST_THRESHOLD: Critical volume spike (default: 4.0)
            ORDER_FLOW_ALERT_WINDOW_SECONDS: Time window in seconds (default: 120)
            ORDER_FLOW_MONITORING_MODE: Monitoring scope (default: "positions_only")

        Returns:
            OrderFlowConfig instance with values from environment or defaults

        Example:
            >>> config = OrderFlowConfig.from_env()
            >>> config.large_order_size_threshold
            10000
        """
        return cls(
            data_source=os.getenv("ORDER_FLOW_DATA_SOURCE", "polygon"),
            polygon_api_key=os.getenv("POLYGON_API_KEY", ""),
            large_order_size_threshold=int(
                os.getenv("ORDER_FLOW_LARGE_ORDER_SIZE", "10000")
            ),
            volume_spike_threshold=float(
                os.getenv("ORDER_FLOW_VOLUME_SPIKE_THRESHOLD", "3.0")
            ),
            red_burst_threshold=float(
                os.getenv("ORDER_FLOW_RED_BURST_THRESHOLD", "4.0")
            ),
            alert_window_seconds=int(
                os.getenv("ORDER_FLOW_ALERT_WINDOW_SECONDS", "120")
            ),
            monitoring_mode=os.getenv("ORDER_FLOW_MONITORING_MODE", "positions_only"),
        )
