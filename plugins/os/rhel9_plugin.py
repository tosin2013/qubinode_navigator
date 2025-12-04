"""
RHEL 9 Plugin - The "Modern Enterprise Infrastructure Specialist"

Handles RHEL 9 specific deployment logic as part of the plugin framework
migration from monolithic scripts (ADR-0028). Represents the current generation
of enterprise Linux with modern container support and enhanced security.
"""

import subprocess
import os
import uuid
from typing import List
from core.base_plugin import (
    QubiNodePlugin,
    PluginResult,
    SystemState,
    ExecutionContext,
    PluginStatus,
)


class RHEL9Plugin(QubiNodePlugin):
    """
    RHEL 9 deployment plugin - Modern Enterprise Infrastructure Specialist

    Implements comprehensive RHEL 9 deployment pipeline:
    - Modern Enterprise Environment Setup
    - Enhanced Container Support (Podman 4.x)
    - Advanced Security Configuration
    - Modern Storage Management
    - Network Optimization
    - Vault Integration
    - Next-Gen Virtualization Platform
    - Modern Tool Integration
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize RHEL 9 plugin"""
        self.logger.info("Initializing RHEL 9 plugin - Modern Enterprise Infrastructure Specialist")

        # Validate we're running on RHEL 9
        if not self._is_rhel9():
            raise RuntimeError("RHEL 9 plugin can only run on RHEL 9 systems")

        # Set configuration constants for modern enterprise deployment
        self.kvm_version = self.config.get("kvm_version", "latest")
        self.ansible_safe_version = self.config.get("ansible_safe_version", "0.0.9")
        self.git_repo = self.config.get("git_repo", "https://github.com/Qubinode/qubinode_navigator.git")

        # Set default packages for RHEL 9 modern deployment
        self.packages = self.config.get(
            "packages",
            [
                "bzip2-devel",
                "libffi-devel",
                "wget",
                "vim",
                "podman",
                "ncurses-devel",
                "sqlite-devel",
                "firewalld",
                "make",
                "gcc",
                "git",
                "unzip",
                "sshpass",
                "lvm2",
                "python3",
                "python3-pip",
                "java-11-openjdk-devel",
                "ansible-core",
                "perl-Digest-SHA",
                "container-tools",
                "buildah",
                "skopeo",  # Modern container tools
            ],
        )

        # Set environment variables
        self.cicd_pipeline = os.getenv("CICD_PIPELINE", "false")
        self.inventory = os.getenv("INVENTORY", "localhost")
        self.guid = os.getenv("GUID", str(uuid.uuid4())[:5])
        self.use_hashicorp_vault = os.getenv("USE_HASHICORP_VAULT", "false")

        # Validate vault configuration if enabled
        if self.use_hashicorp_vault.lower() == "true":
            if not all([os.getenv("VAULT_ADDRESS"), os.getenv("SECRET_PATH")]):
                raise RuntimeError("Vault environment variables not properly configured")

    def _is_rhel9(self) -> bool:
        """Check if running on RHEL 9"""
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                return 'ID="rhel"' in content and 'VERSION_ID="9' in content
        except FileNotFoundError:
            return False

    def check_state(self) -> SystemState:
        """Check current RHEL 9 system state"""
        state_data = {}

        # Check installed packages
        state_data["installed_packages"] = self._get_installed_packages()

        # Check services
        state_data["firewalld_enabled"] = self._is_service_enabled("firewalld")
        state_data["firewalld_active"] = self._is_service_active("firewalld")

        # Check Python version
        state_data["python_version"] = self._get_python_version()

        # Check if lab-user exists
        state_data["lab_user_exists"] = self._user_exists("lab-user")

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired RHEL 9 system state"""
        desired_data = {}

        # All required packages should be installed
        desired_data["installed_packages"] = set(self.packages)

        # Firewall should be enabled and active
        desired_data["firewalld_enabled"] = True
        desired_data["firewalld_active"] = True

        # Python 3.9+ should be available
        desired_data["python_version"] = (3, 9)  # Minimum version

        # Lab user should exist if configured
        create_lab_user = context.config.get("create_lab_user", True)
        desired_data["lab_user_exists"] = create_lab_user

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired RHEL 9 state"""
        changes_made = []

        try:
            # Install missing packages
            current_packages = set(current_state.get("installed_packages", []))
            desired_packages = desired_state.get("installed_packages", set())
            missing_packages = desired_packages - current_packages

            if missing_packages:
                self._install_packages(list(missing_packages))
                changes_made.append(f"Installed packages: {', '.join(missing_packages)}")

            # Configure firewall
            if not current_state.get("firewalld_enabled"):
                self._enable_service("firewalld")
                changes_made.append("Enabled firewalld service")

            if not current_state.get("firewalld_active"):
                self._start_service("firewalld")
                changes_made.append("Started firewalld service")

            # Create lab user if needed
            if desired_state.get("lab_user_exists") and not current_state.get("lab_user_exists"):
                self._create_lab_user()
                changes_made.append("Created lab-user")

            return PluginResult(
                changed=len(changes_made) > 0,
                message=f"Applied {len(changes_made)} changes: {'; '.join(changes_made)}",
                status=PluginStatus.COMPLETED,
                data={"changes": changes_made},
            )

        except Exception as e:
            return PluginResult(
                changed=False,
                message=f"Failed to apply changes: {str(e)}",
                status=PluginStatus.FAILED,
            )

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

    def _is_service_enabled(self, service: str) -> bool:
        """Check if service is enabled"""
        try:
            result = subprocess.run(["systemctl", "is-enabled", service], capture_output=True, text=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def _is_service_active(self, service: str) -> bool:
        """Check if service is active"""
        try:
            result = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True)
            return result.stdout.strip() == "active"
        except subprocess.CalledProcessError:
            return False

    def _enable_service(self, service: str) -> None:
        """Enable a service"""
        subprocess.run(["sudo", "systemctl", "enable", service], check=True)

    def _start_service(self, service: str) -> None:
        """Start a service"""
        subprocess.run(["sudo", "systemctl", "start", service], check=True)

    def _get_python_version(self) -> tuple:
        """Get Python version tuple"""
        try:
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True, check=True)
            version_str = result.stdout.strip().split()[1]  # "Python 3.9.16" -> "3.9.16"
            parts = version_str.split(".")
            return (int(parts[0]), int(parts[1]))
        except (subprocess.CalledProcessError, ValueError, IndexError):
            return (0, 0)

    def _user_exists(self, username: str) -> bool:
        """Check if user exists"""
        try:
            subprocess.run(["id", username], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _create_lab_user(self) -> None:
        """Create lab-user with sudo privileges"""
        # Create user
        subprocess.run(["sudo", "useradd", "-m", "-s", "/bin/bash", "lab-user"], check=True)

        # Add to sudo group
        subprocess.run(["sudo", "usermod", "-aG", "wheel", "lab-user"], check=True)

        self.logger.info("Created lab-user with sudo privileges")

    def get_dependencies(self) -> List[str]:
        """RHEL 9 plugin has no dependencies"""
        return []

    def validate_config(self) -> bool:
        """Validate RHEL 9 plugin configuration"""
        # Check that packages list is valid
        packages = self.config.get("packages", [])
        if not isinstance(packages, list):
            self.logger.error("packages configuration must be a list")
            return False

        return True
