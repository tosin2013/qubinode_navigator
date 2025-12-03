"""
OCP Incremental Update DAG for Disconnected Environments
ADR Reference: ADR 0006 (Lifecycle Management), ADR 0012 (Airflow DAG Orchestration)

This DAG orchestrates incremental cluster updates in disconnected environments:
1. Pre-update validation
2. Incremental image download
3. Push to local registry
4. Apply ICSP/IDMS manifests
5. Trigger cluster update
6. Monitor update progress
7. Update summary

Designed to run on qubinode_navigator's Airflow instance.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule

# Default arguments for all tasks
default_args = {
    "owner": "ocp4-disconnected-helper",
    "depends_on_past": False,
    "start_date": datetime(2025, 11, 26),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    "ocp_incremental_update",
    default_args=default_args,
    description="Incremental OCP cluster update workflow for disconnected environments",
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=[
        "ocp4-disconnected-helper",
        "openshift",
        "update",
        "lifecycle",
        "disconnected",
    ],
    params={
        "current_version": "4.20.0",
        "target_version": "4.20.1",
        "kubeconfig_path": "/root/.kube/config",
        "skip_validation": "false",
    },
    doc_md=__doc__,
)

# ============================================================================
# Task 1: Pre-Update Validation
# ============================================================================
pre_update_validation = BashOperator(
    task_id="pre_update_validation",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 TASK 1: Pre-Update Validation"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    SKIP_VALIDATION="{{ params.skip_validation | default('false') }}"
    KUBECONFIG="{{ params.kubeconfig_path | default('/root/.kube/config') }}"
    CURRENT_VERSION="{{ params.current_version | default('4.20.0') }}"
    TARGET_VERSION="{{ params.target_version | default('4.20.1') }}"

    if [ "$SKIP_VALIDATION" = "true" ]; then
        echo "⚠️  Skipping validation (skip_validation=true)"
        exit 0
    fi

    echo "Current Version: $CURRENT_VERSION"
    echo "Target Version:  $TARGET_VERSION"
    echo "Kubeconfig:      $KUBECONFIG"
    echo ""

    ERRORS=0

    # Check kubeconfig exists
    if [ ! -f "$KUBECONFIG" ]; then
        echo "❌ Kubeconfig not found: $KUBECONFIG"
        ERRORS=$((ERRORS + 1))
    else
        echo "✅ Kubeconfig found"
    fi

    # Check cluster connectivity
    echo ""
    echo "Checking cluster connectivity..."
    export KUBECONFIG="$KUBECONFIG"

    if oc cluster-info &>/dev/null; then
        echo "✅ Cluster is reachable"

        # Get current cluster version
        CLUSTER_VERSION=$(oc get clusterversion version -o jsonpath='{.status.desired.version}' 2>/dev/null)
        echo "   Cluster version: $CLUSTER_VERSION"

        # Check cluster health
        echo ""
        echo "Checking cluster operators..."
        DEGRADED=$(oc get co -o jsonpath='{.items[?(@.status.conditions[?(@.type=="Degraded")].status=="True")].metadata.name}' 2>/dev/null)
        if [ -n "$DEGRADED" ]; then
            echo "⚠️  Degraded operators: $DEGRADED"
        else
            echo "✅ No degraded operators"
        fi

        # Check nodes
        echo ""
        echo "Checking nodes..."
        NOT_READY=$(oc get nodes -o jsonpath='{.items[?(@.status.conditions[?(@.type=="Ready")].status!="True")].metadata.name}' 2>/dev/null)
        if [ -n "$NOT_READY" ]; then
            echo "❌ Nodes not ready: $NOT_READY"
            ERRORS=$((ERRORS + 1))
        else
            echo "✅ All nodes ready"
        fi

    else
        echo "❌ Cannot connect to cluster"
        ERRORS=$((ERRORS + 1))
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ $ERRORS -gt 0 ]; then
        echo "❌ Pre-update validation FAILED with $ERRORS error(s)"
        exit 1
    else
        echo "✅ Pre-update validation PASSED"
    fi
    """,
    dag=dag,
)

