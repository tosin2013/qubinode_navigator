# Response to ocp4-disconnected-helper Integration Team

**From:** Qubinode Navigator Team
**To:** ocp4-disconnected-helper Integration Team
**Date:** December 5, 2025
**Subject:** Architecture Clarification and Integration Path

______________________________________________________________________

## Executive Summary

Thank you for the detailed feedback document. You identified real architectural ambiguities in our documentation. We've addressed these by:

1. **Renaming** `kcli-pipelines` to `qubinode-pipelines` for clarity
1. **Creating new ADRs** (0061, 0062) that define the multi-repository architecture
1. **Updating existing ADRs** (0040, 0047) to reflect the actual implementation
1. **Establishing clear ownership** for DAGs and scripts

______________________________________________________________________

## Answers to Your Questions

### Priority 1: DAG Source of Truth

**Answer: qubinode-pipelines is the source for deployment DAGs**

```
┌─────────────────────────────────────────────────────────────────┐
│  YOUR PROJECT (ocp4-disconnected-helper)                        │
│                                                                  │
│  You maintain:                                                   │
│  - OCP-specific playbooks                                        │
│  - Domain automation logic                                       │
│                                                                  │
│  You contribute (via PR):                                        │
│  - DAGs to qubinode-pipelines/dags/ocp/                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ PR-based contribution
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  QUBINODE-PIPELINES (middleware)                                │
│                                                                  │
│  Canonical source for:                                           │
│  - Deployment DAGs (ocp_*.py, freeipa_*.py, etc.)               │
│  - Deployment scripts (deploy.sh)                               │
│  - DAG registry                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Volume mount
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  QUBINODE_NAVIGATOR (platform)                                  │
│                                                                  │
│  Canonical source for:                                           │
│  - Platform DAGs (rag_*.py only)                                │
│  - Airflow infrastructure                                        │
│  - ADRs, standards, validation tools                            │
└─────────────────────────────────────────────────────────────────┘
```

**Action for you:** Update your ADR-0014 to say ocp4-disconnected-helper **contributes DAGs to** qubinode-pipelines, not "replaces kcli-pipelines".

### Priority 2: kcli-pipelines Status

**Answer: Being renamed to qubinode-pipelines, active and canonical for deployment DAGs**

| Status       | Description                                |
| ------------ | ------------------------------------------ |
| **Active**   | Repository is actively maintained          |
| **Renaming** | `kcli-pipelines` → `qubinode-pipelines`    |
| **Role**     | Middleware for deployment DAGs and scripts |

**Why the rename?**

- "kcli-pipelines" implied only kcli-related content
- "qubinode-pipelines" reflects its role in the ecosystem
- Removes confusion about whether kcli is required

**Action for you:** Update references from `/opt/kcli-pipelines` to `/opt/qubinode-pipelines`. A symlink will be provided for backward compatibility.

### Priority 3: Integration Documentation

**Answer: Created! See ADR-0062**

We've created a comprehensive External Project Integration Guide (ADR-0062) that covers:

1. **DAG Contribution Workflow** - Step-by-step PR process
1. **Source of Truth Rules** - Who owns what
1. **Testing Requirements** - Using validate-dag.sh and lint-dags.sh
1. **DAG Categories** - Where to place your DAGs (dags/ocp/, dags/infrastructure/, etc.)

______________________________________________________________________

## Addressing Your Confusion Points

### 1. "Contradictory Documentation About kcli-pipelines"

**Resolved.** We've updated ADRs to clarify:

- **ADR-0047 now says:** "qubinode-pipelines is the canonical source for deployment scripts AND deployment DAGs"
- **Your ADR-0014 should say:** "Airflow orchestrates deployments via qubinode-pipelines" (not "replaces")

### 2. "Unclear DAG Synchronization Direction"

**Resolved.** The flow is now:

```
ocp4-disconnected-helper ────PR────> qubinode-pipelines ────mount────> qubinode_navigator
                                          │
                                          └── Canonical source for OCP DAGs
```

No sync scripts needed - volume mount provides real-time access.

### 3. "Missing ocp_agent_deployment.py"

**Explanation:** This DAG currently exists in qubinode_navigator because we haven't completed the migration to qubinode-pipelines yet.

**Plan:** All OCP DAGs will be moved to `qubinode-pipelines/dags/ocp/` during migration. Your team can help by submitting updated versions via PR.

