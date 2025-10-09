"""
Unit tests for main.py - CLI entry point and argument parsing

Tests follow TDD approach:
- T036 [RED]: Test parse_arguments() with --dry-run flag
- T038 [RED]: Test main() function exit codes
"""

import sys
from unittest.mock import MagicMock, patch


class TestParseArguments:
    """Test suite for parse_arguments() function."""

    def test_parse_arguments_dry_run(self):
        """T036 [RED]: Test parse_arguments() with --dry-run flag.

        Given: sys.argv = ["main.py", "--dry-run"]
        When: args = parse_arguments()
        Then: Assert args.dry_run == True, args.json == False
        """
        # This will fail because parse_arguments() doesn't exist yet
        from src.trading_bot.main import parse_arguments

        with patch.object(sys, 'argv', ["main.py", "--dry-run"]):
            args = parse_arguments()

            assert args.dry_run is True
            assert args.json is False

    def test_parse_arguments_json_output(self):
        """Test parse_arguments() with --json flag.

        Given: sys.argv = ["main.py", "--json"]
        When: args = parse_arguments()
        Then: Assert args.json == True, args.dry_run == False
        """
        from src.trading_bot.main import parse_arguments

        with patch.object(sys, 'argv', ["main.py", "--json"]):
            args = parse_arguments()

            assert args.json is True
            assert args.dry_run is False

    def test_parse_arguments_both_flags(self):
        """Test parse_arguments() with both flags.

        Given: sys.argv = ["main.py", "--dry-run", "--json"]
        When: args = parse_arguments()
        Then: Assert both flags are True
        """
        from src.trading_bot.main import parse_arguments

        with patch.object(sys, 'argv', ["main.py", "--dry-run", "--json"]):
            args = parse_arguments()

            assert args.dry_run is True
            assert args.json is True

    def test_parse_arguments_no_flags(self):
        """Test parse_arguments() with no flags (defaults).

        Given: sys.argv = ["main.py"]
        When: args = parse_arguments()
        Then: Assert both flags are False
        """
        from src.trading_bot.main import parse_arguments

        with patch.object(sys, 'argv', ["main.py"]):
            args = parse_arguments()

            assert args.dry_run is False
            assert args.json is False


