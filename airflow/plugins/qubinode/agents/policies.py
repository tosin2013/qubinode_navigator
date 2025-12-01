"""
Policy Engine for Qubinode Multi-Agent System
ADR-0049: Multi-Agent LLM Memory Architecture

Implements the four core policies that govern agent behavior:

1. Confidence & RAG Enrichment Policy
   - Don't guess: use RAG for context
   - Low confidence triggers escalation

2. Provider-First Policy
   - Always check for official Airflow providers
   - Use providers over custom implementations

3. Missing Provider Policy
   - No provider? Generate plan, not code
   - Escalate to Calling LLM for guidance

4. Override Policy
   - Calling LLM has ultimate authority
   - Can override any agent decision

Usage:
    from qubinode.agents import PolicyEngine

    engine = PolicyEngine()
    result = await engine.apply_policies(
        task="Create FreeIPA deployment DAG",
        rag_context=rag_context,
        provider_check=provider_check,
        confidence=0.75
    )
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class PolicyResult(Enum):
    """Result of policy evaluation."""
    ALLOW = "allow"           # Policy allows execution
    DENY = "deny"             # Policy blocks execution
    ESCALATE = "escalate"     # Escalate to higher authority
    PLAN = "plan"             # Generate plan instead of executing
    OVERRIDE = "override"     # Override from Calling LLM


@dataclass
class PolicyEvaluation:
    """Result of a single policy evaluation."""
    policy_name: str
    result: PolicyResult
    confidence: float
    reason: str
    recommendations: List[str]
    metadata: Dict[str, Any]


@dataclass
class PolicyEngineResult:
    """Combined result from all policy evaluations."""
    final_action: PolicyResult
    evaluations: List[PolicyEvaluation]
    overall_confidence: float
    should_execute: bool
    requires_approval: bool
    message: str


class Policy(ABC):
    """Abstract base class for policies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Policy name."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Policy priority (higher = evaluated first)."""
        pass

    @abstractmethod
    async def evaluate(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> PolicyEvaluation:
        """
        Evaluate the policy for a given task.

        Args:
            task: Task description
            context: Evaluation context including RAG, provider info, etc.

        Returns:
            PolicyEvaluation result
        """
        pass


class ConfidencePolicy(Policy):
    """
    Policy 1: Confidence & RAG Enrichment

    - Require RAG context for all decisions
    - Escalate when confidence is below threshold
    - Don't guess - ask for documentation
    """

    CONFIDENCE_THRESHOLD = 0.4

    @property
    def name(self) -> str:
        return "confidence_and_rag"

    @property
    def priority(self) -> int:
        return 100  # High priority

    async def evaluate(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> PolicyEvaluation:
        confidence = context.get("confidence", 0)
        rag_context = context.get("rag_context", {})
        rag_hits = len(rag_context.get("documents", []))

        recommendations = []

        # Check if RAG was consulted
        if rag_hits == 0:
            recommendations.append("Ingest relevant documentation into RAG")
            recommendations.append("Search for similar DAG examples")
            return PolicyEvaluation(
                policy_name=self.name,
                result=PolicyResult.ESCALATE,
                confidence=confidence,
                reason="No RAG context available - cannot make informed decision",
                recommendations=recommendations,
                metadata={"rag_hits": rag_hits}
            )

        # Check confidence threshold
        if confidence < self.CONFIDENCE_THRESHOLD:
            recommendations.append("Provide more documentation about this task")
            recommendations.append("Consider providing explicit override instruction")
            return PolicyEvaluation(
                policy_name=self.name,
                result=PolicyResult.ESCALATE,
                confidence=confidence,
                reason=f"Confidence {confidence:.2f} below threshold {self.CONFIDENCE_THRESHOLD}",
                recommendations=recommendations,
                metadata={"threshold": self.CONFIDENCE_THRESHOLD, "rag_hits": rag_hits}
            )

        return PolicyEvaluation(
            policy_name=self.name,
            result=PolicyResult.ALLOW,
            confidence=confidence,
            reason=f"Confidence {confidence:.2f} acceptable with {rag_hits} RAG hits",
            recommendations=[],
            metadata={"rag_hits": rag_hits}
        )


class ProviderFirstPolicy(Policy):
    """
    Policy 2: Provider-First Rule

    - Always check for official Airflow providers
    - Prefer provider operators over custom implementations
    - Document which provider is being used
    """

    @property
    def name(self) -> str:
        return "provider_first"

    @property
    def priority(self) -> int:
        return 90  # High priority

    async def evaluate(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> PolicyEvaluation:
        provider_check = context.get("provider_check", {})
        provider_exists = provider_check.get("provider_exists", False)
        provider_name = provider_check.get("provider_name")
        system = provider_check.get("system")

        if provider_exists and provider_name:
            return PolicyEvaluation(
                policy_name=self.name,
                result=PolicyResult.ALLOW,
                confidence=1.0,
                reason=f"Using official provider: {provider_name}",
                recommendations=[f"Import from {provider_name}"],
                metadata={"provider": provider_name, "system": system}
            )

        if system and not provider_exists:
            # System detected but no provider
            return PolicyEvaluation(
                policy_name=self.name,
                result=PolicyResult.PLAN,
                confidence=0.6,
                reason=f"No official provider for {system} - plan required",
                recommendations=[
                    f"Research if {system} has an Airflow provider",
                    "Consider creating custom operator",
                    "Use BashOperator as fallback"
                ],
                metadata={"system": system, "provider_available": False}
            )

        # No system detected in task
        return PolicyEvaluation(
            policy_name=self.name,
            result=PolicyResult.ALLOW,
            confidence=0.8,
            reason="No specific system integration required",
            recommendations=[],
            metadata={}
        )


class MissingProviderPolicy(Policy):
    """
    Policy 3: Missing Provider → Plan, Not Code

    - When no provider exists, generate implementation plan
    - Don't generate code without proper provider support
    - Escalate for guidance on implementation approach
    """

    @property
    def name(self) -> str:
        return "missing_provider"

    @property
    def priority(self) -> int:
        return 80  # Medium-high priority

    async def evaluate(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> PolicyEvaluation:
        provider_check = context.get("provider_check", {})
        provider_exists = provider_check.get("provider_exists", False)
        system = provider_check.get("system")

        if not system:
            # No specific system - policy doesn't apply
            return PolicyEvaluation(
                policy_name=self.name,
                result=PolicyResult.ALLOW,
                confidence=1.0,
                reason="No system-specific integration required",
                recommendations=[],
                metadata={}
            )

        if provider_exists:
            # Provider exists - use it
            return PolicyEvaluation(
                policy_name=self.name,
                result=PolicyResult.ALLOW,
                confidence=1.0,
                reason="Provider available - proceeding with implementation",
                recommendations=[],
                metadata={"system": system}
            )

        # Missing provider - generate plan
        return PolicyEvaluation(
            policy_name=self.name,
            result=PolicyResult.PLAN,
            confidence=0.5,
            reason=f"No Airflow provider for {system} - generating plan instead of code",
            recommendations=[
                f"Generate implementation plan for {system} integration",
                "Document prerequisites and dependencies",
                "Request approval before code generation",
                "Consider SSH/REST API approach"
            ],
            metadata={
                "system": system,
                "suggested_approach": "plan_then_implement",
                "fallback_operators": ["BashOperator", "PythonOperator", "SSHOperator"]
            }
        )


class OverridePolicy(Policy):
    """
    Policy 4: Calling LLM Override Authority

    - Calling LLM can override any decision
    - Override bypasses all other policies
    - Must be logged for audit
    """

    @property
    def name(self) -> str:
        return "override_authority"

    @property
    def priority(self) -> int:
        return 200  # Highest priority

    async def evaluate(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> PolicyEvaluation:
        override = context.get("override")

        if override:
            return PolicyEvaluation(
                policy_name=self.name,
                result=PolicyResult.OVERRIDE,
                confidence=1.0,
                reason="Calling LLM override received - executing directly",
                recommendations=["Log override for audit trail"],
                metadata={"override_instruction": override[:200]}
            )

        return PolicyEvaluation(
            policy_name=self.name,
            result=PolicyResult.ALLOW,
            confidence=1.0,
            reason="No override present - proceeding with normal evaluation",
            recommendations=[],
            metadata={}
        )


class PolicyEngine:
    """
    Engine for evaluating all policies and determining final action.

    Policies are evaluated in priority order. Special results like
    OVERRIDE and ESCALATE can short-circuit evaluation.
    """

    def __init__(self, policies: Optional[List[Policy]] = None):
        """
        Initialize the policy engine.

        Args:
            policies: Custom list of policies (uses defaults if None)
        """
        if policies is None:
            self.policies = [
                OverridePolicy(),      # Priority 200 - checked first
                ConfidencePolicy(),    # Priority 100
                ProviderFirstPolicy(), # Priority 90
                MissingProviderPolicy() # Priority 80
            ]
        else:
            self.policies = policies

        # Sort by priority (descending)
        self.policies.sort(key=lambda p: p.priority, reverse=True)
        logger.info(f"PolicyEngine initialized with {len(self.policies)} policies")

    async def apply_policies(
        self,
        task: str,
        rag_context: Dict[str, Any],
        provider_check: Dict[str, Any],
        confidence: float,
        override: Optional[str] = None
    ) -> PolicyEngineResult:
        """
        Apply all policies to a task.

        Args:
            task: Task description
            rag_context: RAG query results
            provider_check: Provider availability check
            confidence: Computed confidence score
            override: Optional override instruction

        Returns:
            PolicyEngineResult with final action
        """
        context = {
            "rag_context": rag_context,
            "provider_check": provider_check,
            "confidence": confidence,
            "override": override
        }

        evaluations: List[PolicyEvaluation] = []
        final_action = PolicyResult.ALLOW

        for policy in self.policies:
            try:
                evaluation = await policy.evaluate(task, context)
                evaluations.append(evaluation)

                logger.debug(f"Policy {policy.name}: {evaluation.result.value}")

                # Check for short-circuit conditions
                if evaluation.result == PolicyResult.OVERRIDE:
                    final_action = PolicyResult.OVERRIDE
                    break
                elif evaluation.result == PolicyResult.ESCALATE:
                    final_action = PolicyResult.ESCALATE
                    break
                elif evaluation.result == PolicyResult.PLAN:
                    final_action = PolicyResult.PLAN
                    # Don't break - continue evaluating other policies
                elif evaluation.result == PolicyResult.DENY:
                    final_action = PolicyResult.DENY
                    break

            except Exception as e:
                logger.error(f"Policy {policy.name} evaluation failed: {e}")
                evaluations.append(PolicyEvaluation(
                    policy_name=policy.name,
                    result=PolicyResult.DENY,
                    confidence=0,
                    reason=f"Policy evaluation error: {e}",
                    recommendations=["Investigate policy error"],
                    metadata={"error": str(e)}
                ))

        # Determine final state
        should_execute = final_action in [PolicyResult.ALLOW, PolicyResult.OVERRIDE]
        requires_approval = final_action in [PolicyResult.PLAN, PolicyResult.ESCALATE]

        # Build message
        message = self._build_result_message(final_action, evaluations)

        return PolicyEngineResult(
            final_action=final_action,
            evaluations=evaluations,
            overall_confidence=confidence,
            should_execute=should_execute,
            requires_approval=requires_approval,
            message=message
        )

    def _build_result_message(
        self,
        final_action: PolicyResult,
        evaluations: List[PolicyEvaluation]
    ) -> str:
        """Build human-readable result message."""
        messages = {
            PolicyResult.ALLOW: "All policies passed - ready to execute",
            PolicyResult.DENY: "Policy blocked execution - see evaluations for details",
            PolicyResult.ESCALATE: "Escalating to Calling LLM for guidance",
            PolicyResult.PLAN: "Generating implementation plan instead of code",
            PolicyResult.OVERRIDE: "Executing Calling LLM override instruction"
        }

        base_message = messages.get(final_action, "Unknown policy result")

        # Add recommendations from failed policies
        recommendations = []
        for eval in evaluations:
            if eval.result != PolicyResult.ALLOW:
                recommendations.extend(eval.recommendations)

        if recommendations:
            base_message += "\n\nRecommendations:\n"
            for rec in recommendations[:5]:  # Limit to 5
                base_message += f"- {rec}\n"

        return base_message

    async def check_single_policy(
        self,
        policy_name: str,
        task: str,
        context: Dict[str, Any]
    ) -> Optional[PolicyEvaluation]:
        """
        Check a single policy by name.

        Args:
            policy_name: Name of policy to check
            task: Task description
            context: Evaluation context

        Returns:
            PolicyEvaluation or None if policy not found
        """
        for policy in self.policies:
            if policy.name == policy_name:
                return await policy.evaluate(task, context)
        return None


# Singleton instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create the default PolicyEngine singleton."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine


__version__ = "1.0.0"
__all__ = [
    "PolicyEngine",
    "Policy",
    "PolicyResult",
    "PolicyEvaluation",
    "PolicyEngineResult",
    "ConfidencePolicy",
    "ProviderFirstPolicy",
    "MissingProviderPolicy",
    "OverridePolicy",
    "get_policy_engine"
]
