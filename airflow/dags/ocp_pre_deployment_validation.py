"""
OCP Pre-Deployment Validation DAG
Validates all prerequisites before deploying an OpenShift cluster

This DAG performs comprehensive checks to ensure:
- Infrastructure is ready (Step-CA, Registry, DNS)
- Images are available in the registry
- Configuration files are valid
- Network connectivity is available

Run this DAG before ocp_agent_deployment to catch issues early.
Each validation error points to the specific file/config to fix.
"""

from datetime import datetime, timedelta

from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

from airflow import DAG

# =============================================================================
# Configuration
# =============================================================================
AGENT_INSTALL_DIR = "/root/openshift-agent-install"
EXAMPLES_DIR = f"{AGENT_INSTALL_DIR}/examples"

default_args = {
    "owner": "ocp4-disconnected-helper",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,  # No retries for validation - fail fast
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    "ocp_pre_deployment_validation",
    default_args=default_args,
    description="Validate prerequisites before OpenShift deployment",
    schedule=None,
    catchup=False,
    tags=["ocp4-disconnected-helper", "openshift", "validation", "pre-deployment"],
    params={
        "example_config": Param(
            default="sno-disconnected",
            type="string",
            description="Example configuration to validate",
        ),
        "registry_type": Param(
            default="quay",
            type="string",
            enum=["quay", "harbor", "jfrog"],
            description="Registry type to validate",
        ),
        "ocp_version": Param(
            default="4.19",
            type="string",
            enum=["4.17", "4.18", "4.19", "4.20"],
            description="Expected OpenShift version",
        ),
        "min_cert_days": Param(
            default=7,
            type="integer",
            description="Minimum days of certificate validity",
        ),
    },
    doc_md=__doc__,
)

