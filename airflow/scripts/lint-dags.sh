#!/bin/bash
# =============================================================================
# DAG Linting Script
# =============================================================================
# Comprehensive DAG linting with Airflow-specific tools and custom checks.
#
# Checks:
# 1. Python syntax validation
# 2. pylint-airflow (if available) - Airflow-specific checks
# 3. airflint (if available) - Best practices enforcement
# 4. Complex escape sequences in SSH commands
# 5. Non-SSH kcli/virsh commands (ADR-0046 compliance)
# 6. DAG ID matches filename (ADR-0045)
# 7. Non-ASCII characters in bash commands
#
# Usage: ./lint-dags.sh [dag_file_or_directory]
# =============================================================================

set -euo pipefail

DAGS_DIR="${1:-/opt/airflow/dags}"
ERRORS=0
WARNINGS=0

# Colors (disable if not in terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

echo "========================================"
echo "DAG Linting (Qubinode)"
echo "========================================"
echo "Directory: $DAGS_DIR"
echo ""

# Check for available linting tools
PYLINT_AIRFLOW_AVAILABLE=false
AIRFLINT_AVAILABLE=false

if command -v pylint &>/dev/null && python3 -c "import pylint_airflow" 2>/dev/null; then
    PYLINT_AIRFLOW_AVAILABLE=true
    echo "[INFO] pylint-airflow available"
fi

if command -v airflint &>/dev/null; then
    AIRFLINT_AVAILABLE=true
    echo "[INFO] airflint available"
fi

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
    # Skip helper modules (not actual DAGs)
    [[ "$filename" == "dag_helpers.py" ]] && continue
    [[ "$filename" == "dag_factory.py" ]] && continue
    [[ "$filename" == "dag_loader.py" ]] && continue
    [[ "$filename" == "dag_logging_mixin.py" ]] && continue

    echo "Checking: $filename"

    # ==========================================================================
    # Check 1: Python syntax
    # ==========================================================================
    if ! python3 -c "import ast; ast.parse(open('$dag_file').read())" 2>/dev/null; then
        echo -e "  ${RED}[ERROR]${NC} Python syntax error"
        python3 -c "import ast; ast.parse(open('$dag_file').read())" 2>&1 | head -5 || true
        ERRORS=$((ERRORS + 1))
    fi

    # ==========================================================================
    # Check 2: pylint-airflow (Airflow-specific checks)
    # ==========================================================================
    if $PYLINT_AIRFLOW_AVAILABLE; then
        # Run pylint with airflow plugin, only errors
        pylint_output=$(pylint --load-plugins=pylint_airflow --errors-only --disable=all --enable=E83 "$dag_file" 2>/dev/null || true)
        if [[ -n "$pylint_output" ]]; then
            echo -e "  ${YELLOW}[WARN]${NC} pylint-airflow issues:"
            echo "$pylint_output" | sed 's/^/         /'
            WARNINGS=$((WARNINGS + 1))
        fi
    fi

    # ==========================================================================
    # Check 3: airflint (best practices)
    # ==========================================================================
    if $AIRFLINT_AVAILABLE; then
        airflint_output=$(airflint "$dag_file" 2>/dev/null || true)
        if [[ -n "$airflint_output" ]] && [[ "$airflint_output" != *"No issues"* ]]; then
            echo -e "  ${YELLOW}[WARN]${NC} airflint suggestions:"
            echo "$airflint_output" | sed 's/^/         /'
            WARNINGS=$((WARNINGS + 1))
        fi
    fi

    # ==========================================================================
    # Check 4: Complex escape sequences in SSH commands
    # ==========================================================================
    # Look for patterns like \\\\$ or \\\\\ which indicate over-escaping
    if grep -qE '\\\\\\\\[\$\\"]' "$dag_file" 2>/dev/null; then
        echo -e "  ${RED}[ERROR]${NC} Complex escape sequences found in SSH commands"
        echo "         Use single quotes for SSH remote commands instead"
        echo "         Pattern: ssh root@localhost 'command with \$VAR'"
        ERRORS=$((ERRORS + 1))
    fi

    # ==========================================================================
    # Check 5: Non-SSH kcli/virsh commands (ADR-0046 compliance)
    # ==========================================================================
    # Look for kcli or virsh commands that are NOT inside an SSH context
    if grep -E '^\s*(kcli|virsh)\s+' "$dag_file" 2>/dev/null | grep -vq 'ssh.*kcli\|ssh.*virsh'; then
        # Check if this is actually in a bash_command block without SSH
        if grep -B5 -E '^\s*(kcli|virsh)\s+' "$dag_file" 2>/dev/null | grep -qE 'bash_command'; then
            # Verify it's not wrapped in SSH
            context=$(grep -B10 -A2 -E '^\s*(kcli|virsh)\s+' "$dag_file" 2>/dev/null | head -20)
            if ! echo "$context" | grep -qE 'ssh.*-o|ssh.*root@'; then
                echo -e "  ${YELLOW}[WARN]${NC} kcli/virsh command may not be using SSH (ADR-0046)"
                echo "         Wrap kcli/virsh commands with SSH for host execution"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
    fi

    # ==========================================================================
    # Check 6: Non-ASCII characters in bash commands
    # ==========================================================================
    # Per ADR-0045: ASCII-only characters in bash commands
    if grep -P '[\x80-\xFF]' "$dag_file" 2>/dev/null | grep -qE 'bash_command'; then
        echo -e "  ${YELLOW}[WARN]${NC} Non-ASCII characters found in bash_command"
        echo "         Use ASCII alternatives: [OK], [ERROR], [WARN], [INFO]"
        WARNINGS=$((WARNINGS + 1))
    fi

    # ==========================================================================
    # Check 7: DAG ID matches filename
    # ==========================================================================
    # Per ADR-0045: DAG IDs must be snake_case matching filename
    expected_dag_id=$(basename "$dag_file" .py)
    if grep -qE "DAG\s*\(" "$dag_file" 2>/dev/null; then
        actual_dag_id=$(grep -oP "DAG\s*\(\s*['\"]\\K[^'\"]*" "$dag_file" 2>/dev/null | head -1 || echo "")
        if [[ -n "$actual_dag_id" ]] && [[ "$actual_dag_id" != "$expected_dag_id" ]]; then
            echo -e "  ${YELLOW}[WARN]${NC} DAG ID '$actual_dag_id' doesn't match filename '$expected_dag_id'"
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

# Show tool availability status
echo "Linting tools:"
if $PYLINT_AIRFLOW_AVAILABLE; then
    echo -e "  ${GREEN}[OK]${NC} pylint-airflow"
else
    echo -e "  ${YELLOW}[SKIP]${NC} pylint-airflow (install: pip install pylint-airflow)"
fi
if $AIRFLINT_AVAILABLE; then
    echo -e "  ${GREEN}[OK]${NC} airflint"
else
    echo -e "  ${YELLOW}[SKIP]${NC} airflint (install: pip install airflint)"
fi
echo ""

if [[ $ERRORS -gt 0 ]]; then
    echo -e "${RED}[FAIL]${NC} Fix errors before deploying"
    exit 1
fi

if [[ $WARNINGS -gt 0 ]]; then
    echo -e "${YELLOW}[WARN]${NC} Review warnings for best practices"
fi

echo -e "${GREEN}[OK]${NC} Linting passed"
exit 0
