"""API routes for workflow execution."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.auth import verify_api_key
from ..schemas.workflows import (
    WorkflowListResponse,
    WorkflowStatusResponse,
)
from ..services.workflow_executor import WorkflowExecutor

router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_workflow_executor() -> WorkflowExecutor:
    """Dependency injection for WorkflowExecutor."""
    return WorkflowExecutor()


@router.get(
    "",
    response_model=WorkflowListResponse,
    summary="List available workflows",
    description="Returns list of all available YAML workflow definitions",
)
async def list_workflows(
    _: bool = Depends(verify_api_key),
    executor: WorkflowExecutor = Depends(get_workflow_executor),
) -> WorkflowListResponse:
    """
    List all available workflows.

    Returns:
        WorkflowListResponse with workflow definitions
    """
    workflows = executor.list_workflows()
    return WorkflowListResponse(workflows=workflows, count=len(workflows))


@router.post(
    "/{workflow_id}/execute",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute workflow",
    description="Executes a workflow asynchronously and returns initial status",
)
async def execute_workflow(
    workflow_id: str,
    _: bool = Depends(verify_api_key),
    executor: WorkflowExecutor = Depends(get_workflow_executor),
) -> WorkflowStatusResponse:
    """
    Execute workflow by ID.

    Args:
        workflow_id: Workflow identifier

    Returns:
        WorkflowStatusResponse with execution status

    Raises:
        HTTPException: If workflow not found
    """
    try:
        # Execute workflow (async)
        status_response = await executor.execute(workflow_id)
        return status_response
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}",
        )


@router.get(
    "/{workflow_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Get workflow execution status",
    description="Returns current execution status of a workflow",
)
async def get_workflow_status(
    workflow_id: str,
    _: bool = Depends(verify_api_key),
    executor: WorkflowExecutor = Depends(get_workflow_executor),
) -> WorkflowStatusResponse:
    """
    Get workflow execution status.

    Args:
        workflow_id: Workflow identifier

    Returns:
        WorkflowStatusResponse with current status

    Raises:
        HTTPException: If workflow hasn't been executed
    """
    status_response = executor.get_status(workflow_id)
    if not status_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' has not been executed yet",
        )
    return status_response


@router.delete(
    "/{workflow_id}/cancel",
    summary="Cancel running workflow",
    description="Cancels a running workflow execution",
)
async def cancel_workflow(
    workflow_id: str,
    _: bool = Depends(verify_api_key),
    executor: WorkflowExecutor = Depends(get_workflow_executor),
) -> dict:
    """
    Cancel running workflow.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Cancellation status

    Raises:
        HTTPException: If workflow not running
    """
    cancelled = executor.cancel(workflow_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow '{workflow_id}' is not running",
        )
    return {"message": f"Workflow '{workflow_id}' cancelled successfully"}
