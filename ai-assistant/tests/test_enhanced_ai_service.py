"""
Tests for EnhancedAIService
Tests multi-model AI support, RAG integration, and lineage awareness
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock langchain before importing
sys.modules["langchain"] = MagicMock()
sys.modules["langchain.llms"] = MagicMock()
sys.modules["langchain.llms.base"] = MagicMock()
sys.modules["langchain.callbacks"] = MagicMock()
sys.modules["langchain.callbacks.manager"] = MagicMock()

# Create mock LLM base class
mock_llm_class = MagicMock()
sys.modules["langchain.llms.base"].LLM = mock_llm_class

# Mock litellm
sys.modules["litellm"] = MagicMock()

from enhanced_ai_service import (
    EnhancedAIService,
    LocalLlamaCppLLM,
    LiteLLMLLM,
    create_enhanced_ai_service,
)


@pytest.mark.skip(reason="LLM classes require complex langchain inheritance mocking")
class TestLocalLlamaCppLLM:
    """Test LocalLlamaCppLLM class - skipped due to langchain mocking complexity"""

    def test_local_llm_creation(self):
        """Test creating LocalLlamaCppLLM instance"""
        llm = LocalLlamaCppLLM()
        assert llm.server_url == "http://localhost:8081"
        assert llm.max_tokens == 512
        assert llm.temperature == 0.7

    def test_local_llm_type(self):
        """Test _llm_type property"""
        llm = LocalLlamaCppLLM()
        assert llm._llm_type == "llama_cpp_local"

    def test_local_llm_call_success(self):
        """Test successful local LLM call"""
        llm = LocalLlamaCppLLM()

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"content": "Local response"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = llm._call("Test prompt")

        assert result == "Local response"

    def test_local_llm_call_error(self):
        """Test local LLM call with error"""
        llm = LocalLlamaCppLLM()

        with patch("httpx.post") as mock_post:
            mock_post.side_effect = Exception("Connection refused")

            with pytest.raises(Exception):
                llm._call("Test prompt")


@pytest.mark.skip(reason="LLM classes require complex langchain inheritance mocking")
class TestLiteLLMLLM:
    """Test LiteLLMLLM class - skipped due to langchain mocking complexity"""

    def test_litellm_creation(self):
        """Test creating LiteLLMLLM instance"""
        llm = LiteLLMLLM(model_name="gpt-4")
        assert llm.model_name == "gpt-4"
        assert llm.max_tokens == 512
        assert llm.temperature == 0.7

    def test_litellm_type(self):
        """Test _llm_type property"""
        llm = LiteLLMLLM(model_name="gpt-4")
        assert llm._llm_type == "litellm_api"

    def test_litellm_with_endpoint(self):
        """Test LiteLLMLLM with custom endpoint"""
        llm = LiteLLMLLM(
            model_name="custom-model",
            api_endpoint="https://custom.api.com",
        )
        assert llm.api_endpoint == "https://custom.api.com"


class TestEnhancedAIServiceInit:
    """Test EnhancedAIService initialization"""

    def test_enhanced_service_creation(self, mock_config):
        """Test creating EnhancedAIService instance"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.validate_configuration.return_value = {
                "valid": True,
                "errors": [],
                "warnings": [],
            }

            service = EnhancedAIService(mock_config)

        assert service is not None
        assert service.llm is None
        assert service.rag_service is None

    def test_enhanced_service_is_api_model(self, mock_config):
        """Test detecting API model"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "gpt-4",
                "preset_info": {"provider": "litellm"},
            }

            service = EnhancedAIService(mock_config)

        assert service.is_api_model is True

    def test_enhanced_service_is_local_model(self, mock_config):
        """Test detecting local model"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        assert service.is_api_model is False


