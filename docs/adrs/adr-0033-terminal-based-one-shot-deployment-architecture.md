______________________________________________________________________

## layout: default title: ADR-0033 Terminal-Based One-Shot Deployment parent: Architecture & Design grand_parent: Architectural Decision Records nav_order: 0033

# ADR-0033: Terminal-Based One-Shot Deployment Architecture

## Status

Accepted

## Context

The Qubinode Navigator project has evolved from multiple deployment scripts (setup.sh, rhel9-linux-hypervisor.sh, etc.) to require a unified, repeatable deployment experience. Users need a single entry point that can:

- Deploy on fresh systems reliably and repeatably
- Auto-detect operating systems and deployment targets
- Orchestrate existing deployment scripts without duplication
- Provide comprehensive error handling and recovery
- Support both interactive and CI/CD deployment modes
- Integrate with AI Assistant for troubleshooting guidance
- Work entirely through terminal interface

The current architecture has multiple entry points that can lead to inconsistent deployment experiences and makes it difficult for new users to understand the proper deployment workflow.

## Decision

We will implement a terminal-based one-shot deployment architecture centered around `deploy-qubinode.sh` as the primary entry point for all Qubinode Navigator deployments.

### Core Architecture Principles:

1. **Single Entry Point**: `deploy-qubinode.sh` serves as the unified deployment orchestrator
1. **Environment Auto-Detection**: Automatically detect OS, deployment target, and configuration requirements
1. **Script Orchestration**: Leverage existing scripts (setup.sh workflow) rather than reimplementing functionality
1. **Repeatability**: Support multiple runs on the same system with idempotent operations
1. **Terminal-First**: All interactions through command-line interface with structured logging
1. **AI Integration**: Containerized AI Assistant provides troubleshooting via API calls
1. **Configuration Management**: Comprehensive .env and notouch.env generation for compatibility

### Implementation Details:

#### Deployment Flow:

```bash
./deploy-qubinode.sh
├── OS Detection (RHEL 9/10, CentOS Stream 9/10, Rocky 9, AlmaLinux 9)
├── Prerequisites Check (resources, connectivity, permissions)
├── Configuration Validation (required variables, domain format)
├── Deployment Target Detection (Hetzner, Equinix, local, custom)
├── AI Assistant Startup (containerized, non-blocking)
├── Repository Setup (clone/update qubinode_navigator)
├── Environment Configuration (.env, notouch.env generation)
└── Infrastructure Deployment (orchestrate existing setup.sh workflow)
    ├── OS Configuration & Package Installation
    ├── SSH & Firewall Configuration
    ├── Ansible Navigator Setup
    ├── Vault Configuration
    ├── Inventory Generation
    ├── KVM Host Deployment (ansible-navigator run setup_kvmhost.yml)
    ├── Bash Aliases Configuration
    └── Kcli Base Setup
```

#### Error Handling Strategy:

- Comprehensive error trapping with cleanup on failure
- AI Assistant integration for contextual troubleshooting guidance
- Structured logging to deployment-specific log files
- Graceful degradation when optional components fail

#### Repeatability Features:

- Backup existing configurations before modification
- Idempotent package installation checks
- Existing deployment detection and update handling
- Environment variable validation and defaulting

## Consequences

### Positive:

- **Simplified User Experience**: Single command deployment for all scenarios
- **Consistent Behavior**: Standardized deployment process across all environments
- **Better Error Recovery**: Comprehensive error handling with AI-assisted troubleshooting
- **Maintainability**: Centralized orchestration logic while preserving existing script functionality
- **Documentation**: Clear entry point makes documentation and onboarding simpler
- **CI/CD Ready**: Supports both interactive and automated deployment modes

### Negative:

- **Complexity Concentration**: More logic concentrated in single script (1,387 lines)
- **Testing Overhead**: Comprehensive testing required across all supported OS/deployment combinations
- **Migration Effort**: Users must transition from existing script-specific workflows

### Neutral:

- **Backward Compatibility**: Existing scripts remain functional for specific use cases
- **AI Assistant Dependency**: Optional but recommended for optimal user experience

## Implementation Status

- ✅ Core deploy-qubinode.sh architecture implemented (1,387 lines)
- ✅ OS detection for RHEL 9/10, CentOS Stream 9/10, Rocky 9, AlmaLinux 9
- ✅ Deployment target detection (Hetzner, Equinix, local, custom)
- ✅ AI Assistant container integration
- ✅ Environment configuration generation
- ✅ Error handling and cleanup mechanisms
- ⏳ End-to-end testing and validation
- ⏳ Documentation and user guides

## Related ADRs

### Dependencies (Required)

- ADR-0001: Container-First Execution Model with Ansible Navigator - Provides containerized execution foundation
- ADR-0027: CPU-Based AI Deployment Assistant Architecture - Enables AI-powered troubleshooting integration
- ADR-0026: RHEL 10/CentOS 10 Platform Support Strategy - Defines modern OS support requirements

### Supersedes

- ADR-0008: OS-Specific Deployment Script Strategy - Replaced by unified deployment approach
- ADR-0031: Setup Script Modernization Strategy - Goals achieved through this implementation

### Integrates With

- ADR-0002: Multi-Cloud Inventory Strategy - Uses inventory detection for deployment targets
- ADR-0003: Dynamic Configuration Management - Leverages Python configuration loading
- ADR-0004: Security Architecture with Ansible Vault - Integrates vault password management
- ADR-0007: Bash-First Orchestration - Maintains bash-first approach with Python integration
- ADR-0028: Modular Plugin Framework - Can leverage plugins for extensibility

## Notes

This ADR establishes the foundation for a unified deployment experience that maintains compatibility with existing infrastructure while providing a modern, AI-assisted deployment workflow. The terminal-based approach ensures compatibility with CI/CD pipelines and remote deployment scenarios.

Future enhancements may include Hugging Face integration for broader AI model support and community showcase capabilities.
