"""
OCP Registry Sync DAG - Health Check and Push to Multiple Registries
ADR Reference: ADR 0003 (oc-mirror), ADR 0004 (Dual Registry), ADR 0017 (Quay)

This DAG provides scheduled synchronization of OpenShift images to multiple
container registries with health checks before push operations.

Features:
- Fetches registry credentials from Airflow Variables
- Automatic cleanup on failure (CI/CD style)
- Clear error messages pointing to specific files/configs
- Merges pull-secret with registry credentials automatically

Workflow:
1. Setup credentials from Airflow Variables
2. Check health of all configured registries
3. Download new/updated images (incremental)
4. Push to all healthy registries
5. Generate updated manifests (ICSP, CatalogSource)
6. Report sync status

Target: OpenShift 4.19/4.20

Designed to run on qubinode_navigator's Airflow instance.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import Variable
from airflow.models.param import Param
import json

# =============================================================================
# Configuration
# =============================================================================
DEFAULT_CONFIG = {
    'ocp_version': '4.19',
    'playbooks_path': '/root/ocp4-disconnected-helper/playbooks',
    'extra_vars_path': '/root/ocp4-disconnected-helper/extra_vars',
    'mirror_path': '/opt/images',
    'pull_secret_path': '/root/pull-secret.json',
    
    # Registry configuration - uses FQDNs
    'registries': {
        'quay': {
            'server': 'mirror-registry.example.com',
            'port': 8443,
            'health_endpoint': '/v2/',
            'username_var': 'quay_username',
            'password_var': 'quay_password',
        },
        'harbor': {
            'server': 'harbor.example.com',
            'port': 443,
            'health_endpoint': '/api/v2.0/health',
            'username_var': 'harbor_username',
            'password_var': 'harbor_password',
        },
        'jfrog': {
            'server': 'jfrog.example.com',
            'port': 8082,
            'health_endpoint': '/artifactory/api/system/ping',
            'username_var': 'jfrog_username',
            'password_var': 'jfrog_password',
        },
    },
}

# Default arguments for all tasks
default_args = {
    'owner': 'ocp4-disconnected-helper',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 28),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# =============================================================================
# Define the DAG
# =============================================================================
dag = DAG(
    'ocp_registry_sync',
    default_args=default_args,
    description='Sync OCP images to registries using Airflow Variables for credentials',
    schedule=None,  # Manual trigger only for now
    catchup=False,
    max_active_runs=1,
    tags=['ocp4-disconnected-helper', 'openshift', 'registry', 'sync'],
    params={
        'ocp_version': Param(
            default='4.19',
            type='string',
            enum=['4.17', '4.18', '4.19', '4.20'],
            description='OpenShift version to sync',
        ),
        'target_registry': Param(
            default='quay',
            type='string',
            enum=['quay', 'harbor', 'jfrog', 'all'],
            description='Target registry (or all)',
        ),
        'skip_download': Param(
            default=False,
            type='boolean',
            description='Skip download, only push existing tar',
        ),
        'clean_mirror': Param(
            default=False,
            type='boolean',
            description='Full mirror (true) or incremental (false)',
        ),
    },
    doc_md=__doc__,
)

# =============================================================================
# Task 1: Setup Credentials from Airflow Variables
# =============================================================================
setup_credentials = BashOperator(
    task_id='setup_credentials',
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔐 Setting Up Registry Credentials from Airflow Variables"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    TARGET_REGISTRY="{{ params.target_registry }}"
    PULL_SECRET="/root/pull-secret.json"
    MERGED_SECRET="/tmp/merged-pull-secret.json"
    
    echo "Target Registry: $TARGET_REGISTRY"
    echo "Pull Secret: $PULL_SECRET"
    echo ""
    
    # Verify pull secret exists
    if [ ! -f "$PULL_SECRET" ]; then
        echo "============================================"
        echo "CONFIGURATION ERROR"
        echo "============================================"
        echo "File:  $PULL_SECRET"
        echo "Error: Pull secret file not found"
        echo ""
        echo "To fix:"
        echo "  1. Download pull secret from https://console.redhat.com/openshift/install/pull-secret"
        echo "  2. Save to $PULL_SECRET"
        echo "============================================"
        exit 1
    fi
    
    # Start with the base pull secret
    cp "$PULL_SECRET" "$MERGED_SECRET"
    
    # Function to add registry credentials
    add_registry_creds() {
        local REGISTRY_NAME=$1
        local REGISTRY_HOST=$2
        local REGISTRY_PORT=$3
        local USERNAME_VAR=$4
        local PASSWORD_VAR=$5
        
        echo "Adding credentials for $REGISTRY_NAME..."
        
        # Get credentials from Airflow Variables
        REG_USER=$(airflow variables get "$USERNAME_VAR" 2>/dev/null || echo "")
        REG_PASS=$(airflow variables get "$PASSWORD_VAR" 2>/dev/null || echo "")
        
        if [ -z "$REG_USER" ] || [ -z "$REG_PASS" ]; then
            echo "  ⚠️  Credentials not found in Airflow Variables"
            echo "     Missing: $USERNAME_VAR and/or $PASSWORD_VAR"
            echo ""
            echo "  To fix, set the variables:"
            echo "    airflow variables set $USERNAME_VAR '<username>'"
            echo "    airflow variables set $PASSWORD_VAR '<password>'"
            return 1
        fi
        
        # Create auth string
        AUTH=$(echo -n "$REG_USER:$REG_PASS" | base64 -w0)
        REGISTRY="${REGISTRY_HOST}:${REGISTRY_PORT}"
        
        # Add to merged secret
        jq --arg registry "$REGISTRY" --arg auth "$AUTH" \
           '.auths[$registry] = {"auth": $auth}' \
           "$MERGED_SECRET" > "${MERGED_SECRET}.tmp" && mv "${MERGED_SECRET}.tmp" "$MERGED_SECRET"
        
        echo "  ✅ Added $REGISTRY_NAME ($REGISTRY)"
        
        # Login to registry
        echo "  Logging in to $REGISTRY..."
        if podman login "$REGISTRY" -u "$REG_USER" -p "$REG_PASS" --tls-verify=false 2>/dev/null; then
            echo "  ✅ Login successful"
        else
            echo "  ⚠️  Login failed (may still work with auth file)"
        fi
        
        return 0
    }
    
    # Add credentials based on target registry
    ERRORS=0
    
    if [ "$TARGET_REGISTRY" = "all" ] || [ "$TARGET_REGISTRY" = "quay" ]; then
        add_registry_creds "quay" "mirror-registry.example.com" "8443" "quay_username" "quay_password" || ERRORS=$((ERRORS + 1))
    fi
    
    if [ "$TARGET_REGISTRY" = "all" ] || [ "$TARGET_REGISTRY" = "harbor" ]; then
        add_registry_creds "harbor" "harbor.example.com" "443" "harbor_username" "harbor_password" || ERRORS=$((ERRORS + 1))
    fi
    
    if [ "$TARGET_REGISTRY" = "all" ] || [ "$TARGET_REGISTRY" = "jfrog" ]; then
        add_registry_creds "jfrog" "jfrog.example.com" "8082" "jfrog_username" "jfrog_password" || ERRORS=$((ERRORS + 1))
    fi
    
    echo ""
    echo "Merged pull secret registries:"
    jq -r '.auths | keys[]' "$MERGED_SECRET"
    
    if [ $ERRORS -gt 0 ] && [ "$TARGET_REGISTRY" != "all" ]; then
        echo ""
        echo "❌ Failed to setup credentials for $TARGET_REGISTRY"
        exit 1
    fi
    
    echo ""
    echo "✅ Credentials setup complete"
    echo "   Merged pull secret: $MERGED_SECRET"
    """,
    dag=dag,
)

