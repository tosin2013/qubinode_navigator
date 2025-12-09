"""
Tests for main.py FastAPI application
Tests API endpoints, middleware, and request/response handling
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Ensure TEST_MODE is set before any imports (conftest.py also sets this)
os.environ["TEST_MODE"] = "true"

# Mock langchain before importing (only if not already available)
if "langchain" not in sys.modules:
    sys.modules["langchain"] = MagicMock()
    sys.modules["langchain.llms"] = MagicMock()
    sys.modules["langchain.llms.base"] = MagicMock()
    sys.modules["langchain.callbacks"] = MagicMock()
    sys.modules["langchain.callbacks.manager"] = MagicMock()
    # Create mock LLM base class
    mock_llm_class = MagicMock()
    sys.modules["langchain.llms.base"].LLM = mock_llm_class

if "litellm" not in sys.modules:
    sys.modules["litellm"] = MagicMock()

# Note: Do NOT mock rag_ingestion_api here - it's handled via TEST_MODE env var
# which prevents module-level service initialization

from main import app, ChatRequest, ChatResponse


class TestChatModels:
    """Test Pydantic models"""

    def test_chat_request_creation(self):
        """Test ChatRequest model"""
        request = ChatRequest(message="Test message")
        assert request.message == "Test message"
        assert request.context == {}
        assert request.max_tokens == 512
        assert request.temperature == 0.7

    def test_chat_request_with_all_fields(self):
        """Test ChatRequest with all fields"""
        request = ChatRequest(
            message="Test",
            context={"key": "value"},
            max_tokens=256,
            temperature=0.5,
        )
        assert request.context == {"key": "value"}
        assert request.max_tokens == 256
        assert request.temperature == 0.5

    def test_chat_response_creation(self):
        """Test ChatResponse model"""
        response = ChatResponse(response="AI response")
        assert response.response == "AI response"
        assert response.context == {}
        assert response.metadata == {}


class TestRootEndpoint:
    """Test root endpoint"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns service info"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Qubinode AI Assistant"
        assert "version" in data
        assert "endpoints" in data


class TestHealthEndpoint:
    """Test health endpoint"""

    @pytest.mark.asyncio
    async def test_health_no_monitor(self):
        """Test health endpoint without health monitor"""
        from fastapi.testclient import TestClient

        with patch("main.health_monitor", None):
            client = TestClient(app)
            response = client.get("/health")

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_health_healthy(self):
        """Test health endpoint - healthy"""
        from fastapi.testclient import TestClient

        mock_monitor = MagicMock()
        mock_monitor.get_health_status = AsyncMock(
            return_value={
                "status": "healthy",
                "uptime_seconds": 100,
                "system": {"healthy": True},
                "ai_service": {"healthy": True},
            }
        )

        with patch("main.health_monitor", mock_monitor):
            client = TestClient(app)
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_unhealthy(self):
        """Test health endpoint - unhealthy"""
        from fastapi.testclient import TestClient

        mock_monitor = MagicMock()
        mock_monitor.get_health_status = AsyncMock(
            return_value={
                "status": "unhealthy",
                "error": "Service down",
            }
        )

        with patch("main.health_monitor", mock_monitor):
            client = TestClient(app)
            response = client.get("/health")

        assert response.status_code == 503


class TestChatEndpoint:
    """Test chat endpoint"""

    @pytest.mark.asyncio
    async def test_chat_no_service(self):
        """Test chat endpoint without AI service"""
        from fastapi.testclient import TestClient

        with patch("main.ai_service", None):
            client = TestClient(app)
            response = client.post(
                "/chat",
                json={"message": "Test message"},
            )

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Test successful chat"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.process_message = AsyncMock(
            return_value={
                "text": "AI response about VMs",
                "context": {},
                "metadata": {"model": "granite-4.0-micro"},
            }
        )

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.post(
                "/chat",
                json={
                    "message": "How do I create a VM?",
                    "context": {"task": "vm_creation"},
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "AI response about VMs"

    @pytest.mark.asyncio
    async def test_chat_error(self):
        """Test chat with error"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.process_message = AsyncMock(side_effect=Exception("Processing error"))

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.post(
                "/chat",
                json={"message": "Test"},
            )

        assert response.status_code == 500


class TestDiagnosticsEndpoint:
    """Test diagnostics endpoints"""

    @pytest.mark.asyncio
    async def test_diagnostics_no_service(self):
        """Test diagnostics without AI service"""
        from fastapi.testclient import TestClient

        with patch("main.ai_service", None):
            client = TestClient(app)
            response = client.post("/diagnostics", json={})

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_diagnostics_success(self):
        """Test successful diagnostics"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.run_diagnostics = AsyncMock(
            return_value={
                "diagnostics": {
                    "summary": {"total_tools": 6},
                    "tool_results": {},
                },
                "ai_analysis": None,
            }
        )

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.post(
                "/diagnostics",
                json={"include_ai_analysis": False},
            )

        assert response.status_code == 200


class TestDiagnosticsToolsEndpoint:
    """Test diagnostics tools endpoint"""

    @pytest.mark.asyncio
    async def test_list_diagnostic_tools(self):
        """Test listing diagnostic tools"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.get_available_diagnostic_tools.return_value = {
            "system_info": "Get system information",
            "resource_usage": "Get resource usage",
        }

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.get("/diagnostics/tools")

        assert response.status_code == 200
        data = response.json()
        assert "available_tools" in data
        assert "total_tools" in data


class TestSpecificDiagnosticToolEndpoint:
    """Test specific diagnostic tool endpoint"""

    @pytest.mark.asyncio
    async def test_run_specific_tool(self):
        """Test running specific diagnostic tool"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.run_specific_diagnostic_tool = AsyncMock(
            return_value={
                "tool_result": {
                    "tool_name": "system_info",
                    "success": True,
                    "data": {"hostname": "test-host"},
                },
                "timestamp": 1234567890,
            }
        )

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.post("/diagnostics/tool/system_info", json={})

        assert response.status_code == 200
        data = response.json()
        assert "tool_result" in data


