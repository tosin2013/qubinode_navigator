# HashiCorp Cloud Platform (HCP) Vault Setup for Qubinode Navigator

This guide walks you through setting up HashiCorp Cloud Platform (HCP) Vault Secrets integration with the enhanced Qubinode Navigator configuration system.

## Prerequisites

1. **HCP Account**: Sign up or log in to [HashiCorp Cloud Platform](https://cloud.hashicorp.com/)
1. **HCP CLI**: Install HCP CLI on your local machine
   ```bash
   # Install HCP CLI (Linux)
   curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
   sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
   sudo apt-get update && sudo apt-get install hcp
   ```
1. **Service Principal**: HCP service principal with Client ID and Client Secret
1. **jq**: JSON parser for shell scripts (`sudo dnf install jq -y`)

## Step 1: Create HCP Vault Secrets Application

### 1.1 Log in to HCP

1. Go to [HashiCorp Cloud Platform](https://cloud.hashicorp.com/)
1. Log in with your credentials
1. Navigate to **Vault Secrets** from the dashboard

### 1.2 Create New Application

1. Click **"Create App"** in Vault Secrets interface
1. Provide application name: `qubinode-navigator-secrets`
1. Select your organization and project
1. Click **"Create"** to finalize

### 1.3 Create Service Principal

1. Go to **Access control (IAM)** in HCP
1. Click **"Create service principal"**
1. Name: `qubinode-navigator-sp`
1. Assign role: **Contributor** (or custom role with Vault Secrets access)
1. Save the **Client ID** and **Client Secret** securely

## Step 2: Configure Environment Variables

Create your HCP configuration in `.env` file:

```bash
# Copy and edit the environment file
cp .env-example .env
chmod 600 .env
```

Add the following HCP-specific variables to your `.env` file:

```bash
# =============================================================================
# HCP VAULT SECRETS CONFIGURATION
# =============================================================================

# Enable HCP integration
USE_HASHICORP_VAULT=true
USE_HASHICORP_CLOUD=true

# HCP Service Principal credentials
HCP_CLIENT_ID=your-actual-client-id
HCP_CLIENT_SECRET=your-actual-client-secret

# HCP Organization and Project (get from HCP CLI)
HCP_ORG_ID=your-org-id
HCP_PROJECT_ID=your-project-id

# Application name in HCP Vault Secrets
APP_NAME=qubinode-navigator-secrets

# Environment/Inventory for secret organization
INVENTORY=localhost
```

### 2.1 Get Organization and Project IDs

```bash
# Install and authenticate HCP CLI
hcp auth login

# Get your organization and project IDs
export HCP_ORG_ID=$(hcp profile display --format=json | jq -r .OrganizationID)
export HCP_PROJECT_ID=$(hcp profile display --format=json | jq -r .ProjectID)

# Add to your .env file
echo "HCP_ORG_ID=$HCP_ORG_ID" >> .env
echo "HCP_PROJECT_ID=$HCP_PROJECT_ID" >> .env
```

## Step 3: Store Secrets in HCP Vault Secrets

### 3.1 Authenticate and Get API Token

```bash
# Load environment variables
source .env

# Get HCP API token
export HCP_API_TOKEN=$(curl -s https://auth.idp.hashicorp.com/oauth2/token \
     --data grant_type=client_credentials \
     --data client_id="$HCP_CLIENT_ID" \
     --data client_secret="$HCP_CLIENT_SECRET" \
     --data audience="https://api.hashicorp.cloud" | jq -r .access_token)
```

### 3.2 Store Qubinode Navigator Secrets

```bash
# Store all required secrets for Qubinode Navigator
curl -s \
    --location "https://api.cloud.hashicorp.com/secrets/2023-06-13/organizations/$HCP_ORG_ID/projects/$HCP_PROJECT_ID/apps/$APP_NAME/secrets" \
    --request POST \
    --header "Authorization: Bearer $HCP_API_TOKEN" \
    --header "Content-Type: application/json" \
    --data-raw '{
        "secrets": [
            {
                "name": "rhsm_username",
                "value": "your-rhel-username"
            },
            {
                "name": "rhsm_password",
                "value": "your-rhel-password"
            },
            {
                "name": "rhsm_org",
                "value": "your-org-id"
            },
            {
                "name": "rhsm_activationkey",
                "value": "your-activation-key"
            },
            {
                "name": "admin_user_password",
                "value": "your-secure-admin-password"
            },
            {
                "name": "offline_token",
                "value": "your-red-hat-offline-token"
            },
            {
                "name": "automation_hub_offline_token",
                "value": "your-automation-hub-token"
            },
            {
                "name": "openshift_pull_secret",
                "value": "your-openshift-pull-secret"
            },
            {
                "name": "freeipa_server_admin_password",
                "value": "your-freeipa-admin-password"
            },
            {
                "name": "xrdp_remote_user",
                "value": "remoteuser"
            },
            {
                "name": "xrdp_remote_user_password",
                "value": "your-remote-user-password"
            },
            {
                "name": "aws_access_key",
                "value": "your-aws-access-key"
            },
            {
                "name": "aws_secret_key",
                "value": "your-aws-secret-key"
            }
        ]
    }'
```

### 3.3 Verify Stored Secrets

```bash
# List all secrets in your application
curl -s \
    --location "https://api.cloud.hashicorp.com/secrets/2023-06-13/organizations/$HCP_ORG_ID/projects/$HCP_PROJECT_ID/apps/$APP_NAME/open" \
    --request GET \
    --header "Authorization: Bearer $HCP_API_TOKEN" | jq '.secrets[] | {name: .name, created_at: .created_at}'
```

## Step 4: Test HCP Integration with Enhanced Load Variables

### 4.1 Update Enhanced Script for HCP

The `enhanced-load-variables.py` script needs to be updated to support HCP API calls. Let me create an HCP-specific version:

```bash
# Test basic configuration generation with HCP
export $(cat .env | xargs)
python3 enhanced-load-variables.py --generate-config --template default.yml.j2
```

### 4.2 Run Setup Script

```bash
# Run the automated setup and testing script
./setup-vault-integration.sh
```

This will:

- ✅ Verify HCP connectivity
- ✅ Test secret retrieval
- ✅ Generate configuration with HCP secrets
- ✅ Validate the integration

## Step 5: Environment-Specific HCP Setup

### 5.1 Multiple Environment Support

For different environments (hetzner, equinix, etc.), create separate HCP applications:

```bash
# Create environment-specific applications
APP_NAME="qubinode-hetzner-secrets"
APP_NAME="qubinode-equinix-secrets"
APP_NAME="qubinode-dev-secrets"
```

### 5.2 Template Integration

Use environment-specific templates with HCP:

```bash
# Generate Hetzner-specific configuration from HCP
export INVENTORY="hetzner"
export APP_NAME="qubinode-hetzner-secrets"
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2
```

## Step 6: CI/CD Integration

### 6.1 GitLab CI/CD with HCP

Add to your `.gitlab-ci.yml`:

```yaml
variables:
  HCP_CLIENT_ID: $HCP_CLIENT_ID
  HCP_CLIENT_SECRET: $HCP_CLIENT_SECRET
  HCP_ORG_ID: $HCP_ORG_ID
  HCP_PROJECT_ID: $HCP_PROJECT_ID
  USE_HASHICORP_VAULT: "true"
  USE_HASHICORP_CLOUD: "true"

deploy:
  script:
    - export HCP_API_TOKEN=$(curl -s https://auth.idp.hashicorp.com/oauth2/token --data grant_type=client_credentials --data client_id="$HCP_CLIENT_ID" --data client_secret="$HCP_CLIENT_SECRET" --data audience="https://api.hashicorp.cloud" | jq -r .access_token)
    - python3 enhanced-load-variables.py --generate-config --update-vault
```

## Step 7: Security Best Practices

### 7.1 Secret Rotation

```bash
# Rotate HCP service principal credentials regularly
# Update secrets in HCP Vault Secrets
# Test connectivity after rotation
```

### 7.2 Access Control

1. **Principle of Least Privilege**: Grant minimal required permissions
1. **Service Principal Rotation**: Rotate credentials every 90 days
1. **Audit Logging**: Monitor HCP access logs
1. **Environment Separation**: Use separate applications per environment

## Troubleshooting

### Common Issues

1. **Authentication Failures**

   ```bash
   # Verify credentials
   curl -s https://auth.idp.hashicorp.com/oauth2/token \
        --data grant_type=client_credentials \
        --data client_id="$HCP_CLIENT_ID" \
        --data client_secret="$HCP_CLIENT_SECRET" \
        --data audience="https://api.hashicorp.cloud"
   ```

1. **API Rate Limits**

   - HCP has API rate limits
   - Implement exponential backoff
   - Cache tokens appropriately

1. **Network Connectivity**

   ```bash
   # Test HCP API connectivity
   curl -s https://api.cloud.hashicorp.com/secrets/2023-06-13/health
   ```

### Debug Commands

```bash
# Test HCP CLI authentication
hcp auth print-access-token

# Verify organization access
hcp profile display

# Test API token
echo $HCP_API_TOKEN | jq -R 'split(".") | .[1] | @base64d | fromjson'
```

## Next Steps

1. **Test the integration** with your actual HCP credentials
1. **Create environment-specific applications** in HCP
1. **Set up CI/CD integration** with HCP authentication
1. **Implement secret rotation** procedures
1. **Monitor and audit** HCP access logs

## Support

- **HCP Documentation**: https://learn.hashicorp.com/cloud
- **HCP Support**: Available through HashiCorp Cloud Platform console
- **Qubinode Navigator**: Check repository issues and documentation

This setup provides secure, scalable secret management for Qubinode Navigator using HashiCorp Cloud Platform!
