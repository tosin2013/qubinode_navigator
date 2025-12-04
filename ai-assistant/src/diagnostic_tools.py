"""
System Diagnostic Tools Framework
Provides tool-calling capabilities for AI-powered system diagnostics
Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
"""

import logging
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import psutil
import platform

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a diagnostic tool execution"""

    tool_name: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class DiagnosticTool(ABC):
    """Base class for all diagnostic tools"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the diagnostic tool"""
        pass

    def _create_result(
        self,
        success: bool,
        data: Dict[str, Any],
        error: Optional[str] = None,
        execution_time: float = 0.0,
    ) -> ToolResult:
        """Helper to create a ToolResult"""
        return ToolResult(
            tool_name=self.name,
            success=success,
            data=data,
            error=error,
            execution_time=execution_time,
            timestamp=time.time(),
        )


class SystemInfoTool(DiagnosticTool):
    """Tool for gathering basic system information"""

    def __init__(self):
        super().__init__("system_info", "Gather basic system information")

    async def execute(self, **kwargs) -> ToolResult:
        """Get comprehensive system information"""
        start_time = time.time()

        try:
            # Get system information
            system_info = {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "uptime_seconds": time.time() - psutil.boot_time(),
                "boot_time": psutil.boot_time(),
            }

            execution_time = time.time() - start_time
            return self._create_result(True, system_info, execution_time=execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"System info collection failed: {e}")
            return self._create_result(False, {}, str(e), execution_time)


