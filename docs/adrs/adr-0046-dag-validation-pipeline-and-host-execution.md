# ADR-0046: DAG Validation Pipeline and Host-Based Execution Strategy

## Status

Accepted (Amended 2025-12-05)

## Date

2025-11-27

## Context and Problem Statement

During FreeIPA DAG development, we encountered two significant issues:

### Issue 1: Ansible Version Mismatch

The Airflow container may have a different Ansible version than the host system. This causes:

- Playbook compatibility issues
- Missing collections/modules
- Different behavior between container and host execution
- Maintenance burden of keeping container Ansible in sync with host

### Issue 2: No DAG Validation Before Deployment

Users can deploy DAGs with:

- Syntax errors (Python)
- Bash command issues (Unicode, quoting, PATH)
- Missing dependencies
- Incorrect Jinja templating

These errors are only discovered at runtime, causing failed DAG runs.

## Decision Drivers

- Ansible playbooks should run with the host's Ansible installation
- DAGs should be validated before deployment
- Validation should be automated and easy to use
- Errors should be caught early in the development cycle
- Solution should work in CI/CD pipelines

## Decision Outcome

Implement two complementary solutions:

### Solution 1: SSH-Based Host Execution for Ansible

Instead of running Ansible inside the container, use SSH to execute Ansible on the host.

```python
# Instead of running ansible-playbook directly in container:
bash_command="""
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i inventory playbook.yaml
"""

# Use SSH to run on host:
bash_command="""
ssh -o StrictHostKeyChecking=no root@localhost \
    "cd /opt/freeipa-workshop-deployer && \
     ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook \
     -i $INVENTORY_DIR/inventory \
     --extra-vars 'idm_hostname=${IDM_HOSTNAME}' \
     2_ansible_config/deploy_idm.yaml -v"
"""
```

**Benefits:**

- Uses host's Ansible version and collections
- No need to maintain Ansible in container
- Consistent with manual execution
- Access to host's SSH keys and credentials

**Requirements:**

- SSH key from container to host (passwordless)
- Host SSH server running on localhost
- Container must have SSH client installed

### Solution 2: DAG Validation Pipeline

Implement a multi-tier validation approach with Python DagBag API as the primary validation method.

#### Validation Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DAG Validation Pipeline                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Developer Workstation              GitHub Actions CI                    │
│  ─────────────────────              ──────────────────                   │
│                                                                          │
│  ┌──────────────────────┐          ┌────────────────────────────────┐   │
│  │ validate-dag.sh      │          │ airflow-validate.yml           │   │
│  │ (Quick feedback)     │          │ (Comprehensive validation)     │   │
│  │                      │          │                                │   │
│  │ 1. Python syntax     │          │ 1. Python syntax               │   │
│  │ 2. DagBag import     │          │ 2. DagBag import (full)        │   │
│  │ 3. lint-dags.sh      │          │ 3. lint-dags.sh                │   │
│  │                      │          │ 4. Smoke test (DAG execution)  │   │
│  │                      │          │ 5. OpenLineage integration     │   │
│  │                      │          │ 6. Infrastructure validation   │   │
│  └──────────────────────┘          └────────────────────────────────┘   │
│           │                                     │                        │
│           ▼                                     ▼                        │
│  ┌──────────────────────┐          ┌────────────────────────────────┐   │
│  │ lint-dags.sh         │          │ Python DagBag API              │   │
│  │ (ADR compliance)     │          │ (Airflow recommended)          │   │
│  │                      │          │                                │   │
│  │ - Escape sequences   │          │ dagbag = DagBag(...)           │   │
│  │ - SSH patterns       │          │ if dagbag.import_errors:       │   │
│  │ - DAG ID naming      │          │     # Distinguish real errors  │   │
│  │ - Non-ASCII chars    │          │     # from duplicate warnings  │   │
│  └──────────────────────┘          └────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Primary Validation: Python DagBag API (Airflow Recommended)

The Airflow DagBag API is the authoritative method for DAG validation:

```python
# CI Validation Pattern (airflow-validate.yml)
from airflow.models import DagBag

dagbag = DagBag(include_examples=False)

# Report loaded DAGs
print(f"Loaded {len(dagbag.dags)} DAGs:")
for dag_id in sorted(dagbag.dags.keys()):
    print(f"  [OK] {dag_id}")

# Check for import errors with proper classification
if dagbag.import_errors:
    non_duplicate_errors = []
    duplicate_warnings = []

    for filepath, error in dagbag.import_errors.items():
        error_str = str(error)
        if "DuplicatedIdException" in error_str:
            # Known issue - DAG IDs may appear in multiple files
            duplicate_warnings.append((filepath, error_str))
        else:
            # Real import errors that must be fixed
            non_duplicate_errors.append((filepath, error_str))

    # Report duplicate warnings (don't fail)
    if duplicate_warnings:
        print(f"[WARN] {len(duplicate_warnings)} duplicate DAG ID warnings")

    # Fail on real errors
    if non_duplicate_errors:
        print(f"[ERROR] {len(non_duplicate_errors)} DAG import errors")
        sys.exit(1)

print("[OK] All DAGs validated successfully")
```

**Why DagBag API?**

- Official Airflow validation method
- Catches import errors, dependency issues, and configuration problems
- Properly loads DAGs with all providers and plugins
- Distinguishes between warnings and errors

#### Secondary Validation: lint-dags.sh (ADR Compliance)

The `lint-dags.sh` script enforces project-specific standards:

```bash
# airflow/scripts/lint-dags.sh
# Checks ADR-0045 and ADR-0046 compliance:

# 1. Python syntax validation
# 2. Complex escape sequences in SSH commands
# 3. Non-SSH kcli/virsh commands (ADR-0046)
# 4. DAG ID matches filename (ADR-0045)
# 5. Non-ASCII characters in bash commands
# 6. pylint-airflow checks (if available)
# 7. airflint best practices (if available)
```

