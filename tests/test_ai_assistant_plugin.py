"""
Tests for AI Assistant Plugin

Tests the integration of AI Assistant with the plugin framework.
"""

import json
import os
import sys
import unittest.mock as mock
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.base_plugin import ExecutionContext, PluginResult, PluginStatus, SystemState
from plugins.services.ai_assistant_plugin import AIAssistantPlugin


class TestAIAssistantPlugin:
    """Test cases for AI Assistant Plugin"""

    def setup_method(self):
        """Setup test environment"""
        self.config = {
            "ai_service_url": "http://localhost:8080",
            "container_name": "test-ai-assistant",
            "ai_assistant_path": "/tmp/test-ai-assistant",
            "auto_start": True,
            "health_check_timeout": 10,
            "enable_diagnostics": True,
            "enable_rag": True,
        }

        # Test configurations for different deployment modes
        self.dev_config = {**self.config, "deployment_mode": "development"}

        self.prod_config = {**self.config, "deployment_mode": "production"}

        self.auto_config = {**self.config, "deployment_mode": "auto"}

        self.custom_config = {
            **self.config,
            "deployment_mode": "production",
            "container_image": "custom-registry.example.com/qubinode-ai-assistant:v1.2.3",
        }

        self.plugin = AIAssistantPlugin(self.config)
        self.context = ExecutionContext(
            inventory="localhost", environment="test", config={"test": True}
        )

    def test_plugin_initialization(self):
        """Test plugin initialization"""
        assert self.plugin.name == "AIAssistantPlugin"
        assert self.plugin.version == "1.0.0"
        assert self.plugin.ai_service_url == "http://localhost:8080"
        assert self.plugin.container_name == "test-ai-assistant"
        assert self.plugin.enable_diagnostics is True
        assert self.plugin.enable_rag is True
        assert hasattr(self.plugin, "deployment_mode")
        assert hasattr(self.plugin, "image_config")

    def test_plugin_capabilities(self):
        """Test plugin capabilities"""
        expected_capabilities = [
            "system_diagnostics",
            "deployment_guidance",
            "troubleshooting_assistance",
            "rag_knowledge_retrieval",
            "kvm_hypervisor_support",
            "ansible_automation_help",
        ]

        assert self.plugin.capabilities == expected_capabilities

    def test_get_dependencies(self):
        """Test plugin dependencies"""
        dependencies = self.plugin.get_dependencies()
        assert dependencies == []

    def test_validate_config_success(self):
        """Test successful configuration validation"""
        with patch("os.path.exists", return_value=True):
            assert self.plugin.validate_config() is True

    def test_validate_config_failure(self):
        """Test configuration validation failure"""
        with patch("os.path.exists", return_value=False):
            assert self.plugin.validate_config() is False

    @patch("subprocess.run")
    def test_container_exists_true(self, mock_subprocess):
        """Test container exists check - positive case"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [{"Names": ["test-ai-assistant"], "State": "running"}]
        )
        mock_subprocess.return_value = mock_result

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        assert self.plugin._container_exists() is True

    @patch("subprocess.run")
    def test_container_exists_false(self, mock_subprocess):
        """Test container exists check - negative case"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([])
        mock_subprocess.return_value = mock_result

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        assert self.plugin._container_exists() is False

    @patch("subprocess.run")
    def test_container_running_true(self, mock_subprocess):
        """Test container running check - positive case"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [{"Names": ["test-ai-assistant"], "State": "running"}]
        )
        mock_subprocess.return_value = mock_result

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        assert self.plugin._container_running() is True

    @patch("subprocess.run")
    def test_container_running_false(self, mock_subprocess):
        """Test container running check - negative case"""
        # Mock both docker and podman calls to return empty container list
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([])  # Empty list - no containers
        mock_subprocess.return_value = mock_result

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        assert self.plugin._container_running() is False

    @patch("requests.get")
    def test_ai_service_healthy_true(self, mock_get):
        """Test AI service health check - positive case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        assert self.plugin._ai_service_healthy() is True

    @patch("requests.get")
    def test_ai_service_healthy_false(self, mock_get):
        """Test AI service health check - negative case"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        assert self.plugin._ai_service_healthy() is False

    @patch("requests.get")
    def test_rag_system_loaded_true(self, mock_get):
        """Test RAG system loaded check - positive case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ai_service": {"components": {"rag_service": {"documents_loaded": True}}}
        }
        mock_get.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        assert self.plugin._rag_system_loaded() is True

    @patch("requests.get")
    def test_diagnostic_tools_available_true(self, mock_get):
        """Test diagnostic tools available check - positive case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_tools": 6}
        mock_get.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        assert self.plugin._diagnostic_tools_available() is True

    def test_check_state(self):
        """Test system state checking"""
        with patch.object(
            self.plugin, "_container_exists", return_value=True
        ), patch.object(
            self.plugin, "_container_running", return_value=True
        ), patch.object(
            self.plugin, "_ai_service_healthy", return_value=True
        ), patch.object(
            self.plugin, "_rag_system_loaded", return_value=True
        ), patch.object(
            self.plugin, "_diagnostic_tools_available", return_value=True
        ), patch(
            "os.path.exists", return_value=True
        ):

            state = self.plugin.check_state()

            assert isinstance(state, SystemState)
            assert state.get("container_exists") is True
            assert state.get("container_running") is True
            assert state.get("ai_service_healthy") is True
            assert state.get("rag_system_loaded") is True
            assert state.get("diagnostic_tools_available") is True
            assert state.get("ai_assistant_directory_exists") is True

    def test_get_desired_state(self):
        """Test desired state generation"""
        desired_state = self.plugin.get_desired_state(self.context)

        assert isinstance(desired_state, SystemState)
        assert desired_state.get("container_exists") is True
        assert desired_state.get("container_running") is True
        assert desired_state.get("ai_service_healthy") is True
        assert desired_state.get("rag_system_loaded") is True
        assert desired_state.get("diagnostic_tools_available") is True
        assert desired_state.get("ai_assistant_directory_exists") is True

    def test_apply_changes_already_configured(self):
        """Test apply changes when system is already in desired state"""
        current_state = SystemState(
            {
                "container_exists": True,
                "container_running": True,
                "ai_service_healthy": True,
                "rag_system_loaded": True,
                "diagnostic_tools_available": True,
                "ai_assistant_directory_exists": True,
            }
        )

        desired_state = current_state

        # Mock the execute method to return skipped result
        with patch.object(
            self.plugin, "check_state", return_value=current_state
        ), patch.object(self.plugin, "get_desired_state", return_value=desired_state):

            result = self.plugin.execute(self.context)

            assert isinstance(result, PluginResult)
            assert result.status == PluginStatus.SKIPPED
            assert result.changed is False

    @patch("os.path.exists")
    def test_apply_changes_missing_directory(self, mock_exists):
        """Test apply changes when AI assistant directory is missing"""
        mock_exists.return_value = False

        current_state = SystemState({"ai_assistant_directory_exists": False})

        desired_state = SystemState({"ai_assistant_directory_exists": True})

        result = self.plugin.apply_changes(current_state, desired_state, self.context)

        assert isinstance(result, PluginResult)
        assert result.status == PluginStatus.FAILED
        assert "AI Assistant directory not found" in result.message

    @patch("os.path.exists")
    @patch.object(AIAssistantPlugin, "_build_container")
    @patch.object(AIAssistantPlugin, "_start_container")
    @patch.object(AIAssistantPlugin, "_wait_for_health")
    def test_apply_changes_development_build_flow(
        self, mock_wait_health, mock_start, mock_build, mock_exists
    ):
        """Test apply changes flow for development mode with building"""
        mock_exists.return_value = True
        mock_build.return_value = True
        mock_start.return_value = True
        mock_wait_health.return_value = True

        config = {
            "deployment_mode": "development",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        current_state = SystemState(
            {
                "container_exists": False,
                "container_running": False,
                "ai_service_healthy": False,
                "ai_assistant_directory_exists": True,
            }
        )

        desired_state = SystemState(
            {
                "container_exists": True,
                "container_running": True,
                "ai_service_healthy": True,
                "ai_assistant_directory_exists": True,
            }
        )

        result = plugin.apply_changes(current_state, desired_state, self.context)

        assert isinstance(result, PluginResult)
        assert result.status == PluginStatus.COMPLETED
        assert result.changed is True
        assert "Built AI Assistant container" in str(result.data.get("changes", []))
        mock_build.assert_called_once()
        mock_start.assert_called_once()

    @patch("os.path.exists")
    @patch.object(AIAssistantPlugin, "_pull_container")
    @patch.object(AIAssistantPlugin, "_start_container")
    @patch.object(AIAssistantPlugin, "_wait_for_health")
    def test_apply_changes_production_pull_flow(
        self, mock_wait_health, mock_start, mock_pull, mock_exists
    ):
        """Test apply changes flow for production mode with pulling"""
        mock_exists.return_value = True
        mock_pull.return_value = True
        mock_start.return_value = True
        mock_wait_health.return_value = True

        config = {
            "deployment_mode": "production",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        current_state = SystemState(
            {
                "container_exists": False,
                "container_running": False,
                "ai_service_healthy": False,
                "ai_assistant_directory_exists": True,
            }
        )

        desired_state = SystemState(
            {
                "container_exists": True,
                "container_running": True,
                "ai_service_healthy": True,
                "ai_assistant_directory_exists": True,
            }
        )

        result = plugin.apply_changes(current_state, desired_state, self.context)

        assert isinstance(result, PluginResult)
        assert result.status == PluginStatus.COMPLETED
        assert result.changed is True
        assert "Pulled AI Assistant container" in str(result.data.get("changes", []))
        mock_pull.assert_called_once()
        mock_start.assert_called_once()

    @patch("requests.post")
    def test_ask_ai_success(self, mock_post):
        """Test asking AI a question - success case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "This is an AI response",
            "metadata": {"model": "granite-4.0-micro"},
        }
        mock_post.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        result = self.plugin.ask_ai("What is KVM?")

        assert "text" in result
        assert result["text"] == "This is an AI response"
        assert "metadata" in result

    @patch("requests.post")
    def test_ask_ai_failure(self, mock_post):
        """Test asking AI a question - failure case"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        result = self.plugin.ask_ai("What is KVM?")

        assert "error" in result
        assert "AI request failed" in result["error"]

    @patch("requests.post")
    def test_run_diagnostics_success(self, mock_post):
        """Test running diagnostics - success case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "diagnostics": {"summary": {"successful_tools": 6, "total_tools": 6}}
        }
        mock_post.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        result = self.plugin.run_diagnostics()

        assert "diagnostics" in result
        assert result["diagnostics"]["summary"]["successful_tools"] == 6

    @patch("requests.post")
    def test_run_diagnostics_specific_tool(self, mock_post):
        """Test running specific diagnostic tool"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tool_result": {"success": True, "data": {"hostname": "test-host"}}
        }
        mock_post.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        result = self.plugin.run_diagnostics("system_info")

        assert "tool_result" in result
        assert result["tool_result"]["success"] is True

    @patch("requests.get")
    def test_get_available_tools_success(self, mock_get):
        """Test getting available diagnostic tools - success case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "available_tools": {
                "system_info": "Gather basic system information",
                "resource_usage": "Monitor CPU, memory, disk usage",
            },
            "total_tools": 2,
        }
        mock_get.return_value = mock_response

        # Initialize plugin to set up attributes
        self.plugin.initialize()

        result = self.plugin.get_available_tools()

        assert "available_tools" in result
        assert "system_info" in result["available_tools"]
        assert result["total_tools"] == 2

    def test_get_health_status(self):
        """Test plugin health status"""
        with patch.object(self.plugin, "_get_ai_assistant_status") as mock_status:
            mock_status.return_value = {
                "container_running": True,
                "ai_service_healthy": True,
            }

            health = self.plugin.get_health_status()

            assert health["name"] == "AIAssistantPlugin"
            assert health["version"] == "1.0.0"
            assert "ai_service_url" in health
            assert "capabilities" in health
            assert "ai_assistant_status" in health
            assert "container_image" in health
            assert "deployment_mode" in health


