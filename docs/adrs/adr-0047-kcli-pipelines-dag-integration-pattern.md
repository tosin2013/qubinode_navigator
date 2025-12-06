# ADR-0047: qubinode-pipelines as Deployment Script Repository

**Status:** Accepted (Amended 2025-12-05)
**Date:** 2025-11-27 (Amended: 2025-12-05)
**Authors:** Qubinode Team
**Supersedes:** None
**Related:** ADR-0039, ADR-0040, ADR-0045, ADR-0046, ADR-0061, ADR-0062

> **Amendment Notice (2025-12-05):** This ADR has been updated to:
>
> 1. Reflect the repository rename from `kcli-pipelines` to `qubinode-pipelines`
> 1. Clarify that qubinode-pipelines owns **deployment scripts AND deployment DAGs**
> 1. Distinguish from platform DAGs which remain in qubinode_navigator
>    See ADR-0061 for the full multi-repository architecture.

## Context

Currently, Airflow DAGs contain embedded bash scripts that duplicate logic already present in deployment scripts. This creates:

1. **Code duplication** - Same deployment logic in two places
1. **Maintenance burden** - Updates needed in both DAG and deploy.sh
1. **Inconsistency** - DAG and CLI deployments may behave differently
1. **Harder contributions** - Users must understand both Airflow and bash

The qubinode-pipelines repository (formerly kcli-pipelines) contains well-tested deployment scripts for:

- VyOS Router (`vyos-router/deploy.sh`)
- FreeIPA (`freeipa/deploy.sh` via freeipa-workshop-deployer)
- OpenShift (`ocp4-ai-svc-universal/`)
- And many other infrastructure components

## Decision

**qubinode-pipelines is the canonical source for:**

1. **Deployment scripts** (deploy.sh files) - The actual automation logic
1. **Deployment DAGs** (ocp\_*.py, freeipa\_*.py, etc.) - Airflow orchestration for deployments

**qubinode_navigator owns:**

1. **Platform DAGs** (rag\_\*.py, monitoring) - Core platform functionality
1. **Airflow infrastructure** - docker-compose, validation tools
1. **ADRs and standards** - Development guidelines

