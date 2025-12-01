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
# 6. Enable PKI Secrets Engine (ADR-0054: Unified Certificate Management)
# =============================================================================
log_info "Enabling PKI secrets engine for certificate management..."

PKI_DOMAIN="${PKI_DOMAIN:-example.com}"
PKI_MOUNT="${PKI_MOUNT:-pki}"

if vault secrets list | grep -q "^${PKI_MOUNT}/"; then
    log_warning "PKI secrets engine already enabled at ${PKI_MOUNT}/"
else
    vault secrets enable -path="${PKI_MOUNT}" pki
    log_success "PKI secrets engine enabled"

    # Set max TTL to 10 years for root CA
    vault secrets tune -max-lease-ttl=87600h "${PKI_MOUNT}"
fi

# Generate internal root CA (for development/testing)
log_info "Configuring PKI root CA..."
if ! vault read "${PKI_MOUNT}/cert/ca" &>/dev/null; then
    vault write "${PKI_MOUNT}/root/generate/internal" \
        common_name="Qubinode Root CA" \
        issuer_name="qubinode-root" \
        ttl=87600h \
        key_bits=4096 2>/dev/null || log_warning "Root CA may already exist"

    log_success "Generated internal root CA"
fi

# Configure CA and CRL URLs
vault write "${PKI_MOUNT}/config/urls" \
    issuing_certificates="${VAULT_ADDR}/v1/${PKI_MOUNT}/ca" \
    crl_distribution_points="${VAULT_ADDR}/v1/${PKI_MOUNT}/crl" 2>/dev/null || true

# Create a role for issuing certificates
log_info "Creating PKI issuer role..."
vault write "${PKI_MOUNT}/roles/qubinode-issuer" \
    allowed_domains="${PKI_DOMAIN}" \
    allow_subdomains=true \
    allow_localhost=true \
    allow_ip_sans=true \
    allow_any_name=true \
    max_ttl=8760h \
    ttl=720h \
    key_bits=2048 \
    key_type=rsa 2>/dev/null || log_warning "qubinode-issuer role may already exist"

# Create a short-lived role for dynamic certificates
vault write "${PKI_MOUNT}/roles/qubinode-dynamic" \
    allowed_domains="${PKI_DOMAIN}" \
    allow_subdomains=true \
    allow_localhost=true \
    allow_ip_sans=true \
    max_ttl=24h \
    ttl=1h \
    key_bits=2048 \
    key_type=rsa 2>/dev/null || log_warning "qubinode-dynamic role may already exist"

log_success "PKI secrets engine configured"

# =============================================================================
# 7. Enable SSH Secrets Engine (for SSH Certificate Authority)
# =============================================================================
log_info "Enabling SSH secrets engine for SSH CA..."

SSH_MOUNT="${SSH_MOUNT:-ssh}"

if vault secrets list | grep -q "^${SSH_MOUNT}/"; then
    log_warning "SSH secrets engine already enabled at ${SSH_MOUNT}/"
else
    vault secrets enable -path="${SSH_MOUNT}" ssh
    log_success "SSH secrets engine enabled"
fi

# Configure SSH CA
log_info "Configuring SSH CA..."
if ! vault read "${SSH_MOUNT}/config/ca" &>/dev/null 2>&1; then
    vault write "${SSH_MOUNT}/config/ca" generate_signing_key=true 2>/dev/null || \
        log_warning "SSH CA may already be configured"
    log_success "SSH CA configured"
fi

# Create SSH role for signing user keys
vault write "${SSH_MOUNT}/roles/vm-admin" \
    key_type=ca \
    default_user=root \
    allowed_users="root,cloud-user,admin,ansible" \
    allowed_extensions="permit-pty,permit-agent-forwarding" \
    ttl=1h \
    max_ttl=24h 2>/dev/null || log_warning "vm-admin SSH role may already exist"

# Create SSH role for signing host keys
vault write "${SSH_MOUNT}/roles/host-key" \
    key_type=ca \
    cert_type=host \
    allowed_domains="${PKI_DOMAIN}" \
    allow_subdomains=true \
    ttl=8760h \
    max_ttl=87600h 2>/dev/null || log_warning "host-key SSH role may already exist"

log_success "SSH secrets engine configured"

