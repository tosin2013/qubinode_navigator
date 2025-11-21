# Qubinode Navigator - Architecture Decision Records Index

## Overview
This document provides a comprehensive index of all Architecture Decision Records (ADRs) for the Qubinode Navigator project, organized by status and relationships.

## Current Architecture (Active ADRs)

### 🏗️ Core Architecture
- **[ADR-0001](adr-0001-container-first-execution-model-with-ansible-navigator.md)**: Container-First Execution Model with Ansible Navigator
- **[ADR-0033](adr-0033-terminal-based-one-shot-deployment-architecture.md)**: Terminal-Based One-Shot Deployment Architecture ⭐ *Primary Entry Point*
- **[ADR-0028](adr-0028-modular-plugin-framework-for-extensibility.md)**: Modular Plugin Framework for Extensibility

### 🤖 AI Assistant Integration
- **[ADR-0027](adr-0027-cpu-based-ai-deployment-assistant-architecture.md)**: CPU-Based AI Deployment Assistant Architecture
- **[ADR-0032](adr-0032-ai-assistant-community-distribution-strategy.md)**: AI Assistant Community Distribution Strategy
- **[ADR-0034](adr-0034-ai-assistant-terminal-integration-strategy.md)**: AI Assistant Terminal Integration Strategy
- **[ADR-0038](adr-0038-fastmcp-framework-migration.md)**: FastMCP Framework Migration for MCP Servers ⭐ *New*

### 🖥️ Platform Support
- **[ADR-0005](adr-0005-kvm-libvirt-virtualization-platform.md)**: KVM/Libvirt Virtualization Platform Choice
- **[ADR-0026](adr-0026-rhel-10-centos-10-platform-support-strategy.md)**: RHEL 10/CentOS 10 Platform Support Strategy

### ☁️ Multi-Cloud & Configuration
- **[ADR-0002](adr-0002-multi-cloud-inventory-strategy.md)**: Multi-Cloud Inventory Strategy
- **[ADR-0003](adr-0003-dynamic-configuration-management.md)**: Dynamic Configuration Management
- **[ADR-0009](adr-0009-cloud-provider-specific-configuration.md)**: Cloud Provider-Specific Configuration Management
- **[ADR-0023](adr-0023-enhanced-configuration-management-with-template-support-and-hashicorp-vault-integration.md)**: Enhanced Configuration Management with HashiCorp Vault

### 🔒 Security
- **[ADR-0004](adr-0004-security-architecture-ansible-vault.md)**: Security Architecture with Ansible Vault
- **[ADR-0010](adr-0010-progressive-ssh-security-model.md)**: Progressive SSH Security Model
- **[ADR-0024](adr-0024-vault-integrated-setup-script-security-enhancement.md)**: Vault-Integrated Setup Script Security Enhancement
- **[ADR-0025](adr-0025-ansible-tooling-modernization-security-strategy.md)**: Ansible Tooling Modernization and Security Strategy

### 🛠️ Development & Operations
- **[ADR-0006](adr-0006-modular-dependency-management.md)**: Modular Dependency Management Strategy
- **[ADR-0007](adr-0007-bash-first-orchestration-python-configuration.md)**: Bash-First Orchestration with Python Configuration
- **[ADR-0011](adr-0011-comprehensive-platform-validation.md)**: Comprehensive Platform Validation
- **[ADR-0030](adr-0030-software-and-os-update-strategy.md)**: Software and OS Update Strategy

### 📚 Documentation
- **[ADR-0029](adr-0029-documentation-strategy-and-website-modernization.md)**: Documentation Strategy and Website Modernization
- **[ADR-0035](adr-0035-terminal-centric-documentation-strategy.md)**: Terminal-Centric Documentation Strategy

## Deprecated ADRs

### ❌ Superseded by Current Architecture
- **[ADR-0008](adr-0008-os-specific-deployment-script-strategy.md)**: OS-Specific Deployment Script Strategy
  - *Superseded by ADR-0033: Terminal-Based One-Shot Deployment Architecture*
- **[ADR-0031](adr-0031-setup-script-modernization-strategy.md)**: Setup Script Modernization Strategy
  - *Superseded by ADR-0033: Terminal-Based One-Shot Deployment Architecture*

## Architecture Relationships

### Primary Deployment Flow
```
ADR-0033 (One-Shot Deployment) 
├── depends on → ADR-0001 (Container-First Execution)
├── depends on → ADR-0027 (AI Assistant Architecture)
├── depends on → ADR-0026 (RHEL 10/CentOS 10 Support)
├── integrates → ADR-0002 (Multi-Cloud Inventory)
├── integrates → ADR-0004 (Security/Vault)
└── supersedes → ADR-0008, ADR-0031
```

### AI Assistant Integration
```
ADR-0034 (AI Terminal Integration)
├── depends on → ADR-0027 (AI Assistant Architecture)
├── depends on → ADR-0032 (AI Community Distribution)
├── depends on → ADR-0033 (One-Shot Deployment)
└── documented by → ADR-0035 (Terminal Documentation)
```

### Security Architecture
```
ADR-0004 (Security Architecture)
├── enhanced by → ADR-0024 (Vault Integration)
├── modernized by → ADR-0025 (Ansible Security)
└── supports → ADR-0010 (SSH Security)
```

## Implementation Status Summary

### ✅ Implemented (Production Ready)
- Core deployment architecture (ADR-0033)
- AI Assistant integration (ADR-0027, ADR-0032, ADR-0034)
- RHEL 10/CentOS 10 support (ADR-0026)
- Plugin framework (ADR-0028)
- Security modernization (ADR-0025)

### 🚧 In Progress
- Documentation strategy implementation (ADR-0029, ADR-0035)
- FastMCP framework migration (ADR-0038) - PoC Complete ✅

### 📋 Planned
- Software update automation (ADR-0030)

## Quick Navigation

### For New Users
1. Start with **ADR-0033** (Terminal-Based One-Shot Deployment) - the main deployment approach
2. Review **ADR-0034** (AI Assistant Integration) - for understanding AI-powered assistance
3. Check **ADR-0026** (RHEL 10/CentOS 10 Support) - for modern OS compatibility

### For Developers
1. **ADR-0028** (Plugin Framework) - for extending functionality
2. **ADR-0001** (Container-First Execution) - for understanding execution model
3. **ADR-0007** (Bash-First Orchestration) - for scripting patterns

### For Security/Operations
1. **ADR-0004** (Security Architecture) - foundational security model
2. **ADR-0024** (Vault Integration) - for credential management
3. **ADR-0025** (Ansible Security) - for tooling security

## Missing ADR Numbers
Available for future decisions: ADR-0012 through ADR-0022

---
*Last Updated: 2025-11-11*  
*This index is automatically maintained. Please update when adding new ADRs.*