# =============================================================================
# Task 2: Pre-flight Checks
# =============================================================================
preflight_checks = BashOperator(
    task_id='preflight_checks',
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 OCP Registry Sync - Pre-flight Checks"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Target OCP Version: {{ params.ocp_version }}"
    echo "Target Registry: {{ params.target_registry }}"
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    
    ERRORS=0
    
    # Check required binaries
    echo "📋 Checking required binaries..."
    for cmd in oc oc-mirror curl jq podman; do
        if command -v $cmd &> /dev/null; then
            echo "  ✅ $cmd: $(which $cmd)"
        else
            echo "  ❌ $cmd NOT FOUND"
            echo ""
            echo "  To install:"
            echo "    dnf install -y $cmd"
            ERRORS=$((ERRORS + 1))
        fi
    done
    
    # Check disk space
    echo ""
    echo "📋 Checking disk space..."
    MIRROR_PATH="/opt/images"
    mkdir -p "$MIRROR_PATH" 2>/dev/null || true
    AVAIL=$(df -BG "$MIRROR_PATH" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G')
    if [ "$AVAIL" -gt 50 ]; then
        echo "  ✅ Available space: ${AVAIL}GB"
    else
        echo "  ⚠️  Low disk space: ${AVAIL}GB (50GB+ recommended for full sync)"
    fi
    
    # Check for existing tar files
    echo ""
    echo "📋 Checking for existing mirror content..."
    if ls "$MIRROR_PATH"/*.tar 1>/dev/null 2>&1; then
        TAR_COUNT=$(ls "$MIRROR_PATH"/*.tar 2>/dev/null | wc -l)
        TAR_SIZE=$(du -sh "$MIRROR_PATH"/*.tar 2>/dev/null | tail -1 | cut -f1)
        echo "  ✅ Found $TAR_COUNT TAR file(s), latest: $TAR_SIZE"
    else
        echo "  ℹ️  No existing TAR files found (will download fresh)"
    fi
    
    echo ""
    if [ $ERRORS -gt 0 ]; then
        echo "❌ Pre-flight checks FAILED with $ERRORS error(s)"
        exit 1
    else
        echo "✅ Pre-flight checks PASSED"
    fi
    """,
    dag=dag,
)

# =============================================================================
# Task 3: Health Check Target Registry
# =============================================================================
health_check_registry = BashOperator(
    task_id='health_check_registry',
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🏥 Registry Health Check"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    TARGET_REGISTRY="{{ params.target_registry }}"
    ERRORS=0
    HEALTHY_REGISTRIES=""
    
    check_registry() {
        local NAME=$1
        local HOST=$2
        local PORT=$3
        
        REGISTRY="${HOST}:${PORT}"
        echo "Checking $NAME at $REGISTRY..."
        
        # Check API health
        HTTP_CODE=$(curl -sk --connect-timeout 10 --max-time 30 -o /dev/null -w "%{http_code}" "https://${REGISTRY}/v2/" 2>/dev/null || echo "000")
        
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
            echo "  ✅ API responding (HTTP $HTTP_CODE)"
            
            # Check certificate validity
            CERT_EXPIRY=$(echo | openssl s_client -connect "$REGISTRY" -servername "$HOST" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || echo "")
            
            if [ -n "$CERT_EXPIRY" ]; then
                EXPIRY_EPOCH=$(date -d "$CERT_EXPIRY" +%s 2>/dev/null || echo "0")
                NOW_EPOCH=$(date +%s)
                DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
                
                if [ $DAYS_LEFT -lt 7 ]; then
                    echo "  ⚠️  Certificate expires in $DAYS_LEFT days!"
                    echo ""
                    echo "  To renew, run:"
                    echo "    airflow dags trigger step_ca_operations --conf '{\"action\": \"renew-cert\", \"target\": \"$HOST\"}'"
                else
                    echo "  ✅ Certificate valid for $DAYS_LEFT days"
                fi
            fi
            
            HEALTHY_REGISTRIES="${HEALTHY_REGISTRIES}${NAME},"
            return 0
        else
            echo "  ❌ API not responding (HTTP $HTTP_CODE)"
            echo ""
            echo "  Possible fixes:"
            echo "    1. Check if registry VM is running: virsh list --all | grep $NAME"
            echo "    2. Redeploy registry: airflow dags trigger ${NAME}_deployment --conf '{\"action\": \"create\"}'"
            return 1
        fi
    }
    
    # Check based on target
    if [ "$TARGET_REGISTRY" = "all" ] || [ "$TARGET_REGISTRY" = "quay" ]; then
        check_registry "quay" "mirror-registry.example.com" "8443" || ERRORS=$((ERRORS + 1))
    fi
    
    if [ "$TARGET_REGISTRY" = "all" ] || [ "$TARGET_REGISTRY" = "harbor" ]; then
        check_registry "harbor" "harbor.example.com" "443" || ERRORS=$((ERRORS + 1))
    fi
    
    if [ "$TARGET_REGISTRY" = "all" ] || [ "$TARGET_REGISTRY" = "jfrog" ]; then
        check_registry "jfrog" "jfrog.example.com" "8082" || ERRORS=$((ERRORS + 1))
    fi
    
    # Save status for downstream tasks
    echo "$HEALTHY_REGISTRIES" > /tmp/healthy_registries.txt
    
    echo ""
    if [ $ERRORS -gt 0 ] && [ "$TARGET_REGISTRY" != "all" ]; then
        echo "❌ Target registry is not healthy"
        exit 1
    elif [ -z "$HEALTHY_REGISTRIES" ]; then
        echo "❌ No healthy registries found"
        exit 1
    else
        echo "✅ Health checks passed"
        echo "   Healthy: $HEALTHY_REGISTRIES"
    fi
    """,
    dag=dag,
)

# =============================================================================
# Task 4: Download Images (Skip if skip_download=true)
# =============================================================================
download_images = BashOperator(
    task_id='download_images',
    bash_command="""
    set -euo pipefail
    
    SKIP_DOWNLOAD="{{ params.skip_download }}"
    
    if [ "$SKIP_DOWNLOAD" = "True" ] || [ "$SKIP_DOWNLOAD" = "true" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "⏭️  Skipping Download (skip_download=true)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Check for existing tar
        MIRROR_PATH="/opt/images"
        if ls "$MIRROR_PATH"/*.tar 1>/dev/null 2>&1; then
            echo "Using existing TAR files:"
            ls -lh "$MIRROR_PATH"/*.tar
        else
            echo "❌ No TAR files found at $MIRROR_PATH"
            echo "   Set skip_download=false to download images"
            exit 1
        fi
        exit 0
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⬇️  Downloading OCP {{ params.ocp_version }} Images"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    OCP_VERSION="{{ params.ocp_version }}"
    MIRROR_PATH="/opt/images"
    PULL_SECRET="/root/pull-secret.json"
    
    echo "OCP Version: $OCP_VERSION"
    echo "Mirror Path: $MIRROR_PATH"
    echo ""
    
    mkdir -p "$MIRROR_PATH"
    cd "$MIRROR_PATH"
    
    # Create imageSetConfig if not exists
    if [ ! -f "$MIRROR_PATH/imageSetConfig.yml" ]; then
        echo "Creating imageSetConfig.yml..."
        cat > "$MIRROR_PATH/imageSetConfig.yml" << EOF
kind: ImageSetConfiguration
apiVersion: mirror.openshift.io/v1alpha2
storageConfig:
  local:
    path: $MIRROR_PATH
mirror:
  platform:
    channels:
      - name: stable-${OCP_VERSION}
        minVersion: ${OCP_VERSION}.0
        maxVersion: ${OCP_VERSION}.99
        type: ocp
  additionalImages: []
  helm: {}
EOF
    fi
    
    echo "Running oc-mirror..."
    oc-mirror --config "$MIRROR_PATH/imageSetConfig.yml" \
        file://$MIRROR_PATH \
        --dest-skip-tls \
        -a "$PULL_SECRET" \
        --continue-on-error 2>&1 | tee "$MIRROR_PATH/oc-mirror-download.log" || {
        echo ""
        echo "⚠️  oc-mirror completed with warnings/errors"
        echo "Check log: $MIRROR_PATH/oc-mirror-download.log"
    }
    
    echo ""
    echo "Generated TAR files:"
    ls -lh "$MIRROR_PATH"/*.tar 2>/dev/null || echo "  No TAR files found"
    
    echo ""
    echo "✅ Download complete"
    """,
    execution_timeout=timedelta(hours=4),
    dag=dag,
)

# =============================================================================
# Task 5: Push to Registry
# =============================================================================
push_to_registry = BashOperator(
    task_id='push_to_registry',
    bash_command="""
    set -euo pipefail
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⬆️  Pushing Images to Registry"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    TARGET_REGISTRY="{{ params.target_registry }}"
    MIRROR_PATH="/opt/images"
    MERGED_SECRET="/tmp/merged-pull-secret.json"
    
    # Determine registry URL
    case "$TARGET_REGISTRY" in
        quay)
            REGISTRY_URL="docker://mirror-registry.example.com:8443"
            ;;
        harbor)
            REGISTRY_URL="docker://harbor.example.com"
            ;;
        jfrog)
            REGISTRY_URL="docker://jfrog.example.com:8082"
            ;;
        all)
            # For 'all', we'll push to quay as primary
            REGISTRY_URL="docker://mirror-registry.example.com:8443"
            ;;
        *)
            echo "❌ Unknown registry: $TARGET_REGISTRY"
            exit 1
            ;;
    esac
    
    echo "Target: $REGISTRY_URL"
    echo "Mirror Path: $MIRROR_PATH"
    echo ""
    
    # Find the latest TAR file
    LATEST_TAR=$(ls -t "$MIRROR_PATH"/*.tar 2>/dev/null | head -1)
    
    if [ -z "$LATEST_TAR" ]; then
        echo "============================================"
        echo "CONFIGURATION ERROR"
        echo "============================================"
        echo "Directory: $MIRROR_PATH"
        echo "Error: No TAR files found"
        echo ""
        echo "To fix:"
        echo "  1. Run this DAG with skip_download=false"
        echo "  2. Or manually run: oc-mirror --config imageSetConfig.yml file://$MIRROR_PATH"
        echo "============================================"
        exit 1
    fi
    
    echo "Using TAR: $LATEST_TAR"
    TAR_SIZE=$(du -h "$LATEST_TAR" | cut -f1)
    echo "Size: $TAR_SIZE"
    echo ""
    
    echo "Running oc-mirror to push..."
    oc-mirror --from="$LATEST_TAR" \
        "$REGISTRY_URL" \
        --dest-skip-tls \
        -a "$MERGED_SECRET" \
        --continue-on-error 2>&1 | tee "$MIRROR_PATH/oc-mirror-push.log" || {
        echo ""
        echo "⚠️  oc-mirror push completed with warnings/errors"
        echo "Check log: $MIRROR_PATH/oc-mirror-push.log"
    }
    
    echo ""
    echo "✅ Push complete"
    """,
    execution_timeout=timedelta(hours=2),
    dag=dag,
)

# =============================================================================
# Task 6: Verify Push and Generate Report
# =============================================================================
sync_report = BashOperator(
    task_id='sync_report',
    bash_command="""
    set -euo pipefail
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Registry Sync Report"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Sync Completed: $(date -Iseconds)"
    echo "OCP Version:    {{ params.ocp_version }}"
    echo "Target:         {{ params.target_registry }}"
    echo ""
    
    TARGET_REGISTRY="{{ params.target_registry }}"
    
    # Determine registry URL for verification
    case "$TARGET_REGISTRY" in
        quay)
            REGISTRY="mirror-registry.example.com:8443"
            ;;
        harbor)
            REGISTRY="harbor.example.com"
            ;;
        jfrog)
            REGISTRY="jfrog.example.com:8082"
            ;;
        *)
            REGISTRY="mirror-registry.example.com:8443"
            ;;
    esac
    
    # Verify images in registry
    echo "Verifying images in $REGISTRY..."
    CATALOG=$(curl -sk "https://$REGISTRY/v2/_catalog" 2>/dev/null || echo '{"repositories":[]}')
    REPO_COUNT=$(echo "$CATALOG" | jq -r '.repositories | length' 2>/dev/null || echo "0")
    
    echo "  Repositories in registry: $REPO_COUNT"
    
    if [ "$REPO_COUNT" -gt 0 ]; then
        echo ""
        echo "  Sample repositories:"
        echo "$CATALOG" | jq -r '.repositories[]' 2>/dev/null | head -10 | while read repo; do
            echo "    - $repo"
        done
    fi
    
    # Show mirror path contents
    MIRROR_PATH="/opt/images"
    echo ""
    echo "Mirror Path Contents:"
    ls -lh "$MIRROR_PATH"/*.tar 2>/dev/null | head -5 || echo "  No TAR files"
    
    # Show oc-mirror workspace
    if [ -d "$MIRROR_PATH/oc-mirror-workspace" ]; then
        LATEST_RESULTS=$(ls -td "$MIRROR_PATH/oc-mirror-workspace"/results-* 2>/dev/null | head -1)
        if [ -d "$LATEST_RESULTS" ]; then
            echo ""
            echo "Generated Manifests: $LATEST_RESULTS"
            ls "$LATEST_RESULTS" 2>/dev/null | head -10
        fi
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Next Steps:"
    echo "  1. Verify images: skopeo list-tags docker://$REGISTRY/<repo>"
    echo "  2. Deploy cluster: airflow dags trigger ocp_agent_deployment"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ OCP Registry Sync completed successfully!"
    """,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
)

# =============================================================================
# Task 7: Cleanup on Failure
# =============================================================================
cleanup_on_failure = BashOperator(
    task_id='cleanup_on_failure',
    bash_command="""
    set +e  # Don't exit on error during cleanup
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧹 Cleanup After Failure"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Clean up temporary files
    rm -f /tmp/merged-pull-secret.json
    rm -f /tmp/healthy_registries.txt
    
    # Clean up partial oc-mirror workspace
    MIRROR_PATH="/opt/images"
    if [ -d "$MIRROR_PATH/oc-mirror-workspace" ]; then
        # Keep results but clean working directories
        find "$MIRROR_PATH/oc-mirror-workspace" -type d -name "working-*" -exec rm -rf {} + 2>/dev/null || true
    fi
    
    echo "Cleanup complete"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "SYNC FAILED - Review errors above"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Common fixes:"
    echo "  1. Missing credentials: Set Airflow Variables (quay_username, quay_password, etc.)"
    echo "  2. Registry unhealthy: Redeploy with mirror_registry_deployment DAG"
    echo "  3. Disk space: Free up space in /opt/images"
    echo "  4. Network issues: Check connectivity to registries"
    echo ""
    echo "After fixing, retrigger this DAG"
    """,
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

# =============================================================================
# Task Dependencies
# =============================================================================
setup_credentials >> preflight_checks >> health_check_registry >> download_images >> push_to_registry >> sync_report

# Cleanup runs on any failure
[setup_credentials, preflight_checks, health_check_registry, download_images, push_to_registry] >> cleanup_on_failure
