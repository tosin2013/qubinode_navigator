______________________________________________________________________

## layout: default title: ADR-0025 Ansible ToolingTooling Modernization parent: Configuration & Automation grand_parent: Architectural Decision Records nav_order: 0025

# ADR-0025: Ansible Tooling Stack Modernization and Security Update Strategy

## Status

Accepted - Implemented (2025-11-11)

## Context

Research conducted in July 2025 revealed critical security vulnerabilities and compatibility issues in the current Ansible tooling stack. CVE-2024-11079 in ansible-core versions prior to 2.18.1 enables arbitrary code execution, requiring immediate remediation. Additionally, RHEL 9.6's default Python 3.9 is incompatible with ansible-navigator v25.5.0+ which requires Python 3.10+.

The current execution environment configuration lacks version pinning and uses inconsistent base images, creating reproducibility and security risks across the multi-cloud infrastructure deployment platform. Galaxy API failures during collection installation have highlighted the need for robust dependency management strategies.

Current state analysis shows:

- No explicit version pinning for ansible-navigator, ansible-builder, or ansible-core
- Inconsistent execution environment configurations (localhost:0.1.0 vs quay.io:0.8.0)
- RHEL 9.6 Python 3.9 incompatibility with latest tooling
- Critical security vulnerability requiring immediate attention
- Collection dependency management failures due to Galaxy API issues

## Decision

Implement comprehensive Ansible tooling modernization with mandatory security updates:

1. **Immediate Security Update**: Upgrade to ansible-core 2.18.1+ to address CVE-2024-11079
1. **Tooling Modernization**: Adopt ansible-navigator v25.5.0 and ansible-builder v3.1.0
1. **Base Image Standardization**: Use Red Hat UBI 9 minimal (`registry.access.redhat.com/ubi9/ubi-minimal`) with Python 3.11/3.12
1. **Version Pinning**: Implement strict version pinning for all collections and dependencies
1. **Dependency Management**: Establish Private Automation Hub or Git-based collection sources as fallback
1. **Security Lifecycle**: Implement bi-weekly execution environment rebuilds for security updates
1. **Playbook Refactoring**: Update all playbooks to use explicit boolean conditional logic
1. **Automated Scanning**: Implement vulnerability scanning and dependency management

## Consequences

### Positive

- **Security**: Eliminates critical CVE-2024-11079 arbitrary code execution vulnerability
- **Enterprise Compliance**: UBI 9 standardization provides enterprise support and continuous security updates
- **Reliability**: Improved build success rate through robust dependency management
- **Consistency**: Standardized execution environments across RHEL 9.6, Rocky Linux, and Fedora
- **Long-term Support**: Enables predictable update lifecycle and maintenance
- **Multi-Cloud Compatibility**: Ensures consistent behavior across Equinix Metal, Hetzner Cloud, and bare-metal

### Negative

- **Migration Effort**: Requires significant playbook refactoring for conditional logic changes
- **Temporary Disruption**: Potential service interruption during migration phase
- **Complexity**: Increased execution environment management overhead
- **Tool Compatibility**: AnsibleSafe tool may require updates or workflow changes
- **Training**: Team members need to understand new tooling and procedures

## Alternatives Considered

1. **Maintain Current Versions**: Rejected due to critical security vulnerability and compatibility issues
1. **Partial Upgrade (ansible-core 2.17.x only)**: Insufficient to address Python compatibility requirements
1. **Red Hat Automation Platform Migration**: Too heavyweight and costly for current project needs
1. **Custom Tooling Development**: Would create maintenance burden and delay security fixes

## Evidence Supporting This Decision

- **CVE-2024-11079**: Security analysis confirms arbitrary code execution risk in ansible-core \<2.18.1
- **Compatibility Matrix**: Research shows RHEL 9.6 Python 3.9 incompatible with ansible-navigator v25.5.0+
- **Enterprise Requirements**: UBI 9 provides necessary security updates and enterprise support
- **Dependency Issues**: Galaxy API failures require robust fallback strategies
- **Multi-OS Support**: Testing confirms compatibility across target operating systems

## Implementation Plan

### Phase 1: Development Environment (Week 1-2)

- Build new execution environment with updated tooling
- Test basic functionality and AnsibleSafe compatibility
- Validate playbook conditional logic updates

### Phase 2: Staging Environment (Week 3-4)

- Deploy updated execution environment to staging
- Comprehensive multi-OS testing (RHEL 9.6, Rocky Linux, Fedora)
- Multi-cloud validation (Equinix Metal, Hetzner Cloud, bare-metal)

### Phase 3: Production Rollout (Week 5-6)

- Controlled production deployment with rollback capability
- Monitor performance and functionality
- Complete migration documentation

## Related Decisions

- ADR-0001: Container-First Execution Model (Updated with security requirements)
- ADR-0004: Security Architecture with Ansible Vault (AnsibleSafe compatibility)
- ADR-0006: Modular Dependency Management (Collection management strategy)

## Date

2025-07-10

## Stakeholders

- DevOps Team (implementation)
- Security Team (vulnerability assessment)
- Infrastructure Team (deployment validation)
- QA Team (testing and validation)
- Project Maintainers (architectural oversight)
