#!/bin/bash
# DAG Validation Script
# ADR-0046: DAG Validation Pipeline and Host-Based Execution Strategy
# Usage: ./validate-dag.sh <dag_file.py>

set -e

DAG_FILE="$1"

if [ -z "$DAG_FILE" ]; then
    echo "Usage: $0 <dag_file.py>"
    echo ""
    echo "Validates an Airflow DAG file for common issues:"
    echo "  - Python syntax errors"
    echo "  - Airflow import errors"
    echo "  - Unicode characters in bash commands"
    echo "  - String concatenation in bash_command"
    echo "  - Deprecated parameters"
    echo "  - PATH configuration for kcli/ansible"
    exit 1
fi

if [ ! -f "$DAG_FILE" ]; then
    echo "Error: File not found: $DAG_FILE"
    exit 1
fi

echo "========================================"
echo "DAG Validation: $DAG_FILE"
echo "========================================"
echo ""

ERRORS=0
WARNINGS=0

# 1. Python Syntax Check
echo -n "[1/7] Python syntax... "
if python3 -c "import ast; ast.parse(open('$DAG_FILE').read())" 2>/dev/null; then
    echo "OK"
else
    echo "FAILED"
    echo "  Details:"
    python3 -c "import ast; ast.parse(open('$DAG_FILE').read())" 2>&1 | sed 's/^/    /'
    ERRORS=$((ERRORS + 1))
fi

# 2. Airflow Import Check (if airflow is installed)
echo -n "[2/7] Airflow imports... "
if command -v python3 &>/dev/null && python3 -c "import airflow" 2>/dev/null; then
    IMPORT_CHECK=$(python3 -c "
import sys
import os
sys.path.insert(0, os.path.dirname('$DAG_FILE'))
from airflow.models import DagBag
db = DagBag(os.path.dirname('$DAG_FILE') or '.', include_examples=False)
if db.import_errors:
    for dag, error in db.import_errors.items():
        print(f'  {dag}: {error}')
    sys.exit(1)
" 2>&1)
    if [ $? -eq 0 ]; then
        echo "OK"
    else
        echo "FAILED"
        echo "$IMPORT_CHECK"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "SKIPPED (airflow not installed)"
fi

# 3. Unicode Character Check in bash_command blocks
echo -n "[3/7] Unicode in bash commands... "
# Extract bash_command content and check for non-ASCII
UNICODE_LINES=$(grep -n -P '[^\x00-\x7F]' "$DAG_FILE" 2>/dev/null | grep -v "^#" | head -5)
if [ -n "$UNICODE_LINES" ]; then
    echo "WARNING"
    echo "  Non-ASCII characters found (may cause bash parsing issues):"
    echo "$UNICODE_LINES" | sed 's/^/    /'
    WARNINGS=$((WARNINGS + 1))
else
    echo "OK"
fi

# 4. String Concatenation in bash_command Check
echo -n "[4/7] Bash command concatenation... "
if grep -E "'''\s*\+|\"\"\"\\s*\+" "$DAG_FILE" 2>/dev/null | grep -v "^#" > /dev/null; then
    echo "FAILED"
    echo "  String concatenation in bash_command breaks command parsing:"
    grep -n -E "'''\s*\+|\"\"\"\\s*\+" "$DAG_FILE" | head -5 | sed 's/^/    /'
    ERRORS=$((ERRORS + 1))
else
    echo "OK"
fi

# 5. Deprecated Parameters Check
echo -n "[5/7] Deprecated parameters... "
DEPRECATED=$(grep -n "schedule_interval\s*=" "$DAG_FILE" 2>/dev/null | head -3)
if [ -n "$DEPRECATED" ]; then
    echo "WARNING"
    echo "  Deprecated 'schedule_interval' found (use 'schedule' instead):"
    echo "$DEPRECATED" | sed 's/^/    /'
    WARNINGS=$((WARNINGS + 1))
else
    echo "OK"
fi

# 6. PATH Export Check (for container execution)
echo -n "[6/7] PATH configuration... "
if grep -qE "kcli|ansible-playbook|ansible-galaxy" "$DAG_FILE" 2>/dev/null; then
    if grep -q 'export PATH=' "$DAG_FILE" 2>/dev/null; then
        echo "OK"
    else
        echo "WARNING"
        echo "  DAG uses kcli/ansible but no PATH export found"
        echo "  Add: export PATH=\"/home/airflow/.local/bin:/usr/local/bin:\$PATH\""
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "OK (no kcli/ansible usage detected)"
fi

# 7. Triple Quote Consistency
echo -n "[7/7] Quote consistency... "
SINGLE_TRIPLE=$(grep -c "bash_command='''" "$DAG_FILE" 2>/dev/null || echo 0)
DOUBLE_TRIPLE=$(grep -c 'bash_command="""' "$DAG_FILE" 2>/dev/null || echo 0)
if [ "$SINGLE_TRIPLE" -gt 0 ] && [ "$DOUBLE_TRIPLE" -gt 0 ]; then
    echo "WARNING"
    echo "  Mixed triple quote styles found (''' and \"\"\")"
    echo "  Recommend using \"\"\" consistently per ADR-0045"
    WARNINGS=$((WARNINGS + 1))
else
    echo "OK"
fi

# Summary
echo ""
echo "========================================"
echo "Validation Summary"
echo "========================================"
echo "  Errors:   $ERRORS"
echo "  Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo "Result: PASSED"
    else
        echo "Result: PASSED with warnings"
    fi
    exit 0
else
    echo "Result: FAILED"
    echo ""
    echo "Please fix the errors above before deploying this DAG."
    echo "See ADR-0045 for DAG development standards."
    exit 1
fi
