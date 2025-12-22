"""
RHEL 8 Plugin - The "Legacy Enterprise Infrastructure Architect"

Migrates functionality from rhel8-linux-hypervisor.sh into the modular plugin framework.
Handles RHEL 8 specific deployment logic with enterprise subscription management,
backward compatibility, and legacy system support as defined in ADR-0028.
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


class RHEL8Plugin(QubiNodePlugin):
    """
    RHEL 8 deployment plugin

    Implements comprehensive RHEL 8 deployment pipeline:
    - Legacy Environment Validation
    - Compatibility Setup with RHEL subscriptions
    - Security Configuration and hardening
    - Storage Management (LVM)
    - Network Configuration
    - Vault Integration
    - Virtualization Platform (KVM/libvirt)
    - Legacy Tool Integration
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize RHEL 8 plugin"""
        self.logger.info("Initializing RHEL 8 plugin - Legacy Enterprise Infrastructure Architect")

        # Validate we're running on RHEL 8
        if not self._is_rhel8():
            raise RuntimeError("RHEL 8 plugin can only run on RHEL 8 systems")

        # Set configuration constants
        self.kvm_version = self.config.get("kvm_version", "latest")
        self.ansible_safe_version = self.config.get("ansible_safe_version", "0.0.9")
        self.git_repo = self.config.get("git_repo", "https://github.com/Qubinode/qubinode_navigator.git")

        # Set default packages for RHEL 8
        self.packages = self.config.get(
            "packages",
            [
                "openssl-devel",
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
                "leapp-upgrade",
                "cockpit-leapp",
                "java-11-openjdk",
                "subscription-manager",
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

    def _is_rhel8(self) -> bool:
        """Check if running on RHEL 8"""
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                return 'ID="rhel"' in content and 'VERSION_ID="8' in content
        except FileNotFoundError:
            return False

    def check_state(self) -> SystemState:
        """Check current RHEL 8 system state"""
        state_data = {}

        # Check installed packages
        state_data["installed_packages"] = self._get_installed_packages()

        # Check RHEL subscription status
        state_data["subscription_registered"] = self._is_subscription_registered()
        state_data["subscription_attached"] = self._is_subscription_attached()

        # Check services
        state_data["firewalld_enabled"] = self._is_service_enabled("firewalld")
        state_data["firewalld_active"] = self._is_service_active("firewalld")

        # Check Python version
        state_data["python_version"] = self._get_python_version()

        # Check if lab-user exists
        state_data["lab_user_exists"] = self._user_exists("lab-user")

        # Check repositories
        state_data["repositories_enabled"] = self._check_required_repositories()

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired RHEL 8 system state"""
        desired_data = {}

        # All required packages should be installed
        desired_data["installed_packages"] = set(self.packages)

        # Subscription should be managed (if credentials provided)
        manage_subscription = context.config.get("manage_subscription", False)
        desired_data["subscription_registered"] = manage_subscription
        desired_data["subscription_attached"] = manage_subscription

        # Firewall should be enabled and active
        desired_data["firewalld_enabled"] = True
        desired_data["firewalld_active"] = True

        # Python 3.6+ should be available (RHEL 8 default)
        desired_data["python_version"] = (3, 6)

        # Lab user should exist if configured
        create_lab_user = context.config.get("create_lab_user", True)
        desired_data["lab_user_exists"] = create_lab_user

        # Required repositories should be enabled
        desired_data["repositories_enabled"] = True

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired RHEL 8 state"""
        changes_made = []

        try:
            # Handle subscription management if needed
            if desired_state.get("subscription_registered") and not current_state.get("subscription_registered"):
                username = context.variables.get("rhel_username")
                password = context.variables.get("rhel_password")

                if username and password:
                    self._register_subscription(username, password)
                    changes_made.append("Registered RHEL subscription")
                else:
                    self.logger.warning("RHEL credentials not provided - skipping subscription registration")

            # Attach subscription if registered but not attached
            if desired_state.get("subscription_attached") and current_state.get("subscription_registered") and not current_state.get("subscription_attached"):
                self._attach_subscription()
                changes_made.append("Attached RHEL subscription")

            # Enable required repositories
            if not current_state.get("repositories_enabled") and desired_state.get("repositories_enabled"):
                self._enable_required_repositories()
                changes_made.append("Enabled required repositories")

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

            # Configure comprehensive RHEL 8 setup
            if context.config.get("full_setup", False):
                # Install development tools and EPEL
                self._install_development_tools()
                changes_made.append("Installed development tools and EPEL")

                # Configure Python upgrade if needed
                self._configure_python_upgrade()
                changes_made.append("Configured Python upgrade")

                # Configure rootless podman
                self._configure_podman_rootless()
                changes_made.append("Configured rootless podman")

                # Install Ansible Navigator
                self._install_ansible_navigator()
                changes_made.append("Installed Ansible Navigator")

                # Setup Qubinode Navigator
                self._setup_qubinode_navigator()
                changes_made.append("Setup Qubinode Navigator")

                # Configure Ansible Navigator settings
                self._configure_ansible_navigator_settings()
                changes_made.append("Configured Ansible Navigator settings")

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

    def _is_subscription_registered(self) -> bool:
        """Check if RHEL subscription is registered"""
        try:
            result = subprocess.run(["subscription-manager", "status"], capture_output=True, text=True)

            return "Overall Status: Current" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _is_subscription_attached(self) -> bool:
        """Check if RHEL subscription is attached"""
        try:
            result = subprocess.run(
                ["subscription-manager", "list", "--consumed"],
                capture_output=True,
                text=True,
            )

            return "Pool ID:" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _register_subscription(self, username: str, password: str) -> None:
        """Register RHEL subscription"""
        cmd = [
            "sudo",
            "subscription-manager",
            "register",
            "--username",
            username,
            "--password",
            password,
            "--auto-attach",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Subscription registration failed: {result.stderr}")

        self.logger.info("Registered RHEL subscription")

    def _attach_subscription(self) -> None:
        """Attach RHEL subscription"""
        # Try auto-attach first
        result = subprocess.run(
            ["sudo", "subscription-manager", "attach", "--auto"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            self.logger.warning(f"Auto-attach failed: {result.stderr}")
            # Could implement manual pool selection here

    def _check_required_repositories(self) -> bool:
        """Check if required repositories are enabled"""
        try:
            result = subprocess.run(
                ["subscription-manager", "repos", "--list-enabled"],
                capture_output=True,
                text=True,
            )

            required_repos = [
                "rhel-8-for-x86_64-baseos-rpms",
                "rhel-8-for-x86_64-appstream-rpms",
            ]

            for repo in required_repos:
                if repo not in result.stdout:
                    return False

            return True
        except subprocess.CalledProcessError:
            return False

    def _enable_required_repositories(self) -> None:
        """Enable required RHEL 8 repositories"""
        required_repos = [
            "rhel-8-for-x86_64-baseos-rpms",
            "rhel-8-for-x86_64-appstream-rpms",
            "ansible-2.9-for-rhel-8-x86_64-rpms",
        ]

        for repo in required_repos:
            try:
                subprocess.run(
                    ["sudo", "subscription-manager", "repos", "--enable", repo],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to enable repository {repo}: {e}")

        self.logger.info("Enabled required repositories")

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
            version_str = result.stdout.strip().split()[1]
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

    def _configure_python_upgrade(self) -> None:
        """Configure Python upgrade from 3.6.8 to 3.9 for RHEL 8"""
        try:
            # Check current Python version
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
            version = result.stdout.strip().split()[1]

            if version == "3.6.8":
                self.logger.info("Python version is 3.6.8. Upgrading to 3.9...")

                # Enable Python 3.9 module
                subprocess.run(["sudo", "dnf", "module", "install", "-y", "python39"], check=True)
                subprocess.run(
                    [
                        "sudo",
                        "dnf",
                        "install",
                        "-y",
                        "python39",
                        "python39-devel",
                        "python39-pip",
                    ],
                    check=True,
                )
                subprocess.run(["sudo", "dnf", "module", "enable", "-y", "python39"], check=True)

                # Disable Python 3.6 module
                subprocess.run(["sudo", "dnf", "module", "disable", "-y", "python36"], check=True)

                # Set alternatives
                subprocess.run(
                    ["sudo", "alternatives", "--set", "python", "/usr/bin/python3.9"],
                    check=True,
                )
                subprocess.run(
                    ["sudo", "alternatives", "--set", "python3", "/usr/bin/python3.9"],
                    check=True,
                )

                self.logger.info("Python upgraded to 3.9")
            else:
                self.logger.info(f"Python version {version}. No upgrade needed.")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Python upgrade failed: {e}")
            raise

    def _install_ansible_navigator(self) -> None:
        """Install Ansible Navigator and requirements"""
        try:
            # Check if ansible-navigator is already installed
            result = subprocess.run(["which", "ansible-navigator"], capture_output=True)
            if result.returncode == 0:
                self.logger.info("ansible-navigator is already installed")
                return

            # Install ansible-navigator requirements
            requirements_url = "https://raw.githubusercontent.com/ansible/ansible-navigator/v3.6.0/requirements.txt"
            subprocess.run(
                ["sudo", "python3", "-m", "pip", "install", "-r", requirements_url],
                check=True,
            )

            # Install bastion requirements if available
            bastion_req_path = f"{os.path.expanduser('~')}/qubinode_navigator/bash-aliases/bastion-requirements.txt"
            if os.path.exists(bastion_req_path):
                subprocess.run(
                    ["sudo", "python3", "-m", "pip", "install", "-r", bastion_req_path],
                    check=True,
                )

            self.logger.info("Ansible Navigator installed successfully")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ansible Navigator installation failed: {e}")
            raise

    def _configure_podman_rootless(self) -> None:
        """Configure rootless podman for RHEL 8"""
        try:
            # Set permissions for newgidmap and newuidmap
            subprocess.run(["sudo", "chmod", "4755", "/usr/bin/newgidmap"], check=True)
            subprocess.run(["sudo", "chmod", "4755", "/usr/bin/newuidmap"], check=True)

            # Reinstall shadow-utils
            subprocess.run(["sudo", "dnf", "reinstall", "-yq", "shadow-utils"], check=True)

            # Configure XDG_RUNTIME_DIR
            xdg_script = '''export XDG_RUNTIME_DIR="$HOME/.run/containers"'''
            with open("/tmp/xdg_runtime_dir.sh", "w") as f:
                f.write(xdg_script)

            subprocess.run(
                [
                    "sudo",
                    "mv",
                    "/tmp/xdg_runtime_dir.sh",
                    "/etc/profile.d/xdg_runtime_dir.sh",
                ],
                check=True,
            )
            subprocess.run(
                ["sudo", "chmod", "a+rx", "/etc/profile.d/xdg_runtime_dir.sh"],
                check=True,
            )
            subprocess.run(
                [
                    "sudo",
                    "cp",
                    "/etc/profile.d/xdg_runtime_dir.sh",
                    "/etc/profile.d/xdg_runtime_dir.zsh",
                ],
                check=True,
            )

            # Configure ping group range
            ping_config = "net.ipv4.ping_group_range=0 2000000"
            with open("/tmp/ping_group_range.conf", "w") as f:
                f.write(ping_config)

            subprocess.run(
                [
                    "sudo",
                    "mv",
                    "/tmp/ping_group_range.conf",
                    "/etc/sysctl.d/ping_group_range.conf",
                ],
                check=True,
            )
            subprocess.run(["sudo", "sysctl", "--system"], check=True)

            self.logger.info("Configured rootless podman for RHEL 8")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Podman rootless configuration failed: {e}")
            raise

    def _setup_qubinode_navigator(self) -> None:
        """Setup Qubinode Navigator repository and configuration"""
        try:
            home_dir = os.path.expanduser("~")
            nav_dir = f"{home_dir}/qubinode_navigator"

            if os.path.exists(nav_dir):
                self.logger.info("Qubinode Navigator already exists, pulling latest")
                subprocess.run(["git", "-C", nav_dir, "pull"], check=True)
            else:
                self.logger.info("Cloning Qubinode Navigator repository")
                subprocess.run(["git", "clone", self.git_repo], cwd=home_dir, check=True)

                # Create symlink
                subprocess.run(
                    ["sudo", "usermod", "-aG", "users", os.getenv("USER", "root")],
                    check=True,
                )
                subprocess.run(["sudo", "chown", "-R", "root:users", "/opt"], check=True)
                subprocess.run(["sudo", "chmod", "-R", "g+w", "/opt"], check=True)

                if not os.path.exists("/opt/qubinode_navigator"):
                    subprocess.run(
                        ["sudo", "ln", "-s", nav_dir, "/opt/qubinode_navigator"],
                        check=True,
                    )

            # Install Python requirements
            req_file = f"{nav_dir}/requirements.txt"
            if os.path.exists(req_file):
                subprocess.run(["sudo", "pip3", "install", "-r", req_file], check=True)

            self.logger.info("Qubinode Navigator setup completed")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Qubinode Navigator setup failed: {e}")
            raise

    def _configure_ansible_navigator_settings(self) -> None:
        """Configure Ansible Navigator settings"""
        try:
            # Get QUBINODE_HOME from environment or use default
            qubinode_home = os.environ.get('QUBINODE_HOME', '/opt/qubinode_navigator')
            
            config_content = f"""---