# ============================================================================
# Task 2: Download Incremental Images
# ============================================================================
download_incremental = BashOperator(
    task_id="download_incremental",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⬇️  TASK 2: Downloading Incremental Images"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    EXTRA_VARS_PATH="{{ params.extra_vars_path | default('/root/ocp4-disconnected-helper/extra_vars') }}"
    TARGET_VERSION="{{ params.target_version | default('4.20.1') }}"

    echo "Target Version: $TARGET_VERSION"
    echo "Using incremental mirror (clean_mirror_path=false)"
    echo ""

    cd "$PLAYBOOKS_PATH"

    # Incremental mirror - preserves oc-mirror-workspace state
    EXTRA_VARS="ocp_version=$TARGET_VERSION clean_mirror_path=false"

    if [ -f "$EXTRA_VARS_PATH/download-to-tar.yml" ]; then
        echo "Using extra vars file..."
        ansible-playbook -i inventory download-to-tar.yml \
            -e "@$EXTRA_VARS_PATH/download-to-tar.yml" \
            -e "$EXTRA_VARS" -v
    else
        ansible-playbook -i inventory download-to-tar.yml \
            -e "$EXTRA_VARS" -v
    fi

    echo "✅ Incremental download complete"
    """,
    execution_timeout=timedelta(hours=2),
    dag=dag,
)

# ============================================================================
# Task 3: Push to Registry
# ============================================================================
push_to_registry = BashOperator(
    task_id="push_to_registry",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⬆️  TASK 3: Pushing Images to Registry"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    EXTRA_VARS_PATH="{{ params.extra_vars_path | default('/root/ocp4-disconnected-helper/extra_vars') }}"

    cd "$PLAYBOOKS_PATH"

    if [ -f "$EXTRA_VARS_PATH/push-tar-to-registry.yml" ]; then
        ansible-playbook -i inventory push-tar-to-registry.yml \
            -e "@$EXTRA_VARS_PATH/push-tar-to-registry.yml" -v
    else
        ansible-playbook -i inventory push-tar-to-registry.yml -v
    fi

    echo "✅ Push to registry complete"
    """,
    execution_timeout=timedelta(hours=1),
    dag=dag,
)

