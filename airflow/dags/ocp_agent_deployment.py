"""
Airflow DAG: OpenShift Agent-Based Deployment with Dropdown Parameters
Enhanced version with dynamic example discovery and registry selection

This DAG provides a flexible interface for deploying OpenShift clusters using:
- Dropdown selection for registry type (mirror-registry, harbor, jfrog, upstream)
- Dropdown selection for deployment size (sno, 3-node, full)
- Dynamic discovery of example configurations
- Optional KVM deployment for testing

Reference: https://github.com/tosin2013/openshift-agent-install
"""

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.models.param import Param

# Configuration
AGENT_INSTALL_DIR = "/root/openshift-agent-install"
EXAMPLES_DIR = f"{AGENT_INSTALL_DIR}/examples"
GENERATED_ASSETS_BASE = "/root/generated_assets"


# =============================================================================
# Dynamic Example Discovery
# =============================================================================
def discover_examples():
    """Discover available example configurations from the examples directory."""
    examples = []
    examples_path = Path(EXAMPLES_DIR)

    try:
        if examples_path.exists():
            for example_dir in sorted(examples_path.iterdir()):
                if example_dir.is_dir():
                    # Check if it has cluster.yml or nodes.yml (agent-based config)
                    has_cluster = (example_dir / "cluster.yml").exists()
                    has_nodes = (example_dir / "nodes.yml").exists()
                    # Check if it has appliance-vars.yml (appliance config)
                    has_appliance = (example_dir / "appliance-vars.yml").exists()

                    if has_cluster or has_nodes or has_appliance:
                        examples.append(example_dir.name)
    except (PermissionError, OSError):
        # Handle CI environments where /root is not accessible
        pass

    return examples if examples else ["sno-disconnected"]


# Get examples at DAG parse time
AVAILABLE_EXAMPLES = discover_examples()

# Registry configurations
REGISTRY_CONFIGS = {
    "mirror-registry": {
        "server": "mirror-registry.example.com:8443",
        "description": "Quay-based mirror-registry on 192.168.122.x",
    },
    "harbor": {
        "server": "harbor.example.com",
        "description": "Harbor registry",
    },
    "jfrog": {
        "server": "jfrog.example.com",
        "description": "JFrog Artifactory",
    },
    "upstream": {
        "server": "",
        "description": "Pull directly from upstream (requires internet)",
    },
}

# Deployment size configurations
DEPLOYMENT_SIZES = {
    "sno": {
        "description": "Single Node OpenShift",
        "master_count": 1,
        "worker_count": 0,
    },
    "3-node": {
        "description": "Compact 3-node cluster (masters only)",
        "master_count": 3,
        "worker_count": 0,
    },
    "full": {
        "description": "Full cluster with workers",
        "master_count": 3,
        "worker_count": 2,
    },
}

default_args = {
    "owner": "ocp4-disconnected-helper",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "ocp_agent_deployment",
    default_args=default_args,
    description="OpenShift Agent-Based Deployment with dropdown parameters",
    schedule=None,
    catchup=False,
    tags=[
        "ocp4-disconnected-helper",
        "openshift",
        "agent-install",
        "disconnected",
        "sno",
        "3-node",
    ],
    params={
        "registry_type": Param(
            default="mirror-registry",
            type="string",
            enum=["mirror-registry", "harbor", "jfrog", "upstream"],
            description="Registry type for pulling images",
        ),
        "deployment_size": Param(
            default="sno",
            type="string",
            enum=["sno", "3-node", "full"],
            description="Cluster deployment size",
        ),
        "example_config": Param(
            default="sno-disconnected",
            type="string",
            enum=AVAILABLE_EXAMPLES,
            description="Example configuration to use",
        ),
        "ocp_version": Param(
            default="4.19",
            type="string",
            enum=["4.17", "4.18", "4.19", "4.20"],
            description="OpenShift version",
        ),
        "deploy_on_kvm": Param(
            default=False,
            type="boolean",
            description="Deploy to local KVM for testing",
        ),
        "wait_for_install": Param(
            default=True,
            type="boolean",
            description="Wait for installation to complete",
        ),
    },
    doc_md=f"""
    # OpenShift Agent-Based Deployment DAG

    Deploy OpenShift clusters using the Agent-Based Installer with flexible configuration.

    ## Dropdown Parameters

    | Parameter | Options | Description |
    |-----------|---------|-------------|
    | `registry_type` | mirror-registry, harbor, jfrog, upstream | Registry for pulling images |
    | `deployment_size` | sno, 3-node, full | Cluster size |
    | `example_config` | {', '.join(AVAILABLE_EXAMPLES[:5])}... | Configuration template |
    | `ocp_version` | 4.17, 4.18, 4.19, 4.20 | OpenShift version |
    | `deploy_on_kvm` | true/false | Deploy to local KVM |

    ## Available Example Configurations

    **Discovered {len(AVAILABLE_EXAMPLES)} examples:**

    {chr(10).join([f'- `{ex}`' for ex in AVAILABLE_EXAMPLES])}

    ## Registry Types

    - **mirror-registry**: Quay-based registry at mirror-registry.example.com:8443
    - **harbor**: Harbor registry
    - **jfrog**: JFrog Artifactory
    - **upstream**: Direct pull from quay.io/registry.redhat.io (requires internet)

    ## Workflow

    ```
    validate_config --> setup_registry_trust --> create_agent_iso
        --> deploy_on_kvm (optional) --> wait_bootstrap
        --> wait_install --> post_install_validation

    cleanup_temp (runs on any failure)
    ```

    ## Prerequisites

    1. Mirror registry deployed and synced (for disconnected)
    2. DNS entries configured in FreeIPA
    3. Pull secret available at ~/pull-secret.json

    ## Usage

    ```bash
    # Via CLI
    airflow dags trigger ocp_agent_deployment \\
      --conf '{{"registry_type": "mirror-registry", "deployment_size": "sno", "example_config": "sno-disconnected"}}'

    # Via Airflow UI - use the dropdown parameters
    ```
    """,
)

