# ADR-0058: AI Assistant Integration Testing Approach

## Status

PROPOSED

## Date

2025-12-05

## Context

Integration tests verify that components work together correctly at service boundaries. For the AI Assistant, these boundaries include:

1. **llama.cpp Server** - HTTP API on port 8081 for inference
1. **Qdrant Vector DB** - Embedding storage and similarity search
1. **Marquez API** - OpenLineage data for infrastructure context
1. **System Services** - libvirtd, KVM modules, network interfaces
1. **External LLM APIs** - LiteLLM providers (OpenAI, Anthropic)

### Integration Points Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Assistant Application                         │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Integration Boundaries                     │  │
│  │                                                               │  │
│  │    ┌─────────────┐        ┌─────────────┐                    │  │
│  │    │ AIService   │◄──────►│  llama.cpp  │  HTTP POST         │  │
│  │    │             │        │  :8081      │  /completion       │  │
│  │    └──────┬──────┘        └─────────────┘                    │  │
│  │           │                                                   │  │
│  │    ┌──────▼──────┐        ┌─────────────┐                    │  │
│  │    │ RAGService  │◄──────►│   Qdrant    │  fastembed         │  │
│  │    │             │        │  (embedded) │  collection ops    │  │
│  │    └──────┬──────┘        └─────────────┘                    │  │
│  │           │                                                   │  │
│  │    ┌──────▼──────┐        ┌─────────────┐                    │  │
│  │    │ MarquezSvc  │◄──────►│  Marquez    │  REST API          │  │
│  │    │             │        │  :5001      │  /api/v1/jobs      │  │
│  │    └──────┬──────┘        └─────────────┘                    │  │
│  │           │                                                   │  │
│  │    ┌──────▼──────┐        ┌─────────────┐                    │  │
│  │    │ Diagnostics │◄──────►│  System     │  subprocess        │  │
│  │    │             │        │  (libvirt)  │  psutil, socket    │  │
│  │    └─────────────┘        └─────────────┘                    │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Current Test Gap Analysis

| Integration Point  | Current Tests   | Gap                             |
| ------------------ | --------------- | ------------------------------- |
| llama.cpp HTTP     | 0               | Need narrow integration tests   |
| Qdrant operations  | 5 (mocked)      | Need real embedded Qdrant tests |
| Marquez API        | 4 (mocked)      | Need contract tests             |
| System diagnostics | 12 (real)       | Good coverage                   |
| FastAPI endpoints  | 20 (TestClient) | Need auth/CORS tests            |

## Decision

### Integration Test Classification

We adopt **Narrow Integration Tests** as the primary strategy:

| Type       | Scope                         | When to Use              |
| ---------- | ----------------------------- | ------------------------ |
| **Narrow** | One integration point + mocks | Most integration tests   |
| **Broad**  | Multiple real dependencies    | Critical path validation |

### 1. llama.cpp Server Integration Tests

```python
# tests/integration/test_llm_integration.py

import pytest
from unittest.mock import patch, MagicMock
import httpx

@pytest.fixture
def mock_llama_server():
    """Mock llama.cpp server responses."""
    with patch("httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "This is a response about VM deployment.",
            "model": "granite-4.0-micro",
            "stop": True,
            "tokens_evaluated": 50,
            "tokens_predicted": 30,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        yield mock_post

class TestLlamaServerIntegration:
    """Integration tests for llama.cpp server communication."""

    def test_completion_request_format(self, mock_llama_server):
        """Verify request format matches llama.cpp API spec."""
        from ai_service import LlamaCppLLM

        llm = LlamaCppLLM(server_url="http://localhost:8081")
        llm._call("Test prompt", max_tokens=256, temperature=0.7)

        mock_llama_server.assert_called_once()
        call_args = mock_llama_server.call_args

        # Verify endpoint
        assert "/completion" in call_args[0][0]

        # Verify request body structure
        body = call_args[1]["json"]
        assert "prompt" in body
        assert "n_predict" in body or "max_tokens" in body
        assert "temperature" in body
        assert body["temperature"] == 0.7

    def test_completion_response_parsing(self, mock_llama_server):
        """Verify response is correctly parsed."""
        from ai_service import LlamaCppLLM

        llm = LlamaCppLLM(server_url="http://localhost:8081")
        result = llm._call("Test prompt")

        assert result == "This is a response about VM deployment."

    def test_server_unavailable_handling(self):
        """Test graceful handling when llama server is down."""
        from ai_service import LlamaCppLLM

        with patch("httpx.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            llm = LlamaCppLLM(server_url="http://localhost:8081")
            result = llm._call("Test prompt")

        assert "Error" in result or result == ""

    def test_timeout_handling(self):
        """Test handling of slow inference requests."""
        from ai_service import LlamaCppLLM

        with patch("httpx.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            llm = LlamaCppLLM(server_url="http://localhost:8081", timeout=5)
            result = llm._call("Long prompt that times out")

        assert "Error" in result or "timeout" in result.lower()
```

