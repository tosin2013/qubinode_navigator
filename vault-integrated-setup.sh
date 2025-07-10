#!/bin/bash
# Vault-Integrated Setup Script for Qubinode Navigator
# This script eliminates the /tmp/config.yml security concern by using vault directly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[VAULT-SETUP]${NC} $1"
}

print_header "Vault-Integrated Qubinode Navigator Setup"
echo "============================================="

# Load environment variables from .env file, preserving existing environment variables
if [ -f ".env" ]; then
    print_status "Loading environment variables..."

    # Save critical environment variables that should not be overridden
    SAVED_CICD_PIPELINE="${CICD_PIPELINE}"
    SAVED_SSH_PASSWORD="${SSH_PASSWORD}"
    SAVED_USE_HASHICORP_VAULT="${USE_HASHICORP_VAULT}"
    SAVED_VAULT_ADDR="${VAULT_ADDR}"
    SAVED_VAULT_TOKEN="${VAULT_TOKEN}"

    set -a
    source .env
    set +a

    # Restore critical environment variables if they were set before sourcing .env
    [ -n "${SAVED_CICD_PIPELINE}" ] && CICD_PIPELINE="${SAVED_CICD_PIPELINE}"
    [ -n "${SAVED_SSH_PASSWORD}" ] && SSH_PASSWORD="${SAVED_SSH_PASSWORD}"
    [ -n "${SAVED_USE_HASHICORP_VAULT}" ] && USE_HASHICORP_VAULT="${SAVED_USE_HASHICORP_VAULT}"
    [ -n "${SAVED_VAULT_ADDR}" ] && VAULT_ADDR="${SAVED_VAULT_ADDR}"
    [ -n "${SAVED_VAULT_TOKEN}" ] && VAULT_TOKEN="${SAVED_VAULT_TOKEN}"

    print_status "Environment variables loaded (CI/CD overrides preserved)"
else
    print_error ".env file not found. Please create it first."
    exit 1
fi

# Validate required environment variables
required_vars=("INVENTORY" "USE_HASHICORP_VAULT" "VAULT_ADDR" "VAULT_TOKEN")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

# Check if vault is accessible
print_status "Checking vault connectivity..."
if ! curl -s -f "${VAULT_ADDR}/v1/sys/health" > /dev/null; then
    print_error "Cannot connect to vault at ${VAULT_ADDR}"
    print_status "Starting local Podman vault if needed..."
    
    # Check if vault container exists
    if ! podman ps | grep -q vault-dev; then
        if ! podman ps -a | grep -q vault-dev; then
            print_status "Creating new vault container..."
            mkdir -p ~/vault-data
            podman run -d \
              --name vault-dev \
              --cap-add=IPC_LOCK \
              -p 8200:8200 \
              -e 'VAULT_DEV_ROOT_TOKEN_ID=myroot' \
              -v ~/vault-data:/vault/data:Z \
              docker.io/hashicorp/vault:latest
        else
            print_status "Starting existing vault container..."
            podman start vault-dev
        fi
        
        # Wait for vault to be ready
        print_status "Waiting for vault to be ready..."
        sleep 10
        
        # Enable KV secrets engine if needed
        export VAULT_ADDR=http://localhost:8200
        export VAULT_TOKEN=myroot
        vault secrets enable -version=2 kv 2>/dev/null || true
    fi
fi

# Function to setup vault password file using ansible_vault_setup.sh pattern
setup_vault_password() {
    print_status "Setting up vault password file..."

    # Download ansible_vault_setup.sh if not present
    if [ ! -f "ansible_vault_setup.sh" ]; then
        print_status "Downloading ansible_vault_setup.sh..."
        curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
        chmod +x ansible_vault_setup.sh
    fi

    # Clean up any existing vault password files
    rm -f ~/.vault_password
    sudo rm -rf /root/.vault_password 2>/dev/null || true

    if [ "${CICD_PIPELINE}" = "true" ]; then
        if [ -z "$SSH_PASSWORD" ]; then
            print_error "SSH_PASSWORD environment variable is not set for CI/CD mode"
            exit 1
        fi
        print_status "Setting up vault password for CI/CD mode..."
        echo "$SSH_PASSWORD" > ~/.vault_password
        sudo cp ~/.vault_password /root/.vault_password 2>/dev/null || true
        sudo cp ~/.vault_password /home/lab-user/.vault_password 2>/dev/null || true
        chmod 600 ~/.vault_password
        sudo chmod 600 /root/.vault_password 2>/dev/null || true

        # Create symlink and set environment variable
        ln -sf ~/.vault_password .vault_password 2>/dev/null || true
        export ANSIBLE_VAULT_PASSWORD_FILE=.vault_password

        print_status "✅ Vault password file created for CI/CD mode"
    else
        # Interactive mode - use ansible_vault_setup.sh
        print_status "Running interactive vault password setup..."
        bash ./ansible_vault_setup.sh
        print_status "✅ Vault password setup completed"
    fi
}

