"""
OpenLineage Service for Qubinode Navigator
ADR-0049: Multi-Agent LLM Memory Architecture - Phase 4

Provides lineage tracking and querying capabilities using Marquez.
Enables understanding of data flow, job dependencies, and execution history.

Features:
- Query DAG/task lineage (upstream/downstream)
- Get failure blast radius (what's affected by a failure)
- Track dataset lineage (data flow)
- Custom code lineage facets

Usage:
    from qubinode.lineage_service import LineageService

    service = LineageService()
    lineage = await service.get_dag_lineage("freeipa_deployment")
    blast_radius = await service.get_failure_blast_radius("freeipa_deployment", "install_task")
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
MARQUEZ_API_URL = os.getenv("MARQUEZ_API_URL", "http://localhost:5001")
NAMESPACE = os.getenv("AIRFLOW__OPENLINEAGE__NAMESPACE", "qubinode")
LINEAGE_ENABLED = os.getenv("OPENLINEAGE_DISABLED", "true").lower() != "true"


class LineageService:
    """
    Service for querying and managing OpenLineage data via Marquez.

    Marquez is the reference implementation for OpenLineage and provides:
    - Job lineage (DAG task dependencies)
    - Dataset lineage (data flow)
    - Run history (execution tracking)
    - Custom facets (code lineage)
    """

    def __init__(self, api_url: Optional[str] = None, namespace: Optional[str] = None):
        """
        Initialize the LineageService.

        Args:
            api_url: Marquez API URL
            namespace: OpenLineage namespace
        """
        self.api_url = api_url or MARQUEZ_API_URL
        self.namespace = namespace or NAMESPACE
        self._client = None

        logger.info(f"LineageService initialized: {self.api_url}, namespace={self.namespace}")

    def _get_client(self):
        """Lazy load HTTP client."""
        if self._client is None:
            try:
                import httpx

                self._client = httpx.AsyncClient(base_url=self.api_url, timeout=30.0)
            except ImportError:
                logger.error("httpx not installed")
                raise
        return self._client

    async def is_available(self) -> bool:
        """Check if Marquez is available."""
        try:
            client = self._get_client()
            response = await client.get("/api/v1/namespaces")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Marquez not available: {e}")
            return False

    async def get_namespaces(self) -> List[Dict[str, Any]]:
        """Get all namespaces."""
        try:
            client = self._get_client()
            response = await client.get("/api/v1/namespaces")
            response.raise_for_status()
            return response.json().get("namespaces", [])
        except Exception as e:
            logger.error(f"Failed to get namespaces: {e}")
            return []

    async def get_jobs(self, namespace: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all jobs (DAGs/tasks) in a namespace.

        Args:
            namespace: Namespace to query (defaults to configured)
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries
        """
        ns = namespace or self.namespace
        try:
            client = self._get_client()
            response = await client.get(f"/api/v1/namespaces/{ns}/jobs", params={"limit": limit})
            response.raise_for_status()
            return response.json().get("jobs", [])
        except Exception as e:
            logger.error(f"Failed to get jobs: {e}")
            return []

    async def get_job(self, job_name: str, namespace: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific job.

        Args:
            job_name: Name of the job (DAG.task format)
            namespace: Namespace (defaults to configured)

        Returns:
            Job details dictionary or None
        """
        ns = namespace or self.namespace
        try:
            client = self._get_client()
            response = await client.get(f"/api/v1/namespaces/{ns}/jobs/{job_name}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get job {job_name}: {e}")
            return None

    async def get_dag_lineage(self, dag_id: str, depth: int = 5, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get lineage for a DAG (all tasks and their dependencies).

        Args:
            dag_id: DAG identifier
            depth: How deep to traverse lineage
            namespace: Namespace (defaults to configured)

        Returns:
            Lineage graph with upstream and downstream dependencies
        """
        ns = namespace or self.namespace

        try:
            # Get all jobs for this DAG
            jobs = await self.get_jobs(namespace=ns)
            dag_jobs = [j for j in jobs if j.get("name", "").startswith(f"{dag_id}.")]

            lineage = {
                "dag_id": dag_id,
                "namespace": ns,
                "tasks": [],
                "upstream_dags": set(),
                "downstream_dags": set(),
                "datasets": set(),
            }

            for job in dag_jobs:
                job_name = job.get("name", "")
                task_name = job_name.replace(f"{dag_id}.", "")

                # Get job details including inputs/outputs
                job_details = await self.get_job(job_name, namespace=ns)

                if job_details:
                    task_info = {
                        "name": task_name,
                        "job_name": job_name,
                        "inputs": job_details.get("inputs", []),
                        "outputs": job_details.get("outputs", []),
                        "latest_run": job_details.get("latestRun"),
                        "facets": job_details.get("facets", {}),
                    }
                    lineage["tasks"].append(task_info)

                    # Track datasets
                    for inp in job_details.get("inputs", []):
                        lineage["datasets"].add(inp.get("name", ""))
                    for out in job_details.get("outputs", []):
                        lineage["datasets"].add(out.get("name", ""))

            # Convert sets to lists for JSON serialization
            lineage["upstream_dags"] = list(lineage["upstream_dags"])
            lineage["downstream_dags"] = list(lineage["downstream_dags"])
            lineage["datasets"] = list(lineage["datasets"])

            return lineage

        except Exception as e:
            logger.error(f"Failed to get DAG lineage for {dag_id}: {e}")
            return {"dag_id": dag_id, "error": str(e)}

    async def get_failure_blast_radius(
        self,
        dag_id: str,
        task_id: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get the blast radius of a failure (what would be affected).

        This helps understand the impact of a task/DAG failure by
        identifying all downstream dependencies.

        Args:
            dag_id: DAG identifier
            task_id: Specific task (optional, analyzes entire DAG if not provided)
            namespace: Namespace (defaults to configured)

        Returns:
            Impact analysis dictionary
        """
        ns = namespace or self.namespace

        try:
            job_name = f"{dag_id}.{task_id}" if task_id else dag_id

            # Get downstream lineage
            client = self._get_client()

            # Query lineage API
            response = await client.get(
                "/api/v1/lineage",
                params={"nodeId": f"job:{ns}:{job_name}", "depth": 10},
            )

            if response.status_code != 200:
                # Lineage endpoint might not be available, fall back to job analysis
                return await self._analyze_blast_radius_fallback(dag_id, task_id, ns)

            lineage_data = response.json()

            # Analyze downstream impact
            downstream_jobs = []
            downstream_datasets = []

            for node in lineage_data.get("graph", []):
                if node.get("type") == "JOB":
                    downstream_jobs.append(node.get("id", ""))
                elif node.get("type") == "DATASET":
                    downstream_datasets.append(node.get("id", ""))

            return {
                "source": {"dag_id": dag_id, "task_id": task_id, "job_name": job_name},
                "impact": {
                    "downstream_jobs": downstream_jobs,
                    "downstream_datasets": downstream_datasets,
                    "job_count": len(downstream_jobs),
                    "dataset_count": len(downstream_datasets),
                },
                "severity": self._calculate_severity(len(downstream_jobs), len(downstream_datasets)),
                "recommendation": self._get_failure_recommendation(len(downstream_jobs)),
            }

        except Exception as e:
            logger.error(f"Failed to get blast radius: {e}")
            return {"error": str(e)}

    async def _analyze_blast_radius_fallback(self, dag_id: str, task_id: Optional[str], namespace: str) -> Dict[str, Any]:
        """Fallback blast radius analysis using job API."""
        jobs = await self.get_jobs(namespace=namespace)

        # Find jobs that might depend on this one
        potential_downstream = []
        for job in jobs:
            job_details = await self.get_job(job.get("name", ""), namespace=namespace)
            if job_details:
                for inp in job_details.get("inputs", []):
                    # Check if this job uses outputs from the failing job
                    if dag_id in inp.get("name", ""):
                        potential_downstream.append(job.get("name", ""))
                        break

        return {
            "source": {"dag_id": dag_id, "task_id": task_id},
            "impact": {
                "downstream_jobs": potential_downstream,
                "downstream_datasets": [],
                "job_count": len(potential_downstream),
                "dataset_count": 0,
            },
            "severity": self._calculate_severity(len(potential_downstream), 0),
            "recommendation": self._get_failure_recommendation(len(potential_downstream)),
            "note": "Analysis based on job API (lineage endpoint unavailable)",
        }

    def _calculate_severity(self, job_count: int, dataset_count: int) -> str:
        """Calculate severity of blast radius."""
        total_impact = job_count + dataset_count
        if total_impact == 0:
            return "none"
        elif total_impact < 3:
            return "low"
        elif total_impact < 10:
            return "medium"
        else:
            return "high"

    def _get_failure_recommendation(self, job_count: int) -> str:
        """Get recommendation based on blast radius."""
        if job_count == 0:
            return "No downstream dependencies - safe to retry or skip"
        elif job_count < 3:
            return "Limited impact - can retry with notification"
        elif job_count < 10:
            return "Moderate impact - notify team before retry"
        else:
            return "High impact - escalate before taking action"

    async def get_dataset_lineage(self, dataset_name: str, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get lineage for a specific dataset.

        Shows which jobs produce and consume this dataset.

        Args:
            dataset_name: Dataset identifier
            namespace: Namespace for the dataset

        Returns:
            Dataset lineage with producers and consumers
        """
        ns = namespace or self.namespace

        try:
            client = self._get_client()
            response = await client.get(f"/api/v1/namespaces/{ns}/datasets/{dataset_name}")
            response.raise_for_status()

            dataset = response.json()

            return {
                "name": dataset_name,
                "namespace": ns,
                "description": dataset.get("description", ""),
                "schema": dataset.get("fields", []),
                "producers": dataset.get("currentVersion", {}).get("run", {}).get("jobName", "unknown"),
                "tags": dataset.get("tags", []),
                "facets": dataset.get("facets", {}),
                "created_at": dataset.get("createdAt"),
                "updated_at": dataset.get("updatedAt"),
            }

        except Exception as e:
            logger.error(f"Failed to get dataset lineage for {dataset_name}: {e}")
            return {"name": dataset_name, "error": str(e)}

    async def get_recent_runs(self, job_name: str, namespace: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent runs for a job.

        Args:
            job_name: Job name (DAG.task format)
            namespace: Namespace
            limit: Maximum runs to return

        Returns:
            List of run details
        """
        ns = namespace or self.namespace

        try:
            client = self._get_client()
            response = await client.get(f"/api/v1/namespaces/{ns}/jobs/{job_name}/runs", params={"limit": limit})
            response.raise_for_status()

            runs = response.json().get("runs", [])

            return [
                {
                    "id": run.get("id"),
                    "state": run.get("state"),
                    "started_at": run.get("startedAt"),
                    "ended_at": run.get("endedAt"),
                    "duration_ms": run.get("durationMs"),
                    "facets": run.get("facets", {}),
                }
                for run in runs
            ]

        except Exception as e:
            logger.error(f"Failed to get runs for {job_name}: {e}")
            return []

    async def get_run_facets(self, run_id: str) -> Dict[str, Any]:
        """
        Get facets (custom metadata) for a specific run.

        This includes code lineage facets with git information.

        Args:
            run_id: Run identifier

        Returns:
            Facets dictionary
        """
        try:
            client = self._get_client()
            response = await client.get(f"/api/v1/runs/{run_id}")
            response.raise_for_status()

            run = response.json()
            return run.get("facets", {})

        except Exception as e:
            logger.error(f"Failed to get facets for run {run_id}: {e}")
            return {}

    async def emit_custom_facets(
        self,
        job_name: str,
        run_id: str,
        facets: Dict[str, Any],
        namespace: Optional[str] = None,
    ) -> bool:
        """
        Emit custom facets for a run.

        Used to add code lineage information to runs.

        Args:
            job_name: Job name
            run_id: Run identifier
            facets: Custom facets to emit
            namespace: Namespace

        Returns:
            True if successful
        """
        ns = namespace or self.namespace

        try:
            # Build OpenLineage event
            event = {
                "eventType": "COMPLETE",
                "eventTime": datetime.utcnow().isoformat() + "Z",
                "run": {"runId": run_id, "facets": facets},
                "job": {"namespace": ns, "name": job_name},
                "inputs": [],
                "outputs": [],
            }

            client = self._get_client()
            response = await client.post("/api/v1/lineage", json=event)
            response.raise_for_status()

            logger.info(f"Emitted custom facets for {job_name}:{run_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to emit facets: {e}")
            return False

    async def get_lineage_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about lineage data.

        Args:
            namespace: Namespace to query

        Returns:
            Statistics dictionary
        """
        ns = namespace or self.namespace

        try:
            jobs = await self.get_jobs(namespace=ns, limit=1000)

            # Collect stats
            total_jobs = len(jobs)
            running_jobs = sum(1 for j in jobs if j.get("latestRun", {}).get("state") == "RUNNING")
            failed_jobs = sum(1 for j in jobs if j.get("latestRun", {}).get("state") == "FAILED")

            # Get datasets
            client = self._get_client()
            datasets_response = await client.get(f"/api/v1/namespaces/{ns}/datasets", params={"limit": 1000})
            datasets = datasets_response.json().get("datasets", []) if datasets_response.status_code == 200 else []

            return {
                "namespace": ns,
                "jobs": {
                    "total": total_jobs,
                    "running": running_jobs,
                    "failed": failed_jobs,
                    "success_rate": (total_jobs - failed_jobs) / max(total_jobs, 1) * 100,
                },
                "datasets": {"total": len(datasets)},
                "available": True,
            }

        except Exception as e:
            logger.error(f"Failed to get lineage stats: {e}")
            return {"namespace": ns, "available": False, "error": str(e)}


# Singleton instance
_lineage_service: Optional[LineageService] = None


def get_lineage_service() -> LineageService:
    """Get or create the default LineageService singleton."""
    global _lineage_service
    if _lineage_service is None:
        _lineage_service = LineageService()
    return _lineage_service


__version__ = "1.0.0"
__all__ = ["LineageService", "get_lineage_service"]
