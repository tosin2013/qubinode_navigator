"""
Manager Agent for Qubinode Multi-Agent System
ADR-0049: Multi-Agent LLM Memory Architecture

The Manager Agent orchestrates task execution, maintains session context,
and coordinates with the Developer Agent. It acts as the bridge between
the Calling LLM (Claude/user) and the Developer Agent.

Responsibilities:
- Session context management
- Task decomposition and planning
- Escalation to Calling LLM when confidence is low
- Provider-First Rule enforcement
- Decision logging for learning

Usage:
    from qubinode.agents import ManagerAgent

    manager = ManagerAgent()
    result = await manager.process_task(
        task="Create a DAG for FreeIPA deployment",
        session_id="uuid-here"
    )
"""

import os
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Context maintained throughout a session."""
    session_id: str
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tasks_completed: List[Dict[str, Any]] = field(default_factory=list)
    current_task: Optional[str] = None
    errors_encountered: List[Dict[str, Any]] = field(default_factory=list)
    rag_queries: List[Dict[str, Any]] = field(default_factory=list)
    escalations: List[Dict[str, Any]] = field(default_factory=list)
    overrides: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def add_task_completion(self, task: str, result: str, confidence: float):
        self.tasks_completed.append({
            "task": task,
            "result": result,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        })

    def add_error(self, error: str, context: Dict[str, Any]):
        self.errors_encountered.append({
            "error": error,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        })

    def add_escalation(self, reason: str, task: str, confidence: float):
        self.escalations.append({
            "reason": reason,
            "task": task,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        })


@dataclass
class TaskResult:
    """Result of a task execution."""
    success: bool
    output: str
    confidence: float
    action_taken: str  # 'executed', 'escalated', 'delegated', 'planned'
    details: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    suggested_plan: Optional[str] = None
    error: Optional[str] = None


class ManagerAgent:
    """
    Manager Agent for orchestrating multi-agent task execution.

    The Manager Agent:
    1. Receives tasks from the Calling LLM
    2. Queries RAG for relevant context
    3. Applies policies to determine action
    4. Delegates to Developer Agent or escalates
    5. Logs decisions for learning
    """

    # Confidence thresholds
    CONFIDENCE_HIGH = 0.8  # Auto-execute
    CONFIDENCE_MEDIUM = 0.6  # Execute with logging
    CONFIDENCE_LOW = 0.4  # Escalate to Calling LLM

    def __init__(
        self,
        rag_store=None,
        llm_router=None,
        developer_agent=None,
        model: str = "manager"
    ):
        """
        Initialize the Manager Agent.

        Args:
            rag_store: RAGStore instance for knowledge queries
            llm_router: LLMRouter instance for LLM calls
            developer_agent: DeveloperAgent instance for code generation
            model: Model to use for manager reasoning
        """
        self.rag_store = rag_store
        self.llm_router = llm_router
        self.developer_agent = developer_agent
        self.model = model
        self.sessions: Dict[str, SessionContext] = {}

        logger.info("ManagerAgent initialized")

    def _get_rag_store(self):
        """Lazy load RAG store."""
        if self.rag_store is None:
            try:
                from qubinode.rag_store import get_rag_store
                self.rag_store = get_rag_store()
            except Exception as e:
                logger.warning(f"Could not load RAG store: {e}")
        return self.rag_store

    def _get_llm_router(self):
        """Lazy load LLM router."""
        if self.llm_router is None:
            try:
                from qubinode.llm_router import get_router
                self.llm_router = get_router()
            except Exception as e:
                logger.warning(f"Could not load LLM router: {e}")
        return self.llm_router

    def _get_developer_agent(self):
        """Lazy load Developer agent."""
        if self.developer_agent is None:
            try:
                from qubinode.agents.developer_agent import DeveloperAgent
                self.developer_agent = DeveloperAgent()
            except Exception as e:
                logger.warning(f"Could not load Developer agent: {e}")
        return self.developer_agent

    def get_or_create_session(self, session_id: Optional[str] = None) -> SessionContext:
        """
        Get existing session or create a new one.

        Args:
            session_id: Existing session ID or None for new session

        Returns:
            SessionContext instance
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        if session_id not in self.sessions:
            self.sessions[session_id] = SessionContext(session_id=session_id)
            logger.info(f"Created new session: {session_id}")

        return self.sessions[session_id]

    async def process_task(
        self,
        task: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        override: Optional[str] = None
    ) -> TaskResult:
        """
        Process a task request from the Calling LLM.

        Args:
            task: Task description
            session_id: Session ID for context continuity
            context: Additional context from Calling LLM
            override: Override instruction from Calling LLM (Policy 4)

        Returns:
            TaskResult with execution details
        """
        session = self.get_or_create_session(session_id)
        session.current_task = task

        logger.info(f"Processing task: {task[:100]}... (session: {session.session_id})")

        try:
            # Step 1: Handle override if present (Policy 4)
            if override:
                return await self._handle_override(task, override, session)

            # Step 2: Query RAG for relevant context
            rag_context = await self._query_rag(task, session)

            # Step 3: Check for existing provider (Policy 2)
            provider_check = await self._check_provider(task, rag_context)

            # Step 4: Compute confidence score (Policy 1)
            confidence = await self._compute_confidence(task, rag_context, provider_check)

            # Step 5: Apply policies and determine action
            return await self._apply_policies(
                task, session, rag_context, provider_check, confidence, context
            )

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            session.add_error(str(e), {"task": task})
            return TaskResult(
                success=False,
                output="",
                confidence=0.0,
                action_taken="error",
                error=str(e)
            )

    async def _handle_override(
        self,
        task: str,
        override: str,
        session: SessionContext
    ) -> TaskResult:
        """
        Handle override from Calling LLM (Policy 4).

        When the Calling LLM provides an explicit override, execute it directly.
        """
        logger.info(f"Override received from Calling LLM: {override[:100]}...")

        session.overrides.append({
            "task": task,
            "override": override,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Log the decision
        await self._log_decision(
            session=session,
            decision_type="override",
            decision=override,
            reasoning="Explicit instruction from Calling LLM",
            confidence=1.0  # Full confidence on override
        )

        # Execute override via Developer Agent
        developer = self._get_developer_agent()
        if developer:
            result = await developer.execute_with_override(override, session.session_id)
            return TaskResult(
                success=result.get("success", False),
                output=result.get("output", ""),
                confidence=1.0,
                action_taken="executed",
                details={"override": True, "result": result}
            )

        return TaskResult(
            success=True,
            output=f"Override acknowledged: {override}",
            confidence=1.0,
            action_taken="executed",
            details={"override": True, "developer_unavailable": True}
        )

    async def _query_rag(
        self,
        task: str,
        session: SessionContext
    ) -> Dict[str, Any]:
        """
        Query RAG for relevant context.

        Returns context from:
        - ADRs
        - Provider documentation
        - Similar DAG examples
        - Past troubleshooting
        """
        rag = self._get_rag_store()
        if not rag:
            return {"documents": [], "troubleshooting": []}

        try:
            # Query for relevant documents
            docs = await rag.search_documents(
                query=task,
                doc_types=["adr", "provider_doc", "dag", "guide"],
                limit=5,
                threshold=0.5
            )

            # Query for similar past errors/solutions
            troubleshooting = await rag.search_similar_errors(
                error_description=task,
                only_successful=True,
                limit=3
            )

            # Record the query
            session.rag_queries.append({
                "query": task,
                "doc_count": len(docs),
                "troubleshooting_count": len(troubleshooting),
                "timestamp": datetime.utcnow().isoformat()
            })

            return {
                "documents": docs,
                "troubleshooting": troubleshooting,
                "max_similarity": max([d.get("similarity", 0) for d in docs], default=0)
            }

        except Exception as e:
            logger.warning(f"RAG query failed: {e}")
            return {"documents": [], "troubleshooting": [], "error": str(e)}

    async def _check_provider(
        self,
        task: str,
        rag_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if an Airflow provider exists for the task (Policy 2).

        Extracts system/service name from task and checks provider registry.
        """
        rag = self._get_rag_store()
        if not rag:
            return {"provider_exists": False, "provider_name": None}

        # Extract system name from task (simple heuristic)
        systems = ["freeipa", "vyos", "openshift", "libvirt", "kcli", "step-ca",
                   "kubernetes", "docker", "aws", "azure", "gcp", "ssh", "http"]

        task_lower = task.lower()
        detected_system = None
        for system in systems:
            if system in task_lower:
                detected_system = system
                break

        if not detected_system:
            return {"provider_exists": False, "provider_name": None, "system": None}

        # Check provider registry
        try:
            provider_info = await rag.check_provider_exists(detected_system)
            return {
                "provider_exists": provider_info.get("exists", False),
                "provider_name": provider_info.get("provider_name"),
                "system": detected_system
            }
        except Exception as e:
            logger.warning(f"Provider check failed: {e}")
            return {"provider_exists": False, "provider_name": None, "system": detected_system}

    async def _compute_confidence(
        self,
        task: str,
        rag_context: Dict[str, Any],
        provider_check: Dict[str, Any]
    ) -> float:
        """
        Compute confidence score for the task (Policy 1).

        Confidence is based on:
        - RAG similarity scores
        - Number of relevant documents
        - Provider existence
        - Similar DAG examples
        """
        try:
            from qubinode.agents.confidence_scorer import ConfidenceScorer
            scorer = ConfidenceScorer()
            return scorer.compute(
                rag_similarity=rag_context.get("max_similarity", 0),
                rag_hit_count=len(rag_context.get("documents", [])),
                provider_exists=provider_check.get("provider_exists", False),
                troubleshooting_hits=len(rag_context.get("troubleshooting", []))
            )
        except Exception as e:
            logger.warning(f"Confidence scoring failed: {e}")
            # Fall back to simple calculation
            base = rag_context.get("max_similarity", 0) * 0.5
            if provider_check.get("provider_exists"):
                base += 0.3
            if rag_context.get("documents"):
                base += 0.2
            return min(base, 1.0)

    async def _apply_policies(
        self,
        task: str,
        session: SessionContext,
        rag_context: Dict[str, Any],
        provider_check: Dict[str, Any],
        confidence: float,
        additional_context: Optional[Dict[str, Any]]
    ) -> TaskResult:
        """
        Apply policies to determine action.

        Policies:
        1. Confidence & RAG: If low confidence, request more documentation
        2. Provider-First: Use existing provider if available
        3. Missing Provider: Generate plan, not code
        4. Override: Already handled in _handle_override
        """
        # Policy 1: Low confidence → Escalate
        if confidence < self.CONFIDENCE_LOW:
            return await self._escalate_to_calling_llm(
                task, session, confidence, rag_context,
                reason="Low confidence - need more documentation or guidance"
            )

        # Policy 2: Provider-First
        if provider_check.get("provider_exists"):
            return await self._execute_with_provider(
                task, session, provider_check, rag_context, confidence
            )

        # Policy 3: Missing Provider → Plan
        if provider_check.get("system") and not provider_check.get("provider_exists"):
            return await self._generate_plan(
                task, session, provider_check, rag_context, confidence
            )

        # Medium confidence → Execute with Developer Agent
        if confidence >= self.CONFIDENCE_MEDIUM:
            return await self._delegate_to_developer(
                task, session, rag_context, confidence
            )

        # Between LOW and MEDIUM → Request approval
        return await self._request_approval(
            task, session, confidence, rag_context
        )

    async def _escalate_to_calling_llm(
        self,
        task: str,
        session: SessionContext,
        confidence: float,
        rag_context: Dict[str, Any],
        reason: str
    ) -> TaskResult:
        """Escalate to Calling LLM when confidence is too low."""
        session.add_escalation(reason, task, confidence)

        await self._log_decision(
            session=session,
            decision_type="escalation",
            decision=f"Escalating to Calling LLM: {reason}",
            reasoning=reason,
            confidence=confidence,
            rag_hits=len(rag_context.get("documents", [])),
            rag_similarity=rag_context.get("max_similarity", 0)
        )

        # Build helpful message for Calling LLM
        message = self._build_escalation_message(task, confidence, rag_context, reason)

        return TaskResult(
            success=False,
            output=message,
            confidence=confidence,
            action_taken="escalated",
            requires_approval=True,
            details={
                "reason": reason,
                "rag_context": rag_context,
                "suggestions": self._get_escalation_suggestions(rag_context)
            }
        )

    def _build_escalation_message(
        self,
        task: str,
        confidence: float,
        rag_context: Dict[str, Any],
        reason: str
    ) -> str:
        """Build a helpful escalation message."""
        msg = f"""## Escalation Required

**Task:** {task}
**Confidence:** {confidence:.2f}
**Reason:** {reason}

### What I Found
"""
        docs = rag_context.get("documents", [])
        if docs:
            msg += f"\nFound {len(docs)} related documents:\n"
            for doc in docs[:3]:
                msg += f"- {doc.get('doc_type', 'doc')}: {doc.get('source_path', 'unknown')}\n"
        else:
            msg += "\nNo relevant documentation found in RAG.\n"

        msg += """
### What I Need
To proceed with confidence, I need:
1. More specific documentation about this system
2. An example DAG or similar implementation
3. Explicit instructions on how to proceed

You can provide an override instruction to proceed anyway.
"""
        return msg

    def _get_escalation_suggestions(self, rag_context: Dict[str, Any]) -> List[str]:
        """Generate suggestions for the Calling LLM."""
        suggestions = []
        if not rag_context.get("documents"):
            suggestions.append("Ingest relevant documentation into RAG using ingest_to_rag()")
        if not rag_context.get("troubleshooting"):
            suggestions.append("Check if there are similar tasks in troubleshooting history")
        suggestions.append("Provide an override instruction if you want to proceed anyway")
        return suggestions

    async def _execute_with_provider(
        self,
        task: str,
        session: SessionContext,
        provider_check: Dict[str, Any],
        rag_context: Dict[str, Any],
        confidence: float
    ) -> TaskResult:
        """Execute task using existing Airflow provider (Policy 2)."""
        provider_name = provider_check.get("provider_name")

        await self._log_decision(
            session=session,
            decision_type="provider_check",
            decision=f"Using provider: {provider_name}",
            reasoning="Provider-First Rule: Using official Airflow provider",
            confidence=confidence
        )

        # Delegate to Developer with provider context
        developer = self._get_developer_agent()
        if developer:
            result = await developer.execute_with_provider(
                task=task,
                provider_name=provider_name,
                rag_context=rag_context,
                session_id=session.session_id
            )
            session.add_task_completion(task, result.get("output", ""), confidence)
            return TaskResult(
                success=result.get("success", False),
                output=result.get("output", ""),
                confidence=confidence,
                action_taken="executed",
                details={"provider": provider_name, "result": result}
            )

        return TaskResult(
            success=True,
            output=f"Use provider {provider_name} for this task",
            confidence=confidence,
            action_taken="planned",
            details={"provider": provider_name}
        )

    async def _generate_plan(
        self,
        task: str,
        session: SessionContext,
        provider_check: Dict[str, Any],
        rag_context: Dict[str, Any],
        confidence: float
    ) -> TaskResult:
        """Generate implementation plan instead of code (Policy 3)."""
        system = provider_check.get("system")

        await self._log_decision(
            session=session,
            decision_type="plan_creation",
            decision=f"Generating plan for {system} (no provider available)",
            reasoning="Missing Provider Rule: No official provider, generating plan",
            confidence=confidence
        )

        # Generate plan using LLM
        plan = await self._generate_implementation_plan(task, system, rag_context)

        return TaskResult(
            success=True,
            output=plan,
            confidence=confidence,
            action_taken="planned",
            requires_approval=True,
            suggested_plan=plan,
            details={
                "system": system,
                "missing_provider": True,
                "rag_docs_used": len(rag_context.get("documents", []))
            }
        )

    async def _generate_implementation_plan(
        self,
        task: str,
        system: str,
        rag_context: Dict[str, Any]
    ) -> str:
        """Generate detailed implementation plan using LLM."""
        router = self._get_llm_router()
        if not router:
            return self._generate_simple_plan(task, system)

        # Build context from RAG
        context_str = ""
        for doc in rag_context.get("documents", [])[:3]:
            context_str += f"\n---\n{doc.get('content', '')[:500]}\n"

        prompt = f"""Generate an implementation plan for the following task.
Note: No official Airflow provider exists for {system}, so we need a custom approach.

Task: {task}

Relevant Context:
{context_str}

Generate a detailed plan with:
1. Prerequisites and dependencies
2. Step-by-step implementation approach
3. Testing strategy
4. Potential risks and mitigations
5. Estimated effort

Format as markdown.
"""

        try:
            response = await router.complete(
                model="manager",
                messages=[
                    {"role": "system", "content": "You are a technical architect creating implementation plans."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            return response.get("content", self._generate_simple_plan(task, system))
        except Exception as e:
            logger.warning(f"Plan generation failed: {e}")
            return self._generate_simple_plan(task, system)

    def _generate_simple_plan(self, task: str, system: str) -> str:
        """Generate a simple plan when LLM is unavailable."""
        return f"""## Implementation Plan

**Task:** {task}
**System:** {system}

### Note
No official Airflow provider exists for {system}. A custom implementation is required.

### Recommended Approach
1. Research {system} API/CLI documentation
2. Create custom operator using BashOperator or PythonOperator
3. Implement proper error handling
4. Add retry logic for transient failures
5. Create unit tests

### Next Steps
- Ingest {system} documentation into RAG
- Create a custom operator class
- Write integration tests
"""

    async def _delegate_to_developer(
        self,
        task: str,
        session: SessionContext,
        rag_context: Dict[str, Any],
        confidence: float
    ) -> TaskResult:
        """Delegate task to Developer Agent."""
        await self._log_decision(
            session=session,
            decision_type="delegation",
            decision=f"Delegating to Developer Agent",
            reasoning=f"Confidence {confidence:.2f} meets threshold",
            confidence=confidence,
            rag_hits=len(rag_context.get("documents", []))
        )

        developer = self._get_developer_agent()
        if developer:
            result = await developer.execute_task(
                task=task,
                rag_context=rag_context,
                session_id=session.session_id
            )
            session.add_task_completion(task, result.get("output", ""), confidence)
            return TaskResult(
                success=result.get("success", False),
                output=result.get("output", ""),
                confidence=confidence,
                action_taken="executed",
                details={"delegated_to": "developer", "result": result}
            )

        return TaskResult(
            success=False,
            output="Developer Agent not available",
            confidence=confidence,
            action_taken="error",
            error="Developer Agent not initialized"
        )

    async def _request_approval(
        self,
        task: str,
        session: SessionContext,
        confidence: float,
        rag_context: Dict[str, Any]
    ) -> TaskResult:
        """Request approval from Calling LLM for medium-confidence tasks."""
        await self._log_decision(
            session=session,
            decision_type="confidence_check",
            decision="Requesting approval due to medium confidence",
            reasoning=f"Confidence {confidence:.2f} requires approval",
            confidence=confidence
        )

        return TaskResult(
            success=True,
            output=f"Task ready for execution with confidence {confidence:.2f}. Approve to proceed.",
            confidence=confidence,
            action_taken="pending_approval",
            requires_approval=True,
            details={
                "rag_context": rag_context,
                "recommendation": "proceed" if confidence > 0.5 else "review"
            }
        )

    async def _log_decision(
        self,
        session: SessionContext,
        decision_type: str,
        decision: str,
        reasoning: str,
        confidence: float,
        **kwargs
    ) -> None:
        """Log agent decision for learning."""
        rag = self._get_rag_store()
        if rag:
            try:
                await rag.log_agent_decision(
                    agent="manager",
                    decision_type=decision_type,
                    context={
                        "session_id": session.session_id,
                        "current_task": session.current_task,
                        "tasks_completed": len(session.tasks_completed),
                        **kwargs
                    },
                    decision=decision,
                    reasoning=reasoning,
                    confidence=confidence,
                    rag_hits=kwargs.get("rag_hits"),
                    rag_similarity=kwargs.get("rag_similarity"),
                    session_id=session.session_id
                )
            except Exception as e:
                logger.warning(f"Failed to log decision: {e}")


# Singleton instance
_manager_agent: Optional[ManagerAgent] = None


def get_manager_agent() -> ManagerAgent:
    """Get or create the default Manager Agent singleton."""
    global _manager_agent
    if _manager_agent is None:
        _manager_agent = ManagerAgent()
    return _manager_agent


__version__ = "1.0.0"
__all__ = ["ManagerAgent", "get_manager_agent", "SessionContext", "TaskResult"]
