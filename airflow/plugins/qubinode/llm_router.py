"""
LLM Router for Qubinode Multi-Agent System
ADR-0049: Multi-Agent LLM Memory Architecture

Provides unified interface for routing LLM requests to appropriate models
based on agent role, environment, and availability.

Usage:
    from qubinode.llm_router import get_router, complete

    router = get_router()
    response = await router.complete(
        model="manager",  # or "developer", or specific model name
        messages=[{"role": "user", "content": "Generate a DAG..."}]
    )
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

# Configuration
LITELLM_CONFIG_PATH = os.getenv(
    "LITELLM_CONFIG_PATH", str(Path(__file__).parent / "litellm_config.yaml")
)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
ENVIRONMENT = os.getenv(
    "QUBINODE_ENVIRONMENT", "disconnected"
)  # disconnected, connected, development

# Lazy-loaded router instance
_router: Optional["LLMRouter"] = None


class LLMRouter:
    """
    Router for managing LLM model selection and request routing.

    Features:
    - Model aliasing (manager -> granite-instruct)
    - Environment-aware model filtering
    - Automatic fallback on failure
    - Health checking for local models
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the LLM router.

        Args:
            config_path: Path to LiteLLM config YAML file
        """
        self.config_path = config_path or LITELLM_CONFIG_PATH
        self.config: Dict[str, Any] = {}
        self.model_aliases: Dict[str, str] = {}
        self.available_models: List[str] = []
        self.environment = ENVIRONMENT

        self._load_config()
        self._litellm = None

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    self.config = yaml.safe_load(f)

                # Load model aliases
                self.model_aliases = self.config.get("model_aliases", {})

                # Load environment-specific models
                env_config = self.config.get("environments", {}).get(
                    self.environment, {}
                )
                self.available_models = env_config.get("allowed_models", [])
                self.default_model = env_config.get("default_model", "granite-instruct")

                logger.info(
                    f"LLM Router config loaded: {len(self.available_models)} models for {self.environment}"
                )
            else:
                logger.warning(
                    f"Config file not found: {self.config_path}, using defaults"
                )
                self._set_defaults()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._set_defaults()

    def _set_defaults(self) -> None:
        """Set default configuration for disconnected environment."""
        self.model_aliases = {
            "manager": "granite-instruct",
            "manager_fallback": "llama3",
            "developer": "granite-code",
            "developer_fallback": "codellama",
        }
        self.available_models = [
            "granite-code",
            "granite-instruct",
            "llama3",
            "codellama",
        ]
        self.default_model = "granite-instruct"

    def _get_litellm(self):
        """Lazy load LiteLLM module."""
        if self._litellm is None:
            try:
                import litellm

                self._litellm = litellm

                # Configure LiteLLM
                litellm.set_verbose = False
                litellm.drop_params = True

                logger.info("LiteLLM module loaded")
            except ImportError:
                logger.error("LiteLLM not installed. Run: pip install litellm")
                raise
        return self._litellm

    def resolve_model(self, model_or_alias: str) -> str:
        """
        Resolve model alias to actual model name.

        Args:
            model_or_alias: Model name or alias (e.g., "manager", "developer")

        Returns:
            Resolved model name for LiteLLM
        """
        # Check if it's an alias
        if model_or_alias in self.model_aliases:
            resolved = self.model_aliases[model_or_alias]
            logger.debug(f"Resolved alias '{model_or_alias}' to '{resolved}'")
            return resolved

        # Check if model is in available list
        if model_or_alias in self.available_models:
            return model_or_alias

        # Fallback to default
        logger.warning(
            f"Model '{model_or_alias}' not found, using default: {self.default_model}"
        )
        return self.default_model

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Model configuration dictionary
        """
        model_list = self.config.get("model_list", [])
        for model in model_list:
            if model.get("model_name") == model_name:
                return model
        return {}

    async def check_model_health(self, model_name: str) -> bool:
        """
        Check if a model is available and responding.

        Args:
            model_name: Name of the model to check

        Returns:
            True if model is healthy, False otherwise
        """
        try:
            config = self.get_model_config(model_name)
            litellm_params = config.get("litellm_params", {})

            # For Ollama models, check the API
            if "ollama" in litellm_params.get("model", ""):
                import httpx

                base_url = litellm_params.get("api_base", OLLAMA_BASE_URL)
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{base_url}/api/tags")
                    return response.status_code == 200
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {model_name}: {e}")
            return False

    async def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send completion request to the specified model.

        Args:
            model: Model name or alias
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters for LiteLLM

        Returns:
            Completion response dictionary
        """
        litellm = self._get_litellm()

        # Resolve model alias
        resolved_model = self.resolve_model(model)
        model_config = self.get_model_config(resolved_model)
        litellm_params = model_config.get("litellm_params", {})

        # Build the model string for LiteLLM
        model_string = litellm_params.get("model", f"ollama/{resolved_model}")

        # Prepare request parameters
        request_params = {
            "model": model_string,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        if max_tokens:
            request_params["max_tokens"] = max_tokens

        # Add API base for Ollama models
        if "api_base" in litellm_params:
            request_params["api_base"] = litellm_params["api_base"]

        # Add API key if present
        if "api_key" in litellm_params and litellm_params["api_key"]:
            request_params["api_key"] = litellm_params["api_key"]

        try:
            logger.info(f"Sending request to model: {model_string}")

            if stream:
                return await litellm.acompletion(**request_params, stream=True)
            else:
                response = await litellm.acompletion(**request_params)
                return {
                    "content": response.choices[0].message.content,
                    "model": resolved_model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                    "finish_reason": response.choices[0].finish_reason,
                }
        except Exception as e:
            logger.error(f"Completion failed for {resolved_model}: {e}")

            # Try fallback
            fallback_key = f"{model}_fallback"
            if fallback_key in self.model_aliases:
                fallback_model = self.model_aliases[fallback_key]
                logger.info(f"Trying fallback model: {fallback_model}")
                return await self.complete(
                    model=fallback_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    **kwargs,
                )
            raise

    async def complete_with_functions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        function_call: Optional[Union[str, Dict]] = "auto",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send completion request with function calling.

        Args:
            model: Model name or alias
            messages: List of message dictionaries
            functions: List of function definitions
            function_call: How to handle function calls
            **kwargs: Additional parameters

        Returns:
            Completion response with potential function call
        """
        litellm = self._get_litellm()

        resolved_model = self.resolve_model(model)
        model_config = self.get_model_config(resolved_model)

        # Check if model supports function calling
        model_info = model_config.get("model_info", {})
        if not model_info.get("supports_function_calling", False):
            logger.warning(f"Model {resolved_model} doesn't support function calling")
            # Fall back to regular completion
            return await self.complete(model, messages, **kwargs)

        litellm_params = model_config.get("litellm_params", {})
        model_string = litellm_params.get("model", f"ollama/{resolved_model}")

        request_params = {
            "model": model_string,
            "messages": messages,
            "functions": functions,
            "function_call": function_call,
            **kwargs,
        }

        if "api_base" in litellm_params:
            request_params["api_base"] = litellm_params["api_base"]

        try:
            response = await litellm.acompletion(**request_params)
            message = response.choices[0].message

            result = {
                "content": message.content,
                "model": resolved_model,
                "finish_reason": response.choices[0].finish_reason,
            }

            if hasattr(message, "function_call") and message.function_call:
                result["function_call"] = {
                    "name": message.function_call.name,
                    "arguments": message.function_call.arguments,
                }

            return result
        except Exception as e:
            logger.error(f"Function calling failed: {e}")
            raise

    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        List all available models for the current environment.

        Returns:
            List of model information dictionaries
        """
        models = []
        for model_name in self.available_models:
            config = self.get_model_config(model_name)
            model_info = config.get("model_info", {})
            models.append(
                {
                    "name": model_name,
                    "description": model_info.get("description", ""),
                    "context_window": model_info.get("context_window", 0),
                    "supports_function_calling": model_info.get(
                        "supports_function_calling", False
                    ),
                }
            )
        return models


def get_router() -> LLMRouter:
    """Get or create the default LLM router singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


async def complete(
    model: str, messages: List[Dict[str, str]], **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to complete using the default router.

    Args:
        model: Model name or alias
        messages: List of message dictionaries
        **kwargs: Additional parameters

    Returns:
        Completion response
    """
    router = get_router()
    return await router.complete(model, messages, **kwargs)


# =============================================================================
# Module Info
# =============================================================================

__version__ = "1.0.0"
__all__ = [
    "LLMRouter",
    "get_router",
    "complete",
]