### 2. Qdrant RAG Integration Tests

````python
# tests/integration/test_rag_workflow.py

import pytest
from pathlib import Path
import tempfile
import shutil

@pytest.fixture
def rag_test_environment(tmp_path):
    """Set up isolated RAG test environment."""
    data_dir = tmp_path / "rag_data"
    data_dir.mkdir()

    # Create test documents
    docs_dir = data_dir / "docs"
    docs_dir.mkdir()

    (docs_dir / "vm-guide.md").write_text("""
    # VM Deployment Guide

    ## Using kcli

    To deploy a CentOS VM:
    ```bash
    kcli create vm centos9 -i centos9stream -P memory=4096 -P numcpus=2
    ```

    ## Troubleshooting

    If libvirt connection fails:
    1. Check service: systemctl status libvirtd
    2. Verify permissions: groups $USER
    """)

    yield {
        "data_dir": data_dir,
        "docs_dir": docs_dir,
    }

    # Cleanup
    shutil.rmtree(tmp_path, ignore_errors=True)

class TestQdrantRAGWorkflow:
    """Integration tests for Qdrant RAG operations."""

    @pytest.mark.asyncio
    async def test_document_ingestion_and_search(self, rag_test_environment):
        """Test full document ingestion and retrieval workflow."""
        from qdrant_rag_service import QdrantRAGService

        service = QdrantRAGService(
            data_dir=str(rag_test_environment["data_dir"]),
            collection_name="test_collection",
        )

        # Initialize service
        await service.initialize()
        assert service.is_initialized

        # Ingest documents
        docs_path = rag_test_environment["docs_dir"]
        await service.ingest_documents(str(docs_path))

        # Search for relevant content
        results = await service.search_documents(
            query="How to deploy a VM with kcli?",
            max_results=3,
        )

        # Verify results
        assert len(results) > 0
        assert any("kcli" in r.content.lower() for r in results)

    @pytest.mark.asyncio
    async def test_context_retrieval_format(self, rag_test_environment):
        """Test that context retrieval returns properly formatted data."""
        from qdrant_rag_service import QdrantRAGService

        service = QdrantRAGService(
            data_dir=str(rag_test_environment["data_dir"]),
        )
        await service.initialize()

        context, sources = await service.get_context_for_query(
            query="libvirt troubleshooting",
            max_length=1000,
        )

        # Verify context format
        assert isinstance(context, str)
        assert len(context) <= 1000
        assert isinstance(sources, list)

    @pytest.mark.asyncio
    async def test_empty_collection_handling(self, rag_test_environment):
        """Test behavior with empty document collection."""
        from qdrant_rag_service import QdrantRAGService

        service = QdrantRAGService(
            data_dir=str(rag_test_environment["data_dir"]),
            collection_name="empty_collection",
        )
        await service.initialize()

        results = await service.search_documents(query="any query")

        assert results == []
````

### 3. Marquez API Contract Tests

