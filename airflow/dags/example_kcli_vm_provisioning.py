"""
Example Airflow DAG: kcli VM Provisioning
Phase 6 Goal 2: Workflow Orchestration Integration

This DAG demonstrates:
- Creating a VM using kcli
- Waiting for VM to be ready
- Running validation
- Cleaning up resources
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from qubinode.operators import (
    KcliVMCreateOperator,
    KcliVMDeleteOperator,
    KcliVMListOperator,
)
from qubinode.sensors import KcliVMStatusSensor

# Default arguments for all tasks
default_args = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 11, 19),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    "example_kcli_vm_provisioning",
    default_args=default_args,
    description="Example DAG for VM provisioning using kcli",
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=["qubinode", "kcli", "vm-provisioning", "example"],
)

# Task 1: List existing VMs
list_vms_before = KcliVMListOperator(
    task_id="list_vms_before",
    dag=dag,
)

# Task 2: Create a new VM
create_vm = KcliVMCreateOperator(
    task_id="create_test_vm",
    vm_name=f'test-centos-{datetime.now().strftime("%Y%m%d")}',
    image="centos10stream",  # Use existing image (was: centos-stream-10)
    memory=2048,
    cpus=2,
    disk_size="10G",
    ai_assistance=True,  # Enable AI guidance for VM creation
    dag=dag,
)

# Task 3: Wait for VM to be running
wait_for_vm = KcliVMStatusSensor(
    task_id="wait_for_vm_running",
    vm_name=f'test-centos-{datetime.now().strftime("%Y%m%d")}',
    expected_status="running",
    timeout=300,  # 5 minutes
    poke_interval=30,  # Check every 30 seconds
    dag=dag,
)

# Task 4: Validate VM (using bash command as example)
validate_vm = BashOperator(
    task_id="validate_vm",
    bash_command='echo "VM validation successful: test-centos-{{ ds_nodash }}"',
    dag=dag,
)

# Task 5: List VMs again
list_vms_after = KcliVMListOperator(
    task_id="list_vms_after",
    dag=dag,
)

# Task 6: Keep VM running for 5 minutes so you can check it
keep_vm_running = BashOperator(
    task_id="keep_vm_running_5min",
    bash_command='echo "VM is running. Check it with: kcli list vms" && echo "Waiting 5 minutes before cleanup..." && sleep 300',
    dag=dag,
)

# Task 7: Clean up - Delete the VM
delete_vm = KcliVMDeleteOperator(
    task_id="delete_test_vm",
    vm_name="test-centos-{{ ds_nodash }}",
    force=True,
    dag=dag,
)

# Define task dependencies
(list_vms_before >> create_vm >> wait_for_vm >> validate_vm >> list_vms_after >> keep_vm_running >> delete_vm)

# Task documentation
dag.doc_md = """
# Example kcli VM Provisioning DAG

This DAG demonstrates the Qubinode Navigator Airflow integration with kcli for VM provisioning.

## Workflow Steps

1. **List VMs Before**: Lists all existing VMs
2. **Create Test VM**: Creates a new CentOS Stream 10 VM with 2GB RAM, 2 CPUs, 10GB disk
3. **Wait for VM**: Waits for the VM to reach 'running' status (max 5 minutes)
4. **Validate VM**: Performs basic validation (placeholder)
5. **List VMs After**: Lists all VMs including the new one
6. **Keep VM Running**: Waits 5 minutes so you can check the VM with `kcli list vms`
7. **Delete Test VM**: Cleans up by deleting the test VM

**Note**: The VM stays running for 5 minutes during step 6. Use this time to verify it:
```bash
# From host
kcli list vms

# From Airflow container
podman exec airflow_airflow-scheduler_1 kcli list vms

# Using virsh
virsh -c qemu:///system list --all
```

## AI Assistant Integration

The `create_vm` task has `ai_assistance=True`, which means it will:
- Query the AI Assistant for guidance on VM creation
- Log the AI recommendations
- Proceed with VM creation

## Usage

This DAG is triggered manually. To run it:

1. Navigate to Airflow UI (http://localhost:8080)
2. Find "example_kcli_vm_provisioning" in the DAG list
3. Click the play button to trigger the DAG
4. Monitor the execution in the Graph or Tree view

## Customization

You can customize this DAG by:
- Changing VM specifications (memory, cpus, disk_size)
- Adding more validation steps
- Integrating with OpenShift/Kubernetes deployment
- Adding notification tasks (Slack, email)

## Related

- **ADR-0036**: Apache Airflow Workflow Orchestration Integration
- **ADR-0037**: Git-Based DAG Repository Management
- **Phase 6 Goal 2**: Workflow Orchestration Integration
"""
