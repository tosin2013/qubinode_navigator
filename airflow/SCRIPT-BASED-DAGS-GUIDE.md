# Script-Based DAGs Guide

## 🎯 Why Script-Based DAGs?

**Your observation was excellent:** "Maybe we need to update the dag to call the same scripts we are calling under scripts"

### The Problem with Custom Operators

```python
# Custom Operator Approach (COMPLEX):
KcliVMCreateOperator(
    vm_name='test',
    image='centos10stream',
    ...
)
# ↓
# Calls KcliHook
# ↓  
# Builds command
# ↓
# May have bugs
# ❌ Hard to debug
# ❌ Requires image rebuild to fix
# ❌ Hidden complexity
```

### The Solution: Use Proven Scripts

```bash
# Script Approach (SIMPLE):
BashOperator(
    bash_command='kcli create vm test -i centos10stream ...'
)
# ↓
# Direct command execution
# ✅ Same commands from test scripts
# ✅ Already proven to work
# ✅ Easy to debug
# ✅ Transparent
```

## 📊 Comparison

| Aspect | Custom Operators | Script-Based DAGs |
|--------|------------------|-------------------|
| **Reliability** | Depends on hook implementation | Uses proven test scripts |
| **Debugging** | Check Python code, rebuild image | Check bash command in logs |
| **Testing** | Need full DAG run | Test script directly |
| **Complexity** | High (operators + hooks + error handling) | Low (just bash commands) |
| **Maintenance** | Update Python, rebuild, redeploy | Edit script, reload DAG |
| **Transparency** | Hidden in code | Visible in task logs |
| **Learning Curve** | Need to understand operators/hooks | Just bash/kcli knowledge |
| **Bug Fixes** | Rebuild entire image | Edit DAG file |

## 🚀 New DAG: `example_kcli_script_based`

### What's Different?

**Old DAG (`example_kcli_vm_provisioning`):**
```python
from qubinode.operators import KcliVMCreateOperator

create_vm = KcliVMCreateOperator(
    task_id='create_test_vm',
    vm_name='test-vm',
    image='centos10stream',
    memory=2048,
    cpus=2,
    disk_size='10G',
)
```

**New DAG (`example_kcli_script_based`):**
```python
from airflow.operators.bash import BashOperator

create_vm = BashOperator(
    task_id='create_vm',
    bash_command='''
    echo "Creating VM..."
    kcli create vm {{ params.vm_name }} -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]
    
    if [ $? -eq 0 ]; then
        echo "✅ VM created successfully"
    else
        echo "❌ VM creation failed"
        exit 1
    fi
    ''',
)
```

### Key Improvements

1. **Direct kcli Commands**
   - Same commands from `/opt/airflow/scripts/test-kcli-create-vm.sh`
   - Already tested and proven to work
   - No abstraction layer

2. **Better Error Handling**
   - Explicit exit codes
   - Clear success/failure messages
   - Easy to see what failed

3. **Verification Built-In**
   - Checks if VM exists after creation
   - Waits for running state
   - Shows detailed VM info

4. **Transparent Logging**
   - Every command visible in logs
   - Can copy/paste commands to test manually
   - No hidden operations

## 🔧 Workflow Comparison

### Old Workflow (Operator-Based)

```
User triggers DAG
  ↓
create_test_vm task starts
  ↓
KcliVMCreateOperator.execute()
  ↓
KcliHook.create_vm()
  ↓
Build kcli command (may have bugs)
  ↓
Run subprocess
  ↓
Return result
  ↓
❓ Did it work? Check virsh manually
```

### New Workflow (Script-Based)

```
User triggers DAG
  ↓
create_vm task starts
  ↓
BashOperator executes inline script
  ↓
Echo command (visible in logs)
  ↓
Run kcli create vm (proven command)
  ↓
Check exit code
  ↓
Verify VM exists with virsh
  ↓
Show VM details
  ↓
✅ Clear success/failure
```

## 📋 Task Breakdown

### New DAG Tasks:

1. **list_vms_before**
   ```bash
   /opt/airflow/scripts/test-kcli-list-vms.sh
   ```
   Uses the proven test script directly!

