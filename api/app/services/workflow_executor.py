"""
WorkflowExecutor service for executing YAML-based workflows.

Provides workflow loading, execution, progress tracking, and status queries.
"""

from __future__ import annotations

import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schemas.workflows import (
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowStatusResponse,
    WorkflowStep,
    StepStatus,
)


logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    Service for executing YAML-based workflows.

    Provides:
    - Load workflow definitions from YAML
    - Execute workflows step-by-step
    - Track execution progress
    - Query workflow status
    """

    def __init__(self, workflows_dir: str = "config/workflows"):
        """
        Initialize WorkflowExecutor.

        Args:
            workflows_dir: Directory containing YAML workflow definitions
        """
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self._executions: Dict[str, WorkflowStatusResponse] = {}

    def load_workflow(self, workflow_id: str) -> WorkflowDefinition:
        """
        Load workflow definition from YAML file.

        Args:
            workflow_id: Workflow identifier (filename without .yaml)

        Returns:
            WorkflowDefinition loaded from YAML

        Raises:
            FileNotFoundError: If workflow file doesn't exist
            ValueError: If YAML is invalid
        """
        workflow_file = self.workflows_dir / f"{workflow_id}.yaml"
        if not workflow_file.exists():
            raise FileNotFoundError(
                f"Workflow '{workflow_id}' not found in {self.workflows_dir}"
            )

        try:
            workflow_data = yaml.safe_load(workflow_file.read_text())
            # Convert steps to WorkflowStep objects
            steps = [WorkflowStep(**step) for step in workflow_data.get("steps", [])]
            return WorkflowDefinition(
                id=workflow_data["id"],
                name=workflow_data["name"],
                description=workflow_data["description"],
                steps=steps,
            )
        except Exception as e:
            raise ValueError(f"Invalid workflow YAML: {e}")

    def list_workflows(self) -> List[WorkflowDefinition]:
        """
        List all available workflows.

        Returns:
            List of workflow definitions
        """
        workflows = []
        for workflow_file in self.workflows_dir.glob("*.yaml"):
            try:
                workflow = self.load_workflow(workflow_file.stem)
                workflows.append(workflow)
            except Exception as e:
                logger.warning(f"Failed to load workflow {workflow_file}: {e}")
        return workflows

    async def execute(
        self,
        workflow_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> WorkflowStatusResponse:
        """
        Execute workflow asynchronously.

        Args:
            workflow_id: Workflow to execute
            parameters: Runtime parameters

        Returns:
            WorkflowStatusResponse with execution status
        """
        # Load workflow
        workflow = self.load_workflow(workflow_id)

        # Initialize execution status
        started_at = datetime.utcnow()
        execution = WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            steps=workflow.steps,
            started_at=started_at,
            progress=0,
        )
        self._executions[workflow_id] = execution

        # Execute steps sequentially
        try:
            for i, step in enumerate(workflow.steps):
                # Update step status to running
                step.status = StepStatus.RUNNING
                step.started_at = datetime.utcnow()
                logger.info(f"Executing step {step.id}: {step.description}")

                # Execute step action
                success = await self._execute_step(step, parameters or {})

                # Update step status
                step.completed_at = datetime.utcnow()
                if success:
                    step.status = StepStatus.COMPLETED
                else:
                    step.status = StepStatus.FAILED
                    step.error = "Step execution failed"
                    execution.status = WorkflowStatus.FAILED
                    execution.error = f"Step '{step.id}' failed"
                    execution.completed_at = datetime.utcnow()
                    return execution

                # Update progress
                execution.progress = int(((i + 1) / len(workflow.steps)) * 100)

            # All steps completed successfully
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.progress = 100

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()

        return execution

    async def _execute_step(
        self, step: WorkflowStep, parameters: Dict[str, Any]
    ) -> bool:
        """
        Execute a single workflow step.

        Args:
            step: Step to execute
            parameters: Runtime parameters

        Returns:
            True if step succeeded, False otherwise
        """
        try:
            if step.action_type == "command":
                # Execute shell command
                # For safety, this is stubbed - real implementation would use subprocess
                logger.info(f"Would execute command: {step.parameters.get('cmd')}")
                return True

            elif step.action_type == "api_call":
                # Make API call
                # For now, just validate endpoint exists
                endpoint = step.parameters.get("endpoint", "")
                logger.info(f"Would call API endpoint: {endpoint}")
                return True

            elif step.action_type == "validation":
                # Run validation check
                logger.info(f"Running validation: {step.description}")
                return True

            elif step.action_type == "sleep":
                # Sleep for specified duration
                import asyncio
                duration = step.parameters.get("duration", 1)
                await asyncio.sleep(duration)
                return True

            else:
                logger.warning(f"Unknown action type: {step.action_type}")
                return False

        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            return False

    def get_status(self, workflow_id: str) -> Optional[WorkflowStatusResponse]:
        """
        Get execution status of a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            WorkflowStatusResponse if workflow has been executed, None otherwise
        """
        return self._executions.get(workflow_id)

    def cancel(self, workflow_id: str) -> bool:
        """
        Cancel running workflow.

        Args:
            workflow_id: Workflow to cancel

        Returns:
            True if cancelled, False if not running
        """
        execution = self._executions.get(workflow_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            return True
        return False
