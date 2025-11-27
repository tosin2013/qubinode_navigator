---
layout: default
title: ADR-0040 DAG Distribution from kcli-pipelines
parent: Configuration & Automation
grand_parent: Architectural Decision Records
nav_order: 40
---

# ADR-0040: DAG Distribution Strategy from kcli-pipelines Repository

**Status:** Accepted  
**Date:** 2025-11-27  
**Decision Makers:** Platform Team, DevOps Team  
**Related ADRs:** ADR-0037 (Git-Based DAG Repository), ADR-0039 (FreeIPA/VyOS DAG Integration)

## Context and Problem Statement

The `kcli-pipelines` repository (https://github.com/Qubinode/kcli-pipelines) contains infrastructure deployment scripts that need to be converted to Airflow DAGs. Users need a mechanism to:

1. Store DAGs in the kcli-pipelines repository alongside related scripts
2. Synchronize DAGs to their local qubinode_navigator installation
3. Receive updates when new DAGs are added or existing ones are modified
4. Validate DAGs before deployment to prevent runtime errors

**Current State:**
- DAGs are manually created in `/root/qubinode_navigator/airflow/dags/`
- No standardized distribution mechanism exists
- kcli-pipelines contains shell scripts but no DAGs yet

## Decision Drivers

* Enable community contribution of DAGs via kcli-pipelines
* Provide simple sync mechanism for users
* Maintain DAG quality through validation
* Support both manual and automated synchronization
* Preserve local customizations when syncing

## Decision Outcome

**Chosen approach:** Implement a pull-based DAG distribution system with a sync script that users can run manually or schedule via cron/systemd timer.

### Repository Structure

```
kcli-pipelines/
├── dags/                           # Airflow DAG definitions
│   ├── README.md                   # DAG documentation
│   ├── requirements.txt            # Python dependencies for DAGs
│   ├── freeipa_deployment.py       # FreeIPA deployment DAG
│   ├── vyos_router_deployment.py   # VyOS router deployment DAG
│   └── __init__.py                 # Package marker
├── scripts/
│   └── sync-dags-to-qubinode.sh    # Sync script
├── freeipa/                        # FreeIPA deployment scripts
├── vyos-router/                    # VyOS deployment scripts
└── ...
```

### Sync Script Design

```bash
#!/bin/bash
# sync-dags-to-qubinode.sh
# 
# Synchronizes DAGs from kcli-pipelines to qubinode_navigator
# 
# Usage:
#   ./sync-dags-to-qubinode.sh [options]
#
# Options:
#   --source DIR      Source directory (default: /opt/kcli-pipelines/dags)
#   --target DIR      Target directory (default: $QUBINODE_DAGS_DIR or auto-detect)
#   --validate        Validate DAGs before copying (default: true)
#   --backup          Backup existing DAGs before sync (default: true)
#   --dry-run         Show what would be done without making changes
#   --force           Overwrite local modifications
```

### Sync Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Workflow                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Clone/Update kcli-pipelines                                  │
│     git clone https://github.com/Qubinode/kcli-pipelines.git    │
│     OR: git -C /opt/kcli-pipelines pull                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Run Sync Script                                              │
│     /opt/kcli-pipelines/scripts/sync-dags-to-qubinode.sh        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Sync Process                                                 │
│     a. Validate Python syntax of each DAG                        │
│     b. Check for import errors                                   │
│     c. Backup existing DAGs (optional)                           │
│     d. Copy validated DAGs to target directory                   │
│     e. Report sync status                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Airflow Detects New DAGs                                     │
│     - Scheduler picks up new/modified DAGs                       │
│     - DAGs appear in Airflow UI                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Details

### Sync Script Features

1. **Validation**: Python syntax check and import validation
2. **Backup**: Timestamped backup of existing DAGs before overwrite
3. **Selective Sync**: Option to sync specific DAGs only
4. **Conflict Detection**: Warn about local modifications
5. **Dry Run**: Preview changes without applying
6. **Logging**: Detailed sync logs for troubleshooting

### Integration with Qubinode Navigator

Add MCP tool for DAG synchronization:

```python
# In qubinode-airflow MCP server
@mcp.tool()
async def sync_dags_from_kcli_pipelines(
    source_repo: str = "https://github.com/Qubinode/kcli-pipelines.git",
    branch: str = "main",
    validate: bool = True,
    backup: bool = True
) -> str:
    """
    Synchronize DAGs from kcli-pipelines repository.
    
    Args:
        source_repo: Git repository URL
        branch: Branch to sync from
        validate: Validate DAGs before copying
        backup: Backup existing DAGs
    
    Returns:
        Sync status report
    """
```

### Automated Sync Options

#### Option 1: Systemd Timer
```ini
# /etc/systemd/system/qubinode-dag-sync.timer
[Unit]
Description=Sync DAGs from kcli-pipelines daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

#### Option 2: Cron Job
```bash
# /etc/cron.d/qubinode-dag-sync
0 2 * * * root /opt/kcli-pipelines/scripts/sync-dags-to-qubinode.sh --validate --backup
```

#### Option 3: Git Hook (for developers)
```bash
# .git/hooks/post-merge
#!/bin/bash
if git diff-tree --name-only -r HEAD@{1} HEAD | grep -q "^dags/"; then
    echo "DAGs changed, running sync..."
    /opt/kcli-pipelines/scripts/sync-dags-to-qubinode.sh
fi
```

## Positive Consequences

* **Community Contribution**: Easy for users to contribute DAGs via PR
* **Version Control**: DAGs tracked in Git with full history
* **Validation**: Syntax errors caught before deployment
* **Flexibility**: Users can customize sync behavior
* **Discoverability**: Central location for all infrastructure DAGs
* **Documentation**: DAGs documented alongside related scripts

## Negative Consequences

* **Manual Step**: Users must run sync (unless automated)
* **Potential Conflicts**: Local modifications may be overwritten
* **Network Dependency**: Requires Git access for updates
* **Maintenance**: Sync script needs maintenance

## Alternatives Considered

### Git Submodule
- **Pros**: Automatic version tracking
- **Cons**: Complex for users, merge conflicts

### Package Distribution (PyPI)
- **Pros**: Standard Python packaging
- **Cons**: Overkill for DAG files, slower updates

### Shared Volume Mount
- **Pros**: Real-time sync
- **Cons**: Requires infrastructure changes, no validation

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Sync success rate | >99% | Script exit codes |
| Validation accuracy | 100% | No invalid DAGs deployed |
| User adoption | 80% use sync | Usage analytics |
| Sync time | <30 seconds | Script timing |

## References

* [kcli-pipelines Repository](https://github.com/Qubinode/kcli-pipelines)
* ADR-0037: Git-Based DAG Repository Management
* ADR-0039: FreeIPA and VyOS Airflow DAG Integration

---

**This ADR enables seamless DAG distribution from the community repository! 📦**
