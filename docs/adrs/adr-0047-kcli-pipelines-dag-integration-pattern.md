# ADR-0047: kcli-pipelines as DAG Source Repository

**Status:** Proposed  
**Date:** 2025-11-27  
**Authors:** Qubinode Team  
**Supersedes:** None  
**Related:** ADR-0039, ADR-0040, ADR-0045, ADR-0046

## Context

Currently, Airflow DAGs contain embedded bash scripts that duplicate logic already present in kcli-pipelines deployment scripts. This creates:

1. **Code duplication** - Same deployment logic in two places
2. **Maintenance burden** - Updates needed in both DAG and deploy.sh
3. **Inconsistency** - DAG and CLI deployments may behave differently
4. **Harder contributions** - Users must understand both Airflow and bash

The kcli-pipelines repository already contains well-tested deployment scripts for:
- VyOS Router (`vyos-router/deploy.sh`)
- FreeIPA (`freeipa/deploy.sh` via freeipa-workshop-deployer)
- OpenShift (`ocp4-ai-svc-universal/`)
- And many other infrastructure components

## Decision

**kcli-pipelines will be the canonical source for deployment logic, and Airflow DAGs will call these scripts via SSH to the host.**

### Architecture

```
+---------------------------+     +---------------------------+
|   qubinode_navigator      |     |      kcli-pipelines       |
+---------------------------+     +---------------------------+
| - ADRs & Standards        |     | - deploy.sh scripts       |
| - DAG templates           |     | - Ansible playbooks       |
| - Airflow infrastructure  |     | - Configuration files     |
| - Documentation           |     | - User-contributed DAGs   |
+---------------------------+     +---------------------------+
            |                                  |
            v                                  v
+----------------------------------------------------------+
|                    Airflow DAGs                           |
|  - Call kcli-pipelines scripts via SSH (ADR-0046)        |
|  - Handle workflow orchestration                          |
|  - Provide UI for triggering and monitoring              |
|  - Wait for manual steps when required                    |
+----------------------------------------------------------+
```

### DAG Pattern

DAGs should follow this pattern:

```python
# Task calls kcli-pipelines deploy.sh via SSH to host
deploy_task = BashOperator(
    task_id='deploy_component',
    bash_command='''
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    
    # Set environment variables for the script
    export ACTION="{{ params.action }}"
    export VYOS_VERSION="{{ params.vyos_version }}"
    
    # Execute kcli-pipelines script on host via SSH (ADR-0046)
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "cd /opt/kcli-pipelines/vyos-router && \
         export ACTION=$ACTION && \
         export VYOS_VERSION=$VYOS_VERSION && \
         ./deploy.sh"
    ''',
    dag=dag,
)
```

### Repository Structure

```
kcli-pipelines/
├── dags/                          # Airflow DAGs (distributed to Airflow)
│   ├── freeipa_deployment.py
│   ├── vyos_router_deployment.py
│   ├── ocp_initial_deployment.py
│   └── README.md
├── vyos-router/
│   ├── deploy.sh                  # Canonical deployment script
│   ├── vyos-config.sh             # VyOS configuration script
│   └── README.md
├── freeipa/
│   ├── deploy.sh
│   └── README.md
├── helper_scripts/
│   ├── default.env
│   └── common.sh
└── README.md
```

### Contribution Workflow

1. **User creates deployment script** in kcli-pipelines
2. **User creates DAG** that calls the script
3. **DAG follows qubinode-navigator standards** (ADR-0045)
4. **PR submitted** to kcli-pipelines
5. **DAG validated** using `validate-dag.sh`
6. **Merged** and available to all users

### Standards for kcli-pipelines Scripts

Scripts in kcli-pipelines must:

1. **Support ACTION variable** - `create`, `delete`, `status`
2. **Use environment variables** for configuration
3. **Source default.env** if available
4. **Print clear status messages** with `[OK]`, `[ERROR]`, `[WARN]` prefixes
5. **Exit with proper codes** - 0 for success, non-zero for failure
6. **Document manual steps** clearly when required
7. **Be idempotent** - safe to run multiple times

Example script structure:

