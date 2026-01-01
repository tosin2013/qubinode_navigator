#!/usr/bin/env python3

# =============================================================================
# Enhanced Configuration Generator - The "Smart Brain"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This is the intelligent configuration management system that generates dynamic
# configurations using Jinja2 templates and HashiCorp Vault integration. It replaces
# static configuration files with template-driven, environment-specific configurations.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements sophisticated configuration management:
# 1. [PHASE 1]: Template Processing - Loads Jinja2 templates from templates/ directory
# 2. [PHASE 2]: Variable Gathering - Collects variables from environment, vault, and system
# 3. [PHASE 3]: Vault Integration - Retrieves secrets from HashiCorp Vault or HCP Vault Secrets
# 4. [PHASE 4]: System Detection - Auto-detects network interfaces, storage, and system info
# 5. [PHASE 5]: Configuration Generation - Renders templates with collected variables
# 6. [PHASE 6]: Secure Output - Writes configuration files with proper permissions
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Configuration Engine]: Called by setup scripts to generate /tmp/config.yml
# - [Template System]: Uses templates/*.yml.j2 files for environment-specific configs
# - [Vault Integration]: Implements ADR-0004 security architecture with vault secrets
# - [Backward Compatibility]: Extends load-variables.py while maintaining compatibility
# - [CI/CD Integration]: Supports automated configuration generation in pipelines
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Template-Driven]: Uses Jinja2 templates for flexible, environment-specific configuration
# - [Vault-First Security]: Prioritizes HashiCorp Vault over environment variables
# - [System-Aware]: Auto-detects system configuration and network topology
# - [Secure by Default]: Implements secure file permissions and credential handling
# - [Extensible Design]: Modular architecture for adding new vault backends and templates
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [New Templates]: Add support for new environment templates in templates/ directory
# - [Vault Backends]: Add new vault backend integrations (AWS Secrets Manager, Azure Key Vault)
# - [System Detection]: Enhance auto-detection for new hardware or cloud platforms
# - [Security Features]: Add new encryption methods or credential protection mechanisms
# - [Template Features]: Extend Jinja2 template capabilities with custom filters or functions
#
# 🚨 IMPORTANT FOR LLMs: This script handles sensitive credentials and system configuration.
# It integrates with external vault services and generates configuration files used by
# infrastructure deployment. Changes affect security posture and deployment reliability.

"""
Enhanced Configuration Generator for Qubinode Navigator
Extends existing load-variables.py with template support and HashiCorp Vault integration
Based on repository analysis and HashiCorp Vault Secrets migration patterns
"""

import argparse
import getpass
import os
import yaml
import netifaces
import psutil
import re
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

try:
    import jinja2

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("Warning: Jinja2 not available. Template features disabled.")

try:
    import hvac  # HashiCorp Vault client

    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False
    print("Warning: hvac not available. HashiCorp Vault features disabled.")

try:
    import requests  # For HCP API calls

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not available. HCP API features disabled.")


