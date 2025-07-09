# Local HashiCorp Vault Setup for Qubinode Navigator

This guide walks you through setting up a local HashiCorp Vault server for development and testing with the enhanced Qubinode Navigator configuration system.

## Why Podman for RHEL 9?

**Podman is the recommended container runtime for RHEL 9** because:
- ✅ **Pre-installed**: Included by default in RHEL 9
- ✅ **Rootless**: Runs containers without root privileges
- ✅ **Systemd Integration**: Native systemd service support
- ✅ **SELinux Compatible**: Works seamlessly with RHEL 9 security
- ✅ **Docker Compatible**: Drop-in replacement for Docker commands
- ✅ **Red Hat Supported**: Official Red Hat container runtime

## Prerequisites

1. **Linux System**: RHEL 9, Rocky Linux, or similar
2. **Podman** (RHEL 9 default), **Docker**, or **Vault Binary**
3. **Network Access**: For downloading Vault and dependencies
4. **Root/Sudo Access**: For installation and configuration

## Option A: Podman-Based Local Vault (Recommended for RHEL 9)

### A.1 Install Podman

```bash
# Podman is included by default in RHEL 9
# Verify Podman installation
podman --version

# If not installed, install Podman
sudo dnf install -y podman

# Enable Podman socket for Docker-compatible API (optional)
systemctl --user enable --now podman.socket

# Verify installation
podman info
```

### A.2 Start Vault Development Server

```bash
# Create vault data directory
mkdir -p ~/vault-data

# Start Vault in development mode using Podman (NOT for production)
podman run -d \
  --name vault-dev \
  --cap-add=IPC_LOCK \
  -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=myroot' \
  -e 'VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200' \
  -v ~/vault-data:/vault/data:Z \
  docker.io/hashicorp/vault:latest

# Verify container is running
podman ps | grep vault-dev

# Check vault logs
podman logs vault-dev
```

### A.3 Configure Environment

```bash
# Add to your .env file
cat >> .env << EOF

# =============================================================================
# LOCAL VAULT CONFIGURATION (Development)
# =============================================================================

# Enable local vault integration
USE_HASHICORP_VAULT=true
USE_HASHICORP_CLOUD=false

# Local vault server configuration
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=myroot

# Development settings
VAULT_DEV_MODE=true
EOF
```

### A.4 Test Vault Connectivity

```bash
# Install vault CLI (optional but recommended)
sudo dnf install -y yum-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
sudo dnf install -y vault

# Test vault connection
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=myroot
vault status
```

## Option B: Docker-Based Local Vault (Alternative)

### B.1 Install Docker

```bash
# Install Docker on RHEL 9/Rocky Linux
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

### B.2 Start Vault Development Server

```bash
# Create vault data directory
mkdir -p ~/vault-data

# Start Vault in development mode using Docker (NOT for production)
docker run -d \
  --name vault-dev \
  --cap-add=IPC_LOCK \
  -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=myroot' \
  -e 'VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200' \
  -v ~/vault-data:/vault/data \
  hashicorp/vault:latest

# Verify container is running
docker ps | grep vault-dev
```

### B.3 Configure Environment

```bash
# Add to your .env file
cat >> .env << EOF

# =============================================================================
# LOCAL VAULT CONFIGURATION (Development)
# =============================================================================

# Enable local vault integration
USE_HASHICORP_VAULT=true
USE_HASHICORP_CLOUD=false

# Local vault server configuration
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=myroot

# Development settings
VAULT_DEV_MODE=true
EOF
```

### B.4 Test Vault Connectivity

```bash
# Install vault CLI (optional but recommended)
sudo dnf install -y yum-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
sudo dnf install -y vault

# Test vault connection
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=myroot
vault status
```

## Option C: Binary Installation (Production-Ready)

### C.1 Install Vault Binary

```bash
# Download and install Vault
VAULT_VERSION="1.15.4"
wget https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip
unzip vault_${VAULT_VERSION}_linux_amd64.zip
sudo mv vault /usr/local/bin/
sudo chmod +x /usr/local/bin/vault

# Verify installation
vault version
```

### C.2 Create Vault Configuration

```bash
# Create vault user and directories
sudo useradd --system --home /etc/vault.d --shell /bin/false vault
sudo mkdir -p /opt/vault/data
sudo mkdir -p /etc/vault.d
sudo chown -R vault:vault /opt/vault/data
sudo chown -R vault:vault /etc/vault.d

