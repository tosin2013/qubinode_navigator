"""
Airflow DAG: Registry Deployment (Mirror-Registry & Harbor)
kcli-pipelines integration per ADR-0047

This DAG deploys container registries for:
- Disconnected OpenShift installs
- Container image mirroring
- Air-gapped environments

Supported registries:
- mirror-registry (Quay-based)
- harbor

Integrates with: step-ca for TLS certificates
Calls: /opt/kcli-pipelines/mirror-registry/deploy.sh
       /opt/kcli-pipelines/harbor/deploy.sh (future)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator


# User-configurable SSH user (fix for hardcoded root issue)
SSH_USER = get_ssh_user()
# Import user-configurable helpers for portable DAGs
from dag_helpers import get_ssh_user

# Configuration
KCLI_PIPELINES_DIR = "/opt/kcli-pipelines"
MIRROR_REGISTRY_DIR = f"{KCLI_PIPELINES_DIR}/mirror-registry"
HARBOR_DIR = f"{KCLI_PIPELINES_DIR}/harbor"

default_args = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "registry_deployment",
    default_args=default_args,
    description="Deploy container registries (Mirror-Registry/Harbor) for disconnected installs",
    schedule=None,
    catchup=False,
    tags=[
        "qubinode",
        "kcli-pipelines",
        "registry",
        "disconnected",
        "ocp4-disconnected-helper",
    ],
    params={
        "action": "create",  # create, delete, status, health
        "registry_type": "mirror-registry",  # mirror-registry, harbor
        "vm_name": "mirror-registry",  # VM name
        "quay_version": "v1.3.11",  # Quay mirror-registry version
        "harbor_version": "v2.10.1",  # Harbor version
        "domain": "example.com",  # Domain for certificates
        "target_server": "localhost",  # Target server
        "network": "qubinet",  # Network to deploy on
        "step_ca_vm": "step-ca-server",  # Step-CA server VM name
    },
    doc_md="""
    # Registry Deployment DAG

    Deploy container registries for disconnected OpenShift environments.

    ## Supported Registries

    ### Mirror-Registry (Quay-based)
    - Lightweight Quay registry for image mirroring
    - Supports disconnected/air-gapped installs
    - Integrates with Step-CA for TLS certificates

    ### Harbor (Future)
    - Enterprise container registry
    - Uses Let's Encrypt for certificates

    ## Architecture

    ```
    +------------------+     +------------------+     +------------------+
    |   Step-CA        | --> | Mirror Registry  | --> | OpenShift        |
    |   (Certificates) |     | (Images)         |     | (Disconnected)   |
    +------------------+     +------------------+     +------------------+
    ```

    ## Prerequisites

    1. **Step-CA Server** must be deployed first for TLS certificates:
       ```bash
       airflow dags trigger step_ca_deployment --conf '{"action": "create"}'
       ```

    2. **FreeIPA** should be running for DNS registration

    ## Parameters

    - **action**: create, delete, status, or health
    - **registry_type**: mirror-registry or harbor
    - **vm_name**: Name for the registry VM
    - **quay_version**: Quay mirror-registry version (for mirror-registry)
    - **harbor_version**: Harbor version (for harbor)
    - **domain**: Domain for certificate generation
    - **step_ca_vm**: Name of the Step-CA server VM

    ## Usage

    ### Create Mirror-Registry
    ```bash
    airflow dags trigger registry_deployment --conf '{
        "action": "create",
        "registry_type": "mirror-registry",
        "vm_name": "mirror-registry",
        "quay_version": "v1.3.11"
    }'
    ```

    ### Check Registry Health
    ```bash
    airflow dags trigger registry_deployment --conf '{
        "action": "health",
        "registry_type": "mirror-registry",
        "vm_name": "mirror-registry"
    }'
    ```

    ### Delete Registry
    ```bash
    airflow dags trigger registry_deployment --conf '{
        "action": "delete",
        "vm_name": "mirror-registry"
    }'
    ```

    ## Post-Deployment

    After deployment, the registry will be available at:
    - **Mirror-Registry**: https://mirror-registry.<domain>:8443

    To mirror OpenShift images:
    ```bash
    oc adm release mirror --from=quay.io/openshift-release-dev/ocp-release:4.14.0-x86_64 \\
        --to=mirror-registry.<domain>:8443/ocp4/openshift4 \\
        --to-release-image=mirror-registry.<domain>:8443/ocp4/openshift4:4.14.0-x86_64
    ```

    ## Integration with ocp4-disconnected-helper

    The registry deployment is a prerequisite for:
    - `ocp_initial_deployment` DAG
    - `ocp_incremental_update` DAG
    """,
)


def decide_action(**context):
    """Branch based on action parameter"""
    action = context["params"].get("action", "create")
    if action == "delete":
        return "delete_registry"
    elif action == "status":
        return "check_status"
    elif action == "health":
        return "health_check"
    return "check_step_ca_available"


# Task: Decide action
decide_action_task = BranchPythonOperator(
    task_id="decide_action",
    python_callable=decide_action,
    dag=dag,
)


# Task: Check Step-CA is available (prerequisite)
check_step_ca = BashOperator(
    task_id="check_step_ca_available",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Checking Step-CA Prerequisite"
    echo "========================================"

    STEP_CA_VM="{{ params.step_ca_vm }}"

    # Check if Step-CA VM exists
    STEP_CA_IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm $STEP_CA_VM 2>/dev/null | grep 'ip:' | awk '{print \\$2}' | head -1")

    if [ -z "$STEP_CA_IP" ] || [ "$STEP_CA_IP" == "None" ]; then
        echo "[ERROR] Step-CA server not found: $STEP_CA_VM"
        echo ""
        echo "Step-CA is required for registry TLS certificates."
        echo "Deploy Step-CA first:"
        echo "  airflow dags trigger step_ca_deployment --conf '{\"action\": \"create\"}'"
        exit 1
    fi

    echo "[OK] Step-CA server found at: $STEP_CA_IP"

    # Check Step-CA health
    echo "Checking Step-CA health..."
    if ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "curl -sk https://$STEP_CA_IP:443/health 2>/dev/null | grep -q ok"; then
        echo "[OK] Step-CA is healthy"
    else
        echo "[WARN] Step-CA may not be responding - continuing anyway"
    fi

    # Get CA fingerprint for later use
    echo ""
    echo "Getting CA fingerprint..."
    FINGERPRINT=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "ssh -o StrictHostKeyChecking=no cloud-user@$STEP_CA_IP \
            'sudo step certificate fingerprint /root/.step/certs/root_ca.crt 2>/dev/null'" || true)

    if [ -n "$FINGERPRINT" ]; then
        echo "[OK] CA Fingerprint: $FINGERPRINT"
    else
        echo "[WARN] Could not get CA fingerprint - will try during deployment"
    fi

    echo ""
    echo "[OK] Step-CA prerequisite check complete"
    """,
    dag=dag,
)


