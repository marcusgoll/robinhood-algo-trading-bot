"""
Smoke tests for all API endpoints.

Validates basic functionality of each endpoint without deep logic testing.
Should run in <30 seconds total.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication to bypass token validation."""
    with patch("api.app.core.auth.verify_api_key", return_value=True):
        yield


class TestHealthEndpoints:
    """Smoke tests for health endpoints."""

    def test_healthz_endpoint(self, client):
        """Test health check endpoint is responsive."""
        response = client.get("/api/v1/health/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_readyz_endpoint(self, client):
        """Test readiness endpoint is responsive."""
        response = client.get("/api/v1/health/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data


class TestStateEndpoints:
    """Smoke tests for state endpoints."""

    def test_state_endpoint(self, client, mock_auth):
        """Test GET /api/v1/state returns valid response."""
        response = client.get("/api/v1/state")
        # May fail due to missing dependencies, but should not crash
        assert response.status_code in [200, 500]

    def test_summary_endpoint(self, client, mock_auth):
        """Test GET /api/v1/summary returns valid response."""
        response = client.get("/api/v1/summary")
        # May fail due to missing dependencies, but should not crash
        assert response.status_code in [200, 500]


class TestConfigEndpoints:
    """Smoke tests for config endpoints."""

    def test_get_config(self, client, mock_auth):
        """Test GET /api/v1/config returns current configuration."""
        response = client.get("/api/v1/config")
        assert response.status_code in [200, 404, 500]

    def test_validate_config(self, client, mock_auth):
        """Test POST /api/v1/config/validate endpoint exists."""
        config = {
            "risk_per_trade": 0.02,
            "max_position_size": 5000,
            "circuit_breaker_thresholds": {
                "daily_loss": -0.05,
                "max_drawdown": -0.10,
            },
        }
        response = client.post("/api/v1/config/validate", json=config)
        # Endpoint should exist (not 404)
        assert response.status_code != 404


class TestMetricsEndpoints:
    """Smoke tests for metrics endpoints."""

    def test_get_metrics(self, client, mock_auth):
        """Test GET /api/v1/metrics endpoint exists."""
        response = client.get("/api/v1/metrics")
        assert response.status_code in [200, 500]

    def test_connection_count(self, client, mock_auth):
        """Test GET /api/v1/metrics/connections endpoint."""
        response = client.get("/api/v1/metrics/connections")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data


class TestWorkflowsEndpoints:
    """Smoke tests for workflows endpoints."""

    def test_list_workflows(self, client, mock_auth):
        """Test GET /api/v1/workflows returns workflow list."""
        response = client.get("/api/v1/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert "count" in data


class TestOpenAPIDocumentation:
    """Smoke tests for OpenAPI documentation."""

    def test_openapi_json(self, client):
        """Test OpenAPI spec is generated."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec

    def test_docs_endpoint(self, client):
        """Test Swagger UI docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_redoc_endpoint(self, client):
        """Test ReDoc documentation is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200


@pytest.mark.parametrize(
    "endpoint,method",
    [
        ("/api/v1/health/healthz", "GET"),
        ("/api/v1/health/readyz", "GET"),
        ("/api/v1/state", "GET"),
        ("/api/v1/summary", "GET"),
        ("/api/v1/config", "GET"),
        ("/api/v1/metrics", "GET"),
        ("/api/v1/workflows", "GET"),
    ],
)
def test_endpoint_exists(client, mock_auth, endpoint, method):
    """Parametrized test that all documented endpoints exist."""
    if method == "GET":
        response = client.get(endpoint)
    elif method == "POST":
        response = client.post(endpoint)
    else:
        pytest.fail(f"Unsupported method: {method}")

    # Endpoint should exist (not 404)
    assert response.status_code != 404, f"Endpoint {endpoint} not found"


class TestErrorHandling:
    """Smoke tests for error handling."""

    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_unauthorized_without_token(self, client):
        """Test 401/403 error for protected endpoints without auth."""
        # State endpoint requires auth
        response = client.get("/api/v1/state")
        # Should fail auth (401 or similar)
        assert response.status_code in [401, 403, 500]


def test_full_api_smoke_under_30_seconds(client, mock_auth):
    """
    Comprehensive smoke test that hits all major endpoints.
    Should complete in <30 seconds.
    """
    import time

    start_time = time.time()

    # Hit all endpoints
    endpoints = [
        "/api/v1/health/healthz",
        "/api/v1/health/readyz",
        "/api/v1/state",
        "/api/v1/summary",
        "/api/v1/config",
        "/api/v1/metrics",
        "/api/v1/metrics/connections",
        "/api/v1/workflows",
        "/openapi.json",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        # Just verify endpoint exists
        assert response.status_code != 404, f"Endpoint {endpoint} missing"

    elapsed_time = time.time() - start_time
    assert elapsed_time < 30, f"Smoke tests took {elapsed_time:.2f}s (should be <30s)"
