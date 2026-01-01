"""
Tests for main.py - Orchestrator Endpoints

Tests cover the /orchestrator/* endpoints for PydanticAI integration.
"""

import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Ensure TEST_MODE is set before any imports
os.environ["TEST_MODE"] = "true"

# Mock langchain before importing
if "langchain" not in sys.modules:
    sys.modules["langchain"] = MagicMock()
    sys.modules["langchain.llms"] = MagicMock()
    sys.modules["langchain.llms.base"] = MagicMock()
    sys.modules["langchain.callbacks"] = MagicMock()
    sys.modules["langchain.callbacks.manager"] = MagicMock()
    mock_llm_class = MagicMock()
    sys.modules["langchain.llms.base"].LLM = mock_llm_class

if "litellm" not in sys.modules:
    sys.modules["litellm"] = MagicMock()

from main import app
from fastapi.testclient import TestClient


class TestOrchestratorStatus:
    """Test /orchestrator/status endpoint."""

    def test_orchestrator_status_available(self):
        """Test orchestrator status when PydanticAI is available."""
        with patch("main.PYDANTICAI_AVAILABLE", True):
            with patch("main.get_agent_context", new_callable=AsyncMock) as mock_ctx:
                mock_ctx.return_value = MagicMock()
                mock_ctx.return_value.get_status.return_value = {"rag_available": True}

                client = TestClient(app)
                response = client.get("/orchestrator/status")

                assert response.status_code == 200
                data = response.json()
                assert data["available"] is True
                assert "timestamp" in data
                assert "models" in data

    def test_orchestrator_status_unavailable(self):
        """Test orchestrator status when PydanticAI is not available."""
        with patch("main.PYDANTICAI_AVAILABLE", False):
            client = TestClient(app)
            response = client.get("/orchestrator/status")

            assert response.status_code == 200
            data = response.json()
            assert data["available"] is False


