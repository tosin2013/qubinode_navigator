# How to Add Your Own Test Scripts

## 🎯 Overview

Adding new test scripts is **easy**! Follow this guide to create custom scripts for your specific use cases.

## 🚀 Quick Start (3 Minutes)

### Step 1: Copy the Template (30 seconds)

```bash
cd /root/qubinode_navigator/airflow/scripts

# Copy template with your desired name
cp TEMPLATE-new-script.sh test-my-feature.sh

# Make it executable
chmod +x test-my-feature.sh
```

### Step 2: Edit the Script (2 minutes)

```bash
vim test-my-feature.sh
# or
nano test-my-feature.sh
```

**Customize these sections:**

1. **Lines 8-15**: Configuration (name, description, parameters)
1. **Lines 40-79**: Your test logic
1. **Lines 87-96**: DAG code example

### Step 3: Test It (30 seconds)

```bash
./test-my-feature.sh
```

Done! 🎉

## 📝 Complete Example

Let's create a script to test VM snapshot operations:

### 1. Create the Script

```bash
cp TEMPLATE-new-script.sh test-vm-snapshot.sh
chmod +x test-vm-snapshot.sh
```

### 2. Edit Configuration

```bash
#!/bin/bash
# Test VM Snapshot Creation

# Configuration
SCRIPT_NAME="VM Snapshot Test"
SCRIPT_DESC="Tests creating and managing VM snapshots"

VM_NAME="${1:-test-vm}"
SNAPSHOT_NAME="${2:-snap-$(date +%Y%m%d-%H%M%S)}"
```

### 3. Add Your Test Logic

```bash
# Step 1: Check if VM exists
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Check if VM exists"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if virsh -c qemu:///system dominfo "$VM_NAME" &>/dev/null; then
    echo "✅ VM '$VM_NAME' found"
else
    echo "❌ VM '$VM_NAME' not found"
    exit 1
fi
echo ""

# Step 2: Create snapshot
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Create Snapshot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
SNAPSHOT_CMD="virsh -c qemu:///system snapshot-create-as $VM_NAME $SNAPSHOT_NAME"
echo "Command: $SNAPSHOT_CMD"
echo ""

if eval "$SNAPSHOT_CMD"; then
    echo "✅ Snapshot created successfully"
else
    echo "❌ Snapshot creation failed"
    exit 1
fi
echo ""

# Step 3: List snapshots
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Verify Snapshot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
virsh -c qemu:///system snapshot-list "$VM_NAME"
echo ""
```

### 4. Test It

```bash
# First create a test VM
./test-kcli-create-vm.sh test-vm

# Then test your new script
./test-vm-snapshot.sh test-vm my-snapshot

# Clean up
./test-kcli-delete-vm.sh test-vm
```

## 🎨 Common Script Patterns

### Pattern 1: Simple Command Test

```bash
#!/bin/bash
# Test: List VM Networks

SCRIPT_NAME="List VM Networks"

echo "Testing: virsh net-list --all"
virsh -c qemu:///system net-list --all

echo ""
echo "In DAG use:"
echo "VirshNetworkListOperator(task_id='list_networks')"
```

### Pattern 2: Multi-Step Workflow

```bash
#!/bin/bash
# Test: VM Start → Check → Stop

VM_NAME="${1:-test-vm}"

# Step 1: Start VM
echo "Starting VM..."
virsh -c qemu:///system start "$VM_NAME"

# Step 2: Wait for running state
sleep 5
STATE=$(virsh -c qemu:///system domstate "$VM_NAME")
echo "VM State: $STATE"

# Step 3: Stop VM
echo "Stopping VM..."
virsh -c qemu:///system destroy "$VM_NAME"

echo "✅ Workflow complete!"
```

### Pattern 3: With Error Handling

```bash
#!/bin/bash
set -e  # Exit on any error

VM_NAME="${1}"

# Validate input
if [ -z "$VM_NAME" ]; then
    echo "❌ Error: VM name required"
    echo "Usage: $0 <vm_name>"
    exit 1
fi

# Check if VM exists
if ! virsh -c qemu:///system dominfo "$VM_NAME" &>/dev/null; then
    echo "❌ Error: VM '$VM_NAME' not found"
    exit 1
fi

# Do your operation
echo "✅ Operating on VM: $VM_NAME"
```

### Pattern 4: Interactive Script

