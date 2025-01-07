#!/bin/bash

# Function: handle_hashicorp_vault
# Description: Checks if HashiCorp Vault integration is enabled and verifies that necessary environment variables are set.
# Parameters: None
# Environment Variables:
#   USE_HASHICORP_VAULT - If set to "true", enables HashiCorp Vault integration.
#   VAULT_ADDRESS - The address of the HashiCorp Vault server.
#   VAULT_TOKEN - The token used to authenticate with the HashiCorp Vault server.
#   SECRET_PATH - The path to the secret in HashiCorp Vault.
# Outputs: Logs a message and exits with status 1 if required environment variables are not set.
handle_hashicorp_vault() {
    if [ "$USE_HASHICORP_VAULT" = "true" ]; then
        if [[ -z "$VAULT_ADDRESS" || -z "$VAULT_TOKEN" || -z "$SECRET_PATH" ]]; then
            log_message "VAULT environment variables are not set"
            exit 1
        fi
    fi
}

# Function: configure_ansible_vault
# Description: Configures Ansible Vault by performing the following steps:
# 1. Logs the start of the configuration process.
# 2. Checks if the 'ansiblesafe' command is available; if not, it downloads and installs it.
# 3. Downloads the 'ansible_vault_setup.sh' script if it does not exist in the specified directory.
# 4. Removes any existing vault password file.
# 5. If running in a CI/CD pipeline:
#    a. Ensures the SSH_PASSWORD environment variable is set.
#    b. Writes the SSH_PASSWORD to the vault password file and copies it to the lab-user's home directory.
#    c. Executes the 'ansible_vault_setup.sh' script.
#    d. Depending on the USE_HASHICORP_CLOUD environment variable:
#       - If false, copies 'config.yml' to 'vault.yml' and encrypts it using 'ansiblesafe'.
#       - If true, creates and encrypts 'vault.yml' using 'ansiblesafe', and optionally checks credentials.
# 6. If not running in a CI/CD pipeline:
#    a. Executes the 'ansible_vault_setup.sh' script.
#    b. Encrypts 'vault.yml' using 'ansiblesafe'.
configure_ansible_vault() {
    log_message "Configuring Ansible Vault..."
    if ! command -v ansiblesafe &>/dev/null; then
        local ansiblesafe_url="https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.12/ansiblesafe-v0.0.14-linux-amd64.tar.gz"
        if ! curl -OL "$ansiblesafe_url"; then
            log_message "Failed to download ansiblesafe"
            exit 1
        fi
        if ! tar -zxvf "ansiblesafe-v0.0.14-linux-amd64.tar.gz"; then
            log_message "Failed to extract ansiblesafe"
            exit 1
        fi
        chmod +x ansiblesafe-linux-amd64
        mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
    fi
    if [ ! -f "/opt/qubinode_navigator/ansible_vault_setup.sh" ]; then
        if ! curl -OL https://raw.githubusercontent.com/tosin2013/ansiblesafe/refs/heads/main/ansible_vault_setup.sh; then
            log_message "Failed to download ansible_vault_setup.sh"
            exit 1
        fi
        chmod +x ansible_vault_setup.sh
    fi
    rm -f ~/.vault_password
    if [ "$CICD_PIPELINE" == "true" ]; then
        if [ -z "$SSH_PASSWORD" ]; then
            log_message "SSH_PASSWORD environment variable is not set"
            exit 1
        fi
        echo "$SSH_PASSWORD" > ~/.vault_password
        sudo cp ~/.vault_password /home/lab-user/.vault_password
        if ! bash ./ansible_vault_setup.sh; then
            log_message "Failed to execute ansible_vault_setup.sh"
            exit 1
        fi
        if [ -f /tmp/config.yml ] && [  "$USE_HASHICORP_CLOUD"  == "false" ]; then
            log_message "Copying config.yml to vault.yml"
            if [ -f /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
            then
              rm -rf /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
            fi

            cp -avi /tmp/config.yml "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"
            ls -l "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" || exit $?
            if ! /usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1; then
                log_message "Failed to encrypt vault.yml"
                exit 1
            fi
        elif [ "$USE_HASHICORP_CLOUD" == "true" ]; then
            log_message "Copying config.yml to vault.yml"
            if [ -f /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
            then
              rm -rf /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
            fi

            /usr/local/bin/ansiblesafe -o 5  --file="/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" || exit $?
            ls -l "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" || exit $?
            if [ -f /tmp/config.yml ]; then
                file1_yaml="/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"
                file2_yaml="/tmp/config.yml"
                bash-aliases/check-creds.sh "$file1_yaml" "$file2_yaml"
            fi
            if ! /usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1; then
                log_message "Failed to encrypt vault.yml"
                exit 1
            fi
        else
            log_message "Error:/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml  not created"
            exit 1
        fi
    else
        if ! bash ./ansible_vault_setup.sh; then
            log_message "Failed to execute ansible_vault_setup.sh"
            exit 1
        fi
        if ! /usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"; then
            log_message "Failed to encrypt vault.yml"
            exit 1
        fi
    fi
}
