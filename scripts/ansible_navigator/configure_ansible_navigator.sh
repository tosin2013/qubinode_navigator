#!/bin/bash

# Function: configure_ansible_navigator
# Description: This function configures Ansible Navigator on a RHEL9 Linux hypervisor.
#              It performs the following steps:
#              1. Checks if ansible-navigator is installed. If not, it installs ansible-navigator using pip3.
#              2. Adds the local bin directory to the PATH environment variable and sources the profile.
#              3. Changes the directory to /opt/qubinode_navigator.
#              4. Installs the required Python packages listed in requirements.txt using pip3.
#              5. Configures Ansible Navigator settings by creating a YAML configuration file at ~/.ansible-navigator.yml.
#                 - Sets the inventory file path.
#                 - Configures the execution environment to use Podman with a specific image.
#                 - Sets the logging options, including the log file path and log level.
#                 - Disables playbook artifact generation.
#
# Parameters: None
#
# Returns: None
#
# Exit Codes:
#   1 - If any step in the configuration process fails.
#
# Dependencies:
#   - pip3 for installing ansible-navigator.
#   - dnf for installing Python packages.
#   - log_message function for logging errors.
#
# Example Usage:
#   configure_ansible_navigator
configure_ansible_navigator() {
    if ! command -v ansible-navigator &>/dev/null; then
        log_message "Installing ansible-navigator..."
        if ! pip3 install ansible-navigator --user; then
            log_message "Failed to install ansible-navigator"
            exit 1
        fi
        echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.profile
        source ~/.profile
    fi
    log_message "Configuring ansible-navigator..."
    cd "/opt/qubinode_navigator"
    if ! pip3 install -r requirements.txt; then
        log_message "Failed to install Ansible Navigator requirements"
        exit 1
    fi

    log_message "Configuring Ansible Navigator settings"
    cat >~/.ansible-navigator.yml <<EOF
---
ansible-navigator:
  ansible:
    inventory:
      entries:
      - /opt/qubinode_navigator/inventories/${INVENTORY}
  execution-environment:
    container-engine: podman
    enabled: true
    image: quay.io/qubinode/qubinode-installer:${KVM_VERSION}
    pull:
      policy: missing
  logging:
    append: true
    file: /tmp/navigator/ansible-navigator.log
    level: debug
  playbook-artifact:
    enable: false
EOF
}
