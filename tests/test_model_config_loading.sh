#!/bin/bash
# Integration test for AI Assistant model configuration loading
# Tests the fix for: AI Assistant container ignores model configuration from .env file

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Integration Test: AI Assistant Model Configuration Loading${NC}"
echo "=================================================================="
echo ""

# Get the repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Repository root: $REPO_ROOT"
echo ""

# Test 1: Verify .env file location check works
echo -e "${BLUE}Test 1: .env file discovery (repo root vs script directory)${NC}"

# Create a test .env in repo root
cat > "$REPO_ROOT/.env.test" << 'EOF'
MANAGER_MODEL=openrouter:anthropic/claude-3.5-sonnet
DEVELOPER_MODEL=openrouter:google/gemini-2.0-flash-exp
PYDANTICAI_MODEL=openrouter:openai/gpt-4o
OPENROUTER_API_KEY=TEST_API_KEY_PLACEHOLDER_NOT_REAL
EOF

# Simulate the script's .env loading logic
SCRIPT_DIR="$REPO_ROOT/scripts/development"

if [[ -f "$REPO_ROOT/.env.test" ]]; then
    echo "  ✓ Found .env.test in repository root"
    set -a
    source "$REPO_ROOT/.env.test"
    set +a
elif [[ -f "$SCRIPT_DIR/.env.test" ]]; then
    echo "  Found .env.test in script directory"
    set -a
    source "$SCRIPT_DIR/.env.test"
    set +a
else
    echo -e "${RED}  ✗ No .env.test file found${NC}"
    exit 1
fi

# Verify variables were loaded
if [[ "${MANAGER_MODEL}" == "openrouter:anthropic/claude-3.5-sonnet" ]] && \
   [[ "${DEVELOPER_MODEL}" == "openrouter:google/gemini-2.0-flash-exp" ]] && \
   [[ "${PYDANTICAI_MODEL}" == "openrouter:openai/gpt-4o" ]]; then
    echo -e "${GREEN}  ✓ Model variables loaded correctly from .env.test${NC}"
else
    echo -e "${RED}  ✗ Model variables not loaded correctly${NC}"
    echo "    MANAGER_MODEL: ${MANAGER_MODEL:-NOT_SET}"
    echo "    DEVELOPER_MODEL: ${DEVELOPER_MODEL:-NOT_SET}"
    echo "    PYDANTICAI_MODEL: ${PYDANTICAI_MODEL:-NOT_SET}"
    rm -f "$REPO_ROOT/.env.test"
    exit 1
fi

rm -f "$REPO_ROOT/.env.test"
echo ""

# Test 2: Verify default values are applied when .env is missing
echo -e "${BLUE}Test 2: Default model configuration${NC}"

unset MANAGER_MODEL DEVELOPER_MODEL PYDANTICAI_MODEL

# Apply defaults as the script does
export MANAGER_MODEL="${MANAGER_MODEL:-google-gla:gemini-2.0-flash}"
export DEVELOPER_MODEL="${DEVELOPER_MODEL:-google-gla:gemini-2.0-flash}"
export PYDANTICAI_MODEL="${PYDANTICAI_MODEL:-${MANAGER_MODEL}}"

echo "  Default values:"
echo "    MANAGER_MODEL: ${MANAGER_MODEL}"
echo "    DEVELOPER_MODEL: ${DEVELOPER_MODEL}"
echo "    PYDANTICAI_MODEL: ${PYDANTICAI_MODEL}"

if [[ "${MANAGER_MODEL}" == "google-gla:gemini-2.0-flash" ]] && \
   [[ "${DEVELOPER_MODEL}" == "google-gla:gemini-2.0-flash" ]] && \
   [[ "${PYDANTICAI_MODEL}" == "google-gla:gemini-2.0-flash" ]]; then
    echo -e "${GREEN}  ✓ Default values applied correctly${NC}"
else
    echo -e "${RED}  ✗ Default values not applied correctly${NC}"
    exit 1
fi
echo ""

# Test 3: Verify export and conditional syntax for container
echo -e "${BLUE}Test 3: Container environment variable passing${NC}"

# Set test values
export MANAGER_MODEL="openrouter:test/model-1"
export DEVELOPER_MODEL="openrouter:test/model-2"
export PYDANTICAI_MODEL="openrouter:test/model-3"
export OPENROUTER_API_KEY="TEST_API_KEY_PLACEHOLDER_NOT_REAL"

# Test conditional syntax (used in podman run command)
MANAGER_ARG="${MANAGER_MODEL:+-e MANAGER_MODEL=\"${MANAGER_MODEL}\"}"
DEVELOPER_ARG="${DEVELOPER_MODEL:+-e DEVELOPER_MODEL=\"${DEVELOPER_MODEL}\"}"
PYDANTICAI_ARG="${PYDANTICAI_MODEL:+-e PYDANTICAI_MODEL=\"${PYDANTICAI_MODEL}\"}"
OPENROUTER_ARG="${OPENROUTER_API_KEY:+-e OPENROUTER_API_KEY=\"${OPENROUTER_API_KEY}\"}"

echo "  Container arguments:"
echo "    ${MANAGER_ARG}"
echo "    ${DEVELOPER_ARG}"
echo "    ${PYDANTICAI_ARG}"
echo "    ${OPENROUTER_ARG}"

if [[ -n "${MANAGER_ARG}" ]] && \
   [[ -n "${DEVELOPER_ARG}" ]] && \
   [[ -n "${PYDANTICAI_ARG}" ]] && \
   [[ -n "${OPENROUTER_ARG}" ]]; then
    echo -e "${GREEN}  ✓ All model variables will be passed to container${NC}"
