"""Phase progression and position scaling management.

This module implements a four-phase trading progression system:
- Experience: Paper trading only
- Proof of Concept: 1 trade/day, $100 positions
- Real Money Trial: $200 positions
- Scaling: $200-$2,000 graduated positions

See specs/022-pos-scale-progress/spec.md for full requirements.
"""

# Phase models and management
from .models import Phase
from .manager import PhaseManager, PhaseValidationError
from .trade_limiter import TradeLimitExceeded

__all__ = [
    "Phase",
    "PhaseManager",
    "TradeLimitExceeded",
    "PhaseValidationError",
]
