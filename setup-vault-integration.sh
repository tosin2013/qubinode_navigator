#!/bin/bash
# Setup script for HashiCorp Vault integration with Qubinode Navigator
# This script helps configure vault integration and test connectivity

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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
    echo -e "${BLUE}[SETUP]${NC} $1"
}

# Check if running from correct directory
if [ ! -f "enhanced-load-variables.py" ]; then
    print_error "Please run this script from the qubinode_navigator directory"
    exit 1
fi

print_header "HashiCorp Vault Integration Setup for Qubinode Navigator"
echo "========================================================"

# Step 1: Check dependencies
print_status "Checking Python dependencies..."
python3 -c "import jinja2, hvac, yaml" 2>/dev/null || {
    print_warning "Installing required Python packages..."
    pip3 install --user jinja2 hvac pyyaml
}
print_status "✅ Python dependencies verified"

# Step 2: Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env-example..."
    if [ -f ".env-example" ]; then
        cp .env-example .env
        chmod 600 .env
        print_status "✅ Created .env file from example (permissions set to 600)"
        print_warning "Please edit .env file with your actual values before proceeding"
    else
        print_error ".env-example file not found. Please create it first."
        exit 1
    fi
else
    print_status "✅ .env file exists"
fi

# Step 3: Load environment variables
if [ -f ".env" ]; then
    print_status "Loading environment variables from .env file..."
    set -a  # automatically export all variables
    source .env
    set +a
fi

# Step 4: Validate required variables
print_status "Validating required environment variables..."

required_vars=("INVENTORY" "RHSM_USERNAME" "ADMIN_USER_PASSWORD")
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
    print_warning "Please update your .env file with the missing values"
    exit 1
fi

print_status "✅ Required environment variables validated"

# Step 5: Test basic configuration generation
print_status "Testing basic configuration generation..."
python3 enhanced-load-variables.py --generate-config --template default.yml.j2 || {
    print_error "Failed to generate basic configuration"
    exit 1
}

if [ -f "/tmp/config.yml" ]; then
    print_status "✅ Basic configuration generation successful"
    print_status "Generated configuration preview:"
    head -20 /tmp/config.yml | sed 's/^/  /'
else
    print_error "Configuration file was not created"
    exit 1
fi

# Step 6: Test HashiCorp Vault integration (if enabled)
if [ "${USE_HASHICORP_VAULT}" = "true" ]; then
    print_status "Testing HashiCorp Vault integration..."

    # Detect vault type
    if [ "${OPENSHIFT_VAULT}" = "true" ]; then
        print_status "Detected OpenShift Vault configuration"

        # Check if running in OpenShift/Kubernetes
        if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]; then
            print_status "Running in Kubernetes/OpenShift environment"
            print_status "Using Kubernetes authentication method"
        else
            print_warning "Not running in Kubernetes environment, but OPENSHIFT_VAULT=true"
            print_status "Will attempt token-based authentication"
        fi
    elif [ "${USE_HASHICORP_CLOUD}" = "true" ]; then
        print_status "Detected HCP Vault Secrets configuration"
    else
        print_status "Detected local/standard Vault configuration"
    fi

    # Check vault connectivity
    if [ -n "${VAULT_ADDR}" ] && ([ -n "${VAULT_TOKEN}" ] || [ "${OPENSHIFT_VAULT}" = "true" ]); then
        print_status "Checking vault connectivity to ${VAULT_ADDR}..."
        
        # Test vault connection using Python
        python3 -c "
import hvac
import os
import sys

try:
    client = hvac.Client(url='${VAULT_ADDR}', token='${VAULT_TOKEN}')
    if client.is_authenticated():
        print('✅ Vault authentication successful')
        
        # Test reading a secret (optional)
        try:
            response = client.secrets.kv.v2.read_secret_version(path='ansiblesafe/${INVENTORY}')
            print('✅ Vault secret read test successful')
        except Exception as e:
            print('⚠️  Vault secret read test failed (this is normal for new setups):', str(e))
    else:
        print('❌ Vault authentication failed')
        sys.exit(1)
except Exception as e:
    print('❌ Vault connection failed:', str(e))
    sys.exit(1)
" || {
            print_error "Vault connectivity test failed"
            print_warning "Please check your VAULT_ADDR and VAULT_TOKEN settings"
            exit 1
        }
        
        print_status "✅ HashiCorp Vault integration test successful"
        
        # Test vault update functionality
        print_status "Testing vault update functionality..."
        python3 enhanced-load-variables.py --generate-config --update-vault || {
            print_warning "Vault update test failed (this may be due to permissions)"
        }
        
    else
        print_warning "VAULT_ADDR or VAULT_TOKEN not set. Skipping vault connectivity test."
    fi
else
    print_status "HashiCorp Vault integration disabled (USE_HASHICORP_VAULT=false)"
fi

# Step 7: Test environment-specific templates
print_status "Testing environment-specific templates..."

if [ -f "templates/${INVENTORY}.yml.j2" ]; then
    print_status "Testing ${INVENTORY}-specific template..."
    python3 enhanced-load-variables.py --generate-config --template "${INVENTORY}.yml.j2" || {
        print_warning "Environment-specific template test failed"
    }
else
    print_status "No environment-specific template found for ${INVENTORY}"
    print_status "Available templates:"
    ls -1 templates/*.j2 2>/dev/null | sed 's/^/  /' || echo "  No templates found"
fi

# Step 8: Security check
print_status "Performing security checks..."

# Check file permissions
if [ -f ".env" ]; then
    env_perms=$(stat -c "%a" .env)
    if [ "$env_perms" != "600" ]; then
        print_warning ".env file permissions are $env_perms, should be 600"
        chmod 600 .env
        print_status "✅ Fixed .env file permissions"
    else
        print_status "✅ .env file permissions are secure (600)"
    fi
fi

# Check for sensitive data in git
if [ -d ".git" ]; then
    if git check-ignore .env >/dev/null 2>&1; then
        print_status "✅ .env file is properly ignored by git"
    else
        print_warning ".env file is not in .gitignore"
        echo ".env" >> .gitignore
        print_status "✅ Added .env to .gitignore"
    fi
fi

# Step 9: Summary and next steps
print_header "Setup Summary"
echo "=============="
print_status "✅ Dependencies installed and verified"
print_status "✅ Environment configuration validated"
print_status "✅ Basic configuration generation working"

if [ "${USE_HASHICORP_VAULT}" = "true" ]; then
    print_status "✅ HashiCorp Vault integration configured"
else
    print_status "ℹ️  HashiCorp Vault integration disabled"
fi

print_status "✅ Security checks completed"

echo ""
print_header "Next Steps"
echo "=========="
echo "1. Review and customize your .env file with actual values"
echo "2. Test configuration generation:"
echo "   python3 enhanced-load-variables.py --generate-config"
echo ""
echo "3. For vault integration, set up vault authentication:"
echo "   export USE_HASHICORP_VAULT=true"
echo "   export VAULT_ADDR=https://your-vault-server:8200"
echo "   export VAULT_TOKEN=your-vault-token"
echo ""
echo "4. Test vault integration:"
echo "   python3 enhanced-load-variables.py --generate-config --update-vault"
echo ""
echo "5. Create environment-specific templates in templates/ directory"
echo ""

print_status "Setup completed successfully! 🎉"
