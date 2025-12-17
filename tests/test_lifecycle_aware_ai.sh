#!/bin/bash
# Test for lifecycle-aware AI persona functionality
# Validates that ask_ai_for_help function properly switches between SRE and Architect modes

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Testing Lifecycle-Aware AI Persona${NC}"
echo "=================================================="
echo ""

# Get the repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Repository root: $REPO_ROOT"
echo ""

# Source the deploy script to get the ask_ai_for_help function
# We'll create a minimal mock environment
SCRIPT_DIR="$REPO_ROOT/scripts/development"

# Test 1: Verify ask_ai_for_help function exists and has correct signature
echo -e "${BLUE}Test 1: Function signature validation${NC}"

# Extract function definition from deploy-qubinode.sh
if grep -q "ask_ai_for_help()" "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ ask_ai_for_help function found${NC}"
else
    echo -e "${RED}✗ ask_ai_for_help function not found${NC}"
    exit 1
fi

# Check for lifecycle_stage parameter
if grep -A 3 "ask_ai_for_help()" "$SCRIPT_DIR/deploy-qubinode.sh" | grep -q 'lifecycle_stage="${3:-deployment}"'; then
    echo -e "${GREEN}✓ lifecycle_stage parameter with default value found${NC}"
else
    echo -e "${RED}✗ lifecycle_stage parameter not properly configured${NC}"
    exit 1
fi
echo ""

# Test 2: Verify SRE mode prompt exists
echo -e "${BLUE}Test 2: SRE mode prompt validation${NC}"

if grep -q "ROLE: Site Reliability Engineer (SRE)" "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ SRE mode prompt found${NC}"
else
    echo -e "${RED}✗ SRE mode prompt not found${NC}"
    exit 1
fi

if grep -q "NO Code Refactoring" "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ SRE mode restrictions found${NC}"
else
    echo -e "${RED}✗ SRE mode restrictions not found${NC}"
    exit 1
fi
echo ""

# Test 3: Verify Architect mode prompt exists
echo -e "${BLUE}Test 3: Architect mode prompt validation${NC}"

if grep -q "ROLE: Qubinode System Architect" "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ Architect mode prompt found${NC}"
else
    echo -e "${RED}✗ Architect mode prompt not found${NC}"
    exit 1
fi

if grep -q "Add features, refactor code, and optimize workflows" "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ Architect mode capabilities found${NC}"
else
    echo -e "${RED}✗ Architect mode capabilities not found${NC}"
    exit 1
fi
echo ""

# Test 4: Verify lifecycle_stage is sent in context
echo -e "${BLUE}Test 4: Lifecycle stage context validation${NC}"

if grep -q '"lifecycle_stage": "$lifecycle_stage"' "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ lifecycle_stage included in context payload${NC}"
else
    echo -e "${RED}✗ lifecycle_stage not included in context payload${NC}"
    exit 1
fi
echo ""

# Test 5: Verify signal_deployment_success function exists
echo -e "${BLUE}Test 5: Deployment success signaling${NC}"

if grep -q "signal_deployment_success()" "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ signal_deployment_success function found${NC}"
else
    echo -e "${RED}✗ signal_deployment_success function not found${NC}"
    exit 1
fi

if grep -q 'lifecycle_stage.*operational' "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ Operational stage signal found${NC}"
else
    echo -e "${RED}✗ Operational stage signal not found${NC}"
    exit 1
fi
echo ""

# Test 6: Verify AGENTS.md documentation
echo -e "${BLUE}Test 6: Documentation validation${NC}"

if grep -q "## Lifecycle-Aware Interaction Rules" "$REPO_ROOT/AGENTS.md"; then
    echo -e "${GREEN}✓ Lifecycle-Aware Interaction Rules section found in AGENTS.md${NC}"
else
    echo -e "${RED}✗ Lifecycle-Aware Interaction Rules section not found in AGENTS.md${NC}"
    exit 1
fi

if grep -q "Phase 1: Deployment & Bootstrap (STRICT SRE MODE)" "$REPO_ROOT/AGENTS.md"; then
    echo -e "${GREEN}✓ Phase 1 documentation found${NC}"
else
    echo -e "${RED}✗ Phase 1 documentation not found${NC}"
    exit 1
fi

if grep -q "Phase 2: Operational & Feature (ARCHITECT MODE)" "$REPO_ROOT/AGENTS.md"; then
    echo -e "${GREEN}✓ Phase 2 documentation found${NC}"
else
    echo -e "${RED}✗ Phase 2 documentation not found${NC}"
    exit 1
fi
echo ""

# Test 7: Verify DEVELOPMENT_MODE check
echo -e "${BLUE}Test 7: DEVELOPMENT_MODE override validation${NC}"

if grep -q 'DEVELOPMENT_MODE:-false' "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ DEVELOPMENT_MODE check found${NC}"
else
    echo -e "${RED}✗ DEVELOPMENT_MODE check not found${NC}"
    exit 1
fi
echo ""

# Test 8: Verify display shows persona mode
echo -e "${BLUE}Test 8: Display persona mode validation${NC}"

if grep -q 'AI GUIDANCE ($lifecycle_stage mode)' "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ Persona mode displayed in AI guidance header${NC}"
else
    echo -e "${RED}✗ Persona mode not displayed in AI guidance header${NC}"
    exit 1
fi

if grep -q 'Mode: ${GREEN}Architect/Developer${NC}' "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ Architect/Developer mode shown in completion summary${NC}"
else
    echo -e "${RED}✗ Architect/Developer mode not shown in completion summary${NC}"
    exit 1
fi
echo ""

# Test 9: Verify max_tokens increased for more detailed responses
echo -e "${BLUE}Test 9: Token limit validation${NC}"

if grep -q 'max_tokens.*800' "$SCRIPT_DIR/deploy-qubinode.sh"; then
    echo -e "${GREEN}✓ Token limit increased to 800 for detailed responses${NC}"
else
    echo -e "${RED}✗ Token limit not increased${NC}"
    exit 1
fi
echo ""

echo "=================================================="
echo -e "${GREEN}All lifecycle-aware AI persona tests passed!${NC}"
echo ""
echo "Summary:"
echo "  ✓ ask_ai_for_help function has lifecycle_stage parameter"
echo "  ✓ SRE mode prompt with restrictions is configured"
echo "  ✓ Architect mode prompt with full capabilities is configured"
echo "  ✓ lifecycle_stage is sent in context payload"
echo "  ✓ signal_deployment_success function signals operational mode"
echo "  ✓ AGENTS.md documentation includes lifecycle rules"
echo "  ✓ DEVELOPMENT_MODE override is supported"
echo "  ✓ Persona mode is displayed to users"
echo "  ✓ Token limit increased for detailed AI responses"
echo ""
echo -e "${YELLOW}Note: This test validates the implementation structure.${NC}"
echo -e "${YELLOW}Full functional testing requires a running AI Assistant.${NC}"