# =============================================================================
# Task 1: Validate Step-CA Health
# =============================================================================
validate_step_ca = BashOperator(
    task_id="validate_step_ca",
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔐 Validating Step-CA Server"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    STEP_CA_HOST="step-ca-server.example.com"
    STEP_CA_PORT="443"
    
    # Check if step-ca is reachable
    echo "Checking Step-CA at $STEP_CA_HOST:$STEP_CA_PORT..."
    
    if curl -sk --connect-timeout 10 "https://${STEP_CA_HOST}:${STEP_CA_PORT}/health" 2>/dev/null | grep -q "ok"; then
        echo "  ✅ Step-CA is healthy"
    else
        # Try alternative check
        HTTP_CODE=$(curl -sk --connect-timeout 10 -o /dev/null -w "%{http_code}" "https://${STEP_CA_HOST}:${STEP_CA_PORT}/root.crt" 2>/dev/null || echo "000")
        
        if [ "$HTTP_CODE" = "200" ]; then
            echo "  ✅ Step-CA is responding (root cert available)"
        else
            echo "  ❌ Step-CA is not responding"
            echo ""
            echo "============================================"
            echo "VALIDATION ERROR"
            echo "============================================"
            echo "Service: Step-CA"
            echo "Host: $STEP_CA_HOST:$STEP_CA_PORT"
            echo "Error: Cannot reach Step-CA server"
            echo ""
            echo "To fix:"
            echo "  1. Check if Step-CA VM is running:"
            echo "     virsh list --all | grep step-ca"
            echo ""
            echo "  2. Redeploy Step-CA:"
            echo "     airflow dags trigger step_ca_deployment --conf '{\"action\": \"create\"}'"
            echo "============================================"
            exit 1
        fi
    fi
    
    echo ""
    echo "✅ Step-CA validation passed"
    """,
    dag=dag,
)

# =============================================================================
# Task 2: Validate Registry Health and Certificate
# =============================================================================
validate_registry = BashOperator(
    task_id="validate_registry",
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Validating Registry"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    REGISTRY_TYPE="{{ params.registry_type }}"
    MIN_CERT_DAYS="{{ params.min_cert_days }}"
    
    # Determine registry details
    case "$REGISTRY_TYPE" in
        quay)
            REGISTRY_HOST="mirror-registry.example.com"
            REGISTRY_PORT="8443"
            DEPLOY_DAG="mirror_registry_deployment"
            ;;
        harbor)
            REGISTRY_HOST="harbor.example.com"
            REGISTRY_PORT="443"
            DEPLOY_DAG="harbor_deployment"
            ;;
        jfrog)
            REGISTRY_HOST="jfrog.example.com"
            REGISTRY_PORT="8082"
            DEPLOY_DAG="jfrog_deployment"
            ;;
    esac
    
    REGISTRY="${REGISTRY_HOST}:${REGISTRY_PORT}"
    echo "Registry: $REGISTRY ($REGISTRY_TYPE)"
    echo ""
    
    # Check API health
    echo "Checking API health..."
    HTTP_CODE=$(curl -sk --connect-timeout 10 --max-time 30 -o /dev/null -w "%{http_code}" "https://${REGISTRY}/v2/" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
        echo "  ✅ API responding (HTTP $HTTP_CODE)"
    else
        echo "  ❌ API not responding (HTTP $HTTP_CODE)"
        echo ""
        echo "============================================"
        echo "VALIDATION ERROR"
        echo "============================================"
        echo "Service: $REGISTRY_TYPE registry"
        echo "Host: $REGISTRY"
        echo "Error: Registry API not responding"
        echo ""
        echo "To fix:"
        echo "  1. Check if registry VM is running:"
        echo "     virsh list --all | grep -i registry"
        echo ""
        echo "  2. Redeploy registry:"
        echo "     airflow dags trigger $DEPLOY_DAG --conf '{\"action\": \"create\"}'"
        echo "============================================"
        exit 1
    fi
    
    # Check certificate validity
    echo ""
    echo "Checking certificate validity..."
    CERT_INFO=$(echo | openssl s_client -connect "$REGISTRY" -servername "$REGISTRY_HOST" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "FAILED")
    
    if [ "$CERT_INFO" = "FAILED" ]; then
        echo "  ⚠️  Could not retrieve certificate (may be self-signed)"
    else
        EXPIRY=$(echo "$CERT_INFO" | grep "notAfter" | cut -d= -f2)
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || echo "0")
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
        
        echo "  Certificate expires: $EXPIRY"
        echo "  Days remaining: $DAYS_LEFT"
        
        if [ $DAYS_LEFT -lt $MIN_CERT_DAYS ]; then
            echo ""
            echo "============================================"
            echo "VALIDATION ERROR"
            echo "============================================"
            echo "Service: $REGISTRY_TYPE registry"
            echo "Host: $REGISTRY"
            echo "Error: Certificate expires in $DAYS_LEFT days (minimum: $MIN_CERT_DAYS)"
            echo ""
            echo "To fix:"
            echo "  Renew certificate:"
            echo "  airflow dags trigger step_ca_operations --conf '{\"action\": \"renew-cert\", \"target\": \"$REGISTRY_HOST\"}'"
            echo "============================================"
            exit 1
        else
            echo "  ✅ Certificate valid for $DAYS_LEFT days"
        fi
    fi
    
    echo ""
    echo "✅ Registry validation passed"
    """,
    dag=dag,
)

