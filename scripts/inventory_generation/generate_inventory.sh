#!/bin/bash

# Function: generate_inventory
# Description: Generates an Ansible inventory file for the control node.
# It performs the following steps:
# 1. Logs a message indicating the start of inventory generation.
# 2. Checks if the inventory directory exists; if not, it creates the necessary directories.
# 3. Retrieves the control node's IP address and the current user.
# 4. Writes the control node's information to the inventory file.
# 5. If the DEVELOPMENT_MODEL environment variable is set to "true", it attempts to list the Ansible inventory using ansible-navigator.
#    If this step fails, it logs an error message and exits with a status of 1.
generate_inventory() {
    log_message "Generating inventory..."
    if [ ! -d "/opt/qubinode_navigator/inventories/$INVENTORY" ]; then
        mkdir -p "/opt/qubinode_navigator/inventories/$INVENTORY/group_vars/control"
    fi
    local control_host="$(hostname -I | awk '{print $1}')"
    local control_user="$USER"
    echo "[control]" > "/opt/qubinode_navigator/inventories/$INVENTORY/hosts"
    echo "control ansible_connection=local ansible_user=$control_user" >> "/opt/qubinode_navigator/inventories/$INVENTORY/hosts"
    if [ "${DEVELOPMENT_MODEL}" == "true" ]; then
        if ! ansible-navigator inventory --list -m stdout --vault-password-file ~/.vault_password; then
            log_message "Failed to list Ansible inventory"
            exit 1
        fi
    fi
}
