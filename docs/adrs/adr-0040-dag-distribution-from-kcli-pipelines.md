______________________________________________________________________

## layout: default title: ADR-0040 DAG Distribution from qubinode-pipelines parent: Configuration & Automation grand_parent: Architectural Decision Records nav_order: 40

# ADR-0040: DAG Distribution Strategy from qubinode-pipelines Repository

**Status:** Accepted (Amended 2025-12-05)
**Date:** 2025-11-27 (Amended: 2025-12-05)
**Decision Makers:** Platform Team, DevOps Team
**Related ADRs:** ADR-0037, ADR-0039, ADR-0061 (Multi-Repository Architecture), ADR-0062 (External Integration)

> **Amendment Notice (2025-12-05):** This ADR has been updated to reflect the repository rename from `kcli-pipelines` to `qubinode-pipelines` and the adoption of volume-mount-based DAG distribution instead of sync scripts. See ADR-0061 for the full multi-repository architecture.

## Context and Problem Statement

The `qubinode-pipelines` repository (https://github.com/Qubinode/qubinode-pipelines, formerly kcli-pipelines) serves as the middleware layer for deployment DAGs and scripts. Users need a mechanism to:

1. Access deployment DAGs from a central repository
1. Receive updates when new DAGs are added or existing ones are modified
1. Validate DAGs before deployment to prevent runtime errors
1. Contribute new DAGs via PR-based workflow

**Current State (Updated 2025-12-05):**

- Platform DAGs (rag\_\*.py) live in qubinode_navigator/airflow/dags/
- Deployment DAGs live in qubinode-pipelines/dags/
- qubinode-pipelines is mounted at /opt/qubinode-pipelines via volume mount
- External projects contribute DAGs via PR to qubinode-pipelines

## Decision Drivers

- Enable community contribution of DAGs via qubinode-pipelines
- Provide automatic DAG availability via volume mount
- Maintain DAG quality through validation
- Support PR-based contribution workflow
- Clear separation between platform and deployment DAGs

## Decision Outcome

**Chosen approach:** Volume-mount-based DAG distribution where qubinode-pipelines is cloned to /opt/qubinode-pipelines and mounted into the Airflow container. External projects contribute DAGs via PR to qubinode-pipelines.

### Repository Structure

```
qubinode-pipelines/                 # Renamed from kcli-pipelines
├── dags/                           # Airflow DAG definitions
│   ├── registry.yaml               # DAG manifest for discovery
│   ├── ocp/                        # OCP deployment DAGs
│   │   ├── ocp_initial_deployment.py
│   │   ├── ocp_agent_deployment.py
│   │   ├── ocp_disconnected_workflow.py
│   │   └── ...
│   ├── infrastructure/             # Infrastructure DAGs
│   │   ├── freeipa_deployment.py
│   │   ├── vyos_router_deployment.py
│   │   └── generic_vm_deployment.py
│   └── README.md
├── scripts/                        # Deployment scripts
│   ├── vyos-router/
│   │   └── deploy.sh
│   ├── freeipa/
│   │   └── deploy.sh
│   └── helper_scripts/
│       └── default.env
└── README.md
```

### Volume Mount Configuration

The qubinode-pipelines repository is mounted directly into the Airflow container:

```yaml
# docker-compose.yml
services:
  airflow-worker:
    volumes:
      - /opt/qubinode-pipelines:/opt/qubinode-pipelines:ro
```

### DAG Discovery Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    INSTALLATION WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Clone qubinode-pipelines                                     │
│     git clone https://github.com/Qubinode/qubinode-pipelines    │
│         /opt/qubinode-pipelines                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Deploy qubinode_navigator                                    │
│     ./deploy-qubinode-with-airflow.sh                           │
│     (mounts /opt/qubinode-pipelines automatically)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. DAG Loader discovers DAGs                                    │
│     - Reads /opt/qubinode-pipelines/dags/registry.yaml          │
│     - Imports DAGs from categorized directories                  │
│     - Validates against ADR-0045 standards                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Airflow UI shows available DAGs                              │
│     - Platform DAGs from qubinode_navigator                      │
│     - Deployment DAGs from qubinode-pipelines                    │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                      UPDATE WORKFLOW                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Pull latest changes                                          │
│     git -C /opt/qubinode-pipelines pull                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Airflow automatically detects changes                        │
│     (scheduler rescans DAG directory)                           │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Details

### DAG Loader Configuration

The dag_loader.py in qubinode_navigator discovers DAGs from qubinode-pipelines:

```python
# airflow/dags/dag_loader.py
import os
from pathlib import Path

PIPELINES_DAG_DIR = '/opt/qubinode-pipelines/dags'
CATEGORIES = ['ocp', 'infrastructure', 'networking', 'storage', 'security']

def discover_dags():
    """Discover all DAGs from qubinode-pipelines."""
    for category in CATEGORIES:
        category_path = Path(PIPELINES_DAG_DIR) / category
        if category_path.exists():
            for dag_file in category_path.glob('*.py'):
                # Import and register DAG
                pass
```

### Contribution Workflow

External projects contribute DAGs via PR to qubinode-pipelines:

```
┌─────────────────────────────────────────────────────────────────┐
│                   CONTRIBUTION WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Develop DAG locally in your project                          │
│     your-project/airflow/dags/your_component.py                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Validate using qubinode_navigator tools                      │
│     ./airflow/scripts/validate-dag.sh your_component.py         │
│     ./airflow/scripts/lint-dags.sh your_component.py            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Submit PR to qubinode-pipelines                              │
│     Fork → Add DAG to dags/<category>/ → Create PR              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. CI validates and maintainers review                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Merge and DAG becomes available to all users                 │
└─────────────────────────────────────────────────────────────────┘
```

See ADR-0062 for detailed external project integration guidance.

### Automated Update Options

#### Option 1: Systemd Timer (Recommended)

```ini
# /etc/systemd/system/qubinode-pipelines-update.timer
[Unit]
Description=Update qubinode-pipelines daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/qubinode-pipelines-update.service
[Unit]
Description=Update qubinode-pipelines repository

[Service]
Type=oneshot
ExecStart=/usr/bin/git -C /opt/qubinode-pipelines pull --ff-only
```

#### Option 2: Cron Job

```bash
# /etc/cron.d/qubinode-pipelines-update
0 2 * * * root git -C /opt/qubinode-pipelines pull --ff-only
```

## Positive Consequences

- **Community Contribution**: Easy for users to contribute DAGs via PR
- **Version Control**: DAGs tracked in Git with full history
- **Validation**: Syntax errors caught before deployment via CI
- **Automatic Discovery**: Volume mount means no manual sync needed
- **Discoverability**: Central location for all deployment DAGs
- **Clear Separation**: Platform DAGs vs deployment DAGs clearly separated

## Negative Consequences

- **Two Repositories**: Users must clone both qubinode_navigator and qubinode-pipelines
- **PR Latency**: New DAGs require PR review before availability
- **Network Dependency**: Requires Git access for updates

## Alternatives Considered

### Git Submodule

- **Pros**: Automatic version tracking, single clone
- **Cons**: Complex for users, merge conflicts, harder contribution

### Package Distribution (PyPI)

- **Pros**: Standard Python packaging
- **Cons**: Overkill for DAG files, slower updates

### Sync Script (Original Design)

- **Pros**: Explicit control over what gets deployed
- **Cons**: Manual step required, script maintenance burden

**Decision**: Volume mount chosen for simplicity and automatic updates.

## Backward Compatibility

For existing installations using `/opt/kcli-pipelines`:

```bash
# Create symlink for backward compatibility
ln -sf /opt/qubinode-pipelines /opt/kcli-pipelines
```

This ensures existing DAGs referencing `/opt/kcli-pipelines` continue to work.

## Success Metrics

| Metric              | Target       | Measurement              |
| ------------------- | ------------ | ------------------------ |
| DAG discovery rate  | 100%         | All DAGs appear in UI    |
| Validation accuracy | 100%         | No invalid DAGs deployed |
| PR merge time       | \<48 hours   | GitHub metrics           |
| External PRs        | 5+ quarterly | GitHub PR count          |

## References

- [qubinode-pipelines Repository](https://github.com/Qubinode/qubinode-pipelines)
- ADR-0037: Git-Based DAG Repository Management
- ADR-0039: FreeIPA and VyOS Airflow DAG Integration
- ADR-0061: Multi-Repository Architecture
- ADR-0062: External Project Integration Guide

______________________________________________________________________

**This ADR enables seamless DAG distribution from the community repository via volume mount.**
