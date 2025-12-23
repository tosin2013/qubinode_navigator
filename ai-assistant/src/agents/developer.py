"""
Developer Agent: Task ORCHESTRATION (not code generation).

The Developer Agent:
- Analyzes tasks and decomposes them
- Queries RAG for relevant documentation
- Checks Marquez for execution history
- Computes confidence scores
- Delegates code generation to Aider or returns FallbackCodePrompt

CRITICAL: Granite is NOT capable of complex code generation.
This agent orchestrates but does NOT write code directly.

Per ADR-0063: PydanticAI Core Agent Orchestrator
Per ADR-0049: Multi-Agent LLM Memory Architecture
"""

import os
import logging
import subprocess
from typing import Optional, Any, List

from pydantic_ai import Agent, RunContext

# Import domain models - try relative first, then absolute
try:
    from ..models.domain import (
        DeveloperTaskResult,
        CodeGenerationRequest,
        FallbackCodePrompt,
        AgentRole,  # noqa: F401
    )
    from .base import create_mcp_connection, AgentDependencies  # noqa: F401
except ImportError:
    from models.domain import (
        DeveloperTaskResult,
        CodeGenerationRequest,
        FallbackCodePrompt,
    )
    from agents.base import AgentDependencies

logger = logging.getLogger(__name__)


class DeveloperDependencies(AgentDependencies):
    """Extended dependencies for Developer Agent."""

    # Aider configuration
    aider_enabled: bool = True
    aider_model: str = "claude-sonnet-4-20250514"  # Model for Aider via LiteLLM

    # Working directory for code changes
    working_directory: str = "/opt/qubinode_navigator"

    # Provider cache for Provider-First Rule checks
    provider_cache: dict = {}

    # Injected services (optional)
    rag_service: Any = None  # RAG service for document queries
    lineage_service: Any = None  # Marquez service for execution history


def create_developer_agent(
    model: Optional[str] = None,
) -> Agent[DeveloperDependencies, DeveloperTaskResult]:
    """
    Create Developer Agent for task ORCHESTRATION.

    IMPORTANT: This agent does NOT generate code directly.
    It orchestrates code generation via Aider or FallbackCodePrompt.

    Args:
        model: Model identifier in PydanticAI format (provider:model)
               Examples: google-gla:gemini-2.0-flash, openai:gpt-4o

    Returns:
        Configured PydanticAI Agent for task orchestration
    """
    # PydanticAI model format: provider:model
    model = model or os.getenv("DEVELOPER_MODEL", "google-gla:gemini-2.0-flash")

    agent = Agent(
        model,
        output_type=DeveloperTaskResult,
        deps_type=DeveloperDependencies,
        system_prompt="""You are the Qubinode Developer Agent.

**CRITICAL: You ORCHESTRATE tasks but do NOT write code directly.**

Your responsibilities:
1. Analyze the task and decompose into steps
2. Query RAG for relevant documentation (use query_rag MCP tool)
3. Query Marquez for execution history (use get_dag_lineage MCP tool)
4. Compute confidence based on available context
5. Delegate code generation:
   - If code changes needed, set code_generation_mode to "aider" or "fallback_prompt"
   - If no code changes, set code_generation_mode to "none"

CONFIDENCE SCORING (ADR-0049 Policy 1):
Compute confidence as weighted average:
- 0.4 * RAG similarity score (average of top results)
- 0.3 * RAG hit count (normalized: hits/10, max 1.0)
- 0.2 * Provider availability (1.0 if exists, 0.0 if not)
- 0.1 * Similar past execution exists (from Marquez lineage)

ESCALATION TRIGGERS:
Set escalation_needed=True when:
- Confidence < 0.6
- Same error pattern found in Marquez 2+ times
- Multi-DAG impact detected
- No Airflow provider exists for external system

PROVIDER-FIRST RULE (ADR-0049):
Before any external system integration:
1. Check if provider exists via list_providers tool
2. If NO provider, STOP and escalate
3. Never create pseudo-provider layers

OUTPUT FORMAT:
- success: Whether orchestration completed
- confidence: Computed confidence score
- task_analysis: Your analysis of the task
- rag_sources_used: Documents you retrieved
- code_generation_mode: "aider", "fallback_prompt", or "none"
- escalation_needed/escalation_reason: If escalation required

You do NOT generate code. You gather context and delegate.
""",
    )

    @agent.output_validator
    async def validate_task(
        ctx: RunContext[DeveloperDependencies],
        output: DeveloperTaskResult,
    ) -> DeveloperTaskResult:
        """Validate task result and enforce escalation policies."""
        # Enforce escalation for low confidence
        if output.confidence < ctx.deps.confidence_threshold:
            if not output.escalation_needed:
                output.escalation_needed = True
                output.escalation_reason = f"Low confidence: {output.confidence:.2f}"

        return output

    return agent


