"""
Startup Sequence Orchestrator

Enforces Constitution v1.0.0:
- §Safety_First: All safety systems initialized before trading
- §Pre_Deploy: Comprehensive validation before trading begins
- §Security: Credentials validated, never logged

Provides:
- StartupStep: Dataclass for tracking initialization steps
- StartupOrchestrator: Coordinates startup sequence
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class StartupStep:
    """Represents a single step in the startup sequence.

    Attributes:
        name: Human-readable step name
        status: Current status (pending/running/success/failed)
        error_message: Error details if status=failed
        duration_seconds: Time taken to complete step
    """
    name: str
    status: Literal["pending", "running", "success", "failed"]
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
