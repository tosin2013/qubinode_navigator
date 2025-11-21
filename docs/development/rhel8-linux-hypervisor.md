---
layout: default
title:  Rhel8 Linux Hypervisor
parent: Developer Documentation
nav_order: 1
---

**Script Structure**

The script consists of several major functions:

* `configure_bash_aliases`: Configures bash aliases for the Qubinode environment.
* `confiure_lvm_storage`: Configures LVM storage for the Qubinode host.
* `setup_kcli_base`: Sets up KCLI (Kubernetes Cluster Lifecycle Interface) and configures images for the Qubinode cluster.
* `show_help`: Displays help information for the script.

[Full Script](https://github.com/tosin2013/qubinode_navigator/blob/main/rhel8-linux-hypervisor.sh)

**Key Code Snippets**

1. The `configure_bash_aliases` function uses a combination of `if` statements and `source` commands to configure bash aliases. For example:
```bash
if [ "$(pwd)" != "/root/qubinode_navigator" ]; then
    echo "Current directory is not /root/qubinode_navigator."
    echo "Changing to /root/qubinode_navigator..."
    cd /root/qubinode_navigator
fi
```
This code snippet checks the current working directory and changes it if necessary.

1. The `confiure_lvm_storage` function uses `curl` to download a configuration script from GitHub and then executes it using `sudo`. For example:
```bash
if [ ! -f /tmp/configure-lvm.sh ]; then
    curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/dependancies/equinix-rocky/configure-lvm.sh
    mv configure-lvm.sh /tmp/configure-lvm.sh
    sudo chmod +x /tmp/configure-lvm.sh
fi
/tmp/configure-lvm.sh || exit 1
```
This code snippet downloads and executes a configuration script for LVM storage.

**External Dependencies**

The script relies on the following external dependencies:

* `bash-aliases/functions.sh`: A file containing bash function definitions.
* `bash-aliases/aliases.sh`: A file containing bash alias definitions.
* `freeipa-utils`: A package used for deploying FreeIPA (Free Identity, Authentication, and Policy).
* `kcli`: A package used for setting up KCLI.

**Input and Output Formats**

The script accepts command-line arguments in the following format:
```bash
$0 [OPTION]
```
Where `[OPTION]` can be one of the following:

* `-h`, `--help`: Displays help information.
* `--deploy-kvmhost`: Deploys a KVM host.
* `--configure-bash-aliases`: Configures bash aliases.
* `--setup-kcli-base`: Sets up KCLI and configures images.

The script also uses configuration files in the following format:
```bash
~/.bash_aliases: A file containing bash alias definitions.
```
**Best Practices**

When modifying or extending the script, follow these best practices:

1. Use clear and concise variable names.
2. Follow coding conventions and style guidelines (e.g., PEP 8 for Python).
3. Test your changes thoroughly to ensure they do not break existing functionality.

**References**

For further information on the Qubinode Navigator script, refer to the following resources:

* [Qubinode project documentation](https://github.com/tosin2013/qubinode_navigator/blob/main/docs/README.md)
* [FreeIPA documentation](https://freeipa.org/documentation/)
* [KCLI documentation](https://kcli.readthedocs.io/en/latest/)
