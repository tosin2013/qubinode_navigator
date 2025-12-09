"""
Unit tests for PydanticAI domain models.

Tests validation logic, confidence scoring, and model constraints
per ADR-0063 and ADR-0049.
"""

import pytest
from datetime import datetime

from src.models.domain import (
    # Enums
    DeploymentStatus,
    ConfidenceLevel,
    AgentRole,
    # Infrastructure Models
    VMConfig,
    ClusterSpec,
    DAGDefinition,
    # Agent Result Models
    RAGSource,
    DeploymentResult,
    TaskResult,
    SessionPlan,
    EscalationRequest,
    TroubleshootingAttempt,
    TroubleshootingQuery,
    # Code Generation Models
    CodeGenerationRequest,
    FallbackCodePrompt,
    DeveloperTaskResult,
)


class TestEnums:
    """Test enum definitions."""

    def test_deployment_status_values(self):
        """Verify all expected deployment status values exist."""
        assert DeploymentStatus.PENDING == "pending"
        assert DeploymentStatus.IN_PROGRESS == "in_progress"
        assert DeploymentStatus.SUCCESS == "success"
        assert DeploymentStatus.FAILED == "failed"
        assert DeploymentStatus.ROLLBACK == "rollback"
        assert DeploymentStatus.ESCALATED == "escalated"

    def test_confidence_level_values(self):
        """Verify confidence levels per ADR-0049 Policy 1."""
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"

    def test_agent_role_values(self):
        """Verify agent roles per ADR-0049."""
        assert AgentRole.CALLING_LLM == "calling_llm"
        assert AgentRole.MANAGER == "manager"
        assert AgentRole.DEVELOPER == "developer"


class TestVMConfig:
    """Test VM configuration validation."""

    def test_valid_vm_config(self):
        """Test creating a valid VM config."""
        config = VMConfig(
            name="test-vm",
            template="rhel9",
            cpus=4,
            memory_mb=8192,
            disk_gb=100,
        )
        assert config.name == "test-vm"
        assert config.template == "rhel9"
        assert config.cpus == 4
        assert config.memory_mb == 8192
        assert config.disk_gb == 100
        assert config.network == "default"  # Default value

    def test_vm_config_defaults(self):
        """Test default values are applied."""
        config = VMConfig(name="minimal-vm", template="centos9")
        assert config.cpus == 2
        assert config.memory_mb == 4096
        assert config.disk_gb == 50
        assert config.network == "default"

    def test_vm_config_invalid_name_uppercase(self):
        """Test that uppercase names are rejected."""
        with pytest.raises(ValueError):
            VMConfig(name="Test-VM", template="rhel9")

    def test_vm_config_invalid_name_starts_with_number(self):
        """Test that names starting with numbers are rejected."""
        with pytest.raises(ValueError):
            VMConfig(name="123-vm", template="rhel9")

    def test_vm_config_name_too_long(self):
        """Test that names > 63 chars are rejected."""
        long_name = "a" * 64
        with pytest.raises(ValueError) as exc_info:
            VMConfig(name=long_name, template="rhel9")
        assert "63 characters" in str(exc_info.value)

    def test_vm_config_invalid_cpu_range(self):
        """Test CPU count validation."""
        with pytest.raises(ValueError):
            VMConfig(name="test-vm", template="rhel9", cpus=0)
        with pytest.raises(ValueError):
            VMConfig(name="test-vm", template="rhel9", cpus=100)

    def test_vm_config_invalid_memory_range(self):
        """Test memory validation."""
        with pytest.raises(ValueError):
            VMConfig(name="test-vm", template="rhel9", memory_mb=256)


class TestClusterSpec:
    """Test cluster specification validation."""

    def test_valid_cluster_spec(self):
        """Test creating a valid cluster spec."""
        spec = ClusterSpec(
            name="ocp-cluster",
            version="4.14.0",
            control_plane_count=3,
            worker_count=5,
        )
        assert spec.name == "ocp-cluster"
        assert spec.version == "4.14.0"
        assert spec.control_plane_count == 3
        assert spec.worker_count == 5

    def test_cluster_spec_invalid_version(self):
        """Test version format validation."""
        with pytest.raises(ValueError):
            ClusterSpec(name="cluster", version="invalid")


