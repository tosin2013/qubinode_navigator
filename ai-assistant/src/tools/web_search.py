"""
Smolagents Web Search Integration for Qubinode AI Assistant.

Provides web search capabilities using Smolagents' DuckDuckGoSearchTool
or WebSearchTool for research and information retrieval tasks.

Per ADR-0063: Smolagents complements PydanticAI + Aider architecture
by providing web search capabilities for:
- Researching infrastructure documentation
- Finding troubleshooting guides
- Validating deployment procedures
- Discovering provider-specific configurations
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check Smolagents availability
try:
    from smolagents import (
        CodeAgent,
        ToolCallingAgent,  # noqa: F401
        InferenceClientModel,
        DuckDuckGoSearchTool,
        WebSearchTool,
        Tool,
    )

    SMOLAGENTS_AVAILABLE = True
except ImportError:
    SMOLAGENTS_AVAILABLE = False
    logger.warning("Smolagents not installed. Web search features unavailable.")


@dataclass
class SearchResult:
    """Structured web search result."""

    query: str
    results: List[Dict[str, str]]
    source: str  # 'duckduckgo' or 'web'
    success: bool
    error: Optional[str] = None


class WebSearchService:
    """
    Web search service using Smolagents.

    Provides both simple search tool access and agent-based
    multi-step research capabilities.

    Example:
        >>> service = WebSearchService()
        >>> result = service.search("airflow provider for kubernetes")
        >>> print(result.results)
    """

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-Coder-32B-Instruct",
        use_duckduckgo: bool = True,
    ):
        """
        Initialize web search service.

        Args:
            model_id: HuggingFace model ID for agent-based search
            use_duckduckgo: Use DuckDuckGo (True) or general WebSearch (False)
        """
        if not SMOLAGENTS_AVAILABLE:
            raise ImportError("Smolagents is required for web search. " "Install with: pip install 'smolagents[toolkit]'")

        self.model_id = model_id
        self.use_duckduckgo = use_duckduckgo

        # Initialize search tool
        if use_duckduckgo:
            self._search_tool = DuckDuckGoSearchTool()
        else:
            self._search_tool = WebSearchTool()

        # Lazy-init agent (only when needed for complex queries)
        self._agent: Optional[CodeAgent] = None

    @property
    def search_tool(self) -> Tool:
        """Get the underlying search tool."""
        return self._search_tool

    def search(self, query: str) -> SearchResult:
        """
        Perform a simple web search.

        Args:
            query: Search query string

        Returns:
            SearchResult with search results
        """
        try:
            raw_result = self._search_tool(query)

            # Parse results (format depends on tool)
            results = self._parse_results(raw_result)

            return SearchResult(
                query=query,
                results=results,
                source="duckduckgo" if self.use_duckduckgo else "web",
                success=True,
            )
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return SearchResult(
                query=query,
                results=[],
                source="duckduckgo" if self.use_duckduckgo else "web",
                success=False,
                error=str(e),
            )

    def _parse_results(self, raw_result: Any) -> List[Dict[str, str]]:
        """Parse raw search results into structured format."""
        if isinstance(raw_result, str):
            # Text result - split into items
            return [{"content": raw_result}]
        elif isinstance(raw_result, list):
            return [{"content": str(item)} if not isinstance(item, dict) else item for item in raw_result]
        elif isinstance(raw_result, dict):
            return [raw_result]
        else:
            return [{"content": str(raw_result)}]

    def _get_agent(self) -> CodeAgent:
        """Get or create the search agent."""
        if self._agent is None:
            model = InferenceClientModel(model_id=self.model_id)
            self._agent = CodeAgent(
                tools=[self._search_tool],
                model=model,
                max_steps=5,
            )
        return self._agent

    def research(self, question: str) -> str:
        """
        Perform multi-step research using agent.

        This uses the CodeAgent to perform iterative searches
        and synthesize information from multiple sources.

        Args:
            question: Research question

        Returns:
            Synthesized answer from research
        """
        try:
            agent = self._get_agent()
            result = agent.run(question)
            return str(result)
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return f"Research failed: {e}"

    def search_infrastructure_docs(self, topic: str) -> SearchResult:
        """
        Search for infrastructure documentation.

        Specialized search for Airflow, Kubernetes, OpenShift,
        and other infrastructure topics.

        Args:
            topic: Infrastructure topic to search

        Returns:
            SearchResult with relevant documentation
        """
        # Add context for infrastructure searches
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
    Quick web search returning text result.

    Args:
        query: Search query

    Returns:
        Search results as text
    """
    if not SMOLAGENTS_AVAILABLE:
        return "Web search unavailable: smolagents not installed"

    try:
        tool = DuckDuckGoSearchTool()
        return str(tool(query))
    except Exception as e:
        return f"Search failed: {e}"


def search_airflow_docs(topic: str) -> str:
    """
    Search Airflow documentation.

    Args:
        topic: Topic to search in Airflow docs

    Returns:
        Relevant documentation snippets
    """
    return quick_search(f"apache airflow {topic} documentation")


def search_kubernetes_docs(topic: str) -> str:
    """
    Search Kubernetes documentation.

    Args:
        topic: Topic to search in K8s docs

    Returns:
        Relevant documentation snippets
    """
    return quick_search(f"kubernetes {topic} documentation official")


def search_openshift_docs(topic: str) -> str:
    """
    Search OpenShift documentation.

    Args:
        topic: Topic to search in OpenShift docs

    Returns:
        Relevant documentation snippets
    """
    return quick_search(f"red hat openshift {topic} documentation")
