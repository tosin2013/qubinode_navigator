"""
Example Airflow DAG: kcli VM Provisioning Using Test Scripts
Phase 6 Goal 2: Workflow Orchestration Integration

This DAG uses the proven test scripts from /opt/airflow/scripts/ directory.
This approach is more reliable because the scripts are tested and handle edge cases.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Default arguments for all tasks
default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 20),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
}

# Define the DAG
dag = DAG(
    'example_kcli_script_based',
    default_args=default_args,
    description='VM provisioning using tested shell scripts',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['qubinode', 'kcli', 'vm-provisioning', 'scripts', 'reliable'],
)

# Generate unique VM name using timestamp
vm_name = 'airflow-test-{{ ts_nodash | lower }}'

# Task 1: List VMs before
list_vms_before = BashOperator(
    task_id='list_vms_before',
    bash_command='/opt/airflow/scripts/test-kcli-list-vms.sh',
    dag=dag,
)

# Task 2: Create VM using the proven test script
create_vm = BashOperator(
    task_id='create_vm',
    bash_command=f'''
    # The test script is interactive, so we'll use kcli directly with the proven syntax
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Creating VM: {vm_name}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check if image exists
    if ! virsh -c qemu:///system vol-list default | grep -q centos10stream; then
        echo "❌ Error: centos10stream image not found"
        exit 1
    fi
    
    # Create VM using the same command from our test script
    echo "Creating VM with command:"
    echo "kcli create vm {vm_name} -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]"
    
    kcli create vm {vm_name} -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]
    
    if [ $? -eq 0 ]; then
        echo "✅ VM created successfully"
    else
        echo "❌ VM creation failed"
        exit 1
    fi
    
    # Verify VM exists
    sleep 5
    if virsh -c qemu:///system dominfo {vm_name} &>/dev/null; then
        echo "✅ VM verified in virsh"
    else
        echo "❌ VM not found in virsh"
        exit 1
    fi
    ''',
    dag=dag,
)

# Task 3: Verify VM is running
verify_vm = BashOperator(
    task_id='verify_vm_running',
    bash_command=f'''
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Verifying VM: {vm_name}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Wait up to 60 seconds for VM to be running
    for i in {{1..12}}; do
        STATE=$(virsh -c qemu:///system domstate {vm_name} 2>/dev/null || echo "not-found")
        echo "Attempt $i/12: VM state = $STATE"
        
        if [ "$STATE" = "running" ]; then
            echo "✅ VM is running!"
            break
        fi
        
        if [ $i -eq 12 ]; then
            echo "❌ VM failed to reach running state after 60 seconds"
            exit 1
        fi
        
        sleep 5
    done
    
    # Show VM details
    echo ""
    echo "VM Details:"
    virsh -c qemu:///system dominfo {vm_name}
    ''',
    dag=dag,
)

# Task 4: List VMs after creation
list_vms_after = BashOperator(
    task_id='list_vms_after_creation',
    bash_command=f'''
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Current VMs (including {vm_name}):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo "Using kcli:"
    kcli list vms
    
    echo ""
    echo "Using virsh:"
    virsh -c qemu:///system list --all
    ''',
    dag=dag,
)

# Task 5: Keep VM running for observation (shorter - 2 minutes)
keep_vm_running = BashOperator(
    task_id='keep_vm_running_2min',
    bash_command=f'''
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "VM {vm_name} is running!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "You can check it with:"
    echo "  kcli list vms"
    echo "  virsh -c qemu:///system list --all"
    echo ""
    echo "Keeping VM alive for 2 minutes..."
    
    # Show countdown
    for i in {{120..1}}; do
        if [ $((i % 30)) -eq 0 ]; then
            echo "$i seconds remaining..."
        fi
        sleep 1
    done
    
    echo "✅ Observation period complete"
    ''',
    dag=dag,
)

# Task 6: Delete VM (cleanup)
delete_vm = BashOperator(
    task_id='delete_vm',
    bash_command=f'''
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Deleting VM: {vm_name}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check if VM exists
    if ! virsh -c qemu:///system dominfo {vm_name} &>/dev/null; then
        echo "⚠️  VM {vm_name} not found (may have been manually deleted)"
        exit 0
    fi
    
    # Try to stop VM if running
    STATE=$(virsh -c qemu:///system domstate {vm_name} 2>/dev/null)
    if [ "$STATE" = "running" ]; then
        echo "Stopping VM..."
        virsh -c qemu:///system destroy {vm_name} || true
        sleep 2
    fi
    
    # Delete VM using kcli (preferred)
    echo "Deleting with kcli..."
    if kcli delete vm {vm_name} -y; then
        echo "✅ VM deleted with kcli"
    else
        # Fallback to virsh
        echo "kcli delete failed, trying virsh..."
        virsh -c qemu:///system undefine {vm_name} --remove-all-storage
        echo "✅ VM deleted with virsh"
    fi
    
    # Verify deletion
    sleep 2
    if virsh -c qemu:///system dominfo {vm_name} &>/dev/null; then
        echo "❌ VM still exists after deletion!"
        exit 1
    else
        echo "✅ VM successfully deleted and verified"
    fi
    ''',
    dag=dag,
)

# Task 7: Final VM list (should be back to original)
list_vms_final = BashOperator(
    task_id='list_vms_final',
    bash_command='''
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Final VM List (after cleanup):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    kcli list vms
    
    echo ""
    echo "✅ DAG completed successfully!"
    ''',
    dag=dag,
)

# Define task dependencies (linear workflow)
list_vms_before >> create_vm >> verify_vm >> list_vms_after >> keep_vm_running >> delete_vm >> list_vms_final

# Task documentation
dag.doc_md = """
# kcli VM Provisioning DAG (Script-Based)

