# Complete HashiCorp Vault Setup Guide for Qubinode Navigator

This comprehensive guide covers both HashiCorp Cloud Platform (HCP) and local vault setup options for the enhanced Qubinode Navigator configuration system.

## Quick Decision Matrix

| Feature              | HCP Vault Secrets    | OpenShift Vault     | Local Vault     | Recommendation                 |
| -------------------- | -------------------- | ------------------- | --------------- | ------------------------------ |
| **Setup Complexity** | Low                  | Medium              | Medium          | HCP for quick start            |
| **Cost**             | Paid service         | Infrastructure cost | Free            | Local for development          |
| **Security**         | Managed by HashiCorp | Enterprise-grade    | Self-managed    | OpenShift for enterprise       |
| **Scalability**      | Auto-scaling         | Kubernetes scaling  | Manual scaling  | OpenShift for production       |
| **Control**          | Limited              | High control        | Full control    | OpenShift for enterprise       |
| **Maintenance**      | Zero maintenance     | Kubernetes managed  | Self-maintained | HCP for teams                  |
| **Integration**      | API-based            | Native K8s          | Direct access   | OpenShift for K8s environments |

## Prerequisites for Both Options

1. **Enhanced Qubinode Navigator**: ✅ Already implemented
1. **Python Dependencies**: `jinja2`, `hvac`, `requests` ✅ Already installed
1. **Environment File**: `.env` with your configuration
1. **RHEL Subscription**: Valid Red Hat credentials

## Option 1: HashiCorp Cloud Platform (HCP) Setup

### 🚀 Quick Start with HCP

Since you mentioned you have HCP access, this is the recommended approach:

#### Step 1: Configure HCP Environment

```bash
# Edit your .env file with HCP credentials
vim .env

# Add these HCP-specific variables:
USE_HASHICORP_VAULT=true
USE_HASHICORP_CLOUD=true
HCP_CLIENT_ID=your-actual-client-id
HCP_CLIENT_SECRET=your-actual-client-secret
HCP_ORG_ID=your-org-id
HCP_PROJECT_ID=your-project-id
APP_NAME=qubinode-navigator-secrets
```

#### Step 2: Create HCP Application

1. **Log in to HCP**: https://cloud.hashicorp.com/
1. **Navigate to Vault Secrets**
1. **Create Application**: Name it `qubinode-navigator-secrets`
1. **Create Service Principal** with Vault Secrets access

#### Step 3: Store Your Secrets

Use the HCP web interface or API to store:

- `rhsm_username`: Your RHEL username
- `rhsm_password`: Your RHEL password
- `admin_user_password`: Secure admin password
- `offline_token`: Red Hat offline token
- `openshift_pull_secret`: OpenShift pull secret
- Other required secrets from `.env-example`

#### Step 4: Test HCP Integration

```bash
# Run the setup script
./setup-vault-integration.sh

# Test configuration generation with HCP
python3 enhanced-load-variables.py --generate-config --template default.yml.j2

# Verify HCP secrets are retrieved
cat /tmp/config.yml
```

**📖 Detailed HCP Setup**: See [HCP-VAULT-SETUP.md](HCP-VAULT-SETUP.md)

## Option 2: Local Vault Setup

### 🔧 Local Development Vault

For development, testing, or when you want full control:

#### Step 1: Choose Installation Method

**Option A: Podman (Recommended for RHEL 9)**

```bash
# Start Vault development server with Podman
podman run -d \
  --name vault-dev \
  --cap-add=IPC_LOCK \
  -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=myroot' \
  -v ~/vault-data:/vault/data:Z \
  docker.io/hashicorp/vault:latest

# Configure environment
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=myroot
```

**Option B: Docker (Alternative)**

```bash
# Start Vault development server with Docker
docker run -d \
  --name vault-dev \
  --cap-add=IPC_LOCK \
  -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=myroot' \
  hashicorp/vault:latest

# Configure environment
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=myroot
```

