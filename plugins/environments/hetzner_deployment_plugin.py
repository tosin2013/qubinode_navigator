"""
Hetzner Deployment Plugin

Handles Hetzner-specific deployment workflow including lab-user creation,
SSH configuration, and integration with config files.
Migrates functionality from demo-hetzner-com.markdown deployment guide.
"""

import subprocess
import os
from typing import Dict, Any, List
from core.base_plugin import (
    QubiNodePlugin,
    PluginResult,
    SystemState,
    ExecutionContext,
    PluginStatus,
)


class HetznerDeploymentPlugin(QubiNodePlugin):
    """
    Hetzner Deployment workflow plugin

    Handles the complete Hetzner deployment workflow:
    - Lab-user creation using configure-sudo-user.sh
    - SSH key configuration and setup
    - Config file validation and setup
    - Environment file configuration
    - Rocky Linux specific optimizations for Hetzner
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize Hetzner Deployment plugin"""
        self.logger.info("Initializing Hetzner Deployment plugin")

        # Hetzner deployment specific configuration
        self.configure_script_url = self.config.get(
            "configure_script_url",
            "https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh",
        )

        self.required_packages = self.config.get("required_packages", ["curl", "wget", "git", "vim", "openssh-clients"])

    def check_state(self) -> SystemState:
        """Check current Hetzner deployment state"""
        state_data = {}

        # Check if we're on Hetzner (basic detection)
        state_data["is_hetzner"] = self._is_hetzner_environment()

        # Check if lab-user exists
        state_data["lab_user_exists"] = self._user_exists("lab-user")

        # Check if lab-user has sudo privileges
        state_data["lab_user_sudo"] = self._user_has_sudo("lab-user")

        # Check SSH configuration for lab-user
        state_data["lab_user_ssh_configured"] = self._is_lab_user_ssh_configured()

        # Check if config files exist and are valid
        state_data["config_yml_exists"] = os.path.exists("/tmp/config.yml")
        state_data["notouch_env_exists"] = os.path.exists("notouch.env")

        # Check if configure script is available
        state_data["configure_script_available"] = os.path.exists("./configure-sudo-user.sh")

        # Check required packages
        state_data["required_packages_installed"] = self._check_required_packages()

        # Check if we're running as root (needed for initial setup)
        state_data["running_as_root"] = os.geteuid() == 0

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired Hetzner deployment state"""
        desired_data = {}

        # Should be configured for Hetzner deployment
        desired_data["is_hetzner"] = True

        # Lab-user should exist with sudo privileges
        desired_data["lab_user_exists"] = True
        desired_data["lab_user_sudo"] = True

        # SSH should be configured for lab-user
        desired_data["lab_user_ssh_configured"] = True

        # Config files should exist (we'll validate they're pre-loaded)
        desired_data["config_yml_exists"] = True
        desired_data["notouch_env_exists"] = True

        # Configure script should be available
        desired_data["configure_script_available"] = True

        # Required packages should be installed
        desired_data["required_packages_installed"] = True

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired Hetzner deployment state"""
        changes_made = []

        try:
            # Verify we're running as root for initial setup
            if not current_state.get("running_as_root"):
                return PluginResult(
                    changed=False,
                    message="Hetzner deployment setup must be run as root initially",
                    status=PluginStatus.FAILED,
                )

            # Install required packages if needed
            if not current_state.get("required_packages_installed"):
                self._install_required_packages()
                changes_made.append("Installed required packages")

            # Download configure script if not available
            if not current_state.get("configure_script_available"):
                self._download_configure_script()
                changes_made.append("Downloaded configure-sudo-user.sh script")

            # Create lab-user if it doesn't exist
            if not current_state.get("lab_user_exists"):
                self._create_lab_user()
                changes_made.append("Created lab-user using configure-sudo-user.sh")

            # Ensure lab-user has sudo privileges
            if current_state.get("lab_user_exists") and not current_state.get("lab_user_sudo"):
                self._ensure_lab_user_sudo()
                changes_made.append("Ensured lab-user has sudo privileges")

            # Configure SSH for lab-user
            if not current_state.get("lab_user_ssh_configured"):
                self._configure_lab_user_ssh()
                changes_made.append("Configured SSH keys for lab-user")

            # Validate config files (user should have pre-loaded them)
            config_status = self._validate_config_files()
            if config_status:
                changes_made.append(config_status)

            return PluginResult(
                changed=len(changes_made) > 0,
                message=f"Applied {len(changes_made)} changes: {'; '.join(changes_made)}",
                status=PluginStatus.COMPLETED,
                data={
                    "changes": changes_made,
                    "hetzner_deployment": True,
                    "lab_user_ready": self._user_exists("lab-user") and self._user_has_sudo("lab-user"),
                    "next_steps": self._get_next_steps(),
                },
            )

        except Exception as e:
            return PluginResult(
                changed=False,
                message=f"Failed to apply changes: {str(e)}",
                status=PluginStatus.FAILED,
            )

    def _is_hetzner_environment(self) -> bool:
        """Check if we're in a Hetzner environment"""
        # Basic checks for Hetzner environment
        hetzner_indicators = [
            # Check for Hetzner-specific network interfaces
            lambda: "eth0" in subprocess.run(["ip", "link"], capture_output=True, text=True).stdout,
            # Check for Hetzner metadata (if available)
            lambda: self._check_hetzner_metadata(),
            # Check hostname patterns
            lambda: any(pattern in subprocess.run(["hostname"], capture_output=True, text=True).stdout.lower() for pattern in ["hetzner", "fsn", "nbg", "ash"]),
        ]

        return any(check() for check in hetzner_indicators)

    def _check_hetzner_metadata(self) -> bool:
        """Check for Hetzner metadata service"""
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "--max-time",
                    "3",
                    "http://169.254.169.254/hetzner/v1/metadata",
                ],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _user_exists(self, username: str) -> bool:
        """Check if user exists"""
        try:
            subprocess.run(["id", username], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _user_has_sudo(self, username: str) -> bool:
        """Check if user has sudo privileges"""
        try:
            result = subprocess.run(["groups", username], capture_output=True, text=True, check=True)
            return "wheel" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def _is_lab_user_ssh_configured(self) -> bool:
        """Check if lab-user SSH is configured"""
        lab_user_home = "/home/lab-user"
        ssh_key_path = f"{lab_user_home}/.ssh/id_rsa"
        authorized_keys_path = f"{lab_user_home}/.ssh/authorized_keys"

        return os.path.exists(ssh_key_path) and os.path.exists(authorized_keys_path)

    def _check_required_packages(self) -> bool:
        """Check if required packages are installed"""
        try:
            result = subprocess.run(
                ["rpm", "-qa", "--queryformat", "%{NAME}\n"],
                capture_output=True,
                text=True,
                check=True,
            )
            installed_packages = set(result.stdout.strip().split("\n"))

            return all(pkg in installed_packages for pkg in self.required_packages)
        except subprocess.CalledProcessError:
            return False

    def _install_required_packages(self) -> None:
        """Install required packages"""
        cmd = ["dnf", "install", "-y"] + self.required_packages
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Package installation failed: {result.stderr}")

        self.logger.info(f"Installed required packages: {', '.join(self.required_packages)}")

    def _download_configure_script(self) -> None:
        """Download the configure-sudo-user.sh script"""
        try:
            subprocess.run(["curl", "-OL", self.configure_script_url], check=True)

            subprocess.run(["chmod", "+x", "configure-sudo-user.sh"], check=True)

            self.logger.info("Downloaded and made configure-sudo-user.sh executable")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to download configure script: {e}")

    def _create_lab_user(self) -> None:
        """Create lab-user using the configure script"""
        if not os.path.exists("./configure-sudo-user.sh"):
            raise RuntimeError("configure-sudo-user.sh script not found")

        try:
            # Run the configure script to create lab-user
            result = subprocess.run(
                ["./configure-sudo-user.sh", "lab-user"],
                capture_output=True,
                text=True,
                check=True,
            )

            self.logger.info("Created lab-user using configure-sudo-user.sh")
            self.logger.debug(f"Script output: {result.stdout}")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create lab-user: {e.stderr}")

    def _ensure_lab_user_sudo(self) -> None:
        """Ensure lab-user has sudo privileges"""
        try:
            subprocess.run(["usermod", "-aG", "wheel", "lab-user"], check=True)

            self.logger.info("Ensured lab-user has sudo privileges")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to add lab-user to wheel group: {e}")

    def _configure_lab_user_ssh(self) -> None:
        """Configure SSH keys for lab-user"""
        lab_user_home = "/home/lab-user"
        ssh_dir = f"{lab_user_home}/.ssh"

        try:
            # Create SSH directory
            os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
            subprocess.run(["chown", "lab-user:lab-user", ssh_dir], check=True)

            # Generate SSH key as lab-user
            subprocess.run(
                [
                    "sudo",
                    "-u",
                    "lab-user",
                    "ssh-keygen",
                    "-f",
                    f"{ssh_dir}/id_rsa",
                    "-t",
                    "rsa",
                    "-N",
                    "",
                ],
                check=True,
            )

            # Get IP address and set up SSH copy-id
            ip_result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, check=True)

            ip_address = ip_result.stdout.strip().split()[0]

            # Copy public key to authorized_keys
            with open(f"{ssh_dir}/id_rsa.pub", "r") as pub_key:
                pub_content = pub_key.read()

            with open(f"{ssh_dir}/authorized_keys", "w") as auth_keys:
                auth_keys.write(pub_content)

            # Set proper permissions
            os.chmod(f"{ssh_dir}/authorized_keys", 0o600)
            subprocess.run(["chown", "lab-user:lab-user", f"{ssh_dir}/authorized_keys"], check=True)

            self.logger.info(f"Configured SSH keys for lab-user (IP: {ip_address})")

        except Exception as e:
            raise RuntimeError(f"Failed to configure SSH for lab-user: {e}")

    def _validate_config_files(self) -> str:
        """Validate that config files are properly set up"""
        messages = []

        # Check /tmp/config.yml
        if os.path.exists("/tmp/config.yml"):
            try:
                with open("/tmp/config.yml", "r") as f:
                    config_content = f.read()

                if "PLACEHOLDER" in config_content or len(config_content.strip()) < 50:
                    messages.append("⚠️  /tmp/config.yml exists but appears to be a template - please update with real values")
                else:
                    messages.append("✅ /tmp/config.yml validated")
            except Exception:
                messages.append("❌ /tmp/config.yml exists but cannot be read")
        else:
            messages.append("❌ /tmp/config.yml not found - please create it before running deployment")

        # Check notouch.env
        if os.path.exists("notouch.env"):
            try:
                with open("notouch.env", "r") as f:
                    env_content = f.read()

                if "DontForgetToChangeMe" in env_content:
                    messages.append("⚠️  notouch.env exists but SSH_PASSWORD needs to be updated")
                else:
                    messages.append("✅ notouch.env validated")
            except Exception:
                messages.append("❌ notouch.env exists but cannot be read")
        else:
            messages.append("❌ notouch.env not found - please create it before running deployment")

        return "; ".join(messages) if messages else "Config files validated"

    def _get_next_steps(self) -> List[str]:
        """Get next steps for the user"""
        next_steps = []

        if self._user_exists("lab-user"):
            next_steps.append("Switch to lab-user: sudo su - lab-user")

        if os.path.exists("/tmp/config.yml"):
            next_steps.append("Verify /tmp/config.yml has real credentials (not placeholders)")
        else:
            next_steps.append("Create /tmp/config.yml with your credentials")

        if os.path.exists("notouch.env"):
            next_steps.append("Verify notouch.env has correct SSH_PASSWORD")
        else:
            next_steps.append("Create notouch.env with environment variables")

        next_steps.extend(["Run: source notouch.env", "Continue with Qubinode Navigator deployment"])

        return next_steps

    def get_dependencies(self) -> List[str]:
        """Hetzner Deployment plugin dependencies"""
        return []  # Can work independently

    def validate_config(self) -> bool:
        """Validate Hetzner Deployment plugin configuration"""
        # Check configure script URL
        script_url = self.config.get("configure_script_url", "")
        if not script_url.startswith("http"):
            self.logger.error("configure_script_url must be a valid HTTP URL")
            return False

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status with Hetzner deployment specific info"""
        base_status = super().get_health_status()

        # Add Hetzner deployment specific status
        base_status.update(
            {
                "hetzner_environment": self._is_hetzner_environment(),
                "lab_user_ready": self._user_exists("lab-user") and self._user_has_sudo("lab-user"),
                "ssh_configured": self._is_lab_user_ssh_configured(),
                "config_files_present": os.path.exists("/tmp/config.yml") and os.path.exists("notouch.env"),
            }
        )

        return base_status
