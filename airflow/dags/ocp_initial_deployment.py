"""
OCP Initial Deployment DAG for Disconnected Environments
ADR Reference: ADR 0012, ADR 0014, ADR 0018

This DAG orchestrates the complete initial deployment workflow for OpenShift
in a disconnected environment, including:
1. Environment validation
2. Provision registry VM (via kcli) - ADR 0018
3. Certificate setup
4. Registry deployment (to VM)
5. Image mirroring (download to tar)
6. Push to local registry
7. Appliance build
8. Deployment summary

Designed to run on qubinode_navigator's Airflow instance.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule

# Configuration - can be overridden via DAG params
DEFAULT_CONFIG = {
    "ocp_version": "4.20.0",
    "registry_type": "mirror-registry",  # Options: mirror-registry (recommended), harbor, jfrog
    "mirror_path": "/opt/openshift-mirror",
    "pull_secret_path": "/root/pull-secret.json",
    "playbooks_path": "/root/ocp4-disconnected-helper/playbooks",
    "extra_vars_path": "/root/ocp4-disconnected-helper/extra_vars",
    "clean_mirror": "false",  # 'true' for full mirror, 'false' for incremental
    "provision_registry_vm": "true",  # Set to 'false' to use localhost
    "registry_vm_name": "registry",
    "registry_vm_memory": "8192",
    "registry_vm_cpus": "4",
    "registry_vm_disk_size": "500",
}

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
    "ocp_initial_deployment",
    default_args=default_args,
    description="Complete OCP deployment workflow for disconnected environments",
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=["ocp4-disconnected-helper", "openshift", "deployment", "disconnected"],
    params={
        "ocp_version": "4.20.0",
        "registry_type": "mirror-registry",  # Options: mirror-registry, harbor, jfrog
        "clean_mirror": "false",
    },
    doc_md=__doc__,
)

# ============================================================================
# Task 1: Validate Environment
# ============================================================================
validate_environment = BashOperator(
    task_id="validate_environment",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 TASK 1: Validating Environment"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    ERRORS=0

    # Check required binaries
    echo "Checking required binaries..."
    for cmd in podman ansible-playbook oc oc-mirror; do
        if command -v $cmd &> /dev/null; then
            VERSION=$($cmd --version 2>/dev/null | head -1)
            echo "✅ $cmd: $VERSION"
        else
            echo "❌ $cmd: NOT FOUND"
            ERRORS=$((ERRORS + 1))
        fi
    done

    # Check pull secret
    echo ""
    echo "Checking pull secret..."
    PULL_SECRET="{{ params.pull_secret_path | default('/root/pull-secret.json') }}"
    if [ -f "$PULL_SECRET" ]; then
        echo "✅ Pull secret found: $PULL_SECRET"
    else
        echo "❌ Pull secret not found: $PULL_SECRET"
        ERRORS=$((ERRORS + 1))
    fi

    # Check playbooks directory
    echo ""
    echo "Checking playbooks..."
    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    if [ -d "$PLAYBOOKS_PATH" ]; then
        echo "✅ Playbooks directory: $PLAYBOOKS_PATH"
        ls -la "$PLAYBOOKS_PATH"/*.yml 2>/dev/null | head -10
    else
        echo "❌ Playbooks directory not found: $PLAYBOOKS_PATH"
        ERRORS=$((ERRORS + 1))
    fi

    # Check disk space
    echo ""
    echo "Checking disk space..."
    MIRROR_PATH="{{ params.mirror_path | default('/opt/openshift-mirror') }}"
    mkdir -p "$MIRROR_PATH" 2>/dev/null || true
    AVAIL=$(df -BG "$MIRROR_PATH" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G')
    if [ "$AVAIL" -gt 100 ]; then
        echo "✅ Available space: ${AVAIL}GB (minimum 100GB required)"
    else
        echo "⚠️  Available space: ${AVAIL}GB (100GB+ recommended)"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ $ERRORS -gt 0 ]; then
        echo "❌ Validation FAILED with $ERRORS error(s)"
        exit 1
    else
        echo "✅ Environment validation PASSED"
    fi
    """,
    dag=dag,
)

