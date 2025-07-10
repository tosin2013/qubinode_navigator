# Ansible Version Modernization Research Questions
**Generated**: 2025-07-10
**Context**: Ansible tooling version updates and modernization strategy
**Priority**: High
**Timeline**: Q1 2025
**Project**: Qubinode Navigator - KVM-based Multi-Cloud Infrastructure Automation Platform

## Project Overview

### Qubinode Navigator Mission
Qubinode Navigator is an enterprise-grade infrastructure automation platform designed to deploy and manage KVM-based virtualization environments across multiple cloud providers and bare-metal systems. The project enables organizations to rapidly provision consistent, secure, and scalable virtualization infrastructure using a container-first execution model with Ansible automation.

### Core Project Goals
1. **Multi-Cloud Deployment**: Support RHEL 9.6, Rocky Linux, and Fedora across Equinix Metal, Hetzner Cloud, and bare-metal environments
2. **Container-First Execution**: Eliminate "works on my machine" problems through standardized execution environments
3. **Security-First Architecture**: Implement comprehensive security controls with Ansible Vault integration and progressive SSH hardening
4. **Reproducible Infrastructure**: Ensure identical deployments across development, staging, and production environments
5. **Enterprise Integration**: Support HashiCorp Vault (HCP, local, OpenShift-deployed), Red Hat subscriptions, and enterprise authentication

### Target Use Cases
- **Development Labs**: Rapid KVM host setup for development and testing environments
- **Edge Computing**: Distributed virtualization infrastructure for edge deployments
- **Hybrid Cloud**: Consistent virtualization layer across multiple cloud providers
- **Enterprise Workloads**: Production-ready KVM infrastructure with enterprise security controls
- **CI/CD Infrastructure**: Automated infrastructure provisioning for continuous integration pipelines

### Technical Architecture
- **Execution Model**: Container-first using ansible-navigator with Podman (never native ansible-playbook)
- **Infrastructure as Code**: Declarative configuration through environment-specific inventories
- **Security Model**: Progressive SSH hardening, Ansible Vault encryption, HashiCorp Vault integration
- **Multi-OS Support**: Platform-specific scripts (rhel9-linux-hypervisor.sh, rocky-linux-hetzner.sh)
- **Deployment Targets**: KVM hypervisors with libvirt, bridge networking, and LVM storage management

## Executive Summary

This research document outlines critical questions and investigation areas for modernizing the Qubinode Navigator project's Ansible tooling stack. Current analysis reveals significant version gaps and potential compatibility issues that require systematic investigation to maintain the project's enterprise-grade reliability and security standards.

## Current State Analysis

### Project Infrastructure Context
The Qubinode Navigator project maintains a sophisticated infrastructure automation stack with the following key components:

**Supported Operating Systems:**
- Red Hat Enterprise Linux 9.6 (primary enterprise target)
- Rocky Linux (open-source RHEL alternative)
- Fedora (development and testing environments)

**Cloud Provider Support:**
- Equinix Metal (bare-metal cloud infrastructure)
- Hetzner Cloud (European cloud provider)
- Bare-metal deployments (on-premises infrastructure)

**Core Automation Components:**
- KVM hypervisor setup and configuration
- Libvirt storage pool management with LVM
- Bridge networking configuration (qubibr0)
- SSH security hardening with progressive authentication
- Ansible Vault integration for secrets management
- HashiCorp Vault support (HCP, local Podman, OpenShift)

### Version Inventory
- **ansible-navigator**: Currently unspecified → Latest v25.5.0 (May 2024)
- **ansible-builder**: Currently unspecified → Latest v3.1.0 (June 2024)
- **ansible-core**: Not explicitly pinned → Need to determine compatible version
- **Execution Environment**: Using `quay.io/qubinode/qubinode-installer:0.8.0`
- **Python Requirements**: Minimal (fire, netifaces, psutil, requests)
- **Collection Dependencies**: ansible.posix, containers.podman, community.general, community.libvirt, fedora.linux_system_roles, tosin2013.qubinode_kvmhost_setup_collection

### Critical Dependencies
- **Linux System Roles**: network (1.17.4), firewall (1.10.1), cockpit (1.7.0)
- **Container Runtime**: Podman (required for container-first execution)
- **Vault Integration**: AnsibleSafe tool for vault operations
- **Platform Scripts**: OS-specific deployment scripts with user adaptation logic