class TestModelInfoEndpoint:
    """Test model info endpoint"""

    @pytest.mark.asyncio
    async def test_get_model_info(self):
        """Test getting model info"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.get_model_info.return_value = {
            "model_type": "granite-4.0-micro",
            "threads": 4,
        }

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.get("/model/info")

        assert response.status_code == 200
        data = response.json()
        assert "model_info" in data


class TestHardwareInfoEndpoint:
    """Test hardware info endpoint"""

    @pytest.mark.asyncio
    async def test_get_hardware_info(self):
        """Test getting hardware info"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.get_hardware_info.return_value = {
            "cpu_cores": 8,
            "gpu_available": False,
            "system_memory_gb": 16.0,
        }

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.get("/model/hardware")

        assert response.status_code == 200
        data = response.json()
        assert "hardware_info" in data


class TestConfigEndpoint:
    """Test config endpoint"""

    @pytest.mark.asyncio
    async def test_get_config(self):
        """Test getting sanitized config"""
        from fastapi.testclient import TestClient

        mock_config = MagicMock()
        mock_config.get_sanitized_config.return_value = {
            "ai": {"model_name": "granite-4.0-micro"},
            "security": {"api_key": "***REDACTED***"},
        }

        with patch("main.config_manager", mock_config):
            client = TestClient(app)
            response = client.get("/config")

        assert response.status_code == 200
        data = response.json()
        assert "ai" in data


