# kcli Quick Reference Card

## 🎯 Test Before DAGifying!

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  GOLDEN RULE: Test commands with scripts FIRST!   ┃
┃  ./scripts/test-*.sh → verify → add to DAG        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## 📝 Testing Scripts

```bash
cd /opt/qubinode_navigator/airflow/scripts

# Test VM creation
./test-kcli-create-vm.sh [vm_name] [image] [memory] [cpus] [disk]

# Test VM deletion
./test-kcli-delete-vm.sh <vm_name>

# Test VM listing
./test-kcli-list-vms.sh

# Test complete workflow
./test-complete-workflow.sh
```

## 🔧 kcli Command Syntax (Correct!)

```bash
# ✅ CORRECT kcli syntax
kcli create vm <name> -i <image> -P memory=<MB> -P numcpus=<N> -P disks=[<GB>]

# ❌ WRONG (don't use these flags)
kcli create vm <name> --image <image> --memory <MB> --cpus <N>
```

## 📋 Available Images

```bash
# List images
virsh -c qemu:///system vol-list default

# Current available:
centos10stream, centos9stream, centos8stream
fedora41, rockylinux9
ubuntu2404, ubuntu2204
```

## 🚀 Quick Examples

### Create VM

```bash
# Test first
./scripts/test-kcli-create-vm.sh webserver centos10stream 2048 2 20

# If successful, in DAG:
KcliVMCreateOperator(
    task_id='create_webserver',
    vm_name='webserver',
    image='centos10stream',
    memory=2048,
    cpus=2,
    disk_size='20G'
)
```

### List VMs

```bash
# Test first
./scripts/test-kcli-list-vms.sh

# If successful, in DAG:
KcliVMListOperator(task_id='list_vms')
```

### Delete VM

```bash
# Test first
./scripts/test-kcli-delete-vm.sh webserver

# If successful, in DAG:
KcliVMDeleteOperator(
    task_id='delete_webserver',
    vm_name='webserver',
    force=True
)
```

## 🔍 Debugging Commands

```bash
# Check VMs
virsh -c qemu:///system list --all

# VM details
virsh -c qemu:///system dominfo <vm_name>

# Check from container
podman exec airflow_airflow-scheduler_1 virsh list --all

# Check images
virsh -c qemu:///system vol-list default

# Check networks
virsh -c qemu:///system net-list --all
```

## 🎬 Workflow: Script → DAG

```
1. Test Command
   $ ./scripts/test-kcli-create-vm.sh myvm centos10stream 2048 2 10
   ✅ Success!

2. Note the Command
   Command: kcli create vm myvm -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]

3. Add to DAG
   create = KcliVMCreateOperator(
       vm_name='myvm',
       image='centos10stream',
       memory=2048,
       cpus=2,
       disk_size='10G'
   )

4. Test in Airflow
   http://localhost:8888 → Trigger DAG → Monitor
```

## 📊 Operator Reference

| Operator               | Script to Test             | Parameters                              |
| ---------------------- | -------------------------- | --------------------------------------- |
| `KcliVMCreateOperator` | `test-kcli-create-vm.sh`   | vm_name, image, memory, cpus, disk_size |
| `KcliVMDeleteOperator` | `test-kcli-delete-vm.sh`   | vm_name, force                          |
| `KcliVMListOperator`   | `test-kcli-list-vms.sh`    | (none)                                  |
| `VirshCommandOperator` | test manually with `virsh` | command (list)                          |
| `VirshVMInfoOperator`  | test with `virsh dominfo`  | vm_name                                 |

## 🎯 Common Patterns

### Pattern 1: Simple VM

```bash
# Test
./scripts/test-kcli-create-vm.sh simple centos10stream 1024 1 10

# DAG
KcliVMCreateOperator(vm_name='simple', image='centos10stream', memory=1024, cpus=1, disk_size='10G')
```

### Pattern 2: High-Performance VM

```bash
# Test
./scripts/test-kcli-create-vm.sh powerful ubuntu2404 8192 4 100

# DAG
KcliVMCreateOperator(vm_name='powerful', image='ubuntu2404', memory=8192, cpus=4, disk_size='100G')
```

### Pattern 3: Multiple VMs (test each)

```bash
# Test VM 1
./scripts/test-kcli-create-vm.sh web1 centos10stream 2048 2 20

# Test VM 2
./scripts/test-kcli-create-vm.sh web2 centos10stream 2048 2 20

# DAG (parallel)
web1 = KcliVMCreateOperator(task_id='web1', vm_name='web1', ...)
web2 = KcliVMCreateOperator(task_id='web2', vm_name='web2', ...)
# No dependencies = parallel execution
```

## ⚠️ Common Mistakes

```bash
# ❌ WRONG: Using non-existent image
image='centos-stream-10'  # doesn't exist!

# ✅ CORRECT: Use available image
image='centos10stream'  # exists in libvirt

# ❌ WRONG: Not testing first
# Just add to DAG → fail → debug in Airflow

# ✅ CORRECT: Test first
./scripts/test-kcli-create-vm.sh → works → add to DAG

# ❌ WRONG: Hardcoding dates
vm_name='test-20251119'  # will break tomorrow

# ✅ CORRECT: Use templates or timestamps
vm_name='test-{{ ds_nodash }}'  # Airflow template
vm_name=f'test-{datetime.now().strftime("%Y%m%d")}'  # Python
```

## 🏃 Quick Start (Copy & Paste)

```bash
# 1. Make scripts executable (one-time)
cd /opt/qubinode_navigator/airflow/scripts
chmod +x *.sh

# 2. Test VM creation
./test-kcli-create-vm.sh

# 3. Check if it worked
./test-kcli-list-vms.sh

# 4. Clean up
VM_NAME=$(virsh -c qemu:///system list --name | head -1)
./test-kcli-delete-vm.sh $VM_NAME

# 5. Ready to create DAGs!
```

## 📍 File Locations

```
/opt/qubinode_navigator/airflow/
├── scripts/                      ← Testing scripts
│   ├── test-kcli-create-vm.sh
│   ├── test-kcli-delete-vm.sh
│   ├── test-kcli-list-vms.sh
│   ├── test-complete-workflow.sh
│   └── README.md                 ← Detailed docs
├── dags/                         ← Your DAGs
│   └── example_*.py              ← Examples
├── plugins/qubinode/             ← Operators
│   ├── operators.py
│   └── hooks.py
└── QUICK-REFERENCE.md            ← This file
```

## 🆘 Getting Help

```bash
# Script help
./scripts/test-kcli-create-vm.sh --help

# Detailed docs
cat scripts/README.md

# Check logs
podman logs airflow_airflow-scheduler_1 --tail 100

# AI Assistant
http://localhost:8888/ai-assistant
Ask: "How do I create a VM with kcli?"
```

## 🎓 Learning Resources

1. **Start Here**: `scripts/README.md`
1. **Examples**: `dags/example_kcli_vm_provisioning.py`
1. **Commands**: `TOOLS-AVAILABLE.md`
1. **Bugs Fixed**: `BUGFIX-KCLI-SYNTAX.md`
1. **Testing VMs**: `VM-TESTING-GUIDE.md`
1. **Logging**: `LOGGING-GUIDE.md`

______________________________________________________________________

**Print this card and keep it handy!** 📋
