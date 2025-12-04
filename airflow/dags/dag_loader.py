"""
DAG Loader Module for Qubinode Navigator
ADR-0046: DAG Factory Pattern for Consistent Deployments

This module loads all DAGs from the registry.yaml file and exposes them
to Airflow's DagBag for automatic discovery.

Usage:
    This file should be placed in the Airflow dags folder. Airflow will
    automatically discover and load all DAGs generated from the registry.

The loader:
1. Reads registry.yaml configuration
2. Validates each entry
3. Generates standardized DAGs using dag_factory
4. Exposes DAGs to Airflow via globals()
"""

import os
import sys

# Ensure dag_factory is importable
DAGS_DIR = os.path.dirname(os.path.abspath(__file__))
if DAGS_DIR not in sys.path:
    sys.path.insert(0, DAGS_DIR)

try:
    from dag_factory import load_registry_dags
except ImportError as e:
    print(f"[ERROR] Cannot import dag_factory: {e}")
    print(f"[INFO] DAGS_DIR: {DAGS_DIR}")
    print(f"[INFO] sys.path: {sys.path}")
    load_registry_dags = None


def main():
    """Load all registry DAGs and expose them to Airflow."""
    if load_registry_dags is None:
        print("[ERROR] dag_factory not available - skipping registry DAG loading")
        return {}

    # Try loading from multiple locations
    registry_paths = [
        os.path.join(DAGS_DIR, "registry.yaml"),
        "/opt/kcli-pipelines/dags/registry.yaml",
        "/root/qubinode_navigator/airflow/dags/registry.yaml",
    ]

    for path in registry_paths:
        if os.path.exists(path):
            print(f"[INFO] Loading DAGs from registry: {path}")
            return load_registry_dags(registry_path=path)

    print(f"[WARN] No registry.yaml found at: {registry_paths}")
    return {}


# Load registry DAGs when this module is imported by Airflow
_registry_dags = main()

# Expose DAGs to Airflow's DagBag by adding them to globals()
# This allows Airflow to discover them automatically
for _dag_id, _dag in _registry_dags.items():
    globals()[_dag_id] = _dag

# Cleanup temporary variables
if "_dag_id" in dir():
    del _dag_id
if "_dag" in dir():
    del _dag


# =============================================================================
# Module Information
# =============================================================================

__version__ = "1.0.0"
__author__ = "Qubinode Team"

# Export list of loaded DAGs for debugging
LOADED_DAGS = list(_registry_dags.keys())

if __name__ == "__main__":
    print(f"Loaded {len(LOADED_DAGS)} DAGs from registry:")
    for dag_id in LOADED_DAGS:
        print(f"  - {dag_id}")
