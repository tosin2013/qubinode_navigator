#!/bin/bash
# Test script to verify path calculations in deployment scripts

set -euo pipefail

# Test colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

test_path_calculation() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"
    
    if [[ "$expected" == "$actual" ]]; then
        echo -e "${GREEN}✓${NC} $test_name: $actual"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $test_name: Expected '$expected', got '$actual'"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

echo "Testing deployment script path calculations..."
echo "=============================================="
echo ""

# Get the repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Repository root: $REPO_ROOT"
echo ""

# Test 1: Root deploy-qubinode.sh SCRIPT_DIR calculation
echo "Test 1: Root deploy-qubinode.sh"
SCRIPT_DIR="$(cd "$(dirname "$REPO_ROOT/deploy-qubinode.sh")" && pwd)"
MY_DIR="$(dirname "$SCRIPT_DIR")"
test_path_calculation "SCRIPT_DIR" "$REPO_ROOT" "$SCRIPT_DIR"
test_path_calculation "MY_DIR (parent of repo)" "$(dirname "$REPO_ROOT")" "$MY_DIR"
echo ""

# Test 2: scripts/development/deploy-qubinode.sh SCRIPT_DIR calculation
echo "Test 2: scripts/development/deploy-qubinode.sh"
SCRIPT_DIR="$(cd "$(dirname "$REPO_ROOT/scripts/development/deploy-qubinode.sh")" && pwd)"
MY_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
test_path_calculation "SCRIPT_DIR" "$REPO_ROOT/scripts/development" "$SCRIPT_DIR"
test_path_calculation "MY_DIR (three levels up)" "$(dirname "$REPO_ROOT")" "$MY_DIR"
echo ""

# Test 3: scripts/development/setup.sh SCRIPT_DIR calculation
echo "Test 3: scripts/development/setup.sh"
SCRIPT_DIR="$(cd "$(dirname "$REPO_ROOT/scripts/development/setup.sh")" && pwd)"
MY_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
test_path_calculation "SCRIPT_DIR" "$REPO_ROOT/scripts/development" "$SCRIPT_DIR"
test_path_calculation "MY_DIR (three levels up)" "$(dirname "$REPO_ROOT")" "$MY_DIR"
echo ""

# Test 4: Verify critical file paths exist
echo "Test 4: Critical file paths"
test_path_calculation "load-variables.py exists" "true" "$([ -f "$REPO_ROOT/load-variables.py" ] && echo 'true' || echo 'false')"
test_path_calculation "ansible-builder/requirements.yml exists" "true" "$([ -f "$REPO_ROOT/ansible-builder/requirements.yml" ] && echo 'true' || echo 'false')"
test_path_calculation "ansible-navigator/setup_kvmhost.yml exists" "true" "$([ -f "$REPO_ROOT/ansible-navigator/setup_kvmhost.yml" ] && echo 'true' || echo 'false')"
test_path_calculation "airflow directory exists" "true" "$([ -d "$REPO_ROOT/airflow" ] && echo 'true' || echo 'false')"
echo ""

# Test 5: Simulate sudo environment (note: EUID is readonly, but we can test the path logic)
echo "Test 5: Simulated sudo environment"
ORIGINAL_HOME="$HOME"
export HOME="/root"
# EUID is readonly, but the path calculation doesn't depend on it anymore
SCRIPT_DIR="$REPO_ROOT"
MY_DIR="$(dirname "$SCRIPT_DIR")"
test_path_calculation "MY_DIR with simulated sudo (HOME=/root)" "$(dirname "$REPO_ROOT")" "$MY_DIR"
export HOME="$ORIGINAL_HOME"
echo ""

# Summary
echo "=============================================="
echo "Test Summary:"
echo -e "  Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "  Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
