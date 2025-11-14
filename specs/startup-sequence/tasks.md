# Tasks: Startup Sequence

## [CODEBASE REUSE ANALYSIS]

**Scanned**: src/trading_bot/**/*.py, tests/**/*.py

### [EXISTING - REUSE]
- ✅ Config.from_env_and_json() (src/trading_bot/config.py line 68)
- ✅ Config.validate() (src/trading_bot/config.py line 149)
- ✅ Config.ensure_directories() (src/trading_bot/config.py line 213)
- ✅ ConfigValidator.validate_all() (src/trading_bot/validator.py line 46)
- ✅ TradingLogger.setup() (src/trading_bot/logger.py line 75)
- ✅ ModeSwitcher class (src/trading_bot/mode_switcher.py line 36)
- ✅ CircuitBreaker class (src/trading_bot/bot.py line 18)
- ✅ TradingBot class (src/trading_bot/bot.py line 75)

### [NEW - CREATE]
- 🆕 StartupOrchestrator (no existing orchestrator pattern in codebase)
- 🆕 StartupStep dataclass (no existing step tracking)
- 🆕 StartupResult dataclass (no existing result tracking)
- 🆕 main.py entry point (no existing CLI entry point)
- 🆕 startup logger extension (logger.py has trading/trades/errors logs only)

---

## Phase 3.0: Test Infrastructure Setup

T001 [P] Create test fixtures directory and base configuration files
- **Directory**: tests/fixtures/startup/
- **Files to create**:
  - `.env.valid` - Valid credentials (ROBINHOOD_USERNAME=test_user, ROBINHOOD_PASSWORD=test_pass)
  - `.env.missing_username` - Missing ROBINHOOD_USERNAME
  - `.env.missing_password` - Missing ROBINHOOD_PASSWORD
  - `config.valid.json` - Valid config with paper mode, experience phase
  - `config.phase_conflict.json` - mode=live, phase=experience (validation blocker)
  - `config.invalid.json` - Malformed JSON (trailing comma)
- **Pattern**: tests/unit/test_validator.py uses similar fixtures
- **From**: plan.md Testing Strategy section

T002 [P] Create pytest configuration for startup tests
- **File**: tests/conftest.py (extend existing)
- **Add fixtures**:
  - `@pytest.fixture valid_env_file()` - Returns path to .env.valid
  - `@pytest.fixture valid_config_file()` - Returns path to config.valid.json
  - `@pytest.fixture tmp_logs_dir(tmp_path)` - Temporary logs directory
  - `@pytest.fixture mock_config()` - Mock Config instance
- **Pattern**: Existing conftest.py pattern (if exists)
- **From**: plan.md Testing Strategy

---

## Phase 3.1: Core Data Structures (TDD - RED → GREEN → REFACTOR)

T003 [RED] Write failing test: StartupStep tracks step status
- **File**: tests/unit/test_startup.py
- **Test**: test_startup_step_dataclass()
  - Given: Create StartupStep with name="Loading config", status="running"
  - When: Access attributes
  - Then: Assert name, status, error_message, duration_seconds correct
- **Pattern**: tests/unit/test_config.py dataclass tests
- **From**: plan.md [SCHEMA] StartupStep dataclass

T004 [GREEN→T003] Implement StartupStep dataclass
- **File**: src/trading_bot/startup.py (new file)
- **Code**:
  ```python
  from dataclasses import dataclass
  from typing import Literal, Optional

  @dataclass
  class StartupStep:
      name: str
      status: Literal["pending", "running", "success", "failed"]
      error_message: Optional[str] = None
      duration_seconds: float = 0.0
  ```
- **Pattern**: src/trading_bot/config.py dataclass pattern
- **From**: plan.md [SCHEMA] section

T005 [RED] Write failing test: StartupResult aggregates all startup data
- **File**: tests/unit/test_startup.py
- **Test**: test_startup_result_dataclass()
  - Given: Create StartupResult with status="ready", mode="paper", steps=[], errors=[]
  - When: Access all attributes
  - Then: Assert status, mode, phase, steps, errors, warnings, component_states, startup_duration_seconds, timestamp
- **Pattern**: tests/unit/test_config.py
- **From**: plan.md [SCHEMA] StartupResult

