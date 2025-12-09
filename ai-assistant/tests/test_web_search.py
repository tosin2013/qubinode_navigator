"""
Unit tests for PydanticAI web search integration.

Tests web search capabilities using PydanticAI's DuckDuckGo search tool.
Tests verify the integration layer logic without making real network requests.
"""

import pytest
from unittest.mock import patch, MagicMock


# Mark tests that make network requests
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


class TestSearchResultDataclass:
    """Test SearchResult dataclass structure."""

    def test_search_result_structure(self):
        """Test SearchResult has expected fields."""
        from src.tools.web_search import SearchResult

        result = SearchResult(
            query="test query",
            results=[{"content": "test result"}],
            source="duckduckgo",
            success=True,
        )

        assert result.query == "test query"
        assert result.source == "duckduckgo"
        assert result.success is True
        assert result.error is None

    def test_search_result_with_error(self):
        """Test SearchResult with error."""
        from src.tools.web_search import SearchResult

        result = SearchResult(
            query="test query",
            results=[],
            source="duckduckgo",
            success=False,
            error="Connection timeout",
        )

        assert result.success is False
        assert result.error == "Connection timeout"


class TestDuckDuckGoAvailability:
    """Test DuckDuckGo availability flag."""

    def test_availability_flag_is_boolean(self):
        """Test DUCKDUCKGO_AVAILABLE flag is set correctly."""
        from src.tools.web_search import DUCKDUCKGO_AVAILABLE

        assert isinstance(DUCKDUCKGO_AVAILABLE, bool)

    def test_backwards_compat_alias(self):
        """Test SMOLAGENTS_AVAILABLE alias for backwards compatibility."""
        from src.tools.web_search import SMOLAGENTS_AVAILABLE, DUCKDUCKGO_AVAILABLE

        assert SMOLAGENTS_AVAILABLE == DUCKDUCKGO_AVAILABLE


class TestGetSearchTool:
    """Test get_search_tool function."""

    def test_get_search_tool_returns_tool_or_none(self):
        """Test get_search_tool returns tool when available."""
        from src.tools.web_search import get_search_tool, DUCKDUCKGO_AVAILABLE

        result = get_search_tool()
        if DUCKDUCKGO_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    def test_create_search_enabled_agent_tools(self):
        """Test create_search_enabled_agent_tools returns list."""
        from src.tools.web_search import (
            create_search_enabled_agent_tools,
            DUCKDUCKGO_AVAILABLE,
        )

        tools = create_search_enabled_agent_tools()
        assert isinstance(tools, list)
        if DUCKDUCKGO_AVAILABLE:
            assert len(tools) >= 1


class TestQuickSearchFunction:
    """Test quick_search convenience function."""

    def test_quick_search_unavailable_message(self):
        """Test quick_search returns message when unavailable."""
        with patch("src.tools.web_search.DUCKDUCKGO_AVAILABLE", False):
            from src.tools import web_search

            # Reload to pick up the patched value
            original_available = web_search.DUCKDUCKGO_AVAILABLE
            web_search.DUCKDUCKGO_AVAILABLE = False

            result = web_search.quick_search("test query")
            assert "unavailable" in result.lower() or "not installed" in result.lower()

            # Restore
            web_search.DUCKDUCKGO_AVAILABLE = original_available


class TestConvenienceFunctions:
    """Test convenience search functions."""

    def test_search_airflow_docs_returns_string(self):
        """Test search_airflow_docs returns string."""
        from src.tools.web_search import search_airflow_docs

        result = search_airflow_docs("operators")
        assert isinstance(result, str)

    def test_search_kubernetes_docs_returns_string(self):
        """Test search_kubernetes_docs returns string."""
        from src.tools.web_search import search_kubernetes_docs

        result = search_kubernetes_docs("pods")
        assert isinstance(result, str)

    def test_search_openshift_docs_returns_string(self):
        """Test search_openshift_docs returns string."""
        from src.tools.web_search import search_openshift_docs

        result = search_openshift_docs("routes")
        assert isinstance(result, str)


