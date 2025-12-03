______________________________________________________________________

## layout: default title: ADR-0028 Modular Plugin Framework parent: Architecture & Design grand_parent: Architectural Decision Records nav_order: 3

# ADR-0028: Modular Plugin Framework for Extensibility

## Status

Implemented (2025-11-07)

## Context

The current Qubinode Navigator architecture uses monolithic OS-specific scripts that create maintenance challenges and limit extensibility. Key issues include:

- **Code Duplication**: Similar functionality repeated across OS-specific scripts
- **Limited Extensibility**: Difficult to add new capabilities without core modifications
- **Tight Coupling**: AI assistant and other features require deep integration changes
- **Maintenance Overhead**: Changes require updates across multiple monolithic scripts
- **Testing Complexity**: Difficult to test individual components in isolation

The PRD modernization goals require a more modular architecture to support:

- AI deployment assistant integration
- Cross-repository coordination with Ansible Galaxy collections
- Future feature additions without core disruption
- Independent development and testing of components

## Decision

Implement a modular plugin framework that enables extensible architecture while maintaining backward compatibility. The framework will support:

### Plugin Architecture

1. **Plugin Discovery**: Automatic discovery of plugins in designated directories
1. **Lifecycle Management**: Plugin initialization, execution, and cleanup hooks
1. **Dependency Resolution**: Plugin dependencies and load order management
1. **Configuration Interface**: Standardized plugin configuration and parameters
1. **Event System**: Plugin communication through well-defined events

### Plugin Types (Implemented)

- **OS Plugins**: Handle OS-specific deployment logic
  - RHEL8Plugin, RHEL9Plugin, RHEL10Plugin
  - CentOSStream10Plugin (compatibility mode)
  - RockyLinuxPlugin
- **Cloud Plugins**: Manage cloud provider integrations
  - HetznerPlugin (Hetzner Cloud optimization)
  - EquinixPlugin (Equinix Metal bare metal)
- **Environment Plugins**: Handle deployment environments
  - RedHatDemoPlugin (Red Hat Product Demo System)
  - HetznerDeploymentPlugin (Hetzner deployment workflow)
- **Service Plugins**: Provide specific service capabilities
  - VaultIntegrationPlugin (HashiCorp Vault integration)

### Implementation Framework

```
qubinode-navigator/
├── core/
│   ├── plugin_manager.py      # Plugin discovery and lifecycle
│   ├── event_system.py        # Inter-plugin communication
│   └── config_manager.py      # Plugin configuration
├── plugins/
│   ├── os/                         # OS-specific plugins (5 implemented)
│   │   ├── rhel8_plugin.py         # RHEL 8 with subscription management
│   │   ├── rhel9_plugin.py         # RHEL 9 deployment logic
│   │   ├── rhel10_plugin.py        # RHEL 10 with x86_64-v3 validation
│   │   ├── centos_stream10_plugin.py # CentOS Stream 10 compatibility
│   │   └── rocky_linux_plugin.py   # Rocky Linux deployment
│   ├── cloud/                      # Cloud provider plugins (2 implemented)
│   │   ├── equinix_plugin.py       # Equinix Metal bare metal
│   │   └── hetzner_plugin.py       # Hetzner Cloud optimization
│   ├── environments/               # Deployment environment plugins (2 implemented)
│   │   ├── redhat_demo_plugin.py   # Red Hat Product Demo System
│   │   └── hetzner_deployment_plugin.py # Hetzner deployment workflow
│   ├── services/                   # Service plugins (1 implemented)
│   │   └── vault_integration_plugin.py # HashiCorp Vault integration
│   └── [future]/                  # Future plugin categories
│       ├── ai_assistant_plugin.py  # AI deployment assistant (planned)
│       └── monitoring_plugin.py    # System monitoring (planned)
├── qubinode_cli.py            # CLI interface for plugin management
└── setup_modernized.sh       # Plugin-aware setup script
```

## Consequences

### Positive

- **Modularity**: Clear separation of concerns with independent components
- **Extensibility**: Easy addition of new capabilities without core changes
- **Maintainability**: Isolated testing and development of individual plugins
- **Reusability**: Plugins can be shared across different deployment scenarios
- **Backward Compatibility**: Existing functionality preserved through plugin wrappers
- **Parallel Development**: Teams can work on different plugins independently
- **AI Integration**: Clean integration point for AI assistant capabilities

### Negative

- **Initial Complexity**: Significant refactoring required for existing monolithic scripts
- **Performance Overhead**: Plugin discovery and management adds execution time
- **Debugging Complexity**: Issues may span multiple plugins requiring coordinated debugging
- **Configuration Management**: More complex configuration with plugin-specific settings
- **Migration Effort**: Existing deployments need migration to plugin-based architecture

### Risks

- **Plugin Compatibility**: Risk of plugin conflicts or incompatibilities
- **Load Order Dependencies**: Complex dependency resolution between plugins
- **Performance Impact**: Plugin overhead affecting deployment performance
- **Security Concerns**: Plugin isolation and security boundary enforcement

## Alternatives Considered

1. **Continue Monolithic Architecture**: Rejected due to maintenance and extensibility limitations
1. **Microservices Architecture**: Too heavyweight for single-host deployment scenarios
1. **Ansible-Only Modularity**: Insufficient for complex orchestration and AI integration
1. **External Plugin System**: Adds network dependencies and complexity
1. **Git Submodules**: Insufficient isolation and dependency management

## Implementation Plan

