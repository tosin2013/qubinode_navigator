"""
RHEL 10/CentOS Stream 10 Plugin

Handles RHEL 10 and CentOS Stream 10 specific deployment logic addressing
the breaking changes identified in ADR-0026 and the PRD analysis.
"""

import subprocess
import platform
from typing import Dict, Any, List, Tuple
from core.base_plugin import (
    QubiNodePlugin,
    PluginResult,
    SystemState,
    ExecutionContext,
    PluginStatus,
)


class RHEL10Plugin(QubiNodePlugin):
    """
    RHEL 10/CentOS Stream 10 deployment plugin

    Addresses critical compatibility issues:
    - x86_64-v3 microarchitecture requirement
    - Python 3.12 as default
    - DNF modularity removal
    - Linux kernel 6.12
    - Removed packages (Xorg server, LibreOffice, GIMP, Redis)
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize RHEL 10/CentOS Stream 10 plugin"""
        self.logger.info("Initializing RHEL 10/CentOS Stream 10 plugin")

        # Validate we're running on RHEL 10 or CentOS Stream 10
        if not self._is_rhel10_or_centos10():
            raise RuntimeError("RHEL 10 plugin can only run on RHEL 10 or CentOS Stream 10 systems")

        # Validate x86_64-v3 microarchitecture
        if not self._validate_microarchitecture():
            raise RuntimeError("System does not meet x86_64-v3 microarchitecture requirement for RHEL 10/CentOS 10")

        # Set packages adapted for RHEL 10/CentOS 10 (no modularity)
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
                "java-21-openjdk-devel",  # Updated to Java 21 for RHEL 10
                "ansible-core",
                "perl-Digest-SHA",
                # Note: Removed packages that are no longer available in RHEL 10
            ],
        )

    def _is_rhel10_or_centos10(self) -> bool:
        """Check if running on RHEL 10 or CentOS Stream 10"""
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                # Check for RHEL 10
                if 'ID="rhel"' in content and 'VERSION_ID="10' in content:
                    return True
                # Check for CentOS Stream 10
                if ('ID="centos"' in content and 'VERSION_ID="10"' in content) or ("CentOS Stream release 10" in content):
                    return True
                return False
        except FileNotFoundError:
            return False

    def _validate_microarchitecture(self) -> bool:
        """
        Validate x86_64-v3 microarchitecture requirement

        RHEL 10/CentOS 10 requires x86_64-v3 which includes:
        - AVX, AVX2, BMI1, BMI2, F16C, FMA, LZCNT, MOVBE, XSAVE
        """
        try:
            # Check CPU flags for x86_64-v3 requirements
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()

            required_flags = [
                "avx",
                "avx2",
                "bmi1",
                "bmi2",
                "f16c",
                "fma",
                "lzcnt",
                "movbe",
                "xsave",
            ]

            flags_line = None
            for line in cpuinfo.split("\n"):
                if line.startswith("flags"):
                    flags_line = line
                    break

            if not flags_line:
                self.logger.warning("Could not read CPU flags from /proc/cpuinfo")
                return False

            cpu_flags = flags_line.lower().split()
            missing_flags = [flag for flag in required_flags if flag not in cpu_flags]

            if missing_flags:
                self.logger.error(f"Missing x86_64-v3 CPU flags: {missing_flags}")
                return False

            self.logger.info("x86_64-v3 microarchitecture validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to validate microarchitecture: {e}")
            return False

    def check_state(self) -> SystemState:
        """Check current RHEL 10/CentOS Stream 10 system state"""
        state_data = {}

        # Check OS version
        state_data["os_version"] = self._get_os_version()

        # Check Python version (should be 3.12+ for RHEL 10)
        state_data["python_version"] = self._get_python_version()

        # Check kernel version (should be 6.12+ for RHEL 10)
        state_data["kernel_version"] = self._get_kernel_version()

        # Check installed packages
        state_data["installed_packages"] = self._get_installed_packages()

        # Check services
        state_data["firewalld_enabled"] = self._is_service_enabled("firewalld")
        state_data["firewalld_active"] = self._is_service_active("firewalld")

        # Check if lab-user exists
        state_data["lab_user_exists"] = self._user_exists("lab-user")

        # Check microarchitecture
        state_data["microarch_valid"] = self._validate_microarchitecture()

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired RHEL 10/CentOS Stream 10 system state"""
        desired_data = {}

        # OS should be RHEL 10 or CentOS Stream 10
        desired_data["os_version"] = "rhel10_or_centos10"

        # Python should be 3.12+
        desired_data["python_version"] = (3, 12)

        # Kernel should be 6.x+
        desired_data["kernel_version"] = (6, 0)

        # All required packages should be installed
        desired_data["installed_packages"] = set(self.packages)

        # Firewall should be enabled and active
        desired_data["firewalld_enabled"] = True
        desired_data["firewalld_active"] = True

        # Lab user should exist if configured
        create_lab_user = context.config.get("create_lab_user", True)
        desired_data["lab_user_exists"] = create_lab_user

        # Microarchitecture must be valid
        desired_data["microarch_valid"] = True

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired RHEL 10/CentOS Stream 10 state"""
        changes_made = []

        try:
            # Validate microarchitecture first (blocking requirement)
            if not current_state.get("microarch_valid"):
                return PluginResult(
                    changed=False,
                    message="System does not meet x86_64-v3 microarchitecture requirement",
                    status=PluginStatus.FAILED,
                )

            # Validate Python version
            current_python = current_state.get("python_version", (0, 0))
            required_python = desired_state.get("python_version", (3, 12))

            if current_python < required_python:
                return PluginResult(
                    changed=False,
                    message=f"Python {required_python[0]}.{required_python[1]}+ required, found {current_python[0]}.{current_python[1]}",
                    status=PluginStatus.FAILED,
                )

            # Install missing packages (using dnf without modularity)
            current_packages = set(current_state.get("installed_packages", []))
            desired_packages = desired_state.get("installed_packages", set())
            missing_packages = desired_packages - current_packages

            if missing_packages:
                self._install_packages_no_modularity(list(missing_packages))
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
                data={
                    "changes": changes_made,
                    "os_version": current_state.get("os_version"),
                    "python_version": current_state.get("python_version"),
                    "kernel_version": current_state.get("kernel_version"),
                },
            )

        except Exception as e:
            return PluginResult(
                changed=False,
                message=f"Failed to apply changes: {str(e)}",
                status=PluginStatus.FAILED,
            )

    def _get_os_version(self) -> str:
        """Get OS version string"""
        try:
            with open("/etc/redhat-release", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "Unknown"

    def _get_python_version(self) -> Tuple[int, int]:
        """Get Python version tuple"""
        try:
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True, check=True)
            version_str = result.stdout.strip().split()[1]  # "Python 3.12.1" -> "3.12.1"
            parts = version_str.split(".")
            return (int(parts[0]), int(parts[1]))
        except (subprocess.CalledProcessError, ValueError, IndexError):
            return (0, 0)

    def _get_kernel_version(self) -> Tuple[int, int]:
        """Get kernel version tuple"""
        try:
            kernel_version = platform.release()  # e.g., "6.12.0-1.el10.x86_64"
            parts = kernel_version.split(".")
            return (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return (0, 0)

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

    def _install_packages_no_modularity(self, packages: List[str]) -> None:
        """
        Install packages using dnf without modularity

        RHEL 10/CentOS 10 removed DNF modularity, so we use standard dnf install
        """
        cmd = ["sudo", "dnf", "install", "-y"] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Package installation failed: {result.stderr}")

        self.logger.info(f"Installed packages without modularity: {', '.join(packages)}")

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

        # Add to sudo group (wheel group in RHEL/CentOS)
        subprocess.run(["sudo", "usermod", "-aG", "wheel", "lab-user"], check=True)

        self.logger.info("Created lab-user with sudo privileges")

    def get_dependencies(self) -> List[str]:
        """RHEL 10 plugin has no dependencies"""
        return []

    def validate_config(self) -> bool:
        """Validate RHEL 10 plugin configuration"""
        # Check that packages list is valid
        packages = self.config.get("packages", [])
        if not isinstance(packages, list):
            self.logger.error("packages configuration must be a list")
            return False

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status with RHEL 10 specific info"""
        base_status = super().get_health_status()

        # Add RHEL 10 specific status
        base_status.update(
            {
                "os_compatible": self._is_rhel10_or_centos10(),
                "microarch_valid": self._validate_microarchitecture(),
                "python_version": self._get_python_version(),
                "kernel_version": self._get_kernel_version(),
            }
        )

        return base_status
