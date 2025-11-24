# VM Testing Guide - Watch VMs During DAG Execution

## 🎯 Updated DAG Behavior

The `example_kcli_vm_provisioning` DAG now **keeps VMs running for 5 minutes** before cleanup!

### Workflow Timeline

```
1. List VMs Before      (5 seconds)
2. Create Test VM       (30-60 seconds)
3. Wait for VM Running  (up to 5 minutes)
4. Validate VM          (5 seconds)
5. List VMs After       (5 seconds)
6. Keep VM Running      ⏰ 5 MINUTES ← YOU CAN CHECK HERE!
7. Delete Test VM       (10 seconds)
```

## 🔍 How to Watch Your VMs

### During Step 6 (5-minute window), run these commands:

#### Option 1: From Host (Easiest)
```bash
# List all VMs
kcli list vms

# Get VM details
kcli info vm test-centos-<date>

# Check with virsh
virsh -c qemu:///system list --all
virsh -c qemu:///system dominfo test-centos-<date>
```

#### Option 2: From Airflow Container
```bash
# List VMs from inside container
podman exec airflow_airflow-scheduler_1 kcli list vms

# Get VM info from container
podman exec airflow_airflow-scheduler_1 virsh list --all
```

#### Option 3: Watch in Real-Time
```bash
# Watch VMs update every 2 seconds (host)
watch -n 2 'kcli list vms'

# Watch with virsh (host)
watch -n 2 'virsh -c qemu:///system list --all'
```

## 📊 Expected Output

### When VM is Running (Step 6)

```bash
$ kcli list vms
+------------------------+--------+----------------+----------------+------+---------+
| Name                   | Status | Ip             | Source         | Plan | Profile |
+------------------------+--------+----------------+----------------+------+---------+
| test-centos-20251119   | up     | 192.168.122.50 | centos10stream |      |         |
+------------------------+--------+----------------+----------------+------+---------+
```

### With virsh

```bash
$ virsh -c qemu:///system list --all
 Id   Name                 State
--------------------------------------
 1    test-centos-20251119 running
```

## 🎬 How to Test

### Step 1: Trigger the DAG

1. **Open Airflow UI**: http://localhost:8888
2. **Find DAG**: `example_kcli_vm_provisioning`
3. **Click Play**: Trigger the DAG
4. **Watch Progress**: Go to Graph view

### Step 2: Monitor Task Progress

Watch the task progress in Airflow UI:
- ✅ Green = Completed
- 🟡 Yellow = Running
- ⏸️ Gray = Queued

When you see `keep_vm_running_5min` task turn **yellow** (running), that's your 5-minute window!

### Step 3: Check VMs During the Wait

Open a terminal and run:

```bash
# Quick check
kcli list vms

# Detailed info
kcli info vm test-centos-$(date +%Y%m%d)

# Watch continuously
watch -n 2 'kcli list vms'
```

### Step 4: Watch Auto-Cleanup

After 5 minutes:
- `delete_test_vm` task runs
- VM is automatically removed
- Run `kcli list vms` again - VM should be gone

## 🧪 Manual Testing Commands

### Create VM Manually (for testing)

```bash
# Create a test VM
kcli create vm manual-test -i centos10stream -P memory=1024 -P numcpus=1

# Check it
kcli list vms

# Delete it
kcli delete vm manual-test -y
```

### Check VM Details

```bash
# Basic info
kcli info vm test-centos-20251119

# Detailed virsh info
virsh -c qemu:///system dominfo test-centos-20251119

# VM resources
virsh -c qemu:///system domstats test-centos-20251119

# VM network
virsh -c qemu:///system domiflist test-centos-20251119
```

## 📝 Logs to Monitor

### Watch DAG Logs During Execution

```bash
# Follow scheduler logs
podman logs -f airflow_airflow-scheduler_1 | grep -i "test-centos"

# Check task-specific logs in Airflow UI
# Navigate to: Graph View → Click task → Logs
```

### Key Log Messages

**Step 2 - Create VM:**
```
[INFO] Creating VM: test-centos-20251119
[INFO] Running kcli command: kcli create vm test-centos-20251119 -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]
[INFO] ✅ VM test-centos-20251119 created successfully
```

**Step 6 - Keep Running:**
```
[INFO] VM is running. Check it with: kcli list vms
[INFO] Waiting 5 minutes before cleanup...
```

**Step 7 - Delete:**
```
[INFO] Deleting VM: test-centos-20251119
[INFO] ✅ VM test-centos-20251119 deleted successfully
```

## ⏱️ Timeline Reference

| Task | Duration | What to Do |
|------|----------|------------|
| `list_vms_before` | ~5s | Wait |
| `create_test_vm` | 30-60s | Wait for VM creation |
| `wait_for_vm_running` | 0-300s | VM is starting |
| `validate_vm` | ~5s | Wait |
| `list_vms_after` | ~5s | Wait |
| **`keep_vm_running_5min`** | **300s** | **🎯 CHECK VMs NOW!** |
| `delete_test_vm` | ~10s | VM cleanup |

**Total DAG runtime**: ~7-12 minutes (depending on VM boot time)

## 💡 Pro Tips

### 1. Open Two Terminals

**Terminal 1 - Watch VMs:**
```bash
watch -n 2 'echo "=== kcli list ===" && kcli list vms && echo -e "\n=== virsh list ===" && virsh -c qemu:///system list --all'
```

**Terminal 2 - Watch Logs:**
```bash
podman logs -f airflow_airflow-scheduler_1 | grep --color=auto -E "Creating|created|running|Waiting|Deleting|deleted"
```

### 2. Get Notifications

Add to your terminal:
```bash
# Get notified when VM is running
while true; do
  if kcli list vms | grep -q "test-centos"; then
    echo "✅ VM is UP! Check it now!"
    break
  fi
  sleep 5
done
```

### 3. Screenshot the VM List

```bash
# Save VM list during the 5-minute window
kcli list vms > ~/vm-snapshot-$(date +%Y%m%d-%H%M%S).txt
```

## 🔧 Troubleshooting

### VM Not Appearing?

```bash
# Check if libvirt is running
systemctl status libvirtd

# Check libvirt networks
virsh -c qemu:///system net-list --all

# Check storage pools
virsh -c qemu:///system pool-list --all

# Check for errors in Airflow logs
podman logs airflow_airflow-scheduler_1 --tail 100 | grep -i error
```

### Can't See VM from Host?

```bash
# Verify libvirt connection
virsh -c qemu:///system uri

# Check if kcli is using same connection
kcli list host

# Verify images
virsh -c qemu:///system vol-list default
```

## 🎉 Success Criteria

You've successfully tested when you can:

- ✅ See VM in `kcli list vms` output
- ✅ See VM in `virsh list --all` output  
- ✅ Get VM details with `kcli info vm <name>`
- ✅ See VM get automatically deleted after 5 minutes
- ✅ Confirm VM disappears from both kcli and virsh lists

## 📚 Related Documentation

- **DAG Documentation**: See DAG description in Airflow UI
- **kcli Commands**: `airflow/TOOLS-AVAILABLE.md`
- **Logging Guide**: `airflow/LOGGING-GUIDE.md`
- **Bug Fixes**: `airflow/BUGFIX-KCLI-SYNTAX.md`

## 🚀 Next Steps

Once you verify VMs are working:

1. **Create your own DAG** with custom VM specs
2. **Adjust the 5-minute wait** (change `sleep 300` in the DAG)
3. **Add more validation steps** during the wait period
4. **Build multi-VM workflows** using parallel tasks

---

**Happy VM provisioning!** 🎯
