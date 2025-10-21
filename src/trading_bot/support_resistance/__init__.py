"""
Support/Resistance Zone Detection Module

Feature Status:
- US1 (Daily zones): Complete
- US2 (Strength scoring): Complete
- US3 (Proximity alerts): Complete
- US4 (4-hour zones): Supported via Timeframe.FOUR_HOUR
"""

from .models import Zone, ZoneTouch, ProximityAlert, ZoneType, Timeframe, TouchType
from .config import ZoneDetectionConfig
from .zone_detector import ZoneDetector
from .proximity_checker import ProximityChecker
from .zone_logger import ZoneLogger

__all__ = [
    "Zone", "ZoneTouch", "ProximityAlert", "ZoneType", "Timeframe", "TouchType",
    "ZoneDetector", "ProximityChecker", "ZoneLogger", "ZoneDetectionConfig",
]