# =============================================================================
# Task: Validate Configuration
# =============================================================================
validate_config = BashOperator(
    task_id="validate_config",
    bash_command="""
    set -euo pipefail

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Validating Agent Deployment Configuration         ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    EXAMPLE_CONFIG="{{ params.example_config }}"
    REGISTRY_TYPE="{{ params.registry_type }}"
    DEPLOYMENT_SIZE="{{ params.deployment_size }}"
    OCP_VERSION="{{ params.ocp_version }}"

    EXAMPLES_DIR="""
    + EXAMPLES_DIR
    + """
    CONFIG_PATH="$EXAMPLES_DIR/$EXAMPLE_CONFIG"

    echo "Configuration:"
    echo "  Example Config: $EXAMPLE_CONFIG"
    echo "  Registry Type: $REGISTRY_TYPE"
    echo "  Deployment Size: $DEPLOYMENT_SIZE"
    echo "  OCP Version: $OCP_VERSION"
    echo ""

    # Validate example exists
    if [ ! -d "$CONFIG_PATH" ]; then
        echo "❌ Example configuration not found: $CONFIG_PATH"
        echo "Available examples:"
        ls -1 "$EXAMPLES_DIR/"
        exit 1
    fi
    echo "✅ Example configuration found: $CONFIG_PATH"

    # Check for required files
    if [ -f "$CONFIG_PATH/cluster.yml" ]; then
        echo "✅ cluster.yml found"
    else
        echo "❌ cluster.yml not found in $CONFIG_PATH"
        exit 1
    fi

    if [ -f "$CONFIG_PATH/nodes.yml" ]; then
        echo "✅ nodes.yml found"
    else
        echo "❌ nodes.yml not found in $CONFIG_PATH"
        exit 1
    fi

    # Check for openshift-install
    if ! command -v openshift-install &> /dev/null; then
        echo "❌ openshift-install not found in PATH"
        exit 1
    fi
    echo "✅ openshift-install: $(openshift-install version 2>/dev/null | head -1)"

    # Check for pull secret
    PULL_SECRET_PATH="${HOME}/pull-secret.json"
    if [ ! -f "$PULL_SECRET_PATH" ]; then
        echo "❌ Pull secret not found at $PULL_SECRET_PATH"
        exit 1
    fi
    echo "✅ Pull secret found"

    echo ""
    echo "✅ Configuration validation complete"
    """,
    dag=dag,
)

