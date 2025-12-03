"""
Airflow DAG Template: [Your DAG Name]
=====================================================
Template for creating Qubinode infrastructure DAGs.
Copy this file and customize for your use case.

ADR Compliance:
- ADR-0045: DAG Development Standards
- ADR-0046: SSH Execution Pattern for Host Commands
- ADR-0047: kcli-pipelines Integration

Author: [Your Name]
Created: [Date]
"""

from datetime import datetime, timedelta

from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator

from airflow import DAG

# =============================================================================
# DAG Configuration
# =============================================================================
# ADR-0045: DAG ID must match filename (snake_case)
# If this file is "my_service_deployment.py", DAG ID must be "my_service_deployment"

DAG_ID = "dag_template"  # CHANGE THIS to match your filename

default_args = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# =============================================================================
# DAG Parameters
# =============================================================================
# Define parameters that users can override when triggering the DAG

dag_params = {
    # Common action parameter for create/delete/status workflows
    "action": "create",  # Options: create, delete, status
    # VM Configuration
    "vm_name": "",  # Leave empty for auto-generated names
    "vm_profile": "default",
    "target_server": "localhost",
    # Network Configuration
    "domain": "example.com",
    "dns_server": "",
    # Add your custom parameters here
    # "custom_param": "default_value",
}

# =============================================================================
# DAG Definition
# =============================================================================

dag = DAG(
    DAG_ID,
    default_args=default_args,
    description="Template DAG for Qubinode infrastructure deployment",
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=["qubinode", "template"],
    params=dag_params,
    doc_md="""
    # DAG Template

    This is a template for creating Qubinode infrastructure DAGs.

    ## Usage

    ```bash
    # Create resources
    airflow dags trigger dag_template --conf '{"action": "create"}'

    # Check status
    airflow dags trigger dag_template --conf '{"action": "status"}'

    # Delete resources
    airflow dags trigger dag_template --conf '{"action": "delete"}'
    ```

    ## Parameters

    | Parameter | Description | Default |
    |-----------|-------------|---------|
    | action | Operation to perform | create |
    | vm_name | Name of the VM | auto-generated |
    | vm_profile | kcli profile to use | default |
    | target_server | Target host | localhost |
    | domain | DNS domain | example.com |

    ## Prerequisites

    - kcli-pipelines cloned to /opt/kcli-pipelines
    - SSH access configured to target host
    - Required kcli profiles configured
    """,
)


# =============================================================================
# Helper Functions
# =============================================================================


def decide_action(**context) -> str:
    """
    Branch based on action parameter.

    ADR-0045: Use BranchPythonOperator for action-based workflows.
    """
    action = context["params"].get("action", "create")
    valid_actions = ["create", "delete", "status"]

    if action in valid_actions:
        return f"{action}_resources"
    return "create_resources"


def log_completion(**context) -> None:
    """Log completion status."""
    action = context["params"].get("action", "create")
    print(f"[OK] Action '{action}' completed successfully")


# =============================================================================
# Tasks
# =============================================================================

# Task: Decide which action to perform
decide_action_task = BranchPythonOperator(
    task_id="decide_action",
    python_callable=decide_action,
    dag=dag,
)

# Task: Validate prerequisites
# ADR-0046: Use SSH for host commands
validate_prerequisites = BashOperator(
    task_id="validate_prerequisites",
    bash_command="""
    echo "========================================"
    echo "Validating Prerequisites"
    echo "========================================"

    # ADR-0046: All host commands must go through SSH
    # This ensures consistent execution whether running in container or directly

    # Check SSH connectivity
    echo "[INFO] Checking SSH connectivity..."
    if ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@localhost "echo 'SSH OK'" 2>/dev/null; then
        echo "[ERROR] Cannot SSH to localhost"
        exit 1
    fi
    echo "[OK] SSH connectivity verified"

    # Check kcli-pipelines
    echo "[INFO] Checking kcli-pipelines..."
    if ssh -o StrictHostKeyChecking=no root@localhost "test -d /opt/kcli-pipelines"; then
        echo "[OK] kcli-pipelines found"
    else
        echo "[ERROR] kcli-pipelines not found at /opt/kcli-pipelines"
        exit 1
    fi

    # Check kcli availability
    echo "[INFO] Checking kcli..."
    if ssh -o StrictHostKeyChecking=no root@localhost "which kcli" 2>/dev/null; then
        echo "[OK] kcli is available"
    else
        echo "[ERROR] kcli not found"
        exit 1
    fi

    echo ""
    echo "[OK] All prerequisites validated"
    """,
    dag=dag,
)