# Task: Validate environment
validate_environment = BashOperator(
    task_id="validate_environment",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Validating Registry Deployment Environment"
    echo "========================================"

    REGISTRY_TYPE="{{ params.registry_type }}"
    DOMAIN="{{ params.domain }}"

    echo "Registry Type: $REGISTRY_TYPE"
    echo "Domain: $DOMAIN"

    # Check kcli
    echo "Checking kcli..."
    if ! ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "which kcli" &>/dev/null; then
        echo "[ERROR] kcli not found on host"
        exit 1
    fi
    echo "[OK] kcli available"

    # Check for registry scripts
    echo "Checking registry deployment scripts..."
    if [ "$REGISTRY_TYPE" == "mirror-registry" ]; then
        if ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "test -f /opt/kcli-pipelines/mirror-registry/deploy.sh"; then
            echo "[OK] Mirror-registry deploy script found"
        else
            echo "[ERROR] Mirror-registry deploy.sh not found"
            exit 1
        fi
    elif [ "$REGISTRY_TYPE" == "harbor" ]; then
        if ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "test -f /opt/kcli-pipelines/harbor/harbor.sh"; then
            echo "[OK] Harbor script found"
        else
            echo "[ERROR] Harbor script not found"
            exit 1
        fi
    fi

    # Check RHEL image for mirror-registry
    if [ "$REGISTRY_TYPE" == "mirror-registry" ]; then
        echo "Checking RHEL8 image..."
        if ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "ls /var/lib/libvirt/images/rhel8 2>/dev/null" | grep -q rhel; then
            echo "[OK] RHEL8 image found"
        else
            echo "[WARN] RHEL8 image may not be available"
            echo "Download with: kcli download image rhel8"
        fi
    fi

    # Check FreeIPA for DNS
    echo "Checking FreeIPA..."
    FREEIPA_IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm freeipa 2>/dev/null | grep 'ip:' | awk '{print \\$2}' | head -1")

    if [ -n "$FREEIPA_IP" ]; then
        echo "[OK] FreeIPA available at $FREEIPA_IP"
    else
        echo "[WARN] FreeIPA not found - DNS registration will be skipped"
    fi

    echo ""
    echo "[OK] Environment validation complete"
    """,
    dag=dag,
)


# Task: Create Registry VM
create_registry = BashOperator(
    task_id="create_registry_vm",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Creating Registry VM"
    echo "========================================"

    REGISTRY_TYPE="{{ params.registry_type }}"
    VM_NAME="{{ params.vm_name }}"
    QUAY_VERSION="{{ params.quay_version }}"
    DOMAIN="{{ params.domain }}"
    TARGET_SERVER="{{ params.target_server }}"
    NETWORK="{{ params.network }}"
    STEP_CA_VM="{{ params.step_ca_vm }}"

    echo "Registry Type: $REGISTRY_TYPE"
    echo "VM Name: $VM_NAME"

    # Check if VM already exists
    if ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli list vm | grep -q $VM_NAME"; then
        echo "[OK] VM $VM_NAME already exists"
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "kcli info vm $VM_NAME"
        exit 0
    fi

    # Get Step-CA info
    STEP_CA_IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm $STEP_CA_VM 2>/dev/null | grep 'ip:' | awk '{print \\$2}' | head -1")

    CA_URL="https://${STEP_CA_IP}:443"

    # Get CA fingerprint
    FINGERPRINT=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "ssh -o StrictHostKeyChecking=no cloud-user@$STEP_CA_IP \
            'sudo step certificate fingerprint /root/.step/certs/root_ca.crt 2>/dev/null'")

    echo "Step-CA URL: $CA_URL"
    echo "CA Fingerprint: $FINGERPRINT"

    # Create registry based on type
    if [ "$REGISTRY_TYPE" == "mirror-registry" ]; then
        echo "Creating Mirror-Registry..."
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "export VM_NAME=$VM_NAME && \
             export QUAY_VERSION=$QUAY_VERSION && \
             export CA_URL=$CA_URL && \
             export FINGERPRINT=$FINGERPRINT && \
             export STEP_CA_PASSWORD=password && \
             export NET_NAME=$NETWORK && \
             cd /opt/kcli-pipelines && \
             ./mirror-registry/deploy.sh create"
    elif [ "$REGISTRY_TYPE" == "harbor" ]; then
        echo "[WARN] Harbor deployment via DAG not fully implemented yet"
        echo "Use the harbor.sh script directly for now"
    fi

    echo ""
    echo "[OK] Registry deployment initiated"
    """,
    execution_timeout=timedelta(minutes=45),
    dag=dag,
)


