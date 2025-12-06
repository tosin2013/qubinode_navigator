______________________________________________________________________

## layout: default title: Configuration & Automation parent: Architectural Decision Records nav_order: 3 has_children: true

# Configuration & Automation ADRs

This section contains ADRs related to configuration management, automation strategies, and tooling decisions.

## ADRs in this Category

### Core Configuration Management

- **[ADR-0003](adr-0003-dynamic-configuration-management.md)**: Dynamic Configuration Management with Python
- **[ADR-0007](adr-0007-bash-first-orchestration-python-configuration.md)**: Bash-First Orchestration with Python Configuration
- **[ADR-0023](adr-0023-enhanced-configuration-management-with-template-support-and-hashicorp-vault-integration.md)**: Enhanced Configuration Management with Template Support and HashiCorp Vault Integration

### Automation & Tooling

- **[ADR-0025](adr-0025-ansible-tooling-modernization-security-strategy.md)**: Ansible Tooling Modernization and Security Strategy
- **[ADR-0030](adr-0030-software-and-os-update-strategy.md)**: Software and OS Update Strategy
- **[ADR-0037](adr-0037-git-based-dag-repository-management.md)**: Git-Based DAG Repository Management
- **[ADR-0040](adr-0040-dag-distribution-from-kcli-pipelines.md)**: DAG Distribution from kcli-pipelines
- **[ADR-0044](adr-0044-user-configurable-airflow-volume-mounts.md)**: User-Configurable Airflow Volume Mounts

### Infrastructure Services

- **[ADR-0043](adr-0043-airflow-container-host-network-access.md)**: Airflow Container Host Network Access 🔥 *Critical*
- **[ADR-0055](adr-0055-zero-friction-infrastructure-services.md)**: Zero-Friction Infrastructure Services

## Key Themes

- **Dynamic Configuration**: Automated discovery and configuration adaptation
- **Template-Based Management**: Flexible configuration using templates
- **Tool Modernization**: Keeping automation tools current and secure
- **Update Management**: Automated software and OS update strategies
- **Infrastructure Services**: Zero-friction DNS and certificate automation