class TestDAGDefinition:
    """Test DAG definition validation per ADR-0045."""

    def test_valid_dag_definition(self):
        """Test creating a valid DAG definition."""
        dag = DAGDefinition(
            dag_id="ocp_initial_deployment",
            description="Deploy OpenShift cluster",
            schedule="@daily",
            tags=["openshift", "deployment"],
            tasks=["prepare", "deploy", "validate"],
        )
        assert dag.dag_id == "ocp_initial_deployment"

    def test_dag_invalid_uppercase(self):
        """Test that uppercase DAG IDs are rejected per ADR-0045."""
        with pytest.raises(ValueError) as exc_info:
            DAGDefinition(
                dag_id="OCP_Deployment",
                description="Invalid DAG",
            )
        # Pattern validation catches uppercase - error shows pattern mismatch
        assert "pattern" in str(exc_info.value).lower()

    def test_dag_invalid_starts_with_number(self):
        """Test DAG ID pattern validation."""
        with pytest.raises(ValueError):
            DAGDefinition(dag_id="123_dag", description="Invalid")


class TestRAGSource:
    """Test RAG source model."""

    def test_valid_rag_source(self):
        """Test creating a valid RAG source."""
        source = RAGSource(
            document_id="doc-123",
            title="ADR-0063",
            source_path="/docs/adrs/adr-0063.md",
            similarity_score=0.85,
            chunk_preview="PydanticAI migration...",
        )
        assert source.similarity_score == 0.85

    def test_rag_source_invalid_score(self):
        """Test similarity score bounds."""
        with pytest.raises(ValueError):
            RAGSource(
                document_id="doc-123",
                title="Test",
                source_path="/test",
                similarity_score=1.5,  # Invalid: > 1.0
                chunk_preview="Test",
            )


class TestDeploymentResult:
    """Test deployment result with confidence level computation."""

    def test_high_confidence_level(self):
        """Test automatic HIGH confidence level for >= 0.8."""
        result = DeploymentResult(
            status=DeploymentStatus.SUCCESS,
            confidence=0.85,
            message="Deployment complete",
        )
        assert result.confidence_level == ConfidenceLevel.HIGH

    def test_medium_confidence_level(self):
        """Test automatic MEDIUM confidence level for 0.6-0.8."""
        result = DeploymentResult(
            status=DeploymentStatus.PENDING,
            confidence=0.65,
            message="Proceeding with caveats",
        )
        assert result.confidence_level == ConfidenceLevel.MEDIUM

    def test_low_confidence_level(self):
        """Test automatic LOW confidence level for < 0.6."""
        result = DeploymentResult(
            status=DeploymentStatus.ESCALATED,
            confidence=0.5,
            message="Need more context",
        )
        assert result.confidence_level == ConfidenceLevel.LOW

    def test_explicit_confidence_level(self):
        """Test that explicit confidence level is preserved."""
        result = DeploymentResult(
            status=DeploymentStatus.SUCCESS,
            confidence=0.5,  # Would be LOW
            confidence_level=ConfidenceLevel.MEDIUM,  # Override
            message="Manual override",
        )
        assert result.confidence_level == ConfidenceLevel.MEDIUM


class TestTaskResult:
    """Test task result model."""

    def test_valid_task_result(self):
        """Test creating a valid task result."""
        result = TaskResult(
            success=True,
            confidence=0.75,
            output="Task completed successfully",
            execution_log=["Step 1 done", "Step 2 done"],
        )
        assert result.success is True
        assert result.escalation_needed is False

    def test_task_result_with_escalation(self):
        """Test task result requiring escalation."""
        result = TaskResult(
            success=False,
            confidence=0.4,
            output="Low confidence - escalating",
            escalation_needed=True,
            escalation_reason="Confidence below 0.6 threshold",
        )
        assert result.escalation_needed is True