### 4. "Three-Tier vs Two-Tier Architecture"

**Resolved.** We've documented the three-tier architecture in ADR-0061:

```
TIER 1: Domain Projects (ocp4-disconnected-helper, freeipa-workshop-deployer)
        │
        └── Contribute DAGs and domain logic

TIER 2: qubinode-pipelines (middleware)
        │
        └── Hosts deployment DAGs and scripts

TIER 3: qubinode_navigator (platform)
        │
        └── Provides Airflow runtime and platform DAGs
```

______________________________________________________________________

## What We've Done

### New ADRs Created

| ADR          | Title                              | Purpose                                       |
| ------------ | ---------------------------------- | --------------------------------------------- |
| **ADR-0061** | Multi-Repository Architecture      | Defines three-tier architecture and ownership |
| **ADR-0062** | External Project Integration Guide | Step-by-step guide for your team              |

### ADRs Updated

| ADR          | Changes                                                                       |
| ------------ | ----------------------------------------------------------------------------- |
| **ADR-0040** | Renamed references to qubinode-pipelines, clarified volume mount approach     |
| **ADR-0047** | Clarified deployment scripts vs platform separation, added three-tier diagram |

______________________________________________________________________

## What You Should Do

### Immediate Actions

1. **Update your ADR-0014:**

   - Change "Airflow Replaces kcli-pipelines" to "Airflow Orchestrates via qubinode-pipelines"
   - Reference qubinode_navigator ADR-0061 and ADR-0062

1. **Update your architecture diagram:**

   - Show three-tier relationship
   - Indicate PR-based contribution flow

1. **Prepare OCP DAGs for contribution:**

   - Ensure all DAGs pass `validate-dag.sh` and `lint-dags.sh`
   - Add category docstrings per ADR-0062

### When qubinode-pipelines is Ready

1. **Fork qubinode-pipelines**
1. **Add your OCP DAGs** to `dags/ocp/`:
   - ocp_initial_deployment.py
   - ocp_agent_deployment.py
   - ocp_disconnected_workflow.py
   - ocp_incremental_update.py
   - ocp_pre_deployment_validation.py
   - ocp_registry_sync.py
1. **Submit PR** with validation evidence
1. **We review and merge**
1. **DAGs become available** to all qubinode_navigator users

______________________________________________________________________

## Migration Timeline

| Phase       | Task                                       | Target |
| ----------- | ------------------------------------------ | ------ |
| **Phase 1** | Rename kcli-pipelines → qubinode-pipelines | Week 1 |
| **Phase 2** | Move deployment DAGs to qubinode-pipelines | Week 2 |
| **Phase 3** | Accept first external PRs (your OCP DAGs)  | Week 3 |
| **Phase 4** | Full documentation update                  | Week 4 |

______________________________________________________________________

## Response to Your Proposed Solutions

| Your Proposal                  | Our Decision                            |
| ------------------------------ | --------------------------------------- |
| **Git Submodule**              | Not implementing - adds complexity      |
| **DAG Registry Configuration** | Partially implemented via registry.yaml |
| **Unified Sync Script**        | Not needed - volume mount is simpler    |

______________________________________________________________________

## Open Items for Discussion

1. **OCP DAG Differences:** The 5 OCP DAGs that differ between repos - should we use your versions as the canonical source and migrate them to qubinode-pipelines?

1. **ocp_agent_deployment.py:** This is currently missing from your repo. Should we provide it to you, or is this intentional?

1. **Testing:** Would you like access to our CI validation before the formal PR process is set up?

______________________________________________________________________

## Contact

Please reach out with any questions. We're happy to:

- Review your DAGs before formal PR
- Provide early access to qubinode-pipelines rename
- Schedule a call to discuss integration

Thank you for the detailed feedback - it helped us improve our documentation significantly.

______________________________________________________________________

## Attached ADRs

The following new/updated ADRs are available in qubinode_navigator:

- `docs/adrs/adr-0061-multi-repository-architecture.md` (NEW)
- `docs/adrs/adr-0062-external-project-integration-guide.md` (NEW)
- `docs/adrs/adr-0040-dag-distribution-from-kcli-pipelines.md` (UPDATED)
- `docs/adrs/adr-0047-kcli-pipelines-dag-integration-pattern.md` (UPDATED)
