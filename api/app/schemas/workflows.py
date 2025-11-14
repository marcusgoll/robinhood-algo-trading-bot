"""Pydantic schemas for workflow execution."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Workflow step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(BaseModel):
    """
    Single step in a workflow.

    Attributes:
        id: Step identifier
        description: Human-readable description
        action_type: Type of action (command, api_call, validation)
        parameters: Action-specific parameters
        validation: Success criteria for the step
        status: Current execution status
        error: Error message if step failed
    """

    id: str = Field(..., description="Step identifier")
    description: str = Field(..., description="Step description")
    action_type: str = Field(..., description="Action type")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Step parameters"
    )
    validation: Optional[Dict[str, Any]] = Field(
        None, description="Success criteria"
    )
    status: StepStatus = Field(
        default=StepStatus.PENDING, description="Step status"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "check_health",
                    "description": "Check bot health status",
                    "action_type": "api_call",
                    "parameters": {"endpoint": "/api/v1/health/healthz"},
                    "validation": {"expected_status": "healthy"},
                    "status": "completed",
                }
            ]
        }
    }


class WorkflowDefinition(BaseModel):
    """
    Workflow definition loaded from YAML.

    Attributes:
        id: Workflow identifier
        name: Human-readable name
        description: Workflow purpose
        steps: List of workflow steps
    """

    id: str = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow purpose")
    steps: List[WorkflowStep] = Field(..., description="Workflow steps")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "check-health",
                    "name": "Health Check Workflow",
                    "description": "Verify bot health and connectivity",
                    "steps": [
                        {
                            "id": "check_api",
                            "description": "Check API health",
                            "action_type": "api_call",
                            "parameters": {"endpoint": "/health/healthz"},
                        }
                    ],
                }
            ]
        }
    }


class WorkflowListResponse(BaseModel):
    """
    List of available workflows.

    Attributes:
        workflows: List of workflow definitions
        count: Number of workflows
    """

    workflows: List[WorkflowDefinition] = Field(
        ..., description="Available workflows"
    )
    count: int = Field(..., description="Number of workflows")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workflows": [
                        {
                            "id": "check-health",
                            "name": "Health Check",
                            "description": "Verify bot health",
                            "steps": [],
                        }
                    ],
                    "count": 1,
                }
            ]
        }
    }


class WorkflowExecutionRequest(BaseModel):
    """
    Request to execute a workflow.

    Attributes:
        workflow_id: ID of workflow to execute
        parameters: Optional runtime parameters
    """

    workflow_id: str = Field(..., description="Workflow ID")
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Runtime parameters"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workflow_id": "restart-bot",
                    "parameters": {"graceful": True, "timeout": 30},
                }
            ]
        }
    }


class WorkflowStatusResponse(BaseModel):
    """
    Workflow execution status.

    Attributes:
        workflow_id: Workflow identifier
        status: Current execution status
        steps: List of steps with status
        started_at: Execution start time
        completed_at: Execution completion time (if finished)
        error: Error message if workflow failed
        progress: Percentage complete (0-100)
    """

    workflow_id: str = Field(..., description="Workflow ID")
    status: WorkflowStatus = Field(..., description="Execution status")
    steps: List[WorkflowStep] = Field(..., description="Step statuses")
    started_at: datetime = Field(..., description="Start time")
    completed_at: Optional[datetime] = Field(
        None, description="Completion time"
    )
    error: Optional[str] = Field(None, description="Error message")
    progress: int = Field(
        ..., ge=0, le=100, description="Progress percentage"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workflow_id": "check-health",
                    "status": "completed",
                    "steps": [],
                    "started_at": "2025-10-24T12:00:00Z",
                    "completed_at": "2025-10-24T12:00:05Z",
                    "error": None,
                    "progress": 100,
                }
            ]
        }
    }
