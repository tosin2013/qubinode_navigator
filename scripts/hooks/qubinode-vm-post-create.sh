#!/bin/bash
# =============================================================================
# qubinode-vm-post-create.sh - VM Post-Create Hook
# ADR-0055: Zero-Friction Infrastructure Services
# =============================================================================
#
# This hook is called after a VM is created to automatically:
# 1. Register DNS records (A + PTR) in FreeIPA
# 2. Request and install TLS certificates
#
# Usage (called automatically by kcli or manually):
#   qubinode-vm-post-create.sh <vm_name> [vm_ip]
#
# Environment variables:
#   QUBINODE_DOMAIN     - Domain name (default: example.com)
#   QUBINODE_AUTO_DNS   - Enable auto DNS (default: true)
#   QUBINODE_AUTO_CERT  - Enable auto certificate (default: true)
#   QUBINODE_CERT_SERVICE - Service type for cert (default: generic)
#
set -euo pipefail

LOG_FILE="${QUBINODE_HOOK_LOG:-/var/log/qubinode-hooks.log}"

# Configuration
DOMAIN="${QUBINODE_DOMAIN:-example.com}"
AUTO_DNS="${QUBINODE_AUTO_DNS:-true}"
AUTO_CERT="${QUBINODE_AUTO_CERT:-true}"
CERT_SERVICE="${QUBINODE_CERT_SERVICE:-generic}"
SCRIPTS_DIR="${QUBINODE_SCRIPTS_DIR:-/opt/qubinode_navigator/scripts}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    local msg="$(date -Iseconds) [POST-CREATE] $1"
    echo -e "${GREEN}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

log_warn() {
    local msg="$(date -Iseconds) [POST-CREATE] [WARN] $1"
    echo -e "${YELLOW}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

log_error() {
    local msg="$(date -Iseconds) [POST-CREATE] [ERROR] $1"
    echo -e "${RED}$msg${NC}" >&2
    echo "$msg" >> "$LOG_FILE"
}

# Get VM IP from kcli
get_vm_ip() {
    local vm_name="$1"
    local max_attempts=30
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        attempt=$((attempt + 1))
        local ip
        ip=$(kcli info vm "$vm_name" 2>/dev/null | grep "^ip:" | awk '{print $2}' | head -1)

        if [[ -n "$ip" && "$ip" != "None" ]]; then
            echo "$ip"
            return 0
        fi

        sleep 5
    done

    return 1
}

# Main
main() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <vm_name> [vm_ip]"
        exit 1
    fi

    local vm_name="$1"
    local vm_ip="${2:-}"

    log "Processing VM: $vm_name"

    # Get IP if not provided
    if [[ -z "$vm_ip" ]]; then
        log "Getting IP for VM: $vm_name"
        vm_ip=$(get_vm_ip "$vm_name") || {
            log_error "Could not get IP for VM: $vm_name"
            exit 1
        }
    fi

    log "VM IP: $vm_ip"

    # Construct FQDN
    local fqdn="${vm_name}.${DOMAIN}"
    log "FQDN: $fqdn"

    # Register DNS
    if [[ "$AUTO_DNS" == "true" ]]; then
        log "Registering DNS record..."

        if [[ -x "$SCRIPTS_DIR/qubinode-dns" ]]; then
            "$SCRIPTS_DIR/qubinode-dns" add "$fqdn" "$vm_ip" --ptr || {
                log_warn "DNS registration failed (FreeIPA may not be available)"
            }
            log "DNS record registered: $fqdn -> $vm_ip"
        else
            log_warn "qubinode-dns not found, skipping DNS registration"
        fi
    else
        log "Auto DNS disabled, skipping"
    fi

    # Request certificate
    if [[ "$AUTO_CERT" == "true" ]]; then
        log "Requesting certificate..."

        if [[ -x "$SCRIPTS_DIR/qubinode-cert" ]]; then
            "$SCRIPTS_DIR/qubinode-cert" request "$fqdn" \
                --san "$vm_name" \
                --san "$vm_ip" \
                --service "$CERT_SERVICE" || {
                log_warn "Certificate request failed (CA may not be available)"
            }
            log "Certificate requested for: $fqdn"
        else
            log_warn "qubinode-cert not found, skipping certificate request"
        fi
    else
        log "Auto certificate disabled, skipping"
    fi

    # Update inventory
    local inventory_file="/etc/qubinode/certs/inventory.json"
    if [[ -f "$inventory_file" ]]; then
        log "Updating certificate inventory..."

        # Add entry if not exists
        local temp_file
        temp_file=$(mktemp)
        jq --arg hostname "$fqdn" --arg ip "$vm_ip" \
            '.certificates += [{"hostname": $hostname, "ip": $ip, "created": now | todate}] | .certificates |= unique_by(.hostname)' \
            "$inventory_file" > "$temp_file" 2>/dev/null && \
        mv "$temp_file" "$inventory_file" || rm -f "$temp_file"
    fi

    log "Post-create hook completed for: $vm_name"
    echo ""
    echo "========================================"
    echo "VM Ready: $vm_name"
    echo "========================================"
    echo "FQDN: $fqdn"
    echo "IP: $vm_ip"
    echo "SSH: ssh cloud-user@$vm_ip"
    if [[ "$AUTO_CERT" == "true" ]]; then
        echo "Certs: /etc/qubinode/certs/$fqdn/"
    fi
    echo "========================================"
}

main "$@"
