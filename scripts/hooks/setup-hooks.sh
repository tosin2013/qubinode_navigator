#!/bin/bash
# =============================================================================
# setup-hooks.sh - Install VM Lifecycle Hooks
# ADR-0055: Zero-Friction Infrastructure Services
# =============================================================================
#
# This script installs the qubinode VM lifecycle hooks for automatic
# DNS and certificate management.
#
# Usage:
#   ./setup-hooks.sh [--uninstall]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="/etc/kcli/hooks.d"
SYSTEMD_DIR="/etc/systemd/system"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

install_hooks() {
    log_info "Installing Qubinode VM lifecycle hooks..."

    # Create hooks directory
    mkdir -p "$HOOKS_DIR"

    # Copy hook scripts
    cp "$SCRIPT_DIR/qubinode-vm-post-create.sh" "$HOOKS_DIR/"
    cp "$SCRIPT_DIR/qubinode-vm-pre-delete.sh" "$HOOKS_DIR/"
    chmod +x "$HOOKS_DIR"/*.sh

    log_info "Hooks installed to: $HOOKS_DIR"

    # Create log directory
    mkdir -p /var/log
    touch /var/log/qubinode-hooks.log

    # Create configuration directory
    mkdir -p /etc/qubinode
    mkdir -p /etc/qubinode/certs/ca

    # Create default configuration if not exists
    if [[ ! -f /etc/qubinode/infra.conf ]]; then
        cat > /etc/qubinode/infra.conf << 'EOF'
# Qubinode Infrastructure Configuration
# ADR-0055: Zero-Friction Infrastructure Services

[general]
domain = example.com
auto_dns = true
auto_cert = true

[dns]
provider = auto
# freeipa_server = ipa.example.com
# freeipa_realm = EXAMPLE.COM

[ca]
provider = auto
# step_ca_url = https://step-ca.example.com:443
# vault_addr = http://vault.example.com:8200

[hooks]
enabled = true
on_create = /etc/kcli/hooks.d/qubinode-vm-post-create.sh
on_delete = /etc/kcli/hooks.d/qubinode-vm-pre-delete.sh
EOF
        log_info "Default configuration created: /etc/qubinode/infra.conf"
    fi

    # Initialize certificate inventory
    if [[ ! -f /etc/qubinode/certs/inventory.json ]]; then
        echo '{"certificates": [], "last_updated": "'$(date -Iseconds)'"}' > /etc/qubinode/certs/inventory.json
        log_info "Certificate inventory initialized"
    fi

    # Create kcli wrapper that calls hooks
    if [[ -f /usr/local/bin/kcli-with-hooks ]]; then
        log_warn "kcli wrapper already exists"
    else
        cat > /usr/local/bin/kcli-with-hooks << 'WRAPPER'
#!/bin/bash
# kcli wrapper with Qubinode hooks
# ADR-0055: Zero-Friction Infrastructure Services

HOOKS_DIR="/etc/kcli/hooks.d"
HOOKS_ENABLED="${QUBINODE_HOOKS_ENABLED:-true}"

# Run original kcli
/usr/local/bin/kcli "$@"
EXIT_CODE=$?

# Only run hooks if kcli succeeded and hooks are enabled
if [[ $EXIT_CODE -eq 0 && "$HOOKS_ENABLED" == "true" ]]; then
    case "$1" in
        create)
            if [[ "$2" == "vm" && -n "$3" ]]; then
                VM_NAME="$3"
                if [[ -x "$HOOKS_DIR/qubinode-vm-post-create.sh" ]]; then
                    # Run hook in background after VM is created
                    (sleep 10 && "$HOOKS_DIR/qubinode-vm-post-create.sh" "$VM_NAME") &
                fi
            fi
            ;;
        delete)
            if [[ "$2" == "vm" && -n "$3" ]]; then
                VM_NAME="$3"
                if [[ -x "$HOOKS_DIR/qubinode-vm-pre-delete.sh" ]]; then
                    "$HOOKS_DIR/qubinode-vm-pre-delete.sh" "$VM_NAME"
                fi
            fi
            ;;
    esac
fi

exit $EXIT_CODE
WRAPPER
        chmod +x /usr/local/bin/kcli-with-hooks
        log_info "kcli wrapper created: /usr/local/bin/kcli-with-hooks"
    fi

    # Create alias script
    cat > /etc/profile.d/qubinode-hooks.sh << 'PROFILE'
# Qubinode VM lifecycle hooks
# To enable automatic DNS and certificate management, use:
#   kcli-with-hooks create vm myvm ...
# Or set alias:
#   alias kcli='kcli-with-hooks'

export QUBINODE_DOMAIN="${QUBINODE_DOMAIN:-example.com}"
export QUBINODE_AUTO_DNS="${QUBINODE_AUTO_DNS:-true}"
export QUBINODE_AUTO_CERT="${QUBINODE_AUTO_CERT:-true}"
export QUBINODE_SCRIPTS_DIR="${QUBINODE_SCRIPTS_DIR:-/opt/qubinode_navigator/scripts}"
PROFILE
    log_info "Profile script created: /etc/profile.d/qubinode-hooks.sh"

    echo ""
    log_info "Hooks installation complete!"
    echo ""
    echo "To use automatic DNS/certificate management:"
    echo "  1. Use kcli-with-hooks instead of kcli:"
    echo "     kcli-with-hooks create vm myservice -i centos9stream"
    echo ""
    echo "  2. Or call hooks manually after VM creation:"
    echo "     $HOOKS_DIR/qubinode-vm-post-create.sh myservice"
    echo ""
    echo "Configuration: /etc/qubinode/infra.conf"
    echo "Logs: /var/log/qubinode-hooks.log"
}

uninstall_hooks() {
    log_info "Uninstalling Qubinode VM lifecycle hooks..."

    rm -f "$HOOKS_DIR/qubinode-vm-post-create.sh"
    rm -f "$HOOKS_DIR/qubinode-vm-pre-delete.sh"
    rm -f /usr/local/bin/kcli-with-hooks
    rm -f /etc/profile.d/qubinode-hooks.sh

    log_info "Hooks uninstalled"
    log_warn "Configuration preserved: /etc/qubinode/infra.conf"
}

# Main
case "${1:-}" in
    --uninstall|-u)
        uninstall_hooks
        ;;
    --help|-h)
        echo "Usage: $0 [--uninstall]"
        echo ""
        echo "Install Qubinode VM lifecycle hooks for automatic DNS and certificate management."
        echo ""
        echo "Options:"
        echo "  --uninstall, -u    Remove installed hooks"
        echo "  --help, -h         Show this help"
        ;;
    *)
        install_hooks
        ;;
esac
