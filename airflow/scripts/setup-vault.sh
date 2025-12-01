#!/bin/bash
# =============================================================================
# Vault Setup Script for Qubinode Airflow Integration
# ADR-0051: HashiCorp Vault Secrets Management
# =============================================================================
#
# This script configures Vault for use with Airflow:
# 1. Enables KV v2 secrets engine for connections/variables
# 2. Enables database secrets engine for PostgreSQL dynamic credentials
# 3. Creates AppRole for Airflow authentication
# 4. Sets up policies for least-privilege access
#
# Usage:
#   ./setup-vault.sh [--dev-mode]
#
# Prerequisites:
#   - Vault server running (docker-compose --profile vault up)
#   - VAULT_ADDR and VAULT_TOKEN environment variables set
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
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-qubinode-dev-token}"
MOUNT_POINT="${VAULT_MOUNT_POINT:-qubinode}"

export VAULT_ADDR VAULT_TOKEN

# Check if vault CLI is available
if ! command -v vault &> /dev/null; then
    log_error "vault CLI not found. Install with: dnf install vault"
    exit 1
fi

# Check Vault connectivity
log_info "Checking Vault connectivity at ${VAULT_ADDR}..."
if ! vault status > /dev/null 2>&1; then
    log_error "Cannot connect to Vault at ${VAULT_ADDR}"
    log_info "Start Vault with: cd airflow && podman-compose --profile vault up -d"
    exit 1
fi

log_success "Connected to Vault"

# =============================================================================
# 1. Enable KV v2 Secrets Engine
# =============================================================================
log_info "Enabling KV v2 secrets engine at ${MOUNT_POINT}/..."

if vault secrets list | grep -q "^${MOUNT_POINT}/"; then
    log_warning "Secrets engine already enabled at ${MOUNT_POINT}/"
else
    vault secrets enable -path="${MOUNT_POINT}" kv-v2
    log_success "KV v2 secrets engine enabled"
fi

# =============================================================================
# 2. Create Path Structure for Airflow
# =============================================================================
log_info "Creating secrets path structure..."

# Store sample connection (PostgreSQL)
vault kv put "${MOUNT_POINT}/connections/postgres_default" \
    conn_uri="postgresql://airflow:airflow@localhost:5432/airflow" \
    conn_type="postgres" \
    host="localhost" \
    port="5432" \
    login="airflow" \
    password="airflow" \
    schema="airflow"

log_success "Created sample postgres_default connection"

# Store sample variables
vault kv put "${MOUNT_POINT}/variables/qubinode_config" \
    environment="development" \
    log_level="INFO" \
    embedding_service_url="http://localhost:8891" \
    litellm_proxy_url="http://localhost:4000"

log_success "Created sample variables"

# =============================================================================
# 3. Enable Database Secrets Engine (for dynamic credentials)
# =============================================================================
log_info "Enabling database secrets engine..."

if vault secrets list | grep -q "^database/"; then
    log_warning "Database secrets engine already enabled"
else
    vault secrets enable database
    log_success "Database secrets engine enabled"
fi

# Configure PostgreSQL connection (skip if already configured)
log_info "Configuring PostgreSQL dynamic secrets..."
vault write database/config/airflow-postgres \
    plugin_name=postgresql-database-plugin \
    allowed_roles="airflow-readonly,airflow-readwrite" \
    connection_url="postgresql://{{username}}:{{password}}@localhost:5432/airflow?sslmode=disable" \
    username="airflow" \
    password="airflow" 2>/dev/null || log_warning "PostgreSQL config may already exist"

# Create read-only role
vault write database/roles/airflow-readonly \
    db_name=airflow-postgres \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h" 2>/dev/null || log_warning "airflow-readonly role may already exist"

log_success "Database dynamic secrets configured"

# =============================================================================
# 4. Create Policies
# =============================================================================
log_info "Creating Vault policies..."

# Airflow read policy
cat <<EOF | vault policy write airflow-read -
# Airflow read-only access to secrets
path "${MOUNT_POINT}/data/connections/*" {
  capabilities = ["read", "list"]
}

path "${MOUNT_POINT}/data/variables/*" {
  capabilities = ["read", "list"]
}

path "${MOUNT_POINT}/metadata/*" {
  capabilities = ["list"]
}

# Dynamic database credentials
path "database/creds/airflow-readonly" {
  capabilities = ["read"]
}
EOF

log_success "Created airflow-read policy"

# Airflow admin policy (for DAG development)
cat <<EOF | vault policy write airflow-admin -
# Airflow admin access (for development)
path "${MOUNT_POINT}/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "database/creds/*" {
  capabilities = ["read"]
}

path "sys/leases/revoke" {
  capabilities = ["update"]
}
EOF

log_success "Created airflow-admin policy"

# =============================================================================
# 5. Enable AppRole Authentication
# =============================================================================
log_info "Enabling AppRole authentication..."

if vault auth list | grep -q "^approle/"; then
    log_warning "AppRole auth already enabled"
else
    vault auth enable approle
    log_success "AppRole auth enabled"
fi

# Create AppRole for Airflow
vault write auth/approle/role/airflow \
    token_policies="airflow-read" \
    token_ttl="1h" \
    token_max_ttl="4h" \
    secret_id_ttl="720h" \
    secret_id_num_uses=0

# Get role_id and secret_id
ROLE_ID=$(vault read -field=role_id auth/approle/role/airflow/role-id)
SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/airflow/secret-id)

log_success "Created AppRole for Airflow"

# =============================================================================
# 6. Enable Audit Logging (ADR-0052)
# =============================================================================
log_info "Enabling audit logging..."

if vault audit list | grep -q "^file/"; then
    log_warning "File audit device already enabled"
else
    vault audit enable file file_path=/vault/logs/audit.log 2>/dev/null || \
        log_warning "Could not enable audit logging (may need permissions)"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
log_success "Vault setup complete!"
echo ""
echo "=============================================="
echo "Vault Configuration Summary"
echo "=============================================="
echo ""
echo "Vault Address: ${VAULT_ADDR}"
echo "Secrets Mount: ${MOUNT_POINT}/"
echo ""
echo "AppRole Credentials (for Airflow):"
echo "  Role ID:    ${ROLE_ID}"
echo "  Secret ID:  ${SECRET_ID}"
echo ""
echo "To configure Airflow secrets backend, set:"
echo ""
echo "  VAULT_SECRETS_BACKEND=airflow.providers.hashicorp.secrets.vault.VaultBackend"
echo "  VAULT_BACKEND_KWARGS='{\"connections_path\": \"connections\", \"variables_path\": \"variables\", \"mount_point\": \"${MOUNT_POINT}\", \"url\": \"${VAULT_ADDR}\", \"auth_type\": \"approle\", \"role_id\": \"${ROLE_ID}\", \"secret_id\": \"${SECRET_ID}\"}'"
echo ""
echo "Or create Airflow connection 'vault_default' with:"
echo "  Connection Type: HTTP"
echo "  Host: ${VAULT_ADDR}"
echo "  Login: ${ROLE_ID}"
echo "  Password: ${SECRET_ID}"
echo ""
echo "Test dynamic credentials:"
echo "  vault read database/creds/airflow-readonly"
echo ""
