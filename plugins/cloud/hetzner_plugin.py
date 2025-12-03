"""
Hetzner Cloud Plugin

Handles Hetzner-specific cloud infrastructure setup and optimization.
Migrates cloud-specific functionality from rocky-linux-hetzner.sh.
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


class HetznerPlugin(QubiNodePlugin):
    """
    Hetzner Cloud deployment plugin

    Handles Hetzner-specific cloud infrastructure configuration,
    networking, and optimization for cost-effective deployments.
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize Hetzner plugin"""
        self.logger.info("Initializing Hetzner Cloud plugin")

        # Set default configuration
        self.hetzner_tools = self.config.get(
            "hetzner_tools",
            [
                "hcloud",  # Hetzner Cloud CLI
            ],
        )

        # Cloud-specific packages
        self.cloud_packages = self.config.get(
            "cloud_packages", ["curl", "wget", "jq", "cloud-init", "cloud-utils"]
        )

    def check_state(self) -> SystemState:
        """Check current Hetzner cloud configuration state"""
        state_data = {}

        # Check if we're running on Hetzner (check for Hetzner-specific metadata)
        state_data["is_hetzner_cloud"] = self._is_hetzner_cloud()

        # Check installed cloud packages
        state_data["cloud_packages_installed"] = self._get_installed_packages()

        # Check Hetzner CLI tools
        state_data["hetzner_cli_installed"] = self._is_hetzner_cli_installed()

        # Check cloud-init configuration
        state_data["cloud_init_configured"] = self._is_cloud_init_configured()

        # Check network configuration
        state_data["network_optimized"] = self._is_network_optimized()

        # Check storage configuration
        state_data["storage_optimized"] = self._is_storage_optimized()

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired Hetzner cloud state"""
        desired_data = {}

        # Should be running on Hetzner cloud
        desired_data["is_hetzner_cloud"] = True

        # Cloud packages should be installed
        desired_data["cloud_packages_installed"] = set(self.cloud_packages)

        # Hetzner CLI should be installed
        desired_data["hetzner_cli_installed"] = True

        # Cloud-init should be configured
        desired_data["cloud_init_configured"] = True

        # Network should be optimized
        desired_data["network_optimized"] = True

        # Storage should be optimized
        desired_data["storage_optimized"] = True

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired Hetzner cloud state"""
        changes_made = []

        try:
            # Verify we're on Hetzner cloud
            if not current_state.get("is_hetzner_cloud"):
                self.logger.warning(
                    "Not running on Hetzner Cloud - some optimizations may not apply"
                )

            # Install missing cloud packages
            current_packages = set(current_state.get("cloud_packages_installed", []))
            desired_packages = desired_state.get("cloud_packages_installed", set())
            missing_packages = desired_packages - current_packages

            if missing_packages:
                self._install_packages(list(missing_packages))
                changes_made.append(
                    f"Installed cloud packages: {', '.join(missing_packages)}"
                )

            # Install Hetzner CLI if needed
            if not current_state.get("hetzner_cli_installed") and desired_state.get(
                "hetzner_cli_installed"
            ):
                self._install_hetzner_cli()
                changes_made.append("Installed Hetzner CLI tools")

            # Configure cloud-init if needed
            if not current_state.get("cloud_init_configured") and desired_state.get(
                "cloud_init_configured"
            ):
                self._configure_cloud_init()
                changes_made.append("Configured cloud-init")

            # Optimize network if needed
            if not current_state.get("network_optimized") and desired_state.get(
                "network_optimized"
            ):
                self._optimize_network()
                changes_made.append("Optimized network configuration")

            # Optimize storage if needed
            if not current_state.get("storage_optimized") and desired_state.get(
                "storage_optimized"
            ):
                self._optimize_storage()
                changes_made.append("Optimized storage configuration")

            return PluginResult(
                changed=len(changes_made) > 0,
                message=f"Applied {len(changes_made)} changes: {'; '.join(changes_made)}",
                status=PluginStatus.COMPLETED,
                data={
                    "changes": changes_made,
                    "hetzner_cloud": current_state.get("is_hetzner_cloud", False),
                },
            )

        except Exception as e:
            return PluginResult(
                changed=False,
                message=f"Failed to apply changes: {str(e)}",
                status=PluginStatus.FAILED,
            )

    def _is_hetzner_cloud(self) -> bool:
        """Check if running on Hetzner Cloud"""
        try:
            # Check for Hetzner metadata service
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "--max-time",
                    "5",
                    "http://169.254.169.254/hetzner/v1/metadata",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return True

            # Alternative: check DMI information
            try:
                with open("/sys/class/dmi/id/sys_vendor", "r") as f:
                    vendor = f.read().strip()
                    return "Hetzner" in vendor
            except FileNotFoundError:
                pass

            # Alternative: check for Hetzner-specific network interfaces
            result = subprocess.run(["ip", "addr"], capture_output=True, text=True)
            if "eth0" in result.stdout and "10.0.0" in result.stdout:
                return True

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

    def _is_hetzner_cli_installed(self) -> bool:
        """Check if Hetzner CLI is installed"""
        try:
            subprocess.run(["hcloud", "version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _install_hetzner_cli(self) -> None:
        """Install Hetzner CLI"""
        try:
            # Download and install hcloud CLI
            arch = subprocess.run(
                ["uname", "-m"], capture_output=True, text=True, check=True
            ).stdout.strip()
            if arch == "x86_64":
                arch = "amd64"
            elif arch == "aarch64":
                arch = "arm64"

            # Get latest version
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "https://api.github.com/repos/hetznercloud/cli/releases/latest",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            release_data = json.loads(result.stdout)
            version = release_data["tag_name"].lstrip("v")

            # Download and install
            download_url = f"https://github.com/hetznercloud/cli/releases/download/v{version}/hcloud-linux-{arch}.tar.gz"

            subprocess.run(
                ["curl", "-L", "-o", "/tmp/hcloud.tar.gz", download_url], check=True
            )

            subprocess.run(
                ["tar", "-xzf", "/tmp/hcloud.tar.gz", "-C", "/tmp"], check=True
            )

            subprocess.run(["sudo", "mv", "/tmp/hcloud", "/usr/local/bin/"], check=True)

            subprocess.run(["sudo", "chmod", "+x", "/usr/local/bin/hcloud"], check=True)

            # Cleanup
            os.remove("/tmp/hcloud.tar.gz")

            self.logger.info("Installed Hetzner CLI")

        except Exception as e:
            self.logger.warning(f"Failed to install Hetzner CLI: {e}")

    def _is_cloud_init_configured(self) -> bool:
        """Check if cloud-init is properly configured"""
        return os.path.exists("/etc/cloud/cloud.cfg") and os.path.exists(
            "/var/lib/cloud"
        )

    def _configure_cloud_init(self) -> None:
        """Configure cloud-init for Hetzner Cloud"""
        # Ensure cloud-init is installed
        subprocess.run(["sudo", "dnf", "install", "-y", "cloud-init"], check=True)

        # Configure cloud-init datasource for Hetzner
        cloud_cfg = """
