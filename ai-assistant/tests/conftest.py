"""
Pytest configuration and shared fixtures for AI Assistant tests
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Set TEST_MODE before any src imports to prevent module-level initialization issues
os.environ["TEST_MODE"] = "true"

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Note: We do NOT mock qdrant_client, sentence_transformers, or smolagents here.
# Tests that require these dependencies use pytest.mark.skipif decorators.
# Global mocking breaks the skipif checks and causes MagicMock await errors.

# Only mock litellm if truly not available (it's usually installed)
if "litellm" not in sys.modules:
    sys.modules["litellm"] = MagicMock()

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Provide a mock configuration dictionary"""
    return {
        "ai": {
            "model_name": "granite-4.0-micro",
            "model_path": "/tmp/test-models/granite-4.0-micro.gguf",
            "max_tokens": 512,
            "temperature": 0.7,
            "context_size": 2048,
            "threads": 4,
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "llama_server_port": 8081,
            "log_level": "INFO",
            "timeout": 30,
        },
        "features": {
            "diagnostics": True,
            "system_monitoring": True,
            "log_analysis": True,
            "rag_enabled": True,
        },
        "security": {
            "enable_auth": False,
            "api_key": None,
            "allowed_hosts": ["*"],
            "rate_limit": 100,
        },
        "storage": {
            "models_dir": "/tmp/test-models",
            "data_dir": "/tmp/test-data",
            "logs_dir": "/tmp/test-logs",
            "vector_db_path": "/tmp/test-data/qdrant",
        },
        "qubinode": {
            "integration_enabled": True,
            "plugin_framework_path": "/opt/qubinode/core",
            "ansible_callback": True,
            "setup_hooks": True,
        },
        "ai_service": {
            "model_type": "granite-4.0-micro",
            "use_gpu": "false",
            "gpu_layers": "0",
            "threads": "4",
            "model_path": "/tmp/test-models/granite-4.0-micro.gguf",
            "context_length": "4096",
            "temperature": "0.7",
            "max_tokens": "512",
        },
    }


@pytest.fixture
def mock_config_manager(mock_config):
    """Provide a mock ConfigManager"""
    from config_manager import ConfigManager

    manager = ConfigManager(config_path="/tmp/test-config.yaml")
    manager.config = mock_config
    return manager


@pytest.fixture
def mock_httpx_client():
    """Provide a mock httpx client"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_instance


@pytest.fixture
def mock_httpx_response():
    """Provide a mock httpx response"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "Test response"}
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_llm_response():
    """Provide a mock LLM response"""
    return {
        "content": "This is a test AI response about infrastructure automation.",
        "model": "granite-4.0-micro",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }


@pytest.fixture
def mock_rag_service():
    """Provide a mock RAG service"""
    mock_service = AsyncMock()
    mock_service.initialize = AsyncMock(return_value=True)
    mock_service.get_context_for_query = AsyncMock(return_value=("# Mock Context\n\nThis is mock context.", ["docs/mock.md"]))
    mock_service.search_documents = AsyncMock(return_value=[])
    mock_service.get_health_status = AsyncMock(
        return_value={
            "available": True,
            "initialized": True,
            "documents_loaded": True,
            "document_count": 100,
            "embeddings_model": "all-MiniLM-L6-v2",
        }
    )
    return mock_service


@pytest.fixture
def mock_diagnostic_registry():
    """Provide a mock diagnostic registry"""
    mock_registry = MagicMock()
    mock_registry.list_tools.return_value = {
        "system_info": "Get system information",
        "resource_usage": "Get resource usage",
        "service_status": "Get service status",
    }
    mock_registry.run_tool = AsyncMock(
        return_value=MagicMock(
            tool_name="system_info",
            success=True,
            data={"hostname": "test-host"},
            error=None,
            execution_time=0.1,
            to_dict=lambda: {
                "tool_name": "system_info",
                "success": True,
                "data": {"hostname": "test-host"},
            },
        )
    )
    return mock_registry


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file"""
    config_content = """
ai:
  model_name: granite-4.0-micro
  model_path: /tmp/test-models/granite-4.0-micro.gguf
  max_tokens: 512
  temperature: 0.7
  context_size: 2048
  threads: 4

server:
  host: 0.0.0.0
  port: 8080
  llama_server_port: 8081
  log_level: INFO
  timeout: 30

features:
  diagnostics: true
  rag_enabled: true
  system_monitoring: true
  log_analysis: true

security:
  enable_auth: false
  api_key: null
  allowed_hosts:
    - "*"
  rate_limit: 100

storage:
  models_dir: /tmp/test-models
  data_dir: /tmp/test-data
  logs_dir: /tmp/test-logs
  vector_db_path: /tmp/test-data/qdrant

qubinode:
  integration_enabled: true
  plugin_framework_path: /opt/qubinode/core
  ansible_callback: true
  setup_hooks: true
"""
    config_file = tmp_path / "ai_config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def temp_model_file(tmp_path):
    """Create a temporary model file placeholder"""
    models_dir = tmp_path / "models"
    models_dir.mkdir(exist_ok=True)
    model_file = models_dir / "granite-4.0-micro.gguf"
    model_file.write_text("# Placeholder model file for testing\n")
    return str(model_file)


@pytest.fixture
def mock_psutil():
    """Mock psutil for system resource tests"""
    with patch("psutil.cpu_percent", return_value=45.0):
        with patch("psutil.cpu_count", return_value=8):
            with patch(
                "psutil.virtual_memory",
                return_value=MagicMock(
                    total=16 * 1024**3,
                    available=8 * 1024**3,
                    percent=50.0,
                ),
            ):
                with patch(
                    "psutil.disk_usage",
                    return_value=MagicMock(
                        total=500 * 1024**3,
                        free=250 * 1024**3,
                        percent=50.0,
                    ),
                ):
                    with patch("psutil.getloadavg", return_value=(1.0, 0.8, 0.6)):
                        yield


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for command execution tests"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="success",
            stderr="",
        )
        yield mock_run


@pytest.fixture
def sample_chat_request():
    """Provide a sample chat request"""
    return {
        "message": "How do I deploy a VM with kcli?",
        "context": {"task": "vm_deployment"},
        "max_tokens": 256,
        "temperature": 0.7,
    }


@pytest.fixture
def sample_diagnostic_request():
    """Provide a sample diagnostic request"""
    return {
        "tool": "system_info",
        "include_ai_analysis": False,
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_temp_files(tmp_path):
    """Clean up temporary files after each test"""
    yield
    # Cleanup happens automatically with tmp_path


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
