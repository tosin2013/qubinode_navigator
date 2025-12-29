#!/usr/bin/env python3
"""
Health Monitor for Qubinode AI Assistant
Monitors system health and service status
"""

import asyncio
import logging
import time
import psutil
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors health of AI assistant components."""

    def __init__(self, ai_service=None, use_local_model: bool = False, pydanticai_available: bool = False):
        self.start_time = time.time()
        self.last_health_check = None
        self.health_status = "starting"
        self.ai_service = ai_service
        # When USE_LOCAL_MODEL=false, skip llama.cpp health checks
        self.use_local_model = use_local_model
        # PydanticAI orchestrator availability (required for smart pipeline)
        self.pydanticai_available = pydanticai_available

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        try:
            current_time = time.time()
            uptime = current_time - self.start_time

            # System metrics
            system_health = await self._check_system_health()

            # AI service health
            ai_health = await self._check_ai_service_health()

            # Overall status
            overall_status = "healthy"
            if not system_health["healthy"] or not ai_health["healthy"]:
                overall_status = "unhealthy"
            elif system_health.get("warnings") or ai_health.get("warnings"):
                overall_status = "degraded"

            health_data = {
                "status": overall_status,
                "timestamp": current_time,
                "uptime_seconds": uptime,
                "system": system_health,
                "ai_service": ai_health,
                "version": "1.0.0",
            }

            self.last_health_check = current_time
            self.health_status = overall_status

            return health_data

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "timestamp": time.time(), "error": str(e)}

    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system resource health."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # Load average (if available)
            load_avg = None
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                pass  # Not available on all systems

            # Determine health status
            healthy = True
            warnings = []

            if cpu_percent > 90:
                healthy = False
                warnings.append(f"High CPU usage: {cpu_percent}%")
            elif cpu_percent > 70:
                warnings.append(f"Elevated CPU usage: {cpu_percent}%")

            if memory_percent > 90:
                healthy = False
                warnings.append(f"High memory usage: {memory_percent}%")
            elif memory_percent > 70:
                warnings.append(f"Elevated memory usage: {memory_percent}%")

            if disk_percent > 90:
                healthy = False
                warnings.append(f"High disk usage: {disk_percent}%")
            elif disk_percent > 80:
                warnings.append(f"Elevated disk usage: {disk_percent}%")

            return {
                "healthy": healthy,
                "warnings": warnings,
                "metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk_percent,
                    "disk_free_gb": disk.free / (1024**3),
                    "load_average": load_avg,
                },
            }

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {"healthy": False, "error": str(e)}

    async def _check_ai_service_health(self) -> Dict[str, Any]:
        """Check AI service health."""
        try:
            # Check API responsiveness (always required)
            api_healthy = await self._check_api_responsiveness()

            # Check RAG service status (always required)
            rag_status = await self._check_rag_service()

            warnings = []

            # Only check llama.cpp components if USE_LOCAL_MODEL=true
            if self.use_local_model:
                # Check if llama.cpp server is responding
                llama_healthy = await self._check_llama_server()

                # Check model availability
                model_healthy = await self._check_model_availability()

                healthy = llama_healthy and model_healthy and api_healthy and self.pydanticai_available

                if not llama_healthy:
                    warnings.append("llama.cpp server not responding")

                if not model_healthy:
                    warnings.append("AI model not available")

                components = {
                    "llama_server": llama_healthy,
                    "model": model_healthy,
                    "api": api_healthy,
                    "rag_service": rag_status,
                    "orchestrator": self.pydanticai_available,
                    "mode": "local",
                }
            else:
                # Cloud-only mode: llama.cpp not required, but orchestrator IS required
                healthy = api_healthy and self.pydanticai_available
                components = {
                    "llama_server": "skipped (cloud-only mode)",
                    "model": "skipped (cloud-only mode)",
                    "api": api_healthy,
                    "rag_service": rag_status,
                    "orchestrator": self.pydanticai_available,
                    "mode": "cloud",
                }

            if not api_healthy:
                warnings.append("API not responsive")

            if not self.pydanticai_available:
                warnings.append("PydanticAI orchestrator not available - check pydantic-ai dependency")

            if not rag_status["available"]:
                warnings.append("RAG service not available")
            elif not rag_status["documents_loaded"]:
                warnings.append("RAG documents not loaded")

            return {
                "healthy": healthy,
                "warnings": warnings,
                "components": components,
            }

        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return {"healthy": False, "error": str(e)}

    async def _check_llama_server(self) -> bool:
        """Check if llama.cpp server is responding."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8081/health", timeout=5.0)
                return response.status_code == 200
        except Exception:
            # Try alternative endpoint
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8081/completion",
                        json={"prompt": "test", "max_tokens": 1},
                        timeout=5.0,
                    )
                    return response.status_code in [
                        200,
                        400,
                    ]  # 400 is also ok for health check
            except Exception:
                return False

    async def _check_model_availability(self) -> bool:
        """Check if AI model is available."""
        try:
            from pathlib import Path

            model_path = Path("/app/models/granite-4.0-micro.gguf")
            return model_path.exists() and model_path.stat().st_size > 0
        except Exception:
            return False

    async def _check_api_responsiveness(self) -> bool:
        """Check if main API is responsive."""
        try:
            # This is a self-check, so we'll just verify the service is running
            # In a real implementation, this might check response times
            return True
        except Exception:
            return False

    async def _check_rag_service(self) -> Dict[str, Any]:
        """Check RAG service status."""
        try:
            if self.ai_service and hasattr(self.ai_service, "rag_service") and self.ai_service.rag_service:
                return await self.ai_service.rag_service.get_health_status()
            else:
                return {
                    "available": False,
                    "initialized": False,
                    "documents_loaded": False,
                    "document_count": 0,
                    "embeddings_model": None,
                }
        except Exception as e:
            logger.error(f"RAG service health check failed: {e}")
            return {"available": False, "error": str(e)}

    def get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self.start_time

    def get_status(self) -> str:
        """Get current health status."""
        return self.health_status

    async def wait_for_healthy(self, timeout: float = 60.0) -> bool:
        """Wait for service to become healthy."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            health = await self.get_health_status()
            if health["status"] == "healthy":
                return True

            await asyncio.sleep(1.0)

        return False
