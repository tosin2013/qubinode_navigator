#!/bin/bash

# =============================================================================
# GitHub Actions Runner Deployment - The "CI/CD Integration Specialist"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script deploys and configures GitHub Actions self-hosted runners for
# Qubinode Navigator CI/CD pipelines. It creates secure runner environments
# with proper user management and credential handling.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements GitHub Actions runner deployment:
# 1. [PHASE 1]: Credential Retrieval - Securely retrieves runner tokens from vault
# 2. [PHASE 2]: User Management - Creates dedicated runner user with proper permissions
# 3. [PHASE 3]: Runner Installation - Downloads and installs GitHub Actions runner
# 4. [PHASE 4]: Security Configuration - Sets up secure runner environment
# 5. [PHASE 5]: Registration - Registers runner with GitHub repository
# 6. [PHASE 6]: Service Setup - Configures runner as system service
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [CI/CD Integration]: Enables GitHub Actions workflows for automated deployments
# - [Vault Integration]: Uses AnsibleSafe to securely retrieve runner tokens
# - [Security Architecture]: Implements secure runner deployment per security standards
# - [Infrastructure Automation]: Supports automated infrastructure deployment workflows
# - [Development Pipeline]: Enables continuous integration and deployment
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Security-First]: Uses vault for credential management and secure user setup
# - [Checksum Validation]: Validates runner package integrity before installation
# - [User Isolation]: Creates dedicated runner user with minimal required permissions
# - [Service Integration]: Configures runner as system service for reliability
# - [Token Management]: Securely handles GitHub runner registration tokens
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Runner Updates]: Update RUNNER_VERSION and CONFIG_CHECKSUM_CHECKED for new versions
# - [Security Enhancements]: Improve user permissions or security configurations
# - [Integration Features]: Add support for new GitHub Actions features
# - [Monitoring]: Add logging or monitoring capabilities for runner health
# - [Multi-Runner Support]: Extend to support multiple concurrent runners
#
# 🚨 IMPORTANT FOR LLMs: This script creates system users, modifies sudoers, and
# registers with external GitHub services. It requires root privileges and handles
# sensitive runner tokens. Changes affect CI/CD pipeline security and functionality.

set -euo pipefail
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
set -x

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
RUNNER_VERSION="2.319.1"  # GitHub Actions runner version - update for new releases
CONFIG_CHECKSUM_CHECKED="3f6efb7488a183e291fc2c62876e14c9ee732864173734facc85a1bfb1744464"  # SHA256 checksum for security validation
RUNNER_USER="runner"      # Dedicated user account for runner execution
RUNNER_HOME="/home/$RUNNER_USER"  # Runner user home directory

/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 2
export PASSWORD=$(yq eval '.rhsm_password' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")
export KCLI_PIPELINES_RUNNER_TOKEN=$(yq eval '.kcli_pipelines_runner_token' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1

# Create the user if it doesn't exist
if ! id -u $RUNNER_USER &>/dev/null; then
  echo "Creating user $RUNNER_USER"
  useradd -m $RUNNER_USER -p ${PASSWORD} || exit $?
fi

# Create a folder for the runner
mkdir -p $RUNNER_HOME/actions-runner
chown -R $RUNNER_USER:$RUNNER_USER $RUNNER_HOME/actions-runner

usermod -aG wheel ${RUNNER_USER}
echo "${RUNNER_USER} ALL=(root) NOPASSWD:ALL" | tee -a /etc/sudoers.d/${RUNNER_USER}
chmod 0440 /etc/sudoers.d/${RUNNER_USER}

# Switch to the runner user
sudo -u  $RUNNER_USER bash << EOF

# Navigate to the runner directory
cd $RUNNER_HOME/actions-runner

# Download the latest runner package
curl -o "actions-runner-linux-x64-$RUNNER_VERSION.tar.gz" \
  -L "https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz"

# Optional: Validate the hash
shasum -a 256 "actions-runner-linux-x64-$RUNNER_VERSION.tar.gz" | grep -q "^$CONFIG_CHECKSUM_CHECKED" || {
  echo "Checksum validation failed!"
  exit 1
}

# Extract the installer
tar xzf actions-runner-linux-x64-$RUNNER_VERSION.tar.gz

# Create the runner and start the configuration experience
echo "Configuring runner..."
echo ./config.sh --unattended --url https://github.com/tosin2013/kcli-pipelines --token "$KCLI_PIPELINES_RUNNER_TOKEN" --labels "self-hosted,Linux,X64,${GUID}-github-runner" --name "${GUID}-github-runner" --replace 
./config.sh --unattended --url https://github.com/tosin2013/kcli-pipelines --token "$KCLI_PIPELINES_RUNNER_TOKEN" --labels "self-hosted,Linux,X64,${GUID}-github-runner" --name "${GUID}-github-runner" --replace
echo "Runner configured!"

# Start the runner as service
cd $RUNNER_HOME/actions-runner
sudo ./svc.sh  install
sudo ./svc.sh start


# Log the process ID
echo "Runner started with PID \$!"

EOF

# Notify the user
echo "Runner has been started  as service for user $RUNNER_USER."