# =============================================================================
# Task 3: Validate Images Exist in Registry
# =============================================================================
validate_images = BashOperator(
    task_id="validate_images",
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🖼️  Validating OCP Images in Registry"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    REGISTRY_TYPE="{{ params.registry_type }}"
    OCP_VERSION="{{ params.ocp_version }}"
    
    # Determine registry
    case "$REGISTRY_TYPE" in
        quay)
            REGISTRY="mirror-registry.example.com:8443"
            ;;
        harbor)
            REGISTRY="harbor.example.com"
            ;;
        jfrog)
            REGISTRY="jfrog.example.com:8082"
            ;;
    esac
    
    echo "Registry: $REGISTRY"
    echo "Expected OCP Version: $OCP_VERSION"
    echo ""
    
    # Get catalog
    echo "Fetching registry catalog..."
    CATALOG=$(curl -sk "https://$REGISTRY/v2/_catalog" 2>/dev/null || echo '{"repositories":[]}')
    REPO_COUNT=$(echo "$CATALOG" | jq -r '.repositories | length' 2>/dev/null || echo "0")
    
    echo "Repositories found: $REPO_COUNT"
    
    if [ "$REPO_COUNT" -eq 0 ]; then
        echo ""
        echo "============================================"
        echo "VALIDATION ERROR"
        echo "============================================"
        echo "Registry: $REGISTRY"
        echo "Error: Registry is empty - no images found"
        echo ""
        echo "To fix:"
        echo "  Sync OCP images to registry:"
        echo "  airflow dags trigger ocp_registry_sync --conf '{\"ocp_version\": \"$OCP_VERSION\", \"target_registry\": \"$REGISTRY_TYPE\"}'"
        echo "============================================"
        exit 1
    fi
    
    # Check for OpenShift release images
    echo ""
    echo "Checking for OpenShift release images..."
    
    OCP_REPOS=$(echo "$CATALOG" | jq -r '.repositories[]' 2>/dev/null | grep -E "(openshift-release-dev|ocp4|openshift4)" | head -5 || echo "")
    
    if [ -z "$OCP_REPOS" ]; then
        echo "  ❌ No OpenShift release images found"
        echo ""
        echo "============================================"
        echo "VALIDATION ERROR"
        echo "============================================"
        echo "Registry: $REGISTRY"
        echo "Error: OpenShift release images not found"
        echo ""
        echo "Expected repositories like:"
        echo "  - openshift-release-dev/ocp-release"
        echo "  - ocp4/openshift4"
        echo ""
        echo "To fix:"
        echo "  Sync OCP images to registry:"
        echo "  airflow dags trigger ocp_registry_sync --conf '{\"ocp_version\": \"$OCP_VERSION\", \"target_registry\": \"$REGISTRY_TYPE\"}'"
        echo "============================================"
        exit 1
    else
        echo "  ✅ OpenShift images found:"
        echo "$OCP_REPOS" | while read repo; do
            echo "    - $repo"
        done
    fi
    
    echo ""
    echo "✅ Image validation passed"
    """,
    dag=dag,
)

# =============================================================================
# Task 4: Validate DNS Resolution
# =============================================================================
validate_dns = BashOperator(
    task_id="validate_dns",
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Validating DNS Resolution"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    EXAMPLE_CONFIG="{{ params.example_config }}"
    CONFIG_PATH="/root/openshift-agent-install/examples/$EXAMPLE_CONFIG"
    
    # Extract cluster name and domain from cluster.yml
    if [ -f "$CONFIG_PATH/cluster.yml" ]; then
        CLUSTER_NAME=$(grep "^cluster_name:" "$CONFIG_PATH/cluster.yml" 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "")
        BASE_DOMAIN=$(grep "^base_domain:" "$CONFIG_PATH/cluster.yml" 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "")
    else
        echo "  ⚠️  cluster.yml not found, using defaults"
        CLUSTER_NAME="sno-disconnected"
        BASE_DOMAIN="example.com"
    fi
    
    echo "Cluster: $CLUSTER_NAME.$BASE_DOMAIN"
    echo ""
    
    ERRORS=0
    
    # Check api.<cluster>.<domain>
    echo "Checking api.$CLUSTER_NAME.$BASE_DOMAIN..."
    API_IP=$(dig +short api.$CLUSTER_NAME.$BASE_DOMAIN 2>/dev/null | head -1 || echo "")
    
    if [ -z "$API_IP" ]; then
        echo "  ❌ DNS record not found"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ Resolves to $API_IP"
    fi
    
    # Check api-int.<cluster>.<domain>
    echo ""
    echo "Checking api-int.$CLUSTER_NAME.$BASE_DOMAIN..."
    API_INT_IP=$(dig +short api-int.$CLUSTER_NAME.$BASE_DOMAIN 2>/dev/null | head -1 || echo "")
    
    if [ -z "$API_INT_IP" ]; then
        echo "  ❌ DNS record not found"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ Resolves to $API_INT_IP"
    fi
    
    # Check *.apps.<cluster>.<domain>
    echo ""
    echo "Checking *.apps.$CLUSTER_NAME.$BASE_DOMAIN..."
    APPS_IP=$(dig +short test.apps.$CLUSTER_NAME.$BASE_DOMAIN 2>/dev/null | head -1 || echo "")
    
    if [ -z "$APPS_IP" ]; then
        echo "  ❌ Wildcard DNS not found"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ Resolves to $APPS_IP"
    fi
    
    if [ $ERRORS -gt 0 ]; then
        echo ""
        echo "============================================"
        echo "VALIDATION ERROR"
        echo "============================================"
        echo "Cluster: $CLUSTER_NAME.$BASE_DOMAIN"
        echo "Error: $ERRORS DNS record(s) missing"
        echo ""
        echo "Required DNS records:"
        echo "  - api.$CLUSTER_NAME.$BASE_DOMAIN -> <node IP>"
        echo "  - api-int.$CLUSTER_NAME.$BASE_DOMAIN -> <node IP>"
        echo "  - *.apps.$CLUSTER_NAME.$BASE_DOMAIN -> <node IP>"
        echo ""
        echo "To fix:"
        echo "  airflow dags trigger freeipa_dns_management --conf '{\"action\": \"add-cluster\", \"cluster\": \"$CLUSTER_NAME\", \"domain\": \"$BASE_DOMAIN\"}'"
        echo "============================================"
        exit 1
    fi
    
    echo ""
    echo "✅ DNS validation passed"
    """,
    dag=dag,
)

