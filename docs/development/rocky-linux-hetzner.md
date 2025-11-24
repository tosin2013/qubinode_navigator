---
layout: default
title:  Rocky Linux on Hetzner
parent: Developer Documentation
nav_order: 1
---
**Script Structure**

The script consists of several major functions:

* `bash_aliases`: Configures bash aliases and sources function definitions.
* `confiure_lvm_storage`: Configures LVM storage for the Qubinode environment.
* `setup_kcli_base`: Sets up KCLI (Kubernetes Cluster Lifecycle Interface) and configures images.
* `show_help`: Displays help information for the script.

[Full Script](https://github.com/Qubinode/qubinode_navigator/blob/main/rocky-linux-hetzner.sh)

**Key Code Snippets**

1. `bash_aliases`:
```bash
if [ "$(pwd)" != "/root/qubinode_navigator" ]; then
    echo "Current directory is not /root/qubinode_navigator."
    echo "Changing to /root/qubinode_navigator..."
    cd /root/qubinode_navigator
fi
```
This code snippet checks the current working directory and changes it if necessary. This ensures that the script runs in the correct directory.

1. `confiure_lvm_storage`:
```bash
if [ ! -f /tmp/configure-lvm.sh ]; then
    curl -OL https://raw.githubusercontent.com/Qubinode/qubinode_navigator/main/dependancies/equinix-rocky/configure-lvm.sh
    mv configure-lvm.sh /tmp/configure-lvm.sh
    sudo chmod +x /tmp/configure-lvm.sh
fi
```
This code snippet checks if the `configure-lvm.sh` script exists. If not, it downloads and installs the script from GitHub.

**External Dependencies**

The script relies on the following external dependencies:

* Bash aliases: The script uses bash aliases to configure various components of the Qubinode ecosystem.
* LVM storage: The script configures LVM storage for the Qubinode environment.
* KCLI (Kubernetes Cluster Lifecycle Interface): The script sets up and configures KCLI.

**Input and Output Formats**

The script accepts command-line arguments, which can be used to customize its behavior. For example:

* `-h` or `--help`: Displays help information for the script.
* `--deploy-kvmhost`: Deploys a KVM host.
* `--configure-bash-aliases`: Configures bash aliases.

**Best Practices**

When modifying or extending the script, follow these best practices:

1. Use clear and concise variable names.
2. Follow coding conventions and style guidelines (e.g., PEP 8 for Python).
3. Test your changes thoroughly to ensure they do not break existing functionality.

**References**

For more information on the Qubinode project and its components, refer to the following resources:

* [Qubinode documentation](https://qubinode.readthedocs.io/en/latest/)
* [Kubernetes Cluster Lifecycle Interface (KCLI) documentation](https://kcli.readthedocs.io/en/latest/)
* [Bash scripting guide](https://tldp.org/LDP/abs/html/index.html)