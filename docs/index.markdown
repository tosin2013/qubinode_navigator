---
layout: default
title: Qubinode Navigator
nav_order: 1
description: "Infrastructure automation platform for deploying OpenShift on KVM"
permalink: /
---

# Qubinode Navigator
{: .fs-9 }

Infrastructure automation platform for deploying OpenShift on KVM using Ansible, with support for multiple cloud providers and comprehensive security features.
{: .fs-6 .fw-300 }

[Get started now](#getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/tosin2013/qubinode_navigator){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Overview

Qubinode Navigator is a powerful infrastructure automation platform that simplifies the deployment of OpenShift on KVM environments. Whether you're deploying on cloud providers like Hetzner, Red Hat Product Demo System, or baremetal servers, Qubinode Navigator provides comprehensive guides and automation tools for a smooth deployment experience.

## Key Features

- **🚀 Multi-Platform Support**: Deploy on Hetzner, Red Hat Demo System, or baremetal servers
- **🔒 Security-First**: Integrated HashiCorp Vault support and comprehensive security features
- **📦 Container-First**: Ansible Navigator execution environment with modern tooling
- **🔧 Modular Architecture**: Flexible plugin system and configurable deployment options
- **📚 Comprehensive Documentation**: Detailed guides, ADRs, and research documentation

---

## Quick Start

### Prerequisites

- RHEL 8/9 or Rocky Linux system
- Minimum 32GB RAM, 500GB storage
- Internet connectivity for package downloads

### Installation

```bash
# Clone the repository
git clone https://github.com/tosin2013/qubinode_navigator.git
cd qubinode_navigator

# Run the setup script
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

## Architecture & Security

Qubinode Navigator follows modern infrastructure automation best practices:

### 🏗️ **Architectural Decision Records (ADRs)**
- [Container-First Execution Model](/adrs/adr-0001-container-first-execution-model-with-ansible-navigator.html)
- [Security Architecture with Ansible Vault](/adrs/adr-0004-security-architecture-ansible-vault.html)
- [HashiCorp Vault Integration](/adrs/adr-0023-enhanced-configuration-management-with-template-support-and-hashicorp-vault-integration.html)

### 🔐 **Security Features**
- **HashiCorp Vault Integration**: Secure credential management
- **Ansible Vault**: Encrypted configuration files
- **Progressive SSH Security**: Multi-layered access controls
- **Security Compliance**: Built-in security best practices

### 🔌 **Plugin Ecosystem**
- **Kcli Pipelines**: Streamlined deployment automation
- **OneDev Integration**: Git server with CI/CD capabilities
- **GitHub Actions**: Automated testing and deployment
- **Custom Extensions**: Modular plugin architecture

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
