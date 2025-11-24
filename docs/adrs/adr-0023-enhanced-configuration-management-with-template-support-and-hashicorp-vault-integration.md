---
layout: default
title: ADR-0023 Enhanced Configuration
parent: Configuration & Automation
grand_parent: Architectural Decision Records
nav_order: 0023
---

# ADR-0023: Enhanced Configuration Management with Template Support and HashiCorp Vault Integration

## Status
Accepted

## Context
The Qubinode Navigator project needed a more flexible and secure configuration management system to replace manual /tmp/config.yml creation. The existing load-variables.py script was functional but lacked template support and modern vault integration capabilities. With HashiCorp moving towards dedicated vault solutions and the need for environment-specific configurations, an enhanced system was required.

Key challenges identified:
- Manual creation of /tmp/config.yml was error-prone and inconsistent
- No template system for environment-specific configurations
- Limited HashiCorp Vault integration despite existing CI/CD usage
- Security concerns with temporary file handling
- Need for smooth migration path to modern secret management

## Decision
Implement enhanced-load-variables.py with Jinja2 template support and HashiCorp Vault integration while maintaining full backward compatibility with existing workflows. The solution includes:

1. **Template-based configuration generation** using Jinja2
2. **HashiCorp Vault client integration** using hvac library  
3. **Dynamic vault updates** following HashiCorp migration patterns
4. **Secure file handling** with proper permissions (600)
5. **Variable priority hierarchy**: env vars → vault → interactive → defaults
6. **Environment-specific templates** for different deployment scenarios

### Implementation Details
- Enhanced script: `enhanced-load-variables.py`
- Template directory: `templates/` with Jinja2 templates
- Dependencies: jinja2, hvac (HashiCorp Vault client)
- Backward compatibility: All existing functionality preserved
- Security: Secure temporary file creation and cleanup

### Usage Examples
```bash
# Basic template generation
python3 enhanced-load-variables.py --generate-config --template default.yml.j2

# With HashiCorp Vault integration
export USE_HASHICORP_VAULT="true"
python3 enhanced-load-variables.py --generate-config --update-vault

# Environment-specific configuration
export INVENTORY="hetzner"
python3 enhanced-load-variables.py --generate-config --template hetzner.yml.j2
```

## Consequences

### Positive
- **Consistency**: Template-based approach ensures reproducible configurations across environments
- **Security**: Enhanced file permissions, secure handling, and vault integration
- **Flexibility**: Environment-specific templates and conditional logic
- **Migration Path**: Smooth transition to HashiCorp Vault following official patterns
- **Backward Compatibility**: Existing workflows continue to work unchanged
- **Scalability**: Easy to add new environments and configuration options

### Negative  
- **Dependencies**: Introduces new Python dependencies (jinja2, hvac)
- **Complexity**: Additional setup required for vault integration
- **Learning Curve**: Template syntax and vault concepts for team members
- **Maintenance**: Template files require ongoing maintenance

### Risks
- **Vault Availability**: Dependency on external vault service availability
- **Authentication**: Need for proper vault token management and rotation
- **Template Maintenance**: Risk of template drift between environments
- **Migration Complexity**: Potential issues during vault migration process

## Alternatives Considered

1. **Continue with existing load-variables.py**: Rejected due to lack of flexibility and vault integration
2. **Create completely new system**: Rejected due to backward compatibility concerns
3. **Environment variables only**: Rejected due to lack of template support and security concerns
4. **Vault integration without templates**: Rejected due to configuration consistency needs

## Evidence Supporting Decision

- HashiCorp official migration documentation supports implemented patterns
- Existing CI/CD pipelines already use `vault kv get` commands in .gitlab-ci.yml
- Repository analysis shows 7 different environment inventories requiring flexible configuration
- Security analysis indicates need for proper file permissions (600) and secret handling
- Template system successfully generates /tmp/config.yml with proper metadata
- Testing confirms backward compatibility with existing workflows

## Implementation Tasks

- [x] Implement Jinja2 template system for config generation
- [x] Integrate HashiCorp Vault using hvac library
- [x] Create environment-specific config templates (default.yml.j2, hetzner.yml.j2)
- [x] Add secure file handling with proper permissions
- [x] Test template generation and vault integration
- [ ] Update CI/CD pipelines for enhanced vault integration
- [ ] Create additional environment-specific templates
- [ ] Migrate existing configurations to new system
- [ ] Create comprehensive documentation and examples

## Related ADRs
- ADR-0003: Dynamic Configuration Management with Python
- ADR-0004: Security Architecture with Ansible Vault
- ADR-0011: Comprehensive Platform Validation

## References
- HashiCorp Vault Secrets Migration Documentation
- Enhanced load-variables.py implementation
- Template system architecture in templates/ directory
- Research documentation: vault-migration-dynamic-updates-2025-07-09.md
