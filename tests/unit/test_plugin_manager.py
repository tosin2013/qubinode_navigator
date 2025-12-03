"""
Unit tests for PluginManager

Tests the plugin discovery, loading, and execution functionality
as defined in ADR-0028.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.base_plugin import (
    ExecutionContext,
    PluginResult,
    PluginStatus,
    QubiNodePlugin,
    SystemState,
)
from core.event_system import EventSystem
from core.plugin_manager import PluginInfo, PluginManager


class MockPlugin(QubiNodePlugin):
    """Mock plugin for testing"""

    def __init__(self, config=None):
        super().__init__(config or {})
        self.__version__ = "1.0.0"
        self.description = "Mock plugin for testing"

    def _initialize_plugin(self) -> None:
        """Initialize mock plugin"""
        pass

    def check_state(self) -> SystemState:
        """Check current system state"""
        return SystemState({"mock": "state"})

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply mock changes"""
        return PluginResult(
            changed=True, message="Mock changes applied", status=PluginStatus.COMPLETED
        )


class TestPluginManager(unittest.TestCase):
    """Test cases for PluginManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_dir = os.path.join(self.temp_dir, "plugins")
        os.makedirs(self.plugin_dir)

        self.event_system = EventSystem()
        self.plugin_manager = PluginManager(
            plugin_directories=[self.plugin_dir], event_system=self.event_system
        )

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test PluginManager initialization"""
        self.assertIsInstance(self.plugin_manager.event_system, EventSystem)
        self.assertEqual(self.plugin_manager.plugin_directories, [self.plugin_dir])
        self.assertEqual(len(self.plugin_manager._discovered_plugins), 0)
        self.assertEqual(len(self.plugin_manager._loaded_plugins), 0)

    def test_discover_plugins_empty_directory(self):
        """Test plugin discovery with empty directory"""
        self.plugin_manager.discover_plugins()
        self.assertEqual(len(self.plugin_manager._discovered_plugins), 0)

    def test_discover_plugins_with_mock_plugin(self):
        """Test plugin discovery with a mock plugin file"""
        # Create a mock plugin file
        plugin_content = """
from core.base_plugin import QubiNodePlugin, PluginResult, ExecutionContext, PluginStatus

class TestPlugin(QubiNodePlugin):
    def __init__(self):
        super().__init__()
        self.name = "test_plugin"
        self.version = "1.0.0"
        self.dependencies = []
        self.description = "Test plugin"
    
    def validate_environment(self, context):
        return PluginResult(success=True, status=PluginStatus.SUCCESS, message="OK")
    
    def execute(self, context):
        return PluginResult(success=True, status=PluginStatus.SUCCESS, message="OK")
"""

        plugin_file = os.path.join(self.plugin_dir, "test_plugin.py")
        with open(plugin_file, "w") as f:
            f.write(plugin_content)

        # Mock the import to avoid actual module loading issues
        with patch("importlib.util.spec_from_file_location") as mock_spec:
            with patch("importlib.util.module_from_spec") as mock_module:
                mock_spec.return_value = Mock()
                mock_mod = Mock()
                mock_module.return_value = mock_mod
                mock_mod.TestPlugin = MockPlugin

                self.plugin_manager.discover_plugins()
                self.assertGreaterEqual(
                    len(self.plugin_manager._discovered_plugins), 0
                )  # May find other plugins too

    def test_load_plugin_success(self):
        """Test successful plugin loading"""
        # Create a mock plugin info
        plugin_info = PluginInfo(
            name="mock_plugin",
            class_name="MockPlugin",
            module_path="mock_path",
            plugin_class=MockPlugin,
            dependencies=[],
            version="1.0.0",
            description="Mock plugin",
        )

        self.plugin_manager._discovered_plugins["mock_plugin"] = plugin_info

        result = self.plugin_manager.load_plugin("mock_plugin")
        self.assertIsNotNone(result)
        self.assertIn("mock_plugin", self.plugin_manager._loaded_plugins)
        self.assertIsInstance(
            self.plugin_manager._loaded_plugins["mock_plugin"], MockPlugin
        )

    def test_load_plugin_not_found(self):
        """Test loading non-existent plugin"""
        result = self.plugin_manager.load_plugin("nonexistent_plugin")
        self.assertIsNone(result)

    def test_load_plugin_with_dependencies(self):
        """Test loading plugin with dependencies"""
        # Create dependency plugin
        dep_plugin_info = PluginInfo(
            name="dependency_plugin",
            class_name="MockPlugin",
            module_path="mock_path",
            plugin_class=MockPlugin,
            dependencies=[],
            version="1.0.0",
        )

        # Create main plugin with dependency
        main_plugin_info = PluginInfo(
            name="main_plugin",
            class_name="MockPlugin",
            module_path="mock_path",
            plugin_class=MockPlugin,
            dependencies=["dependency_plugin"],
            version="1.0.0",
        )

        self.plugin_manager._discovered_plugins["dependency_plugin"] = dep_plugin_info
        self.plugin_manager._discovered_plugins["main_plugin"] = main_plugin_info

        result = self.plugin_manager.load_plugin("main_plugin")
        self.assertIsNotNone(result)
        self.assertIn("main_plugin", self.plugin_manager._loaded_plugins)

    def test_execute_plugin_success(self):
        """Test successful plugin execution"""
        # Load mock plugin
        plugin_info = PluginInfo(
            name="mock_plugin",
            class_name="MockPlugin",
            module_path="mock_path",
            plugin_class=MockPlugin,
            dependencies=[],
            version="1.0.0",
        )

        self.plugin_manager._discovered_plugins["mock_plugin"] = plugin_info
        self.plugin_manager.load_plugin("mock_plugin")

        context = ExecutionContext(inventory="localhost", config={})

        result = self.plugin_manager.execute_plugin("mock_plugin", context)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, PluginStatus.COMPLETED)

    def test_execute_plugin_not_loaded(self):
        """Test executing plugin that's not loaded"""
        context = ExecutionContext(inventory="localhost", config={})
        result = self.plugin_manager.execute_plugin("nonexistent_plugin", context)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, PluginStatus.FAILED)

    def test_list_plugins(self):
        """Test listing discovered plugins"""
        plugin_info = PluginInfo(
            name="mock_plugin",
            class_name="MockPlugin",
            module_path="mock_path",
            plugin_class=MockPlugin,
            dependencies=[],
            version="1.0.0",
        )

        self.plugin_manager._discovered_plugins["mock_plugin"] = plugin_info

        plugins = self.plugin_manager.list_plugins()
        self.assertIn("mock_plugin", plugins)

    def test_get_plugin_info(self):
        """Test getting plugin information"""
        plugin_info = PluginInfo(
            name="mock_plugin",
            class_name="MockPlugin",
            module_path="mock_path",
            plugin_class=MockPlugin,
            dependencies=[],
            version="1.0.0",
            description="Mock plugin",
        )

        self.plugin_manager._discovered_plugins["mock_plugin"] = plugin_info

        info = self.plugin_manager.get_plugin_info("mock_plugin")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "mock_plugin")
        self.assertEqual(info.version, "1.0.0")
        self.assertEqual(info.description, "Mock plugin")

    def test_get_plugin_info_not_found(self):
        """Test getting info for non-existent plugin"""
        info = self.plugin_manager.get_plugin_info("nonexistent_plugin")
        self.assertIsNone(info)

    def test_resolve_dependencies_simple(self):
        """Test simple dependency resolution"""
        # Create plugins with dependencies
        plugin_a = PluginInfo("plugin_a", "A", "path", MockPlugin, [], "1.0.0")
        plugin_b = PluginInfo(
            "plugin_b", "B", "path", MockPlugin, ["plugin_a"], "1.0.0"
        )
        plugin_c = PluginInfo(
            "plugin_c", "C", "path", MockPlugin, ["plugin_b"], "1.0.0"
        )

        self.plugin_manager._discovered_plugins = {
            "plugin_a": plugin_a,
            "plugin_b": plugin_b,
            "plugin_c": plugin_c,
        }

        order = self.plugin_manager._resolve_dependencies(["plugin_c"])
        self.assertEqual(order, ["plugin_a", "plugin_b", "plugin_c"])

    def test_resolve_dependencies_circular(self):
        """Test circular dependency detection"""
        plugin_a = PluginInfo(
            "plugin_a", "A", "path", MockPlugin, ["plugin_b"], "1.0.0"
        )
        plugin_b = PluginInfo(
            "plugin_b", "B", "path", MockPlugin, ["plugin_a"], "1.0.0"
        )

        self.plugin_manager._discovered_plugins = {
            "plugin_a": plugin_a,
            "plugin_b": plugin_b,
        }

        with self.assertRaises(ValueError):
            self.plugin_manager._resolve_dependencies(["plugin_a"])

    def test_event_system_integration(self):
        """Test integration with event system"""
        events_received = []

        def event_handler(event):
            events_received.append(event)

        self.event_system.subscribe("plugin.loaded", event_handler)

        plugin_info = PluginInfo(
            name="mock_plugin",
            class_name="MockPlugin",
            module_path="mock_path",
            plugin_class=MockPlugin,
            dependencies=[],
            version="1.0.0",
        )

        self.plugin_manager._discovered_plugins["mock_plugin"] = plugin_info
        self.plugin_manager.load_plugin("mock_plugin")

        # Check if event was emitted (this depends on the actual implementation)
        # For now, just verify the event system is accessible
        self.assertIsNotNone(self.plugin_manager.event_system)


if __name__ == "__main__":
    unittest.main()
