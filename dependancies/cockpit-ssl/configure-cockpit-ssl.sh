#!/bin/bash
# https://kenmoini.com/post/2021/12/custom-certificates-in-cockpit/
set -xe
# Decrypt the vault file to access AWS credentials
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 2

# Extract required AWS credentials using yq
AWS_ACCESS_KEY_ID=$(yq eval '.aws_access_key' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")
AWS_SECRET_ACCESS_KEY=$(yq eval '.aws_secret_key' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")

# Re-encrypt the vault file
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1

# Define constants
CONTAINER_RUN_TIME="podman" # Ensure this is set correctly based on the runtime environment
COCKPIT_DOMAIN="cockpit.${GUID}.${DOMAIN}" # Ensure GUID and DOMAIN are set correctly
COCKPIT_CERT_DIR="/etc/cockpit/ws-certs.d"

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
