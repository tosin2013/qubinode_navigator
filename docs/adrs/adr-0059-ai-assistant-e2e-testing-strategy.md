# ADR-0059: AI Assistant End-to-End Testing Strategy

## Status

PROPOSED

## Date

2025-12-05

## Context

End-to-end (E2E) tests validate complete user workflows through the entire AI Assistant stack. These are the most expensive tests to write and maintain but provide the highest confidence that the system works as users expect.

### E2E Test Scope for AI Assistant

```
User Request                                                    User Response
     │                                                                ▲
     ▼                                                                │
┌────────────────────────────────────────────────────────────────────────┐
│                         E2E Test Boundary                              │
│                                                                        │
│   ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌─────────────┐   │
│   │ FastAPI  │───►│ AIService │───►│   RAG    │───►│  Response   │   │
│   │ Endpoint │    │           │    │  Context │    │  Generation │   │
│   └────┬─────┘    └─────┬─────┘    └────┬─────┘    └──────┬──────┘   │
│        │                │               │                  │          │
│        │          ┌─────▼─────┐   ┌─────▼─────┐            │          │
│        │          │  Marquez  │   │  Qdrant   │            │          │
│        │          │  Context  │   │  Vector   │            │          │
│        │          └───────────┘   └───────────┘            │          │
│        │                                                   │          │
│   ┌────▼─────────────────────────────────────────────────▼─────┐    │
│   │                  llama.cpp Server                            │    │
│   │                  (CPU Inference)                             │    │
│   └──────────────────────────────────────────────────────────────┘    │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### E2E Test Philosophy

Following the Practical Test Pyramid principles:

- **Few E2E tests**: Only 3-5% of total tests
- **Critical paths only**: Test the most important user journeys
- **High-value scenarios**: Focus on what breaks when it fails
- **Minimal, not exhaustive**: Unit/integration tests cover edge cases

## Decision

### Critical User Journeys to Test

We identify **5 critical E2E workflows**:

| Journey               | Priority | What Breaks If It Fails            |
| --------------------- | -------- | ---------------------------------- |
| Chat with RAG context | HIGH     | Users get no documentation context |
| Health check pipeline | HIGH     | Monitoring/alerting fails          |
| Diagnostic workflow   | MEDIUM   | Can't troubleshoot issues          |
| Model info retrieval  | MEDIUM   | Can't verify deployment            |
| Project status check  | LOW      | Dashboard incomplete               |

### E2E Test Implementation

```python
# tests/e2e/test_chat_workflow.py
"""
End-to-end tests for the chat workflow.

These tests verify the complete user journey from HTTP request
to AI-generated response, including RAG context retrieval.

Prerequisites:
- AI Assistant service running on localhost:8080
- llama.cpp server running on localhost:8081
- Qdrant vector DB initialized with test documents
"""

import pytest
import httpx
import os

# E2E tests require real services - skip if not available
E2E_ENABLED = os.getenv("E2E_TESTS_ENABLED", "false").lower() == "true"
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="E2E tests disabled. Set E2E_TESTS_ENABLED=true to run."
)