```python
# tests/integration/test_marquez_contract.py

import pytest
from unittest.mock import patch, AsyncMock
import httpx

@pytest.fixture
def mock_marquez_api():
    """Mock Marquez API responses matching OpenLineage spec."""

    async def mock_get(url, *args, **kwargs):
        response = AsyncMock()
        response.status_code = 200

        if "/api/v1/jobs" in url:
            response.json.return_value = {
                "jobs": [
                    {
                        "name": "freeipa_deployment",
                        "namespace": "qubinode",
                        "createdAt": "2025-01-15T10:30:00Z",
                        "updatedAt": "2025-01-15T11:00:00Z",
                        "latestRun": {
                            "state": "COMPLETED",
                            "startedAt": "2025-01-15T10:30:00Z",
                            "endedAt": "2025-01-15T10:45:00Z",
                        },
                    }
                ],
                "totalCount": 1,
            }
        elif "/api/v1/lineage" in url:
            response.json.return_value = {
                "graph": {
                    "nodes": [
                        {"id": "job:freeipa_deployment", "type": "JOB"},
                        {"id": "dataset:vm_inventory", "type": "DATASET"},
                    ],
                    "edges": [
                        {"source": "dataset:vm_inventory", "target": "job:freeipa_deployment"}
                    ],
                }
            }
        else:
            response.status_code = 404
            response.json.return_value = {"error": "Not found"}

        return response

    return mock_get

class TestMarquezContractCompliance:
    """Contract tests for Marquez API integration."""

    @pytest.mark.asyncio
    async def test_job_list_response_schema(self, mock_marquez_api):
        """Verify job list response matches expected schema."""
        from marquez_context_service import MarquezContextService

        with patch("httpx.AsyncClient.get", mock_marquez_api):
            service = MarquezContextService(base_url="http://localhost:5001")
            jobs = await service.list_jobs(namespace="qubinode")

        # Verify schema
        assert "jobs" in jobs or isinstance(jobs, list)
        if isinstance(jobs, dict) and "jobs" in jobs:
            job = jobs["jobs"][0]
            assert "name" in job
            assert "namespace" in job
            assert "latestRun" in job
            assert job["latestRun"]["state"] in ["COMPLETED", "FAILED", "RUNNING", "ABORTED"]

    @pytest.mark.asyncio
    async def test_context_generation_from_lineage(self, mock_marquez_api):
        """Test that lineage data is correctly transformed to prompt context."""
        from marquez_context_service import MarquezContextService

        with patch("httpx.AsyncClient.get", mock_marquez_api):
            service = MarquezContextService(base_url="http://localhost:5001")
            context = await service.get_context_for_prompt()

        # Verify context is meaningful for LLM
        assert isinstance(context, str)
        assert len(context) > 0
        # Should mention jobs or recent activity
        assert "freeipa" in context.lower() or "deployment" in context.lower()

    @pytest.mark.asyncio
    async def test_marquez_unavailable_fallback(self):
        """Test graceful degradation when Marquez is unavailable."""
        from marquez_context_service import MarquezContextService

        async def connection_error(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient.get", connection_error):
            service = MarquezContextService(base_url="http://localhost:5001")
            context = await service.get_context_for_prompt()

        # Should return empty or fallback, not raise
        assert context == "" or context is None
```

### 4. FastAPI Endpoint Integration Tests

