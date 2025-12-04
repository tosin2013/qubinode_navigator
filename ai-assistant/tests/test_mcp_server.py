"""
Tests for MCP Server (mcp_server_fastmcp.py)
Tests MCP tools, server configuration, and HTTP communication
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMCPServerConfiguration:
    """Test MCP server configuration"""

    def test_default_configuration(self):
        """Test default configuration values"""
        # Test with clean environment
        clean_env = {k: v for k, v in os.environ.items() if k not in ["AI_SERVICE_URL", "MCP_SERVER_PORT", "MCP_SERVER_HOST", "MCP_SERVER_ENABLED"]}
        with patch.dict(os.environ, clean_env, clear=True):
            AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")
            MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8081"))
            MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
            MCP_ENABLED = os.getenv("MCP_SERVER_ENABLED", "false").lower() == "true"

            assert AI_SERVICE_URL == "http://localhost:8080"
            assert MCP_SERVER_PORT == 8081
            assert MCP_SERVER_HOST == "0.0.0.0"
            assert MCP_ENABLED is False

    def test_custom_configuration(self):
        """Test custom configuration from environment"""
        with patch.dict(
            os.environ,
            {
                "AI_SERVICE_URL": "http://custom:9000",
                "MCP_SERVER_PORT": "9999",
                "MCP_SERVER_HOST": "127.0.0.1",
                "MCP_SERVER_ENABLED": "true",
            },
        ):
            AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")
            MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "9999"))
            MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
            MCP_ENABLED = os.getenv("MCP_SERVER_ENABLED", "false").lower() == "true"

            assert AI_SERVICE_URL == "http://custom:9000"
            assert MCP_SERVER_PORT == 9999
            assert MCP_SERVER_HOST == "127.0.0.1"
            assert MCP_ENABLED is True


class TestQueryDocumentsTool:
    """Test query_documents MCP tool"""

    @pytest.mark.asyncio
    async def test_query_documents_empty_query(self):
        """Test query_documents with empty query"""
        from mcp_server_fastmcp import query_documents

        # Access the underlying function via .fn attribute
        result = await query_documents.fn(query="", max_results=5)

        assert "Error" in result
        assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_query_documents_invalid_max_results(self):
        """Test query_documents with invalid max_results"""
        from mcp_server_fastmcp import query_documents

        # Too low
        result = await query_documents.fn(query="test", max_results=0)
        assert "Error" in result

        # Too high
        result = await query_documents.fn(query="test", max_results=25)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_query_documents_success(self):
        """Test successful query_documents"""
        from mcp_server_fastmcp import query_documents

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "results": [
                    {
                        "content": "Test document content",
                        "score": 0.95,
                        "source": "docs/test.md",
                    }
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await query_documents.fn(query="test query", max_results=5)

        assert "Document Search Results" in result
        assert "Test document content" in result

    @pytest.mark.asyncio
    async def test_query_documents_no_results(self):
        """Test query_documents with no results"""
        from mcp_server_fastmcp import query_documents

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await query_documents.fn(query="obscure query", max_results=5)

        assert "No results found" in result

    @pytest.mark.asyncio
    async def test_query_documents_http_error(self):
        """Test query_documents with HTTP error"""
        from mcp_server_fastmcp import query_documents
        import httpx

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.HTTPError("Connection refused"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await query_documents.fn(query="test", max_results=5)

        assert "Error" in result


class TestChatWithContextTool:
    """Test chat_with_context MCP tool"""

    @pytest.mark.asyncio
    async def test_chat_empty_message(self):
        """Test chat_with_context with empty message"""
        from mcp_server_fastmcp import chat_with_context

        result = await chat_with_context.fn(message="")

        assert "Error" in result
        assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Test successful chat_with_context"""
        from mcp_server_fastmcp import chat_with_context

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "AI response about VM deployment"}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await chat_with_context.fn(
                message="How do I deploy a VM?",
                task="vm_deployment",
                environment="production",
            )

        assert "AI response" in result

    @pytest.mark.asyncio
    async def test_chat_with_all_context(self):
        """Test chat_with_context with all context fields"""
        from mcp_server_fastmcp import chat_with_context

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "Contextual response"}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await chat_with_context.fn(
                message="Test message",
                task="deployment",
                environment="dev",
                user_role="admin",
            )

        assert "Contextual response" in result

    @pytest.mark.asyncio
    async def test_chat_http_error(self):
        """Test chat_with_context with HTTP error"""
        from mcp_server_fastmcp import chat_with_context
        import httpx

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.HTTPError("Service unavailable"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await chat_with_context.fn(message="Test")

        assert "Error" in result


class TestGetProjectStatusTool:
    """Test get_project_status MCP tool"""

    @pytest.mark.asyncio
    async def test_get_project_status_success(self):
        """Test successful get_project_status"""
        from mcp_server_fastmcp import get_project_status

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "ai_status": "healthy",
                "airflow_status": "running",
                "vm_count": 5,
                "metrics": {"cpu": "45%", "memory": "60%"},
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await get_project_status.fn()

        assert "Qubinode Navigator Project Status" in result
        assert "healthy" in result
        assert "5" in result

    @pytest.mark.asyncio
    async def test_get_project_status_error(self):
        """Test get_project_status with error"""
        from mcp_server_fastmcp import get_project_status
        import httpx

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await get_project_status.fn()

        assert "Error" in result


class TestAskQubinodeTool:
    """Test ask_qubinode MCP tool"""

    @pytest.mark.asyncio
    async def test_ask_qubinode_empty_question(self):
        """Test ask_qubinode with empty question"""
        from mcp_server_fastmcp import ask_qubinode

        result = await ask_qubinode.fn(question="")

        assert "Error" in result
        assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_ask_qubinode_success(self):
        """Test successful ask_qubinode"""
        from mcp_server_fastmcp import ask_qubinode

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            # Mock both search and chat responses
            mock_search_response = MagicMock()
            mock_search_response.status_code = 200
            mock_search_response.json.return_value = {"results": [{"content": "Plugin documentation", "source": "docs/plugins.md"}]}

            mock_chat_response = MagicMock()
            mock_chat_response.status_code = 200
            mock_chat_response.json.return_value = {"response": "To create a plugin, follow these steps..."}

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=[mock_search_response, mock_chat_response])
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await ask_qubinode.fn(
                question="How do I create a plugin?",
                topic="plugins",
                skill_level="beginner",
            )

        assert "To create a plugin" in result

    @pytest.mark.asyncio
    async def test_ask_qubinode_fallback_to_docs(self):
        """Test ask_qubinode falls back to docs when chat fails"""
        from mcp_server_fastmcp import ask_qubinode

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            # Mock search success, chat failure
            mock_search_response = MagicMock()
            mock_search_response.status_code = 200
            mock_search_response.json.return_value = {"results": [{"content": "Plugin documentation", "source": "docs/plugins.md"}]}

            mock_chat_response = MagicMock()
            mock_chat_response.status_code = 500

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=[mock_search_response, mock_chat_response])
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await ask_qubinode.fn(question="How do I create a plugin?")

        # Should fall back to showing docs
        assert "Documentation" in result or "documentation" in result or "Plugin" in result

    @pytest.mark.asyncio
    async def test_ask_qubinode_http_error(self):
        """Test ask_qubinode with HTTP error"""
        from mcp_server_fastmcp import ask_qubinode
        import httpx

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.HTTPError("Service unavailable"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await ask_qubinode.fn(question="Test question")

        assert "Error" in result


class TestMCPServerMain:
    """Test MCP server main function"""

    def test_main_disabled(self):
        """Test main function when MCP is disabled"""
        with patch.dict(os.environ, {"MCP_SERVER_ENABLED": "false", "MCP_SERVER_PORT": "8081"}):
            import importlib
            import mcp_server_fastmcp

            importlib.reload(mcp_server_fastmcp)

            with pytest.raises(SystemExit) as exc_info:
                mcp_server_fastmcp.main()

            assert exc_info.value.code == 0

    def test_main_enabled(self):
        """Test main function when MCP is enabled"""
        with patch.dict(os.environ, {"MCP_SERVER_ENABLED": "true", "MCP_SERVER_PORT": "8081"}):
            import importlib
            import mcp_server_fastmcp

            importlib.reload(mcp_server_fastmcp)

            with patch.object(mcp_server_fastmcp.mcp, "run") as mock_run:
                mcp_server_fastmcp.main()

            mock_run.assert_called_once_with(
                transport="sse",
                host="0.0.0.0",
                port=8081,
            )


class TestMCPServerTools:
    """Test MCP server tool registration"""

    def test_mcp_instance_created(self):
        """Test that FastMCP instance is created"""
        from mcp_server_fastmcp import mcp

        assert mcp is not None
        assert mcp.name == "qubinode-ai-assistant"

    def test_tools_are_function_tools(self):
        """Test that decorated functions become FunctionTool objects"""
        from mcp_server_fastmcp import query_documents, chat_with_context, get_project_status, ask_qubinode
        from fastmcp.tools.tool import FunctionTool

        assert isinstance(query_documents, FunctionTool)
        assert isinstance(chat_with_context, FunctionTool)
        assert isinstance(get_project_status, FunctionTool)
        assert isinstance(ask_qubinode, FunctionTool)

    def test_tools_have_underlying_functions(self):
        """Test that FunctionTool objects have callable fn attribute"""
        from mcp_server_fastmcp import query_documents, chat_with_context

        assert callable(query_documents.fn)
        assert callable(chat_with_context.fn)


class TestMCPServerInputValidation:
    """Test input validation for MCP tools"""

    @pytest.mark.asyncio
    async def test_query_documents_whitespace_only(self):
        """Test query_documents with whitespace-only query"""
        from mcp_server_fastmcp import query_documents

        result = await query_documents.fn(query="   ", max_results=5)

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_chat_whitespace_only(self):
        """Test chat_with_context with whitespace-only message"""
        from mcp_server_fastmcp import chat_with_context

        result = await chat_with_context.fn(message="   ")

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_ask_qubinode_whitespace_only(self):
        """Test ask_qubinode with whitespace-only question"""
        from mcp_server_fastmcp import ask_qubinode

        result = await ask_qubinode.fn(question="   ")

        assert "Error" in result


class TestMCPServerErrorMessages:
    """Test error message formatting"""

    @pytest.mark.asyncio
    async def test_error_includes_service_url(self):
        """Test that error messages include service URL"""
        from mcp_server_fastmcp import query_documents
        import httpx

        with patch("mcp_server_fastmcp.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(side_effect=httpx.HTTPError("Connection refused"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await query_documents.fn(query="test", max_results=5)

        assert "AI Assistant service" in result or "localhost" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
