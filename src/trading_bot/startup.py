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
from typing import Literal, Optional, List, Dict, Tuple, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from .config import Config


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


class StartupOrchestrator:
    """Orchestrates startup sequence initialization.

    Coordinates loading, validation, and initialization of all
    trading bot components in dependency order.
    """

    def __init__(self, config: Optional['Config'], dry_run: bool = False, json_output: bool = False):
        """Initialize orchestrator.

        Args:
            config: Configuration instance (None to load from env)
            dry_run: If True, validate but don't start trading loop
            json_output: If True, output JSON instead of text
        """
        self.config = config
        self.dry_run = dry_run
        self.json_output = json_output
        self.steps: List[StartupStep] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.component_states: Dict[str, Dict] = {}
        self.start_time: Optional[float] = None

    def _load_config(self) -> 'Config':
        """Load configuration from environment and JSON files.

        Returns:
            Loaded Config instance

        Raises:
            Exception: If configuration loading fails
        """
        from .config import Config

        step = StartupStep(name="Loading configuration", status="running")
        self.steps.append(step)

        try:
            config = Config.from_env_and_json()
            step.status = "success"
            self.config = config
            return config
        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            self.errors.append(f"Configuration loading failed: {e}")
            raise