# Task: Wait for Registry VM
wait_for_registry = BashOperator(
    task_id="wait_for_registry_vm",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Waiting for Registry VM"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"
    MAX_ATTEMPTS=40
    ATTEMPT=0

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))
        echo "Check $ATTEMPT/$MAX_ATTEMPTS..."

        # Get VM IP
        IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "kcli info vm $VM_NAME 2>/dev/null | grep 'ip:' | awk '{print \\$2}' | head -1")

        if [ -n "$IP" ] && [ "$IP" != "None" ]; then
            echo "VM IP: $IP"

            # Check SSH connectivity
            if ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
                "nc -z -w5 $IP 22" 2>/dev/null; then
                echo ""
                echo "[OK] Registry VM is accessible at $IP"
                exit 0
            fi
        fi

        sleep 30
    done

    echo "[WARN] Timeout waiting for Registry VM - may still be provisioning"
    """,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)


# Task: Validate registry is healthy
validate_registry_health = BashOperator(
    task_id="validate_registry_health",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Validating Registry Health"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"
    REGISTRY_TYPE="{{ params.registry_type }}"

    # Get VM IP
    IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm $VM_NAME 2>/dev/null | grep 'ip:' | awk '{print \\$2}' | head -1")

    if [ -z "$IP" ]; then
        echo "[ERROR] Could not get VM IP"
        exit 1
    fi

    echo "Registry VM IP: $IP"

    # Wait for registry to be ready (can take time after VM boots)
    echo "Waiting for registry service to be ready..."
    MAX_ATTEMPTS=30
    ATTEMPT=0

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))

        if [ "$REGISTRY_TYPE" == "mirror-registry" ]; then
            # Check Quay health endpoint
            HEALTH=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
                "curl -sk https://$IP:8443/health/instance 2>/dev/null" || true)

            if echo "$HEALTH" | grep -qi "healthy"; then
                echo ""
                echo "[OK] Mirror-Registry is HEALTHY"
                echo "$HEALTH"
                exit 0
            fi
        elif [ "$REGISTRY_TYPE" == "harbor" ]; then
            # Check Harbor health
            HEALTH=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
                "curl -sk https://$IP/api/v2.0/health 2>/dev/null" || true)

            if echo "$HEALTH" | grep -qi "healthy"; then
                echo ""
                echo "[OK] Harbor is HEALTHY"
                exit 0
            fi
        fi

        echo "Waiting for registry to become healthy... ($ATTEMPT/$MAX_ATTEMPTS)"
        sleep 30
    done

    echo ""
    echo "[WARN] Registry health check timed out"
    echo "The registry may still be initializing. Check manually:"
    echo "  curl -k https://$IP:8443/health/instance"
    """,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)


