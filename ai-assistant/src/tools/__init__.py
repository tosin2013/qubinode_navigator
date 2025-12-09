"""
Tools module for Qubinode AI Assistant.

Provides various tools for agent capabilities:
- Web search (via PydanticAI DuckDuckGo)
- Code generation (via Aider)
- RAG retrieval
"""

from .web_search import (
    DUCKDUCKGO_AVAILABLE,
    SMOLAGENTS_AVAILABLE,  # Backwards compatibility alias
    WebSearchService,
    SearchResult,
    quick_search,
    search_airflow_docs,
    search_kubernetes_docs,
    search_openshift_docs,
    get_search_tool,
    create_search_enabled_agent_tools,
)

__all__ = [
    # Availability flags
    "DUCKDUCKGO_AVAILABLE",
    "SMOLAGENTS_AVAILABLE",  # Backwards compatibility
    # Web search
    "WebSearchService",
    "SearchResult",
    "quick_search",
    "search_airflow_docs",
    "search_kubernetes_docs",
    "search_openshift_docs",
    # Agent integration
    "get_search_tool",
    "create_search_enabled_agent_tools",
]
