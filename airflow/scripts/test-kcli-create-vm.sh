#!/bin/bash
# Test Script: Create VM with kcli
# Run this BEFORE adding to DAG to verify it works

set -e  # Exit on error

# Configuration
VM_NAME="${1:-test-vm-$(date +%Y%m%d-%H%M%S)}"
IMAGE="${2:-centos10stream}"
MEMORY="${3:-2048}"
CPUS="${4:-2}"
DISK="${5:-10}"

echo "=================================="
echo "kcli VM Creation Test Script"
echo "=================================="
echo "VM Name:  $VM_NAME"
echo "Image:    $IMAGE"
echo "Memory:   ${MEMORY}MB"
echo "CPUs:     $CPUS"
echo "Disk:     ${DISK}GB"
echo "=================================="
echo ""

# Step 1: Check available images
echo "📋 Step 1: Checking available images..."
echo "Command: virsh -c qemu:///system vol-list default"
virsh -c qemu:///system vol-list default
echo ""

# Step 2: Verify image exists
if ! virsh -c qemu:///system vol-list default | grep -q "$IMAGE"; then
    echo "❌ ERROR: Image '$IMAGE' not found!"
    echo "Available images:"
    virsh -c qemu:///system vol-list default | grep -v "^---" | grep -v "Name.*Path"
    exit 1
fi
echo "✅ Image '$IMAGE' found"
echo ""

# Step 3: Show the exact kcli command
echo "🔧 Step 2: kcli command to be executed:"
KCLI_CMD="kcli create vm $VM_NAME -i $IMAGE -P memory=$MEMORY -P numcpus=$CPUS -P disks=[$DISK]"
echo "$KCLI_CMD"
echo ""

# Step 4: Confirm before proceeding
read -p "Execute this command? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted by user"
    exit 0
fi

# Step 5: Execute the command
echo "🚀 Step 3: Creating VM..."
if eval "$KCLI_CMD"; then
    echo "✅ VM creation command completed"
else
    echo "❌ VM creation failed"
    exit 1
fi
echo ""

# Step 6: Wait a moment for VM to initialize
echo "⏳ Waiting 5 seconds for VM to initialize..."
sleep 5
echo ""

# Step 7: Verify VM exists
echo "🔍 Step 4: Verifying VM was created..."
echo "Command: virsh -c qemu:///system list --all"
virsh -c qemu:///system list --all
echo ""

# Step 8: Get VM details
echo "📊 Step 5: VM Details:"
echo "Command: virsh -c qemu:///system dominfo $VM_NAME"
if virsh -c qemu:///system dominfo "$VM_NAME" 2>/dev/null; then
    echo "✅ VM details retrieved successfully"
else
    echo "⚠️  Could not get VM details (VM may still be starting)"
fi
echo ""

# Step 9: Show how to check from kcli
echo "📋 Step 6: Check with kcli (if available):"
echo "Command: kcli list vms"
if command -v kcli &> /dev/null; then
    kcli list vms || echo "⚠️  kcli list failed (may not be configured for this user)"
else
    echo "⚠️  kcli not available in PATH for this user"
    echo "Try: sudo kcli list vms"
fi
echo ""

# Step 10: Instructions
echo "=================================="
echo "✅ VM Creation Test Complete!"
echo "=================================="
echo ""
echo "VM Name: $VM_NAME"
echo ""
echo "Useful commands:"
echo "  • List VMs:      virsh -c qemu:///system list --all"
echo "  • VM Info:       virsh -c qemu:///system dominfo $VM_NAME"
echo "  • Start VM:      virsh -c qemu:///system start $VM_NAME"
echo "  • Stop VM:       virsh -c qemu:///system destroy $VM_NAME"
echo "  • Delete VM:     virsh -c qemu:///system undefine $VM_NAME --remove-all-storage"
echo ""
echo "To delete this test VM, run:"
echo "  ./scripts/test-kcli-delete-vm.sh $VM_NAME"
echo ""
echo "If successful, you can now use this in your DAG:"
echo "  KcliVMCreateOperator("
echo "      vm_name='$VM_NAME',"
echo "      image='$IMAGE',"
echo "      memory=$MEMORY,"
echo "      cpus=$CPUS,"
echo "      disk_size='${DISK}G'"
echo "  )"
echo ""
