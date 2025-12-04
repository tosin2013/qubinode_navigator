"""
Vault Integration Plugin

Handles HashiCorp Vault integration setup and configuration.
Migrates functionality from setup-vault-integration.sh.
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


class VaultIntegrationPlugin(QubiNodePlugin):
    """
    HashiCorp Vault integration plugin

    Handles secure credential management setup and configuration
    for Qubinode Navigator deployments.
    """

    __version__ = "1.0.0"

    def _initialize_plugin(self) -> None:
        """Initialize Vault Integration plugin"""
        self.logger.info("Initializing Vault Integration plugin")

        # Set default configuration
        self.vault_packages = self.config.get("vault_packages", ["python3-pip", "python3-requests", "python3-hvac"])

        self.vault_url = self.config.get("vault_url", "http://localhost:8200")
        self.vault_token_file = self.config.get("vault_token_file", "~/.vault_token")
        self.env_file = self.config.get("env_file", ".env")

    def check_state(self) -> SystemState:
        """Check current Vault integration state"""
        state_data = {}

        # Check if required packages are installed
        state_data["vault_packages_installed"] = self._check_vault_packages()

        # Check if .env file exists and is configured
        state_data["env_file_configured"] = self._is_env_file_configured()

        # Check if vault token exists
        state_data["vault_token_exists"] = self._vault_token_exists()

        # Check vault connectivity
        state_data["vault_connectivity"] = self._test_vault_connectivity()

        # Check enhanced_load_variables.py integration
        state_data["enhanced_loader_available"] = self._is_enhanced_loader_available()

        # Check vault authentication
        state_data["vault_authenticated"] = self._is_vault_authenticated()

        return SystemState(state_data)

    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired Vault integration state"""
        desired_data = {}

        # Vault packages should be installed
        desired_data["vault_packages_installed"] = True

        # Environment file should be configured
        desired_data["env_file_configured"] = True

        # Vault token should exist (if vault is available)
        desired_data["vault_token_exists"] = True

        # Vault connectivity should work (if vault is available)
        desired_data["vault_connectivity"] = True

        # Enhanced loader should be available
        desired_data["enhanced_loader_available"] = True

        # Vault should be authenticated (if vault is available)
        desired_data["vault_authenticated"] = True

        return SystemState(desired_data)

    def apply_changes(
        self,
        current_state: SystemState,
        desired_state: SystemState,
        context: ExecutionContext,
    ) -> PluginResult:
        """Apply changes to achieve desired Vault integration state"""
        changes_made = []

        try:
            # Install vault packages if needed
            if not current_state.get("vault_packages_installed") and desired_state.get("vault_packages_installed"):
                self._install_vault_packages()
                changes_made.append("Installed Vault integration packages")

            # Configure environment file if needed
            if not current_state.get("env_file_configured") and desired_state.get("env_file_configured"):
                self._configure_env_file()
                changes_made.append("Configured environment file for Vault")

            # Set up vault token if needed (and vault is available)
            if not current_state.get("vault_token_exists") and desired_state.get("vault_token_exists"):
                if self._is_vault_server_available():
                    self._setup_vault_token()
                    changes_made.append("Configured Vault authentication token")
                else:
                    self.logger.warning("Vault server not available - skipping token setup")

            # Test vault connectivity
            if desired_state.get("vault_connectivity"):
                if self._test_vault_connectivity():
                    changes_made.append("Validated Vault connectivity")
                else:
                    self.logger.warning("Vault connectivity test failed - check configuration")

            return PluginResult(
                changed=len(changes_made) > 0,
                message=f"Applied {len(changes_made)} changes: {'; '.join(changes_made)}",
                status=PluginStatus.COMPLETED,
                data={
                    "changes": changes_made,
                    "vault_url": self.vault_url,
                    "vault_available": self._is_vault_server_available(),
                },
            )

        except Exception as e:
            return PluginResult(
                changed=False,
                message=f"Failed to apply changes: {str(e)}",
                status=PluginStatus.FAILED,
            )

    def _check_vault_packages(self) -> bool:
        """Check if vault-related packages are installed"""
        try:
            # Check for hvac (HashiCorp Vault API client)
            subprocess.run(["python3", "-c", "import hvac"], check=True, capture_output=True)

            # Check for requests
            subprocess.run(["python3", "-c", "import requests"], check=True, capture_output=True)

            return True
        except subprocess.CalledProcessError:
            return False

    def _install_vault_packages(self) -> None:
        """Install vault-related packages"""
        # Install system packages
        system_packages = ["python3-pip", "python3-requests"]
        cmd = ["sudo", "dnf", "install", "-y"] + system_packages
        subprocess.run(cmd, check=True)

        # Install Python packages
        python_packages = ["hvac", "python-dotenv"]
        for package in python_packages:
            subprocess.run(["pip3", "install", package], check=True)

        self.logger.info("Installed Vault integration packages")

    def _is_env_file_configured(self) -> bool:
        """Check if .env file is configured for Vault"""
        env_path = os.path.expanduser(self.env_file)
        if not os.path.exists(env_path):
            return False

        try:
            with open(env_path, "r") as f:
                content = f.read()
                return "VAULT_ADDR" in content
        except Exception:
            return False

    def _configure_env_file(self) -> None:
        """Configure .env file for Vault integration"""
        env_path = os.path.expanduser(self.env_file)

        # Read existing content if file exists
        existing_content = ""
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                existing_content = f.read()

        # Add vault configuration if not present
        vault_config = f"""
# HashiCorp Vault Configuration
VAULT_ADDR={self.vault_url}
VAULT_TOKEN_FILE={os.path.expanduser(self.vault_token_file)}
VAULT_NAMESPACE=
VAULT_SKIP_VERIFY=false

# Qubinode Navigator Vault Integration
QUBINODE_VAULT_ENABLED=true
QUBINODE_VAULT_PATH=secret/qubinode
"""

        if "VAULT_ADDR" not in existing_content:
            with open(env_path, "a") as f:
                f.write(vault_config)

        self.logger.info(f"Configured environment file: {env_path}")

    def _vault_token_exists(self) -> bool:
        """Check if vault token file exists"""
        token_path = os.path.expanduser(self.vault_token_file)
        return os.path.exists(token_path)

    def _setup_vault_token(self) -> None:
        """Set up vault token (placeholder - requires manual configuration)"""
        token_path = os.path.expanduser(self.vault_token_file)

        # Create placeholder token file with instructions
        token_content = """# Vault Token Configuration
#
# This file should contain your HashiCorp Vault token.
# Replace this content with your actual vault token.
#
# To get a token:
# 1. vault auth -method=userpass username=<your-username>
# 2. Copy the token from the output
# 3. Replace this file content with just the token string
#
# Example:
# s.1234567890abcdef1234567890abcdef12345678

# PLACEHOLDER_TOKEN - REPLACE WITH ACTUAL TOKEN
"""

        with open(token_path, "w") as f:
            f.write(token_content)

        os.chmod(token_path, 0o600)  # Secure permissions

        self.logger.info(f"Created vault token file template: {token_path}")
        self.logger.warning("Please replace the placeholder token with your actual Vault token")

    def _is_vault_server_available(self) -> bool:
        """Check if Vault server is available"""
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "5", f"{self.vault_url}/v1/sys/health"],
                capture_output=True,
                text=True,
            )

            return result.returncode == 0
        except Exception:
            return False

    def _test_vault_connectivity(self) -> bool:
        """Test vault connectivity"""
        if not self._is_vault_server_available():
            return False

        try:
            # Test with Python hvac client
            test_script = f"""
import hvac
import os

client = hvac.Client(url='{self.vault_url}')
health = client.sys.read_health_status()
print("Vault connectivity: OK")
"""

            result = subprocess.run(["python3", "-c", test_script], capture_output=True, text=True)

            return result.returncode == 0

        except Exception:
            return False

    def _is_enhanced_loader_available(self) -> bool:
        """Check if enhanced_load_variables.py is available"""
        return os.path.exists("enhanced_load_variables.py")

    def _is_vault_authenticated(self) -> bool:
        """Check if vault is authenticated"""
        if not self._vault_token_exists() or not self._is_vault_server_available():
            return False

        try:
            token_path = os.path.expanduser(self.vault_token_file)
            with open(token_path, "r") as f:
                token_content = f.read().strip()

            # Skip if it's still the placeholder
            if "PLACEHOLDER_TOKEN" in token_content:
                return False

            # Test authentication with hvac
            test_script = f"""
import hvac
import os

token = open('{token_path}', 'r').read().strip()
client = hvac.Client(url='{self.vault_url}', token=token)

# Test token validity
if client.is_authenticated():
    print("Vault authentication: OK")
else:
    exit(1)
"""

            result = subprocess.run(["python3", "-c", test_script], capture_output=True, text=True)

            return result.returncode == 0

        except Exception:
            return False

    def get_dependencies(self) -> List[str]:
        """Vault integration plugin dependencies"""
        return []  # Can work independently

    def validate_config(self) -> bool:
        """Validate Vault integration plugin configuration"""
        # Check vault URL format
        vault_url = self.config.get("vault_url", "")
        if not vault_url.startswith(("http://", "https://")):
            self.logger.error("vault_url must start with http:// or https://")
            return False

        return True

    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status with Vault-specific info"""
        base_status = super().get_health_status()

        # Add Vault-specific status
        base_status.update(
            {
                "vault_url": self.vault_url,
                "vault_server_available": self._is_vault_server_available(),
                "vault_connectivity": self._test_vault_connectivity(),
                "vault_authenticated": self._is_vault_authenticated(),
            }
        )

        return base_status
