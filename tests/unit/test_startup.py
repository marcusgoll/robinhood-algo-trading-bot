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

    def test_display_banner_paper_mode(self, mock_config, capsys):
        """Test display_banner shows mode and phase.

        T022 [RED]: Write failing test for _display_banner()
        - Given: Config with mode=paper, phase=experience
        - When: orchestrator._display_banner()
        - Then: Assert stdout contains "PAPER TRADING", "experience"
        """
        # Given: Config with mode=paper, phase=experience
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True)

        # When: Display banner
        orchestrator._display_banner()

        # Then: Assert stdout contains "PAPER TRADING"
        captured = capsys.readouterr()
        assert "PAPER TRADING" in captured.out
        assert "Simulation - No Real Money" in captured.out
        assert "ROBINHOOD TRADING BOT" in captured.out

    def test_display_summary_shows_config(self, mock_config, capsys):
        """Test display_summary shows startup configuration summary.

        T024 [RED]: Write failing test for _display_summary()
        - Given: Successful startup
        - When: orchestrator._display_summary()
        - Then: Assert stdout contains "STARTUP COMPLETE", "Current Phase", "Circuit Breaker: Active"
        """
        # Given: Orchestrator with successful startup
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True)

        # When: Display summary
        orchestrator._display_summary()

        # Then: Assert stdout contains expected sections
        captured = capsys.readouterr()
        assert "STARTUP COMPLETE" in captured.out
        assert "Ready to trade" in captured.out
        assert "Current Phase: experience" in captured.out
        assert "Max Trades Today: 999" in captured.out
        assert "Circuit Breaker: Active" in captured.out
        assert "Max Loss: 3.0%" in captured.out
        assert "Max Consecutive: 3" in captured.out
        assert "[DRY RUN] Exiting without starting trading loop" in captured.out

    def test_json_output_format(self, mock_config):
        """Test JSON output format matches schema."""
        import json
        from datetime import datetime, timezone

        # Given: Successful startup result
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True, json_output=True)

        result = StartupResult(
            status="ready",
            mode="paper",
            phase="experience",
            steps=[
                StartupStep(name="Config", status="success"),
                StartupStep(name="Validation", status="success")
            ],
            errors=[],
            warnings=["Low balance"],
            component_states={
                "logging": {"status": "ready"},
                "mode_switcher": {"status": "ready"}
            },
            startup_duration_seconds=2.5,
            timestamp="2025-01-08T10:00:00Z"
        )

        # When: Format JSON output
        json_output = orchestrator._format_json_output(result)

        # Then: Assert JSON has all required fields
        parsed = json.loads(json_output)
        assert parsed["status"] == "ready"
        assert parsed["mode"] == "paper"
        assert parsed["phase"] == "experience"
        assert parsed["startup_duration_seconds"] == 2.5
        assert parsed["timestamp"] == "2025-01-08T10:00:00Z"
        assert "logging" in parsed["components"]
        assert "mode_switcher" in parsed["components"]
        assert parsed["errors"] == []
        assert parsed["warnings"] == ["Low balance"]

    def test_verify_health_checks_components(self, mock_config, tmp_logs_dir):
        """Test verify_health checks all components are ready.

        T030 [RED]: Write failing test for _verify_health()
        - Given: All components initialized
        - When: orchestrator._verify_health()
        - Then: Assert all component_states have status="ready"
        """
        # Given: Orchestrator with all components initialized
        mock_config.logs_dir = str(tmp_logs_dir)
        orchestrator = StartupOrchestrator(config=mock_config, dry_run=True)

        # Initialize all required components
        orchestrator._initialize_logging()
        orchestrator._initialize_mode_switcher()
        orchestrator._initialize_circuit_breakers()
        orchestrator._initialize_bot()

        # When: Verify health
        orchestrator._verify_health()

        # Then: Assert health verification step added
        assert len(orchestrator.steps) == 5  # 4 init steps + 1 health check
        assert orchestrator.steps[-1].name == "Verifying component health"
        assert orchestrator.steps[-1].status == "success"

        # Assert all components have status="ready"
        assert orchestrator.component_states["logging"]["status"] == "ready"
        assert orchestrator.component_states["mode_switcher"]["status"] == "ready"
        assert orchestrator.component_states["circuit_breaker"]["status"] == "ready"
        assert orchestrator.component_states["trading_bot"]["status"] == "ready"