### Identified Issues
1. Galaxy API failures during collection installation (blocking builds)
2. No explicit version pinning in requirements (reproducibility risk)
3. Inconsistent execution environment configurations (local vs production)
4. Missing fallback strategies for dependency resolution
5. Potential Python version compatibility issues with latest tooling
6. Security vulnerabilities in unversioned dependencies

## Research Questions

### 1. Version Compatibility Assessment

**Q1.1**: What is the compatibility matrix between ansible-navigator v25.5.0, ansible-builder v3.1.0, and the latest ansible-core versions for Qubinode Navigator's multi-OS support?
- **Priority**: Critical
- **Context**: Must support RHEL 9.6, Rocky Linux, and Fedora with consistent behavior
- **Method**: Documentation review, compatibility testing on all target OS
- **Success Criteria**: Complete compatibility matrix with supported version combinations for each OS
- **Timeline**: Week 1
- **Specific Focus**: Container-first execution model compatibility, Podman integration

**Q1.2**: Which Python versions are required/supported by the latest Ansible tooling stack across RHEL 9.6, Rocky Linux, and Fedora?
- **Priority**: High
- **Context**: Project requires consistent Python environment across diverse OS targets
- **Method**: Official documentation analysis, testing on RHEL 9.6/Rocky Linux/Fedora
- **Success Criteria**: Confirmed Python version requirements for all target OS with migration path
- **Timeline**: Week 1
- **Specific Focus**: Platform-python compatibility, virtual environment requirements

**Q1.3**: What are the breaking changes between current usage and latest versions that could impact KVM infrastructure automation?
- **Priority**: Critical
- **Context**: Must maintain libvirt, LVM, and bridge networking automation capabilities
- **Method**: Changelog analysis, migration guide review, infrastructure component testing
- **Success Criteria**: Documented list of breaking changes with infrastructure automation impact assessment
- **Timeline**: Week 2
- **Specific Focus**: Collection compatibility, execution environment changes, container runtime requirements

### 2. Execution Environment Modernization

**Q2.1**: What base images should be used for updated execution environments to support Qubinode Navigator's enterprise and multi-cloud requirements?
- **Priority**: High
- **Context**: Must support enterprise compliance, security scanning, and multi-OS compatibility
- **Method**: Research Red Hat UBI images, community images, security scanning, enterprise compliance review
- **Success Criteria**: Recommended base image with security, compliance, and compatibility justification for enterprise environments
- **Timeline**: Week 2
- **Specific Focus**: UBI 9 compatibility, security update lifecycle, container registry strategy

**Q2.2**: How should collection dependencies be managed to avoid Galaxy API failures while maintaining the extensive automation capabilities required for KVM infrastructure?
- **Priority**: Critical
- **Context**: Project requires ansible.posix, containers.podman, community.general, community.libvirt, fedora.linux_system_roles, and custom collections
- **Method**: Test fallback strategies, private registry options, Git-based sources, collection mirroring
- **Success Criteria**: Robust dependency resolution strategy with multiple fallbacks ensuring 99%+ build success rate
- **Timeline**: Week 1-2
- **Specific Focus**: Custom collection hosting, Git-based collection sources, collection version pinning

**Q2.3**: What is the optimal execution environment versioning strategy for supporting multiple deployment environments (dev, staging, production) across different cloud providers?
- **Priority**: Medium
- **Context**: Must support environment-specific configurations while maintaining consistency
- **Method**: Industry best practices research, semantic versioning analysis, multi-environment deployment patterns
- **Success Criteria**: Versioning strategy aligned with project release cycles and environment promotion workflows
- **Timeline**: Week 3
- **Specific Focus**: Environment-specific tagging, rollback capabilities, version lifecycle management

### 3. CI/CD Pipeline Impact

**Q3.1**: How will version updates affect existing GitHub Actions workflows?
- **Priority**: High
- **Method**: Workflow analysis, testing with updated versions
- **Success Criteria**: Updated workflows with no functionality regression
- **Timeline**: Week 2-3

**Q3.2**: What changes are needed in the build-deploy-ee.yml workflow?
- **Priority**: High
- **Method**: Workflow testing, ansible-builder v3.1.0 feature analysis
- **Success Criteria**: Optimized workflow leveraging new ansible-builder features
- **Timeline**: Week 2

**Q3.3**: How can we implement automated version scanning and updates?
- **Priority**: Medium
- **Method**: Dependabot configuration, security scanning tools research
- **Success Criteria**: Automated dependency management with security alerts
- **Timeline**: Week 4