T006 [GREEN→T005] Implement StartupResult dataclass
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  from typing import List, Dict
  from datetime import datetime

  @dataclass
  class StartupResult:
      status: Literal["ready", "blocked"]
      mode: str
      phase: str
      steps: List[StartupStep]
      errors: List[str]
      warnings: List[str]
      component_states: Dict[str, Dict]
      startup_duration_seconds: float
      timestamp: str  # ISO 8601 UTC
  ```
- **Pattern**: src/trading_bot/config.py
- **From**: plan.md [SCHEMA]

---

## Phase 3.2: Startup Orchestrator - Configuration Loading

T007 [RED] Write failing test: Orchestrator initializes with config
- **File**: tests/unit/test_startup.py
- **Test**: test_orchestrator_init()
  - Given: Valid Config instance
  - When: orchestrator = StartupOrchestrator(config, dry_run=True, json_output=False)
  - Then: Assert orchestrator.config, orchestrator.dry_run, orchestrator.json_output set correctly
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE]

T008 [GREEN→T007] Implement StartupOrchestrator __init__ method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  class StartupOrchestrator:
      def __init__(self, config: 'Config', dry_run: bool = False, json_output: bool = False):
          self.config = config
          self.dry_run = dry_run
          self.json_output = json_output
          self.steps: List[StartupStep] = []
          self.errors: List[str] = []
          self.warnings: List[str] = []
          self.component_states: Dict[str, Dict] = {}
          self.start_time: Optional[float] = None
  ```
- **Pattern**: src/trading_bot/bot.py TradingBot.__init__
- **From**: plan.md StartupOrchestrator class

T009 [RED] Write failing test: Load config from environment and JSON
- **File**: tests/unit/test_startup.py
- **Test**: test_load_config_success(valid_env_file, valid_config_file, monkeypatch)
  - Given: Valid .env and config.json files
  - When: config = orchestrator._load_config()
  - Then: Assert config is not None, config.trading.mode exists
- **REUSE**: Config.from_env_and_json() from config.py
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T010 [GREEN→T009] Implement _load_config() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _load_config(self) -> 'Config':
      from .config import Config
      step = StartupStep(name="Loading configuration", status="running")
      self.steps.append(step)

      try:
          config = Config.from_env_and_json()
          step.status = "success"
          return config
      except Exception as e:
          step.status = "failed"
          step.error_message = str(e)
          self.errors.append(f"Configuration loading failed: {e}")
          raise
  ```
- **REUSE**: Config.from_env_and_json() (config.py line 68)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T011 [RED] Write failing test: Validate config detects phase-mode conflicts
- **File**: tests/unit/test_startup.py
- **Test**: test_validate_config_phase_mode_conflict(mock_config)
  - Given: Config with mode=live, phase=experience
  - When: orchestrator._validate_config()
  - Then: Assert ValidationError raised, error message includes "phase-mode conflict"
- **REUSE**: ConfigValidator.validate_all() from validator.py
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T012 [GREEN→T011] Implement _validate_config() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _validate_config(self) -> Tuple[bool, List[str], List[str]]:
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
  ```
- **REUSE**: ConfigValidator.validate_all() (validator.py line 46)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

---

## Phase 3.3: Startup Orchestrator - Component Initialization

T013 [RED] Write failing test: Initialize logging system creates startup log
- **File**: tests/unit/test_startup.py
- **Test**: test_initialize_logging_creates_startup_log(tmp_logs_dir)
  - Given: Orchestrator with valid config
  - When: orchestrator._initialize_logging()
  - Then: Assert logs/startup.log exists
- **Extension**: Extend TradingLogger in logger.py
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] Startup Logger

T014 [GREEN→T013] Extend TradingLogger with get_startup_logger() method
- **File**: src/trading_bot/logger.py
- **Code**:
  ```python
  @staticmethod
  def get_startup_logger() -> logging.Logger:
      """Get logger for startup sequence."""
      logger = logging.getLogger("startup")

      # Create startup log handler if not exists
      startup_log_path = Path("logs") / "startup.log"
      startup_log_path.parent.mkdir(parents=True, exist_ok=True)

      handler = RotatingFileHandler(
          startup_log_path,
          maxBytes=10 * 1024 * 1024,  # 10MB
          backupCount=5
      )
      handler.setFormatter(UTCFormatter(
          '%(asctime)s - %(levelname)s - %(message)s'
      ))
      logger.addHandler(handler)
      logger.setLevel(logging.INFO)

      return logger
  ```
