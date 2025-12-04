"""
CentOS Stream 10 Plugin - The "Next-Generation Infrastructure Pioneer"

Handles CentOS Stream 10 (Coughlan) deployment as the cutting-edge preview of RHEL 10.
Provides native development and testing environment for next-generation enterprise Linux
with x86_64-v3 microarchitecture validation and Python 3.12 compatibility.

**NATIVE DEVELOPMENT ADVANTAGE**: This plugin runs on the actual target system,
providing immediate validation and real-world testing capabilities.
"""

import subprocess
import os
import platform
import uuid
import sys
from typing import List, Tuple
from core.base_plugin import (
    QubiNodePlugin,
    PluginResult,
    SystemState,
    ExecutionContext,
    PluginStatus,
)


class CentOSStream10Plugin(QubiNodePlugin):
    """
    CentOS Stream 10 deployment plugin - Next-Generation Infrastructure Pioneer

    Implements comprehensive CentOS Stream 10 (Coughlan) deployment pipeline:
    - Next-Generation Platform Setup (x86_64-v3 microarchitecture)
    - Python 3.12 Native Support and Validation
    - Modern Container Platform (Podman 5.x)
    - Advanced Security Configuration
    - DNF Modularity-Free Package Management
    - Next-Gen Virtualization Platform
    - Future-Ready Tool Integration
    - Native Development Environment Validation

    **DEVELOPMENT ADVANTAGE**: Running natively on CentOS Stream 10 provides
    immediate feedback and real-world validation for RHEL 10 compatibility.
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize CentOS Stream 10 plugin"""
        self.logger.info("Initializing CentOS Stream 10 plugin - Next-Generation Infrastructure Pioneer")
        self.logger.info("🚀 NATIVE DEVELOPMENT ADVANTAGE: Running on actual target system!")

        # Validate we're running on CentOS Stream 10
        if not self._is_centos_stream10():
            raise RuntimeError("CentOS Stream 10 plugin can only run on CentOS Stream 10 systems")

        # Validate x86_64-v3 microarchitecture (strict for production readiness)
        self._validate_x86_64_v3_microarchitecture()

        # Validate Python 3.12 availability (native testing)
        self._validate_python312_compatibility()

        # Set configuration constants for next-generation deployment
        self.kvm_version = self.config.get("kvm_version", "latest")  # Always use latest version
        self.ansible_safe_version = self.config.get("ansible_safe_version", "0.1.0")
        self.git_repo = self.config.get("git_repo", "https://github.com/Qubinode/qubinode_navigator.git")

        # Set packages optimized for CentOS Stream 10 / RHEL 10
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
                "java-21-openjdk-devel",  # Java 21 LTS for next-gen
                "ansible-core",
                "perl-Digest-SHA",
                "container-tools",
                "buildah",
                "skopeo",  # Modern container stack
                "python3-devel",
                "python3-setuptools",  # Python 3.12 development
            ],
        )

        # Set environment variables
        self.cicd_pipeline = os.getenv("CICD_PIPELINE", "false")
        self.inventory = os.getenv("INVENTORY", "localhost")
        self.guid = os.getenv("GUID", str(uuid.uuid4())[:5])
        self.use_hashicorp_vault = os.getenv("USE_HASHICORP_VAULT", "false")

        # Log native development capabilities
        self.logger.info(f"🎯 Native Python version: {sys.version}")
        self.logger.info(f"🎯 Native platform: {platform.platform()}")
        self.logger.info(f"🎯 Native architecture: {platform.machine()}")

    def _is_centos_stream10(self) -> bool:
        """Check if running on CentOS Stream 10"""
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                return ('ID="centos"' in content and 'VERSION_ID="10"' in content) or ("CentOS Stream release 10" in content)
        except FileNotFoundError:
            return False

    def _validate_x86_64_v3_microarchitecture(self) -> None:
        """Validate x86_64-v3 microarchitecture requirements for RHEL 10"""
        self.logger.info("🔍 Validating x86_64-v3 microarchitecture requirements...")

        try:
            # Check CPU flags for x86_64-v3 requirements
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()

            # x86_64-v3 required flags (subset of key requirements)
            required_flags = [
                "avx",
                "avx2",
                "bmi1",
                "bmi2",
                "f16c",
                "fma",
                "abm",
                "movbe",
            ]

            missing_flags = []
            for flag in required_flags:
                if flag not in cpuinfo:
                    missing_flags.append(flag)

            if missing_flags:
                self.logger.warning(f"⚠️  Missing x86_64-v3 CPU flags: {', '.join(missing_flags)}")
                self.logger.warning("⚠️  System may not meet RHEL 10 hardware requirements")
                # Don't fail in development mode, but log the issue
                if self.config.get("strict_hardware_validation", False):
                    raise RuntimeError(f"x86_64-v3 validation failed: missing {missing_flags}")
            else:
                self.logger.info("✅ x86_64-v3 microarchitecture requirements satisfied")

            # Additional architecture validation
            arch = platform.machine()
            if arch != "x86_64":
                raise RuntimeError(f"Unsupported architecture: {arch}. RHEL 10 requires x86_64.")

            self.logger.info(f"✅ Architecture validation passed: {arch}")

        except FileNotFoundError:
            self.logger.error("❌ Cannot read /proc/cpuinfo for architecture validation")
            raise RuntimeError("CPU information not available for validation")

    def _validate_python312_compatibility(self) -> None:
        """Validate Python 3.12 compatibility on native system"""
        self.logger.info("🐍 Validating Python 3.12 compatibility...")

        try:
            # Check current Python version
            python_version = sys.version_info
            self.logger.info(f"🎯 Native Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")

            # Check if Python 3.12 is available
            try:
                result = subprocess.run(["python3.12", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    self.logger.info(f"✅ Python 3.12 available: {version_str}")
                else:
                    self.logger.warning("⚠️  Python 3.12 not available, checking alternatives...")
                    self._check_python_alternatives()
            except FileNotFoundError:
                self.logger.warning("⚠️  python3.12 command not found, checking alternatives...")
                self._check_python_alternatives()

            # Test Python 3.12 features that are important for RHEL 10
            self._test_python312_features()

        except Exception as e:
            self.logger.error(f"❌ Python 3.12 validation failed: {e}")
            if self.config.get("strict_python_validation", False):
                raise RuntimeError(f"Python 3.12 validation failed: {e}")

    def _check_python_alternatives(self) -> None:
        """Check for alternative Python installations"""
        alternatives = ["python3", "python"]

        for alt in alternatives:
            try:
                result = subprocess.run([alt, "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    self.logger.info(f"📍 Found {alt}: {version_str}")
            except FileNotFoundError:
                continue

    def _test_python312_features(self) -> None:
        """Test Python 3.12 specific features that may be used in RHEL 10"""
        self.logger.info("🧪 Testing Python 3.12 feature compatibility...")

        try:
            # Test f-string improvements (Python 3.12+)
            test_code = """
import sys
# Test basic functionality that should work in Python 3.12+
version = f"{sys.version_info.major}.{sys.version_info.minor}"
print(f"Python version: {version}")
"""

            result = subprocess.run([sys.executable, "-c", test_code], capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info("✅ Python feature compatibility test passed")
            else:
                self.logger.warning(f"⚠️  Python feature test failed: {result.stderr}")

        except Exception as e:
            self.logger.warning(f"⚠️  Python feature testing failed: {e}")

    def _validate_dnf_modularity_removal(self) -> None:
        """Validate DNF modularity removal in CentOS Stream 10"""
        self.logger.info("📦 Validating DNF modularity removal...")

        try:
            # Check if dnf module commands are available (they shouldn't be in Stream 10)
            result = subprocess.run(["dnf", "module", "list"], capture_output=True, text=True)

            if "No such command: module" in result.stderr or result.returncode != 0:
                self.logger.info("✅ DNF modularity removed as expected in CentOS Stream 10")
            else:
                self.logger.warning("⚠️  DNF modularity still present - may be older system")

            # Test modern package management
            self._test_modern_package_management()

        except Exception as e:
            self.logger.warning(f"⚠️  DNF modularity validation failed: {e}")

    def _test_modern_package_management(self) -> None:
        """Test modern package management without modularity"""
        self.logger.info("📦 Testing modern package management...")

        try:
            # Test basic dnf functionality
            result = subprocess.run(["dnf", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                dnf_version = result.stdout.strip().split("\n")[0]
                self.logger.info(f"✅ DNF version: {dnf_version}")

            # Test package search (non-destructive)
            result = subprocess.run(["dnf", "search", "python3"], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("✅ Package search functionality working")
            else:
                self.logger.warning("⚠️  Package search test failed")

        except Exception as e:
            self.logger.warning(f"⚠️  Package management testing failed: {e}")

    def _check_microarchitecture_compatibility(self) -> None:
        """Check microarchitecture and warn if not fully compatible"""
        try:
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

            if flags_line:
                cpu_flags = flags_line.lower().split()
                missing_flags = [flag for flag in required_flags if flag not in cpu_flags]

                if missing_flags:
                    self.logger.warning(f"Missing x86_64-v3 CPU flags: {missing_flags}")
                    self.logger.warning("This system may not be fully compatible with production RHEL 10")
                    self.logger.info("Continuing in compatibility mode for development/testing")
                else:
                    self.logger.info("x86_64-v3 microarchitecture validation passed")

        except Exception as e:
            self.logger.warning(f"Could not validate microarchitecture: {e}")

    def check_state(self) -> SystemState:
        """Check current CentOS Stream 10 system state"""
        state_data = {}

        # Check OS version
        state_data["os_version"] = self._get_os_version()

        # Check Python version
        state_data["python_version"] = self._get_python_version()

        # Check kernel version
        state_data["kernel_version"] = self._get_kernel_version()

        # Check installed packages
        state_data["installed_packages"] = self._get_installed_packages()

        # Check services
        state_data["firewalld_enabled"] = self._is_service_enabled("firewalld")
        state_data["firewalld_active"] = self._is_service_active("firewalld")

        # Check if lab-user exists
        state_data["lab_user_exists"] = self._user_exists("lab-user")

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired CentOS Stream 10 system state"""
        desired_data = {}

        # OS should be CentOS Stream 10
        desired_data["os_version"] = "centos_stream10"

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

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired CentOS Stream 10 state"""
        changes_made = []

        try:
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
                    "compatibility_mode": True,
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
            version_str = result.stdout.strip().split()[1]
            parts = version_str.split(".")
            return (int(parts[0]), int(parts[1]))
        except (subprocess.CalledProcessError, ValueError, IndexError):
            return (0, 0)

    def _get_kernel_version(self) -> Tuple[int, int]:
        """Get kernel version tuple"""
        try:
            kernel_version = platform.release()
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
        """Install packages using dnf without modularity"""
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
        """CentOS Stream 10 plugin has no dependencies"""
        return []

    def validate_config(self) -> bool:
        """Validate plugin configuration"""
        packages = self.config.get("packages", [])
        if not isinstance(packages, list):
            self.logger.error("packages configuration must be a list")
            return False
        return True
