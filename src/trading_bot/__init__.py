"""
Robinhood Trading Bot

A Python-based algorithmic trading bot using the robin_stocks library.

Constitution: v1.0.0
License: MIT
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from .bot import TradingBot
from .config import Config
from . import error_handling
from . import order_management

__all__ = ["TradingBot", "Config", "error_handling", "order_management"]