- **REUSE**: UTCFormatter (logger.py line 23), RotatingFileHandler pattern (logger.py line 59)
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE]

T015 [GREEN→T013] Implement _initialize_logging() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _initialize_logging(self) -> None:
      from .logger import TradingLogger
      step = StartupStep(name="Initializing logging system", status="running")
      self.steps.append(step)

      try:
          TradingLogger.setup(logs_dir=self.config.logs_dir)
          self.startup_logger = TradingLogger.get_startup_logger()
          self.startup_logger.info("Startup sequence initiated")

          step.status = "success"
          self.component_states["logging"] = {
              "status": "ready",
              "logs_dir": self.config.logs_dir
          }
      except Exception as e:
          step.status = "failed"
          step.error_message = str(e)
          self.errors.append(f"Logging initialization failed: {e}")
          raise
  ```
- **REUSE**: TradingLogger.setup() (logger.py line 75)
- **From**: plan.md StartupOrchestrator methods

T016 [RED] Write failing test: Initialize mode switcher with config
- **File**: tests/unit/test_startup.py
- **Test**: test_initialize_mode_switcher(mock_config)
  - Given: Config with mode=paper, phase=experience
  - When: orchestrator._initialize_mode_switcher()
  - Then: Assert mode_switcher created, mode_switcher.mode == "paper"
- **REUSE**: ModeSwitcher from mode_switcher.py
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T017 [GREEN→T016] Implement _initialize_mode_switcher() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _initialize_mode_switcher(self) -> 'ModeSwitcher':
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
  ```
- **REUSE**: ModeSwitcher class (mode_switcher.py line 36)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T018 [RED] Write failing test: Initialize circuit breakers with risk params
- **File**: tests/unit/test_startup.py
- **Test**: test_initialize_circuit_breakers(mock_config)
  - Given: Config with max_daily_loss_pct=3.0, max_consecutive_losses=3
  - When: orchestrator._initialize_circuit_breakers()
  - Then: Assert circuit_breaker created, max_daily_loss_pct == 3.0
- **REUSE**: CircuitBreaker from bot.py
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T019 [GREEN→T018] Implement _initialize_circuit_breakers() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _initialize_circuit_breakers(self) -> 'CircuitBreaker':
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
  ```
- **REUSE**: CircuitBreaker class (bot.py line 18)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T020 [RED] Write failing test: Initialize trading bot with dependencies
- **File**: tests/unit/test_startup.py
- **Test**: test_initialize_bot(mock_config)
  - Given: Config with paper_trading=True
  - When: orchestrator._initialize_bot()
  - Then: Assert bot created, bot.paper_trading == True
- **REUSE**: TradingBot from bot.py
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

T021 [GREEN→T020] Implement _initialize_bot() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _initialize_bot(self) -> 'TradingBot':
      from .bot import TradingBot
      step = StartupStep(name="Initializing trading bot", status="running")
      self.steps.append(step)

      try:
          bot = TradingBot(
              paper_trading=(self.config.trading.mode == "paper"),
              max_position_pct=self.config.risk_management.max_position_pct,
              max_daily_loss_pct=self.config.risk_management.max_daily_loss_pct,
              max_consecutive_losses=self.config.risk_management.max_consecutive_losses
          )
          self.bot = bot

          step.status = "success"
          self.component_states["trading_bot"] = {
              "status": "ready",
              "is_running": False
          }
          return bot
      except Exception as e:
          step.status = "failed"
          step.error_message = str(e)
          self.errors.append(f"Trading bot initialization failed: {e}")
          raise
  ```
- **REUSE**: TradingBot class (bot.py line 75)
- **From**: plan.md [EXISTING INFRASTRUCTURE - REUSE]

---

## Phase 3.4: Display and Output Formatting

T022 [RED] Write failing test: Display banner shows mode and phase
- **File**: tests/unit/test_startup.py
- **Test**: test_display_banner_paper_mode(mock_config, capsys)
  - Given: Config with mode=paper, phase=experience
  - When: orchestrator._display_banner()
  - Then: Assert stdout contains "PAPER TRADING", "experience"
- **From**: plan.md [INTEGRATION SCENARIOS] expected output

