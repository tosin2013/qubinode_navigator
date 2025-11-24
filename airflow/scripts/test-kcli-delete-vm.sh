#!/bin/bash
# Test Script: Delete VM with kcli
# Run this to test VM deletion before adding to DAG

set -e  # Exit on error

VM_NAME="${1}"

if [ -z "$VM_NAME" ]; then
    echo "Usage: $0 <vm_name>"
    echo ""
    echo "Available VMs:"
    virsh -c qemu:///system list --all
    exit 1
fi

echo "=================================="
echo "kcli VM Deletion Test Script"
echo "=================================="
echo "VM Name: $VM_NAME"
echo "=================================="
echo ""

# Step 1: Check if VM exists
echo "🔍 Step 1: Checking if VM exists..."
if virsh -c qemu:///system dominfo "$VM_NAME" &>/dev/null; then
    echo "✅ VM '$VM_NAME' found"
else
    echo "❌ VM '$VM_NAME' not found"
    echo ""
    echo "Available VMs:"
    virsh -c qemu:///system list --all
    exit 1
fi
echo ""

# Step 2: Show VM state
echo "📊 Step 2: Current VM state:"
virsh -c qemu:///system domstate "$VM_NAME"
echo ""

# Step 3: Show the kcli delete command
echo "🔧 Step 3: kcli command to be executed:"
KCLI_CMD="kcli delete vm $VM_NAME -y"
echo "$KCLI_CMD"
echo ""
echo "Note: This is equivalent to:"
echo "  virsh -c qemu:///system destroy $VM_NAME (if running)"
echo "  virsh -c qemu:///system undefine $VM_NAME --remove-all-storage"
echo ""

# Step 4: Confirm
read -p "Delete this VM? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted by user"
    exit 0
fi

# Step 5: Stop VM if running
echo "🛑 Step 4: Stopping VM if running..."
if [ "$(virsh -c qemu:///system domstate "$VM_NAME")" = "running" ]; then
    virsh -c qemu:///system destroy "$VM_NAME" || echo "⚠️  Could not stop VM (may already be stopped)"
    sleep 2
fi
echo ""

# Step 6: Delete with kcli
echo "🗑️  Step 5: Deleting VM with kcli..."
if eval "$KCLI_CMD"; then
    echo "✅ VM deletion command completed"
else
    echo "⚠️  kcli delete failed, trying virsh fallback..."
    virsh -c qemu:///system undefine "$VM_NAME" --remove-all-storage
fi
echo ""

# Step 7: Verify deletion
echo "🔍 Step 6: Verifying VM was deleted..."
sleep 2
if virsh -c qemu:///system dominfo "$VM_NAME" &>/dev/null; then
    echo "⚠️  VM still exists!"
    virsh -c qemu:///system list --all
    exit 1
else
    echo "✅ VM successfully deleted"
fi
echo ""

# Step 8: Show remaining VMs
echo "📋 Step 7: Remaining VMs:"
virsh -c qemu:///system list --all
echo ""

echo "=================================="
echo "✅ VM Deletion Test Complete!"
echo "=================================="
echo ""
echo "If successful, you can now use this in your DAG:"
echo "  KcliVMDeleteOperator("
echo "      vm_name='$VM_NAME',"
echo "      force=True"
echo "  )"
echo ""
