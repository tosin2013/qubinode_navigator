---
layout: default
title: ADR-0007 Bash-First Orchestration
parent: Configuration & Automation
grand_parent: Architectural Decision Records
nav_order: 7
---

# ADR-0007: Bash-First Orchestration with Python Configuration

## Status
Accepted

## Context
Qubinode Navigator required a scripting approach that could handle complex system administration tasks, package management, service configuration, and infrastructure orchestration across multiple Linux distributions (RHEL 8/9, Rocky Linux, Fedora). The solution needed to be accessible to system administrators familiar with shell scripting while providing sophisticated configuration management capabilities for complex data structures, network discovery, and YAML manipulation.

## Decision
Adopt a hybrid approach using Bash as the primary orchestration language for system-level operations, process management, and workflow control, complemented by Python scripts for complex configuration management, data processing, and structured file manipulation. Bash handles the main execution flow, system commands, and service management, while Python manages YAML configurations, network discovery, and data validation.

## Consequences

### Positive Consequences
- Leverages existing system administrator expertise with Bash scripting
- Provides powerful data processing capabilities through Python
- Enables complex YAML and JSON manipulation with Python libraries
- Maintains compatibility with standard Linux system administration practices
- Allows sophisticated network and system discovery through Python libraries
- Provides clear separation between orchestration logic and configuration management
- Facilitates debugging with familiar tools and approaches

### Negative Consequences  
- Requires maintaining expertise in two different programming languages
- Potential for inconsistent error handling between Bash and Python components
- Complexity in managing dependencies for both Bash utilities and Python packages
- May create confusion about which language to use for new functionality
- Debugging issues that span both Bash and Python components can be challenging
- Performance overhead from context switching between languages

## Alternatives Considered

1. **Pure Bash scripting** - Rejected due to limitations in complex data processing and YAML handling
2. **Pure Python approach** - Would alienate system administrators familiar with shell scripting
3. **Ansible-only automation** - Insufficient for complex system setup and package management
4. **Go or Rust single binary** - Would require significant rewrite and learning curve
5. **Node.js with shell integration** - Less familiar to target audience of system administrators

## Evidence Supporting This Decision

- Primary orchestration in `setup.sh` (489 lines) and `qubinode_navigator.sh` using Bash
- Complex configuration management in `load-variables.py` using Python
- Bash handles system package installation, service management, and process control
- Python manages YAML file manipulation, network discovery, and data validation
- Clear separation of concerns between orchestration and configuration

## Implementation Details

### Bash Orchestration Responsibilities
```bash
# From setup.sh - System-level orchestration
function configure_os(){
    if [ ${1} == "ROCKY8" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user gcc python3-devel podman ansible-core make sshpass -y
    elif [ ${1} == "FEDORA" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user gcc python3-devel podman ansible-core make sshpass -y
    fi
}
```

### Python Configuration Management
```python
# From load-variables.py - Complex data processing
def update_inventory(username=None, domain_name=None, dnf_forwarder=None):
    inventory_path = 'inventories/'+str(inventory_env)+'/group_vars/all.yml'
    with open(inventory_path, 'r') as f:
        inventory = yaml.safe_load(f)
    # Complex YAML manipulation and validation
```

### Language Responsibility Matrix

| Task Category | Primary Language | Rationale |
|---------------|------------------|-----------|
| System Package Management | Bash | Native system integration |
| Service Control | Bash | Standard Linux administration |
| Process Management | Bash | Shell process control |
| File System Operations | Bash | Native file system commands |
| Network Configuration | Python | Complex data structures |
| YAML/JSON Processing | Python | Structured data libraries |
| Data Validation | Python | Rich validation libraries |
| API Interactions | Python | HTTP libraries and JSON handling |

### Integration Patterns
```bash
# Bash calling Python for configuration
python3 load-variables.py --username "$USERNAME" --domain "$DOMAIN"

# Python updating files that Bash will use
# Python writes YAML, Bash reads environment variables
```

### Error Handling Strategy
- **Bash**: Uses exit codes and conditional execution (`|| exit 1`)
- **Python**: Uses exceptions with try/catch blocks
- **Integration**: Python scripts return appropriate exit codes for Bash consumption

### Dependency Management
```bash
# Bash manages system dependencies
sudo pip3 install -r requirements.txt

# Python requirements.txt manages Python dependencies
# fire
# netifaces  
# psutil
# requests
```

### Key Libraries and Tools

#### Bash Utilities
- **System Commands**: `dnf`, `yum`, `systemctl`, `firewall-cmd`
- **File Operations**: `cp`, `mv`, `mkdir`, `chmod`, `chown`
- **Network Tools**: `ssh`, `scp`, `curl`, `wget`
- **Process Control**: `ps`, `kill`, `jobs`, `nohup`

#### Python Libraries
- **YAML Processing**: `yaml` library for configuration file manipulation
- **Network Discovery**: `netifaces` for network interface information
- **System Information**: `psutil` for system and process utilities
- **CLI Interface**: `fire` for command-line interface generation
- **HTTP Requests**: `requests` for API interactions

### Workflow Integration
1. **Bash Orchestration**: Main workflow control and system setup
2. **Python Configuration**: Generate and validate configuration files
3. **Bash Execution**: Execute system commands based on Python-generated configs
4. **Python Validation**: Verify system state and configuration consistency

### Development Guidelines
- **Bash Scripts**: Focus on system operations, process control, and workflow orchestration
- **Python Scripts**: Handle complex data processing, validation, and structured file manipulation
- **Interface Design**: Clear parameter passing and return code conventions
- **Error Propagation**: Consistent error handling across language boundaries

## Benefits Realized

### Operational Benefits
- **Familiar Tools**: System administrators can work with familiar Bash patterns
- **Powerful Processing**: Complex configuration tasks handled efficiently in Python
- **System Integration**: Native Linux system administration capabilities
- **Flexibility**: Right tool for each specific task type

### Development Benefits
- **Clear Separation**: Distinct responsibilities for each language
- **Maintainability**: Easier to maintain focused, single-purpose scripts
- **Testability**: Each component can be tested independently
- **Extensibility**: Easy to extend with new Bash or Python components

### Performance Benefits
- **Efficiency**: Each language used for its strengths
- **Resource Usage**: Minimal overhead for simple system operations
- **Scalability**: Python handles complex data processing efficiently

## Related Decisions
- ADR-0001: Container-First Execution Model with Ansible Navigator
- ADR-0002: Multi-Cloud Inventory Strategy with Environment-Specific Configurations
- ADR-0003: Dynamic Configuration Management with Python
- ADR-0004: Security Architecture with Ansible Vault and AnsibleSafe
- ADR-0005: KVM/Libvirt Virtualization Platform Choice
- ADR-0006: Modular Dependency Management Strategy

## Date
2025-01-09

## Stakeholders
- DevOps Team
- System Administrators
- Infrastructure Team
- Development Teams
- Project Maintainers
