#!/bin/bash
# Complete Workflow Test: Create → Wait → Validate → Delete
# This mirrors the example_kcli_vm_provisioning DAG

set -e

VM_NAME="test-workflow-$(date +%Y%m%d-%H%M%S)"
IMAGE="centos10stream"

echo "=========================================="
echo "Complete VM Workflow Test"
echo "=========================================="
echo "This script tests the full VM lifecycle:"
echo "  1. List VMs (before)"
echo "  2. Create VM"
echo "  3. Wait for VM to be running"
echo "  4. Validate VM"
echo "  5. List VMs (after)"
echo "  6. Keep VM running (configurable)"
echo "  7. Delete VM"
echo ""
echo "VM: $VM_NAME"
echo "=========================================="
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Step 1: List VMs before
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1/7: List VMs (BEFORE)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
virsh -c qemu:///system list --all
echo ""
sleep 2

# Step 2: Create VM
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2/7: Create VM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: kcli create vm $VM_NAME -i $IMAGE -P memory=2048 -P numcpus=2 -P disks=[10]"
if kcli create vm "$VM_NAME" -i "$IMAGE" -P memory=2048 -P numcpus=2 -P disks=[10]; then
    echo "✅ VM created successfully"
else
    echo "❌ VM creation failed"
    exit 1
fi
echo ""
sleep 3

# Step 3: Wait for VM to be running
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3/7: Wait for VM to be running"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
MAX_WAIT=300  # 5 minutes
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATE=$(virsh -c qemu:///system domstate "$VM_NAME" 2>/dev/null || echo "unknown")
    echo "[$ELAPSED/${MAX_WAIT}s] VM State: $STATE"

    if [ "$STATE" = "running" ]; then
        echo "✅ VM is running!"
        break
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ "$STATE" != "running" ]; then
    echo "⚠️  VM did not reach running state within ${MAX_WAIT}s"
    echo "Current state: $STATE"
fi
echo ""
sleep 2

# Step 4: Validate VM
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4/7: Validate VM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Getting VM details..."
virsh -c qemu:///system dominfo "$VM_NAME"
echo ""
echo "✅ VM validation successful"
sleep 2

# Step 5: List VMs after
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5/7: List VMs (AFTER)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
virsh -c qemu:///system list --all
echo ""

# Highlight the test VM
echo "Test VM details:"
virsh -c qemu:///system list --all | grep "$VM_NAME" || echo "VM not found in list!"
echo ""
sleep 2

# Step 6: Keep VM running
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 6/7: Keep VM Running"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "VM is running. You can check it with:"
echo "  • kcli list vms"
echo "  • virsh -c qemu:///system list --all"
echo "  • kcli info vm $VM_NAME"
echo ""
echo "How long to keep VM running before cleanup?"
echo "  1) 30 seconds (quick test)"
echo "  2) 5 minutes (like DAG)"
echo "  3) Keep running (manual cleanup)"
echo "  4) Delete immediately"
echo ""
read -p "Choose (1-4): " -n 1 -r WAIT_CHOICE
echo ""

case $WAIT_CHOICE in
    1)
        WAIT_TIME=30
        echo "Waiting 30 seconds..."
        ;;
    2)
        WAIT_TIME=300
        echo "Waiting 5 minutes (like the DAG)..."
        ;;
    3)
        echo "VM will keep running. Delete manually with:"
        echo "  ./scripts/test-kcli-delete-vm.sh $VM_NAME"
        echo ""
        echo "=========================================="
        echo "✅ Workflow Test Complete (VM still running)"
        echo "=========================================="
        exit 0
        ;;
    4)
        WAIT_TIME=0
        echo "Proceeding to immediate cleanup..."
        ;;
    *)
        WAIT_TIME=30
        echo "Invalid choice, defaulting to 30 seconds..."
        ;;
esac

if [ $WAIT_TIME -gt 0 ]; then
    for i in $(seq $WAIT_TIME -1 1); do
        printf "\r⏳ Waiting... %3ds remaining (Check VM now!)   " $i
        sleep 1
    done
    echo ""
fi
echo ""

# Step 7: Delete VM
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 7/7: Delete VM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "Delete the test VM now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Deleting VM: $VM_NAME"
    if kcli delete vm "$VM_NAME" -y; then
        echo "✅ VM deleted successfully"
    else
        echo "⚠️  kcli delete failed, trying virsh..."
        virsh -c qemu:///system destroy "$VM_NAME" 2>/dev/null || true
        virsh -c qemu:///system undefine "$VM_NAME" --remove-all-storage
        echo "✅ VM deleted with virsh"
    fi
else
    echo "VM kept running. Delete manually with:"
    echo "  ./scripts/test-kcli-delete-vm.sh $VM_NAME"
fi
echo ""

# Final verification
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Final State"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
virsh -c qemu:///system list --all
echo ""

echo "=========================================="
echo "✅ Complete Workflow Test Finished!"
echo "=========================================="
echo ""
echo "If all steps succeeded, your DAG should work!"
echo "This test covered all tasks in:"
echo "  example_kcli_vm_provisioning"
echo ""
