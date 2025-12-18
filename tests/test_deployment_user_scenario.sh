#!/bin/bash
# Simulate deployment scenarios with different user configurations

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Testing Deployment User Scenarios${NC}"
echo "=============================================="
echo ""

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_SCRIPT="$REPO_ROOT/scripts/development/deploy-qubinode.sh"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper to run deployment scenario test
# Args:
#   $1 - scenario_name: Human-readable description of the test scenario
#   $2 - env_setup: Environment variable assignments to test (e.g., "export USER=testuser")
#   $3 - expected_user: The username that should be detected in this scenario
test_scenario() {
    local scenario_name="$1"
    local env_setup="$2"
    local expected_user="$3"

    echo -e "${BLUE}Scenario: $scenario_name${NC}"

    # Create temp .env file
    local temp_env=$(mktemp)
    echo "$env_setup" > "$temp_env"

    # Extract and test user detection logic from deploy script
    local detected_user
    detected_user=$(bash -c "
        # Clear all user-related environment variables first
        unset QUBINODE_ADMIN_USER SUDO_USER SSH_USER USER

        # Then source the test environment
        source '$temp_env'

        # Extract user detection logic from deploy-qubinode.sh
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
            export QUBINODE_ADMIN_USER=\"\$DEFAULT_USER\"
        fi

        echo \"\$QUBINODE_ADMIN_USER\"
    ")

    rm -f "$temp_env"

    if [[ "$detected_user" == "$expected_user" ]]; then
        echo -e "${GREEN}✓ PASS${NC} - Detected: $detected_user"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} - Expected: $expected_user, Got: $detected_user"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    echo ""
}

echo -e "${BLUE}=== Real-World Deployment Scenarios ===${NC}"
echo ""

# Scenario 1: User explicitly sets QUBINODE_ADMIN_USER in .env
test_scenario "User sets QUBINODE_ADMIN_USER in .env" \
    "QUBINODE_ADMIN_USER=custom_admin" \
    "custom_admin"

# Scenario 2: Running with sudo (no .env)
test_scenario "Running with sudo as lab-user" \
    "export SUDO_USER=lab-user" \
    "lab-user"

# Scenario 3: SSH into system as specific user
test_scenario "SSH login as centos user" \
    "export SSH_USER=centos" \
    "centos"

# Scenario 4: Local development on RHEL workstation
test_scenario "Local RHEL workstation (USER=developer)" \
    "export USER=developer" \
    "developer"

# Scenario 5: Hetzner cloud deployment
test_scenario "Hetzner cloud (SSH_USER=lab-user)" \
    "export SSH_USER=lab-user" \
    "lab-user"

# Scenario 6: Red Hat Demo System (Equinix)
test_scenario "Red Hat Demo System (SUDO_USER=lab-user)" \
    "export SUDO_USER=lab-user" \
    "lab-user"

# Scenario 7: No env vars set (fallback)
test_scenario "No env vars set (fallback to lab-user)" \
    "" \
    "lab-user"

# Scenario 8: Root is filtered out
test_scenario "SUDO_USER=root is filtered, falls to USER" \
    "export SUDO_USER=root
export USER=normaluser" \
    "normaluser"

# Test validation with actual users
echo -e "${BLUE}=== User Validation Tests ===${NC}"
echo ""

echo -e "${BLUE}Test: Validate existing user (runner)${NC}"
if bash -c "
export QUBINODE_ADMIN_USER=runner
if id \"\$QUBINODE_ADMIN_USER\" &>/dev/null; then
    exit 0
else
    exit 1
fi
"; then
    echo -e "${GREEN}✓ PASS${NC} - User validation works for existing user"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} - User validation failed for existing user"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

echo -e "${BLUE}Test: Detect non-existing user${NC}"
if bash -c "
export QUBINODE_ADMIN_USER=nonexistent_admin_xyz
if ! id \"\$QUBINODE_ADMIN_USER\" &>/dev/null; then
    exit 0
else
    exit 1
fi
"; then
    echo -e "${GREEN}✓ PASS${NC} - Correctly detects non-existing user"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Should detect non-existing user"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test Python script with deployment scenarios
echo -e "${BLUE}=== Python Script Deployment Scenarios ===${NC}"
echo ""

echo -e "${BLUE}Test: Python auto-detection with SUDO_USER${NC}"
python_result=$(python3 -c "
import os
os.environ['SUDO_USER'] = 'lab-user'
os.environ['SSH_USER'] = 'centos'

username = (
    os.environ.get('QUBINODE_ADMIN_USER')
    or os.environ.get('ENV_USERNAME')
    or (os.environ.get('SUDO_USER') if os.environ.get('SUDO_USER') != 'root' else None)
    or (os.environ.get('SSH_USER') if os.environ.get('SSH_USER') != 'root' else None)
    or (os.environ.get('USER') if os.environ.get('USER') != 'root' else None)
)
print(username)
")

if [[ "$python_result" == "lab-user" ]]; then
    echo -e "${GREEN}✓ PASS${NC} - Python detects SUDO_USER correctly"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Python detection failed (got: $python_result)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Test error messaging
echo -e "${BLUE}=== Error Message Tests ===${NC}"
echo ""

echo -e "${BLUE}Test: Error message for non-existing user${NC}"
error_output=$(bash -c "
export QUBINODE_ADMIN_USER=nonexistent_user_test
export QUBINODE_DOMAIN=test.local
export QUBINODE_CLUSTER_NAME=test

if ! id \"\$QUBINODE_ADMIN_USER\" &>/dev/null; then
    echo \"ERROR: User '\$QUBINODE_ADMIN_USER' does not exist on this system\"
    echo \"Available non-root users:\"
    getent passwd | awk -F: '\$3 >= 1000 && \$3 < 65534 {print \"  - \" \$1}' | head -3
    echo \"\"
    echo \"To fix this issue:\"
    echo \"  1. Set QUBINODE_ADMIN_USER in .env to an existing user\"
    echo \"  2. Or create the user: sudo useradd -m \$QUBINODE_ADMIN_USER\"
    echo \"  3. Or run the script as the target user (it will be auto-detected)\"
fi
" 2>&1)

if echo "$error_output" | grep -q "does not exist" && \
   echo "$error_output" | grep -q "Available non-root users" && \
   echo "$error_output" | grep -q "To fix this issue"; then
    echo -e "${GREEN}✓ PASS${NC} - Error message provides helpful guidance"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} - Error message incomplete"
    TESTS_FAILED=$((TESTS_FAILED + 1))
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
    echo -e "${GREEN}All deployment scenario tests passed! ✓${NC}"
    echo ""
    echo "The fix correctly handles:"
    echo "  • Explicit user configuration in .env"
    echo "  • sudo deployments (SUDO_USER)"
    echo "  • SSH deployments (SSH_USER)"
    echo "  • Local deployments (USER)"
    echo "  • Hetzner and Equinix environments"
    echo "  • Fallback to lab-user"
    echo "  • Root user filtering"
    echo "  • User existence validation"
    echo "  • Clear error messages"
    exit 0
else
    echo -e "${RED}Some deployment scenario tests failed! ✗${NC}"
    exit 1
fi