### 4. Security and Compliance

**Q4.1**: What security vulnerabilities exist in current vs. latest versions, particularly affecting the progressive SSH security model and Ansible Vault integration?
- **Priority**: Critical
- **Context**: Project implements progressive SSH hardening (password → key-based → hardened) and extensive Ansible Vault usage
- **Method**: CVE database analysis, security scanning tools, SSH security assessment, vault security review
- **Success Criteria**: Security risk assessment with mitigation recommendations for SSH and vault components
- **Timeline**: Week 1
- **Specific Focus**: SSH key management, vault encryption standards, container security

**Q4.2**: How do version updates affect compliance with enterprise security requirements for Red Hat environments and HashiCorp Vault integration?
- **Priority**: High
- **Context**: Must maintain compliance with enterprise security policies, Red Hat security standards, and HashiCorp Vault security models
- **Method**: Enterprise security policy review, compliance framework analysis, Red Hat security guidelines review
- **Success Criteria**: Compliance impact assessment and remediation plan for enterprise deployments
- **Timeline**: Week 2
- **Specific Focus**: RHEL security compliance, vault security standards, container security policies

**Q4.3**: How do the latest versions impact the AnsibleSafe tool integration and vault password management workflows?
- **Priority**: High
- **Context**: Project uses custom AnsibleSafe tool (/usr/local/bin/ansiblesafe) for vault operations with specific encrypt/decrypt workflows
- **Method**: AnsibleSafe compatibility testing, vault workflow validation, encryption/decryption testing
- **Success Criteria**: Confirmed AnsibleSafe compatibility with updated Ansible versions and migration plan if needed
- **Timeline**: Week 2
- **Specific Focus**: Vault file compatibility, encryption algorithm support, workflow automation

### 5. Performance and Reliability

**Q5.1**: What performance improvements are available in latest versions?
- **Priority**: Medium
- **Method**: Benchmark testing, release notes analysis
- **Success Criteria**: Performance comparison and optimization recommendations
- **Timeline**: Week 3

**Q5.2**: How do latest versions improve build reliability and error handling?
- **Priority**: High
- **Method**: Error handling testing, reliability feature analysis
- **Success Criteria**: Improved build success rate and error recovery
- **Timeline**: Week 2-3

## Implementation Research

### 6. Migration Strategy

**Q6.1**: What is the optimal migration sequence to minimize disruption to active KVM infrastructure deployments across multiple cloud providers?
- **Priority**: Critical
- **Context**: Must account for active deployments on Equinix Metal, Hetzner Cloud, and bare-metal environments
- **Method**: Risk analysis, rollback planning, phased deployment design, environment-specific testing
- **Success Criteria**: Step-by-step migration plan with rollback procedures for each deployment environment
- **Timeline**: Week 3-4
- **Specific Focus**: Environment-specific migration paths, inventory compatibility, vault migration

**Q6.2**: How can we maintain backward compatibility during transition while preserving the extensive platform-specific script functionality?
- **Priority**: High
- **Context**: Must preserve rhel9-linux-hypervisor.sh, rocky-linux-hetzner.sh functionality and user adaptation logic
- **Method**: Compatibility testing, feature flag analysis, script compatibility validation
- **Success Criteria**: Transition plan maintaining existing functionality across all platform scripts
- **Timeline**: Week 3
- **Specific Focus**: Script compatibility, user detection logic, environment variable handling

**Q6.3**: What testing strategy ensures successful version updates across the diverse infrastructure automation scenarios?
- **Priority**: High
- **Context**: Must validate KVM setup, libvirt configuration, bridge networking, LVM management, and vault integration
- **Method**: Test framework design, validation criteria definition, infrastructure component testing
- **Success Criteria**: Comprehensive testing strategy with automated validation for all infrastructure components
- **Timeline**: Week 2-3
- **Specific Focus**: Infrastructure validation, multi-OS testing, vault integration testing

**Q6.4**: How should the migration handle the transition from current execution environment inconsistencies (localhost:0.1.0 vs quay.io:0.8.0)?
- **Priority**: High
- **Context**: Current inconsistency between local and production execution environments creates deployment challenges
- **Method**: Execution environment standardization, image migration planning, registry strategy
- **Success Criteria**: Unified execution environment strategy with consistent versioning across all environments
- **Timeline**: Week 2-3
- **Specific Focus**: Image registry consolidation, version alignment, deployment consistency

