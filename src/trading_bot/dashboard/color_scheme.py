"""
Color scheme constants for dashboard rendering.

Centralizes all color definitions for consistent theming and easy maintenance.
"""

from __future__ import annotations


class ColorScheme:
    """Color constants for dashboard UI elements."""

    # Basic colors
    GREEN = "green"
    RED = "red"
    YELLOW = "yellow"
    WHITE = "white"
    CYAN = "cyan"
    BLUE = "blue"
    MAGENTA = "magenta"
    DIM = "dim"

    # Semantic colors for P&L
    PROFIT = GREEN
    LOSS = RED
    NEUTRAL = YELLOW

    # Semantic colors for streaks
    WIN_STREAK = GREEN
    LOSS_STREAK = RED
    NO_STREAK = YELLOW

    # Semantic colors for market status
    MARKET_OPEN = GREEN
    MARKET_CLOSED = YELLOW

    # Semantic colors for targets
    TARGET_MET = GREEN
    TARGET_MISSED = RED

    # Semantic colors for warnings
    WARNING = YELLOW

    # Text styles
    BOLD = "bold"
    BOLD_WHITE = "bold white"
    BOLD_GREEN = "green bold"
    BOLD_YELLOW = "yellow bold"
    BOLD_CYAN = "bold cyan"

    # Combined styles
    BOLD_WHITE_ON_BLUE = "bold white on blue"