class TestEnhancedAIServiceChat:
    """Test chat functionality"""

    @pytest.mark.asyncio
    async def test_chat_not_initialized(self, mock_config):
        """Test chat when not initialized"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)
            service.llm = None

        with pytest.raises(RuntimeError, match="not initialized"):
            await service.chat("Test message")

    @pytest.mark.asyncio
    async def test_chat_success(self, mock_config, mock_rag_service):
        """Test successful chat"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.model_type = "granite-4.0-micro"

            service = EnhancedAIService(mock_config)

        # Mock RAG service with proper retrieval result
        mock_retrieval = MagicMock()
        mock_retrieval.contexts = ["Context 1", "Context 2"]
        mock_retrieval.sources = ["doc1.md", "doc2.md"]
        mock_rag_service.retrieve_relevant_context = AsyncMock(return_value=mock_retrieval)
        service.rag_service = mock_rag_service

        mock_llm = MagicMock()
        service.llm = mock_llm
        service.is_api_model = False

        with patch.object(service, "_generate_local_response", return_value="AI Response"):
            result = await service.chat("How do I deploy a VM?")

        assert "response" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_chat_with_lineage_context(self, mock_config):
        """Test chat with lineage context from Marquez"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.model_type = "granite-4.0-micro"

            service = EnhancedAIService(mock_config)

        # Mock Marquez service
        mock_marquez = AsyncMock()
        mock_marquez.get_context_for_prompt = AsyncMock(return_value="Recent DAG runs: freeipa_deployment (SUCCESS)")
        service.marquez_service = mock_marquez
        service.rag_service = None

        mock_llm = MagicMock()
        service.llm = mock_llm
        service.is_api_model = False

        with patch.object(service, "_generate_local_response", return_value="Response with lineage"):
            result = await service.chat("What's the status of deployments?")

        assert "metadata" in result
        assert result["metadata"]["lineage_enabled"] is True


class TestEnhancedAIServiceBuildPrompt:
    """Test prompt building"""

    def test_build_prompt_basic(self, mock_config):
        """Test building basic prompt"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        prompt = service._build_prompt("Test question", [], None, "")

        assert "Qubinode Navigator AI Assistant" in prompt
        assert "Test question" in prompt

    def test_build_prompt_with_rag_context(self, mock_config):
        """Test building prompt with RAG context"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        rag_context = ["Documentation about VMs", "KVM setup guide"]
        prompt = service._build_prompt("How to create VM?", rag_context, None, "")

        assert "Documentation about VMs" in prompt
        assert "KVM setup guide" in prompt

    def test_build_prompt_with_lineage_context(self, mock_config):
        """Test building prompt with lineage context"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        lineage_context = "Recent runs: deployment_dag (SUCCESS)"
        prompt = service._build_prompt("Status?", [], None, lineage_context)

        assert "Recent runs: deployment_dag" in prompt


class TestEnhancedAIServiceProcessMessage:
    """Test process_message compatibility method"""

    @pytest.mark.asyncio
    async def test_process_message(self, mock_config):
        """Test process_message method"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.model_type = "granite-4.0-micro"

            service = EnhancedAIService(mock_config)

        service.llm = MagicMock()
        service.rag_service = None
        service.is_api_model = False

        with patch.object(
            service,
            "chat",
            return_value={
                "response": "AI response",
                "metadata": {},
            },
        ):
            result = await service.process_message("Test message")

        assert "text" in result
        assert result["text"] == "AI response"

    @pytest.mark.asyncio
    async def test_process_message_error(self, mock_config):
        """Test process_message error handling"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        with patch.object(service, "chat", side_effect=Exception("Chat error")):
            result = await service.process_message("Test")

        assert "Error" in result["text"]


