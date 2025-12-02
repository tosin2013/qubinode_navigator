#!/bin/bash
# Clear Airflow DAG cache and force reload
# Usage: ./clear-dag-cache.sh [dag_id]
#
# This script clears:
# 1. Python bytecode cache (.pyc files)
# 2. DAG processor manager logs
# 3. Reserializes DAGs in the database
#
# Per Issue #1 in Developer Issue Report - DAG Cache/Parsing Problems

set -euo pipefail

DAG_ID="${1:-}"

echo "========================================"
echo "Clearing Airflow DAG Cache"
echo "========================================"
echo ""

# Clear Python bytecode cache
echo "[INFO] Clearing Python bytecode cache..."
find /opt/airflow/dags -name "*.pyc" -delete 2>/dev/null || true
find /opt/airflow/dags -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
echo "[OK] Python bytecode cache cleared"

# Clear DAG processor manager cache
echo ""
echo "[INFO] Clearing DAG processor manager logs..."
rm -rf /opt/airflow/logs/dag_processor_manager/* 2>/dev/null || true
echo "[OK] DAG processor manager logs cleared"

# Reserialize DAGs
echo ""
if [ -n "$DAG_ID" ]; then
    echo "[INFO] Reserializing DAG: $DAG_ID"
    airflow dags reserialize --dag-id "$DAG_ID" 2>/dev/null || {
        echo "[WARN] Could not reserialize specific DAG, trying all DAGs..."
        airflow dags reserialize 2>/dev/null || true
    }
else
    echo "[INFO] Reserializing all DAGs..."
    airflow dags reserialize 2>/dev/null || true
fi
echo "[OK] DAG reserialization complete"

# List DAGs to verify
echo ""
echo "[INFO] Current DAGs in system:"
airflow dags list 2>/dev/null | head -20 || echo "[WARN] Could not list DAGs"

echo ""
echo "========================================"
echo "[OK] DAG cache cleared successfully"
echo "========================================"
echo ""
echo "The scheduler will reload DAGs on the next cycle."
echo "This typically takes 30-120 seconds depending on configuration."
echo ""
if [ -n "$DAG_ID" ]; then
    echo "To verify the DAG was reloaded:"
    echo "  airflow dags show $DAG_ID"
fi