# ============================================================================
# Task 4: Apply ICSP/IDMS Manifests
# ============================================================================
apply_manifests = BashOperator(
    task_id="apply_manifests",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📄 TASK 4: Applying ICSP/IDMS Manifests"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    KUBECONFIG="{{ params.kubeconfig_path | default('/root/.kube/config') }}"
    MIRROR_PATH="{{ params.mirror_path | default('/opt/openshift-mirror') }}"

    export KUBECONFIG="$KUBECONFIG"

    # Find and apply ICSP/IDMS manifests from oc-mirror output
    RESULTS_DIR="$MIRROR_PATH/oc-mirror-workspace/results-*"

    echo "Looking for manifests in: $RESULTS_DIR"

    for dir in $RESULTS_DIR; do
        if [ -d "$dir" ]; then
            echo "Found results directory: $dir"

            # Apply ImageContentSourcePolicy (OCP < 4.13)
            if ls "$dir"/*ImageContentSourcePolicy*.yaml &>/dev/null 2>&1; then
                echo "Applying ImageContentSourcePolicy..."
                oc apply -f "$dir"/*ImageContentSourcePolicy*.yaml
            fi

            # Apply ImageDigestMirrorSet (OCP >= 4.13)
            if ls "$dir"/*ImageDigestMirrorSet*.yaml &>/dev/null 2>&1; then
                echo "Applying ImageDigestMirrorSet..."
                oc apply -f "$dir"/*ImageDigestMirrorSet*.yaml
            fi

            # Apply CatalogSource
            if ls "$dir"/*CatalogSource*.yaml &>/dev/null 2>&1; then
                echo "Applying CatalogSource..."
                oc apply -f "$dir"/*CatalogSource*.yaml
            fi
        fi
    done

    echo ""
    echo "Waiting for MachineConfigPool to update..."
    echo "(This may take several minutes as nodes are updated)"

    # Wait for MCPs to start updating
    sleep 30

    # Check MCP status
    oc get mcp

    echo "✅ Manifests applied"
    """,
    dag=dag,
)

# ============================================================================
# Task 5: Trigger Cluster Update
# ============================================================================
trigger_update = BashOperator(
    task_id="trigger_update",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 TASK 5: Triggering Cluster Update"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    KUBECONFIG="{{ params.kubeconfig_path | default('/root/.kube/config') }}"
    TARGET_VERSION="{{ params.target_version | default('4.20.1') }}"

    export KUBECONFIG="$KUBECONFIG"

    echo "Target Version: $TARGET_VERSION"
    echo ""

    # Get current version
    CURRENT=$(oc get clusterversion version -o jsonpath='{.status.desired.version}')
    echo "Current Version: $CURRENT"

    if [ "$CURRENT" = "$TARGET_VERSION" ]; then
        echo "✅ Cluster is already at target version $TARGET_VERSION"
        exit 0
    fi

    # Check available updates
    echo ""
    echo "Checking available updates..."
    oc adm upgrade

    # Trigger the update
    echo ""
    echo "Triggering update to $TARGET_VERSION..."
    oc adm upgrade --to=$TARGET_VERSION

    echo ""
    echo "✅ Update triggered"
    echo "Monitor progress with: oc get clusterversion"
    """,
    dag=dag,
)

# ============================================================================
# Task 6: Monitor Update Progress
# ============================================================================
monitor_update = BashOperator(
    task_id="monitor_update",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 TASK 6: Monitoring Update Progress"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    KUBECONFIG="{{ params.kubeconfig_path | default('/root/.kube/config') }}"
    TARGET_VERSION="{{ params.target_version | default('4.20.1') }}"

    export KUBECONFIG="$KUBECONFIG"

    MAX_WAIT=7200  # 2 hours
    INTERVAL=60    # Check every minute
    ELAPSED=0

    echo "Monitoring update progress (max wait: $((MAX_WAIT/60)) minutes)..."
    echo ""

    while [ $ELAPSED -lt $MAX_WAIT ]; do
        # Get cluster version status
        VERSION=$(oc get clusterversion version -o jsonpath='{.status.desired.version}' 2>/dev/null)
        PROGRESSING=$(oc get clusterversion version -o jsonpath='{.status.conditions[?(@.type=="Progressing")].status}' 2>/dev/null)
        AVAILABLE=$(oc get clusterversion version -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null)
        MESSAGE=$(oc get clusterversion version -o jsonpath='{.status.conditions[?(@.type=="Progressing")].message}' 2>/dev/null)

        echo "[$(date '+%H:%M:%S')] Version: $VERSION | Progressing: $PROGRESSING | Available: $AVAILABLE"

        if [ "$VERSION" = "$TARGET_VERSION" ] && [ "$PROGRESSING" = "False" ] && [ "$AVAILABLE" = "True" ]; then
            echo ""
            echo "✅ Update to $TARGET_VERSION completed successfully!"
            exit 0
        fi

        if [ -n "$MESSAGE" ]; then
            echo "   Status: $MESSAGE"
        fi

        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    done

    echo ""
    echo "⚠️  Update monitoring timed out after $((MAX_WAIT/60)) minutes"
    echo "The update may still be in progress. Check manually with:"
    echo "  oc get clusterversion"
    echo "  oc get co"
    """,
    execution_timeout=timedelta(hours=3),
    dag=dag,
)

# ============================================================================
# Task 7: Update Summary
# ============================================================================
update_summary = BashOperator(
    task_id="update_summary",
    bash_command="""
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 UPDATE SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    KUBECONFIG="{{ params.kubeconfig_path | default('/root/.kube/config') }}"
    TARGET_VERSION="{{ params.target_version | default('4.20.1') }}"

    export KUBECONFIG="$KUBECONFIG"

    echo ""
    echo "Target Version: $TARGET_VERSION"
    echo ""

    echo "Cluster Version Status:"
    oc get clusterversion version

    echo ""
    echo "Cluster Operators:"
    oc get co | head -20

    echo ""
    echo "Nodes:"
    oc get nodes

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ OCP Incremental Update DAG completed!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    """,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ============================================================================
# Task Dependencies
# ============================================================================
(
    pre_update_validation
    >> download_incremental
    >> push_to_registry
    >> apply_manifests
    >> trigger_update
    >> monitor_update
    >> update_summary
)

# ============================================================================
# DAG Documentation
# ============================================================================
dag.doc_md = """
# OCP Incremental Update DAG

**Project:** ocp4-disconnected-helper
**ADR References:** ADR 0006, ADR 0012

## Overview

This DAG orchestrates incremental cluster updates in disconnected environments,
leveraging oc-mirror's stateful workspace for efficient delta downloads.

## Workflow

1. **Pre-Update Validation** - Verify cluster health and connectivity
2. **Download Incremental** - Mirror only new/changed images
3. **Push to Registry** - Upload to local registry
4. **Apply Manifests** - Update ICSP/IDMS configurations
5. **Trigger Update** - Initiate cluster update via CVO
6. **Monitor Progress** - Track update completion
7. **Update Summary** - Report final status

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `current_version` | 4.20.0 | Current cluster version |
| `target_version` | 4.20.1 | Target update version |
| `kubeconfig_path` | /root/.kube/config | Path to kubeconfig |
| `skip_validation` | false | Skip pre-update checks |

## Triggering

### Via MCP Server
```python
trigger_dag("ocp_incremental_update", {
    "current_version": "4.20.0",
    "target_version": "4.20.1"
})
```

## Execution Time

- Pre-validation: ~2 minutes
- Incremental download: 15-60 minutes
- Push to registry: 10-30 minutes
- Apply manifests: ~5 minutes
- Cluster update: 30-120 minutes

**Total: 1-3 hours** (typical incremental update)
"""