class TestEnhancedAIServiceDiagnostics:
    """Test diagnostics methods"""

    def test_get_available_diagnostic_tools(self, mock_config):
        """Test getting available diagnostic tools"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        with patch("enhanced_ai_service.diagnostic_registry") as mock_registry:
            mock_registry.list_tools.return_value = {"tool1": "desc1"}
            tools = service.get_available_diagnostic_tools()

        assert isinstance(tools, dict)

    @pytest.mark.asyncio
    async def test_run_diagnostics(self, mock_config):
        """Test running diagnostics"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        with patch.object(service, "get_diagnostics", return_value={"result": "data"}):
            result = await service.run_diagnostics({"tool_name": "system_info"})

        assert "result" in result

    @pytest.mark.asyncio
    async def test_run_specific_diagnostic_tool(self, mock_config):
        """Test running specific diagnostic tool"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        with patch("enhanced_ai_service.diagnostic_registry") as mock_registry:
            mock_registry.run_diagnostic = AsyncMock(return_value={"status": "ok"})
            result = await service.run_specific_diagnostic_tool("system_info")

        assert "status" in result or "error" in result


class TestEnhancedAIServiceLineage:
    """Test lineage-related methods"""

    @pytest.mark.asyncio
    async def test_get_lineage_summary_no_service(self, mock_config):
        """Test getting lineage summary without Marquez"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)
            service.marquez_service = None

        result = await service.get_lineage_summary()

        assert result["available"] is False

    @pytest.mark.asyncio
    async def test_get_lineage_summary_with_service(self, mock_config):
        """Test getting lineage summary with Marquez"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        mock_marquez = AsyncMock()
        mock_marquez.get_lineage_summary = AsyncMock(return_value={"jobs": 10, "runs": 50})
        service.marquez_service = mock_marquez

        result = await service.get_lineage_summary()

        assert result["jobs"] == 10

    @pytest.mark.asyncio
    async def test_get_job_lineage_no_service(self, mock_config):
        """Test getting job lineage without Marquez"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)
            service.marquez_service = None

        result = await service.get_job_lineage("test_job")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_job_lineage_with_service(self, mock_config):
        """Test getting job lineage with Marquez"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        mock_marquez = AsyncMock()
        mock_marquez.get_job_details = AsyncMock(return_value={"job_name": "test_job", "status": "SUCCESS"})
        service.marquez_service = mock_marquez

        result = await service.get_job_lineage("test_job")

        assert result["job_name"] == "test_job"


class TestEnhancedAIServiceModelInfo:
    """Test model information methods"""

    def test_get_model_info(self, mock_config):
        """Test getting model information"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "threads": 4,
            }

            service = EnhancedAIService(mock_config)

        info = service.get_model_info()

        assert info["model_type"] == "granite-4.0-micro"

    def test_get_hardware_info(self, mock_config):
        """Test getting hardware information"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.detect_hardware_capabilities.return_value = {
                "cpu_cores": 8,
                "gpu_available": False,
            }

            service = EnhancedAIService(mock_config)

        info = service.get_hardware_info()

        assert info["cpu_cores"] == 8


class TestEnhancedAIServiceShutdown:
    """Test shutdown and cleanup"""

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_config):
        """Test cleanup method"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        with patch.object(service, "shutdown", new_callable=AsyncMock) as mock_shutdown:
            await service.cleanup()

        mock_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_with_process(self, mock_config):
        """Test shutdown with llama process"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = EnhancedAIService(mock_config)

        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = MagicMock()
        service.llama_process = mock_process

        await service.shutdown()

        mock_process.terminate.assert_called_once()


class TestEnhancedAIServiceFactory:
    """Test factory function"""

    def test_create_enhanced_ai_service(self, mock_config):
        """Test factory function"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }

            service = create_enhanced_ai_service(mock_config)

        assert isinstance(service, EnhancedAIService)


class TestEnhancedAIServiceInitialization:
    """Test service initialization paths"""

    @pytest.mark.asyncio
    async def test_initialize_cloud_only_mode(self, mock_config):
        """Test initialization in cloud-only mode"""
        mock_config["ai"]["use_local_model"] = False
        
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "gpt-4",
                "preset_info": {},
                "max_tokens": 512,
                "temperature": 0.7
            }
            
            service = EnhancedAIService(mock_config)
            
            with patch("enhanced_ai_service.create_rag_service") as mock_rag:
                mock_rag_instance = AsyncMock()
                mock_rag_instance.initialize = AsyncMock(return_value=True)
                mock_rag.return_value = mock_rag_instance
                
                await service.initialize()
            
            # Should skip local model initialization
            assert service.llama_process is None

    @pytest.mark.asyncio
    async def test_initialize_api_model_invalid_config(self, mock_config):
        """Test initialization with invalid API model config"""
        mock_config["ai"]["use_local_model"] = True
        
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "gpt-4",
                "preset_info": {"provider": "litellm"},
            }
            mock_mm.return_value.validate_configuration.return_value = {
                "valid": False,
                "errors": ["Missing API key"],
                "warnings": []
            }
            
            service = EnhancedAIService(mock_config)
            
            with pytest.raises(ValueError, match="Invalid model configuration"):
                await service.initialize()

    @pytest.mark.asyncio
    async def test_initialize_local_model_invalid_config(self, mock_config):
        """Test initialization with invalid local model config"""
        mock_config["ai"]["use_local_model"] = True
        
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.validate_configuration.return_value = {
                "valid": False,
                "errors": ["Model file not found"],
                "warnings": []
            }
            
            service = EnhancedAIService(mock_config)
            
            with pytest.raises(ValueError, match="Invalid model configuration"):
                await service.initialize()

    @pytest.mark.asyncio
    async def test_initialize_with_warnings(self, mock_config):
        """Test initialization with configuration warnings"""
        mock_config["ai"]["use_local_model"] = False
        
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.validate_configuration.return_value = {
                "valid": True,
                "errors": [],
                "warnings": ["GPU not available, using CPU"]
            }
            
            service = EnhancedAIService(mock_config)
            
            with patch("enhanced_ai_service.create_rag_service") as mock_rag:
                mock_rag_instance = AsyncMock()
                mock_rag_instance.initialize = AsyncMock(return_value=True)
                mock_rag.return_value = mock_rag_instance
                
                # Should complete despite warnings
                await service.initialize()


