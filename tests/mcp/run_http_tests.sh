#!/bin/bash
# Quick MCP HTTP Server Tests

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

AIRFLOW_URL="http://localhost:8889"
AI_URL="http://localhost:8081"
AIRFLOW_KEY="65efb281f1ea9dc8498ec563f7bf42af4f8bf8a6b7bb542141902ce462cdb98a"
AI_KEY="74008c5dde3fca81946c7a5c019ee1e64aef85dbe7a08c2ea9a709bdcfae1e0f"

PASSED=0
FAILED=0

echo "========================================"
echo "MCP HTTP Server Quick Tests"
echo "========================================"
echo ""

# Test Airflow
echo "Testing Airflow MCP (port 8889)..."
if curl -s -H "X-API-Key: ${AIRFLOW_KEY}" "${AIRFLOW_URL}/health" | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} Airflow MCP is healthy"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗${NC} Airflow MCP failed"
    FAILED=$((FAILED + 1))
fi

# Test AI Assistant
echo "Testing AI Assistant MCP (port 8081)..."
if curl -s -H "X-API-Key: ${AI_KEY}" "${AI_URL}/health" | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} AI Assistant MCP is healthy"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗${NC} AI Assistant MCP failed"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "========================================"
echo "Results: ${PASSED} passed, ${FAILED} failed"
echo "========================================"

[ $FAILED -eq 0 ] && exit 0 || exit 1