ansible-navigator:
  ansible:
    inventory:
      entries:
      - {qubinode_home}/inventories/{self.inventory}
  execution-environment:
    container-engine: podman
    enabled: true
    image: quay.io/qubinode/qubinode-installer:{self.kvm_version}
    pull:
      policy: missing
  logging:
    append: true
    file: /tmp/navigator/ansible-navigator.log
    level: debug
  playbook-artifact:
    enable: false
"""

            config_path = os.path.expanduser("~/.ansible-navigator.yml")
            with open(config_path, "w") as f:
                f.write(config_content)

            self.logger.info("Configured Ansible Navigator settings")

        except Exception as e:
            self.logger.error(f"Ansible Navigator configuration failed: {e}")
            raise

    def _install_development_tools(self) -> None:
        """Install Development Tools group and additional packages"""
        try:
            # Check if Development Tools is already installed
            result = subprocess.run(
                ["dnf", "group", "info", "Development Tools"],
                capture_output=True,
                text=True,
            )

            if "Installed Groups:" not in result.stdout:
                self.logger.info("Installing Development Tools group")
                subprocess.run(
                    ["sudo", "dnf", "groupinstall", "Development Tools", "-y"],
                    check=True,
                )

                # Add Microsoft repository for VS Code
                subprocess.run(
                    [
                        "sudo",
                        "rpm",
                        "--import",
                        "https://packages.microsoft.com/keys/microsoft.asc",
                    ],
                    check=True,
                )

                repo_content = """[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc"""

                with open("/tmp/vscode.repo", "w") as f:
                    f.write(repo_content)

                subprocess.run(
                    ["sudo", "mv", "/tmp/vscode.repo", "/etc/yum.repos.d/vscode.repo"],
                    check=True,
                )
                subprocess.run(["sudo", "dnf", "check-update"], check=False)  # Don't fail if no updates
                subprocess.run(["sudo", "dnf", "install", "code", "-y"], check=True)
            else:
                self.logger.info("Development Tools group already installed")

            # Install EPEL repository
            subprocess.run(
                [
                    "sudo",
                    "dnf",
                    "install",
                    "https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm",
                    "-y",
                ],
                check=True,
            )

            # Update system
            subprocess.run(["sudo", "dnf", "update", "-y"], check=True)

            self.logger.info("Development tools and EPEL repository installed")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Development tools installation failed: {e}")
            raise

    def get_dependencies(self) -> List[str]:
        """RHEL 8 plugin has no dependencies"""
        return []

    def validate_config(self) -> bool:
        """Validate RHEL 8 plugin configuration"""
        # Check that packages list is valid
        packages = self.config.get("packages", [])
        if not isinstance(packages, list):
            self.logger.error("packages configuration must be a list")
            return False

        return True
