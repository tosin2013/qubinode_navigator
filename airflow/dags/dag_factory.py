"""
DAG Factory Module for Qubinode Navigator
ADR-0046: DAG Validation Pipeline and Host-Based Execution Strategy

This module provides factory functions to generate standardized Airflow DAGs
from configuration, ensuring consistent patterns across all deployments.

Features:
- Automatic enforcement of ADR-0045 standards
- SSH-based host execution pattern (ADR-0046)
- YAML registry support for simple DAGs
- Helper functions for complex multi-stage DAGs
- Built-in validation and environment checks

Usage:
    # Simple DAG from registry
    from dag_factory import load_registry_dags
    dags = load_registry_dags()

    # Custom DAG using factory
    from dag_factory import create_deployment_dag
    dag = create_deployment_dag(
        component='myapp',
        description='Deploy MyApp',
        script_path='/opt/kcli-pipelines/myapp',
        tags=['compute', 'myapp'],
        category='compute',
    )
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule

# Import user-configurable helpers for portable DAGs
from dag_helpers import get_ssh_user

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# =============================================================================
# Constants and Configuration
# =============================================================================

# Qubinode standard defaults (ADR-0045 compliant)
QUBINODE_DEFAULTS = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
}

# Valid categories for DAG classification
VALID_CATEGORIES = [
    "compute",  # VMs, containers, clusters
    "network",  # Routers, firewalls, load balancers
    "identity",  # Authentication, authorization, directory services
    "storage",  # Persistent storage, backups
    "security",  # PKI, secrets management, scanning
    "monitoring",  # Logging, metrics, alerting
]

# Validation patterns
NAMING_PATTERN = r"^[a-z][a-z0-9_]*$"  # snake_case only
REQUIRED_FIELDS = ["component", "description", "script_path", "tags", "category"]

# Default registry path
DEFAULT_REGISTRY_PATH = "/opt/kcli-pipelines/dags/registry.yaml"
ALT_REGISTRY_PATH = os.path.expanduser("~/qubinode_navigator/airflow/dags/registry.yaml")

# User-configurable SSH user
SSH_USER = get_ssh_user()


# =============================================================================
# Validation Functions
# =============================================================================


def validate_registry_entry(config: Dict[str, Any]) -> List[str]:
    """
    Validate a DAG configuration before generation.

    Args:
        config: Dictionary with DAG configuration

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Required fields check
    for field in REQUIRED_FIELDS:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    # Component naming convention (ADR-0045 compliance)
    component = config.get("component", "")
    if component and not re.match(NAMING_PATTERN, component):
        errors.append(f"Component name must be snake_case: '{component}'")

    # Script path validation
    script_path = config.get("script_path", "")
    if script_path and not script_path.startswith("/opt/"):
        errors.append(f"Script path should be in /opt/: '{script_path}'")

    # Category validation
    category = config.get("category", "")
    if category and category not in VALID_CATEGORIES:
        errors.append(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")

    # Tags validation
    tags = config.get("tags", [])
    if not isinstance(tags, list):
        errors.append("Tags must be a list")
    elif len(tags) == 0:
        errors.append("Tags must be a non-empty list")

    return errors


def validate_component_name(name: str) -> bool:
    """Check if component name follows snake_case convention."""
    return bool(re.match(NAMING_PATTERN, name))


# =============================================================================
# Core Factory Function
# =============================================================================


def create_deployment_dag(
    component: str,
    description: str,
    script_path: str,
    tags: List[str],
    category: str,
    params: Optional[Dict[str, Any]] = None,
    volume_mounts: Optional[List[str]] = None,
    custom_validation: Optional[str] = None,
    default_args_override: Optional[Dict[str, Any]] = None,
) -> DAG:
    """
    Factory function that generates standardized deployment DAGs.

    Automatically enforces:
    - ADR-0045: Naming conventions, coding standards
    - ADR-0046: SSH execution pattern, validation
    - ADR-0047: kcli-pipelines integration

    Args:
        component: Component name (snake_case)
        description: Human-readable description
        script_path: Path to deploy.sh in kcli-pipelines
        tags: List of tags for filtering
        category: Component category (compute, network, identity, etc.)
        params: Runtime parameters with defaults
        volume_mounts: Required volume mounts (for documentation)
        custom_validation: Additional validation bash commands
        default_args_override: Override default_args values

    Returns:
        Configured Airflow DAG

    Example:
        dag = create_deployment_dag(
            component='freeipa',
            description='Deploy FreeIPA Identity Management',
            script_path='/opt/kcli-pipelines/freeipa',
            tags=['identity', 'dns', 'kerberos'],
            category='identity',
            params={'action': 'create', 'domain': 'example.com'},
        )
    """
    # Validate inputs
    errors = validate_registry_entry(
        {
            "component": component,
            "description": description,
            "script_path": script_path,
            "tags": tags,
            "category": category,
        }
    )
    if errors:
        raise ValueError(f"Invalid DAG configuration: {errors}")

    # Build DAG ID
    dag_id = f"{component}_deployment"

    # Merge default args with overrides
    dag_default_args = QUBINODE_DEFAULTS.copy()
    if default_args_override:
        dag_default_args.update(default_args_override)

    # Build params with action default
    dag_params = {"action": "create"}
    if params:
        dag_params.update(params)

    # Build unique tags list
    all_tags = ["qubinode", component, category]
    for tag in tags:
        if tag not in all_tags:
            all_tags.append(tag)

    # Generate documentation
    doc_md = _generate_dag_documentation(
        component=component,
        description=description,
        script_path=script_path,
        params=dag_params,
        volume_mounts=volume_mounts,
    )

    # Create DAG
    dag = DAG(
        dag_id,
        default_args=dag_default_args,
        description=description,
        schedule=None,  # Manual trigger for deployment DAGs
        catchup=False,
        tags=all_tags,
        params=dag_params,
        doc_md=doc_md,
    )

    # Create branching task for action
    def decide_action(**context):
        """Branch based on action parameter."""
        action = context["params"].get("action", "create")
        if action in ("delete", "destroy"):
            return f"destroy_{component}"
        elif action == "status":
            return f"status_{component}"
        return "validate_environment"

    decide_action_task = BranchPythonOperator(
        task_id="decide_action",
        python_callable=decide_action,
        dag=dag,
    )

    # Task: Environment validation (always included)
    validate_env = BashOperator(
        task_id="validate_environment",
        bash_command=_generate_validation_script(
            component=component,
            script_path=script_path,
            custom_validation=custom_validation,
        ),
        dag=dag,
    )

    # Task: Deploy using SSH execution pattern (ADR-0046)
    deploy = BashOperator(
        task_id=f"deploy_{component}",
        bash_command=_generate_deploy_script(
            component=component,
            script_path=script_path,
            action="create",
        ),
        dag=dag,
    )

    # Task: Destroy
    destroy = BashOperator(
        task_id=f"destroy_{component}",
        bash_command=_generate_deploy_script(
            component=component,
            script_path=script_path,
            action="delete",
        ),
        dag=dag,
    )

    # Task: Status check
    status = BashOperator(
        task_id=f"status_{component}",
        bash_command=_generate_deploy_script(
            component=component,
            script_path=script_path,
            action="status",
        ),
        dag=dag,
    )

    # Task: Cleanup on failure
    cleanup_on_failure = BashOperator(
        task_id="cleanup_on_failure",
        bash_command=f"""
        echo "========================================"
        echo "[WARN] Deployment failed - running cleanup"
        echo "========================================"

        # Attempt cleanup via SSH
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {SSH_USER}@localhost \\
            "export ACTION=delete && cd {script_path} && ./deploy.sh" 2>/dev/null || true

        echo "[INFO] Cleanup attempted"
        """,
        dag=dag,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Wire up the workflow
    decide_action_task >> [validate_env, destroy, status]
    validate_env >> deploy >> cleanup_on_failure

    return dag


# =============================================================================
# Helper Functions for Script Generation
# =============================================================================


def _generate_validation_script(
    component: str,
    script_path: str,
    custom_validation: Optional[str] = None,
) -> str:
    """Generate the validation bash script."""
    custom_block = custom_validation or ""

    return f"""
    echo "========================================"
    echo "Validating environment for {component}"
    echo "========================================"

    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

    # Check SSH connectivity to host
    echo -n "[1/4] SSH connectivity... "
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {SSH_USER}@localhost "echo ok" > /dev/null 2>&1; then
        echo "OK"
    else
        echo "FAILED"
        echo "[ERROR] Cannot SSH to localhost"
        echo "Ensure SSH is configured per ADR-0046"
        exit 1
    fi

    # Check deploy script exists
    echo -n "[2/4] Deploy script... "
    if ssh -o StrictHostKeyChecking=no {SSH_USER}@localhost "test -f {script_path}/deploy.sh"; then
        echo "OK"
    else
        echo "FAILED"
        echo "[ERROR] Deploy script not found: {script_path}/deploy.sh"
        exit 1
    fi

    # Check kcli availability on host (warning only)
    echo -n "[3/4] kcli availability... "
    if ssh -o StrictHostKeyChecking=no {SSH_USER}@localhost "command -v kcli" > /dev/null 2>&1; then
        echo "OK"
    else
        echo "WARN (not installed)"
    fi

    # Check libvirt connectivity (warning only)
    echo -n "[4/4] libvirt connectivity... "
    if ssh -o StrictHostKeyChecking=no {SSH_USER}@localhost "virsh -c qemu:///system list" > /dev/null 2>&1; then
        echo "OK"
    else
        echo "WARN (not available)"
    fi

    {custom_block}

    echo ""
    echo "[OK] Environment validation complete"
    """


def _generate_deploy_script(
    component: str,
    script_path: str,
    action: str,
) -> str:
    """Generate the deployment bash script using SSH execution pattern."""
    action_display = action.upper()

    return f"""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

    echo "========================================"
    echo "{action_display}: {component}"
    echo "Action: {{{{ params.action }}}}"
    echo "========================================"

    # Build ACTION from params
    ACTION="{{{{ params.action }}}}"

    # Execute deploy.sh on host via SSH (ADR-0046 pattern)
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \\
        "export ACTION=$ACTION && \\
         cd {script_path} && \\
         ./deploy.sh"

    EXIT_CODE=$?

    echo "========================================"
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[OK] {component} {action} complete"
    else
        echo "[ERROR] {component} {action} failed (exit code: $EXIT_CODE)"
        exit $EXIT_CODE
    fi
    echo "========================================"
    """


def _generate_dag_documentation(
    component: str,
    description: str,
    script_path: str,
    params: Dict[str, Any],
    volume_mounts: Optional[List[str]] = None,
) -> str:
    """Generate markdown documentation for the DAG."""
    # Format params as YAML-like string
    params_str = "\n".join(f"  {k}: {v}" for k, v in params.items())

    # Format volume mounts
    mounts_str = ""
    if volume_mounts:
        mounts_str = "\n".join(f"- `{m}`" for m in volume_mounts)
    else:
        mounts_str = "None required"

    return f"""
# {component.replace("_", " ").title()} Deployment

{description}

## Script Location
`{script_path}/deploy.sh`

## Parameters
```yaml
{params_str}
```

## Volume Mounts Required
{mounts_str}

## Usage
```bash
# Create
airflow dags trigger {component}_deployment --conf '{{"action": "create"}}'

# Delete
airflow dags trigger {component}_deployment --conf '{{"action": "delete"}}'

# Status
airflow dags trigger {component}_deployment --conf '{{"action": "status"}}'
```

## Related ADRs
- ADR-0045: DAG Development Standards
- ADR-0046: Validation Pipeline and Host Execution
- ADR-0047: kcli-pipelines Integration
"""


# =============================================================================
# Registry Loading Functions
# =============================================================================


def load_registry_dags(
    registry_path: Optional[str] = None,
) -> Dict[str, DAG]:
    """
    Load and generate all DAGs from the YAML registry.

    Args:
        registry_path: Path to registry.yaml file

    Returns:
        Dictionary of dag_id -> DAG objects
    """
    if not YAML_AVAILABLE:
        print("[WARN] PyYAML not installed - cannot load registry DAGs")
        return {}

    # Try multiple registry locations
    paths_to_try = []
    if registry_path:
        paths_to_try.append(registry_path)
    paths_to_try.extend([DEFAULT_REGISTRY_PATH, ALT_REGISTRY_PATH])

    registry = None
    for path in paths_to_try:
        try:
            with open(path) as f:
                registry = yaml.safe_load(f)
                print(f"[INFO] Loaded DAG registry from: {path}")
                break
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"[WARN] Error loading {path}: {e}")
            continue

    if not registry:
        print(f"[INFO] No registry.yaml found at: {paths_to_try}")
        return {}

    dags = {}
    for dag_config in registry.get("dags", []):
        component = dag_config.get("component", "unknown")

        # Validate configuration
        errors = validate_registry_entry(dag_config)
        if errors:
            print(f"[WARN] Skipping invalid DAG config for '{component}': {errors}")
            continue

        try:
            # Generate DAG
            dag = create_deployment_dag(**dag_config)
            dags[dag.dag_id] = dag
            print(f"[OK] Generated DAG: {dag.dag_id}")
        except Exception as e:
            print(f"[ERROR] Failed to generate DAG for '{component}': {e}")
            continue

    return dags


# =============================================================================
# Helper Functions for Complex DAGs
# =============================================================================


def add_stage(
    dag: DAG,
    stage_name: str,
    script_name: str,
    script_path: Optional[str] = None,
) -> BashOperator:
    """
    Add a deployment stage that runs a script via SSH.

    Args:
        dag: Parent DAG
        stage_name: Name for this stage (becomes task_id)
        script_name: Script filename to execute (e.g., '01-prepare.sh')
        script_path: Override script path (defaults to dag's script_path)

    Returns:
        BashOperator task
    """
    # Use dag description to infer component or use provided path
    if not script_path:
        # Try to extract from dag description or use default
        script_path = "/opt/kcli-pipelines"

    return BashOperator(
        task_id=stage_name,
        bash_command=f"""
        export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

        echo "========================================"
        echo "Stage: {stage_name}"
        echo "========================================"

        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR {SSH_USER}@localhost \\
            "cd {script_path} && ./{script_name}"

        echo "[OK] Stage {stage_name} complete"
        """,
        dag=dag,
    )


def add_manual_step(
    dag: DAG,
    task_id: str,
    instructions: str,
    timeout_hours: int = 2,
) -> BashOperator:
    """
    Add a manual approval/intervention step.

    The task displays instructions and waits for a file to be created.

    Args:
        dag: Parent DAG
        task_id: Task identifier
        instructions: Instructions to display
        timeout_hours: Timeout in hours (default 2)

    Returns:
        BashOperator task (the final cleanup task for chaining)
    """
    approval_file = f"/tmp/airflow_approval_{dag.dag_id}_{task_id}"

    # Single task that shows instructions and waits
    manual_task = BashOperator(
        task_id=task_id,
        bash_command=f"""
        echo "========================================"
        echo "MANUAL STEP REQUIRED"
        echo "========================================"
        echo ""
        echo "{instructions}"
        echo ""
        echo "When ready, create approval file on the host:"
        echo "  touch {approval_file}"
        echo ""
        echo "Waiting up to {timeout_hours} hours..."
        echo "========================================"

        TIMEOUT_SECONDS=$(({timeout_hours} * 3600))
        ELAPSED=0

        while [ ! -f "{approval_file}" ]; do
            sleep 30
            ELAPSED=$((ELAPSED + 30))
            if [ $ELAPSED -ge $TIMEOUT_SECONDS ]; then
                echo "[ERROR] Timeout waiting for approval"
                exit 1
            fi
            echo "[INFO] Waiting... ($ELAPSED seconds elapsed)"
        done

        echo "[OK] Approval received"
        rm -f "{approval_file}"
        """,
        dag=dag,
    )

    return manual_task


def add_conditional_branch(
    dag: DAG,
    param_name: str,
    branches: Dict[str, str],
    default_branch: Optional[str] = None,
) -> BranchPythonOperator:
    """
    Add conditional branching based on a parameter value.

    Args:
        dag: Parent DAG
        param_name: Parameter name to branch on
        branches: Mapping of param values to task_ids
        default_branch: Default task_id if param value not in branches

    Returns:
        BranchPythonOperator task
    """

    def choose_branch(**context):
        param_value = context["params"].get(param_name)
        if param_value in branches:
            return branches[param_value]
        return default_branch or list(branches.values())[0]

    return BranchPythonOperator(
        task_id=f"branch_on_{param_name}",
        python_callable=choose_branch,
        dag=dag,
    )


# =============================================================================
# Module Information
# =============================================================================

__version__ = "1.0.0"
__author__ = "Qubinode Team"
__all__ = [
    "create_deployment_dag",
    "load_registry_dags",
    "validate_registry_entry",
    "add_stage",
    "add_manual_step",
    "add_conditional_branch",
    "VALID_CATEGORIES",
    "QUBINODE_DEFAULTS",
]
