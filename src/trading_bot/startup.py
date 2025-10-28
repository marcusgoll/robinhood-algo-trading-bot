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

import json
import time
from dataclasses import dataclass
from datetime import UTC
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from .bot import CircuitBreaker, TradingBot
    from .config import Config
    from .mode_switcher import ModeSwitcher
    from .telegram.command_handler import TelegramCommandHandler


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
    error_message: str | None = None
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
    steps: list[StartupStep]
    errors: list[str]
    warnings: list[str]
    component_states: dict[str, dict]
    startup_duration_seconds: float
    timestamp: str  # ISO 8601 UTC


class StartupOrchestrator:
    """Orchestrates startup sequence initialization.

    Coordinates loading, validation, and initialization of all
    trading bot components in dependency order.

    Enforces Constitution v1.0.0:
    - Safety_First: All safety systems initialized before trading
    - Pre_Deploy: Comprehensive validation before trading begins
    - Security: Credentials validated, never logged

    Attributes:
        config: Configuration instance (None to load from env)
        dry_run: If True, validate but don't start trading loop
        json_output: If True, output JSON instead of text
        steps: List of StartupStep objects tracking progress
        errors: List of error messages encountered
        warnings: List of warning messages
        component_states: Dict of component name to state dict
        start_time: Timestamp when startup sequence began
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
        self.steps: list[StartupStep] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.component_states: dict[str, dict] = {}
        self.start_time: float | None = None

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

    def _validate_config(self) -> tuple[bool, list[str], list[str]]:
        """Validate configuration settings.

        Returns:
            Tuple of (is_valid, errors, warnings)

        Raises:
            Exception: If validation fails unexpectedly
        """
        from .validator import ConfigValidator

        assert self.config is not None, "Config must be loaded before validation"

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

        assert self.config is not None, "Config must be loaded before logging initialization"

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

        assert self.config is not None, "Config must be loaded before mode switcher initialization"

        step = StartupStep(name="Initializing mode switcher", status="running")
        self.steps.append(step)

        try:
            mode_switcher = ModeSwitcher(self.config)
            self.mode_switcher = mode_switcher

            step.status = "success"
            self.component_states["mode_switcher"] = {
                "status": "ready",
                "mode": "paper" if self.config.paper_trading else "live",
                "phase": self.config.current_phase
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

        assert self.config is not None, "Config must be loaded before circuit breaker initialization"

        step = StartupStep(name="Initializing circuit breakers", status="running")
        self.steps.append(step)

        try:
            circuit_breaker = CircuitBreaker(
                max_daily_loss_pct=self.config.max_daily_loss_pct,
                max_consecutive_losses=self.config.max_consecutive_losses
            )
            self.circuit_breaker = circuit_breaker

            step.status = "success"
            self.component_states["circuit_breaker"] = {
                "status": "ready",
                "max_daily_loss_pct": self.config.max_daily_loss_pct,
                "max_consecutive_losses": self.config.max_consecutive_losses
            }
            return circuit_breaker
        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            self.errors.append(f"Circuit breaker initialization failed: {e}")
            raise

    def _initialize_bot(self) -> 'TradingBot':
        """Initialize trading bot with configuration.

        Returns:
            TradingBot instance

        Raises:
            Exception: If trading bot initialization fails
        """
        from .bot import TradingBot

        assert self.config is not None, "Config must be loaded before bot initialization"

        step = StartupStep(name="Initializing trading bot", status="running")
        self.steps.append(step)

        try:
            bot = TradingBot(
                config=self.config,
                paper_trading=self.config.paper_trading,
                max_position_pct=self.config.max_position_pct,
                max_daily_loss_pct=self.config.max_daily_loss_pct,
                max_consecutive_losses=self.config.max_consecutive_losses
            )
            self.bot = bot

            step.status = "success"
            self.component_states["trading_bot"] = {
                "status": "ready",
                "is_running": False,
                "health_monitor": "ready" if bot.health_monitor else "disabled"
            }
            return bot
        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            self.errors.append(f"Trading bot initialization failed: {e}")
            raise

    def _initialize_telegram_commands(self) -> Optional['TelegramCommandHandler']:
        """Initialize Telegram command handler (Feature #031).

        Conditionally starts Telegram command handler if TELEGRAM_ENABLED=true.

        Returns:
            TelegramCommandHandler instance or None if disabled

        Raises:
            Exception: If command handler initialization fails
        """
        import os
        from .telegram.command_handler import TelegramCommandHandler

        step = StartupStep(name="Initializing Telegram command handler", status="running")
        self.steps.append(step)

        # Check if Telegram is enabled
        telegram_enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
        if not telegram_enabled:
            step.status = "success"
            step.error_message = "Skipped (TELEGRAM_ENABLED=false)"
            self.component_states["telegram_commands"] = {
                "status": "disabled",
                "enabled": False
            }
            return None

        try:
            import asyncio

            # Initialize command handler
            handler = TelegramCommandHandler.from_env()
            handler.register_commands()

            # Start command handler in background
            asyncio.create_task(handler.start())

            step.status = "success"
            self.component_states["telegram_commands"] = {
                "status": "ready",
                "enabled": True,
                "commands_registered": 7
            }
            self.telegram_command_handler = handler
            return handler
        except Exception as e:
            # Non-blocking failure - log warning but continue startup
            step.status = "success"
            step.error_message = f"Failed to initialize (non-blocking): {e}"
            self.warnings.append(f"Telegram command handler initialization failed: {e}")
            self.component_states["telegram_commands"] = {
                "status": "failed",
                "enabled": False,
                "error": str(e)
            }
            return None

    def run(self) -> StartupResult:
        """Execute the full startup sequence.

        Coordinates all initialization steps in dependency order:
        1. Display banner (if not json_output)
        2. Load configuration
        3. Validate configuration
        4. Initialize logging system
        5. Initialize mode switcher
        6. Initialize circuit breakers
        7. Initialize trading bot
        8. Initialize Telegram command handler (Feature #031)
        9. Verify component health
        10. Display summary (if not json_output)

        Returns:
            StartupResult with status="ready" or "blocked"

        T029 [GREEN→T028]: Implement run() method
        """
        from datetime import datetime

        self.start_time = time.time()

        try:
            # Display banner
            if not self.json_output:
                self._display_banner()

            # Execute startup sequence
            self._load_config()
            assert self.config is not None, "Config must be loaded before proceeding"
            is_valid, errors, warnings = self._validate_config()

            if not is_valid:
                return self._create_blocked_result("Validation failed")

            self._initialize_logging()
            self._initialize_mode_switcher()
            self._initialize_circuit_breakers()
            self._initialize_bot()
            self._initialize_telegram_commands()  # Feature #031
            self._verify_health()

            # Display summary
            if not self.json_output:
                self._display_summary()

            # Create success result
            duration = time.time() - self.start_time
            result = StartupResult(
                status="ready",
                mode="paper" if self.config.paper_trading else "live",
                phase=self.config.current_phase,
                steps=self.steps,
                errors=self.errors,
                warnings=self.warnings,
                component_states=self.component_states,
                startup_duration_seconds=duration,
                timestamp=datetime.now(UTC).isoformat()
            )

            if self.json_output:
                print(self._format_json_output(result))

            return result

        except Exception as e:
            self._cleanup_on_failure()
            duration = time.time() - self.start_time if self.start_time else 0.0
            return self._create_blocked_result(str(e), duration)

    def _display_banner(self) -> None:
        """Display startup banner with mode and phase information.

        Shows:
        - Bot title
        - Trading mode (PAPER or LIVE)
        - Clear safety warnings

        Pattern: Reuses mode_switcher.py display_mode_banner() approach (line 141)
        T023 [GREEN]: Implementation for _display_banner() test
        """
        assert self.config is not None, "Config must be loaded before displaying banner"
        mode_display = "PAPER TRADING (Simulation - No Real Money)" if self.config.paper_trading else "LIVE TRADING (Real Money)"

        print("=" * 60)
        print("         ROBINHOOD TRADING BOT - STARTUP SEQUENCE")
        print("=" * 60)
        print(f"Mode: {mode_display}")
        print("=" * 60)
        print()

    def _display_summary(self) -> None:
        """Display startup completion summary with configuration details.

        Shows:
        - Startup completion message
        - Current phase and phase-specific settings
        - Circuit breaker status and limits
        - Dry run indicator (if applicable)

        T025 [GREEN]: Implementation for _display_summary() test
        """
        assert self.config is not None, "Config must be loaded before displaying summary"

        print("=" * 60)
        print("✅ STARTUP COMPLETE - Ready to trade")
        print("=" * 60)
        print(f"Current Phase: {self.config.current_phase}")

        # Get phase-specific config (max_trades_per_day is directly on config)
        phase_config = self.config
        print(f"Max Trades Today: {phase_config.max_trades_per_day}")
        print(f"Circuit Breaker: Active (Max Loss: {self.config.max_daily_loss_pct}%, Max Consecutive: {self.config.max_consecutive_losses})")

        bot = getattr(self, "bot", None)
        if bot is not None and getattr(bot, "health_monitor", None) is not None:
            print("Session Health Monitor: READY (5m interval, auto re-auth if needed)")
        else:
            print("Session Health Monitor: DISABLED (run manual checks before trading)")
        print()

        if self.dry_run:
            print("[DRY RUN] Exiting without starting trading loop")

    def _verify_health(self) -> None:
        """Verify all components are initialized and ready.

        Checks that all required components have been initialized and
        have status="ready" in component_states.

        Raises:
            RuntimeError: If any component is missing or not ready

        T031 [GREEN→T030]: Implement _verify_health() method
        """
        step = StartupStep(name="Verifying component health", status="running")
        self.steps.append(step)

        try:
            # Check all components initialized
            required_components = ["logging", "mode_switcher", "circuit_breaker", "trading_bot"]
            for component in required_components:
                if component not in self.component_states:
                    raise RuntimeError(f"Component {component} not initialized")
                if self.component_states[component].get("status") != "ready":
                    raise RuntimeError(f"Component {component} not ready")

            trading_bot_state = self.component_states.get("trading_bot", {})
            if trading_bot_state.get("health_monitor") != "ready":
                self.warnings.append(
                    "Session health monitor inactive — periodic checks will not run (paper/offline mode)"
                )

            step.status = "success"
        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            self.errors.append(f"Health check failed: {e}")
            raise

    def _cleanup_on_failure(self) -> None:
        """Gracefully clean up resources on startup failure.

        T033 [GREEN→T032]: Implement _cleanup_on_failure() method
        """
        try:
            # Close logging handlers if initialized
            if hasattr(self, 'startup_logger'):
                for handler in self.startup_logger.handlers[:]:
                    handler.close()
                    self.startup_logger.removeHandler(handler)
        except Exception as e:
            # Log cleanup errors but don't raise
            print(f"Warning: Cleanup error: {e}")

    def _get_mode(self) -> str:
        """Get current trading mode for reporting.

        Returns:
            Trading mode string ("paper", "live", or "unknown")
        """
        if hasattr(self, 'config') and self.config:
            return "paper" if self.config.paper_trading else "live"
        return "unknown"

    def _get_phase(self) -> str:
        """Get current phase for reporting.

        Returns:
            Current phase string or "unknown"
        """
        if hasattr(self, 'config') and self.config:
            return self.config.current_phase
        return "unknown"

    def _create_blocked_result(self, error_message: str, duration: float = 0.0) -> StartupResult:
        """Create a blocked result with error information.

        Args:
            error_message: Error message describing the failure
            duration: Startup duration in seconds

        Returns:
            StartupResult with status="blocked"

        T035 [GREEN→T034]: Implement _create_blocked_result() method
        """
        from datetime import datetime

        # Add error message to errors list if not already present
        if error_message not in self.errors:
            self.errors.append(error_message)

        return StartupResult(
            status="blocked",
            mode=self._get_mode(),
            phase=self._get_phase(),
            steps=self.steps,
            errors=self.errors,
            warnings=self.warnings,
            component_states=self.component_states,
            startup_duration_seconds=duration,
            timestamp=datetime.now(UTC).isoformat()
        )

    def _format_json_output(self, result: StartupResult) -> str:
        """Format startup result as JSON for machine-readable output.

        Args:
            result: StartupResult instance to format

        Returns:
            JSON string with formatted startup result
        """
        output = {
            "status": result.status,
            "mode": result.mode,
            "phase": result.phase,
            "startup_duration_seconds": result.startup_duration_seconds,
            "timestamp": result.timestamp,
            "components": result.component_states,
            "errors": result.errors,
            "warnings": result.warnings
        }
        return json.dumps(output, indent=2)