# Configuration Generation Engine - The "Template Master"
class EnhancedConfigGenerator:
    """
    🎯 FOR LLMs: This class is the core configuration generation engine that combines
    Jinja2 templates, HashiCorp Vault secrets, and system auto-detection to create
    dynamic, environment-specific configurations.

    🔄 WORKFLOW:
    1. Initializes vault clients (HashiCorp Vault, HCP Vault Secrets)
    2. Loads Jinja2 templates from templates/ directory
    3. Gathers variables from multiple sources (env, vault, system)
    4. Renders templates with collected variables
    5. Outputs secure configuration files with proper permissions

    📊 KEY CAPABILITIES:
    - Template-based configuration generation using Jinja2
    - HashiCorp Vault integration for secure credential management
    - HCP Vault Secrets API integration for cloud-native secrets
    - System auto-detection (network, storage, hardware)
    - Secure file handling with proper permissions

    ⚠️  SECURITY CONSIDERATIONS:
    - Handles sensitive credentials and API tokens
    - Creates temporary files with restricted permissions
    - Integrates with external vault services requiring network access
    """

    def __init__(self):
        # 📊 GLOBAL VARIABLES (shared with bash scripts):
        self.inventory_env = os.environ.get("INVENTORY")  # Environment inventory (e.g., 'hetzner', 'rhel9-equinix')
        if not self.inventory_env:
            print("INVENTORY environment variable not found.")
            sys.exit(1)

        self.templates_dir = Path("templates")  # Jinja2 template directory
        self.vault_client = None  # HashiCorp Vault client instance

        # 🔧 CONFIGURATION CONSTANTS FOR LLMs:
        self.use_vault = os.environ.get("USE_HASHICORP_VAULT", "false").lower() == "true"  # Enable HashiCorp Vault
        self.use_hcp = os.environ.get("USE_HASHICORP_CLOUD", "false").lower() == "true"  # Enable HCP Vault Secrets
        self.openshift_vault = os.environ.get("OPENSHIFT_VAULT", "false").lower() == "true"  # OpenShift vault mode
        self.hcp_token = None  # HCP API token for cloud secrets

        # Initialize HashiCorp Vault client if enabled
        if self.use_vault and HVAC_AVAILABLE:
            self._init_vault_client()

        # Initialize HCP API client if enabled
        if self.use_hcp and REQUESTS_AVAILABLE:
            self._init_hcp_client()

    def _init_vault_client(self):
        """Initialize HashiCorp Vault client"""
        try:
            vault_addr = os.environ.get("VAULT_ADDR")
            vault_token = os.environ.get("VAULT_TOKEN")
            vault_auth_method = os.environ.get("VAULT_AUTH_METHOD", "token")

            if vault_addr:
                self.vault_client = hvac.Client(url=vault_addr)

                # Handle different authentication methods
                if vault_auth_method == "kubernetes" and self.openshift_vault:
                    self._authenticate_kubernetes()
                elif vault_token:
                    self.vault_client.token = vault_token
                    if self.vault_client.is_authenticated():
                        print(f"✅ Connected to HashiCorp Vault at {vault_addr}")
                    else:
                        print("❌ Failed to authenticate with HashiCorp Vault")
                        self.vault_client = None
                else:
                    print("⚠️ No valid authentication method configured. Vault features disabled.")
                    self.vault_client = None
            else:
                print("⚠️ VAULT_ADDR not set. Vault features disabled.")
        except Exception as e:
            print(f"❌ Error connecting to Vault: {e}")
            self.vault_client = None

    def _authenticate_kubernetes(self):
        """Authenticate with Vault using Kubernetes auth method"""
        try:
            # Read service account token
            token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
            if os.path.exists(token_path):
                with open(token_path, "r") as f:
                    jwt_token = f.read().strip()

                vault_role = os.environ.get("VAULT_ROLE", "qubinode-navigator")

                # Authenticate with Kubernetes auth method
                response = self.vault_client.auth.kubernetes.login(role=vault_role, jwt=jwt_token)

                if response and "auth" in response:
                    self.vault_client.token = response["auth"]["client_token"]
                    print("✅ Authenticated with Vault using Kubernetes auth")
                else:
                    print("❌ Failed to authenticate with Kubernetes auth")
                    self.vault_client = None
            else:
                print("⚠️ Kubernetes service account token not found")
                self.vault_client = None

        except Exception as e:
            print(f"❌ Error with Kubernetes authentication: {e}")
            self.vault_client = None

    def _init_hcp_client(self):
        """Initialize HCP API client"""
        try:
            hcp_client_id = os.environ.get("HCP_CLIENT_ID")
            hcp_client_secret = os.environ.get("HCP_CLIENT_SECRET")

            if hcp_client_id and hcp_client_secret:
                # Get HCP API token
                auth_url = "https://auth.idp.hashicorp.com/oauth2/token"
                auth_data = {
                    "grant_type": "client_credentials",
                    "client_id": hcp_client_id,
                    "client_secret": hcp_client_secret,
                    "audience": "https://api.hashicorp.cloud",
                }

                response = requests.post(auth_url, data=auth_data)
                if response.status_code == 200:
                    self.hcp_token = response.json().get("access_token")
                    print("✅ Connected to HashiCorp Cloud Platform")
                else:
                    print(f"❌ Failed to authenticate with HCP: {response.status_code}")
                    self.hcp_token = None
            else:
                print("⚠️ HCP_CLIENT_ID or HCP_CLIENT_SECRET not set. HCP features disabled.")
        except Exception as e:
            print(f"❌ Error connecting to HCP: {e}")
            self.hcp_token = None

    def generate_config_template(
        self,
        output_path: str = "/tmp/config.yml",
        template_name: str = "default.yml.j2",
    ) -> bool:
        """Generate /tmp/config.yml from template with current system variables"""

        print(f"🔧 Generating configuration from template: {template_name}")

        # Gather all variables (existing + new)
        variables = self._gather_all_variables()

        # Generate config using template or fallback
        if JINJA2_AVAILABLE and self.templates_dir.exists():
            config_content = self._render_template(template_name, variables)
        else:
            config_content = self._generate_fallback_config(variables)

        # Write securely to output file
        return self._write_secure_config(config_content, output_path)

    def _gather_all_variables(self) -> Dict[str, Any]:
        """Gather variables from all sources (env, vault, interactive)"""
        variables = {
            "generation_timestamp": datetime.now().isoformat(),
            "environment": self.inventory_env,
            "vault_enabled": self.use_vault,
        }

        # Environment variables (highest priority)
        env_vars = {
            "rhsm_username": os.environ.get("RHSM_USERNAME", ""),
            "rhsm_password": os.environ.get("RHSM_PASSWORD", ""),
            "rhsm_org": os.environ.get("RHSM_ORG", ""),
            "rhsm_activationkey": os.environ.get("RHSM_ACTIVATIONKEY", ""),
            "admin_user_password": os.environ.get("ADMIN_USER_PASSWORD", ""),
            "offline_token": os.environ.get("OFFLINE_TOKEN", ""),
            "openshift_pull_secret": os.environ.get("OPENSHIFT_PULL_SECRET", ""),
            "automation_hub_offline_token": os.environ.get("AUTOMATION_HUB_OFFLINE_TOKEN", ""),
            "freeipa_server_admin_password": os.environ.get("FREEIPA_SERVER_ADMIN_PASSWORD", ""),
            "xrdp_remote_user": os.environ.get("XRDP_REMOTE_USER", "remoteuser"),
            "xrdp_remote_user_password": os.environ.get("XRDP_REMOTE_USER_PASSWORD", ""),
            "aws_access_key": os.environ.get("AWS_ACCESS_KEY", ""),
            "aws_secret_key": os.environ.get("AWS_SECRET_KEY", ""),
        }
        variables.update(env_vars)

        # HashiCorp Vault variables (if enabled)
        if self.vault_client:
            vault_vars = self._get_vault_variables()
            # Vault variables override empty env vars but not set env vars
            for key, value in vault_vars.items():
                if not variables.get(key):
                    variables[key] = value

        # HCP Vault Secrets variables (if enabled)
        if self.hcp_token:
            hcp_vars = self._get_hcp_variables()
            # HCP variables override empty env vars but not set env vars
            for key, value in hcp_vars.items():
                if not variables.get(key):
                    variables[key] = value

        # Interactive prompts for missing required fields
        variables = self._prompt_for_missing_variables(variables)

        return variables

    def _get_vault_variables(self) -> Dict[str, str]:
        """Retrieve variables from HashiCorp Vault"""
        vault_vars = {}

        if not self.vault_client:
            return vault_vars

        try:
            # Based on existing CI/CD patterns in repository
            secret_path = os.environ.get("SECRET_PATH", f"ansiblesafe/{self.inventory_env}")

            # Try to read from configured secret path (kv mount)
            try:
                response = self.vault_client.secrets.kv.v2.read_secret_version(path=secret_path, mount_point="kv")
                if response and "data" in response and "data" in response["data"]:
                    vault_vars.update(response["data"]["data"])
                    print(f"✅ Retrieved {len(vault_vars)} secrets from Vault")
            except Exception as e:
                print(f"⚠️ Could not read from {secret_path}: {e}")

            # Try alternative paths
            for path in [
                secret_path,
                f"qubinode/{secret_path}",
                f"secrets/{secret_path}",
            ]:
                try:
                    response = self.vault_client.secrets.kv.v2.read_secret_version(path=path, mount_point="kv")
                    if response and "data" in response and "data" in response["data"]:
                        vault_vars.update(response["data"]["data"])
                        print(f"✅ Retrieved secrets from Vault path: {path}")
                        break
                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Error retrieving from Vault: {e}")

        return vault_vars

    def _get_hcp_variables(self) -> Dict[str, str]:
        """Retrieve variables from HCP Vault Secrets"""
        hcp_vars = {}

        if not self.hcp_token:
            return hcp_vars

        try:
            # Get HCP configuration
            hcp_org_id = os.environ.get("HCP_ORG_ID")
            hcp_project_id = os.environ.get("HCP_PROJECT_ID")
            app_name = os.environ.get("APP_NAME", "qubinode-navigator-secrets")

            if not all([hcp_org_id, hcp_project_id]):
                print("⚠️ HCP_ORG_ID or HCP_PROJECT_ID not set")
                return hcp_vars

            # HCP Vault Secrets API endpoint
            api_url = f"https://api.cloud.hashicorp.com/secrets/2023-06-13/organizations/{hcp_org_id}/projects/{hcp_project_id}/apps/{app_name}/open"

            headers = {
                "Authorization": f"Bearer {self.hcp_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(api_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                secrets = data.get("secrets", [])

                for secret in secrets:
                    secret_name = secret.get("name")
                    secret_value = secret.get("static_version", {}).get("value")
                    if secret_name and secret_value:
                        hcp_vars[secret_name] = secret_value

                print(f"✅ Retrieved {len(hcp_vars)} secrets from HCP Vault Secrets")
            else:
                print(f"⚠️ Failed to retrieve HCP secrets: {response.status_code}")
                if response.status_code == 404:
                    print(f"   App '{app_name}' not found. Please create it in HCP Vault Secrets.")

        except Exception as e:
            print(f"❌ Error retrieving from HCP: {e}")

        return hcp_vars

    def _prompt_for_missing_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Prompt for missing required variables"""

        required_fields = ["rhsm_username", "rhsm_password", "admin_user_password"]

        for field in required_fields:
            if not variables.get(field):
                if "password" in field.lower():
                    variables[field] = getpass.getpass(f"Enter {field.replace('_', ' ')}: ")
                else:
                    variables[field] = input(f"Enter {field.replace('_', ' ')}: ")

        return variables

    def _render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render Jinja2 template with variables"""

        template_path = self.templates_dir / template_name

        if not template_path.exists():
            print(f"⚠️ Template {template_name} not found, using fallback")
            return self._generate_fallback_config(variables)

        try:
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.templates_dir))
            template = env.get_template(template_name)

            # Add custom functions for templates
            env.globals["vault_get"] = lambda path: self._vault_get(path)
            env.globals["generate_password"] = lambda length=16: os.urandom(length).hex()[:length]

            return template.render(**variables)

        except Exception as e:
            print(f"❌ Error rendering template: {e}")
            return self._generate_fallback_config(variables)

    def _vault_get(self, path: str) -> str:
        """Template function to get value from Vault"""
        if not self.vault_client:
            return ""

        try:
            response = self.vault_client.secrets.kv.v2.read_secret_version(path=path)
            if response and "data" in response and "data" in response["data"]:
                return response["data"]["data"].get("value", "")
        except Exception:
            pass

        return ""

    def _generate_fallback_config(self, variables: Dict[str, Any]) -> str:
        """Generate configuration without templates (fallback)"""

        config = {
            "rhsm_username": variables.get("rhsm_username", ""),
            "rhsm_password": variables.get("rhsm_password", ""),
            "rhsm_org": variables.get("rhsm_org", ""),
            "rhsm_activationkey": variables.get("rhsm_activationkey", ""),
            "admin_user_password": variables.get("admin_user_password", "changeme"),
            "offline_token": variables.get("offline_token", ""),
            "openshift_pull_secret": variables.get("openshift_pull_secret", ""),
            "automation_hub_offline_token": variables.get("automation_hub_offline_token", ""),
            "freeipa_server_admin_password": variables.get("freeipa_server_admin_password", "changeme"),
            "xrdp_remote_user": variables.get("xrdp_remote_user", "remoteuser"),
            "xrdp_remote_user_password": variables.get("xrdp_remote_user_password", "changeme"),
        }

        # Add optional AWS credentials if provided
        if variables.get("aws_access_key"):
            config["aws_access_key"] = variables["aws_access_key"]
            config["aws_secret_key"] = variables.get("aws_secret_key", "")

        return yaml.dump(config, default_flow_style=False)

    def _write_secure_config(self, content: str, output_path: str) -> bool:
        """Write configuration securely to file"""

        try:
            # Create temporary file with secure permissions
            temp_fd, temp_path = tempfile.mkstemp(suffix=".yml", prefix="config_")

            try:
                # Set secure permissions (600 - owner read/write only)
                os.chmod(temp_path, 0o600)

                # Write content
                with os.fdopen(temp_fd, "w") as f:
                    f.write(content)

                # Move to final location
                shutil.move(temp_path, output_path)
                os.chmod(output_path, 0o600)

                print(f"✅ Configuration written to {output_path}")
                return True

            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise e

        except Exception as e:
            print(f"❌ Error writing configuration: {e}")
            return False

    def update_vault_with_config(self, config_path: str = "/tmp/config.yml") -> bool:
        """Update HashiCorp Vault with configuration values"""

        if not self.vault_client:
            print("❌ Vault client not available")
            return False

        if not os.path.exists(config_path):
            print(f"❌ Configuration file not found: {config_path}")
            return False

        try:
            # Read configuration
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Prepare secrets for Vault
            secret_path = os.environ.get("SECRET_PATH", f"ansiblesafe/{self.inventory_env}")

            # Write to Vault
            self.vault_client.secrets.kv.v2.create_or_update_secret(path=secret_path, secret=config)

            print(f"✅ Updated Vault at path: {secret_path}")
            return True

        except Exception as e:
            print(f"❌ Error updating Vault: {e}")
            return False


