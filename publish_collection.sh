#!/bin/bash

# =============================================================================
# Ansible Galaxy Collection Publishing Script
# =============================================================================
#
# This script publishes the updated qubinode_kvmhost_setup_collection to
# Ansible Galaxy with CentOS Stream 10 support.
#
# Prerequisites:
# 1. Ansible Galaxy API token configured
# 2. Collection built successfully
# 3. All tests passing

set -e

COLLECTION_DIR="/root/qubinode_navigator/qubinode_kvmhost_setup_collection"
COLLECTION_VERSION="0.9.27"
COLLECTION_TARBALL="tosin2013-qubinode_kvmhost_setup_collection-${COLLECTION_VERSION}.tar.gz"

echo "🚀 Ansible Galaxy Collection Publishing Process"
echo "================================================"

# Change to collection directory
cd "$COLLECTION_DIR"

# Verify collection tarball exists
if [ ! -f "$COLLECTION_TARBALL" ]; then
    echo "❌ Collection tarball not found: $COLLECTION_TARBALL"
    echo "🔧 Building collection..."
    ansible-galaxy collection build
fi

echo "✅ Collection tarball found: $COLLECTION_TARBALL"

# Verify collection structure
echo "🔍 Verifying collection structure..."
ansible-galaxy collection install "$COLLECTION_TARBALL" --force

# Run collection tests (if available)
echo "🧪 Running collection validation..."
if [ -f "test-validation.yml" ]; then
    echo "📋 Running validation playbook..."
    ansible-playbook test-validation.yml
else
    echo "⚠️ No validation playbook found, skipping tests"
fi

# Display collection information
echo "📊 Collection Information:"
echo "  - Namespace: tosin2013"
echo "  - Name: qubinode_kvmhost_setup_collection"
echo "  - Version: $COLLECTION_VERSION"
echo "  - Features: RHEL 8/9/10, CentOS Stream 10, Rocky Linux, AlmaLinux support"
echo "  - New in this version: CentOS Stream 10 support with Python 3.12 and enhanced container support"

# Check if Galaxy token is configured
if [ -z "$ANSIBLE_GALAXY_TOKEN" ] && [ ! -f ~/.ansible/galaxy_token" ]; then
    echo "⚠️ Ansible Galaxy token not configured"
    echo "📋 To publish, you need to:"
    echo "   1. Get your API token from https://galaxy.ansible.com/me/preferences"
    echo "   2. Set ANSIBLE_GALAXY_TOKEN environment variable, or"
    echo "   3. Save token to ~/.ansible/galaxy_token"
    echo ""
    echo "🔧 Example:"
    echo "   export ANSIBLE_GALAXY_TOKEN='your-token-here'"
    echo "   ansible-galaxy collection publish $COLLECTION_TARBALL"
    echo ""
    echo "📝 Manual publishing command:"
    echo "   ansible-galaxy collection publish $COLLECTION_TARBALL --api-key YOUR_TOKEN"
    exit 1
fi

# Publish to Galaxy
echo "📤 Publishing to Ansible Galaxy..."
ansible-galaxy collection publish "$COLLECTION_TARBALL"

if [ $? -eq 0 ]; then
    echo "🎉 Collection published successfully!"
    echo "🔗 View at: https://galaxy.ansible.com/tosin2013/qubinode_kvmhost_setup_collection"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Update requirements.yml files to use version $COLLECTION_VERSION"
    echo "   2. Test collection installation: ansible-galaxy collection install tosin2013.qubinode_kvmhost_setup_collection:$COLLECTION_VERSION"
    echo "   3. Update documentation with new features"
else
    echo "❌ Publishing failed. Check the error messages above."
    exit 1
fi
