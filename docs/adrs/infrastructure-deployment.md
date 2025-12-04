______________________________________________________________________

## layout: default title: Infrastructure & Deployment parent: Architectural Decision Records nav_order: 1 has_children: true

# Infrastructure & Deployment ADRs

This section contains ADRs related to infrastructure setup, deployment strategies, and platform choices.

## ADRs in this Category

- **[ADR-0001](adr-0001-container-first-execution-model-with-ansible-navigator.md)**: Container-First Execution Model with Ansible Navigator
- **[ADR-0002](adr-0002-multi-cloud-inventory-strategy.md)**: Multi-Cloud Inventory Strategy with Environment-Specific Configurations
- **[ADR-0005](adr-0005-kvm-libvirt-virtualization-platform.md)**: KVM/Libvirt Virtualization Platform Choice
- **[ADR-0008](adr-0008-os-specific-deployment-script-strategy.md)**: OS-Specific Deployment Script Strategy
- **[ADR-0009](adr-0009-cloud-provider-specific-configuration.md)**: Cloud Provider-Specific Configuration Management
- **[ADR-0026](adr-0026-rhel-10-centos-10-platform-support-strategy.md)**: RHEL 10/CentOS 10 Platform Support Strategy
- **[ADR-0031](adr-0031-setup-script-modernization-strategy.md)**: Setup Script Modernization Strategy

## Key Themes

- **Container-First Approach**: All deployments use standardized container execution environments
- **Multi-Cloud Support**: Flexible deployment across different cloud providers
- **OS Compatibility**: Support for multiple Linux distributions and versions
- **Automation**: Scripted deployment and configuration management