**DAGs call deployment scripts via SSH to the host (per ADR-0046).**

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TIER 1: DOMAIN PROJECTS                           │
│         (ocp4-disconnected-helper, freeipa-workshop-deployer)           │
│                                                                          │
│  Own: Domain-specific playbooks, automation logic                        │
│  Contribute: DAGs and scripts to qubinode-pipelines via PR              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ PR-based contribution
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TIER 2: QUBINODE-PIPELINES                          │
│                  (formerly kcli-pipelines - middleware)                  │
│                                                                          │
│  Own:                                                                    │
│  - Deployment scripts (scripts/*/deploy.sh)                              │
│  - Deployment DAGs (dags/ocp/*.py, dags/infrastructure/*.py)            │
│  - DAG registry (dags/registry.yaml)                                     │
│                                                                          │
│  Mounted at: /opt/qubinode-pipelines                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Volume mount
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     TIER 3: QUBINODE_NAVIGATOR                           │
│                        (platform / runtime)                              │
│                                                                          │
│  Own:                                                                    │
│  - Airflow infrastructure (docker-compose, containers)                   │
│  - Platform DAGs (rag_*.py, dag_factory.py, dag_loader.py)              │
│  - ADRs, standards, validation tools                                     │
│  - AI Assistant, MCP server                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### DAG Pattern

DAGs should follow this pattern:

```python
# Task calls qubinode-pipelines deploy.sh via SSH to host
deploy_task = BashOperator(
    task_id='deploy_component',
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

    # Set environment variables for the script
    export ACTION="{{ params.action }}"
    export VYOS_VERSION="{{ params.vyos_version }}"

    # Execute qubinode-pipelines script on host via SSH (ADR-0046)
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "cd /opt/qubinode-pipelines/vyos-router && \
         export ACTION=$ACTION && \
         export VYOS_VERSION=$VYOS_VERSION && \
         ./deploy.sh"
    """,
    dag=dag,
)
```

### Repository Structure

```
qubinode-pipelines/                 # Renamed from kcli-pipelines
├── dags/                           # Deployment DAGs
│   ├── registry.yaml               # DAG manifest
│   ├── ocp/                        # OCP deployment DAGs
│   │   ├── ocp_initial_deployment.py
│   │   ├── ocp_agent_deployment.py
│   │   ├── ocp_disconnected_workflow.py
│   │   ├── ocp_incremental_update.py
│   │   ├── ocp_pre_deployment_validation.py
│   │   └── ocp_registry_sync.py
│   ├── infrastructure/             # Infrastructure DAGs
│   │   ├── freeipa_deployment.py
│   │   ├── vyos_router_deployment.py
│   │   └── generic_vm_deployment.py
│   └── README.md
├── scripts/                        # Deployment scripts
│   ├── vyos-router/
│   │   ├── deploy.sh               # Canonical deployment script
│   │   └── vyos-config.sh
│   ├── freeipa/
│   │   └── deploy.sh
│   └── helper_scripts/
│       ├── default.env
│       └── common.sh
└── README.md
```

### Contribution Workflow

1. **Developer creates deployment script** in their domain project
1. **Developer creates DAG** that calls the script via SSH
1. **DAG follows qubinode_navigator standards** (ADR-0045)
1. **Developer validates** using `validate-dag.sh` and `lint-dags.sh`
1. **PR submitted** to qubinode-pipelines
1. **CI validates** and maintainers review
1. **Merged** and available to all users via volume mount

See ADR-0062 for detailed external project integration guidance.

### CI/CD Cross-Repository Validation

The `airflow-validate.yml` workflow in qubinode_navigator validates DAGs from **both repositories**:

```bash
# Trigger manually with specific qubinode-pipelines branch
gh workflow run airflow-validate.yml -f pipelines_ref=develop
```

**What gets validated:**

- Platform DAGs from `qubinode_navigator/airflow/dags/`
- Deployment DAGs from `qubinode-pipelines/dags/{category}/`
- ADR-0045/ADR-0046 compliance for all DAGs
- Airflow DagBag import validation

This ensures changes in either repository don't break the integrated system.

### Standards for qubinode-pipelines Scripts

Scripts in qubinode-pipelines must:

1. **Support ACTION variable** - `create`, `delete`, `status`
1. **Use environment variables** for configuration
1. **Source default.env** if available
1. **Print clear status messages** with `[OK]`, `[ERROR]`, `[WARN]` prefixes
1. **Exit with proper codes** - 0 for success, non-zero for failure
1. **Document manual steps** clearly when required
1. **Be idempotent** - safe to run multiple times

Example script structure:

```bash
#!/bin/bash
# Component: vyos-router
# Description: Deploy VyOS router for network segmentation
# Usage: ACTION=create ./deploy.sh

set -euo pipefail

# Source common environment
if [ -f /opt/qubinode-pipelines/scripts/helper_scripts/default.env ]; then
    source /opt/qubinode-pipelines/scripts/helper_scripts/default.env
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

DAGs are stored in `qubinode-pipelines/dags/` and distributed to Airflow via volume mount:

```yaml
# docker-compose.yml
volumes:
  - /opt/qubinode-pipelines:/opt/qubinode-pipelines:ro
```

The dag_loader.py in qubinode_navigator discovers and loads DAGs from the mounted directory.

## Consequences

### Positive

- **Single source of truth** - Deployment logic in one place (qubinode-pipelines)
- **Clear separation** - Platform vs deployment concerns separated
- **Easier contributions** - External projects contribute via PR
- **Consistent behavior** - CLI and DAG use same scripts
- **Better testing** - Scripts can be tested independently
- **Reusability** - Scripts work with or without Airflow
- **Community growth** - qubinode-pipelines becomes a pipeline marketplace

### Negative

- **SSH dependency** - DAGs require SSH access to host
- **Two repositories** - Users must clone both repos
- **Version coordination** - DAG and script versions must match
- **PR latency** - Contributions require review before availability

### Risks

- Script changes may break DAGs
- SSH connectivity issues affect DAG execution
- Environment variable mismatches between DAG and script
- Migration from kcli-pipelines name may cause temporary confusion

## Migration Plan

### Phase 1: Repository Rename

1. Rename GitHub repository: `kcli-pipelines` → `qubinode-pipelines`
1. GitHub auto-redirects old URLs
1. Update all documentation references
1. Create backward-compatible symlink: `/opt/kcli-pipelines` → `/opt/qubinode-pipelines`

### Phase 2: DAG Migration

1. Move deployment DAGs from qubinode_navigator to qubinode-pipelines:

   - ocp\_\*.py → qubinode-pipelines/dags/ocp/
   - freeipa\_\*.py → qubinode-pipelines/dags/infrastructure/
   - vyos\_\*.py → qubinode-pipelines/dags/infrastructure/

1. Update dag_loader.py to discover DAGs from /opt/qubinode-pipelines/dags/

### Phase 3: External Project Integration

1. Notify external projects (ocp4-disconnected-helper) of new architecture
1. Accept first PR contributions to validate workflow
1. Update CI/CD to validate contributions

## Implementation

### Update VyOS DAG to Call deploy.sh

```python
create_vyos_vm = BashOperator(
    task_id='create_vyos_vm',
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

    ACTION="create"
    VYOS_VERSION="{{ params.vyos_version }}"

    # Execute qubinode-pipelines script on host via SSH
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "export ACTION=$ACTION && \
         export VYOS_VERSION=$VYOS_VERSION && \
         cd /opt/qubinode-pipelines/scripts/vyos-router && \
         ./deploy.sh"
    """,
    dag=dag,
)
```

### Add DAG Contribution Template

Create `qubinode-pipelines/dags/TEMPLATE.py`:

```python
"""
Airflow DAG: [Component Name]
qubinode-pipelines integration per ADR-0047

This DAG calls qubinode-pipelines/scripts/[component]/deploy.sh
Category: infrastructure  # or: ocp, networking, storage, security
Contributed by: [your-project-name]
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

PIPELINES_DIR = '/opt/qubinode-pipelines'
COMPONENT_DIR = 'component-name'

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

dag = DAG(
    'component_deployment',  # Must match filename: component_deployment.py
    default_args=default_args,
    description='Deploy [Component] via qubinode-pipelines',
    schedule=None,
    catchup=False,
    tags=['qubinode', 'infrastructure'],  # Use appropriate category tag
    params={
        'action': 'create',
    },
)

deploy = BashOperator(
    task_id='deploy',
    bash_command="""
    set -euo pipefail

    ACTION="{{ params.action }}"

    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "export ACTION=$ACTION && \
         cd /opt/qubinode-pipelines/scripts/component-name && \
         ./deploy.sh"

    echo "[OK] Component deployment completed"
    """,
    dag=dag,
)
```

______________________________________________________________________

## Related ADRs

- **ADR-0039**: FreeIPA and VyOS Airflow DAG Integration
- **ADR-0040**: DAG Distribution from qubinode-pipelines
- **ADR-0045**: Airflow DAG Development Standards
- **ADR-0046**: DAG Validation Pipeline and Host-Based Execution
- **ADR-0061**: Multi-Repository Architecture
- **ADR-0062**: External Project Integration Guide

## References

- [qubinode-pipelines Repository](https://github.com/Qubinode/qubinode-pipelines)
- [Qubinode Navigator](https://github.com/Qubinode/qubinode_navigator)
- [Airflow BashOperator](https://airflow.apache.org/docs/apache-airflow/stable/howto/operator/bash.html)

______________________________________________________________________

**This ADR establishes qubinode-pipelines as the canonical source for deployment scripts and DAGs.**
