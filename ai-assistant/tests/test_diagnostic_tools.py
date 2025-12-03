"""
Tests for the Diagnostic Tools Framework
Tests the tool-calling framework for system diagnostics
"""

import pytest
import time
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from diagnostic_tools import (
    DiagnosticTool,
    ToolResult,
    SystemInfoTool,
    ResourceUsageTool,
    ServiceStatusTool,
    ProcessInfoTool,
    KVMDiagnosticTool,
    NetworkDiagnosticTool,
    DiagnosticToolRegistry,
    diagnostic_registry,
)


class TestToolResult:
    """Test ToolResult dataclass"""

    def test_tool_result_creation(self):
        """Test creating a ToolResult"""
        result = ToolResult(
            tool_name="test_tool",
            success=True,
            data={"key": "value"},
            error=None,
            execution_time=1.5,
            timestamp=time.time(),
        )

        assert result.tool_name == "test_tool"
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.execution_time == 1.5
        assert result.timestamp > 0

    def test_tool_result_to_dict(self):
        """Test converting ToolResult to dictionary"""
        result = ToolResult(
            tool_name="test_tool",
            success=True,
            data={"test": "data"},
            execution_time=0.5,
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["tool_name"] == "test_tool"
        assert result_dict["success"] is True
        assert result_dict["data"] == {"test": "data"}


class TestDiagnosticTool:
    """Test base DiagnosticTool class"""

    def test_diagnostic_tool_creation(self):
        """Test creating a diagnostic tool"""

        class TestTool(DiagnosticTool):
            async def execute(self, **kwargs):
                return self._create_result(True, {"test": "data"})

        tool = TestTool("test_tool", "Test tool description")
        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"

    def test_create_result_helper(self):
        """Test the _create_result helper method"""

        class TestTool(DiagnosticTool):
            async def execute(self, **kwargs):
                return self._create_result(True, {"test": "data"}, execution_time=1.0)

        tool = TestTool("test_tool", "Test tool")
        result = tool._create_result(True, {"test": "data"}, execution_time=1.0)

        assert isinstance(result, ToolResult)
        assert result.tool_name == "test_tool"
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.execution_time == 1.0


class TestSystemInfoTool:
    """Test SystemInfoTool"""

    @pytest.mark.asyncio
    async def test_system_info_execution(self):
        """Test SystemInfoTool execution"""
        tool = SystemInfoTool()
        result = await tool.execute()

        assert isinstance(result, ToolResult)
        assert result.tool_name == "system_info"
        assert result.success is True
        assert "hostname" in result.data
        assert "platform" in result.data
        assert "system" in result.data
        assert "uptime_seconds" in result.data
        assert result.execution_time > 0


class TestResourceUsageTool:
    """Test ResourceUsageTool"""

    @pytest.mark.asyncio
    async def test_resource_usage_execution(self):
        """Test ResourceUsageTool execution"""
        tool = ResourceUsageTool()
        result = await tool.execute()

        assert isinstance(result, ToolResult)
        assert result.tool_name == "resource_usage"
        assert result.success is True
        assert "cpu" in result.data
        assert "memory" in result.data
        assert "disk" in result.data
        assert "network" in result.data

        # Check CPU data structure
        cpu_data = result.data["cpu"]
        assert "usage_percent" in cpu_data
        assert "count_logical" in cpu_data
        assert "count_physical" in cpu_data

        # Check memory data structure
        memory_data = result.data["memory"]
        assert "total_gb" in memory_data
        assert "available_gb" in memory_data
        assert "usage_percent" in memory_data


class TestServiceStatusTool:
    """Test ServiceStatusTool"""

    @pytest.mark.asyncio
    async def test_service_status_execution(self):
        """Test ServiceStatusTool execution"""
        tool = ServiceStatusTool()
        result = await tool.execute()

        assert isinstance(result, ToolResult)
        assert result.tool_name == "service_status"
        assert result.success is True
        assert "services" in result.data

        services = result.data["services"]
        assert isinstance(services, dict)

        # Check that default services are checked
        expected_services = [
            "libvirtd",
            "qemu-kvm",
            "NetworkManager",
            "firewalld",
            "sshd",
        ]
        for service in expected_services:
            if service in services:
                assert "status" in services[service]
                assert "active" in services[service]

    @pytest.mark.asyncio
    async def test_service_status_custom_services(self):
        """Test ServiceStatusTool with custom services"""
        tool = ServiceStatusTool()
        custom_services = ["sshd", "chronyd"]
        result = await tool.execute(services=custom_services)

        assert result.success is True
        services = result.data["services"]

        for service in custom_services:
            assert service in services


class TestProcessInfoTool:
    """Test ProcessInfoTool"""

    @pytest.mark.asyncio
    async def test_process_info_execution(self):
        """Test ProcessInfoTool execution"""
        tool = ProcessInfoTool()
        result = await tool.execute()

        assert isinstance(result, ToolResult)
        assert result.tool_name == "process_info"
        assert result.success is True
        assert "total_processes" in result.data
        assert "filtered_processes" in result.data
        assert "processes" in result.data

        processes = result.data["processes"]
        assert isinstance(processes, list)
        assert len(processes) <= 10  # Default top_n limit

        if processes:
            process = processes[0]
            assert "pid" in process
            assert "name" in process
            assert "memory_mb" in process

    @pytest.mark.asyncio
    async def test_process_info_with_filter(self):
        """Test ProcessInfoTool with name filter"""
        tool = ProcessInfoTool()
        result = await tool.execute(filter_name="python", top_n=5)

        assert result.success is True
        processes = result.data["processes"]

        # All returned processes should contain "python" in the name
        for process in processes:
            assert "python" in process["name"].lower()


class TestKVMDiagnosticTool:
    """Test KVMDiagnosticTool"""

    @pytest.mark.asyncio
    async def test_kvm_diagnostics_execution(self):
        """Test KVMDiagnosticTool execution"""
        tool = KVMDiagnosticTool()
        result = await tool.execute()

        assert isinstance(result, ToolResult)
        assert result.tool_name == "kvm_diagnostics"
        assert result.success is True

        # Should have some KVM-related data
        data = result.data
        assert isinstance(data, dict)

        # Check for expected keys (some may not be present depending on system)
        possible_keys = [
            "kvm_module_loaded",
            "kvm_intel_loaded",
            "kvm_amd_loaded",
            "vmx_support",
            "svm_support",
            "libvirt_available",
            "vm_count",
        ]

        # At least some KVM data should be present
        assert any(key in data for key in possible_keys)


class TestNetworkDiagnosticTool:
    """Test NetworkDiagnosticTool"""

    @pytest.mark.asyncio
    async def test_network_diagnostics_execution(self):
        """Test NetworkDiagnosticTool execution"""
        tool = NetworkDiagnosticTool()
        result = await tool.execute()

        assert isinstance(result, ToolResult)
        assert result.tool_name == "network_diagnostics"
        assert result.success is True

        data = result.data
        assert "interfaces" in data
        assert "connectivity" in data

        # Check connectivity results
        connectivity = data["connectivity"]
        default_targets = ["8.8.8.8", "1.1.1.1", "google.com"]

        for target in default_targets:
            if target in connectivity:
                assert "reachable" in connectivity[target]

    @pytest.mark.asyncio
    async def test_network_diagnostics_custom_targets(self):
        """Test NetworkDiagnosticTool with custom targets"""
        tool = NetworkDiagnosticTool()
        custom_targets = ["127.0.0.1", "localhost"]
        result = await tool.execute(targets=custom_targets)

        assert result.success is True
        connectivity = result.data["connectivity"]

        for target in custom_targets:
            assert target in connectivity


class TestDiagnosticToolRegistry:
    """Test DiagnosticToolRegistry"""

    def test_registry_initialization(self):
        """Test registry initialization with default tools"""
        registry = DiagnosticToolRegistry()

        # Should have default tools registered
        tools = registry.list_tools()
        expected_tools = [
            "system_info",
            "resource_usage",
            "service_status",
            "process_info",
            "kvm_diagnostics",
            "network_diagnostics",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools

    def test_tool_registration(self):
        """Test registering a custom tool"""
        registry = DiagnosticToolRegistry()

        class CustomTool(DiagnosticTool):
            async def execute(self, **kwargs):
                return self._create_result(True, {"custom": "data"})

        custom_tool = CustomTool("custom_tool", "Custom test tool")
        registry.register_tool(custom_tool)

        assert "custom_tool" in registry.list_tools()
        assert registry.get_tool("custom_tool") == custom_tool

    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist"""
        registry = DiagnosticToolRegistry()
        tool = registry.get_tool("nonexistent_tool")
        assert tool is None

    @pytest.mark.asyncio
    async def test_run_tool(self):
        """Test running a tool through the registry"""
        registry = DiagnosticToolRegistry()
        result = await registry.run_tool("system_info")

        assert isinstance(result, ToolResult)
        assert result.tool_name == "system_info"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_nonexistent_tool(self):
        """Test running a tool that doesn't exist"""
        registry = DiagnosticToolRegistry()
        result = await registry.run_tool("nonexistent_tool")

        assert isinstance(result, ToolResult)
        assert result.tool_name == "nonexistent_tool"
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_run_all_tools(self):
        """Test running all tools"""
        registry = DiagnosticToolRegistry()
        results = await registry.run_all_tools()

        assert isinstance(results, dict)

        # Should have results for all default tools
        expected_tools = [
            "system_info",
            "resource_usage",
            "service_status",
            "process_info",
            "kvm_diagnostics",
            "network_diagnostics",
        ]

        for tool_name in expected_tools:
            assert tool_name in results
            assert isinstance(results[tool_name], ToolResult)

    @pytest.mark.asyncio
    async def test_comprehensive_diagnostics(self):
        """Test running comprehensive diagnostics"""
        registry = DiagnosticToolRegistry()
        result = await registry.run_comprehensive_diagnostics()

        assert isinstance(result, dict)
        assert "summary" in result
        assert "tool_results" in result

        summary = result["summary"]
        assert "total_tools" in summary
        assert "successful_tools" in summary
        assert "failed_tools" in summary
        assert "total_execution_time" in summary
        assert "timestamp" in summary

        tool_results = result["tool_results"]
        assert isinstance(tool_results, dict)

        # Each tool result should be a dictionary (from to_dict())
        for tool_name, tool_result in tool_results.items():
            assert isinstance(tool_result, dict)
            assert "tool_name" in tool_result
            assert "success" in tool_result
            assert "data" in tool_result


class TestGlobalRegistry:
    """Test the global diagnostic registry"""

    def test_global_registry_exists(self):
        """Test that global registry is available"""
        assert diagnostic_registry is not None
        assert isinstance(diagnostic_registry, DiagnosticToolRegistry)

    def test_global_registry_has_tools(self):
        """Test that global registry has default tools"""
        tools = diagnostic_registry.list_tools()
        assert len(tools) > 0

        expected_tools = [
            "system_info",
            "resource_usage",
            "service_status",
            "process_info",
            "kvm_diagnostics",
            "network_diagnostics",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools


class TestIntegration:
    """Integration tests for the diagnostic framework"""

    @pytest.mark.asyncio
    async def test_full_diagnostic_workflow(self):
        """Test a complete diagnostic workflow"""
        # Run comprehensive diagnostics
        result = await diagnostic_registry.run_comprehensive_diagnostics()

        # Verify structure
        assert "summary" in result
        assert "tool_results" in result

        summary = result["summary"]
        tool_results = result["tool_results"]

        # Should have run all tools
        assert summary["total_tools"] == len(diagnostic_registry.tools)
        assert len(tool_results) == summary["total_tools"]

        # Check that we got meaningful data
        successful_tools = [
            name for name, result in tool_results.items() if result["success"]
        ]

        # Most tools should succeed in a normal environment
        assert len(successful_tools) >= 4  # At least 4 out of 6 should work

        # Verify specific tool results have expected data
        if "system_info" in successful_tools:
            sys_result = tool_results["system_info"]
            assert "hostname" in sys_result["data"]
            assert "platform" in sys_result["data"]

        if "resource_usage" in successful_tools:
            res_result = tool_results["resource_usage"]
            assert "cpu" in res_result["data"]
            assert "memory" in res_result["data"]

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in diagnostic tools"""

        # Create a tool that always fails
        class FailingTool(DiagnosticTool):
            async def execute(self, **kwargs):
                try:
                    raise Exception("Intentional test failure")
                except Exception as e:
                    return self._create_result(False, {}, str(e))

        failing_tool = FailingTool("failing_tool", "Tool that always fails")

        # Test direct execution
        result = await failing_tool.execute()
        assert result.success is False
        assert "Intentional test failure" in result.error

        # Test through registry
        test_registry = DiagnosticToolRegistry()
        test_registry.register_tool(failing_tool)

        result = await test_registry.run_tool("failing_tool")
        assert result.success is False
        assert "Intentional test failure" in result.error


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
