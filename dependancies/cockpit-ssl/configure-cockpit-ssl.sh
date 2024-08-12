#!/bin/bash
set -xe 

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <AWS_ACCESS_KEY> <AWS_SECRET_ACCESS_KEY> <CONTAINER_RUN_TIME>"
    exit 1
fi

AWS_ACCESS_KEY_ID="$1"
AWS_SECRET_ACCESS_KEY="$2"
CONTAINER_RUN_TIME="$3"

# Obtain domain and API URL from Cockpit configurations
export COCKPIT_DOMAIN="your-cockpit-domain.com" # Update this with the actual domain
export COCKPIT_CERT_DIR="/etc/cockpit/ws-certs.d"

if [[ "$CONTAINER_RUN_TIME" == "docker" ]]; then
    echo "Using Docker"
    docker run --rm -it --env AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" --env AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -v "/etc/letsencrypt:/etc/letsencrypt" certbot/dns-route53 certonly --dns-route53 -d "$COCKPIT_DOMAIN" -d "*.$COCKPIT_DOMAIN" --agree-tos
elif [[ "$CONTAINER_RUN_TIME" == "podman" ]]; then
    echo "Using Podman"
    mkdir -p /etc/letsencrypt/
    podman run --rm -it \
        --env AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
        --env AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
        -v "/etc/letsencrypt:/etc/letsencrypt:Z" \
        certbot/dns-route53 \
        certonly --dns-route53 \
        -d "$COCKPIT_DOMAIN" \
        -d "*.$COCKPIT_DOMAIN" \
        --agree-tos 
else
    echo "Invalid container runtime"
    exit 1
fi

CERTDIR="/etc/letsencrypt/live/$COCKPIT_DOMAIN"
sudo cp "${CERTDIR}/fullchain.pem" "${COCKPIT_CERT_DIR}/0-ssl.pem"
sudo cp "${CERTDIR}/privkey.pem" "${COCKPIT_CERT_DIR}/0-ssl-key.pem"

# Restart Cockpit service to apply new certificates
sudo systemctl restart cockpit

echo "Cockpit SSL certificates updated successfully."
