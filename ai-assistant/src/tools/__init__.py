"""
Tools module for Qubinode AI Assistant.

Provides various tools for agent capabilities:
- Web search (via Smolagents)
- Code generation (via Aider)
- RAG retrieval
"""

from .web_search import (
    SMOLAGENTS_AVAILABLE,
    WebSearchService,
    SearchResult,
    quick_search,
    search_airflow_docs,
    search_kubernetes_docs,
    search_openshift_docs,
)

__all__ = [
    # Availability flags
    "SMOLAGENTS_AVAILABLE",
    # Web search
    "WebSearchService",
    "SearchResult",
    "quick_search",
    "search_airflow_docs",
    "search_kubernetes_docs",
    "search_openshift_docs",
]
