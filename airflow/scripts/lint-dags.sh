#!/bin/bash
# =============================================================================
# DAG Linting Script
# =============================================================================
# Issue #5 Fix: Check for common DAG issues including escape sequences
#
# Checks:
# 1. Complex escape sequences in SSH commands
# 2. Non-SSH kcli/virsh commands (ADR-0046 compliance)
# 3. Python syntax errors
# 4. Missing required imports
#
# Usage: ./lint-dags.sh [dag_file]
# =============================================================================

set -euo pipefail

DAGS_DIR="${1:-/opt/airflow/dags}"
ERRORS=0
WARNINGS=0

echo "========================================"
echo "DAG Linting"
echo "========================================"
echo "Directory: $DAGS_DIR"
echo ""

# If a single file is provided, lint just that file
if [[ -f "$DAGS_DIR" ]]; then
    FILES="$DAGS_DIR"
else
    FILES=$(find "$DAGS_DIR" -maxdepth 1 -name "*.py" -type f 2>/dev/null | sort)
fi

for dag_file in $FILES; do
    filename=$(basename "$dag_file")

    # Skip __pycache__ and other special files
    [[ "$filename" == "__"* ]] && continue
    [[ "$filename" == "."* ]] && continue

    echo "Checking: $filename"

    # ==========================================================================
    # Check 1: Python syntax
    # ==========================================================================
    if ! python3 -c "import ast; ast.parse(open('$dag_file').read())" 2>/dev/null; then
        echo "  [ERROR] Python syntax error"
        ERRORS=$((ERRORS + 1))
    fi

    # ==========================================================================
    # Check 2: Complex escape sequences in SSH commands
    # ==========================================================================
    # Look for patterns like \\\\$ or \\\\\ which indicate over-escaping
    if grep -qE '\\\\\\\\[\$\\"]' "$dag_file" 2>/dev/null; then
        echo "  [ERROR] Complex escape sequences found in SSH commands"
        echo "         Use single quotes for SSH remote commands instead"
        echo "         Pattern: ssh root@localhost 'command with \$VAR'"
        ERRORS=$((ERRORS + 1))
    fi

    # ==========================================================================
    # Check 3: Non-SSH kcli/virsh commands (ADR-0046 compliance)
    # ==========================================================================
    # Look for kcli or virsh commands that are NOT inside an SSH context
    if grep -E '^\s*(kcli|virsh)\s+' "$dag_file" 2>/dev/null | grep -vq 'ssh.*kcli\|ssh.*virsh'; then
        # Check if this is actually in a bash_command block without SSH
        if grep -B5 -E '^\s*(kcli|virsh)\s+' "$dag_file" 2>/dev/null | grep -qE 'bash_command'; then
            # Verify it's not wrapped in SSH
            context=$(grep -B10 -A2 -E '^\s*(kcli|virsh)\s+' "$dag_file" 2>/dev/null | head -20)
            if ! echo "$context" | grep -qE 'ssh.*-o|ssh.*root@'; then
                echo "  [WARN] kcli/virsh command may not be using SSH (ADR-0046)"
                echo "         Wrap kcli/virsh commands with SSH for host execution"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
    fi

    # ==========================================================================
    # Check 4: Triple single quotes in bash_command (should use triple double)
    # ==========================================================================
    # Per ADR-0045: Use """ (triple double quotes) for bash_command, never '''
    if grep -qE "bash_command='''" "$dag_file" 2>/dev/null; then
        echo "  [ERROR] bash_command uses triple single quotes"
        echo "         Per ADR-0045, use triple double quotes: bash_command=\"\"\""
        ERRORS=$((ERRORS + 1))
    fi

    # ==========================================================================
    # Check 5: Non-ASCII characters in bash commands
    # ==========================================================================
    # Per ADR-0045: ASCII-only characters in bash commands
    if grep -P '[\x80-\xFF]' "$dag_file" 2>/dev/null | grep -qE 'bash_command'; then
        echo "  [WARN] Non-ASCII characters found in bash_command"
        echo "         Use ASCII alternatives: [OK], [ERROR], [WARN], [INFO]"
        WARNINGS=$((WARNINGS + 1))
    fi

    # ==========================================================================
    # Check 6: DAG ID matches filename
    # ==========================================================================
    # Per ADR-0045: DAG IDs must be snake_case matching filename
    expected_dag_id=$(basename "$dag_file" .py)
    if grep -qE "DAG\s*\(" "$dag_file"; then
        actual_dag_id=$(grep -oP "DAG\s*\(\s*['\"]\\K[^'\"]*" "$dag_file" 2>/dev/null | head -1)
        if [[ -n "$actual_dag_id" ]] && [[ "$actual_dag_id" != "$expected_dag_id" ]]; then
            echo "  [WARN] DAG ID '$actual_dag_id' doesn't match filename '$expected_dag_id'"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi

done

echo ""
echo "========================================"
echo "Linting Summary"
echo "========================================"
echo "Errors:   $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [[ $ERRORS -gt 0 ]]; then
    echo "[FAIL] Fix errors before deploying"
    exit 1
fi

if [[ $WARNINGS -gt 0 ]]; then
    echo "[WARN] Review warnings for best practices"
fi

echo "[OK] Linting passed"
exit 0
