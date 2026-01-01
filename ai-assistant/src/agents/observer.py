"""
Lineage Observer Agent: Comprehensive DAG execution monitoring and feedback.

This agent ALWAYS reports back with full status, regardless of pass/fail.
It provides:
- Real-time execution status monitoring
- Task-level progress tracking
- Error detection (including "shadow errors")
- Success confirmation with details
- Concerns and recommendations

Per ADR-0066: Developer Agent DAG Validation and Smart Pipelines
Per ADR-0049: Multi-Agent LLM Memory Architecture
"""

import os
import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """DAG/Task execution status."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    UP_FOR_RETRY = "up_for_retry"
    UP_FOR_RESCHEDULE = "up_for_reschedule"
    UPSTREAM_FAILED = "upstream_failed"
    UNKNOWN = "unknown"


class ConcernLevel(str, Enum):
    """Level of concern for observations."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TaskObservation:
    """Observation about a specific task."""

    task_id: str
    status: ExecutionStatus
    duration_seconds: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    log_snippet: Optional[str] = None
    error_message: Optional[str] = None
    concerns: List[str] = field(default_factory=list)


@dataclass
class Concern:
    """A concern or observation about the execution."""

    level: ConcernLevel
    category: str
    message: str
    task_id: Optional[str] = None
    recommendation: Optional[str] = None


class ObserverReport(BaseModel):
    """Comprehensive report from the Lineage Observer Agent."""

    # Identifiers
    dag_id: str
    run_id: str
    observation_time: datetime = Field(default_factory=datetime.now)

    # Overall Status
    overall_status: ExecutionStatus
    is_complete: bool = False
    success: bool = False

    # Progress
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: int = 0
    pending_tasks: int = 0
    progress_percent: float = 0.0

    # Task Details
    task_statuses: Dict[str, str] = Field(default_factory=dict)
    failed_task_details: List[Dict[str, Any]] = Field(default_factory=list)

    # Concerns (ALWAYS populated - even on success)
    concerns: List[Dict[str, Any]] = Field(default_factory=list)
    has_warnings: bool = False
    has_errors: bool = False
    has_critical: bool = False

    # Recommendations (ALWAYS provided)
    recommendations: List[str] = Field(default_factory=list)

    # Timing
    elapsed_seconds: Optional[float] = None
    estimated_remaining_seconds: Optional[float] = None

    # Summary (human-readable)
    summary: str = ""
    detailed_message: str = ""

    # Lineage Data (if available)
    lineage_run_id: Optional[str] = None
    lineage_events: List[Dict[str, Any]] = Field(default_factory=list)


class ObserverDependencies(BaseModel):
    """Dependencies for the Observer Agent."""

    airflow_api_url: str = "http://localhost:8888"
    airflow_user: str = "admin"
    airflow_pass: str = "admin"
    marquez_api_url: Optional[str] = "http://localhost:5001"

    # Observation settings
    check_logs: bool = True
    log_lines_to_fetch: int = 50
    detect_shadow_errors: bool = True

    # Shadow error patterns to detect in logs
    shadow_error_patterns: List[str] = Field(
        default_factory=lambda: [
            "[ERROR]",
            "Error:",
            "Exception:",
            "Failed:",
            "FAILED",
            "Traceback",
            "not found",
            "permission denied",
            "Connection refused",
            "timeout",
            "vault.yml not found",
            "No such file or directory",
            "command not found",
        ]
    )

    class Config:
        arbitrary_types_allowed = True