## Research Methodology

### Investigation Approach
1. **Documentation Review**: Official Ansible documentation, release notes, migration guides, Red Hat documentation
2. **Multi-OS Compatibility Testing**: Version matrix testing on RHEL 9.6, Rocky Linux, and Fedora
3. **Infrastructure Component Testing**: KVM, libvirt, LVM, bridge networking, and container runtime validation
4. **Security Analysis**: CVE scanning, vulnerability assessment, SSH security validation, vault encryption testing
5. **Performance Benchmarking**: Build time, execution performance, infrastructure deployment time comparison
6. **Enterprise Integration Testing**: HashiCorp Vault integration, Red Hat subscription compatibility
7. **Community Research**: Best practices from Ansible community, enterprise patterns, multi-cloud deployment strategies

### Success Metrics
- **Compatibility**: 100% functionality preservation during upgrade across all supported OS
- **Security**: Zero critical vulnerabilities in updated stack, maintained SSH security model
- **Performance**: No degradation in build/execution times, improved infrastructure deployment speed
- **Reliability**: 95%+ build success rate with new versions across all environments
- **Enterprise Integration**: Maintained HashiCorp Vault integration and Red Hat subscription compatibility
- **Documentation**: Complete migration guide and troubleshooting procedures for all platform scripts

### Risk Mitigation
- **Rollback Plan**: Ability to revert to current versions within 1 hour across all deployment environments
- **Testing Environment**: Isolated testing before production deployment on each supported OS
- **Multi-Environment Validation**: Testing across dev, staging, and production-like environments
- **Stakeholder Communication**: Regular updates on research progress and findings to DevOps, Security, and Infrastructure teams
- **Documentation**: Comprehensive change documentation and training materials for all platform-specific scripts
- **Backup Strategy**: Complete backup of current execution environments and configurations before migration

### Qubinode Navigator Specific Considerations
- **Container-First Compliance**: Ensure all updates maintain strict container-first execution model
- **Platform Script Compatibility**: Validate all OS-specific scripts (rhel9-linux-hypervisor.sh, rocky-linux-hetzner.sh)
- **Vault Integration Preservation**: Maintain AnsibleSafe tool compatibility and vault workflow functionality
- **Multi-Cloud Support**: Ensure updates work consistently across Equinix Metal, Hetzner Cloud, and bare-metal
- **User Adaptation Logic**: Preserve dynamic user detection and path adaptation functionality
- **Enterprise Security**: Maintain progressive SSH hardening and enterprise compliance requirements

## Next Steps

1. **Week 1**: Critical compatibility and security research (Q1.1, Q1.2, Q4.1)
2. **Week 2**: Execution environment and CI/CD analysis (Q2.1, Q2.2, Q3.1)
3. **Week 3**: Migration planning and performance testing (Q6.1, Q5.1)
4. **Week 4**: Implementation strategy and automation setup (Q3.3, Q6.3)

## Deliverables

### Primary Deliverables
- **Updated ADR for Ansible tooling version management** with enterprise compliance considerations
- **Migration guide with step-by-step procedures** for each supported OS (RHEL 9.6, Rocky Linux, Fedora)
- **Updated execution environment configurations** with standardized base images and version pinning
- **Enhanced CI/CD workflows** with version pinning and multi-environment support
- **Security assessment and compliance documentation** including SSH security and vault integration
- **Performance benchmarking results** and optimization recommendations for infrastructure deployment

### Qubinode Navigator Specific Deliverables
- **Platform Script Compatibility Matrix** documenting changes needed for rhel9-linux-hypervisor.sh and rocky-linux-hetzner.sh
- **Vault Integration Migration Guide** ensuring AnsibleSafe tool compatibility and workflow preservation
- **Multi-Cloud Deployment Validation** confirming functionality across Equinix Metal, Hetzner Cloud, and bare-metal
- **Container Registry Strategy** for execution environment distribution and version management
- **Enterprise Integration Documentation** covering HashiCorp Vault and Red Hat subscription compatibility
- **User Adaptation Logic Validation** ensuring dynamic user detection continues to function correctly

### Supporting Documentation
- **Troubleshooting Guide** for common migration issues across different environments
- **Rollback Procedures** for each deployment scenario and environment type
- **Testing Framework** for validating infrastructure automation components
- **Version Lifecycle Management** procedures for ongoing maintenance and updates
- **Training Materials** for team members on new tooling and procedures
