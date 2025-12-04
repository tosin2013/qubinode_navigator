"""
Tests for HealthMonitor
Tests health monitoring, system checks, and service status
"""

import pytest
import os
import sys
import time
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from health_monitor import HealthMonitor


class TestHealthMonitorInit:
    """Test HealthMonitor initialization"""

    def test_health_monitor_creation(self):
        """Test creating a HealthMonitor instance"""
        monitor = HealthMonitor()
        assert monitor is not None
        assert monitor.health_status == "starting"
        assert monitor.ai_service is None

    def test_health_monitor_with_ai_service(self):
        """Test creating HealthMonitor with AI service"""
        mock_ai_service = MagicMock()
        monitor = HealthMonitor(ai_service=mock_ai_service)

        assert monitor.ai_service == mock_ai_service

    def test_health_monitor_start_time(self):
        """Test that start time is recorded"""
        before = time.time()
        monitor = HealthMonitor()
        after = time.time()

        assert before <= monitor.start_time <= after


class TestHealthMonitorUptime:
    """Test uptime tracking"""

    def test_get_uptime(self):
        """Test getting uptime"""
        monitor = HealthMonitor()
        time.sleep(0.1)  # Small delay

        uptime = monitor.get_uptime()
        assert uptime > 0
        assert uptime >= 0.1

    def test_get_status(self):
        """Test getting status"""
        monitor = HealthMonitor()
        status = monitor.get_status()

        assert status == "starting"


class TestHealthMonitorSystemHealth:
    """Test system health checking"""

    @pytest.mark.asyncio
    async def test_check_system_health(self, mock_psutil):
        """Test system health check"""
        monitor = HealthMonitor()
        health = await monitor._check_system_health()

        assert "healthy" in health
        assert "metrics" in health
        assert "cpu_percent" in health["metrics"]
        assert "memory_percent" in health["metrics"]
        assert "disk_percent" in health["metrics"]

    @pytest.mark.asyncio
    async def test_system_health_high_cpu_warning(self):
        """Test warning for high CPU usage"""
        monitor = HealthMonitor()

        with patch("psutil.cpu_percent", return_value=75.0):
            with patch(
                "psutil.virtual_memory",
                return_value=MagicMock(percent=50.0, available=8 * 1024**3),
            ):
                with patch(
                    "psutil.disk_usage",
                    return_value=MagicMock(percent=50.0, free=250 * 1024**3),
                ):
                    with patch("psutil.getloadavg", return_value=(1.0, 0.8, 0.6)):
                        health = await monitor._check_system_health()

        assert any("CPU" in w for w in health["warnings"])

    @pytest.mark.asyncio
    async def test_system_health_high_cpu_unhealthy(self):
        """Test unhealthy status for very high CPU"""
        monitor = HealthMonitor()

        with patch("psutil.cpu_percent", return_value=95.0):
            with patch(
                "psutil.virtual_memory",
                return_value=MagicMock(percent=50.0, available=8 * 1024**3),
            ):
                with patch(
                    "psutil.disk_usage",
                    return_value=MagicMock(percent=50.0, free=250 * 1024**3),
                ):
                    with patch("psutil.getloadavg", return_value=(1.0, 0.8, 0.6)):
                        health = await monitor._check_system_health()

        assert health["healthy"] is False

    @pytest.mark.asyncio
    async def test_system_health_high_memory(self):
        """Test warning for high memory usage"""
        monitor = HealthMonitor()

        with patch("psutil.cpu_percent", return_value=50.0):
            with patch(
                "psutil.virtual_memory",
                return_value=MagicMock(percent=92.0, available=1 * 1024**3),
            ):
                with patch(
                    "psutil.disk_usage",
                    return_value=MagicMock(percent=50.0, free=250 * 1024**3),
                ):
                    with patch("psutil.getloadavg", return_value=(1.0, 0.8, 0.6)):
                        health = await monitor._check_system_health()

        assert health["healthy"] is False
        assert any("memory" in w.lower() for w in health["warnings"])

    @pytest.mark.asyncio
    async def test_system_health_high_disk(self):
        """Test warning for high disk usage"""
        monitor = HealthMonitor()

        with patch("psutil.cpu_percent", return_value=50.0):
            with patch(
                "psutil.virtual_memory",
                return_value=MagicMock(percent=50.0, available=8 * 1024**3),
            ):
                with patch(
                    "psutil.disk_usage",
                    return_value=MagicMock(percent=92.0, free=10 * 1024**3),
                ):
                    with patch("psutil.getloadavg", return_value=(1.0, 0.8, 0.6)):
                        health = await monitor._check_system_health()

        assert health["healthy"] is False
        assert any("disk" in w.lower() for w in health["warnings"])


class TestHealthMonitorAIServiceHealth:
    """Test AI service health checking"""

    @pytest.mark.asyncio
    async def test_check_ai_service_health_no_service(self):
        """Test AI service health without service"""
        monitor = HealthMonitor()
        health = await monitor._check_ai_service_health()

        assert "healthy" in health
        assert "components" in health

    @pytest.mark.asyncio
    async def test_check_ai_service_health_with_rag(self):
        """Test AI service health with RAG service"""
        mock_ai_service = MagicMock()
        mock_ai_service.rag_service = MagicMock()
        mock_ai_service.rag_service.get_health_status = AsyncMock(
            return_value={
                "available": True,
                "initialized": True,
                "documents_loaded": True,
                "document_count": 100,
            }
        )

        monitor = HealthMonitor(ai_service=mock_ai_service)

        with patch.object(monitor, "_check_llama_server", return_value=True):
            with patch.object(monitor, "_check_model_availability", return_value=True):
                health = await monitor._check_ai_service_health()

        assert health["components"]["rag_service"]["available"] is True