```bash
#!/bin/bash
# Interactive VM selection

echo "Available VMs:"
virsh -c qemu:///system list --all --name

read -p "Select VM name: " VM_NAME

read -p "What operation? (start/stop/info): " OP

case $OP in
    start)
        virsh -c qemu:///system start "$VM_NAME"
        ;;
    stop)
        virsh -c qemu:///system destroy "$VM_NAME"
        ;;
    info)
        virsh -c qemu:///system dominfo "$VM_NAME"
        ;;
    *)
        echo "Unknown operation"
        exit 1
        ;;
esac
```

## 📚 Making Scripts RAG-Aware

### How AI Assistant Learns About Your Scripts

The AI Assistant (RAG) becomes aware of scripts through:

1. **File Content** - When users reference scripts, AI reads them
1. **Documentation** - README.md and markdown docs
1. **Conversations** - When you discuss scripts with AI
1. **Context Files** - .mcp-server-context.md updates

### Best Practices for RAG Awareness

#### 1. Clear Documentation Header

```bash
#!/bin/bash
# Script: test-custom-feature.sh
# Purpose: Tests custom VM network configuration
# Usage: ./test-custom-feature.sh <vm_name> <network>
# Example: ./test-custom-feature.sh myvm default
#
# This script:
#   1. Checks if VM exists
#   2. Configures network settings
#   3. Verifies connectivity
#
# Equivalent DAG operator:
#   CustomNetworkOperator(vm_name='myvm', network='default')
```

#### 2. Add to scripts/README.md

```bash
# Edit the README
vim scripts/README.md

# Add your script to the table:
| `test-custom-feature.sh` | Test custom network config | Before using CustomNetworkOperator |
```

#### 3. Create a Companion Markdown Doc (Optional)

````bash
# For complex scripts, create documentation
cat > ../CUSTOM-FEATURE-GUIDE.md << 'EOF'
# Custom Feature Testing Guide

## Overview
This guide explains how to test custom network configurations...

## Script Usage
```bash
./scripts/test-custom-feature.sh myvm default
````

## When to Use

Use this before adding CustomNetworkOperator to your DAGs...
EOF

```

#### 4. Use Consistent Naming

Follow the pattern: `test-<category>-<action>.sh`

```

✅ Good names:
test-vm-snapshot-create.sh
test-network-attach-vm.sh
test-storage-pool-create.sh

❌ Avoid:
my_script.sh
temp-test.sh
script1.sh

````

### Example: Making a Script Discoverable

**Before (low discoverability):**
```bash
#!/bin/bash
# temp script
kcli info vm $1
````

**After (high discoverability):**

```bash
#!/bin/bash
# ============================================
# Script: test-vm-info-detailed.sh
# Purpose: Get comprehensive VM information
# Category: VM Information
# ============================================
#
# Description:
#   Retrieves detailed information about a VM using both
#   kcli and virsh commands for complete visibility.
#
# Usage:
#   ./test-vm-info-detailed.sh <vm_name>
#
# Example:
#   ./test-vm-info-detailed.sh webserver-01
#
# Output:
#   - Basic VM info (kcli)
#   - Detailed VM stats (virsh)
#   - Network configuration
#   - Disk information
#
# Use in DAG:
#   This script tests functionality for:
#   - VirshVMInfoOperator
#   - KcliVMInfoOperator (if created)
#
# ============================================

VM_NAME="${1}"

if [ -z "$VM_NAME" ]; then
    echo "Usage: $0 <vm_name>"
    exit 1
fi

echo "🔍 VM Information: $VM_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# kcli info
echo "📋 kcli info:"
kcli info vm "$VM_NAME" 2>/dev/null || echo "⚠️  kcli not available"

# virsh info
echo ""
echo "📋 virsh dominfo:"
virsh -c qemu:///system dominfo "$VM_NAME"

# Network
echo ""
echo "📋 Network interfaces:"
virsh -c qemu:///system domiflist "$VM_NAME"

# Disks
echo ""
echo "📋 Disk devices:"
virsh -c qemu:///system domblklist "$VM_NAME"
```

Now the AI can:

- Understand what the script does
- Recommend it when users ask about VM info
- Explain how to use it
- Suggest related operators

## 🎓 Script Development Workflow

### 1. Start with Template

```bash
cp TEMPLATE-new-script.sh test-my-new-feature.sh
chmod +x test-my-new-feature.sh
```

### 2. Develop Iteratively

```bash
# Edit
vim test-my-new-feature.sh

# Test
./test-my-new-feature.sh

# Fix errors
# Repeat until working
```

### 3. Add Documentation

```bash
# Add clear header comments
# Update scripts/README.md
# Optional: Create companion .md file
```

### 4. Test Edge Cases

