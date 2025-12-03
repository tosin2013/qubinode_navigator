"""
Example DAG: Combined kcli and virsh Operations
Demonstrates using both kcli and virsh operators together

This DAG shows:
- Using kcli for high-level VM provisioning
- Using virsh for low-level libvirt management
- Combining both tools in a single workflow
"""

from datetime import datetime, timedelta

from airflow.operators.bash import BashOperator
from qubinode.operators import KcliVMCreateOperator, KcliVMListOperator
from qubinode.virsh_operators import (
    VirshCommandOperator,
    VirshNetworkListOperator,
    VirshVMInfoOperator,
    VirshVMStartOperator,
)

from airflow import DAG

default_args = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 11, 19),
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "example_kcli_virsh_combined",
    default_args=default_args,
    description="Demonstrates using both kcli and virsh operators",
    schedule_interval=None,
    catchup=False,
    tags=["qubinode", "kcli", "virsh", "example"],
)

# Task 1: List libvirt networks using virsh
list_networks = VirshNetworkListOperator(
    task_id="list_libvirt_networks",
    show_inactive=True,
    dag=dag,
)

# Task 2: List existing VMs using kcli
list_vms_kcli = KcliVMListOperator(
    task_id="list_vms_kcli",
    dag=dag,
)

# Task 3: List VMs using virsh
list_vms_virsh = VirshCommandOperator(
    task_id="list_vms_virsh",
    command=["list", "--all"],
    dag=dag,
)

# Task 4: Get hypervisor info using virsh
get_hypervisor_info = VirshCommandOperator(
    task_id="get_hypervisor_info",
    command=["nodeinfo"],
    dag=dag,
)

# Task 5: Get libvirt version
get_libvirt_version = VirshCommandOperator(
    task_id="get_libvirt_version",
    command=["version"],
    dag=dag,
)

# Task 6: List storage pools
list_storage_pools = VirshCommandOperator(
    task_id="list_storage_pools",
    command=["pool-list", "--all"],
    dag=dag,
)

# Task 7: Get pool info for default pool
get_pool_info = VirshCommandOperator(
    task_id="get_default_pool_info",
    command=["pool-info", "default"],
    dag=dag,
)

# Task 8: Summary report
summary_report = BashOperator(
    task_id="generate_summary",
    bash_command="""
    echo "================================================"
    echo "Qubinode Infrastructure Summary"
    echo "================================================"
    echo "Timestamp: $(date)"
    echo ""
    echo "✅ kcli and virsh operators are working!"
    echo ""
    echo "You can now use both:"
    echo "  • kcli for high-level VM provisioning"
    echo "  • virsh for low-level libvirt management"
    echo ""
    echo "================================================"
    """,
    dag=dag,
)

# Define task dependencies
# First: Get system info in parallel
[
    list_networks,
    list_vms_kcli,
    list_vms_virsh,
    get_hypervisor_info,
    get_libvirt_version,
] >> list_storage_pools

# Then: Get detailed pool info
list_storage_pools >> get_pool_info

# Finally: Generate summary
get_pool_info >> summary_report

# Documentation
dag.doc_md = """
# Combined kcli and virsh Operations

This DAG demonstrates using both kcli and virsh operators in the same workflow.

## Tools Available

### kcli (High-Level)
- **Purpose**: Simplified VM provisioning and management
- **Best For**: Quick VM creation, profile-based deployments
- **Example**: `kcli create vm myvm -i centos10stream`

### virsh (Low-Level)
- **Purpose**: Direct libvirt management
- **Best For**: Fine-grained control, debugging, advanced operations
- **Example**: `virsh dominfo myvm`

## When to Use Each

**Use kcli when:**
- Creating VMs from templates/images
- Managing VM profiles
- Quick provisioning
- Simplified workflows

**Use virsh when:**
- Need detailed VM information
- Managing networks and storage pools
- Debugging issues
- Advanced libvirt operations
- Fine-grained resource control

## Available Commands in Containers

Both tools connect to the same libvirt daemon (`qemu:///system`) via the mounted socket:
`/var/run/libvirt/libvirt-sock`

**kcli commands:**
```bash
kcli list vm
kcli create vm
kcli delete vm
kcli info vm
```

**virsh commands:**
```bash
virsh list --all
virsh dominfo <vm>
virsh start <vm>
virsh shutdown <vm>
virsh destroy <vm>
virsh net-list
virsh pool-list
virsh nodeinfo
```

## Example: Combining Both

```python
# Use kcli to create VM
create = KcliVMCreateOperator(
    task_id='create_vm',
    vm_name='myvm',
    image='centos10stream'  # Use existing image
)

# Use virsh to get detailed info
get_info = VirshVMInfoOperator(
    task_id='get_vm_details',
    vm_name='myvm'
)

# Use virsh to start if stopped
start = VirshVMStartOperator(
    task_id='ensure_running',
    vm_name='myvm'
)

create >> get_info >> start
```

## Related

- **Operators**: `/opt/airflow/plugins/qubinode/operators.py` (kcli)
- **Operators**: `/opt/airflow/plugins/qubinode/virsh_operators.py` (virsh)
- **Hooks**: `/opt/airflow/plugins/qubinode/hooks.py`
"""
