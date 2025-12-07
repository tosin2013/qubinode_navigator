#!/bin/bash
# =============================================================================
# Sync Credentials to Airflow Variables
# =============================================================================
#
# This script syncs credentials from various sources to Airflow Variables:
# 1. Ansible Vault (vault.yml) -> Airflow Variables
# 2. HashiCorp Vault -> Airflow Variables (if enabled)
# 3. Environment variables -> Airflow Variables
#
# This makes credentials easily accessible to DAGs via:
#   from airflow.models import Variable
#   password = Variable.get("rhsm_password", default_var="")
#
# Usage:
#   ./sync-credentials-to-airflow.sh [--source ansible|vault|env|all]
#
# Prerequisites:
#   - Airflow running with admin access
#   - For Ansible Vault: ~/.vault_password file and vault.yml
#   - For HashiCorp Vault: vault CLI and VAULT_ADDR/VAULT_TOKEN
#
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AIRFLOW_URL="${AIRFLOW_URL:-http://localhost:8888}"
AIRFLOW_USER="${AIRFLOW_USER:-admin}"
AIRFLOW_PASSWORD="${AIRFLOW_PASSWORD:-admin}"
VAULT_PASSWORD_FILE="${VAULT_PASSWORD_FILE:-$HOME/.vault_password}"
INVENTORY="${INVENTORY:-localhost}"

# HashiCorp Vault configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_MOUNT_POINT="${VAULT_MOUNT_POINT:-qubinode}"

# =============================================================================
# Utility Functions
# =============================================================================

check_airflow_connection() {
    log_info "Checking Airflow connection at $AIRFLOW_URL..."
    if curl -s -u "$AIRFLOW_USER:$AIRFLOW_PASSWORD" "$AIRFLOW_URL/api/v1/health" | grep -q "healthy"; then
        log_success "Airflow is accessible"
        return 0
    else
        log_error "Cannot connect to Airflow at $AIRFLOW_URL"
        log_info "Make sure Airflow is running and credentials are correct"
        return 1
    fi
}

set_airflow_variable() {
    local key="$1"
    local value="$2"
    local description="${3:-Synced from external source}"

    # Skip if value is empty or contains placeholder
    if [[ -z "$value" ]] || [[ "$value" == "CHANGEME" ]] || [[ "$value" == '""' ]]; then
        log_warning "Skipping $key: empty or placeholder value"
        return 0
    fi

    log_info "Setting Airflow variable: $key"

    # Use Airflow REST API to set variable
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -u "$AIRFLOW_USER:$AIRFLOW_PASSWORD" \
        -H "Content-Type: application/json" \
        -d "{\"key\": \"$key\", \"value\": \"$value\", \"description\": \"$description\"}" \
        "$AIRFLOW_URL/api/v1/variables" 2>/dev/null)

    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        log_success "Set variable: $key"
        return 0
    elif [[ "$http_code" == "409" ]]; then
        # Variable exists, try to update it
        response=$(curl -s -w "\n%{http_code}" -X PATCH \
            -u "$AIRFLOW_USER:$AIRFLOW_PASSWORD" \
            -H "Content-Type: application/json" \
            -d "{\"key\": \"$key\", \"value\": \"$value\", \"description\": \"$description\"}" \
            "$AIRFLOW_URL/api/v1/variables/$key" 2>/dev/null)

        http_code=$(echo "$response" | tail -1)
        if [[ "$http_code" == "200" ]]; then
            log_success "Updated variable: $key"
            return 0
        fi
    fi

    log_warning "Failed to set variable $key (HTTP $http_code)"
    return 1
}

# =============================================================================
# Source: Ansible Vault
# =============================================================================

