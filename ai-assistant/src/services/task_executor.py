"""
Task Executor Service: Executes planned tasks via Developer Agent.

This service bridges the gap between Manager Agent (planning) and Developer Agent (execution),
implementing the three-tier architecture per ADR-0049.

Features:
- Executes planned tasks from SessionPlan
- Invokes Developer Agent for each task
- Logs the entire coding process to a reviewable file
- Handles escalations and confidence thresholds
- Returns comprehensive execution results

Per ADR-0063: PydanticAI Core Agent Orchestrator
Per ADR-0049: Multi-Agent LLM Memory Architecture
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel

# Import domain models
try:
    from ..models.domain import (
        SessionPlan,
        DeveloperTaskResult,
        CodeGenerationRequest,
        EscalationRequest,
        AgentRole,
    )
    from ..agents.developer import (
        create_developer_agent,
        DeveloperDependencies,
        execute_code_generation,
    )
except ImportError:
    from models.domain import (
        SessionPlan,
        DeveloperTaskResult,
        CodeGenerationRequest,
        EscalationRequest,
        AgentRole,
    )
    from agents.developer import (
        create_developer_agent,
        DeveloperDependencies,
        execute_code_generation,
    )

logger = logging.getLogger(__name__)

# Directory for execution logs
EXECUTION_LOGS_DIR = Path(os.getenv("EXECUTION_LOGS_DIR", "/tmp/qubinode-execution-logs"))
EXECUTION_LOGS_DIR.mkdir(parents=True, exist_ok=True)


class TaskExecutionLog(BaseModel):
    """Log entry for a single task execution."""

    task_index: int
    task_description: str
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    developer_result: Optional[Dict[str, Any]] = None
    escalation: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, in_progress, completed, failed, escalated
    error: Optional[str] = None


class ExecutionSessionLog(BaseModel):
    """Complete execution session log."""

    session_id: str
    started_at: str
    completed_at: Optional[str] = None
    plan: Dict[str, Any]
    task_logs: List[TaskExecutionLog] = []
    overall_status: str = "pending"
    overall_confidence: float = 0.0
    escalations: List[Dict[str, Any]] = []
    code_changes: List[Dict[str, Any]] = []
    summary: Optional[str] = None
    log_file_path: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result of task execution."""

    success: bool
    session_id: str
    tasks_executed: int
    tasks_succeeded: int
    tasks_failed: int
    tasks_escalated: int
    overall_confidence: float
    execution_log: ExecutionSessionLog
    log_file_path: str
    escalation_needed: bool = False
    escalation_requests: List[EscalationRequest] = []
    code_changes: List[Dict[str, Any]] = []
    summary: str