# Hetzner Cloud configuration
datasource_list: [ Hetzner, None ]
datasource:
  Hetzner: {}

# Preserve hostname
preserve_hostname: false

# Cloud config modules
cloud_init_modules:
 - migrator
 - seed_random
 - bootcmd
 - write-files
 - growpart
 - resizefs
 - disk_setup
 - mounts
 - set_hostname
 - update_hostname
 - update_etc_hosts
 - ca-certs
 - rsyslog
 - users-groups
 - ssh

cloud_config_modules:
 - ssh-import-id
 - locale
 - set-passwords
 - package-update-upgrade-install
 - yum-add-repo
 - ntp
 - timezone
 - disable-ec2-metadata
 - runcmd

cloud_final_modules:
 - package-update-upgrade-install
 - rightscale_userdata
 - scripts-vendor
 - scripts-per-once
 - scripts-per-boot
 - scripts-per-instance
 - scripts-user
 - ssh-authkey-fingerprints
 - keys-to-console
 - phone-home
 - final-message
 - power-state-change
"""

        with open("/tmp/cloud.cfg", "w") as f:
            f.write(cloud_cfg)

        subprocess.run(
            ["sudo", "mv", "/tmp/cloud.cfg", "/etc/cloud/cloud.cfg"], check=True
        )

        # Enable cloud-init services
        services = ["cloud-init-local", "cloud-init", "cloud-config", "cloud-final"]
        for service in services:
            subprocess.run(["sudo", "systemctl", "enable", service], check=True)

        self.logger.info("Configured cloud-init for Hetzner Cloud")

    def _is_network_optimized(self) -> bool:
        """Check if network is optimized for cloud"""
        # Check if network tuning is applied
        try:
            with open("/etc/sysctl.conf", "r") as f:
                content = f.read()
                return "net.core.rmem_max" in content
        except FileNotFoundError:
            return False

    def _optimize_network(self) -> None:
        """Optimize network configuration for Hetzner Cloud"""
        # Network tuning for cloud environments
        network_tuning = """
