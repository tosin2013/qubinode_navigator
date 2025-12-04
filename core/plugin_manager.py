"""
Plugin Manager

Implements plugin discovery, lifecycle management, and orchestration
as defined in ADR-0028.
"""

import os
import sys
import importlib
import importlib.util
import inspect
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
import logging
from dataclasses import dataclass

from .base_plugin import QubiNodePlugin, PluginResult, ExecutionContext, PluginStatus
from .event_system import EventSystem


@dataclass
class PluginInfo:
    """Information about a discovered plugin"""

    name: str
    class_name: str
    module_path: str
    plugin_class: Type[QubiNodePlugin]
    dependencies: List[str]
    version: str
    description: str = ""


class PluginManager:
    """
    Manages plugin discovery, loading, and execution

    Provides centralized plugin lifecycle management with dependency
    resolution and event-driven communication.
    """

    def __init__(self, plugin_directories: List[str] = None, event_system: EventSystem = None):
        self.logger = logging.getLogger(__name__)
        self.plugin_directories = plugin_directories or ["plugins"]
        self.event_system = event_system or EventSystem()

        # Plugin registry
        self._discovered_plugins: Dict[str, PluginInfo] = {}
        self._loaded_plugins: Dict[str, QubiNodePlugin] = {}
        self._plugin_execution_order: List[str] = []

        # State tracking
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize the plugin manager

        Returns:
            bool: True if initialization successful
        """
        try:
            self.discover_plugins()
            self._resolve_dependencies()
            self._initialized = True
            self.logger.info("Plugin manager initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin manager: {e}")
            return False

    def discover_plugins(self) -> None:
        """Discover all available plugins in plugin directories"""
        self.logger.info("Discovering plugins...")

        for plugin_dir in self.plugin_directories:
            if not os.path.exists(plugin_dir):
                self.logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue

            self._scan_directory(plugin_dir)

        self.logger.info(f"Discovered {len(self._discovered_plugins)} plugins")

    def _scan_directory(self, directory: str) -> None:
        """Scan a directory for plugin files"""
        plugin_path = Path(directory)

        # Add plugin directory to Python path
        if str(plugin_path.absolute()) not in sys.path:
            sys.path.insert(0, str(plugin_path.absolute()))

        # Scan for Python files
        for py_file in plugin_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                self._load_plugin_module(py_file, directory)
            except Exception as e:
                self.logger.error(f"Failed to load plugin from {py_file}: {e}")

    def _load_plugin_module(self, py_file: Path, base_dir: str) -> None:
        """Load a plugin module and extract plugin classes"""
        # Calculate module name
        relative_path = py_file.relative_to(base_dir)
        module_name = str(relative_path.with_suffix("")).replace(os.sep, ".")

        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, QubiNodePlugin) and obj != QubiNodePlugin and obj.__module__ == module_name:
                    self._register_plugin(name, obj, str(py_file))

        except Exception as e:
            self.logger.error(f"Failed to import module {module_name}: {e}")

    def _register_plugin(self, name: str, plugin_class: Type[QubiNodePlugin], module_path: str) -> None:
        """Register a discovered plugin"""
        try:
            # Create temporary instance to get metadata
            temp_instance = plugin_class({})

            plugin_info = PluginInfo(
                name=name,
                class_name=plugin_class.__name__,
                module_path=module_path,
                plugin_class=plugin_class,
                dependencies=temp_instance.get_dependencies(),
                version=temp_instance.version,
                description=plugin_class.__doc__ or "",
            )

            self._discovered_plugins[name] = plugin_info
            self.logger.debug(f"Registered plugin: {name}")

        except Exception as e:
            self.logger.error(f"Failed to register plugin {name}: {e}")

    def _resolve_dependencies(self) -> None:
        """Resolve plugin dependencies and determine execution order"""
        self.logger.info("Resolving plugin dependencies...")

        # Topological sort for dependency resolution
        visited = set()
        temp_visited = set()
        execution_order = []

        def visit(plugin_name: str):
            if plugin_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {plugin_name}")
            if plugin_name in visited:
                return

            temp_visited.add(plugin_name)

            if plugin_name in self._discovered_plugins:
                plugin_info = self._discovered_plugins[plugin_name]
                for dependency in plugin_info.dependencies:
                    if dependency not in self._discovered_plugins:
                        raise ValueError(f"Plugin {plugin_name} depends on missing plugin: {dependency}")
                    visit(dependency)

            temp_visited.remove(plugin_name)
            visited.add(plugin_name)
            execution_order.append(plugin_name)

        # Visit all plugins
        for plugin_name in self._discovered_plugins:
            if plugin_name not in visited:
                visit(plugin_name)

        self._plugin_execution_order = execution_order
        self.logger.info(f"Plugin execution order: {execution_order}")

    def load_plugin(self, plugin_name: str, config: Dict[str, Any] = None) -> Optional[QubiNodePlugin]:
        """
        Load and initialize a specific plugin

        Args:
            plugin_name: Name of the plugin to load
            config: Plugin configuration

        Returns:
            QubiNodePlugin: Loaded plugin instance or None if failed
        """
        if plugin_name in self._loaded_plugins:
            return self._loaded_plugins[plugin_name]

        if plugin_name not in self._discovered_plugins:
            self.logger.error(f"Plugin not found: {plugin_name}")
            return None

        try:
            plugin_info = self._discovered_plugins[plugin_name]
            plugin_instance = plugin_info.plugin_class(config or {})

            if plugin_instance.initialize():
                self._loaded_plugins[plugin_name] = plugin_instance
                self.event_system.emit("plugin_loaded", {"plugin_name": plugin_name})
                self.logger.info(f"Loaded plugin: {plugin_name}")
                return plugin_instance
            else:
                self.logger.error(f"Failed to initialize plugin: {plugin_name}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return None

    def execute_plugin(self, plugin_name: str, context: ExecutionContext) -> PluginResult:
        """
        Execute a specific plugin

        Args:
            plugin_name: Name of the plugin to execute
            context: Execution context

        Returns:
            PluginResult: Result of plugin execution
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return PluginResult(
                changed=False,
                message=f"Plugin not found: {plugin_name}",
                status=PluginStatus.FAILED,
            )

        try:
            self.event_system.emit("plugin_execution_start", {"plugin_name": plugin_name})
            result = plugin.execute(context)
            self.event_system.emit(
                "plugin_execution_complete",
                {"plugin_name": plugin_name, "result": result},
            )
            return result

        except Exception as e:
            self.logger.error(f"Plugin execution failed for {plugin_name}: {e}")
            return PluginResult(
                changed=False,
                message=f"Execution failed: {str(e)}",
                status=PluginStatus.FAILED,
            )

    def execute_plugins(self, plugin_names: List[str] = None, context: ExecutionContext = None) -> Dict[str, PluginResult]:
        """
        Execute multiple plugins in dependency order

        Args:
            plugin_names: List of plugin names to execute (None for all)
            context: Execution context

        Returns:
            Dict[str, PluginResult]: Results keyed by plugin name
        """
        if not self._initialized:
            raise RuntimeError("Plugin manager not initialized")

        context = context or ExecutionContext()
        plugins_to_execute = plugin_names or self._plugin_execution_order
        results = {}

        self.logger.info(f"Executing plugins: {plugins_to_execute}")

        for plugin_name in self._plugin_execution_order:
            if plugin_name not in plugins_to_execute:
                continue

            result = self.execute_plugin(plugin_name, context)
            results[plugin_name] = result

            # Stop on failure if configured
            if result.status == PluginStatus.FAILED:
                self.logger.error(f"Plugin {plugin_name} failed, stopping execution")
                break

        return results

    def get_plugin(self, plugin_name: str) -> Optional[QubiNodePlugin]:
        """Get a loaded plugin instance"""
        return self._loaded_plugins.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """List all discovered plugins"""
        return list(self._discovered_plugins.keys())

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """Get information about a plugin"""
        return self._discovered_plugins.get(plugin_name)

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        if plugin_name in self._loaded_plugins:
            try:
                plugin = self._loaded_plugins[plugin_name]
                plugin.cleanup()
                del self._loaded_plugins[plugin_name]
                self.event_system.emit("plugin_unloaded", {"plugin_name": plugin_name})
                self.logger.info(f"Unloaded plugin: {plugin_name}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to unload plugin {plugin_name}: {e}")
                return False
        return False

    def cleanup(self) -> None:
        """Cleanup all loaded plugins"""
        for plugin_name in list(self._loaded_plugins.keys()):
            self.unload_plugin(plugin_name)

    def get_status(self) -> Dict[str, Any]:
        """Get plugin manager status"""
        return {
            "initialized": self._initialized,
            "discovered_plugins": len(self._discovered_plugins),
            "loaded_plugins": len(self._loaded_plugins),
            "execution_order": self._plugin_execution_order,
            "plugin_status": {name: plugin.get_health_status() for name, plugin in self._loaded_plugins.items()},
        }
