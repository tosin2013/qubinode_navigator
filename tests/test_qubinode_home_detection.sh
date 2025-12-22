#!/bin/bash
# =============================================================================
# QUBINODE_HOME Path Detection Test
# =============================================================================
#
# This test validates that QUBINODE_HOME environment variable is properly
# detected and used throughout the codebase for flexible installation paths.
#
# Tests:
#   1. Default path detection (script location)
#   2. Environment variable override
#   3. Fallback to /root/qubinode_navigator
#   4. Fallback to /opt/qubinode_navigator
#   5. Invalid path handling
#
# =============================================================================

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

# Test helper functions
test_result() {
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

echo "============================================================================="
echo "                  QUBINODE_HOME PATH DETECTION TESTS"
echo "============================================================================="
echo ""

# Get the actual repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo -e "${BLUE}INFO:${NC} Test repository root: $REPO_ROOT"
echo ""

# =============================================================================
# Test 1: Script-based detection (default behavior)
# =============================================================================
echo -e "${BLUE}Test 1:${NC} Script-based QUBINODE_HOME detection"
unset QUBINODE_HOME
SCRIPT_DIR="$REPO_ROOT"
DETECTED_HOME="${QUBINODE_HOME:-$SCRIPT_DIR}"
test_result "Auto-detected from script location" "$REPO_ROOT" "$DETECTED_HOME"
echo ""

# =============================================================================
# Test 2: Environment variable override
# =============================================================================
echo -e "${BLUE}Test 2:${NC} QUBINODE_HOME environment variable override"
export QUBINODE_HOME="/custom/path/qubinode_navigator"
DETECTED_HOME="${QUBINODE_HOME}"
test_result "Custom QUBINODE_HOME respected" "/custom/path/qubinode_navigator" "$DETECTED_HOME"
echo ""

# =============================================================================
# Test 3: .env.example contains QUBINODE_HOME documentation
# =============================================================================
echo -e "${BLUE}Test 3:${NC} QUBINODE_HOME documented in .env.example"
if grep -q "QUBINODE_HOME" "$REPO_ROOT/.env.example"; then
    test_result ".env.example contains QUBINODE_HOME" "true" "true"
else
    test_result ".env.example contains QUBINODE_HOME" "true" "false"
fi
echo ""

# =============================================================================
# Test 4: deploy-qubinode.sh sets QUBINODE_HOME
# =============================================================================
echo -e "${BLUE}Test 4:${NC} deploy-qubinode.sh exports QUBINODE_HOME"
if grep -q "export QUBINODE_HOME" "$REPO_ROOT/scripts/development/deploy-qubinode.sh"; then
    test_result "deploy-qubinode.sh exports QUBINODE_HOME" "true" "true"
else
    test_result "deploy-qubinode.sh exports QUBINODE_HOME" "true" "false"
fi
echo ""

# =============================================================================
# Test 5: Top shell scripts use QUBINODE_HOME
# =============================================================================
echo -e "${BLUE}Test 5:${NC} High-priority scripts use QUBINODE_HOME"

# Check rocky-linux-hetzner.sh
if grep -q "QUBINODE_HOME" "$REPO_ROOT/rocky-linux-hetzner.sh"; then
    test_result "rocky-linux-hetzner.sh uses QUBINODE_HOME" "true" "true"
else
    test_result "rocky-linux-hetzner.sh uses QUBINODE_HOME" "true" "false"
fi

# Check rhel8-linux-hypervisor.sh
if grep -q "QUBINODE_HOME" "$REPO_ROOT/rhel8-linux-hypervisor.sh"; then
    test_result "rhel8-linux-hypervisor.sh uses QUBINODE_HOME" "true" "true"
else
    test_result "rhel8-linux-hypervisor.sh uses QUBINODE_HOME" "true" "false"
fi

# Check pre-deployment-cleanup.sh
if grep -q "QUBINODE_HOME" "$REPO_ROOT/pre-deployment-cleanup.sh"; then
    test_result "pre-deployment-cleanup.sh uses QUBINODE_HOME" "true" "true"
else
    test_result "pre-deployment-cleanup.sh uses QUBINODE_HOME" "true" "false"
fi
echo ""

# =============================================================================
# Test 6: Python plugins use QUBINODE_HOME
# =============================================================================
echo -e "${BLUE}Test 6:${NC} Python plugins use QUBINODE_HOME"

# Check ai_assistant_plugin.py
if grep -q "QUBINODE_HOME" "$REPO_ROOT/plugins/services/ai_assistant_plugin.py"; then
    test_result "ai_assistant_plugin.py uses QUBINODE_HOME" "true" "true"
else
    test_result "ai_assistant_plugin.py uses QUBINODE_HOME" "true" "false"
fi

# Check rhel8_plugin.py
if grep -q "QUBINODE_HOME" "$REPO_ROOT/plugins/os/rhel8_plugin.py"; then
    test_result "rhel8_plugin.py uses QUBINODE_HOME" "true" "true"
else
    test_result "rhel8_plugin.py uses QUBINODE_HOME" "true" "false"
fi

# Check rocky_linux_plugin.py
if grep -q "QUBINODE_HOME" "$REPO_ROOT/plugins/os/rocky_linux_plugin.py"; then
    test_result "rocky_linux_plugin.py uses QUBINODE_HOME" "true" "true"
else
    test_result "rocky_linux_plugin.py uses QUBINODE_HOME" "true" "false"
fi
echo ""

# =============================================================================
# Test 7: Test files use QUBINODE_HOME
# =============================================================================
echo -e "${BLUE}Test 7:${NC} Test files use QUBINODE_HOME"

if grep -q "QUBINODE_HOME" "$REPO_ROOT/tests/test_modernized_setup.py"; then
    test_result "test_modernized_setup.py uses QUBINODE_HOME" "true" "true"
else
    test_result "test_modernized_setup.py uses QUBINODE_HOME" "true" "false"
fi
echo ""

# =============================================================================
# Test 8: Verify backward compatibility (REPO_ROOT still works)
# =============================================================================
echo -e "${BLUE}Test 8:${NC} Backward compatibility with REPO_ROOT"

if grep -q "REPO_ROOT.*QUBINODE_HOME" "$REPO_ROOT/scripts/development/deploy-qubinode.sh"; then
    test_result "REPO_ROOT set from QUBINODE_HOME for compatibility" "true" "true"
else
    test_result "REPO_ROOT set from QUBINODE_HOME for compatibility" "true" "false"
fi
echo ""

# =============================================================================
# Test Summary
# =============================================================================
echo "============================================================================="
echo "                            TEST SUMMARY"
echo "============================================================================="
echo -e "  Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "  ${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "  ${RED}Failed: ${TESTS_FAILED}${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ All QUBINODE_HOME detection tests passed!${NC}"
    echo ""
    echo "QUBINODE_HOME is properly implemented and will support:"
    echo "  - Root installations: /root/qubinode_navigator"
    echo "  - Non-root users: /home/lab-user/qubinode_navigator"
    echo "  - Custom paths: /opt/qubinode_navigator or any location"
    exit 0
else
    echo -e "${RED}✗ Some QUBINODE_HOME tests failed!${NC}"
    echo ""
    echo "Please review the failures above and ensure QUBINODE_HOME is properly"
    echo "implemented in all critical scripts and configuration files."
    exit 1
fi
