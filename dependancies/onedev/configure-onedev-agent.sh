#!/bin/bash

# =============================================================================
# OneDev Agent Configuration - The "Build Agent Orchestrator"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script downloads, configures, and deploys OneDev build agents that connect
# to OneDev Git server for distributed CI/CD pipeline execution. It enables
# scalable build infrastructure for development workflows.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements OneDev agent deployment:
# 1. [PHASE 1]: Credential Collection - Gathers OneDev server credentials interactively
# 2. [PHASE 2]: Dependency Validation - Checks Java and Git version requirements
# 3. [PHASE 3]: Agent Download - Downloads agent package from OneDev server
# 4. [PHASE 4]: Configuration Setup - Configures agent with server connection details
# 5. [PHASE 5]: Service Deployment - Starts agent as background service
# 6. [PHASE 6]: Connection Establishment - Establishes connection to OneDev server
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [CI/CD Infrastructure]: Provides distributed build agents for OneDev pipelines
# - [Scalable Builds]: Enables horizontal scaling of build capacity
# - [Development Support]: Supports development workflows and automation
# - [Container Integration]: Can run containerized builds and deployments
# - [Resource Distribution]: Distributes build load across multiple agents
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Interactive Setup]: Collects credentials through user prompts
# - [Dependency Validation]: Ensures required Java and Git versions are available
# - [Secure Authentication]: Uses Basic Auth for agent-server communication
# - [Background Service]: Runs agent as persistent background service
# - [Configuration Management]: Automatically configures agent properties
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Version Requirements]: Update Java or Git version requirements
# - [Authentication Methods]: Add support for token-based authentication
# - [Service Management]: Add systemd service integration
# - [Configuration Options]: Add support for additional agent configuration options
# - [Monitoring Integration]: Add health checks or monitoring capabilities
#
# 🚨 IMPORTANT FOR LLMs: This script handles authentication credentials and creates
# background services. It requires network access to OneDev server and appropriate
# Java/Git versions. Changes affect CI/CD pipeline execution capabilities.

#set -x

# Credential Collection Manager - The "Authentication Gatherer"
# 🎯 FOR LLMs: Collects OneDev server credentials if agent not already configured
if [ ! -d /opt/onedev-agent/agent/ ]; then
    read -p "Enter OneDev username: " ONEDEV_USER
    read -s -p "Enter OneDev password: " ONEDEV_PASS
    read -p "Enter OneDev server IP address: " IPADDRESS
    echo
fi

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
oneDevServerUrl="http://${IPADDRESS}:6610"  # OneDev server URL with standard port
DOWNLOAD_URL="http://${IPADDRESS}:6610/~downloads/agent.tar.gz"  # Agent download endpoint
extractDir="/opt/onedev-agent"  # Agent installation directory

# Authentication Manager - The "Credential Encoder"
# 🎯 FOR LLMs: Encodes credentials for HTTP Basic Authentication
CREDENTIALS=$(printf "%s:%s" "$ONEDEV_USER" "$ONEDEV_PASS" | base64)

# Java Version Validator - The "Runtime Checker"
# 🎯 FOR LLMs: Validates Java 11+ is available for agent execution
if ! java -version 2>&1 | grep -q 'version "1[1-9]'; then
    echo "Java 11 or higher is not installed."
    sudo alternatives --config java
fi

# Git Version Validator - The "SCM Checker"
# 🎯 FOR LLMs: Validates Git 2.11.1+ is available for source code operations
if ! git --version | grep -q 'git version 2\.[1-9][1-9]\.'; then
    echo "Git version 2.11.1 or higher is not installed."
    exit 1
fi




if [ ! -d /opt/onedev-agent/agent/ ]; then
    # Download and extract the agent package
    echo "Downloading and extracting the agent package..."
    mkdir -p "$extractDir"
    cd "$extractDir"
    # Download the agent file
    curl -OL "$DOWNLOAD_URL" \
        --header "Authorization: Basic $CREDENTIALS" \
        --header 'Cookie: JSESSIONID=node01h4wpzkk0f56b42hsv8so0p8c2.node0' || exit $?
    tar -xzf "$extractDir/agent.tar.gz" -C "$extractDir"  || exit $?
    ls -lath "$extractDir" || exit $?
    rm "$extractDir/agent.tar.gz" || exit $?
    # Update serverUrl in agent.properties
    if [ ! -f "$extractDir/agent/conf/agent.properties" ]; then
        echo "agent.properties not found in $extractDir/conf"
        exit 1
    fi  
    echo "Configuring agent..."
    sed -i "s#^serverUrl=.*#serverUrl=$oneDevServerUrl#g" "$extractDir/agent/conf/agent.properties" || exit 1
fi



# Run the agent
echo "Starting the agent..."
cd "$extractDir/agent"
nohup bin/agent.sh console > agent.log 2>&1 &