# ============================================================================
# Task 2: Provision Registry VM (ADR 0018)
# ============================================================================
provision_registry_vm = BashOperator(
    task_id="provision_registry_vm",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🖥️  TASK 2: Provisioning Registry VM"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    PROVISION_VM="{{ params.provision_registry_vm | default('true') }}"
    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    VM_NAME="{{ params.registry_vm_name | default('registry') }}"
    VM_MEMORY="{{ params.registry_vm_memory | default('8192') }}"
    VM_CPUS="{{ params.registry_vm_cpus | default('4') }}"
    VM_DISK="{{ params.registry_vm_disk_size | default('500') }}"

    if [ "$PROVISION_VM" = "false" ]; then
        echo "Skipping VM provisioning (provision_registry_vm=false)"
        echo "Registry will be deployed to localhost"
        exit 0
    fi

    cd "$PLAYBOOKS_PATH"

    # Check if VM already exists
    if kcli info vm "$VM_NAME" >/dev/null 2>&1; then
        echo "Registry VM '$VM_NAME' already exists"
        kcli info vm "$VM_NAME"
    else
        echo "Creating registry VM: $VM_NAME"
        echo "  Memory: ${VM_MEMORY}MB"
        echo "  CPUs:   $VM_CPUS"
        echo "  Disk:   ${VM_DISK}GB"

        ansible-playbook -i inventory provision-registry-vm.yml \
            -e "registry_vm_name=$VM_NAME" \
            -e "registry_vm_memory=$VM_MEMORY" \
            -e "registry_vm_cpus=$VM_CPUS" \
            -e "registry_vm_disk_size=$VM_DISK" -v
    fi

    echo "✅ Registry VM ready"
    """,
    execution_timeout=timedelta(minutes=30),
    dag=dag,
)

# ============================================================================
# Task 3: Setup Certificates
# ============================================================================
setup_certificates = BashOperator(
    task_id="setup_certificates",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔐 TASK 3: Setting Up Certificates"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    CERT_PLAYBOOK="$PLAYBOOKS_PATH/setup-certificates.yml"

    if [ -f "$CERT_PLAYBOOK" ]; then
        echo "Running certificate setup playbook..."
        cd "$PLAYBOOKS_PATH"
        ansible-playbook -i inventory setup-certificates.yml -v
    else
        echo "⚠️  Certificate playbook not found: $CERT_PLAYBOOK"
        echo "Skipping certificate setup - ensure certificates are configured manually"
        echo "See ADR 0016: Trusted Certificate Management"
    fi

    echo "✅ Certificate setup complete"
    """,
    dag=dag,
)

