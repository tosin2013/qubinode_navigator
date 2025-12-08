"""
Feedback Loop: Complete orchestration flow from user intent to execution feedback.

This module integrates:
- Project Registry (Phase 1)
- DAG Validation (Phase 2)
- Project Editing (Phase 3)
- Smart Pipeline (Phase 4)

Into a unified flow that:
1. Analyzes user intent
2. Finds or creates appropriate DAGs
3. Proposes project edits if needed
4. Executes with validation
5. Provides actionable feedback

Per ADR-0066: Developer Agent DAG Validation and Smart Pipelines
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class FlowStep(str, Enum):
    """Steps in the orchestration flow."""

    ANALYZE_INTENT = "analyze_intent"
    FIND_PROJECT = "find_project"
    FIND_DAG = "find_dag"
    CREATE_DAG = "create_dag"
    PROPOSE_EDITS = "propose_edits"
    VALIDATE_DAG = "validate_dag"
    EXECUTE_DAG = "execute_dag"
    MONITOR_EXECUTION = "monitor_execution"
    PROVIDE_FEEDBACK = "provide_feedback"


class FlowStatus(str, Enum):
    """Status of the orchestration flow."""

    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class FlowContext:
    """Context maintained throughout the orchestration flow."""

    flow_id: str
    user_intent: str
    current_step: FlowStep
    status: FlowStatus = FlowStatus.IN_PROGRESS
    started_at: datetime = field(default_factory=datetime.now)

    # Phase 1: Project Discovery
    source_project: Optional[str] = None
    project_path: Optional[str] = None
    project_capabilities: List[str] = field(default_factory=list)

    # Phase 2: DAG Discovery/Creation
    dag_id: Optional[str] = None
    dag_found: bool = False
    dag_created: bool = False
    dag_match_score: float = 0.0
    dag_validation_passed: bool = False

    # Phase 3: Project Edits
    pending_edits: List[str] = field(default_factory=list)  # Edit IDs
    applied_edits: List[str] = field(default_factory=list)

    # Phase 4: Execution
    execution_id: Optional[str] = None
    run_id: Optional[str] = None
    execution_status: Optional[str] = None

    # Feedback
    user_actions: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    escalation_reason: Optional[str] = None


@dataclass
class FlowResult:
    """Result of the orchestration flow."""

    flow_id: str
    status: FlowStatus
    summary: str
    dag_id: Optional[str] = None
    execution_id: Optional[str] = None

    # What happened in each phase
    phases_completed: List[str] = field(default_factory=list)
    phases_skipped: List[str] = field(default_factory=list)

    # User feedback
    user_actions: List[Dict[str, Any]] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)

    # Monitoring
    airflow_ui_url: Optional[str] = None
    status_endpoint: Optional[str] = None

    # Error handling
    error_message: Optional[str] = None
    escalation_context: Optional[Dict[str, Any]] = None


class FeedbackLoopOrchestrator:
    """
    Orchestrates the complete flow from user intent to execution feedback.

    This is the main entry point for ADR-0066 functionality.
    """

    def __init__(self):
        self._flows: Dict[str, FlowContext] = {}

    async def orchestrate(
        self,
        user_intent: str,
        params: Optional[Dict[str, Any]] = None,
        auto_approve: bool = False,
        auto_execute: bool = True,
    ) -> FlowResult:
        """
        Orchestrate the complete flow for a user intent.

        Args:
            user_intent: What the user wants to accomplish
            params: Additional parameters for the task
            auto_approve: Automatically approve DAG creation and edits
            auto_execute: Automatically execute after validation

        Returns:
            FlowResult with status, actions, and monitoring info
        """
        import uuid

        flow_id = f"flow-{uuid.uuid4().hex[:12]}"
        params = params or {}

        context = FlowContext(
            flow_id=flow_id,
            user_intent=user_intent,
            current_step=FlowStep.ANALYZE_INTENT,
        )
        self._flows[flow_id] = context

        phases_completed = []
        phases_skipped = []

        try:
            # =================================================================
            # Phase 1: Find Source Project
            # =================================================================
            context.current_step = FlowStep.FIND_PROJECT

            try:
                from project_registry import get_project_registry

                registry = await get_project_registry()
                matching_projects = registry.find_for_task(user_intent)

                if matching_projects:
                    best_project = matching_projects[0]
                    context.source_project = best_project.name
                    context.project_path = best_project.path
                    context.project_capabilities = [c.value for c in best_project.capabilities]
                    phases_completed.append("project_discovery")
                    logger.info(f"Flow {flow_id}: Found project {best_project.name}")
                else:
                    phases_skipped.append("project_discovery")
            except ImportError:
                phases_skipped.append("project_discovery")

            # =================================================================
            # Phase 2: Find or Create DAG
            # =================================================================
            context.current_step = FlowStep.FIND_DAG

            try:
                from dag_validator import find_or_create_dag, get_dag_validator

                dag_result = await find_or_create_dag(user_intent, params)

                context.dag_found = dag_result.get("found", False)
                context.dag_id = dag_result.get("dag_id")
                context.dag_match_score = dag_result.get("match_score", 0.0)

                if context.dag_found:
                    phases_completed.append("dag_discovery")

                    # Validate the DAG
                    context.current_step = FlowStep.VALIDATE_DAG
                    validation = dag_result.get("validation", {})
                    context.dag_validation_passed = validation.get("can_proceed", False)

                    if context.dag_validation_passed:
                        phases_completed.append("dag_validation")
                    else:
                        # Validation failed
                        context.status = FlowStatus.FAILED
                        context.error_message = validation.get("error_summary", "DAG validation failed")
                        context.user_actions = dag_result.get("user_actions", [])
                        return self._build_result(context, phases_completed, phases_skipped)
                else:
                    # Need to create a new DAG
                    context.current_step = FlowStep.CREATE_DAG

                    if auto_approve or await self._should_auto_create_dag(user_intent):
                        # Get creation result
                        creation = dag_result.get("creation", {})
                        if creation.get("success"):
                            # Deploy the DAG
                            validator = await get_dag_validator()
                            success, msg = await validator.deploy_dag(
                                creation.get("dag_code", ""),
                                creation.get("file_path", ""),
                            )
                            if success:
                                context.dag_created = True
                                context.dag_validation_passed = True
                                phases_completed.append("dag_creation")
                            else:
                                context.status = FlowStatus.FAILED
                                context.error_message = msg
                                return self._build_result(context, phases_completed, phases_skipped)
                    else:
                        # Need user approval
                        context.status = FlowStatus.AWAITING_APPROVAL
                        context.user_actions = dag_result.get("user_actions", [])
                        return self._build_result(context, phases_completed, phases_skipped)

            except ImportError:
                phases_skipped.append("dag_discovery")
                phases_skipped.append("dag_validation")

            # =================================================================
            # Phase 3: Propose Project Edits (if needed)
            # =================================================================
            context.current_step = FlowStep.PROPOSE_EDITS

            # Check if we need to edit project files based on params
            edits_needed = self._check_edits_needed(user_intent, params, context)

            if edits_needed:
                try:
                    from project_editor import get_project_editor

                    _editor = get_project_editor()  # noqa: F841 - prepared for future use
                    # For now, skip edit phase - can be expanded
                    phases_skipped.append("project_editing")
                except ImportError:
                    phases_skipped.append("project_editing")
            else:
                phases_skipped.append("project_editing")

            # =================================================================
            # Phase 4: Execute DAG
            # =================================================================
            if not auto_execute:
                context.status = FlowStatus.AWAITING_APPROVAL
                context.user_actions = [
                    {
                        "action_type": "execute",
                        "description": f"Execute DAG '{context.dag_id}'",
                        "endpoint": "/orchestrator/execute",
                    },
                    {
                        "action_type": "skip",
                        "description": "Skip execution",
                    },
                ]
                return self._build_result(context, phases_completed, phases_skipped)

            context.current_step = FlowStep.EXECUTE_DAG

            if context.dag_id and context.dag_validation_passed:
                try:
                    from smart_pipeline import execute_smart_pipeline

                    execution_result = await execute_smart_pipeline(
                        dag_id=context.dag_id,
                        params=params,
                        validate_first=True,
                    )

                    context.execution_id = execution_result.get("execution_id")
                    context.run_id = execution_result.get("run_id")
                    context.execution_status = execution_result.get("status")

                    if execution_result.get("status") == "running":
                        context.status = FlowStatus.EXECUTING
                        phases_completed.append("dag_execution")

                        # Get monitoring info (stored for future use)
                        _monitoring = execution_result.get("monitoring", {})  # noqa: F841
                        context.user_actions = execution_result.get("user_actions", [])

                    elif execution_result.get("status") == "failed":
                        context.status = FlowStatus.FAILED
                        context.error_message = execution_result.get("error_message")
                        context.user_actions = execution_result.get("user_actions", [])

                except ImportError:
                    phases_skipped.append("dag_execution")

            # =================================================================
            # Phase 5: Provide Feedback
            # =================================================================
            context.current_step = FlowStep.PROVIDE_FEEDBACK
            phases_completed.append("feedback")

            if context.status == FlowStatus.EXECUTING:
                context.status = FlowStatus.IN_PROGRESS

            return self._build_result(context, phases_completed, phases_skipped)

        except Exception as e:
            logger.error(f"Flow {flow_id} failed: {e}")
            context.status = FlowStatus.FAILED
            context.error_message = str(e)
            return self._build_result(context, phases_completed, phases_skipped)

    async def _should_auto_create_dag(self, user_intent: str) -> bool:
        """Determine if we should auto-create a DAG without approval."""
        # Simple heuristic: auto-create for common operations
        intent_lower = user_intent.lower()
        auto_create_keywords = ["create vm", "deploy", "test", "health check"]
        return any(kw in intent_lower for kw in auto_create_keywords)

    def _check_edits_needed(
        self,
        user_intent: str,
        params: Dict[str, Any],
        context: FlowContext,
    ) -> bool:
        """Check if project file edits are needed."""
        # Check for explicit memory/cpu/disk changes
        if any(k in params for k in ["memory", "cpus", "disk_size", "memory_mb"]):
            return True

        # Check for profile customization keywords
        intent_lower = user_intent.lower()
        if any(kw in intent_lower for kw in ["custom", "8gb", "16gb", "32gb"]):
            return True

        return False

    def _build_result(
        self,
        context: FlowContext,
        phases_completed: List[str],
        phases_skipped: List[str],
    ) -> FlowResult:
        """Build the flow result from context."""

        # Build summary
        if context.status == FlowStatus.EXECUTING:
            summary = f"DAG '{context.dag_id}' is executing. Run ID: {context.run_id}"
        elif context.status == FlowStatus.AWAITING_APPROVAL:
            summary = "Awaiting approval for DAG creation or execution"
        elif context.status == FlowStatus.SUCCESS:
            summary = f"Successfully completed: {context.dag_id}"
        elif context.status == FlowStatus.FAILED:
            summary = f"Failed: {context.error_message}"
        else:
            summary = f"Flow in progress: step={context.current_step.value}"

        # Build next steps
        next_steps = []
        if context.status == FlowStatus.EXECUTING:
            next_steps = [
                f"Monitor execution at: /orchestrator/executions/{context.execution_id}/status",
                "Wait for completion notification",
                "Check Airflow UI for detailed progress",
            ]
        elif context.status == FlowStatus.AWAITING_APPROVAL:
            next_steps = [
                "Review the proposed DAG or changes",
                "Approve to proceed or reject to cancel",
            ]
        elif context.status == FlowStatus.FAILED:
            next_steps = [
                "Review the error message",
                "Try one of the suggested user actions",
                "Escalate to Manager Agent if needed",
            ]

        # Get monitoring URLs
        airflow_ui_url = None
        status_endpoint = None
        if context.execution_id:
            airflow_ui_url = f"http://localhost:8888/dags/{context.dag_id}/grid"
            status_endpoint = f"/orchestrator/executions/{context.execution_id}/status"

        return FlowResult(
            flow_id=context.flow_id,
            status=context.status,
            summary=summary,
            dag_id=context.dag_id,
            execution_id=context.execution_id,
            phases_completed=phases_completed,
            phases_skipped=phases_skipped,
            user_actions=context.user_actions,
            next_steps=next_steps,
            airflow_ui_url=airflow_ui_url,
            status_endpoint=status_endpoint,
            error_message=context.error_message,
            escalation_context={
                "user_intent": context.user_intent,
                "source_project": context.source_project,
                "dag_id": context.dag_id,
                "error": context.error_message,
            }
            if context.status in (FlowStatus.FAILED, FlowStatus.ESCALATED)
            else None,
        )

    def get_flow_status(self, flow_id: str) -> Optional[FlowContext]:
        """Get the status of a flow by ID."""
        return self._flows.get(flow_id)


# Singleton instance
_orchestrator: Optional[FeedbackLoopOrchestrator] = None


async def get_feedback_orchestrator() -> FeedbackLoopOrchestrator:
    """Get the singleton feedback loop orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = FeedbackLoopOrchestrator()
    return _orchestrator


async def execute_user_intent(
    user_intent: str,
    params: Optional[Dict[str, Any]] = None,
    auto_approve: bool = False,
    auto_execute: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to execute a user intent through the full flow.

    This is the main entry point for ADR-0066 functionality.

    Args:
        user_intent: What the user wants to accomplish
        params: Additional parameters
        auto_approve: Auto-approve DAG creation
        auto_execute: Auto-execute after validation

    Returns:
        Flow result as dict
    """
    orchestrator = await get_feedback_orchestrator()
    result = await orchestrator.orchestrate(
        user_intent=user_intent,
        params=params,
        auto_approve=auto_approve,
        auto_execute=auto_execute,
    )

    return {
        "flow_id": result.flow_id,
        "status": result.status.value,
        "summary": result.summary,
        "dag_id": result.dag_id,
        "execution_id": result.execution_id,
        "phases_completed": result.phases_completed,
        "phases_skipped": result.phases_skipped,
        "user_actions": result.user_actions,
        "next_steps": result.next_steps,
        "airflow_ui_url": result.airflow_ui_url,
        "status_endpoint": result.status_endpoint,
        "error_message": result.error_message,
        "escalation_context": result.escalation_context,
    }
