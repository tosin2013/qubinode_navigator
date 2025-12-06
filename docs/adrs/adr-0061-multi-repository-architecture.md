# ADR-0061: Multi-Repository Architecture and qubinode-pipelines

**Status:** Proposed
**Date:** 2025-12-05
**Authors:** Qubinode Team
**Supersedes:** Portions of ADR-0040, ADR-0047
**Related:** ADR-0040, ADR-0045, ADR-0046, ADR-0047, ADR-0062

## Context and Problem Statement

The Qubinode ecosystem has evolved to include multiple repositories with overlapping responsibilities:

- **qubinode_navigator**: Airflow platform, ADRs, validation tools
- **kcli-pipelines**: Deployment scripts and (per ADR-0040/0047) DAGs
- **ocp4-disconnected-helper**: OCP automation playbooks and DAGs

External teams integrating with qubinode_navigator have reported confusion about:

1. Which repository is the "source of truth" for DAGs
1. Where to contribute new DAGs
1. The role of kcli-pipelines vs qubinode_navigator
1. How external projects should integrate

Additionally, the name "kcli-pipelines" causes confusion:

- Implies only kcli-related content
- Doesn't reflect its role as a workflow repository
- Users wonder if kcli is required

## Decision

### 1. Rename kcli-pipelines to qubinode-pipelines

The repository `https://github.com/Qubinode/kcli-pipelines` will be renamed to `https://github.com/Qubinode/qubinode-pipelines`.

**Rationale:**

- Aligns with Qubinode ecosystem naming
- Clarifies purpose as a pipelines/workflow repository
- Removes implication that kcli is required
- Better reflects the middleware role between domain projects and the platform

### 2. Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TIER 1: DOMAIN PROJECTS                              │
│  (ocp4-disconnected-helper, freeipa-workshop-deployer, user projects)   │
│                                                                          │
│  Responsibilities:                                                       │
│  - Domain-specific playbooks and automation                              │
│  - Testing and validation of domain logic                                │
│  - Contributing DAGs upstream to qubinode-pipelines                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ PR-based contribution
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    TIER 2: QUBINODE-PIPELINES                            │
│                    (middleware / DAG registry)                           │
│                                                                          │
│  Responsibilities:                                                       │
│  - Deployment scripts (deploy.sh, configure-*.sh)                        │
│  - Deployment DAGs for infrastructure components                         │
│  - DAG registry manifest (registry.yaml)                                 │
│  - Community-contributed workflows                                       │
│                                                                          │
│  Does NOT own:                                                           │
│  - Platform infrastructure (Airflow, containers)                         │
│  - Core platform DAGs (RAG, monitoring)                                  │
│  - ADRs and development standards                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Volume mount at /opt/qubinode-pipelines
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   TIER 3: QUBINODE_NAVIGATOR                             │
│                    (platform / runtime)                                  │
│                                                                          │
│  Responsibilities:                                                       │
│  - Airflow platform infrastructure                                       │
│  - Core platform DAGs (rag_*.py, monitoring, health checks)              │
│  - ADRs..... development standards, and validation tools                 │
│  - AI Assistant service                                                  │
│  - MCP server                                                            │
│                                                                          │
│  Does NOT own:                                                           │
│  - Deployment scripts                                                    │
│  - Infrastructure deployment DAGs                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Repository Responsibility Matrix

| Artifact                                                    | Owner                     | Contributors    |
| ----------------------------------------------------------- | ------------------------- | --------------- |
| Airflow docker-compose, containers                          | qubinode_navigator        | -               |
| ADRs and development standards                              | qubinode_navigator        | All projects    |
| Validation tools (validate-dag.sh, lint-dags.sh)            | qubinode_navigator        | -               |
| Core platform DAGs (rag\_\*.py, monitoring)                 | qubinode_navigator        | -               |
| AI Assistant service                                        | qubinode_navigator        | -               |
| MCP server                                                  | qubinode_navigator        | -               |
| Deployment scripts (deploy.sh)                              | qubinode-pipelines        | Domain projects |
| Infrastructure DAGs (ocp\_*.py, freeipa\_*.py, vyos\_\*.py) | qubinode-pipelines        | Domain projects |
| DAG registry manifest                                       | qubinode-pipelines        | All projects    |
| OCP playbooks and automation                                | ocp4-disconnected-helper  | -               |
| FreeIPA playbooks                                           | freeipa-workshop-deployer | -               |

