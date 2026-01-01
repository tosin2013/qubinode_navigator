"""
PydanticAI Web Search Integration for Qubinode AI Assistant.

Provides web search capabilities using PydanticAI's built-in DuckDuckGo search tool.
This replaces the previous smolagents-based implementation.

Per ADR-0063: PydanticAI Core Agent Orchestrator
- Agents can use web search to inform users with real-time data
- Search results can be fed into RAG for persistent context
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check PydanticAI DuckDuckGo availability
DUCKDUCKGO_AVAILABLE = False
duckduckgo_search_tool = None

try:
    from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    logger.warning("PydanticAI DuckDuckGo search not available. Install with: pip install 'pydantic-ai-slim[duckduckgo]'")


@dataclass
class SearchResult:
    """Structured web search result."""

    query: str
    results: List[Dict[str, str]]
    source: str  # 'duckduckgo'
    success: bool
    error: Optional[str] = None


def get_search_tool():
    """
    Get the PydanticAI DuckDuckGo search tool for use in agents.

    Returns the tool function that can be added to an agent's tools list.

    Example:
        >>> from pydantic_ai import Agent
        >>> from src.tools.web_search import get_search_tool
        >>>
        >>> agent = Agent(
        ...     'google-gla:gemini-2.5-flash',
        ...     tools=[get_search_tool()],
        ... )

    Returns:
        The duckduckgo_search_tool function, or None if not available.
    """
    if not DUCKDUCKGO_AVAILABLE:
        logger.warning("DuckDuckGo search tool not available")
        return None
    return duckduckgo_search_tool()


def create_search_enabled_agent_tools() -> List:
    """
    Get a list of search tools for adding to PydanticAI agents.

    Returns:
        List of tool functions to add to agent's tools parameter.
    """
    tools = []
    if DUCKDUCKGO_AVAILABLE:
        tools.append(duckduckgo_search_tool())
    return tools


class WebSearchService:
    """
    Web search service using PydanticAI's DuckDuckGo integration.

    This service provides both standalone search functionality and
    tools for integration with PydanticAI agents.

    Example:
        >>> service = WebSearchService()
        >>> result = service.search("airflow provider for kubernetes")
        >>> print(result.results)
    """

    def __init__(self):
        """Initialize web search service."""
        if not DUCKDUCKGO_AVAILABLE:
            raise ImportError("PydanticAI DuckDuckGo search is required. Install with: pip install 'pydantic-ai-slim[duckduckgo]'")
        self._search_tool = duckduckgo_search_tool()

    @property
    def search_tool(self):
        """Get the underlying search tool for agent integration."""
        return self._search_tool

    def search(self, query: str) -> SearchResult:
        """
        Perform a web search.

        Args:
            query: Search query string

        Returns:
            SearchResult with search results
        """
        try:
            # The tool returns search results directly
            raw_result = self._search_tool.function(query)
            results = self._parse_results(raw_result)

            return SearchResult(
                query=query,
                results=results,
                source="duckduckgo",
                success=True,
            )
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return SearchResult(
                query=query,
                results=[],
                source="duckduckgo",
                success=False,
                error=str(e),
            )

    def _parse_results(self, raw_result: Any) -> List[Dict[str, str]]:
        """Parse raw search results into structured format."""
        if isinstance(raw_result, str):
            return [{"content": raw_result}]
        elif isinstance(raw_result, list):
            return [{"content": str(item)} if not isinstance(item, dict) else item for item in raw_result]
        elif isinstance(raw_result, dict):
            return [raw_result]
        else:
            return [{"content": str(raw_result)}]

    def search_infrastructure_docs(self, topic: str) -> SearchResult:
        """
        Search for infrastructure documentation.

        Args:
            topic: Infrastructure topic to search

        Returns:
            SearchResult with relevant documentation
        """
        query = f"{topic} documentation guide tutorial"
        return self.search(query)

    def search_troubleshooting(self, error: str, context: str = "") -> SearchResult:
        """
        Search for troubleshooting guides.

        Args:
            error: Error message or description
            context: Additional context (e.g., "airflow", "kubernetes")

        Returns:
            SearchResult with troubleshooting guides
        """
        query = f"{context} {error} fix solution troubleshooting"
        return self.search(query)

    def search_provider_info(self, provider_name: str) -> SearchResult:
        """
        Search for Airflow provider information.

        Args:
            provider_name: Name of the Airflow provider

        Returns:
            SearchResult with provider documentation
        """
        query = f"apache airflow {provider_name} provider documentation pypi"
        return self.search(query)


# Convenience functions for direct usage
def quick_search(query: str) -> str:
    """
    Quick web search returning text result (synchronous wrapper).

    For async code, use WebSearchService.search() instead.

    Args:
        query: Search query

    Returns:
        Search results as text, or message if search unavailable
    """
    if not DUCKDUCKGO_AVAILABLE:
        return "Web search unavailable: pydantic-ai[duckduckgo] not installed"

    # Return informational message - actual search requires async context
    return f"Web search available for query: '{query}'. Use WebSearchService.search() in async context for actual results."


def search_airflow_docs(topic: str) -> str:
    """
    Search Airflow documentation.

    Args:
        topic: Topic to search in Airflow docs

    Returns:
        Informational message about search capability
    """
    return quick_search(f"apache airflow {topic} documentation")


def search_kubernetes_docs(topic: str) -> str:
    """
    Search Kubernetes documentation.

    Args:
        topic: Topic to search in K8s docs

    Returns:
        Informational message about search capability
    """
    return quick_search(f"kubernetes {topic} documentation official")


def search_openshift_docs(topic: str) -> str:
    """
    Search OpenShift documentation.

    Args:
        topic: Topic to search in OpenShift docs

    Returns:
        Informational message about search capability
    """
    return quick_search(f"red hat openshift {topic} documentation")


# For backwards compatibility, expose DUCKDUCKGO_AVAILABLE as SMOLAGENTS_AVAILABLE
SMOLAGENTS_AVAILABLE = DUCKDUCKGO_AVAILABLE