class ResourceUsageTool(DiagnosticTool):
    """Tool for monitoring system resource usage"""

    def __init__(self):
        super().__init__("resource_usage", "Monitor CPU, memory, disk, and network usage")

    async def execute(self, **kwargs) -> ToolResult:
        """Get current resource usage statistics"""
        start_time = time.time()

        try:
            # CPU information
            cpu_info = {
                "usage_percent": psutil.cpu_percent(interval=1),
                "count_logical": psutil.cpu_count(logical=True),
                "count_physical": psutil.cpu_count(logical=False),
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else None,
                "per_cpu_usage": psutil.cpu_percent(interval=1, percpu=True),
            }

            # Memory information
            memory = psutil.virtual_memory()
            memory_info = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "usage_percent": memory.percent,
                "free_gb": round(memory.free / (1024**3), 2),
            }

            # Disk information
            disk_info = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[partition.mountpoint] = {
                        "device": partition.device,
                        "fstype": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "usage_percent": round((usage.used / usage.total) * 100, 1),
                    }
                except PermissionError:
                    continue

            # Network information
            network_info = {}
            net_io = psutil.net_io_counters(pernic=True)
            for interface, stats in net_io.items():
                network_info[interface] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errors_in": stats.errin,
                    "errors_out": stats.errout,
                    "drops_in": stats.dropin,
                    "drops_out": stats.dropout,
                }

            resource_data = {
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "network": network_info,
            }

            execution_time = time.time() - start_time
            return self._create_result(True, resource_data, execution_time=execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Resource usage collection failed: {e}")
            return self._create_result(False, {}, str(e), execution_time)


class ServiceStatusTool(DiagnosticTool):
    """Tool for checking system service status"""

    def __init__(self):
        super().__init__("service_status", "Check status of system services")

    async def execute(self, services: Optional[List[str]] = None, **kwargs) -> ToolResult:
        """Check status of specified services or common services"""
        start_time = time.time()

        # Default services to check for Qubinode/KVM environment
        default_services = [
            "libvirtd",
            "qemu-kvm",
            "NetworkManager",
            "firewalld",
            "sshd",
            "chronyd",
            "systemd-resolved",
            "dnsmasq",
        ]

        services_to_check = services or default_services

        try:
            service_status = {}

            for service in services_to_check:
                try:
                    # Check if service exists and get status
                    result = subprocess.run(
                        ["systemctl", "is-active", service],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    is_active = result.returncode == 0
                    status = result.stdout.strip()

                    # Get additional service info
                    info_result = subprocess.run(
                        [
                            "systemctl",
                            "show",
                            service,
                            "--property=LoadState,ActiveState,SubState",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    service_info = {"status": status, "active": is_active}

                    if info_result.returncode == 0:
                        for line in info_result.stdout.strip().split("\n"):
                            if "=" in line:
                                key, value = line.split("=", 1)
                                service_info[key.lower()] = value

                    service_status[service] = service_info

                except subprocess.TimeoutExpired:
                    service_status[service] = {
                        "status": "timeout",
                        "active": False,
                        "error": "Command timeout",
                    }
                except Exception as e:
                    service_status[service] = {
                        "status": "error",
                        "active": False,
                        "error": str(e),
                    }

            execution_time = time.time() - start_time
            return self._create_result(True, {"services": service_status}, execution_time=execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Service status check failed: {e}")
            return self._create_result(False, {}, str(e), execution_time)


class ProcessInfoTool(DiagnosticTool):
    """Tool for gathering process information"""

    def __init__(self):
        super().__init__("process_info", "Gather information about running processes")

    async def execute(self, filter_name: Optional[str] = None, top_n: int = 10, **kwargs) -> ToolResult:
        """Get information about running processes"""
        start_time = time.time()

        try:
            processes = []

            for proc in psutil.process_iter(
                [
                    "pid",
                    "name",
                    "cpu_percent",
                    "memory_percent",
                    "status",
                    "create_time",
                ]
            ):
                try:
                    proc_info = proc.info

                    # Filter by name if specified
                    if filter_name and filter_name.lower() not in proc_info["name"].lower():
                        continue

                    # Add additional info
                    proc_info["memory_mb"] = round(proc.memory_info().rss / (1024 * 1024), 2)
                    proc_info["uptime_seconds"] = time.time() - proc_info["create_time"]

                    processes.append(proc_info)

                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    continue

            # Sort by CPU usage and limit results
            processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
            if not filter_name:
                processes = processes[:top_n]

            process_data = {
                "total_processes": len(psutil.pids()),
                "filtered_processes": len(processes),
                "processes": processes,
            }

            execution_time = time.time() - start_time
            return self._create_result(True, process_data, execution_time=execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Process info collection failed: {e}")
            return self._create_result(False, {}, str(e), execution_time)


class KVMDiagnosticTool(DiagnosticTool):
    """Tool for KVM/libvirt specific diagnostics"""

    def __init__(self):
        super().__init__("kvm_diagnostics", "Check KVM/libvirt environment status")

    async def execute(self, **kwargs) -> ToolResult:
        """Check KVM/libvirt specific components"""
        start_time = time.time()

        try:
            kvm_data = {}

            # Check KVM module
            try:
                with open("/proc/modules", "r") as f:
                    modules = f.read()
                    kvm_data["kvm_module_loaded"] = "kvm" in modules
                    kvm_data["kvm_intel_loaded"] = "kvm_intel" in modules
                    kvm_data["kvm_amd_loaded"] = "kvm_amd" in modules
            except Exception as e:
                kvm_data["kvm_module_error"] = str(e)

            # Check CPU virtualization support
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read()
                    kvm_data["vmx_support"] = "vmx" in cpuinfo  # Intel
                    kvm_data["svm_support"] = "svm" in cpuinfo  # AMD
            except Exception as e:
                kvm_data["cpu_check_error"] = str(e)

            # Check libvirt connection
            try:
                result = subprocess.run(["virsh", "version"], capture_output=True, text=True, timeout=10)
                kvm_data["libvirt_available"] = result.returncode == 0
                if result.returncode == 0:
                    kvm_data["libvirt_version"] = result.stdout.strip()
            except Exception as e:
                kvm_data["libvirt_error"] = str(e)

            # Check for VMs
            try:
                result = subprocess.run(
                    ["virsh", "list", "--all"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")[2:]  # Skip header
                    kvm_data["vm_count"] = len([line for line in lines if line.strip()])
                    kvm_data["vm_list"] = result.stdout.strip()
            except Exception as e:
                kvm_data["vm_list_error"] = str(e)

            execution_time = time.time() - start_time
            return self._create_result(True, kvm_data, execution_time=execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"KVM diagnostics failed: {e}")
            return self._create_result(False, {}, str(e), execution_time)


class NetworkDiagnosticTool(DiagnosticTool):
    """Tool for network connectivity diagnostics"""

    def __init__(self):
        super().__init__("network_diagnostics", "Check network connectivity and configuration")

    async def execute(self, targets: Optional[List[str]] = None, **kwargs) -> ToolResult:
        """Check network connectivity and configuration"""
        start_time = time.time()

        default_targets = ["8.8.8.8", "1.1.1.1", "google.com"]
        test_targets = targets or default_targets

        try:
            network_data = {}

            # Get network interfaces
            try:
                interfaces = psutil.net_if_addrs()
                network_data["interfaces"] = {}
                for interface, addrs in interfaces.items():
                    network_data["interfaces"][interface] = []
                    for addr in addrs:
                        network_data["interfaces"][interface].append(
                            {
                                "family": str(addr.family),
                                "address": addr.address,
                                "netmask": addr.netmask,
                                "broadcast": addr.broadcast,
                            }
                        )
            except Exception as e:
                network_data["interface_error"] = str(e)

            # Test connectivity
            connectivity_results = {}
            for target in test_targets:
                try:
                    result = subprocess.run(
                        ["ping", "-c", "3", "-W", "3", target],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )

                    connectivity_results[target] = {
                        "reachable": result.returncode == 0,
                        "output": result.stdout if result.returncode == 0 else result.stderr,
                    }
                except subprocess.TimeoutExpired:
                    connectivity_results[target] = {
                        "reachable": False,
                        "error": "timeout",
                    }
                except Exception as e:
                    connectivity_results[target] = {"reachable": False, "error": str(e)}

            network_data["connectivity"] = connectivity_results

            # Check DNS resolution
            try:
                result = subprocess.run(
                    ["nslookup", "google.com"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                network_data["dns_resolution"] = {
                    "working": result.returncode == 0,
                    "output": result.stdout if result.returncode == 0 else result.stderr,
                }
            except Exception as e:
                network_data["dns_error"] = str(e)

            execution_time = time.time() - start_time
            return self._create_result(True, network_data, execution_time=execution_time)

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Network diagnostics failed: {e}")
            return self._create_result(False, {}, str(e), execution_time)


class DiagnosticToolRegistry:
    """Registry for managing diagnostic tools"""

    def __init__(self):
        self.tools: Dict[str, DiagnosticTool] = {}
        self.logger = logging.getLogger(__name__)
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default diagnostic tools"""
        default_tools = [
            SystemInfoTool(),
            ResourceUsageTool(),
            ServiceStatusTool(),
            ProcessInfoTool(),
            KVMDiagnosticTool(),
            NetworkDiagnosticTool(),
        ]

        for tool in default_tools:
            self.register_tool(tool)

    def register_tool(self, tool: DiagnosticTool):
        """Register a diagnostic tool"""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered diagnostic tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[DiagnosticTool]:
        """Get a diagnostic tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> Dict[str, str]:
        """List all available tools with descriptions"""
        return {name: tool.description for name, tool in self.tools.items()}

    async def run_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Run a specific diagnostic tool"""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                data={},
                error=f"Tool '{tool_name}' not found",
                timestamp=time.time(),
            )

        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            self.logger.error(f"Tool execution failed for {tool_name}: {e}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                data={},
                error=str(e),
                timestamp=time.time(),
            )

    async def run_all_tools(self, **kwargs) -> Dict[str, ToolResult]:
        """Run all registered diagnostic tools"""
        results = {}

        for tool_name in self.tools:
            try:
                result = await self.run_tool(tool_name, **kwargs)
                results[tool_name] = result
            except Exception as e:
                self.logger.error(f"Failed to run tool {tool_name}: {e}")
                results[tool_name] = ToolResult(
                    tool_name=tool_name,
                    success=False,
                    data={},
                    error=str(e),
                    timestamp=time.time(),
                )

        return results

    async def run_comprehensive_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostics"""
        start_time = time.time()

        # Run all tools
        tool_results = await self.run_all_tools()

        # Compile summary
        summary = {
            "total_tools": len(self.tools),
            "successful_tools": sum(1 for result in tool_results.values() if result.success),
            "failed_tools": sum(1 for result in tool_results.values() if not result.success),
            "total_execution_time": time.time() - start_time,
            "timestamp": time.time(),
        }

        return {
            "summary": summary,
            "tool_results": {name: result.to_dict() for name, result in tool_results.items()},
        }


# Global registry instance
diagnostic_registry = DiagnosticToolRegistry()