class TestOrchestratorContext:
    """Test /orchestrator/context endpoints."""

    def test_get_context_no_agent(self):
        """Test getting context when agent context is unavailable."""
        with patch("main.get_agent_context", new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = None

            client = TestClient(app)
            response = client.get("/orchestrator/context")

            # Returns 200 with available=False when agent is not initialized
            assert response.status_code == 200
            data = response.json()
            assert data["available"] is False

    def test_get_context_success(self):
        """Test getting context successfully."""
        with patch("main.get_agent_context", new_callable=AsyncMock) as mock_ctx:
            mock_agent_ctx = MagicMock()
            mock_agent_ctx.get_status.return_value = {
                "rag_available": True,
                "lineage_available": True,
                "adrs_loaded": 50,
            }
            mock_ctx.return_value = mock_agent_ctx

            client = TestClient(app)
            response = client.get("/orchestrator/context")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_context_query_no_agent(self):
        """Test context query when agent is unavailable."""
        with patch("main.get_agent_context", new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = None

            client = TestClient(app)
            response = client.post(
                "/orchestrator/context/query",
                json={"query": "What is FreeIPA?"},
            )

            assert response.status_code == 503

    def test_context_query_success(self):
        """Test context query successfully."""
        with patch("main.get_agent_context", new_callable=AsyncMock) as mock_ctx:
            mock_agent_ctx = MagicMock()
            # Use get_context_for_task (the actual method name)
            mock_agent_ctx.get_context_for_task = AsyncMock(
                return_value={
                    "rag": {"documents": ["FreeIPA is an identity management system"]},
                    "lineage": {},
                }
            )
            mock_ctx.return_value = mock_agent_ctx

            client = TestClient(app)
            response = client.post(
                "/orchestrator/context/query",
                json={"query": "What is FreeIPA?"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "rag" in data


class TestOrchestratorDAGs:
    """Test /orchestrator/dags endpoints."""

    def test_list_dags_no_validator(self):
        """Test listing DAGs when validator is unavailable."""
        with patch("main.DAG_VALIDATOR_AVAILABLE", False):
            client = TestClient(app)
            response = client.get("/orchestrator/dags")

            assert response.status_code == 503

    def test_list_dags_success(self):
        """Test listing DAGs successfully."""
        mock_validator = MagicMock()
        mock_validator.discover_dags = AsyncMock(
            return_value=[
                MagicMock(
                    dag_id="freeipa_deployment",
                    description="Deploy FreeIPA",
                    tags=["infrastructure"],
                    file_path="/dags/freeipa.py",
                    schedule="@daily",
                    params={"vm_name": "freeipa"},
                )
            ]
        )

        with patch("main.DAG_VALIDATOR_AVAILABLE", True):
            with patch("main.get_dag_validator", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_validator

                client = TestClient(app)
                response = client.get("/orchestrator/dags")

                assert response.status_code == 200
                data = response.json()
                assert "dags" in data
                assert data["total"] >= 0

    def test_search_dags(self):
        """Test searching for DAGs."""
        with patch("main.DAG_VALIDATOR_AVAILABLE", True):
            with patch("main.find_or_create_dag", new_callable=AsyncMock) as mock_find:
                mock_find.return_value = {
                    "found": True,
                    "matching_dags": [],
                    "best_match": None,
                    "recommendation": "Use existing DAG",
                }

                client = TestClient(app)
                response = client.post(
                    "/orchestrator/dags/search",
                    json={"task_description": "deploy freeipa server"},
                )

                assert response.status_code == 200

    def test_validate_dag(self):
        """Test validating a specific DAG."""
        mock_validator = MagicMock()
        mock_validation = MagicMock()
        mock_validation.is_valid = True
        mock_validation.can_proceed = True
        mock_validation.overall_status = MagicMock(value="passed")
        mock_validation.checks = []
        mock_validation.user_actions = []
        mock_validation.error_summary = None
        mock_validator.validate_dag = AsyncMock(return_value=mock_validation)

        with patch("main.DAG_VALIDATOR_AVAILABLE", True):
            with patch("main.get_dag_validator", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_validator

                client = TestClient(app)
                response = client.post(
                    "/orchestrator/dags/validate",
                    json={"dag_id": "freeipa_deployment", "params": {}},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["is_valid"] is True


class TestOrchestratorProjects:
    """Test /orchestrator/projects endpoints."""

    def test_list_projects_no_registry(self):
        """Test listing projects when registry is unavailable."""
        with patch("main.PROJECT_REGISTRY_AVAILABLE", False):
            client = TestClient(app)
            response = client.get("/orchestrator/projects")

            assert response.status_code == 503

    def test_list_projects_success(self):
        """Test listing projects successfully."""
        mock_registry = MagicMock()
        mock_registry.list_projects.return_value = [
            MagicMock(
                name="freeipa",
                project_type="vm",
                description="FreeIPA server",
                dag_id="freeipa_deployment",
                default_params={},
                tags=["infrastructure"],
            ),
        ]

        with patch("main.PROJECT_REGISTRY_AVAILABLE", True):
            with patch("main.get_project_registry", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_registry

                client = TestClient(app)
                response = client.get("/orchestrator/projects")

                assert response.status_code == 200
                data = response.json()
                assert "projects" in data

    def test_get_project_not_found(self):
        """Test getting a project that doesn't exist."""
        mock_registry = MagicMock()
        mock_registry.get_project.return_value = None

        with patch("main.PROJECT_REGISTRY_AVAILABLE", True):
            with patch("main.get_project_registry", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_registry

                client = TestClient(app)
                response = client.get("/orchestrator/projects/nonexistent")

                assert response.status_code == 404

    def test_get_project_success(self):
        """Test getting a project successfully."""
        mock_registry = MagicMock()
        mock_project = MagicMock()
        mock_project.name = "freeipa"
        mock_project.project_type = "vm"
        mock_project.description = "FreeIPA server"
        mock_project.dag_id = "freeipa_deployment"
        mock_project.default_params = {"memory": 4096}
        mock_project.tags = ["infrastructure"]
        mock_registry.get_project.return_value = mock_project

        with patch("main.PROJECT_REGISTRY_AVAILABLE", True):
            with patch("main.get_project_registry", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_registry

                client = TestClient(app)
                response = client.get("/orchestrator/projects/freeipa")

                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "freeipa"


class TestOrchestratorExecute:
    """Test /orchestrator/execute endpoint."""

    def test_execute_no_orchestrator(self):
        """Test execute when orchestrator is unavailable."""
        with patch("main.SMART_PIPELINE_AVAILABLE", False):
            client = TestClient(app)
            response = client.post(
                "/orchestrator/execute",
                json={"dag_id": "freeipa_deployment", "params": {}},
            )

            assert response.status_code == 503

    def test_execute_success(self):
        """Test successful execution request."""
        mock_result = {
            "execution_id": "exec-123",
            "dag_id": "freeipa_deployment",
            "status": "running",
            "run_id": "run-456",
            "validation_passed": True,
            "user_actions": [],
        }

        with patch("main.SMART_PIPELINE_AVAILABLE", True):
            with patch("main.execute_smart_pipeline", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = mock_result

                client = TestClient(app)
                response = client.post(
                    "/orchestrator/execute",
                    json={"dag_id": "freeipa_deployment", "params": {"vm_name": "freeipa"}},
                )

                assert response.status_code == 200
                data = response.json()
                assert "execution_id" in data


class TestOrchestratorObserve:
    """Test /orchestrator/observe endpoints."""

    def test_observe_dag_run_unavailable(self):
        """Test observing when observer is unavailable."""
        with patch("main.OBSERVER_AVAILABLE", False):
            client = TestClient(app)
            response = client.get("/orchestrator/observe/freeipa_deployment/run-123")

            assert response.status_code == 503

    def test_observe_dag_run_success(self):
        """Test observing a DAG run."""
        mock_report = {
            "dag_id": "freeipa_deployment",
            "run_id": "run-123",
            "overall_status": "success",
            "is_complete": True,
            "success": True,
            "progress_percent": 100.0,
            "total_tasks": 3,
            "completed_tasks": 3,
            "failed_tasks": 0,
            "running_tasks": 0,
        }

        with patch("main.OBSERVER_AVAILABLE", True):
            with patch("main.observe_dag_run", new_callable=AsyncMock) as mock_observe:
                mock_observe.return_value = mock_report

                client = TestClient(app)
                response = client.get("/orchestrator/observe/freeipa_deployment/run-123")

                assert response.status_code == 200
                data = response.json()
                assert data["dag_id"] == "freeipa_deployment"

    def test_observe_post_unavailable(self):
        """Test POST observe when observer is unavailable."""
        with patch("main.OBSERVER_AVAILABLE", False):
            client = TestClient(app)
            response = client.post(
                "/orchestrator/observe",
                params={"dag_id": "test_dag"},
            )

            assert response.status_code == 503

    def test_observe_post_no_runs(self):
        """Test POST observe when no runs exist."""
        with patch("main.OBSERVER_AVAILABLE", True):
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"dag_runs": []}
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                client = TestClient(app)
                response = client.post(
                    "/orchestrator/observe",
                    params={"dag_id": "test_dag"},
                )

                # Returns pending status when no runs
                assert response.status_code == 200


class TestOrchestratorIntent:
    """Test /orchestrator/intent endpoint."""

    def test_intent_no_feedback_loop(self):
        """Test intent when feedback loop is unavailable."""
        with patch("main.FEEDBACK_LOOP_AVAILABLE", False):
            client = TestClient(app)
            response = client.post(
                "/orchestrator/intent",
                json={"intent": "Deploy FreeIPA server"},
            )

            assert response.status_code == 503

    def test_intent_success(self):
        """Test successful intent processing."""
        mock_result = {
            "flow_id": "flow-123",
            "user_intent": "Deploy FreeIPA",
            "status": "completed",
            "dag_id": "freeipa_deployment",
        }

        with patch("main.FEEDBACK_LOOP_AVAILABLE", True):
            with patch("main.execute_user_intent", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = mock_result

                client = TestClient(app)
                response = client.post(
                    "/orchestrator/intent",
                    json={
                        "intent": "Deploy FreeIPA server",
                        "auto_approve": True,
                        "auto_execute": True,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["flow_id"] == "flow-123"


class TestOrchestratorFlows:
    """Test /orchestrator/flows endpoint."""

    def test_get_flow_unavailable(self):
        """Test getting a flow when feedback loop unavailable."""
        with patch("main.FEEDBACK_LOOP_AVAILABLE", False):
            client = TestClient(app)
            response = client.get("/orchestrator/flows/test-flow")
            assert response.status_code == 503

    def test_get_flow_not_found(self):
        """Test getting a non-existent flow."""
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_flow_status.return_value = None

        with patch("main.FEEDBACK_LOOP_AVAILABLE", True):
            with patch("main.get_feedback_orchestrator", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_orchestrator

                client = TestClient(app)
                response = client.get("/orchestrator/flows/nonexistent-flow")
                assert response.status_code == 404

    def test_get_flow_success(self):
        """Test getting an existing flow."""
        mock_context = MagicMock()
        mock_context.flow_id = "flow-123"
        mock_context.user_intent = "Deploy FreeIPA"
        mock_context.current_step = MagicMock(value="dag_validation")
        mock_context.status = MagicMock(value="in_progress")
        mock_context.source_project = "freeipa"
        mock_context.dag_id = "freeipa_deployment"
        mock_context.dag_found = True
        mock_context.validation_result = None
        mock_context.execution_result = None
        mock_context.observation_report = None
        mock_context.user_actions = []
        mock_context.errors = []

        mock_orchestrator = MagicMock()
        mock_orchestrator.get_flow_status.return_value = mock_context

        with patch("main.FEEDBACK_LOOP_AVAILABLE", True):
            with patch("main.get_feedback_orchestrator", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_orchestrator

                client = TestClient(app)
                response = client.get("/orchestrator/flows/flow-123")
                assert response.status_code == 200
                data = response.json()
                assert data["flow_id"] == "flow-123"


class TestOrchestratorShadowErrors:
    """Test /orchestrator/shadow-errors endpoint."""

    def test_shadow_errors_unavailable(self):
        """Test shadow errors when query not available."""
        with patch("main.SHADOW_ERROR_QUERY_AVAILABLE", False):
            client = TestClient(app)
            response = client.get("/orchestrator/shadow-errors")
            assert response.status_code == 503

    def test_shadow_errors_success(self):
        """Test shadow errors when available."""
        mock_result = {
            "dag_id": None,
            "since_hours": 24,
            "shadow_errors": [],
            "error_count": 0,
            "recommendations": [],
        }

        with patch("main.SHADOW_ERROR_QUERY_AVAILABLE", True):
            with patch("main.query_shadow_errors_for_manager", new_callable=AsyncMock) as mock_query:
                mock_query.return_value = mock_result

                client = TestClient(app)
                response = client.get("/orchestrator/shadow-errors")
                assert response.status_code == 200


class TestBasicEndpoints:
    """Test basic health and root endpoints."""

    def test_health_endpoint_no_monitor(self):
        """Test /health endpoint when monitor is not available."""
        with patch("main.health_monitor", None):
            client = TestClient(app)
            response = client.get("/health")

            # Returns 503 when health monitor is not initialized
            assert response.status_code == 503

    def test_health_endpoint_healthy(self):
        """Test /health endpoint when healthy."""
        mock_monitor = MagicMock()
        mock_monitor.get_health_status = AsyncMock(
            return_value={
                "status": "healthy",
                "services": {"ai": "up", "rag": "up"},
            }
        )

        with patch("main.health_monitor", mock_monitor):
            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_health_endpoint_degraded(self):
        """Test /health endpoint when degraded (still 200)."""
        mock_monitor = MagicMock()
        mock_monitor.get_health_status = AsyncMock(
            return_value={
                "status": "degraded",
                "services": {"ai": "up", "rag": "down"},
            }
        )

        with patch("main.health_monitor", mock_monitor):
            client = TestClient(app)
            response = client.get("/health")

            # Degraded returns 200 (operational with warnings)
            assert response.status_code == 200

    def test_root_endpoint(self):
        """Test root endpoint returns API info."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data or "status" in data