T023 [GREEN→T022] Implement _display_banner() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _display_banner(self) -> None:
      mode_display = "PAPER TRADING (Simulation - No Real Money)" if self.config.trading.mode == "paper" else "LIVE TRADING (Real Money)"

      print("=" * 60)
      print("         ROBINHOOD TRADING BOT - STARTUP SEQUENCE")
      print("=" * 60)
      print(f"Mode: {mode_display}")
      print("=" * 60)
      print()
  ```
- **Pattern**: mode_switcher.py display_mode_banner() (line 141)
- **From**: plan.md [INTEGRATION SCENARIOS]

T024 [RED] Write failing test: Display summary shows configuration details
- **File**: tests/unit/test_startup.py
- **Test**: test_display_summary_shows_config(mock_config, capsys)
  - Given: Successful startup
  - When: orchestrator._display_summary()
  - Then: Assert stdout contains "STARTUP COMPLETE", "Current Phase", "Circuit Breaker: Active"
- **From**: plan.md [INTEGRATION SCENARIOS] expected output

T025 [GREEN→T024] Implement _display_summary() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _display_summary(self) -> None:
      print("=" * 60)
      print("✅ STARTUP COMPLETE - Ready to trade")
      print("=" * 60)
      print(f"Current Phase: {self.config.phase_progression.current_phase}")

      phase_config = getattr(self.config.phase_progression, self.config.phase_progression.current_phase)
      print(f"Max Trades Today: {phase_config.max_trades_per_day}")
      print(f"Circuit Breaker: Active (Max Loss: {self.config.risk_management.max_daily_loss_pct}%, Max Consecutive: {self.config.risk_management.max_consecutive_losses})")
      print()

      if self.dry_run:
          print("[DRY RUN] Exiting without starting trading loop")
  ```
- **From**: plan.md [INTEGRATION SCENARIOS] expected output

T026 [RED] Write failing test: JSON output format matches schema
- **File**: tests/unit/test_startup.py
- **Test**: test_json_output_format(mock_config)
  - Given: Successful startup with json_output=True
  - When: result = orchestrator.run()
  - Then: Assert JSON has status, mode, phase, components, errors, warnings, timestamp
- **From**: plan.md [SCHEMA] JSON Output Schema

T027 [GREEN→T026] Implement _format_json_output() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  import json
  from datetime import datetime, timezone

  def _format_json_output(self, result: StartupResult) -> str:
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
  ```
- **From**: plan.md [SCHEMA] JSON Output Schema

---

## Phase 3.5: Main Orchestration Logic

T028 [RED] Write failing test: Run method executes all steps successfully
- **File**: tests/unit/test_startup.py
- **Test**: test_run_success_path(valid_env_file, valid_config_file)
  - Given: Valid .env and config.json
  - When: result = orchestrator.run()
  - Then: Assert result.status == "ready", len(result.steps) == 6, all steps success
- **From**: plan.md StartupOrchestrator.run() method

T029 [GREEN→T028] Implement run() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def run(self) -> StartupResult:
      import time
      self.start_time = time.time()

      try:
          # Display banner
          if not self.json_output:
              self._display_banner()

          # Execute startup sequence
          config = self._load_config()
          is_valid, errors, warnings = self._validate_config()

          if not is_valid:
              return self._create_blocked_result("Validation failed")

          self._initialize_logging()
          self._initialize_mode_switcher()
          self._initialize_circuit_breakers()
          self._initialize_bot()
          self._verify_health()

          # Display summary
          if not self.json_output:
              self._display_summary()

          # Create success result
          duration = time.time() - self.start_time
          result = StartupResult(
              status="ready",
              mode=self.config.trading.mode,
              phase=self.config.phase_progression.current_phase,
              steps=self.steps,
              errors=self.errors,
              warnings=self.warnings,
              component_states=self.component_states,
              startup_duration_seconds=duration,
              timestamp=datetime.now(timezone.utc).isoformat()
          )

          if self.json_output:
              print(self._format_json_output(result))

          return result

      except Exception as e:
          self._cleanup_on_failure()
          duration = time.time() - self.start_time if self.start_time else 0.0
          return self._create_blocked_result(str(e), duration)
  ```
- **From**: plan.md StartupOrchestrator.run()

T030 [RED] Write failing test: Verify health checks all components
- **File**: tests/unit/test_startup.py
- **Test**: test_verify_health_checks_components(mock_config)
  - Given: All components initialized
  - When: orchestrator._verify_health()
  - Then: Assert all component_states have status="ready"
- **From**: plan.md StartupOrchestrator._verify_health()