# Get SSH CA public key for trust
SSH_CA_PUBLIC_KEY=$(vault read -field=public_key "${SSH_MOUNT}/config/ca" 2>/dev/null || echo "")

# =============================================================================
# 8. Enable Audit Logging (ADR-0052)
# =============================================================================
log_info "Enabling audit logging..."

if vault audit list | grep -q "^file/"; then
    log_warning "File audit device already enabled"
else
    vault audit enable file file_path=/vault/logs/audit.log 2>/dev/null || \
        log_warning "Could not enable audit logging (may need permissions)"
fi

# =============================================================================
# 9. Update Policies for PKI and SSH
# =============================================================================
log_info "Updating policies for PKI and SSH access..."

# Certificate issuer policy
cat <<EOF | vault policy write cert-issuer -
# Certificate issuer policy (ADR-0054)
path "${PKI_MOUNT}/issue/qubinode-issuer" {
  capabilities = ["create", "update"]
}

path "${PKI_MOUNT}/issue/qubinode-dynamic" {
  capabilities = ["create", "update"]
}

path "${PKI_MOUNT}/ca/pem" {
  capabilities = ["read"]
}

path "${PKI_MOUNT}/cert/ca" {
  capabilities = ["read"]
}

# SSH certificate signing
path "${SSH_MOUNT}/sign/vm-admin" {
  capabilities = ["create", "update"]
}

path "${SSH_MOUNT}/config/ca" {
  capabilities = ["read"]
}
EOF

log_success "Created cert-issuer policy"

# Update airflow-admin policy to include PKI
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

# PKI access for certificate management
path "${PKI_MOUNT}/issue/*" {
  capabilities = ["create", "update"]
}

path "${PKI_MOUNT}/ca/pem" {
  capabilities = ["read"]
}

# SSH CA access
path "${SSH_MOUNT}/sign/*" {
  capabilities = ["create", "update"]
}

path "${SSH_MOUNT}/config/ca" {
  capabilities = ["read"]
}
EOF

log_success "Updated airflow-admin policy"

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
echo "=============================================="
echo "PKI Secrets Engine (ADR-0054)"
echo "=============================================="
echo "Mount Point:  ${PKI_MOUNT}/"
echo "Domain:       ${PKI_DOMAIN}"
echo "Roles:"
echo "  - qubinode-issuer (30 day default TTL)"
echo "  - qubinode-dynamic (1 hour default TTL)"
echo ""
echo "Request a certificate:"
echo "  vault write ${PKI_MOUNT}/issue/qubinode-issuer \\"
echo "    common_name=\"myservice.${PKI_DOMAIN}\" \\"
echo "    ttl=\"720h\""
echo ""
echo "Get root CA certificate:"
echo "  vault read -field=certificate ${PKI_MOUNT}/cert/ca"
echo ""
echo "=============================================="
echo "SSH Secrets Engine"
echo "=============================================="
echo "Mount Point:  ${SSH_MOUNT}/"
echo "Roles:"
echo "  - vm-admin (user key signing, 1h TTL)"
echo "  - host-key (host key signing, 1y TTL)"
echo ""
if [[ -n "${SSH_CA_PUBLIC_KEY:-}" ]]; then
echo "SSH CA Public Key (add to /etc/ssh/trusted-user-ca-keys.pub):"
echo "  ${SSH_CA_PUBLIC_KEY}"
fi
echo ""
echo "Sign an SSH user key:"
echo "  vault write ${SSH_MOUNT}/sign/vm-admin public_key=@~/.ssh/id_rsa.pub"
echo ""
echo "=============================================="
echo "Airflow Integration"
echo "=============================================="
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
echo "=============================================="
echo "qubinode-cert Integration"
echo "=============================================="
echo ""
echo "Configure qubinode-cert to use Vault PKI:"
echo ""
echo "  export VAULT_ADDR=${VAULT_ADDR}"
echo "  export VAULT_TOKEN=<your-token>"
echo "  qubinode-cert request myservice.${PKI_DOMAIN} --ca vault --service nginx --install"
echo ""
echo "Test commands:"
echo "  vault read database/creds/airflow-readonly"
echo "  vault write ${PKI_MOUNT}/issue/qubinode-issuer common_name=\"test.${PKI_DOMAIN}\""
echo ""