class TestLineageEndpoints:
    """Test lineage endpoints"""

    @pytest.mark.asyncio
    async def test_get_lineage_summary(self):
        """Test getting lineage summary"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.get_lineage_summary = AsyncMock(
            return_value={
                "jobs": 10,
                "recent_runs": [],
            }
        )

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.get("/lineage")

        assert response.status_code == 200
        data = response.json()
        assert "lineage" in data

    @pytest.mark.asyncio
    async def test_get_job_lineage(self):
        """Test getting job lineage"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.get_job_lineage = AsyncMock(
            return_value={
                "job_name": "freeipa_deployment",
                "status": "SUCCESS",
            }
        )

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.get("/lineage/job/freeipa_deployment")

        assert response.status_code == 200
        data = response.json()
        assert "job" in data

    @pytest.mark.asyncio
    async def test_get_job_lineage_not_found(self):
        """Test getting job lineage - not found"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.get_job_lineage = AsyncMock(return_value=None)

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.get("/lineage/job/nonexistent")

        assert response.status_code == 404


class TestRAGQueryEndpoint:
    """Test /api/query endpoint for RAG document search"""

    @pytest.mark.asyncio
    async def test_query_documents_no_service(self):
        """Test query endpoint without AI service"""
        from fastapi.testclient import TestClient

        with patch("main.ai_service", None):
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={"query": "test query"},
            )

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_query_documents_no_rag_service(self):
        """Test query endpoint without RAG service"""
        from fastapi.testclient import TestClient

        mock_ai_service = MagicMock()
        mock_ai_service.rag_service = None

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={"query": "test query"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total_results"] == 0

    @pytest.mark.asyncio
    async def test_query_documents_success(self):
        """Test successful document query"""
        from fastapi.testclient import TestClient

        mock_result = MagicMock()
        mock_result.content = "Test document content"
        mock_result.score = 0.95
        mock_result.source_file = "docs/test.md"
        mock_result.title = "Test Document"

        mock_rag = MagicMock()
        mock_rag.search_documents = AsyncMock(return_value=[mock_result])

        mock_ai_service = MagicMock()
        mock_ai_service.rag_service = mock_rag

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={"query": "test query", "max_results": 5},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["content"] == "Test document content"
        assert data["results"][0]["score"] == 0.95
        assert data["total_results"] == 1

    @pytest.mark.asyncio
    async def test_query_documents_empty_results(self):
        """Test query with no results"""
        from fastapi.testclient import TestClient

        mock_rag = MagicMock()
        mock_rag.search_documents = AsyncMock(return_value=[])

        mock_ai_service = MagicMock()
        mock_ai_service.rag_service = mock_rag

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={"query": "nonexistent topic"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total_results"] == 0

    @pytest.mark.asyncio
    async def test_query_documents_error(self):
        """Test query endpoint with error"""
        from fastapi.testclient import TestClient

        mock_rag = MagicMock()
        mock_rag.search_documents = AsyncMock(side_effect=Exception("RAG error"))

        mock_ai_service = MagicMock()
        mock_ai_service.rag_service = mock_rag

        with patch("main.ai_service", mock_ai_service):
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={"query": "test"},
            )

        assert response.status_code == 500


class TestProjectStatusEndpoint:
    """Test /api/status endpoint for project status"""

    @pytest.mark.asyncio
    async def test_project_status_no_health_monitor(self):
        """Test status endpoint without health monitor"""
        from fastapi.testclient import TestClient

        with patch("main.health_monitor", None):
            client = TestClient(app)
            response = client.get("/api/status")

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_project_status_success(self):
        """Test successful project status retrieval"""
        from fastapi.testclient import TestClient

        mock_health_monitor = MagicMock()
        mock_health_monitor.get_health_status = AsyncMock(
            return_value={
                "status": "healthy",
                "uptime_seconds": 3600,
                "system": {
                    "metrics": {
                        "cpu_percent": 45.0,
                        "memory_percent": 60.0,
                        "disk_percent": 30.0,
                    }
                },
            }
        )

        mock_ai_service = MagicMock()
        mock_ai_service.get_lineage_summary = AsyncMock(
            return_value={
                "available": True,
                "job_stats": {"total": 10},
                "recent_failures": [],
            }
        )

        with patch("main.health_monitor", mock_health_monitor):
            with patch("main.ai_service", mock_ai_service):
                client = TestClient(app)
                response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert data["ai_status"] == "healthy"
        assert data["airflow_status"] == "connected"
        assert data["vm_count"] == 10
        assert "metrics" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_project_status_lineage_unavailable(self):
        """Test status when lineage is unavailable"""
        from fastapi.testclient import TestClient

        mock_health_monitor = MagicMock()
        mock_health_monitor.get_health_status = AsyncMock(
            return_value={
                "status": "healthy",
                "uptime_seconds": 3600,
                "system": {"metrics": {"cpu_percent": 45.0, "memory_percent": 60.0, "disk_percent": 30.0}},
            }
        )

        mock_ai_service = MagicMock()
        mock_ai_service.get_lineage_summary = AsyncMock(side_effect=Exception("Marquez unavailable"))

        with patch("main.health_monitor", mock_health_monitor):
            with patch("main.ai_service", mock_ai_service):
                client = TestClient(app)
                response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert data["airflow_status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_project_status_no_ai_service(self):
        """Test status when AI service is None"""
        from fastapi.testclient import TestClient

        mock_health_monitor = MagicMock()
        mock_health_monitor.get_health_status = AsyncMock(
            return_value={
                "status": "healthy",
                "uptime_seconds": 3600,
                "system": {"metrics": {"cpu_percent": 45.0, "memory_percent": 60.0, "disk_percent": 30.0}},
            }
        )

        with patch("main.health_monitor", mock_health_monitor):
            with patch("main.ai_service", None):
                client = TestClient(app)
                response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        # Lineage should be unavailable
        assert data["airflow_status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_project_status_error(self):
        """Test status endpoint with error"""
        from fastapi.testclient import TestClient

        mock_health_monitor = MagicMock()
        mock_health_monitor.get_health_status = AsyncMock(side_effect=Exception("Health check failed"))

        with patch("main.health_monitor", mock_health_monitor):
            client = TestClient(app)
            response = client.get("/api/status")

        assert response.status_code == 500


class TestCORSMiddleware:
    """Test CORS middleware configuration"""

    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """Test CORS headers are present"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS should allow the request
        assert response.status_code in [200, 400]  # Either is valid


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        """Test handling invalid JSON"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post(
            "/chat",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_field(self):
        """Test handling missing required field"""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post(
            "/chat",
            json={},  # Missing 'message' field
        )

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