T031 [GREEN→T030] Implement _verify_health() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _verify_health(self) -> None:
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

          step.status = "success"
      except Exception as e:
          step.status = "failed"
          step.error_message = str(e)
          self.errors.append(f"Health check failed: {e}")
          raise
  ```
- **From**: plan.md StartupOrchestrator._verify_health()

---

## Phase 3.6: Error Handling and Cleanup

T032 [RED] Write failing test: Cleanup on failure releases resources
- **File**: tests/unit/test_startup.py
- **Test**: test_cleanup_on_failure_closes_logger()
  - Given: Partial initialization (logging initialized, then error)
  - When: orchestrator._cleanup_on_failure()
  - Then: Assert logger handlers closed, no resource leaks
- **From**: plan.md StartupOrchestrator._cleanup_on_failure()

T033 [GREEN→T032] Implement _cleanup_on_failure() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _cleanup_on_failure(self) -> None:
      """Gracefully clean up resources on startup failure."""
      try:
          # Close logging handlers if initialized
          if hasattr(self, 'startup_logger'):
              for handler in self.startup_logger.handlers[:]:
                  handler.close()
                  self.startup_logger.removeHandler(handler)
      except Exception as e:
          # Log cleanup errors but don't raise
          print(f"Warning: Cleanup error: {e}")
  ```
- **From**: plan.md StartupOrchestrator._cleanup_on_failure()

T034 [RED] Write failing test: Create blocked result on validation failure
- **File**: tests/unit/test_startup.py
- **Test**: test_create_blocked_result_includes_error_message()
  - Given: Validation failure with error="Missing credentials"
  - When: result = orchestrator._create_blocked_result("Missing credentials")
  - Then: Assert result.status == "blocked", "Missing credentials" in result.errors
- **From**: plan.md StartupResult with status="blocked"

T035 [GREEN→T034] Implement _create_blocked_result() method
- **File**: src/trading_bot/startup.py
- **Code**:
  ```python
  def _create_blocked_result(self, error_message: str, duration: float = 0.0) -> StartupResult:
      """Create a blocked result with error information."""
      if error_message not in self.errors:
          self.errors.append(error_message)

      return StartupResult(
          status="blocked",
          mode=self.config.trading.mode if hasattr(self, 'config') and self.config else "unknown",
          phase=self.config.phase_progression.current_phase if hasattr(self, 'config') and self.config else "unknown",
          steps=self.steps,
          errors=self.errors,
          warnings=self.warnings,
          component_states=self.component_states,
          startup_duration_seconds=duration,
          timestamp=datetime.now(timezone.utc).isoformat()
      )
  ```
- **From**: plan.md StartupResult schema

---

## Phase 3.7: Entry Point and CLI

T036 [RED] Write failing test: Parse arguments handles --dry-run flag
- **File**: tests/unit/test_main.py
- **Test**: test_parse_arguments_dry_run()
  - Given: sys.argv = ["main.py", "--dry-run"]
  - When: args = parse_arguments()
  - Then: Assert args.dry_run == True, args.json == False
- **From**: plan.md main.py parse_arguments()

T037 [GREEN→T036] Implement parse_arguments() function
- **File**: src/trading_bot/main.py (new file)
- **Code**:
  ```python
  import argparse
  from typing import Namespace

  def parse_arguments() -> Namespace:
      """Parse command-line arguments."""
      parser = argparse.ArgumentParser(
          description="Robinhood Trading Bot - Automated trading system"
      )
      parser.add_argument(
          "--dry-run",
          action="store_true",
          help="Run startup validation without entering trading loop"
      )
      parser.add_argument(
          "--json",
          action="store_true",
          help="Output status as JSON for machine parsing"
      )
      return parser.parse_args()
  ```
- **Pattern**: Standard argparse pattern
- **From**: plan.md main.py functions

T038 [RED] Write failing test: Main function exits with correct exit codes
- **File**: tests/unit/test_main.py
- **Test**: test_main_exit_code_success(monkeypatch)
  - Given: Valid configuration
  - When: exit_code = main()
  - Then: Assert exit_code == 0
- **From**: plan.md main.py exit code handling

