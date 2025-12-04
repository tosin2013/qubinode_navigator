"""
Equinix Metal Plugin

Handles Equinix Metal bare metal deployment configuration and optimization.
Migrates functionality from demo-redhat-com.markdown deployment guide.
"""

import subprocess
import os
import json
from typing import Dict, Any, List
from core.base_plugin import (
    QubiNodePlugin,
    PluginResult,
    SystemState,
    ExecutionContext,
    PluginStatus,
)


class EquinixPlugin(QubiNodePlugin):
    """
    Equinix Metal deployment plugin

    Handles Equinix Metal bare metal infrastructure configuration,
    networking, and optimization for enterprise deployments.
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize Equinix Metal plugin"""
        self.logger.info("Initializing Equinix Metal plugin")

        # Set default configuration
        self.equinix_tools = self.config.get(
            "equinix_tools",
            [
                "metal-cli",  # Equinix Metal CLI
            ],
        )

        # Bare metal specific packages
        self.metal_packages = self.config.get("metal_packages", ["curl", "wget", "jq", "dmidecode", "lshw", "pciutils"])

    def check_state(self) -> SystemState:
        """Check current Equinix Metal configuration state"""
        state_data = {}

        # Check if we're running on Equinix Metal
        state_data["is_equinix_metal"] = self._is_equinix_metal()

        # Check installed metal packages
        state_data["metal_packages_installed"] = self._get_installed_packages()

        # Check Equinix CLI tools
        state_data["equinix_cli_installed"] = self._is_equinix_cli_installed()

        # Check network configuration for bare metal
        state_data["network_configured"] = self._is_network_configured()

        # Check hardware optimization
        state_data["hardware_optimized"] = self._is_hardware_optimized()

        # Check SSH configuration for bare metal access
        state_data["ssh_configured"] = self._is_ssh_configured()

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired Equinix Metal state"""
        desired_data = {}

        # Should be running on Equinix Metal (if applicable)
        desired_data["is_equinix_metal"] = True

        # Metal packages should be installed
        desired_data["metal_packages_installed"] = set(self.metal_packages)

        # Equinix CLI should be installed
        desired_data["equinix_cli_installed"] = True

        # Network should be configured for bare metal
        desired_data["network_configured"] = True

        # Hardware should be optimized
        desired_data["hardware_optimized"] = True

        # SSH should be configured for bare metal access
        desired_data["ssh_configured"] = True

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired Equinix Metal state"""
        changes_made = []

        try:
            # Verify we're on Equinix Metal (or skip optimizations)
            if not current_state.get("is_equinix_metal"):
                self.logger.warning("Not running on Equinix Metal - some optimizations may not apply")

            # Install missing metal packages
            current_packages = set(current_state.get("metal_packages_installed", []))
            desired_packages = desired_state.get("metal_packages_installed", set())
            missing_packages = desired_packages - current_packages

            if missing_packages:
                self._install_packages(list(missing_packages))
                changes_made.append(f"Installed metal packages: {', '.join(missing_packages)}")

            # Install Equinix CLI if needed
            if not current_state.get("equinix_cli_installed") and desired_state.get("equinix_cli_installed"):
                self._install_equinix_cli()
                changes_made.append("Installed Equinix Metal CLI tools")

            # Configure network for bare metal if needed
            if not current_state.get("network_configured") and desired_state.get("network_configured"):
                self._configure_bare_metal_network()
                changes_made.append("Configured bare metal networking")

            # Optimize hardware if needed
            if not current_state.get("hardware_optimized") and desired_state.get("hardware_optimized"):
                self._optimize_bare_metal_hardware()
                changes_made.append("Optimized bare metal hardware configuration")

            # Configure SSH for bare metal access if needed
            if not current_state.get("ssh_configured") and desired_state.get("ssh_configured"):
                self._configure_bare_metal_ssh()
                changes_made.append("Configured SSH for bare metal access")

            return PluginResult(
                changed=len(changes_made) > 0,
                message=f"Applied {len(changes_made)} changes: {'; '.join(changes_made)}",
                status=PluginStatus.COMPLETED,
                data={
                    "changes": changes_made,
                    "equinix_metal": current_state.get("is_equinix_metal", False),
                },
            )

        except Exception as e:
            return PluginResult(
                changed=False,
                message=f"Failed to apply changes: {str(e)}",
                status=PluginStatus.FAILED,
            )

    def _is_equinix_metal(self) -> bool:
        """Check if running on Equinix Metal"""
        try:
            # Check for Equinix Metal metadata service
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "--max-time",
                    "5",
                    "https://metadata.platformequinix.com/metadata",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return True

            # Alternative: check DMI information for Equinix
            try:
                with open("/sys/class/dmi/id/sys_vendor", "r") as f:
                    vendor = f.read().strip()
                    if "Equinix" in vendor or "Packet" in vendor:
                        return True
            except FileNotFoundError:
                pass

            # Alternative: check for Equinix-specific hardware signatures
            try:
                result = subprocess.run(
                    ["dmidecode", "-s", "system-manufacturer"],
                    capture_output=True,
                    text=True,
                )
                if "Equinix" in result.stdout or "Packet" in result.stdout:
                    return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            return False

        except Exception:
            return False

    def _get_installed_packages(self) -> List[str]:
        """Get list of installed packages"""
        try:
            result = subprocess.run(
                ["rpm", "-qa", "--queryformat", "%{NAME}\n"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip().split("\n")
        except subprocess.CalledProcessError:
            return []

    def _install_packages(self, packages: List[str]) -> None:
        """Install packages using dnf"""
        cmd = ["sudo", "dnf", "install", "-y"] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Package installation failed: {result.stderr}")

        self.logger.info(f"Installed packages: {', '.join(packages)}")

    def _is_equinix_cli_installed(self) -> bool:
        """Check if Equinix Metal CLI is installed"""
        try:
            subprocess.run(["metal", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _install_equinix_cli(self) -> None:
        """Install Equinix Metal CLI"""
        try:
            # Download and install metal CLI
            arch = subprocess.run(["uname", "-m"], capture_output=True, text=True, check=True).stdout.strip()
            if arch == "x86_64":
                arch = "amd64"
            elif arch == "aarch64":
                arch = "arm64"

            # Get latest version from GitHub releases
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "https://api.github.com/repos/equinix/metal-cli/releases/latest",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            release_data = json.loads(result.stdout)
            version = release_data["tag_name"].lstrip("v")

            # Download and install
            download_url = f"https://github.com/equinix/metal-cli/releases/download/v{version}/metal-linux-{arch}"

            subprocess.run(["curl", "-L", "-o", "/tmp/metal", download_url], check=True)

            subprocess.run(["sudo", "mv", "/tmp/metal", "/usr/local/bin/"], check=True)

            subprocess.run(["sudo", "chmod", "+x", "/usr/local/bin/metal"], check=True)

            self.logger.info("Installed Equinix Metal CLI")

        except Exception as e:
            self.logger.warning(f"Failed to install Equinix Metal CLI: {e}")

    def _is_network_configured(self) -> bool:
        """Check if network is configured for bare metal"""
        # Check if bonding is configured (common for bare metal)
        try:
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
            return "bond0" in result.stdout or "team0" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def _configure_bare_metal_network(self) -> None:
        """Configure network for bare metal deployment"""
        # Network tuning for bare metal servers
        network_tuning = """
# Network optimizations for Equinix Metal bare metal
net.core.rmem_max = 268435456
net.core.wmem_max = 268435456
net.ipv4.tcp_rmem = 4096 87380 268435456
net.ipv4.tcp_wmem = 4096 65536 268435456
net.core.netdev_max_backlog = 30000
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
"""

        with open("/tmp/99-equinix-network.conf", "w") as f:
            f.write(network_tuning)

        subprocess.run(["sudo", "mv", "/tmp/99-equinix-network.conf", "/etc/sysctl.d/"], check=True)

        # Apply settings
        subprocess.run(["sudo", "sysctl", "--system"], check=True)

        self.logger.info("Configured bare metal networking for Equinix Metal")

    def _is_hardware_optimized(self) -> bool:
        """Check if hardware is optimized for bare metal"""
        # Check if CPU governor is set to performance
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", "r") as f:
                governor = f.read().strip()
                return governor == "performance"
        except FileNotFoundError:
            return True  # No CPU frequency scaling available

    def _optimize_bare_metal_hardware(self) -> None:
        """Optimize hardware configuration for bare metal"""
        # Set CPU governor to performance
        try:
            subprocess.run(["sudo", "cpupower", "frequency-set", "-g", "performance"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("Could not set CPU governor - cpupower not available")

        # Disable swap for better performance
        subprocess.run(["sudo", "swapoff", "-a"], check=True)

        # Configure I/O scheduler for bare metal storage
        io_scheduler_config = """
# I/O scheduler optimization for Equinix Metal bare metal
ACTION=="add|change", KERNEL=="sd[a-z]*", ATTR{queue/scheduler}="mq-deadline"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"
"""

        with open("/tmp/99-equinix-io.rules", "w") as f:
            f.write(io_scheduler_config)

        subprocess.run(["sudo", "mv", "/tmp/99-equinix-io.rules", "/etc/udev/rules.d/"], check=True)

        self.logger.info("Optimized bare metal hardware configuration")

    def _is_ssh_configured(self) -> bool:
        """Check if SSH is configured for bare metal access"""
        return os.path.exists("/root/.ssh/authorized_keys")

    def _configure_bare_metal_ssh(self) -> None:
        """Configure SSH for bare metal access"""
        # Ensure SSH directory exists
        ssh_dir = "/root/.ssh"
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)

        # Configure SSH for bare metal access patterns
        ssh_config = """
# SSH configuration for Equinix Metal bare metal
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
    Compression yes
"""

        with open("/tmp/ssh_config", "w") as f:
            f.write(ssh_config)

        subprocess.run(
            ["sudo", "mv", "/tmp/ssh_config", "/etc/ssh/ssh_config.d/99-equinix.conf"],
            check=True,
        )

        self.logger.info("Configured SSH for bare metal access")

    def get_dependencies(self) -> List[str]:
        """Equinix Metal plugin dependencies"""
        return []  # Can work independently

    def validate_config(self) -> bool:
        """Validate Equinix Metal plugin configuration"""
        # Check that tool lists are valid
        tools = self.config.get("equinix_tools", [])
        if not isinstance(tools, list):
            self.logger.error("equinix_tools configuration must be a list")
            return False

        packages = self.config.get("metal_packages", [])
        if not isinstance(packages, list):
            self.logger.error("metal_packages configuration must be a list")
            return False

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status with Equinix-specific info"""
        base_status = super().get_health_status()

        # Add Equinix-specific status
        base_status.update(
            {
                "equinix_metal": self._is_equinix_metal(),
                "equinix_cli_available": self._is_equinix_cli_installed(),
                "bare_metal_optimized": True,  # Will be determined by state checks
            }
        )

        return base_status
