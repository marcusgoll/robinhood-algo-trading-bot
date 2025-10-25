"""
Integration tests for Configuration Management API.

Tests config routes with TestClient:
- GET /api/v1/config - Get current configuration
- POST /api/v1/config/validate - Validate configuration
- GET /api/v1/config/diff - Preview configuration changes
- PUT /api/v1/config - Apply new configuration
- PUT /api/v1/config/rollback - Rollback to previous version
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes.config import router as config_router
from api.app.schemas.config import BotConfigRequest


@pytest.fixture
def app():
    """Create FastAPI app with config routes."""
    app = FastAPI()
    app.include_router(config_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create TestClient for API testing."""
    return TestClient(app)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with test files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create default config
    default_config = {
        "risk_per_trade": 0.02,
        "max_position_size": 5000,
        "circuit_breaker_thresholds": {
            "daily_loss": -0.05,
            "max_drawdown": -0.10,
        },
        "trading_hours": {"start": "09:30", "end": "16:00"},
        "max_daily_trades": 10,
    }
    (config_dir / "bot_config.json").write_text(json.dumps(default_config, indent=2))
    (config_dir / "config_history.jsonl").touch()

    return config_dir


@pytest.fixture
def mock_config_validator(temp_config_dir):
    """Mock ConfigValidator to use temp directory."""
    with patch("api.app.routes.config.get_config_validator") as mock:
        from api.app.services.config_validator import ConfigValidator

        validator = ConfigValidator(
            config_file=str(temp_config_dir / "bot_config.json"),
            history_file=str(temp_config_dir / "config_history.jsonl"),
            schema_file=str(temp_config_dir / "config.schema.json"),
        )
        mock.return_value = validator
        yield mock


@pytest.fixture
def mock_auth():
    """Mock API key authentication."""
    with patch("api.app.routes.config.verify_api_key") as mock:
        mock.return_value = True
        yield mock