```bash
# Test with invalid input
./test-my-new-feature.sh ""

# Test with missing resources
./test-my-new-feature.sh nonexistent-vm

# Test with valid input
./test-my-new-feature.sh real-vm
```

### 5. Share/Document

```bash
# Commit to git
git add scripts/test-my-new-feature.sh
git commit -m "Add test script for new feature"

# Tell AI about it
# Go to AI Assistant and say:
# "I created a new test script at scripts/test-my-new-feature.sh
#  that tests X. Can you help me document it?"
```

## 🔧 Debugging Your Scripts

### Enable Debug Mode

```bash
#!/bin/bash
set -x  # Print each command before executing
set -e  # Exit on error
set -u  # Exit on undefined variable

# Your script logic...
```

### Add Verbose Output

```bash
# Add -v flag support
VERBOSE=${VERBOSE:-false}

if [ "$VERBOSE" = "true" ]; then
    echo "DEBUG: VM_NAME=$VM_NAME"
    echo "DEBUG: Running command: $COMMAND"
fi

# Use it:
VERBOSE=true ./test-my-script.sh
```

### Test with bash -x

```bash
# Run script with trace mode
bash -x ./test-my-script.sh

# See every command executed
```

## 📊 Script Quality Checklist

Before considering your script "done":

- [ ] Has clear documentation header
- [ ] Validates input parameters
- [ ] Uses proper error handling (set -e)
- [ ] Shows commands before executing
- [ ] Includes verification steps
- [ ] Provides DAG code example
- [ ] Has meaningful error messages
- [ ] Uses consistent formatting
- [ ] Follows naming convention
- [ ] Added to scripts/README.md
- [ ] Tested with valid input
- [ ] Tested with invalid input
- [ ] Tested edge cases

## 🎯 Real-World Examples

### Example 1: Test Multi-VM Creation

```bash
#!/bin/bash
# Test creating multiple VMs in parallel

NUM_VMS="${1:-3}"
BASE_NAME="worker"

echo "Creating $NUM_VMS VMs..."

for i in $(seq 1 $NUM_VMS); do
    VM_NAME="${BASE_NAME}-${i}"
    echo "Creating $VM_NAME..."

    kcli create vm "$VM_NAME" \
        -i centos10stream \
        -P memory=1024 \
        -P numcpus=1 \
        -P disks=[10] &
done

wait
echo "✅ All VMs created!"

kcli list vms
```

### Example 2: Test VM Cleanup

```bash
#!/bin/bash
# Clean up all test VMs

echo "Finding test VMs (prefix: test-*)..."
TEST_VMS=$(virsh -c qemu:///system list --all --name | grep "^test-")

if [ -z "$TEST_VMS" ]; then
    echo "No test VMs found"
    exit 0
fi

echo "Found VMs:"
echo "$TEST_VMS"
echo ""

read -p "Delete all these VMs? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    while IFS= read -r vm; do
        [ -z "$vm" ] && continue
        echo "Deleting $vm..."
        kcli delete vm "$vm" -y || true
    done <<< "$TEST_VMS"

    echo "✅ Cleanup complete!"
fi
```

## 🚀 Advanced: Script Templates

### For Different Use Cases

**Network Testing:**

```bash
cp TEMPLATE-new-script.sh test-network-custom.sh
# Edit to test network operations
```

**Storage Testing:**

```bash
cp TEMPLATE-new-script.sh test-storage-pool.sh
# Edit to test storage operations
```

**Performance Testing:**

```bash
cp TEMPLATE-new-script.sh test-vm-performance.sh
# Edit to test VM performance
```

## 📞 Getting Help

### From AI Assistant

Go to http://localhost:8888/ai-assistant and ask:

```
"I want to create a test script that [does X].
 Can you help me based on the template?"

"How do I test [Y] before adding it to a DAG?"

"Show me an example script that tests [Z]"
```

### From Documentation

```bash
# Read template
cat scripts/TEMPLATE-new-script.sh

# Read examples
cat scripts/test-kcli-create-vm.sh

# Read this guide
cat scripts/HOW-TO-ADD-SCRIPTS.md
```

## ✅ Summary

**Adding scripts is easy:**

1. Copy template (1 command)
1. Edit 3 sections (2 minutes)
1. Test it (30 seconds)

**RAG awareness happens through:**

1. Clear documentation in scripts
1. Updates to README.md
1. Companion markdown docs
1. Consistent naming patterns

**The AI Assistant will know about your scripts when:**

- You reference them in conversations
- They're well-documented
- They're in the scripts/ directory
- They follow naming conventions

**Start creating your own scripts now!** 🎯