class TestChatWorkflowE2E:
    """
    E2E tests for the complete chat workflow.

    Test the critical path:
    User question → RAG retrieval → LLM inference → Response

    These tests require:
    1. AI Assistant running with model loaded
    2. RAG service with indexed documents
    3. Network access to localhost
    """

    @pytest.fixture(scope="class")
    def http_client(self):
        """Create HTTP client for E2E tests."""
        return httpx.Client(base_url=AI_SERVICE_URL, timeout=60.0)

    def test_health_check_before_chat(self, http_client):
        """
        Verify service is healthy before running chat tests.

        This acts as a guard - if health fails, subsequent tests
        will likely fail for the same reason.
        """
        response = http_client.get("/health")

        assert response.status_code == 200
        health = response.json()
        assert health["status"] in ["healthy", "degraded"]
        # Service must be at least degraded (not unhealthy) to proceed
        assert health["status"] != "unhealthy", (
            f"Service unhealthy: {health.get('components', {})}"
        )

    def test_chat_with_infrastructure_question(self, http_client):
        """
        Test complete chat flow with infrastructure-related question.

        This is the PRIMARY E2E test - validates the core value proposition:
        User asks about infrastructure → Gets contextual AI response
        """
        response = http_client.post(
            "/chat",
            json={
                "message": "How do I deploy a CentOS VM using kcli?",
                "max_tokens": 256,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Response must have text
        assert "response" in data or "text" in data
        response_text = data.get("response", data.get("text", ""))
        assert len(response_text) > 50, "Response too short - likely error"

        # Response should be relevant (mentions kcli or VM)
        response_lower = response_text.lower()
        assert any(term in response_lower for term in ["kcli", "vm", "virtual", "deploy"]), (
            f"Response not relevant to question: {response_text[:200]}"
        )

        # Metadata should indicate RAG was used
        metadata = data.get("metadata", {})
        # RAG should be enabled for infrastructure questions
        if "rag_enabled" in metadata:
            assert metadata["rag_enabled"] is True, "RAG should be enabled"

    def test_chat_response_time_acceptable(self, http_client):
        """
        Test that chat response time is acceptable for user experience.

        CPU inference is slow - but should still be < 30 seconds for
        typical queries. This catches performance regressions.
        """
        import time

        start = time.time()
        response = http_client.post(
            "/chat",
            json={
                "message": "What is libvirt?",
                "max_tokens": 128,  # Shorter response for speed test
            },
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 30, f"Response took {elapsed:.1f}s - too slow for UX"

    def test_chat_handles_long_context(self, http_client):
        """
        Test that chat can handle questions requiring extensive context.

        This validates RAG chunking and context window management.
        """
        response = http_client.post(
            "/chat",
            json={
                "message": (
                    "Explain the complete process for setting up a KVM "
                    "hypervisor on CentOS, including network bridging, "
                    "storage pools, and deploying VMs with kcli. Include "
                    "troubleshooting steps for common issues."
                ),
                "max_tokens": 512,
            },
        )

        assert response.status_code == 200
        data = response.json()
        response_text = data.get("response", data.get("text", ""))

        # Long response expected for comprehensive question
        assert len(response_text) > 200, "Response too short for comprehensive question"
```

### Health Check Pipeline E2E Test

```python
# tests/e2e/test_health_check_pipeline.py
"""
E2E tests for the health monitoring pipeline.

These tests verify that health checks correctly report system status
across all components - critical for monitoring and alerting.
"""

import pytest
import httpx
import os

E2E_ENABLED = os.getenv("E2E_TESTS_ENABLED", "false").lower() == "true"
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="E2E tests disabled. Set E2E_TESTS_ENABLED=true to run."
)

class TestHealthCheckPipelineE2E:
    """
    E2E tests for health monitoring.

    These tests verify the complete health check flow:
    /health → HealthMonitor → Component checks → Aggregated status
    """

    @pytest.fixture(scope="class")
    def http_client(self):
        return httpx.Client(base_url=AI_SERVICE_URL, timeout=30.0)

    def test_health_endpoint_returns_all_components(self, http_client):
        """
        Verify health endpoint returns status for all expected components.
        """
        response = http_client.get("/health")

        assert response.status_code == 200
        health = response.json()

        # Required top-level fields
        assert "status" in health
        assert "uptime" in health or "uptime_seconds" in health

        # Component breakdown
        if "components" in health:
            components = health["components"]
            # These components should always be reported
            expected_components = ["system", "ai_service"]
            for comp in expected_components:
                assert comp in components, f"Missing component: {comp}"

    def test_health_status_reflects_reality(self, http_client):
        """
        Verify health status accurately reflects component states.

        If all components healthy → status = healthy
        If any degraded → status = degraded
        If critical component unhealthy → status = unhealthy
        """
        response = http_client.get("/health")
        health = response.json()

        status = health["status"]
        components = health.get("components", {})

        # Verify consistency
        component_statuses = list(components.values())
        if all(s == "healthy" for s in component_statuses if isinstance(s, str)):
            assert status == "healthy", "All components healthy but status not healthy"
        elif any(s == "unhealthy" for s in component_statuses if isinstance(s, str)):
            assert status in ["unhealthy", "degraded"], (
                "Has unhealthy component but status is healthy"
            )

    def test_health_check_performance(self, http_client):
        """
        Health checks must be fast - they're called frequently by monitors.
        """
        import time

        times = []
        for _ in range(3):
            start = time.time()
            response = http_client.get("/health")
            elapsed = time.time() - start
            times.append(elapsed)
            assert response.status_code == 200

        avg_time = sum(times) / len(times)
        assert avg_time < 2.0, f"Health check too slow: {avg_time:.2f}s average"

    def test_health_endpoint_idempotent(self, http_client):
        """
        Multiple health checks should return consistent results.
        """
        results = []
        for _ in range(3):
            response = http_client.get("/health")
            results.append(response.json()["status"])

        # Status should be consistent (not flapping)
        assert len(set(results)) == 1, f"Health status inconsistent: {results}"
```

### Diagnostic Workflow E2E Test

```python
# tests/e2e/test_diagnostic_workflow.py
"""
E2E tests for the diagnostic workflow.

These tests verify that diagnostics correctly gather and report
system information for troubleshooting.
"""

import pytest
import httpx
import os

E2E_ENABLED = os.getenv("E2E_TESTS_ENABLED", "false").lower() == "true"
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="E2E tests disabled. Set E2E_TESTS_ENABLED=true to run."
)

class TestDiagnosticWorkflowE2E:
    """
    E2E tests for diagnostics.

    Verifies: User requests diagnostics → Tools execute → Results returned
    """

    @pytest.fixture(scope="class")
    def http_client(self):
        return httpx.Client(base_url=AI_SERVICE_URL, timeout=60.0)

    def test_list_available_diagnostic_tools(self, http_client):
        """
        Verify diagnostic tools list is accessible and populated.
        """
        response = http_client.get("/diagnostics/tools")

        assert response.status_code == 200
        data = response.json()

        # Should have multiple tools
        tools = data.get("tools", data)
        assert len(tools) >= 5, "Expected at least 5 diagnostic tools"

        # Expected tools should be present
        expected_tools = ["system_info", "resource_usage", "kvm_diagnostics"]
        for tool in expected_tools:
            assert tool in tools, f"Missing diagnostic tool: {tool}"

    def test_run_comprehensive_diagnostics(self, http_client):
        """
        Run full diagnostic suite and verify complete results.
        """
        response = http_client.post(
            "/diagnostics",
            json={"include_ai_analysis": False},  # Skip AI to speed up
        )

        assert response.status_code == 200
        data = response.json()

        # Should have diagnostics results
        assert "diagnostics" in data or "tool_results" in data
        results = data.get("diagnostics", data.get("tool_results", {}))

        # Key diagnostic data should be present
        if "system_info" in results:
            sys_info = results["system_info"]
            assert sys_info.get("success", True), "system_info failed"
            if "data" in sys_info:
                assert "hostname" in sys_info["data"]

    def test_run_specific_diagnostic_tool(self, http_client):
        """
        Run a specific diagnostic tool.
        """
        response = http_client.post("/diagnostics/tool/resource_usage")

        assert response.status_code == 200
        data = response.json()

        # Should have resource data
        result = data.get("tool_result", data)
        assert result.get("success", True) or "data" in result

        if "data" in result:
            assert "cpu" in result["data"] or "memory" in result["data"]
```

### E2E Test Infrastructure

```python
# tests/e2e/conftest.py
"""
E2E test configuration and fixtures.

These fixtures support E2E testing against running services.
"""

import pytest
import httpx
import os
import time

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")
E2E_STARTUP_TIMEOUT = int(os.getenv("E2E_STARTUP_TIMEOUT", "60"))

@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """
    Wait for all services to be ready before running E2E tests.

    This runs once at the start of the test session.
    """
    if os.getenv("E2E_TESTS_ENABLED", "false").lower() != "true":
        return  # Skip if E2E not enabled

    print(f"\nWaiting for AI service at {AI_SERVICE_URL}...")

    start = time.time()
    while time.time() - start < E2E_STARTUP_TIMEOUT:
        try:
            response = httpx.get(f"{AI_SERVICE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                health = response.json()
                if health.get("status") in ["healthy", "degraded"]:
                    print(f"Service ready (status: {health['status']})")
                    return
        except httpx.RequestError:
            pass

        time.sleep(2)

    pytest.fail(f"Service not ready after {E2E_STARTUP_TIMEOUT}s")

@pytest.fixture(scope="session")
def base_url():
    """Provide base URL for E2E tests."""
    return AI_SERVICE_URL

@pytest.fixture(scope="session")
def session_client():
    """Provide shared HTTP client for E2E session."""
    return httpx.Client(
        base_url=AI_SERVICE_URL,
        timeout=60.0,
        headers={"User-Agent": "AI-Assistant-E2E-Tests"},
    )
```

### CI/CD Integration

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  schedule:
    - cron: '0 0 * * *'  # Nightly
  workflow_dispatch:  # Manual trigger
  push:
    tags:
      - 'v*'  # On releases

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r ai-assistant/requirements.txt
          pip install pytest httpx

      - name: Download test model
        run: |
          # Download small model for testing
          wget -q -O /tmp/model.gguf \
            https://huggingface.co/bartowski/granite-3.3-2b-instruct-GGUF/resolve/main/granite-3.3-2b-instruct-Q4_K_M.gguf

      - name: Start AI service
        run: |
          cd ai-assistant
          python -m main &
          sleep 10
        env:
          AI_MODEL_PATH: /tmp/model.gguf

      - name: Run E2E tests
        run: |
          cd ai-assistant
          pytest tests/e2e/ -v --tb=short
        env:
          E2E_TESTS_ENABLED: true
          AI_SERVICE_URL: http://localhost:8080
```

## Consequences

### Positive

1. **User Confidence**: Validates complete user journeys work
1. **Release Safety**: Catch breaking changes before deployment
1. **Integration Verification**: Tests full stack interaction
1. **Documentation**: E2E tests document expected behavior
1. **Regression Detection**: Catch subtle interaction bugs

### Negative

1. **Slow Execution**: E2E tests take minutes, not seconds
1. **Flakiness Risk**: Network, timing, and state issues
1. **Environment Dependency**: Requires running services
1. **Maintenance Cost**: Must update when API changes
1. **Limited Coverage**: Can't test all edge cases

### Risk Mitigation

| Risk               | Mitigation                                                 |
| ------------------ | ---------------------------------------------------------- |
| Flaky tests        | Add retries, increase timeouts, check service health first |
| Slow feedback      | Run E2E nightly, unit/integration on every PR              |
| Environment issues | Use Docker Compose for consistent setup                    |
| Data dependencies  | Reset test data before each test suite                     |

## Related ADRs

- [ADR-0056: AI Assistant Test Strategy Overview](adr-0056-ai-assistant-test-strategy-overview.md)
- [ADR-0057: Unit Testing Standards](adr-0057-ai-assistant-unit-testing-standards.md)
- [ADR-0058: Integration Testing Approach](adr-0058-ai-assistant-integration-testing-approach.md)

## References

- [The Practical Test Pyramid - E2E Tests](https://martinfowler.com/articles/practical-test-pyramid.html#End-to-endTests)
- [Testing Microservices](https://martinfowler.com/articles/microservice-testing/)
- [Avoiding Flaky Tests](https://testing.googleblog.com/2020/12/test-flakiness-one-of-main-challenges.html)
