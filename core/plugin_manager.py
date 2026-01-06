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
from typing import Dict, List, Any, Optional, Type, Callable
from pathlib import Path
import logging
from dataclasses import dataclass

from .base_plugin import QubiNodePlugin, PluginResult, ExecutionContext, PluginStatus, DiagnosticContext
from .event_system import EventSystem
from .failure_analyzer import FailureAnalyzer, FailureAnalysis
from .recovery_planner import RecoveryPlanner, RecoveryPlan


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
        
        # Failure recovery support
        self._failure_analyzer = FailureAnalyzer()
        self._recovery_planner = RecoveryPlanner()
        self._plugin_checkpoints: Dict[str, Any] = {}  # State snapshots for recovery
        self._recovery_handlers: Dict[str, List[Callable]] = {}  # Custom recovery handlers
        self._auto_recovery_enabled = True
        self._approval_callback: Optional[Callable[[RecoveryPlan], bool]] = None

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

    def diagnose_failure(
        self,
        plugin_name: str,
        failure_message: str,
        context: ExecutionContext,
    ) -> Optional[FailureAnalysis]:
        """
        Diagnose the root cause of a plugin failure
        
        Args:
            plugin_name: Name of the failed plugin
            failure_message: Error message from the failure
            context: Execution context at time of failure
        
        Returns:
            FailureAnalysis with root cause and recommendations
        """
        self.logger.info(f"Diagnosing failure for plugin: {plugin_name}")
        
        try:
            # Collect diagnostic context
            plugin = self.get_plugin(plugin_name)
            dependencies = self._get_plugin_dependencies(plugin_name)
            
            diagnostic_ctx = DiagnosticContext(
                plugin_name=plugin_name,
                failure_timestamp=__import__("datetime").datetime.now(),
                error_message=failure_message,
                dependent_plugins=dependencies,
            )
            
            # Collect service health
            diagnostic_ctx.service_health = self._collect_service_health()
            
            # Collect system resources
            diagnostic_ctx.system_resources = DiagnosticContext.get_system_resources()
            
            # Collect recent logs
            diagnostic_ctx.recent_logs = DiagnosticContext.get_plugin_logs(plugin_name, since_seconds=300)
            
            # Analyze failure
            analysis = self._failure_analyzer.analyze(diagnostic_ctx)
            
            # Emit event
            self.event_system.emit("plugin_failure_diagnosed", {
                "plugin_name": plugin_name,
                "root_cause": analysis.root_cause.value,
                "confidence": analysis.confidence,
            })
            
            return analysis
        
        except Exception as e:
            self.logger.error(f"Failed to diagnose failure: {e}")
            return None

    def plan_recovery(self, failure_analysis: FailureAnalysis, plugin_name: str) -> Optional[RecoveryPlan]:
        """
        Create recovery plan for a diagnosed failure
        
        Args:
            failure_analysis: Result from failure diagnosis
            plugin_name: Name of the failed plugin
        
        Returns:
            RecoveryPlan with recovery options
        """
        self.logger.info(f"Planning recovery for: {plugin_name}")
        
        try:
            plugin_config = self._discovered_plugins.get(plugin_name)
            config_dict = {
                "plugin_name": plugin_name,
                "version": plugin_config.version if plugin_config else "unknown",
            }
            
            plan = self._recovery_planner.plan_recovery(failure_analysis, config_dict)
            
            self.event_system.emit("recovery_plan_created", {
                "plugin_name": plugin_name,
                "num_options": len(plan.recovery_options),
                "recommended": plan.recommended_option.action_type.value if plan.recommended_option else None,
            })
            
            return plan
        
        except Exception as e:
            self.logger.error(f"Failed to plan recovery: {e}")
            return None

    def execute_recovery(self, recovery_plan: RecoveryPlan, context: ExecutionContext) -> bool:
        """
        Execute the recommended recovery option
        
        Args:
            recovery_plan: Recovery plan from plan_recovery()
            context: Execution context
        
        Returns:
            True if recovery succeeded, False otherwise
        """
        self.logger.info(f"Executing recovery for: {recovery_plan.failed_plugin}")
        
        if not recovery_plan.recommended_option:
            self.logger.error("No recommended recovery option in plan")
            return False
        
        try:
            option = recovery_plan.recommended_option
            
            # Check approval if callback is set
            if self._approval_callback:
                if not self._approval_callback(recovery_plan):
                    self.logger.info("Recovery execution denied by approval callback")
                    return False
            
            # Execute the recovery option
            success = self._recovery_planner.execute_recovery(
                recovery_plan,
                option,
                approval_callback=self._approval_callback,
            )
            
            self.event_system.emit("recovery_executed", {
                "plugin_name": recovery_plan.failed_plugin,
                "action_type": option.action_type.value,
                "success": success,
            })
            
            # If retry option and successful, re-execute the plugin
            if success and option.action_type.value == "retry":
                self.logger.info(f"Retrying plugin: {recovery_plan.failed_plugin}")
                result = self.execute_plugin(recovery_plan.failed_plugin, context)
                return result.status != PluginStatus.FAILED
            
            return success
        
        except Exception as e:
            self.logger.error(f"Failed to execute recovery: {e}")
            return False

    def record_checkpoint(self, plugin_name: str, state: Any) -> None:
        """
        Record a state checkpoint for recovery
        
        Args:
            plugin_name: Name of the plugin
            state: State snapshot for recovery
        """
        self._plugin_checkpoints[plugin_name] = {
            "timestamp": __import__("datetime").datetime.now(),
            "state": state,
        }
        self.logger.debug(f"Checkpoint recorded for plugin: {plugin_name}")

    def register_recovery_handler(
        self,
        plugin_name: str,
        handler: Callable[[RecoveryPlan], bool],
    ) -> None:
        """
        Register a custom recovery handler for a plugin
        
        Args:
            plugin_name: Name of the plugin
            handler: Callable that executes custom recovery logic
        """
        if plugin_name not in self._recovery_handlers:
            self._recovery_handlers[plugin_name] = []
        
        self._recovery_handlers[plugin_name].append(handler)
        self.logger.debug(f"Registered recovery handler for: {plugin_name}")

    def set_auto_recovery_enabled(self, enabled: bool) -> None:
        """Enable or disable automatic recovery"""
        self._auto_recovery_enabled = enabled
        self.logger.info(f"Auto-recovery: {'enabled' if enabled else 'disabled'}")

    def set_approval_callback(self, callback: Optional[Callable[[RecoveryPlan], bool]]) -> None:
        """
        Set approval callback for recovery execution
        
        Args:
            callback: Function that returns True to approve recovery
        """
        self._approval_callback = callback

    def _collect_service_health(self) -> Dict[str, Any]:
        """Collect health status of key services"""
        services = ["libvirtd", "podman", "airflow", "vault", "networking"]
        health = {}
        
        for service in services:
            try:
                health[service] = DiagnosticContext.get_service_status(service)
            except Exception as e:
                health[service] = {"error": str(e)}
        
        return health

    def _get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """Get list of plugins that depend on this one"""
        dependents = []
        
        for name, info in self._discovered_plugins.items():
            if plugin_name in info.dependencies:
                dependents.append(name)
        
        return dependents

    def _execute_plugin_with_recovery(
        self,
        plugin_name: str,
        context: ExecutionContext,
    ) -> PluginResult:
        """
        Execute plugin with automatic failure recovery
        
        Args:
            plugin_name: Name of plugin to execute
            context: Execution context
        
        Returns:
            PluginResult from plugin execution
        """
        # Execute plugin normally
        result = self.execute_plugin(plugin_name, context)
        
        # If failed and auto-recovery enabled, attempt recovery
        if result.status == PluginStatus.FAILED and self._auto_recovery_enabled:
            self.logger.info(f"Plugin failed; attempting automatic recovery")
            
            # Diagnose failure
            analysis = self.diagnose_failure(plugin_name, result.message, context)
            if not analysis:
                return result
            
            # Plan recovery
            plan = self.plan_recovery(analysis, plugin_name)
            if not plan:
                return result
            
            # Execute recovery
            if self.execute_recovery(plan, context):
                # Try to get updated result from retry
                result = self.execute_plugin(plugin_name, context)
        
        return result
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