class TaskExecutor:
    """
    Executes planned tasks from Manager Agent via Developer Agent.

    This class implements the Manager -> Developer delegation pattern,
    with comprehensive logging for review.
    """

    def __init__(
        self,
        session_id: str,
        rag_service: Any = None,
        lineage_service: Any = None,
        working_directory: str = "/opt/qubinode_navigator",
    ):
        self.session_id = session_id
        self.rag_service = rag_service
        self.lineage_service = lineage_service
        self.working_directory = working_directory
        self.execution_log: Optional[ExecutionSessionLog] = None
        self.log_file_path: Optional[str] = None

    async def execute_plan(
        self,
        plan: SessionPlan,
        rag_context: List[str] = None,
        lineage_context: Dict[str, Any] = None,
    ) -> ExecutionResult:
        """
        Execute all tasks in a SessionPlan.

        Args:
            plan: SessionPlan from Manager Agent
            rag_context: RAG context from previous queries
            lineage_context: Lineage context from Marquez

        Returns:
            ExecutionResult with comprehensive execution details
        """
        rag_context = rag_context or []
        lineage_context = lineage_context or {}

        # Initialize execution log
        start_time = datetime.utcnow()
        self.execution_log = ExecutionSessionLog(
            session_id=self.session_id,
            started_at=start_time.isoformat(),
            plan=plan.model_dump() if hasattr(plan, "model_dump") else dict(plan),
            overall_status="in_progress",
        )

        # Create log file path
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file_path = str(EXECUTION_LOGS_DIR / f"execution_{self.session_id}_{timestamp}.json")
        self.execution_log.log_file_path = self.log_file_path

        self._write_log("=" * 80)
        self._write_log(f"EXECUTION SESSION STARTED: {self.session_id}")
        self._write_log(f"Time: {start_time.isoformat()}")
        self._write_log(f"User Intent: {plan.user_intent}")
        self._write_log(f"Planned Tasks: {len(plan.planned_tasks)}")
        self._write_log(f"Estimated Confidence: {plan.estimated_confidence:.2%}")
        self._write_log("=" * 80)

        # Track results
        tasks_succeeded = 0
        tasks_failed = 0
        tasks_escalated = 0
        escalation_requests = []
        code_changes = []
        confidence_scores = []

        # Execute each task
        for idx, task_description in enumerate(plan.planned_tasks):
            self._write_log(f"\n{'='*60}")
            self._write_log(f"TASK {idx + 1}/{len(plan.planned_tasks)}: {task_description}")
            self._write_log(f"{'='*60}")

            task_log = TaskExecutionLog(
                task_index=idx,
                task_description=task_description,
                started_at=datetime.utcnow().isoformat(),
                status="in_progress",
            )
            self.execution_log.task_logs.append(task_log)

            try:
                # Execute task via Developer Agent
                result = await self._execute_task(
                    task_description=task_description,
                    rag_context=rag_context,
                    lineage_context=lineage_context,
                    required_providers=plan.required_providers,
                )

                # Update task log
                task_log.completed_at = datetime.utcnow().isoformat()
                task_log.developer_result = result.model_dump() if hasattr(result, "model_dump") else dict(result)
                task_log.duration_ms = self._calculate_duration(task_log.started_at, task_log.completed_at)

                confidence_scores.append(result.confidence)

                if result.escalation_needed:
                    task_log.status = "escalated"
                    tasks_escalated += 1
                    escalation = await self._create_escalation(result, task_description)
                    task_log.escalation = escalation.model_dump() if hasattr(escalation, "model_dump") else dict(escalation)
                    escalation_requests.append(escalation)
                    self.execution_log.escalations.append(task_log.escalation)

                    self._write_log(f"[ESCALATED] Task requires escalation: {result.escalation_reason}")
                elif result.success:
                    task_log.status = "completed"
                    tasks_succeeded += 1

                    # Track code changes
                    if result.code_generation_mode in ["aider", "fallback_prompt"]:
                        change = {
                            "task": task_description,
                            "mode": result.code_generation_mode,
                            "result": result.aider_result if result.aider_result else None,
                            "fallback": result.fallback_prompt.model_dump() if result.fallback_prompt else None,
                        }
                        code_changes.append(change)
                        self.execution_log.code_changes.append(change)

                    self._write_log(f"[SUCCESS] Confidence: {result.confidence:.2%}")
                    self._write_log(f"Analysis: {result.task_analysis}")
                else:
                    task_log.status = "failed"
                    tasks_failed += 1
                    self._write_log("[FAILED] Task execution failed")

                # Log RAG sources used
                if result.rag_sources_used:
                    self._write_log(f"RAG Sources: {', '.join(result.rag_sources_used[:5])}")

                # Log code generation details
                if result.code_generation_mode != "none":
                    self._write_log(f"Code Generation Mode: {result.code_generation_mode}")
                    if result.aider_result:
                        self._write_log(f"Aider Result: {json.dumps(result.aider_result, indent=2)}")
                    if result.fallback_prompt:
                        self._write_log("Fallback Prompt Generated for Calling LLM")

            except Exception as e:
                task_log.completed_at = datetime.utcnow().isoformat()
                task_log.status = "failed"
                task_log.error = str(e)
                tasks_failed += 1

                self._write_log(f"[ERROR] Exception during task execution: {e}")
                logger.error(f"Task execution error: {e}", exc_info=True)

            # Save log after each task
            self._save_log()

        # Compute overall confidence
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Determine overall status
        if tasks_escalated > 0:
            overall_status = "escalated"
        elif tasks_failed > 0:
            overall_status = "partial_failure"
        elif tasks_succeeded == len(plan.planned_tasks):
            overall_status = "completed"
        else:
            overall_status = "unknown"

        # Update execution log
        end_time = datetime.utcnow()
        self.execution_log.completed_at = end_time.isoformat()
        self.execution_log.overall_status = overall_status
        self.execution_log.overall_confidence = overall_confidence

        # Generate summary
        summary = self._generate_summary(
            plan=plan,
            tasks_succeeded=tasks_succeeded,
            tasks_failed=tasks_failed,
            tasks_escalated=tasks_escalated,
            overall_confidence=overall_confidence,
            code_changes=code_changes,
        )
        self.execution_log.summary = summary

        self._write_log(f"\n{'='*80}")
        self._write_log("EXECUTION SESSION COMPLETED")
        self._write_log(f"{'='*80}")
        self._write_log(summary)

        # Final save
        self._save_log()

        return ExecutionResult(
            success=tasks_failed == 0 and tasks_escalated == 0,
            session_id=self.session_id,
            tasks_executed=len(plan.planned_tasks),
            tasks_succeeded=tasks_succeeded,
            tasks_failed=tasks_failed,
            tasks_escalated=tasks_escalated,
            overall_confidence=overall_confidence,
            execution_log=self.execution_log,
            log_file_path=self.log_file_path,
            escalation_needed=tasks_escalated > 0,
            escalation_requests=escalation_requests,
            code_changes=code_changes,
            summary=summary,
        )

    async def _execute_task(
        self,
        task_description: str,
        rag_context: List[str],
        lineage_context: Dict[str, Any],
        required_providers: List[str],
    ) -> DeveloperTaskResult:
        """
        Execute a single task via Developer Agent.

        Args:
            task_description: The task to execute
            rag_context: RAG context for the task
            lineage_context: Lineage context from Marquez
            required_providers: List of required Airflow providers

        Returns:
            DeveloperTaskResult from Developer Agent
        """
        self._write_log("\n[DEVELOPER AGENT] Creating Developer Agent...")

        # Create Developer Agent
        developer_agent = create_developer_agent()

        # Create dependencies with injected services
        deps = DeveloperDependencies(
            session_id=self.session_id,
            rag_service=self.rag_service,
            lineage_service=self.lineage_service,
            working_directory=self.working_directory,
            rag_context=rag_context,
            lineage_context=lineage_context,
        )

        # Build enhanced task message with context
        enhanced_task = f"""## Task:
{task_description}

## Available Context:
- RAG documents: {len(rag_context)} relevant documents
- Lineage data: {"Available" if lineage_context else "Not available"}
- Required providers: {', '.join(required_providers) if required_providers else 'None specified'}

## Instructions:
1. Analyze this task and determine what needs to be done
2. Query RAG for any additional documentation needed
3. Compute your confidence score
4. If code changes are needed, specify the mode (aider or fallback_prompt)
5. If confidence < 0.6 or you cannot complete this task, set escalation_needed=True
"""

        self._write_log("[DEVELOPER AGENT] Running Developer Agent with task...")
        self._write_log(f"Task Preview: {task_description[:200]}...")

        # Run Developer Agent
        result = await developer_agent.run(enhanced_task, deps=deps)
        dev_result: DeveloperTaskResult = result.output

        self._write_log("[DEVELOPER AGENT] Result received:")
        self._write_log(f"  - Success: {dev_result.success}")
        self._write_log(f"  - Confidence: {dev_result.confidence:.2%}")
        self._write_log(f"  - Code Generation Mode: {dev_result.code_generation_mode}")
        self._write_log(f"  - Escalation Needed: {dev_result.escalation_needed}")

        # Execute code generation if needed
        if dev_result.code_generation_mode in ["aider", "fallback_prompt"] and dev_result.success:
            self._write_log("\n[CODE GENERATION] Executing code generation...")

            code_request = CodeGenerationRequest(
                task_description=task_description,
                target_files=self._infer_target_files(task_description),
                rag_context=rag_context,
                lineage_context=lineage_context,
                working_directory=self.working_directory,
            )

            code_result = await execute_code_generation(code_request, deps)

            # Merge code generation result
            dev_result.aider_result = code_result.aider_result
            dev_result.fallback_prompt = code_result.fallback_prompt

            if code_result.escalation_needed:
                dev_result.escalation_needed = True
                dev_result.escalation_reason = code_result.escalation_reason

            self._write_log("[CODE GENERATION] Completed")

        return dev_result

    async def _create_escalation(
        self,
        result: DeveloperTaskResult,
        task_description: str,
    ) -> EscalationRequest:
        """Create an escalation request for the Calling LLM."""
        return EscalationRequest(
            trigger="confidence_deadlock" if result.confidence < 0.6 else "developer_escalation",
            context={
                "task": task_description,
                "confidence": result.confidence,
                "analysis": result.task_analysis,
                "rag_sources": result.rag_sources_used,
            },
            failed_attempts=0,
            last_error=result.escalation_reason,
            requested_action="Provide guidance or additional context for this task",
            agent_source=AgentRole.DEVELOPER,
        )

    def _infer_target_files(self, task_description: str) -> List[str]:
        """Infer target files from task description."""
        # Basic inference - could be enhanced with RAG
        files = []
        task_lower = task_description.lower()

        if "dag" in task_lower:
            files.append("airflow/dags/")
        if "plugin" in task_lower:
            files.append("plugins/")
        if "test" in task_lower:
            files.append("tests/")
        if "config" in task_lower:
            files.append("config/")

        return files or ["./"]

    def _calculate_duration(self, start: str, end: str) -> int:
        """Calculate duration in milliseconds."""
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            return int((end_dt - start_dt).total_seconds() * 1000)
        except Exception:
            return 0

    def _generate_summary(
        self,
        plan: SessionPlan,
        tasks_succeeded: int,
        tasks_failed: int,
        tasks_escalated: int,
        overall_confidence: float,
        code_changes: List[Dict[str, Any]],
    ) -> str:
        """Generate execution summary."""
        total = len(plan.planned_tasks)
        lines = [
            f"Execution Summary for Session: {self.session_id}",
            "",
            f"User Intent: {plan.user_intent}",
            "",
            "Task Execution:",
            f"  - Total Tasks: {total}",
            f"  - Succeeded: {tasks_succeeded}",
            f"  - Failed: {tasks_failed}",
            f"  - Escalated: {tasks_escalated}",
            "",
            f"Overall Confidence: {overall_confidence:.2%}",
            "",
        ]

        if code_changes:
            lines.append("Code Changes:")
            for change in code_changes:
                lines.append(f"  - {change.get('task', 'Unknown task')[:50]}...")
                lines.append(f"    Mode: {change.get('mode', 'unknown')}")

        if tasks_escalated > 0:
            lines.append("")
            lines.append("Escalations Required:")
            lines.append("  Review the execution log for escalation details.")

        lines.append("")
        lines.append(f"Full log available at: {self.log_file_path}")

        return "\n".join(lines)

    def _write_log(self, message: str):
        """Write message to log."""
        logger.info(message)
        # Also print to allow capture in execution log
        print(f"[{datetime.utcnow().isoformat()}] {message}")

    def _save_log(self):
        """Save execution log to file."""
        if self.execution_log and self.log_file_path:
            try:
                with open(self.log_file_path, "w") as f:
                    json.dump(
                        self.execution_log.model_dump() if hasattr(self.execution_log, "model_dump") else dict(self.execution_log),
                        f,
                        indent=2,
                        default=str,
                    )
            except Exception as e:
                logger.error(f"Failed to save execution log: {e}")


async def execute_session_plan(
    session_id: str,
    plan: SessionPlan,
    rag_service: Any = None,
    lineage_service: Any = None,
    rag_context: List[str] = None,
    lineage_context: Dict[str, Any] = None,
    working_directory: str = "/opt/qubinode_navigator",
) -> ExecutionResult:
    """
    Convenience function to execute a session plan.

    Args:
        session_id: Unique session identifier
        plan: SessionPlan from Manager Agent
        rag_service: Optional RAG service instance
        lineage_service: Optional lineage service instance
        rag_context: Pre-fetched RAG context
        lineage_context: Pre-fetched lineage context
        working_directory: Working directory for code changes

    Returns:
        ExecutionResult with comprehensive execution details
    """
    executor = TaskExecutor(
        session_id=session_id,
        rag_service=rag_service,
        lineage_service=lineage_service,
        working_directory=working_directory,
    )

    return await executor.execute_plan(
        plan=plan,
        rag_context=rag_context,
        lineage_context=lineage_context,
    )
