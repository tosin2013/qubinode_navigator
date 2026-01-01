"""
Tests for smart_pipeline.py - Smart Pipeline Orchestration

Tests cover:
- ModelRetry exception class
- DataQuality facets (DataQualityAssertion, ShadowErrorFacet)
- OpenLineageEmitter
- SmartPipelineOrchestrator initialization and execution
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test mode
os.environ["TEST_MODE"] = "true"

from smart_pipeline import (
    ModelRetry,
    DataQualityAssertion,
    ShadowErrorFacet,
    OpenLineageEmitter,
    SmartPipelineOrchestrator,
    SmartPipelineExecution,
    ExecutionStatus,
    UserAction,
    UserActionType,
)


class TestModelRetry:
    """Tests for ModelRetry exception class."""

    def test_model_retry_creation_defaults(self):
        """Test ModelRetry with default values."""
        retry = ModelRetry("Something went wrong")
        assert retry.message == "Something went wrong"
        assert retry.corrected_params == {}
        assert retry.fix_commands == []
        assert retry.retry_count == 0
        assert retry.max_retries == 2

    def test_model_retry_creation_with_params(self):
        """Test ModelRetry with custom parameters."""
        retry = ModelRetry(
            message="Validation failed",
            corrected_params={"vm_name": "freeipa-fixed"},
            fix_commands=["kcli delete vm freeipa", "kcli create vm freeipa-fixed"],
            retry_count=1,
            max_retries=3,
        )
        assert retry.message == "Validation failed"
        assert retry.corrected_params == {"vm_name": "freeipa-fixed"}
        assert len(retry.fix_commands) == 2
        assert retry.retry_count == 1
        assert retry.max_retries == 3

    def test_can_retry_true(self):
        """Test can_retry returns True when retries available."""
        retry = ModelRetry("Error", retry_count=0, max_retries=2)
        assert retry.can_retry is True

        retry = ModelRetry("Error", retry_count=1, max_retries=2)
        assert retry.can_retry is True

    def test_can_retry_false(self):
        """Test can_retry returns False when max retries reached."""
        retry = ModelRetry("Error", retry_count=2, max_retries=2)
        assert retry.can_retry is False

        retry = ModelRetry("Error", retry_count=3, max_retries=2)
        assert retry.can_retry is False

    def test_to_dict(self):
        """Test to_dict serialization."""
        retry = ModelRetry(
            message="Test error",
            corrected_params={"key": "value"},
            fix_commands=["cmd1"],
            retry_count=1,
            max_retries=3,
        )
        result = retry.to_dict()

        assert result["message"] == "Test error"
        assert result["corrected_params"] == {"key": "value"}
        assert result["fix_commands"] == ["cmd1"]
        assert result["retry_count"] == 1
        assert result["max_retries"] == 3
        assert result["can_retry"] is True


class TestDataQualityAssertion:
    """Tests for DataQualityAssertion dataclass."""

    def test_assertion_creation_minimal(self):
        """Test assertion with minimal fields."""
        assertion = DataQualityAssertion(
            assertion="vm_exists",
            success=True,
        )
        assert assertion.assertion == "vm_exists"
        assert assertion.success is True
        assert assertion.column is None
        assert assertion.details is None

    def test_assertion_creation_full(self):
        """Test assertion with all fields."""
        assertion = DataQualityAssertion(
            assertion="profile_valid",
            success=False,
            column="memory",
            details="Memory value exceeds available resources",
        )
        assert assertion.assertion == "profile_valid"
        assert assertion.success is False
        assert assertion.column == "memory"
        assert assertion.details == "Memory value exceeds available resources"


class TestShadowErrorFacet:
    """Tests for ShadowErrorFacet dataclass."""

    def test_shadow_error_facet_defaults(self):
        """Test ShadowErrorFacet with default values."""
        facet = ShadowErrorFacet()
        assert facet._producer == "qubinode-smart-pipeline"
        assert facet.expected_outcome is None
        assert facet.actual_outcome is None
        assert facet.outcome_validated is False
        assert facet.shadow_errors == []
        assert facet.retry_suggested is False
        assert facet.retry_params is None
        assert facet.fix_commands == []

    def test_shadow_error_facet_with_data(self):
        """Test ShadowErrorFacet with actual data."""
        facet = ShadowErrorFacet(
            expected_outcome="vm_running",
            actual_outcome="vm_failed",
            outcome_validated=True,
            shadow_errors=[{"type": "ssh_timeout", "message": "Connection refused"}],
            retry_suggested=True,
            retry_params={"timeout": 60},
            fix_commands=["systemctl restart sshd"],
        )
        assert facet.expected_outcome == "vm_running"
        assert facet.actual_outcome == "vm_failed"
        assert facet.outcome_validated is True
        assert len(facet.shadow_errors) == 1
        assert facet.retry_suggested is True

    def test_to_openlineage_format(self):
        """Test OpenLineage format conversion."""
        facet = ShadowErrorFacet(
            expected_outcome="success",
            actual_outcome="partial",
            outcome_validated=True,
            shadow_errors=[{"type": "warning", "message": "Slow network"}],
            retry_suggested=False,
            fix_commands=["check_network"],
        )
        result = facet.to_openlineage_format()

        assert "shadowErrors" in result
        shadow = result["shadowErrors"]
        assert shadow["_producer"] == "qubinode-smart-pipeline"
        assert shadow["outcomeValidation"]["expected"] == "success"
        assert shadow["outcomeValidation"]["actual"] == "partial"
        assert shadow["outcomeValidation"]["validated"] is True
        assert len(shadow["errors"]) == 1
        assert shadow["retrySuggested"] is False
        assert shadow["fixCommands"] == ["check_network"]


class TestOpenLineageEmitter:
    """Tests for OpenLineageEmitter class."""

    def test_emitter_initialization_defaults(self):
        """Test emitter with default values."""
        emitter = OpenLineageEmitter()
        assert emitter.namespace == "qubinode"
        assert "localhost:5001" in emitter.marquez_api_url

    def test_emitter_initialization_custom(self):
        """Test emitter with custom values."""
        emitter = OpenLineageEmitter(
            marquez_api_url="http://marquez:5000",
            namespace="custom-namespace",
        )
        assert emitter.marquez_api_url == "http://marquez:5000"
        assert emitter.namespace == "custom-namespace"

    @pytest.mark.asyncio
    async def test_emit_shadow_error_event_success(self):
        """Test emitting shadow error event successfully."""
        emitter = OpenLineageEmitter(marquez_api_url="http://test-marquez:5001")
        facet = ShadowErrorFacet(
            expected_outcome="vm_running",
            actual_outcome="vm_running",
            outcome_validated=True,
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await emitter.emit_shadow_error_event(
                dag_id="test_dag",
                run_id="run-123",
                facet=facet,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_emit_shadow_error_event_with_assertions(self):
        """Test emitting shadow error with data quality assertions."""
        emitter = OpenLineageEmitter()
        facet = ShadowErrorFacet(outcome_validated=True)
        assertions = [
            DataQualityAssertion(assertion="vm_exists", success=True),
            DataQualityAssertion(assertion="profile_valid", success=True),
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await emitter.emit_shadow_error_event(
                dag_id="test_dag",
                run_id="run-123",
                facet=facet,
                assertions=assertions,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_emit_shadow_error_event_failure(self):
        """Test emitting shadow error event when Marquez returns error."""
        emitter = OpenLineageEmitter()
        facet = ShadowErrorFacet()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await emitter.emit_shadow_error_event(
                dag_id="test_dag",
                run_id="run-123",
                facet=facet,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_query_shadow_errors(self):
        """Test querying shadow errors from Marquez."""
        emitter = OpenLineageEmitter()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"runs": []}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await emitter.query_shadow_errors(dag_id="test_dag")

            assert result == []


class TestSmartPipelineOrchestrator:
    """Tests for SmartPipelineOrchestrator class."""

    def test_orchestrator_initialization_defaults(self):
        """Test orchestrator with default values."""
        # Clear environment to test defaults
        with patch.dict(os.environ, {}, clear=True):
            orchestrator = SmartPipelineOrchestrator()
            # Should add /api/v1 to default URL
            assert orchestrator.airflow_api_url == "http://localhost:8888/api/v1"
            assert orchestrator.marquez_api_url == "http://localhost:5001/api/v1"
            assert orchestrator.airflow_user == "airflow"
            assert orchestrator.airflow_pass == "airflow"

    def test_orchestrator_initialization_with_env(self):
        """Test orchestrator reads from environment."""
        env_vars = {
            "AIRFLOW_API_URL": "http://airflow:8080",
            "MARQUEZ_API_URL": "http://marquez:5000",
            "AIRFLOW_USER": "admin",
            "AIRFLOW_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            orchestrator = SmartPipelineOrchestrator()
            # Should add /api/v1 since env doesn't include it
            assert orchestrator.airflow_api_url == "http://airflow:8080/api/v1"
            assert orchestrator.marquez_api_url == "http://marquez:5000/api/v1"
            assert orchestrator.airflow_user == "admin"
            assert orchestrator.airflow_pass == "secret"

    def test_orchestrator_initialization_api_v1_not_duplicated(self):
        """Test that /api/v1 is not duplicated if already present."""
        env_vars = {
            "AIRFLOW_API_URL": "http://airflow:8080/api/v1",
            "MARQUEZ_API_URL": "http://marquez:5000/api/v1",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            orchestrator = SmartPipelineOrchestrator()
            # Should NOT duplicate /api/v1
            assert orchestrator.airflow_api_url == "http://airflow:8080/api/v1"
            assert orchestrator.marquez_api_url == "http://marquez:5000/api/v1"
            # Verify no double /api/v1
            assert "/api/v1/api/v1" not in orchestrator.airflow_api_url
            assert "/api/v1/api/v1" not in orchestrator.marquez_api_url

    def test_orchestrator_initialization_explicit_urls(self):
        """Test orchestrator with explicit URL parameters."""
        orchestrator = SmartPipelineOrchestrator(
            airflow_api_url="http://custom-airflow:9000",
            marquez_api_url="http://custom-marquez:6000",
        )
        # Should add /api/v1
        assert orchestrator.airflow_api_url == "http://custom-airflow:9000/api/v1"
        assert orchestrator.marquez_api_url == "http://custom-marquez:6000/api/v1"

    def test_orchestrator_stores_executions(self):
        """Test that orchestrator maintains execution registry."""
        orchestrator = SmartPipelineOrchestrator()
        assert orchestrator._executions == {}

    @pytest.mark.asyncio
    async def test_execute_with_validation_creates_execution(self):
        """Test that execute_with_validation creates an execution record."""
        orchestrator = SmartPipelineOrchestrator()

        # Mock the internal methods
        with patch.object(orchestrator, "_validate_dag", new_callable=AsyncMock) as mock_validate:
            with patch.object(orchestrator, "_check_and_unpause_dag", new_callable=AsyncMock) as mock_unpause:
                with patch.object(orchestrator, "_trigger_dag", new_callable=AsyncMock) as mock_trigger:
                    mock_validate.return_value = {"can_proceed": True, "checks": []}
                    mock_unpause.return_value = (False, "Already unpaused")
                    mock_trigger.return_value = {
                        "success": True,
                        "run_id": "test-run-123",
                    }

                    execution = await orchestrator.execute_with_validation(
                        dag_id="test_dag",
                        params={"key": "value"},
                    )

                    assert execution.dag_id == "test_dag"
                    assert execution.params == {"key": "value"}
                    assert execution.execution_id.startswith("exec-")

    @pytest.mark.asyncio
    async def test_execute_with_validation_fails_on_invalid(self):
        """Test that execute_with_validation fails when validation fails."""
        orchestrator = SmartPipelineOrchestrator()

        with patch.object(orchestrator, "_validate_dag", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                "can_proceed": False,
                "checks": [{"name": "syntax", "status": "failed"}],
                "error_summary": "DAG has syntax errors",
            }

            execution = await orchestrator.execute_with_validation(
                dag_id="broken_dag",
                validate_first=True,
            )

            assert execution.status == ExecutionStatus.FAILED
            assert execution.validation_passed is False
            assert "syntax" in str(execution.error_message).lower() or execution.error_message


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all expected statuses are defined."""
        assert ExecutionStatus.PENDING
        assert ExecutionStatus.VALIDATING
        assert ExecutionStatus.RUNNING
        assert ExecutionStatus.SUCCESS
        assert ExecutionStatus.FAILED
        assert ExecutionStatus.CANCELLED

    def test_status_values(self):
        """Test status enum values."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.VALIDATING.value == "validating"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CANCELLED.value == "cancelled"


class TestUserActionType:
    """Tests for UserActionType enum."""

    def test_all_action_types_exist(self):
        """Test that all action types are defined."""
        assert UserActionType.MONITOR
        assert UserActionType.CANCEL
        assert UserActionType.RETRY
        assert UserActionType.SELF_FIX
        assert UserActionType.ESCALATE


class TestUserAction:
    """Tests for UserAction dataclass."""

    def test_user_action_creation(self):
        """Test UserAction creation."""
        action = UserAction(
            action_type=UserActionType.RETRY,
            description="Retry the failed execution with corrected parameters",
        )
        assert action.action_type == UserActionType.RETRY
        assert action.description == "Retry the failed execution with corrected parameters"
        assert action.command is None
        assert action.difficulty == "easy"

    def test_user_action_with_command(self):
        """Test UserAction with command."""
        action = UserAction(
            action_type=UserActionType.SELF_FIX,
            description="Apply the suggested fix",
            command="kcli restart vm freeipa",
            difficulty="moderate",
        )
        assert action.action_type == UserActionType.SELF_FIX
        assert action.command == "kcli restart vm freeipa"
        assert action.difficulty == "moderate"

    def test_user_action_with_api_endpoint(self):
        """Test UserAction with API endpoint."""
        action = UserAction(
            action_type=UserActionType.MONITOR,
            description="Monitor the execution",
            api_endpoint="/orchestrator/flows/123/status",
        )
        assert action.api_endpoint == "/orchestrator/flows/123/status"


class TestSmartPipelineExecution:
    """Tests for SmartPipelineExecution dataclass."""

    def test_execution_creation_minimal(self):
        """Test execution with minimal fields."""
        execution = SmartPipelineExecution(
            execution_id="exec-123",
            dag_id="test_dag",
        )
        assert execution.execution_id == "exec-123"
        assert execution.dag_id == "test_dag"
        assert execution.status == ExecutionStatus.PENDING
        assert execution.params == {}

    def test_execution_creation_full(self):
        """Test execution with all fields."""
        execution = SmartPipelineExecution(
            execution_id="exec-456",
            dag_id="freeipa_deployment",
            params={"vm_name": "freeipa"},
            status=ExecutionStatus.RUNNING,
            run_id="run-789",
            validation_passed=True,
        )
        assert execution.execution_id == "exec-456"
        assert execution.dag_id == "freeipa_deployment"
        assert execution.params == {"vm_name": "freeipa"}
        assert execution.status == ExecutionStatus.RUNNING
        assert execution.run_id == "run-789"
        assert execution.validation_passed is True

    def test_execution_with_user_actions(self):
        """Test execution with user actions."""
        actions = [
            UserAction(
                action_type=UserActionType.MONITOR,
                description="Check execution status",
            ),
            UserAction(
                action_type=UserActionType.CANCEL,
                description="Cancel execution",
            ),
        ]
        execution = SmartPipelineExecution(
            execution_id="exec-789",
            dag_id="test_dag",
            user_actions=actions,
        )
        assert len(execution.user_actions) == 2
        assert execution.user_actions[0].action_type == UserActionType.MONITOR
