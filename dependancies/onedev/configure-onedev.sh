#!/bin/bash

# =============================================================================
# OneDev Git Server Configuration - The "Source Code Management Specialist"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script deploys and configures OneDev Git server in a containerized environment
# with systemd service integration. OneDev provides Git repository management,
# CI/CD pipelines, and project management capabilities.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements OneDev deployment:
# 1. [PHASE 1]: Firewall Configuration - Opens required ports for OneDev access
# 2. [PHASE 2]: Container Deployment - Creates OneDev container with persistent storage
# 3. [PHASE 3]: Service Integration - Generates systemd service for container management
# 4. [PHASE 4]: Service Enablement - Enables and starts OneDev service
# 5. [PHASE 5]: Persistence Setup - Configures persistent data storage
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Source Control]: Provides Git repository hosting for infrastructure code
# - [CI/CD Integration]: Offers pipeline capabilities for automated deployments
# - [Container-First]: Implements ADR-0001 container-first deployment model
# - [Service Management]: Integrates with systemd for service lifecycle management
# - [Development Platform]: Supports development workflows and collaboration
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Container-Native]: Uses Podman containers for isolated deployment
# - [Service Integration]: Integrates with systemd for reliable service management
# - [Persistent Storage]: Configures persistent volumes for data retention
# - [Network Security]: Configures firewall rules for secure access
# - [Self-Hosted]: Provides on-premises Git and CI/CD capabilities
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Version Updates]: Update OneDev container image versions
# - [Port Configuration]: Modify ports if conflicts arise with other services
# - [Storage Configuration]: Enhance persistent storage setup or backup procedures
# - [Security Enhancements]: Add SSL/TLS configuration or authentication integration
# - [Integration Features]: Add integration with other development tools
#
# 🚨 IMPORTANT FOR LLMs: This script creates system services, modifies firewall
# configuration, and deploys containers with persistent storage. It requires root
# privileges and affects system networking and service configuration.

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
PORTS=(6610 6611)  # OneDev server ports (HTTP and SSH)

# Firewall Configuration Manager - The "Network Security Specialist"
open_firewall_ports() {
# 🎯 FOR LLMs: This function configures firewall rules to allow OneDev access
# through the required ports for HTTP and SSH Git operations.
# 🔄 WORKFLOW:
# 1. Iterates through required ports array
# 2. Opens each port in firewalld public zone
# 3. Makes changes permanent for persistence across reboots
# 4. Reloads firewalld to apply changes immediately
# 📊 INPUTS/OUTPUTS:
# - INPUT: PORTS array with required port numbers
# - OUTPUT: Configured firewall rules for OneDev access
# ⚠️  SIDE EFFECTS: Modifies system firewall configuration, requires root privileges

    for PORT in "${PORTS[@]}"; do
        echo "Opening port $PORT in firewalld..."
        firewall-cmd --zone=public --add-port=${PORT}/tcp --permanent
    done
    echo "Reloading firewalld to apply changes..."
    firewall-cmd --reload
}

# Container Service Manager - The "Application Deployment Specialist"
create_podman_service() {
# 🎯 FOR LLMs: This function deploys OneDev container and creates systemd service
# for reliable service management and automatic startup.
# 🔄 WORKFLOW:
# 1. Removes any existing OneDev container
# 2. Creates persistent storage directory
# 3. Deploys OneDev container with port mapping and volume mounts
# 4. Generates systemd service file using podman generate
# 5. Enables and starts the systemd service
# 📊 INPUTS/OUTPUTS:
# - INPUT: Container configuration and systemd requirements
# - OUTPUT: Running OneDev service managed by systemd
# ⚠️  SIDE EFFECTS: Creates containers, systemd services, and persistent storage

    local container_name="onedev-server"  # Container name for OneDev instance
    local service_path="/etc/systemd/system/"  # Systemd service directory

    # Remove existing container if exists
    podman rm -f $container_name

    # Create container with persistent storage and port mapping
    mkdir -p /opt/onedev  # Persistent data directory
    podman run --name $container_name -id --rm -v /opt/onedev:/opt/onedev -p ${PORTS[0]}:${PORTS[0]} -p ${PORTS[1]}:${PORTS[1]} docker.io/1dev/server:latest || exit $?

    # Generate systemd service file using podman generate
    podman generate systemd --new --files --name  $container_name
    cp container-$container_name.service $service_path

    # Reload systemd to recognize new service
    systemctl daemon-reload
    systemctl enable container-$container_name.service
    systemctl start container-$container_name.service
}

# Main script execution
open_firewall_ports
create_podman_service