#### Local Developer Script: validate-dag.sh

Quick feedback script for developers before commit:

```bash
#!/bin/bash
# airflow/scripts/validate-dag.sh
# Quick local validation - delegates to DagBag API and lint-dags.sh

DAG_FILE="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Python syntax check (fast)
python3 -c "import ast; ast.parse(open('$DAG_FILE').read())"

# 2. DagBag import check (comprehensive)
python3 << PYTHON_SCRIPT
from airflow.models import DagBag
import os
import sys

dag_dir = os.path.dirname('$DAG_FILE') or '.'
dagbag = DagBag(dag_dir, include_examples=False)

if dagbag.import_errors:
    for filepath, error in dagbag.import_errors.items():
        if "DuplicatedIdException" not in str(error):
            print(f"[ERROR] {filepath}: {error}")
            sys.exit(1)

print("[OK] DagBag validation passed")
PYTHON_SCRIPT

# 3. ADR compliance checks
"$SCRIPT_DIR/lint-dags.sh" "$DAG_FILE"
```

#### Pre-commit Hook: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: validate-airflow-dags
        name: Validate Airflow DAGs
        entry: bash -c 'for f in "$@"; do ./airflow/scripts/validate-dag.sh "$f" || exit 1; done' --
        language: system
        files: ^airflow/dags/.*\.py$
        pass_filenames: true
```

#### GitHub Actions Workflow

The comprehensive CI workflow (`.github/workflows/airflow-validate.yml`) performs:

1. **validate-dags job:**

   - Python syntax validation
   - lint-dags.sh (ADR compliance)
   - DagBag API import check with proper error classification

1. **validate-containers job:**

   - docker-compose.yml syntax
   - Container image builds
   - Required files verification

1. **smoke-test job (Full Integration):**

   - PostgreSQL + Marquez service containers
   - Actual DAG execution with OpenLineage
   - Lineage data validation in Marquez
   - Failure path testing
   - Infrastructure DAG structure validation
   - MCP server startup test

```yaml
# Key validation step from airflow-validate.yml
- name: Check Airflow DAG imports
  run: |
    # Use Python DagBag API for reliable import error checking
    # This is the recommended approach per Airflow best practices
    python3 << 'PYTHON_SCRIPT'
    import sys
    from airflow.models import DagBag

    dagbag = DagBag(include_examples=False)

    # Properly classify errors vs warnings
    if dagbag.import_errors:
        non_duplicate_errors = []
        for filepath, error in dagbag.import_errors.items():
            if "DuplicatedIdException" not in str(error):
                non_duplicate_errors.append((filepath, error))

        if non_duplicate_errors:
            print(f"[ERROR] {len(non_duplicate_errors)} DAG import errors")
            sys.exit(1)

    print("[OK] All DAGs validated successfully")
    PYTHON_SCRIPT
```

______________________________________________________________________

## Implementation Plan

### Phase 1: SSH-Based Execution (Completed)

1. ~~Add SSH client to Airflow container Dockerfile~~
1. ~~Configure SSH key sharing between container and host~~
1. ~~Update DAGs to use SSH for Ansible execution~~
1. ~~Document the SSH execution pattern~~

### Phase 2: Validation Scripts (Completed)

1. ~~Create `airflow/scripts/validate-dag.sh` - Quick local validation~~
1. ~~Create `airflow/scripts/lint-dags.sh` - ADR compliance checking~~
1. ~~Add to repository with executable permissions~~
1. ~~Document usage in ADR-0045~~

### Phase 3: CI/CD Integration (Completed)

1. ~~Add pre-commit hook configuration~~
1. ~~Create GitHub Actions workflow (`airflow-validate.yml`)~~
1. ~~Implement Python DagBag API validation~~
1. ~~Add smoke test with DAG execution~~
1. ~~Add OpenLineage/Marquez integration testing~~

### Phase 4: Validation Refinement (Current)

1. Align local `validate-dag.sh` with CI workflow patterns
1. Ensure consistent error classification (DuplicatedIdException handling)
1. Consolidate redundant checks between scripts

______________________________________________________________________

## SSH Execution Pattern

### Container Dockerfile Addition

```dockerfile
# Add SSH client for host execution
RUN apt-get update && apt-get install -y \
    openssh-client \
    && apt-get clean
```

### Docker Compose Volume Mount

```yaml
volumes:
  # Mount SSH keys for host access
  - /root/.ssh:/root/.ssh:ro
  # Mount SSH socket for agent forwarding (optional)
  - ${SSH_AUTH_SOCK:-/dev/null}:/ssh-agent:ro