### 4. DAG Categories and Locations

| DAG Category        | Location                         | Examples                                               |
| ------------------- | -------------------------------- | ------------------------------------------------------ |
| **Platform DAGs**   | qubinode_navigator/airflow/dags/ | rag_bootstrap.py, rag_document_ingestion.py            |
| **Deployment DAGs** | qubinode-pipelines/dags/         | ocp\_*.py, freeipa\_*.py, vyos\_*.py, generic_vm\_*.py |

### 5. Integration Pattern

External projects integrate via **PR-based contribution**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  CONTRIBUTION WORKFLOW                                                    │
└──────────────────────────────────────────────────────────────────────────┘

1. DEVELOP locally in domain project
   ┌─────────────────────────────────┐
   │  ocp4-disconnected-helper/      │
   │  ├── playbooks/                 │  ← Domain automation
   │  └── airflow/dags/              │  ← Local DAG development
   │      └── ocp_new_feature.py     │
   └─────────────────────────────────┘

2. TEST using qubinode_navigator validation tools
   $ ./airflow/scripts/validate-dag.sh airflow/dags/ocp_new_feature.py

3. SUBMIT PR to qubinode-pipelines
   ┌─────────────────────────────────┐
   │  qubinode-pipelines/            │
   │  └── dags/ocp/                  │  ← PR target
   │      └── ocp_new_feature.py     │
   └─────────────────────────────────┘

4. CI VALIDATES the DAG
   - Python syntax check
   - Airflow import validation
   - ADR-0045 compliance (lint-dags.sh)
   - Integration test (optional)

5. MERGE and available to all users
   - DAG appears in Airflow UI
   - registry.yaml updated automatically
```

### 6. CI/CD Cross-Repository Validation

The `airflow-validate.yml` workflow validates DAGs from **both repositories** together, ensuring integrated compatibility:

**What CI validates:**

- Platform DAGs from `qubinode_navigator/airflow/dags/`
- Deployment DAGs from `qubinode-pipelines/dags/{category}/`
- ADR-0045/ADR-0046 compliance for all DAGs
- Airflow DagBag import validation

**Manual trigger with specific pipelines version:**

```bash
# Test against a specific qubinode-pipelines branch
gh workflow run airflow-validate.yml -f pipelines_ref=develop

# Or via GitHub Actions UI:
# Actions → Airflow Validation → Run workflow → Enter branch/tag/SHA
```

**Workflow inputs:**

| Input           | Description                               | Default |
| --------------- | ----------------------------------------- | ------- |
| `pipelines_ref` | Branch, tag, or SHA of qubinode-pipelines | `main`  |

This enables:

- Testing changes in either repo against the other
- Validating PRs before merge
- Coordinating releases between repositories

### 7. Directory Structure After Refactoring

**qubinode_navigator:**

```
qubinode_navigator/
├── airflow/
│   ├── dags/
│   │   ├── rag_bootstrap.py           # Platform DAG
│   │   ├── rag_document_ingestion.py  # Platform DAG
│   │   ├── dag_factory.py             # DAG factory (loads from registry)
│   │   └── dag_loader.py              # Discovers DAGs from pipelines
│   ├── scripts/
│   │   ├── validate-dag.sh
│   │   └── lint-dags.sh
│   └── docker-compose.yml
├── ai-assistant/
├── docs/adrs/
└── scripts/
```

**qubinode-pipelines (renamed from kcli-pipelines):**

```
qubinode-pipelines/
├── dags/
│   ├── registry.yaml                  # DAG manifest
│   ├── ocp/
│   │   ├── ocp_initial_deployment.py
│   │   ├── ocp_agent_deployment.py
│   │   ├── ocp_disconnected_workflow.py
│   │   ├── ocp_incremental_update.py
│   │   ├── ocp_pre_deployment_validation.py
│   │   └── ocp_registry_sync.py
│   ├── infrastructure/
│   │   ├── freeipa_deployment.py
│   │   ├── vyos_router_deployment.py
│   │   └── generic_vm_deployment.py
│   └── README.md
├── scripts/
│   ├── vyos-router/
│   │   └── deploy.sh
│   ├── freeipa/
│   │   └── deploy.sh
│   ├── step-ca-server/
│   │   └── register-step-ca.sh
│   └── helper_scripts/
│       └── default.env
└── README.md
```

### 7. Volume Mount Changes

Update `docker-compose.yml`:

```yaml
# Before (kcli-pipelines)
- /opt/kcli-pipelines:/opt/kcli-pipelines:ro