# =============================================================================
# Task: Setup Registry Trust
# =============================================================================
setup_registry_trust = BashOperator(
    task_id="setup_registry_trust",
    bash_command="""
    set -euo pipefail

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Setting Up Registry Trust                         ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    REGISTRY_TYPE="{{ params.registry_type }}"
    EXAMPLE_CONFIG="{{ params.example_config }}"

    AGENT_INSTALL_DIR="""
    + AGENT_INSTALL_DIR
    + """
    CONFIG_PATH="$AGENT_INSTALL_DIR/examples/$EXAMPLE_CONFIG"

    echo "Registry Type: $REGISTRY_TYPE"

    if [ "$REGISTRY_TYPE" == "upstream" ]; then
        echo "Using upstream registries - no additional trust setup needed"
        exit 0
    fi

    # Run the setup-disconnected-registry.sh script if it exists
    if [ -f "$AGENT_INSTALL_DIR/hack/setup-disconnected-registry.sh" ]; then
        echo "Running setup-disconnected-registry.sh..."
        cd "$AGENT_INSTALL_DIR/hack"

        case "$REGISTRY_TYPE" in
            mirror-registry)
                export REGISTRY_HOST="mirror-registry.example.com"
                export REGISTRY_PORT="8443"
                ;;
            harbor)
                export REGISTRY_HOST="harbor.example.com"
                export REGISTRY_PORT="443"
                ;;
            jfrog)
                export REGISTRY_HOST="jfrog.example.com"
                export REGISTRY_PORT="443"
                ;;
        esac

        ./setup-disconnected-registry.sh "$EXAMPLE_CONFIG" || true
    else
        echo "setup-disconnected-registry.sh not found, checking manual configuration..."

        # Check if cluster.yml has additional_trust_bundle
        if grep -q "additional_trust_bundle:" "$CONFIG_PATH/cluster.yml"; then
            echo "✅ Trust bundle already configured in cluster.yml"
        else
            echo "⚠️  No trust bundle configured - may need manual setup"
        fi
    fi

    echo ""
    echo "✅ Registry trust setup complete"
    """,
    dag=dag,
)

# =============================================================================
# Task: Create Agent ISO
# =============================================================================
create_agent_iso = BashOperator(
    task_id="create_agent_iso",
    bash_command="""
    set -euo pipefail

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Creating Agent ISO                                ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    EXAMPLE_CONFIG="{{ params.example_config }}"
    OCP_VERSION="{{ params.ocp_version }}"

    AGENT_INSTALL_DIR="""
    + AGENT_INSTALL_DIR
    + """
    GENERATED_ASSETS="""
    + GENERATED_ASSETS_BASE
    + """/$EXAMPLE_CONFIG

    echo "Example Config: $EXAMPLE_CONFIG"
    echo "OCP Version: $OCP_VERSION"
    echo "Output Directory: $GENERATED_ASSETS"
    echo ""

    # Clean up previous assets
    rm -rf "$GENERATED_ASSETS"
    mkdir -p "$GENERATED_ASSETS"

    cd "$AGENT_INSTALL_DIR"

    # Run the create-iso.sh script
    if [ -f "hack/create-iso.sh" ]; then
        echo "Running create-iso.sh..."
        cd hack
        ./create-iso.sh "$EXAMPLE_CONFIG"
    else
        # Fallback to direct ansible-playbook
        echo "Running ansible playbook directly..."
        ansible-playbook playbooks/create-iso.yml \
            -e cluster_config_path="examples/$EXAMPLE_CONFIG" \
            -e generated_asset_path="$GENERATED_ASSETS"
    fi

    # Verify ISO was created
    if [ -f "$GENERATED_ASSETS/agent.x86_64.iso" ]; then
        SIZE=$(du -h "$GENERATED_ASSETS/agent.x86_64.iso" | cut -f1)
        echo ""
        echo "✅ Agent ISO created: $GENERATED_ASSETS/agent.x86_64.iso ($SIZE)"
    else
        echo "❌ Agent ISO not found at expected location"
        echo "Checking for ISO files..."
        find "$GENERATED_ASSETS" -name "*.iso" -ls
        exit 1
    fi
    """,
    dag=dag,
)


# =============================================================================
# Task: Deploy on KVM (Optional)
# =============================================================================
def should_deploy_kvm(**context):
    """Branch based on deploy_on_kvm parameter."""
    deploy_kvm = context["params"].get("deploy_on_kvm", False)
    if deploy_kvm:
        return "deploy_on_kvm"
    else:
        return "skip_kvm_deploy"


decide_kvm_deploy = BranchPythonOperator(
    task_id="decide_kvm_deploy",
    python_callable=should_deploy_kvm,
    dag=dag,
)