class LineageObserverAgent:
    """
    Lineage Observer Agent for comprehensive DAG monitoring.

    This agent ALWAYS reports back with full context:
    - On success: confirms what worked, timing, any minor concerns
    - On failure: detailed error info, affected tasks, recommendations
    - On running: progress update, ETA, any early warnings

    Key principle: Never stay silent. Always provide actionable feedback.
    """

    def __init__(
        self,
        airflow_api_url: Optional[str] = None,
        airflow_user: Optional[str] = None,
        airflow_pass: Optional[str] = None,
        marquez_api_url: Optional[str] = None,
    ):
        self.airflow_api_url = airflow_api_url or os.getenv("AIRFLOW_API_URL", "http://localhost:8888")
        self.airflow_user = airflow_user or os.getenv("AIRFLOW_API_USER", "admin")
        self.airflow_pass = airflow_pass or os.getenv("AIRFLOW_API_PASSWORD", "admin")
        self.marquez_api_url = marquez_api_url or os.getenv("MARQUEZ_API_URL", "http://localhost:5001")

        self.deps = ObserverDependencies(
            airflow_api_url=self.airflow_api_url,
            airflow_user=self.airflow_user,
            airflow_pass=self.airflow_pass,
            marquez_api_url=self.marquez_api_url,
        )

        # Track observations over time for pattern detection
        self._observation_history: List[ObserverReport] = []

    async def observe(
        self,
        dag_id: str,
        run_id: str,
        check_logs: bool = True,
    ) -> ObserverReport:
        """
        Observe a DAG run and return comprehensive feedback.

        ALWAYS returns a full report with:
        - Current status
        - Task-level details
        - Any concerns (even minor ones)
        - Recommendations for next steps

        Args:
            dag_id: The DAG to observe
            run_id: The specific run to observe
            check_logs: Whether to fetch and analyze task logs

        Returns:
            ObserverReport with complete status and feedback
        """
        report = ObserverReport(
            dag_id=dag_id,
            run_id=run_id,
            overall_status=ExecutionStatus.UNKNOWN,
        )

        concerns: List[Concern] = []
        recommendations: List[str] = []

        try:
            # Get DAG run status
            run_info = await self._get_dag_run(dag_id, run_id)
            if not run_info:
                report.overall_status = ExecutionStatus.UNKNOWN
                concerns.append(
                    Concern(
                        level=ConcernLevel.ERROR,
                        category="api",
                        message=f"Could not retrieve DAG run info for {dag_id}/{run_id}",
                        recommendation="Check if the DAG run exists and Airflow API is accessible",
                    )
                )
                report.summary = f"Unable to observe DAG run {dag_id}/{run_id}"
                self._finalize_report(report, concerns, recommendations)
                return report

            # Parse run status
            state = run_info.get("state", "unknown").lower()
            report.overall_status = self._map_state(state)
            report.is_complete = state in ["success", "failed"]
            report.success = state == "success"

            # Calculate elapsed time
            start_date = run_info.get("start_date")
            end_date = run_info.get("end_date")
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else datetime.now(start_dt.tzinfo)
                report.elapsed_seconds = (end_dt - start_dt).total_seconds()

            # Get task instances
            task_instances = await self._get_task_instances(dag_id, run_id)
            await self._analyze_tasks(report, task_instances, concerns, recommendations, check_logs)

            # Check for shadow errors in logs
            if check_logs and self.deps.detect_shadow_errors:
                await self._detect_shadow_errors(dag_id, run_id, task_instances, concerns, recommendations)

            # Get lineage data if available
            await self._get_lineage_data(dag_id, run_id, report)

            # Generate summary and recommendations
            self._generate_summary(report, concerns, recommendations)

        except Exception as e:
            logger.error(f"Observer error for {dag_id}/{run_id}: {e}")
            concerns.append(
                Concern(
                    level=ConcernLevel.ERROR,
                    category="observer",
                    message=f"Observer encountered an error: {str(e)}",
                    recommendation="Check observer logs and Airflow connectivity",
                )
            )
            report.summary = f"Observer error: {str(e)}"

        self._finalize_report(report, concerns, recommendations)
        self._observation_history.append(report)

        return report

    async def observe_until_complete(
        self,
        dag_id: str,
        run_id: str,
        poll_interval: int = 10,
        max_wait: int = 3600,
        callback: Optional[callable] = None,
    ) -> ObserverReport:
        """
        Observe a DAG run until completion, providing periodic updates.

        Args:
            dag_id: The DAG to observe
            run_id: The run to observe
            poll_interval: Seconds between checks
            max_wait: Maximum seconds to wait
            callback: Optional callback for each observation

        Returns:
            Final ObserverReport when complete
        """
        elapsed = 0
        last_report = None

        while elapsed < max_wait:
            report = await self.observe(dag_id, run_id, check_logs=True)
            last_report = report

            # Call callback with current status
            if callback:
                try:
                    await callback(report) if asyncio.iscoroutinefunction(callback) else callback(report)
                except Exception as e:
                    logger.warning(f"Callback error: {e}")

            # Check if complete
            if report.is_complete:
                logger.info(f"DAG {dag_id} run {run_id} completed: {'SUCCESS' if report.success else 'FAILED'}")
                return report

            # Wait before next check
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout
        if last_report:
            last_report.concerns.append(
                {
                    "level": "warning",
                    "category": "timeout",
                    "message": f"Observation timed out after {max_wait}s",
                    "recommendation": "DAG may still be running - check Airflow UI",
                }
            )
            last_report.recommendations.append(f"Check Airflow UI: {self.airflow_api_url}/dags/{dag_id}/grid")

        return last_report or ObserverReport(
            dag_id=dag_id,
            run_id=run_id,
            overall_status=ExecutionStatus.UNKNOWN,
            summary="Observation timed out",
        )

    async def _get_dag_run(self, dag_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Get DAG run information from Airflow API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.airflow_api_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}",
                    auth=(self.airflow_user, self.airflow_pass),
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to get DAG run: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error getting DAG run: {e}")
            return None

    async def _get_task_instances(self, dag_id: str, run_id: str) -> List[Dict[str, Any]]:
        """Get all task instances for a DAG run."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.airflow_api_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances",
                    auth=(self.airflow_user, self.airflow_pass),
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("task_instances", [])
                else:
                    logger.warning(f"Failed to get task instances: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error getting task instances: {e}")
            return []

    async def _get_task_logs(self, dag_id: str, run_id: str, task_id: str, try_number: int = 1) -> Optional[str]:
        """Get logs for a specific task instance."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.airflow_api_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}",
                    auth=(self.airflow_user, self.airflow_pass),
                )
                if response.status_code == 200:
                    return response.text
                return None
        except Exception as e:
            logger.debug(f"Could not get logs for {task_id}: {e}")
            return None

    async def _analyze_tasks(
        self,
        report: ObserverReport,
        task_instances: List[Dict[str, Any]],
        concerns: List[Concern],
        recommendations: List[str],
        check_logs: bool,
    ) -> None:
        """Analyze task instances and update report."""
        report.total_tasks = len(task_instances)

        for task in task_instances:
            task_id = task.get("task_id", "unknown")
            state = task.get("state", "unknown")
            report.task_statuses[task_id] = state

            if state == "success":
                report.completed_tasks += 1
            elif state == "failed":
                report.failed_tasks += 1
                # Get failure details
                failure_info = {
                    "task_id": task_id,
                    "state": state,
                    "try_number": task.get("try_number", 1),
                    "start_date": task.get("start_date"),
                    "end_date": task.get("end_date"),
                }

                # Fetch logs for failed tasks
                if check_logs:
                    logs = await self._get_task_logs(
                        report.dag_id,
                        report.run_id,
                        task_id,
                        task.get("try_number", 1),
                    )
                    if logs:
                        # Extract last N lines
                        log_lines = logs.strip().split("\n")
                        failure_info["log_tail"] = "\n".join(log_lines[-self.deps.log_lines_to_fetch :])

                        # Look for error messages
                        error_lines = [line for line in log_lines if any(pattern.lower() in line.lower() for pattern in ["error", "exception", "failed"])]
                        if error_lines:
                            failure_info["error_messages"] = error_lines[-5:]

                report.failed_task_details.append(failure_info)

                concerns.append(
                    Concern(
                        level=ConcernLevel.ERROR,
                        category="task_failure",
                        message=f"Task '{task_id}' failed",
                        task_id=task_id,
                        recommendation=f"Check logs for task '{task_id}' in Airflow UI",
                    )
                )

            elif state == "running":
                report.running_tasks += 1
            elif state in ["queued", "scheduled", "none", None]:
                report.pending_tasks += 1
            elif state == "upstream_failed":
                concerns.append(
                    Concern(
                        level=ConcernLevel.WARNING,
                        category="upstream_failure",
                        message=f"Task '{task_id}' skipped due to upstream failure",
                        task_id=task_id,
                    )
                )
            elif state == "skipped":
                # Note skipped tasks
                concerns.append(
                    Concern(
                        level=ConcernLevel.INFO,
                        category="task_skipped",
                        message=f"Task '{task_id}' was skipped",
                        task_id=task_id,
                    )
                )

        # Calculate progress
        if report.total_tasks > 0:
            report.progress_percent = ((report.completed_tasks + report.failed_tasks) / report.total_tasks) * 100

    async def _detect_shadow_errors(
        self,
        dag_id: str,
        run_id: str,
        task_instances: List[Dict[str, Any]],
        concerns: List[Concern],
        recommendations: List[str],
    ) -> None:
        """
        Detect shadow errors - failures that don't cause task failure but indicate problems.

        These are errors in logs that might be missed if only checking task status.
        """
        for task in task_instances:
            task_id = task.get("task_id", "unknown")
            state = task.get("state", "unknown")

            # Check "successful" tasks for hidden errors
            if state == "success":
                logs = await self._get_task_logs(dag_id, run_id, task_id, task.get("try_number", 1))
                if logs:
                    shadow_errors = []
                    for pattern in self.deps.shadow_error_patterns:
                        if pattern.lower() in logs.lower():
                            # Find the actual line containing the error
                            for line in logs.split("\n"):
                                if pattern.lower() in line.lower():
                                    shadow_errors.append(line.strip()[:200])
                                    break

                    if shadow_errors:
                        concerns.append(
                            Concern(
                                level=ConcernLevel.WARNING,
                                category="shadow_error",
                                message=(f"Task '{task_id}' succeeded but contains error patterns in logs"),
                                task_id=task_id,
                                recommendation=(f"Review logs for '{task_id}' - may have non-fatal errors: {shadow_errors[0][:100]}..."),
                            )
                        )

    async def _get_lineage_data(self, dag_id: str, run_id: str, report: ObserverReport) -> None:
        """Get lineage data from Marquez if available."""
        if not self.marquez_api_url:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to find lineage run by job name
                job_name = f"{dag_id}"
                response = await client.get(
                    f"{self.marquez_api_url}/api/v1/namespaces/default/jobs/{job_name}/runs",
                    params={"limit": 5},
                )
                if response.status_code == 200:
                    data = response.json()
                    runs = data.get("runs", [])
                    if runs:
                        report.lineage_run_id = runs[0].get("id")
                        report.lineage_events = runs[:3]  # Last 3 events
        except Exception as e:
            logger.debug(f"Lineage query failed (Marquez may not be running): {e}")

    def _generate_summary(
        self,
        report: ObserverReport,
        concerns: List[Concern],
        recommendations: List[str],
    ) -> None:
        """Generate human-readable summary and recommendations."""

        # Build summary based on status
        if report.overall_status == ExecutionStatus.SUCCESS:
            report.summary = f"DAG '{report.dag_id}' completed successfully. {report.completed_tasks}/{report.total_tasks} tasks completed"
            if report.elapsed_seconds:
                report.summary += f" in {report.elapsed_seconds:.0f}s"

            recommendations.append("DAG execution successful - no action required")

            # Add timing recommendation if slow
            if report.elapsed_seconds and report.elapsed_seconds > 600:
                concerns.append(
                    Concern(
                        level=ConcernLevel.INFO,
                        category="performance",
                        message=f"DAG took {report.elapsed_seconds:.0f}s to complete",
                        recommendation="Consider optimizing long-running tasks",
                    )
                )

        elif report.overall_status == ExecutionStatus.FAILED:
            report.summary = f"DAG '{report.dag_id}' FAILED. {report.failed_tasks} task(s) failed out of {report.total_tasks}"

            # Add specific failure recommendations
            if report.failed_task_details:
                first_failure = report.failed_task_details[0]
                task_id = first_failure.get("task_id", "unknown")
                recommendations.append(f"Check logs for failed task '{task_id}' in Airflow UI")

                if first_failure.get("error_messages"):
                    error = first_failure["error_messages"][0][:100]
                    recommendations.append(f"First error: {error}")

            recommendations.append(f"View full logs: {self.airflow_api_url}/dags/{report.dag_id}/grid")

        elif report.overall_status == ExecutionStatus.RUNNING:
            report.summary = f"DAG '{report.dag_id}' is running. Progress: {report.progress_percent:.0f}% ({report.completed_tasks}/{report.total_tasks} tasks complete)"

            if report.running_tasks > 0:
                running = [tid for tid, state in report.task_statuses.items() if state == "running"]
                report.summary += f". Currently running: {', '.join(running[:3])}"

            recommendations.append("DAG execution in progress - monitoring")

        else:
            report.summary = f"DAG '{report.dag_id}' status: {report.overall_status.value}"

        # Build detailed message
        detail_parts = [report.summary]

        if report.failed_task_details:
            detail_parts.append("\nFailed tasks:")
            for failure in report.failed_task_details[:3]:
                detail_parts.append(f"  - {failure['task_id']}")
                if failure.get("error_messages"):
                    detail_parts.append(f"    Error: {failure['error_messages'][0][:100]}")

        if any(c.level in [ConcernLevel.WARNING, ConcernLevel.ERROR] for c in concerns):
            detail_parts.append("\nConcerns:")
            for concern in concerns:
                if concern.level in [ConcernLevel.WARNING, ConcernLevel.ERROR]:
                    detail_parts.append(f"  [{concern.level.value.upper()}] {concern.message}")

        report.detailed_message = "\n".join(detail_parts)

    def _finalize_report(
        self,
        report: ObserverReport,
        concerns: List[Concern],
        recommendations: List[str],
    ) -> None:
        """Finalize the report with concerns and recommendations."""
        # Convert concerns to dict format
        report.concerns = [
            {
                "level": c.level.value,
                "category": c.category,
                "message": c.message,
                "task_id": c.task_id,
                "recommendation": c.recommendation,
            }
            for c in concerns
        ]

        # Set concern flags
        report.has_warnings = any(c.level == ConcernLevel.WARNING for c in concerns)
        report.has_errors = any(c.level == ConcernLevel.ERROR for c in concerns)
        report.has_critical = any(c.level == ConcernLevel.CRITICAL for c in concerns)

        # Deduplicate recommendations
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        report.recommendations = unique_recommendations

        # Always add Airflow UI link
        if not any("View full" in r or "Airflow UI" in r for r in report.recommendations):
            report.recommendations.append(f"Airflow UI: {self.airflow_api_url}/dags/{report.dag_id}/grid")

    def _map_state(self, state: str) -> ExecutionStatus:
        """Map Airflow state to ExecutionStatus."""
        state_map = {
            "queued": ExecutionStatus.QUEUED,
            "running": ExecutionStatus.RUNNING,
            "success": ExecutionStatus.SUCCESS,
            "failed": ExecutionStatus.FAILED,
            "skipped": ExecutionStatus.SKIPPED,
            "up_for_retry": ExecutionStatus.UP_FOR_RETRY,
            "up_for_reschedule": ExecutionStatus.UP_FOR_RESCHEDULE,
            "upstream_failed": ExecutionStatus.UPSTREAM_FAILED,
        }
        return state_map.get(state.lower(), ExecutionStatus.UNKNOWN)

    def get_observation_history(self) -> List[ObserverReport]:
        """Get history of observations for pattern analysis."""
        return self._observation_history.copy()


