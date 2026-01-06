"""
Base Plugin Classes and Interfaces

Implements the plugin interface specification from ADR-0028 with
idempotency support and comprehensive state management.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
import subprocess
import psutil
import os
from datetime import datetime


class PluginStatus(Enum):
    """Plugin execution status"""

    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SystemState:
    """Represents the current state of the system for idempotency checks"""

    def __init__(self, state_data: Dict[str, Any] = None):
        self.state_data = state_data or {}

    def matches(self, other: "SystemState") -> bool:
        """Compare system states for idempotency checks"""
        if not isinstance(other, SystemState):
            return False
        return self.state_data == other.state_data

    def get(self, key: str, default: Any = None) -> Any:
        """Get state value by key"""
        return self.state_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set state value by key"""
        self.state_data[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple state values"""
        self.state_data.update(updates)


@dataclass
class PluginResult:
    """Result of plugin execution"""

    def __init__(
        self,
        changed: bool = False,
        message: str = "",
        data: Dict[str, Any] = None,
        status: PluginStatus = PluginStatus.COMPLETED,
        final_state: SystemState = None,
    ):
        self.changed = changed
        self.message = message
        self.data = data or {}
        self.status = status
        self.final_state = final_state or SystemState()


@dataclass
class ExecutionContext:
    """Context information for plugin execution"""

    def __init__(
        self,
        inventory: str = "localhost",
        environment: str = "development",
        config: Dict[str, Any] = None,
        variables: Dict[str, Any] = None,
    ):
        self.inventory = inventory
        self.environment = environment
        self.config = config or {}
        self.variables = variables or {}


@dataclass
class DiagnosticContext:
    """
    Failure diagnosis context providing real-time system state and diagnostics

    Enables plugins to report detailed failure information for root cause analysis
    """

    plugin_name: str
    failure_timestamp: datetime
    error_message: str
    system_state: Dict[str, Any] = field(default_factory=dict)
    dependent_plugins: List[str] = field(default_factory=list)
    service_health: Dict[str, Any] = field(default_factory=dict)
    system_resources: Dict[str, Any] = field(default_factory=dict)
    recent_logs: List[Dict[str, Any]] = field(default_factory=list)
    network_status: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def get_plugin_logs(plugin_name: str, since_seconds: int = 300) -> List[Dict[str, Any]]:
        """
        Retrieve recent plugin logs

        Args:
            plugin_name: Name of the plugin
            since_seconds: Time window in seconds to retrieve logs

        Returns:
            List of log entries with timestamp, level, and message
        """
        logs = []

        # In a real implementation, this would query a centralized log store
        # For now, we return a structured format for log aggregation
        try:
            # This is a placeholder - actual implementation would query:
            # - systemd journal (journalctl)
            # - podman logs
            # - file-based logs in /var/log or /opt/qubinode_navigator/logs
            logs.append({"timestamp": datetime.now().isoformat(), "level": "INFO", "plugin": plugin_name, "message": f"Retrieving logs for {plugin_name} from last {since_seconds}s"})
        except Exception as e:
            logs.append({"timestamp": datetime.now().isoformat(), "level": "ERROR", "plugin": plugin_name, "message": f"Failed to retrieve logs: {str(e)}"})

        return logs

    @staticmethod
    def get_service_status(service_name: str) -> Dict[str, Any]:
        """
        Get status of a system service (supports both systemd and containerized services)

        Args:
            service_name: Name of the service (e.g., 'airflow', 'libvirtd', 'postgres')

        Returns:
            Dict with service state, pid, uptime, last restart, and container info if applicable
        """
        status = {
            "service": service_name,
            "active": False,
            "pid": None,
            "uptime_seconds": None,
            "last_restart": None,
            "is_container": False,
            "container_id": None,
            "details": {},
        }

        # Step 1: Check if this service has a Podman container
        container_status = DiagnosticContext._check_container_status(service_name)
        if container_status and container_status["active"]:
            status.update(container_status)
            return status

        # Step 2: Fall back to systemctl
        try:
            result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, timeout=5)
            status["active"] = result.returncode == 0

            if status["active"]:
                # Get service info
                show_result = subprocess.run(["systemctl", "show", service_name], capture_output=True, timeout=5, text=True)
                if show_result.returncode == 0:
                    for line in show_result.stdout.split("\n"):
                        if "=" in line:
                            key, val = line.split("=", 1)
                            status["details"][key.lower()] = val

        except subprocess.TimeoutExpired:
            status["details"]["error"] = "Service status check timed out"
        except FileNotFoundError:
            # systemctl not available, try pgrep
            try:
                result = subprocess.run(["pgrep", "-f", service_name], capture_output=True, timeout=5, text=True)
                if result.returncode == 0:
                    status["active"] = True
                    status["pid"] = result.stdout.strip().split()[0] if result.stdout else None
            except Exception as e:
                status["details"]["error"] = str(e)
        except Exception as e:
            status["details"]["error"] = str(e)

        return status

    @staticmethod
    def _service_to_container_names(service_name: str) -> List[str]:
        """
        Map service name to possible container names

        Args:
            service_name: Name of the service (e.g., 'airflow', 'postgres')

        Returns:
            List of possible container names to check
        """
        container_name_mapping = {
            "airflow": ["airflow-scheduler", "airflow-webserver", "airflow-worker"],
            "postgres": ["postgres", "airflow-postgres", "pgvector"],
            "marquez": ["marquez-api", "marquez-web"],
            "mcp": ["mcp-server", "airflow-mcp"],
            "libvirtd": ["libvirtd"],
        }
        return container_name_mapping.get(service_name, [service_name])

    @staticmethod
    def _check_container_status(service_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if a service is running in a Podman container

        Args:
            service_name: Name of the service

        Returns:
            Dict with container status or None if not found
        """
        possible_names = DiagnosticContext._service_to_container_names(service_name)

        for container_name in possible_names:
            try:
                # Check if container exists and is running
                result = subprocess.run(
                    ["podman", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.ID}}|{{.State}}|{{.Names}}"],
                    capture_output=True,
                    timeout=5,
                    text=True,
                )

                if result.returncode == 0 and result.stdout.strip():
                    container_id, state, names = result.stdout.strip().split("|")
                    is_running = state == "running"

                    # Get container details
                    container_info = DiagnosticContext._get_container_info(container_id)
                    container_info.update(
                        {
                            "is_container": True,
                            "container_id": container_id,
                            "active": is_running,
                            "container_name": names,
                            "container_state": state,
                        }
                    )
                    return container_info
            except subprocess.TimeoutExpired:
                continue
            except FileNotFoundError:
                # Podman not available
                return None
            except Exception:
                continue

        return None

    @staticmethod
    def _get_container_info(container_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a running container

        Args:
            container_id: Container ID or name

        Returns:
            Dict with container details (uptime, restart count, etc.)
        """
        info = {"details": {}}

        try:
            # Get container inspect data
            result = subprocess.run(
                [
                    "podman",
                    "inspect",
                    container_id,
                    "--format",
                    "{{.State.StartedAt}}|{{.RestartCount}}|{{.State.Pid}}|{{.State.Status}}",
                ],
                capture_output=True,
                timeout=5,
                text=True,
            )

            if result.returncode == 0:
                started_at, restart_count, pid, status = result.stdout.strip().split("|")
                info["pid"] = int(pid) if pid and pid != "0" else None

                # Calculate uptime
                try:
                    from datetime import datetime

                    start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    uptime = (datetime.now(start_time.tzinfo) - start_time).total_seconds()
                    info["uptime_seconds"] = int(uptime)
                except Exception:
                    pass

                info["details"]["restart_count"] = int(restart_count)
                info["details"]["container_status"] = status

        except subprocess.TimeoutExpired:
            info["details"]["error"] = "Container inspect timed out"
        except FileNotFoundError:
            return {}
        except Exception as e:
            info["details"]["error"] = str(e)

        return info

    @staticmethod
    def get_system_resources() -> Dict[str, Any]:
        """
        Get current system resource utilization

        Returns:
            Dict with CPU, memory, disk, and network metrics
        """
        resources = {"timestamp": datetime.now().isoformat(), "cpu": {}, "memory": {}, "disk": {}, "network": {}}

        try:
            # CPU metrics
            resources["cpu"]["percent"] = psutil.cpu_percent(interval=1)
            resources["cpu"]["count_logical"] = psutil.cpu_count()
            resources["cpu"]["count_physical"] = psutil.cpu_count(logical=False)
            resources["cpu"]["load_average"] = dict(zip(["1min", "5min", "15min"], os.getloadavg() if hasattr(os, "getloadavg") else [0, 0, 0]))
        except Exception as e:
            resources["cpu"]["error"] = str(e)

        try:
            # Memory metrics
            mem = psutil.virtual_memory()
            resources["memory"]["total"] = mem.total
            resources["memory"]["available"] = mem.available
            resources["memory"]["percent"] = mem.percent
            resources["memory"]["used"] = mem.used
        except Exception as e:
            resources["memory"]["error"] = str(e)

        try:
            # Disk metrics
            disk = psutil.disk_usage("/")
            resources["disk"]["total"] = disk.total
            resources["disk"]["used"] = disk.used
            resources["disk"]["free"] = disk.free
            resources["disk"]["percent"] = disk.percent
        except Exception as e:
            resources["disk"]["error"] = str(e)

        try:
            # Network metrics
            net_if = psutil.net_if_stats()
            resources["network"]["interfaces"] = {}
            for iface, stats in net_if.items():
                resources["network"]["interfaces"][iface] = {"up": stats.isup, "speed": stats.speed, "mtu": stats.mtu}
        except Exception as e:
            resources["network"]["error"] = str(e)

        return resources

    @staticmethod
    def get_network_connectivity(target: str) -> Dict[str, Any]:
        """
        Check network connectivity to a target

        Args:
            target: Hostname or IP address to check

        Returns:
            Dict with connectivity status and latency info
        """
        connectivity = {"target": target, "reachable": False, "latency_ms": None, "details": {}}

        try:
            import socket

            # Try DNS resolution
            ip = socket.gethostbyname(target)
            connectivity["details"]["resolved_ip"] = ip

            # Try ICMP ping
            result = subprocess.run(["ping", "-c", "1", "-W", "2", target], capture_output=True, timeout=5, text=True)
            if result.returncode == 0:
                connectivity["reachable"] = True
                # Extract latency
                import re

                match = re.search(r"time=(\d+\.?\d*) ms", result.stdout)
                if match:
                    connectivity["latency_ms"] = float(match.group(1))
            else:
                connectivity["details"]["ping_error"] = result.stderr

        except socket.gaierror as e:
            connectivity["details"]["dns_error"] = str(e)
        except Exception as e:
            connectivity["details"]["error"] = str(e)

        return connectivity


class QubiNodePlugin(ABC):
    """
    Base class for all Qubinode Navigator plugins

    Implements the plugin interface specification from ADR-0028
    with idempotency support and comprehensive lifecycle management.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._initialized = False

    @property
    def name(self) -> str:
        """Plugin name for identification"""
        return self.__class__.__name__

    @property
    def version(self) -> str:
        """Plugin version"""
        return getattr(self, "__version__", "1.0.0")

    def initialize(self) -> bool:
        """
        Initialize plugin resources

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self._initialize_plugin()
            self._initialized = True
            self.logger.info(f"Plugin {self.name} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin {self.name}: {e}")
            return False

    @abstractmethod
    def _initialize_plugin(self) -> None:
        """Plugin-specific initialization logic"""
        pass

    @abstractmethod
    def check_state(self) -> SystemState:
        """
        Check current system state for idempotency

        Returns:
            SystemState: Current state of the system
        """
        pass

    def is_idempotent(self) -> bool:
        """
        Verify plugin can be safely re-run

        Returns:
            bool: True if plugin is idempotent, False otherwise
        """
        return True

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """
        Get the desired system state based on context

        Args:
            context: Execution context with configuration and variables

        Returns:
            SystemState: Desired state of the system
        """
        # Default implementation - plugins should override if needed
        return SystemState()

    def execute(self, context: ExecutionContext) -> PluginResult:
        """
        Execute plugin functionality with idempotent behavior

        Args:
            context: Execution context with configuration and variables

        Returns:
            PluginResult: Result of plugin execution
        """
        if not self._initialized:
            if not self.initialize():
                return PluginResult(
                    changed=False,
                    message=f"Plugin {self.name} initialization failed",
                    status=PluginStatus.FAILED,
                )

        try:
            # Check current state for idempotency
            current_state = self.check_state()
            desired_state = self.get_desired_state(context)

            if current_state.matches(desired_state):
                self.logger.info(f"Plugin {self.name}: System already in desired state")
                return PluginResult(
                    changed=False,
                    message="Already in desired state",
                    status=PluginStatus.SKIPPED,
                    final_state=current_state,
                )

            # Execute plugin-specific logic
            self.logger.info(f"Plugin {self.name}: Applying changes")
            result = self.apply_changes(current_state, desired_state, context)

            # Verify final state
            final_state = self.check_state()
            result.final_state = final_state

            self.logger.info(f"Plugin {self.name}: Execution completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Plugin {self.name} execution failed: {e}")
            return PluginResult(
                changed=False,
                message=f"Execution failed: {str(e)}",
                status=PluginStatus.FAILED,
            )

    @abstractmethod
    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """
        Apply changes to move from current state to desired state

        Args:
            current_state: Current system state
            desired_state: Desired system state
            context: Execution context

        Returns:
            PluginResult: Result of applying changes
        """
        pass

    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        try:
            self._cleanup_plugin()
            self.logger.info(f"Plugin {self.name} cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Failed to cleanup plugin {self.name}: {e}")

    def _cleanup_plugin(self) -> None:
        """Plugin-specific cleanup logic"""
        pass

    def get_dependencies(self) -> List[str]:
        """
        Return list of required plugins

        Returns:
            List[str]: List of plugin names this plugin depends on
        """
        return []

    def validate_config(self) -> bool:
        """
        Validate plugin configuration

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        return True

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get plugin health status

        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "status": "healthy" if self._initialized else "not_initialized",
        }
