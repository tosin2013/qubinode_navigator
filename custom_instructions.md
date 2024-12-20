# Custom Instructions for `rhel9-linux-hypervisor.sh`

## Purpose
The `rhel9-linux-hypervisor.sh` script is designed to automate the setup and configuration of a RHEL 9-based hypervisor. It includes functions for installing packages, configuring various services (like KVM, Ansible Navigator, HashiCorp Vault, etc.), and setting up the environment for different CI/CD environments (Onedev, GitLab, GitHub).

## Key Functions and Their Roles
- **`main()`**: Orchestrates the entire setup process by calling various configuration functions.
- **`check_root()`**: Ensures the script is run as root.
- **`handle_hashicorp_vault()`**: Configures HashiCorp Vault.
- **`hcp_cloud_vault()`**: Configures HashiCorp Cloud Vault if enabled.
- **`install_packages()`**: Installs necessary packages.
- **`configure_firewalld()`**: Configures the firewall.
- **`configure_lvm_storage()`**: Configures LVM storage.
- **`clone_repository()`**: Clones a repository (likely for additional configuration files).
- **`configure_ansible_navigator()`**: Configures Ansible Navigator.
- **`configure_ansible_vault()`**: Configures Ansible Vault.
- **`generate_inventory()`**: Generates an inventory file for Ansible.
- **`configure_navigator()`**: Configures the navigator (likely Ansible Navigator).
- **`configure_ssh()`**: Configures SSH.
- **`deploy_kvmhost()`**: Deploys the KVM host.
- **`configure_bash_aliases()`**: Configures Bash aliases.
- **`setup_kcli_base()`**: Sets up KCLI base.
- **`configure_route53()`**: Configures Route53.
- **`configure_cockpit_ssl()`**: Configures Cockpit with SSL.
- **`configure_onedev()`, `configure_gitlab()`, `configure_github()`**: Configures CI/CD environments based on the environment variable.
- **`configure_ollama()`**: Configures Ollama if the workload is enabled.

## How It Connects to Other Parts of the Project
- The script sources multiple other scripts located in the `scripts/` directory, such as `common_functions.sh`, `install_packages.sh`, `configure_kvm.sh`, etc. These scripts provide modularized functions that are essential for the hypervisor setup.
- It interacts with various configuration files and directories, such as `ansible-builder/`, `ansible-navigator/`, and `inventories/`, which are part of the broader project structure.
- The script also sets up different CI/CD environments (Onedev, GitLab, GitHub) based on environment variables, indicating its integration with the project's CI/CD pipeline.