# ============================================================================
# Code Generation Execution
# ============================================================================


async def execute_code_generation(
    request: CodeGenerationRequest,
    deps: DeveloperDependencies,
) -> DeveloperTaskResult:
    """
    Execute code generation based on configuration.

    If Aider is enabled: Use Aider + LiteLLM with Claude/GPT-4
    If not enabled: Return FallbackCodePrompt for Calling LLM

    Args:
        request: Code generation request with task and context
        deps: Developer dependencies with configuration

    Returns:
        DeveloperTaskResult with either aider_result or fallback_prompt
    """
    if deps.aider_enabled and _check_aider_available():
        return await _execute_with_aider(request, deps)
    else:
        return await _create_fallback_prompt(request, deps)


def _check_aider_available() -> bool:
    """Check if Aider is installed and API keys are available."""
    try:
        result = subprocess.run(
            ["which", "aider"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False

        # Check for API keys
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        return has_anthropic or has_openai
    except Exception as e:
        logger.warning(f"Aider availability check failed: {e}")
        return False


async def _execute_with_aider(
    request: CodeGenerationRequest,
    deps: DeveloperDependencies,
) -> DeveloperTaskResult:
    """Execute code generation via Aider with capable model."""

    # Build enriched prompt with RAG + lineage context
    prompt_parts = [request.task_description]

    if request.rag_context:
        prompt_parts.append("\n## Relevant Documentation:")
        prompt_parts.extend(request.rag_context[:5])  # Limit context

    if request.lineage_context:
        prompt_parts.append("\n## Execution History:")
        if request.lineage_context.get("past_errors"):
            prompt_parts.append(f"Errors to avoid: {request.lineage_context['past_errors']}")
        if request.lineage_context.get("successful_patterns"):
            prompt_parts.append(f"Patterns to follow: {request.lineage_context['successful_patterns']}")

    full_prompt = "\n".join(prompt_parts)

    # Configure environment for Aider
    env = os.environ.copy()
    env["AIDER_MODEL"] = deps.aider_model

    cmd = [
        "aider",
        "--yes",
        "--message",
        full_prompt,
        *request.target_files,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=request.working_directory,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )

        return DeveloperTaskResult(
            success=result.returncode == 0,
            confidence=0.8 if result.returncode == 0 else 0.3,
            task_analysis=f"Executed via Aider with {deps.aider_model}",
            rag_sources_used=request.rag_context[:5],
            code_generation_mode="aider",
            aider_result={
                "success": result.returncode == 0,
                "files_modified": request.target_files,
                "output": result.stdout[-2000:] if result.stdout else "",
                "error": result.stderr if result.returncode != 0 else None,
            },
        )
    except subprocess.TimeoutExpired:
        return DeveloperTaskResult(
            success=False,
            confidence=0.0,
            task_analysis="Aider execution timed out",
            rag_sources_used=request.rag_context[:5],
            code_generation_mode="aider",
            escalation_needed=True,
            escalation_reason="Aider timed out after 5 minutes",
        )
    except Exception as e:
        logger.error(f"Aider execution failed: {e}")
        return DeveloperTaskResult(
            success=False,
            confidence=0.0,
            task_analysis=f"Aider execution error: {str(e)}",
            rag_sources_used=request.rag_context[:5],
            code_generation_mode="aider",
            escalation_needed=True,
            escalation_reason=str(e),
        )


async def _create_fallback_prompt(
    request: CodeGenerationRequest,
    deps: DeveloperDependencies,
) -> DeveloperTaskResult:
    """
    Create FallbackCodePrompt for Calling LLM.

    This is returned when Aider is not available, allowing the
    Calling LLM to perform code generation with full context.
    """

    # Read current file contents
    current_contents = {}
    for file_path in request.target_files:
        full_path = os.path.join(request.working_directory, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r") as f:
                    current_contents[file_path] = f.read()
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                current_contents[file_path] = f"# Error reading file: {e}"

    # Query RAG if service available
    relevant_docs: List[dict] = []
    related_adrs: List[str] = []
    if deps.rag_service:
        try:
            rag_results = await deps.rag_service.retrieve_relevant_context(
                query=request.task_description,
                top_k=10,
            )
            relevant_docs = [
                {
                    "title": getattr(r, "title", "Unknown"),
                    "content": getattr(r, "content", "")[:1000],
                    "similarity": getattr(r, "score", 0.5),
                }
                for r in getattr(rag_results, "contexts", [])[:10]
            ]
            related_adrs = [r.get("title", "") for r in relevant_docs if "adr" in str(r.get("title", "")).lower()][:5]
        except Exception as e:
            logger.warning(f"RAG query failed: {e}")

    # Query lineage if service available
    execution_history = None
    past_errors: List[str] = []
    successful_patterns: List[str] = []
    if deps.lineage_service and request.lineage_context:
        lineage_data = request.lineage_context
        execution_history = {
            "total_runs": lineage_data.get("run_count", 0),
            "success_rate": lineage_data.get("success_rate"),
        }
        past_errors = lineage_data.get("error_patterns", [])[:5]
        successful_patterns = lineage_data.get("success_patterns", [])[:5]

    fallback = FallbackCodePrompt(
        task_description=request.task_description,
        target_files=request.target_files,
        current_file_contents=current_contents,
        relevant_documentation=relevant_docs,
        related_adrs=related_adrs,
        execution_history=execution_history,
        past_errors=past_errors,
        successful_patterns=successful_patterns,
    )

    return DeveloperTaskResult(
        success=True,  # Successfully created prompt
        confidence=0.7,  # Medium - requires Calling LLM to execute
        task_analysis="Created FallbackCodePrompt for Calling LLM",
        rag_sources_used=[d.get("title", "") for d in relevant_docs],
        code_generation_mode="fallback_prompt",
        fallback_prompt=fallback,
    )


# ============================================================================
# Confidence Calculation Utility
# ============================================================================


def compute_confidence(
    rag_scores: List[float],
    rag_hits: int,
    provider_exists: bool,
    lineage_match: bool,
) -> float:
    """
    Compute confidence score per ADR-0049 Policy 1.

    Weights:
    - 0.4: RAG similarity score (average of top results)
    - 0.3: RAG hit count (normalized: hits/10, max 1.0)
    - 0.2: Provider availability (1.0 if exists, 0.0 if not)
    - 0.1: Similar past execution exists (from Marquez)

    Args:
        rag_scores: List of similarity scores from RAG
        rag_hits: Number of relevant documents found
        provider_exists: Whether Airflow provider exists
        lineage_match: Whether similar execution found in Marquez

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # RAG similarity (40%)
    avg_rag_score = sum(rag_scores) / len(rag_scores) if rag_scores else 0.0
    rag_similarity = min(avg_rag_score, 1.0) * 0.4

    # RAG hit count (30%)
    normalized_hits = min(rag_hits / 10.0, 1.0) * 0.3

    # Provider availability (20%)
    provider_score = 1.0 if provider_exists else 0.0
    provider_weight = provider_score * 0.2

    # Lineage match (10%)
    lineage_score = 1.0 if lineage_match else 0.0
    lineage_weight = lineage_score * 0.1

    total = rag_similarity + normalized_hits + provider_weight + lineage_weight
    return round(min(total, 1.0), 2)
