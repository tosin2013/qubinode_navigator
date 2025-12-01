#!/bin/bash
# =============================================================================
# qubinode-vm-pre-delete.sh - VM Pre-Delete Hook
# ADR-0055: Zero-Friction Infrastructure Services
# =============================================================================
#
# This hook is called before a VM is deleted to automatically:
# 1. Remove DNS records from FreeIPA
# 2. Revoke TLS certificates (optional)
# 3. Clean up inventory
#
# Usage (called automatically by kcli or manually):
#   qubinode-vm-pre-delete.sh <vm_name>
#
# Environment variables:
#   QUBINODE_DOMAIN     - Domain name (default: example.com)
#   QUBINODE_AUTO_DNS   - Enable auto DNS cleanup (default: true)
#   QUBINODE_REVOKE_CERT - Revoke certificate on delete (default: false)
#
set -euo pipefail

LOG_FILE="${QUBINODE_HOOK_LOG:-/var/log/qubinode-hooks.log}"

# Configuration
DOMAIN="${QUBINODE_DOMAIN:-example.com}"
AUTO_DNS="${QUBINODE_AUTO_DNS:-true}"
REVOKE_CERT="${QUBINODE_REVOKE_CERT:-false}"
SCRIPTS_DIR="${QUBINODE_SCRIPTS_DIR:-/opt/qubinode_navigator/scripts}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    local msg="$(date -Iseconds) [PRE-DELETE] $1"
    echo -e "${GREEN}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

log_warn() {
    local msg="$(date -Iseconds) [PRE-DELETE] [WARN] $1"
    echo -e "${YELLOW}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

log_error() {
    local msg="$(date -Iseconds) [PRE-DELETE] [ERROR] $1"
    echo -e "${RED}$msg${NC}" >&2
    echo "$msg" >> "$LOG_FILE"
}

# Main
main() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <vm_name>"
        exit 1
    fi

    local vm_name="$1"

    log "Processing VM deletion: $vm_name"

    # Construct FQDN
    local fqdn="${vm_name}.${DOMAIN}"
    log "FQDN: $fqdn"

    # Remove DNS
    if [[ "$AUTO_DNS" == "true" ]]; then
        log "Removing DNS record..."

        if [[ -x "$SCRIPTS_DIR/qubinode-dns" ]]; then
            "$SCRIPTS_DIR/qubinode-dns" remove "$fqdn" || {
                log_warn "DNS removal failed (record may not exist)"
            }
            log "DNS record removed: $fqdn"
        else
            log_warn "qubinode-dns not found, skipping DNS cleanup"
        fi
    else
        log "Auto DNS cleanup disabled, skipping"
    fi

    # Revoke certificate (optional)
    if [[ "$REVOKE_CERT" == "true" ]]; then
        log "Revoking certificate..."

        if [[ -x "$SCRIPTS_DIR/qubinode-cert" ]]; then
            "$SCRIPTS_DIR/qubinode-cert" revoke "$fqdn" || {
                log_warn "Certificate revocation failed"
            }
            log "Certificate revoked for: $fqdn"
        else
            log_warn "qubinode-cert not found, skipping certificate revocation"
        fi
    fi

    # Clean up local certificate files
    local cert_dir="/etc/qubinode/certs/$fqdn"
    if [[ -d "$cert_dir" ]]; then
        log "Removing local certificate files: $cert_dir"
        rm -rf "$cert_dir"
    fi

    # Update inventory
    local inventory_file="/etc/qubinode/certs/inventory.json"
    if [[ -f "$inventory_file" ]]; then
        log "Updating certificate inventory..."

        local temp_file
        temp_file=$(mktemp)
        jq --arg hostname "$fqdn" \
            '.certificates |= map(select(.hostname != $hostname))' \
            "$inventory_file" > "$temp_file" 2>/dev/null && \
        mv "$temp_file" "$inventory_file" || rm -f "$temp_file"
    fi

    log "Pre-delete hook completed for: $vm_name"
}

main "$@"
