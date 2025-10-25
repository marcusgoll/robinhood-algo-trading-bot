"""
Integration tests for Workflow Execution API.

Tests workflow routes:
- GET /api/v1/workflows - List available workflows
- POST /api/v1/workflows/{id}/execute - Execute workflow
- GET /api/v1/workflows/{id}/status - Get execution status
- DELETE /api/v1/workflows/{id}/cancel - Cancel workflow
"""

from pathlib import Path
from unittest.mock import patch
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.app.routes.workflows import router as workflows_router


@pytest.fixture
def temp_workflows_dir():
    """Create temporary workflows directory with test workflows."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workflows_dir = Path(tmp_dir) / "workflows"
        workflows_dir.mkdir()

        # Create test workflow
        test_workflow = workflows_dir / "test-workflow.yaml"
        test_workflow.write_text("""
id: test-workflow
name: Test Workflow
description: Simple test workflow

steps:
  - id: step1
    description: First step
    action_type: validation
    parameters:
      message: Step 1 executing

  - id: step2
    description: Second step
    action_type: sleep
    parameters:
      duration: 0.1

  - id: step3
    description: Third step
    action_type: validation
    parameters:
      message: Step 3 complete
""")

        yield workflows_dir


@pytest.fixture
def app():
    """Create FastAPI app with workflows routes."""
    app = FastAPI()
    app.include_router(workflows_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create TestClient for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock API key authentication."""
    with patch("api.app.routes.workflows.verify_api_key") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_workflow_executor(temp_workflows_dir):
    """Mock WorkflowExecutor to use temp directory."""
    with patch("api.app.routes.workflows.get_workflow_executor") as mock:
        from api.app.services.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor(workflows_dir=str(temp_workflows_dir))
        mock.return_value = executor
        yield mock


class TestWorkflowsAPI:
    """Integration tests for workflows API endpoints."""

    def test_list_workflows(self, client, mock_workflow_executor, mock_auth):
        """
        GIVEN: Workflows directory with YAML definitions
        WHEN: Client queries GET /api/v1/workflows
        THEN: List of available workflows is returned
        """
        response = client.get("/api/v1/workflows")

        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert "count" in data
        assert data["count"] > 0
        assert data["workflows"][0]["id"] == "test-workflow"
        assert data["workflows"][0]["name"] == "Test Workflow"

    @pytest.mark.asyncio
    async def test_execute_workflow(self, client, mock_workflow_executor, mock_auth):
        """
        GIVEN: Valid workflow exists
        WHEN: Client executes POST /api/v1/workflows/{id}/execute
        THEN: Workflow executes and returns status
        """
        response = client.post("/api/v1/workflows/test-workflow/execute")

        assert response.status_code == 202  # Accepted
        data = response.json()
        assert data["workflow_id"] == "test-workflow"
        assert "status" in data
        assert "steps" in data
        assert "progress" in data

    def test_execute_nonexistent_workflow(
        self, client, mock_workflow_executor, mock_auth
    ):
        """
        GIVEN: Workflow does not exist
        WHEN: Client tries to execute
        THEN: 404 error is returned
        """
        response = client.post("/api/v1/workflows/nonexistent/execute")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_workflow_status(
        self, client, mock_workflow_executor, mock_auth
    ):
        """
        GIVEN: Workflow has been executed
        WHEN: Client queries GET /api/v1/workflows/{id}/status
        THEN: Execution status is returned
        """
        # First execute workflow
        execute_response = client.post("/api/v1/workflows/test-workflow/execute")
        assert execute_response.status_code == 202

        # Then query status
        status_response = client.get("/api/v1/workflows/test-workflow/status")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["workflow_id"] == "test-workflow"
        assert data["status"] in ["running", "completed", "failed"]
        assert len(data["steps"]) == 3  # Three steps in test workflow

    def test_get_status_not_executed(
        self, client, mock_workflow_executor, mock_auth
    ):
        """
        GIVEN: Workflow has not been executed
        WHEN: Client queries status
        THEN: 404 error is returned
        """
        response = client.get("/api/v1/workflows/test-workflow/status")

        assert response.status_code == 404
        assert "not been executed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_workflow_execution_tracks_progress(
        self, client, mock_workflow_executor, mock_auth
    ):
        """
        GIVEN: Workflow with multiple steps
        WHEN: Workflow executes
        THEN: Progress is tracked through steps
        """
        response = client.post("/api/v1/workflows/test-workflow/execute")

        assert response.status_code == 202
        data = response.json()

        # Progress should be tracked
        assert "progress" in data
        assert 0 <= data["progress"] <= 100

        # Steps should have status
        for step in data["steps"]:
            assert "status" in step
            assert step["status"] in [
                "pending",
                "running",
                "completed",
                "failed",
                "skipped",
            ]


class TestWorkflowExecutor:
    """Unit tests for WorkflowExecutor service."""

    def test_load_workflow(self, temp_workflows_dir):
        """
        GIVEN: YAML workflow file exists
        WHEN: Executor loads workflow
        THEN: WorkflowDefinition is returned
        """
        from api.app.services.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor(workflows_dir=str(temp_workflows_dir))
        workflow = executor.load_workflow("test-workflow")

        assert workflow.id == "test-workflow"
        assert workflow.name == "Test Workflow"
        assert len(workflow.steps) == 3

    def test_load_nonexistent_workflow(self, temp_workflows_dir):
        """
        GIVEN: Workflow file doesn't exist
        WHEN: Executor tries to load
        THEN: FileNotFoundError is raised
        """
        from api.app.services.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor(workflows_dir=str(temp_workflows_dir))

        with pytest.raises(FileNotFoundError):
            executor.load_workflow("nonexistent")

    def test_list_workflows(self, temp_workflows_dir):
        """
        GIVEN: Multiple workflow files exist
        WHEN: Executor lists workflows
        THEN: All workflows are returned
        """
        from api.app.services.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor(workflows_dir=str(temp_workflows_dir))
        workflows = executor.list_workflows()

        assert len(workflows) >= 1
        assert any(w.id == "test-workflow" for w in workflows)

    @pytest.mark.asyncio
    async def test_execute_workflow(self, temp_workflows_dir):
        """
        GIVEN: Valid workflow
        WHEN: Executor executes workflow
        THEN: All steps execute successfully
        """
        from api.app.services.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor(workflows_dir=str(temp_workflows_dir))
        status = await executor.execute("test-workflow")

        assert status.workflow_id == "test-workflow"
        assert status.status in ["running", "completed"]
        assert len(status.steps) == 3

    @pytest.mark.asyncio
    async def test_get_workflow_status(self, temp_workflows_dir):
        """
        GIVEN: Workflow has been executed
        WHEN: Executor queries status
        THEN: Status is returned
        """
        from api.app.services.workflow_executor import WorkflowExecutor

        executor = WorkflowExecutor(workflows_dir=str(temp_workflows_dir))

        # Execute first
        await executor.execute("test-workflow")

        # Then query status
        status = executor.get_status("test-workflow")
        assert status is not None
        assert status.workflow_id == "test-workflow"
