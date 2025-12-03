#!/usr/bin/env python3
"""
Qubinode Navigator Bootstrap Assistant
Standalone AI-powered tool for guided infrastructure setup
"""

import asyncio
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests


@dataclass
class SystemEnvironment:
    """System environment information"""

    os_name: str
    os_version: str
    kernel_version: str
    cpu_cores: int
    total_memory_gb: float
    available_memory_gb: float
    disk_space_gb: float
    network_interfaces: List[str]
    virtualization_support: bool
    container_runtime: Optional[str]
    python_version: str
    architecture: str


@dataclass
class SetupStep:
    """Individual setup step"""

    id: str
    title: str
    description: str
    command: Optional[str]
    requires_input: bool
    prompt: Optional[str]
    validation: Optional[str]
    estimated_time: str
    difficulty: str


class EnvironmentDetector:
    """Detects system environment and capabilities"""

    def __init__(self):
        self.env = None

    async def scan_environment(self) -> SystemEnvironment:
        """Comprehensive environment scan"""

        print("🔍 Scanning system environment...")

        # Basic system info
        os_info = platform.uname()

        # Memory info
        memory = psutil.virtual_memory()

        # Disk info
        disk = psutil.disk_usage("/")

        # Network interfaces
        interfaces = list(psutil.net_if_addrs().keys())

        # Check virtualization support
        virt_support = self._check_virtualization_support()

        # Check container runtime
        container_runtime = self._detect_container_runtime()

        self.env = SystemEnvironment(
            os_name=os_info.system,
            os_version=self._get_os_version(),
            kernel_version=os_info.release,
            cpu_cores=psutil.cpu_count(),
            total_memory_gb=memory.total / (1024**3),
            available_memory_gb=memory.available / (1024**3),
            disk_space_gb=disk.free / (1024**3),
            network_interfaces=interfaces,
            virtualization_support=virt_support,
            container_runtime=container_runtime,
            python_version=platform.python_version(),
            architecture=platform.machine(),
        )

        return self.env

    def _get_os_version(self) -> str:
        """Get detailed OS version"""
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=")[1].strip().strip('"')
            return platform.platform()
        except:
            return platform.platform()

    def _check_virtualization_support(self) -> bool:
        """Check if system supports virtualization"""
        try:
            # Check for VT-x/AMD-V support
            result = subprocess.run(
                ["grep", "-E", "(vmx|svm)", "/proc/cpuinfo"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except:
            return False

    def _detect_container_runtime(self) -> Optional[str]:
        """Detect available container runtime"""
        runtimes = ["podman", "docker"]

        for runtime in runtimes:
            try:
                result = subprocess.run(
                    [runtime, "--version"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    return runtime
            except FileNotFoundError:
                continue

        return None


class LocalAI:
    """Lightweight local AI for bootstrap guidance"""

    def __init__(self):
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load lightweight knowledge base"""
        return {
            "rhel": {
                "min_memory": 8,
                "recommended_memory": 16,
                "required_packages": ["kvm", "libvirt", "virt-manager"],
                "common_issues": [
                    "SELinux blocking virtualization",
                    "Firewall blocking libvirt",
                    "Insufficient memory allocation",
                ],
            },
            "centos": {
                "min_memory": 8,
                "recommended_memory": 16,
                "required_packages": ["kvm", "libvirt", "virt-manager"],
                "stream_10_notes": "Latest CentOS Stream 10 requires updated kernel modules",
            },
            "ubuntu": {
                "min_memory": 8,
                "recommended_memory": 16,
                "required_packages": [
                    "qemu-kvm",
                    "libvirt-daemon-system",
                    "virt-manager",
                ],
                "common_issues": [
                    "AppArmor blocking virtualization",
                    "User not in libvirt group",
                ],
            },
        }

    async def analyze_environment(self, env: SystemEnvironment) -> Dict[str, Any]:
        """Analyze environment and provide guidance"""

        analysis = {
            "welcome_message": f"Welcome! I've detected {env.os_name} {env.os_version} with {env.cpu_cores} cores and {env.total_memory_gb:.1f}GB RAM.",
            "compatibility": self._check_compatibility(env),
            "recommendations": self._generate_recommendations(env),
            "setup_steps": self._generate_setup_steps(env),
            "warnings": self._identify_warnings(env),
        }

        return analysis

    def _check_compatibility(self, env: SystemEnvironment) -> Dict[str, Any]:
        """Check system compatibility"""

        compatible = True
        issues = []

        # Check minimum requirements
        if env.total_memory_gb < 8:
            compatible = False
            issues.append(
                f"Insufficient memory: {env.total_memory_gb:.1f}GB (minimum 8GB required)"
            )

        if env.cpu_cores < 2:
            compatible = False
            issues.append(
                f"Insufficient CPU cores: {env.cpu_cores} (minimum 2 required)"
            )

        if not env.virtualization_support:
            compatible = False
            issues.append("Virtualization support not detected (VT-x/AMD-V required)")

        if env.disk_space_gb < 50:
            issues.append(
                f"Low disk space: {env.disk_space_gb:.1f}GB (50GB+ recommended)"
            )

        return {
            "compatible": compatible,
            "issues": issues,
            "score": max(0, 100 - len(issues) * 25),
        }

    def _generate_recommendations(self, env: SystemEnvironment) -> List[str]:
        """Generate personalized recommendations"""

        recommendations = []

        # Memory recommendations
        if env.total_memory_gb < 16:
            recommendations.append(
                f"Consider upgrading RAM to 16GB+ for better VM performance"
            )
        elif env.total_memory_gb >= 32:
            recommendations.append(
                f"Excellent! {env.total_memory_gb:.1f}GB RAM allows for multiple VMs"
            )

        # Container runtime
        if not env.container_runtime:
            recommendations.append("Install Podman or Docker for container support")
        else:
            recommendations.append(
                f"Great! {env.container_runtime} detected for container orchestration"
            )

        # OS-specific recommendations
        os_lower = env.os_name.lower()
        if "red hat" in env.os_version.lower() or "rhel" in env.os_version.lower():
            recommendations.append(
                "RHEL detected - ensure subscription is active for package updates"
            )
        elif "centos" in env.os_version.lower():
            if "stream" in env.os_version.lower():
                recommendations.append("CentOS Stream detected - using latest packages")

        return recommendations

    def _generate_setup_steps(self, env: SystemEnvironment) -> List[SetupStep]:
        """Generate personalized setup steps"""

        steps = []

        # Step 1: System updates
        steps.append(
            SetupStep(
                id="system_update",
                title="Update System Packages",
                description="Ensure your system has the latest security updates and packages",
                command=self._get_update_command(env),
                requires_input=False,
                prompt=None,
                validation="rpm -qa | grep kernel",
                estimated_time="5-10 minutes",
                difficulty="easy",
            )
        )

        # Step 2: Install virtualization packages
        steps.append(
            SetupStep(
                id="install_virt",
                title="Install Virtualization Packages",
                description="Install KVM, libvirt, and related virtualization tools",
                command=self._get_virt_install_command(env),
                requires_input=False,
                prompt=None,
                validation="systemctl status libvirtd",
                estimated_time="10-15 minutes",
                difficulty="easy",
            )
        )

        # Step 3: Configure user permissions
        steps.append(
            SetupStep(
                id="user_permissions",
                title="Configure User Permissions",
                description="Add your user to the libvirt group for VM management",
                command=f"sudo usermod -a -G libvirt {os.getenv('USER', 'user')}",
                requires_input=False,
                prompt=None,
                validation="groups | grep libvirt",
                estimated_time="1 minute",
                difficulty="easy",
            )
        )

        # Step 4: Download Qubinode Navigator
        steps.append(
            SetupStep(
                id="download_qubinode",
                title="Download Qubinode Navigator",
                description="Clone the Qubinode Navigator repository",
                command="git clone https://github.com/Qubinode/qubinode_navigator.git",
                requires_input=True,
                prompt="Enter installation directory (default: /opt/qubinode)",
                validation="ls qubinode_navigator/README.md",
                estimated_time="2-5 minutes",
                difficulty="easy",
            )
        )

        # Step 5: Run initial setup
        steps.append(
            SetupStep(
                id="initial_setup",
                title="Run Qubinode Initial Setup",
                description="Execute the Qubinode Navigator setup script",
                command="cd qubinode_navigator && ./setup.sh",
                requires_input=True,
                prompt="Review configuration before proceeding? (y/n)",
                validation="qubinode-navigator --version",
                estimated_time="15-30 minutes",
                difficulty="intermediate",
            )
        )

        return steps

    def _get_update_command(self, env: SystemEnvironment) -> str:
        """Get appropriate system update command"""
        os_lower = env.os_version.lower()

        if "ubuntu" in os_lower or "debian" in os_lower:
            return "sudo apt update && sudo apt upgrade -y"
        elif (
            "rhel" in os_lower
            or "red hat" in os_lower
            or "centos" in os_lower
            or "fedora" in os_lower
        ):
            return "sudo dnf update -y"
        else:
            return "# Please update your system packages manually"

    def _get_virt_install_command(self, env: SystemEnvironment) -> str:
        """Get virtualization packages install command"""
        os_lower = env.os_version.lower()

        if "ubuntu" in os_lower or "debian" in os_lower:
            return "sudo apt install -y qemu-kvm libvirt-daemon-system virt-manager bridge-utils"
        elif (
            "rhel" in os_lower
            or "red hat" in os_lower
            or "centos" in os_lower
            or "fedora" in os_lower
        ):
            return "sudo dnf install -y qemu-kvm libvirt virt-manager virt-install bridge-utils"
        else:
            return "# Please install virtualization packages for your distribution"

    def _identify_warnings(self, env: SystemEnvironment) -> List[str]:
        """Identify potential issues or warnings"""

        warnings = []

        if env.available_memory_gb < 4:
            warnings.append("Low available memory - close unnecessary applications")

        if len(env.network_interfaces) < 2:
            warnings.append(
                "Only one network interface detected - consider adding bridge interface"
            )

        if not env.container_runtime:
            warnings.append(
                "No container runtime detected - some features may be limited"
            )

        return warnings


class BootstrapAssistant:
    """Main bootstrap assistant class"""

    def __init__(self):
        self.env_detector = EnvironmentDetector()
        self.local_ai = LocalAI()
        self.setup_progress = {}

    async def run_interactive_setup(self):
        """Run the interactive setup process"""

        print("🚀 Qubinode Navigator Bootstrap Assistant")
        print("=" * 50)

        # Detect environment
        env = await self.env_detector.scan_environment()

        # Get AI analysis
        analysis = await self.local_ai.analyze_environment(env)

        # Display welcome and analysis
        print(f"\n🤖 AI Assistant: {analysis['welcome_message']}")

        # Show compatibility check
        compatibility = analysis["compatibility"]
        if compatibility["compatible"]:
            print(f"✅ System Compatibility: {compatibility['score']}/100")
        else:
            print(f"❌ Compatibility Issues Found:")
            for issue in compatibility["issues"]:
                print(f"   • {issue}")

            if not self._confirm("Continue anyway? (not recommended)"):
                print("Setup cancelled. Please address compatibility issues first.")
                return

        # Show recommendations
        if analysis["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in analysis["recommendations"]:
                print(f"   • {rec}")

        # Show warnings
        if analysis["warnings"]:
            print(f"\n⚠️  Warnings:")
            for warning in analysis["warnings"]:
                print(f"   • {warning}")

        print(f"\n📋 Setup Plan ({len(analysis['setup_steps'])} steps):")
        for i, step in enumerate(analysis["setup_steps"], 1):
            print(f"   {i}. {step.title} ({step.estimated_time})")

        if not self._confirm("\nProceed with setup?"):
            print("Setup cancelled.")
            return

        # Execute setup steps
        await self._execute_setup_steps(analysis["setup_steps"])

        print("\n🎉 Bootstrap setup complete!")
        print("Next steps:")
        print("  1. Reboot your system to apply all changes")
        print("  2. Run 'qubinode-navigator --help' to see available commands")
        print("  3. Visit https://docs.qubinode.io for detailed documentation")

    async def _execute_setup_steps(self, steps: List[SetupStep]):
        """Execute setup steps with user interaction"""

        for i, step in enumerate(steps, 1):
            print(f"\n📋 Step {i}/{len(steps)}: {step.title}")
            print(f"💡 {step.description}")
            print(f"⏱️  Estimated time: {step.estimated_time}")

            if step.requires_input and step.prompt:
                user_input = input(f"➤ {step.prompt}: ")
                if step.id == "download_qubinode" and user_input.strip():
                    # Modify command with user's directory choice
                    install_dir = user_input.strip()
                    step.command = f"git clone https://github.com/Qubinode/qubinode_navigator.git {install_dir}/qubinode_navigator"

            if not self._confirm(f"Execute: {step.command}"):
                print("Step skipped.")
                continue

            # Execute command
            success = await self._execute_command(step.command)

            if success:
                print(f"✅ Step {i} completed successfully")
                self.setup_progress[step.id] = "completed"
            else:
                print(f"❌ Step {i} failed")
                self.setup_progress[step.id] = "failed"

                if not self._confirm("Continue with remaining steps?"):
                    break

            # Validation
            if step.validation:
                print(f"🔍 Validating: {step.validation}")
                validation_success = await self._execute_command(
                    step.validation, show_output=False
                )
                if validation_success:
                    print("✅ Validation passed")
                else:
                    print("⚠️  Validation failed - step may need manual verification")

    async def _execute_command(self, command: str, show_output: bool = True) -> bool:
        """Execute a shell command"""

        try:
            if show_output:
                print(f"🔧 Executing: {command}")

            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                if show_output and stdout:
                    print(stdout.decode().strip())
                return True
            else:
                if show_output:
                    print(f"Error: {stderr.decode().strip()}")
                return False

        except Exception as e:
            if show_output:
                print(f"Exception: {e}")
            return False

    def _confirm(self, message: str) -> bool:
        """Get user confirmation"""
        while True:
            response = input(f"{message} (y/n): ").lower().strip()
            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                print("Please enter 'y' or 'n'")


async def main():
    """Main entry point"""
    try:
        assistant = BootstrapAssistant()
        await assistant.run_interactive_setup()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
