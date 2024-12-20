# Qubinode Navigator
This repository contains a quickstart script setup.sh to set up and configure Qubinode Navigator. Qubinode Navigator helps to automate the deployment and management of virtual machines, containers, and other infrastructure resources.

## Prerequisites
* Linux-based operating system (RHEL 9.2, CentOS, Rocky Linux, or Fedora)
* Git

## Documentation
* [Qubinode Navigator Documentation](https://tosin2013.github.io/qubinode_navigator/)

## Quickstart 

### Running on RHEL, CentOS, or Fedora
```
curl https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/setup.sh | bash
```

## Goals of the Repository
The primary goal of this repository is to provide a streamlined and automated approach to setting up and managing infrastructure resources such as virtual machines, containers, and other services. The scripts and configurations included in this repository aim to simplify the deployment process, reduce manual intervention, and ensure consistency across environments.

### Goals of `rhel9-linux-hypervisor.sh`
The `rhel9-linux-hypervisor.sh` script is designed to automate the setup and configuration of a RHEL 9-based hypervisor. Its goals include:
1. **Automate the setup of a RHEL 9-based hypervisor**: The script aims to simplify the deployment process by automating the installation and configuration of necessary packages and services.
2. **Configure various services**: The script configures services such as KVM, Ansible Navigator, HashiCorp Vault, SSH, firewall, and more.
3. **Support for multiple CI/CD environments**: The script can configure different CI/CD environments (Onedev, GitLab, GitHub) based on the environment variable.
4. **Ensure consistency across environments**: The script ensures that the configuration is consistent across different environments by automating the setup process.
The primary goal of this repository is to provide a streamlined and automated approach to setting up and managing infrastructure resources such as virtual machines, containers, and other services. The scripts and configurations included in this repository aim to simplify the deployment process, reduce manual intervention, and ensure consistency across environments.

## Contributing
[Contributing to Qubinode Navigator: A Comprehensive Developer's Guide](https://tosin2013.github.io/qubinode_navigator/development/developers_guide.html)