class TestMain:
    """Test suite for main() function."""

    def test_main_exit_code_success(self, monkeypatch):
        """T038 [RED]: Test main() returns 0 on successful startup.

        Given: Valid configuration
        When: exit_code = main()
        Then: Assert exit_code == 0
        """
        # This will fail because main() doesn't exist yet
        from src.trading_bot.main import main

        # Mock sys.argv for dry run mode
        monkeypatch.setattr(sys, 'argv', ["main.py", "--dry-run"])

        # Mock Config.from_env_and_json to return valid config
        mock_config = MagicMock()
        mock_config.paper_trading = True
        mock_config.current_phase = "experience"
        mock_config.logs_dir = "logs"
        mock_config.max_daily_loss_pct = 3.0
        mock_config.max_consecutive_losses = 3
        mock_config.max_trades_per_day = 5

        # Mock StartupOrchestrator
        mock_result = MagicMock()
        mock_result.status = "ready"
        mock_result.errors = []

        with patch('src.trading_bot.config.Config') as MockConfig:
            with patch('src.trading_bot.startup.StartupOrchestrator') as MockOrchestrator:
                MockConfig.from_env_and_json.return_value = mock_config
                MockOrchestrator.return_value.run.return_value = mock_result

                exit_code = main()

        assert exit_code == 0

    def test_main_exit_code_configuration_error(self, monkeypatch):
        """Test main() returns 1 on configuration error.

        Given: Invalid configuration
        When: exit_code = main()
        Then: Assert exit_code == 1
        """
        from src.trading_bot.main import main

        monkeypatch.setattr(sys, 'argv', ["main.py"])

        # Mock Config.from_env_and_json to raise ValueError
        with patch('src.trading_bot.config.Config') as MockConfig:
            MockConfig.from_env_and_json.side_effect = ValueError("Missing credentials")

            exit_code = main()

        assert exit_code == 1

    def test_main_exit_code_validation_error(self, monkeypatch):
        """Test main() returns 2 on validation error.

        Given: Validation failure
        When: exit_code = main()
        Then: Assert exit_code == 2
        """
        from src.trading_bot.main import main

        monkeypatch.setattr(sys, 'argv', ["main.py"])

        mock_config = MagicMock()
        mock_result = MagicMock()
        mock_result.status = "blocked"
        mock_result.errors = ["Validation failed: Invalid phase-mode combination"]

        with patch('src.trading_bot.config.Config') as MockConfig:
            with patch('src.trading_bot.startup.StartupOrchestrator') as MockOrchestrator:
                MockConfig.from_env_and_json.return_value = mock_config
                MockOrchestrator.return_value.run.return_value = mock_result

                exit_code = main()

        assert exit_code == 2

    def test_main_exit_code_keyboard_interrupt(self, monkeypatch, capsys):
        """Test main() returns 130 on KeyboardInterrupt.

        Given: User presses Ctrl+C during startup
        When: exit_code = main()
        Then: Assert exit_code == 130
        """
        from src.trading_bot.main import main

        monkeypatch.setattr(sys, 'argv', ["main.py"])

        with patch('src.trading_bot.config.Config') as MockConfig:
            MockConfig.from_env_and_json.side_effect = KeyboardInterrupt()

            exit_code = main()

        assert exit_code == 130

        # Verify message printed
        captured = capsys.readouterr()
        assert "interrupted by user" in captured.out.lower()

    def test_main_prints_errors_non_json_mode(self, monkeypatch, capsys):
        """Test main() prints errors in non-JSON mode.

        Given: Startup fails with errors
        When: main() called without --json
        Then: Errors are printed to stdout
        """
        from src.trading_bot.main import main

        monkeypatch.setattr(sys, 'argv', ["main.py"])

        mock_config = MagicMock()
        mock_result = MagicMock()
        mock_result.status = "blocked"
        mock_result.errors = ["Configuration loading failed", "Validation error"]

        with patch('src.trading_bot.config.Config') as MockConfig:
            with patch('src.trading_bot.startup.StartupOrchestrator') as MockOrchestrator:
                MockConfig.from_env_and_json.return_value = mock_config
                MockOrchestrator.return_value.run.return_value = mock_result

                main()  # Don't need exit code, just checking output

        captured = capsys.readouterr()
        assert "Startup failed" in captured.out
        assert "Configuration loading failed" in captured.out
        assert "Validation error" in captured.out

    def test_main_no_error_print_json_mode(self, monkeypatch, capsys):
        """Test main() suppresses error printing in JSON mode.

        Given: Startup fails with --json flag
        When: main() called
        Then: Errors not printed (orchestrator handles JSON output)
        """
        from src.trading_bot.main import main

        monkeypatch.setattr(sys, 'argv', ["main.py", "--json"])

        mock_config = MagicMock()
        mock_result = MagicMock()
        mock_result.status = "blocked"
        mock_result.errors = ["Configuration error"]

        with patch('src.trading_bot.config.Config') as MockConfig:
            with patch('src.trading_bot.startup.StartupOrchestrator') as MockOrchestrator:
                MockConfig.from_env_and_json.return_value = mock_config
                MockOrchestrator.return_value.run.return_value = mock_result

                main()  # Don't need exit code, just checking output

        captured = capsys.readouterr()
        # In JSON mode, errors should not be printed by main()
        # (orchestrator handles JSON output)
        assert "Startup failed" not in captured.out


class TestMainModule:
    """Test suite for __main__.py module invocation."""

    def test_main_module_importable(self):
        """Test __main__.py module can be imported.

        CRITICAL-002: Add test coverage for __main__.py (0% → 100%)

        Given: __main__.py exists
        When: Module is imported
        Then: Assert it imports without error and has main reference
        """
        # This test ensures __main__.py exists and is importable
        import src.trading_bot.__main__ as main_module

        # Verify the module has access to main function
        assert hasattr(main_module, 'main'), "__main__.py should import main function"
        assert callable(main_module.main), "main should be callable"