class TestAIAssistantDeploymentStrategy:
    """Test cases for AI Assistant deployment strategy"""

    def test_development_mode_initialization(self):
        """Test plugin initialization in development mode"""
        config = {
            "deployment_mode": "development",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert plugin.deployment_mode == "development"
        assert plugin.container_image == "localhost/qubinode-ai-assistant:latest"
        assert plugin.image_config["development"]["build_required"] is True

    def test_production_mode_initialization(self):
        """Test plugin initialization in production mode"""
        config = {
            "deployment_mode": "production",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert plugin.deployment_mode == "production"
        assert plugin.container_image == "quay.io/takinosh/qubinode-ai-assistant:latest"
        assert plugin.image_config["production"]["build_required"] is False

    def test_custom_image_override(self):
        """Test custom container image override"""
        custom_image = "custom-registry.example.com/qubinode-ai-assistant:v1.2.3"
        config = {
            "deployment_mode": "production",
            "container_image": custom_image,
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert plugin.container_image == custom_image

    @patch.dict(os.environ, {"QUBINODE_DEPLOYMENT_MODE": "development"})
    def test_auto_mode_environment_variable(self):
        """Test auto mode detection via environment variable"""
        config = {
            "deployment_mode": "auto",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert plugin.deployment_mode == "development"

    @patch("os.path.exists")
    def test_auto_mode_container_detection(self, mock_exists):
        """Test auto mode detection for container environment"""

        def side_effect(path):
            if path == "/.dockerenv":
                return True
            return False

        mock_exists.side_effect = side_effect

        config = {
            "deployment_mode": "auto",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert plugin.deployment_mode == "production"

    @patch("os.path.exists")
    def test_auto_mode_development_detection(self, mock_exists):
        """Test auto mode detection for development environment"""

        def side_effect(path):
            if "/tmp/test-ai-assistant" in path:
                return True
            if path.endswith("Dockerfile"):
                return True
            return False

        mock_exists.side_effect = side_effect

        config = {
            "deployment_mode": "auto",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert plugin.deployment_mode == "development"

    def test_unknown_deployment_mode_fallback(self):
        """Test fallback to development for unknown deployment mode"""
        config = {
            "deployment_mode": "unknown_mode",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert plugin.deployment_mode == "development"
        assert plugin.container_image == "localhost/qubinode-ai-assistant:latest"

    @patch("subprocess.run")
    @patch("os.path.exists")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_build_container_development_mode(
        self, mock_getcwd, mock_chdir, mock_exists, mock_subprocess
    ):
        """Test container building in development mode"""
        mock_getcwd.return_value = "/current/dir"
        mock_exists.return_value = True

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        config = {
            "deployment_mode": "development",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        result = plugin._build_container()

        assert result is True
        mock_subprocess.assert_called_once_with(
            ["./scripts/build.sh"], capture_output=True, text=True, timeout=300
        )

    def test_build_container_production_mode_error(self):
        """Test that building is not allowed in production mode"""
        config = {
            "deployment_mode": "production",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        result = plugin._build_container()

        assert result is False

    @patch("subprocess.run")
    def test_pull_container_success(self, mock_subprocess):
        """Test successful container pull"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        config = {
            "deployment_mode": "production",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        result = plugin._pull_container()

        assert result is True
        mock_subprocess.assert_called_with(
            ["podman", "pull", "quay.io/takinosh/qubinode-ai-assistant:latest"],
            capture_output=True,
            text=True,
            timeout=300,
        )

    @patch("subprocess.run")
    def test_pull_container_fallback_to_docker(self, mock_subprocess):
        """Test container pull fallback from podman to docker"""

        def side_effect(*args, **kwargs):
            if args[0][0] == "podman":
                raise FileNotFoundError("podman not found")
            elif args[0][0] == "docker":
                result = MagicMock()
                result.returncode = 0
                return result

        mock_subprocess.side_effect = side_effect

        config = {
            "deployment_mode": "production",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        result = plugin._pull_container()

        assert result is True

    @patch("subprocess.run")
    def test_pull_container_failure(self, mock_subprocess):
        """Test container pull failure"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Pull failed"
        mock_subprocess.return_value = mock_result

        config = {
            "deployment_mode": "production",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        result = plugin._pull_container()

        assert result is False


class TestAIAssistantVersionManagement:
    """Test cases for AI Assistant version management"""

    def test_version_configuration_initialization(self):
        """Test version configuration initialization"""
        config = {
            "container_version": "1.2.0",
            "version_strategy": "specific",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert plugin.container_version == "1.2.0"
        assert plugin.version_strategy == "specific"

    def test_default_version_configuration(self):
        """Test default version configuration"""
        config = {"ai_assistant_path": "/tmp/test-ai-assistant"}
        plugin = AIAssistantPlugin(config)

        assert plugin.container_version == "latest"
        assert plugin.version_strategy == "auto"

    @patch("os.path.exists")
    @patch("builtins.open", mock_open(read_data="1.5.0"))
    def test_get_development_tag_from_version_file(self, mock_exists):
        """Test getting development tag from VERSION file"""
        mock_exists.return_value = True

        config = {
            "deployment_mode": "development",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        # The tag should be read from VERSION file
        assert "1.5.0" in plugin.container_image

    def test_get_development_tag_with_specific_version(self):
        """Test getting development tag with specific version"""
        config = {
            "deployment_mode": "development",
            "container_version": "2.0.0",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert "2.0.0" in plugin.container_image

    def test_get_production_tag_latest_strategy(self):
        """Test getting production tag with latest strategy"""
        config = {
            "deployment_mode": "production",
            "version_strategy": "latest",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert "latest" in plugin.container_image

    def test_get_production_tag_specific_strategy(self):
        """Test getting production tag with specific strategy"""
        config = {
            "deployment_mode": "production",
            "version_strategy": "specific",
            "container_version": "1.3.0",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert "1.3.0" in plugin.container_image

    @patch("os.path.exists")
    @patch("builtins.open", mock_open(read_data="2.1.0"))
    def test_get_production_tag_semver_strategy(self, mock_exists):
        """Test getting production tag with semver strategy"""
        mock_exists.return_value = True

        config = {
            "deployment_mode": "production",
            "version_strategy": "semver",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert "2.1.0" in plugin.container_image

    @patch("os.path.exists")
    @patch("builtins.open", mock_open(read_data="2.1.0-alpha.1"))
    def test_get_latest_stable_version_excludes_prerelease(self, mock_exists):
        """Test that latest stable version excludes prerelease versions"""
        mock_exists.return_value = True

        config = {
            "deployment_mode": "production",
            "version_strategy": "semver",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        # Should fall back to latest since 2.1.0-alpha.1 is prerelease
        assert "latest" in plugin.container_image

    @patch.dict(os.environ, {"QUBINODE_AI_VERSION": "3.0.0"})
    def test_environment_version_override(self):
        """Test version override via environment variable"""
        config = {
            "deployment_mode": "production",
            "version_strategy": "semver",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        assert "3.0.0" in plugin.container_image

    def test_version_in_health_status(self):
        """Test that version information is included in health status"""
        config = {
            "container_version": "1.4.0",
            "version_strategy": "specific",
            "ai_assistant_path": "/tmp/test-ai-assistant",
        }
        plugin = AIAssistantPlugin(config)

        with patch.object(plugin, "_get_ai_assistant_status") as mock_status:
            mock_status.return_value = {"container_running": True}

            health = plugin.get_health_status()

            assert "container_version" in health
            assert "version_strategy" in health
            assert health["container_version"] == "1.4.0"
            assert health["version_strategy"] == "specific"

    @patch("os.path.exists")
    def test_version_file_read_error_handling(self, mock_exists):
        """Test graceful handling of VERSION file read errors"""
        mock_exists.return_value = True

        with patch("builtins.open", side_effect=IOError("Permission denied")):
            config = {
                "deployment_mode": "development",
                "ai_assistant_path": "/tmp/test-ai-assistant",
            }
            plugin = AIAssistantPlugin(config)

            # Should fall back to latest on read error
            assert "latest" in plugin.container_image

    def test_auto_version_strategy_with_stable_version(self):
        """Test auto version strategy with stable version available"""
        with patch.object(
            AIAssistantPlugin, "_get_latest_stable_version", return_value="1.8.0"
        ):
            config = {
                "deployment_mode": "production",
                "version_strategy": "auto",
                "ai_assistant_path": "/tmp/test-ai-assistant",
            }
            plugin = AIAssistantPlugin(config)

            assert "1.8.0" in plugin.container_image

    def test_auto_version_strategy_fallback_to_latest(self):
        """Test auto version strategy fallback to latest"""
        with patch.object(
            AIAssistantPlugin, "_get_latest_stable_version", return_value="latest"
        ):
            config = {
                "deployment_mode": "production",
                "version_strategy": "auto",
                "ai_assistant_path": "/tmp/test-ai-assistant",
            }
            plugin = AIAssistantPlugin(config)

            assert "latest" in plugin.container_image


class TestAIAssistantPluginIntegration:
    """Integration tests for AI Assistant Plugin"""

    @pytest.mark.integration
    def test_plugin_discovery(self):
        """Test that plugin can be discovered by plugin manager"""
        # This would require actual plugin manager setup
        pass

    @pytest.mark.integration
    def test_plugin_execution_flow(self):
        """Test complete plugin execution flow"""
        # This would require actual container and AI service
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
