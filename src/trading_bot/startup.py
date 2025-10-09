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

    def _validate_config(self) -> Tuple[bool, List[str], List[str]]:
        """Validate configuration settings.

        Returns:
            Tuple of (is_valid, errors, warnings)

        Raises:
            Exception: If validation fails unexpectedly
        """
        from .validator import ConfigValidator

        step = StartupStep(name="Validating configuration", status="running")
        self.steps.append(step)

        try:
            validator = ConfigValidator(self.config)
            is_valid, errors, warnings = validator.validate_all(test_api=False)

            if is_valid:
                step.status = "success"
            else:
                step.status = "failed"
                step.error_message = "; ".join(errors)
                self.errors.extend(errors)

            self.warnings.extend(warnings)
            return is_valid, errors, warnings
        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            self.errors.append(f"Validation failed: {e}")
            raise

    def _initialize_logging(self) -> None:
        """Initialize logging system and create startup logger.

        Raises:
            Exception: If logging initialization fails
        """
        from pathlib import Path
        from .logger import TradingLogger

        step = StartupStep(name="Initializing logging system", status="running")
        self.steps.append(step)

        try:
            # Convert logs_dir to Path if it's a string
            logs_dir = Path(self.config.logs_dir) if isinstance(self.config.logs_dir, str) else self.config.logs_dir
            TradingLogger.setup(logs_dir=logs_dir)
            self.startup_logger = TradingLogger.get_startup_logger()
            self.startup_logger.info("Startup sequence initiated")

            step.status = "success"
            self.component_states["logging"] = {
                "status": "ready",
                "logs_dir": str(self.config.logs_dir)
            }
        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            self.errors.append(f"Logging initialization failed: {e}")
            raise

    def _initialize_mode_switcher(self) -> 'ModeSwitcher':
        """Initialize mode switcher for paper/live trading management.

        Returns:
            ModeSwitcher instance

        Raises:
            Exception: If mode switcher initialization fails
        """
        from .mode_switcher import ModeSwitcher

        step = StartupStep(name="Initializing mode switcher", status="running")
        self.steps.append(step)

        try:
            mode_switcher = ModeSwitcher(self.config)
            self.mode_switcher = mode_switcher

            step.status = "success"
            self.component_states["mode_switcher"] = {
                "status": "ready",
                "mode": self.config.trading.mode,
                "phase": self.config.phase_progression.current_phase
            }
            return mode_switcher
        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            self.errors.append(f"Mode switcher initialization failed: {e}")
            raise

    def _initialize_circuit_breakers(self) -> 'CircuitBreaker':
        """Initialize circuit breakers for risk management.

        Returns:
            CircuitBreaker instance

        Raises:
            Exception: If circuit breaker initialization fails
        """
        from .bot import CircuitBreaker

        step = StartupStep(name="Initializing circuit breakers", status="running")
        self.steps.append(step)

        try:
            circuit_breaker = CircuitBreaker(
                max_daily_loss_pct=self.config.risk_management.max_daily_loss_pct,
                max_consecutive_losses=self.config.risk_management.max_consecutive_losses
            )
            self.circuit_breaker = circuit_breaker

            step.status = "success"
            self.component_states["circuit_breaker"] = {
                "status": "ready",
                "max_daily_loss_pct": self.config.risk_management.max_daily_loss_pct,
                "max_consecutive_losses": self.config.risk_management.max_consecutive_losses
            }
            return circuit_breaker
        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            self.errors.append(f"Circuit breaker initialization failed: {e}")
            raise
