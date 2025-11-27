---
layout: default
title: ADR-0039 FreeIPA and VyOS Airflow DAG Integration
parent: Infrastructure & Deployment
grand_parent: Architectural Decision Records
nav_order: 39
---

# ADR-0039: FreeIPA and VyOS Router Airflow DAG Integration

**Status:** Accepted  
**Date:** 2025-11-27  
**Decision Makers:** Platform Team, DevOps Team  
**Related ADRs:** ADR-0036 (Airflow Integration), ADR-0037 (Git-Based DAG Repository)

## Context and Problem Statement

The Qubinode Navigator platform needs to automate the deployment of FreeIPA identity management servers and VyOS routers as part of infrastructure provisioning workflows. Currently, these deployments are handled by shell scripts in the `kcli-pipelines` repository:

- **FreeIPA**: `/root/kcli-pipelines/freeipa/deploy-freeipa.sh` - Deploys FreeIPA using the `freeipa-workshop-deployer` project
- **VyOS Router**: `/root/kcli-pipelines/vyos-router/deploy.sh` - Deploys VyOS router with multiple network interfaces

**Key Challenges:**
1. Manual script execution lacks orchestration, monitoring, and retry capabilities
2. No integration with Airflow workflow engine for scheduling and dependencies
3. VyOS deployment uses outdated rolling release (`1.5-rolling-202409250007`)
4. FreeIPA deployer uses RHEL 8/CentOS 8 Stream (approaching end-of-life)
5. No standardized DAG distribution mechanism from kcli-pipelines to qubinode_navigator

## Decision Drivers

* Enable workflow orchestration for infrastructure provisioning
* Provide visibility into deployment status via Airflow UI
* Support both create and destroy operations with proper cleanup
* Maintain compatibility with existing kcli-pipelines scripts
* Enable DAG synchronization from kcli-pipelines repository
* Update to current OS versions and VyOS releases

## Decision Outcome

**Chosen approach:** Create dedicated Airflow DAGs for FreeIPA and VyOS deployments that wrap existing kcli-pipelines scripts, with a Git-based synchronization mechanism.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    kcli-pipelines Repository                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  /dags/                                                      ││
│  │  ├── freeipa_deployment.py                                   ││
│  │  ├── vyos_router_deployment.py                               ││
│  │  └── dag_sync_config.yaml                                    ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  /freeipa/                                                   ││
│  │  ├── deploy-freeipa.sh                                       ││
│  │  └── template.yaml                                           ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  /vyos-router/                                               ││
│  │  ├── deploy.sh                                               ││
│  │  └── vyos-config.sh                                          ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ sync-dags.sh
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  qubinode_navigator/airflow/dags/                │
│  ├── freeipa_deployment.py                                       │
│  ├── vyos_router_deployment.py                                   │
│  └── (other existing DAGs)                                       │
└─────────────────────────────────────────────────────────────────┘
```

### FreeIPA DAG Design

```python
# DAG: freeipa_deployment
# Tasks:
# 1. validate_environment - Check prerequisites
# 2. clone_freeipa_deployer - Clone/update freeipa-workshop-deployer
# 3. configure_deployment - Set up vars.sh with environment config
# 4. create_freeipa_vm - Create VM using kcli
# 5. configure_freeipa - Run Ansible configuration
# 6. configure_dns - Update DNS settings
# 7. validate_deployment - Verify FreeIPA is operational
```

### VyOS DAG Design

```python
# DAG: vyos_router_deployment
# Tasks:
# 1. validate_environment - Check prerequisites
# 2. create_libvirt_networks - Create isolated networks (1924-1928)
# 3. download_vyos_iso - Download VyOS ISO if not present
# 4. create_vyos_vm - Create VM with multiple NICs
# 5. wait_for_boot - Wait for VyOS to boot
# 6. configure_vyos - Apply network configuration
# 7. add_host_routes - Configure host routing
# 8. validate_connectivity - Test network connectivity
```

## Implementation Details

### 1. DAG Synchronization Script

Create `/root/kcli-pipelines/scripts/sync-dags-to-qubinode.sh`:

```bash
#!/bin/bash
# Sync DAGs from kcli-pipelines to qubinode_navigator
KCLI_PIPELINES_DIR="${KCLI_PIPELINES_DIR:-/opt/kcli-pipelines}"
QUBINODE_DAGS_DIR="${QUBINODE_DAGS_DIR:-/root/qubinode_navigator/airflow/dags}"

# Copy DAGs with validation
for dag in "$KCLI_PIPELINES_DIR/dags/"*.py; do
    python3 -m py_compile "$dag" && cp "$dag" "$QUBINODE_DAGS_DIR/"
done
```

### 2. VyOS Version Update

Update from `1.5-rolling-202409250007` to latest stable or LTS release:
- Check https://github.com/vyos/vyos-rolling-nightly-builds/releases for latest
- Consider using VyOS 1.4 LTS for production stability

### 3. FreeIPA Base OS Update

Update `freeipa-workshop-deployer` to support:
- RHEL 9.x as primary platform
- CentOS 9 Stream as community alternative
- Maintain RHEL 8 support during transition period

## Positive Consequences

* **Orchestration**: Full Airflow workflow capabilities (retries, dependencies, scheduling)
* **Visibility**: Deployment status visible in Airflow UI
* **Maintainability**: DAGs stored in kcli-pipelines with version control
* **Reusability**: DAGs can be triggered via API, CLI, or UI
* **Consistency**: Standardized deployment patterns across infrastructure
* **Auditability**: Complete execution logs and history

## Negative Consequences

* **Complexity**: Additional layer between scripts and execution
* **Dependencies**: Requires Airflow infrastructure to be operational
* **Learning Curve**: Team needs familiarity with Airflow DAG development
* **Sync Overhead**: DAG synchronization adds maintenance burden

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Script compatibility | High | Wrap existing scripts, don't rewrite |
| VyOS version instability | Medium | Pin to tested version, document upgrade path |
| OS migration issues | Medium | Phased rollout, maintain dual support |
| DAG sync failures | Low | Validation before copy, rollback capability |

## Implementation Plan

### Phase 1: DAG Development (Week 1)
- [ ] Create `freeipa_deployment.py` DAG
- [ ] Create `vyos_router_deployment.py` DAG
- [ ] Create `sync-dags-to-qubinode.sh` script
- [ ] Test DAGs in development environment

### Phase 2: Version Updates (Week 2)
- [ ] Update VyOS to latest stable release
- [ ] Update freeipa-workshop-deployer for RHEL 9
- [ ] Test updated deployments

### Phase 3: Integration (Week 3)
- [ ] Integrate DAG sync into CI/CD pipeline
- [ ] Document DAG usage and parameters
- [ ] Create MCP tool integration for DAG triggering

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| DAG execution success rate | >95% | Airflow metrics |
| Deployment time (FreeIPA) | <15 minutes | Task duration |
| Deployment time (VyOS) | <10 minutes | Task duration |
| DAG sync reliability | 100% | Sync script logs |

## References

* [kcli-pipelines Repository](https://github.com/Qubinode/kcli-pipelines)
* [freeipa-workshop-deployer](https://github.com/Qubinode/freeipa-workshop-deployer)
* [VyOS Documentation](https://docs.vyos.io/)
* ADR-0036: Apache Airflow Workflow Orchestration Integration
* ADR-0037: Git-Based DAG Repository Management

---

**This ADR establishes the foundation for automated infrastructure provisioning via Airflow! 🚀**