# ============================================================================
# Task 3: Setup Registry
# ============================================================================
setup_registry = BashOperator(
    task_id="setup_registry",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 TASK 3: Setting Up Registry"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    REGISTRY_TYPE="{{ params.registry_type | default('harbor') }}"

    echo "Registry type: $REGISTRY_TYPE"

    cd "$PLAYBOOKS_PATH"

    if [ "$REGISTRY_TYPE" = "mirror-registry" ]; then
        echo "Deploying Quay mirror-registry (recommended)..."
        if [ -f "setup-mirror-registry.yml" ]; then
            ansible-playbook -i inventory setup-mirror-registry.yml -v
        else
            echo "❌ mirror-registry playbook not found"
            exit 1
        fi
    elif [ "$REGISTRY_TYPE" = "harbor" ]; then
        echo "Deploying Harbor registry..."
        if [ -f "setup-harbor-registry.yml" ]; then
            ansible-playbook -i inventory setup-harbor-registry.yml -v
        else
            echo "❌ Harbor playbook not found"
            exit 1
        fi
    elif [ "$REGISTRY_TYPE" = "jfrog" ]; then
        echo "Deploying JFrog Artifactory..."
        if [ -f "setup-jfrog-registry.yml" ]; then
            ansible-playbook -i inventory setup-jfrog-registry.yml -v
        else
            echo "❌ JFrog playbook not found"
            exit 1
        fi
    else
        echo "❌ Unknown registry type: $REGISTRY_TYPE"
        echo "   Valid options: mirror-registry, harbor, jfrog"
        exit 1
    fi

    echo "✅ Registry setup complete"
    """,
    dag=dag,
)

# ============================================================================
# Task 4: Download Images to TAR
# ============================================================================
download_to_tar = BashOperator(
    task_id="download_to_tar",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⬇️  TASK 4: Downloading Images to TAR"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    EXTRA_VARS_PATH="{{ params.extra_vars_path | default('/root/ocp4-disconnected-helper/extra_vars') }}"
    OCP_VERSION="{{ params.ocp_version | default('4.20.0') }}"
    CLEAN_MIRROR="{{ params.clean_mirror | default('false') }}"
    PULL_SECRET="{{ params.pull_secret_path | default('/root/pull-secret.json') }}"

    echo "OCP Version: $OCP_VERSION"
    echo "Clean Mirror: $CLEAN_MIRROR"
    echo "Pull Secret: $PULL_SECRET"

    cd "$PLAYBOOKS_PATH"

    # Build extra vars
    EXTRA_VARS="ocp_version=$OCP_VERSION"
    EXTRA_VARS="$EXTRA_VARS clean_mirror_path=$CLEAN_MIRROR"
    EXTRA_VARS="$EXTRA_VARS local_rh_pull_secret_path=$PULL_SECRET"

    # Check for extra vars file
    if [ -f "$EXTRA_VARS_PATH/download-to-tar.yml" ]; then
        echo "Using extra vars file: $EXTRA_VARS_PATH/download-to-tar.yml"
        ansible-playbook -i inventory download-to-tar.yml \
            -e "@$EXTRA_VARS_PATH/download-to-tar.yml" \
            -e "$EXTRA_VARS" -v
    else
        echo "Running with default configuration..."
        ansible-playbook -i inventory download-to-tar.yml \
            -e "$EXTRA_VARS" -v
    fi

    echo "✅ Download to TAR complete"
    """,
    execution_timeout=timedelta(hours=4),  # Mirroring can take a long time
    dag=dag,
)