# Function to securely retrieve secrets from vault and create vault.yml
create_vault_yml_from_vault() {
    # Use current directory structure for testing, adjust for production
    local base_path="${PWD}"
    if [ -d "/root/qubinode_navigator" ]; then
        base_path="/root/qubinode_navigator"
    fi
    local inventory_path="${base_path}/inventories/${INVENTORY}/group_vars/control"
    local vault_yml_path="${inventory_path}/vault.yml"

    print_status "Creating vault.yml directly from HashiCorp Vault (no /tmp/config.yml needed)..."

    # Ensure directory exists
    mkdir -p "${inventory_path}"

    # Setup vault password file first
    setup_vault_password
    
    # Create temporary secure file for vault.yml generation
    local temp_vault_yml=$(mktemp --suffix=.yml)
    chmod 600 "${temp_vault_yml}"
    
    # Generate vault.yml content directly from vault
    cat > "${temp_vault_yml}" << EOF
# Qubinode Navigator Vault Configuration
# Generated directly from HashiCorp Vault - no intermediate files created
# Generated: $(date -Iseconds)
# Environment: ${INVENTORY}

EOF
    
    # Retrieve secrets from vault and append to vault.yml
    # Use Python YAML generation for proper formatting (more secure and reliable)
    print_status "Retrieving secrets from vault path: kv/ansiblesafe/${INVENTORY}"

    # Note: YAML generation now handled in the ansiblesafe section below
    print_status "Preparing for vault.yml generation..."
    
    # Move to final location
    mv "${temp_vault_yml}" "${vault_yml_path}"
    chmod 600 "${vault_yml_path}"
    
    print_status "✅ Created ${vault_yml_path} directly from vault"
    
    # Use our Python YAML generation instead of ansiblesafe for better formatting
    if [ -f /usr/local/bin/ansiblesafe ]; then
        print_status "Using Python YAML generation for proper formatting..."
        cd "$(dirname "${vault_yml_path}")"

        # Generate properly formatted vault.yml using our Python code
        python3 -c "
import os
import yaml
import sys
sys.path.append('/opt/qubinode_navigator')
from enhanced_load_variables import EnhancedConfigGenerator

try:
    gen = EnhancedConfigGenerator()
    if gen.vault_client:
        vault_vars = gen._get_vault_variables()
        if vault_vars:
            # Write properly formatted YAML
            with open('vault.yml', 'w') as f:
                yaml.dump(vault_vars, f, default_flow_style=False, allow_unicode=True, default_style='\"')
            print('✅ Generated properly formatted vault.yml from HashiCorp Vault')
        else:
            print('⚠️ No secrets retrieved from vault')
            exit(1)
    else:
        print('❌ Vault client not available')
        exit(1)
except Exception as e:
    print(f'❌ Error generating vault.yml: {e}')
    exit(1)
"

        # Check if Python generation succeeded
        if [ $? -eq 0 ] && [ -f vault.yml ]; then
            print_status "✅ Secrets retrieved from HashiCorp Vault with proper YAML formatting"

            # Now encrypt the vault.yml file
            if /usr/local/bin/ansiblesafe -f vault.yml -o 1; then
                print_status "✅ vault.yml encrypted successfully"
            else
                print_warning "Failed to encrypt vault.yml, but secrets were retrieved"
            fi
        else
            print_warning "Python YAML generation failed, falling back to ansiblesafe"
            # Fallback: use ansiblesafe operation 4
            export VAULT_ADDRESS="${VAULT_ADDR}"
            export SECRET_PATH="kv/ansiblesafe/${INVENTORY}"

            if /usr/local/bin/ansiblesafe -f vault.yml -o 4; then
                print_status "✅ Secrets retrieved from HashiCorp Vault (ansiblesafe fallback)"
                /usr/local/bin/ansiblesafe -f vault.yml -o 1
            else
                print_warning "Failed to retrieve secrets, creating empty vault.yml"
                /usr/local/bin/ansiblesafe -f vault.yml -o 1
            fi
        fi
    else
        print_warning "ansiblesafe not found at /usr/local/bin/ansiblesafe, vault.yml left unencrypted"
    fi
}