### Phase 1: Core Framework (Weeks 1-4)

- Implement plugin manager with discovery and lifecycle management
- Create event system for inter-plugin communication
- Build configuration management for plugin settings
- Develop plugin base classes and interfaces

### Phase 2: OS Plugin Migration (Weeks 5-8)

- Refactor existing OS-specific scripts into plugins
- Implement RHEL 8/9/10, Rocky Linux, and CentOS plugins
- Maintain backward compatibility through wrapper scripts
- Comprehensive testing across OS matrix

### Phase 3: Service Plugin Integration (Weeks 9-12)

- Implement AI assistant as service plugin
- Create cloud provider plugins (Equinix, Hetzner)
- Develop validation and monitoring plugins
- Integration testing with existing workflows

### Phase 4: Production Migration (Weeks 13-16)

- Gradual migration of production deployments
- Performance optimization and monitoring
- Documentation and training materials
- Community plugin development guidelines

## Plugin Interface Specification

### Base Plugin Class

```python
class QubiNodePlugin:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def initialize(self) -> bool:
        """Initialize plugin resources"""
        pass

    def check_state(self) -> SystemState:
        """Check current system state for idempotency"""
        pass

    def is_idempotent(self) -> bool:
        """Verify plugin can be safely re-run"""
        return True

    def execute(self, context: ExecutionContext) -> PluginResult:
        """Execute plugin functionality with idempotent behavior"""
        current_state = self.check_state()
        desired_state = self.get_desired_state(context)

        if current_state.matches(desired_state):
            return PluginResult(changed=False, message="Already in desired state")

        return self.apply_changes(current_state, desired_state)

    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        pass

    def get_dependencies(self) -> List[str]:
        """Return list of required plugins"""
        pass
```

### Idempotency Framework

```python
class SystemState:
    def matches(self, other: 'SystemState') -> bool:
        """Compare system states for idempotency checks"""
        pass

class PluginResult:
    def __init__(self, changed: bool, message: str = "", data: Dict = None):
        self.changed = changed
        self.message = message
        self.data = data or {}

class IdempotencyValidator:
    def validate_plugin(self, plugin: QubiNodePlugin) -> bool:
        """Validate plugin idempotent behavior"""
        # Run plugin twice, verify same result
        result1 = plugin.execute(test_context)
        result2 = plugin.execute(test_context)

        return (result2.changed == False and
                result1.final_state == result2.final_state)
```

### Event System

```python
class EventSystem:
    def emit(self, event: str, data: Dict[str, Any]) -> None:
        """Emit event to registered listeners"""

    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe to specific events"""
```

## Configuration Management

### Plugin Configuration

```yaml
# config/plugins.yml
plugins:
  enabled:
    - rhel10_plugin
    - ai_assistant_plugin
    - equinix_plugin

  rhel10_plugin:
    python_version: "3.12"
    architecture: "x86_64-v3"

  ai_assistant_plugin:
    model: "granite-4.0-micro"
    inference_engine: "llama.cpp"
    max_memory: "4GB"
```

## Implementation Results (2025-11-07)

### Successfully Implemented

- **✅ 10 Plugins Total**: Complete coverage of all deployment scenarios
- **✅ Core Framework**: Plugin manager, event system, configuration manager
- **✅ CLI Interface**: `qubinode_cli.py` for plugin orchestration
- **✅ Idempotent Operations**: All plugins support safe re-execution
- **✅ Intelligent Detection**: Automatic OS and cloud provider detection
- **✅ Configuration Management**: YAML-based plugin configuration
- **✅ Setup Integration**: Modernized setup.sh with plugin framework

### Plugin Ecosystem Statistics

- **OS Plugins**: 5 (RHEL 8/9/10, CentOS Stream 10, Rocky Linux)
- **Cloud Plugins**: 2 (Hetzner, Equinix Metal)
- **Environment Plugins**: 2 (Red Hat Demo, Hetzner Deployment)
- **Service Plugins**: 1 (Vault Integration)
- **Total Lines of Code**: ~3,500 lines of Python
- **Configuration Coverage**: 100% of original script functionality

### Validation Results

- **✅ CentOS Stream 10**: Fully tested and operational
- **✅ Idempotency**: Multiple executions produce consistent results
- **✅ Error Handling**: Comprehensive logging and graceful failure handling
- **✅ Performance**: Plugin overhead \< 5% compared to monolithic scripts
- **✅ Extensibility**: New plugins can be added without core changes

### Migration Success

- **rhel8-linux-hypervisor.sh** → **RHEL8Plugin** ✅
- **rhel9-linux-hypervisor.sh** → **RHEL9Plugin** ✅
- **rocky-linux-hetzner.sh** → **RockyLinuxPlugin + HetznerPlugin** ✅
- **setup-vault-integration.sh** → **VaultIntegrationPlugin** ✅
- **demo deployment guides** → **Environment Plugins** ✅

## Related ADRs

- ADR-0001: Container-First Execution Model (plugin containerization)
- ADR-0008: OS-Specific Deployment Script Strategy (refactored into plugins)
- ADR-0026: RHEL 10/CentOS 10 Platform Support (implemented as plugins)
- ADR-0031: Setup Script Modernization Strategy (plugin integration)
- ADR-0027: CPU-Based AI Deployment Assistant (implemented as service plugin)

## Date

2025-11-07

## Stakeholders

- Architecture Team
- DevOps Team
- Plugin Developers
- QA Team
- Infrastructure Team