# ============================================================================
# Task 5: Push TAR to Registry
# ============================================================================
push_to_registry = BashOperator(
    task_id="push_to_registry",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⬆️  TASK 5: Pushing Images to Registry"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    EXTRA_VARS_PATH="{{ params.extra_vars_path | default('/root/ocp4-disconnected-helper/extra_vars') }}"

    cd "$PLAYBOOKS_PATH"

    # Check for extra vars file
    if [ -f "$EXTRA_VARS_PATH/push-tar-to-registry.yml" ]; then
        echo "Using extra vars file: $EXTRA_VARS_PATH/push-tar-to-registry.yml"
        ansible-playbook -i inventory push-tar-to-registry.yml \
            -e "@$EXTRA_VARS_PATH/push-tar-to-registry.yml" -v
    else
        echo "Running with default configuration..."
        ansible-playbook -i inventory push-tar-to-registry.yml -v
    fi

    echo "✅ Push to registry complete"
    """,
    execution_timeout=timedelta(hours=2),
    dag=dag,
)

# ============================================================================
# Task 6: Build Appliance
# ============================================================================
build_appliance = BashOperator(
    task_id="build_appliance",
    bash_command="""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔧 TASK 6: Building OpenShift Appliance"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    PLAYBOOKS_PATH="{{ params.playbooks_path | default('/root/ocp4-disconnected-helper/playbooks') }}"
    EXTRA_VARS_PATH="{{ params.extra_vars_path | default('/root/ocp4-disconnected-helper/extra_vars') }}"
    OCP_VERSION="{{ params.ocp_version | default('4.20.0') }}"
    REGISTRY_TYPE="{{ params.registry_type | default('mirror-registry') }}"

    cd "$PLAYBOOKS_PATH"

    # Check if build-appliance playbook exists
    if [ ! -f "build-appliance.yml" ]; then
        echo "❌ build-appliance.yml not found"
        echo "See ADR 0005: OpenShift Appliance Builder"
        exit 1
    fi

    # Determine local registry URI based on registry type
    # The registry was set up in Task 3 and populated in Tasks 4-5
    REGISTRY_HOST="{{ ansible_fqdn | default('localhost') }}"
    case "$REGISTRY_TYPE" in
        mirror-registry)
            LOCAL_REGISTRY_URI="${REGISTRY_HOST}:8443"
            ;;
        harbor)
            LOCAL_REGISTRY_URI="${REGISTRY_HOST}:443"
            ;;
        jfrog)
            LOCAL_REGISTRY_URI="${REGISTRY_HOST}:8082"
            ;;
        *)
            LOCAL_REGISTRY_URI="${REGISTRY_HOST}:8443"
            ;;
    esac

    echo "Using local registry: $LOCAL_REGISTRY_URI"
    echo "Registry type: $REGISTRY_TYPE"
    echo ""
    echo "NOTE: This task uses the local registry populated by previous tasks:"
    echo "  - Task 3: Registry setup ($REGISTRY_TYPE)"
    echo "  - Task 4: Downloaded OCP images to TAR"
    echo "  - Task 5: Pushed images to local registry"
    echo ""

    # Build extra vars - use local registry with mirrored content
    EXTRA_VARS="ocp_release_version=$OCP_VERSION use_local_registry=true local_registry_uri=$LOCAL_REGISTRY_URI"

    # Check for extra vars file
    if [ -f "$EXTRA_VARS_PATH/build-appliance.yml" ]; then
        echo "Using extra vars file: $EXTRA_VARS_PATH/build-appliance.yml"
        ansible-playbook -i inventory build-appliance.yml \
            -e "@$EXTRA_VARS_PATH/build-appliance.yml" \
            -e "$EXTRA_VARS" -v
    else
        echo "Running with default configuration..."
        ansible-playbook -i inventory build-appliance.yml \
            -e "$EXTRA_VARS" -v
    fi

    echo "✅ Appliance build complete"
    """,
    execution_timeout=timedelta(hours=2),
    dag=dag,
)

# ============================================================================
# Task 7: Deployment Summary
# ============================================================================
deployment_summary = BashOperator(
    task_id="deployment_summary",
    bash_command="""
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 DEPLOYMENT SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "OCP Version:    {{ params.ocp_version | default('4.20.0') }}"
    echo "Registry Type:  {{ params.registry_type | default('harbor') }}"
    echo "Clean Mirror:   {{ params.clean_mirror | default('false') }}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📁 Generated Artifacts"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    MIRROR_PATH="{{ params.mirror_path | default('/opt/openshift-mirror') }}"

    echo ""
    echo "Mirror Path: $MIRROR_PATH"
    if [ -d "$MIRROR_PATH" ]; then
        echo "Contents:"
        ls -lah "$MIRROR_PATH" 2>/dev/null | head -20

        # Check for TAR files
        TAR_COUNT=$(find "$MIRROR_PATH" -name "*.tar" 2>/dev/null | wc -l)
        echo ""
        echo "TAR files found: $TAR_COUNT"

        # Check for appliance
        if [ -f "$MIRROR_PATH/appliance.raw" ]; then
            APPLIANCE_SIZE=$(ls -lh "$MIRROR_PATH/appliance.raw" | awk '{print $5}')
            echo "Appliance image: $MIRROR_PATH/appliance.raw ($APPLIANCE_SIZE)"
        fi
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📖 Next Steps"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Transfer appliance image to disconnected environment"
    echo "2. Boot target nodes from appliance"
    echo "3. Complete agent-based installation"
    echo "4. Verify cluster health"
    echo ""
    echo "Documentation:"
    echo "  - ADR 0005: OpenShift Appliance Builder"
    echo "  - ADR 0007: 3-Node Compact Cluster"
    echo "  - docs/manual-execution.md"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ OCP Initial Deployment DAG completed successfully!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    """,
    trigger_rule=TriggerRule.ALL_SUCCESS,
    dag=dag,
)

# ============================================================================
# Task Dependencies
# ============================================================================
# Linear workflow with all tasks in sequence
# Workflow: Provision VM, mirror content, then build appliance using local registry
# 1. Validate environment
# 2. Provision registry VM (via kcli) - ADR 0018
# 3. Setup certificates (for registry TLS)
# 4. Setup registry (mirror-registry/harbor/jfrog) - deployed to VM
# 5. Download images to TAR (oc-mirror)
# 6. Push TAR to local registry
# 7. Build appliance (using local registry with mirrored content)
# 8. Summary
(validate_environment >> provision_registry_vm >> setup_certificates >> setup_registry >> download_to_tar >> push_to_registry >> build_appliance >> deployment_summary)

# ============================================================================
# DAG Documentation
# ============================================================================
dag.doc_md = """
# OCP Initial Deployment DAG