**Option C: Binary Installation (Production-ready)**

```bash
# Install Vault binary
wget https://releases.hashicorp.com/vault/1.15.4/vault_1.15.4_linux_amd64.zip
unzip vault_1.15.4_linux_amd64.zip
sudo mv vault /usr/local/bin/

# Configure and start Vault service
# (See LOCAL-VAULT-SETUP.md for complete instructions)
```

#### Step 2: Configure Local Environment

```bash
# Edit your .env file for local vault
vim .env

# Add these local vault variables:
USE_HASHICORP_VAULT=true
USE_HASHICORP_CLOUD=false
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=myroot
SECRET_PATH=ansiblesafe/localhost
```

#### Step 3: Store Secrets in Local Vault

```bash
# Enable KV secrets engine
vault secrets enable -version=2 kv

# Store your secrets
vault kv put kv/ansiblesafe/localhost \
  rhsm_username="your-rhel-username" \
  rhsm_password="your-rhel-password" \
  admin_user_password="your-admin-password"
```

#### Step 4: Test Local Vault Integration

```bash
# Test vault connectivity
vault status

# Test configuration generation
python3 enhanced-load-variables.py --generate-config --template default.yml.j2
```

**📖 Detailed Local Setup**: See [LOCAL-VAULT-SETUP.md](LOCAL-VAULT-SETUP.md)

## Option 3: OpenShift Vault Setup

### 🏢 Enterprise Vault on OpenShift

For enterprise environments running OpenShift/Kubernetes:

#### Step 1: Choose Deployment Method

**Option A: Vault Operator (Recommended)**

```bash
# Install from OperatorHub
oc new-project vault-system
oc apply -f - << EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: vault-operator
  namespace: vault-system
spec:
  channel: stable
  name: vault
  source: community-operators
  sourceNamespace: openshift-marketplace
EOF
```

**Option B: Helm Chart**

```bash
# Add HashiCorp Helm repository
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault -n vault-system --set global.openshift=true
```

#### Step 2: Configure OpenShift Environment

```bash
# Edit your .env file for OpenShift vault
vim .env

# Add these OpenShift vault variables:
USE_HASHICORP_VAULT=true
USE_HASHICORP_CLOUD=false
OPENSHIFT_VAULT=true
VAULT_ADDR=https://vault.apps.your-cluster.com
VAULT_AUTH_METHOD=kubernetes
VAULT_ROLE=qubinode-navigator
```

#### Step 3: Configure Kubernetes Authentication

```bash
# Enable Kubernetes auth in Vault
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
    token_reviewer_jwt="$(oc serviceaccounts get-token vault -n vault-system)" \
    kubernetes_host="https://kubernetes.default.svc:443"

# Create policy and role for Qubinode Navigator
vault policy write qubinode-navigator - << EOF
path "kv/data/ansiblesafe/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF

vault write auth/kubernetes/role/qubinode-navigator \
    bound_service_account_names=qubinode-navigator \
    bound_service_account_namespaces=qubinode-navigator \
    policies=qubinode-navigator \
    ttl=24h
```

#### Step 4: Test OpenShift Integration

```bash
# Create service account for Qubinode Navigator
oc new-project qubinode-navigator
oc create serviceaccount qubinode-navigator

# Test configuration generation
python3 enhanced-load-variables.py --generate-config --template default.yml.j2
```

**📖 Detailed OpenShift Setup**: See [OPENSHIFT-VAULT-SETUP.md](OPENSHIFT-VAULT-SETUP.md)

## Testing Both Environments

### Automated Testing Script

```bash
# Run comprehensive setup and testing
./setup-vault-integration.sh
```

This script will:

- ✅ Detect your vault configuration (HCP vs Local)
- ✅ Test connectivity and authentication
- ✅ Validate secret retrieval
- ✅ Generate test configuration
- ✅ Verify integration works correctly

### Manual Testing Commands