# Extend existing functionality
class EnhancedLoadVariables(EnhancedConfigGenerator):
    """Enhanced version of original load-variables.py with template support"""

    def update_inventory(self, username=None, domain_name=None, dnf_forwarder=None):
        """Original update_inventory function with enhancements"""
        if username is None:
            if os.geteuid() == 0:
                username = input("Enter username: ")
            else:
                username = getpass.getuser()

        if domain_name is None:
            while True:
                domain_name = input("Enter the domain name for your system: ")
                regex = r"^(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,}$"
                if re.match(regex, domain_name):
                    break
                print("Invalid domain name format. Please try again.")

        if dnf_forwarder is None:
            dnf_forwarder = input("Enter the DNS forwarder for your system: ")

        inventory_path = f"inventories/{self.inventory_env}/group_vars/all.yml"
        with open(inventory_path, "r") as f:
            inventory = yaml.safe_load(f)

        inventory["admin_user"] = username
        inventory["domain"] = domain_name
        inventory["dns_forwarder"] = dnf_forwarder

        with open(inventory_path, "w") as f:
            yaml.dump(inventory, f, default_flow_style=False)

    def get_interface_ips(self, configure_bridge=None, interface=None):
        """Network interface detection and configuration with automatic discovery"""
        if configure_bridge is None:
            if os.geteuid() == 0:
                print("Error: Cannot set configure_bridge to True when running as root.")
                configure_bridge = False
                print("configure_bridge is set to", configure_bridge)
            else:
                configure_bridge = True
                print("configure_bridge is set to", configure_bridge)
        else:
            # Handle string values from environment variables
            if isinstance(configure_bridge, str):
                configure_bridge = configure_bridge.lower() in (
                    "true",
                    "1",
                    "yes",
                    "on",
                )
            print(f"🔧 Bridge configuration from parameter: {configure_bridge}")

        # Get a list of network interfaces
        interfaces = netifaces.interfaces()

        # Filter out loopback interfaces and any that don't have an IPv4 address
        interfaces = [i for i in interfaces if i != "lo" and netifaces.AF_INET in netifaces.ifaddresses(i)]

        if interface is None:
            # If there's only one interface, use that
            if len(interfaces) == 1:
                interface = interfaces[0]
            # If there's more than one, prompt the user to choose one
            elif len(interfaces) > 1:
                print("Multiple network interfaces found:")
                for i, iface in enumerate(interfaces):
                    print(f"{i + 1}. {iface}")
                choice = int(input("Choose an interface to use: "))
                interface = interfaces[choice - 1]
            # If there are no interfaces, raise an exception
            else:
                raise Exception("No network interfaces found")

        # Get the IPv4 address, netmask, and MAC address for the chosen interface
        addrs = netifaces.ifaddresses(interface)
        ip = addrs[netifaces.AF_INET][0]["addr"]
        netmask = addrs[netifaces.AF_INET][0]["netmask"]
        macaddr = addrs[netifaces.AF_LINK][0]["addr"]

        # Calculate the network address and prefix length from the netmask
        ".".join(str(int(x) & int(y)) for x, y in zip(ip.split("."), netmask.split(".")))
        prefix_len = sum(bin(int(x)).count("1") for x in netmask.split("."))

        inventory_path = f"inventories/{self.inventory_env}/group_vars/control/kvm_host.yml"
        with open(inventory_path, "r") as f:
            inventory = yaml.safe_load(f)

        inventory["configure_bridge"] = configure_bridge
        inventory["kvm_host_gw"] = netifaces.gateways()["default"][netifaces.AF_INET][0]
        inventory["kvm_host_interface"] = interface
        inventory["kvm_host_ip"] = ip
        inventory["kvm_host_macaddr"] = macaddr
        inventory["kvm_host_mask_prefix"] = prefix_len
        inventory["kvm_host_netmask"] = netmask

        with open(inventory_path, "w") as f:
            yaml.dump(inventory, f, default_flow_style=False)

        network_config = {
            "kvm_host_gw": netifaces.gateways()["default"][netifaces.AF_INET][0],
            "kvm_host_interface": interface,
            "kvm_host_ip": ip,
            "kvm_host_macaddr": macaddr,
            "kvm_host_mask_prefix": prefix_len,
            "kvm_host_netmask": netmask,
        }

        print("🔧 Network configuration detected and updated:")
        print(network_config)
        return network_config

    def get_disk(self):
        """Get available disks for storage configuration"""
        disks = []
        for device in psutil.disk_partitions():
            if device.device.startswith("/dev/"):
                disks.append(device.device)
        return disks

    def select_disk(self, disks=None):
        """Disk selection and storage configuration with automatic detection"""
        # Check if vg_qubi is present
        try:
            vgdisplay_output = subprocess.check_output(["sudo", "vgdisplay"]).decode()
        except subprocess.CalledProcessError:
            print("Error: Could not get volume group information.")
            return False

        inventory_path = f"inventories/{self.inventory_env}/group_vars/control/kvm_host.yml"

        if "vg_qubi" in vgdisplay_output:
            print("✅ Volume group 'vg_qubi' already exists.")
            # Update YAML file with storage settings
            with open(inventory_path, "r") as f:
                inventory = yaml.safe_load(f)
            inventory["create_libvirt_storage"] = False
            inventory["create_lvm"] = False
            inventory["skip_libvirt_pool"] = True
            with open(inventory_path, "w") as f:
                yaml.dump(inventory, f, default_flow_style=False)
            print("🔧 Storage configuration updated: LVM creation disabled (existing vg_qubi detected)")
            print(f"📁 Updated {inventory_path}")
            return True

        elif disks == "skip":
            print("⏭️ Skipping disk selection.")
            # Update YAML file with storage settings
            with open(inventory_path, "r") as f:
                inventory = yaml.safe_load(f)
            inventory["create_libvirt_storage"] = False
            inventory["create_lvm"] = False
            with open(inventory_path, "w") as f:
                yaml.dump(inventory, f, default_flow_style=False)
            print(f"📁 Updated {inventory_path}")
            return True
        else:
            # Get available disks
            if disks is None:
                disks = self.get_disk()
            print(f"💾 Available disks: {disks}")

            # Check if disk is already mounted
            mounted = False
            if disks:
                for disk in disks:
                    if os.path.ismount(f"/mnt/{disk}"):
                        print(f"📁 Disk {disk} is already mounted.")
                        disks = [disk]
                        mounted = True
                        break

            # Skip disk selection if only one disk is available and already mounted
            if mounted and len(disks) == 1:
                print(f"💾 Using disk: {disks[0]}")
                use_root_disk = True
            else:
                use_root_disk = False

            # Update YAML file with selected disk
            with open(inventory_path, "r") as f:
                inventory = yaml.safe_load(f)

            if use_root_disk is True:
                print("⚠️ No disk selected.")
                inventory["create_libvirt_storage"] = False
                inventory["create_lvm"] = False
                with open(inventory_path, "w") as f:
                    yaml.dump(inventory, f, default_flow_style=False)
                return False
            else:
                disks = disks.replace("/dev/", "")
                inventory["create_libvirt_storage"] = True
                inventory["create_lvm"] = True
                inventory["kvm_host_libvirt_extra_disk"] = disks
                with open(inventory_path, "w") as f:
                    yaml.dump(inventory, f)

                print(f"💾 Selected disk: {disks}")
                print(f"📁 Updated {inventory_path}")
                return True