# Create PydanticAI agent for structured observation
def create_observer_agent(
    model: Optional[str] = None,
) -> Agent[ObserverDependencies, ObserverReport]:
    """
    Create a PydanticAI Observer Agent for DAG monitoring.

    This agent provides structured observation and feedback.

    Args:
        model: Model identifier (e.g., google-gla:gemini-2.0-flash)

    Returns:
        Configured PydanticAI Agent
    """
    model = model or os.getenv("OBSERVER_MODEL", "google-gla:gemini-2.0-flash")

    agent = Agent(
        model,
        output_type=ObserverReport,
        deps_type=ObserverDependencies,
        system_prompt="""You are a Qubinode Lineage Observer Agent.

Your role is to monitor DAG executions and provide COMPREHENSIVE feedback.

CORE PRINCIPLE: Always report back with full status, regardless of pass/fail.

For EVERY observation, provide:
1. Overall status (running/success/failed/unknown)
2. Task-level progress and details
3. Any concerns - even minor ones
4. Recommendations for next steps
5. Links to relevant UIs for investigation

Shadow Error Detection:
- Check logs even for "successful" tasks
- Look for error patterns that didn't cause task failure
- Report warnings like "vault.yml not found" even if task continued

Never stay silent. Every observation should result in actionable feedback.
""",
    )

    return agent


