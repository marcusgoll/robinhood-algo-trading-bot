"""Smoke tests for OpenAPI specification and API documentation.

Test Scope:
- OpenAPI spec accessible at /openapi.json
- Swagger UI accessible at /docs
- All expected endpoints documented
- Schema examples present

Speed Target: <10s total
Coverage: Critical path only (documentation available)
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from api.app.main import app

    return TestClient(app)


def test_openapi_spec_accessible(client):
    """
    Verify OpenAPI spec is accessible at /openapi.json.

    GIVEN: FastAPI app with OpenAPI enabled
    WHEN: Client requests /openapi.json
    THEN: Returns 200 with valid JSON spec
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    # Verify spec structure
    assert "openapi" in spec
    assert spec["openapi"].startswith("3.")
    assert "info" in spec
    assert "paths" in spec


def test_swagger_ui_accessible(client):
    """
    Verify Swagger UI is accessible at /docs.

    GIVEN: FastAPI app with Swagger UI enabled
    WHEN: Client requests /docs
    THEN: Returns 200 with HTML content
    """
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_spec_includes_all_endpoints(client):
    """
    Verify all expected endpoints are documented in OpenAPI spec.

    GIVEN: FastAPI app with state, metrics, config, workflow routes
    WHEN: Client fetches /openapi.json
    THEN: Spec includes all expected endpoints
    """
    response = client.get("/openapi.json")
    spec = response.json()
    paths = spec["paths"]

    # Expected endpoints (MVP)
    expected_endpoints = [
        "/api/v1/state",
        "/api/v1/summary",
        "/api/v1/health",
        "/api/v1/health/healthz",
        "/api/v1/health/readyz",
    ]

    for endpoint in expected_endpoints:
        assert endpoint in paths, f"Missing endpoint: {endpoint}"

    # Verify GET method exists for state endpoints
    assert "get" in paths["/api/v1/state"]
    assert "get" in paths["/api/v1/summary"]
    assert "get" in paths["/api/v1/health"]


def test_openapi_spec_includes_tags(client):
    """
    Verify OpenAPI spec includes tag definitions.

    GIVEN: FastAPI app with openapi_tags configured
    WHEN: Client fetches /openapi.json
    THEN: Spec includes tag metadata
    """
    response = client.get("/openapi.json")
    spec = response.json()

    assert "tags" in spec
    tag_names = {tag["name"] for tag in spec["tags"]}

    # Expected tags
    expected_tags = {"state", "health", "orders"}  # MVP tags
    assert expected_tags.issubset(tag_names)


def test_state_endpoint_has_schema_example(client):
    """
    Verify state endpoint has schema examples in OpenAPI spec.

    GIVEN: BotStateResponse with model_config example
    WHEN: Client fetches /openapi.json
    THEN: Schema includes example data
    """
    response = client.get("/openapi.json")
    spec = response.json()

    # Navigate to BotStateResponse schema
    schemas = spec.get("components", {}).get("schemas", {})
    assert "BotStateResponse" in schemas

    state_schema = schemas["BotStateResponse"]

    # Verify example exists (Pydantic v2 puts it in different locations)
    # Check both possible locations for compatibility
    has_example = (
        "example" in state_schema or
        "examples" in state_schema or
        any("example" in prop for prop in state_schema.get("properties", {}).values())
    )

    assert has_example, "BotStateResponse schema missing examples"


def test_api_info_metadata(client):
    """
    Verify API info metadata is correctly configured.

    GIVEN: FastAPI app with title, description, version
    WHEN: Client fetches /openapi.json
    THEN: Info section has correct metadata
    """
    response = client.get("/openapi.json")
    spec = response.json()
    info = spec["info"]

    assert info["title"] == "Trading Bot API"
    assert "LLM-friendly" in info["description"]
    assert info["version"] == "1.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
