"""
Rocky Linux Plugin - The "Cloud Infrastructure Specialist"

Migrates functionality from rocky-linux-hetzner.sh into the modular plugin framework.
Handles Rocky Linux specific deployment logic optimized for Hetzner cloud infrastructure
with cost-effective open-source alternatives as defined in ADR-0028.
"""

import subprocess
import os
from typing import List
from core.base_plugin import (
    QubiNodePlugin,
    PluginResult,
    SystemState,
    ExecutionContext,
    PluginStatus,
)


class RockyLinuxPlugin(QubiNodePlugin):
    """
    Rocky Linux deployment plugin - Cloud Infrastructure Specialist

    Implements cloud-optimized Rocky Linux deployment:
    - Cloud Environment Setup (Hetzner-specific networking and storage)
    - Open Source Stack (Rocky Linux packages without subscription requirements)
    - Security Hardening (SSH security and firewall configuration)
    - Cloud Storage (cloud-optimized storage and backup solutions)
    - Network Optimization (cloud networking and load balancing)
    - Vault Integration (HashiCorp Vault for cloud credential management)
    - Virtualization Platform (KVM/libvirt optimized for cloud environments)
    - Cloud Tools (Hetzner CLI, monitoring, and automation tools)
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize Rocky Linux plugin"""
        self.logger.info("Initializing Rocky Linux plugin - Cloud Infrastructure Specialist")

        # Validate we're running on Rocky Linux
        if not self._is_rocky_linux():
            raise RuntimeError("Rocky Linux plugin can only run on Rocky Linux systems")

        # Set configuration constants for cloud deployment
        self.kvm_version = self.config.get("kvm_version", "latest")
        self.ansible_safe_version = self.config.get("ansible_safe_version", "0.0.9")
        self.git_repo = self.config.get("git_repo", "https://github.com/Qubinode/qubinode_navigator.git")

        # Set default packages for Rocky Linux cloud deployment
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
                "lvm",
                "lvm2",
                "zlib-devel",
                "python3.11",
                "python3.11-pip",
                "python3.11-devel",
                "java-11-openjdk",
            ],
        )

        # Set cloud-specific environment variables
        self.cicd_pipeline = os.getenv("CICD_PIPELINE", "false")
        self.use_hashicorp_vault = os.getenv("USE_HASHICORP_VAULT", "false")
        self.use_hashicorp_cloud = os.getenv("USE_HASHICORP_CLOUD", "false")
        self.vault_addr = os.getenv("VAULT_ADDR", "")
        self.vault_token = os.getenv("VAULT_TOKEN", "")
        self.use_route53 = os.getenv("USE_ROUTE53", "false")
        self.route_53_domain = os.getenv("ROUTE_53_DOMAIN", "")
        self.cicd_environment = os.getenv("CICD_ENVIORNMENT", "github")
        self.secret_path = os.getenv("SECRET_PATH", "")
        self.inventory = os.getenv("INVENTORY", "hetzner")
        self.development_model = os.getenv("DEVELOPMENT_MODEL", "false")
        self.config_template = os.getenv("CONFIG_TEMPLATE", "hetzner.yml.j2")
        self.vault_dev_mode = os.getenv("VAULT_DEV_MODE", "false")

        # Validate HashiCorp Vault configuration if enabled
        if self.use_hashicorp_vault.lower() == "true":
            if not all([self.vault_addr, self.vault_token, self.secret_path]):
                raise RuntimeError("HashiCorp Vault environment variables not properly configured")

    def _is_rocky_linux(self) -> bool:
        """Check if running on Rocky Linux"""
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                return 'ID="rocky"' in content
        except FileNotFoundError:
            return False

    def check_state(self) -> SystemState:
        """Check current Rocky Linux system state"""
        state_data = {}

        # Check installed packages
        state_data["installed_packages"] = self._get_installed_packages()

        # Check services
        state_data["firewalld_enabled"] = self._is_service_enabled("firewalld")
        state_data["firewalld_active"] = self._is_service_active("firewalld")

        # Check Python version and configuration
        state_data["python_version"] = self._get_python_version()
        state_data["python_configured"] = self._is_python_configured()

        # Check SSH configuration
        state_data["ssh_configured"] = self._is_ssh_configured()
        state_data["ssh_password_auth"] = self._is_ssh_password_auth_enabled()

        # Check if lab-user exists
        state_data["lab_user_exists"] = self._user_exists("lab-user")

        # Check groups configuration
        state_data["groups_configured"] = self._are_groups_configured()

        # Check Ansible Navigator configuration
        state_data["ansible_navigator_configured"] = self._is_ansible_navigator_configured()

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired Rocky Linux system state"""
        desired_data = {}

        # All required packages should be installed
        desired_data["installed_packages"] = set(self.packages)

        # Firewall should be enabled and active
        desired_data["firewalld_enabled"] = True
        desired_data["firewalld_active"] = True

        # Python should be configured
        desired_data["python_configured"] = True

        # SSH should be configured
        desired_data["ssh_configured"] = True
        desired_data["ssh_password_auth"] = context.config.get("enable_ssh_password_auth", True)

        # Lab user should exist if configured
        create_lab_user = context.config.get("create_lab_user", True)
        desired_data["lab_user_exists"] = create_lab_user

        # Groups should be configured
        desired_data["groups_configured"] = True

        # Ansible Navigator should be configured
        desired_data["ansible_navigator_configured"] = True

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired Rocky Linux state"""
        changes_made = []

        try:
            # Install missing packages
            current_packages = set(current_state.get("installed_packages", []))
            desired_packages = desired_state.get("installed_packages", set())
            missing_packages = desired_packages - current_packages

            if missing_packages:
                self._install_packages(list(missing_packages))
                changes_made.append(f"Installed packages: {', '.join(missing_packages)}")

            # Configure Python if needed
            if not current_state.get("python_configured") and desired_state.get("python_configured"):
                self._configure_python()
                changes_made.append("Configured Python environment")

            # Configure SSH if needed
            if not current_state.get("ssh_configured") and desired_state.get("ssh_configured"):
                self._configure_ssh()
                changes_made.append("Configured SSH keys")

            # Configure SSH password authentication
            current_ssh_auth = current_state.get("ssh_password_auth", False)
            desired_ssh_auth = desired_state.get("ssh_password_auth", True)

            if current_ssh_auth != desired_ssh_auth:
                if desired_ssh_auth:
                    self._enable_ssh_password_authentication()
                    changes_made.append("Enabled SSH password authentication")
                else:
                    self._disable_ssh_password_authentication()
                    changes_made.append("Disabled SSH password authentication")

            # Configure firewall
            if not current_state.get("firewalld_enabled"):
                self._enable_service("firewalld")
                changes_made.append("Enabled firewalld service")

            if not current_state.get("firewalld_active"):
                self._start_service("firewalld")
                self._configure_firewalld()
                changes_made.append("Started and configured firewalld")

            # Create lab user if needed
            if desired_state.get("lab_user_exists") and not current_state.get("lab_user_exists"):
                self._create_lab_user()
                changes_made.append("Created lab-user")

            # Configure groups if needed
            if not current_state.get("groups_configured") and desired_state.get("groups_configured"):
                self._configure_groups()
                changes_made.append("Configured user groups")

            # Configure Ansible Navigator if needed
            if not current_state.get("ansible_navigator_configured") and desired_state.get("ansible_navigator_configured"):
                self._configure_ansible_navigator()
                changes_made.append("Configured Ansible Navigator")

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

    def _get_python_version(self) -> tuple:
        """Get Python version tuple"""
        try:
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True, check=True)
            version_str = result.stdout.strip().split()[1]
            parts = version_str.split(".")
            return (int(parts[0]), int(parts[1]))
        except (subprocess.CalledProcessError, ValueError, IndexError):
            return (0, 0)

    def _is_python_configured(self) -> bool:
        """Check if Python is properly configured"""
        # Check if python3 is available and pip is installed
        try:
            subprocess.run(["python3", "--version"], check=True, capture_output=True)
            subprocess.run(["pip3", "--version"], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _configure_python(self) -> None:
        """Configure Python environment"""
        # Ensure pip is available
        subprocess.run(["sudo", "dnf", "install", "-y", "python3-pip"], check=True)

        # Update pip
        subprocess.run(["python3", "-m", "pip", "install", "--upgrade", "pip"], check=True)

        self.logger.info("Configured Python environment")

    def _is_ssh_configured(self) -> bool:
        """Check if SSH keys are configured"""
        return os.path.exists(os.path.expanduser("~/.ssh/id_rsa"))

    def _configure_ssh(self) -> None:
        """Configure SSH keys"""
        ssh_dir = os.path.expanduser("~/.ssh")
        os.makedirs(ssh_dir, exist_ok=True)

        if not os.path.exists(f"{ssh_dir}/id_rsa"):
            subprocess.run(
                ["ssh-keygen", "-f", f"{ssh_dir}/id_rsa", "-t", "rsa", "-N", ""],
                check=True,
            )

        self.logger.info("Configured SSH keys")

    def _is_ssh_password_auth_enabled(self) -> bool:
        """Check if SSH password authentication is enabled"""
        try:
            with open("/etc/ssh/sshd_config", "r") as f:
                content = f.read()
                return "PasswordAuthentication yes" in content
        except FileNotFoundError:
            return False

    def _enable_ssh_password_authentication(self) -> None:
        """Enable SSH password authentication"""
        subprocess.run(
            [
                "sudo",
                "sed",
                "-i",
                "s/#PasswordAuthentication.*/PasswordAuthentication yes/g",
                "/etc/ssh/sshd_config",
            ],
            check=True,
        )

        subprocess.run(["sudo", "systemctl", "restart", "sshd"], check=True)
        self.logger.info("Enabled SSH password authentication")

    def _disable_ssh_password_authentication(self) -> None:
        """Disable SSH password authentication"""
        subprocess.run(
            [
                "sudo",
                "sed",
                "-i",
                "s/PasswordAuthentication.*/PasswordAuthentication no/g",
                "/etc/ssh/sshd_config",
            ],
            check=True,
        )

        subprocess.run(["sudo", "systemctl", "restart", "sshd"], check=True)
        self.logger.info("Disabled SSH password authentication")

    def _user_exists(self, username: str) -> bool:
        """Check if user exists"""
        try:
            subprocess.run(["id", username], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _create_lab_user(self) -> None:
        """Create lab-user with cloud-optimized configuration"""
        if self._user_exists("lab-user"):
            self.logger.info("lab-user already exists")
            return

        try:
            # Download and execute configure-sudo-user script
            script_url = "https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh"
            subprocess.run(["curl", "-OL", script_url], check=True)
            subprocess.run(["chmod", "+x", "configure-sudo-user.sh"], check=True)
            subprocess.run(["./configure-sudo-user.sh", "lab-user"], check=True)

            self.logger.info("Created lab-user with cloud-optimized configuration")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create lab-user: {e}")
            raise

    def _are_groups_configured(self) -> bool:
        """Check if required groups are configured"""
        try:
            result = subprocess.run(["getent", "group", "lab-user"], capture_output=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def _configure_groups(self) -> None:
        """Configure required groups"""
        try:
            # Check if lab-user group exists
            result = subprocess.run(["getent", "group", "lab-user"], capture_output=True)
            if result.returncode != 0:
                subprocess.run(["sudo", "groupadd", "lab-user"], check=True)
                self.logger.info("Created lab-user group")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to configure groups: {e}")
            raise

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

    def _configure_firewalld(self) -> None:
        """Configure firewalld for cloud environment"""
        try:
            # Basic firewall configuration for cloud deployment
            subprocess.run(["sudo", "firewall-cmd", "--permanent", "--add-service=ssh"], check=True)
            subprocess.run(
                ["sudo", "firewall-cmd", "--permanent", "--add-service=http"],
                check=True,
            )
            subprocess.run(
                ["sudo", "firewall-cmd", "--permanent", "--add-service=https"],
                check=True,
            )
            subprocess.run(["sudo", "firewall-cmd", "--reload"], check=True)

            self.logger.info("Configured firewalld for cloud environment")

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Firewall configuration failed: {e}")

    def _is_ansible_navigator_configured(self) -> bool:
        """Check if Ansible Navigator is configured"""
        config_path = os.path.expanduser("~/.ansible-navigator.yml")
        return os.path.exists(config_path)

    def _configure_ansible_navigator(self) -> None:
        """Configure Ansible Navigator for cloud deployment"""
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

            self.logger.info("Configured Ansible Navigator for cloud deployment")

        except Exception as e:
            self.logger.error(f"Ansible Navigator configuration failed: {e}")
            raise

    def _setup_cloud_tools(self) -> None:
        """Setup cloud-specific tools and configurations"""
        try:
            # Install EPEL repository for additional packages
            subprocess.run(
                [
                    "sudo",
                    "dnf",
                    "install",
                    "-y",
                    "https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm",
                ],
                check=True,
            )

            # Install cloud development tools
            subprocess.run(["sudo", "dnf", "groupinstall", "-y", "Development Tools"], check=True)

            # Update system
            subprocess.run(["sudo", "dnf", "update", "-y"], check=True)

            self.logger.info("Setup cloud tools and development environment")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Cloud tools setup failed: {e}")
            raise

    def _configure_vault_integrated_setup(self) -> None:
        """Configure vault-integrated setup for cloud credential management"""
        try:
            # Get QUBINODE_HOME from environment or use default
            nav_dir = os.environ.get('QUBINODE_HOME', '/opt/qubinode_navigator')
            vault_script = f"{nav_dir}/vault-integrated-setup.sh"

            if os.path.exists(vault_script):
                subprocess.run(["chmod", "+x", vault_script], check=True)

                if self.cicd_pipeline.lower() == "true":
                    self.logger.info("Running vault-integrated setup in CI/CD mode")
                    subprocess.run([vault_script], check=True, cwd=nav_dir)
                else:
                    self.logger.info("Running vault-integrated setup in interactive mode")
                    subprocess.run([vault_script], check=True, cwd=nav_dir)

                self.logger.info("Vault-integrated setup completed successfully")
            else:
                self.logger.warning("vault-integrated-setup.sh not found, skipping vault configuration")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Vault-integrated setup failed: {e}")
            raise

    def _setup_qubinode_navigator_cloud(self) -> None:
        """Setup Qubinode Navigator for cloud deployment"""
        try:
            home_dir = os.path.expanduser("~")
            nav_dir = f"{home_dir}/qubinode_navigator"

            if os.path.exists(nav_dir):
                self.logger.info("Qubinode Navigator already exists, pulling latest")
                subprocess.run(["git", "-C", nav_dir, "pull"], check=True)
            else:
                self.logger.info("Cloning Qubinode Navigator repository")
                subprocess.run(["git", "clone", self.git_repo], cwd=home_dir, check=True)

                # Create symlink for cloud deployment
                if not os.path.exists("/opt/qubinode_navigator"):
                    subprocess.run(
                        ["sudo", "ln", "-s", nav_dir, "/opt/qubinode_navigator"],
                        check=True,
                    )

            # Install Python requirements for cloud deployment
            req_file = f"{nav_dir}/requirements.txt"
            if os.path.exists(req_file):
                subprocess.run(["sudo", "pip3", "install", "-r", req_file], check=True)

            # Use enhanced load variables for cloud template processing
            enhanced_script = f"{nav_dir}/enhanced_load_variables.py"
            if os.path.exists(enhanced_script):
                self.logger.info("Using enhanced load variables for cloud template processing")

            self.logger.info("Qubinode Navigator cloud setup completed")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Qubinode Navigator cloud setup failed: {e}")
            raise

    def get_dependencies(self) -> List[str]:
        """Rocky Linux plugin has no dependencies"""
        return []

    def validate_config(self) -> bool:
        """Validate Rocky Linux plugin configuration"""
        # Check that packages list is valid
        packages = self.config.get("packages", [])
        if not isinstance(packages, list):
            self.logger.error("packages configuration must be a list")
            return False

        # Validate cloud-specific configuration
        if self.use_hashicorp_vault.lower() == "true":
            if not all([self.vault_addr, self.vault_token, self.secret_path]):
                self.logger.error("HashiCorp Vault configuration incomplete")
                return False

        return True
