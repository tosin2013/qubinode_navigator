"""
PydanticAI Agents for Qubinode Infrastructure Management.

This module provides the multi-agent architecture per ADR-0049 and ADR-0063:
- Manager Agent: Session orchestration and planning
- Developer Agent: Task execution and orchestration (NOT code generation)
- Agent Context: Shared RAG and lineage services for all agents

Code generation is delegated to:
- Option 1: Aider + LiteLLM (when API keys available)
- Option 2: FallbackCodePrompt returned to Calling LLM
"""

from .base import (
    AgentDependencies,
    create_mcp_connection,
    confidence_validator,
    create_deployment_agent,
    create_deployment_agent_with_mcp,
    create_task_agent,
)
from .manager import ManagerDependencies, create_manager_agent
from .developer import (
    DeveloperDependencies,
    create_developer_agent,
    execute_code_generation,
)
from .context import (
    AgentContextManager,
    agent_context,
    get_agent_context,
    initialize_agent_context,
    RAGContext,
    LineageContext,
)

__all__ = [
    # Base
    "AgentDependencies",
    "create_mcp_connection",
    "confidence_validator",
    "create_deployment_agent",
    "create_deployment_agent_with_mcp",
    "create_task_agent",
    # Manager
    "ManagerDependencies",
    "create_manager_agent",
    # Developer
    "DeveloperDependencies",
    "create_developer_agent",
    "execute_code_generation",
    # Context
    "AgentContextManager",
    "agent_context",
    "get_agent_context",
    "initialize_agent_context",
    "RAGContext",
    "LineageContext",
]
