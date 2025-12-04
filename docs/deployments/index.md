______________________________________________________________________

## layout: default title: Deployment Documentation nav_order: 2 has_children: true description: "Comprehensive deployment guides for different platforms and environments"

# Deployment Documentation

{: .fs-8 }

Choose your deployment platform and follow our comprehensive guides to deploy OpenShift with Qubinode Navigator.
{: .fs-6 .fw-300 }

______________________________________________________________________

## Available Deployment Options

| Platform                   | Use Case                                     | Complexity | Guide                                                       |
| :------------------------- | :------------------------------------------- | :--------- | :---------------------------------------------------------- |
| **🌐 Hetzner Cloud**       | Cloud deployment with managed infrastructure | ⭐⭐       | [Deploy on Hetzner](/deployments/demo-hetzner-com.html)     |
| **🔴 Red Hat Demo System** | Demo and testing environments                | ⭐         | [Deploy on Red Hat Demo](/deployments/demo-redhat-com.html) |
| **🖥️ Baremetal Server**    | On-premises deployment with full control     | ⭐⭐⭐     | [Deploy on Baremetal](/deployments/setup-sh.html)           |

______________________________________________________________________

## Prerequisites

Before starting any deployment, ensure you have:

- **Operating System**: RHEL 8/9 or Rocky Linux
- **Hardware**: Minimum 32GB RAM, 500GB storage
- **Network**: Internet connectivity for package downloads
- **Access**: Root or sudo privileges
- **Credentials**: Platform-specific access credentials

______________________________________________________________________

## Quick Start

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Qubinode/qubinode_navigator.git
   cd qubinode_navigator
   ```

1. **Choose your platform** and follow the specific guide

1. **Run the setup script** with platform-specific parameters

1. **Monitor the deployment** progress and logs

______________________________________________________________________

## Security Considerations

All deployment methods support:

- **HashiCorp Vault integration** for secure credential management
- **Ansible Vault** for encrypted configuration files
- **SSH key-based authentication** for secure access
- **Network security** with firewall configurations

For detailed security setup, see our [Security Documentation](/security/).