sync_from_ansible_vault() {
    log_info "Syncing credentials from Ansible Vault..."

    local vault_file="$REPO_ROOT/inventories/$INVENTORY/group_vars/control/vault.yml"

    if [[ ! -f "$vault_file" ]]; then
        log_warning "Vault file not found: $vault_file"
        return 1
    fi

    if [[ ! -f "$VAULT_PASSWORD_FILE" ]]; then
        log_error "Vault password file not found: $VAULT_PASSWORD_FILE"
        return 1
    fi

    # Check if file is encrypted
    if head -1 "$vault_file" | grep -q '^\$ANSIBLE_VAULT'; then
        log_info "Decrypting Ansible Vault file..."
        local decrypted
        decrypted=$(ansible-vault view "$vault_file" --vault-password-file "$VAULT_PASSWORD_FILE" 2>/dev/null) || {
            log_error "Failed to decrypt vault file"
            return 1
        }
    else
        log_info "Vault file is not encrypted, reading directly..."
        decrypted=$(cat "$vault_file")
    fi

    # Parse YAML and extract variables
    # Using grep/sed for simple extraction (yq would be better but may not be installed)
    local vars_to_sync=(
        "freeipa_server_admin_password"
        "rhsm_org"
        "rhsm_activationkey"
        "rhsm_username"
        "rhsm_password"
        "openshift_pull_secret"
        "quay_password"
        "registry_password"
    )

    local synced=0
    for var in "${vars_to_sync[@]}"; do
        local value
        value=$(echo "$decrypted" | grep "^${var}:" | sed 's/^[^:]*: *//' | tr -d '"' | tr -d "'")

        if [[ -n "$value" ]] && [[ "$value" != '""' ]] && [[ "$value" != "''" ]]; then
            if set_airflow_variable "$var" "$value" "Synced from Ansible Vault"; then
                ((synced++))
            fi
        fi
    done

    log_success "Synced $synced variables from Ansible Vault"
    return 0
}

# =============================================================================
# Source: HashiCorp Vault
# =============================================================================

sync_from_hashicorp_vault() {
    log_info "Syncing credentials from HashiCorp Vault..."

    if ! command -v vault &> /dev/null; then
        log_warning "vault CLI not found, skipping HashiCorp Vault sync"
        return 1
    fi

    # Check Vault connectivity
    if ! vault status > /dev/null 2>&1; then
        log_warning "Cannot connect to Vault at $VAULT_ADDR"
        return 1
    fi

    # Sync variables from Vault KV store
    log_info "Reading variables from $VAULT_MOUNT_POINT/variables/..."

    local vars_path="$VAULT_MOUNT_POINT/data/variables/qubinode_config"
    local vault_data
    vault_data=$(vault kv get -format=json "$VAULT_MOUNT_POINT/variables/qubinode_config" 2>/dev/null) || {
        log_warning "No variables found in Vault at $vars_path"
        return 0
    }

    # Parse JSON and sync to Airflow
    local synced=0
    for key in $(echo "$vault_data" | jq -r '.data.data | keys[]' 2>/dev/null); do
        local value
        value=$(echo "$vault_data" | jq -r ".data.data[\"$key\"]" 2>/dev/null)
        if [[ -n "$value" ]] && [[ "$value" != "null" ]]; then
            if set_airflow_variable "$key" "$value" "Synced from HashiCorp Vault"; then
                ((synced++))
            fi
        fi
    done

    # Also sync connection secrets if they exist
    log_info "Reading connection secrets from $VAULT_MOUNT_POINT/connections/..."
    local conn_list
    conn_list=$(vault kv list -format=json "$VAULT_MOUNT_POINT/connections" 2>/dev/null) || {
        log_info "No connections found in Vault"
        conn_list="[]"
    }

    for conn in $(echo "$conn_list" | jq -r '.[]' 2>/dev/null); do
        log_info "Found connection secret: $conn (use Airflow Vault backend for full integration)"
    done

    log_success "Synced $synced variables from HashiCorp Vault"
    return 0
}

# =============================================================================
# Source: Environment Variables
# =============================================================================