# Singleton instance
_observer: Optional[LineageObserverAgent] = None


async def get_observer() -> LineageObserverAgent:
    """Get the singleton Lineage Observer Agent."""
    global _observer
    if _observer is None:
        _observer = LineageObserverAgent()
    return _observer


async def observe_dag_run(
    dag_id: str,
    run_id: str,
    check_logs: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to observe a DAG run.

    Args:
        dag_id: The DAG ID
        run_id: The run ID
        check_logs: Whether to check task logs

    Returns:
        Observation report as dict
    """
    observer = await get_observer()
    report = await observer.observe(dag_id, run_id, check_logs)

    return {
        "dag_id": report.dag_id,
        "run_id": report.run_id,
        "overall_status": report.overall_status.value,
        "is_complete": report.is_complete,
        "success": report.success,
        "progress_percent": report.progress_percent,
        "total_tasks": report.total_tasks,
        "completed_tasks": report.completed_tasks,
        "failed_tasks": report.failed_tasks,
        "running_tasks": report.running_tasks,
        "task_statuses": report.task_statuses,
        "failed_task_details": report.failed_task_details,
        "concerns": report.concerns,
        "has_warnings": report.has_warnings,
        "has_errors": report.has_errors,
        "recommendations": report.recommendations,
        "summary": report.summary,
        "detailed_message": report.detailed_message,
        "elapsed_seconds": report.elapsed_seconds,
        "airflow_ui_url": f"http://localhost:8888/dags/{dag_id}/grid",
    }
