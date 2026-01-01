#!/usr/bin/env python3
"""
Marquez/OpenLineage Context Service for Qubinode AI Assistant
ADR-0049: Multi-Agent LLM Memory Architecture

This service queries Marquez to provide real-time lineage context
to the AI assistant, enabling smarter responses about:
- Recent DAG runs and their status
- Failed tasks and error patterns
- Infrastructure deployment history
- Data lineage relationships
"""

import logging
import os
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)


class MarquezContextService:
    """Service for querying Marquez lineage data to enrich AI context."""

    # Common host addresses to try when MARQUEZ_API_URL is not set
    # Order: explicit env var > host.containers.internal (podman/docker) > localhost
    DEFAULT_HOSTS = [
        "host.containers.internal",  # Podman/Docker host access
        "host.docker.internal",  # Docker Desktop host access
        "172.17.0.1",  # Default Docker bridge gateway
        "localhost",  # Local development
    ]

    def __init__(self, marquez_url: str = None):
        self.marquez_url = marquez_url or os.getenv("MARQUEZ_API_URL")
        self.namespace = os.getenv("OPENLINEAGE_NAMESPACE", "qubinode")
        self.client = httpx.AsyncClient(timeout=10.0)
        self._cache = {}
        self._cache_ttl = 60  # Cache for 60 seconds
        self._discovered_url = None

    async def _discover_marquez_url(self) -> Optional[str]:
        """Try to discover Marquez URL by testing multiple host options."""
        if self._discovered_url:
            return self._discovered_url

        # If URL is explicitly set, use it
        if self.marquez_url:
            return self.marquez_url

        # Try each host in order
        for host in self.DEFAULT_HOSTS:
            test_url = f"http://{host}:5001"
            try:
                response = await self.client.get(f"{test_url}/api/v1/namespaces", timeout=3.0)
                if response.status_code == 200:
                    logger.info(f"Discovered Marquez at {test_url}")
                    self._discovered_url = test_url
                    self.marquez_url = test_url
                    return test_url
            except Exception:
                logger.debug(f"Marquez not available at {test_url}")
                continue

        logger.warning("Could not discover Marquez URL - tried all default hosts")
        return None

    async def is_available(self) -> bool:
        """Check if Marquez is available."""
        try:
            # Try to discover URL if not set
            url = await self._discover_marquez_url()
            if not url:
                return False

            response = await self.client.get(f"{url}/api/v1/namespaces")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Marquez not available: {e}")
            return False

    async def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent DAG/job runs from Marquez."""
        try:
            # Get all jobs in namespace
            response = await self.client.get(
                f"{self.marquez_url}/api/v1/namespaces/{self.namespace}/jobs",
                params={"limit": 50},
            )
            if response.status_code != 200:
                return []

            jobs = response.json().get("jobs", [])
            runs = []

            for job in jobs[:limit]:
                job_name = job.get("name", "")
                # Get latest run for this job
                run_response = await self.client.get(
                    f"{self.marquez_url}/api/v1/namespaces/{self.namespace}/jobs/{job_name}/runs",
                    params={"limit": 1},
                )
                if run_response.status_code == 200:
                    job_runs = run_response.json().get("runs", [])
                    if job_runs:
                        run = job_runs[0]
                        runs.append(
                            {
                                "job_name": job_name,
                                "run_id": run.get("id"),
                                "state": run.get("state"),
                                "started_at": run.get("startedAt"),
                                "ended_at": run.get("endedAt"),
                                "duration_ms": run.get("durationMs"),
                            }
                        )

            # Sort by start time, most recent first
            runs.sort(key=lambda x: x.get("started_at") or "", reverse=True)
            return runs[:limit]

        except Exception as e:
            logger.error(f"Error getting recent runs: {e}")
            return []

    async def get_failed_runs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get failed runs from the last N hours."""
        try:
            runs = await self.get_recent_runs(limit=50)
            failed = [r for r in runs if r.get("state") in ["FAILED", "ABORTED"]]
            return failed
        except Exception as e:
            logger.error(f"Error getting failed runs: {e}")
            return []

    async def get_job_details(self, job_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific job."""
        try:
            response = await self.client.get(f"{self.marquez_url}/api/v1/namespaces/{self.namespace}/jobs/{job_name}")
            if response.status_code != 200:
                return None

            job = response.json()

            # Get recent runs
            runs_response = await self.client.get(
                f"{self.marquez_url}/api/v1/namespaces/{self.namespace}/jobs/{job_name}/runs",
                params={"limit": 5},
            )
            recent_runs = []
            if runs_response.status_code == 200:
                recent_runs = runs_response.json().get("runs", [])

            return {
                "name": job.get("name"),
                "description": job.get("description"),
                "inputs": [inp.get("name") for inp in job.get("inputs", [])],
                "outputs": [out.get("name") for out in job.get("outputs", [])],
                "latest_run": job.get("latestRun", {}),
                "recent_runs": [
                    {
                        "state": r.get("state"),
                        "started_at": r.get("startedAt"),
                        "duration_ms": r.get("durationMs"),
                    }
                    for r in recent_runs
                ],
                "tags": job.get("tags", []),
            }
        except Exception as e:
            logger.error(f"Error getting job details for {job_name}: {e}")
            return None

    async def get_lineage_summary(self) -> Dict[str, Any]:
        """Get a summary of lineage data for AI context."""
        try:
            available = await self.is_available()
            if not available:
                return {
                    "available": False,
                    "message": "Marquez lineage service is not available",
                }

            # Get namespace info
            await self.client.get(f"{self.marquez_url}/api/v1/namespaces/{self.namespace}")

            # Get jobs
            jobs_response = await self.client.get(
                f"{self.marquez_url}/api/v1/namespaces/{self.namespace}/jobs",
                params={"limit": 100},
            )

            jobs = []
            job_stats = {"total": 0, "running": 0, "completed": 0, "failed": 0}

            if jobs_response.status_code == 200:
                jobs = jobs_response.json().get("jobs", [])
                job_stats["total"] = len(jobs)

                for job in jobs:
                    latest_run = job.get("latestRun", {})
                    state = latest_run.get("state", "UNKNOWN")
                    if state == "RUNNING":
                        job_stats["running"] += 1
                    elif state == "COMPLETED":
                        job_stats["completed"] += 1
                    elif state in ["FAILED", "ABORTED"]:
                        job_stats["failed"] += 1

            # Get recent failures
            failed_runs = await self.get_failed_runs(hours=24)

            return {
                "available": True,
                "namespace": self.namespace,
                "job_stats": job_stats,
                "recent_failures": [
                    {
                        "job": r["job_name"],
                        "state": r["state"],
                        "when": r.get("started_at"),
                    }
                    for r in failed_runs[:5]
                ],
                "jobs": [
                    {
                        "name": j.get("name"),
                        "latest_state": j.get("latestRun", {}).get("state", "UNKNOWN"),
                    }
                    for j in jobs[:10]
                ],
            }
        except Exception as e:
            logger.error(f"Error getting lineage summary: {e}")
            return {"available": False, "error": str(e)}

    async def search_jobs(self, query: str) -> List[Dict[str, Any]]:
        """Search for jobs matching a query string."""
        try:
            response = await self.client.get(
                f"{self.marquez_url}/api/v1/namespaces/{self.namespace}/jobs",
                params={"limit": 100},
            )
            if response.status_code != 200:
                return []

            jobs = response.json().get("jobs", [])
            query_lower = query.lower()

            matches = []
            for job in jobs:
                name = job.get("name", "").lower()
                if query_lower in name:
                    matches.append(
                        {
                            "name": job.get("name"),
                            "latest_state": job.get("latestRun", {}).get("state"),
                            "description": job.get("description"),
                        }
                    )

            return matches
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return []

    async def get_context_for_prompt(self, user_message: str) -> str:
        """
        Generate lineage context to inject into AI prompts.
        This gives the AI awareness of current infrastructure state.
        """
        try:
            summary = await self.get_lineage_summary()

            if not summary.get("available"):
                return ""

            # Build context string
            context_parts = []

            context_parts.append("=== Infrastructure Lineage Context ===")

            # Job statistics
            stats = summary.get("job_stats", {})
            context_parts.append(f"DAG Status: {stats.get('total', 0)} total jobs, {stats.get('running', 0)} running, {stats.get('completed', 0)} completed, {stats.get('failed', 0)} failed")

            # Recent failures (important for troubleshooting)
            failures = summary.get("recent_failures", [])
            if failures:
                context_parts.append("\nRecent Failures (last 24h):")
                for f in failures:
                    context_parts.append(f"  - {f['job']}: {f['state']}")

            # Check if user is asking about a specific DAG
            user_lower = user_message.lower()
            keywords = ["freeipa", "dns", "vm", "deployment", "dag", "failed", "error"]

            for keyword in keywords:
                if keyword in user_lower:
                    # Search for relevant jobs
                    matches = await self.search_jobs(keyword)
                    if matches:
                        context_parts.append(f"\nRelevant DAGs for '{keyword}':")
                        for m in matches[:3]:
                            context_parts.append(f"  - {m['name']}: {m.get('latest_state', 'UNKNOWN')}")

            context_parts.append("=== End Lineage Context ===\n")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error generating prompt context: {e}")
            return ""

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_marquez_service: Optional[MarquezContextService] = None


def get_marquez_service() -> MarquezContextService:
    """Get or create the Marquez context service singleton."""
    global _marquez_service
    if _marquez_service is None:
        _marquez_service = MarquezContextService()
    return _marquez_service


async def create_marquez_service(marquez_url: str = None) -> MarquezContextService:
    """Create a new Marquez context service."""
    service = MarquezContextService(marquez_url)
    return service