# =============================================================================
# Task 5: Validate Configuration Files
# =============================================================================
validate_config = BashOperator(
    task_id="validate_config",
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📄 Validating Configuration Files"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    EXAMPLE_CONFIG="{{ params.example_config }}"
    CONFIG_PATH="/root/openshift-agent-install/examples/$EXAMPLE_CONFIG"
    
    echo "Config Path: $CONFIG_PATH"
    echo ""
    
    ERRORS=0
    
    # Check directory exists
    if [ ! -d "$CONFIG_PATH" ]; then
        echo "============================================"
        echo "VALIDATION ERROR"
        echo "============================================"
        echo "Path: $CONFIG_PATH"
        echo "Error: Configuration directory not found"
        echo ""
        echo "Available configurations:"
        ls -1 /root/openshift-agent-install/examples/ 2>/dev/null | head -10
        echo ""
        echo "To fix:"
        echo "  Choose a valid example_config parameter"
        echo "============================================"
        exit 1
    fi
    
    # Check cluster.yml
    echo "Checking cluster.yml..."
    CLUSTER_YML="$CONFIG_PATH/cluster.yml"
    
    if [ ! -f "$CLUSTER_YML" ]; then
        echo "  ❌ File not found: $CLUSTER_YML"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ File exists"
        
        # Validate YAML syntax
        if python3 -c "import yaml; yaml.safe_load(open('$CLUSTER_YML'))" 2>/dev/null; then
            echo "  ✅ YAML syntax valid"
        else
            echo "  ❌ YAML syntax error"
            echo ""
            echo "  Run to see error details:"
            echo "    python3 -c \"import yaml; yaml.safe_load(open('$CLUSTER_YML'))\""
            ERRORS=$((ERRORS + 1))
        fi
        
        # Check required fields
        for field in cluster_name base_domain; do
            if grep -q "^$field:" "$CLUSTER_YML" 2>/dev/null; then
                VALUE=$(grep "^$field:" "$CLUSTER_YML" | head -1 | cut -d: -f2- | xargs)
                echo "  ✅ $field: $VALUE"
            else
                echo "  ❌ Missing required field: $field"
                ERRORS=$((ERRORS + 1))
            fi
        done
    fi
    
    # Check nodes.yml
    echo ""
    echo "Checking nodes.yml..."
    NODES_YML="$CONFIG_PATH/nodes.yml"
    
    if [ ! -f "$NODES_YML" ]; then
        echo "  ❌ File not found: $NODES_YML"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ File exists"
        
        # Validate YAML syntax
        if python3 -c "import yaml; yaml.safe_load(open('$NODES_YML'))" 2>/dev/null; then
            echo "  ✅ YAML syntax valid"
        else
            echo "  ❌ YAML syntax error"
            ERRORS=$((ERRORS + 1))
        fi
        
        # Check node count
        NODE_COUNT=$(grep -c "^  - name:" "$NODES_YML" 2>/dev/null || echo "0")
        echo "  Nodes defined: $NODE_COUNT"
        
        if [ "$NODE_COUNT" -eq 0 ]; then
            echo "  ❌ No nodes defined"
            ERRORS=$((ERRORS + 1))
        fi
    fi
    
    # Check for additional_trust_bundle (for disconnected)
    echo ""
    echo "Checking trust bundle..."
    if grep -q "additional_trust_bundle" "$CLUSTER_YML" 2>/dev/null; then
        echo "  ✅ Trust bundle configured"
    else
        echo "  ⚠️  No trust bundle configured (may be needed for disconnected)"
    fi
    
    if [ $ERRORS -gt 0 ]; then
        echo ""
        echo "============================================"
        echo "VALIDATION ERROR"
        echo "============================================"
        echo "Config: $CONFIG_PATH"
        echo "Errors: $ERRORS configuration error(s)"
        echo ""
        echo "To fix:"
        echo "  1. Review the errors above"
        echo "  2. Edit the configuration files:"
        echo "     vim $CLUSTER_YML"
        echo "     vim $NODES_YML"
        echo "  3. Retrigger this DAG"
        echo "============================================"
        exit 1
    fi
    
    echo ""
    echo "✅ Configuration validation passed"
    """,
    dag=dag,
)

# =============================================================================
# Task 6: Validate Pull Secret
# =============================================================================
validate_pull_secret = BashOperator(
    task_id="validate_pull_secret",
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔑 Validating Pull Secret"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    PULL_SECRET="/root/pull-secret.json"
    REGISTRY_TYPE="{{ params.registry_type }}"
    
    # Determine registry
    case "$REGISTRY_TYPE" in
        quay)
            REGISTRY="mirror-registry.example.com:8443"
            ;;
        harbor)
            REGISTRY="harbor.example.com"
            ;;
        jfrog)
            REGISTRY="jfrog.example.com:8082"
            ;;
    esac
    
    # Check pull secret exists
    if [ ! -f "$PULL_SECRET" ]; then
        echo "============================================"
        echo "VALIDATION ERROR"
        echo "============================================"
        echo "File: $PULL_SECRET"
        echo "Error: Pull secret file not found"
        echo ""
        echo "To fix:"
        echo "  1. Download from: https://console.redhat.com/openshift/install/pull-secret"
        echo "  2. Save to: $PULL_SECRET"
        echo "============================================"
        exit 1
    fi
    
    echo "Pull secret: $PULL_SECRET"
    echo ""
    
    # Validate JSON syntax
    echo "Checking JSON syntax..."
    if jq -e '.' "$PULL_SECRET" > /dev/null 2>&1; then
        echo "  ✅ Valid JSON"
    else
        echo "  ❌ Invalid JSON"
        echo ""
        echo "============================================"
        echo "VALIDATION ERROR"
        echo "============================================"
        echo "File: $PULL_SECRET"
        echo "Error: Invalid JSON syntax"
        echo ""
        echo "To fix:"
        echo "  1. Validate JSON: jq '.' $PULL_SECRET"
        echo "  2. Re-download from Red Hat console"
        echo "============================================"
        exit 1
    fi
    
    # Check for registry credentials
    echo ""
    echo "Checking registry credentials..."
    REGISTRIES=$(jq -r '.auths | keys[]' "$PULL_SECRET" 2>/dev/null)
    echo "  Configured registries:"
    echo "$REGISTRIES" | while read reg; do
        echo "    - $reg"
    done
    
    # Check if our target registry is included
    echo ""
    echo "Checking for $REGISTRY..."
    if echo "$REGISTRIES" | grep -q "$REGISTRY"; then
        echo "  ✅ Target registry credentials found"
    else
        echo "  ⚠️  Target registry not in pull secret"
        echo "     Will be added by ocp_registry_sync DAG"
    fi
    
    echo ""
    echo "✅ Pull secret validation passed"
    """,
    dag=dag,
)