# After (qubinode-pipelines)
- /opt/qubinode-pipelines:/opt/qubinode-pipelines:ro
```

Symlink for backward compatibility:

```bash
ln -sf /opt/qubinode-pipelines /opt/kcli-pipelines
```

## Migration Plan

### Phase 1: Repository Rename (Week 1)

1. Rename GitHub repository: `kcli-pipelines` → `qubinode-pipelines`
1. GitHub will auto-redirect old URLs
1. Update all documentation references
1. Create backward-compatible symlinks

### Phase 2: DAG Migration (Week 2)

1. Move deployment DAGs from qubinode_navigator to qubinode-pipelines:

   - ocp\_\*.py → qubinode-pipelines/dags/ocp/
   - freeipa\_\*.py → qubinode-pipelines/dags/infrastructure/
   - vyos\_\*.py → qubinode-pipelines/dags/infrastructure/
   - generic_vm\_\*.py → qubinode-pipelines/dags/infrastructure/

1. Keep platform DAGs in qubinode_navigator:

   - rag\_\*.py (stay)
   - dag_factory.py (stay)
   - dag_loader.py (stay)

1. Update dag_loader.py to discover DAGs from /opt/qubinode-pipelines/dags/

### Phase 3: ADR Updates (Week 2)

1. Update ADR-0040: Reference qubinode-pipelines, clarify sync is via volume mount
1. Update ADR-0047: Clarify deployment scripts vs platform code separation
1. Create ADR-0062: External project integration guide

### Phase 4: External Project Notification (Week 3)

1. Notify ocp4-disconnected-helper team of new architecture
1. Provide migration guide for their ADRs
1. Accept first PR for OCP DAGs to validate workflow

## Consequences

### Positive

- **Clear ownership**: Each repository has defined responsibilities
- **Easier contribution**: External projects know where to contribute
- **Better naming**: qubinode-pipelines reflects actual purpose
- **Separation of concerns**: Platform vs workflows clearly separated
- **Scalability**: New domain projects can easily integrate

### Negative

- **Migration effort**: Need to move DAGs and update references
- **Two repos to clone**: Users need both qubinode_navigator and qubinode-pipelines
- **Backward compatibility**: Old scripts referencing /opt/kcli-pipelines need updates

### Risks

- GitHub redirect may not work for all git operations
- Users with existing installations need migration instructions
- CI/CD pipelines referencing old paths will break

## Success Metrics

| Metric                 | Target                         | Measurement     |
| ---------------------- | ------------------------------ | --------------- |
| External project PRs   | 5+ in first quarter            | GitHub PR count |
| Documentation clarity  | No "confusion" issues          | GitHub issues   |
| Migration completion   | 100% within 4 weeks            | Checklist       |
| Backward compatibility | Zero breaking changes reported | Issue tracker   |

## References

- [GitHub Repository Rename Documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository)
- ADR-0040: DAG Distribution Strategy
- ADR-0047: kcli-pipelines as DAG Source Repository
- ADR-0062: External Project Integration Guide (companion ADR)

______________________________________________________________________

**This ADR establishes the foundation for a scalable, contributor-friendly Qubinode ecosystem.**
