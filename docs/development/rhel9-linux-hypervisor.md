---
layout: default
title:  Rhel9 Linux Hypervisor
parent: Developer Documentation
nav_order: 1
---

**Script Structure**

The script consists of several major functions:

* `check_root`: Verifies if the script is running with root privileges.
* `handle_hashicorp_vault`: Handles HashiCorp Vault-related tasks.
* `install_packages`: Installs necessary packages for the Qubinode environment.
* `configure_firewalld`: Configures firewalld rules for the Qubinode environment.
* `confiure_lvm_storage`: Configures LVM storage for the Qubinode environment.
* `clone_repository`: Clones a repository required for the Qubinode environment.
* `configure_ansible_navigator`: Configures Ansible Navigator settings.
* `configure_ansible_vault`: Configures Ansible Vault settings.
* `generate_inventory`: Generates an inventory file for Ansible.
* `configure_navigator`: Configures the Qubinode Navigator settings.
* `configure_ssh`: Configures SSH settings for the Qubinode environment.
* `deploy_kvmhost`: Deploys a KVM host for the Qubinode environment.
* `configure_bash_aliases`: Configures bash aliases for the Qubinode environment.
* `setup_kcli_base`: Sets up kcli base configuration.
* `configure_route53`: Configures Route53 settings.
* `configure_cockpit_ssl`: Configures Cockpit SSL settings.
* `configure_gitlab`: Configures GitLab settings (if CICD_ENVIORNMENT is set to "gitlab").
* `configure_ollama`: Configures Ollama Workload settings (if OLLAMA_WORKLOAD is set to "true").

[Full Script](https://github.com/Qubinode/qubinode_navigator/blob/main/rhel9-linux-hypervisor.sh)

**Key Code Snippets and Algorithms**

1. The script uses the `curl` command to check if Ollama is already running and skip configuration if it is.
2. The script sets the `OLLAMA_API_BASE` environment variable by appending a line to the `~/.bashrc` file.

**External Dependencies and Libraries**

The script relies on the following external dependencies:

* HashiCorp Vault
* Ansible Navigator
* Cockpit SSL
* Route53
* GitLab (if CICD_ENVIORNMENT is set to "gitlab")
* Ollama Workload (if OLLAMA_WORKLOAD is set to "true")

**Input and Output Formats**

The script accepts the following input formats:

* Command-line arguments: `USE_HASHICORP_CLOUD`, `CICD_ENVIORNMENT`, and `OLLAMA_WORKLOAD`
* Configuration files: Not applicable
* Expected results: The script generates various configuration files, inventory files, and sets environment variables

**Best Practices for Modifying or Extending the Script**

1. Follow coding conventions and style guidelines (e.g., PEP 8 for Python)
2. Use clear and descriptive variable names
3. Comment code thoroughly to explain complex logic or algorithms
4. Test changes thoroughly before committing them to the main branch

**References and Additional Resources**

For further information on the Qubinode Navigator script, please refer to:

* [The Qubinode Navigator documentation](https://qubinode.github.io/qubinode_navigator/)
* [HashiCorp Vault documentation](https://developer.hashicorp.com/vault/docs/what-is-vault)
* [Ansible Navigator documentation](https://ansible-navigator.readthedocs.io/en/latest/)
* [Cockpit SSL documentation](https://cockpit-project.org/guide/latest/https.html)
* [Route53 documentation](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)
* [GitLab documentation](https://docs.gitlab.com/)
* [Github documentation](https://docs.github.com/en)
* [Ollama Workload documentation](https://www.ollama.com/)