2. **create_vm**
   ```bash
   kcli create vm {vm_name} -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]
   ```
   Same command from test script that we know works!

3. **verify_vm_running**
   ```bash
   virsh domstate {vm_name}
   # Waits up to 60 seconds for 'running' state
   ```
   Built-in verification!

4. **list_vms_after_creation**
   ```bash
   kcli list vms
   virsh list --all
   ```
   Shows VM in both tools!

5. **keep_vm_running_2min**
   ```bash
   echo "VM running, check with: kcli list vms"
   sleep 120  # 2 minutes (shorter for faster testing)
   ```
   Countdown timer included!

6. **delete_vm**
   ```bash
   kcli delete vm {vm_name} -y
   # Fallback to virsh if kcli fails
   # Verifies deletion
   ```
   Robust cleanup!

7. **list_vms_final**
   ```bash
   kcli list vms
   ```
   Confirms cleanup!

## 🧪 Testing the New DAG

### Step 1: Verify Scripts Are Mounted

```bash
podman exec airflow_airflow-scheduler_1 ls -la /opt/airflow/scripts/

# Should show:
# test-kcli-create-vm.sh
# test-kcli-delete-vm.sh
# test-kcli-list-vms.sh
# test-complete-workflow.sh
```

### Step 2: Check DAG is Available

```bash
podman exec airflow_airflow-scheduler_1 airflow dags list | grep script_based

# Should show:
# example_kcli_script_based | ... | False  (not paused)
```

### Step 3: Trigger the DAG

1. Go to: http://localhost:8888
2. Find `example_kcli_script_based`
3. Click play button ▶️
4. Select "Trigger DAG"

### Step 4: Monitor Execution

```bash
# Watch VMs appear
watch -n 2 'kcli list vms'

# Watch DAG logs
podman logs -f airflow_airflow-scheduler_1 | grep -E "Creating VM|VM created|✅|❌"
```

### Step 5: Expected Output

```
Task: create_vm
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creating VM: airflow-test-20251120001234
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creating VM with command:
kcli create vm airflow-test-20251120001234 -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]

Deploying vm airflow-test-20251120001234 from image centos10stream...
airflow-test-20251120001234 created on local

✅ VM created successfully
✅ VM verified in virsh
```

## 🔍 Debugging

### If create_vm Fails

**Check the exact command:**
```bash
# From DAG logs, copy the kcli command and run it manually:
podman exec airflow_airflow-scheduler_1 kcli create vm test-manual -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]
```

**Check if image exists:**
```bash
virsh -c qemu:///system vol-list default | grep centos10stream
```

**Use test script:**
```bash
cd /root/qubinode_navigator/airflow
./scripts/test-kcli-create-vm.sh test-debug centos10stream 2048 2 10
```

### If verify_vm_running Fails

**Check VM state manually:**
```bash
virsh -c qemu:///system domstate airflow-test-<timestamp>
```

**Check VM info:**
```bash
virsh -c qemu:///system dominfo airflow-test-<timestamp>
```

### If delete_vm Fails

**Manual cleanup:**
```bash
# Try kcli first
kcli delete vm airflow-test-<timestamp> -y

# Fallback to virsh
virsh -c qemu:///system destroy airflow-test-<timestamp>
virsh -c qemu:///system undefine airflow-test-<timestamp> --remove-all-storage
```

## 💡 Advantages in Practice

### Scenario 1: Bug in VM Creation

**Operator Approach:**
```
1. Find bug in KcliHook
2. Edit /opt/airflow/plugins/qubinode/hooks.py
3. Rebuild entire Docker image (5 minutes)
4. Restart all containers
5. Wait for Airflow to reload (2 minutes)
6. Test again
Total: ~10 minutes
```

**Script Approach:**
```
1. Find bug in bash command
2. Edit /opt/airflow/dags/example_kcli_script_based.py
3. DAG automatically reloads (30 seconds)
4. Test again
Total: ~1 minute
```

### Scenario 2: Testing Before DAG Run

**Operator Approach:**
```
1. Trigger DAG
2. Wait for task to run
3. Check logs
4. If failed, check operator code
5. Maybe test hook method manually?
```