```

### DAG Pattern for Host Execution

```python
# Task that runs Ansible on host via SSH
run_ansible = BashOperator(
    task_id='run_ansible_on_host',
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

    # Variables
    INVENTORY_DIR="/root/.generated/.idm.example.com"
    PLAYBOOK_DIR="/opt/freeipa-workshop-deployer"

    # Execute Ansible on host via SSH
    ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        root@localhost \
        "cd $PLAYBOOK_DIR && \\
         ANSIBLE_HOST_KEY_CHECKING=False \\
         ansible-playbook \\
         -i $INVENTORY_DIR/inventory \\
         --extra-vars 'domain=example.com' \\
         2_ansible_config/deploy_idm.yaml -v"
    """,
    dag=dag,
)
```

______________________________________________________________________

## Validation Checklist

### Before Submitting a DAG PR

**Quick Local Validation:**

- [ ] Run `./airflow/scripts/validate-dag.sh <dag_file.py>`
- [ ] All validation checks pass (syntax, DagBag, lint)

**ADR Compliance (checked by lint-dags.sh):**

- [ ] No Unicode characters in bash commands (ADR-0045)
- [ ] No string concatenation in bash_command (ADR-0045)
- [ ] DAG ID matches filename (ADR-0045)
- [ ] SSH execution pattern used for kcli/Ansible (ADR-0046)
- [ ] PATH export included for kcli/ansible usage

**Local Testing:**

- [ ] Tested locally with `airflow dags test <dag_id> <date>`

**CI Will Verify:**

- Python DagBag import validation (with proper error classification)
- Full smoke test with DAG execution
- OpenLineage/Marquez integration
- Infrastructure DAG structure validation

______________________________________________________________________

## Consequences

### Positive

- Ansible version consistency with host
- Early error detection before deployment
- Automated validation in CI/CD
- Reduced debugging time
- Better developer experience

### Negative

- SSH setup required between container and host
- Additional validation step in development workflow
- Slightly more complex DAG patterns for Ansible

### Risks

- SSH key security must be managed carefully
- Host must have SSH server running
- Network policies may block localhost SSH

## Automated SSH Configuration

The `deploy-qubinode-with-airflow.sh` script automatically configures SSH access:

```bash
# From deploy-qubinode-with-airflow.sh

# Ensure SSH key exists
if [[ ! -f "$HOME/.ssh/id_rsa" ]]; then
    ssh-keygen -t rsa -b 4096 -f "$HOME/.ssh/id_rsa" -N '' -q
fi

# Add the key to authorized_keys for localhost access
if ! grep -q "$(cat $HOME/.ssh/id_rsa.pub)" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
    cat "$HOME/.ssh/id_rsa.pub" >> "$HOME/.ssh/authorized_keys"
    chmod 600 "$HOME/.ssh/authorized_keys"
fi
```

This ensures the Airflow container can SSH to the host for Ansible execution without manual intervention.

______________________________________________________________________

______________________________________________________________________

## Solution 3: DAG Factory Pattern for Consistent Deployments

**Added:** 2025-12-01
**Status:** Proposed Amendment

### Problem Statement

Even with validation and SSH execution patterns established, contributors still face challenges:

1. **Boilerplate duplication** - Each DAG repeats 50-100 lines of standard configuration
1. **Inconsistent implementations** - Standards from ADR-0045 require manual compliance
1. **High barrier to entry** - Contributors must understand Airflow Python API
1. **Configuration drift** - DAGs diverge over time as patterns evolve

### Decision

Implement a **hybrid DAG Factory Pattern** that provides:

1. **YAML Registry** - Simple deployments defined in configuration (80% of DAGs)
1. **Python Factory** - Complex workflows using factory helper functions (20% of DAGs)

Both approaches enforce ADR-0045 standards automatically and use the SSH execution pattern from this ADR.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAG Generation Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────────────────┐  │
│  │  registry.yaml   │         │  Python DAG using Factory    │  │
│  │  (Simple DAGs)   │         │  (Complex DAGs)              │  │
│  │                  │         │                              │  │
│  │  - freeipa       │         │  - ocp_deployment.py         │  │
│  │  - vyos          │         │  - disconnected_ocp.py       │  │
│  │  - stepca        │         │  - multi_cluster.py          │  │
│  │  - keycloak      │         │                              │  │
│  └────────┬─────────┘         └──────────────┬───────────────┘  │
│           │                                   │                  │
│           ▼                                   ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    dag_factory.py                            ││
│  │  - Enforces ADR-0045 standards                               ││
│  │  - Applies SSH execution pattern (ADR-0046)                  ││
│  │  - Generates consistent BashOperator tasks                   ││
│  │  - Validates configuration before generation                 ││
│  └─────────────────────────────────────────────────────────────┘│
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Generated/Validated DAGs                        ││
│  │  - Consistent naming conventions                             ││
│  │  - Standardized default_args                                 ││
│  │  - Built-in environment validation                           ││
│  │  - Automatic PATH and SSH configuration                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### YAML Registry Schema

Location: `kcli-pipelines/dags/registry.yaml`

```yaml
# DAG Registry - Simple deployments defined here
# Factory auto-generates DAGs from these definitions

version: "1.0"
defaults:
  owner: qubinode
  retries: 2
  retry_delay_minutes: 3

dags:
  # FreeIPA Identity Management
  - component: freeipa
    description: Deploy FreeIPA Identity Management Server
    script_path: /opt/kcli-pipelines/freeipa
    tags: [identity, dns, kerberos, ldap]
    category: identity
    params:
      action: create
      domain: example.com
      realm: EXAMPLE.COM
      idm_hostname: idm.example.com
    volume_mounts:
      - /opt/freeipa-workshop-deployer:/opt/freeipa-workshop-deployer
      - /root/.generated:/root/.generated

  # VyOS Router
  - component: vyos
    description: Deploy VyOS Router for Network Segmentation
    script_path: /opt/kcli-pipelines/vyos-router
    tags: [network, router, firewall]
    category: network
    params:
      action: create
      vyos_version: "1.5"

  # Step-CA PKI
  - component: stepca
    description: Deploy Step-CA PKI for Certificate Management
    script_path: /opt/kcli-pipelines/step-ca
    tags: [security, pki, certificates]
    category: security
    params:
      action: create
      ca_hostname: ca.example.com

  # Keycloak SSO
  - component: keycloak
    description: Deploy Keycloak Identity Provider
    script_path: /opt/kcli-pipelines/keycloak
    tags: [identity, sso, oauth]
    category: identity
    params:
      action: create
      keycloak_version: "24.0"
```

### Registry Validation Rules

```python
# dag_factory.py - validation enforced on all registry entries

REQUIRED_FIELDS = ['component', 'description', 'script_path', 'tags', 'category']
VALID_CATEGORIES = ['compute', 'network', 'identity', 'storage', 'security', 'monitoring']
NAMING_PATTERN = r'^[a-z][a-z0-9_]*$'  # snake_case only

def validate_registry_entry(config: dict) -> list[str]:
    """Validate a DAG configuration before generation."""
    errors = []

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    # Naming convention (ADR-0045 compliance)
    component = config.get('component', '')
    if not re.match(NAMING_PATTERN, component):
        errors.append(f"Component name must be snake_case: {component}")

    # Script path validation
    script_path = config.get('script_path', '')
    if not script_path.startswith('/opt/kcli-pipelines/'):
        errors.append(f"Script path must be in /opt/kcli-pipelines/: {script_path}")

    # Category validation
    category = config.get('category', '')
    if category not in VALID_CATEGORIES:
        errors.append(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")

    # Tags must be non-empty list
    tags = config.get('tags', [])
    if not isinstance(tags, list) or len(tags) == 0:
        errors.append("Tags must be a non-empty list")

    return errors
```

### Factory Implementation

```python
# dag_factory.py - Core factory module

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
import yaml
import re

# Qubinode standard defaults (ADR-0045 compliant)
QUBINODE_DEFAULTS = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}


def create_deployment_dag(
    component: str,
    description: str,
    script_path: str,
    tags: list[str],
    category: str,
    params: dict = None,
    volume_mounts: list[str] = None,
    custom_validation: str = None,
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
        tags: List of tags including category
        category: Component category
        params: Runtime parameters with defaults
        volume_mounts: Required volume mounts (for documentation)
        custom_validation: Additional validation commands

    Returns:
        Configured Airflow DAG
    """
    dag_id = f"{component}_deployment"

    dag = DAG(
        dag_id,
        default_args=QUBINODE_DEFAULTS,
        description=description,
        schedule=None,  # Manual trigger for deployment DAGs
        catchup=False,
        tags=['qubinode', component, category] + [t for t in tags if t not in [component, category]],
        params=params or {'action': 'create'},
        doc_md=f"""
## {component.replace('_', ' ').title()} Deployment

{description}

### Script Location
`{script_path}/deploy.sh`

### Parameters
{yaml.dump(params or {'action': 'create'}, default_flow_style=False)}

### Volume Mounts Required
{chr(10).join(f'- `{m}`' for m in (volume_mounts or []))}

### Related ADRs
- ADR-0045: DAG Development Standards
- ADR-0046: Validation Pipeline and Host Execution
- ADR-0047: kcli-pipelines Integration
        """,
    )

    # Task 1: Environment validation (always included)
    validate_env = BashOperator(
        task_id='validate_environment',
        bash_command=f"""
        echo "========================================"
        echo "Validating environment for {component}"
        echo "========================================"

        export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

        # Check SSH connectivity to host
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@localhost "echo '[OK] SSH to host'" || {{
            echo "[ERROR] Cannot SSH to localhost"
            exit 1
        }}

        # Check script exists
        ssh -o StrictHostKeyChecking=no root@localhost "test -f {script_path}/deploy.sh" || {{
            echo "[ERROR] Deploy script not found: {script_path}/deploy.sh"
            exit 1
        }}

        # Check kcli is available on host
        ssh -o StrictHostKeyChecking=no root@localhost "command -v kcli" || {{
            echo "[WARN] kcli not found on host - some deployments may fail"
        }}

        {custom_validation or ''}

        echo "[OK] Environment validation complete"
        """,
        dag=dag,
    )

    # Task 2: Deploy using SSH execution pattern (ADR-0046)
    deploy = BashOperator(
        task_id=f'deploy_{component}',
        bash_command=f"""
        export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

        echo "========================================"
        echo "Deploying {component}"
        echo "Action: {{{{ params.action }}}}"
        echo "========================================"

        # Build environment variables from params
        ACTION="{{{{ params.action }}}}"

        # Execute deploy.sh on host via SSH (ADR-0046 pattern)
        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \\
            "export ACTION=$ACTION && \\
             cd {script_path} && \\
             ./deploy.sh"

        echo "========================================"
        echo "[OK] {component} deployment complete"
        echo "========================================"
        """,
        dag=dag,
    )

    validate_env >> deploy

    return dag


def load_registry_dags(registry_path: str = '/opt/kcli-pipelines/dags/registry.yaml') -> dict:
    """
    Load and generate all DAGs from the YAML registry.

    Returns:
        Dictionary of dag_id -> DAG objects
    """
    try:
        with open(registry_path) as f:
            registry = yaml.safe_load(f)
    except FileNotFoundError:
        return {}

    dags = {}
    for dag_config in registry.get('dags', []):
        # Validate configuration
        errors = validate_registry_entry(dag_config)
        if errors:
            print(f"[WARN] Skipping invalid DAG config for {dag_config.get('component', 'unknown')}: {errors}")
            continue

        # Generate DAG
        dag = create_deployment_dag(**dag_config)
        dags[dag.dag_id] = dag

    return dags
```

### DAG Loader Module

```python
# kcli-pipelines/dags/dag_loader.py
# This file is placed in the Airflow dags folder and loads all registry DAGs

from dag_factory import load_registry_dags

# Load all DAGs from registry - they become available to Airflow
registry_dags = load_registry_dags()

# Expose DAGs to Airflow's DagBag
for dag_id, dag in registry_dags.items():
    globals()[dag_id] = dag
```

### Python Factory for Complex DAGs

For workflows requiring manual steps, branching, or multi-stage deployments:

```python
# kcli-pipelines/dags/ocp_deployment.py
# Complex DAG using factory helpers

from dag_factory import create_deployment_dag, add_stage, add_manual_step

# Create base DAG with factory
dag = create_deployment_dag(
    component='ocp',
    description='Deploy OpenShift Container Platform',
    script_path='/opt/kcli-pipelines/ocp4-ai-svc-universal',
    tags=['compute', 'kubernetes', 'openshift'],
    category='compute',
    params={
        'action': 'create',
        'cluster_type': 'sno',  # sno, compact, standard
        'ocp_version': '4.14',
    },
)

# Add multi-stage deployment with manual approval
stage1 = add_stage(dag, 'prepare_infrastructure', '01-prepare.sh')
stage2 = add_stage(dag, 'deploy_bootstrap', '02-bootstrap.sh')
stage3 = add_stage(dag, 'deploy_masters', '03-masters.sh')

approval = add_manual_step(
    dag,
    task_id='approve_cluster_ready',
    instructions='Verify cluster bootstrap complete. Check: oc get nodes',
    timeout_hours=4,
)

stage4 = add_stage(dag, 'post_install', '04-post-install.sh')

# Define workflow
stage1 >> stage2 >> stage3 >> approval >> stage4
```

### Helper Functions for Complex DAGs

```python
# dag_factory.py - additional helpers

from airflow.sensors.base import BaseSensorOperator
from airflow.operators.python import BranchPythonOperator


def add_stage(dag: DAG, stage_name: str, script_name: str) -> BashOperator:
    """Add a deployment stage that runs a script via SSH."""
    script_path = dag.params.get('script_path', '/opt/kcli-pipelines')

    return BashOperator(
        task_id=stage_name,
        bash_command=f"""
        export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

        echo "========================================"
        echo "Stage: {stage_name}"
        echo "========================================"

        ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \\
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
) -> BaseSensorOperator:
    """
    Add a manual approval/intervention step.

    The task will wait for manual confirmation before proceeding.
    """
    from airflow.sensors.filesystem import FileSensor

    approval_file = f"/tmp/airflow_approval_{dag.dag_id}_{task_id}"

    # Create instruction task
    show_instructions = BashOperator(
        task_id=f'{task_id}_instructions',
        bash_command=f"""
        echo "========================================"
        echo "MANUAL STEP REQUIRED"
        echo "========================================"
        echo ""
        echo "{instructions}"
        echo ""
        echo "When ready, create approval file:"
        echo "  touch {approval_file}"
        echo ""
        echo "Waiting up to {timeout_hours} hours..."
        echo "========================================"
        """,
        dag=dag,
    )

    # Wait for approval file
    wait_for_approval = FileSensor(
        task_id=task_id,
        filepath=approval_file,
        poke_interval=30,
        timeout=timeout_hours * 3600,
        mode='poke',
        dag=dag,
    )

    # Cleanup approval file
    cleanup = BashOperator(
        task_id=f'{task_id}_cleanup',
        bash_command=f"rm -f {approval_file}",
        dag=dag,
    )

    show_instructions >> wait_for_approval >> cleanup

    return cleanup  # Return last task for chaining


def add_conditional_branch(
    dag: DAG,
    param_name: str,
    branches: dict[str, str],
) -> BranchPythonOperator:
    """
    Add conditional branching based on a parameter value.

    Args:
        dag: Parent DAG
        param_name: Parameter to branch on
        branches: Mapping of param values to task_ids
    """
    def choose_branch(**context):
        param_value = context['params'].get(param_name)
        return branches.get(param_value, list(branches.values())[0])

    return BranchPythonOperator(
        task_id=f'branch_on_{param_name}',
        python_callable=choose_branch,
        dag=dag,
    )
```

### Contributor Guide: Adding a New DAG

This section provides a repeatable, step-by-step process for contributors to add new DAGs.

#### Prerequisites

Before contributing, ensure you have:

- [ ] Fork of kcli-pipelines repository
- [ ] Local clone of your fork
- [ ] Python 3.12+ installed
- [ ] Basic understanding of your component's deployment process

#### Step-by-Step Process for Simple DAGs (YAML Registry)

**Use this process for:** Single-script deployments like FreeIPA, VyOS, Step-CA, Keycloak

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 1: Create Component Directory Structure             │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# Clone your fork
git clone https://github.com/<your-username>/kcli-pipelines.git
cd kcli-pipelines

# Create new branch
git checkout -b add-<component>-dag

# Create component directory
mkdir -p <component>
```

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 2: Create the Deploy Script                         │
└─────────────────────────────────────────────────────────────────┘
```

Create `<component>/deploy.sh` following this template:

```bash
#!/bin/bash
# Component: <component>
# Description: <what this deploys>
# Usage: ACTION=create ./deploy.sh
#
# Environment Variables:
#   ACTION          - create, delete, or status (required)
#   <COMPONENT>_VAR - component-specific variable (optional)
#
# Prerequisites:
#   - kcli installed and configured
#   - Required VM images available

set -euo pipefail

# Source common environment if available
if [ -f /opt/kcli-pipelines/helper_scripts/default.env ]; then
    source /opt/kcli-pipelines/helper_scripts/default.env
fi

# Configuration with defaults
COMPONENT_VERSION="${COMPONENT_VERSION:-1.0.0}"

# Functions
function create() {
    echo "[INFO] Creating <component>..."

    # Your deployment logic here
    # Example: kcli create vm -P image=fedora39 <component>

    echo "[OK] <component> created successfully"
}

function destroy() {
    echo "[INFO] Destroying <component>..."

    # Your cleanup logic here
    # Example: kcli delete vm <component> -y

    echo "[OK] <component> destroyed successfully"
}

function status() {
    echo "[INFO] Checking <component> status..."

    # Your status check logic here
    # Example: kcli list vm | grep <component>
}

# Main entry point
case "${ACTION:-help}" in
    create)  create ;;
    delete|destroy) destroy ;;
    status)  status ;;
    *)
        echo "Usage: ACTION=create|delete|status $0"
        echo ""
        echo "Environment Variables:"
        echo "  ACTION              - Required: create, delete, or status"
        echo "  COMPONENT_VERSION   - Optional: version to deploy (default: 1.0.0)"
        exit 1
        ;;
esac
```

Make it executable:

```bash
chmod +x <component>/deploy.sh
```

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 3: Add README for Your Component                    │
└─────────────────────────────────────────────────────────────────┘
```

Create `<component>/README.md`:

````markdown
# <Component Name>

## Description
Brief description of what this component does and why it's useful.

## Prerequisites
- List prerequisites here
- Required VM images
- Network requirements

## Usage

### Via Airflow DAG
Trigger the `<component>_deployment` DAG from the Airflow UI.

### Via Command Line
```bash
cd /opt/kcli-pipelines/<component>
ACTION=create ./deploy.sh
````

## Parameters

| Parameter         | Default    | Description               |
| ----------------- | ---------- | ------------------------- |
| ACTION            | (required) | create, delete, or status |
| COMPONENT_VERSION | 1.0.0      | Version to deploy         |

## Troubleshooting

Common issues and solutions.

```

```

┌─────────────────────────────────────────────────────────────────┐
│         STEP 4: Add Entry to DAG Registry                        │
└─────────────────────────────────────────────────────────────────┘

````

Edit `dags/registry.yaml` and add your component:

```yaml
  # <Component Name> - Added by <your-name>
  - component: <component>                    # Required: snake_case name
    description: <Brief description>          # Required: what it deploys
    script_path: /opt/kcli-pipelines/<component>  # Required: path to deploy.sh
    tags: [<category>, <keyword1>, <keyword2>]    # Required: for filtering
    category: <category>                      # Required: compute|network|identity|storage|security|monitoring
    params:                                   # Optional: runtime parameters
      action: create
      <component>_version: "1.0.0"
    volume_mounts:                            # Optional: if component needs host paths
      - /path/on/host:/path/in/container
````

**Valid Categories:**

- `compute` - VMs, containers, clusters
- `network` - Routers, firewalls, load balancers
- `identity` - Authentication, authorization, directory services
- `storage` - Persistent storage, backups
- `security` - PKI, secrets management, scanning
- `monitoring` - Logging, metrics, alerting

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 5: Validate Locally                                 │
└─────────────────────────────────────────────────────────────────┘
```

Run local validation before submitting:

```bash
# Install dependencies (one-time)
pip install pyyaml apache-airflow

# Validate your registry entry
python3 -c "
import yaml
import re

REQUIRED_FIELDS = ['component', 'description', 'script_path', 'tags', 'category']
VALID_CATEGORIES = ['compute', 'network', 'identity', 'storage', 'security', 'monitoring']
NAMING_PATTERN = r'^[a-z][a-z0-9_]*$'

with open('dags/registry.yaml') as f:
    registry = yaml.safe_load(f)

# Find your component
component_name = '<component>'  # Replace with your component name
your_entry = next((d for d in registry['dags'] if d.get('component') == component_name), None)

if not your_entry:
    print(f'[ERROR] Component {component_name} not found in registry')
    exit(1)

errors = []
for field in REQUIRED_FIELDS:
    if field not in your_entry:
        errors.append(f'Missing required field: {field}')

if not re.match(NAMING_PATTERN, your_entry.get('component', '')):
    errors.append('Component name must be snake_case')

if your_entry.get('category') not in VALID_CATEGORIES:
    errors.append(f'Invalid category. Must be one of: {VALID_CATEGORIES}')

if errors:
    print('[ERROR] Validation failed:')
    for e in errors:
        print(f'  - {e}')
    exit(1)

print('[OK] Validation passed!')
print(f'Component: {your_entry[\"component\"]}')
print(f'Description: {your_entry[\"description\"]}')
print(f'Category: {your_entry[\"category\"]}')
"

# Test deploy.sh syntax
bash -n <component>/deploy.sh && echo "[OK] Shell syntax valid"

# Test deploy.sh help
ACTION=help ./<component>/deploy.sh
```

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 6: Submit Pull Request                              │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# Commit your changes
git add <component>/ dags/registry.yaml
git commit -m "feat(<component>): Add <component> deployment DAG

- Add deploy.sh script for <component> deployment
- Add registry entry for DAG factory generation
- Add README with usage documentation

Closes #<issue-number>"

# Push to your fork
git push origin add-<component>-dag
```

Create PR with this template:

```markdown
## Summary
Add <component> deployment DAG to kcli-pipelines.

## Component Details
- **Name:** <component>
- **Category:** <category>
- **Description:** <what it deploys>

## Checklist
- [ ] deploy.sh follows the standard template
- [ ] deploy.sh supports ACTION=create|delete|status
- [ ] deploy.sh uses [OK]/[ERROR]/[INFO] log prefixes
- [ ] README.md documents prerequisites and usage
- [ ] Registry entry includes all required fields
- [ ] Local validation passes
- [ ] Tested manually on my system

## Testing Done
Describe how you tested the deployment.
```

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 7: CI Validation (Automatic)                        │
└─────────────────────────────────────────────────────────────────┘
```

GitHub Actions will automatically:

1. Validate registry schema
1. Check Python syntax (if any)
1. Test DAG loading in Airflow
1. Report results on your PR

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 8: After Merge                                      │
└─────────────────────────────────────────────────────────────────┘
```

Once merged, users get your DAG by syncing:

```bash
# Users run this to get new DAGs
cd /opt/kcli-pipelines && git pull

# DAG appears automatically in Airflow UI as: <component>_deployment
```

______________________________________________________________________

#### Step-by-Step Process for Complex DAGs (Python Factory)

**Use this process for:** Multi-stage deployments, manual approval steps, conditional branching (e.g., OpenShift)

Follow Steps 1-3 from above, then:

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 4: Create Python DAG Using Factory                  │
└─────────────────────────────────────────────────────────────────┘
```

Create `dags/<component>_deployment.py`:

```python
"""
Airflow DAG: <Component Name> Deployment
kcli-pipelines integration per ADR-0046/ADR-0047

This DAG deploys <component> using a multi-stage process.
"""

from dag_factory import (
    create_deployment_dag,
    add_stage,
    add_manual_step,
    add_conditional_branch,
)

# Create base DAG using factory
dag = create_deployment_dag(
    component='<component>',
    description='Deploy <Component Name>',
    script_path='/opt/kcli-pipelines/<component>',
    tags=['<category>', '<keyword1>', '<keyword2>'],
    category='<category>',
    params={
        'action': 'create',
        'variant': 'standard',  # Options your component supports
    },
)

# Define stages (each calls a script via SSH)
stage1 = add_stage(dag, 'prepare', '01-prepare.sh')
stage2 = add_stage(dag, 'deploy', '02-deploy.sh')

# Add manual approval if needed
approval = add_manual_step(
    dag,
    task_id='verify_deployment',
    instructions='Verify <component> is running. Check: <verification command>',
    timeout_hours=2,
)

stage3 = add_stage(dag, 'configure', '03-configure.sh')

# Wire up the workflow
stage1 >> stage2 >> approval >> stage3

# Optional: Add conditional branching
# branch = add_conditional_branch(
#     dag,
#     param_name='variant',
#     branches={
#         'standard': 'deploy_standard',
#         'ha': 'deploy_ha',
#     },
# )
```

```
┌─────────────────────────────────────────────────────────────────┐
│         STEP 5: Validate Python DAG Locally                      │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# Check Python syntax
python3 -c "import ast; ast.parse(open('dags/<component>_deployment.py').read())"
echo "[OK] Python syntax valid"

# Test Airflow can load it
python3 -c "
from airflow.models import DagBag
db = DagBag('dags/', include_examples=False)
if '<component>_deployment' in db.dags:
    print('[OK] DAG loaded successfully')
    dag = db.dags['<component>_deployment']
    print(f'Tasks: {[t.task_id for t in dag.tasks]}')
else:
    print('[ERROR] DAG not found')
    if db.import_errors:
        print(f'Import errors: {db.import_errors}')
"
```

Continue with Steps 6-8 from the simple process.

______________________________________________________________________

#### Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAG Contribution Checklist                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  deploy.sh Requirements:                                         │
│  [ ] Shebang: #!/bin/bash                                       │
│  [ ] set -euo pipefail                                          │
│  [ ] Supports ACTION=create|delete|status                       │
│  [ ] Uses [OK]/[ERROR]/[INFO]/[WARN] prefixes                   │
│  [ ] Sources default.env if available                           │
│  [ ] Has usage/help output                                      │
│  [ ] Executable permissions (chmod +x)                          │
│                                                                  │
│  Registry Entry Requirements:                                    │
│  [ ] component: snake_case name                                 │
│  [ ] description: brief description                             │
│  [ ] script_path: /opt/kcli-pipelines/<component>               │
│  [ ] tags: [category, keywords...]                              │
│  [ ] category: compute|network|identity|storage|security|monitoring │
│  [ ] params: at minimum { action: create }                      │
│                                                                  │
│  Documentation:                                                  │
│  [ ] README.md in component directory                           │
│  [ ] Prerequisites listed                                       │
│  [ ] Parameters documented                                      │
│                                                                  │
│  Validation:                                                     │
│  [ ] Local validation passes                                    │
│  [ ] deploy.sh tested manually                                  │
│  [ ] CI checks pass on PR                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Scaffolding Script (Optional Helper)

Contributors can use this script to generate the initial structure:

```bash
#!/bin/bash
# scaffold-dag.sh - Generate DAG contribution scaffolding
# Usage: ./scaffold-dag.sh <component_name> <category> "<description>"

COMPONENT="$1"
CATEGORY="$2"
DESCRIPTION="$3"

if [ -z "$COMPONENT" ] || [ -z "$CATEGORY" ] || [ -z "$DESCRIPTION" ]; then
    echo "Usage: $0 <component_name> <category> \"<description>\""
    echo ""
    echo "Categories: compute, network, identity, storage, security, monitoring"
    echo ""
    echo "Example:"
    echo "  $0 keycloak identity \"Deploy Keycloak Identity Provider\""
    exit 1
fi

# Validate category
case "$CATEGORY" in
    compute|network|identity|storage|security|monitoring) ;;
    *)
        echo "[ERROR] Invalid category: $CATEGORY"
        echo "Valid categories: compute, network, identity, storage, security, monitoring"
        exit 1
        ;;
esac

echo "[INFO] Scaffolding DAG for: $COMPONENT"

# Create directory
mkdir -p "$COMPONENT"

# Create deploy.sh
cat > "$COMPONENT/deploy.sh" << 'DEPLOY_EOF'
#!/bin/bash
# Component: COMPONENT_PLACEHOLDER
# Description: DESCRIPTION_PLACEHOLDER
# Usage: ACTION=create ./deploy.sh

set -euo pipefail

if [ -f /opt/kcli-pipelines/helper_scripts/default.env ]; then
    source /opt/kcli-pipelines/helper_scripts/default.env
fi

function create() {
    echo "[INFO] Creating COMPONENT_PLACEHOLDER..."
    # TODO: Add your deployment logic here
    echo "[OK] COMPONENT_PLACEHOLDER created successfully"
}

function destroy() {
    echo "[INFO] Destroying COMPONENT_PLACEHOLDER..."
    # TODO: Add your cleanup logic here
    echo "[OK] COMPONENT_PLACEHOLDER destroyed successfully"
}

function status() {
    echo "[INFO] Checking COMPONENT_PLACEHOLDER status..."
    # TODO: Add your status check logic here
}

case "${ACTION:-help}" in
    create)  create ;;
    delete|destroy) destroy ;;
    status)  status ;;
    *)
        echo "Usage: ACTION=create|delete|status $0"
        exit 1
        ;;
esac
DEPLOY_EOF

# Replace placeholders
sed -i "s/COMPONENT_PLACEHOLDER/$COMPONENT/g" "$COMPONENT/deploy.sh"
sed -i "s/DESCRIPTION_PLACEHOLDER/$DESCRIPTION/g" "$COMPONENT/deploy.sh"
chmod +x "$COMPONENT/deploy.sh"

# Create README
cat > "$COMPONENT/README.md" << README_EOF
# ${COMPONENT^}

## Description
$DESCRIPTION

## Prerequisites
- kcli installed and configured
- Required VM images available

## Usage

### Via Airflow DAG
Trigger the \`${COMPONENT}_deployment\` DAG from the Airflow UI.

### Via Command Line
\`\`\`bash
cd /opt/kcli-pipelines/$COMPONENT
ACTION=create ./deploy.sh
\`\`\`

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| ACTION | (required) | create, delete, or status |

## Troubleshooting
Add common issues and solutions here.
README_EOF

# Add registry entry (append to file)
echo ""
echo "[INFO] Add this entry to dags/registry.yaml:"
echo ""
cat << REGISTRY_EOF
  # ${COMPONENT^}
  - component: $COMPONENT
    description: $DESCRIPTION
    script_path: /opt/kcli-pipelines/$COMPONENT
    tags: [$CATEGORY, $COMPONENT]
    category: $CATEGORY
    params:
      action: create
REGISTRY_EOF

echo ""
echo "[OK] Scaffolding complete!"
echo ""
echo "Next steps:"
echo "  1. Edit $COMPONENT/deploy.sh with your deployment logic"
echo "  2. Add the registry entry shown above to dags/registry.yaml"
echo "  3. Run local validation"
echo "  4. Submit PR"
```

Usage:

```bash
./scaffold-dag.sh keycloak identity "Deploy Keycloak Identity Provider"
```

### Updated GitHub Actions Validation

```yaml
# .github/workflows/dag-validation.yml (updated)
name: DAG Validation

on:
  pull_request:
    paths:
      - 'dags/**'
      - 'kcli-pipelines/dags/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install apache-airflow==2.10.4 pyyaml

      - name: Validate Registry Schema
        run: |
          python -c "
          import yaml
          import sys
          sys.path.insert(0, 'dags')
          from dag_factory import validate_registry_entry

          with open('dags/registry.yaml') as f:
              registry = yaml.safe_load(f)

          errors = []
          for dag_config in registry.get('dags', []):
              dag_errors = validate_registry_entry(dag_config)
              if dag_errors:
                  errors.extend([f\"{dag_config.get('component')}: {e}\" for e in dag_errors])

          if errors:
              print('Registry validation failed:')
              for e in errors:
                  print(f'  - {e}')
              sys.exit(1)
          print('[OK] Registry validation passed')
          "

      - name: Validate Python DAGs
        run: |
          for dag in dags/*.py; do
            if [ "$dag" != "dags/dag_factory.py" ] && [ "$dag" != "dags/dag_loader.py" ]; then
              echo "Validating $dag..."
              python -c "import ast; ast.parse(open('$dag').read())"
            fi
          done

      - name: Test DAG Loading
        run: |
          python -c "
          from airflow.models import DagBag
          db = DagBag('dags/', include_examples=False)
          if db.import_errors:
              print('DAG import errors:')
              for dag, error in db.import_errors.items():
                  print(f'  {dag}: {error}')
              exit(1)
          print(f'[OK] Loaded {len(db.dags)} DAGs successfully')
          "
```

### Success Metrics

| Metric                      | Target       | Measurement               |
| --------------------------- | ------------ | ------------------------- |
| DAG deployment success rate | >95%         | Airflow task success rate |
| Time to create new DAG      | \<15 minutes | PR submission time        |
| Boilerplate reduction       | >70%         | Lines of code per DAG     |
| Standard compliance         | 100%         | Factory validation        |
| Configuration drift         | 0%           | All DAGs use factory      |
| Contributor onboarding      | \<1 hour     | Time to first DAG PR      |

### When to Use Each Approach

| Use YAML Registry                | Use Python Factory            |
| -------------------------------- | ----------------------------- |
| Single deploy.sh script          | Multi-stage deployments       |
| No manual steps needed           | Manual approval required      |
| Standard create/delete actions   | Conditional branching         |
| FreeIPA, VyOS, Step-CA, Keycloak | OpenShift, Disconnected OCP   |
| New contributors                 | Experienced Python developers |

______________________________________________________________________

## Related ADRs

- ADR-0037: Git-Based DAG Repository Management
- ADR-0040: DAG Distribution from kcli-pipelines
- ADR-0043: Airflow Container Host Network Access
- ADR-0044: User-Configurable Airflow Volume Mounts
- ADR-0045: Airflow DAG Development Standards
- ADR-0047: kcli-pipelines as DAG Source Repository

## References

- Apache Airflow Best Practices
- Pre-commit framework documentation
- GitHub Actions workflow syntax
- [Factory Pattern - Design Patterns](https://refactoring.guru/design-patterns/factory-method)
- [GitOps Principles](https://opengitops.dev/)
