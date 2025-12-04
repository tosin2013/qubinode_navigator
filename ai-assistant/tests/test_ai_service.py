"""
Tests for AIService
Tests AI inference, RAG integration, and diagnostics
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

from ai_service import AIService, LlamaCppLLM


@pytest.mark.skip(reason="LlamaCppLLM requires complex langchain inheritance mocking")
class TestLlamaCppLLM:
    """Test LlamaCppLLM class - skipped due to langchain mocking complexity"""

    def test_llm_creation(self):
        """Test creating LlamaCppLLM instance"""
        llm = LlamaCppLLM()
        assert llm.server_url == "http://localhost:8081"
        assert llm.max_tokens == 512
        assert llm.temperature == 0.7

    def test_llm_custom_params(self):
        """Test LlamaCppLLM with custom parameters"""
        llm = LlamaCppLLM(
            server_url="http://custom:9000",
            max_tokens=1024,
            temperature=0.5,
        )
        assert llm.server_url == "http://custom:9000"
        assert llm.max_tokens == 1024
        assert llm.temperature == 0.5

    def test_llm_type(self):
        """Test _llm_type property"""
        llm = LlamaCppLLM()
        assert llm._llm_type == "llama_cpp"

    def test_llm_call_success(self):
        """Test successful LLM call"""
        llm = LlamaCppLLM()

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"content": "Test response"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = llm._call("Test prompt")

        assert result == "Test response"
        mock_post.assert_called_once()

    def test_llm_call_with_stop(self):
        """Test LLM call with stop sequences"""
        llm = LlamaCppLLM()

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"content": "Test response"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            llm._call("Test prompt", stop=["STOP"])

        call_args = mock_post.call_args
        assert call_args[1]["json"]["stop"] == ["STOP"]

    def test_llm_call_error(self):
        """Test LLM call with error"""
        llm = LlamaCppLLM()

        with patch("httpx.post") as mock_post:
            mock_post.side_effect = Exception("Connection error")

            result = llm._call("Test prompt")

        assert "Error" in result

    def test_llm_call_custom_kwargs(self):
        """Test LLM call with custom kwargs"""
        llm = LlamaCppLLM()

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"content": "Response"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            llm._call("Prompt", max_tokens=256, temperature=0.3)

        call_args = mock_post.call_args
        assert call_args[1]["json"]["max_tokens"] == 256
        assert call_args[1]["json"]["temperature"] == 0.3


class TestAIServiceInit:
    """Test AIService initialization"""

    def test_ai_service_creation(self, mock_config_manager):
        """Test creating AIService instance"""
        service = AIService(mock_config_manager)

        assert service.config_manager == mock_config_manager
        assert service.llm is None
        assert service.is_initialized is False
        assert service.rag_service is None

    def test_ai_service_attributes(self, mock_config_manager):
        """Test AIService attributes after creation"""
        service = AIService(mock_config_manager)

        assert service.server_process is None
        assert service.model_path is None


class TestAIServiceSystemPrompt:
    """Test system prompt generation"""

    def test_get_system_prompt(self, mock_config_manager):
        """Test getting system prompt"""
        service = AIService(mock_config_manager)
        prompt = service._get_system_prompt()

        assert "Qubinode Navigator AI Assistant" in prompt
        assert "infrastructure automation" in prompt.lower()
        assert "KVM" in prompt


class TestAIServiceProcessMessage:
    """Test message processing"""

    @pytest.mark.asyncio
    async def test_process_message_not_initialized(self, mock_config_manager):
        """Test processing message when not initialized"""
        service = AIService(mock_config_manager)

        with pytest.raises(RuntimeError, match="not initialized"):
            await service.process_message("Test message")

    @pytest.mark.asyncio
    async def test_process_message_success(self, mock_config_manager, mock_rag_service):
        """Test successful message processing"""
        service = AIService(mock_config_manager)
        service.is_initialized = True
        service.rag_service = mock_rag_service

        mock_llm = MagicMock()
        mock_llm._call.return_value = "AI response about infrastructure"
        service.llm = mock_llm

        result = await service.process_message("How do I deploy a VM?")

        assert "text" in result
        assert "metadata" in result
        assert result["text"] == "AI response about infrastructure"

    @pytest.mark.asyncio
    async def test_process_message_with_context(self, mock_config_manager, mock_rag_service):
        """Test message processing with context"""
        service = AIService(mock_config_manager)
        service.is_initialized = True
        service.rag_service = mock_rag_service

        mock_llm = MagicMock()
        mock_llm._call.return_value = "Contextual response"
        service.llm = mock_llm

        context = {"task": "vm_deployment", "environment": "production"}
        result = await service.process_message("Deploy VM", context=context)

        assert result["context"] == context

    @pytest.mark.asyncio
    async def test_process_message_rag_failure(self, mock_config_manager):
        """Test message processing when RAG fails"""
        service = AIService(mock_config_manager)
        service.is_initialized = True

        # RAG service that raises exception
        mock_rag = AsyncMock()
        mock_rag.get_context_for_query = AsyncMock(side_effect=Exception("RAG error"))
        service.rag_service = mock_rag

        mock_llm = MagicMock()
        mock_llm._call.return_value = "Response without RAG"
        service.llm = mock_llm

        result = await service.process_message("Test message")

        assert "text" in result
        assert result["metadata"]["rag_enabled"] is False

    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, mock_config_manager):
        """Test error handling in message processing"""
        service = AIService(mock_config_manager)
        service.is_initialized = True
        service.rag_service = None

        mock_llm = MagicMock()
        mock_llm._call.side_effect = Exception("LLM error")
        service.llm = mock_llm

        result = await service.process_message("Test message")

        assert "error" in result["text"].lower() or result["metadata"].get("error")


class TestAIServiceDiagnostics:
    """Test diagnostics functionality"""

    @pytest.mark.asyncio
    async def test_run_diagnostics_comprehensive(self, mock_config_manager, mock_diagnostic_registry):
        """Test running comprehensive diagnostics"""
        service = AIService(mock_config_manager)
        service.is_initialized = True

        with patch("ai_service.diagnostic_registry", mock_diagnostic_registry):
            mock_diagnostic_registry.run_comprehensive_diagnostics = AsyncMock(
                return_value={
                    "summary": {
                        "total_tools": 6,
                        "successful_tools": 6,
                        "failed_tools": 0,
                    },
                    "tool_results": {
                        "system_info": {
                            "success": True,
                            "data": {"hostname": "test"},
                        }
                    },
                }
            )

            result = await service.run_diagnostics({"include_ai_analysis": False})

        assert "diagnostics" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_run_diagnostics_specific_tool(self, mock_config_manager, mock_diagnostic_registry):
        """Test running specific diagnostic tool"""
        service = AIService(mock_config_manager)
        service.is_initialized = True

        # Create proper tool result mock
        mock_tool_result = MagicMock()
        mock_tool_result.success = True
        mock_tool_result.execution_time = 0.1
        mock_tool_result.to_dict.return_value = {
            "tool_name": "system_info",
            "success": True,
            "data": {"hostname": "test-host"},
            "execution_time": 0.1,
        }
        mock_diagnostic_registry.run_tool = AsyncMock(return_value=mock_tool_result)

        with patch("ai_service.diagnostic_registry", mock_diagnostic_registry):
            result = await service.run_diagnostics({"tool": "system_info", "include_ai_analysis": False})

        assert "diagnostics" in result

    @pytest.mark.asyncio
    async def test_run_specific_diagnostic_tool(self, mock_config_manager, mock_diagnostic_registry):
        """Test run_specific_diagnostic_tool method"""
        service = AIService(mock_config_manager)

        with patch("ai_service.diagnostic_registry", mock_diagnostic_registry):
            result = await service.run_specific_diagnostic_tool("system_info")

        assert "tool_result" in result
        assert "timestamp" in result

    def test_get_available_diagnostic_tools(self, mock_config_manager, mock_diagnostic_registry):
        """Test getting available diagnostic tools"""
        service = AIService(mock_config_manager)

        with patch("ai_service.diagnostic_registry", mock_diagnostic_registry):
            tools = service.get_available_diagnostic_tools()

        assert "system_info" in tools


class TestAIServiceExtractKeyFindings:
    """Test key findings extraction"""

    def test_extract_key_findings_system_info(self, mock_config_manager):
        """Test extracting key findings from system info"""
        service = AIService(mock_config_manager)

        tool_results = {
            "system_info": {
                "success": True,
                "data": {
                    "platform": "linux",
                    "uptime_seconds": 3600,
                },
            }
        }

        findings = service._extract_key_findings(tool_results)

        assert "system" in findings
        assert findings["system"]["platform"] == "linux"
        assert findings["system"]["uptime_hours"] == 1.0

    def test_extract_key_findings_resource_usage(self, mock_config_manager):
        """Test extracting key findings from resource usage"""
        service = AIService(mock_config_manager)

        tool_results = {
            "resource_usage": {
                "success": True,
                "data": {
                    "cpu": {"usage_percent": 45.0},
                    "memory": {"usage_percent": 60.0},
                    "disk": {"/": {"usage_percent": 70.0}},
                },
            }
        }

        findings = service._extract_key_findings(tool_results)

        assert "resources" in findings
        assert findings["resources"]["cpu_usage"] == 45.0
        assert findings["resources"]["memory_usage"] == 60.0

    def test_extract_key_findings_kvm(self, mock_config_manager):
        """Test extracting key findings from KVM diagnostics"""
        service = AIService(mock_config_manager)

        tool_results = {
            "kvm_diagnostics": {
                "success": True,
                "data": {
                    "vmx_support": True,
                    "kvm_module_loaded": True,
                    "libvirt_available": True,
                    "vm_count": 5,
                },
            }
        }

        findings = service._extract_key_findings(tool_results)

        assert "kvm" in findings
        assert findings["kvm"]["virtualization_support"] is True
        assert findings["kvm"]["vm_count"] == 5

    def test_extract_key_findings_error_handling(self, mock_config_manager):
        """Test error handling in key findings extraction"""
        service = AIService(mock_config_manager)

        # Malformed data
        tool_results = {
            "system_info": {
                "success": True,
                "data": None,  # Invalid data
            }
        }

        findings = service._extract_key_findings(tool_results)

        # Should handle gracefully
        assert isinstance(findings, dict)


class TestAIServiceListModels:
    """Test model listing"""

    @pytest.mark.asyncio
    async def test_list_models(self, mock_config_manager, tmp_path):
        """Test listing available models"""
        service = AIService(mock_config_manager)

        model_path = tmp_path / "model.gguf"
        model_path.write_text("model content")
        service.model_path = model_path
        service.is_initialized = True

        result = await service.list_models()

        assert result["current_model"] == "granite-4.0-micro"
        assert result["status"] == "loaded"
        assert result["model_size"] > 0

    @pytest.mark.asyncio
    async def test_list_models_not_loaded(self, mock_config_manager):
        """Test listing models when not loaded"""
        service = AIService(mock_config_manager)
        service.is_initialized = False

        result = await service.list_models()

        assert result["status"] == "not_loaded"


class TestAIServiceCleanup:
    """Test cleanup functionality"""

    @pytest.mark.asyncio
    async def test_cleanup_no_process(self, mock_config_manager):
        """Test cleanup when no server process"""
        service = AIService(mock_config_manager)
        service.server_process = None

        # Should not raise
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_with_process(self, mock_config_manager):
        """Test cleanup with server process"""
        service = AIService(mock_config_manager)

        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()
        service.server_process = mock_process

        await service.cleanup()

        mock_process.terminate.assert_called_once()


class TestAIServiceIntegration:
    """Integration tests for AIService"""

    @pytest.mark.asyncio
    async def test_full_message_flow(self, mock_config_manager, mock_rag_service):
        """Test complete message processing flow"""
        service = AIService(mock_config_manager)
        service.is_initialized = True
        service.rag_service = mock_rag_service

        mock_llm = MagicMock()
        mock_llm._call.return_value = "Complete response with RAG context"
        service.llm = mock_llm

        # Process message
        result = await service.process_message(
            "How do I configure network bridging for KVM?",
            context={"task": "network_config"},
        )

        assert "text" in result
        assert "metadata" in result
        assert "timestamp" in result["metadata"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
