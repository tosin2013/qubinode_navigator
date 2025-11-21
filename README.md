# Qubinode Navigator

**Modern Enterprise Infrastructure Automation Platform**

Qubinode Navigator is an AI-enhanced, container-first infrastructure automation platform that provides hypervisor deployment and management capabilities across multiple cloud providers and operating systems. Built with a modular plugin architecture, it supports the latest enterprise Linux distributions including RHEL 10 and CentOS Stream 10.

## 🚀 Key Features

- **🔌 Modular Plugin Architecture**: Extensible framework with OS, cloud provider, and deployment plugins
- **🤖 AI-Powered MCP Servers**: Model Context Protocol integration for LLM-driven infrastructure management
  - **Airflow MCP Server**: DAG management and VM operations (9 tools)
  - **AI Assistant MCP Server**: RAG-powered documentation search and chat (3 tools)
- **📦 Container-First Execution**: All deployments use Ansible Navigator with standardized execution environments
- **🌐 Multi-Cloud Support**: Equinix, Hetzner, AWS, and bare-metal deployments
- **🔒 Enterprise Security**: Ansible Vault integration with HashiCorp Vault support
- **📊 Automated Updates**: Intelligent update detection and compatibility validation (planned)

## 🖥️ Supported Platforms

- **RHEL 8/9/10** - Full enterprise support with subscription management
- **CentOS Stream 10** - Next-generation enterprise Linux
- **Rocky Linux** - RHEL-compatible community distribution
- **Fedora** - Cutting-edge features and packages

## 📋 Prerequisites

- Linux-based operating system (RHEL 8+, CentOS, Rocky Linux, or Fedora)
- Git
- Podman or Docker
- 4GB+ RAM (8GB+ recommended for AI features)

## 🚀 Quick Start

### Modern Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/tosin2013/qubinode_navigator.git
cd qubinode_navigator

# Run the modernized setup script
./setup_modernized.sh
```

### Legacy Setup
```bash
curl https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/setup.sh | bash
```

### Plugin Framework CLI
```bash
# List available plugins
python3 qubinode_cli.py list

# Deploy with specific OS plugin
python3 qubinode_cli.py deploy --plugin rhel10

# Get plugin information
python3 qubinode_cli.py info --plugin rocky_linux
```

## 🏗️ Architecture

Qubinode Navigator follows a **container-first, plugin-based architecture**:

- **Core Framework** (`core/`): Plugin manager, configuration, and event system
- **OS Plugins** (`plugins/os/`): Operating system-specific deployment logic
- **Cloud Plugins** (`plugins/cloud/`): Cloud provider integrations
- **Environment Plugins** (`plugins/environments/`): Deployment environment configurations

## 📚 Documentation

- **[Complete Documentation](https://tosin2013.github.io/qubinode_navigator/)** - Full documentation website
- **[MCP Quick Start](MCP-QUICK-START.md)** - Get started with MCP servers in 5 minutes
- **[MCP Implementation Guide](FASTMCP-COMPLETE.md)** - Complete FastMCP migration details
- **[Architecture Decision Records](docs/adrs/)** - Design decisions and rationale
- **[Implementation Plan](docs/IMPLEMENTATION-PLAN.md)** - Current development status
- **[Developer Guide](https://tosin2013.github.io/qubinode_navigator/development/developers_guide.html)** - Contributing guidelines

## 🧪 Testing

The project includes comprehensive testing:

```bash
# Run unit tests
python3 -m pytest tests/unit/

# Run integration tests
python3 -m pytest tests/integration/

# Test specific plugin
python3 -m pytest tests/unit/test_rhel10_plugin.py -v
```

## 🤝 Contributing

We welcome contributions! Please see our [Developer's Guide](https://tosin2013.github.io/qubinode_navigator/development/developers_guide.html) for:

- Development setup
- Plugin development guidelines
- Testing requirements
- Code style standards

## 📄 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## 🔗 Related Projects

- [qubinode_kvmhost_setup_collection](qubinode_kvmhost_setup_collection/) - Ansible collection for KVM host setup
- [Ansible Navigator](https://ansible-navigator.readthedocs.io/) - Container-based Ansible execution