**Script Approach:**
```
1. Copy command from DAG bash_command
2. Run it directly:
   podman exec airflow_airflow-scheduler_1 kcli create vm test ...
3. Instant feedback
4. If it works, DAG will work!
```

### Scenario 3: Understanding What Happened

**Operator Approach:**
```
Looking at logs:
"VM creation failed: <cryptic error>"

Need to:
- Check operator code
- Check hook implementation  
- Understand Python abstraction
- Find actual kcli command that ran
```

**Script Approach:**
```
Looking at logs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creating VM with command:
kcli create vm test -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]

Deploying vm test from image centos10stream...
❌ VM creation failed

✅ SEE EXACT COMMAND
✅ SEE EXACT ERROR
✅ CAN TEST IMMEDIATELY
```

## 📚 Related Files

### Test Scripts
- `/opt/airflow/scripts/test-kcli-create-vm.sh` - VM creation test
- `/opt/airflow/scripts/test-kcli-delete-vm.sh` - VM deletion test
- `/opt/airflow/scripts/test-kcli-list-vms.sh` - List VMs test
- `/opt/airflow/scripts/test-complete-workflow.sh` - Full workflow test

### DAG Files
- `/opt/airflow/dags/example_kcli_script_based.py` - ✅ **NEW** (script-based)
- `/opt/airflow/dags/example_kcli_vm_provisioning.py` - Old (operator-based, paused)
- `/opt/airflow/dags/example_kcli_virsh_combined.py` - Combined example

### Documentation
- `SCRIPTS-VS-DAGS.md` - Scripts vs DAG operators comparison
- `BUGFIX-KCLI-VERSION.md` - kcli version bug fix
- `HOW-TO-ADD-SCRIPTS.md` - Creating new test scripts
- `SCRIPTS-SUMMARY.md` - Testing results summary

## ✅ Status

**Current State:**

```bash
# DAG Status
$ airflow dags list | grep example_kcli
example_kcli_script_based     | False  ✅ ACTIVE (recommended)
example_kcli_vm_provisioning  | True   ⏸️  PAUSED (old approach)
example_kcli_virsh_combined   | False  ✅ ACTIVE

# Scripts Mounted
$ ls /opt/airflow/scripts/
test-kcli-create-vm.sh      ✅
test-kcli-delete-vm.sh      ✅
test-kcli-list-vms.sh       ✅
test-complete-workflow.sh   ✅
TEMPLATE-new-script.sh      ✅

# kcli Version
$ python -m pip list | grep kcli
kcli  99.0.202511192102  ✅ (latest, bug-fixed)

# genisoimage
$ which genisoimage
/usr/bin/genisoimage  ✅
```

## 🚀 Next Steps

1. **Test the new DAG:**
   ```
   http://localhost:8888
   Trigger: example_kcli_script_based
   ```

2. **Watch it work:**
   ```bash
   watch -n 2 'kcli list vms'
   ```

3. **Expected result:**
   - ✅ VM created
   - ✅ VM verified running
   - ✅ VM visible in kcli & virsh
   - ✅ Waits 2 minutes
   - ✅ VM deleted
   - ✅ DAG succeeds!

4. **If successful, you can:**
   - Create more script-based DAGs
   - Use the template for new workflows
   - Build complex orchestration
   - Integrate with other systems

## 🎯 Recommendation

**Use script-based DAGs for:**
- ✅ VM provisioning
- ✅ Infrastructure management
- ✅ Anything testable with bash
- ✅ Operations you test manually first

**Keep operator-based DAGs for:**
- Complex Python logic
- APIs that need authentication
- Data transformation
- Tasks that benefit from Python

## 🎉 Summary

Your idea to use the test scripts directly was **spot-on!**

**Benefits:**
- ✅ More reliable (proven commands)
- ✅ Easier to debug (see exact commands)
- ✅ Faster to fix (edit DAG, not code)
- ✅ Transparent (logs show everything)
- ✅ Testable (run commands directly)

**The new `example_kcli_script_based` DAG should work perfectly!** 🚀

Try it now at: **http://localhost:8888**
