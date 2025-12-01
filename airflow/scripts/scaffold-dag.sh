#!/bin/bash
# scaffold-dag.sh - Generate DAG contribution scaffolding
# ADR-0046: DAG Factory Pattern for Consistent Deployments
#
# This script creates the initial structure for a new DAG contribution:
# - Component directory with deploy.sh template
# - README.md documentation
# - registry.yaml entry (printed, not auto-added)
#
# Usage:
#   ./scaffold-dag.sh <component_name> <category> "<description>"
#
# Example:
#   ./scaffold-dag.sh keycloak identity "Deploy Keycloak Identity Provider"
#
# Categories:
#   compute    - VMs, containers, clusters
#   network    - Routers, firewalls, load balancers
#   identity   - Authentication, authorization, directory services
#   storage    - Persistent storage, backups
#   security   - PKI, secrets management, scanning
#   monitoring - Logging, metrics, alerting

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Valid categories
VALID_CATEGORIES=("compute" "network" "identity" "storage" "security" "monitoring")

# Arguments
COMPONENT="${1:-}"
CATEGORY="${2:-}"
DESCRIPTION="${3:-}"

# Help function
show_help() {
    echo "scaffold-dag.sh - Generate DAG contribution scaffolding"
    echo ""
    echo "Usage:"
    echo "  $0 <component_name> <category> \"<description>\""
    echo ""
    echo "Arguments:"
    echo "  component_name  - snake_case name for the component (e.g., keycloak, harbor)"
    echo "  category        - One of: compute, network, identity, storage, security, monitoring"
    echo "  description     - Brief description of what the component deploys"
    echo ""
    echo "Categories:"
    echo "  compute    - VMs, containers, clusters"
    echo "  network    - Routers, firewalls, load balancers"
    echo "  identity   - Authentication, authorization, directory services"
    echo "  storage    - Persistent storage, backups"
    echo "  security   - PKI, secrets management, scanning"
    echo "  monitoring - Logging, metrics, alerting"
    echo ""
    echo "Examples:"
    echo "  $0 keycloak identity \"Deploy Keycloak Identity Provider\""
    echo "  $0 harbor storage \"Deploy Harbor Container Registry\""
    echo "  $0 prometheus monitoring \"Deploy Prometheus Monitoring Stack\""
    echo ""
    echo "After running this script:"
    echo "  1. Edit <component>/deploy.sh with your deployment logic"
    echo "  2. Add the registry entry to dags/registry.yaml"
    echo "  3. Run local validation"
    echo "  4. Submit PR to kcli-pipelines"
}

# Validate arguments
if [ -z "$COMPONENT" ] || [ -z "$CATEGORY" ] || [ -z "$DESCRIPTION" ]; then
    echo -e "${RED}[ERROR]${NC} Missing required arguments"
    echo ""
    show_help
    exit 1
fi

# Validate component name (snake_case)
if ! [[ "$COMPONENT" =~ ^[a-z][a-z0-9_]*$ ]]; then
    echo -e "${RED}[ERROR]${NC} Component name must be snake_case: '$COMPONENT'"
    echo "Examples: keycloak, harbor_registry, step_ca"
    exit 1
fi

# Validate category
VALID=false
for cat in "${VALID_CATEGORIES[@]}"; do
    if [ "$cat" == "$CATEGORY" ]; then
        VALID=true
        break
    fi
done

if [ "$VALID" != "true" ]; then
    echo -e "${RED}[ERROR]${NC} Invalid category: '$CATEGORY'"
    echo "Valid categories: ${VALID_CATEGORIES[*]}"
    exit 1
fi

echo -e "${BLUE}[INFO]${NC} Scaffolding DAG for: $COMPONENT"
echo "  Category: $CATEGORY"
echo "  Description: $DESCRIPTION"
echo ""

# Create component directory
mkdir -p "$COMPONENT"
echo -e "${GREEN}[OK]${NC} Created directory: $COMPONENT/"

# Create deploy.sh
cat > "$COMPONENT/deploy.sh" << 'DEPLOY_TEMPLATE'
#!/bin/bash
# Component: COMPONENT_PLACEHOLDER
# Description: DESCRIPTION_PLACEHOLDER
# Usage: ACTION=create ./deploy.sh
#
# This script is called by Airflow DAGs via SSH (ADR-0046).
#
# Environment Variables:
#   ACTION          - Required: create, delete, or status
#   COMPONENT_PLACEHOLDER_VERSION - Optional: version to deploy
#
# Prerequisites:
#   - kcli installed and configured
#   - Required VM images available
#   - Network connectivity

set -euo pipefail

# Source common environment if available
if [ -f /opt/kcli-pipelines/helper_scripts/default.env ]; then
    source /opt/kcli-pipelines/helper_scripts/default.env
fi

# Configuration with defaults
COMPONENT_VERSION="${COMPONENT_PLACEHOLDER_VERSION:-1.0.0}"
VM_NAME="${VM_NAME:-COMPONENT_PLACEHOLDER}"

# =============================================================================
# Functions
# =============================================================================

function create() {
    echo "[INFO] Creating COMPONENT_PLACEHOLDER..."
    echo "[INFO] Version: $COMPONENT_VERSION"

    # TODO: Add your deployment logic here
    # Example using kcli:
    # kcli create vm \
    #     -P image=fedora39 \
    #     -P memory=4096 \
    #     -P numcpus=2 \
    #     "$VM_NAME"

    # Verify deployment
    # kcli list vm | grep -q "$VM_NAME" || {
    #     echo "[ERROR] VM creation failed"
    #     exit 1
    # }

    echo "[OK] COMPONENT_PLACEHOLDER created successfully"
}

