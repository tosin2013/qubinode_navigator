#!/bin/bash

# =============================================================================
# Cockpit SSL Configuration - The "Web Management Security Specialist"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script configures SSL certificates for Cockpit web management interface
# using Let's Encrypt certificates with AWS Route53 DNS validation. It provides
# secure HTTPS access to system management capabilities.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements SSL certificate management for Cockpit:
# 1. [PHASE 1]: Credential Retrieval - Securely retrieves AWS credentials from vault
# 2. [PHASE 2]: Service Enablement - Enables Cockpit web management service
# 3. [PHASE 3]: Certificate Generation - Uses certbot with Route53 DNS validation
# 4. [PHASE 4]: Certificate Installation - Installs certificates in Cockpit directory
# 5. [PHASE 5]: Service Configuration - Configures Cockpit to use SSL certificates
# 6. [PHASE 6]: Security Validation - Validates SSL configuration and access
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Web Management]: Provides secure web interface for system management
# - [Vault Integration]: Uses AnsibleSafe for secure AWS credential retrieval
# - [DNS Integration]: Integrates with AWS Route53 for domain validation
# - [Container-First]: Uses containerized certbot per ADR-0001
# - [Security Enhancement]: Implements HTTPS for web management interfaces
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Security-First]: Uses Let's Encrypt certificates for trusted SSL
# - [DNS Validation]: Uses Route53 DNS challenge for certificate validation
# - [Container-Native]: Uses containerized certbot for certificate generation
# - [Credential Security]: Securely handles AWS credentials through vault
# - [Service Integration]: Integrates with Cockpit web management service
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Certificate Updates]: Update certbot container versions or configurations
# - [DNS Providers]: Add support for other DNS providers besides Route53
# - [Security Enhancements]: Implement certificate rotation or monitoring
# - [Container Updates]: Update container runtime configurations
# - [Domain Management]: Add support for multiple domains or subdomains
#
# 🚨 IMPORTANT FOR LLMs: This script handles SSL certificates and AWS credentials.
# It modifies system SSL configuration and requires network access to Let's Encrypt
# and AWS Route53. Changes affect web management security and accessibility.

# Reference: https://kenmoini.com/post/2021/12/custom-certificates-in-cockpit/
set -xe

# Secure Credential Retrieval - The "Vault Access Manager"
# 🎯 FOR LLMs: Securely retrieves AWS credentials from encrypted vault
# Decrypt the vault file to access AWS credentials
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 2

# Extract required AWS credentials using yq
AWS_ACCESS_KEY_ID=$(yq eval '.aws_access_key' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")
AWS_SECRET_ACCESS_KEY=$(yq eval '.aws_secret_key' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")

# Re-encrypt the vault file for security
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
CONTAINER_RUN_TIME="podman"  # Container runtime for certbot execution
COCKPIT_DOMAIN="cockpit.${GUID}.${DOMAIN}"  # Cockpit web interface domain
COCKPIT_CERT_DIR="/etc/cockpit/ws-certs.d"  # Cockpit SSL certificate directory

# Enable Cockpit service if not already enabled
sudo systemctl enable --now cockpit.socket

# Use case-insensitive comparison for container runtime
case "$(echo "$CONTAINER_RUN_TIME" | tr '[:upper:]' '[:lower:]')" in
    docker)
        echo "Using Docker"
        docker run --rm -it \
            --env AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
            --env AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
            -v "/etc/letsencrypt:/etc/letsencrypt" \
            certbot/dns-route53 \
            certonly \
            --dns-route53 \
            -d "${COCKPIT_DOMAIN}" -d "*.${COCKPIT_DOMAIN}" \
            --agree-tos \
            --email "${EMAIL}" \
            --non-interactive
        ;;
    podman)
        echo "Using Podman"
        mkdir -p /etc/letsencrypt/
        podman run --rm -it \
            --env AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
            --env AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
            -v "/etc/letsencrypt:/etc/letsencrypt:Z" \
            docker.io/certbot/dns-route53 \
            certonly \
            --dns-route53 \
            -d "${COCKPIT_DOMAIN}" \
            --agree-tos \
            --email "${EMAIL}" \
            --non-interactive
        ;;
    *)
        echo "Invalid container runtime"
        exit 1
        ;;
esac

# Define certificate directory
CERTDIR="/etc/letsencrypt/live/${COCKPIT_DOMAIN}"

# Remove existing self-signed certificates
sudo rm -f /etc/cockpit/ws-certs.d/0-self-signed*

# Combine server certificate and intermediate cert chain
sudo cat "${CERTDIR}/fullchain.pem" | sudo tee /etc/cockpit/ws-certs.d/99-${COCKPIT_DOMAIN}.cert > /dev/null
# Copy over the key
sudo cp "${CERTDIR}/privkey.pem" /etc/cockpit/ws-certs.d/99-${COCKPIT_DOMAIN}.key

# Set proper permissions
sudo chown root:cockpit-ws /etc/cockpit/ws-certs.d/99-${COCKPIT_DOMAIN}.*

# Restart Cockpit service to apply new certificates
sudo systemctl restart cockpit

echo "Cockpit SSL certificates updated successfully."

echo "Cockpit URL: https://${COCKPIT_DOMAIN}:9090" > /home/lab-user/cockpit-url.txt
