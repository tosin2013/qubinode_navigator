"""
PydanticAI Domain Models for Qubinode Infrastructure Management.

These models define the structured outputs for all agent operations,
enabling type-safe LLM responses with automatic validation.

Per ADR-0063: PydanticAI Core Agent Orchestrator
Per ADR-0049: Multi-Agent LLM Memory Architecture
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ============================================================================
# Enums
# ============================================================================


class DeploymentStatus(str, Enum):
    """Status of a deployment operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"
    ESCALATED = "escalated"


class ConfidenceLevel(str, Enum):
    """
    Confidence classification per ADR-0049 Policy 1.

    - HIGH (>=0.8): Proceed with task autonomously
    - MEDIUM (0.6-0.8): Proceed with caveats, recommend review
    - LOW (<0.6): STOP and escalate to Calling LLM
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentRole(str, Enum):
    """Agent roles in the multi-agent architecture per ADR-0049."""

    CALLING_LLM = "calling_llm"  # External LLM (Claude Code, etc.)
    MANAGER = "manager"  # Session orchestration
    DEVELOPER = "developer"  # Task execution (orchestration only)


# ============================================================================
# Infrastructure Models
# ============================================================================


class VMConfig(BaseModel):
    """Configuration for VM creation via kcli."""

    name: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9-]*$",
        description="VM name (lowercase, alphanumeric with hyphens)",
    )
    template: str = Field(..., description="Base template/image name")
    cpus: int = Field(ge=1, le=64, default=2, description="Number of CPUs")
    memory_mb: int = Field(ge=512, le=262144, default=4096, description="Memory in MB")
    disk_gb: int = Field(ge=10, le=2048, default=50, description="Disk size in GB")
    network: str = Field(default="default", description="Network name")

    @field_validator("name")
    @classmethod
    def validate_name_length(cls, v: str) -> str:
        if len(v) > 63:
            raise ValueError("VM name must be 63 characters or less")
        return v


class ClusterSpec(BaseModel):
    """Specification for OpenShift/Kubernetes cluster."""

    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]*$")
    version: str = Field(..., pattern=r"^\d+\.\d+(\.\d+)?$")
    control_plane_count: int = Field(ge=1, le=5, default=3)
    worker_count: int = Field(ge=0, le=100, default=3)
    network_type: str = Field(default="OVNKubernetes")
    storage_class: str = Field(default="local-storage")


class DAGDefinition(BaseModel):
    """
    Airflow DAG definition for validation.

    Per ADR-0045: DAG IDs must be snake_case matching filename.
    """

    dag_id: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Snake_case DAG ID matching filename",
    )
    description: str
    schedule: Optional[str] = None
    tags: List[str] = []
    tasks: List[str] = []

    @field_validator("dag_id")
    @classmethod
    def validate_dag_id(cls, v: str) -> str:
        # Per ADR-0045: DAG IDs must be snake_case
        if not v.islower():
            raise ValueError("DAG ID must be lowercase snake_case")
        return v


# ============================================================================
# Agent Result Models
# ============================================================================


class RAGSource(BaseModel):
    """Source document from RAG retrieval."""

    document_id: str
    title: str
    source_path: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    chunk_preview: str = Field(max_length=500)


class DeploymentResult(BaseModel):
    """Structured result from deployment operations."""

    status: DeploymentStatus
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: Optional[ConfidenceLevel] = None
    message: str
    affected_resources: List[str] = []
    rollback_available: bool = False
    next_steps: Optional[List[str]] = None
    rag_sources: List[RAGSource] = []
    execution_time_ms: Optional[int] = None

    @model_validator(mode="after")
    def compute_confidence_level(self) -> "DeploymentResult":
        """Auto-compute confidence level from numeric confidence."""
        if self.confidence_level is None:
            if self.confidence >= 0.8:
                self.confidence_level = ConfidenceLevel.HIGH
            elif self.confidence >= 0.6:
                self.confidence_level = ConfidenceLevel.MEDIUM
            else:
                self.confidence_level = ConfidenceLevel.LOW
        return self


class TaskResult(BaseModel):
    """Result from Developer Agent task execution."""

    success: bool
    confidence: float = Field(ge=0.0, le=1.0)
    output: str
    code_changes: Optional[List[str]] = None
    rag_sources_used: List[RAGSource] = []
    escalation_needed: bool = False
    escalation_reason: Optional[str] = None
    provider_used: Optional[str] = None
    execution_log: List[str] = []


class SessionPlan(BaseModel):
    """Manager Agent session orchestration plan."""

    session_id: str
    user_intent: str
    planned_tasks: List[str]
    estimated_confidence: float = Field(ge=0.0, le=1.0)
    requires_external_docs: bool = False
    required_providers: List[str] = []
    escalation_triggers: List[str] = []


class EscalationRequest(BaseModel):
    """
    Request to escalate to Calling LLM per ADR-0049 Policy 4.

    Escalation triggers:
    - repeated_failure: Same error 2+ times
    - architecture_scope: Change affects multiple DAGs
    - confidence_deadlock: Cannot achieve 0.6 threshold
    - user_request: Explicit user escalation
    """

    trigger: str
    context: Dict[str, Any]
    failed_attempts: int = 0
    last_error: Optional[str] = None
    requested_action: str
    agent_source: AgentRole


class OverrideInstruction(BaseModel):
    """Override instruction from Calling LLM to Developer Agent."""

    override: bool = True
    instruction: str
    reasoning: str
    constraints: List[str] = []
    confidence_override: bool = False


# ============================================================================
# Troubleshooting Models
# ============================================================================


class TroubleshootingAttempt(BaseModel):
    """Record of a troubleshooting attempt for memory storage."""

    session_id: str
    task_description: str
    error_message: str
    attempted_solution: str
    result: str  # 'success', 'failed', 'partial'
    confidence_score: float = Field(ge=0.0, le=1.0)
    override_by: Optional[AgentRole] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TroubleshootingQuery(BaseModel):
    """Query for past troubleshooting attempts."""

    error_pattern: Optional[str] = None
    session_id: Optional[str] = None
    limit: int = Field(ge=1, le=50, default=10)
    min_confidence: float = Field(ge=0.0, le=1.0, default=0.0)


# ============================================================================
# Code Generation Models (ADR-0063 Hybrid Strategy)
# ============================================================================


class CodeGenerationRequest(BaseModel):
    """Request for code generation via Aider + LiteLLM."""

    task_description: str
    target_files: List[str]
    rag_context: List[str]
    lineage_context: Optional[Dict[str, Any]] = None
    working_directory: str = "/opt/qubinode_navigator"


class FallbackCodePrompt(BaseModel):
    """
    Structured prompt returned to Calling LLM when Aider is unavailable.

    Contains all context needed for the Calling LLM to perform code generation.
    This is the "Option 2" path per ADR-0063.
    """

    prompt_type: str = "code_generation_request"

    # Task context
    task_description: str
    target_files: List[str]
    current_file_contents: Dict[str, str]

    # RAG context from PgVector
    relevant_documentation: List[Dict[str, Any]]
    related_adrs: List[str]

    # Lineage context from Marquez
    execution_history: Optional[Dict[str, Any]] = None
    past_errors: List[str] = []
    successful_patterns: List[str] = []

    # Instructions for Calling LLM
    instructions: str = """
Generate the code changes for the task described above.

Context provided:
- Current file contents for files to be modified
- Relevant documentation from the project's RAG system
- Related ADRs that inform the implementation
- Execution history showing past runs and errors to avoid

Please provide:
1. Complete file contents for each modified file
2. Explanation of changes made
3. Any follow-up actions needed
"""


class DeveloperTaskResult(BaseModel):
    """
    Extended result from Developer Agent with code generation support.

    The Developer Agent orchestrates but does NOT generate code directly.
    Code generation is delegated to Aider or returned as FallbackCodePrompt.
    """

    success: bool
    confidence: float = Field(ge=0.0, le=1.0)

    # Orchestration outputs
    task_analysis: str
    rag_sources_used: List[str]

    # Code generation mode
    code_generation_mode: str  # "aider", "fallback_prompt", "none"

    # Aider result (if used)
    aider_result: Optional[Dict[str, Any]] = None

    # Fallback prompt (if Aider unavailable)
    fallback_prompt: Optional[FallbackCodePrompt] = None

    # Escalation
    escalation_needed: bool = False
    escalation_reason: Optional[str] = None
