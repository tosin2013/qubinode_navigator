# Available Tools in Airflow Containers

## 🎯 Overview

The Qubinode Airflow containers have **BOTH kcli AND virsh** available for VM management.

## 📦 Installed Packages

### System Packages (via apt)

```bash
libvirt-clients     # Provides: virsh, virt-admin, virt-host-validate
libvirt-dev         # Development libraries for libvirt
```

### Python Packages (via pip)

```bash
kcli==99.0          # KVM Cloud Instances CLI
libvirt-python      # Python bindings for libvirt API
paramiko            # SSH library
```

## 🔧 Available Commands

### kcli Commands

```bash
kcli list vm                          # List all VMs
kcli list image                       # List available images
kcli list plan                        # List deployment plans
kcli list network                     # List networks
kcli create vm <name> --image <img>  # Create VM
kcli delete vm <name>                 # Delete VM
kcli start vm <name>                  # Start VM
kcli stop vm <name>                   # Stop VM
kcli info vm <name>                   # Get VM info
kcli info host                        # Get hypervisor info
kcli ssh <vm>                         # SSH into VM
```

### virsh Commands

```bash
# VM Management
virsh list --all                      # List all VMs
virsh start <vm>                      # Start VM
virsh shutdown <vm>                   # Graceful shutdown
virsh destroy <vm>                    # Force stop
virsh reboot <vm>                     # Reboot VM
virsh dominfo <vm>                    # Get VM details
virsh domstate <vm>                   # Get VM state
virsh dumpxml <vm>                    # Get VM XML config

# Network Management
virsh net-list --all                  # List networks
virsh net-info <network>              # Network details
virsh net-start <network>             # Start network
virsh net-destroy <network>           # Stop network
virsh net-dumpxml <network>           # Network XML config

# Storage Management
virsh pool-list --all                 # List storage pools
virsh pool-info <pool>                # Pool details
virsh pool-refresh <pool>             # Refresh pool
virsh vol-list <pool>                 # List volumes in pool

# Hypervisor Info
virsh nodeinfo                        # Host hardware info
virsh nodecpustats                    # CPU statistics
virsh nodememstats                    # Memory statistics
virsh version                         # Libvirt version
virsh capabilities                    # Host capabilities

# Snapshots
virsh snapshot-list <vm>              # List snapshots
virsh snapshot-create <vm>            # Create snapshot
virsh snapshot-revert <vm> <snapshot> # Revert to snapshot
virsh snapshot-delete <vm> <snapshot> # Delete snapshot
```

## 🔌 Connection Details

Both tools connect to the same libvirt daemon:

```bash
Connection URI: qemu:///system
Socket: /var/run/libvirt/libvirt-sock (mounted from host)
User: root (for socket access permissions)
```

## 🎨 When to Use Each Tool

### Use kcli for:

✅ Quick VM provisioning from images/templates
✅ Profile-based deployments
✅ Simplified workflows
✅ Multi-VM deployments (plans)
✅ Integration with cloud images

### Use virsh for:

✅ Detailed VM inspection and debugging
✅ Network and storage pool management
✅ XML configuration editing
✅ Snapshot management
✅ Low-level libvirt operations
✅ Performance tuning

## 💡 Examples in Airflow DAGs

### Example 1: Using kcli

```python
from qubinode.operators import KcliVMCreateOperator

create_vm = KcliVMCreateOperator(
    task_id='create_vm',
    vm_name='test-vm',
    image='centos-stream-10',
    memory=2048,
    cpus=2
)
```

### Example 2: Using virsh

```python
from qubinode.virsh_operators import VirshVMInfoOperator

get_info = VirshVMInfoOperator(
    task_id='get_vm_info',
    vm_name='test-vm'
)
```

### Example 3: Generic virsh command

```python
from qubinode.virsh_operators import VirshCommandOperator

list_snapshots = VirshCommandOperator(
    task_id='list_snapshots',
    command=['snapshot-list', 'test-vm']
)
```

## 🧪 Testing in Container

You can test the tools directly in a running container:

```bash
# Enter the scheduler container
podman exec -it airflow_airflow-scheduler_1 bash

# Test kcli
kcli version
kcli list vm
kcli info host

# Test virsh
virsh version
virsh list --all
virsh nodeinfo
```

## 📚 Available Operators

### kcli Operators

- `KcliVMCreateOperator` - Create VM
- `KcliVMDeleteOperator` - Delete VM
- `KcliVMListOperator` - List VMs

### virsh Operators

- `VirshCommandOperator` - Run any virsh command
- `VirshVMStartOperator` - Start VM
- `VirshVMStopOperator` - Stop VM
- `VirshVMInfoOperator` - Get VM info
- `VirshNetworkListOperator` - List networks

## 🔐 Permissions

The containers run as root and have access to the libvirt socket because:

1. Libvirt socket is owned by `root:libvirt` with `0770` permissions
1. Containers run as user `0:0` (root:root)
1. Container is added to group `107` (libvirt group)
1. Socket is mounted: `/var/run/libvirt/libvirt-sock:/var/run/libvirt/libvirt-sock`

## 📖 See Also

- **Example DAGs**:
  - `/opt/airflow/dags/example_kcli_vm_provisioning.py`
  - `/opt/airflow/dags/example_kcli_virsh_combined.py`
- **Plugin Code**: `/opt/airflow/plugins/qubinode/`
- **Architecture**: `/root/qubinode_navigator/airflow/ARCHITECTURE.md`