if __name__ == "__main__":
    generator = EnhancedConfigGenerator()

    parser = argparse.ArgumentParser(description="Enhanced Qubinode Navigator Configuration Generator")
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate /tmp/config.yml from template",
    )
    parser.add_argument(
        "--template",
        default="default.yml.j2",
        help="Template file to use (default: default.yml.j2)",
    )
    parser.add_argument(
        "--output",
        default="/tmp/config.yml",
        help="Output file path (default: /tmp/config.yml)",
    )
    parser.add_argument(
        "--update-vault",
        action="store_true",
        help="Update HashiCorp Vault with generated config",
    )

    # Original arguments for backward compatibility
    parser.add_argument("--username", help="Username for the system")
    parser.add_argument("--domain", help="Domain name for the system")
    parser.add_argument("--forwarder", help="DNS forwarder for the system")
    parser.add_argument("--bridge", help="Configure bridge for the system (true/false)")
    parser.add_argument("--interface", help="Network interface to use")
    parser.add_argument("--disk", help='Disk to use, or "skip" to skip disk selection')

    args = parser.parse_args()

    if args.generate_config:
        success = generator.generate_config_template(args.output, args.template)

        if success and args.update_vault:
            generator.update_vault_with_config(args.output)
    else:
        # Run original functionality for backward compatibility
        print("Running original load-variables functionality...")
        enhanced_loader = EnhancedLoadVariables()

        # Update inventory with provided arguments
        enhanced_loader.update_inventory(args.username, args.domain, args.forwarder)

        # Detect and update network configuration
        enhanced_loader.get_interface_ips(args.bridge, args.interface)

        # Detect and configure storage
        enhanced_loader.select_disk(args.disk)