function destroy() {
    echo "[INFO] Destroying COMPONENT_PLACEHOLDER..."

    # TODO: Add your cleanup logic here
    # Example using kcli:
    # if kcli list vm | grep -q "$VM_NAME"; then
    #     kcli delete vm "$VM_NAME" -y
    # fi

    echo "[OK] COMPONENT_PLACEHOLDER destroyed successfully"
}

function status() {
    echo "[INFO] Checking COMPONENT_PLACEHOLDER status..."

    # TODO: Add your status check logic here
    # Example using kcli:
    # if kcli list vm | grep -q "$VM_NAME"; then
    #     echo "[OK] COMPONENT_PLACEHOLDER VM is running"
    #     kcli info vm "$VM_NAME"
    # else
    #     echo "[WARN] COMPONENT_PLACEHOLDER VM not found"
    # fi

    echo "[INFO] Status check complete"
}

# =============================================================================
# Main Entry Point
# =============================================================================

case "${ACTION:-help}" in
    create)
        create
        ;;
    delete|destroy)
        destroy
        ;;
    status)
        status
        ;;
    help|*)
        echo "COMPONENT_PLACEHOLDER Deployment Script"
        echo ""
        echo "Usage: ACTION=create|delete|status $0"
        echo ""
        echo "Environment Variables:"
        echo "  ACTION                      - Required: create, delete, or status"
        echo "  COMPONENT_PLACEHOLDER_VERSION - Optional: version to deploy (default: 1.0.0)"
        echo "  VM_NAME                     - Optional: VM name (default: COMPONENT_PLACEHOLDER)"
        echo ""
        echo "Examples:"
        echo "  ACTION=create ./deploy.sh"
        echo "  ACTION=delete ./deploy.sh"
        echo "  ACTION=status ./deploy.sh"
        exit 1
        ;;
esac
DEPLOY_TEMPLATE

# Replace placeholders in deploy.sh
sed -i "s/COMPONENT_PLACEHOLDER/$COMPONENT/g" "$COMPONENT/deploy.sh"
sed -i "s/DESCRIPTION_PLACEHOLDER/$DESCRIPTION/g" "$COMPONENT/deploy.sh"

# Make executable
chmod +x "$COMPONENT/deploy.sh"
echo -e "${GREEN}[OK]${NC} Created: $COMPONENT/deploy.sh"

# Create README.md
COMPONENT_TITLE=$(echo "$COMPONENT" | sed 's/_/ /g' | sed 's/\b\(.\)/\u\1/g')
cat > "$COMPONENT/README.md" << README_TEMPLATE
# $COMPONENT_TITLE

## Description

$DESCRIPTION

## Prerequisites

- kcli installed and configured
- Required VM images available (e.g., fedora39, centos9stream)
- Network connectivity to target hypervisor
- Sufficient resources (CPU, memory, storage)

## Usage

### Via Airflow DAG

Trigger the \`${COMPONENT}_deployment\` DAG from the Airflow UI:

1. Navigate to Airflow UI
2. Find \`${COMPONENT}_deployment\` DAG
3. Click "Trigger DAG"
4. Set parameters as needed
5. Monitor execution

### Via Command Line

\`\`\`bash
cd /opt/kcli-pipelines/$COMPONENT

# Create
ACTION=create ./deploy.sh

# Check status
ACTION=status ./deploy.sh

# Delete
ACTION=delete ./deploy.sh
\`\`\`

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| ACTION | (required) | create, delete, or status |
| ${COMPONENT^^}_VERSION | 1.0.0 | Version to deploy |
| VM_NAME | $COMPONENT | VM name for kcli |

## Architecture

\`\`\`
+------------------+
|   $COMPONENT_TITLE     |
|                  |
| [Add diagram]    |
+------------------+
\`\`\`

## Post-Deployment

After successful deployment:

1. Verify the service is running
2. Configure any required settings
3. Test connectivity

## Troubleshooting

### Common Issues

**Issue: VM creation fails**
- Check kcli connectivity: \`kcli list vm\`
- Verify image exists: \`kcli list images\`
- Check available resources: \`virsh nodeinfo\`

**Issue: Service doesn't start**
- Check VM console: \`kcli console $COMPONENT\`
- Review logs on the VM

## Related ADRs

- ADR-0045: DAG Development Standards
- ADR-0046: Validation Pipeline and Host Execution
- ADR-0047: kcli-pipelines Integration

## Contributing

See the [Contributor Guide](../../docs/adrs/adr-0046-dag-validation-pipeline-and-host-execution.md#contributor-guide-adding-a-new-dag) for detailed instructions.
README_TEMPLATE

echo -e "${GREEN}[OK]${NC} Created: $COMPONENT/README.md"

# Print registry entry
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Registry Entry for dags/registry.yaml${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Add this entry to your dags/registry.yaml file:${NC}"
echo ""
cat << REGISTRY_ENTRY
  # $COMPONENT_TITLE
  - component: $COMPONENT
    description: $DESCRIPTION
    script_path: /opt/kcli-pipelines/$COMPONENT
    tags: [$CATEGORY, $COMPONENT]
    category: $CATEGORY
    params:
      action: create
REGISTRY_ENTRY

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}[OK] Scaffolding complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $COMPONENT/deploy.sh with your deployment logic"
echo "  2. Update $COMPONENT/README.md with specific details"
echo "  3. Add the registry entry shown above to dags/registry.yaml"
echo "  4. Run local validation:"
echo "     python3 -c \"import yaml; print(yaml.safe_load(open('dags/registry.yaml')))\""
echo "  5. Test deploy.sh manually:"
echo "     ACTION=create ./$COMPONENT/deploy.sh"
echo "  6. Submit PR to kcli-pipelines"
echo ""
