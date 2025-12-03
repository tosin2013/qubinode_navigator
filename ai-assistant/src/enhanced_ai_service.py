#!/usr/bin/env python3
"""
Enhanced AI Service with LiteLLM support
Supports both local models (llama.cpp) and API models (OpenAI, Anthropic, etc.)
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import httpx
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.schema import Generation, LLMResult

# Import LiteLLM with error handling
try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logging.warning("LiteLLM not available - API models will not work")

from qdrant_rag_service import create_rag_service, RetrievalResult
from diagnostic_tools import diagnostic_registry
from model_manager import ModelManager

# Import Marquez context service for lineage awareness
try:
    from marquez_context_service import MarquezContextService, get_marquez_service
    MARQUEZ_AVAILABLE = True
except ImportError:
    MARQUEZ_AVAILABLE = False
    logging.warning("Marquez context service not available - lineage awareness disabled")

logger = logging.getLogger(__name__)


class EnhancedAIService:
    """Enhanced AI service supporting multiple model types"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_manager = ModelManager(config)
        self.rag_service = None
        self.llm = None
        self.llama_process = None
        self.marquez_service = None  # Lineage context service

        # Determine model type
        model_info = self.model_manager.get_model_info()
        self.is_api_model = model_info.get('preset_info', {}).get('provider') == 'litellm'

        logger.info(f"Enhanced AI Service initialized")
        logger.info(f"Model type: {model_info['model_type']}")
        logger.info(f"API model: {self.is_api_model}")
    
    async def initialize(self):
        """Initialize the AI service"""
        logger.info("Initializing Enhanced AI service...")
        
        # Validate configuration
        validation = self.model_manager.validate_configuration()
        if not validation['valid']:
            for error in validation['errors']:
                logger.error(f"Configuration error: {error}")
            raise ValueError("Invalid model configuration")
        
        for warning in validation['warnings']:
            logger.warning(f"Configuration warning: {warning}")
        
        # Initialize model based on type
        if self.is_api_model:
            await self._initialize_api_model()
        else:
            await self._initialize_local_model()
        
        # Initialize RAG service
        logger.info("Initializing RAG service...")
        self.rag_service = create_rag_service("/app/data")

        # Initialize Marquez context service for lineage awareness
        if MARQUEZ_AVAILABLE:
            logger.info("Initializing Marquez context service...")
            self.marquez_service = get_marquez_service()
            if await self.marquez_service.is_available():
                logger.info("Marquez lineage service connected - AI has lineage awareness")
            else:
                logger.warning("Marquez not available - AI will work without lineage context")
        else:
            logger.info("Marquez context service not installed - skipping lineage integration")

        logger.info("Enhanced AI service initialized successfully")
    
    async def _initialize_local_model(self):
        """Initialize local model (llama.cpp)"""
        logger.info("Initializing local model...")
        
        # Download model if needed
        if not self.model_manager.download_model():
            raise RuntimeError("Failed to download model")
        
        # Start llama.cpp server
        logger.info("Starting llama.cpp server...")
        self.llama_process = self.model_manager.start_llama_server()
        
        # Test connection
        await self._test_local_model_connection()
        
        # Create LLM wrapper
        model_info = self.model_manager.get_model_info()
        self.llm = LocalLlamaCppLLM(
            server_url="http://localhost:8081",
            max_tokens=model_info['max_tokens'],
            temperature=model_info['temperature']
        )
        
        logger.info("Local model initialized successfully")
    
    async def _initialize_api_model(self):
        """Initialize API model (LiteLLM)"""
        if not LITELLM_AVAILABLE:
            raise RuntimeError("LiteLLM not available - cannot use API models")
        
        logger.info("Initializing API model...")
        
        model_info = self.model_manager.get_model_info()
        preset_info = model_info.get('preset_info', {})
        
        # Set up LiteLLM configuration
        model_name = preset_info.get('model_name')
        api_endpoint = preset_info.get('api_endpoint')
        
        if not model_name:
            raise ValueError("Model name not specified for API model")
        
        # Configure API credentials from environment
        self._configure_api_credentials(model_name)
        
        # Create LiteLLM wrapper
        self.llm = LiteLLMLLM(
            model_name=model_name,
            api_endpoint=api_endpoint,
            max_tokens=model_info['max_tokens'],
            temperature=model_info['temperature']
        )
        
        # Test API connection
        await self._test_api_model_connection()
        
        logger.info("API model initialized successfully")
    
    def _configure_api_credentials(self, model_name: str):
        """Configure API credentials based on model type"""
        
        if "gpt" in model_name.lower() or "openai" in model_name.lower():
            if not os.getenv("OPENAI_API_KEY"):
                logger.warning("OPENAI_API_KEY not set - OpenAI models may not work")
        
        elif "claude" in model_name.lower() or "anthropic" in model_name.lower():
            if not os.getenv("ANTHROPIC_API_KEY"):
                logger.warning("ANTHROPIC_API_KEY not set - Anthropic models may not work")
        
        elif "azure" in model_name.lower():
            required_vars = ["AZURE_API_KEY", "AZURE_API_BASE", "AZURE_API_VERSION"]
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                logger.warning(f"Missing Azure environment variables: {missing}")
    
    async def _test_local_model_connection(self):
        """Test connection to local llama.cpp server"""
        max_retries = 30
        for i in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8081/completion",
                        json={"prompt": "Hello", "max_tokens": 5},
                        timeout=10
                    )
                    if response.status_code == 200:
                        logger.info("AI service connection test successful")
                        return
            except Exception as e:
                if i == max_retries - 1:
                    raise RuntimeError(f"Failed to connect to llama.cpp server: {e}")
                await asyncio.sleep(1)
    
    async def _test_api_model_connection(self):
        """Test connection to API model"""
        try:
            # Simple test completion
            response = await self.llm._acall("Hello")
            logger.info("API model connection test successful")
        except Exception as e:
            logger.error(f"API model connection test failed: {e}")
            raise
    
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process chat message with RAG and return response"""
        
        if not self.llm:
            raise RuntimeError("AI service not initialized")
        
        try:
            # Retrieve relevant context using RAG
            rag_context = []
            sources = []
            
            if self.rag_service:
                try:
                    retrieval_result = await self.rag_service.retrieve_relevant_context(
                        query=message,
                        top_k=6
                    )
                    rag_context = retrieval_result.contexts
                    sources = retrieval_result.sources

                    logger.info(f"Retrieved {len(rag_context)} relevant contexts")

                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}")

            # Get lineage context from Marquez (if available)
            lineage_context = ""
            if self.marquez_service:
                try:
                    lineage_context = await self.marquez_service.get_context_for_prompt(message)
                    if lineage_context:
                        logger.info("Added lineage context from Marquez")
                except Exception as e:
                    logger.warning(f"Marquez context retrieval failed: {e}")

            # Build prompt with context
            prompt = self._build_prompt(message, rag_context, context, lineage_context)
            
            # Generate response
            if self.is_api_model:
                response_text = await self._generate_api_response(prompt)
            else:
                response_text = await self._generate_local_response(prompt)
            
            return {
                "response": response_text,
                "context": {
                    "rag_contexts": len(rag_context),
                    "sources": sources[:10]  # Limit sources in response
                },
                "metadata": {
                    "model": self.model_manager.model_type,
                    "timestamp": time.time(),
                    "rag_enabled": bool(self.rag_service),
                    "lineage_enabled": bool(lineage_context),
                    "sources": sources
                }
            }
            
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            return {
                "response": f"Error: Unable to process request - {str(e)}",
                "context": {},
                "metadata": {
                    "model": self.model_manager.model_type,
                    "timestamp": time.time(),
                    "rag_enabled": bool(self.rag_service),
                    "error": str(e)
                }
            }
    
    def _build_prompt(
        self,
        message: str,
        rag_context: List[str],
        context: Optional[Dict[str, Any]] = None,
        lineage_context: str = ""
    ) -> str:
        """Build prompt with RAG and lineage context"""

        system_prompt = """You are the Qubinode Navigator AI Assistant, an expert in infrastructure automation, hypervisor deployment, and virtualization technologies.