```python
# tests/integration/test_api_endpoints.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.fixture
def test_client():
    """Create test client with mocked services."""
    from main import app

    # Reset global services
    import main
    main.ai_service = None
    main.health_monitor = None

    return TestClient(app)

@pytest.fixture
def test_client_with_service():
    """Create test client with initialized mock AI service."""
    from main import app
    import main

    mock_ai_service = MagicMock()
    mock_ai_service.process_message = AsyncMock(return_value={
        "text": "AI response about deployment",
        "metadata": {"model": "granite-4.0-micro", "rag_enabled": True},
    })
    mock_ai_service.get_model_info = MagicMock(return_value={
        "model_type": "granite-4.0-micro",
        "status": "loaded",
    })

    mock_health_monitor = MagicMock()
    mock_health_monitor.get_health_status = AsyncMock(return_value={
        "status": "healthy",
        "components": {"ai_service": "healthy", "rag_service": "healthy"},
    })

    main.ai_service = mock_ai_service
    main.health_monitor = mock_health_monitor

    return TestClient(app)

class TestAPIHealthEndpoints:
    """Integration tests for health check endpoints."""

    def test_health_endpoint_returns_status(self, test_client_with_service):
        """Test /health returns proper status."""
        response = test_client_with_service.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns welcome message."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Qubinode" in data["message"]

class TestAPIChatEndpoints:
    """Integration tests for chat endpoints."""

    def test_chat_endpoint_success(self, test_client_with_service):
        """Test /chat endpoint with valid request."""
        response = test_client_with_service.post(
            "/chat",
            json={"message": "How do I deploy a VM?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "text" in data

    def test_chat_endpoint_empty_message(self, test_client_with_service):
        """Test /chat rejects empty messages."""
        response = test_client_with_service.post(
            "/chat",
            json={"message": ""},
        )

        assert response.status_code in [400, 422]

    def test_chat_endpoint_no_service(self, test_client):
        """Test /chat when AI service not initialized."""
        response = test_client.post(
            "/chat",
            json={"message": "Test message"},
        )

        assert response.status_code == 503
        assert "not available" in response.json().get("detail", "").lower()

class TestAPIDiagnosticsEndpoints:
    """Integration tests for diagnostics endpoints."""

    def test_diagnostics_list_tools(self, test_client_with_service):
        """Test /diagnostics/tools returns available tools."""
        response = test_client_with_service.get("/diagnostics/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data or isinstance(data, dict)

    def test_diagnostics_run_specific_tool(self, test_client_with_service):
        """Test running specific diagnostic tool."""
        from main import ai_service

        ai_service.run_specific_diagnostic_tool = AsyncMock(return_value={
            "tool_result": {"success": True, "data": {"hostname": "test"}},
            "timestamp": "2025-01-15T10:00:00Z",
        })

        response = test_client_with_service.post(
            "/diagnostics/tool/system_info",
        )

        assert response.status_code == 200
```

### 5. Database Integration Test Patterns

```python
# tests/integration/conftest.py

import pytest
import tempfile
from pathlib import Path

@pytest.fixture(scope="session")
def integration_test_dir():
    """Create shared temp directory for integration tests."""
    temp_dir = tempfile.mkdtemp(prefix="ai_assistant_integration_")
    yield Path(temp_dir)
    # Cleanup after all tests
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def isolated_qdrant_db(integration_test_dir, request):
    """Create isolated Qdrant collection per test."""
    test_name = request.node.name
    db_path = integration_test_dir / f"qdrant_{test_name}"
    db_path.mkdir(exist_ok=True)

    yield {
        "path": str(db_path),
        "collection_name": f"test_{test_name}",
    }

    # Cleanup after test
    import shutil
    shutil.rmtree(db_path, ignore_errors=True)
```

## Consequences

### Positive

1. **Boundary Verification**: Catch integration issues at service boundaries
1. **Contract Compliance**: Ensure API responses match expected schemas
1. **Isolated Testing**: Each integration point tested independently
1. **Realistic Scenarios**: Test real workflows, not just units
1. **CI/CD Safety**: Prevent broken integrations from reaching production

### Negative

1. **Slower Execution**: Integration tests take 5-10x longer than unit tests
1. **Environment Complexity**: May need Docker/containers for dependencies
1. **Flakiness Risk**: Network/timing issues can cause intermittent failures
1. **Maintenance Overhead**: Mock data must track API changes

### Test Execution Strategy

```yaml
# Run integration tests separately in CI
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/unit/ -v

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests  # Only run if unit tests pass
    steps:
      - run: pytest tests/integration/ -v --tb=short
```

## Related ADRs

- [ADR-0056: AI Assistant Test Strategy Overview](adr-0056-ai-assistant-test-strategy-overview.md)
- [ADR-0057: Unit Testing Standards](adr-0057-ai-assistant-unit-testing-standards.md)
- [ADR-0059: End-to-End Testing Strategy](adr-0059-ai-assistant-e2e-testing-strategy.md)

## References

- [The Practical Test Pyramid - Integration Tests](https://martinfowler.com/articles/practical-test-pyramid.html#IntegrationTests)
- [Contract Testing with Pact](https://pact.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Qdrant Testing Best Practices](https://qdrant.tech/documentation/guides/testing/)
