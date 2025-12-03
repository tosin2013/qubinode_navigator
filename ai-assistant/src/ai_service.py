#!/usr/bin/env python3
"""
AI Service Module for Qubinode AI Assistant
Implements llama.cpp integration with Granite-4.0-Micro model
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from diagnostic_tools import diagnostic_registry
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.schema import Generation, LLMResult
from qdrant_rag_service import RetrievalResult, create_rag_service

logger = logging.getLogger(__name__)


class LlamaCppLLM(LLM):
    """Custom LangChain LLM wrapper for llama.cpp server."""

    server_url: str = "http://localhost:8081"
    max_tokens: int = 512
    temperature: float = 0.7

    @property
    def _llm_type(self) -> str:
        return "llama_cpp"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the llama.cpp server for inference."""
        try:
            response = httpx.post(
                f"{self.server_url}/completion",
                json={
                    "prompt": prompt,
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature),
                    "stop": stop or [],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("content", "")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: Unable to process request - {str(e)}"


class AIService:
    """Main AI service for handling inference and system integration."""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.llm = None
        self.server_process = None
        self.model_path = None
        self.is_initialized = False
        self.rag_service = None

    async def initialize(self):
        """Initialize the AI service."""
        try:
            logger.info("Initializing AI service...")

            # Load model
            await self._load_model()

            # Start llama.cpp server
            await self._start_llama_server()

            # Initialize LLM wrapper
            self.llm = LlamaCppLLM(server_url="http://localhost:8081")

            # Test the connection
            await self._test_connection()

            # Initialize RAG service
            self.rag_service = create_rag_service("/app/data")
            rag_initialized = await self.rag_service.initialize()
            if rag_initialized:
                logger.info("RAG service initialized successfully")
            else:
                logger.warning(
                    "RAG service initialization failed - using basic responses"
                )

            self.is_initialized = True
            logger.info("AI service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            raise

    async def _load_model(self):
        """Load the Granite-4.0-Micro model."""
        models_dir = Path("/app/models")
        models_dir.mkdir(exist_ok=True)

        # Check if model exists
        model_file = "granite-4.0-micro.gguf"
        self.model_path = models_dir / model_file

        if not self.model_path.exists():
            logger.info("Granite-4.0-Micro model not found, downloading...")
            await self._download_model()
        else:
            logger.info(f"Using existing model: {self.model_path}")

    async def _download_model(self):
        """Download Granite-4.0-Micro model in GGUF format."""
        # Official IBM Granite-4.0-Micro GGUF model (Q4_K_M quantization)
        model_url = "https://huggingface.co/ibm-granite/granite-4.0-micro-GGUF/resolve/main/granite-4.0-micro-Q4_K_M.gguf"

        try:
            logger.info("Downloading Granite-4.0-Micro model...")

            # Use wget for reliable download with progress
            cmd = [
                "wget",
                "-O",
                str(self.model_path),
                "--progress=bar:force",
                model_url,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info("Model downloaded successfully")
            else:
                logger.error(f"Model download failed: {stderr.decode()}")
                # Create a placeholder file for testing
                logger.warning("Creating placeholder model file for testing")
                self.model_path.write_text("# Placeholder model file\n")

        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            # Create placeholder for development
            self.model_path.write_text("# Placeholder model file\n")

    async def _start_llama_server(self):
        """Start the llama.cpp server."""
        try:
            logger.info("Starting llama.cpp server...")

            cmd = [
                "llama-server",
                "--model",
                str(self.model_path),
                "--host",
                "0.0.0.0",
                "--port",
                "8081",
                "--ctx-size",
                "2048",
                "--threads",
                str(os.cpu_count() or 4),
                "--log-disable",
            ]

            self.server_process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Wait for server to start
            await asyncio.sleep(5)

            if self.server_process.returncode is not None:
                stdout, stderr = await self.server_process.communicate()
                logger.error(f"llama-server failed to start: {stderr.decode()}")
                raise RuntimeError("Failed to start llama-server")

            logger.info("llama.cpp server started successfully")

        except Exception as e:
            logger.error(f"Error starting llama server: {e}")
            # For development, create a mock server
            logger.warning("Starting mock server for development")
            await self._start_mock_server()

    async def _start_mock_server(self):
        """Start a mock server for development/testing."""
        import uvicorn
        from fastapi import FastAPI

        mock_app = FastAPI()

        @mock_app.post("/completion")
        async def mock_completion(request: dict):
            prompt = request.get("prompt", "")
            return {
                "content": f"Mock AI response to: {prompt[:100]}...",
                "model": "granite-4.0-micro-mock",
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            }

        # Start mock server in background
        config = uvicorn.Config(
            mock_app, host="0.0.0.0", port=8081, log_level="warning"
        )
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())

        await asyncio.sleep(2)  # Give server time to start
        logger.info("Mock server started on port 8081")

    async def _test_connection(self):
        """Test connection to llama.cpp server."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8081/completion",
                    json={"prompt": "Test", "max_tokens": 10},
                    timeout=10.0,
                )
                response.raise_for_status()
                logger.info("AI service connection test successful")

        except Exception as e:
            logger.warning(f"Connection test failed: {e}")

    async def process_message(
        self, message: str, context: dict = None, **kwargs
    ) -> dict:
        """Process a user message and return AI response with RAG enhancement."""
        if not self.is_initialized:
            raise RuntimeError("AI service not initialized")

        try:
            # Get relevant documentation context using RAG
            rag_context = ""
            sources = []

            if self.rag_service:
                try:
                    rag_context, sources = await self.rag_service.get_context_for_query(
                        message
                    )
                    logger.info(f"Retrieved RAG context from {len(sources)} sources")
                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}")

            # Prepare enhanced prompt with RAG context
            system_prompt = self._get_system_prompt()

            # Build the full prompt with RAG context if available
            if rag_context:
                full_prompt = f"""{system_prompt}

{rag_context}

Based on the above documentation context, please answer the following question:

User: {message}
Assistant:"""
            else:
                full_prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"

            # Get AI response
            response = self.llm._call(full_prompt, **kwargs)

            return {
                "text": response,
                "context": context or {},
                "metadata": {
                    "model": "granite-4.0-micro",
                    "timestamp": time.time(),
                    "rag_enabled": bool(rag_context),
                    "sources": sources,
                },
            }

        except Exception as e:
            logger.error(f"Message processing error: {e}")
            return {
                "text": f"I apologize, but I encountered an error processing your request: {str(e)}",
                "context": context or {},
                "metadata": {"error": True},
            }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for Qubinode AI assistant."""
        return """You are the Qubinode Navigator AI Assistant, an expert in infrastructure automation and hypervisor deployment. You help users with:

- RHEL/CentOS/Rocky Linux system configuration
- KVM/libvirt hypervisor setup
- Ansible automation and troubleshooting
- Container orchestration with Podman
- Cloud provider integration (AWS, Hetzner, Equinix)
- Network and storage configuration
- Security best practices

Provide clear, actionable guidance. When troubleshooting, ask for specific error messages or logs. Always prioritize security and best practices."""

    async def run_diagnostics(self, request: dict) -> dict:
        """Run comprehensive system diagnostics with AI analysis using tool-calling framework."""
        try:
            # Extract parameters from request
            tool_name = request.get("tool", None)
            run_all = request.get("run_all", True)
            include_ai_analysis = request.get("include_ai_analysis", True)

            if tool_name:
                # Run specific diagnostic tool
                logger.info(f"Running specific diagnostic tool: {tool_name}")
                tool_result = await diagnostic_registry.run_tool(tool_name, **request)

                diagnostics_data = {
                    "tool_results": {tool_name: tool_result.to_dict()},
                    "summary": {
                        "tools_run": 1,
                        "successful": tool_result.success,
                        "execution_time": tool_result.execution_time,
                    },
                }
            else:
                # Run comprehensive diagnostics
                logger.info("Running comprehensive system diagnostics")
                diagnostics_data = (
                    await diagnostic_registry.run_comprehensive_diagnostics()
                )

            # Get AI analysis if requested
            ai_analysis = None
            if include_ai_analysis:
                try:
                    # Create a concise summary for AI analysis
                    analysis_data = {
                        "summary": diagnostics_data["summary"],
                        "key_findings": self._extract_key_findings(
                            diagnostics_data["tool_results"]
                        ),
                    }

                    analysis_prompt = f"""Analyze this system diagnostic data and provide actionable recommendations for a Qubinode KVM hypervisor environment:

{json.dumps(analysis_data, indent=2)}

Focus on:
1. Critical issues that need immediate attention
2. Performance optimization opportunities  
3. Security concerns
4. Resource utilization recommendations
5. KVM/libvirt specific issues

Provide clear, actionable recommendations."""

                    ai_response = await self.process_message(
                        analysis_prompt, max_tokens=500
                    )
                    ai_analysis = ai_response["text"]

                except Exception as e:
                    logger.warning(f"AI analysis failed: {e}")
                    ai_analysis = f"AI analysis unavailable: {str(e)}"

            result = {
                "diagnostics": diagnostics_data,
                "ai_analysis": ai_analysis,
                "available_tools": diagnostic_registry.list_tools(),
                "timestamp": time.time(),
            }

            logger.info(
                f"Diagnostics completed: {diagnostics_data['summary']['successful_tools']}/{diagnostics_data['summary']['total_tools']} tools successful"
            )
            return result

        except Exception as e:
            logger.error(f"Diagnostics error: {e}")
            return {"error": str(e), "timestamp": time.time()}

    def _extract_key_findings(self, tool_results: dict) -> dict:
        """Extract key findings from diagnostic tool results for AI analysis."""
        key_findings = {}

        try:
            # System info key points
            if "system_info" in tool_results and tool_results["system_info"]["success"]:
                sys_data = tool_results["system_info"]["data"]
                key_findings["system"] = {
                    "platform": sys_data.get("platform", "unknown"),
                    "uptime_hours": round(sys_data.get("uptime_seconds", 0) / 3600, 1),
                }

            # Resource usage key points
            if (
                "resource_usage" in tool_results
                and tool_results["resource_usage"]["success"]
            ):
                res_data = tool_results["resource_usage"]["data"]
                key_findings["resources"] = {
                    "cpu_usage": res_data.get("cpu", {}).get("usage_percent", 0),
                    "memory_usage": res_data.get("memory", {}).get("usage_percent", 0),
                    "disk_usage": {
                        k: v.get("usage_percent", 0)
                        for k, v in res_data.get("disk", {}).items()
                    },
                }

            # Service status key points
            if (
                "service_status" in tool_results
                and tool_results["service_status"]["success"]
            ):
                svc_data = tool_results["service_status"]["data"]
                services = svc_data.get("services", {})
                key_findings["services"] = {
                    "critical_services_down": [
                        name
                        for name, info in services.items()
                        if not info.get("active", False)
                    ],
                    "total_services_checked": len(services),
                }

            # KVM diagnostics key points
            if (
                "kvm_diagnostics" in tool_results
                and tool_results["kvm_diagnostics"]["success"]
            ):
                kvm_data = tool_results["kvm_diagnostics"]["data"]
                key_findings["kvm"] = {
                    "virtualization_support": kvm_data.get("vmx_support", False)
                    or kvm_data.get("svm_support", False),
                    "kvm_module_loaded": kvm_data.get("kvm_module_loaded", False),
                    "libvirt_available": kvm_data.get("libvirt_available", False),
                    "vm_count": kvm_data.get("vm_count", 0),
                }

            # Network diagnostics key points
            if (
                "network_diagnostics" in tool_results
                and tool_results["network_diagnostics"]["success"]
            ):
                net_data = tool_results["network_diagnostics"]["data"]
                connectivity = net_data.get("connectivity", {})
                key_findings["network"] = {
                    "connectivity_issues": [
                        target
                        for target, info in connectivity.items()
                        if not info.get("reachable", False)
                    ],
                    "dns_working": net_data.get("dns_resolution", {}).get(
                        "working", False
                    ),
                }

        except Exception as e:
            logger.warning(f"Failed to extract key findings: {e}")
            key_findings["extraction_error"] = str(e)

        return key_findings

    async def run_specific_diagnostic_tool(self, tool_name: str, **kwargs) -> dict:
        """Run a specific diagnostic tool by name."""
        try:
            tool_result = await diagnostic_registry.run_tool(tool_name, **kwargs)
            return {"tool_result": tool_result.to_dict(), "timestamp": time.time()}
        except Exception as e:
            logger.error(f"Specific diagnostic tool error: {e}")
            return {"error": str(e), "timestamp": time.time()}

    def get_available_diagnostic_tools(self) -> dict:
        """Get list of available diagnostic tools."""
        return diagnostic_registry.list_tools()

    async def list_models(self) -> dict:
        """List available AI models."""
        return {
            "current_model": "granite-4.0-micro",
            "model_path": str(self.model_path) if self.model_path else None,
            "model_size": (
                self.model_path.stat().st_size
                if self.model_path and self.model_path.exists()
                else 0
            ),
            "status": "loaded" if self.is_initialized else "not_loaded",
        }

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up AI service...")

        if self.server_process:
            try:
                self.server_process.terminate()
                await asyncio.wait_for(self.server_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.server_process.kill()
                await self.server_process.wait()

        logger.info("AI service cleanup complete")
