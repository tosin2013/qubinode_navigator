#!/usr/bin/env python3
"""
Shadow Error Detector - Detects Failures That Don't Immediately Crash

Implements ADR-0067 shadow error detection:
- Monitors DAG execution vs system state correlation
- Detects VM creation that succeeds syntactically but fails semantically
- Catches broken OpenLineage hooks (lineage missing despite success)
- Correlates Airflow task success with actual infrastructure changes
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ShadowError:
    """A failure that doesn't immediately manifest"""

    timestamp: datetime
    error_type: str  # "vm_not_created", "lineage_missing", "state_mismatch"
    severity: str  # "critical", "high", "medium", "low"
    description: str
    dag_id: str
    task_id: Optional[str] = None
    affected_resource: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)  # Data proving the error
    correlation_confidence: float = 0.0  # 0.0 to 1.0


@dataclass
class ExecutionRecord:
    """Record of a DAG or task execution"""

    execution_id: str
    dag_id: str
    task_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    state: str  # "running", "success", "failed"
    has_lineage: bool = False
    created_resources: List[str] = field(default_factory=list)
    expected_resources: List[str] = field(default_factory=list)


class ShadowErrorDetector:
    """
    Detects shadow errors - failures that don't immediately crash

    Correlates Airflow DAG execution with actual infrastructure state
    to find misalignments where the DAG succeeded but infrastructure failed.
    """

    def __init__(
        self,
        airflow_url: str = "http://localhost:8888",
        marquez_url: str = "http://localhost:5001",
        kcli_check_enabled: bool = True,
    ):
        """
        Initialize shadow error detector

        Args:
            airflow_url: URL to Airflow API
            marquez_url: URL to Marquez lineage API
            kcli_check_enabled: Whether to correlate with kcli VM state
        """
        self.airflow_url = airflow_url
        self.marquez_url = marquez_url
        self.kcli_check_enabled = kcli_check_enabled

        self.execution_records: Dict[str, ExecutionRecord] = {}
        self.shadow_errors: List[ShadowError] = []
        self.last_check_time = datetime.now() - timedelta(hours=1)

    async def scan_for_shadow_errors(self) -> List[ShadowError]:
        """
        Scan for shadow errors in recent executions

        Returns:
            List of detected shadow errors
        """
        logger.info("Scanning for shadow errors...")

        new_errors = []

        try:
            # Get recent DAG runs
            recent_dags = await self._get_recent_dag_runs()

            for dag_id, runs in recent_dags.items():
                for run in runs:
                    # Check each DAG run for shadow errors
                    errors = await self._analyze_dag_run(dag_id, run)
                    new_errors.extend(errors)

            self.shadow_errors.extend(new_errors)
            self.last_check_time = datetime.now()

            if new_errors:
                logger.warning(f"Detected {len(new_errors)} shadow errors")

            return new_errors

        except Exception as e:
            logger.error(f"Shadow error scanning failed: {e}")
            return []

    async def _get_recent_dag_runs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent DAG runs from Airflow"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Query Airflow REST API
                response = await client.get(
                    f"{self.airflow_url}/api/v1/dags",
                    params={"limit": 20},
                )
                response.raise_for_status()

                dags = response.json().get("dags", [])
                dag_runs = {}

                for dag in dags:
                    dag_id = dag.get("dag_id")
                    if dag_id:
                        # Get recent runs for this DAG
                        runs_response = await client.get(
                            f"{self.airflow_url}/api/v1/dags/{dag_id}/dagRuns",
                            params={"limit": 10, "order_by": "-execution_date"},
                        )
                        if runs_response.status_code == 200:
                            dag_runs[dag_id] = runs_response.json().get("dag_runs", [])

                return dag_runs

        except Exception as e:
            logger.error(f"Failed to get recent DAG runs: {e}")
            return {}

    async def _analyze_dag_run(self, dag_id: str, run: Dict[str, Any]) -> List[ShadowError]:
        """Analyze a single DAG run for shadow errors"""

        errors = []
        dag_run_id = run.get("dag_run_id", "unknown")
        state = run.get("state", "unknown")

        # Only analyze successful DAG runs (shadow errors occur in "success" runs)
        if state != "success":
            return errors

        logger.debug(f"Analyzing DAG run: {dag_id}/{dag_run_id}")

        try:
            # Check 1: Lineage presence
            lineage_error = await self._check_lineage_presence(dag_id, dag_run_id)
            if lineage_error:
                errors.append(lineage_error)

            # Check 2: Resource creation (VM deployment DAGs)
            resource_error = await self._check_resource_creation(dag_id, dag_run_id)
            if resource_error:
                errors.append(resource_error)

            # Check 3: State consistency
            consistency_error = await self._check_state_consistency(dag_id, dag_run_id)
            if consistency_error:
                errors.append(consistency_error)

        except Exception as e:
            logger.error(f"Error analyzing DAG run {dag_id}/{dag_run_id}: {e}")

        return errors

    async def _check_lineage_presence(self, dag_id: str, dag_run_id: str) -> Optional[ShadowError]:
        """Check if lineage was recorded for a successful DAG run"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Query Marquez lineage
                response = await client.get(
                    f"{self.marquez_url}/api/v1/namespaces/qubinode/jobs",
                )
                response.raise_for_status()

                jobs = response.json().get("jobs", [])

                # Check if any job matches this DAG
                matching_jobs = [j for j in jobs if dag_id in j.get("name", "").lower()]

                if not matching_jobs:
                    return ShadowError(
                        timestamp=datetime.now(),
                        error_type="lineage_missing",
                        severity="high",
                        description=f"No lineage recorded for {dag_id} despite successful DAG run",
                        dag_id=dag_id,
                        affected_resource="observability",
                        evidence={
                            "dag_run_id": dag_run_id,
                            "marquez_jobs_count": len(jobs),
                        },
                        correlation_confidence=0.8,
                    )

        except Exception as e:
            logger.debug(f"Lineage check failed for {dag_id}: {e}")

        return None

    async def _check_resource_creation(self, dag_id: str, dag_run_id: str) -> Optional[ShadowError]:
        """Check if expected resources were actually created"""

        # Only check VM creation DAGs
        vm_creation_dags = [
            "freeipa_deployment",
            "example_kcli_vm_provisioning",
            "ocp_agent_deployment",
        ]

        if not any(pattern in dag_id.lower() for pattern in vm_creation_dags):
            return None

        try:
            # Try to query kcli for VMs
            import subprocess
            import json

            result = subprocess.run(
                ["kcli", "list", "vm", "-o", "json"],
                capture_output=True,
                timeout=10,
                text=True,
            )

            if result.returncode != 0:
                # kcli command failed; can't verify resources
                return ShadowError(
                    timestamp=datetime.now(),
                    error_type="kcli_check_failed",
                    severity="medium",
                    description=f"Cannot verify resource creation for {dag_id}: kcli unreachable",
                    dag_id=dag_id,
                    affected_resource="kvm_hypervisor",
                    evidence={"kcli_error": result.stderr},
                    correlation_confidence=0.5,
                )

            vms = json.loads(result.stdout) if result.stdout else []
            vm_names = [vm.get("name") for vm in vms]

            # Extract expected VM name from DAG run or context
            expected_vm = self._extract_vm_name_from_dag(dag_id, dag_run_id)

            if expected_vm and expected_vm not in vm_names:
                return ShadowError(
                    timestamp=datetime.now(),
                    error_type="vm_not_created",
                    severity="critical",
                    description=f"DAG {dag_id} succeeded but VM {expected_vm} not found",
                    dag_id=dag_id,
                    task_id="vm_creation",
                    affected_resource=expected_vm,
                    evidence={
                        "expected_vm": expected_vm,
                        "existing_vms": vm_names,
                    },
                    correlation_confidence=0.95,
                )

        except subprocess.TimeoutExpired:
            logger.warning(f"kcli check timed out for {dag_id}")
        except Exception as e:
            logger.debug(f"Resource creation check failed for {dag_id}: {e}")

        return None

    async def _check_state_consistency(self, dag_id: str, dag_run_id: str) -> Optional[ShadowError]:
        """Check consistency between Airflow state and actual infrastructure"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get task instances for this run
                response = await client.get(
                    f"{self.airflow_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
                )
                response.raise_for_status()

                task_instances = response.json().get("task_instances", [])

                # Check for suspicious task execution patterns
                failed_tasks = [t for t in task_instances if t.get("state") == "failed"]

                # If we have failed tasks in a successful DAG run, that's a shadow error
                if failed_tasks:
                    return ShadowError(
                        timestamp=datetime.now(),
                        error_type="state_mismatch",
                        severity="high",
                        description=f"DAG {dag_id} marked success but contains failed tasks",
                        dag_id=dag_id,
                        evidence={
                            "failed_tasks": [t.get("task_id") for t in failed_tasks],
                            "total_tasks": len(task_instances),
                        },
                        correlation_confidence=0.9,
                    )

        except Exception as e:
            logger.debug(f"State consistency check failed for {dag_id}: {e}")

        return None

    def _extract_vm_name_from_dag(self, dag_id: str, dag_run_id: str) -> Optional[str]:
        """Extract VM name from DAG ID or run context"""

        # Pattern matching for known DAG types
        if "freeipa" in dag_id.lower():
            return "freeipa"

        if "ocp" in dag_id.lower():
            return "ocp-bootstrap"  # Common prefix for OCP VMs

        # Default: try to extract from DAG run context (would need to query Airflow)
        return None

    async def monitor_continuously(self, interval_seconds: int = 300) -> None:
        """
        Continuously monitor for shadow errors

        Args:
            interval_seconds: Check interval (default 5 minutes)
        """
        logger.info(f"Starting continuous shadow error monitoring (interval: {interval_seconds}s)")

        try:
            while True:
                await self.scan_for_shadow_errors()
                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info("Shadow error monitoring stopped")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")

    def get_recent_errors(self, limit: int = 10) -> List[ShadowError]:
        """Get recent shadow errors (newest first)"""
        sorted_errors = sorted(self.shadow_errors, key=lambda e: e.timestamp, reverse=True)
        return sorted_errors[:limit]

    def clear_errors(self, older_than_hours: int = 24) -> int:
        """Clear errors older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        before_count = len(self.shadow_errors)

        self.shadow_errors = [e for e in self.shadow_errors if e.timestamp > cutoff_time]

        removed_count = before_count - len(self.shadow_errors)
        logger.info(f"Cleared {removed_count} old shadow errors")

        return removed_count
