"""
Unit tests for Smolagents web search integration.

Tests web search capabilities without making real network requests
by mocking the underlying search tools.

Note: Some tests verify actual search functionality when smolagents
is available. Mocked tests verify the integration layer logic.
"""

import pytest
from unittest.mock import patch, MagicMock


# Mark tests that make network requests
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


class TestSearchResultDataclass:
    """Test SearchResult dataclass structure."""

    def test_search_result_structure(self):
        """Test SearchResult has expected fields."""
        # Import conditionally to handle missing smolagents
        try:
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
        except ImportError:
            pytest.skip("smolagents not installed")

    def test_search_result_with_error(self):
        """Test SearchResult with error."""
        try:
            from src.tools.web_search import SearchResult

            result = SearchResult(
                query="test query",
                results=[],
                source="web",
                success=False,
                error="Connection timeout",
            )

            assert result.success is False
            assert result.error == "Connection timeout"
        except ImportError:
            pytest.skip("smolagents not installed")


class TestWebSearchServiceMocked:
    """Test WebSearchService with mocked smolagents."""

    def test_smolagents_availability_flag(self):
        """Test SMOLAGENTS_AVAILABLE flag is set correctly."""
        from src.tools.web_search import SMOLAGENTS_AVAILABLE

        # Flag should be boolean
        assert isinstance(SMOLAGENTS_AVAILABLE, bool)

    @patch("src.tools.web_search.SMOLAGENTS_AVAILABLE", True)
    @patch("src.tools.web_search.DuckDuckGoSearchTool")
    def test_search_returns_result(self, mock_ddg_tool):
        """Test search method returns SearchResult."""
        # Mock the search tool
        mock_tool_instance = MagicMock()
        mock_tool_instance.return_value = "Search results for test"
        mock_ddg_tool.return_value = mock_tool_instance

        from src.tools.web_search import WebSearchService, SearchResult

        # Create service with mocked tool
        with patch.object(WebSearchService, "__init__", lambda self, **kwargs: None):
            service = WebSearchService()
            service.use_duckduckgo = True
            service._search_tool = mock_tool_instance
            service._agent = None

            result = service.search("test query")

            assert isinstance(result, SearchResult)
            assert result.query == "test query"
            assert result.success is True

    @patch("src.tools.web_search.SMOLAGENTS_AVAILABLE", True)
    def test_parse_results_string(self):
        """Test _parse_results handles string input."""
        from src.tools.web_search import WebSearchService

        with patch.object(WebSearchService, "__init__", lambda self, **kwargs: None):
            service = WebSearchService()

            result = service._parse_results("plain text result")

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["content"] == "plain text result"

    @patch("src.tools.web_search.SMOLAGENTS_AVAILABLE", True)
    def test_parse_results_list(self):
        """Test _parse_results handles list input."""
        from src.tools.web_search import WebSearchService

        with patch.object(WebSearchService, "__init__", lambda self, **kwargs: None):
            service = WebSearchService()

            result = service._parse_results(["item1", "item2"])

            assert isinstance(result, list)
            assert len(result) == 2

    @patch("src.tools.web_search.SMOLAGENTS_AVAILABLE", True)
    def test_parse_results_dict(self):
        """Test _parse_results handles dict input."""
        from src.tools.web_search import WebSearchService

        with patch.object(WebSearchService, "__init__", lambda self, **kwargs: None):
            service = WebSearchService()

            result = service._parse_results({"title": "Test", "url": "http://test.com"})

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["title"] == "Test"


class TestConvenienceFunctions:
    """Test convenience functions for quick searches."""

    def test_quick_search_returns_string(self):
        """Test quick_search returns a string result."""
        from src.tools.web_search import quick_search, SMOLAGENTS_AVAILABLE

        if not SMOLAGENTS_AVAILABLE:
            pytest.skip("smolagents not installed")

        # Just verify it returns a string (may make real request)
        result = quick_search("python programming")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_airflow_docs_returns_string(self):
        """Test search_airflow_docs returns results."""
        from src.tools.web_search import search_airflow_docs, SMOLAGENTS_AVAILABLE

        if not SMOLAGENTS_AVAILABLE:
            pytest.skip("smolagents not installed")

        result = search_airflow_docs("operators")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_kubernetes_docs_returns_string(self):
        """Test search_kubernetes_docs returns results."""
        from src.tools.web_search import search_kubernetes_docs, SMOLAGENTS_AVAILABLE

        if not SMOLAGENTS_AVAILABLE:
            pytest.skip("smolagents not installed")

        result = search_kubernetes_docs("pods")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_openshift_docs_returns_string(self):
        """Test search_openshift_docs returns results."""
        from src.tools.web_search import search_openshift_docs, SMOLAGENTS_AVAILABLE

        if not SMOLAGENTS_AVAILABLE:
            pytest.skip("smolagents not installed")

        result = search_openshift_docs("routes")
        assert isinstance(result, str)
        assert len(result) > 0


class TestSpecializedSearchMethods:
    """Test specialized search methods in WebSearchService."""

    @patch("src.tools.web_search.SMOLAGENTS_AVAILABLE", True)
    def test_search_infrastructure_docs(self):
        """Test infrastructure docs search adds context."""
        from src.tools.web_search import WebSearchService

        with patch.object(WebSearchService, "__init__", lambda self, **kwargs: None):
            service = WebSearchService()
            service.use_duckduckgo = True

            # Mock the search method
            mock_result = MagicMock()
            service.search = MagicMock(return_value=mock_result)

            service.search_infrastructure_docs("helm charts")

            # Verify search was called with enhanced query
            service.search.assert_called_once()
            call_arg = service.search.call_args[0][0]
            assert "helm charts" in call_arg
            assert "documentation" in call_arg

    @patch("src.tools.web_search.SMOLAGENTS_AVAILABLE", True)
    def test_search_troubleshooting(self):
        """Test troubleshooting search adds fix context."""
        from src.tools.web_search import WebSearchService

        with patch.object(WebSearchService, "__init__", lambda self, **kwargs: None):
            service = WebSearchService()
            service.use_duckduckgo = True
            service.search = MagicMock()

            service.search_troubleshooting("connection refused", context="postgresql")

            call_arg = service.search.call_args[0][0]
            assert "connection refused" in call_arg
            assert "postgresql" in call_arg
            assert "fix" in call_arg or "solution" in call_arg

    @patch("src.tools.web_search.SMOLAGENTS_AVAILABLE", True)
    def test_search_provider_info(self):
        """Test provider info search targets Airflow providers."""
        from src.tools.web_search import WebSearchService

        with patch.object(WebSearchService, "__init__", lambda self, **kwargs: None):
            service = WebSearchService()
            service.use_duckduckgo = True
            service.search = MagicMock()

            service.search_provider_info("apache-airflow-providers-ssh")

            call_arg = service.search.call_args[0][0]
            assert "apache-airflow-providers-ssh" in call_arg
            assert "airflow" in call_arg.lower()
            assert "provider" in call_arg.lower()


class TestModuleExports:
    """Test module exports are correct."""

    def test_all_exports_available(self):
        """Test all expected exports are available."""
        from src.tools import (
            SMOLAGENTS_AVAILABLE,
            WebSearchService,
            SearchResult,
            quick_search,
            search_airflow_docs,
            search_kubernetes_docs,
            search_openshift_docs,
        )

        # All imports should succeed
        assert SMOLAGENTS_AVAILABLE is not None
        assert WebSearchService is not None
        assert SearchResult is not None
        assert quick_search is not None
        assert search_airflow_docs is not None
        assert search_kubernetes_docs is not None
        assert search_openshift_docs is not None