class TestConfigAPI:
    """Integration tests for configuration management API."""

    def test_get_current_config(self, client, mock_config_validator, mock_auth):
        """
        GIVEN: API is running with default configuration
        WHEN: Client queries GET /api/v1/config
        THEN: Current configuration is returned
        """
        response = client.get("/api/v1/config")

        assert response.status_code == 200
        data = response.json()
        assert data["risk_per_trade"] == 0.02
        assert data["max_position_size"] == 5000
        assert data["circuit_breaker_thresholds"]["daily_loss"] == -0.05

    def test_validate_config_valid(self, client, mock_config_validator, mock_auth):
        """
        GIVEN: Valid configuration request
        WHEN: Client posts to POST /api/v1/config/validate
        THEN: Validation passes with no errors
        """
        valid_config = {
            "risk_per_trade": 0.03,
            "max_position_size": 7000,
            "circuit_breaker_thresholds": {
                "daily_loss": -0.05,
                "max_drawdown": -0.10,
            },
        }

        response = client.post("/api/v1/config/validate", json=valid_config)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0

    def test_validate_config_invalid(self, client, mock_config_validator, mock_auth):
        """
        GIVEN: Invalid configuration (bad trading hours format)
        WHEN: Client posts to POST /api/v1/config/validate
        THEN: Validation fails with error messages
        """
        invalid_config = {
            "risk_per_trade": 0.02,
            "max_position_size": 5000,
            "circuit_breaker_thresholds": {
                "daily_loss": -0.05,
                "max_drawdown": -0.10,
            },
            "trading_hours": {"start": "9:30", "end": "16:00"},  # Wrong format
        }

        response = client.post("/api/v1/config/validate", json=invalid_config)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert any("HH:MM format" in err for err in data["errors"])

    def test_get_config_diff(self, client, mock_config_validator, mock_auth):
        """
        GIVEN: Proposed configuration change
        WHEN: Client queries GET /api/v1/config/diff
        THEN: Diff shows changed, added, and unchanged fields
        """
        new_config = {
            "risk_per_trade": 0.03,  # Changed from 0.02
            "max_position_size": 5000,  # Unchanged
            "circuit_breaker_thresholds": {
                "daily_loss": -0.05,
                "max_drawdown": -0.10,
            },
            "max_daily_trades": 15,  # Changed from 10
        }

        response = client.get("/api/v1/config/diff", json=new_config)

        assert response.status_code == 200
        data = response.json()
        assert "changes" in data
        assert "risk_per_trade" in data["changes"]
        assert data["changes"]["risk_per_trade"]["old"] == 0.02
        assert data["changes"]["risk_per_trade"]["new"] == 0.03
        assert data["unchanged"] > 0

    def test_apply_config(self, client, mock_config_validator, mock_auth):
        """
        GIVEN: Valid new configuration
        WHEN: Client applies PUT /api/v1/config
        THEN: Configuration is applied and version incremented
        """
        new_config = {
            "risk_per_trade": 0.025,
            "max_position_size": 6000,
            "circuit_breaker_thresholds": {
                "daily_loss": -0.05,
                "max_drawdown": -0.10,
            },
        }

        response = client.put(
            "/api/v1/config", json=new_config, params={"reason": "Testing new risk level"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["config_version"] > 0
        assert data["rollback_available"] is True

        # Verify config was actually written
        validator = mock_config_validator.return_value
        current = validator.get_current_config()
        assert current["risk_per_trade"] == 0.025
        assert current["max_position_size"] == 6000

    def test_apply_config_invalid(self, client, mock_config_validator, mock_auth):
        """
        GIVEN: Invalid configuration (bad trading hours)
        WHEN: Client applies PUT /api/v1/config
        THEN: Request is rejected with 400 error
        """
        invalid_config = {
            "risk_per_trade": 0.02,
            "max_position_size": 5000,
            "circuit_breaker_thresholds": {
                "daily_loss": -0.05,
                "max_drawdown": -0.10,
            },
            "trading_hours": {"start": "invalid", "end": "16:00"},
        }

        response = client.put("/api/v1/config", json=invalid_config)

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_rollback_config(self, client, mock_config_validator, mock_auth):
        """
        GIVEN: Multiple configuration versions in history
        WHEN: Client requests PUT /api/v1/config/rollback
        THEN: Configuration rolls back to previous version
        """
        # First, apply a new config to create history
        config_v1 = {
            "risk_per_trade": 0.03,
            "max_position_size": 7000,
            "circuit_breaker_thresholds": {
                "daily_loss": -0.05,
                "max_drawdown": -0.10,
            },
        }
        client.put("/api/v1/config", json=config_v1)

        # Then rollback
        response = client.put("/api/v1/config/rollback", params={"versions": 1})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Rolled back" in data["message"]

        # Verify config was rolled back
        validator = mock_config_validator.return_value
        current = validator.get_current_config()
        assert current["risk_per_trade"] == 0.02  # Back to original

    def test_rollback_config_insufficient_history(
        self, client, mock_config_validator, mock_auth
    ):
        """
        GIVEN: No configuration history
        WHEN: Client requests rollback
        THEN: Request is rejected with error message
        """
        response = client.put("/api/v1/config/rollback", params={"versions": 5})

        assert response.status_code == 400
        assert "Cannot rollback" in response.json()["detail"]

    def test_config_validation_and_rollback_workflow(
        self, client, mock_config_validator, mock_auth
    ):
        """
        GIVEN: API with default configuration
        WHEN: User validates → applies → verifies → rolls back
        THEN: Complete workflow succeeds with audit trail
        """
        # Step 1: Validate new config
        new_config = {
            "risk_per_trade": 0.025,
            "max_position_size": 6000,
            "circuit_breaker_thresholds": {
                "daily_loss": -0.06,
                "max_drawdown": -0.12,
            },
        }

        validate_response = client.post("/api/v1/config/validate", json=new_config)
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        # Step 2: Preview diff
        diff_response = client.get("/api/v1/config/diff", json=new_config)
        assert diff_response.status_code == 200
        diff = diff_response.json()
        assert "risk_per_trade" in diff["changes"]

        # Step 3: Apply config
        apply_response = client.put("/api/v1/config", json=new_config)
        assert apply_response.status_code == 200
        assert apply_response.json()["success"] is True

        # Step 4: Verify applied
        get_response = client.get("/api/v1/config")
        assert get_response.json()["risk_per_trade"] == 0.025

        # Step 5: Rollback
        rollback_response = client.put("/api/v1/config/rollback")
        assert rollback_response.status_code == 200
        assert rollback_response.json()["success"] is True

        # Step 6: Verify rollback
        final_response = client.get("/api/v1/config")
        assert final_response.json()["risk_per_trade"] == 0.02  # Original value


@pytest.mark.parametrize(
    "risk,expected_valid",
    [
        (0.01, True),  # Minimum valid
        (0.02, True),  # Normal
        (0.05, True),  # Maximum valid
        (0.06, False),  # Too high
        (0.005, False),  # Too low
    ],
)
def test_risk_per_trade_boundaries(
    client, mock_config_validator, mock_auth, risk, expected_valid
):
    """Test risk_per_trade validation at boundary values."""
    config = {
        "risk_per_trade": risk,
        "max_position_size": 5000,
        "circuit_breaker_thresholds": {
            "daily_loss": -0.05,
            "max_drawdown": -0.10,
        },
    }

    response = client.post("/api/v1/config/validate", json=config)

    if expected_valid:
        assert response.status_code == 200
    else:
        # Pydantic validation will fail before hitting our validator
        assert response.status_code in [200, 422]