deploy_on_kvm = BashOperator(
    task_id="deploy_on_kvm",
    bash_command="""
    set -euo pipefail

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Deploying to KVM                                  ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    EXAMPLE_CONFIG="{{ params.example_config }}"

    AGENT_INSTALL_DIR="""
    + AGENT_INSTALL_DIR
    + """
    GENERATED_ASSETS="""
    + GENERATED_ASSETS_BASE
    + """/$EXAMPLE_CONFIG

    cd "$AGENT_INSTALL_DIR/hack"

    # Export environment variables
    export CLUSTER_CONFIG="examples/$EXAMPLE_CONFIG"
    export GENERATED_ASSET_PATH="$GENERATED_ASSETS"

    # Run the KVM deployment script
    if [ -f "deploy-on-kvm.sh" ]; then
        ./deploy-on-kvm.sh
    else
        echo "❌ deploy-on-kvm.sh not found"
        exit 1
    fi

    echo ""
    echo "✅ KVM deployment initiated"
    echo "   Monitor with: watch 'virsh list --all'"
    """,
    dag=dag,
)

skip_kvm_deploy = BashOperator(
    task_id="skip_kvm_deploy",
    bash_command="""
    echo "Skipping KVM deployment (deploy_on_kvm=false)"
    echo "Agent ISO is ready for manual deployment"
    """,
    dag=dag,
)

# =============================================================================
# Task: Wait for Bootstrap
# =============================================================================
wait_bootstrap = BashOperator(
    task_id="wait_bootstrap",
    bash_command="""
    set -euo pipefail

    EXAMPLE_CONFIG="{{ params.example_config }}"
    WAIT_FOR_INSTALL="{{ params.wait_for_install }}"

    GENERATED_ASSETS="""
    + GENERATED_ASSETS_BASE
    + """/$EXAMPLE_CONFIG

    if [ "$WAIT_FOR_INSTALL" != "True" ] && [ "$WAIT_FOR_INSTALL" != "true" ]; then
        echo "Skipping bootstrap wait (wait_for_install=false)"
        exit 0
    fi

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Waiting for Bootstrap Complete                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    cd "$GENERATED_ASSETS"

    # Wait for bootstrap with timeout
    timeout 3600 openshift-install agent wait-for bootstrap-complete \
        --dir "$GENERATED_ASSETS" \
        --log-level info || {
        echo "⚠️  Bootstrap wait timed out or failed"
        echo "Check logs in $GENERATED_ASSETS/.openshift_install.log"
        exit 1
    }

    echo ""
    echo "✅ Bootstrap complete"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)

# =============================================================================
# Task: Wait for Install Complete
# =============================================================================
wait_install = BashOperator(
    task_id="wait_install",
    bash_command="""
    set -euo pipefail

    EXAMPLE_CONFIG="{{ params.example_config }}"
    WAIT_FOR_INSTALL="{{ params.wait_for_install }}"

    GENERATED_ASSETS="""
    + GENERATED_ASSETS_BASE
    + """/$EXAMPLE_CONFIG

    if [ "$WAIT_FOR_INSTALL" != "True" ] && [ "$WAIT_FOR_INSTALL" != "true" ]; then
        echo "Skipping install wait (wait_for_install=false)"
        exit 0
    fi

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Waiting for Install Complete                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    cd "$GENERATED_ASSETS"

    # Wait for install with timeout (2 hours for full install)
    timeout 7200 openshift-install agent wait-for install-complete \
        --dir "$GENERATED_ASSETS" \
        --log-level info || {
        echo "⚠️  Install wait timed out or failed"
        echo "Check logs in $GENERATED_ASSETS/.openshift_install.log"
        exit 1
    }

    echo ""
    echo "✅ Installation complete"

    # Show kubeconfig location
    if [ -f "$GENERATED_ASSETS/auth/kubeconfig" ]; then
        echo ""
        echo "Kubeconfig: export KUBECONFIG=$GENERATED_ASSETS/auth/kubeconfig"
    fi
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)

# =============================================================================
# Task: Post-Install Validation
# =============================================================================
post_install_validation = BashOperator(
    task_id="post_install_validation",
    bash_command="""
    set -euo pipefail

    EXAMPLE_CONFIG="{{ params.example_config }}"
    WAIT_FOR_INSTALL="{{ params.wait_for_install }}"

    GENERATED_ASSETS="""
    + GENERATED_ASSETS_BASE
    + """/$EXAMPLE_CONFIG

    if [ "$WAIT_FOR_INSTALL" != "True" ] && [ "$WAIT_FOR_INSTALL" != "true" ]; then
        echo "Skipping post-install validation (wait_for_install=false)"
        exit 0
    fi

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Post-Install Validation                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    export KUBECONFIG="$GENERATED_ASSETS/auth/kubeconfig"

    if [ ! -f "$KUBECONFIG" ]; then
        echo "⚠️  Kubeconfig not found - skipping validation"
        exit 0
    fi

    echo "Checking cluster nodes..."
    oc get nodes -o wide || echo "Failed to get nodes"

    echo ""
    echo "Checking cluster operators..."
    oc get co || echo "Failed to get cluster operators"

    echo ""
    echo "Checking cluster version..."
    oc get clusterversion || echo "Failed to get cluster version"

    echo ""
    echo "✅ Post-install validation complete"
    """,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)

