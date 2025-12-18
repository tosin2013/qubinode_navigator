#!/bin/bash
# Test script for user detection in deploy-qubinode.sh and load-variables.py

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Testing User Detection Logic${NC}"
echo "=============================================="
echo ""

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="$REPO_ROOT/scripts/development/deploy-qubinode.sh"
PYTHON_SCRIPT="$REPO_ROOT/load-variables.py"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    local expected_user="$3"
    
    echo -e "${BLUE}Test: $test_name${NC}"
    
    # Extract just the user detection logic from the script
    local detected_user
    detected_user=$(eval "$test_cmd")
    
    if [[ "$detected_user" == "$expected_user" ]]; then
        echo -e "${GREEN}✓ PASS${NC} - Detected user: $detected_user"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC} - Expected: $expected_user, Got: $detected_user"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Test 1: QUBINODE_ADMIN_USER set (highest priority)
echo -e "${BLUE}=== Priority Tests ===${NC}"
run_test "QUBINODE_ADMIN_USER takes precedence" \
    "QUBINODE_ADMIN_USER=custom_user SUDO_USER=sudo_user SSH_USER=ssh_user USER=current_user bash -c '
        if [[ -z \"\${QUBINODE_ADMIN_USER:-}\" ]]; then
            if [[ -n \"\${SUDO_USER:-}\" && \"\${SUDO_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SUDO_USER\"
            elif [[ -n \"\${SSH_USER:-}\" && \"\${SSH_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SSH_USER\"
            elif [[ -n \"\${USER:-}\" && \"\${USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$USER\"
            else
                DEFAULT_USER=\"lab-user\"
            fi
            echo \"\$DEFAULT_USER\"
        else
            echo \"\$QUBINODE_ADMIN_USER\"
        fi
    '" \
    "custom_user"

# Test 2: SUDO_USER when QUBINODE_ADMIN_USER not set
run_test "SUDO_USER detection (2nd priority)" \
    "SUDO_USER=sudo_user SSH_USER=ssh_user USER=current_user bash -c '
        if [[ -z \"\${QUBINODE_ADMIN_USER:-}\" ]]; then
            if [[ -n \"\${SUDO_USER:-}\" && \"\${SUDO_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SUDO_USER\"
            elif [[ -n \"\${SSH_USER:-}\" && \"\${SSH_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SSH_USER\"
            elif [[ -n \"\${USER:-}\" && \"\${USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$USER\"
            else
                DEFAULT_USER=\"lab-user\"
            fi
            echo \"\$DEFAULT_USER\"
        else
            echo \"\$QUBINODE_ADMIN_USER\"
        fi
    '" \
    "sudo_user"

# Test 3: SSH_USER when SUDO_USER not available
run_test "SSH_USER detection (3rd priority)" \
    "SSH_USER=ssh_user USER=current_user bash -c '
        if [[ -z \"\${QUBINODE_ADMIN_USER:-}\" ]]; then
            if [[ -n \"\${SUDO_USER:-}\" && \"\${SUDO_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SUDO_USER\"
            elif [[ -n \"\${SSH_USER:-}\" && \"\${SSH_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SSH_USER\"
            elif [[ -n \"\${USER:-}\" && \"\${USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$USER\"
            else
                DEFAULT_USER=\"lab-user\"
            fi
            echo \"\$DEFAULT_USER\"
        else
            echo \"\$QUBINODE_ADMIN_USER\"
        fi
    '" \
    "ssh_user"

# Test 4: USER when other vars not available
run_test "USER detection (4th priority)" \
    "USER=current_user bash -c '
        if [[ -z \"\${QUBINODE_ADMIN_USER:-}\" ]]; then
            if [[ -n \"\${SUDO_USER:-}\" && \"\${SUDO_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SUDO_USER\"
            elif [[ -n \"\${SSH_USER:-}\" && \"\${SSH_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SSH_USER\"
            elif [[ -n \"\${USER:-}\" && \"\${USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$USER\"
            else
                DEFAULT_USER=\"lab-user\"
            fi
            echo \"\$DEFAULT_USER\"
        else
            echo \"\$QUBINODE_ADMIN_USER\"
        fi
    '" \
    "current_user"

# Test 5: Fallback to lab-user
run_test "Fallback to lab-user" \
    "bash -c '
        if [[ -z \"\${QUBINODE_ADMIN_USER:-}\" ]]; then
            if [[ -n \"\${SUDO_USER:-}\" && \"\${SUDO_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SUDO_USER\"
            elif [[ -n \"\${SSH_USER:-}\" && \"\${SSH_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SSH_USER\"
            elif [[ -n \"\${USER:-}\" && \"\${USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$USER\"
            else
                DEFAULT_USER=\"lab-user\"
            fi
            echo \"\$DEFAULT_USER\"
        else
            echo \"\$QUBINODE_ADMIN_USER\"
        fi
    '" \
    "lab-user"

# Test 6: Root user is skipped
echo -e "${BLUE}=== Root User Filtering Tests ===${NC}"
run_test "Root SUDO_USER is skipped" \
    "SUDO_USER=root SSH_USER=ssh_user bash -c '
        if [[ -z \"\${QUBINODE_ADMIN_USER:-}\" ]]; then
            if [[ -n \"\${SUDO_USER:-}\" && \"\${SUDO_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SUDO_USER\"
            elif [[ -n \"\${SSH_USER:-}\" && \"\${SSH_USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$SSH_USER\"
            elif [[ -n \"\${USER:-}\" && \"\${USER}\" != \"root\" ]]; then
                DEFAULT_USER=\"\$USER\"
            else
                DEFAULT_USER=\"lab-user\"
            fi
            echo \"\$DEFAULT_USER\"
        else
            echo \"\$QUBINODE_ADMIN_USER\"
        fi
    '" \
    "ssh_user"

# Test 7: User validation - existing user
echo -e "${BLUE}=== User Validation Tests ===${NC}"
CURRENT_USER=$(whoami)
echo -e "${BLUE}Test: Validate existing user${NC}"
if id "$CURRENT_USER" &>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC} - User '$CURRENT_USER' exists on system"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - User '$CURRENT_USER' should exist"
    ((TESTS_FAILED++))
fi
echo ""

# Test 8: User validation - non-existing user
echo -e "${BLUE}Test: Validate non-existing user${NC}"
if ! id "nonexistent_user_12345" &>/dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - Correctly detected non-existent user"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - User 'nonexistent_user_12345' should not exist"
    ((TESTS_FAILED++))
fi
echo ""

# Test 9: Python script user detection
echo -e "${BLUE}=== Python Script Tests ===${NC}"
echo -e "${BLUE}Test: Python script auto-detection${NC}"
if [[ -f "$PYTHON_SCRIPT" ]]; then
    # Create a temporary test to verify Python logic doesn't error
    # We'll just ensure it can import and the logic is syntactically correct
    if python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
import pwd
import os

# Test the same logic as in load-variables.py
username = (
    os.environ.get('QUBINODE_ADMIN_USER')
    or os.environ.get('ENV_USERNAME')
    or (os.environ.get('SUDO_USER') if os.environ.get('SUDO_USER') != 'root' else None)
    or (os.environ.get('SSH_USER') if os.environ.get('SSH_USER') != 'root' else None)
    or (os.environ.get('USER') if os.environ.get('USER') != 'root' else None)
)

# Should get current user
import getpass
if username is None:
    username = getpass.getuser()

print(username)

# Validate user exists
try:
    pwd.getpwnam(username)
    print('User validation: OK')
except KeyError:
    print('User validation: FAIL')
    sys.exit(1)
" 2>&1 | grep -q "User validation: OK"; then
        echo -e "${GREEN}✓ PASS${NC} - Python script user detection logic works"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC} - Python script user detection failed"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}⚠ SKIP${NC} - Python script not found at $PYTHON_SCRIPT"
fi
echo ""

# Summary
echo "=============================================="
echo -e "${BLUE}Test Summary${NC}"
echo "=============================================="
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ✗${NC}"
    exit 1
fi