# Create vault configuration file
sudo tee /etc/vault.d/vault.hcl << EOF
storage "file" {
  path = "/opt/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"
ui = true
EOF
```

### C.3 Create Systemd Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/vault.service << EOF
[Unit]
Description=HashiCorp Vault
Documentation=https://www.vaultproject.io/docs/
Requires=network-online.target
After=network-online.target
ConditionFileNotEmpty=/etc/vault.d/vault.hcl
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=notify
User=vault
Group=vault
ProtectSystem=full
ProtectHome=read-only
PrivateTmp=yes
PrivateDevices=yes
SecureBits=keep-caps
AmbientCapabilities=CAP_IPC_LOCK
Capabilities=CAP_IPC_LOCK+ep
CapabilityBoundingSet=CAP_SYSLOG CAP_IPC_LOCK
NoNewPrivileges=yes
ExecStart=/usr/local/bin/vault server -config=/etc/vault.d/vault.hcl
ExecReload=/bin/kill --signal HUP \$MAINPID
KillMode=process
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
StartLimitInterval=60
StartLimitBurst=3
LimitNOFILE=65536
LimitMEMLOCK=infinity

[Install]
WantedBy=multi-user.target
EOF

# Enable and start vault service
sudo systemctl daemon-reload
sudo systemctl enable vault
sudo systemctl start vault
sudo systemctl status vault
```

### C.4 Initialize Vault

```bash
# Initialize vault (first time only)
export VAULT_ADDR=http://127.0.0.1:8200
vault operator init -key-shares=1 -key-threshold=1

# Save the unseal key and root token securely!
# Example output:
# Unseal Key 1: <UNSEAL_KEY>
# Initial Root Token: <ROOT_TOKEN>

# Unseal vault
vault operator unseal <UNSEAL_KEY>

# Login with root token
vault auth <ROOT_TOKEN>
```

## Step 2: Configure Vault for Qubinode Navigator

### 2.1 Enable KV Secrets Engine

```bash
# Enable KV v2 secrets engine
vault secrets enable -version=2 kv

# Create path for ansiblesafe secrets (matching existing pattern)
vault kv put kv/ansiblesafe/localhost test=value
vault kv delete kv/ansiblesafe/localhost
```

### 2.2 Create Vault Policy

```bash
# Create policy for Qubinode Navigator
vault policy write qubinode-navigator - << EOF
# Allow read/write access to ansiblesafe secrets
path "kv/data/ansiblesafe/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "kv/metadata/ansiblesafe/*" {
  capabilities = ["list", "read", "delete"]
}

# Allow listing of secret engines
path "sys/mounts" {
  capabilities = ["read"]
}
EOF
```

### 2.3 Create Application Token

```bash
# Create token for Qubinode Navigator
QUBINODE_TOKEN=$(vault token create \
  -policy=qubinode-navigator \
  -ttl=24h \
  -renewable=true \
  -format=json | jq -r .auth.client_token)

echo "Qubinode Navigator Token: $QUBINODE_TOKEN"

# Add to your .env file
echo "VAULT_TOKEN=$QUBINODE_TOKEN" >> .env
```

## Step 3: Store Secrets in Local Vault

### 3.1 Store Qubinode Navigator Secrets

```bash
# Store RHEL subscription secrets
vault kv put kv/ansiblesafe/localhost \
  rhsm_username="your-rhel-username" \
  rhsm_password="your-rhel-password" \
  rhsm_org="your-org-id" \
  rhsm_activationkey="your-activation-key"

# Store user management secrets
vault kv put kv/ansiblesafe/localhost \
  admin_user_password="your-secure-admin-password" \
  xrdp_remote_user="remoteuser" \
  xrdp_remote_user_password="your-remote-user-password" \
  freeipa_server_admin_password="your-freeipa-admin-password"

# Store service tokens
vault kv put kv/ansiblesafe/localhost \
  offline_token="your-red-hat-offline-token" \
  openshift_pull_secret="your-openshift-pull-secret" \
  automation_hub_offline_token="your-automation-hub-token"

# Store AWS credentials (optional)
vault kv put kv/ansiblesafe/localhost \
  aws_access_key="your-aws-access-key" \
  aws_secret_key="your-aws-secret-key"
```

### 3.2 Verify Stored Secrets

```bash
# List all secrets
vault kv list kv/ansiblesafe/

# Read specific secret
vault kv get kv/ansiblesafe/localhost

# Read specific field
vault kv get -field=rhsm_username kv/ansiblesafe/localhost
```

## Step 4: Update Enhanced Load Variables for Local Vault

The current `enhanced-load-variables.py` script needs to be updated to work with the local vault path structure:

### 4.1 Update Vault Path Configuration

```bash
# Add to your .env file
cat >> .env << EOF

# Local vault path configuration
SECRET_PATH=ansiblesafe/localhost
VAULT_KV_PATH=kv/data/ansiblesafe/localhost
EOF
```

### 4.2 Test Integration

```bash
# Load environment variables
source .env

# Test basic configuration generation
python3 enhanced-load-variables.py --generate-config --template default.yml.j2

# Test vault integration
python3 enhanced-load-variables.py --generate-config --update-vault
```

## Step 5: Environment-Specific Local Vault Setup

### 5.1 Multiple Environment Support

```bash
# Create secrets for different environments
vault kv put kv/ansiblesafe/hetzner \
  rhsm_username="hetzner-rhel-user" \
  admin_user_password="hetzner-admin-pass"

vault kv put kv/ansiblesafe/equinix \
  rhsm_username="equinix-rhel-user" \
  admin_user_password="equinix-admin-pass"

vault kv put kv/ansiblesafe/dev \
  rhsm_username="dev-rhel-user" \
  admin_user_password="dev-admin-pass"
```

### 5.2 Test Environment-Specific Configuration

```bash
# Test different environments
export INVENTORY="hetzner"
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2

export INVENTORY="equinix"
python3 enhanced-load-variables.py --generate-config --template default.yml.j2
```

## Step 6: Backup and Recovery

### 6.1 Backup Vault Data

```bash
# For Podman setup (recommended)
podman exec vault-dev vault operator raft snapshot save /vault/data/backup.snap

# For Docker setup
docker exec vault-dev vault operator raft snapshot save /vault/data/backup.snap

# For binary setup
vault operator raft snapshot save /opt/vault/backup.snap
```

### 6.2 Restore from Backup

```bash
# Stop vault service
sudo systemctl stop vault

# Restore from snapshot
vault operator raft snapshot restore /opt/vault/backup.snap

# Start vault service
sudo systemctl start vault
```

## Step 7: Security Hardening

### 7.1 Enable TLS (Production)

```bash
# Generate self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -keyout vault-key.pem -out vault-cert.pem -days 365 -nodes

# Update vault.hcl
sudo tee -a /etc/vault.d/vault.hcl << EOF
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/etc/vault.d/vault-cert.pem"
  tls_key_file  = "/etc/vault.d/vault-key.pem"
}
EOF
```

### 7.2 Firewall Configuration

```bash
# Open vault port
sudo firewall-cmd --permanent --add-port=8200/tcp
sudo firewall-cmd --reload
```

## Troubleshooting

### Common Issues

1. **Vault Sealed**
   ```bash
   vault operator unseal <UNSEAL_KEY>
   ```

2. **Permission Denied**
   ```bash
   # Check token permissions
   vault token lookup
   
   # Renew token if needed
   vault token renew
   ```

3. **Connection Refused**
   ```bash
   # Check vault status
   vault status
   
   # Check service status
   sudo systemctl status vault
   ```

### Debug Commands

```bash
# Check vault logs
sudo journalctl -u vault -f

# Test vault API
curl -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/health

# List all secrets
vault kv list kv/ansiblesafe/
```

## Next Steps

1. **Test the integration** with your local vault setup
2. **Create environment-specific secrets** for different inventories
3. **Set up backup procedures** for vault data
4. **Implement monitoring** for vault health
5. **Plan migration** to production vault when ready

## Podman vs Docker Comparison

| Feature | Podman (RHEL 9) | Docker |
|---------|-----------------|--------|
| **Installation** | Pre-installed | Requires installation |
| **Root Access** | Rootless by default | Requires root daemon |
| **Security** | SELinux compatible | Additional configuration needed |
| **Systemd** | Native integration | Third-party integration |
| **Resource Usage** | Lower overhead | Higher daemon overhead |
| **RHEL Support** | Official Red Hat | Community support |

## Quick Test

Run the provided test script to verify your Podman-based vault setup:

```bash
# Test Podman vault setup
./test-podman-vault.sh
```

This setup provides a complete local development environment for testing HashiCorp Vault integration with Qubinode Navigator, optimized for RHEL 9 with Podman!
