# Reference Scripts for Testing kcli Commands

## 📋 Overview

**ALWAYS test kcli commands with these scripts BEFORE adding them to DAGs!**

These scripts help you:

- ✅ Verify kcli syntax is correct
- ✅ Confirm commands work on your system
- ✅ See actual output before DAGifying
- ✅ Debug issues faster
- ✅ Understand the command flow

## 🎯 Best Practice Workflow

```
1. Test command with script  →  2. Verify it works  →  3. Add to DAG
   (./scripts/test-*.sh)         (check output)         (operators.py)
```

## 📁 Available Scripts

| Script                      | Purpose             | When to Use                         |
| --------------------------- | ------------------- | ----------------------------------- |
| `test-kcli-create-vm.sh`    | Test VM creation    | Before using `KcliVMCreateOperator` |
| `test-kcli-delete-vm.sh`    | Test VM deletion    | Before using `KcliVMDeleteOperator` |
| `test-kcli-list-vms.sh`     | Test VM listing     | Before using `KcliVMListOperator`   |
| `test-complete-workflow.sh` | Test full lifecycle | Before creating new DAGs            |

## 🚀 Quick Start

### 1. Make Scripts Executable

```bash
cd /opt/qubinode_navigator/airflow/scripts
chmod +x *.sh
```

### 2. Test VM Creation

```bash
# Basic test with defaults
./test-kcli-create-vm.sh

# Custom configuration
./test-kcli-create-vm.sh my-test-vm centos10stream 4096 4 20
```

### 3. List VMs

```bash
./test-kcli-list-vms.sh
```

### 4. Delete Test VM

```bash
./test-kcli-delete-vm.sh my-test-vm
```

### 5. Run Complete Workflow

```bash
./test-complete-workflow.sh
```

## 📖 Detailed Usage

### Test VM Creation

**Script:** `test-kcli-create-vm.sh`

**Usage:**

```bash
./test-kcli-create-vm.sh [vm_name] [image] [memory_mb] [cpus] [disk_gb]
```

**Examples:**

```bash
# Default (auto-generated name, centos10stream, 2GB RAM, 2 CPUs, 10GB disk)
./test-kcli-create-vm.sh

# Custom name only
./test-kcli-create-vm.sh my-custom-vm

# Full custom configuration
./test-kcli-create-vm.sh webserver ubuntu2404 4096 4 50
```

**What it does:**

1. ✅ Checks if image exists
1. ✅ Shows the exact kcli command
1. ✅ Asks for confirmation
1. ✅ Creates the VM
1. ✅ Verifies creation succeeded
1. ✅ Shows how to use in DAG

**Output:**

```
✅ VM creation command completed
📊 VM Details:
Id:             1
Name:           test-vm-20251119-140530
UUID:           ...
OS Type:        hvm
State:          running
CPU(s):         2
Max memory:     2097152 KiB
Used memory:    2097152 KiB
```

### Test VM Deletion

**Script:** `test-kcli-delete-vm.sh`

**Usage:**

```bash
./test-kcli-delete-vm.sh <vm_name>
```

**Examples:**

```bash
# Delete specific VM
./test-kcli-delete-vm.sh my-test-vm

# List VMs first, then delete
./test-kcli-list-vms.sh
./test-kcli-delete-vm.sh test-vm-20251119-140530
```

**What it does:**

1. ✅ Checks if VM exists
1. ✅ Shows current VM state
1. ✅ Asks for confirmation
1. ✅ Stops VM if running
1. ✅ Deletes VM
1. ✅ Verifies deletion

### Test VM Listing

**Script:** `test-kcli-list-vms.sh`

**Usage:**

```bash
./test-kcli-list-vms.sh
```

**What it does:**

1. ✅ Lists VMs using virsh
1. ✅ Lists VMs using kcli (if available)
1. ✅ Lists VMs from Airflow container
1. ✅ Shows count summary

**Output:**

```
📋 Method 1: virsh -c qemu:///system list --all
 Id   Name                 State
--------------------------------------
 1    test-vm-123          running

📋 Method 2: kcli list vms
+-------------+--------+----------------+
| Name        | Status | Ip             |
+-------------+--------+----------------+
| test-vm-123 | up     | 192.168.122.50 |
+-------------+--------+----------------+

Summary
Total VMs:    1
Running VMs:  1
```

### Test Complete Workflow

**Script:** `test-complete-workflow.sh`

**Usage:**

```bash
./test-complete-workflow.sh
```

**What it does:**
Mirrors the `example_kcli_vm_provisioning` DAG:

1. ✅ Lists VMs (before)
1. ✅ Creates test VM
1. ✅ Waits for VM to be running
1. ✅ Validates VM
1. ✅ Lists VMs (after)
1. ✅ Keeps VM running (configurable)
1. ✅ Deletes VM (optional)

**Interactive options:**

- 30 seconds wait (quick test)
- 5 minutes wait (like DAG)
- Keep running (manual cleanup)
- Delete immediately

## 🔧 Troubleshooting Scripts

### Debug Image Issues

```bash
# List available images
virsh -c qemu:///system vol-list default

# Check specific image
virsh -c qemu:///system vol-info centos10stream --pool default
```

### Debug libvirt Connection

