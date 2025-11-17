---
layout: default
title: Qubinode Navigator
nav_order: 1
description: "Modern AI-enhanced infrastructure automation platform with plugin architecture"
permalink: /
---

# Qubinode Navigator
{: .fs-9 }

Modern AI-enhanced, container-first infrastructure automation platform with modular plugin architecture, supporting RHEL 10, CentOS Stream 10, and next-generation enterprise deployments.
{: .fs-6 .fw-300 }

[Get started now](#getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/tosin2013/qubinode_navigator){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Overview

Qubinode Navigator is a next-generation infrastructure automation platform built with a **modular plugin architecture** and **AI-enhanced capabilities**. It simplifies enterprise infrastructure deployment across multiple operating systems and cloud providers, with special focus on **RHEL 10/CentOS Stream 10** support and **container-first execution**.

## 🚀 Key Features

- **🔌 Plugin Architecture**: Extensible framework with OS, cloud provider, and deployment plugins
- **🤖 AI-Powered Assistant**: CPU-based AI deployment guidance with interactive troubleshooting *(coming soon)*
- **🖥️ Next-Gen OS Support**: Native RHEL 10, CentOS Stream 10, Rocky Linux, and Fedora support
- **📦 Container-First**: Ansible Navigator execution with standardized environments
- **🌐 Multi-Cloud Ready**: Equinix, Hetzner, AWS, and bare-metal deployments
- **🔒 Enterprise Security**: HashiCorp Vault integration and progressive SSH security
- **📊 Automated Updates**: Intelligent update detection and compatibility validation *(coming soon)*
- **🧪 Comprehensive Testing**: 84%+ test coverage with real deployment validation

---

## Quick Start

### Prerequisites

- **Operating System**: RHEL 8/9/10, CentOS Stream 10, Rocky Linux, or Fedora
- **Memory**: Minimum 4GB RAM (8GB+ recommended for AI features)
- **Storage**: 500GB+ available space
- **Container Runtime**: Podman or Docker
- **Network**: Internet connectivity for package downloads

### Modern Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/tosin2013/qubinode_navigator.git
cd qubinode_navigator

# Run the modernized setup script with plugin framework
./setup_modernized.sh
```

### Plugin Framework CLI

```bash
# List available plugins
python3 qubinode_cli.py list

# Deploy with specific OS plugin
python3 qubinode_cli.py deploy --plugin rhel10

# Get plugin information
python3 qubinode_cli.py info --plugin centos_stream10
```

### Legacy Installation

```bash
# Traditional setup script (compatibility mode)
./setup.sh
```

---

## Deployment Options

| Platform | Description | Guide |
|:---------|:------------|:------|
| **Hetzner Cloud** | Deploy on Hetzner's cloud infrastructure | [Hetzner Guide](/deployments/demo-hetzner-com.html) |
| **Red Hat Demo** | Deploy on Red Hat Product Demo System | [Demo Guide](/deployments/demo-redhat-com.html) |
| **Baremetal** | Deploy on physical hardware | [Baremetal Guide](/deployments/setup-sh.html) |

---

## 🏗️ Architecture & Design

Qubinode Navigator follows a **modern, plugin-based architecture** with comprehensive decision documentation:

### 📋 **Latest Architectural Decisions (2025)**
- [**ADR-0026**: RHEL 10/CentOS 10 Platform Support Strategy](/adrs/adr-0026-rhel-10-centos-10-platform-support-strategy.html)
- [**ADR-0027**: CPU-Based AI Deployment Assistant Architecture](/adrs/adr-0027-cpu-based-ai-deployment-assistant-architecture.html)
- [**ADR-0028**: Modular Plugin Framework for Extensibility](/adrs/adr-0028-modular-plugin-framework-for-extensibility.html)
- [**ADR-0029**: Documentation Strategy and Website Modernization](/adrs/adr-0029-documentation-strategy-and-website-modernization.html)
- [**ADR-0030**: Software and OS Update Strategy](/adrs/adr-0030-software-and-os-update-strategy.html)

### 🏛️ **Foundation ADRs**
- [**ADR-0001**: Container-First Execution Model](/adrs/adr-0001-container-first-execution-model-with-ansible-navigator.html)
- [**ADR-0004**: Security Architecture with Ansible Vault](/adrs/adr-0004-security-architecture-ansible-vault.html)
- [**ADR-0023**: HashiCorp Vault Integration](/adrs/adr-0023-enhanced-configuration-management-with-template-support-and-hashicorp-vault-integration.html)

### 🔐 **Enterprise Security**
- **HashiCorp Vault Integration**: Centralized secret management
- **Ansible Vault**: Encrypted configuration files and credentials
- **Progressive SSH Security**: Multi-layered access controls and key management
- **Container Isolation**: Secure execution environments with Ansible Navigator
- **Credential Scanning**: Automated detection of exposed secrets

### 🔌 **Plugin Architecture**
- **OS Plugins**: RHEL 8/9/10, CentOS Stream 10, Rocky Linux, Fedora
- **Cloud Plugins**: Equinix, Hetzner, AWS integrations
- **Environment Plugins**: Red Hat Demo, development, production configurations
- **Service Plugins**: Vault integration, monitoring, logging
- **Extensible Framework**: Easy plugin development with standardized interfaces

---

## Documentation Sections

| Section | Description |
|:--------|:------------|
| [**Deployment Guides**](/deployments/) | Step-by-step deployment instructions for different platforms |
| [**Developer Documentation**](/development/) | Contributing guides, development setup, and coding standards |
| [**Plugins**](/plugins/) | Available plugins and integration guides |
| [**Security**](/security/) | Security architecture and vault integration guides |
| [**Research**](/research/) | Technical research and analysis documentation |

---

## Getting Started

Ready to deploy OpenShift with Qubinode Navigator? Choose your deployment path:

1. **📖 Read the Documentation**: Start with our [Deployment Documentation](/deployments/) to understand the available options
2. **🚀 Quick Deploy**: Use the automated setup script for rapid deployment
3. **🔧 Custom Setup**: Follow platform-specific guides for tailored deployments
4. **🔒 Security Setup**: Configure [HashiCorp Vault integration](/vault-setup/) for enhanced security

### Next Steps

- [Choose your deployment platform](/deployments/)
- [Set up your development environment](/development/)
- [Configure security features](/security/)
- [Explore available plugins](/plugins/)

---

## Community & Support

### 🤝 Contributing

We welcome contributions from the community! Here's how you can get involved:

- **📝 Documentation**: Help improve our guides and documentation
- **🐛 Bug Reports**: Report issues and help us improve
- **💡 Feature Requests**: Suggest new features and enhancements
- **🔧 Code Contributions**: Submit pull requests with improvements

Read our [Contributing Guide](/development/developers_guide.html) to get started.

### 📞 Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/tosin2013/qubinode_navigator/issues)
- **Documentation**: Comprehensive guides and troubleshooting
- **Community**: Join discussions and share experiences

---

## License

This project is licensed under the [GNU General Public License v3.0](https://github.com/tosin2013/qubinode_navigator/blob/main/LICENSE).

---

*Qubinode Navigator - Simplifying OpenShift deployment on KVM infrastructure.*
