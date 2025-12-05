#!/bin/bash
# =============================================================================
# DAG Validation Script
# =============================================================================
# ADR-0046: DAG Validation Pipeline and Host-Based Execution Strategy
#
# Quick local validation for developers before commit.
# Uses the same Python DagBag API approach as GitHub Actions CI.
#
# Usage: ./validate-dag.sh <dag_file.py>
#        ./validate-dag.sh airflow/dags/        # Validate all DAGs in directory
#
# This script performs:
#   1. Python syntax check (fast)
#   2. Airflow DagBag import validation (Airflow recommended approach)
#   3. ADR compliance checks via lint-dags.sh
#
# For comprehensive validation, see: .github/workflows/airflow-validate.yml
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-}"

# Colors (disable if not in terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

function usage() {
    echo "DAG Validation Script (ADR-0046)"
    echo ""
    echo "Usage: $0 <dag_file.py|dag_directory>"
    echo ""
    echo "Validates Airflow DAG files for common issues:"
    echo "  - Python syntax errors"
    echo "  - Airflow import errors (using DagBag API)"
    echo "  - ADR-0045/0046 compliance (via lint-dags.sh)"
    echo ""
    echo "Examples:"
    echo "  $0 airflow/dags/freeipa_deployment.py"
    echo "  $0 airflow/dags/"
    echo ""
    echo "For comprehensive CI validation, see:"
    echo "  .github/workflows/airflow-validate.yml"
    exit 1
}

if [[ -z "$TARGET" ]]; then
    usage
fi

if [[ ! -e "$TARGET" ]]; then
    echo -e "${RED}[ERROR]${NC} Path not found: $TARGET"
    exit 1
fi

echo "========================================"
echo "DAG Validation (ADR-0046)"
echo "========================================"
echo ""

TOTAL_ERRORS=0
TOTAL_WARNINGS=0
VALIDATED_COUNT=0

# Determine files to validate
if [[ -d "$TARGET" ]]; then
    FILES=$(find "$TARGET" -maxdepth 1 -name "*.py" -type f 2>/dev/null | sort)
    echo -e "${BLUE}[INFO]${NC} Validating directory: $TARGET"
else
    FILES="$TARGET"
    echo -e "${BLUE}[INFO]${NC} Validating file: $TARGET"
fi

echo ""

for dag_file in $FILES; do
    filename=$(basename "$dag_file")

    # Skip non-DAG files
    [[ "$filename" == "__"* ]] && continue
    [[ "$filename" == "."* ]] && continue
    [[ "$filename" == "dag_helpers.py" ]] && continue
    [[ "$filename" == "dag_factory.py" ]] && continue
    [[ "$filename" == "dag_loader.py" ]] && continue
    [[ "$filename" == "dag_logging_mixin.py" ]] && continue

    echo "----------------------------------------"
    echo "File: $filename"
    echo "----------------------------------------"

    ERRORS=0
    WARNINGS=0

    # =========================================================================
    # Check 1: Python Syntax (Fast)
    # =========================================================================
    echo -n "[1/3] Python syntax... "
    if python3 -c "import ast; ast.parse(open('$dag_file').read())" 2>/dev/null; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo "  Details:"
        python3 -c "import ast; ast.parse(open('$dag_file').read())" 2>&1 | sed 's/^/    /' || true
        ERRORS=$((ERRORS + 1))
    fi

    # =========================================================================
    # Check 2: Airflow DagBag Import (Airflow Recommended Approach)
    # =========================================================================
    echo -n "[2/3] DagBag import... "

    # Check if Airflow is installed
    if ! python3 -c "import airflow" 2>/dev/null; then
        echo -e "${YELLOW}SKIPPED${NC} (airflow not installed)"
        echo "  Install with: pip install apache-airflow"
    else
        DAGBAG_RESULT=$(python3 << PYTHON_SCRIPT 2>&1
import sys
import os

# Set up minimal Airflow environment
os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'false')
os.environ.setdefault('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', 'sqlite:////tmp/airflow_validate.db')

from airflow.models import DagBag

dag_dir = os.path.dirname('$dag_file') or '.'
dagbag = DagBag(dag_dir, include_examples=False)

