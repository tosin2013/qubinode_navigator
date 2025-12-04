# Configuration Management Strategy Research Questions

**Generated**: 2025-07-09
**Context**: Qubinode Navigator configuration options analysis
**Focus**: /tmp/config.yml vs vault configuration approaches

## Executive Summary

Based on codebase analysis, Qubinode Navigator supports **two primary configuration approaches**:

1. **CI/CD Pipeline Mode**: Uses `/tmp/config.yml` for automated deployments
1. **Interactive Mode**: Uses Ansible Vault with interactive setup

## Key Research Questions

### 1. Configuration File Location and Usage

**Q1.1**: When should `/tmp/config.yml` be used versus interactive vault setup?

- **Context**: Code shows `/tmp/config.yml` is checked in CI/CD pipeline mode
- **Evidence**: Lines 300-307 in `qubinode_navigator.sh` show conditional logic
- **Priority**: High - Affects deployment strategy

**Q1.2**: What is the expected format and content of `/tmp/config.yml`?

- **Context**: Documentation shows RHEL subscription example
- **Evidence**: `docs/deployments/demo-hetzner-com.markdown` lines 42-46
- **Priority**: High - Required for CI/CD deployments

**Q1.3**: How does the system handle missing `/tmp/config.yml` in CI/CD mode?

- **Evidence**: Script exits with error if file not found (line 306)
- **Impact**: Deployment failure
- **Priority**: Medium - Error handling

### 2. Vault Configuration Architecture

**Q2.1**: What is the relationship between `/tmp/config.yml` and vault.yml?

- **Evidence**: `/tmp/config.yml` is copied to `vault.yml` and encrypted with ansiblesafe
- **Process**: `cp /tmp/config.yml → vault.yml → ansiblesafe encryption`
- **Priority**: High - Security workflow

**Q2.2**: How does ansiblesafe integrate with the configuration process?

- **Tool**: `/usr/local/bin/ansiblesafe` for vault encryption/decryption
- **Options**: `-o 1` for encryption, `-o 4` for HashiCorp Vault integration
- **Priority**: High - Security implementation

**Q2.3**: What are the security implications of each approach?

- **CI/CD**: Temporary file in `/tmp/` → encrypted vault
- **Interactive**: Direct vault creation with user input
- **Priority**: Critical - Security assessment

### 3. Environment-Specific Configuration

**Q3.1**: How does inventory selection affect configuration management?

- **Variable**: `INVENTORY` environment variable determines path
- **Path**: `/inventories/${INVENTORY}/group_vars/control/vault.yml`
- **Priority**: Medium - Multi-environment support

**Q3.2**: What configuration options are available for different environments?

- **Environments**: dev, equinix, hetzner, hetzner-bridge, rhel8-equinix, rhel9-equinix, sample
- **Structure**: Each has `group_vars/control/` directory
- **Priority**: Medium - Environment management

### 4. Integration and Workflow Questions

**Q4.1**: How does the load-variables.py script interact with configuration?

- **Context**: Script failed due to missing INVENTORY variable
- **Dependencies**: Requires fire, netifaces, psutil, requests modules
- **Priority**: High - Current blocker

**Q4.2**: What is the complete configuration workflow for a new environment?

- **Steps**: Package install → vault setup → inventory generation → variable loading
- **Current Status**: Completed RHEL 9 setup, at inventory generation phase
- **Priority**: High - Immediate next steps

**Q4.3**: How does Ansible Navigator configuration relate to vault setup?

- **File**: `~/.ansible-navigator.yml`
- **Integration**: References inventory path and execution environment
- **Priority**: Medium - Tool integration

## Recommended Configuration Approach

### For Development/Local Environment:

1. **Use Interactive Mode** (current situation)
1. **Set INVENTORY="localhost"** or create localhost inventory
1. **Run ansible_vault_setup.sh** for secure credential management
1. **Use load-variables.py** for dynamic configuration

### For CI/CD Pipeline:

1. **Create `/tmp/config.yml`** with required credentials
1. **Set CICD_PIPELINE="true"**
1. **Provide SSH_PASSWORD** environment variable
1. **System automatically encrypts and manages vault**

## Immediate Action Items

1. **Create localhost inventory** if not exists
1. **Set INVENTORY environment variable** to "localhost"
1. **Run load-variables.py** to continue setup
1. **Document configuration workflow** for future reference

## Security Considerations

- `/tmp/config.yml` is temporary and should be secured/deleted after use
- Vault files are encrypted using Ansible Vault with ansiblesafe
- Password files are managed with proper permissions
- CI/CD mode requires secure environment variable management

## Related Documentation

- ADR-0003: Dynamic Configuration Management with Python
- ADR-0004: Security Architecture with Ansible Vault
- Developer Guide: Configure Ansible Navigator section
- Deployment Guide: Hetzner demo configuration example
