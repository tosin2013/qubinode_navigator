"""
PydanticAI Domain Models for Qubinode Infrastructure Management.

This module provides structured output types for all agent operations,
enabling type-safe LLM responses with automatic validation per ADR-0063.
"""

from .domain import (
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
    OverrideInstruction,
    # Troubleshooting Models
    TroubleshootingAttempt,
    TroubleshootingQuery,
    # Code Generation Models
    CodeGenerationRequest,
    FallbackCodePrompt,
    DeveloperTaskResult,
)

__all__ = [
    # Enums
    "DeploymentStatus",
    "ConfidenceLevel",
    "AgentRole",
    # Infrastructure Models
    "VMConfig",
    "ClusterSpec",
    "DAGDefinition",
    # Agent Result Models
    "RAGSource",
    "DeploymentResult",
    "TaskResult",
    "SessionPlan",
    "EscalationRequest",
    "OverrideInstruction",
    # Troubleshooting Models
    "TroubleshootingAttempt",
    "TroubleshootingQuery",
    # Code Generation Models
    "CodeGenerationRequest",
    "FallbackCodePrompt",
    "DeveloperTaskResult",
]