**This DAG uses proven shell scripts and direct kcli commands.**

## Why This Approach?

✅ **Reliable**: Uses the same commands from our tested scripts  
✅ **Transparent**: You can see exactly what commands run  
✅ **Debuggable**: Easy to test commands outside Airflow  
✅ **Battle-tested**: Scripts proven to work in `/opt/airflow/scripts/`

## Workflow Steps

1. **List VMs Before** - Shows current VMs using test script
2. **Create VM** - Creates VM using proven kcli command
3. **Verify VM Running** - Waits up to 60s for VM to be running
4. **List VMs After** - Shows VM in the list
5. **Keep Running 2min** - VM stays alive for observation
6. **Delete VM** - Cleanup using kcli/virsh
7. **List VMs Final** - Verify cleanup

## VM Configuration

- **Name**: `airflow-test-<timestamp>` (unique per run)
- **Image**: `centos10stream`
- **Memory**: 2048 MB
- **CPUs**: 2
- **Disk**: 10 GB

## Testing Commands

You can test each step manually:

```bash
# List VMs
/opt/airflow/scripts/test-kcli-list-vms.sh

# Create VM
kcli create vm test-vm -i centos10stream -P memory=2048 -P numcpus=2 -P disks=[10]

# Check status
virsh -c qemu:///system domstate test-vm

# Delete VM
kcli delete vm test-vm -y
```

## Monitoring During Run

While the DAG is running (during step 5), you can check the VM:

```bash
# From host
kcli list vms

# From container
podman exec airflow_airflow-scheduler_1 kcli list vms

# Using virsh
virsh -c qemu:///system list --all
```

## Advantages Over Custom Operators

| Aspect | Custom Operators | Shell Scripts |
|--------|------------------|---------------|
| Complexity | High (Python classes) | Low (bash commands) |
| Debugging | Need to rebuild image | Just edit script |
| Testing | Requires DAG run | Can test directly |
| Transparency | Hidden in code | Visible in logs |
| Reliability | Depends on hooks | Uses proven commands |

## Related Files

- `/opt/airflow/scripts/test-kcli-create-vm.sh` - Test script for VM creation
- `/opt/airflow/scripts/test-kcli-delete-vm.sh` - Test script for VM deletion
- `/opt/airflow/scripts/test-kcli-list-vms.sh` - Test script for listing VMs
- `/opt/airflow/scripts/test-complete-workflow.sh` - Complete workflow test

## Related Documentation

- **ADR-0036**: Apache Airflow Workflow Orchestration Integration
- **BUGFIX-KCLI-VERSION.md**: kcli version fix documentation
- **SCRIPTS-VS-DAGS.md**: Comparison of scripts vs operators
- **HOW-TO-ADD-SCRIPTS.md**: Guide for creating new test scripts

## Usage

1. Go to Airflow UI: http://localhost:8888
2. Find `example_kcli_script_based` DAG
3. Click play button ▶️ to trigger
4. Watch it create, verify, and cleanup a VM!

**This DAG should be more reliable than the operator-based version!** ✅
"""
