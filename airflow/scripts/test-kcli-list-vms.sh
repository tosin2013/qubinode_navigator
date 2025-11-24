#!/bin/bash
# Test Script: List VMs
# Shows VMs using both kcli and virsh

echo "=================================="
echo "VM Listing Test Script"
echo "=================================="
echo ""

# Method 1: Using virsh (always works)
echo "📋 Method 1: virsh -c qemu:///system list --all"
echo "---"
virsh -c qemu:///system list --all
echo ""

# Method 2: Using kcli (if available)
echo "📋 Method 2: kcli list vms"
echo "---"
if command -v kcli &> /dev/null; then
    if kcli list vms 2>/dev/null; then
        echo "✅ kcli list successful"
    else
        echo "⚠️  kcli list failed (may not be configured)"
        echo "Try: sudo kcli list vms"
    fi
else
    echo "⚠️  kcli not in PATH"
fi
echo ""

# Method 3: From Airflow container
echo "📋 Method 3: From Airflow container"
echo "---"
if podman ps --format '{{.Names}}' | grep -q airflow_airflow-scheduler_1; then
    echo "Command: podman exec airflow_airflow-scheduler_1 virsh list --all"
    podman exec airflow_airflow-scheduler_1 virsh list --all 2>/dev/null || echo "⚠️  Container not accessible"
else
    echo "⚠️  Airflow scheduler container not running"
fi
echo ""

# Summary
echo "=================================="
echo "Summary"
echo "=================================="
VM_COUNT=$(virsh -c qemu:///system list --all --name | grep -v '^$' | wc -l)
RUNNING_COUNT=$(virsh -c qemu:///system list --name | grep -v '^$' | wc -l)
echo "Total VMs:    $VM_COUNT"
echo "Running VMs:  $RUNNING_COUNT"
echo ""

if [ "$VM_COUNT" -eq 0 ]; then
    echo "💡 No VMs found. Create one with:"
    echo "   ./scripts/test-kcli-create-vm.sh"
fi
echo ""

# DAG equivalent
echo "In Airflow DAG, use:"
echo "  KcliVMListOperator(task_id='list_vms')"
echo ""