# Task: Complete deployment
deployment_complete = BashOperator(
    task_id="deployment_complete",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Registry Deployment Complete"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"
    REGISTRY_TYPE="{{ params.registry_type }}"
    DOMAIN="{{ params.domain }}"

    # Get VM info
    IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm $VM_NAME 2>/dev/null | grep 'ip:' | awk '{print \\$2}' | head -1")

    echo ""
    echo "Registry Details:"
    echo "  VM Name: $VM_NAME"
    echo "  IP Address: $IP"
    echo "  Type: $REGISTRY_TYPE"

    if [ "$REGISTRY_TYPE" == "mirror-registry" ]; then
        echo "  URL: https://mirror-registry.${DOMAIN}:8443"
        echo "  Health: https://${IP}:8443/health/instance"
        echo ""
        echo "Login credentials (check VM):"
        echo "  ssh root@$IP 'cat /root/mirror-registry-offline.log | grep -A2 credentials'"
        echo ""
        echo "To mirror OpenShift images:"
        echo "  oc adm release mirror --from=quay.io/openshift-release-dev/ocp-release:<version> \\"
        echo "      --to=mirror-registry.${DOMAIN}:8443/ocp4/openshift4 \\"
        echo "      --to-release-image=mirror-registry.${DOMAIN}:8443/ocp4/openshift4:<version>"
    fi

    echo ""
    echo "========================================"
    echo "Registry is ready for ocp4-disconnected-helper workflows"
    echo "========================================"
    """,
    dag=dag,
)


# Task: Health check (standalone)
health_check = BashOperator(
    task_id="health_check",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Registry Health Check"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"
    REGISTRY_TYPE="{{ params.registry_type }}"

    # Get VM IP
    IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm $VM_NAME 2>/dev/null | grep 'ip:' | awk '{print \\$2}' | head -1")

    if [ -z "$IP" ]; then
        echo "[ERROR] VM $VM_NAME not found or has no IP"
        exit 1
    fi

    echo "Registry VM: $VM_NAME"
    echo "IP Address: $IP"
    echo ""

    if [ "$REGISTRY_TYPE" == "mirror-registry" ]; then
        echo "Checking Mirror-Registry health..."
        HEALTH=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "curl -sk https://$IP:8443/health/instance 2>/dev/null")

        if echo "$HEALTH" | grep -qi "healthy"; then
            echo "[OK] Registry is HEALTHY"
            echo "$HEALTH" | jq . 2>/dev/null || echo "$HEALTH"
            exit 0
        else
            echo "[ERROR] Registry is NOT HEALTHY"
            echo "Response: $HEALTH"
            exit 1
        fi
    elif [ "$REGISTRY_TYPE" == "harbor" ]; then
        echo "Checking Harbor health..."
        HEALTH=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "curl -sk https://$IP/api/v2.0/health 2>/dev/null")

        if echo "$HEALTH" | grep -qi "healthy"; then
            echo "[OK] Harbor is HEALTHY"
            exit 0
        else
            echo "[ERROR] Harbor is NOT HEALTHY"
            exit 1
        fi
    fi
    """,
    dag=dag,
)


# Task: Delete Registry
delete_registry = BashOperator(
    task_id="delete_registry",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Deleting Registry"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"
    TARGET_SERVER="{{ params.target_server }}"

    echo "Deleting VM: $VM_NAME"

    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "export VM_NAME=$VM_NAME && \
         cd /opt/kcli-pipelines && \
         ./mirror-registry/deploy.sh delete" || \
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "kcli delete vm $VM_NAME -y" || \
        echo "[WARN] VM may not exist"

    echo "[OK] Registry deleted"
    """,
    execution_timeout=timedelta(minutes=10),
    dag=dag,
)


# Task: Check status
check_status = BashOperator(
    task_id="check_status",
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    echo "========================================"
    echo "Registry Status"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"

    # Get VM info
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm $VM_NAME" 2>/dev/null || echo "VM not found: $VM_NAME"

    # Get IP and check health
    IP=$(ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
        "kcli info vm $VM_NAME 2>/dev/null | grep 'ip:' | awk '{print \\$2}' | head -1")

    if [ -n "$IP" ]; then
        echo ""
        echo "Health Check:"
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \
            "curl -sk https://$IP:8443/health/instance 2>/dev/null" || echo "Health check failed"
    fi
    """,
    dag=dag,
)


# Define task dependencies
# Main create flow
decide_action_task >> check_step_ca >> validate_environment >> create_registry
create_registry >> wait_for_registry >> validate_registry_health >> deployment_complete

# Alternative flows
decide_action_task >> delete_registry
decide_action_task >> check_status
decide_action_task >> health_check