class TestSessionPlan:
    """Test session plan model."""

    def test_valid_session_plan(self):
        """Test creating a valid session plan."""
        plan = SessionPlan(
            session_id="sess-123",
            user_intent="Deploy FreeIPA server",
            planned_tasks=[
                "Query RAG for FreeIPA docs",
                "Create VM via kcli",
                "Configure FreeIPA",
            ],
            estimated_confidence=0.75,
            required_providers=["apache-airflow-providers-ssh"],
            escalation_triggers=["Any task fails twice"],
        )
        assert len(plan.planned_tasks) == 3


class TestEscalationRequest:
    """Test escalation request model."""

    def test_valid_escalation_request(self):
        """Test creating escalation request per ADR-0049 Policy 4."""
        request = EscalationRequest(
            trigger="repeated_failure",
            context={"error": "Connection refused", "attempts": 3},
            failed_attempts=3,
            last_error="Connection refused",
            requested_action="Provide guidance on connectivity issues",
            agent_source=AgentRole.DEVELOPER,
        )
        assert request.trigger == "repeated_failure"
        assert request.agent_source == AgentRole.DEVELOPER


class TestTroubleshootingModels:
    """Test troubleshooting models for memory storage."""

    def test_troubleshooting_attempt(self):
        """Test troubleshooting attempt model."""
        attempt = TroubleshootingAttempt(
            session_id="sess-123",
            task_description="Fix DAG import error",
            error_message="ModuleNotFoundError",
            attempted_solution="Install missing module",
            result="success",
            confidence_score=0.9,
        )
        assert attempt.result == "success"
        assert isinstance(attempt.timestamp, datetime)

    def test_troubleshooting_query(self):
        """Test troubleshooting query model."""
        query = TroubleshootingQuery(
            error_pattern="Connection.*refused",
            limit=5,
            min_confidence=0.6,
        )
        assert query.limit == 5


class TestCodeGenerationModels:
    """Test code generation models per ADR-0063 hybrid strategy."""

    def test_code_generation_request(self):
        """Test code generation request model."""
        request = CodeGenerationRequest(
            task_description="Add error handling to DAG",
            target_files=["airflow/dags/test_dag.py"],
            rag_context=["ADR-0045 DAG standards", "Error handling patterns"],
        )
        assert len(request.target_files) == 1
        assert request.working_directory == "/root/qubinode_navigator"

    def test_fallback_code_prompt(self):
        """Test FallbackCodePrompt for Calling LLM."""
        prompt = FallbackCodePrompt(
            task_description="Implement retry logic",
            target_files=["src/service.py"],
            current_file_contents={"src/service.py": "class Service:\n    pass"},
            relevant_documentation=[{"title": "Retry patterns", "content": "..."}],
            related_adrs=["ADR-0063"],
        )
        assert prompt.prompt_type == "code_generation_request"
        assert "src/service.py" in prompt.current_file_contents

    def test_developer_task_result_aider_mode(self):
        """Test developer task result with Aider mode."""
        result = DeveloperTaskResult(
            success=True,
            confidence=0.8,
            task_analysis="Task analyzed and delegated to Aider",
            rag_sources_used=["ADR-0063", "Provider docs"],
            code_generation_mode="aider",
            aider_result={
                "success": True,
                "files_modified": ["src/test.py"],
            },
        )
        assert result.code_generation_mode == "aider"
        assert result.fallback_prompt is None

    def test_developer_task_result_fallback_mode(self):
        """Test developer task result with fallback prompt."""
        fallback = FallbackCodePrompt(
            task_description="Test task",
            target_files=["test.py"],
            current_file_contents={},
            relevant_documentation=[],
            related_adrs=[],
        )
        result = DeveloperTaskResult(
            success=True,
            confidence=0.7,
            task_analysis="Aider not available, created fallback prompt",
            rag_sources_used=[],
            code_generation_mode="fallback_prompt",
            fallback_prompt=fallback,
        )
        assert result.code_generation_mode == "fallback_prompt"
        assert result.fallback_prompt is not None
