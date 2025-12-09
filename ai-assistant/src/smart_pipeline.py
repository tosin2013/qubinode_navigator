"""
Smart Pipeline: Orchestrated DAG execution with tracking and feedback.

This module provides:
- DAG execution with pre-validation
- OpenLineage event tracking with DataQuality facets
- Shadow error detection with ModelRetry pattern
- Execution status monitoring
- User feedback with actionable options

Per ADR-0066: Developer Agent DAG Validation and Smart Pipelines
Enhanced with research from:
- OpenLineage DataQuality facets for quality metadata
- PydanticAI ModelRetry pattern for self-correction
- Airflow listener hooks patterns
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# ModelRetry Pattern - Self-Correction Support
# =============================================================================


class ModelRetry(Exception):
    """
    Exception to signal that the model/agent should retry with corrected parameters.

    Based on PydanticAI's ModelRetry pattern for output validation.
    When raised during outcome validation, it provides:
    - A clear message about what went wrong
    - Suggested corrections
    - Updated parameters for retry
    """

    def __init__(
        self,
        message: str,
        corrected_params: Optional[Dict[str, Any]] = None,
        fix_commands: Optional[List[str]] = None,
        retry_count: int = 0,
        max_retries: int = 2,
    ):
        super().__init__(message)
        self.message = message
        self.corrected_params = corrected_params or {}
        self.fix_commands = fix_commands or []
        self.retry_count = retry_count
        self.max_retries = max_retries

    @property
    def can_retry(self) -> bool:
        """Check if retry is still allowed."""
        return self.retry_count < self.max_retries

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "message": self.message,
            "corrected_params": self.corrected_params,
            "fix_commands": self.fix_commands,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_retry": self.can_retry,
        }


# =============================================================================
# OpenLineage DataQuality Facet Integration
# =============================================================================


@dataclass
class DataQualityAssertion:
    """
    Represents a data quality assertion per OpenLineage spec.

    Based on: https://openlineage.io/spec/facets/1-0-0/DataQualityAssertionsDatasetFacet.json
    """

    assertion: str  # e.g., "vm_exists", "profile_valid", "no_shadow_errors"
    success: bool
    column: Optional[str] = None  # For column-level assertions
    details: Optional[str] = None  # Additional context


@dataclass
class ShadowErrorFacet:
    """
    Custom OpenLineage facet for shadow error detection.

    This facet captures errors that occurred but didn't cause task failure,
    enabling the Manager Agent to understand actual vs reported outcomes.
    """

    _producer: str = "qubinode-smart-pipeline"
    _schemaURL: str = "https://qubinode.io/spec/facets/1-0-0/ShadowErrorFacet.json"

    # Outcome validation
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    outcome_validated: bool = False

    # Shadow errors detected
    shadow_errors: List[Dict[str, Any]] = field(default_factory=list)

    # ModelRetry info for self-correction
    retry_suggested: bool = False
    retry_params: Optional[Dict[str, Any]] = None
    fix_commands: List[str] = field(default_factory=list)

    def to_openlineage_format(self) -> Dict[str, Any]:
        """Convert to OpenLineage facet format for Marquez API."""
        return {
            "shadowErrors": {
                "_producer": self._producer,
                "_schemaURL": self._schemaURL,
                "outcomeValidation": {
                    "expected": self.expected_outcome,
                    "actual": self.actual_outcome,
                    "validated": self.outcome_validated,
                },
                "errors": self.shadow_errors,
                "retrySuggested": self.retry_suggested,
                "retryParams": self.retry_params,
                "fixCommands": self.fix_commands,
            }
        }


class OpenLineageEmitter:
    """
    Emits OpenLineage events to Marquez with DataQuality facets.

    Enables the Manager Agent to query shadow errors and outcome validations
    through the Marquez lineage API.
    """

    def __init__(self, marquez_api_url: str = None, namespace: str = None):
        self.marquez_api_url = marquez_api_url or os.environ.get("MARQUEZ_API_URL", "http://localhost:5001")
        self.namespace = namespace or os.environ.get("OPENLINEAGE_NAMESPACE", "qubinode")

    async def emit_shadow_error_event(
        self,
        dag_id: str,
        run_id: str,
        facet: ShadowErrorFacet,
        assertions: Optional[List[DataQualityAssertion]] = None,
    ) -> bool:
        """
        Emit a shadow error detection event to Marquez.

        This creates an OpenLineage event with:
        - ShadowErrors custom facet
        - DataQualityAssertions facet (if assertions provided)

        Args:
            dag_id: DAG identifier
            run_id: Airflow run ID
            facet: Shadow error facet with detection results
            assertions: Optional list of quality assertions

        Returns:
            True if successfully emitted
        """
        try:
            # Build the OpenLineage event
            event = {
                "eventType": "COMPLETE",
                "eventTime": datetime.utcnow().isoformat() + "Z",
                "run": {
                    "runId": run_id,
                    "facets": facet.to_openlineage_format(),
                },
                "job": {
                    "namespace": self.namespace,
                    "name": dag_id,
                    "facets": {},
                },
                "inputs": [],
                "outputs": [],
            }

            # Add DataQualityAssertions if provided
            if assertions:
                event["run"]["facets"]["dataQualityAssertions"] = {
                    "_producer": "qubinode-smart-pipeline",
                    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataQualityAssertionsDatasetFacet.json",
                    "assertions": [
                        {
                            "assertion": a.assertion,
                            "success": a.success,
                            "column": a.column,
                        }
                        for a in assertions
                    ],
                }

            # Emit to Marquez
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.marquez_api_url}/api/v1/lineage",
                    json=event,
                )

                if response.status_code in (200, 201, 204):
                    logger.info(f"Emitted shadow error facet for {dag_id}:{run_id} to Marquez")
                    return True
                else:
                    logger.warning(f"Failed to emit to Marquez: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.warning(f"Could not emit OpenLineage event: {e}")
            return False

    async def query_shadow_errors(
        self,
        dag_id: Optional[str] = None,
        since_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Query recent shadow errors from Marquez.

        This allows the Manager Agent to understand patterns in shadow failures.

        Args:
            dag_id: Optional DAG to filter by
            since_hours: How far back to look

        Returns:
            List of shadow error events
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get recent runs with shadow error facets
                url = f"{self.marquez_api_url}/api/v1/namespaces/{self.namespace}/jobs"
                if dag_id:
                    url = f"{url}/{dag_id}/runs"

                response = await client.get(url, params={"limit": 50})

                if response.status_code != 200:
                    return []

                data = response.json()
                shadow_errors = []

                # Extract runs or jobs depending on endpoint
                items = data.get("runs", data.get("jobs", []))

                for item in items:
                    facets = item.get("facets", {})
                    if "shadowErrors" in facets:
                        shadow_errors.append(
                            {
                                "job_name": item.get("name") or dag_id,
                                "run_id": item.get("id") or item.get("runId"),
                                "shadow_errors": facets["shadowErrors"],
                                "started_at": item.get("startedAt"),
                            }
                        )

                return shadow_errors

        except Exception as e:
            logger.warning(f"Could not query shadow errors: {e}")
            return []


class ExecutionStatus(str, Enum):
    """Status of a pipeline execution."""

    PENDING = "pending"
    VALIDATING = "validating"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserActionType(str, Enum):
    """Types of user actions."""

    MONITOR = "monitor"
    CANCEL = "cancel"
    RETRY = "retry"
    SELF_FIX = "self_fix"
    ESCALATE = "escalate"


@dataclass
class UserAction:
    """An action the user can take in response to execution status."""

    action_type: UserActionType
    description: str
    command: Optional[str] = None
    api_endpoint: Optional[str] = None
    difficulty: str = "easy"  # easy, moderate, advanced


@dataclass
class ExecutionMonitoring:
    """Monitoring information for a pipeline execution."""

    airflow_ui_url: str
    status_endpoint: str
    openlineage_enabled: bool = True
    expected_duration_minutes: int = 10
    webhook_url: Optional[str] = None


@dataclass
class SmartPipelineExecution:
    """A smart pipeline execution with full tracking."""

    execution_id: str
    dag_id: str
    run_id: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    triggered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Validation
    validation_passed: bool = False
    validation_checks: List[Dict[str, Any]] = field(default_factory=list)

    # Parameters
    params: Dict[str, Any] = field(default_factory=dict)

    # Monitoring
    monitoring: Optional[ExecutionMonitoring] = None

    # User feedback
    user_actions: List[UserAction] = field(default_factory=list)
    error_message: Optional[str] = None
    failed_task: Optional[str] = None

    # Escalation
    escalation_needed: bool = False
    escalation_reason: Optional[str] = None


class SmartPipelineOrchestrator:
    """
    Orchestrates DAG execution with validation, tracking, and feedback.

    Features:
    - Pre-execution validation
    - OpenLineage event emission with DataQuality facets
    - Shadow error detection with ModelRetry pattern
    - Status monitoring
    - User action recommendations
    - Escalation support for Manager Agent

    Enhanced per ADR-0066 with:
    - PydanticAI ModelRetry pattern for self-correction
    - OpenLineage DataQuality facets for lineage tracking
    """

    def __init__(
        self,
        airflow_api_url: str = None,
        marquez_api_url: str = None,
    ):
        # Use environment variables for container/host operation
        if airflow_api_url is None:
            airflow_api_url = os.environ.get("AIRFLOW_API_URL", "http://localhost:8888/api/v1")
        if marquez_api_url is None:
            marquez_api_url = os.environ.get("MARQUEZ_API_URL", "http://localhost:5001/api/v1")
        self.airflow_api_url = airflow_api_url
        self.marquez_api_url = marquez_api_url

        # Airflow auth from environment
        self.airflow_user = os.environ.get("AIRFLOW_USER", "airflow")
        self.airflow_pass = os.environ.get("AIRFLOW_PASSWORD", "airflow")

        self._executions: Dict[str, SmartPipelineExecution] = {}

        # OpenLineage emitter for shadow error tracking
        self._openlineage_emitter = OpenLineageEmitter(marquez_api_url=marquez_api_url.replace("/api/v1", "") if marquez_api_url else None)

    async def execute_with_validation(
        self,
        dag_id: str,
        params: Optional[Dict[str, Any]] = None,
        validate_first: bool = True,
        smart_pipeline: bool = True,
    ) -> SmartPipelineExecution:
        """
        Execute a DAG with pre-validation and smart tracking.

        Args:
            dag_id: The DAG to execute
            params: DAG parameters/configuration
            validate_first: Whether to run validation before execution
            smart_pipeline: Whether to enable smart tracking features

        Returns:
            SmartPipelineExecution with status and monitoring info
        """
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        params = params or {}

        execution = SmartPipelineExecution(
            execution_id=execution_id,
            dag_id=dag_id,
            params=params,
        )
        self._executions[execution_id] = execution

        try:
            # Phase 1: Validation
            if validate_first:
                execution.status = ExecutionStatus.VALIDATING
                validation_result = await self._validate_dag(dag_id, params)

                execution.validation_checks = validation_result.get("checks", [])
                execution.validation_passed = validation_result.get("can_proceed", False)

                if not execution.validation_passed:
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = validation_result.get("error_summary", "Validation failed")
                    execution.user_actions = self._get_validation_failure_actions(validation_result)
                    return execution

            # Phase 2: Check and auto-unpause DAG if needed
            was_unpaused, unpause_message = await self._check_and_unpause_dag(dag_id)
            if was_unpaused:
                # Add info about auto-unpause to validation checks
                execution.validation_checks.append(
                    {
                        "name": "dag_auto_unpause",
                        "status": "passed",
                        "message": unpause_message,
                    }
                )
                logger.info(unpause_message)

            # Phase 3: Trigger DAG
            execution.status = ExecutionStatus.RUNNING
            execution.triggered_at = datetime.now()

            trigger_result = await self._trigger_dag(dag_id, params)

            if not trigger_result.get("success"):
                execution.status = ExecutionStatus.FAILED
                execution.error_message = trigger_result.get("error", "Failed to trigger DAG")
                execution.user_actions = self._get_trigger_failure_actions(dag_id)
                return execution

            execution.run_id = trigger_result.get("run_id")

            # Phase 4: Setup monitoring
            airflow_base = self.airflow_api_url.replace("/api/v1", "")
            execution.monitoring = ExecutionMonitoring(
                airflow_ui_url=f"{airflow_base}/dags/{dag_id}/grid?run_id={execution.run_id}",
                status_endpoint=f"/orchestrator/executions/{execution_id}/status",
                openlineage_enabled=smart_pipeline,
                expected_duration_minutes=self._estimate_duration(dag_id),
            )

            # Setup running actions
            execution.user_actions = [
                UserAction(
                    action_type=UserActionType.MONITOR,
                    description="Watch execution progress in Airflow UI",
                    api_endpoint=execution.monitoring.airflow_ui_url,
                ),
                UserAction(
                    action_type=UserActionType.CANCEL,
                    description="Cancel this execution",
                    api_endpoint=f"/orchestrator/executions/{execution_id}/cancel",
                ),
            ]

            return execution

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.user_actions = [
                UserAction(
                    action_type=UserActionType.ESCALATE,
                    description="Get help from Manager Agent",
                    api_endpoint="/orchestrator/escalate",
                ),
            ]
            logger.error(f"Pipeline execution failed: {e}")
            return execution

    async def get_execution_status(
        self,
        execution_id: str,
    ) -> Optional[SmartPipelineExecution]:
        """
        Get the current status of an execution.

        Polls Airflow for the latest DAG run status.
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        if execution.status not in (ExecutionStatus.RUNNING, ExecutionStatus.PENDING):
            return execution

        # Poll Airflow for current status
        if execution.run_id:
            run_status = await self._get_dag_run_status(
                execution.dag_id,
                execution.run_id,
            )

            if run_status:
                airflow_state = run_status.get("state", "").lower()

                if airflow_state == "success":
                    execution.status = ExecutionStatus.SUCCESS
                    execution.completed_at = datetime.now()
                    execution.user_actions = self._get_success_actions(execution)

                elif airflow_state in ("failed", "error"):
                    execution.status = ExecutionStatus.FAILED
                    execution.completed_at = datetime.now()
                    execution.failed_task = run_status.get("failed_task")
                    execution.error_message = run_status.get("error_message", "DAG run failed")
                    execution.user_actions = self._get_failure_actions(execution)

        return execution

    async def cancel_execution(
        self,
        execution_id: str,
    ) -> Dict[str, Any]:
        """Cancel a running execution."""
        execution = self._executions.get(execution_id)
        if not execution:
            return {"success": False, "error": "Execution not found"}

        if execution.status != ExecutionStatus.RUNNING:
            return {"success": False, "error": f"Cannot cancel: status is {execution.status.value}"}

        # Cancel in Airflow
        if execution.run_id:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.patch(
                        f"{self.airflow_api_url}/dags/{execution.dag_id}/dagRuns/{execution.run_id}",
                        json={"state": "failed"},
                        auth=(self.airflow_user, self.airflow_pass),
                    )
                    if response.status_code in (200, 204):
                        execution.status = ExecutionStatus.CANCELLED
                        execution.completed_at = datetime.now()
                        return {"success": True, "message": "Execution cancelled"}
            except Exception as e:
                logger.warning(f"Failed to cancel in Airflow: {e}")

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.now()
        return {"success": True, "message": "Execution marked as cancelled"}

    async def escalate_execution(
        self,
        execution_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Escalate an execution to Manager Agent."""
        execution = self._executions.get(execution_id)
        if not execution:
            return {"success": False, "error": "Execution not found"}

        execution.escalation_needed = True
        execution.escalation_reason = reason

        return {
            "success": True,
            "execution_id": execution_id,
            "escalation_reason": reason,
            "context": {
                "dag_id": execution.dag_id,
                "status": execution.status.value,
                "error_message": execution.error_message,
                "failed_task": execution.failed_task,
                "validation_checks": execution.validation_checks,
            },
        }

    async def _validate_dag(
        self,
        dag_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate a DAG before execution."""
        try:
            from dag_validator import get_dag_validator

            validator = await get_dag_validator()
            validation = await validator.validate_dag(dag_id, params)

            return {
                "can_proceed": validation.can_proceed,
                "checks": [
                    {
                        "name": c.name,
                        "status": c.status.value,
                        "message": c.message,
                        "fix_suggestion": c.fix_suggestion,
                    }
                    for c in validation.checks
                ],
                "error_summary": validation.error_summary,
            }
        except ImportError:
            # DAG validator not available, assume valid
            return {"can_proceed": True, "checks": []}
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            return {
                "can_proceed": False,
                "checks": [{"name": "validation_error", "status": "failed", "message": str(e)}],
                "error_summary": str(e),
            }

    async def _trigger_dag(
        self,
        dag_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Trigger a DAG run in Airflow."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.airflow_api_url}/dags/{dag_id}/dagRuns",
                    json={
                        "conf": params,
                        "note": "Triggered by Qubinode Smart Pipeline",
                    },
                    auth=(self.airflow_user, self.airflow_pass),
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    return {
                        "success": True,
                        "run_id": data.get("dag_run_id"),
                        "logical_date": data.get("logical_date"),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Airflow returned {response.status_code}: {response.text}",
                    }
        except Exception as e:
            logger.error(f"Failed to trigger DAG: {e}")
            return {"success": False, "error": str(e)}

    async def _get_dag_run_status(
        self,
        dag_id: str,
        run_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the status of a DAG run from Airflow."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.airflow_api_url}/dags/{dag_id}/dagRuns/{run_id}",
                    auth=(self.airflow_user, self.airflow_pass),
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "state": data.get("state"),
                        "start_date": data.get("start_date"),
                        "end_date": data.get("end_date"),
                    }
        except Exception as e:
            logger.debug(f"Could not get DAG run status: {e}")
        return None

    async def _check_and_unpause_dag(self, dag_id: str) -> Tuple[bool, str]:
        """
        Check if a DAG is paused and auto-unpause it if needed.

        Returns:
            Tuple of (was_unpaused, message)
            - was_unpaused: True if we unpaused the DAG, False if it was already active
            - message: Description of what happened
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get DAG info
                response = await client.get(
                    f"{self.airflow_api_url}/dags/{dag_id}",
                    auth=(self.airflow_user, self.airflow_pass),
                )

                if response.status_code != 200:
                    logger.warning(f"Could not get DAG info: {response.status_code}")
                    return False, f"Could not check DAG status (HTTP {response.status_code})"

                data = response.json()
                is_paused = data.get("is_paused", False)

                if not is_paused:
                    logger.info(f"DAG '{dag_id}' is already active")
                    return False, f"DAG '{dag_id}' is already active"

                # DAG is paused - unpause it
                logger.info(f"DAG '{dag_id}' is paused, auto-unpausing...")

                unpause_response = await client.patch(
                    f"{self.airflow_api_url}/dags/{dag_id}",
                    json={"is_paused": False},
                    auth=(self.airflow_user, self.airflow_pass),
                )

                if unpause_response.status_code == 200:
                    logger.info(f"Successfully unpaused DAG '{dag_id}'")
                    return True, f"DAG '{dag_id}' was paused - automatically unpaused it"
                else:
                    logger.warning(f"Failed to unpause DAG: {unpause_response.status_code}")
                    return False, f"DAG '{dag_id}' is paused and could not be auto-unpaused"

        except Exception as e:
            logger.debug(f"Could not check/unpause DAG: {e}")
            return False, f"Could not verify DAG pause status: {e}"

    def _estimate_duration(self, dag_id: str) -> int:
        """Estimate execution duration in minutes based on DAG type."""
        dag_lower = dag_id.lower()

        if "vm" in dag_lower:
            return 15  # VM deployments take ~15 min
        elif "openshift" in dag_lower or "ocp" in dag_lower:
            return 60  # OpenShift can take an hour
        elif "freeipa" in dag_lower:
            return 20  # FreeIPA ~20 min
        elif "harbor" in dag_lower or "registry" in dag_lower:
            return 15  # Registry ~15 min
        else:
            return 10  # Default 10 min

    def _get_validation_failure_actions(
        self,
        validation_result: Dict[str, Any],
    ) -> List[UserAction]:
        """Get user actions for validation failures."""
        actions = []

        for check in validation_result.get("checks", []):
            if check.get("status") == "failed" and check.get("fix_suggestion"):
                actions.append(
                    UserAction(
                        action_type=UserActionType.SELF_FIX,
                        description=check["fix_suggestion"],
                        difficulty="moderate",
                    )
                )

        actions.append(
            UserAction(
                action_type=UserActionType.RETRY,
                description="Retry with different parameters",
                api_endpoint="/orchestrator/execute",
                difficulty="easy",
            )
        )

        actions.append(
            UserAction(
                action_type=UserActionType.ESCALATE,
                description="Get help from Manager Agent",
                api_endpoint="/orchestrator/escalate",
                difficulty="easy",
            )
        )

        return actions

    def _get_trigger_failure_actions(self, dag_id: str) -> List[UserAction]:
        """Get user actions for trigger failures."""
        return [
            UserAction(
                action_type=UserActionType.RETRY,
                description="Retry triggering the DAG",
                api_endpoint="/orchestrator/execute",
            ),
            UserAction(
                action_type=UserActionType.SELF_FIX,
                description=f"Check if DAG '{dag_id}' is active in Airflow",
                command=f"airflow dags unpause {dag_id}",
                difficulty="easy",
            ),
            UserAction(
                action_type=UserActionType.ESCALATE,
                description="Get help from Manager Agent",
                api_endpoint="/orchestrator/escalate",
            ),
        ]

    def _get_success_actions(self, execution: SmartPipelineExecution) -> List[UserAction]:
        """Get user actions after successful execution."""
        return [
            UserAction(
                action_type=UserActionType.MONITOR,
                description="View execution details in Airflow",
                api_endpoint=execution.monitoring.airflow_ui_url if execution.monitoring else None,
            ),
        ]

    def _get_failure_actions(self, execution: SmartPipelineExecution) -> List[UserAction]:
        """Get user actions after execution failure."""
        actions = []

        # Add specific fix based on error
        if execution.error_message:
            if "template" in execution.error_message.lower():
                actions.append(
                    UserAction(
                        action_type=UserActionType.SELF_FIX,
                        description="Download the missing template",
                        command="kcli download <template_name>",
                        difficulty="easy",
                    )
                )
            elif "disk" in execution.error_message.lower() or "space" in execution.error_message.lower():
                actions.append(
                    UserAction(
                        action_type=UserActionType.SELF_FIX,
                        description="Free disk space on target server",
                        command="df -h && du -sh /var/lib/libvirt/images/*",
                        difficulty="moderate",
                    )
                )
            elif "network" in execution.error_message.lower():
                actions.append(
                    UserAction(
                        action_type=UserActionType.SELF_FIX,
                        description="Check network connectivity",
                        command="ping -c 3 <target_ip>",
                        difficulty="easy",
                    )
                )

        # Always add retry and escalate
        actions.append(
            UserAction(
                action_type=UserActionType.RETRY,
                description="Retry with updated parameters",
                api_endpoint="/orchestrator/execute",
                difficulty="easy",
            )
        )

        actions.append(
            UserAction(
                action_type=UserActionType.ESCALATE,
                description="Get help from Manager Agent",
                api_endpoint="/orchestrator/escalate",
                difficulty="easy",
            )
        )

        return actions

    # =========================================================================
    # Shadow Error Detection & Outcome Validation
    # =========================================================================

    async def _get_task_logs(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
    ) -> Optional[str]:
        """Fetch task logs from Airflow API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get task instances first
                response = await client.get(
                    f"{self.airflow_api_url}/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/1",
                    auth=(self.airflow_user, self.airflow_pass),
                )
                if response.status_code == 200:
                    return response.text
        except Exception as e:
            logger.debug(f"Could not fetch task logs: {e}")
        return None

    async def _get_all_task_instances(
        self,
        dag_id: str,
        run_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all task instances for a DAG run."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.airflow_api_url}/dags/{dag_id}/dagRuns/{run_id}/taskInstances",
                    auth=(self.airflow_user, self.airflow_pass),
                )
                if response.status_code == 200:
                    return response.json().get("task_instances", [])
        except Exception as e:
            logger.debug(f"Could not fetch task instances: {e}")
        return []

    def _detect_shadow_errors(self, log_content: str) -> List[Dict[str, Any]]:
        """
        Analyze task logs to detect shadow errors - failures that didn't cause task failure.

        These are errors that occurred but the task still reported success (exit 0).
        """
        shadow_errors = []

        # Known error patterns that indicate failure even if exit code was 0
        # These patterns match actual task output, not bash script source code
        # The log format is: {subprocess.py:106} INFO - <actual output>
        error_patterns = [
            # Script errors in actual output
            {
                "pattern": r"Error: '([^']+)' does not exist",
                "type": "missing_path",
                "severity": "critical",
                "description": "Required file or directory does not exist",
            },
            {
                "pattern": r"Error: ([^\n]+)",
                "type": "script_error",
                "severity": "high",
                "description": "Script reported an error",
            },
            {
                "pattern": r"\[ERROR\] ([^\n]+)",
                "type": "explicit_error",
                "severity": "high",
                "description": "Explicit error logged",
            },
            # Bash errors
            {
                "pattern": r"bash: line \d+: cd: ([^:]+): No such file or directory",
                "type": "missing_directory",
                "severity": "critical",
                "description": "Failed to change to required directory",
            },
            {
                "pattern": r"bash: ([^:]+): command not found",
                "type": "missing_command",
                "severity": "critical",
                "description": "Required command is not installed",
            },
            {
                "pattern": r"bash: ([^:]+): Permission denied",
                "type": "permission_denied",
                "severity": "critical",
                "description": "Insufficient permissions",
            },
            # SSH/Network errors
            {
                "pattern": r"ssh: connect to host ([^\s]+) .+ Connection refused",
                "type": "connection_refused",
                "severity": "high",
                "description": "SSH connection refused",
            },
            {
                "pattern": r"Connection timed out",
                "type": "connection_timeout",
                "severity": "high",
                "description": "Connection timed out",
            },
            # kcli specific errors
            {
                "pattern": r"kcli: error: ([^\n]+)",
                "type": "kcli_error",
                "severity": "high",
                "description": "kcli command failed",
            },
            {
                "pattern": r"(?:Image|Template|Profile) '?([^']+)'? (?:not found|does not exist)",
                "type": "missing_image",
                "severity": "high",
                "description": "Required VM image or profile not found",
            },
            # Generic failure indicators
            {
                "pattern": r"FATAL: ([^\n]+)",
                "type": "fatal_error",
                "severity": "critical",
                "description": "Fatal error occurred",
            },
            {
                "pattern": r"Failed to (create|delete|start|stop|connect|download|configure) ([^\n]+)",
                "type": "operation_failed",
                "severity": "high",
                "description": "Operation explicitly failed",
            },
            # Exit codes logged (the inner script exited with error)
            {
                "pattern": r"exit 1",
                "type": "script_exit_error",
                "severity": "high",
                "description": "Script exited with error code 1",
            },
        ]

        import re

        for pattern_info in error_patterns:
            matches = re.findall(pattern_info["pattern"], log_content, re.IGNORECASE | re.MULTILINE)
            if matches:
                for match in matches:
                    shadow_errors.append(
                        {
                            "type": pattern_info["type"],
                            "severity": pattern_info["severity"],
                            "description": pattern_info["description"],
                            "detail": match if isinstance(match, str) else match[0] if match else "",
                            "pattern": pattern_info["pattern"],
                        }
                    )

        return shadow_errors

    def _generate_fix_suggestions(
        self,
        shadow_errors: List[Dict[str, Any]],
        dag_id: str,
        params: Dict[str, Any],
    ) -> List[UserAction]:
        """Generate actionable fix suggestions based on detected shadow errors."""
        actions = []

        for error in shadow_errors:
            error_type = error.get("type")
            detail = error.get("detail", "")

            if error_type == "missing_directory":
                # Detect if it's kcli-pipelines
                if "kcli-pipelines" in detail or "qubinode-pipelines" in detail:
                    actions.append(
                        UserAction(
                            action_type=UserActionType.SELF_FIX,
                            description="Install kcli-pipelines on the target host",
                            command="git clone https://github.com/tosin2013/kcli-pipelines.git /opt/kcli-pipelines",
                            difficulty="easy",
                        )
                    )
                else:
                    actions.append(
                        UserAction(
                            action_type=UserActionType.SELF_FIX,
                            description=f"Create missing directory: {detail}",
                            command=f"mkdir -p {detail}",
                            difficulty="easy",
                        )
                    )

            elif error_type == "missing_path":
                actions.append(
                    UserAction(
                        action_type=UserActionType.SELF_FIX,
                        description=f"Verify path exists: {detail}",
                        command=f"ls -la {detail}",
                        difficulty="easy",
                    )
                )

            elif error_type == "missing_command":
                actions.append(
                    UserAction(
                        action_type=UserActionType.SELF_FIX,
                        description="Install missing command/tool",
                        command=f"which {detail.split()[0] if detail else 'COMMAND'}",
                        difficulty="moderate",
                    )
                )

            elif error_type == "permission_denied":
                actions.append(
                    UserAction(
                        action_type=UserActionType.SELF_FIX,
                        description="Check and fix file permissions",
                        command=f"ls -la {detail}" if detail else "Check permissions on the target path",
                        difficulty="moderate",
                    )
                )

            elif error_type == "connection_failed":
                actions.append(
                    UserAction(
                        action_type=UserActionType.SELF_FIX,
                        description="Check network connectivity and service status",
                        command="systemctl status sshd && ping -c 3 localhost",
                        difficulty="moderate",
                    )
                )

        return actions

    async def validate_outcome(
        self,
        execution: SmartPipelineExecution,
        emit_to_openlineage: bool = True,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Validate the actual outcome matches the expected outcome.

        Enhanced with:
        - ModelRetry pattern for self-correction suggestions
        - OpenLineage DataQuality facet emission for Manager Agent

        For VM creation: verify the VM exists
        For deletion: verify the VM is gone

        Args:
            execution: The pipeline execution to validate
            emit_to_openlineage: Whether to emit shadow errors to Marquez
            retry_count: Current retry attempt (for ModelRetry tracking)

        Returns:
            Validation result with shadow errors, fix suggestions, and retry info
        """
        result = {
            "validated": False,
            "expected_outcome": None,
            "actual_outcome": None,
            "shadow_errors": [],
            "fix_suggestions": [],
            # ModelRetry pattern fields
            "model_retry": None,
            "can_self_correct": False,
            "corrected_params": {},
            # OpenLineage tracking
            "openlineage_emitted": False,
        }

        dag_id = execution.dag_id
        params = execution.params

        # Determine expected outcome based on DAG and params
        if "vm" in dag_id.lower():
            action = params.get("action", "create")
            vm_name = params.get("vm_name", "")
            vm_profile = params.get("vm_profile", "")

            if action == "create":
                result["expected_outcome"] = f"VM should exist: {vm_name or vm_profile}"
                # Check if VM was actually created
                vm_exists = await self._check_vm_exists(vm_name, vm_profile)
                result["actual_outcome"] = "VM exists" if vm_exists else "VM NOT found"
                result["validated"] = vm_exists

            elif action == "delete":
                result["expected_outcome"] = f"VM should be deleted: {vm_name}"
                vm_exists = await self._check_vm_exists(vm_name, vm_profile)
                result["actual_outcome"] = "VM deleted" if not vm_exists else "VM still exists"
                result["validated"] = not vm_exists

        # Analyze task logs for shadow errors
        if execution.run_id:
            task_instances = await self._get_all_task_instances(execution.dag_id, execution.run_id)
            for task in task_instances:
                task_id = task.get("task_id")
                if task_id:
                    logs = await self._get_task_logs(execution.dag_id, execution.run_id, task_id)
                    if logs:
                        errors = self._detect_shadow_errors(logs)
                        result["shadow_errors"].extend(errors)

        # Generate fix suggestions
        fix_actions = []
        fix_commands = []
        if result["shadow_errors"]:
            fix_actions = self._generate_fix_suggestions(result["shadow_errors"], dag_id, params)
            result["fix_suggestions"] = fix_actions
            fix_commands = [a.command for a in fix_actions if a.command]

        # =====================================================================
        # ModelRetry Pattern: Generate self-correction suggestions
        # =====================================================================
        if not result["validated"] or result["shadow_errors"]:
            corrected_params, retry_message = self._generate_model_retry_params(result["shadow_errors"], dag_id, params)

            if corrected_params or fix_commands:
                model_retry = ModelRetry(
                    message=retry_message or f"Validation failed: {result['actual_outcome']}",
                    corrected_params=corrected_params,
                    fix_commands=fix_commands,
                    retry_count=retry_count,
                )
                result["model_retry"] = model_retry.to_dict()
                result["can_self_correct"] = model_retry.can_retry and bool(corrected_params)
                result["corrected_params"] = corrected_params

        # =====================================================================
        # OpenLineage: Emit shadow error facet to Marquez for Manager Agent
        # =====================================================================
        if emit_to_openlineage and execution.run_id:
            # Build quality assertions
            assertions = [
                DataQualityAssertion(
                    assertion="outcome_validated",
                    success=result["validated"],
                    details=result["actual_outcome"],
                ),
                DataQualityAssertion(
                    assertion="no_shadow_errors",
                    success=len(result["shadow_errors"]) == 0,
                    details=f"{len(result['shadow_errors'])} shadow errors detected",
                ),
            ]

            # Build shadow error facet
            facet = ShadowErrorFacet(
                expected_outcome=result["expected_outcome"],
                actual_outcome=result["actual_outcome"],
                outcome_validated=result["validated"],
                shadow_errors=result["shadow_errors"],
                retry_suggested=result["can_self_correct"],
                retry_params=result.get("corrected_params"),
                fix_commands=fix_commands,
            )

            # Emit to Marquez
            emitted = await self._openlineage_emitter.emit_shadow_error_event(
                dag_id=dag_id,
                run_id=execution.run_id,
                facet=facet,
                assertions=assertions,
            )
            result["openlineage_emitted"] = emitted

            if emitted:
                logger.info(f"Shadow error facet emitted to Marquez for {dag_id}:{execution.run_id}")

        return result

    def _generate_model_retry_params(
        self,
        shadow_errors: List[Dict[str, Any]],
        dag_id: str,
        params: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Generate corrected parameters for ModelRetry based on shadow errors.

        This enables self-correction when the agent detects specific error patterns.

        Returns:
            Tuple of (corrected_params, retry_message)
        """
        corrected_params = {}
        messages = []

        for error in shadow_errors:
            error_type = error.get("type")
            detail = error.get("detail", "")

            if error_type == "missing_image":
                # Suggest a valid profile
                messages.append(f"Profile '{detail}' not found. Try a valid kcli profile.")
                # Could query available profiles and suggest one
                corrected_params["_suggestion"] = "Use 'kcli list profiles' to see available options"

            elif error_type == "missing_directory":
                if "kcli-pipelines" in detail:
                    messages.append("kcli-pipelines not installed. Run fix command first.")
                    corrected_params["_requires_fix"] = True
                    corrected_params["_fix_command"] = "git clone https://github.com/tosin2013/kcli-pipelines.git /opt/kcli-pipelines"

            elif error_type == "connection_refused" or error_type == "connection_timeout":
                # Suggest different target server or wait
                messages.append("Connection failed. Check target server is reachable.")
                if params.get("target_server") == "localhost":
                    corrected_params["target_server"] = "Check SSH service is running"

            elif error_type == "permission_denied":
                messages.append("Permission denied. May need sudo or different user.")
                corrected_params["_requires_elevated_permissions"] = True

        retry_message = "; ".join(messages) if messages else None
        return corrected_params, retry_message

    async def _check_vm_exists(
        self,
        vm_name: str,
        vm_profile: str,
    ) -> bool:
        """Check if a VM exists via SSH to host."""
        try:
            import asyncio

            # Use asyncio subprocess to check VM exists
            search_term = vm_name if vm_name else vm_profile
            if not search_term:
                return False

            proc = await asyncio.create_subprocess_shell(
                f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@localhost 'kcli list vm' 2>/dev/null | grep -q '{search_term}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception as e:
            logger.warning(f"Could not check VM existence: {e}")
            return False


# Singleton instance
_orchestrator: Optional[SmartPipelineOrchestrator] = None


async def get_smart_orchestrator() -> SmartPipelineOrchestrator:
    """Get the singleton smart pipeline orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SmartPipelineOrchestrator()
    return _orchestrator


async def execute_smart_pipeline(
    dag_id: str,
    params: Optional[Dict[str, Any]] = None,
    validate_first: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to execute a smart pipeline.

    Returns execution result with monitoring and user actions.
    """
    orchestrator = await get_smart_orchestrator()
    execution = await orchestrator.execute_with_validation(
        dag_id=dag_id,
        params=params,
        validate_first=validate_first,
    )

    return {
        "execution_id": execution.execution_id,
        "dag_id": execution.dag_id,
        "run_id": execution.run_id,
        "status": execution.status.value,
        "validation_passed": execution.validation_passed,
        "validation_checks": execution.validation_checks,
        "monitoring": {
            "airflow_ui_url": execution.monitoring.airflow_ui_url if execution.monitoring else None,
            "status_endpoint": execution.monitoring.status_endpoint if execution.monitoring else None,
            "expected_duration_minutes": execution.monitoring.expected_duration_minutes if execution.monitoring else None,
        }
        if execution.monitoring
        else None,
        "user_actions": [
            {
                "action_type": a.action_type.value,
                "description": a.description,
                "command": a.command,
                "api_endpoint": a.api_endpoint,
                "difficulty": a.difficulty,
            }
            for a in execution.user_actions
        ],
        "error_message": execution.error_message,
        "escalation_needed": execution.escalation_needed,
    }


# =============================================================================
# Manager Agent Integration: Shadow Error Query API
# =============================================================================


async def query_shadow_errors_for_manager(
    dag_id: Optional[str] = None,
    since_hours: int = 24,
) -> Dict[str, Any]:
    """
    Query shadow errors from Marquez for the Manager Agent.

    This enables the Manager Agent to:
    - Understand patterns in shadow failures
    - Make decisions about escalation
    - Track recurring issues across DAGs

    Args:
        dag_id: Optional DAG to filter by
        since_hours: How far back to look

    Returns:
        Summary of shadow errors for Manager Agent
    """
    emitter = OpenLineageEmitter()
    errors = await emitter.query_shadow_errors(dag_id, since_hours)

    # Aggregate by error type
    error_types = {}
    for event in errors:
        shadow_errors = event.get("shadow_errors", {}).get("errors", [])
        for err in shadow_errors:
            err_type = err.get("type", "unknown")
            if err_type not in error_types:
                error_types[err_type] = {"count": 0, "examples": []}
            error_types[err_type]["count"] += 1
            if len(error_types[err_type]["examples"]) < 3:
                error_types[err_type]["examples"].append(
                    {
                        "job": event.get("job_name"),
                        "detail": err.get("detail"),
                    }
                )

    return {
        "total_shadow_failures": len(errors),
        "dag_filter": dag_id,
        "since_hours": since_hours,
        "error_types": error_types,
        "events": errors[:10],  # Return last 10 events
        "recommendations": _generate_manager_recommendations(error_types),
    }


def _generate_manager_recommendations(error_types: Dict[str, Any]) -> List[str]:
    """Generate recommendations for the Manager Agent based on error patterns."""
    recommendations = []

    for err_type, data in error_types.items():
        count = data.get("count", 0)

        if err_type == "missing_directory" and count >= 2:
            recommendations.append(f"Recurring 'missing_directory' errors ({count}x). " "Consider adding prerequisite check DAG or alerting ops team.")

        if err_type == "missing_image" and count >= 2:
            recommendations.append(f"Recurring 'missing_image' errors ({count}x). " "Suggest pre-downloading common images or adding profile validation.")

        if err_type == "connection_refused" and count >= 3:
            recommendations.append(f"High 'connection_refused' errors ({count}x). " "Infrastructure connectivity issue - escalate to ops.")

        if err_type == "permission_denied" and count >= 1:
            recommendations.append(f"'permission_denied' errors detected ({count}x). " "Review service account permissions on target hosts.")

    if not recommendations:
        recommendations.append("No critical patterns detected. Continue monitoring.")

    return recommendations


async def get_openlineage_emitter() -> OpenLineageEmitter:
    """Get an OpenLineage emitter for external use."""
    return OpenLineageEmitter()


# Export key classes and functions
__all__ = [
    # Core classes
    "SmartPipelineOrchestrator",
    "SmartPipelineExecution",
    "ExecutionStatus",
    "UserActionType",
    "UserAction",
    "ExecutionMonitoring",
    # ModelRetry pattern
    "ModelRetry",
    # OpenLineage integration
    "OpenLineageEmitter",
    "ShadowErrorFacet",
    "DataQualityAssertion",
    # Convenience functions
    "get_smart_orchestrator",
    "execute_smart_pipeline",
    "query_shadow_errors_for_manager",
    "get_openlineage_emitter",
]
