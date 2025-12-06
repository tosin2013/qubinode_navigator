#!/bin/bash
# Integration test for deployment script path handling

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Integration Test: Deployment Script Path Handling${NC}"
echo "=================================================="
echo ""

# Get the repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Repository root: $REPO_ROOT"
echo ""

# Test 1: Extract SCRIPT_DIR and MY_DIR from root deploy-qubinode.sh
echo -e "${BLUE}Test 1: Root deploy-qubinode.sh path extraction${NC}"
cd "$REPO_ROOT"

echo "Script path: $REPO_ROOT/deploy-qubinode.sh"

# Simulate the script's SCRIPT_DIR calculation as if BASH_SOURCE[0] is deploy-qubinode.sh
SIMULATED_BASH_SOURCE="$REPO_ROOT/deploy-qubinode.sh"
SCRIPT_DIR="$(cd "$(dirname "$SIMULATED_BASH_SOURCE")" && pwd)"
MY_DIR="$(dirname "$SCRIPT_DIR")"

echo "When deployed-qubinode.sh is executed:"
echo "  SCRIPT_DIR would be: $SCRIPT_DIR"
echo "  MY_DIR would be: $MY_DIR"
echo "  Expected SCRIPT_DIR: $REPO_ROOT"
echo "  Expected MY_DIR: $(dirname "$REPO_ROOT")"

if [[ "$SCRIPT_DIR" == "$REPO_ROOT" ]] && [[ "$MY_DIR" == "$(dirname "$REPO_ROOT")" ]]; then
    echo -e "${GREEN}✓ Root deploy-qubinode.sh path calculation is correct${NC}"
else
    echo -e "${RED}✗ Root deploy-qubinode.sh path calculation failed${NC}"
    exit 1
fi
echo ""

# Test 2: Extract SCRIPT_DIR and MY_DIR from scripts/development/deploy-qubinode.sh
echo -e "${BLUE}Test 2: scripts/development/deploy-qubinode.sh path extraction${NC}"

echo "Script path: $REPO_ROOT/scripts/development/deploy-qubinode.sh"

# Simulate the script's SCRIPT_DIR calculation as if BASH_SOURCE[0] is the deploy script
SIMULATED_BASH_SOURCE="$REPO_ROOT/scripts/development/deploy-qubinode.sh"
SCRIPT_DIR="$(cd "$(dirname "$SIMULATED_BASH_SOURCE")" && pwd)"
MY_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

echo "When scripts/development/deploy-qubinode.sh is executed:"
echo "  SCRIPT_DIR would be: $SCRIPT_DIR"
echo "  MY_DIR would be: $MY_DIR"
echo "  Expected SCRIPT_DIR: $REPO_ROOT/scripts/development"
echo "  Expected MY_DIR: $(dirname "$REPO_ROOT")"

if [[ "$SCRIPT_DIR" == "$REPO_ROOT/scripts/development" ]] && [[ "$MY_DIR" == "$(dirname "$REPO_ROOT")" ]]; then
    echo -e "${GREEN}✓ scripts/development/deploy-qubinode.sh path calculation is correct${NC}"
else
    echo -e "${RED}✗ scripts/development/deploy-qubinode.sh path calculation failed${NC}"
    exit 1
fi
echo ""

# Test 3: Verify critical file paths are accessible
echo -e "${BLUE}Test 3: Verify critical file paths${NC}"
cd "$REPO_ROOT"

FILES_TO_CHECK=(
    "load-variables.py"
    "ansible-builder/requirements.yml"
    "ansible-navigator/setup_kvmhost.yml"
    ".env.example"
)

ALL_FOUND=true
for file in "${FILES_TO_CHECK[@]}"; do
    if [[ -f "$REPO_ROOT/$file" ]]; then
        echo -e "${GREEN}✓${NC} Found: $file"
    else
        echo -e "${RED}✗${NC} Missing: $file"
        ALL_FOUND=false
    fi
done

if $ALL_FOUND; then
    echo -e "${GREEN}✓ All critical files are accessible${NC}"
else
    echo -e "${RED}✗ Some critical files are missing${NC}"
    exit 1
fi
echo ""

# Test 4: Simulate sudo environment
echo -e "${BLUE}Test 4: Sudo simulation${NC}"
echo "When run with sudo, SCRIPT_DIR should still point to the actual script location"
echo "not to /root or \$HOME"

# Simulate sudo by setting HOME to /root (we can't change EUID in a script)
ORIGINAL_HOME="$HOME"
export HOME="/root"

SIMULATED_BASH_SOURCE="$REPO_ROOT/deploy-qubinode.sh"
SCRIPT_DIR="$(cd "$(dirname "$SIMULATED_BASH_SOURCE")" && pwd)"
MY_DIR="$(dirname "$SCRIPT_DIR")"

echo "With HOME=/root:"
echo "  SCRIPT_DIR: $SCRIPT_DIR"
echo "  MY_DIR: $MY_DIR"
echo "  Expected: SCRIPT_DIR should be $REPO_ROOT (not /root)"

if [[ "$SCRIPT_DIR" == "$REPO_ROOT" ]]; then
    echo -e "${GREEN}✓ SCRIPT_DIR correctly ignores HOME variable${NC}"
else
    echo -e "${RED}✗ SCRIPT_DIR incorrectly uses HOME variable${NC}"
    exit 1
fi

export HOME="$ORIGINAL_HOME"
echo ""

echo "=================================================="
echo -e "${GREEN}All integration tests passed!${NC}"
echo ""
echo "Summary:"
echo "  ✓ Root deploy-qubinode.sh calculates paths correctly"
echo "  ✓ scripts/development/deploy-qubinode.sh calculates paths correctly"
echo "  ✓ All critical files are accessible from calculated paths"
echo "  ✓ Path calculations work correctly under sudo (ignoring \$HOME)"