```bash
#!/bin/bash
# Component: vyos-router
# Description: Deploy VyOS router for network segmentation
# Usage: ACTION=create ./deploy.sh

set -euo pipefail

# Source common environment
if [ -f /opt/kcli-pipelines/helper_scripts/default.env ]; then
    source /opt/kcli-pipelines/helper_scripts/default.env
fi

# Configuration with defaults
COMPONENT_VERSION=${COMPONENT_VERSION:-"1.0.0"}

function create() {
    echo "[INFO] Creating component..."
    # Implementation
    echo "[OK] Component created"
}

function destroy() {
    echo "[INFO] Destroying component..."
    # Implementation
    echo "[OK] Component destroyed"
}

function status() {
    echo "[INFO] Checking component status..."
    # Implementation
}

# Main
case "${ACTION:-help}" in
    create) create ;;
    delete|destroy) destroy ;;
    status) status ;;
    *) echo "Usage: ACTION=create|delete|status $0" ;;
esac
```

### DAG Distribution

DAGs are stored in `kcli-pipelines/dags/` and distributed to Airflow via:

1. **Volume mount** - `/opt/kcli-pipelines/dags` mounted to Airflow
2. **Git sync** - Airflow pulls from kcli-pipelines repo
3. **Manual copy** - `deploy-qubinode-with-airflow.sh` copies DAGs

## Consequences

### Positive

- **Single source of truth** - Deployment logic in one place
- **Easier contributions** - Users familiar with bash can contribute
- **Consistent behavior** - CLI and DAG use same scripts
- **Better testing** - Scripts can be tested independently
- **Reusability** - Scripts work with or without Airflow
- **Community growth** - kcli-pipelines becomes a pipeline marketplace

### Negative

- **SSH dependency** - DAGs require SSH access to host
- **Two repositories** - Logic split between repos
- **Version coordination** - DAG and script versions must match

### Risks

- Script changes may break DAGs
- SSH connectivity issues affect DAG execution
- Environment variable mismatches between DAG and script

## Migration Plan

1. **Phase 1**: Update existing DAGs to call kcli-pipelines scripts
   - VyOS router DAG → calls `vyos-router/deploy.sh`
   - FreeIPA DAG → calls freeipa-workshop-deployer scripts

2. **Phase 2**: Document contribution guidelines
   - Script standards
   - DAG template
   - Testing requirements

3. **Phase 3**: Add validation
   - Script linting
   - DAG validation in CI/CD
   - Integration tests

## Implementation

### Update VyOS DAG to Call deploy.sh

```python
create_vyos_vm = BashOperator(
    task_id='create_vyos_vm',
    bash_command='''
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    
    ACTION="create"
    VYOS_VERSION="{{ params.vyos_version }}"
    
    # Execute kcli-pipelines script on host via SSH
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "export ACTION=$ACTION && \
         export VYOS_VERSION=$VYOS_VERSION && \
         cd /opt/kcli-pipelines/vyos-router && \
         ./deploy.sh"
    ''',
    dag=dag,
)
```

### Add DAG Contribution Template

Create `kcli-pipelines/dags/TEMPLATE.py`:

```python
"""
Airflow DAG: [Component Name]
kcli-pipelines integration per ADR-0047

This DAG calls kcli-pipelines/[component]/deploy.sh
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

KCLI_PIPELINES_DIR = '/opt/kcli-pipelines'
COMPONENT_DIR = 'component-name'

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

dag = DAG(
    'component_deployment',
    default_args=default_args,
    description='Deploy [Component] via kcli-pipelines',
    schedule=None,
    catchup=False,
    tags=['qubinode', 'kcli-pipelines'],
    params={
        'action': 'create',
    },
)

deploy = BashOperator(
    task_id='deploy',
    bash_command=f'''
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    
    ACTION="{{{{ params.action }}}}"
    
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "export ACTION=$ACTION && \
         cd {KCLI_PIPELINES_DIR}/{COMPONENT_DIR} && \
         ./deploy.sh"
    ''',
    dag=dag,
)
```

---

## Related ADRs

- **ADR-0039**: FreeIPA and VyOS Airflow DAG Integration
- **ADR-0040**: DAG Distribution from kcli-pipelines
- **ADR-0045**: Airflow DAG Development Standards
- **ADR-0046**: DAG Validation Pipeline and Host-Based Execution

## References

- [kcli-pipelines Repository](https://github.com/tosin2013/kcli-pipelines)
- [Qubinode Navigator](https://github.com/Qubinode/qubinode_navigator)
- [Airflow BashOperator](https://airflow.apache.org/docs/apache-airflow/stable/howto/operator/bash.html)