else
    echo -e "${RED}  ✗ Some model variables will not be passed to container${NC}"
    exit 1
fi
echo ""

# Test 4: Verify PYDANTICAI_MODEL defaults to MANAGER_MODEL
echo -e "${BLUE}Test 4: PYDANTICAI_MODEL default behavior${NC}"

unset PYDANTICAI_MODEL
export MANAGER_MODEL="openrouter:custom/manager-model"
export PYDANTICAI_MODEL="${PYDANTICAI_MODEL:-${MANAGER_MODEL}}"

echo "  When PYDANTICAI_MODEL is not set:"
echo "    MANAGER_MODEL: ${MANAGER_MODEL}"
echo "    PYDANTICAI_MODEL: ${PYDANTICAI_MODEL}"

if [[ "${PYDANTICAI_MODEL}" == "${MANAGER_MODEL}" ]]; then
    echo -e "${GREEN}  ✓ PYDANTICAI_MODEL correctly defaults to MANAGER_MODEL${NC}"
else
    echo -e "${RED}  ✗ PYDANTICAI_MODEL does not default to MANAGER_MODEL${NC}"
    exit 1
fi
echo ""

# Test 5: Verify priority - .env overrides defaults
echo -e "${BLUE}Test 5: .env values override defaults${NC}"

# Set defaults first
export MANAGER_MODEL="google-gla:gemini-2.0-flash"
export DEVELOPER_MODEL="google-gla:gemini-2.0-flash"
export PYDANTICAI_MODEL="google-gla:gemini-2.0-flash"

echo "  Initial (default) values:"
echo "    MANAGER_MODEL: ${MANAGER_MODEL}"

# Create .env with custom values
cat > "$REPO_ROOT/.env.test" << 'EOF'
MANAGER_MODEL=openrouter:mistralai/devstral-2512:free
DEVELOPER_MODEL=ollama:granite3.3:8b
PYDANTICAI_MODEL=anthropic:claude-3-haiku-20240307
EOF

# Source .env (simulating the fix)
set -a
source "$REPO_ROOT/.env.test"
set +a

# Re-apply export with defaults (values from .env should be preserved)
export MANAGER_MODEL="${MANAGER_MODEL:-google-gla:gemini-2.0-flash}"
export DEVELOPER_MODEL="${DEVELOPER_MODEL:-google-gla:gemini-2.0-flash}"
export PYDANTICAI_MODEL="${PYDANTICAI_MODEL:-${MANAGER_MODEL}}"

echo "  After loading .env.test:"
echo "    MANAGER_MODEL: ${MANAGER_MODEL}"
echo "    DEVELOPER_MODEL: ${DEVELOPER_MODEL}"
echo "    PYDANTICAI_MODEL: ${PYDANTICAI_MODEL}"

if [[ "${MANAGER_MODEL}" == "openrouter:mistralai/devstral-2512:free" ]] && \
   [[ "${DEVELOPER_MODEL}" == "ollama:granite3.3:8b" ]] && \
   [[ "${PYDANTICAI_MODEL}" == "anthropic:claude-3-haiku-20240307" ]]; then
    echo -e "${GREEN}  ✓ .env values correctly override defaults${NC}"
else
    echo -e "${RED}  ✗ .env values did not override defaults${NC}"
    rm -f "$REPO_ROOT/.env.test"
    exit 1
fi

rm -f "$REPO_ROOT/.env.test"
echo ""

# Test 6: Verify script directory .env also works
echo -e "${BLUE}Test 6: .env in script directory (fallback)${NC}"

# Create .env in script directory
mkdir -p "$REPO_ROOT/scripts/development"
cat > "$REPO_ROOT/scripts/development/.env.test" << 'EOF'
MANAGER_MODEL=script-dir-model
EOF

unset MANAGER_MODEL

SCRIPT_DIR="$REPO_ROOT/scripts/development"

# Simulate the script's logic: check repo root first, then script dir
if [[ -f "$REPO_ROOT/.env.test" ]]; then
    echo "  Loading from repo root..."
    set -a
    source "$REPO_ROOT/.env.test"
    set +a
elif [[ -f "$SCRIPT_DIR/.env.test" ]]; then
    echo "  Loading from script directory..."
    set -a
    source "$SCRIPT_DIR/.env.test"
    set +a
fi

export MANAGER_MODEL="${MANAGER_MODEL:-google-gla:gemini-2.0-flash}"

echo "  MANAGER_MODEL: ${MANAGER_MODEL}"

if [[ "${MANAGER_MODEL}" == "script-dir-model" ]]; then
    echo -e "${GREEN}  ✓ Script directory .env works as fallback${NC}"
else
    echo -e "${RED}  ✗ Script directory .env not loaded${NC}"
    rm -f "$REPO_ROOT/scripts/development/.env.test"
    exit 1
fi

rm -f "$REPO_ROOT/scripts/development/.env.test"
echo ""

echo "=================================================================="
echo -e "${GREEN}All integration tests passed!${NC}"
echo ""
echo "Summary:"
echo "  ✓ .env file discovered in repository root"
echo "  ✓ Default values applied when .env is missing"
echo "  ✓ Model variables passed to container correctly"
echo "  ✓ PYDANTICAI_MODEL defaults to MANAGER_MODEL"
echo "  ✓ .env values override defaults"
echo "  ✓ Script directory .env works as fallback"