# =============================================================================
# Task: Cleanup Temp (runs on any outcome)
# =============================================================================
cleanup_temp = BashOperator(
    task_id="cleanup_temp",
    bash_command="""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Cleanup Temporary Files                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    EXAMPLE_CONFIG="{{ params.example_config }}"
    GENERATED_ASSETS="""
    + GENERATED_ASSETS_BASE
    + """/$EXAMPLE_CONFIG

    # Clean up oc-mirror workspace if it exists
    if [ -d "/tmp/oc-mirror-workspace" ]; then
        echo "Cleaning up /tmp/oc-mirror-workspace..."
        rm -rf /tmp/oc-mirror-workspace
    fi

    # Clean up any orphaned ISO build directories
    find /tmp -maxdepth 1 -name "agent-*" -type d -mmin +60 -exec rm -rf {} \\; 2>/dev/null || true

    echo "✅ Cleanup complete"
    """,
    trigger_rule="all_done",  # Run regardless of upstream task status
    dag=dag,
)

# =============================================================================
# Task: Cleanup VM on Failure (CI/CD style - auto cleanup for retry)
# =============================================================================
from airflow.utils.trigger_rule import TriggerRule

cleanup_vm_on_failure = BashOperator(
    task_id="cleanup_vm_on_failure",
    bash_command="""
    set +e  # Don't exit on error during cleanup

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          Cleanup VM After Failure                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    EXAMPLE_CONFIG="{{ params.example_config }}"

    # Extract cluster name from config
    CONFIG_PATH="/root/openshift-agent-install/examples/$EXAMPLE_CONFIG"
    if [ -f "$CONFIG_PATH/cluster.yml" ]; then
        CLUSTER_NAME=$(grep "^cluster_name:" "$CONFIG_PATH/cluster.yml" 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "$EXAMPLE_CONFIG")
    else
        CLUSTER_NAME="$EXAMPLE_CONFIG"
    fi

    echo "Cleaning up VMs for cluster: $CLUSTER_NAME"
    echo ""

    # Find and destroy VMs matching the cluster name
    for VM in $(virsh list --all --name 2>/dev/null | grep -E "^${CLUSTER_NAME}" || true); do
        echo "Destroying VM: $VM"
        virsh destroy "$VM" 2>/dev/null || true
        virsh undefine "$VM" --remove-all-storage 2>/dev/null || true
    done

    # Also try kcli cleanup
    if command -v kcli &> /dev/null; then
        for VM in $(kcli list vm 2>/dev/null | grep "$CLUSTER_NAME" | awk '{print $2}' || true); do
            echo "Deleting via kcli: $VM"
            kcli delete vm "$VM" -y 2>/dev/null || true
        done
    fi

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          DEPLOYMENT FAILED                                 ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "VMs have been cleaned up automatically."
    echo ""
    echo "Review the failed task logs above for specific errors."
    echo "Each error includes:"
    echo "  - The specific file or config with the issue"
    echo "  - Commands to fix the issue"
    echo ""
    echo "After fixing, retrigger this DAG - no manual cleanup needed."
    echo ""
    echo "Common fixes:"
    echo "  - Config error: Edit the file mentioned in the error"
    echo "  - Registry issue: airflow dags trigger mirror_registry_deployment"
    echo "  - DNS missing: airflow dags trigger freeipa_dns_management"
    echo "  - Certificate expired: airflow dags trigger step_ca_operations"
    """,
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag,
)

# =============================================================================
# Task Dependencies
# =============================================================================
validate_config >> setup_registry_trust >> create_agent_iso >> decide_kvm_deploy

# KVM deployment branch
decide_kvm_deploy >> [deploy_on_kvm, skip_kvm_deploy]

# Both paths lead to bootstrap wait
deploy_on_kvm >> wait_bootstrap
skip_kvm_deploy >> wait_bootstrap

# Installation monitoring
wait_bootstrap >> wait_install >> post_install_validation

# Cleanup runs after everything
post_install_validation >> cleanup_temp

# Cleanup VM on failure - runs if any deployment task fails
[
    validate_config,
    setup_registry_trust,
    create_agent_iso,
    deploy_on_kvm,
    wait_bootstrap,
    wait_install,
] >> cleanup_vm_on_failure
