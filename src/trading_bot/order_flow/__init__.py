"""
Order Flow Monitoring Module

Provides Level 2 order book and Time & Sales (tape) analysis for detecting
institutional selling pressure and volume spikes.

Components:
- OrderFlowDetector: Analyzes Level 2 order book for large seller alerts
- TapeMonitor: Tracks Time & Sales for red burst patterns
- PolygonClient: Polygon.io API wrapper with rate limiting and error handling
- OrderFlowConfig: Configuration management with validation
"""

from .config import OrderFlowConfig
from .data_models import OrderBookSnapshot, OrderFlowAlert, TimeAndSalesRecord
from .order_flow_detector import OrderFlowDetector
from .polygon_client import PolygonClient
from .tape_monitor import TapeMonitor
from .validators import validate_level2_data, validate_order_flow_config, validate_tape_data

__all__ = [
    "OrderFlowDetector",
    "TapeMonitor",
    "PolygonClient",
    "OrderFlowConfig",
    "OrderFlowAlert",
    "OrderBookSnapshot",
    "TimeAndSalesRecord",
    "validate_level2_data",
    "validate_tape_data",
    "validate_order_flow_config",
]
