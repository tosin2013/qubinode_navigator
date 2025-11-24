"""
Red Hat Product Demo System Plugin

Handles Red Hat Product Demo System specific configuration and environment setup.
Migrates functionality from demo-redhat-com.markdown deployment guide.
"""

import subprocess
import os
from typing import Dict, Any, List
from core.base_plugin import QubiNodePlugin, PluginResult, SystemState, ExecutionContext, PluginStatus


class RedHatDemoPlugin(QubiNodePlugin):
    """
    Red Hat Product Demo System plugin
    
    Handles specific configuration requirements for Red Hat Product Demo System
    deployments including RHSM subscription management, environment variables,
    and demo-specific tooling.
    """
    
    __version__ = "1.0.0"
    
    def _initialize_plugin(self) -> None:
        """Initialize Red Hat Demo System plugin"""
        self.logger.info("Initializing Red Hat Product Demo System plugin")
        
        # Demo system specific configuration
        self.demo_packages = self.config.get('demo_packages', [
            'subscription-manager', 'ansible-core', 'git', 'vim',
            'curl', 'wget', 'jq', 'python3-pip'
        ])
        
        # Required environment variables for demo system
        self.required_env_vars = self.config.get('required_env_vars', [
            'SSH_USER', 'CICD_PIPELINE', 'ENV_USERNAME', 'KVM_VERSION',
            'CICD_ENVIORNMENT', 'DOMAIN'
        ])
        
    def check_state(self) -> SystemState:
        """Check current Red Hat Demo System state"""
        state_data = {}
        
        # Check if we're in a demo environment
        state_data['is_demo_environment'] = self._is_demo_environment()
        
        # Check RHSM subscription status
        state_data['rhsm_registered'] = self._is_rhsm_registered()
        state_data['rhsm_subscribed'] = self._is_rhsm_subscribed()
        
        # Check config file setup
        state_data['config_file_exists'] = self._config_file_exists()
        state_data['config_file_valid'] = self._is_config_file_valid()
        
        # Check environment file setup
        state_data['env_file_exists'] = self._env_file_exists()
        state_data['env_file_valid'] = self._is_env_file_valid()
        
        # Check demo packages
        state_data['demo_packages_installed'] = self._get_installed_packages()
        
        # Check lab-user configuration
        state_data['lab_user_configured'] = self._is_lab_user_configured()
        
        # Check bashrc configuration
        state_data['bashrc_configured'] = self._is_bashrc_configured()
        
        return SystemState(state_data)
        
    def get_desired_state(self, context: ExecutionContext) -> SystemState:
        """Get desired Red Hat Demo System state"""
        desired_data = {}
        
        # Should be configured for demo environment
        desired_data['is_demo_environment'] = True
        
        # RHSM should be registered and subscribed
        desired_data['rhsm_registered'] = True
        desired_data['rhsm_subscribed'] = True
        
        # Config file should exist and be valid
        desired_data['config_file_exists'] = True
        desired_data['config_file_valid'] = True
        
        # Environment file should exist and be valid
        desired_data['env_file_exists'] = True
        desired_data['env_file_valid'] = True
        
        # Demo packages should be installed
        desired_data['demo_packages_installed'] = set(self.demo_packages)
        
        # Lab user should be configured
        desired_data['lab_user_configured'] = True
        
        # Bashrc should be configured
        desired_data['bashrc_configured'] = True
        
        return SystemState(desired_data)
        
    def apply_changes(self, 
                     current_state: SystemState, 
                     desired_state: SystemState,
                     context: ExecutionContext) -> PluginResult:
        """Apply changes to achieve desired Red Hat Demo System state"""
        changes_made = []
        
        try:
            # Install missing demo packages
            current_packages = set(current_state.get('demo_packages_installed', []))
            desired_packages = desired_state.get('demo_packages_installed', set())
            missing_packages = desired_packages - current_packages
            
            if missing_packages:
                self._install_packages(list(missing_packages))
                changes_made.append(f"Installed demo packages: {', '.join(missing_packages)}")
                
            # Create config file template if needed
            if not current_state.get('config_file_exists') and desired_state.get('config_file_exists'):
                self._create_config_file_template()
                changes_made.append("Created /tmp/config.yml template")
                
            # Create environment file if needed
            if not current_state.get('env_file_exists') and desired_state.get('env_file_exists'):
                self._create_env_file()
                changes_made.append("Created notouch.env file")
                
            # Configure lab user if needed
            if not current_state.get('lab_user_configured') and desired_state.get('lab_user_configured'):
                self._configure_lab_user()
                changes_made.append("Configured lab-user for demo system")
                
            # Configure bashrc if needed
            if not current_state.get('bashrc_configured') and desired_state.get('bashrc_configured'):
                self._configure_bashrc()
                changes_made.append("Configured .bashrc for demo environment")
                
            # Handle RHSM registration if credentials provided
            if (desired_state.get('rhsm_registered') and 
                not current_state.get('rhsm_registered')):
                
                rhsm_username = context.variables.get('rhsm_username')
                rhsm_password = context.variables.get('rhsm_password')
                rhsm_org = context.variables.get('rhsm_org')
                rhsm_activationkey = context.variables.get('rhsm_activationkey')
                
                if rhsm_username and rhsm_password:
                    self._register_rhsm_userpass(rhsm_username, rhsm_password)
                    changes_made.append("Registered RHSM with username/password")
                elif rhsm_org and rhsm_activationkey:
                    self._register_rhsm_activation_key(rhsm_org, rhsm_activationkey)
                    changes_made.append("Registered RHSM with activation key")
                else:
                    self.logger.warning("RHSM credentials not provided - skipping registration")
                    
            return PluginResult(
                changed=len(changes_made) > 0,
                message=f"Applied {len(changes_made)} changes: {'; '.join(changes_made)}",
                status=PluginStatus.COMPLETED,
                data={
                    'changes': changes_made,
                    'demo_environment': current_state.get('is_demo_environment', False)
                }
            )
            
        except Exception as e:
            return PluginResult(
                changed=False,
                message=f"Failed to apply changes: {str(e)}",
                status=PluginStatus.FAILED
            )
            
    def _is_demo_environment(self) -> bool:
        """Check if we're in a Red Hat demo environment"""
        # Check for demo-specific indicators
        indicators = [
            '/tmp/config.yml',
            'notouch.env',
            os.path.expanduser('~lab-user')
        ]
        
        return any(os.path.exists(indicator) for indicator in indicators)
        
    def _is_rhsm_registered(self) -> bool:
        """Check if RHSM is registered"""
        try:
            result = subprocess.run([
                'subscription-manager', 'status'
            ], capture_output=True, text=True)
            
            return 'Overall Status: Current' in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
    def _is_rhsm_subscribed(self) -> bool:
        """Check if RHSM has active subscriptions"""
        try:
            result = subprocess.run([
                'subscription-manager', 'list', '--consumed'
            ], capture_output=True, text=True)
            
            return 'Pool ID:' in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
    def _config_file_exists(self) -> bool:
        """Check if config file exists"""
        return os.path.exists('/tmp/config.yml')
        
    def _is_config_file_valid(self) -> bool:
        """Check if config file has required fields"""
        if not self._config_file_exists():
            return False
            
        try:
            with open('/tmp/config.yml', 'r') as f:
                content = f.read()
                
            required_fields = [
                'rhsm_username', 'rhsm_password', 'admin_user_password',
                'offline_token', 'openshift_pull_secret'
            ]
            
            return all(field in content for field in required_fields)
        except Exception:
            return False
            
    def _create_config_file_template(self) -> None:
        """Create config file template"""
        config_template = """# Red Hat Product Demo System Configuration
# Generated by Qubinode Navigator RedHatDemoPlugin
# 
# IMPORTANT: Replace all placeholder values with actual credentials
# Use ansiblesafe to generate secure content: https://github.com/tosin2013/ansiblesafe
# Documentation: https://dev.to/tosin2013/ansible-vault-secrets-documentation-3g1a

rhsm_username: rheluser  # Replace with your Red Hat username
rhsm_password: rhelpassword  # Replace with your Red Hat password
rhsm_org: orgid  # Replace with your organization ID (for activation key)
rhsm_activationkey: activationkey  # Replace with your activation key
admin_user_password: password  # Change to the lab-user password
offline_token: offlinetoken  # Replace with your Red Hat offline token
openshift_pull_secret: pullsecret  # Replace with your OpenShift pull secret
automation_hub_offline_token: automationhubtoken  # Replace with automation hub token
freeipa_server_admin_password: password  # Change to the lab-user password
xrdp_remote_user: remoteuser  # Replace with remote user
xrdp_remote_user_password: password  # Replace with remote user password
aws_access_key: accesskey  # Optional: for AWS credentials and Route53
aws_secret_key: secretkey  # Optional: for AWS credentials and Route53

# Additional demo system configuration
domain: qubinodelab.io  # Change to your domain if using custom domain
kvm_version: "latest"
cicd_environment: gitlab  # or onedev - change for default CICD environment
"""
        
        with open('/tmp/config.yml', 'w') as f:
            f.write(config_template)
            
        # Set secure permissions
        os.chmod('/tmp/config.yml', 0o600)
        
        self.logger.info("Created /tmp/config.yml template")
        self.logger.warning("Please update /tmp/config.yml with actual credentials")
        
    def _env_file_exists(self) -> bool:
        """Check if environment file exists"""
        return os.path.exists('notouch.env')
        
    def _is_env_file_valid(self) -> bool:
        """Check if environment file has required variables"""
        if not self._env_file_exists():
            return False
            
        try:
            with open('notouch.env', 'r') as f:
                content = f.read()
                
            return all(var in content for var in self.required_env_vars)
        except Exception:
            return False
            
    def _create_env_file(self) -> None:
        """Create environment file for demo system"""
        env_content = """# Red Hat Product Demo System Environment Variables
# Generated by Qubinode Navigator RedHatDemoPlugin

export SSH_USER=lab-user
export CICD_PIPELINE='true'
export ENV_USERNAME=lab-user
export KVM_VERSION="latest"
export CICD_ENVIORNMENT="gitlab"  # or onedev - change for default CICD environment
export DOMAIN=qubinodelab.io  # Change to your domain if using custom domain

# SSH Configuration
export SSH_PASSWORD=DontForgetToChangeMe  # Use the password of the lab-user

# Demo System Specific
export DEMO_ENVIRONMENT=true
export QUBINODE_DEMO_MODE=true
"""
        
        with open('notouch.env', 'w') as f:
            f.write(env_content)
            
        self.logger.info("Created notouch.env file")
        self.logger.warning("Please update SSH_PASSWORD in notouch.env")
        
    def _get_installed_packages(self) -> List[str]:
        """Get list of installed packages"""
        try:
            result = subprocess.run(
                ['rpm', '-qa', '--queryformat', '%{NAME}\n'],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip().split('\n')
        except subprocess.CalledProcessError:
            return []
            
    def _install_packages(self, packages: List[str]) -> None:
        """Install packages using dnf"""
        cmd = ['sudo', 'dnf', 'install', '-y'] + packages
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Package installation failed: {result.stderr}")
            
        self.logger.info(f"Installed packages: {', '.join(packages)}")
        
    def _is_lab_user_configured(self) -> bool:
        """Check if lab-user is properly configured"""
        return os.path.exists(os.path.expanduser('~lab-user'))
        
    def _configure_lab_user(self) -> None:
        """Configure lab-user for demo system"""
        # Ensure lab-user exists
        try:
            subprocess.run(['id', 'lab-user'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Create lab-user
            subprocess.run([
                'sudo', 'useradd', '-m', '-s', '/bin/bash', 'lab-user'
            ], check=True)
            
            # Add to wheel group
            subprocess.run([
                'sudo', 'usermod', '-aG', 'wheel', 'lab-user'
            ], check=True)
            
        self.logger.info("Configured lab-user for demo system")
        
    def _is_bashrc_configured(self) -> bool:
        """Check if .bashrc is configured for demo environment"""
        bashrc_path = os.path.expanduser('~lab-user/.bashrc')
        if not os.path.exists(bashrc_path):
            return False
            
        try:
            with open(bashrc_path, 'r') as f:
                content = f.read()
                return 'notouch.env' in content
        except Exception:
            return False
            
    def _configure_bashrc(self) -> None:
        """Configure .bashrc for demo environment"""
        bashrc_path = os.path.expanduser('~lab-user/.bashrc')
        
        bashrc_addition = """
# Red Hat Product Demo System Configuration
# Added by Qubinode Navigator RedHatDemoPlugin

# Source demo environment variables
if [ -f ~/notouch.env ]; then
    source ~/notouch.env
fi

# Demo system aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias qn='cd ~/qubinode_navigator'
alias config-edit='vi /tmp/config.yml'
alias env-edit='vi ~/notouch.env'

# Demo system prompt
export PS1="[\\u@\\h-DEMO \\W]\\$ "
"""
        
        with open(bashrc_path, 'a') as f:
            f.write(bashrc_addition)
            
        # Set ownership to lab-user
        subprocess.run(['sudo', 'chown', 'lab-user:lab-user', bashrc_path], check=True)
        
        self.logger.info("Configured .bashrc for demo environment")
        
    def _register_rhsm_userpass(self, username: str, password: str) -> None:
        """Register RHSM with username/password"""
        cmd = [
            'sudo', 'subscription-manager', 'register',
            '--username', username,
            '--password', password,
            '--auto-attach'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"RHSM registration failed: {result.stderr}")
            
        self.logger.info("Registered RHSM with username/password")
        
    def _register_rhsm_activation_key(self, org: str, activation_key: str) -> None:
        """Register RHSM with activation key"""
        cmd = [
            'sudo', 'subscription-manager', 'register',
            '--org', org,
            '--activationkey', activation_key
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"RHSM registration failed: {result.stderr}")
            
        self.logger.info("Registered RHSM with activation key")
        
    def get_dependencies(self) -> List[str]:
        """Red Hat Demo System plugin dependencies"""
        return []  # Can work independently
        
    def validate_config(self) -> bool:
        """Validate Red Hat Demo System plugin configuration"""
        # Check that package lists are valid
        packages = self.config.get('demo_packages', [])
        if not isinstance(packages, list):
            self.logger.error("demo_packages configuration must be a list")
            return False
            
        env_vars = self.config.get('required_env_vars', [])
        if not isinstance(env_vars, list):
            self.logger.error("required_env_vars configuration must be a list")
            return False
            
        return True
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status with demo system specific info"""
        base_status = super().get_health_status()
        
        # Add demo system specific status
        base_status.update({
            'demo_environment': self._is_demo_environment(),
            'rhsm_registered': self._is_rhsm_registered(),
            'config_file_ready': self._config_file_exists() and self._is_config_file_valid()
        })
        
        return base_status