Your expertise includes:
- KVM/libvirt virtualization
- KCLI for VM provisioning and management
- OpenShift/Kubernetes deployment
- RHEL/CentOS/Rocky Linux systems
- Cloud providers (AWS, Azure, GCP, Hetzner, Equinix)
- Infrastructure automation and CI/CD
- Airflow DAG orchestration and troubleshooting
- Security hardening and monitoring

You have access to real-time infrastructure lineage data from Marquez/OpenLineage, which shows recent DAG runs, failures, and deployment history. Use this context to provide informed answers about the current state of the infrastructure.

Provide helpful, accurate, and actionable guidance for infrastructure deployment and management."""

        prompt_parts = [system_prompt]

        # Add lineage context if available (real-time infrastructure state)
        if lineage_context:
            prompt_parts.append(f"\n{lineage_context}")

        # Add RAG documentation context
        if rag_context:
            context_text = "\n\n".join(rag_context[:4])  # Limit context to avoid token limits
            prompt_parts.append(f"\nRelevant Documentation:\n{context_text}")

        prompt_parts.append(f"\nUser Question: {message}\n\nResponse:")

        return "\n".join(prompt_parts)
    
    async def _generate_local_response(self, prompt: str) -> str:
        """Generate response using local model"""
        try:
            # Use the LangChain LLM wrapper
            response = await asyncio.to_thread(self.llm, prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Local model generation failed: {e}")
            raise
    
    async def _generate_api_response(self, prompt: str) -> str:
        """Generate response using API model"""
        try:
            response = await self.llm._acall(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"API model generation failed: {e}")
            raise
    
    async def process_message(self, message: str, context: dict = None, **kwargs) -> dict:
        """Process a user message and return AI response with RAG enhancement."""
        try:
            # Use the chat method which already handles RAG and context
            response = await self.chat(message, context)
            
            # Return in the expected format for compatibility
            return {
                "text": response.get("response", ""),
                "rag_context": response.get("rag_context", []),
                "model_info": response.get("model_info", {}),
                "timestamp": response.get("timestamp", time.time())
            }
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "text": f"Error processing message: {str(e)}",
                "rag_context": [],
                "model_info": {},
                "timestamp": time.time()
            }

    def get_available_diagnostic_tools(self) -> dict:
        """Get list of available diagnostic tools."""
        try:
            return diagnostic_registry.list_tools()
        except Exception as e:
            logger.error(f"Error getting diagnostic tools: {e}")
            return {}

    async def get_lineage_summary(self) -> Dict[str, Any]:
        """Get lineage summary from Marquez for API endpoint."""
        if not self.marquez_service:
            return {
                "available": False,
                "message": "Marquez context service not initialized"
            }
        try:
            return await self.marquez_service.get_lineage_summary()
        except Exception as e:
            logger.error(f"Error getting lineage summary: {e}")
            return {"available": False, "error": str(e)}

    async def get_job_lineage(self, job_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed lineage for a specific job/DAG."""
        if not self.marquez_service:
            return None
        try:
            return await self.marquez_service.get_job_details(job_name)
        except Exception as e:
            logger.error(f"Error getting job lineage for {job_name}: {e}")
            return None

    async def run_diagnostics(self, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run system diagnostics (compatibility method)"""
        try:
            tool_name = None
            if request and isinstance(request, dict):
                tool_name = request.get('tool_name')
            return await self.get_diagnostics(tool_name)
        except Exception as e:
            logger.error(f"Error running diagnostics: {e}")
            return {"error": str(e), "timestamp": time.time()}

    async def run_specific_diagnostic_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Run a specific diagnostic tool"""
        try:
            return await diagnostic_registry.run_diagnostic(tool_name)
        except Exception as e:
            logger.error(f"Error running diagnostic tool {tool_name}: {e}")
            return {"error": str(e), "tool": tool_name, "timestamp": time.time()}

    async def get_diagnostics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get system diagnostics"""
        return await diagnostic_registry.run_diagnostic(tool_name)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        return self.model_manager.get_model_info()
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware capabilities and recommendations"""
        return self.model_manager.detect_hardware_capabilities()

    async def cleanup(self):
        """Cleanup method for compatibility (alias for shutdown)"""
        await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the AI service"""
        logger.info("Shutting down Enhanced AI service...")
        
        if self.llama_process:
            self.llama_process.terminate()
            try:
                self.llama_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.llama_process.kill()
            logger.info("llama.cpp server stopped")


class LocalLlamaCppLLM(LLM):
    """LangChain wrapper for local llama.cpp server"""
    
    server_url: str = "http://localhost:8081"
    max_tokens: int = 512
    temperature: float = 0.7
    
    @property
    def _llm_type(self) -> str:
        return "llama_cpp_local"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the local llama.cpp server"""
        try:
            response = httpx.post(
                f"{self.server_url}/completion",
                json={
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stop": stop or []
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result.get("content", "")
        except Exception as e:
            logger.error(f"Local model call failed: {e}")
            raise


class LiteLLMLLM(LLM):
    """LangChain wrapper for LiteLLM API models"""
    
    model_name: str
    api_endpoint: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.7
    
    @property
    def _llm_type(self) -> str:
        return "litellm_api"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call API model through LiteLLM"""
        if not LITELLM_AVAILABLE:
            raise RuntimeError("LiteLLM not available")
        
        try:
            response = litellm.completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                api_base=self.api_endpoint
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LiteLLM API call failed: {e}")
            raise
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Async call to API model"""
        return await asyncio.to_thread(self._call, prompt, stop, run_manager, **kwargs)


def create_enhanced_ai_service(config: Dict[str, Any]) -> EnhancedAIService:
    """Factory function to create enhanced AI service"""
    return EnhancedAIService(config)
