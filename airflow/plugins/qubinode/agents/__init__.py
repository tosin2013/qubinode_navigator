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
"""

from .manager_agent import ManagerAgent
from .developer_agent import DeveloperAgent
from .confidence_scorer import ConfidenceScorer
from .policies import (
    PolicyEngine,
    ConfidencePolicy,
    ProviderFirstPolicy,
    MissingProviderPolicy,
    OverridePolicy
)

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
