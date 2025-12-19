#!/bin/bash
# =============================================================================
# CI Setup Script for Airflow DAG Validation
# =============================================================================
# This script sets up the environment for Airflow CI jobs.
# It handles PATH configuration, dependency installation, and DB initialization.
#
# Usage:
#   source ./airflow/scripts/ci-setup.sh [command]
#
# Commands:
#   install     - Install Airflow and dependencies
#   init-db     - Initialize Airflow database
#   validate    - Run DAG validation
#   all         - Run all steps (default)
#
# Environment Variables:
#   AIRFLOW_HOME     - Airflow home directory (default: /tmp/airflow)
#   AIRFLOW_VERSION  - Airflow version to install (default: 2.10.4)
#   INSTALL_SSH      - Install SSH provider (default: true)
# =============================================================================

set -euo pipefail

# Default values
AIRFLOW_HOME="${AIRFLOW_HOME:-/tmp/airflow}"
AIRFLOW_VERSION="${AIRFLOW_VERSION:-2.10.4}"
INSTALL_SSH="${INSTALL_SSH:-true}"

# Colors (disable if not in terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# =============================================================================
# Helper Functions
# =============================================================================

setup_path() {
    # Add Python scripts directory to PATH
    SCRIPTS_DIR=$(python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))")
    export PATH="$SCRIPTS_DIR:$PATH"
    echo -e "${GREEN}[OK]${NC} Added to PATH: $SCRIPTS_DIR"
}

verify_airflow() {
    if command -v airflow &>/dev/null; then
        echo -e "${GREEN}[OK]${NC} airflow CLI found: $(which airflow)"
        return 0
    else
        echo -e "${RED}[ERROR]${NC} airflow CLI not found"
        return 1
    fi
}

install_airflow() {
    echo "========================================"
    echo "Installing Airflow $AIRFLOW_VERSION"
    echo "========================================"

    python -m pip install --upgrade pip
    pip install "apache-airflow[postgres,celery]==$AIRFLOW_VERSION"

    if [[ "$INSTALL_SSH" == "true" ]]; then
        echo "Installing SSH provider..."
        pip install "apache-airflow-providers-ssh"
    fi

    pip install pytest pytest-asyncio pyyaml

    # Setup PATH and verify
    setup_path
    verify_airflow

    echo -e "${GREEN}[OK]${NC} Airflow installation complete"
}

init_db() {
    echo "========================================"
    echo "Initializing Airflow Database"
    echo "========================================"

    setup_path
    export AIRFLOW_HOME="$AIRFLOW_HOME"

    verify_airflow || {
        echo -e "${RED}[ERROR]${NC} Cannot initialize DB - airflow not found"
        exit 1
    }

    airflow db init
    echo -e "${GREEN}[OK]${NC} Airflow database initialized"
}

validate_dags() {
    echo "========================================"
    echo "Validating DAGs"
    echo "========================================"

    setup_path
    export AIRFLOW_HOME="$AIRFLOW_HOME"
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/airflow/dags:$(pwd)/airflow/plugins"

    # Copy DAGs to Airflow home
    mkdir -p "$AIRFLOW_HOME/dags"
    cp -r airflow/dags/* "$AIRFLOW_HOME/dags/" 2>/dev/null || true

    # List DAGs
    echo "Listing DAGs..."
    airflow dags list || echo -e "${YELLOW}[WARN]${NC} No DAGs found or error listing"

    # Validate Python syntax
    echo ""
    echo "Validating Python syntax..."
    for dag in airflow/dags/*.py; do
        if [[ "$dag" != *"__init__.py"* ]]; then
            python3 -c "import ast; ast.parse(open('$dag').read())" || {
                echo -e "${RED}[ERROR]${NC} Syntax error in $dag"
                exit 1
            }
        fi
    done
    echo -e "${GREEN}[OK]${NC} All DAGs have valid syntax"
}

run_all() {
    install_airflow
    init_db
    validate_dags
}

# =============================================================================
# Main
# =============================================================================

COMMAND="${1:-all}"

case "$COMMAND" in
    install)
        install_airflow
        ;;
    init-db)
        init_db
        ;;
    validate)
        validate_dags
        ;;
    all)
        run_all
        ;;
    setup-path)
        # Just setup PATH - useful for sourcing
        setup_path
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Usage: $0 [install|init-db|validate|all|setup-path]"
        exit 1
        ;;
esac
