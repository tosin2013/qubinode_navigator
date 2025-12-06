______________________________________________________________________

## layout: default title: Security & Operations parent: Architectural Decision Records nav_order: 2 has_children: true

# Security & Operations ADRs

This section contains ADRs related to security architecture, operational procedures, and access control.

## ADRs in this Category

### Core Security

- **[ADR-0004](adr-0004-security-architecture-ansible-vault.md)**: Security Architecture with Ansible Vault and AnsibleSafe
- **[ADR-0010](adr-0010-progressive-ssh-security-model.md)**: Progressive SSH Security Model
- **[ADR-0024](adr-0024-vault-integrated-setup-script-security-enhancement.md)**: Vault-Integrated Setup Script Security Enhancement
- **[ADR-0025](adr-0025-ansible-tooling-modernization-security-strategy.md)**: Ansible Tooling Modernization and Security Strategy

### HashiCorp Vault Integration

- **[ADR-0051](adr-0051-hashicorp-vault-secrets-management.md)**: HashiCorp Vault Integration for Secrets Management
- **[ADR-0052](adr-0052-vault-audit-logging.md)**: Vault Audit Logging and Centralized Audit Trails
- **[ADR-0053](adr-0053-vault-dynamic-secrets-airflow.md)**: Dynamic Secrets for Apache Airflow Tasks

### Certificate & PKI Management

- **[ADR-0048](adr-0048-step-ca-integration-for-disconnected-deployments.md)**: Step-CA Integration for Disconnected Deployments
- **[ADR-0054](adr-0054-unified-certificate-management.md)**: Unified Certificate Management

## Key Themes

- **Credential Protection**: Secure handling of sensitive information using Ansible Vault and HashiCorp Vault
- **Access Control**: Progressive security models with role-based access
- **Operational Security**: Security-first approach to system operations
- **Audit & Compliance**: Comprehensive logging and audit trails
- **Certificate Management**: Unified PKI for disconnected and connected environments