**Project:** ocp4-disconnected-helper
**ADR References:** ADR 0012, ADR 0014, ADR 0018

## Overview

This DAG orchestrates the complete initial deployment workflow for OpenShift
in a disconnected environment. It automates the following steps:

1. **Validate Environment** - Check prerequisites (binaries, pull secret, disk space)
2. **Provision Registry VM** - Create dedicated VM for registry via kcli (ADR 0018)
3. **Setup Certificates** - Generate/configure TLS certificates (ADR 0016)
4. **Setup Registry** - Deploy mirror-registry/Harbor/JFrog to VM
5. **Download to TAR** - Mirror OCP images using oc-mirror
6. **Push to Registry** - Upload images to local registry
7. **Build Appliance** - Create bootable appliance image
8. **Deployment Summary** - Report results and next steps

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ocp_version` | 4.20.0 | OpenShift version to deploy |
| `registry_type` | mirror-registry | Registry type (mirror-registry, harbor, jfrog) |
| `clean_mirror` | false | Full mirror (true) or incremental (false) |
| `provision_registry_vm` | true | Create dedicated VM for registry |
| `registry_vm_name` | registry | Name of registry VM |
| `registry_vm_memory` | 8192 | VM memory in MB |
| `registry_vm_disk_size` | 500 | VM disk size in GB |

## Triggering

### Via Airflow UI
1. Navigate to http://localhost:8888
2. Find `ocp_initial_deployment` DAG
3. Click "Trigger DAG" button
4. Optionally configure parameters
5. Click "Trigger"

### Via Airflow CLI
```bash
airflow dags trigger ocp_initial_deployment \\
    --conf '{"ocp_version": "4.20.0", "registry_type": "harbor"}'
```

### Via MCP Server
```python
trigger_dag("ocp_initial_deployment", {
    "ocp_version": "4.20.0",
    "registry_type": "harbor",
    "clean_mirror": "false"
})
```

## Prerequisites

- qubinode_navigator deployed with Airflow
- Pull secret at `/root/pull-secret.json`
- ocp4-disconnected-helper cloned
- Sufficient disk space (100GB+ recommended)

## Execution Time

Typical execution times:
- Validate Environment: ~1 minute
- Setup Certificates: ~2 minutes
- Setup Registry: ~10 minutes
- Download to TAR: 1-4 hours (depends on content)
- Push to Registry: 30-120 minutes
- Build Appliance: 30-60 minutes

**Total: 2-6 hours** (first run with full mirror)

## Related DAGs

- `ocp_incremental_update` - For cluster updates
- `ocp_registry_setup` - Registry-only deployment
- `ocp_health_check` - Cluster health validation

## Troubleshooting

### Task Failures
1. Check task logs in Airflow UI
2. Review Ansible playbook output
3. Verify prerequisites are met

### Common Issues
- **Pull secret invalid**: Refresh from cloud.redhat.com
- **Disk space**: Ensure 100GB+ available
- **Registry connection**: Check certificates (ADR 0016)
- **oc-mirror timeout**: Increase `execution_timeout`

## Files

- DAG: `airflow/dags/ocp_initial_deployment.py`
- Playbooks: `playbooks/*.yml`
- Extra vars: `extra_vars/*.yml`
"""