```bash
# Test connection
virsh -c qemu:///system uri

# Check if libvirtd is running
systemctl status libvirtd

# List networks
virsh -c qemu:///system net-list --all
```

### Debug kcli Configuration

```bash
# Check kcli config
cat ~/.kcli/config.yml

# List kcli hosts
kcli list host

# Get kcli version
kcli version
```

## 📝 Script-to-DAG Translation

### Example: VM Creation

**After testing with script:**

```bash
./test-kcli-create-vm.sh test-vm centos10stream 2048 2 10
```

**Successful output:**

```
✅ VM creation command completed
Command: kcli create vm test-vm -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]
```

**Add to DAG:**

```python
from qubinode.operators import KcliVMCreateOperator

create_vm = KcliVMCreateOperator(
    task_id='create_test_vm',
    vm_name='test-vm',
    image='centos10stream',  # ✅ Verified image name
    memory=2048,              # ✅ Tested memory size
    cpus=2,                   # ✅ Tested CPU count
    disk_size='10G',          # ✅ Tested disk size
    dag=dag
)
```

### Example: Complete Workflow

**Test full workflow:**

```bash
./test-complete-workflow.sh
# Select option 2 (5 minutes wait)
```

**If all steps succeed, create DAG:**

```python
# All these operators have been tested!
list_before = KcliVMListOperator(task_id='list_before', dag=dag)
create_vm = KcliVMCreateOperator(..., dag=dag)
wait_vm = KcliVMStatusSensor(..., dag=dag)
validate = BashOperator(..., dag=dag)
list_after = KcliVMListOperator(task_id='list_after', dag=dag)
keep_running = BashOperator(bash_command='sleep 300', dag=dag)
delete_vm = KcliVMDeleteOperator(..., dag=dag)

# Define workflow
list_before >> create_vm >> wait_vm >> validate >> list_after >> keep_running >> delete_vm
```

## 🎓 Learning Path

### 1. Start Simple

```bash
# Just list VMs
./test-kcli-list-vms.sh
```

### 2. Create and Delete

```bash
# Create a test VM
./test-kcli-create-vm.sh

# Delete it
./test-kcli-delete-vm.sh test-vm-<timestamp>
```

### 3. Try Custom Configs

```bash
# Different sizes
./test-kcli-create-vm.sh small-vm centos10stream 1024 1 10
./test-kcli-create-vm.sh big-vm ubuntu2404 8192 4 100
```

### 4. Full Workflow

```bash
# Run the complete test
./test-complete-workflow.sh
```

### 5. Create Your DAG

```bash
# Now you're ready!
# Copy example_kcli_vm_provisioning.py and customize
```

## 💡 Pro Tips

### Tip 1: Test Before Every DAG Change

```bash
# Before modifying DAG
./test-kcli-create-vm.sh my-vm centos10stream 4096 2 20

# If successful, update DAG
# If failed, debug with script output
```

### Tip 2: Keep Test VMs for Reference

```bash
# Create a reference VM
./test-kcli-create-vm.sh reference-vm centos10stream 2048 2 10

# When workflow runs, choose "Keep running"
# Check it anytime with: kcli list vms
```

### Tip 3: Use Scripts for Debugging

```bash
# DAG failed? Test the exact command
./test-kcli-create-vm.sh <same_name> <same_image> <same_memory> <same_cpus> <same_disk>

# See the actual error message
# Fix the issue
# Test again until it works
# Update DAG with working values
```

### Tip 4: Create Custom Scripts

Copy and modify these scripts for your specific needs:

```bash
# Copy template
cp test-kcli-create-vm.sh test-my-custom-workflow.sh

# Edit for your use case
vim test-my-custom-workflow.sh

# Test it
./test-my-custom-workflow.sh

# DAGify it once working
```

## 🔗 Related Documentation

- **kcli Syntax**: `../BUGFIX-KCLI-SYNTAX.md`
- **DAG Examples**: `../dags/example_kcli_vm_provisioning.py`
- **Operators**: `../plugins/qubinode/operators.py`
- **VM Testing**: `../VM-TESTING-GUIDE.md`
- **Tools Reference**: `../TOOLS-AVAILABLE.md`

## 📊 Success Criteria

You know the scripts are working when:

- ✅ `test-kcli-list-vms.sh` shows your VMs
- ✅ `test-kcli-create-vm.sh` creates a VM successfully
- ✅ Created VM appears in `virsh list --all`
- ✅ `test-kcli-delete-vm.sh` removes the VM
- ✅ `test-complete-workflow.sh` runs without errors
- ✅ DAGs work after testing commands

## 🚦 Quick Reference Card

```bash
# BEFORE adding to DAG, ALWAYS test:

# 1. Test your command
./scripts/test-kcli-create-vm.sh myvm centos10stream 2048 2 10

# 2. Verify it worked
./scripts/test-kcli-list-vms.sh

# 3. Clean up
./scripts/test-kcli-delete-vm.sh myvm

# 4. If successful, add to DAG
# Edit dags/my_dag.py with working values

# 5. Test DAG in Airflow UI
# http://localhost:8888
```

______________________________________________________________________

**Remember:** Scripts are faster to debug than DAGs! Test first, DAGify later. 🚀
