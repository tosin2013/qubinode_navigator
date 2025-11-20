#!/bin/bash
# Template for Creating New Test Scripts
# Copy this file and customize for your use case

# ============================================
# CONFIGURATION (Customize this section)
# ============================================

# Script name and description
SCRIPT_NAME="My Custom Test Script"
SCRIPT_DESC="Tests my custom kcli/virsh workflow"

# Default parameters (customize these)
PARAM1="${1:-default_value1}"
PARAM2="${2:-default_value2}"

# ============================================
# SCRIPT HEADER (Keep this pattern)
# ============================================

set -e  # Exit on error

echo "=========================================="
echo "$SCRIPT_NAME"
echo "=========================================="
echo "$SCRIPT_DESC"
echo ""
echo "Parameters:"
echo "  Param1: $PARAM1"
echo "  Param2: $PARAM2"
echo "=========================================="
echo ""

# Optional: Confirm before proceeding
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted by user"
    exit 0
fi

# ============================================
# YOUR TEST LOGIC (Customize this section)
# ============================================

# Step 1: Pre-check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Pre-check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# Add your pre-checks here
# Example: Check if image exists, verify resources, etc.
echo "Running pre-checks..."
echo "✅ Pre-checks passed"
echo ""

# Step 2: Main command
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Execute Main Command"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# Build your command
MY_COMMAND="kcli list vms"  # Replace with your command
echo "Command: $MY_COMMAND"
echo ""

# Execute the command
if eval "$MY_COMMAND"; then
    echo "✅ Command completed successfully"
else
    echo "❌ Command failed"
    exit 1
fi
echo ""

# Step 3: Verification
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Verify Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# Add verification logic
# Example: Check if VM was created, verify state, etc.
echo "Verifying results..."
echo "✅ Verification passed"
echo ""

# ============================================
# SUMMARY (Keep this pattern)
# ============================================

echo "=========================================="
echo "✅ $SCRIPT_NAME Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • All steps completed successfully"
echo "  • Results verified"
echo ""
echo "To use this in an Airflow DAG:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "from qubinode.operators import YourOperator"
echo ""
echo "task = YourOperator("
echo "    task_id='my_task',"
echo "    param1='$PARAM1',"
echo "    param2='$PARAM2',"
echo "    dag=dag"
echo ")"
echo ""

# ============================================
# HOW TO USE THIS TEMPLATE
# ============================================
# 
# 1. Copy this file:
#    cp TEMPLATE-new-script.sh my-custom-test.sh
#
# 2. Make it executable:
#    chmod +x my-custom-test.sh
#
# 3. Customize these sections:
#    - CONFIGURATION (lines 8-15)
#    - YOUR TEST LOGIC (lines 40-79)
#    - SUMMARY DAG code (lines 87-96)
#
# 4. Test your script:
#    ./my-custom-test.sh [param1] [param2]
#
# 5. Once working, add to DAG!
#
# ============================================
# BEST PRACTICES
# ============================================
#
# ✅ DO:
#   - Use clear step markers (━━━━━)
#   - Add verification steps
#   - Show exact commands before running
#   - Provide confirmation prompts
#   - Exit with proper codes (0=success, 1=error)
#   - Print DAG code example at end
#
# ❌ DON'T:
#   - Skip error handling (use set -e)
#   - Run destructive commands without confirmation
#   - Forget to verify results
#   - Mix test logic with production code
#
# ============================================
# EXAMPLES OF COMMON PATTERNS
# ============================================
#
# Pattern 1: Check if resource exists
# ------------------------------------
# if virsh -c qemu:///system dominfo "$VM_NAME" &>/dev/null; then
#     echo "✅ VM exists"
# else
#     echo "❌ VM not found"
#     exit 1
# fi
#
# Pattern 2: Loop with timeout
# ----------------------------
# MAX_WAIT=300
# ELAPSED=0
# while [ $ELAPSED -lt $MAX_WAIT ]; do
#     STATE=$(virsh -c qemu:///system domstate "$VM_NAME")
#     if [ "$STATE" = "running" ]; then
#         echo "✅ VM is running"
#         break
#     fi
#     sleep 10
#     ELAPSED=$((ELAPSED + 10))
# done
#
# Pattern 3: Parse kcli output
# ---------------------------
# VM_IP=$(kcli info vm "$VM_NAME" | grep "ip:" | awk '{print $2}')
# echo "VM IP: $VM_IP"
#
# Pattern 4: Multiple commands in sequence
# ----------------------------------------
# COMMANDS=(
#     "kcli list vms"
#     "virsh list --all"
#     "virsh net-list --all"
# )
# for cmd in "${COMMANDS[@]}"; do
#     echo "Running: $cmd"
#     eval "$cmd" || echo "⚠️  Command failed: $cmd"
# done
#
# ============================================
# RAG AWARENESS
# ============================================
#
# For AI Assistant to be aware of your script:
#
# 1. Add clear documentation at the top
# 2. Use consistent naming: test-<feature>-<action>.sh
# 3. Include usage examples in comments
# 4. Add to scripts/README.md
# 5. Optional: Create a markdown doc explaining it
#
# The AI Assistant will learn about scripts through:
# - File content (when user asks about them)
# - Documentation in README.md
# - Context from conversations
# - Markdown docs in airflow/ directory
#
# ============================================
