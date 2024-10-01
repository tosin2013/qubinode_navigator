#!/bin/bash

# Define variables
RUNNER_VERSION="2.319.1"
CONFIG_CHECKSUM_CHECKED="3f6efb7488a183e291fc2c62876e14c9ee732864173734facc85a1bfb1744464"

# Create a folder
mkdir -p actions-runner && cd actions-runner

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
./config.sh --url https://github.com/tosin2013/kcli-pipelines --token $KCLI_PIPELINES_GITHUB_TOKEN
echo "Runner configured! Run the runner:"
echo "./run.sh"