```bash
# Test basic template generation (no vault)
export RHSM_USERNAME="test" RHSM_PASSWORD="test" ADMIN_USER_PASSWORD="test"
python3 enhanced-load-variables.py --generate-config

# Test with vault integration
python3 enhanced-load-variables.py --generate-config --update-vault

# Test environment-specific templates
export INVENTORY="hetzner"
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2
```

## Environment-Specific Configuration

### Multiple Environments Support

Both HCP and local vault support multiple environments:

#### HCP Approach

- Create separate applications: `qubinode-hetzner-secrets`, `qubinode-equinix-secrets`
- Use `APP_NAME` environment variable to switch between them

#### Local Vault Approach

- Create separate paths: `kv/ansiblesafe/hetzner`, `kv/ansiblesafe/equinix`
- Use `INVENTORY` environment variable to switch between them

### Example Multi-Environment Setup

```bash
# Hetzner environment
export INVENTORY="hetzner"
export APP_NAME="qubinode-hetzner-secrets"  # For HCP
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2

# Equinix environment
export INVENTORY="equinix"
export APP_NAME="qubinode-equinix-secrets"  # For HCP
python3 enhanced-load-variables.py --generate-config --template default.yml.j2
```

## Security Best Practices

### For Both Environments

1. **Environment File Security**

   ```bash
   chmod 600 .env
   echo ".env" >> .gitignore
   ```

1. **Token Management**

   - Rotate tokens regularly
   - Use short-lived tokens when possible
   - Store tokens securely

1. **Access Control**

   - Follow principle of least privilege
   - Use separate credentials per environment
   - Monitor access logs

### HCP-Specific Security

- Use service principals instead of user tokens
- Enable audit logging in HCP
- Set up proper IAM roles and policies

### Local Vault Security

- Enable TLS in production
- Use proper authentication methods (not dev mode)
- Implement backup and recovery procedures
- Configure firewall rules

## Migration Path

### From Local to HCP

```bash
# Export secrets from local vault
vault kv get -format=json kv/ansiblesafe/localhost > local-secrets.json

# Import to HCP using API
# (See HCP-VAULT-SETUP.md for import script)
```

### From HCP to Local

```bash
# Export from HCP
curl -H "Authorization: Bearer $HCP_API_TOKEN" \
  "https://api.cloud.hashicorp.com/secrets/2023-06-13/organizations/$HCP_ORG_ID/projects/$HCP_PROJECT_ID/apps/$APP_NAME/open" \
  > hcp-secrets.json

# Import to local vault
# (Process JSON and store in local vault)
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**

   - Verify credentials in `.env` file
   - Check token expiration
   - Validate network connectivity

1. **Secret Not Found**

   - Verify secret names match exactly
   - Check application/path configuration
   - Ensure secrets are properly stored

1. **Template Errors**

   - Verify Jinja2 syntax in templates
   - Check variable names in templates
   - Test with basic template first

### Debug Commands

```bash
# Test vault connectivity
vault status  # For local vault
curl -H "Authorization: Bearer $HCP_API_TOKEN" https://api.cloud.hashicorp.com/secrets/2023-06-13/health  # For HCP

# Test secret retrieval
python3 -c "
from enhanced_load_variables import EnhancedConfigGenerator
gen = EnhancedConfigGenerator()
vars = gen._gather_all_variables()
print(vars)
"
```

## Next Steps

1. **Choose your vault setup** (HCP recommended for your case)
1. **Configure your environment** using the appropriate guide
1. **Store your actual secrets** (replace example values)
1. **Test the integration** with real credentials
1. **Set up CI/CD integration** for automated deployments
1. **Create environment-specific templates** as needed

## Support Resources

- **HCP Documentation**: https://learn.hashicorp.com/cloud
- **Vault Documentation**: https://www.vaultproject.io/docs
- **Qubinode Navigator**: Repository documentation and issues
- **Setup Scripts**: `./setup-vault-integration.sh` for automated testing

Choose the option that best fits your needs and follow the detailed setup guide for your chosen approach!
