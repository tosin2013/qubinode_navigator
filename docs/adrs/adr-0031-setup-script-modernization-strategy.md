# ADR-0031: Setup Script Modernization Strategy

## Status
**DEPRECATED** - Superseded by ADR-0033: Terminal-Based One-Shot Deployment Architecture

This ADR is no longer needed as the modernization goals have been achieved through the implementation of `deploy-qubinode.sh` which provides a unified, intelligent deployment orchestrator with AI Assistant integration.

## Context

The current `setup.sh` script serves as the primary entry point for Qubinode Navigator deployment but has several limitations that need to be addressed:

### Current Issues
1. **Missing OS Support**: No support for RHEL 10, CentOS Stream 10, or Rocky Linux 9
2. **Monolithic Architecture**: Hardcoded calls to OS-specific scripts (rhel8-linux-hypervisor.sh, rhel9-linux-hypervisor.sh, rocky-linux-hetzner.sh)
3. **Limited Intelligence**: Basic OS detection without cloud provider or environment awareness
4. **Maintenance Overhead**: Duplicate logic across multiple scripts
5. **No Plugin Integration**: Cannot leverage the new plugin framework (ADR-0028)

### Plugin Framework Integration Opportunity
With the successful implementation of ADR-0028 (Modular Plugin Framework), we now have:
- 10+ plugins covering all deployment scenarios
- Intelligent environment detection
- Idempotent operations
- Comprehensive logging and error handling
- Extensible architecture for future OS/cloud support

## Decision

We will modernize `setup.sh` to integrate with the plugin framework while maintaining backward compatibility:

### 1. Enhanced OS Detection
- Add support for RHEL 10, CentOS Stream 10, Rocky Linux 9
- Implement intelligent plugin selection based on detected OS
- Add cloud provider detection (Hetzner, Equinix, bare metal)
- Detect demo environments (Red Hat Demo System, Hetzner deployment)

### 2. Plugin Framework Integration
- Replace monolithic script calls with plugin orchestration
- Use `qubinode_cli.py` for plugin execution
- Dynamic plugin configuration based on environment detection
- Leverage plugin dependency resolution and execution order

### 3. Backward Compatibility Strategy
- Keep original `setup.sh` as `setup_legacy.sh`
- Create modernized `setup_modernized.sh` with plugin integration
- Provide migration path and compatibility information
- Maintain existing environment variable interfaces

### 4. Intelligent Environment Detection
```bash
# Enhanced detection logic
get_os_version()          # RHEL 8/9/10, CentOS 9/10, Rocky 8/9, Fedora
detect_cloud_provider()   # Hetzner, Equinix, bare metal, demo environments
select_plugins()          # Intelligent plugin selection
execute_plugins()         # Plugin framework orchestration
```

## Consequences

### Positive
- **Comprehensive OS Support**: All modern enterprise Linux distributions supported
- **Reduced Maintenance**: Single plugin framework instead of multiple scripts
- **Enhanced Intelligence**: Automatic environment detection and optimization
- **Improved Reliability**: Idempotent operations and better error handling
- **Future-Proof**: Easy to add new OS/cloud support via plugins
- **Better User Experience**: Clear next steps and intelligent guidance

### Negative
- **Migration Complexity**: Users need to understand new plugin-based approach
- **Testing Requirements**: Need to validate across all supported environments
- **Documentation Updates**: All deployment guides need updating

### Risks and Mitigations
- **Risk**: Breaking existing workflows
  - **Mitigation**: Maintain backward compatibility and provide migration guide
- **Risk**: Plugin framework bugs affecting setup
  - **Mitigation**: Comprehensive testing and fallback to legacy scripts
- **Risk**: User confusion about new approach
  - **Mitigation**: Clear documentation and migration assistance

## Implementation Plan

### Phase 1: Core Modernization (Week 1)
- [x] Create `setup_modernized.sh` with plugin integration
- [x] Implement enhanced OS detection for all supported versions
- [x] Add cloud provider and environment detection
- [ ] Test on CentOS Stream 10 environment

### Phase 2: Validation and Documentation (Week 2)
- [ ] Test across all supported OS versions (RHEL 8/9/10, Rocky 8/9, CentOS 9/10)
- [ ] Validate cloud provider detection (Hetzner, Equinix)
- [ ] Update deployment documentation
- [ ] Create migration guide from legacy setup

### Phase 3: Integration and Rollout (Week 3)
- [ ] Replace `setup.sh` with modernized version
- [ ] Archive legacy scripts with clear deprecation notices
- [ ] Update all deployment guides and documentation
- [ ] Announce changes to community

## Validation Criteria

### Technical Validation
- [ ] All supported OS versions detected correctly
- [ ] Plugin framework integration works seamlessly
- [ ] Cloud provider detection functions properly
- [ ] Backward compatibility maintained for existing users
- [ ] Performance equivalent or better than legacy scripts

### User Experience Validation
- [ ] Clear and helpful output messages
- [ ] Intelligent next steps provided
- [ ] Error messages are actionable
- [ ] Migration path is straightforward
- [ ] Documentation is comprehensive

## Related ADRs
- ADR-0028: Modular Plugin Framework for Extensibility
- ADR-0026: RHEL 10/CentOS 10 Platform Support Strategy
- ADR-0029: Documentation Strategy and Website Modernization

## References
- Plugin Framework Implementation: `/root/qubinode_navigator/core/`
- Legacy Setup Script: `/root/qubinode_navigator/setup.sh`
- Modernized Setup Script: `/root/qubinode_navigator/setup_modernized.sh`
- Plugin Configurations: `/root/qubinode_navigator/config/plugins.yml`