# Task: Create resources
# ADR-0046: Wrap kcli/virsh commands in SSH
create_resources = BashOperator(
    task_id="create_resources",
    bash_command="""
    echo "========================================"
    echo "Creating Resources"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"
    VM_PROFILE="{{ params.vm_profile }}"
    TARGET_SERVER="{{ params.target_server }}"

    # Generate VM name if not provided
    if [ -z "$VM_NAME" ]; then
        VM_NAME="${VM_PROFILE}-$(date +%s | md5sum | head -c 5)"
        echo "[INFO] Generated VM name: $VM_NAME"
    fi

    # ADR-0046: Execute kcli via SSH
    echo "[INFO] Creating VM via kcli..."
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "kcli create vm -p ${VM_PROFILE} ${VM_NAME}" || {
        echo "[ERROR] Failed to create VM"
        exit 1
    }

    # Wait for VM to get IP
    echo "[INFO] Waiting for VM to get IP address..."
    for i in {1..30}; do
        VM_IP=$(ssh -o StrictHostKeyChecking=no root@localhost \
            "kcli info vm ${VM_NAME} 2>/dev/null | grep '^ip:' | awk '{print \\$2}' | head -1")
        if [ -n "$VM_IP" ]; then
            echo "[OK] VM IP: $VM_IP"
            break
        fi
        echo "  Waiting... ($i/30)"
        sleep 10
    done

    if [ -z "$VM_IP" ]; then
        echo "[WARN] VM created but no IP assigned yet"
    fi

    echo ""
    echo "[OK] Resource creation complete"
    echo "VM Name: $VM_NAME"
    echo "VM IP: ${VM_IP:-pending}"
    """,
    dag=dag,
)

# Task: Delete resources
delete_resources = BashOperator(
    task_id="delete_resources",
    bash_command="""
    echo "========================================"
    echo "Deleting Resources"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"
    VM_PROFILE="{{ params.vm_profile }}"

    # Find VM by profile if name not provided
    if [ -z "$VM_NAME" ]; then
        echo "[INFO] Looking for VMs matching profile: $VM_PROFILE"
        VM_NAME=$(ssh -o StrictHostKeyChecking=no root@localhost \
            "kcli list vm 2>/dev/null | grep ${VM_PROFILE} | tail -1 | awk '{print \\$2}'" 2>/dev/null)
    fi

    if [ -z "$VM_NAME" ]; then
        echo "[WARN] No VM found to delete"
        exit 0
    fi

    # ADR-0046: Execute kcli via SSH
    echo "[INFO] Deleting VM: $VM_NAME"
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "kcli delete vm ${VM_NAME} -y" || {
        echo "[ERROR] Failed to delete VM"
        exit 1
    }

    echo ""
    echo "[OK] VM $VM_NAME deleted successfully"
    """,
    dag=dag,
)

# Task: Check status
status_resources = BashOperator(
    task_id="status_resources",
    bash_command="""
    echo "========================================"
    echo "Resource Status"
    echo "========================================"

    VM_NAME="{{ params.vm_name }}"
    VM_PROFILE="{{ params.vm_profile }}"

    # List VMs matching profile
    echo "[INFO] VMs matching profile '$VM_PROFILE':"
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "kcli list vm 2>/dev/null | grep -E 'Name|${VM_PROFILE}'" || echo "No VMs found"

    # If specific VM name provided, show details
    if [ -n "$VM_NAME" ]; then
        echo ""
        echo "[INFO] Details for VM: $VM_NAME"
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
            "kcli info vm ${VM_NAME} 2>/dev/null" || echo "VM not found"
    fi

    echo ""
    echo "[OK] Status check complete"
    """,
    dag=dag,
)

# Task: Completion logging
completion_task = PythonOperator(
    task_id="log_completion",
    python_callable=log_completion,
    trigger_rule="none_failed_min_one_success",  # Run if any branch succeeds
    dag=dag,
)

# =============================================================================
# Task Dependencies
# =============================================================================
# ADR-0045: Define clear task dependencies

validate_prerequisites >> decide_action_task

decide_action_task >> create_resources >> completion_task
decide_action_task >> delete_resources >> completion_task
decide_action_task >> status_resources >> completion_task
