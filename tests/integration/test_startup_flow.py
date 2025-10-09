"""
Integration tests for startup flow.

Tests full startup sequence from main() entry point with real files.
Uses temporary directories, monkeypatch, and real Config loading.

Constitution v1.0.0: End-to-end validation of startup sequence.
"""

from unittest.mock import patch


class TestStartupFlowIntegration:
    """Integration tests for full startup flow."""

    def test_full_startup_flow_paper_mode(self, tmp_path, monkeypatch, capsys):
        """Test full startup flow in paper mode with --dry-run.

        T041 [RED]: Write integration test for full startup flow
        T042 [GREEN→T041]: Ensure integration test passes with real files
        - Given: Valid .env and config.json in tmp_path
        - When: Run main() with --dry-run
        - Then: Assert exit code 0, logs/startup.log created, all steps success
        """
        # Given: Valid .env and config.json in tmp_path
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "ROBINHOOD_USERNAME=test_user\n"
            "ROBINHOOD_PASSWORD=test_pass\n"
            "ROBINHOOD_MFA_SECRET=TESTSECRET123456\n"
            "ROBINHOOD_DEVICE_TOKEN=test_device_token\n"
        )

        # Create config.json
        config_file = tmp_path / "config.json"
        config_file.write_text(
            '{\n'
            '  "trading": {"mode": "paper"},\n'
            '  "phase_progression": {"current_phase": "experience"},\n'
            '  "risk_management": {\n'
            '    "max_daily_loss_pct": 3.0,\n'
            '    "max_consecutive_losses": 3,\n'
            '    "max_position_pct": 5.0\n'
            '  }\n'
            '}\n'
        )

        # Create logs directory
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Monkeypatch environment and cwd
        monkeypatch.setenv("ROBINHOOD_USERNAME", "test_user")
        monkeypatch.setenv("ROBINHOOD_PASSWORD", "test_pass")
        monkeypatch.chdir(tmp_path)

        # When: Run main() with --dry-run
        with patch('sys.argv', ['main.py', '--dry-run']):
            from src.trading_bot.main import main
            exit_code = main()

        # Then: Assert exit code 0
        assert exit_code == 0, "Expected exit code 0 for successful dry run"

        # Assert logs/startup.log created
        startup_log = logs_dir / "startup.log"
        assert startup_log.exists(), "Expected logs/startup.log to be created"

        # Assert all steps succeeded (verify by checking log content)
        log_content = startup_log.read_text()
        assert "Startup sequence initiated" in log_content, "Expected startup log message"

        # T042 [GREEN→T041]: Verify comprehensive startup completion
        # Assert console output shows startup complete
        captured = capsys.readouterr()
        assert "STARTUP COMPLETE" in captured.out, "Expected startup completion message"
        assert "Ready to trade" in captured.out, "Expected ready to trade message"
        assert "PAPER TRADING" in captured.out, "Expected paper trading mode display"
        assert "Current Phase: experience" in captured.out, "Expected current phase display"
        assert "Circuit Breaker: Active" in captured.out, "Expected circuit breaker status"

    def test_startup_fails_missing_credentials(self, tmp_path, monkeypatch, capsys):
        """Test startup fails when credentials are missing.

        T043 [RED]: Write integration test for startup fails with missing credentials
        - Given: config.json exists but .env missing
        - When: Run main()
        - Then: Assert exit code 1, error message includes "Missing credentials"
        """
        # Given: config.json exists but .env missing
        config_file = tmp_path / "config.json"
        config_file.write_text(
            '{\n'
            '  "trading": {"mode": "paper"},\n'
            '  "phase_progression": {"current_phase": "experience"},\n'
            '  "risk_management": {\n'
            '    "max_daily_loss_pct": 3.0,\n'
            '    "max_consecutive_losses": 3,\n'
            '    "max_position_pct": 5.0\n'
            '  }\n'
            '}\n'
        )

        # Create logs directory
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Monkeypatch cwd but DON'T set credentials in environment
        monkeypatch.chdir(tmp_path)
        # Clear any existing credentials from environment
        monkeypatch.delenv("ROBINHOOD_USERNAME", raising=False)
        monkeypatch.delenv("ROBINHOOD_PASSWORD", raising=False)

        # When: Run main() with --dry-run
        with patch('sys.argv', ['main.py', '--dry-run']):
            from src.trading_bot.main import main
            exit_code = main()

        # Then: Assert exit code 1 (configuration error)
        assert exit_code == 1, "Expected exit code 1 for missing credentials"

        # Assert error message includes "credentials" or "username" or "password"
        captured = capsys.readouterr()
        error_output = captured.out.lower()
        assert any(term in error_output for term in ["credential", "username", "password", "missing"]), \
            f"Expected error message about missing credentials, got: {captured.out}"

    def test_startup_fails_phase_mode_conflict(self, tmp_path, monkeypatch, capsys):
        """Test startup fails with phase-mode conflict.

        T045 [RED]: Write integration test for startup fails with phase-mode conflict
        - Given: config.json with mode=live, phase=experience
        - When: Run main()
        - Then: Assert exit code 2, error includes "phase-mode conflict"
        """
        # Given: Valid .env but config.json with phase-mode conflict
        env_file = tmp_path / ".env"
        env_file.write_text(
            "ROBINHOOD_USERNAME=test_user\n"
            "ROBINHOOD_PASSWORD=test_pass\n"
            "ROBINHOOD_MFA_SECRET=TESTSECRET123456\n"
            "ROBINHOOD_DEVICE_TOKEN=test_device_token\n"
        )

        # Create config.json with mode=live, phase=experience (conflict!)
        config_file = tmp_path / "config.json"
        config_file.write_text(
            '{\n'
            '  "trading": {"mode": "live"},\n'
            '  "phase_progression": {"current_phase": "experience"},\n'
            '  "risk_management": {\n'
            '    "max_daily_loss_pct": 3.0,\n'
            '    "max_consecutive_losses": 3,\n'
            '    "max_position_pct": 5.0\n'
            '  }\n'
            '}\n'
        )

        # Create logs directory
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Monkeypatch environment and cwd
        monkeypatch.setenv("ROBINHOOD_USERNAME", "test_user")
        monkeypatch.setenv("ROBINHOOD_PASSWORD", "test_pass")
        monkeypatch.chdir(tmp_path)

        # When: Run main() with --dry-run
        with patch('sys.argv', ['main.py', '--dry-run']):
            from src.trading_bot.main import main
            exit_code = main()

        # Then: Assert exit code 2 (validation error)
        assert exit_code == 2, "Expected exit code 2 for phase-mode conflict validation error"

        # Assert error message includes "phase-mode" or "conflict" or validation failure
        captured = capsys.readouterr()
        error_output = captured.out.lower()
        assert any(term in error_output for term in ["phase", "validation", "experience", "live"]), \
            f"Expected error message about phase-mode conflict, got: {captured.out}"

    def test_json_output_mode(self, tmp_path, monkeypatch, capsys):
        """Test JSON output mode produces valid machine-readable output.

        Additional test for end-to-end JSON output validation.

        - Given: Valid environment with --json flag
        - When: Run main() with --json --dry-run
        - Then: Assert valid JSON output with expected structure
        """
        import json

        # Given: Valid .env and config.json in tmp_path
        env_file = tmp_path / ".env"
        env_file.write_text(
            "ROBINHOOD_USERNAME=test_user\n"
            "ROBINHOOD_PASSWORD=test_pass\n"
            "ROBINHOOD_MFA_SECRET=TESTSECRET123456\n"
            "ROBINHOOD_DEVICE_TOKEN=test_device_token\n"
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(
            '{\n'
            '  "trading": {"mode": "paper"},\n'
            '  "phase_progression": {"current_phase": "experience"},\n'
            '  "risk_management": {\n'
            '    "max_daily_loss_pct": 3.0,\n'
            '    "max_consecutive_losses": 3,\n'
            '    "max_position_pct": 5.0\n'
            '  }\n'
            '}\n'
        )

        # Create logs directory
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Monkeypatch environment and cwd
        monkeypatch.setenv("ROBINHOOD_USERNAME", "test_user")
        monkeypatch.setenv("ROBINHOOD_PASSWORD", "test_pass")
        monkeypatch.chdir(tmp_path)

        # When: Run main() with --json --dry-run
        with patch('sys.argv', ['main.py', '--json', '--dry-run']):
            from src.trading_bot.main import main
            exit_code = main()

        # Then: Assert exit code 0
        assert exit_code == 0, "Expected exit code 0 for successful dry run"

        # Capture and validate JSON output
        captured = capsys.readouterr()

        # Extract JSON from output (filter out logger messages)
        # JSON output starts with '{'
        output_lines = captured.out.strip().split('\n')
        json_lines = []
        in_json = False
        for line in output_lines:
            if line.strip().startswith('{'):
                in_json = True
            if in_json:
                json_lines.append(line)

        json_text = '\n'.join(json_lines)

        # Parse JSON output
        json_output = json.loads(json_text)

        # Validate structure
        assert json_output["status"] == "ready"
        assert json_output["mode"] == "paper"
        assert json_output["phase"] == "experience"
        assert "startup_duration_seconds" in json_output
        assert "timestamp" in json_output
        assert "components" in json_output
        assert "errors" in json_output
        assert "warnings" in json_output

        # Validate components
        assert "logging" in json_output["components"]
        assert "mode_switcher" in json_output["components"]
        assert "circuit_breaker" in json_output["components"]
        assert "trading_bot" in json_output["components"]

        # Validate no errors
        assert len(json_output["errors"]) == 0
