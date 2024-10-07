#!/bin/bash
set -euo pipefail
# Define variables
RUNNER_VERSION="2.319.1"
CONFIG_CHECKSUM_CHECKED="3f6efb7488a183e291fc2c62876e14c9ee732864173734facc85a1bfb1744464"
RUNNER_USER="runner"
RUNNER_HOME="/home/$RUNNER_USER"

/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 2
PASSWORD=$(yq eval '.rhsm_password' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1

# Create the user if it doesn't exist
if ! id -u $RUNNER_USER &>/dev/null; then
  echo "Creating user $RUNNER_USER"
  useradd -m $RUNNER_USER -p ${PASSWORD} || exit $?
fi

# Create a folder for the runner
mkdir -p $RUNNER_HOME/actions-runner
chown -R $RUNNER_USER:$RUNNER_USER $RUNNER_HOME/actions-runner

usermod -aG wheel ${RUNNER_HOME}
echo "${RUNNER_HOME} ALL=(root) NOPASSWD:ALL" | tee -a /etc/sudoers.d/${RUNNER_HOME}
chmod 0440 /etc/sudoers.d/${RUNNER_HOME}

# Switch to the runner user
sudo -u $RUNNER_USER bash << EOF

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
./config.sh --unattended --url https://github.com/tosin2013/kcli-pipelines --token "$KCLI_PIPELINES_GITHUB_TOKEN" --labels "self-hosted,Linux,X64" --name "${GUID}-github-runner" --replace || exit $?
echo "Runner configured!"

# Start the runner as a background job
nohup ./run.sh &

# Log the process ID
echo "Runner started with PID \$!"

EOF

# Notify the user
echo "Runner has been started as a background job for user $RUNNER_USER."