# Check for import errors with proper classification
# This matches the CI workflow approach
if dagbag.import_errors:
    non_duplicate_errors = []
    duplicate_warnings = []

    for filepath, error in dagbag.import_errors.items():
        error_str = str(error)
        if "DuplicatedIdException" in error_str:
            # Known issue - multiple files may define same DAG ID
            duplicate_warnings.append(os.path.basename(filepath))
        else:
            non_duplicate_errors.append((os.path.basename(filepath), error_str[:200]))

    if duplicate_warnings:
        print(f"WARN_DUPLICATES:{len(duplicate_warnings)}")

    if non_duplicate_errors:
        print("ERROR")
        for filepath, error in non_duplicate_errors:
            print(f"  {filepath}: {error}")
        sys.exit(1)
    else:
        print("OK")
else:
    print("OK")
PYTHON_SCRIPT
)
        if echo "$DAGBAG_RESULT" | grep -q "^ERROR"; then
            echo -e "${RED}FAILED${NC}"
            echo "$DAGBAG_RESULT" | grep -v "^ERROR" | sed 's/^/    /'
            ERRORS=$((ERRORS + 1))
        elif echo "$DAGBAG_RESULT" | grep -q "^WARN_DUPLICATES"; then
            DUPE_COUNT=$(echo "$DAGBAG_RESULT" | grep "^WARN_DUPLICATES" | cut -d: -f2)
            echo -e "${GREEN}OK${NC} ${YELLOW}(${DUPE_COUNT} duplicate DAG ID warnings)${NC}"
            WARNINGS=$((WARNINGS + 1))
        elif echo "$DAGBAG_RESULT" | grep -q "^OK"; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${YELLOW}UNKNOWN${NC}"
            echo "  $DAGBAG_RESULT"
        fi
    fi

    # =========================================================================
    # Check 3: ADR Compliance (lint-dags.sh)
    # =========================================================================
    echo -n "[3/3] ADR compliance... "

    if [[ -x "$SCRIPT_DIR/lint-dags.sh" ]]; then
        # Run lint-dags.sh and capture result
        LINT_OUTPUT=$("$SCRIPT_DIR/lint-dags.sh" "$dag_file" 2>&1) || LINT_EXIT=$?
        LINT_EXIT=${LINT_EXIT:-0}

        if [[ $LINT_EXIT -eq 0 ]]; then
            # Check for warnings in output
            if echo "$LINT_OUTPUT" | grep -q "Warnings:   0"; then
                echo -e "${GREEN}OK${NC}"
            else
                WARN_COUNT=$(echo "$LINT_OUTPUT" | grep "Warnings:" | awk '{print $2}')
                echo -e "${GREEN}OK${NC} ${YELLOW}(${WARN_COUNT} warnings)${NC}"
                WARNINGS=$((WARNINGS + 1))
            fi
        else
            echo -e "${RED}FAILED${NC}"
            # Show relevant error lines
            echo "$LINT_OUTPUT" | grep -E "\[ERROR\]|\[WARN\]" | head -10 | sed 's/^/    /'
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "${YELLOW}SKIPPED${NC} (lint-dags.sh not found)"
    fi

    echo ""
    TOTAL_ERRORS=$((TOTAL_ERRORS + ERRORS))
    TOTAL_WARNINGS=$((TOTAL_WARNINGS + WARNINGS))
    VALIDATED_COUNT=$((VALIDATED_COUNT + 1))
done

# Summary
echo "========================================"
echo "Validation Summary"
echo "========================================"
echo "  Files validated: $VALIDATED_COUNT"
echo "  Errors:          $TOTAL_ERRORS"
echo "  Warnings:        $TOTAL_WARNINGS"
echo ""

if [[ $TOTAL_ERRORS -eq 0 ]]; then
    if [[ $TOTAL_WARNINGS -eq 0 ]]; then
        echo -e "${GREEN}[OK]${NC} All validations passed"
    else
        echo -e "${GREEN}[OK]${NC} Passed with warnings"
        echo ""
        echo "Review warnings for best practices (ADR-0045/0046)"
    fi
    echo ""
    echo "Next steps:"
    echo "  - Test locally: airflow dags test <dag_id> 2025-01-01"
    echo "  - CI will run comprehensive validation on PR"
    exit 0
else
    echo -e "${RED}[FAIL]${NC} Validation failed"
    echo ""
    echo "Please fix the errors above before committing."
    echo "See ADR-0045 and ADR-0046 for DAG development standards."
    exit 1
fi