# Network optimizations for Hetzner Cloud
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 65536 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_congestion_control = bbr
"""

        with open("/tmp/99-hetzner-network.conf", "w") as f:
            f.write(network_tuning)

        subprocess.run(
            ["sudo", "mv", "/tmp/99-hetzner-network.conf", "/etc/sysctl.d/"], check=True
        )

        # Apply settings
        subprocess.run(["sudo", "sysctl", "--system"], check=True)

        self.logger.info("Optimized network configuration for Hetzner Cloud")

    def _is_storage_optimized(self) -> bool:
        """Check if storage is optimized for cloud"""
        # Check if fstrim timer is enabled
        try:
            result = subprocess.run(
                ["systemctl", "is-enabled", "fstrim.timer"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def _optimize_storage(self) -> None:
        """Optimize storage configuration for Hetzner Cloud"""
        # Enable fstrim for SSD optimization
        subprocess.run(["sudo", "systemctl", "enable", "fstrim.timer"], check=True)
        subprocess.run(["sudo", "systemctl", "start", "fstrim.timer"], check=True)

        # Configure I/O scheduler for cloud storage
        io_scheduler_config = """
# I/O scheduler optimization for Hetzner Cloud
ACTION=="add|change", KERNEL=="sd[a-z]*", ATTR{queue/scheduler}="mq-deadline"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"
"""

        with open("/tmp/99-hetzner-io.rules", "w") as f:
            f.write(io_scheduler_config)

        subprocess.run(
            ["sudo", "mv", "/tmp/99-hetzner-io.rules", "/etc/udev/rules.d/"], check=True
        )

        self.logger.info("Optimized storage configuration for Hetzner Cloud")

    def get_dependencies(self) -> List[str]:
        """Hetzner plugin dependencies"""
        return []  # Can work independently

    def validate_config(self) -> bool:
        """Validate Hetzner plugin configuration"""
        # Check that tool lists are valid
        tools = self.config.get("hetzner_tools", [])
        if not isinstance(tools, list):
            self.logger.error("hetzner_tools configuration must be a list")
            return False

        packages = self.config.get("cloud_packages", [])
        if not isinstance(packages, list):
            self.logger.error("cloud_packages configuration must be a list")
            return False

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status with Hetzner-specific info"""
        base_status = super().get_health_status()

        # Add Hetzner-specific status
        base_status.update(
            {
                "hetzner_cloud": self._is_hetzner_cloud(),
                "hetzner_cli_available": self._is_hetzner_cli_installed(),
                "cloud_optimized": True,  # Will be determined by state checks
            }
        )

        return base_status
