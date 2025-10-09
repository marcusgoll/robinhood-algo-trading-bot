"""
Startup Sequence Orchestrator

Enforces Constitution v1.0.0:
- §Safety_First: All safety systems initialized before trading
- §Pre_Deploy: Comprehensive validation before trading begins
- §Security: Credentials validated, never logged

Provides:
- StartupStep: Dataclass for tracking initialization steps
- StartupResult: Dataclass for aggregating startup sequence data
- StartupOrchestrator: Coordinates startup sequence
"""

from dataclasses import dataclass
from typing import Literal, Optional, List, Dict


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


@dataclass
class StartupResult:
    """Aggregates all startup sequence data.

    Attributes:
        status: Overall startup status (ready/blocked)
        mode: Trading mode (paper/live)
        phase: Current phase (experience/proof_of_concept/etc)
        steps: List of StartupStep objects tracking progress
        errors: List of error messages
        warnings: List of warning messages
        component_states: Dict of component name -> state dict
        startup_duration_seconds: Total time for startup sequence
        timestamp: ISO 8601 UTC timestamp of completion
    """
    status: Literal["ready", "blocked"]
    mode: str
    phase: str
    steps: List[StartupStep]
    errors: List[str]
    warnings: List[str]
    component_states: Dict[str, Dict]
    startup_duration_seconds: float
    timestamp: str  # ISO 8601 UTC
