"""
Tests for AI Assistant Plugin

Tests the integration of AI Assistant with the plugin framework.
"""

import pytest
import unittest.mock as mock
from unittest.mock import patch, MagicMock
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from plugins.services.ai_assistant_plugin import AIAssistantPlugin
from core.base_plugin import PluginResult, SystemState, ExecutionContext, PluginStatus


class TestAIAssistantPlugin:
    """Test cases for AI Assistant Plugin"""
    
    def setup_method(self):
        """Setup test environment"""
        self.config = {
            'ai_service_url': 'http://localhost:8080',
            'container_name': 'test-ai-assistant',
            'container_image': 'localhost/qubinode-ai-assistant:latest',
            'ai_assistant_path': '/tmp/test-ai-assistant',
            'auto_start': True,
            'health_check_timeout': 10,
            'enable_diagnostics': True,
            'enable_rag': True
        }
        
        self.plugin = AIAssistantPlugin(self.config)
        self.context = ExecutionContext(
            inventory="localhost",
            environment="test",
            config={"test": True}
        )
    
    def test_plugin_initialization(self):
        """Test plugin initialization"""
        assert self.plugin.name == "AIAssistantPlugin"
        assert self.plugin.version == "1.0.0"
        assert self.plugin.ai_service_url == "http://localhost:8080"
        assert self.plugin.container_name == "test-ai-assistant"
        assert self.plugin.enable_diagnostics is True
        assert self.plugin.enable_rag is True
    
    def test_plugin_capabilities(self):
        """Test plugin capabilities"""
        expected_capabilities = [
            'system_diagnostics',
            'deployment_guidance', 
            'troubleshooting_assistance',
            'rag_knowledge_retrieval',
            'kvm_hypervisor_support',
            'ansible_automation_help'
        ]
        
        assert self.plugin.capabilities == expected_capabilities
    
    def test_get_dependencies(self):
        """Test plugin dependencies"""
        dependencies = self.plugin.get_dependencies()
        assert dependencies == []
    
    def test_validate_config_success(self):
        """Test successful configuration validation"""
        with patch('os.path.exists', return_value=True):
            assert self.plugin.validate_config() is True
    
    def test_validate_config_failure(self):
        """Test configuration validation failure"""
        with patch('os.path.exists', return_value=False):
            assert self.plugin.validate_config() is False
    
    @patch('subprocess.run')
    def test_container_exists_true(self, mock_subprocess):
        """Test container exists check - positive case"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {"Names": ["test-ai-assistant"], "State": "running"}
        ])
        mock_subprocess.return_value = mock_result
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        assert self.plugin._container_exists() is True
    
    @patch('subprocess.run')
    def test_container_exists_false(self, mock_subprocess):
        """Test container exists check - negative case"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([])
        mock_subprocess.return_value = mock_result
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        assert self.plugin._container_exists() is False
    
    @patch('subprocess.run')
    def test_container_running_true(self, mock_subprocess):
        """Test container running check - positive case"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {"Names": ["test-ai-assistant"], "State": "running"}
        ])
        mock_subprocess.return_value = mock_result
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        assert self.plugin._container_running() is True
    
    @patch('subprocess.run')
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
    
    @patch('requests.get')
    def test_ai_service_healthy_true(self, mock_get):
        """Test AI service health check - positive case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        assert self.plugin._ai_service_healthy() is True
    
    @patch('requests.get')
    def test_ai_service_healthy_false(self, mock_get):
        """Test AI service health check - negative case"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        assert self.plugin._ai_service_healthy() is False
    
    @patch('requests.get')
    def test_rag_system_loaded_true(self, mock_get):
        """Test RAG system loaded check - positive case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ai_service": {
                "components": {
                    "rag_service": {
                        "documents_loaded": True
                    }
                }
            }
        }
        mock_get.return_value = mock_response
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        assert self.plugin._rag_system_loaded() is True
    
    @patch('requests.get')
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
        with patch.object(self.plugin, '_container_exists', return_value=True), \
             patch.object(self.plugin, '_container_running', return_value=True), \
             patch.object(self.plugin, '_ai_service_healthy', return_value=True), \
             patch.object(self.plugin, '_rag_system_loaded', return_value=True), \
             patch.object(self.plugin, '_diagnostic_tools_available', return_value=True), \
             patch('os.path.exists', return_value=True):
            
            state = self.plugin.check_state()
            
            assert isinstance(state, SystemState)
            assert state.get('container_exists') is True
            assert state.get('container_running') is True
            assert state.get('ai_service_healthy') is True
            assert state.get('rag_system_loaded') is True
            assert state.get('diagnostic_tools_available') is True
            assert state.get('ai_assistant_directory_exists') is True
    
    def test_get_desired_state(self):
        """Test desired state generation"""
        desired_state = self.plugin.get_desired_state(self.context)
        
        assert isinstance(desired_state, SystemState)
        assert desired_state.get('container_exists') is True
        assert desired_state.get('container_running') is True
        assert desired_state.get('ai_service_healthy') is True
        assert desired_state.get('rag_system_loaded') is True
        assert desired_state.get('diagnostic_tools_available') is True
        assert desired_state.get('ai_assistant_directory_exists') is True
    
    def test_apply_changes_already_configured(self):
        """Test apply changes when system is already in desired state"""
        current_state = SystemState({
            'container_exists': True,
            'container_running': True,
            'ai_service_healthy': True,
            'rag_system_loaded': True,
            'diagnostic_tools_available': True,
            'ai_assistant_directory_exists': True
        })
        
        desired_state = current_state
        
        # Mock the execute method to return skipped result
        with patch.object(self.plugin, 'check_state', return_value=current_state), \
             patch.object(self.plugin, 'get_desired_state', return_value=desired_state):
            
            result = self.plugin.execute(self.context)
            
            assert isinstance(result, PluginResult)
            assert result.status == PluginStatus.SKIPPED
            assert result.changed is False
    
    @patch('os.path.exists')
    def test_apply_changes_missing_directory(self, mock_exists):
        """Test apply changes when AI assistant directory is missing"""
        mock_exists.return_value = False
        
        current_state = SystemState({
            'ai_assistant_directory_exists': False
        })
        
        desired_state = SystemState({
            'ai_assistant_directory_exists': True
        })
        
        result = self.plugin.apply_changes(current_state, desired_state, self.context)
        
        assert isinstance(result, PluginResult)
        assert result.status == PluginStatus.FAILED
        assert "AI Assistant directory not found" in result.message
    
    @patch('requests.post')
    def test_ask_ai_success(self, mock_post):
        """Test asking AI a question - success case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "This is an AI response",
            "metadata": {"model": "granite-4.0-micro"}
        }
        mock_post.return_value = mock_response
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        result = self.plugin.ask_ai("What is KVM?")
        
        assert "text" in result
        assert result["text"] == "This is an AI response"
        assert "metadata" in result
    
    @patch('requests.post')
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
    
    @patch('requests.post')
    def test_run_diagnostics_success(self, mock_post):
        """Test running diagnostics - success case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "diagnostics": {
                "summary": {"successful_tools": 6, "total_tools": 6}
            }
        }
        mock_post.return_value = mock_response
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        result = self.plugin.run_diagnostics()
        
        assert "diagnostics" in result
        assert result["diagnostics"]["summary"]["successful_tools"] == 6
    
    @patch('requests.post')
    def test_run_diagnostics_specific_tool(self, mock_post):
        """Test running specific diagnostic tool"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tool_result": {
                "success": True,
                "data": {"hostname": "test-host"}
            }
        }
        mock_post.return_value = mock_response
        
        # Initialize plugin to set up attributes
        self.plugin.initialize()
        
        result = self.plugin.run_diagnostics("system_info")
        
        assert "tool_result" in result
        assert result["tool_result"]["success"] is True
    
    @patch('requests.get')
    def test_get_available_tools_success(self, mock_get):
        """Test getting available diagnostic tools - success case"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "available_tools": {
                "system_info": "Gather basic system information",
                "resource_usage": "Monitor CPU, memory, disk usage"
            },
            "total_tools": 2
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
        with patch.object(self.plugin, '_get_ai_assistant_status') as mock_status:
            mock_status.return_value = {
                'container_running': True,
                'ai_service_healthy': True
            }
            
            health = self.plugin.get_health_status()
            
            assert health['name'] == 'AIAssistantPlugin'
            assert health['version'] == '1.0.0'
            assert 'ai_service_url' in health
            assert 'capabilities' in health
            assert 'ai_assistant_status' in health


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
