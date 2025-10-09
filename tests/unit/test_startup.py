"""
Unit tests for startup sequence components.

Tests:
- StartupStep dataclass
- StartupOrchestrator initialization
- Individual startup steps
"""

import pytest
from src.trading_bot.startup import StartupStep, StartupResult, StartupOrchestrator
from src.trading_bot.config import Config


class TestStartupStep:
    """Tests for StartupStep dataclass."""

    def test_startup_step_dataclass(self):
        """Test StartupStep dataclass tracks step status."""
        # Given: Create StartupStep with name, status
        step = StartupStep(
            name="Loading config",
            status="running"
        )

        # When: Access attributes
        # Then: Assert all attributes correct
        assert step.name == "Loading config"
        assert step.status == "running"
        assert step.error_message is None
        assert step.duration_seconds == 0.0

        # Test with error
        step_failed = StartupStep(
            name="Validation",
            status="failed",
            error_message="Missing credentials",
            duration_seconds=1.5
        )
        assert step_failed.status == "failed"
        assert step_failed.error_message == "Missing credentials"
        assert step_failed.duration_seconds == 1.5


class TestStartupResult:
    """Tests for StartupResult dataclass."""

    def test_startup_result_dataclass(self):
        """Test StartupResult aggregates all startup data."""
        # Given: Create StartupResult with all fields
        steps = [
            StartupStep(name="Config", status="success"),
            StartupStep(name="Validation", status="success")
        ]

        result = StartupResult(
            status="ready",
            mode="paper",
            phase="experience",
            steps=steps,
            errors=[],
            warnings=["Low balance"],
            component_states={"logging": {"status": "ready"}},
            startup_duration_seconds=2.5,
            timestamp="2025-01-08T10:00:00Z"
        )

        # When: Access all attributes
        # Then: Assert all fields populated correctly
        assert result.status == "ready"
        assert result.mode == "paper"
        assert result.phase == "experience"
        assert len(result.steps) == 2
        assert result.errors == []
        assert result.warnings == ["Low balance"]
        assert result.component_states == {"logging": {"status": "ready"}}
        assert result.startup_duration_seconds == 2.5
        assert result.timestamp == "2025-01-08T10:00:00Z"

        # Test blocked status
        result_blocked = StartupResult(
            status="blocked",
            mode="paper",
            phase="experience",
            steps=[],
            errors=["Validation failed"],
            warnings=[],
            component_states={},
            startup_duration_seconds=0.5,
            timestamp="2025-01-08T10:00:00Z"
        )
        assert result_blocked.status == "blocked"
        assert "Validation failed" in result_blocked.errors


class TestStartupOrchestrator:
    """Tests for StartupOrchestrator class."""

    def test_orchestrator_init(self, mock_config):
        """Test Orchestrator initializes with config."""
        # Given: Valid Config instance
        # When: Create orchestrator
        orchestrator = StartupOrchestrator(
            config=mock_config,
            dry_run=True,
            json_output=False
        )

        # Then: Assert all fields initialized correctly
        assert orchestrator.config == mock_config
        assert orchestrator.dry_run == True
        assert orchestrator.json_output == False
        assert orchestrator.steps == []
        assert orchestrator.errors == []
        assert orchestrator.warnings == []
        assert orchestrator.component_states == {}
        assert orchestrator.start_time is None

    def test_load_config_success(self, valid_env_file, valid_config_file, monkeypatch, tmp_path):
        """Test load_config successfully loads configuration."""
        # Given: Valid .env and config.json files
        # Monkeypatch to use test environment
        monkeypatch.setenv("ROBINHOOD_USERNAME", "test_user")
        monkeypatch.setenv("ROBINHOOD_PASSWORD", "test_pass")

        # When: Load config
        orchestrator = StartupOrchestrator(config=None, dry_run=True)
        config = orchestrator._load_config()

        # Then: Config loaded successfully
        assert config is not None
        assert config.robinhood_username == "test_user"
        assert config.robinhood_password == "test_pass"
        assert len(orchestrator.steps) == 1
        assert orchestrator.steps[0].name == "Loading configuration"
        assert orchestrator.steps[0].status == "success"

    def test_validate_config_success(self, mock_config):
        """Test validate_config with valid configuration."""
        # Given: Orchestrator with valid config
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True)

        # When: Validate config
        is_valid, errors, warnings = orchestrator._validate_config()

        # Then: Validation passes
        assert is_valid == True
        assert errors == []
        assert len(orchestrator.steps) == 1
        assert orchestrator.steps[0].name == "Validating configuration"
        assert orchestrator.steps[0].status == "success"

    def test_initialize_logging_creates_startup_log(self, mock_config, tmp_logs_dir, monkeypatch):
        """Test initialize_logging creates startup.log file."""
        # Given: Orchestrator with config pointing to tmp logs dir
        mock_config.logs_dir = str(tmp_logs_dir)
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True)

        # When: Initialize logging
        orchestrator._initialize_logging()

        # Then: startup.log exists
        startup_log = tmp_logs_dir / "startup.log"
        assert startup_log.exists()
        assert len(orchestrator.steps) == 1
        assert orchestrator.steps[0].name == "Initializing logging system"
        assert orchestrator.steps[0].status == "success"
        assert "logging" in orchestrator.component_states

    def test_initialize_mode_switcher(self, mock_config):
        """Test initialize_mode_switcher creates ModeSwitcher."""
        # Given: Orchestrator with paper mode config
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True)

        # When: Initialize mode switcher
        mode_switcher = orchestrator._initialize_mode_switcher()

        # Then: Mode switcher created
        assert mode_switcher is not None
        assert hasattr(orchestrator, 'mode_switcher')
        assert "mode_switcher" in orchestrator.component_states
        assert orchestrator.component_states["mode_switcher"]["status"] == "ready"

    def test_initialize_circuit_breakers(self, mock_config):
        """Test initialize_circuit_breakers creates CircuitBreaker."""
        # Given: Orchestrator with risk params
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True)

        # When: Initialize circuit breakers
        circuit_breaker = orchestrator._initialize_circuit_breakers()

        # Then: Circuit breaker created with correct params
        assert circuit_breaker is not None
        assert hasattr(orchestrator, 'circuit_breaker')
        assert "circuit_breaker" in orchestrator.component_states

    def test_initialize_bot(self, mock_config):
        """Test initialize_bot creates TradingBot."""
        # Given: Orchestrator with paper trading config
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True)

        # When: Initialize bot
        bot = orchestrator._initialize_bot()

        # Then: Bot created with correct settings
        assert bot is not None
        assert hasattr(orchestrator, 'bot')
        assert "trading_bot" in orchestrator.component_states
        assert orchestrator.component_states["trading_bot"]["is_running"] == False
