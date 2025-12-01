"""
Qubinode Multi-Agent System
ADR-0049: Multi-Agent LLM Memory Architecture

This package implements the hierarchical multi-agent system for
intelligent DAG development and troubleshooting.

Architecture:
    Calling LLM (Claude/GPT-4) - User interface, override authority
        ↓
    Manager LLM (Granite) - Orchestration, session context
        ↓
    Developer Agent (Granite + Aider) - Code generation, RAG-augmented

Core Policies:
    1. Confidence & RAG Enrichment
    2. Provider-First Rule
    3. Missing Provider → Plan, Not Code
    4. Calling LLM Override Authority

Note: This module is loaded lazily to avoid import errors when loaded
by Airflow's plugin manager (which doesn't set up proper package context).
"""

__version__ = "1.0.0"
__all__ = [
    "ManagerAgent",
    "DeveloperAgent",
    "ConfidenceScorer",
    "PolicyEngine",
    "ConfidencePolicy",
    "ProviderFirstPolicy",
    "MissingProviderPolicy",
    "OverridePolicy",
]

# Lazy imports to avoid relative import errors when loaded by Airflow plugin manager
def __getattr__(name):
    """Lazy load agents module components."""
    if name == "ManagerAgent":
        from qubinode.agents.manager_agent import ManagerAgent
        return ManagerAgent
    elif name == "DeveloperAgent":
        from qubinode.agents.developer_agent import DeveloperAgent
        return DeveloperAgent
    elif name == "ConfidenceScorer":
        from qubinode.agents.confidence_scorer import ConfidenceScorer
        return ConfidenceScorer
    elif name == "PolicyEngine":
        from qubinode.agents.policies import PolicyEngine
        return PolicyEngine
    elif name == "ConfidencePolicy":
        from qubinode.agents.policies import ConfidencePolicy
        return ConfidencePolicy
    elif name == "ProviderFirstPolicy":
        from qubinode.agents.policies import ProviderFirstPolicy
        return ProviderFirstPolicy
    elif name == "MissingProviderPolicy":
        from qubinode.agents.policies import MissingProviderPolicy
        return MissingProviderPolicy
    elif name == "OverridePolicy":
        from qubinode.agents.policies import OverridePolicy
        return OverridePolicy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