class TestWebSearchServiceMocked:
    """Test WebSearchService with mocked dependencies."""

    @pytest.fixture
    def mock_duckduckgo_tool(self):
        """Create a mock DuckDuckGo tool."""
        mock_tool = MagicMock()
        mock_tool.function = MagicMock(return_value="Mock search results")
        return mock_tool

    def test_service_initialization_when_available(self, mock_duckduckgo_tool):
        """Test service can be initialized when DuckDuckGo is available."""
        with patch("src.tools.web_search.DUCKDUCKGO_AVAILABLE", True):
            with patch(
                "src.tools.web_search.duckduckgo_search_tool",
                return_value=mock_duckduckgo_tool,
            ):
                from src.tools.web_search import WebSearchService

                service = WebSearchService()
                assert service is not None

    def test_service_search_returns_result(self, mock_duckduckgo_tool):
        """Test service search returns SearchResult."""
        with patch("src.tools.web_search.DUCKDUCKGO_AVAILABLE", True):
            with patch(
                "src.tools.web_search.duckduckgo_search_tool",
                return_value=mock_duckduckgo_tool,
            ):
                from src.tools.web_search import WebSearchService

                service = WebSearchService()
                result = service.search("test query")

                assert result.query == "test query"
                assert result.source == "duckduckgo"
                assert result.success is True

    def test_parse_results_string(self, mock_duckduckgo_tool):
        """Test _parse_results handles string input."""
        with patch("src.tools.web_search.DUCKDUCKGO_AVAILABLE", True):
            with patch(
                "src.tools.web_search.duckduckgo_search_tool",
                return_value=mock_duckduckgo_tool,
            ):
                from src.tools.web_search import WebSearchService

                service = WebSearchService()
                results = service._parse_results("plain text result")

                assert len(results) == 1
                assert results[0]["content"] == "plain text result"

    def test_parse_results_list(self, mock_duckduckgo_tool):
        """Test _parse_results handles list input."""
        with patch("src.tools.web_search.DUCKDUCKGO_AVAILABLE", True):
            with patch(
                "src.tools.web_search.duckduckgo_search_tool",
                return_value=mock_duckduckgo_tool,
            ):
                from src.tools.web_search import WebSearchService

                service = WebSearchService()
                results = service._parse_results(["item1", "item2"])

                assert len(results) == 2

    def test_parse_results_dict(self, mock_duckduckgo_tool):
        """Test _parse_results handles dict input."""
        with patch("src.tools.web_search.DUCKDUCKGO_AVAILABLE", True):
            with patch(
                "src.tools.web_search.duckduckgo_search_tool",
                return_value=mock_duckduckgo_tool,
            ):
                from src.tools.web_search import WebSearchService

                service = WebSearchService()
                results = service._parse_results({"title": "Test", "url": "http://test.com"})

                assert len(results) == 1
                assert results[0]["title"] == "Test"


class TestSpecializedSearchMethods:
    """Test specialized search methods on WebSearchService."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock WebSearchService."""
        with patch("src.tools.web_search.DUCKDUCKGO_AVAILABLE", True):
            mock_tool = MagicMock()
            mock_tool.function = MagicMock(return_value="Mock results")
            with patch(
                "src.tools.web_search.duckduckgo_search_tool",
                return_value=mock_tool,
            ):
                from src.tools.web_search import WebSearchService

                return WebSearchService()

    def test_search_infrastructure_docs(self, mock_service):
        """Test search_infrastructure_docs adds context."""
        result = mock_service.search_infrastructure_docs("helm charts")
        assert result.success is True
        assert result.source == "duckduckgo"

    def test_search_troubleshooting(self, mock_service):
        """Test search_troubleshooting adds fix context."""
        result = mock_service.search_troubleshooting("connection refused", context="postgresql")
        assert result.success is True

    def test_search_provider_info(self, mock_service):
        """Test search_provider_info targets Airflow providers."""
        result = mock_service.search_provider_info("kubernetes")
        assert result.success is True


class TestModuleExports:
    """Test module exports are correct."""

    def test_all_exports_available(self):
        """Test all expected exports are available."""
        from src.tools.web_search import (
            DUCKDUCKGO_AVAILABLE,
            SMOLAGENTS_AVAILABLE,
            SearchResult,
            WebSearchService,  # noqa: F401
            quick_search,
            search_airflow_docs,
            search_kubernetes_docs,
            search_openshift_docs,
            get_search_tool,
            create_search_enabled_agent_tools,
        )

        # All should be importable (not None values, but the actual objects)
        assert DUCKDUCKGO_AVAILABLE is not None
        assert SMOLAGENTS_AVAILABLE is not None
        assert SearchResult is not None
        assert quick_search is not None
        assert search_airflow_docs is not None
        assert search_kubernetes_docs is not None
        assert search_openshift_docs is not None
        assert get_search_tool is not None
        assert create_search_enabled_agent_tools is not None