T039 [GREEN→T038] Implement main() function
- **File**: src/trading_bot/main.py
- **Code**:
  ```python
  import sys
  from .config import Config
  from .startup import StartupOrchestrator

  def main() -> int:
      """Main entry point for trading bot."""
      try:
          args = parse_arguments()

          # Load configuration
          config = Config.from_env_and_json()

          # Run startup sequence
          orchestrator = StartupOrchestrator(
              config=config,
              dry_run=args.dry_run,
              json_output=args.json
          )
          result = orchestrator.run()

          # Handle result
          if result.status == "ready":
              if args.dry_run:
                  return 0  # Success - dry run complete
              # TODO: Enter trading loop here (future work)
              return 0
          else:
              # Startup blocked
              if not args.json:
                  print(f"\n❌ Startup failed:")
                  for error in result.errors:
                      print(f"  - {error}")

              # Determine exit code based on first error
              if result.errors:
                  error_msg = result.errors[0].lower()
                  if "configuration" in error_msg or "credentials" in error_msg:
                      return 1  # Configuration error
                  elif "validation" in error_msg or "phase-mode" in error_msg:
                      return 2  # Validation error
                  else:
                      return 3  # Initialization failure
              return 3  # Unknown error

      except KeyboardInterrupt:
          print("\n\n⚠️  Startup interrupted by user")
          return 130  # Standard exit code for SIGINT
      except Exception as e:
          print(f"\n❌ Fatal error: {e}")
          return 1

  if __name__ == "__main__":
      sys.exit(main())
  ```
- **From**: plan.md main.py main() function

T040 [P] Add __main__.py for python -m invocation
- **File**: src/trading_bot/__main__.py (new file)
- **Code**:
  ```python
  from .main import main
  import sys

  if __name__ == "__main__":
      sys.exit(main())
  ```
- **Pattern**: Standard Python module execution pattern
- **From**: plan.md main.py entry point

---

## Phase 3.8: Integration Testing

T041 [RED] Write integration test: Full startup flow with valid config
- **File**: tests/integration/test_startup_flow.py (new file)
- **Test**: test_full_startup_flow_paper_mode(tmp_path, monkeypatch)
  - Given: Valid .env and config.json in tmp_path
  - When: Run main() with --dry-run
  - Then: Assert exit code 0, logs/startup.log created, all steps success
- **From**: plan.md Integration Tests

T042 [GREEN→T041] Ensure integration test passes with real files
- **File**: tests/integration/test_startup_flow.py
- **Code**: Complete integration test that:
  1. Creates temporary .env and config.json
  2. Monkeypatches os.getcwd() to return tmp_path
  3. Calls main() with --dry-run
  4. Asserts all startup steps complete
  5. Verifies logs/startup.log exists
  6. Checks component_states populated
- **Pattern**: tests/integration/ existing patterns (if any)
- **From**: plan.md Integration Tests

T043 [RED] Write integration test: Startup fails with missing credentials
- **File**: tests/integration/test_startup_flow.py
- **Test**: test_startup_fails_missing_credentials(tmp_path, monkeypatch)
  - Given: config.json exists but .env missing
  - When: Run main()
  - Then: Assert exit code 1, error message includes "Missing credentials"
- **From**: plan.md [ERROR SCENARIOS]

T044 [GREEN→T043] Ensure integration test catches credential errors
- **File**: tests/integration/test_startup_flow.py
- **Code**: Integration test verifying:
  1. Missing .env detected early
  2. Appropriate error message shown
  3. Exit code 1 returned
  4. No partial initialization
- **From**: plan.md [ERROR SCENARIOS]

T045 [RED] Write integration test: Startup fails with phase-mode conflict
- **File**: tests/integration/test_startup_flow.py
- **Test**: test_startup_fails_phase_mode_conflict(tmp_path, monkeypatch)
  - Given: config.json with mode=live, phase=experience
  - When: Run main()
  - Then: Assert exit code 2, error includes "phase-mode conflict"
- **From**: plan.md [ERROR SCENARIOS]

T046 [GREEN→T045] Ensure integration test catches validation errors
- **File**: tests/integration/test_startup_flow.py
- **Code**: Integration test verifying:
  1. Phase-mode conflict detected by validator
  2. Startup blocked before component init
  3. Exit code 2 returned
  4. Error references Constitution §Safety_First
- **From**: plan.md [ERROR SCENARIOS]

---

## Phase 3.9: Documentation and Polish

T047 [P] Add docstrings to all StartupOrchestrator methods
- **File**: src/trading_bot/startup.py
- **Add**: Google-style docstrings for:
  - StartupOrchestrator class
  - run() method
  - All private methods (_display_banner, _load_config, etc.)