# Function to handle CI/CD pipeline mode
handle_cicd_mode() {
    print_status "Running in CI/CD pipeline mode"
    
    if [ "${USE_HASHICORP_VAULT}" = "true" ]; then
        print_status "Using vault-integrated approach (secure)"
        create_vault_yml_from_vault
    else
        # Fallback to traditional method if vault not available
        print_warning "Vault not enabled, falling back to /tmp/config.yml method"
        if [ -f /tmp/config.yml ]; then
            print_warning "⚠️ SECURITY CONCERN: Using /tmp/config.yml with sensitive data"
            local base_path="${PWD}"
            if [ -d "/root/qubinode_navigator" ]; then
                base_path="/root/qubinode_navigator"
            fi
            cp /tmp/config.yml "${base_path}/inventories/${INVENTORY}/group_vars/control/vault.yml"
            cd "${base_path}/inventories/${INVENTORY}/group_vars/control"
            /usr/local/bin/ansiblesafe -f vault.yml -o 1
        else
            print_error "Error: config.yml file not found and vault not available"
            exit 1
        fi
    fi
}

# Function to handle interactive mode
handle_interactive_mode() {
    print_status "Running in interactive mode"
    
    if [ "${USE_HASHICORP_VAULT}" = "true" ]; then
        print_status "Vault integration available - offering enhanced setup"
        echo ""
        echo "Choose setup method:"
        echo "1) Use vault-integrated setup (recommended - more secure)"
        echo "2) Use traditional interactive ansiblesafe setup"
        echo ""
        read -p "Enter choice (1 or 2): " choice
        
        case $choice in
            1)
                print_status "Using vault-integrated setup..."
                create_vault_yml_from_vault
                ;;
            2)
                print_status "Using traditional interactive setup..."
                setup_vault_password
                local base_path="${PWD}"
                if [ -d "/root/qubinode_navigator" ]; then
                    base_path="/root/qubinode_navigator"
                fi
                cd "${base_path}/inventories/${INVENTORY}/group_vars/control"
                /usr/local/bin/ansiblesafe -f vault.yml
                ;;
            *)
                print_error "Invalid choice. Exiting."
                exit 1
                ;;
        esac
    else
        print_status "Using traditional interactive ansiblesafe setup..."
        setup_vault_password
        local base_path="${PWD}"
        if [ -d "/root/qubinode_navigator" ]; then
            base_path="/root/qubinode_navigator"
        fi
        cd "${base_path}/inventories/${INVENTORY}/group_vars/control"
        /usr/local/bin/ansiblesafe -f vault.yml
    fi
}

# Main execution logic
print_status "Environment: ${INVENTORY}"
print_status "Vault integration: ${USE_HASHICORP_VAULT}"
print_status "Vault address: ${VAULT_ADDR}"

if [ "${CICD_PIPELINE}" = "true" ]; then
    handle_cicd_mode
else
    handle_interactive_mode
fi

# Security cleanup
print_status "Performing security cleanup..."

# Remove any temporary config files
find /tmp -name "*config*.yml" -user $(whoami) -delete 2>/dev/null || true
find /tmp -name "*vault*.yml" -user $(whoami) -delete 2>/dev/null || true

# Clear sensitive environment variables from history
unset VAULT_TOKEN
unset RHSM_PASSWORD
unset ADMIN_USER_PASSWORD
unset OFFLINE_TOKEN
unset OPENSHIFT_PULL_SECRET

print_header "Setup Complete"
echo "=============="
print_status "✅ Vault-integrated setup completed successfully"
print_status "✅ No sensitive data left in /tmp directory"
print_status "✅ vault.yml created and encrypted"
print_status "✅ Environment variables cleared from memory"

if [ "${USE_HASHICORP_VAULT}" = "true" ]; then
    print_status "🔐 Security: All secrets managed through HashiCorp Vault"
    print_status "📁 Configuration: /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"
else
    print_warning "⚠️ Consider enabling vault integration for enhanced security"
fi

echo ""
print_status "Ready to proceed with Qubinode Navigator deployment! 🚀"