sync_from_environment() {
    log_info "Syncing credentials from environment variables..."

    # List of environment variables to sync
    local env_vars=(
        "SSH_PASSWORD"
        "RHSM_ORG:rhsm_org"
        "RHSM_ACTIVATIONKEY:rhsm_activationkey"
        "RHSM_USERNAME:rhsm_username"
        "RHSM_PASSWORD:rhsm_password"
        "OPENSHIFT_PULL_SECRET:openshift_pull_secret"
        "QUAY_PASSWORD:quay_password"
        "REGISTRY_PASSWORD:registry_password"
        "HETZNER_TOKEN:hetzner_token"
        "AWS_ACCESS_KEY_ID:aws_access_key_id"
        "AWS_SECRET_ACCESS_KEY:aws_secret_access_key"
    )

    local synced=0
    for mapping in "${env_vars[@]}"; do
        local env_name="${mapping%%:*}"
        local airflow_name="${mapping##*:}"

        # If no mapping, use lowercase env name
        if [[ "$env_name" == "$airflow_name" ]]; then
            airflow_name=$(echo "$env_name" | tr '[:upper:]' '[:lower:]')
        fi

        local value="${!env_name:-}"
        if [[ -n "$value" ]]; then
            if set_airflow_variable "$airflow_name" "$value" "Synced from environment variable $env_name"; then
                ((synced++))
            fi
        fi
    done

    log_success "Synced $synced variables from environment"
    return 0
}

# =============================================================================
# Main
# =============================================================================

main() {
    local source="${1:-all}"

    echo "=============================================="
    echo "Sync Credentials to Airflow Variables"
    echo "=============================================="
    echo ""
    echo "Airflow URL: $AIRFLOW_URL"
    echo "Source: $source"
    echo ""

    # Check Airflow connection first
    check_airflow_connection || exit 1

    case "$source" in
        ansible)
            sync_from_ansible_vault
            ;;
        vault|hashicorp)
            sync_from_hashicorp_vault
            ;;
        env|environment)
            sync_from_environment
            ;;
        all)
            log_info "Syncing from all sources..."
            sync_from_environment || true
            sync_from_ansible_vault || true
            sync_from_hashicorp_vault || true
            ;;
        *)
            echo "Usage: $0 [--source ansible|vault|env|all]"
            exit 1
            ;;
    esac

    echo ""
    log_success "Credential sync completed!"
    echo ""
    echo "Variables are now available in DAGs via:"
    echo "  from airflow.models import Variable"
    echo "  password = Variable.get('rhsm_password', default_var='')"
    echo ""
    echo "For more secure access, consider using HashiCorp Vault backend:"
    echo "  See: airflow/dags/examples/vault_dynamic_secrets_example.py"
    echo ""
}

# Handle arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--source ansible|vault|env|all]"
        echo ""
        echo "Sync credentials from various sources to Airflow Variables"
        echo ""
        echo "Sources:"
        echo "  ansible    - Sync from Ansible Vault (inventories/*/group_vars/control/vault.yml)"
        echo "  vault      - Sync from HashiCorp Vault (qubinode/ mount point)"
        echo "  env        - Sync from environment variables"
        echo "  all        - Sync from all sources (default)"
        echo ""
        echo "Environment Variables:"
        echo "  AIRFLOW_URL       - Airflow API URL (default: http://localhost:8888)"
        echo "  AIRFLOW_USER      - Airflow admin user (default: admin)"
        echo "  AIRFLOW_PASSWORD  - Airflow admin password (default: admin)"
        echo "  VAULT_PASSWORD_FILE - Path to Ansible vault password (default: ~/.vault_password)"
        echo "  VAULT_ADDR        - HashiCorp Vault address (default: http://localhost:8200)"
        echo "  INVENTORY         - Inventory name for Ansible Vault (default: localhost)"
        echo ""
        exit 0
        ;;
    --source)
        main "${2:-all}"
        ;;
    *)
        main "${1:-all}"
        ;;
esac
