# HashiCorp Vault Integration Testing Guide

This guide helps you test the enhanced configuration management system with HashiCorp Vault integration.

## Prerequisites

1. **Enhanced script**: `enhanced-load-variables.py` ✅ (Created)
2. **Templates**: `templates/` directory with Jinja2 templates ✅ (Created)
3. **Dependencies**: jinja2, hvac Python packages ✅ (Installed)
4. **Environment file**: `.env` with your configuration ⏳ (Needs your input)

## Quick Start

### 1. Run the Setup Script
```bash
cd /home/vpcuser/qubinode_navigator
./setup-vault-integration.sh
```

This script will:
- ✅ Verify dependencies
- ✅ Create .env file from example
- ✅ Test basic configuration generation
- ✅ Validate environment variables
- ✅ Test vault connectivity (if enabled)

### 2. Configure Your Environment

Edit the `.env` file with your actual values:

```bash
# Copy the example and edit
cp .env-example .env
chmod 600 .env
vim .env  # or your preferred editor
```

**Required values you need to provide:**

#### Core Configuration
```bash
INVENTORY=localhost                    # Your environment
RHSM_USERNAME=your-rhel-username      # Your RHEL subscription username
RHSM_PASSWORD=your-rhel-password      # Your RHEL subscription password
ADMIN_USER_PASSWORD=your-admin-pass   # Secure admin password
```

#### For HashiCorp Vault Integration (Optional)
```bash
USE_HASHICORP_VAULT=true
VAULT_ADDR=https://vault.company.com:8200
VAULT_TOKEN=hvs.CAESIJ...your-token
```

## Testing Scenarios

### Scenario 1: Basic Template Generation (No Vault)

```bash
# Set required environment variables
export INVENTORY="localhost"
export RHSM_USERNAME="your-username"
export RHSM_PASSWORD="your-password"
export ADMIN_USER_PASSWORD="your-admin-password"

# Generate configuration from template
python3 enhanced-load-variables.py --generate-config --template default.yml.j2

# Check the generated file
cat /tmp/config.yml
```

**Expected Result**: `/tmp/config.yml` created with your values and template metadata.

### Scenario 2: Environment-Specific Templates

```bash
# Test Hetzner-specific template
export INVENTORY="hetzner"
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2

# Test with different environments
export INVENTORY="equinix"
python3 enhanced-load-variables.py --generate-config --template default.yml.j2
```

### Scenario 3: HashiCorp Vault Integration

#### Option A: Using HashiCorp Vault Cloud/Enterprise
```bash
# Configure vault connection
export USE_HASHICORP_VAULT="true"
export VAULT_ADDR="https://your-vault-server:8200"
export VAULT_TOKEN="hvs.CAESIJ...your-token"

# Generate config and update vault
python3 enhanced-load-variables.py --generate-config --update-vault
```

#### Option B: Local Vault Development Server
```bash
# Start local vault server (for testing)
vault server -dev -dev-root-token-id="myroot"

# In another terminal
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="myroot"
export USE_HASHICORP_VAULT="true"

# Test vault integration
python3 enhanced-load-variables.py --generate-config --update-vault
```

### Scenario 4: CI/CD Pipeline Simulation

```bash
# Simulate CI/CD environment
export CICD_PIPELINE="true"
export USE_HASHICORP_VAULT="true"
export VAULT_ADDR="https://vault.company.com:8200"
export VAULT_TOKEN="$CI_VAULT_TOKEN"

# Generate and upload to vault
python3 enhanced-load-variables.py --generate-config --update-vault
```

## What I Need From You

To complete the vault integration testing, please provide:

### 1. HashiCorp Vault Access (Choose One)

#### Option A: Existing Vault Instance
- **Vault URL**: `https://your-vault-server:8200`
- **Authentication method**: Token, AppRole, or other
- **Credentials**: Vault token or role credentials
- **Permissions**: Ability to read/write to `ansiblesafe/` path

#### Option B: HashiCorp Cloud Platform (HCP)
- **HCP Organization ID**: Your HCP org ID
- **HCP Project ID**: Your HCP project ID  
- **Client ID**: HCP service principal client ID
- **Client Secret**: HCP service principal client secret

#### Option C: Local Development Vault
- I can help you set up a local Vault server for testing
- Requires Docker or direct Vault binary installation

### 2. RHEL Subscription Information
- **Username**: Your Red Hat customer portal username
- **Password**: Your Red Hat customer portal password
- **Organization ID**: Your RHEL organization ID (optional)
- **Activation Key**: Your RHEL activation key (optional)

### 3. Service Tokens (Optional but Recommended)
- **Red Hat Offline Token**: For API access
- **OpenShift Pull Secret**: For container registry access
- **Automation Hub Token**: For Ansible content access

### 4. AWS Credentials (Optional - for Route53)
- **Access Key**: AWS access key for Route53 management
- **Secret Key**: AWS secret key

## Testing Commands

Once you provide the information, we can test:

### Basic Functionality Test
```bash
./setup-vault-integration.sh
```

### Manual Testing Commands
```bash
# Test template generation
python3 enhanced-load-variables.py --generate-config

# Test with specific template
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2

# Test vault integration
python3 enhanced-load-variables.py --generate-config --update-vault

# Test with environment variables only
export RHSM_USERNAME="test" RHSM_PASSWORD="test" ADMIN_USER_PASSWORD="test"
python3 enhanced-load-variables.py --generate-config
```

### Validation Commands
```bash
# Check generated configuration
cat /tmp/config.yml

# Verify file permissions
ls -la /tmp/config.yml  # Should show -rw------- (600)

# Test vault connectivity (if using vault)
vault status  # Requires vault CLI
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   pip3 install --user jinja2 hvac pyyaml
   ```

2. **Permission Errors**
   ```bash
   chmod 600 .env
   chmod +x setup-vault-integration.sh
   ```

3. **Vault Connection Issues**
   - Check VAULT_ADDR is accessible
   - Verify VAULT_TOKEN is valid
   - Test with: `curl -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/health`

4. **Template Errors**
   - Check template syntax in `templates/` directory
   - Verify Jinja2 is installed
   - Test with basic template first

## Next Steps After Testing

1. **Create additional templates** for your specific environments
2. **Set up CI/CD integration** with vault authentication
3. **Migrate existing configurations** to the new system
4. **Configure vault policies** for proper access control
5. **Set up secret rotation** for enhanced security

## Support

If you encounter issues:
1. Run `./setup-vault-integration.sh` for automated diagnostics
2. Check the generated logs and error messages
3. Verify all required environment variables are set
4. Test vault connectivity independently
5. Review the ADR-0023 documentation for implementation details

Let me know what vault setup option works best for you, and I'll help you configure and test the integration!
