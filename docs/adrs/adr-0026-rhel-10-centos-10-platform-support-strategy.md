______________________________________________________________________

## layout: default title: ADR-0026 RHEL 10/CentOS 10 Platform Support parent: Infrastructure & Deployment grand_parent: Architectural Decision Records nav_order: 0026

# ADR-0026: RHEL 10/CentOS 10 Platform Support Strategy

## Status

Accepted - Implemented (2025-11-11)

RHEL 10 and CentOS Stream 10 support has been fully implemented with comprehensive plugin framework integration, native testing validation, and production deployment capabilities.

## Context

The Qubinode Navigator project currently supports RHEL 8/9 and Rocky Linux but lacks compatibility with the next generation of enterprise Linux distributions. RHEL 10 and CentOS Stream 10 introduce breaking changes including:

- **x86_64-v3 microarchitecture requirement**: Older hardware may not be supported
- **Python 3.12 as default**: Current execution environments use Python 3.9/3.11
- **DNF modularity removal**: Application streams delivered as traditional RPMs
- **Linux kernel 6.12**: Major kernel version jump with potential compatibility impacts
- **Package removals**: Key packages like Xorg server, LibreOffice, GIMP, Redis removed

The PRD analysis identified this as a critical compatibility gap that prevents deployment on modern enterprise systems and blocks future adoption.

## Decision

Extend platform support to include RHEL 10 and CentOS Stream 10 while maintaining backward compatibility with existing RHEL 8/9 deployments. Implementation includes:

1. **OS Detection Enhancement**: Update `get_rhel_version` function and setup scripts to recognize RHEL 10/CentOS 10
1. **Hardware Validation**: Add pre-flight checks for x86_64-v3 microarchitecture compatibility
1. **Python 3.12 Compatibility**: Update execution environments and Ansible tooling for Python 3.12
1. **Package Management Adaptation**: Remove DNF modularity logic and adapt to non-modular RPM streams
1. **Collection Updates**: Coordinate with `qubinode_kvmhost_setup_collection` for Ansible Galaxy updates

## Consequences

### Positive

- Enables deployment on next-generation enterprise Linux systems
- Future-proofs the platform against upstream OS evolution
- Maintains competitive advantage in enterprise automation space
- Supports modern hardware and security features

### Negative

- Requires extensive testing across expanded OS matrix (RHEL 8/9/10, CentOS Stream 10)
- Increases complexity in OS-specific deployment scripts
- May necessitate hardware upgrades for x86_64-v3 requirement
- Additional maintenance overhead for multiple OS versions

### Risks

- Potential compatibility regressions during transition period
- Collection dependency synchronization complexity
- Performance impact from supporting wider OS range

## Alternatives Considered

1. **Continue RHEL 9 only**: Rejected due to enterprise adoption of RHEL 10
1. **Separate project for RHEL 10**: Rejected due to maintenance fragmentation
1. **Container-only deployment**: Insufficient for hypervisor setup requirements
1. **Delayed adoption**: Rejected due to competitive disadvantage

## Implementation Plan

### Phase 1: Collection Updates

- Update `qubinode_kvmhost_setup_collection` for RHEL 10/CentOS 10 compatibility
- Test and publish new collection version to Ansible Galaxy
- Validate role functionality across OS matrix

### Phase 2: Navigator Integration

- Update OS detection logic in setup scripts
- Modify execution environment configurations for Python 3.12
- Update `requirements.yml` to use new collection version

### Phase 3: Validation & Documentation

- Comprehensive testing across all supported OS versions
- Update documentation and deployment guides
- Create migration path for existing deployments

## Related ADRs

- ADR-0001: Container-First Execution Model (execution environment updates)
- ADR-0008: OS-Specific Deployment Script Strategy (extends OS support)
- ADR-0025: Ansible Tooling Modernization (Python 3.12 compatibility)

## Date

2025-11-07

## Stakeholders

- Platform Engineering Team
- DevOps Team
- QA Team
- Infrastructure Team
- Collection Maintainers