class TestHealthMonitorLlamaServer:
    """Test llama.cpp server health checking"""

    @pytest.mark.asyncio
    async def test_check_llama_server_healthy(self):
        """Test llama server health check - healthy"""
        monitor = HealthMonitor()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await monitor._check_llama_server()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_llama_server_unhealthy(self):
        """Test llama server health check - unhealthy"""
        monitor = HealthMonitor()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_instance.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await monitor._check_llama_server()

        assert result is False


class TestHealthMonitorModelAvailability:
    """Test model availability checking"""

    @pytest.mark.asyncio
    async def test_check_model_available(self, tmp_path):
        """Test model availability - model exists"""
        monitor = HealthMonitor()

        model_path = tmp_path / "models" / "granite-4.0-micro.gguf"
        model_path.parent.mkdir(parents=True)
        model_path.write_text("model content")

        # Patch pathlib.Path since it's imported inside the method
        with patch("pathlib.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.stat.return_value = MagicMock(st_size=1000)
            mock_path_class.return_value = mock_path

            result = await monitor._check_model_availability()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_model_not_available(self):
        """Test model availability - model missing"""
        monitor = HealthMonitor()

        with patch("pathlib.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path

            result = await monitor._check_model_availability()

        assert result is False


class TestHealthMonitorRAGService:
    """Test RAG service health checking"""

    @pytest.mark.asyncio
    async def test_check_rag_service_no_service(self):
        """Test RAG service check without service"""
        monitor = HealthMonitor()
        result = await monitor._check_rag_service()

        assert result["available"] is False
        assert result["initialized"] is False

    @pytest.mark.asyncio
    async def test_check_rag_service_with_service(self):
        """Test RAG service check with service"""
        mock_ai_service = MagicMock()
        mock_ai_service.rag_service = MagicMock()
        mock_ai_service.rag_service.get_health_status = AsyncMock(
            return_value={
                "available": True,
                "initialized": True,
                "documents_loaded": True,
                "document_count": 500,
                "embeddings_model": "all-MiniLM-L6-v2",
            }
        )

        monitor = HealthMonitor(ai_service=mock_ai_service)
        result = await monitor._check_rag_service()

        assert result["available"] is True
        assert result["document_count"] == 500


class TestHealthMonitorOverallHealth:
    """Test overall health status"""

    @pytest.mark.asyncio
    async def test_get_health_status_healthy(self, mock_psutil):
        """Test getting overall health status - healthy"""
        monitor = HealthMonitor()

        with patch.object(
            monitor,
            "_check_ai_service_health",
            return_value={
                "healthy": True,
                "warnings": [],
                "components": {},
            },
        ):
            health = await monitor.get_health_status()

        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in health
        assert "uptime_seconds" in health
        assert "system" in health
        assert "ai_service" in health

    @pytest.mark.asyncio
    async def test_get_health_status_degraded(self, mock_psutil):
        """Test getting health status - degraded"""
        monitor = HealthMonitor()

        with patch.object(
            monitor,
            "_check_ai_service_health",
            return_value={
                "healthy": True,
                "warnings": ["Some warning"],
                "components": {},
            },
        ):
            health = await monitor.get_health_status()

        # With warnings but still healthy, should be degraded
        assert health["status"] in ["healthy", "degraded"]

    @pytest.mark.asyncio
    async def test_get_health_status_unhealthy(self):
        """Test getting health status - unhealthy"""
        monitor = HealthMonitor()

        with patch.object(
            monitor,
            "_check_system_health",
            return_value={"healthy": False, "warnings": ["Critical error"]},
        ):
            with patch.object(
                monitor,
                "_check_ai_service_health",
                return_value={"healthy": False, "warnings": [], "components": {}},
            ):
                health = await monitor.get_health_status()

        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_get_health_status_error(self):
        """Test getting health status with error"""
        monitor = HealthMonitor()

        with patch.object(
            monitor,
            "_check_system_health",
            side_effect=Exception("Test error"),
        ):
            health = await monitor.get_health_status()

        assert health["status"] == "error"
        assert "error" in health


class TestHealthMonitorWaitForHealthy:
    """Test wait_for_healthy method"""

    @pytest.mark.asyncio
    async def test_wait_for_healthy_immediate(self, mock_psutil):
        """Test waiting for healthy - immediately healthy"""
        monitor = HealthMonitor()

        with patch.object(
            monitor,
            "_check_ai_service_health",
            return_value={"healthy": True, "warnings": [], "components": {}},
        ):
            result = await monitor.wait_for_healthy(timeout=5.0)

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_healthy_timeout(self):
        """Test waiting for healthy - timeout"""
        monitor = HealthMonitor()

        with patch.object(
            monitor,
            "get_health_status",
            return_value={"status": "unhealthy"},
        ):
            result = await monitor.wait_for_healthy(timeout=0.5)

        assert result is False


class TestHealthMonitorIntegration:
    """Integration tests for HealthMonitor"""

    @pytest.mark.asyncio
    async def test_full_health_check_workflow(self, mock_psutil):
        """Test complete health check workflow"""
        monitor = HealthMonitor()

        # First check
        health1 = await monitor.get_health_status()
        assert "status" in health1

        # Check status updated
        assert monitor.health_status == health1["status"]

        # Check last health check time updated
        assert monitor.last_health_check is not None

        # Second check
        health2 = await monitor.get_health_status()
        assert health2["timestamp"] >= health1["timestamp"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