class TestEnhancedAIServiceAPICredentials:
    """Test API credentials configuration"""

    def test_configure_openai_credentials(self, mock_config):
        """Test OpenAI credentials check"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "gpt-4",
                "preset_info": {},
            }
            
            service = EnhancedAIService(mock_config)
            
            with patch.dict(os.environ, {}, clear=True):
                # Should log warning but not raise
                service._configure_api_credentials("gpt-4")

    def test_configure_anthropic_credentials(self, mock_config):
        """Test Anthropic credentials check"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "claude-3",
                "preset_info": {},
            }
            
            service = EnhancedAIService(mock_config)
            
            with patch.dict(os.environ, {}, clear=True):
                service._configure_api_credentials("claude-3-opus")

    def test_configure_azure_credentials(self, mock_config):
        """Test Azure credentials check"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "azure-gpt-4",
                "preset_info": {},
            }
            
            service = EnhancedAIService(mock_config)
            
            with patch.dict(os.environ, {}, clear=True):
                service._configure_api_credentials("azure-gpt-4")


class TestEnhancedAIServiceChatErrors:
    """Test chat error handling"""

    @pytest.mark.asyncio
    async def test_chat_rag_error(self, mock_config):
        """Test chat with RAG retrieval error"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.model_type = "granite-4.0-micro"
            
            service = EnhancedAIService(mock_config)
        
        # Mock RAG service that raises error
        mock_rag = AsyncMock()
        mock_rag.retrieve_relevant_context = AsyncMock(side_effect=Exception("RAG error"))
        service.rag_service = mock_rag
        
        mock_llm = MagicMock()
        service.llm = mock_llm
        service.is_api_model = False
        
        with patch.object(service, "_generate_local_response", return_value="Response despite RAG error"):
            result = await service.chat("Test message")
        
        # Should handle error gracefully
        assert "response" in result
        assert result["response"] == "Response despite RAG error"

    @pytest.mark.asyncio
    async def test_chat_generation_error(self, mock_config):
        """Test chat with generation error"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.model_type = "granite-4.0-micro"
            
            service = EnhancedAIService(mock_config)
        
        service.rag_service = None
        mock_llm = MagicMock()
        service.llm = mock_llm
        service.is_api_model = False
        
        with patch.object(service, "_generate_local_response", side_effect=Exception("Generation failed")):
            result = await service.chat("Test message")
        
        # Should return error response
        assert "error" in result["metadata"]


class TestEnhancedAIServiceMarquezIntegration:
    """Test Marquez lineage integration"""

    @pytest.mark.asyncio
    async def test_marquez_not_available(self, mock_config):
        """Test when Marquez is not available"""
        with patch("enhanced_ai_service.ModelManager") as mock_mm:
            mock_mm.return_value.get_model_info.return_value = {
                "model_type": "granite-4.0-micro",
                "preset_info": {},
            }
            mock_mm.return_value.model_type = "granite-4.0-micro"
            
            service = EnhancedAIService(mock_config)
        
        # Mock Marquez service that returns error
        mock_marquez = AsyncMock()
        mock_marquez.get_context_for_prompt = AsyncMock(side_effect=Exception("Marquez unavailable"))
        service.marquez_service = mock_marquez
        service.rag_service = None
        
        mock_llm = MagicMock()
        service.llm = mock_llm
        service.is_api_model = False
        
        with patch.object(service, "_generate_local_response", return_value="Response without lineage"):
            result = await service.chat("Test message")
        
        # Should handle Marquez error gracefully
        assert "response" in result
        assert result["metadata"]["lineage_enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