# =============================================================================
# Task 7: Validate Disk Space
# =============================================================================
validate_disk_space = BashOperator(
    task_id="validate_disk_space",
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💾 Validating Disk Space"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Check /var/lib/libvirt/images (VM storage)
    echo "Checking VM storage (/var/lib/libvirt/images)..."
    if [ -d "/var/lib/libvirt/images" ]; then
        AVAIL=$(df -BG /var/lib/libvirt/images 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G')
        echo "  Available: ${AVAIL}GB"
        
        if [ "$AVAIL" -lt 100 ]; then
            echo "  ⚠️  Low space for VM deployment (recommend 100GB+)"
        else
            echo "  ✅ Sufficient space"
        fi
    else
        echo "  ⚠️  Directory not found"
    fi
    
    # Check /opt/images (mirror storage)
    echo ""
    echo "Checking mirror storage (/opt/images)..."
    mkdir -p /opt/images 2>/dev/null || true
    AVAIL=$(df -BG /opt/images 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G')
    echo "  Available: ${AVAIL}GB"
    
    # Check generated assets
    echo ""
    echo "Checking generated assets (/root/generated_assets)..."
    if [ -d "/root/generated_assets" ]; then
        USED=$(du -sh /root/generated_assets 2>/dev/null | cut -f1)
        echo "  Used: $USED"
    else
        echo "  Directory will be created during deployment"
    fi
    
    echo ""
    echo "✅ Disk space validation passed"
    """,
    dag=dag,
)

# =============================================================================
# Task 8: Generate Validation Report
# =============================================================================
validation_report = BashOperator(
    task_id="validation_report",
    bash_command="""
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Pre-Deployment Validation Report"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Timestamp: $(date -Iseconds)"
    echo "Configuration: {{ params.example_config }}"
    echo "Registry: {{ params.registry_type }}"
    echo "OCP Version: {{ params.ocp_version }}"
    echo ""
    echo "Validation Results:"
    echo "  ✅ Step-CA: Healthy"
    echo "  ✅ Registry: Healthy, certificate valid"
    echo "  ✅ Images: Available in registry"
    echo "  ✅ DNS: All records resolve"
    echo "  ✅ Config: Valid YAML, required fields present"
    echo "  ✅ Pull Secret: Valid JSON"
    echo "  ✅ Disk Space: Sufficient"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ ALL VALIDATIONS PASSED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Ready to deploy! Run:"
    echo "  airflow dags trigger ocp_agent_deployment --conf '{"
    echo "    \"example_config\": \"{{ params.example_config }}\","
    echo "    \"registry_type\": \"{{ params.registry_type }}\","
    echo "    \"deploy_on_kvm\": true"
    echo "  }'"
    """,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
)

# =============================================================================
# Task 9: Failure Summary
# =============================================================================
failure_summary = BashOperator(
    task_id="failure_summary",
    bash_command="""
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ PRE-DEPLOYMENT VALIDATION FAILED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "One or more validation checks failed."
    echo "Review the failed task logs above for specific error details."
    echo ""
    echo "Each error message includes:"
    echo "  - The specific file or service with the issue"
    echo "  - The exact error encountered"
    echo "  - Commands to fix the issue"
    echo ""
    echo "After fixing, retrigger this DAG to validate again."
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    """,
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

# =============================================================================
# Task Dependencies
# =============================================================================
# All validations run in parallel for speed
[
    validate_step_ca,
    validate_registry,
    validate_images,
    validate_dns,
    validate_config,
    validate_pull_secret,
    validate_disk_space,
] >> validation_report

# Failure summary runs if any validation fails
[
    validate_step_ca,
    validate_registry,
    validate_images,
    validate_dns,
    validate_config,
    validate_pull_secret,
    validate_disk_space,
] >> failure_summary