- **Pattern**: Existing docstrings in config.py, validator.py
- **From**: plan.md Implementation Checklist Phase 6

T048 [P] Update README.md with startup instructions
- **File**: README.md
- **Add section**: "Usage" with:
  - `python -m src.trading_bot.main` - Normal startup
  - `python -m src.trading_bot.main --dry-run` - Validation only
  - `python -m src.trading_bot.main --json` - Machine-readable output
- **Add section**: "Troubleshooting" with:
  - Check logs/startup.log for errors
  - Common error scenarios and fixes
- **Pattern**: Existing README.md structure
- **From**: plan.md [DOCUMENTATION UPDATES]

T049 [P] Add startup error scenarios to error-log.md
- **File**: specs/startup-sequence/error-log.md
- **Add entries**:
  - Error 1: Missing .env file (remediation: copy .env.example)
  - Error 2: Invalid config.json (remediation: check JSON syntax)
  - Error 3: Phase-mode conflict (remediation: change mode or phase)
  - Error 4: Filesystem permissions (remediation: check directory permissions)
  - Error 5: Component init failure (remediation: check logs/startup.log)
- **Pattern**: Existing error-log.md entries
- **From**: plan.md [ERROR SCENARIOS]

T050 [P] Update CHANGELOG.md with startup-sequence feature
- **File**: CHANGELOG.md
- **Add entry**:
  ```markdown
  ## [Unreleased]
  ### Added
  - Startup sequence with orchestrated component initialization
  - Startup validation with fail-fast error handling
  - --dry-run flag for configuration validation
  - --json flag for machine-readable status output
  - logs/startup.log for startup audit trail
  - Unicode progress indicators for visual feedback
  ```
- **Pattern**: Keep-a-Changelog format
- **From**: plan.md [DOCUMENTATION UPDATES]

---

## TASK SUMMARY

**Total Tasks**: 50

**By Phase**:
- Phase 3.0: Test Infrastructure (2 tasks)
- Phase 3.1: Core Data Structures (4 tasks - 2 RED, 2 GREEN)
- Phase 3.2: Configuration Loading (6 tasks - 3 RED, 3 GREEN)
- Phase 3.3: Component Initialization (9 tasks - 5 RED, 4 GREEN + 1 extension)
- Phase 3.4: Display & Output (6 tasks - 3 RED, 3 GREEN)
- Phase 3.5: Main Orchestration (4 tasks - 2 RED, 2 GREEN)
- Phase 3.6: Error Handling (4 tasks - 2 RED, 2 GREEN)
- Phase 3.7: Entry Point & CLI (5 tasks - 2 RED, 2 GREEN + 1 parallel)
- Phase 3.8: Integration Testing (6 tasks - 3 RED, 3 GREEN)
- Phase 3.9: Documentation (4 tasks - all parallel)

**By TDD Cycle**:
- RED (write failing tests): 17 tasks
- GREEN (implement to pass tests): 18 tasks
- REFACTOR: 0 tasks (no refactoring needed - clean first implementation)
- Parallel (independent): 11 tasks
- Extension: 1 task (extend existing logger.py)
- Integration: 4 tasks (combined RED+GREEN integration tests)

**By Type**:
- Backend (Python): 42 tasks
- Testing: 20 tasks (unit + integration)
- Documentation: 4 tasks
- Configuration: 4 tasks

**Estimated Duration**: 10-15 hours total
- Phase 3.0-3.1: 1 hour (test infrastructure + data structures)
- Phase 3.2-3.3: 4 hours (config loading + component init)
- Phase 3.4-3.5: 2 hours (display + orchestration)
- Phase 3.6-3.7: 2 hours (error handling + CLI)
- Phase 3.8: 3 hours (integration testing)
- Phase 3.9: 1 hour (documentation)

**Dependencies**:
- T003-T006 must complete before T007 (need dataclasses for orchestrator)
- T007-T012 must complete before T013 (need config/validation before component init)
- T013-T021 must complete before T028 (need all components before run())
- T001-T002 should complete early (test infrastructure needed throughout)
- T036-T040 depend on T028-T031 (CLI needs working orchestrator)
- T041-T046 depend on T036-T040 (integration tests need CLI)
- T047-T050 are parallel and independent (documentation)

**Success Criteria**:
- All 50 tasks complete
- Test coverage >90% for startup.py
- All integration tests pass
- Startup time <5 seconds
- All error scenarios have tests and remediation guidance
