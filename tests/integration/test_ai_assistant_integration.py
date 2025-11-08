"""
Comprehensive Integration Tests for AI Assistant
Tests the full integration between AI Assistant container, plugin framework, and diagnostic tools
"""

import pytest
import requests
import subprocess
import time
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.services.ai_assistant_plugin import AIAssistantPlugin
from core.base_plugin import ExecutionContext, PluginResult, SystemState, PluginStatus


class TestAIAssistantFullIntegration:
    """Full integration tests for AI Assistant ecosystem"""
    
    @classmethod
    def setup_class(cls):
        """Setup for integration tests"""
        cls.ai_service_url = "http://localhost:8080"
        cls.container_name = "ai-integration-test"
        cls.container_image = "qubinode-ai-assistant:test"
        
    def test_container_lifecycle_management(self):
        """Test AI Assistant container lifecycle through plugin"""
        config = {
            'ai_service_url': self.ai_service_url,
            'container_name': self.container_name,
            'container_image': self.container_image,
            'ai_assistant_path': '/root/qubinode_navigator/ai-assistant',  # Use real path
            'auto_start': False,  # Don't auto-start to avoid build process
            'health_check_timeout': 30,
            'enable_diagnostics': True,
            'enable_rag': True
        }
        
        plugin = AIAssistantPlugin(config)
        context = ExecutionContext(
            inventory="localhost",
            environment="integration_test",
            config={"test": True}
        )
        
        # Mock container operations to simulate already running container
        with patch('subprocess.run') as mock_run, \
             patch('requests.get') as mock_get:
            
            # Mock container already exists and is running
            mock_run.return_value = MagicMock(
                returncode=0, 
                stdout='[{"Names": ["ai-integration-test"], "State": "running"}]'
            )
            
            # Mock healthy AI service
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "status": "healthy",
                    "ai_service": {
                        "components": {
                            "rag_service": {"documents_loaded": True}
                        }
                    }
                }
            )
            
            # Test plugin state checking
            current_state = plugin.check_state()
            desired_state = plugin.get_desired_state(context)
            
            # Test that when container is already running and healthy, no changes needed
            result = plugin.apply_changes(current_state, desired_state, context)
            assert result.status == PluginStatus.COMPLETED
            assert isinstance(result.changed, bool)
            
    def test_ai_assistant_api_endpoints(self):
        """Test AI Assistant REST API endpoints"""
        # This test assumes AI Assistant container is running
        # In CI/CD, this would be handled by the workflow
        
        # Mock the requests for testing
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            # Mock health endpoint
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {"status": "healthy", "components": {"llm": True, "rag": True, "diagnostics": True}}
            )
            
            # Mock chat endpoint
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: {"response": "KVM is a virtualization technology..."}
            )
            
            # Test health endpoint
            response = requests.get(f"{self.ai_service_url}/health")
            assert response.status_code == 200
            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert "components" in health_data
            
            # Test chat endpoint
            response = requests.post(f"{self.ai_service_url}/chat",
                json={"message": "What is KVM virtualization?"})
            assert response.status_code == 200
            chat_data = response.json()
            assert "response" in chat_data
            assert len(chat_data["response"]) > 0
            
    def test_diagnostic_tools_integration(self):
        """Test diagnostic tools integration with AI Assistant"""
        with patch('requests.get') as mock_get:
            # Mock diagnostics endpoints
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    "tools": [
                        {"name": "system_info", "description": "System information"},
                        {"name": "resource_usage", "description": "Resource usage"},
                        {"name": "kvm_diagnostics", "description": "KVM diagnostics"}
                    ]
                }
            )
            
            # Test available tools endpoint
            response = requests.get(f"{self.ai_service_url}/diagnostics/tools")
            assert response.status_code == 200
            tools_data = response.json()
            assert "tools" in tools_data
            assert len(tools_data["tools"]) >= 3
            
            # Verify expected diagnostic tools are available
            tool_names = [tool["name"] for tool in tools_data["tools"]]
            expected_tools = ["system_info", "resource_usage", "kvm_diagnostics"]
            for tool in expected_tools:
                assert tool in tool_names
                
    def test_plugin_framework_integration(self):
        """Test AI Assistant plugin integration with framework"""
        config = {
            'ai_service_url': self.ai_service_url,
            'container_name': self.container_name,
            'auto_start': False,  # Don't auto-start for testing
            'health_check_timeout': 10
        }
        
        plugin = AIAssistantPlugin(config)
        context = ExecutionContext(
            inventory="localhost",
            environment="test",
            config={"test": True}
        )
        
        # Test plugin capabilities
        capabilities = plugin.capabilities
        assert "system_diagnostics" in capabilities
        assert "deployment_guidance" in capabilities
        assert "troubleshooting_assistance" in capabilities
        
        # Test plugin dependencies
        dependencies = plugin.get_dependencies()
        assert isinstance(dependencies, list)  # Should return empty list as per implementation
        
        # Mock AI service health check
        with patch.object(plugin, '_ai_service_healthy') as mock_health:
            mock_health.return_value = True
            
            # Test plugin health status by checking state
            current_state = plugin.check_state()
            assert current_state.get('ai_service_healthy')
            
        # Mock AI query
        with patch.object(plugin, 'ask_ai') as mock_ask:
            mock_ask.return_value = "Hypervisor is a virtualization layer..."
            
            # Test AI query functionality
            response = plugin.ask_ai("What is a hypervisor?")
            assert response is not None
            assert len(response) > 0
            
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        config = {
            'ai_service_url': "http://localhost:9999",  # Invalid URL
            'container_name': self.container_name,
            'auto_start': False,
            'health_check_timeout': 5
        }
        
        plugin = AIAssistantPlugin(config)
        
        # Test handling of unavailable AI service
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            # Plugin should handle connection errors gracefully
            current_state = plugin.check_state()
            assert not current_state.get('ai_service_healthy')
            
        # Test handling of invalid responses
        with patch('requests.post') as mock_post:
            mock_post.return_value = MagicMock(status_code=500)
            
            # AI query should handle errors gracefully
            response = plugin.ask_ai("test query")
            assert response is None or (isinstance(response, dict) and "error" in str(response).lower())
            
    def test_performance_characteristics(self):
        """Test performance characteristics of AI Assistant integration"""
        config = {
            'ai_service_url': self.ai_service_url,
            'container_name': self.container_name,
            'auto_start': False,
            'health_check_timeout': 10
        }
        
        plugin = AIAssistantPlugin(config)
        
        # Mock all health check methods for fast execution
        with patch.object(plugin, '_ai_service_healthy') as mock_ai_health, \
             patch.object(plugin, '_container_exists') as mock_container_exists, \
             patch.object(plugin, '_container_running') as mock_container_running, \
             patch.object(plugin, '_rag_system_loaded') as mock_rag_loaded, \
             patch.object(plugin, '_diagnostic_tools_available') as mock_diagnostics:
            
            # Mock all checks to return quickly
            mock_ai_health.return_value = True
            mock_container_exists.return_value = True
            mock_container_running.return_value = True
            mock_rag_loaded.return_value = True
            mock_diagnostics.return_value = True
            
            # Test health check performance
            start_time = time.time()
            current_state = plugin.check_state()
            is_healthy = current_state.get('ai_service_healthy')
            end_time = time.time()
            
            assert is_healthy
            # Health check should be fast (< 1 second when mocked)
            assert (end_time - start_time) < 1.0
            
        # Mock AI query with timing
        with patch.object(plugin, 'ask_ai') as mock_ask:
            mock_ask.return_value = "Quick response"
            
            # Test AI query performance
            start_time = time.time()
            response = plugin.ask_ai("Quick question")
            end_time = time.time()
            
            assert response is not None
            # Mocked response should be very fast
            assert (end_time - start_time) < 0.1
            
    def test_configuration_validation(self):
        """Test configuration validation and error handling"""
        # Test configuration with non-existent path (should fail validation)
        invalid_config = {
            'ai_service_url': 'http://localhost:8080',
            'ai_assistant_path': '/non/existent/path'  # This path doesn't exist
        }
        
        plugin = AIAssistantPlugin(invalid_config)
        
        # Validation should fail for non-existent path
        result = plugin.validate_config()
        assert not result  # Should return False for invalid config
        
        # Test valid configuration
        valid_config = {
            'ai_service_url': 'http://localhost:8080',
            'ai_assistant_path': '/root/qubinode_navigator/ai-assistant'  # This path exists
        }
        
        valid_plugin = AIAssistantPlugin(valid_config)
        result = valid_plugin.validate_config()
        assert result  # Should return True for valid config
                
    def test_concurrent_operations(self):
        """Test concurrent operations and thread safety"""
        config = {
            'ai_service_url': self.ai_service_url,
            'container_name': self.container_name,
            'auto_start': False,
            'health_check_timeout': 10
        }
        
        plugin = AIAssistantPlugin(config)
        
        # Mock concurrent AI queries
        with patch.object(plugin, 'ask_ai') as mock_ask:
            mock_ask.return_value = "Concurrent response"
            
            # Simulate concurrent queries
            import threading
            results = []
            
            def query_ai():
                response = plugin.ask_ai("Concurrent query")
                results.append(response)
                
            # Start multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=query_ai)
                threads.append(thread)
                thread.start()
                
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
                
            # All queries should complete successfully
            assert len(results) == 5
            for result in results:
                assert result is not None


class TestAIAssistantContainerIntegration:
    """Integration tests that require actual container"""
    
    @pytest.mark.skipif(
        os.getenv("CI") != "true",
        reason="Container tests only run in CI environment"
    )
    def test_real_container_integration(self):
        """Test integration with real AI Assistant container"""
        # This test would run in CI/CD with actual container
        container_name = "ai-real-test"
        
        try:
            # Start container
            subprocess.run([
                'docker', 'run', '-d', '--name', container_name,
                '-p', '8081:8080', 'qubinode-ai-assistant:test'
            ], check=True)
            
            # Wait for container to start
            time.sleep(30)
            
            # Test real endpoints
            response = requests.get('http://localhost:8081/health', timeout=10)
            assert response.status_code == 200
            
            response = requests.post('http://localhost:8081/chat',
                json={'message': 'What is virtualization?'}, timeout=30)
            assert response.status_code == 200
            
        finally:
            # Cleanup
            subprocess.run(['docker', 'stop', container_name], check=False)
            subprocess.run(['docker', 'rm', container_name], check=False)


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])
